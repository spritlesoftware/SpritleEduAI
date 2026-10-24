"""Pure logic: lesson keys, study schedule, adaptive recommendations. No I/O."""
PASS = 0.7


def key(m, l):
    return f"m{m}l{l}"


def lessons(course):
    """Ordered list of (key, lesson) incl. remedial lessons inserted after the lesson that triggered them."""
    out = []
    rem = course.get("remedial", [])
    for m, mod in enumerate(course["modules"]):
        for l, les in enumerate(mod["lessons"]):
            k = key(m, l)
            out.append((k, les))
            out += [(r["key"], r) for r in rem if r["after"] == k]
    return out


def schedule(course, done, today=1):
    """Greedy-pack remaining lessons into days of daily_study_minutes, starting at day `today`.
    If the plan overruns duration_days, lessons are still scheduled (days > duration flagged by caller)."""
    cap = course["daily_study_minutes"]
    days, cur, used = [], [], 0
    for k, les in lessons(course):
        if k in done:
            continue
        mins = les.get("estimated_minutes", 20)
        if cur and used + mins > cap:
            days.append(cur); cur, used = [], 0
        cur.append((k, les["title"], mins)); used += mins
    if cur:
        days.append(cur)
    return [{"day": today + i, "items": d} for i, d in enumerate(days)]


def recommend(course, key_taken, question_results):
    """question_results: [{concept, correct, review}] -> failing quiz returns review lesson keys (earlier lessons) to revisit."""
    score = sum(q["correct"] for q in question_results) / max(1, len(question_results))
    if score >= PASS:
        return score, []
    valid = {k for k, _ in lessons(course)}
    revisit = []
    for q in question_results:
        r = q.get("review")
        if not q["correct"] and r in valid and r not in revisit:
            revisit.append(r)
    return score, revisit or [key_taken]


def add_remedial(course, after_key, title, minutes=15):
    rem = course.setdefault("remedial", [])
    k = f"r{len(rem)}"
    rem.append({"key": k, "after": after_key, "title": title, "estimated_minutes": minutes,
                "content_type": "practice", "remedial": True})
    return k


if __name__ == "__main__":
    c = {"daily_study_minutes": 60, "modules": [{"lessons": [{"title": "a", "estimated_minutes": 30}, {"title": "b", "estimated_minutes": 30}, {"title": "c", "estimated_minutes": 30}]}]}
    assert [len(d["items"]) for d in schedule(c, set())] == [2, 1]
    assert [len(d["items"]) for d in schedule(c, {"m0l0"})] == [2]
    s, rv = recommend(c, "m0l2", [{"concept": "x", "correct": False, "review": "m0l0"}, {"concept": "y", "correct": True}])
    assert s == 0.5 and rv == ["m0l0"]
    assert recommend(c, "m0l2", [{"concept": "x", "correct": True}])[1] == []
    k = add_remedial(c, "m0l2", "Review x")
    assert lessons(c)[-1][0] == k and schedule(c, set())[-1]["items"][-1][1] == "Review x"
    print("ok")
