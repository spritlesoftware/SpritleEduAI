import { useEffect, useState, createContext, useContext } from "react";

export const Lang = createContext(["en", () => {}]);
export const useLang = () => useContext(Lang);

export const Icon = ({ n, className = "" }) => <span className={`ms ${className}`}>{n}</span>;

// Runs fn on mount/deps change; returns {data, error, loading, reload}.
export function useAsync(fn, deps = []) {
  const [s, set] = useState({ data: null, error: null, loading: true });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let live = true;
    set((p) => ({ ...p, loading: true, error: null }));
    fn().then((data) => live && set({ data, error: null, loading: false }), (error) => live && set({ data: null, error: error.message, loading: false }));
    return () => { live = false; };
  }, [...deps, tick]);
  return { ...s, reload: () => setTick((t) => t + 1) };
}

export const Spinner = ({ label = "Loading…" }) => (
  <div className="flex items-center gap-2 text-muted p-6"><Icon n="progress_activity" className="animate-spin" />{label}</div>
);
export const ErrorBox = ({ error }) => error && (
  <div className="rounded-lg bg-error-container text-error px-4 py-3 text-sm">{error}</div>
);
export const Bar = ({ value }) => (
  <div className="h-2 rounded-full bg-surface-container overflow-hidden">
    <div className="h-full bg-primary-container" style={{ width: `${Math.round(value * 100)}%` }} />
  </div>
);

// Lesson title lookup incl. remedial lessons: key -> {title, estimated_minutes}
export function lessonIndex(course) {
  const m = {};
  course.modules.forEach((mod, mi) => mod.lessons.forEach((l, li) => (m[`m${mi}l${li}`] = l)));
  (course.remedial || []).forEach((r) => (m[r.key] = r));
  return m;
}
