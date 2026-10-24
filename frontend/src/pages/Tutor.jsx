import { useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api.js";
import { ErrorBox, Icon, Spinner, lessonIndex, useAsync, useLang } from "../ui.jsx";

export function TutorPanel({ id, k, lang }) {
  const [msgs, setMsgs] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [rec, setRec] = useState(null);
  const [err, setErr] = useState(null);

  async function ask(t, audio, label) {
    setMsgs((m) => [...m, { me: true, t: label ?? t }]); setBusy(true); setErr(null);
    try {
      const { reply } = await api.tutor(id, k, lang, t, audio);
      setMsgs((m) => [...m, { t: reply }]);
    } catch (e) { setErr(e.message); }
    setBusy(false);
  }
  const send = () => { const t = text.trim(); if (t) { setText(""); ask(t); } };
  const speak = async (t) => new Audio(await api.tts(t, lang)).play().catch((e) => setErr(e.message));

  async function toggleMic() {
    if (rec) { rec.stop(); return; }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream), chunks = [];
      mr.ondataavailable = (e) => chunks.push(e.data);
      mr.onstop = () => { stream.getTracks().forEach((t) => t.stop()); setRec(null); ask(null, new File(chunks, "q.webm", { type: mr.mimeType }), "🎤 (voice question)"); };
      mr.start(); setRec(mr);
    } catch (e) { setErr("Microphone unavailable: " + e.message); }
  }

  return (
    <section className="card p-4 flex flex-col h-[32rem]">
      <div className="flex items-center gap-2 font-bold"><span className={`h-2 w-2 rounded-full ${rec ? "bg-error animate-pulse" : "bg-tertiary-container"}`} />AI Voice Tutor
        <span className="ml-auto eyebrow">{rec ? "Listening…" : "Online"}</span></div>
      <div className="flex-1 overflow-y-auto py-3 space-y-3 text-sm">
        {!msgs.length && <p className="text-muted">Ask anything about this lesson — type or use the mic.</p>}
        {msgs.map((m, i) => (
          <div key={i} className={m.me ? "flex justify-end" : ""}>
            <div className={`max-w-[85%] rounded-xl px-3 py-2 ${m.me ? "bg-primary-container text-white" : "bg-surface-container-low"}`}>
              {m.t}
              {!m.me && <button className="ml-2 text-primary" onClick={() => speak(m.t)} title="Read aloud"><Icon n="volume_up" className="!text-base" /></button>}
            </div>
          </div>
        ))}
        {busy && <Spinner label="Thinking…" />}
      </div>
      <ErrorBox error={err} />
      <div className="flex gap-2 mt-2">
        <button className={`btn ${rec ? "!bg-error" : "btn-ghost"}`} onClick={toggleMic} title="Record a question"><Icon n={rec ? "stop" : "mic"} /></button>
        <input value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} placeholder="Ask the AI tutor…"
          className="flex-1 min-w-0 rounded-lg border border-border px-3 focus:outline-none focus:ring-2 focus:ring-primary-container" />
        <button className="btn" onClick={send} disabled={busy}><Icon n="arrow_upward" /></button>
      </div>
    </section>
  );
}

// Standalone tutor page: picks the latest course / first lesson unless given in the URL.
export default function Tutor() {
  const p = useParams();
  const [lang] = useLang();
  const { data, error, loading } = useAsync(async () => {
    const id = p.id ?? (await api.courses())[0]?.id;
    if (id == null) return null;
    const c = await api.course(id);
    return c;
  }, [p.id]);
  if (error) return <ErrorBox error={error} />;
  if (loading) return <Spinner />;
  if (!data) return <p className="text-muted">Create a course first, then come back to talk to your tutor.</p>;
  const idx = lessonIndex(data), k = p.k ?? data.lesson_keys.find((x) => !data.done.includes(x)) ?? data.lesson_keys[0];
  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <div><div className="eyebrow">Voice tutor</div><h1 className="text-2xl font-bold">{idx[k].title}</h1>
        <Link to={`/courses/${data.id}`} className="text-sm text-primary">{data.title}</Link></div>
      <select value={k} onChange={(e) => (location.href = `/tutor/${data.id}/${e.target.value}`)} className="w-full rounded-lg border border-border p-2 text-sm">
        {data.lesson_keys.map((x) => <option key={x} value={x}>{idx[x].title}</option>)}
      </select>
      <TutorPanel key={k} id={data.id} k={k} lang={lang} />
    </div>
  );
}
