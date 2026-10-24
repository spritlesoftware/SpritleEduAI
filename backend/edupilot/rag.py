import os
import chromadb
import fitz
from chromadb import EmbeddingFunction
from .ai import client

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
    if chunks:
        _col().add(ids=[f"{course_tag}:{source}:{i}" for i in range(len(chunks))], documents=chunks,
                   metadatas=[{"source": source, "tag": course_tag}] * len(chunks))
    return len(chunks)


def retrieve(query, k=4, tag=None):
    col = _col()
    if col.count() == 0:
        return []
    r = col.query(query_texts=[query], n_results=k, where={"tag": tag} if tag else None)
    return [{"text": d, "source": m["source"]} for d, m in zip(r["documents"][0], r["metadatas"][0])]
