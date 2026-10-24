import { useState } from "react";
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

function Builder() {
  const nav = useNavigate();
  const [f, setF] = useState({ goal: "", level: "beginner", duration_days: 30, daily_study_minutes: 60, format: "Mixed learning" });
  const [files, setFiles] = useState([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  async function submit() {
    setBusy(true); setErr(null);
    try {
      const body = { ...f };
      if (files.length) {
        body.notes_tag = `notes-${Date.now()}`;
        await api.uploadNotes(files, body.notes_tag);
      }
      const c = await api.createCourse(body);
      nav(`/courses/${c.id}`);
    } catch (e) { setErr(e.message); setBusy(false); }
  }

  return (
    <section className="card bg-gradient-to-br from-white to-surface-container-low border-primary-fixed p-8">
      <div className="eyebrow flex items-center gap-1"><Icon n="auto_awesome" />AI course builder</div>
      <h2 className="text-3xl font-bold tracking-tight mt-2">Create your own custom curriculum</h2>
      <p className="text-muted mt-1">Describe your target outcome. EduPilot generates modules, projects and an adaptive study plan.</p>
      <textarea value={f.goal} onChange={(e) => setF({ ...f, goal: e.target.value })} rows={3}
        placeholder="e.g., I want to learn Python from scratch and build a production-grade FastAPI microservice."
        className="mt-5 w-full rounded-lg border border-border p-4 focus:outline-none focus:ring-2 focus:ring-primary-container" />
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
        <label className="btn btn-ghost cursor-pointer"><Icon n="upload_file" />{files.length ? `${files.length} PDF(s)` : "Add PDF notes"}
          <input type="file" accept="application/pdf" multiple hidden onChange={(e) => setFiles([...e.target.files])} />
        </label>
        <button className="btn ml-auto" disabled={busy || f.goal.trim().length < 3} onClick={submit}>
          {busy ? <><Icon n="progress_activity" className="animate-spin" />Generating (≈30s)…</> : <>Generate course plan <Icon n="arrow_forward" /></>}
        </button>
      </div>
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
