# SpritleEduAI

AI course builder by Spritle. A student describes a goal (or uploads their own PDF notes) and gets a full course: modules, lessons with slides, narrated video, quizzes, flashcards and projects, plus a voice tutor and an adaptive study plan that reacts to quiz results.

MVP stage. Gemini does all generation.

## Features

- **Two ways to build a course**
  - *Learn a topic*: AI designs the curriculum from your goal, level, duration, daily time and format.
  - *Learn from my notes*: the course is built only from your uploaded PDFs (RAG). Lessons list their source files.
- **Lessons**: narrated slide video with captions (renders automatically when a lesson opens), in-depth slides, explanation, code example, key takeaways, flashcards. Lessons are generated the first time you open them.
- **Quizzes with instant grading**: failing one adds a full-length practice lesson to your plan, written in the background. Mastery per concept is tracked.
- **Voice tutor** (Google ADK): ask by typing or by voice. Speech is transcribed and shown in the chat, voice questions get spoken answers (mute button available), chat history is saved.
- **Study plan**: lessons packed into your daily study time; practice lessons are inserted and the plan re-flows.

## Layout

```
boot.sh        one-command setup and run
backend/       FastAPI + SQLite + ChromaDB, Gemini via google-genai / ADK
  api.py         REST endpoints (docs at /docs)
  edupilot/      ai (generation), plan (schedule + adaptivity), media (video), rag, tutor, db, log
  tutor_agent/   same tutor agent for `adk web` (real-time voice)
  e2e.py         end-to-end test against the real API and Gemini
frontend/      React + Vite + Tailwind (proxies /api to :8000)
```

## Requirements

- Python 3.12, Node 18+, `ffmpeg` (`sudo apt install ffmpeg`)
- A Gemini API key

## Setup

```bash
cp backend/.env.example backend/.env     # then set GEMINI_API_KEY (and GEMINI_MODEL)
./boot.sh                                # creates the venv, installs deps, serves the API on :8000
cd frontend && npm install && npm run dev   # UI on http://localhost:5173
```

`./boot.sh` modes: *(none)* run the API, `adk` real-time voice dev UI, `test` pytest, `e2e` full end-to-end run.

## Configuration (`backend/.env`)

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | required |
| `GEMINI_MODEL` | text/JSON generation, tutor, transcription |
| `GEMINI_LIVE_MODEL` | real-time voice model for `./boot.sh adk` |
| `GEMINI_VIDEO_MODEL` | optional AI clip intro; leave empty to skip. Check current availability and quota first |
| `LOG_LEVEL` | `INFO` (default) or `DEBUG` |

Free-tier keys have tight per-minute and per-day request limits and some models are unavailable to new keys. The API retries per-minute limits and returns HTTP 429 with a clear message when the daily quota is gone. If that happens, switch `GEMINI_MODEL`.

## API (summary)

`POST /notes` upload PDFs, returns `notes_tag` · `POST /courses` (`source`: `topic` | `notes`) · `GET /courses`, `/courses/{id}`, `/courses/{id}/schedule`, `/courses/{id}/review` · `GET /courses/{id}/lessons/{key}` · `POST .../quiz` · `POST .../video` · `POST /tutor` (text or audio) · `GET /courses/{id}/chat` · `POST /tts` · `GET /health`.
Quiz answers are never sent to the client; grading happens on the server.

## Testing

```bash
./boot.sh test   # schedule/adaptivity self-check
./boot.sh e2e    # create course, lesson, video, fail/pass quiz, adaptive plan, voice, notes-RAG (uses real Gemini calls)
```

## Known limits

- Real-time streaming voice works through `./boot.sh adk` only; in the app the tutor is turn-based (record, then reply) and Tamil is not exposed in the UI.
- Video rendering blocks its request for about a minute; a job queue would be the next step.
- Single-user: no auth, one shared "current lesson" for the tutor, SQLite storage.
- Scanned (image-only) PDFs have no text to index.
