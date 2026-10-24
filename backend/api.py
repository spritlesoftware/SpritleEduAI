"""EduPilot REST API. Frontend-agnostic; interactive docs at /docs."""
import asyncio, os
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from edupilot import ai, db, media, plan

app = FastAPI(title="EduPilot AI")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])  # ponytail: tighten origins once frontend URL is known
Lang = str  # "en" | "ta"


class CourseIn(BaseModel):
    goal: str = Field(min_length=3)
    level: str = Field("beginner", pattern="^(beginner|intermediate|advanced)$")
    duration_days: int = Field(30, ge=1, le=365)
    daily_study_minutes: int = Field(60, ge=10, le=480)
    format: str = "Mixed learning"
    notes_tag: str | None = None  # tag returned by POST /notes


class QuizIn(BaseModel):
    answers: list[int]
    lang: Lang = "en"


def _course(cid):
    c = db.get_course(cid)
    if not c:
        raise HTTPException(404, "course not found")
    return c


def _lesson(c, k, lang, ctx=""):
    if k not in dict(plan.lessons(c)):
        raise HTTPException(404, "lesson not found")
    had = lang in c.get("content", {}).get(k, {})
    L = ai.lesson_for(c, k, lang, ctx)
    if not had:
        db.save_course(c, c["id"])
    return L


@app.post("/notes")
async def upload_notes(files: list[UploadFile] = File(...), tag: str = Form("pending")):
    from edupilot import rag
    n = sum([rag.ingest_pdf(await f.read(), f.filename, tag) for f in files])
    return {"tag": tag, "chunks": n}


@app.post("/courses")
def create_course(b: CourseIn):
    notes = ""
    if b.notes_tag:
        from edupilot import rag
        notes = "\n---\n".join(r["text"][:800] for r in rag.retrieve(b.goal, 5, b.notes_tag))
    c = ai.generate_course(b.goal, b.level, b.duration_days, b.daily_study_minutes, b.format, notes)
    c["notes_tag"] = b.notes_tag
    db.save_course(c)
    return c


@app.get("/courses")
def courses():
    return [{"id": i, "title": t} for i, t in db.list_courses()]


@app.get("/courses/{cid}")
def course(cid: int):
    c = _course(cid)
    c.pop("content", None)
    done = db.done_keys(cid)
    ls = plan.lessons(c)
    return {**c, "lesson_keys": [k for k, _ in ls], "done": sorted(done), "progress": len(done) / max(1, len(ls))}


@app.get("/courses/{cid}/schedule")
def schedule(cid: int):
    c = _course(cid)
    s = plan.schedule(c, db.done_keys(cid))
    return {"days": s, "over_goal": len(s) > c["duration_days"]}


@app.get("/courses/{cid}/lessons/{k}")
def lesson(cid: int, k: str, lang: Lang = "en"):
    c = _course(cid)
    ctx = ""
    if c.get("notes_tag"):
        from edupilot import rag
        ctx = "\n".join(r["text"] for r in rag.retrieve(dict(plan.lessons(c))[k]["title"], 3, c["notes_tag"]))
    L = _lesson(c, k, lang, ctx)
    db.kv_set("current", {"course_id": cid, "key": k}); db.kv_set("lang", lang)  # context for the voice tutor
    return {**L, "title": dict(plan.lessons(c))[k]["title"],
            "quiz": [{kk: v for kk, v in q.items() if kk not in ("answer_index", "explanation", "review")} for q in L["quiz"]]}


@app.post("/courses/{cid}/lessons/{k}/quiz")
def submit_quiz(cid: int, k: str, b: QuizIn):
    c = _course(cid)
    quiz = _lesson(c, k, b.lang)["quiz"]
    if len(b.answers) != len(quiz):
        raise HTTPException(422, f"expected {len(quiz)} answers")
    res = [{"concept": q["concept"], "review": q["review"], "correct": a == q["answer_index"]} for q, a in zip(quiz, b.answers)]
    score, revisit = plan.recommend(c, k, res)
    missed = [r["concept"] for r in res if not r["correct"]]
    db.record_attempt(cid, k, score, missed, [(r["concept"], r["correct"]) for r in res])
    out = {"score": score, "passed": score >= plan.PASS, "revisit": revisit, "remedial": None,
           "results": [{"correct": r["correct"], "correct_index": q["answer_index"], "explanation": q["explanation"]} for q, r in zip(quiz, res)]}
    if out["passed"]:
        db.mark_done(cid, k)
    else:
        p = ai.generate_practice(c, k, missed, b.lang)
        rk = plan.add_remedial(c, k, p["title"])
        dict(plan.lessons(c))[rk]["practice"] = p
        db.save_course(c, cid)
        out["remedial"] = {"key": rk, "title": p["title"]}
    return out


@app.post("/courses/{cid}/lessons/{k}/complete")
def complete(cid: int, k: str):
    _course(cid); db.mark_done(cid, k)
    return {"ok": True}


@app.post("/courses/{cid}/lessons/{k}/video")
async def build_video(cid: int, k: str, lang: Lang = "en", with_clip: bool = False):
    c = _course(cid)
    L = _lesson(c, k, lang)
    if "slides" not in L:
        raise HTTPException(422, "remedial lessons have no video")
    def work():
        clip = media.generate_clip(L["clip_prompt"], os.path.join(media.OUT, f"{cid}_{k}_clip.mp4")) if with_clip else None
        media.build_video(L, f"{cid}_{k}_{lang}", lang, clip)
    try:
        await asyncio.to_thread(work)  # ponytail: blocks the request ~1 min; move to a job queue if needed
    except Exception as e:
        raise HTTPException(502, f"video failed: {e}")
    return {"video": f"/media/{cid}_{k}_{lang}.mp4", "captions": f"/media/{cid}_{k}_{lang}.vtt"}


@app.get("/media/{name}")
def media_file(name: str):
    p = os.path.realpath(os.path.join(media.OUT, name))
    if not p.startswith(os.path.realpath(media.OUT) + os.sep) or not os.path.exists(p):
        raise HTTPException(404)
    return FileResponse(p, media_type="text/vtt" if name.endswith(".vtt") else "video/mp4")


@app.get("/courses/{cid}/review")
def review(cid: int, lang: Lang = "en"):
    c = _course(cid)
    cards = [x for k, _ in plan.lessons(c) for x in c.get("content", {}).get(k, {}).get(lang, {}).get("flashcards", [])]
    m = db.mastery(cid)
    return {"flashcards": cards, "mastery": m, "weak_concepts": [x for x, v in m.items() if v < plan.PASS],
            "attempts": [{"key": a["key"], "score": a["score"], "ts": a["ts"]} for a in db.attempts(cid)]}


@app.post("/tutor")
async def tutor_ask(course_id: int = Form(...), key: str = Form(...), lang: Lang = Form("en"),
                    text: str | None = Form(None), audio: UploadFile | None = File(None)):
    from edupilot import tutor
    _course(course_id)
    db.kv_set("current", {"course_id": course_id, "key": key}); db.kv_set("lang", lang)
    if not text and not audio:
        raise HTTPException(422, "send text or audio")
    reply = await tutor._ask(text, await audio.read() if audio else None)
    return {"reply": reply}


@app.post("/tts")
async def tts(text: str = Form(...), lang: Lang = Form("en")):
    return Response(await asyncio.to_thread(media.speak, text, lang), media_type="audio/mpeg")


@app.get("/health")
def health():
    return {"ok": True, "gemini_key": bool(os.environ.get("GEMINI_API_KEY"))}
