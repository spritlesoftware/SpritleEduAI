import json, os, sqlite3, time

PATH = os.environ.get("EDUPILOT_DB", os.path.join(os.path.dirname(__file__), "..", "data", "edupilot.db"))


def conn():
    c = sqlite3.connect(PATH)
    c.row_factory = sqlite3.Row
    c.executescript("""
    CREATE TABLE IF NOT EXISTS courses(id INTEGER PRIMARY KEY, data TEXT, created REAL);
    CREATE TABLE IF NOT EXISTS done(course_id INT, key TEXT, ts REAL, PRIMARY KEY(course_id,key));
    CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY, course_id INT, key TEXT, score REAL, missed TEXT, ts REAL);
    CREATE TABLE IF NOT EXISTS concepts(course_id INT, concept TEXT, right INT DEFAULT 0, total INT DEFAULT 0, PRIMARY KEY(course_id,concept));
    CREATE TABLE IF NOT EXISTS kv(k TEXT PRIMARY KEY, v TEXT);
    """)
    return c


def save_course(course, cid=None):
    with conn() as c:
        if cid is None:
            cid = c.execute("INSERT INTO courses(data,created) VALUES('{}',?)", (time.time(),)).lastrowid
        course["id"] = cid
        c.execute("UPDATE courses SET data=? WHERE id=?", (json.dumps(course), cid))
    return cid


def get_course(cid):
    r = conn().execute("SELECT data FROM courses WHERE id=?", (cid,)).fetchone()
    return json.loads(r["data"]) if r else None


def list_courses():
    return [(r["id"], json.loads(r["data"]).get("title", "?")) for r in conn().execute("SELECT id,data FROM courses ORDER BY id DESC")]


def mark_done(cid, key):
    with conn() as c:
        c.execute("INSERT OR IGNORE INTO done VALUES(?,?,?)", (cid, key, time.time()))


def done_keys(cid):
    return {r["key"] for r in conn().execute("SELECT key FROM done WHERE course_id=?", (cid,))}


def record_attempt(cid, key, score, missed, concept_results):
    """concept_results: list of (concept, correct_bool)."""
    with conn() as c:
        c.execute("INSERT INTO attempts(course_id,key,score,missed,ts) VALUES(?,?,?,?,?)",
                  (cid, key, score, json.dumps(missed), time.time()))
        for concept, ok in concept_results:
            c.execute("INSERT OR IGNORE INTO concepts(course_id,concept) VALUES(?,?)", (cid, concept))
            c.execute("UPDATE concepts SET total=total+1, right=right+? WHERE course_id=? AND concept=?", (int(ok), cid, concept))


def attempts(cid):
    return [dict(r) for r in conn().execute("SELECT * FROM attempts WHERE course_id=? ORDER BY id", (cid,))]


def mastery(cid):
    return {r["concept"]: r["right"] / r["total"] for r in conn().execute("SELECT * FROM concepts WHERE course_id=?", (cid,)) if r["total"]}


def kv_set(k, v):
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO kv VALUES(?,?)", (k, json.dumps(v)))


def kv_get(k, default=None):
    r = conn().execute("SELECT v FROM kv WHERE k=?", (k,)).fetchone()
    return json.loads(r["v"]) if r else default
