import os
import json
from typing import Dict, Any, Generator, Optional, List

from windowsprefetch import Prefetch


def _safe_str(value: Any) -> Optional[str]:
    """
    Convert values safely to string.
    Returns None for empty/invalid values.
    """
    if value is None:
        return None
    try:
        s = str(value).strip()
        return s if s else None
    except Exception:
        return None


def _pick_last_run(timestamps: List[Any]) -> Optional[str]:
    """
    Prefetch exposes timestamps as a list of execution times.
    We use the first one as the latest observed execution time.
    """
    if not timestamps:
        return None
    try:
        return _safe_str(timestamps[0])
    except Exception:
        return None


def _extract_full_path(executable_name: Optional[str], resources: List[str]) -> Optional[str]:
    """
    Try to find the executable's full path from the Prefetch resources list.
    """
    if not executable_name or not resources:
        return None

    exe_upper = executable_name.upper()

    for item in resources:
        try:
            candidate = str(item).strip()
        except Exception:
            continue

        if not candidate:
            continue

        if candidate.upper().endswith("\\" + exe_upper) or candidate.upper().endswith("/" + exe_upper):
            return candidate

    return None


def iter_prefetch_events(prefetch_path: str) -> Generator[Dict[str, Any], None, None]:
    """
    Parse one .pf file and yield one normalized Prefetch event.
    """
    try:
        pf = Prefetch(prefetch_path)

        executable = _safe_str(getattr(pf, "executableName", None))
        run_count = getattr(pf, "runCount", None)
        timestamps = getattr(pf, "timestamps", []) or []
        resources = getattr(pf, "resources", []) or []

        last_run = _pick_last_run(timestamps)
        full_path = _extract_full_path(executable, resources)

        yield {
            "source": "prefetch",
            "prefetch_file": os.path.basename(prefetch_path),
            "executable": executable,
            "full_path": full_path,
            "run_count": run_count,
            "last_run": last_run,
            "referenced_files_count": len(resources),
        }

    except Exception as e:
        print(f"[PREFETCH] failed to parse {prefetch_path}: {e}")
        return


def format_prefetch_event(event: Dict[str, Any]) -> str:
    """
    Convert Prefetch event into one-line normalized text for:
    - semantic indexing
    - case review
    - AI explanation
    """
    ts = event.get("last_run") or "UNKNOWN_TIME"
    exe = event.get("executable") or "UNKNOWN_EXE"
    path = event.get("full_path") or ""
    run_count = event.get("run_count")
    refs = event.get("referenced_files_count")
    pf_name = event.get("prefetch_file") or ""

    return (
        f"[{ts}] SOURCE=prefetch "
        f"Executable={exe} "
        f"Path={path} "
        f"RunCount={run_count} "
        f"ReferencedFiles={refs} "
        f"PrefetchFile={pf_name}"
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