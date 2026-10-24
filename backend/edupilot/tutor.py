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
from .log import get

log = get("tutor")


def get_current_lesson() -> dict:
    """Get the lesson the student is currently studying: title, explanation, takeaways and the student's preferred language."""
    log.info("tool get_current_lesson")
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
    log.info("tool generate_hint topic=%.40r", topic)
    r = ai.gen(f"Topic: {topic}\nQuestion: {question}\nGive a one-sentence hint that nudges without revealing the answer.")
    return {"hint": r.text}


def create_practice_question(concept: str) -> dict:
    """Create one new multiple-choice practice question for a concept the student finds difficult."""
    log.info("tool create_practice_question concept=%.40r", concept)
    return ai._json(f"Write one multiple-choice practice question (4 options) on: {concept}. review can be empty.", ai.Question)


def search_notes(query: str) -> dict:
    """Search the student's uploaded notes (PDFs) for relevant passages."""
    log.info("tool search_notes q=%.50r", query)
    from . import rag
    cur = db.kv_get("current")
    tag = cur and (db.get_course(cur["course_id"]) or {}).get("notes_tag")
    return {"results": rag.retrieve(query, 3, tag)} if tag else {"results": [], "note": "This course has no uploaded notes."}


INSTRUCTION = ("You are SpritleEduAI's friendly voice tutor. Always call get_current_lesson first to ground your answers in the student's current lesson, "
               "and reply in the student's preferred_language. Keep spoken answers short (2-4 sentences), let the student interrupt, explain code and "
               "quiz mistakes patiently, and use generate_hint / create_practice_question / search_notes when helpful. Never just reveal quiz answers.")


def make_agent(model):
    return Agent(name="edupilot_tutor", model=model, instruction=INSTRUCTION,
                 tools=[get_current_lesson, generate_hint, create_practice_question, search_notes])


_svc = InMemorySessionService()
_runner = Runner(agent=make_agent(ai.MODEL), app_name="edupilot", session_service=_svc)


def transcribe(audio: bytes, mime: str = "audio/wav") -> str:
    log.info("transcribe %d bytes %s", len(audio), mime)
    r = ai.gen([types.Part.from_bytes(data=audio, mime_type=mime),
                "Transcribe this speech verbatim (keep the original language, Tamil or English). Output only the transcript."])
    return (r.text or "").strip()


async def _ask(text, course_id=None):
    """Text turn. Session memory is in-process, so a fresh session is seeded from the persisted chat log."""
    cid = course_id if course_id is not None else (db.kv_get("current") or {"course_id": 0})["course_id"]
    sid = f"c{cid}"
    if not await _svc.get_session(app_name="edupilot", user_id="student", session_id=sid):
        await _svc.create_session(app_name="edupilot", user_id="student", session_id=sid)
        hist = db.get_chat(cid, limit=12)
        if hist:
            text = "Earlier conversation (for context):\n" + "\n".join(f"{m['role']}: {m['text']}" for m in hist) + "\n\nNew message: " + text
    for i in range(4):
        out = ""
        log.info("ask session=%s attempt=%d msg=%.80r", sid, i + 1, text)
        try:
            async for ev in _runner.run_async(user_id="student", session_id=sid, new_message=types.Content(role="user", parts=[types.Part(text=text)])):
                if ev.is_final_response() and ev.content and ev.content.parts:
                    out = "".join(p.text or "" for p in ev.content.parts)
            log.info("reply %d chars", len(out))
            return out
        except Exception as e:
            if not ai.is_quota(e) or ai.is_daily(e) or i == 3:
                raise
            await asyncio.sleep(ai.retry_delay(e))


def ask(text):
    return asyncio.run(_ask(text))
