import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { Bar, ErrorBox, Icon, Spinner, useAsync } from "../ui.jsx";

const OPTS = {
  level: [["beginner", "Beginner"], ["intermediate", "Intermediate"], ["advanced", "Advanced"]],
  duration_days: [[7, "7d"], [30, "30d"], [60, "60d"], [90, "90d"]],
  daily_study_minutes: [[30, "30 min"], [60, "1 hour"], [120, "2 hours"]],
  format: [["Video + Lab", "Video + Lab"], ["Mixed learning", "Mixed"], ["Reading", "Reading"]],
};
const LABEL = { level: "Current level", duration_days: "Course duration", daily_study_minutes: "Daily study time", format: "Learning format" };

const STEPS = [
  ["Understanding your goal and level", "Reading what you want to achieve"],
  ["Designing modules and lessons", "Ordering topics so each one builds on the last"],
  ["Adding projects and a capstone", "Hands-on work for every module"],
  ["Building your adaptive study plan", "Fitting lessons into your daily study time"],
  ["Saving your course", "Almost ready"],
];

function Generating({ fromNotes, uploading }) {
  const steps = fromNotes ? [["Uploading and indexing your PDFs", "Splitting notes into searchable passages"], ...STEPS] : STEPS;
  const [t, setT] = useState(0);
  useEffect(() => { const i = setInterval(() => setT((x) => x + 1), 1000); return () => clearInterval(i); }, []);
  const base = fromNotes ? (uploading ? 0 : 1) : 0;
  const active = Math.min(steps.length - 1, base + (uploading ? 0 : Math.floor(t / 7)));
  const pct = Math.min(95, Math.round(100 * (1 - Math.exp(-t / 22))));
  return (
    <div className="mt-6 rounded-xl border border-primary-fixed bg-white p-5">
      <div className="flex items-center justify-between text-sm">
        <span className="font-bold flex items-center gap-2"><Icon n="progress_activity" className="animate-spin text-primary-container" />Building your course…</span>
        <span className="text-muted">{t}s · usually under 40s</span>
      </div>
      <div className="h-2 rounded-full bg-primary-fixed mt-3 overflow-hidden"><div className="h-full bg-primary-container transition-all duration-1000" style={{ width: `${pct}%` }} /></div>
      <ul className="mt-4 space-y-2.5">
        {steps.map(([title, sub], i) => (
          <li key={title} className={`flex items-start gap-3 ${i > active ? "opacity-40" : ""}`}>
            <span className="mt-0.5">{i < active ? <Icon n="check_circle" className="text-tertiary-container !text-xl" /> : i === active ? <Icon n="progress_activity" className="animate-spin text-primary-container !text-xl" /> : <Icon n="radio_button_unchecked" className="!text-xl" />}</span>
            <div><div className="text-sm font-semibold">{title}</div>{i === active && <div className="text-xs text-muted">{sub}</div>}</div>
          </li>
        ))}
      </ul>
      <p className="text-xs text-muted mt-4">Each lesson (slides, quiz, flashcards) is generated the first time you open it, so the course appears quickly.</p>
    </div>
  );
}

