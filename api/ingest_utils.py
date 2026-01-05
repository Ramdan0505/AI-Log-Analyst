# api/ingest_utils.py

import os
from typing import List, Dict, Any

from api.evtx_parser import generate_evtx_derivatives
from api.registry_parser import generate_registry_derivatives
from api.embedder import embed_texts

# File type sets
TEXT_EXTENSIONS = {".txt", ".log", ".json", ".csv", ".md"}
REGISTRY_EXTENSIONS = {".dat", ".hiv", ".hive", ".reg"}


def build_and_index_case_corpus(case_dir: str, case_id: str) -> int:
    """
    Walk the case directory, collect all extracted text (EVTX, registry, files),
    and push it into Chroma via embed_texts().

    Returns number of text chunks indexed.
    """

    text_chunks: List[str] = []
    metadata_list: List[Dict[str, Any]] = []

    # -------------------------------------------------
    # 1) Index EVTX-derived text files
    # -------------------------------------------------
    evtx_txt_dir = os.path.join(case_dir, "artifacts", "evtx")

    if os.path.isdir(evtx_txt_dir):
        for fname in os.listdir(evtx_txt_dir):
            if not fname.endswith(".txt"):
                continue

            path = os.path.join(evtx_txt_dir, fname)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    text_chunks.append(line)
                    metadata_list.append({
                        "source": "evtx",
                        "case_id": case_id,
                        "file": f"artifacts/evtx/{fname}",
                    })

    # -------------------------------------------------
    # 2) Walk remaining files (registry + generic text)
    # -------------------------------------------------
    evtx_summary_path = os.path.join(case_dir, "evtx_summaries.jsonl")
    reg_summary_path = os.path.join(case_dir, "registry_summaries.jsonl")

    evtx_summary_f = None
    reg_summary_f = None

    try:
        evtx_summary_f = open(evtx_summary_path, "w", encoding="utf-8")
        reg_summary_f = open(reg_summary_path, "w", encoding="utf-8")

        for root, _, files in os.walk(case_dir):
            for filename in files:
                path = os.path.join(root, filename)
                ext = os.path.splitext(filename)[1].lower()
                rel_path = os.path.relpath(path, case_dir)

                # Skip generated summary files
                if filename in ("evtx_summaries.jsonl", "registry_summaries.jsonl"):
                    continue

                # Registry hives
                if ext in REGISTRY_EXTENSIONS:
                    stats = generate_registry_derivatives(path, case_dir)
                    if stats.get("events_count", 0) > 0:
                        with open(stats["txt_path"], "r", encoding="utf-8") as f:
                            for line in f:
                                line = line.strip()
                                if not line:
                                    continue

                                text_chunks.append(line)
                                metadata_list.append({
                                    "source": "registry",
                                    "case_id": case_id,
                                    "file": rel_path,
                                })
                                reg_summary_f.write(line + "\n")

                # Plain text files
                elif ext in TEXT_EXTENSIONS:
                    try:
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read().strip()
                    except Exception:
                        continue

                    if content:
                        text_chunks.append(content)
                        metadata_list.append({
                            "source": "file",
                            "case_id": case_id,
                            "file": rel_path,
                        })

    finally:
        if evtx_summary_f:
            evtx_summary_f.close()
        if reg_summary_f:
            reg_summary_f.close()

    # -------------------------------------------------
    # 3) Embed into Chroma (batched)
    # -------------------------------------------------
    if not text_chunks:
        print(f"[EMBED] No text found for case {case_id}")
        return 0

    max_batch = 5000
    total = len(text_chunks)

    for start in range(0, total, max_batch):
        end = start + max_batch
        batch_texts = text_chunks[start:end]
        batch_meta = metadata_list[start:end]

        print(f"[EMBED] case={case_id} batch={start}-{end-1} of {total}")
        embed_texts(case_id, batch_texts, batch_meta)

    return total
