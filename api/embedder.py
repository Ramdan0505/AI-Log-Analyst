from typing import List, Dict, Any
import os
import uuid

from sentence_transformers import SentenceTransformer
import chromadb

_model = SentenceTransformer("all-MiniLM-L6-v2")

CHROMA_HOST = os.getenv("CHROMA_HOST", "chroma")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
try:
    _client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
except Exception as e:
    print(f"[embedder] HttpClient failed ({e}); falling back to local PersistentClient at /data")
    _client = chromadb.PersistentClient(path="/data")


def _get_collection(case_id: str):
    return _client.get_or_create_collection(
        name=f"case_{case_id}",
        metadata={"hnsw:space": "cosine"},
    )


def embed_texts(case_id: str, texts: List[str], metadata_list: List[Dict[str, Any]]):
    if not texts:
        return

    coll = _get_collection(case_id)
    embeddings = _model.encode(texts).tolist()

    # FIX: unique ids to avoid collisions across multiple ingests
    ids = [f"{case_id}_{uuid.uuid4().hex}" for _ in texts]

    coll.add(ids=ids, documents=texts, metadatas=metadata_list, embeddings=embeddings)


def semantic_search(case_id: str, query: str, top_k: int = 5) -> Dict[str, Any]:
    coll = _get_collection(case_id)
    q_emb = _model.encode(query).tolist()
    res = coll.query(query_embeddings=[q_emb], n_results=top_k)

    hits = []
    for i in range(len(res["ids"][0])):
        hits.append(
            {
                "id": res["ids"][0][i],
                # FIX: call it what it is
                "distance": res["distances"][0][i],
                "text": res["documents"][0][i],
                "metadata": res["metadatas"][0][i],
            }
        )
    return {"results": hits}
