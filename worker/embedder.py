from typing import List, Dict, Any
import os

from sentence_transformers import SentenceTransformer
import chromadb

# Simple global singleton – fine for this use
_model = SentenceTransformer("all-MiniLM-L6-v2")

CHROMA_HOST = os.getenv("CHROMA_HOST", "chroma")   # docker-compose service name
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
    """Index a batch of texts for a single case."""
    if not texts:
        return

    coll = _get_collection(case_id)
    embeddings = _model.encode(texts).tolist()
    ids = [f"{case_id}_{i}" for i in range(len(texts))]

    coll.add(
        ids=ids,
        documents=texts,
        metadatas=metadata_list,
        embeddings=embeddings,
    )


def semantic_search(case_id: str, query: str, top_k: int = 5) -> Dict[str, Any]:
    """Query a case's collection semantically."""
    coll = _get_collection(case_id)
    q_emb = _model.encode(query).tolist()
    res = coll.query(query_embeddings=[q_emb], n_results=top_k)

    # Normalize into a cleaner response
    hits = []
    for i in range(len(res["ids"][0])):
        hits.append(
            {
                "id": res["ids"][0][i],
                "score": res["distances"][0][i],
                "text": res["documents"][0][i],
                "metadata": res["metadatas"][0][i],
            }
        )
    return {"results": hits}
