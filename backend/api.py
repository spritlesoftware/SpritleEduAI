"""SpritleEduAI REST API. Frontend-agnostic; interactive docs at /docs."""
import asyncio, os, time, uuid
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel, Field

from edupilot import ai, db, media, plan
from edupilot.log import get

log = get("api")

app = FastAPI(title="SpritleEduAI")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])  # ponytail: tighten origins once frontend URL is known


@app.middleware("http")
async def _access(request, call_next):
    t = time.time()
    try:
        r = await call_next(request)
    except Exception:
        log.exception("%s %s -> unhandled error (%.0fms)", request.method, request.url.path, (time.time() - t) * 1000)
        raise
    log.info("%s %s -> %d (%.0fms)", request.method, request.url.path, r.status_code, (time.time() - t) * 1000)
    return r


@app.exception_handler(Exception)
async def _quota(request, e):
    log.error("%s %s failed: %s: %.300s", request.method, request.url.path, type(e).__name__, e, exc_info=not ai.is_quota(e))
    if ai.is_quota(e):
        return JSONResponse({"detail": "Gemini daily quota exhausted; use another key/model or wait." if ai.is_daily(e) else "Gemini rate limit reached, retry in about a minute."}, status_code=429, headers={"Retry-After": "60"})
    return JSONResponse({"detail": f"internal error: {e}"}, status_code=500)


Lang = str  # "en" | "ta"


class CourseIn(BaseModel):
    source: str = Field("topic", pattern="^(topic|notes)$")  # topic = AI builds from the goal; notes = built ONLY from the student's uploaded notes (RAG)
    goal: str = Field("", max_length=2000)
    level: str = Field("beginner", pattern="^(beginner|intermediate|advanced)$")
    duration_days: int = Field(30, ge=1, le=365)
    daily_study_minutes: int = Field(60, ge=10, le=480)
    format: str = "Mixed learning"
    notes_tag: str | None = None  # required when source="notes"; returned by POST /notes


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
async def upload_notes(files: list[UploadFile] = File(...), tag: str | None = Form(None)):
    """Upload PDF notes. Returns a `notes_tag` to pass to POST /courses (source="notes") - each upload gets its own tag unless one is given."""
    from edupilot import rag
    tag = tag or uuid.uuid4().hex[:12]
    chunks = {}
    for f in files:
        chunks[f.filename] = await asyncio.to_thread(rag.ingest_pdf, await f.read(), f.filename, tag)
    log.info("notes uploaded tag=%s files=%s", tag, chunks)
    if not any(chunks.values()):
        raise HTTPException(422, "no readable text found (scanned/image-only PDF?)")
    return {"notes_tag": tag, "files": chunks}


@app.post("/courses")
def create_course(b: CourseIn):
    from edupilot import rag
    if b.source == "notes":
        if not b.notes_tag or not rag.count(b.notes_tag):
            raise HTTPException(422, "source='notes' needs a notes_tag from POST /notes with readable PDFs")
        goal = b.goal.strip() or "Learn the material in my notes"
        notes = "\n---\n".join(f"[{r['source']}] {r['text']}" for r in rag.sample(b.notes_tag, 12))
        c = ai.generate_course(goal, b.level, b.duration_days, b.daily_study_minutes, b.format, notes, from_notes=True)
        c["source"], c["notes_tag"] = "notes", b.notes_tag
    else:
        if len(b.goal.strip()) < 3:
            raise HTTPException(422, "goal is required for source='topic'")
        c = ai.generate_course(b.goal, b.level, b.duration_days, b.daily_study_minutes, b.format)
        c["source"], c["notes_tag"] = "topic", None
    db.save_course(c)
    log.info("course created id=%s source=%s title=%r", c["id"], c["source"], c["title"])
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
    if k not in dict(plan.lessons(c)):
        raise HTTPException(404, "lesson not found")
    ctx, sources = "", []
    if c.get("source") == "notes" and lang not in c.get("content", {}).get(k, {}):
        from edupilot import rag
        hits = rag.retrieve(dict(plan.lessons(c))[k]["title"], 5, c["notes_tag"])
        ctx = "\n".join(f"[{h['source']}] {h['text']}" for h in hits)
        c.setdefault("sources", {})[k] = sorted({h["source"] for h in hits})
    L = _lesson(c, k, lang, ctx)
    db.kv_set("current", {"course_id": cid, "key": k}); db.kv_set("lang", lang)  # context for the voice tutor
    return {**L, "title": dict(plan.lessons(c))[k]["title"], "sources": c.get("sources", {}).get(k, []),
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
    log.info("quiz course=%s lesson=%s score=%.0f%% missed=%s", cid, k, score * 100, missed)
    out = {"score": score, "passed": score >= plan.PASS, "revisit": revisit, "remedial": None,
           "results": [{"correct": r["correct"], "correct_index": q["answer_index"], "explanation": q["explanation"]} for q, r in zip(quiz, res)]}
    if out["passed"]:
        db.mark_done(cid, k)
    else:
        p = ai.generate_practice(c, k, missed, b.lang)
        rk = plan.add_remedial(c, k, p["title"])
        dict(plan.lessons(c))[rk]["practice"] = p
        db.save_course(c, cid)
        log.info("remedial lesson %s added after %s: %r", rk, k, p["title"])
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
        media.build_video(L, f"{cid}_{k}_{lang}_v{L.get('v', 1)}", lang, clip)
    try:
        await asyncio.to_thread(work)  # ponytail: blocks the request ~1 min; move to a job queue if needed
    except Exception as e:
        raise HTTPException(502, f"video failed: {e}")
    return {"video": f"/media/{cid}_{k}_{lang}_v{L.get('v', 1)}.mp4", "captions": f"/media/{cid}_{k}_{lang}_v{L.get('v', 1)}.vtt"}


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
    """Send text, or recorded speech (any browser audio format). Speech is transcribed, saved as the user's chat message and returned as `transcript`."""
    from edupilot import tutor
    _course(course_id)
    if not text and not audio:
        raise HTTPException(422, "send text or audio")
    db.kv_set("current", {"course_id": course_id, "key": key}); db.kv_set("lang", lang)
    transcript = None
    if audio:
        transcript = await asyncio.to_thread(tutor.transcribe, await audio.read(), (audio.content_type or "audio/wav").split(";")[0])
        if not transcript:
            raise HTTPException(422, "could not understand the audio")
    user_text = text or transcript
    db.add_chat(course_id, key, "user", user_text, "voice" if audio else "text")
    log.info("tutor q (%s) course=%s lesson=%s: %.100r", "voice" if audio else "text", course_id, key, user_text)
    reply = await tutor._ask(user_text, course_id)
    db.add_chat(course_id, key, "assistant", reply)
    return {"transcript": transcript, "reply": reply}


@app.get("/courses/{cid}/chat")
def chat_history(cid: int, key: str | None = None):
    """Persisted tutor conversation (all lessons, or one with ?key=)."""
    _course(cid)
    return db.get_chat(cid, key)


@app.post("/tts")
async def tts(text: str = Form(...), lang: Lang = Form("en")):
    return Response(await asyncio.to_thread(media.speak, text, lang), media_type="audio/mpeg")


@app.get("/health")
def health():
    return {"ok": True, "gemini_key": bool(os.environ.get("GEMINI_API_KEY"))}
