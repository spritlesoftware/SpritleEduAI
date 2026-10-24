import { useState } from "react";
import logo from "./assets/spritle-logo.svg";
import icon from "./assets/spritle-icon.svg";
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
];

export default function App() {
  const { data: health } = useAsync(() => api.health(), []);
  return (
    <Lang.Provider value={["en", () => {}]}>
      <div className="min-h-screen md:flex">
        <aside className="hidden md:flex md:w-60 shrink-0 flex-col border-r border-border bg-white p-4 gap-1 sticky top-0 h-screen">
          <div className="px-3 py-4 mb-2">
            <img src={logo} alt="Spritle" className="h-8 mb-3" />
            <div className="text-xl font-extrabold tracking-tight">SpritleEduAI</div>
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
            <span className="md:hidden flex items-center gap-2 font-extrabold"><img src={icon} alt="Spritle" className="h-6" />SpritleEduAI</span>
            <nav className="md:hidden flex gap-3">{NAV.map(([to, , icon]) => <NavLink key={to} to={to} end={to === "/"} className={({ isActive }) => isActive ? "text-primary-container" : "text-muted"}><Icon n={icon} /></NavLink>)}</nav>
          </header>
          <main className="max-w-[1600px] mx-auto p-4 md:p-8">
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
