import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import Markdown from "react-markdown";
import { api } from "../api.js";
import { ErrorBox, Icon, Spinner, lessonIndex, useAsync, useLang } from "../ui.jsx";
import { TutorPanel } from "./Tutor.jsx";

function Video({ id, k, lang }) {
  const [v, setV] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const build = async () => {
    setBusy(true); setErr(null);
    try { setV(await api.video(id, k, lang)); } catch (e) { setErr(e.message); }
    setBusy(false);
  };
  return (
    <section className="rounded-xl bg-navy p-4 text-white">
      {v ? (
        <video controls className="w-full rounded-lg" src={api.mediaUrl(v.video)} crossOrigin="anonymous">
          <track default kind="captions" src={api.mediaUrl(v.captions)} />
        </video>
      ) : (
        <div className="py-10 text-center">
          <button className="btn" onClick={build} disabled={busy}>
            {busy ? <><Icon n="progress_activity" className="animate-spin" />Rendering narrated video (~1 min)…</> : <><Icon n="play_arrow" />Generate lesson video</>}
          </button>
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
    <section className="card">
      <div className="flex justify-between items-center mb-3">
        <h3 className="font-bold">Slides</h3>
        <div className="flex items-center gap-2 text-sm text-muted">
          <button className="chip" disabled={i === 0} onClick={() => setI(i - 1)}><Icon n="chevron_left" /></button>
          {i + 1} / {slides.length}
          <button className="chip" disabled={i === slides.length - 1} onClick={() => setI(i + 1)}><Icon n="chevron_right" /></button>
        </div>
      </div>
      <h4 className="font-semibold text-lg">{s.title}</h4>
      <ul className="list-disc pl-6 mt-2 space-y-1">{s.bullets.map((b) => <li key={b}>{b}</li>)}</ul>
      {s.code && <pre className="mt-3 bg-navy text-slate-100 rounded-lg p-4 overflow-x-auto text-sm">{s.code}</pre>}
      <p className="mt-3 text-sm text-muted italic">“{s.narration}”</p>
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
    <div className="grid xl:grid-cols-3 gap-6">
      <div className="xl:col-span-2 space-y-6 min-w-0">
        <div>
          <Link to={`/courses/${id}`} className="eyebrow">{course.title}</Link>
          <h1 className="text-3xl font-extrabold tracking-tight mt-1">{L.title}</h1>
        </div>
        {L.slides && <Video id={id} k={k} lang={lang} />}
        <section className="card prose-lite"><Markdown>{L.explanation}</Markdown></section>
        {L.key_takeaways && (
          <section className="card">
            <h3 className="font-bold mb-2 flex items-center gap-2"><Icon n="lightbulb" className="text-amber" />Key takeaways</h3>
            <ul className="list-disc pl-6 space-y-1">{L.key_takeaways.map((t) => <li key={t}>{t}</li>)}</ul>
          </section>
        )}
        {L.code_example && (
          <section className="rounded-xl bg-navy text-slate-100 p-4">
            <div className="text-xs text-slate-400 mb-2">{L.code_language}</div>
            <pre className="overflow-x-auto text-sm">{L.code_example}</pre>
          </section>
        )}
        {L.slides && <Slides slides={L.slides} />}
        <Quiz key={`${k}${lang}`} id={id} k={k} quiz={L.quiz} lang={lang} onPassed={() => setMarked(true)} />
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
