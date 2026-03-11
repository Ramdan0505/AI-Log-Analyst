# api/prefetch_parser.py
import os
import json
from typing import Dict, Any, Generator, Optional, List
from pyprefetch import Prefetch

def _safe_iso(ts: Any) -> Optional[str]:
    """
    Convert a timestamp-like object to a string safely.
    Works whether the parser returns a datetime or a plain string.
    """
    if ts is None:
        return None
    try:
        if hasattr(ts, "isoformat"):
            return ts.isoformat()
        return str(ts)
    except Exception:
        return None


def _extract_full_path(executable_name: Optional[str], referenced_files: List[str]) -> Optional[str]:
    """
    Best-effort guess for the executable's full path by looking through
    referenced files and matching the executable name.
    """
    if not executable_name:
        return None

    exe_upper = executable_name.upper()

    for ref in referenced_files:
        try:
            candidate = str(ref).strip()
        except Exception:
            continue

        if not candidate:
            continue

        if candidate.upper().endswith("\\" + exe_upper) or candidate.upper().endswith("/" + exe_upper):
            return candidate

    return None


def iter_prefetch_events(prefetch_path):

    pf = Prefetch(prefetch_path)

    executable = pf.executable_name
    run_count = pf.run_count

    last_run = None
    if pf.last_run_times:
        last_run = pf.last_run_times[0]

    referenced_files = pf.files_loaded or []

    full_path = None
    if referenced_files:
        for f in referenced_files:
            if executable.lower() in f.lower():
                full_path = f
                break

    yield {
        "source": "prefetch",
        "prefetch_file": os.path.basename(prefetch_path),
        "executable": executable,
        "full_path": full_path,
        "run_count": run_count,
        "last_run": str(last_run) if last_run else None,
        "referenced_files_count": len(referenced_files)
    }


def format_prefetch_event(event: Dict[str, Any]) -> str:
    """
    Convert the normalized prefetch event into one line of text.
    This is what gets indexed and searched semantically.
    """
    ts = event.get("last_run") or "UNKNOWN_TIME"
    exe = event.get("executable") or "UNKNOWN_EXE"
    path = event.get("full_path") or ""
    run_count = event.get("run_count")
    pf = event.get("prefetch_file") or ""
    refs = event.get("referenced_files_count")

    return (
        f"[{ts}] SOURCE=prefetch Executable={exe} "
        f"Path={path} RunCount={run_count} "
        f"ReferencedFiles={refs} PrefetchFile={pf}"
    ).strip()


def generate_prefetch_derivatives(prefetch_path: str, case_dir: str) -> Dict[str, Any]:
    """
    Write:
      - artifacts/prefetch/<basename>.jsonl
      - artifacts/prefetch/<basename>.txt
    """
    os.makedirs(case_dir, exist_ok=True)

    base = os.path.splitext(os.path.basename(prefetch_path))[0]
    out_dir = os.path.join(case_dir, "artifacts", "prefetch")
    os.makedirs(out_dir, exist_ok=True)

    jsonl_path = os.path.join(out_dir, f"{base}.jsonl")
    txt_path = os.path.join(out_dir, f"{base}.txt")

    count = 0

    with open(jsonl_path, "w", encoding="utf-8") as jf, open(txt_path, "w", encoding="utf-8") as tf:
        for evt in iter_prefetch_events(prefetch_path):
            count += 1
            jf.write(json.dumps(evt, ensure_ascii=False) + "\n")
            tf.write(format_prefetch_event(evt) + "\n")

    return {
        "events_count": count,
        "jsonl_path": jsonl_path,
        "txt_path": txt_path,
    }