import os
import chromadb
import pymupdf as fitz
from chromadb import EmbeddingFunction
from .ai import client
from .log import get

log = get("rag")

EMB = "gemini-embedding-001"


class _Emb(EmbeddingFunction):
    def __init__(self): pass
    def __call__(self, input):
        r = client().models.embed_content(model=EMB, contents=list(input))
        return [e.values for e in r.embeddings]


def _col():
    path = os.path.join(os.path.dirname(__file__), "..", "data", "chroma")
    return chromadb.PersistentClient(path).get_or_create_collection("notes", embedding_function=_Emb())


def ingest_pdf(data: bytes, source: str, course_tag: str = "pending", chunk=1200):
    text = "".join(p.get_text() for p in fitz.open(stream=data, filetype="pdf"))
    chunks = [text[i:i + chunk] for i in range(0, len(text), chunk)]
    log.info("ingest %s tag=%s chars=%d chunks=%d", source, course_tag, len(text), len(chunks))
    if chunks:
        _col().add(ids=[f"{course_tag}:{source}:{i}" for i in range(len(chunks))], documents=chunks,
                   metadatas=[{"source": source, "tag": course_tag}] * len(chunks))
    return len(chunks)


def retrieve(query, k=4, tag=None):
    col = _col()
    if col.count() == 0:
        return []
    r = col.query(query_texts=[query], n_results=k, where={"tag": tag} if tag else None)
    log.info("retrieve tag=%s q=%.50r hits=%d", tag, query, len(r["documents"][0]))
    return [{"text": d, "source": m["source"]} for d, m in zip(r["documents"][0], r["metadatas"][0])]


def count(tag):
    return len(_col().get(where={"tag": tag}, include=[])["ids"])


def sample(tag, n=12):
    """Evenly spaced chunks across the student's notes (for outlining a whole course)."""
    r = _col().get(where={"tag": tag}, include=["documents", "metadatas"])
    order = sorted(range(len(r["ids"])), key=lambda i: (r["metadatas"][i]["source"], r["ids"][i].rsplit(":", 1)[0], int(r["ids"][i].rsplit(":", 1)[1])))
    step = max(1, len(order) / n)
    return [{"text": r["documents"][order[int(i * step)]], "source": r["metadatas"][order[int(i * step)]]["source"]} for i in range(min(n, len(order)))]
