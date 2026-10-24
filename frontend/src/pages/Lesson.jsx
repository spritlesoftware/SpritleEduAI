import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import Markdown from "react-markdown";
import { api } from "../api.js";
import { ErrorBox, Icon, Spinner, lessonIndex, useAsync, useLang } from "../ui.jsx";
import { TutorPanel } from "./Tutor.jsx";

function Video({ id, k, lang }) {
  const [v, setV] = useState(null);
  const [busy, setBusy] = useState(true);
  const [err, setErr] = useState(null);
  const [t, setT] = useState(0);
  const build = async () => {
    setBusy(true); setErr(null); setT(0);
    try { setV(await api.video(id, k, lang)); } catch (e) { setErr(e.message); }
    setBusy(false);
  };
  useEffect(() => { build(); }, [id, k, lang]);  // start rendering as soon as the lesson opens; cached on the server after the first time
  useEffect(() => { if (!busy) return; const i = setInterval(() => setT((x) => x + 1), 1000); return () => clearInterval(i); }, [busy]);
  const stage = ["Writing slides", "Recording narration", "Syncing captions", "Assembling video"][Math.min(3, Math.floor(t / 12))];
  return (
    <section className="rounded-xl bg-navy p-4 text-white">
      {v ? (
        <video controls className="w-full rounded-lg" src={api.mediaUrl(v.video)} crossOrigin="anonymous">
          <track default kind="captions" src={api.mediaUrl(v.captions)} />
        </video>
      ) : (
        <div className="py-12 text-center">
          {busy ? (
            <>
              <Icon n="movie" className="!text-5xl text-primary-fixed animate-pulse" />
              <div className="font-bold mt-2">Your narrated lesson video is rendering…</div>
              <div className="text-sm text-slate-300 mt-1">{stage} · {t}s · read on, it will appear here</div>
              <div className="h-1.5 w-64 max-w-full mx-auto rounded-full bg-white/15 mt-4 overflow-hidden"><div className="h-full bg-primary-fixed transition-all duration-1000" style={{ width: `${Math.min(95, Math.round(100 * (1 - Math.exp(-t / 40))))}%` }} /></div>
            </>
          ) : <button className="btn" onClick={build}><Icon n="refresh" />Retry rendering video</button>}
        </div>
      )}
      {err && <div className="mt-3"><ErrorBox error={err} /></div>}
    </section>
  );
}

function Slides({ slides }) {
  const [i, setI] = useState(0);
  const s = slides[i];
  return (
    <section className="card !p-8 min-h-[30rem] flex flex-col">
      <div className="flex justify-between items-center mb-5">
        <h3 className="font-bold text-lg">Slides</h3>
        <div className="flex items-center gap-2 text-sm text-muted">
          <button className="chip" disabled={i === 0} onClick={() => setI(i - 1)}><Icon n="chevron_left" /></button>
          {i + 1} / {slides.length}
          <button className="chip" disabled={i === slides.length - 1} onClick={() => setI(i + 1)}><Icon n="chevron_right" /></button>
        </div>
      </div>
      <h4 className="font-bold text-2xl">{s.title}</h4>
      <ul className="list-disc pl-7 mt-4 space-y-2.5 text-lg leading-relaxed">{s.bullets.map((b) => <li key={b}>{b}</li>)}</ul>
      {s.detail && <div className="mt-5 rounded-lg bg-primary-fixed/40 border border-primary-fixed p-4 text-base leading-relaxed"><div className="eyebrow mb-1">In depth</div>{s.detail}</div>}
      {s.code && <pre className="mt-5 bg-navy text-slate-100 rounded-lg p-5 overflow-x-auto text-base leading-relaxed">{s.code}</pre>}
      <p className="mt-auto pt-6 text-base text-muted italic">“{s.narration}”</p>
    </section>
  );
}

