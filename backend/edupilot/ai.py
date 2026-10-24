import json, os
from typing import Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel

from . import plan

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


LANG = {"en": "English", "ta": "Tamil (தமிழ்) explanations, keeping technical terms and code in English"}


def _json(prompt, schema, system=None):
    r = client().models.generate_content(
        model=MODEL, contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema,
                                           system_instruction=system, temperature=0.6))
    return json.loads(r.text)


def generate_course(goal, level, days, minutes, fmt, notes=""):
    total = days * minutes
    d = _json(
        f"Student goal: {goal}\nLevel: {level}\nDuration: {days} days, {minutes} min/day (~{total} total minutes).\n"
        f"Preferred format: {fmt}.\n{('Reference notes from student documents:'+chr(10)+notes) if notes else ''}\n"
        f"Design a Coursera-style course. Sum of lesson estimated_minutes should be roughly {total}. "
        "Each lesson 15-45 minutes. Each module has a hands-on project; include a final capstone. "
        "content_type must be one of video_and_practice, reading_and_exercises, voice_and_project, matching the preferred format (Mixed: vary them).",
        Course, "You are an expert curriculum designer.")
    d.update(goal=goal, level=level, duration_days=days, daily_study_minutes=minutes, format=fmt, content={}, remedial=[])
    return d


def outline(course):
    return "\n".join(f"{k}: {l['title']}" for k, l in plan.lessons(course))


def generate_lesson(course, k, lang="en", context=""):
    les = dict(plan.lessons(course))[k]
    return _json(
        f"Course: {course['title']} (level {course['level']}). Goal: {course['goal']}\n"
        f"Course outline (key: title):\n{outline(course)}\n\n"
        f"Write lesson {k}: '{les['title']}' (~{les['estimated_minutes']} min). Language: {LANG[lang]}.\n"
        f"{('Ground the content in these student notes:'+chr(10)+context) if context else ''}\n"
        "Give: explanation (markdown), 3-5 key_takeaways, a runnable code_example if the topic is programming (else null), "
        "4-6 slides (each with concise bullets, optional code, and a 2-4 sentence spoken narration), "
        "4 multiple-choice questions (4 options, answer_index 0-3) each tagged with a short `concept` and `review` = the outline key of the lesson "
        "that best teaches that concept (must be this lesson or an earlier one), 4 flashcards, and a one-sentence clip_prompt for an illustrative visual.",
        Lesson, "You are an engaging, accurate teacher.")


def generate_practice(course, k, missed_concepts, lang="en"):
    les = dict(plan.lessons(course))[k]
    return _json(
        f"Course: {course['title']}. The student struggled with: {', '.join(missed_concepts)} (lesson '{les['title']}').\n"
        f"Outline:\n{outline(course)}\nLanguage: {LANG[lang]}.\n"
        "Write a short targeted remedial lesson: title, a clear explanation with a worked example, and 3 new multiple-choice questions "
        "(different from a standard quiz) with concept and review keys from the outline.",
        Practice, "You are a patient tutor.")


def lesson_for(course, k, lang="en", context=""):
    """Cached lesson content; generated on first open. Mutates course['content']; caller saves."""
    c = course.setdefault("content", {}).setdefault(k, {})
    if lang not in c:
        les = dict(plan.lessons(course))[k]
        if les.get("remedial"):
            c[lang] = les["practice"]
        else:
            c[lang] = generate_lesson(course, k, lang, context)
    return c[lang]
