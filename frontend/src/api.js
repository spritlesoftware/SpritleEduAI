// Thin client for the FastAPI backend (proxied at /api in dev).
const BASE = "/api";

async function req(path, opts) {
  const r = await fetch(BASE + path, opts);
  if (!r.ok) {
    const e = await r.json().catch(() => ({}));
    throw new Error(typeof e.detail === "string" ? e.detail : `${r.status} ${r.statusText}`);
  }
  return r.headers.get("content-type")?.includes("json") ? r.json() : r;
}
const json = (body) => ({ method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
const form = (obj) => { const f = new FormData(); Object.entries(obj).forEach(([k, v]) => v != null && f.append(k, v)); return { method: "POST", body: f }; };

export const api = {
  courses: () => req("/courses"),
  course: (id) => req(`/courses/${id}`),
  createCourse: (b) => req("/courses", json(b)),
  uploadNotes: (files, tag) => { const f = new FormData(); files.forEach((x) => f.append("files", x)); f.append("tag", tag); return req("/notes", { method: "POST", body: f }); },
  schedule: (id) => req(`/courses/${id}/schedule`),
  lesson: (id, k, lang) => req(`/courses/${id}/lessons/${k}?lang=${lang}`),
  quiz: (id, k, answers, lang) => req(`/courses/${id}/lessons/${k}/quiz`, json({ answers, lang })),
  complete: (id, k) => req(`/courses/${id}/lessons/${k}/complete`, { method: "POST" }),
  video: (id, k, lang) => req(`/courses/${id}/lessons/${k}/video?lang=${lang}`, { method: "POST" }),
  review: (id, lang) => req(`/courses/${id}/review?lang=${lang}`),
  tutor: (course_id, key, lang, text, audio) => req("/tutor", form({ course_id, key, lang, text, audio })),
  chat: (id, k) => req(`/courses/${id}/chat?key=${k}`),
  health: () => req("/health"),
  tts: async (text, lang) => URL.createObjectURL(await (await req("/tts", form({ text, lang }))).blob()),
  mediaUrl: (p) => BASE + p,
};
