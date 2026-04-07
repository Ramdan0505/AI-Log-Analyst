#!/usr/bin/env python3
import sys
import os
import json
import hashlib
import shutil
import zipfile
import re
import requests
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = None
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY)

API_URL = os.getenv("API_URL", "http://api:8000")  # Docker internal hostname


# ----------------------- helpers -----------------------

ARTIFACTS_SUBDIR = "files"

def hash_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure(out_dir, rel_path):
    dst = os.path.join(out_dir, ARTIFACTS_SUBDIR, rel_path)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    return dst


def record_meta(out_dir, rel_path, sha=None, extra=None):
    meta = {"path": rel_path}
    if sha:
        meta["sha256"] = sha
    if extra:
        meta.update(extra)
    with open(os.path.join(out_dir, "metadata.jsonl"), "a", encoding="utf-8") as m:
        m.write(json.dumps(meta) + "\n")


# -------------------------------------------------------
# Worker → API communication
# -------------------------------------------------------
def post_to_api(endpoint: str, payload: dict):
    url = f"{API_URL}{endpoint}"
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"[worker] ERROR posting to API {url}: {e}")
        return None


# -------------------------------------------------------
# Optional OpenAI helper
# -------------------------------------------------------
def call_openai(prompt: str) -> str:
    if client is None:
        print("[worker] No OPENAI_API_KEY set, skipping AI call.")
        return ""

    try:
        response = client.chat.completions.create(
            model="gpt-5.1",
            messages=[
                {"role": "system", "content": "You are a DFIR assistant worker module."},
                {"role": "user", "content": prompt},
            ],
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"[worker] OpenAI error: {e}")
        return ""


# ----------------------- ingest ------------------------

def unpack_zip(zip_path, out_dir):
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.infolist():
            if member.is_dir():
                continue
            rel = member.filename
            dst = ensure(out_dir, rel)
            with zf.open(member) as src, open(dst, "wb") as dstf:
                shutil.copyfileobj(src, dstf)
            record_meta(out_dir, rel, hash_file(dst), {"source": "zip"})


def copy_single(path, out_dir):
    base = os.path.basename(path)
    dst = ensure(out_dir, base)
    shutil.copy2(path, dst)
    record_meta(out_dir, base, hash_file(dst), {"source": "single"})


def walk_dir(root_path, out_dir):
    for root, _, files in os.walk(root_path):
        for f in files:
            p = os.path.join(root, f)
            rel = os.path.relpath(p, root_path)
            dst = ensure(out_dir, rel)
            if os.path.abspath(p) == os.path.abspath(dst):
                continue
            shutil.copy2(p, dst)
            record_meta(out_dir, rel, hash_file(dst), {"source": "dir"})


# ----------------------- EVTX --------------------------

def parse_evtx(out_dir):
    try:
        from Evtx.Evtx import Evtx
    except Exception:
        print("[worker] python-evtx not available; skipping EVTX parsing")
        return

    files_root = os.path.join(out_dir, ARTIFACTS_SUBDIR)

    # IMPORTANT:
    # Keep worker raw capture separate from API-generated semantic summary file.
    raw_summaries_path = os.path.join(out_dir, "evtx_raw_summaries.jsonl")
    total = 0

    # Start clean per case run
    if os.path.exists(raw_summaries_path):
        try:
            os.remove(raw_summaries_path)
        except Exception:
            pass

    for path in Path(files_root).rglob("*.evtx"):
        try:
            with Evtx(str(path)) as log:
                i = 0
                for rec in log.records():
                    if i >= 200:
                        break

                    try:
                        xml = rec.xml()
                    except Exception:
                        xml = None

                    try:
                        record_num = rec.record_num()
                    except Exception:
                        record_num = None

                    try:
                        timestamp = rec.timestamp().isoformat() if rec.timestamp() else None
                    except Exception:
                        timestamp = None

                    event_id = None
                    try:
                        maybe_eid = getattr(rec, "event_id", None)
                        if callable(maybe_eid):
                            event_id = maybe_eid()
                    except Exception:
                        event_id = None

                    out = {
                        "file": str(path.relative_to(files_root)),
                        "record_num": record_num,
                        "timestamp": timestamp,
                        "event_id": event_id,
                        "xml_snippet": (xml[:800] if xml else None),
                    }

                    with open(raw_summaries_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(out) + "\n")

                    i += 1
                    total += 1

        except Exception as e:
            print(f"[worker] EVTX parse error for {path}: {e}")
            record_meta(
                out_dir,
                str(path.relative_to(files_root)),
                extra={"evtx_parse_error": str(e)}
            )

    with open(os.path.join(out_dir, "evtx_parse_stats.json"), "w", encoding="utf-8") as f:
        json.dump({"total_records_captured": total}, f)


# ----------------------- Registry ----------------------

def parse_registry(out_dir):
    try:
        from regipy.registry import RegistryHive
    except Exception:
        print("[worker] regipy not available; skipping registry parsing")
        return

    # Placeholder: current worker-side registry parser intentionally omitted
    # because your API-side pipeline already handles registry derivatives.
    pass


# ----------------------- main --------------------------

def main():
    if len(sys.argv) < 3:
        print("Usage: extract_job.py <image_path> <case_id>")
        sys.exit(1)

    image_path, case_id = sys.argv[1], sys.argv[2]
    out_dir = f"/data/artifacts/{case_id}"
    os.makedirs(os.path.join(out_dir, ARTIFACTS_SUBDIR), exist_ok=True)

    # Extraction logic
    if os.path.isfile(image_path) and image_path.lower().endswith(".zip"):
        unpack_zip(image_path, out_dir)
    elif os.path.isdir(image_path):
        walk_dir(image_path, out_dir)
    else:
        copy_single(image_path, out_dir)

    # DFIR pipelines
    parse_evtx(out_dir)
    parse_registry(out_dir)

    print(f"[worker] Extraction complete for case: {case_id}")

    # Notify API so indexing can happen
    post_to_api("/worker_done", {"case_id": case_id})

    # Optional AI worker summary
    ai_summary = call_openai(f"Summarize extraction steps for case {case_id}")
    if ai_summary:
        with open(os.path.join(out_dir, "worker_ai_summary.txt"), "w", encoding="utf-8") as f:
            f.write(ai_summary)


if __name__ == "__main__":
    main()