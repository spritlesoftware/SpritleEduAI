"""Voice tutor on Google ADK. Same agent serves `adk web` (live model, real-time voice) and Streamlit (turn-based audio/text)."""
import asyncio, os
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault("GOOGLE_API_KEY", os.environ.get("GEMINI_API_KEY", ""))

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from . import ai, db, plan


def get_current_lesson() -> dict:
    """Get the lesson the student is currently studying: title, explanation, takeaways and the student's preferred language."""
    cur = db.kv_get("current")
    if not cur:
        return {"error": "No lesson open yet."}
    course = db.get_course(cur["course_id"])
    lang = db.kv_get("lang", "en")
    les = dict(plan.lessons(course))[cur["key"]]
    L = course.get("content", {}).get(cur["key"], {}).get(lang) or next(iter(course.get("content", {}).get(cur["key"], {}).values()), {})
    return {"course": course["title"], "lesson": les["title"], "explanation": L.get("explanation", ""),
            "key_takeaways": L.get("key_takeaways", []), "code": L.get("code_example"),
            "preferred_language": "Tamil (keep technical terms in English)" if lang == "ta" else "English",
            "mastery_gaps": [c for c, v in db.mastery(cur["course_id"]).items() if v < plan.PASS]}


def generate_hint(question: str, topic: str) -> dict:
    """Give a short hint (not the answer) for a quiz question the student is stuck on."""
    r = ai.client().models.generate_content(model=ai.MODEL, contents=f"Topic: {topic}\nQuestion: {question}\nGive a one-sentence hint that nudges without revealing the answer.")
    return {"hint": r.text}


def create_practice_question(concept: str) -> dict:
    """Create one new multiple-choice practice question for a concept the student finds difficult."""
    return ai._json(f"Write one multiple-choice practice question (4 options) on: {concept}. review can be empty.", ai.Question)


def search_notes(query: str) -> dict:
    """Search the student's uploaded notes (PDFs) for relevant passages."""
    from . import rag
    return {"results": rag.retrieve(query, 3, "pending")}


INSTRUCTION = ("You are EduPilot's friendly voice tutor. Always call get_current_lesson first to ground your answers in the student's current lesson, "
               "and reply in the student's preferred_language. Keep spoken answers short (2-4 sentences), let the student interrupt, explain code and "
               "quiz mistakes patiently, and use generate_hint / create_practice_question / search_notes when helpful. Never just reveal quiz answers.")


def make_agent(model):
    return Agent(name="edupilot_tutor", model=model, instruction=INSTRUCTION,
                 tools=[get_current_lesson, generate_hint, create_practice_question, search_notes])


_svc = InMemorySessionService()
_runner = Runner(agent=make_agent(ai.MODEL), app_name="edupilot", session_service=_svc)


async def _ask(text, audio):
    cur = db.kv_get("current") or {"course_id": 0}
    sid = f"c{cur['course_id']}"
    if not await _svc.get_session(app_name="edupilot", user_id="student", session_id=sid):
        await _svc.create_session(app_name="edupilot", user_id="student", session_id=sid)
    parts = ([types.Part.from_bytes(data=audio, mime_type="audio/wav")] if audio else []) + ([types.Part(text=text)] if text else [])
    out = ""
    async for ev in _runner.run_async(user_id="student", session_id=sid, new_message=types.Content(role="user", parts=parts)):
        if ev.is_final_response() and ev.content and ev.content.parts:
            out = "".join(p.text or "" for p in ev.content.parts)
    return out


def ask(text=None, audio=None):
    """Turn-based tutor call (text and/or wav bytes). Returns reply text."""
    return asyncio.run(_ask(text, audio))
