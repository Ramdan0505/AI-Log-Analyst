# api/ingest_utils.py

import os
from typing import List, Dict, Any

from api.evtx_parser import generate_evtx_derivatives
from api.registry_parser import generate_registry_derivatives
from api.embedder import embed_texts

TEXT_EXTENSIONS = {".txt", ".log", ".json", ".csv", ".md"}


def build_and_index_case_corpus(case_dir: str, case_id: str) -> int:
    """
    Walk the case directory, convert EVTX → text, collect all text,
    write EVTX summaries to evtx_summaries.jsonl, and push everything
    into Chroma via embed_texts().

    Returns number of text chunks indexed.
    """
    text_chunks: List[str] = []
    metadata_list: List[Dict[str, Any]] = []

    evtx_summary_path = os.path.join(case_dir, "evtx_summaries.jsonl")
    evtx_summary_f = None

    try:
        # Overwrite summaries on each reindex to avoid infinite growth
        evtx_summary_f = open(evtx_summary_path, "w", encoding="utf-8")

        for root, _, files in os.walk(case_dir):
            for filename in files:
                path = os.path.join(root, filename)
                ext = os.path.splitext(filename)[1].lower()
                rel_path = os.path.relpath(path, case_dir)

                # 1) EVTX: parse and add summaries
                if ext == ".evtx":
                    stats = generate_evtx_derivatives(path, case_dir)
                    print(f"[EVTX] {filename}: {stats['events_count']} events parsed")

                    with open(stats["txt_path"], "r", encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue

                            text_chunks.append(line)
                            metadata_list.append(
                                {
                                    "source": "evtx",
                                    "case_id": case_id,
                                    "file": rel_path,
                                }
                            )
                            evtx_summary_f.write(line + "\n")

                # 2) Normal text-like files
                elif ext in TEXT_EXTENSIONS:
                    try:
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                    except (UnicodeDecodeError, OSError):
                        continue

                    if content.strip():
                        text_chunks.append(content)
                        metadata_list.append(
                            {
                                "source": "file",
                                "case_id": case_id,
                                "file": rel_path,
                            }
                        )
    finally:
        if evtx_summary_f is not None:
            evtx_summary_f.close()

    if text_chunks:
        # Your embed_texts expects (case_id, texts, metadata_list)
        embed_texts(case_id, text_chunks, metadata_list)

    return len(text_chunks)

