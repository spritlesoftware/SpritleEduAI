"""End-to-end through the real HTTP API against live Gemini. Temp DB. Flow: course -> lesson -> video -> fail quiz -> adaptive plan -> pass -> review -> tutor."""
import os, tempfile
os.environ["EDUPILOT_DB"] = os.path.join(tempfile.mkdtemp(), "e2e.db")
from fastapi.testclient import TestClient
from api import app
from edupilot import db

c = TestClient(app)


def step(m): print(f"\n== {m}", flush=True)


def ok(r):
    assert r.status_code == 200, f"{r.request.url} -> {r.status_code} {r.text[:300]}"
    return r.json()


assert ok(c.get("/health"))["gemini_key"], "GEMINI_API_KEY missing"

step("1. create course")
course = ok(c.post("/courses", json={"goal": "Learn Python basics and build a small project", "level": "beginner",
                                     "duration_days": 7, "daily_study_minutes": 30, "format": "Video + interactive lessons"}))
cid = course["id"]
assert course["modules"] and course["capstone"]
print(course["title"], "|", len(ok(c.get(f"/courses/{cid}"))["lesson_keys"]), "lessons")
assert ok(c.get("/courses"))[0]["id"] == cid

step("2. study plan")
print(len(ok(c.get(f"/courses/{cid}/schedule"))["days"]), "days")

step("3. lesson (answers must not leak)")
k = "m0l0"
L = ok(c.get(f"/courses/{cid}/lessons/{k}"))
assert L["slides"] and len(L["quiz"]) >= 3 and L["flashcards"]
assert all("answer_index" not in q for q in L["quiz"])
n = len(L["quiz"]); print(len(L["slides"]), "slides,", n, "questions")

step("4. narrated video + captions")
v = ok(c.post(f"/courses/{cid}/lessons/{k}/video"))
mp4, vtt = c.get(v["video"]), c.get(v["captions"])
assert mp4.status_code == 200 and len(mp4.content) > 10_000 and vtt.text.startswith("WEBVTT")
print(v["video"], len(mp4.content) // 1024, "KB")

step("5. wrong answers -> failed, remedial lesson added to plan")
full = db.get_course(cid)["content"][k]["en"]["quiz"]
wrong = [(q["answer_index"] + 1) % len(q["options"]) for q in full]
r = ok(c.post(f"/courses/{cid}/lessons/{k}/quiz", json={"answers": wrong}))
assert not r["passed"] and r["revisit"] and r["remedial"]
rk = r["remedial"]["key"]
plan_keys = [i[0] for d in ok(c.get(f"/courses/{cid}/schedule"))["days"] for i in d["items"]]
assert rk in plan_keys, "remedial not scheduled"
print("remedial:", r["remedial"]["title"])
rem = ok(c.get(f"/courses/{cid}/lessons/{rk}"))
assert rem["quiz"] and "answer_index" not in rem["quiz"][0]

step("6. correct answers -> pass, lesson done")
r = ok(c.post(f"/courses/{cid}/lessons/{k}/quiz", json={"answers": [q["answer_index"] for q in full]}))
assert r["passed"]
assert k in ok(c.get(f"/courses/{cid}"))["done"]

step("7. review: flashcards + mastery")
rv = ok(c.get(f"/courses/{cid}/review"))
assert rv["flashcards"] and rv["mastery"] and len(rv["attempts"]) == 2
print(len(rv["flashcards"]), "cards, weak:", rv["weak_concepts"])

step("8. voice tutor (text turn via ADK + tools) and TTS")
t = ok(c.post("/tutor", data={"course_id": cid, "key": k, "text": "Explain this lesson in two sentences."}))
assert t["reply"].strip(); print(t["reply"][:300])
a = c.post("/tts", data={"text": t["reply"][:200]})
assert a.status_code == 200 and len(a.content) > 1000

print("\nE2E PASSED")
