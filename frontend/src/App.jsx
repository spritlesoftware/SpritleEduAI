import { useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { Icon, Lang, useAsync } from "./ui.jsx";
import { api } from "./api.js";
import Home from "./pages/Home.jsx";
import Course from "./pages/Course.jsx";
import Lesson from "./pages/Lesson.jsx";
import Planner from "./pages/Planner.jsx";
import Tutor from "./pages/Tutor.jsx";

const NAV = [
  ["/", "Home", "home"],
  ["/courses", "My Courses", "menu_book"],
  ["/planner", "Study Planner", "calendar_month"],
  ["/tutor", "Voice Tutor", "graphic_eq"],
];

export default function App() {
  const lang = useState(localStorage.lang || "en");
  const setLang = (l) => { localStorage.lang = l; lang[1](l); };
  const { data: health } = useAsync(() => api.health(), []);
  return (
    <Lang.Provider value={[lang[0], setLang]}>
      <div className="min-h-screen md:flex">
        <aside className="hidden md:flex md:w-60 shrink-0 flex-col border-r border-border bg-white p-4 gap-1 sticky top-0 h-screen">
          <div className="px-3 py-4 mb-2">
            <div className="text-xl font-extrabold tracking-tight">EduPilot</div>
            <div className="eyebrow">AI Learning OS</div>
          </div>
          {NAV.map(([to, label, icon]) => (
            <NavLink key={to} to={to} end={to === "/"}
              className={({ isActive }) => `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium ${isActive ? "bg-primary-container text-white" : "text-muted hover:bg-subtle"}`}>
              <Icon n={icon} />{label}
            </NavLink>
          ))}
          {health && !health.gemini_key && <p className="mt-auto text-xs text-amber px-3">GEMINI_API_KEY not set on server</p>}
        </aside>
        <div className="flex-1 min-w-0">
          <header className="flex items-center justify-between gap-4 border-b border-border bg-white px-4 md:px-8 h-14 sticky top-0 z-10">
            <span className="md:hidden font-extrabold">EduPilot</span>
            <nav className="md:hidden flex gap-3">{NAV.map(([to, , icon]) => <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => isActive ? "text-primary-container" : "text-muted"}><Icon n={icon} /></NavLink>)}</nav>
            <div className="ml-auto flex rounded-full border border-border overflow-hidden text-sm font-semibold">
              {[["en", "English"], ["ta", "தமிழ்"]].map(([c, l]) => (
                <button key={c} onClick={() => setLang(c)} className={`px-3 py-1 ${lang[0] === c ? "bg-primary-container text-white" : "text-muted"}`}>{l}</button>
              ))}
            </div>
          </header>
          <main className="max-w-6xl mx-auto p-4 md:p-8">
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/courses" element={<Home listOnly />} />
              <Route path="/courses/:id" element={<Course />} />
              <Route path="/courses/:id/lessons/:k" element={<Lesson />} />
              <Route path="/planner/:id?" element={<Planner />} />
              <Route path="/tutor/:id?/:k?" element={<Tutor />} />
            </Routes>
          </main>
        </div>
      </div>
    </Lang.Provider>
  );
}