function Builder() {
  const nav = useNavigate();
  const [f, setF] = useState({ goal: "", level: "beginner", duration_days: 30, daily_study_minutes: 60, format: "Mixed learning" });
  const [files, setFiles] = useState([]);
  const [source, setSource] = useState("topic");
  const fromNotes = source === "notes";
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [err, setErr] = useState(null);

  async function submit() {
    setBusy(true); setErr(null);
    try {
      const body = { ...f, source };
      if (fromNotes) {
        body.notes_tag = `notes-${Date.now()}`;
        setUploading(true);
        await api.uploadNotes(files, body.notes_tag);
        setUploading(false);
      }
      const c = await api.createCourse(body);
      nav(`/courses/${c.id}`);
    } catch (e) { setErr(e.message); setBusy(false); setUploading(false); }
  }

  return (
    <section className="card bg-gradient-to-br from-white to-surface-container-low border-primary-fixed p-8">
      <div className="eyebrow flex items-center gap-1"><Icon n="auto_awesome" />AI course builder</div>
      <h2 className="text-3xl font-bold tracking-tight mt-2">Create your own custom curriculum</h2>
      <p className="text-muted mt-1">Describe your target outcome. SpritleEduAI generates modules, projects and an adaptive study plan.</p>
      <div className="flex gap-2 mt-5">
        {[["topic", "auto_awesome", "Learn a topic"], ["notes", "description", "Learn from my notes"]].map(([v, ic, l]) => (
          <button key={v} onClick={() => setSource(v)} className={`chip flex items-center gap-1 ${source === v ? "chip-on" : ""}`}><Icon n={ic} className="!text-base" />{l}</button>
        ))}
      </div>
      <p className="text-xs text-muted mt-2">{fromNotes ? "The course is built only from the PDFs you upload — lessons cite them." : "AI designs the course from your goal."}</p>
      <textarea value={f.goal} onChange={(e) => setF({ ...f, goal: e.target.value })} rows={3}
        placeholder={fromNotes ? "Optional: what should you focus on in these notes?" : "e.g., I want to learn Python from scratch and build a production-grade FastAPI microservice."}
        className="mt-3 w-full rounded-lg border border-border p-4 focus:outline-none focus:ring-2 focus:ring-primary-container" />
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5 mt-5">
        {Object.entries(OPTS).map(([k, opts]) => (
          <div key={k}>
            <div className="text-xs font-bold uppercase tracking-wider text-muted mb-2">{LABEL[k]}</div>
            <div className="flex flex-wrap gap-1.5">
              {opts.map(([v, l]) => <button key={v} onClick={() => setF({ ...f, [k]: v })} className={`chip ${f[k] === v ? "chip-on" : ""}`}>{l}</button>)}
            </div>
          </div>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-4 mt-6">
        {fromNotes && <label className="btn btn-ghost cursor-pointer"><Icon n="upload_file" />{files.length ? `${files.length} PDF(s)` : "Upload PDF notes"}
          <input type="file" accept="application/pdf" multiple hidden onChange={(e) => setFiles([...e.target.files])} />
        </label>}
        <button className="btn ml-auto" disabled={busy || (fromNotes ? !files.length : f.goal.trim().length < 3)} onClick={submit}>
          {busy ? <><Icon n="progress_activity" className="animate-spin" />Generating…</> : <>Generate course plan <Icon n="arrow_forward" /></>}
        </button>
      </div>
      {busy && <Generating fromNotes={fromNotes} uploading={uploading} />}
      <div className="mt-4"><ErrorBox error={err} /></div>
    </section>
  );
}

function CourseCard({ id }) {
  const { data: c } = useAsync(() => api.course(id), [id]);
  if (!c) return <div className="card h-28" />;
  return (
    <Link to={`/courses/${id}`} className="card hover:border-primary-container transition block">
      <div className="font-bold">{c.title}</div>
      <div className="text-sm text-muted mb-3">{c.level} · {c.duration_days} days · {c.modules.length} modules</div>
      <Bar value={c.progress} />
      <div className="text-xs text-muted mt-1">{Math.round(c.progress * 100)}% complete</div>
    </Link>
  );
}

function Gaps({ id }) {
  const { data } = useAsync(() => api.review(id, "en"), [id]);
  const weak = data?.weak_concepts ?? [];
  if (!weak.length) return null;
  return (
    <section className="card bg-amber/10 border-amber/30">
      <h3 className="font-bold flex items-center gap-2"><Icon n="warning" className="text-amber" />Knowledge gaps identified</h3>
      <ul className="mt-3 space-y-2">
        {weak.map((w) => (
          <li key={w} className="flex justify-between bg-white rounded-lg px-3 py-2 text-sm">
            <span>{w}</span><span className="font-bold text-error">{Math.round(data.mastery[w] * 100)}% mastery</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export default function Home({ listOnly }) {
  const { data: courses, error, loading } = useAsync(() => api.courses(), []);
  const latest = courses?.[0];
  return (
    <div className="space-y-8">
      {!listOnly && <Builder />}
      <ErrorBox error={error} />
      {loading && <Spinner />}
      {courses && (
        <div className={listOnly ? "" : "grid lg:grid-cols-3 gap-6"}>
          <section className={listOnly ? "" : "lg:col-span-2"}>
            <h2 className="text-xl font-bold mb-4">{listOnly ? "My courses" : "Continue learning"}</h2>
            {!courses.length && <p className="text-muted">No courses yet — generate your first one above.</p>}
            <div className="grid sm:grid-cols-2 gap-4">{courses.map((c) => <CourseCard key={c.id} id={c.id} />)}</div>
          </section>
          {!listOnly && latest && <Gaps id={latest.id} />}
        </div>
      )}
    </div>
  );
}
