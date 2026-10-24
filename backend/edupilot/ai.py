import json, os, re, time
from typing import Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

from . import plan
from .log import get

log = get("ai")

load_dotenv()
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
_client = None


def client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _client


class LessonStub(BaseModel):
    title: str
    estimated_minutes: int
    content_type: str  # video_and_practice | reading_and_exercises | voice_and_project


class Project(BaseModel):
    title: str
    description: str


class Module(BaseModel):
    title: str
    learning_objectives: list[str]
    lessons: list[LessonStub]
    project: Project


class Course(BaseModel):
    title: str
    description: str
    prerequisites: list[str]
    learning_outcomes: list[str]
    modules: list[Module]
    capstone: Project


class Slide(BaseModel):
    title: str
    bullets: list[str]
    code: Optional[str] = None
    detail: Optional[str] = None  # deeper explanation shown under the bullets
    narration: str


class Question(BaseModel):
    question: str
    options: list[str]
    answer_index: int
    concept: str
    review: str  # key of an EARLIER-or-same lesson to revisit if missed
    explanation: str


class Card(BaseModel):
    front: str
    back: str


class Lesson(BaseModel):
    explanation: str
    key_takeaways: list[str]
    code_language: Optional[str] = None
    code_example: Optional[str] = None
    slides: list[Slide]
    quiz: list[Question]
    flashcards: list[Card]
    clip_prompt: str


class Practice(BaseModel):
    title: str
    explanation: str
    quiz: list[Question]


CONTENT_V = 3  # bump to regenerate cached lessons with a richer format
LANG = {"en": "English", "ta": "Tamil (தமிழ்) explanations, keeping technical terms and code in English"}


def is_quota(e):
    return "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e)


def is_daily(e):
    return "PerDay" in str(e)  # daily quota: retrying within a minute is pointless


def retry_delay(e):
    m = re.search(r"retry in ([\d.]+)s", str(e))
    return min(float(m.group(1)) + 2, 65) if m else 30


def gen(contents, config=None):
    """generate_content with backoff on 429 (free tier is ~5 req/min)."""
    for i in range(4):
        t = time.time()
        try:
            r = client().models.generate_content(model=MODEL, contents=contents, config=config)
            log.info("gemini ok model=%s %.1fs attempt=%d", MODEL, time.time() - t, i + 1)
            return r
        except Exception as e:
            if not is_quota(e) or is_daily(e) or i == 3:
                log.error("gemini failed model=%s %.1fs daily_quota=%s: %.200s", MODEL, time.time() - t, is_daily(e), e)
                raise
            d = retry_delay(e)
            log.warning("gemini rate-limited (attempt %d), sleeping %.0fs", i + 1, d)
            time.sleep(d)


def _json(prompt, schema, system=None):
    r = gen(prompt, types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema,
                                                system_instruction=system, temperature=0.6))
    return json.loads(r.text)


def generate_course(goal, level, days, minutes, fmt, notes="", from_notes=False):
    total = days * minutes
    log.info("generate_course goal=%.60r level=%s %dd x %dmin from_notes=%s", goal, level, days, minutes, from_notes)
    d = _json(
        f"Student goal: {goal}\nLevel: {level}\nDuration: {days} days, {minutes} min/day (~{total} total minutes).\n"
        f"Preferred format: {fmt}.\n"
        + (f"SOURCE MODE: the student wants to learn FROM THEIR OWN NOTES. Build the curriculum ONLY from topics present in these notes; "
           f"do not add outside topics. Order them pedagogically.\nNOTES:\n{notes}\n" if from_notes else "") +
        f"Design a Coursera-style course. Sum of lesson estimated_minutes should be roughly {total}. "
        "Each lesson 15-45 minutes. Each module has a hands-on project; include a final capstone. "
        "content_type must be one of video_and_practice, reading_and_exercises, voice_and_project, matching the preferred format (Mixed: vary them).",
        Course, "You are an expert curriculum designer.")
    log.info("course ready: %r, %d modules, %d lessons", d["title"], len(d["modules"]), sum(len(m["lessons"]) for m in d["modules"]))
    d.update(goal=goal, level=level, duration_days=days, daily_study_minutes=minutes, format=fmt, content={}, remedial=[])
    return d


def outline(course):
    return "\n".join(f"{k}: {l['title']}" for k, l in plan.lessons(course))


def generate_lesson(course, k, lang="en", context=""):
    notes_mode = course.get("source") == "notes"
    les = dict(plan.lessons(course))[k]
    log.info("generate_lesson course=%s key=%s %r lang=%s grounded=%s", course.get("id"), k, les["title"], lang, bool(context))
    out = _json(
        f"Course: {course['title']} (level {course['level']}). Goal: {course['goal']}\n"
        f"Course outline (key: title):\n{outline(course)}\n\n"
        f"Write lesson {k}: '{les['title']}' (~{les['estimated_minutes']} min). Language: {LANG[lang]}.\n"
        + (f"{'Teach ONLY from' if notes_mode else 'Ground the content in'} these student notes{' (do not invent facts beyond them; say so if they do not cover something)' if notes_mode else ''}:{chr(10)}{context}{chr(10)}" if context else "") +
        "Give: explanation (markdown), 3-5 key_takeaways, a runnable code_example if the topic is programming (else null), "
        "6-8 detailed slides that together TEACH the lesson (not just outline it): each has a clear title, 4-6 bullets written as full explanatory sentences (15-30 words) with concrete facts and definitions, a `detail` field of 3-5 sentences (60-100 words) that goes deeper with a worked example, analogy or common pitfall, optional code with a short comment per line when the slide is about code, and a 5-7 sentence spoken narration that elaborates beyond the bullets, "
        "4 multiple-choice questions (4 options, answer_index 0-3) each tagged with a short `concept` and `review` = the outline key of the lesson "
        "that best teaches that concept (must be this lesson or an earlier one), 4 flashcards, and a one-sentence clip_prompt for an illustrative visual.",
        Lesson, "You are an engaging, accurate teacher.")
    out["v"] = CONTENT_V
    return out


def generate_practice(course, k, missed_concepts, lang="en"):
    les = dict(plan.lessons(course))[k]
    log.info("generate_practice course=%s key=%s concepts=%s", course.get("id"), k, missed_concepts)
    return _json(
        f"Course: {course['title']}. The student struggled with: {', '.join(missed_concepts)} (lesson '{les['title']}').\n"
        f"Outline:\n{outline(course)}\nLanguage: {LANG[lang]}.\n"
        "Write a short targeted remedial lesson: title, a clear explanation with a worked example, and 3 new multiple-choice questions "
        "(different from a standard quiz) with concept and review keys from the outline.",
        Practice, "You are a patient tutor.")


def lesson_for(course, k, lang="en", context=""):
    """Cached lesson content; generated on first open. Mutates course['content']; caller saves."""
    c = course.setdefault("content", {}).setdefault(k, {})
    if lang in c and not dict(plan.lessons(course))[k].get("remedial") and c[lang].get("v") != CONTENT_V:
        log.info("lesson %s cached with old format (v=%s), regenerating", k, c[lang].get("v"))
        del c[lang]
    if lang not in c:
        les = dict(plan.lessons(course))[k]
        if les.get("remedial"):
            c[lang] = les["practice"]
        else:
            c[lang] = generate_lesson(course, k, lang, context)
    return c[lang]
