import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import { Bar, ErrorBox, Icon, Spinner, lessonIndex, useAsync } from "../ui.jsx";

export default function Course() {
  const { id } = useParams();
  const { data: c, error } = useAsync(() => api.course(id), [id]);
  if (error) return <ErrorBox error={error} />;
  if (!c) return <Spinner />;
  const done = new Set(c.done);
  const idx = lessonIndex(c);
  const next = c.lesson_keys.find((k) => !done.has(k));
  const row = (k) => (
    <Link key={k} to={`/courses/${id}/lessons/${k}`} className="flex items-center gap-3 rounded-lg px-3 py-2.5 hover:bg-subtle">
      <Icon n={done.has(k) ? "check_circle" : "radio_button_unchecked"} className={done.has(k) ? "text-tertiary-container" : "text-outline-variant"} />
      <span className="flex-1">{idx[k].title}</span>
      {idx[k].remedial && <span className="text-xs font-bold text-amber">REVIEW</span>}
      <span className="text-xs text-muted">{idx[k].estimated_minutes} min</span>
    </Link>
  );
  const remAfter = (k) => c.lesson_keys.filter((x) => idx[x].remedial && idx[x].after === k);
  return (
    <div className="space-y-6">
      <div>
        <div className="eyebrow">{c.level} · {c.duration_days} days · {c.daily_study_minutes} min/day</div>
        <h1 className="text-3xl font-extrabold tracking-tight mt-1">{c.title}</h1>
        <p className="text-muted mt-2 max-w-3xl">{c.description}</p>
        <div className="flex items-center gap-4 mt-4 max-w-md">
          <div className="flex-1"><Bar value={c.progress} /></div><span className="text-sm font-semibold">{Math.round(c.progress * 100)}%</span>
        </div>
        <div className="flex gap-3 mt-4">
          {next && <Link className="btn" to={`/courses/${id}/lessons/${next}`}>Resume lesson <Icon n="arrow_forward" /></Link>}
          <Link className="btn btn-ghost" to={`/planner/${id}`}><Icon n="calendar_month" />Study plan</Link>
        </div>
      </div>
      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          {c.modules.map((m, mi) => (
            <section key={mi} className="card">
              <div className="eyebrow">Module {mi + 1}</div>
              <h3 className="font-bold text-lg">{m.title}</h3>
              <div className="mt-2">{m.lessons.flatMap((_, li) => [`m${mi}l${li}`, ...remAfter(`m${mi}l${li}`)]).map(row)}</div>
              <div className="mt-3 rounded-lg bg-surface-container-low p-3 text-sm"><b>Project:</b> {m.project.title} — <span className="text-muted">{m.project.description}</span></div>
            </section>
          ))}
        </div>
        <aside className="space-y-4">
          <section className="card"><h3 className="font-bold mb-2">Learning outcomes</h3><ul className="list-disc pl-5 text-sm space-y-1">{c.learning_outcomes.map((o) => <li key={o}>{o}</li>)}</ul></section>
          <section className="card"><h3 className="font-bold mb-2">Prerequisites</h3><ul className="list-disc pl-5 text-sm space-y-1">{c.prerequisites.map((o) => <li key={o}>{o}</li>)}</ul></section>
          <section className="card bg-navy text-white"><div className="eyebrow !text-cyan">Capstone</div><h3 className="font-bold">{c.capstone.title}</h3><p className="text-sm text-slate-300 mt-1">{c.capstone.description}</p></section>
        </aside>
      </div>
    </div>
  );
}