function Quiz({ id, k, quiz, lang, onPassed }) {
  const [ans, setAns] = useState(Array(quiz.length).fill(null));
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const submit = async () => {
    setBusy(true); setErr(null);
    try { const r = await api.quiz(id, k, ans, lang); setRes(r); if (r.passed) onPassed(); } catch (e) { setErr(e.message); }
    setBusy(false);
  };
  return (
    <section className="card">
      <div className="eyebrow">Checkpoint challenge</div>
      <h3 className="font-bold text-lg mb-4">Quiz</h3>
      <div className="space-y-6">
        {quiz.map((q, qi) => (
          <div key={qi}>
            <p className="font-semibold mb-2">{qi + 1}. {q.question}</p>
            <div className="space-y-2">
              {q.options.map((o, oi) => {
                const r = res?.results[qi];
                const state = r ? (oi === r.correct_index ? "border-tertiary-container bg-tertiary-fixed/30" : ans[qi] === oi ? "border-error bg-error-container/50" : "border-border") : ans[qi] === oi ? "border-primary-container bg-primary-fixed" : "border-border hover:bg-subtle";
                return (
                  <label key={oi} className={`flex gap-3 rounded-lg border px-4 py-2.5 cursor-pointer ${state}`}>
                    <input type="radio" name={`q${qi}`} disabled={!!res} checked={ans[qi] === oi} onChange={() => setAns(ans.map((a, i) => (i === qi ? oi : a)))} />
                    <span className="text-sm">{o}</span>
                  </label>
                );
              })}
            </div>
            {res && <p className="text-sm text-muted mt-2">{res.results[qi].explanation}</p>}
          </div>
        ))}
      </div>
      <div className="mt-5"><ErrorBox error={err} /></div>
      {!res ? (
        <button className="btn mt-4" disabled={busy || ans.includes(null)} onClick={submit}>{busy ? "Grading…" : "Submit answers"}</button>
      ) : (
        <div className={`mt-5 rounded-lg p-4 ${res.passed ? "bg-tertiary-fixed/30" : "bg-amber/10"}`}>
          <div className="text-2xl font-extrabold">{Math.round(res.score * 100)}% — {res.passed ? "Passed 🎉" : "Needs reinforcement"}</div>
          {!res.passed && (
            <div className="mt-2 text-sm space-y-1">
              {res.revisit.length > 0 && <p>Revisit: {res.revisit.map((r) => <Link key={r} className="text-primary underline mr-2" to={`/courses/${id}/lessons/${r}`}>{r}</Link>)}</p>}
              {res.remedial && <p>New practice lesson added: <Link className="text-primary font-semibold underline" to={`/courses/${id}/lessons/${res.remedial.key}`}>{res.remedial.title}</Link></p>}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

function QuizGate({ children }) {
  const [open, setOpen] = useState(false);
  if (open) return children;
  return (
    <section className="card text-center py-8">
      <p className="text-muted mb-3">Finished reading and watching? Test yourself when you're ready.</p>
      <button className="btn" onClick={() => setOpen(true)}><Icon n="quiz" />I'm ready — take the quiz</button>
    </section>
  );
}

export default function Lesson() {
  const { id, k } = useParams();
  const [lang] = useLang();
  const nav = useNavigate();
  const { data: course } = useAsync(() => api.course(id), [id]);
  const { data: L, error, loading } = useAsync(() => api.lesson(id, k, lang), [id, k, lang]);
  const [marked, setMarked] = useState(false);
  if (error) return <ErrorBox error={error} />;
  if (loading || !course) return <Spinner label="Preparing lesson (first open generates it with AI)…" />;

  const keys = course.lesson_keys, i = keys.indexOf(k), idx = lessonIndex(course);
  const prev = keys[i - 1], next = keys[i + 1];
  const complete = async () => { await api.complete(id, k); setMarked(true); };
  return (
    <div className="grid xl:grid-cols-[minmax(0,1fr)_28rem] gap-6">
      <div className="space-y-6 min-w-0">
        <div>
          <Link to={`/courses/${id}`} className="eyebrow">{course.title}</Link>
          <h1 className="text-3xl font-extrabold tracking-tight mt-1">{L.title}</h1>
        </div>
        {L.slides && <Video id={id} k={k} lang={lang} />}
        {L.slides && <Slides slides={L.slides} />}
        <section className="card prose-lite"><Markdown>{L.explanation}</Markdown></section>
        {L.code_example && (
          <section className="rounded-xl bg-navy text-slate-100 p-4">
            <div className="text-xs text-slate-400 mb-2">{L.code_language}</div>
            <pre className="overflow-x-auto text-sm">{L.code_example}</pre>
          </section>
        )}
        {L.key_takeaways && (
          <section className="card">
            <h3 className="font-bold mb-2 flex items-center gap-2"><Icon n="lightbulb" className="text-amber" />Key takeaways</h3>
            <ul className="list-disc pl-6 space-y-1">{L.key_takeaways.map((t) => <li key={t}>{t}</li>)}</ul>
          </section>
        )}
        <QuizGate key={`${k}${lang}`}><Quiz id={id} k={k} quiz={L.quiz} lang={lang} onPassed={() => setMarked(true)} /></QuizGate>
        <div className="flex flex-wrap items-center gap-3 border-t border-border pt-4">
          {prev && <Link className="btn btn-ghost" to={`/courses/${id}/lessons/${prev}`}><Icon n="arrow_back" />{idx[prev].title}</Link>}
          <button className="btn btn-ghost mx-auto" disabled={marked || course.done.includes(k)} onClick={complete}>
            <Icon n="check_circle" />{marked || course.done.includes(k) ? "Completed" : "Mark as complete"}
          </button>
          {next && <button className="btn" onClick={() => nav(`/courses/${id}/lessons/${next}`)}>{idx[next].title}<Icon n="arrow_forward" /></button>}
        </div>
      </div>
      <aside className="xl:sticky xl:top-20 self-start"><TutorPanel id={id} k={k} lang={lang} /></aside>
    </div>
  );
}
