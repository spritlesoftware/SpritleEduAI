import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import { Bar, ErrorBox, Icon, Spinner, useAsync, useLang } from "../ui.jsx";

export default function Planner() {
  const p = useParams();
  const [lang] = useLang();
  const { data, error } = useAsync(async () => {
    const id = p.id ?? (await api.courses())[0]?.id;
    if (id == null) return { empty: true };
    const [course, sched, review] = await Promise.all([api.course(id), api.schedule(id), api.review(id, lang)]);
    return { id, course, sched, review };
  }, [p.id, lang]);
  if (error) return <ErrorBox error={error} />;
  if (!data) return <Spinner />;
  if (data.empty) return <p className="text-muted">No courses yet.</p>;
  const { id, course, sched, review } = data;
  const mastery = Object.entries(review.mastery);
  return (
    <div className="space-y-6">
      <div>
        <div className="eyebrow">Study planner & progress</div>
        <h1 className="text-3xl font-extrabold tracking-tight">{course.title}</h1>
        <div className="flex items-center gap-3 mt-3 max-w-md"><div className="flex-1"><Bar value={course.progress} /></div><b>{Math.round(course.progress * 100)}%</b></div>
        {sched.over_goal && <p className="mt-3 text-sm text-amber font-semibold">⚠ Remaining lessons overrun your {course.duration_days}-day goal (review lessons were added).</p>}
      </div>
      <div className="grid lg:grid-cols-3 gap-6">
        <section className="lg:col-span-2 space-y-3">
          <h2 className="font-bold text-lg">Schedule</h2>
          {!sched.days.length && <p className="text-muted">Everything is complete 🎉</p>}
          {sched.days.map((d) => (
            <div key={d.day} className="card p-4">
              <div className="text-xs font-bold uppercase tracking-wider text-muted mb-2">Day {d.day}</div>
              {d.items.map(([k, title, mins]) => (
                <Link key={k} to={`/courses/${id}/lessons/${k}`} className="flex justify-between rounded-lg px-3 py-2 hover:bg-subtle">
                  <span className="flex items-center gap-2"><Icon n="play_circle" className="text-primary-container" />{title}</span><span className="text-sm text-muted">{mins} min</span>
                </Link>
              ))}
            </div>
          ))}
        </section>
        <aside className="space-y-4">
          <section className="card">
            <h3 className="font-bold mb-3">Concept mastery</h3>
            {!mastery.length && <p className="text-sm text-muted">Take a quiz to see mastery.</p>}
            <div className="space-y-3">{mastery.map(([c, v]) => (
              <div key={c}><div className="flex justify-between text-sm"><span>{c}</span><b className={v < 0.7 ? "text-error" : "text-tertiary"}>{Math.round(v * 100)}%</b></div><Bar value={v} /></div>
            ))}</div>
          </section>
          <section className="card">
            <h3 className="font-bold mb-2">Quiz attempts</h3>
            {review.attempts.map((a, i) => <div key={i} className="flex justify-between text-sm py-1"><span>{a.key}</span><b>{Math.round(a.score * 100)}%</b></div>)}
            {!review.attempts.length && <p className="text-sm text-muted">None yet.</p>}
          </section>
          {review.flashcards.length > 0 && <Flashcards cards={review.flashcards} />}
        </aside>
      </div>
    </div>
  );
}

function Flashcards({ cards }) {
  return (
    <section className="card">
      <h3 className="font-bold mb-2">Flashcards ({cards.length})</h3>
      <div className="space-y-2 max-h-72 overflow-y-auto">
        {cards.map((c, i) => <details key={i} className="rounded-lg border border-border px-3 py-2 text-sm"><summary className="cursor-pointer font-medium">{c.front}</summary><p className="mt-1 text-muted">{c.back}</p></details>)}
      </div>
    </section>
  );
}
