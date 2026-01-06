# api/timeline.py
import os
import json
from datetime import datetime, MAXYEAR
from typing import Any, Dict, List, Optional


def _parse_timestamp(ts: Optional[str]) -> Optional[datetime]:
    """
    Parse ISO timestamps into naive datetime for consistent sorting.
    Handles 'Z' suffix.
    """
    if not ts:
        return None
    try:
        s = ts.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except Exception:
        return None


def _load_evtx_events(case_dir: str) -> List[Dict[str, Any]]:
    evtx_dir = os.path.join(case_dir, "artifacts", "evtx")
    if not os.path.isdir(evtx_dir):
        return []

    out: List[Dict[str, Any]] = []

    for filename in os.listdir(evtx_dir):
        if not filename.lower().endswith(".jsonl"):
            continue

        path = os.path.join(evtx_dir, filename)
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        evt = json.loads(line)
                    except Exception:
                        continue

                    ts_obj = _parse_timestamp(evt.get("timestamp"))
                    if ts_obj is None:
                        continue

                    eid = evt.get("event_id")
                    channel = evt.get("channel") or ""
                    computer = evt.get("computer") or ""
                    data = evt.get("data") or {}

                    pieces = []
                    for key in (
                        "SubjectUserName",
                        "SubjectDomainName",
                        "TargetUserName",
                        "IpAddress",
                        "ProcessName",
                        "CommandLine",
                        "ServiceName",
                        "LogonType",
                    ):
                        v = data.get(key)
                        if v:
                            pieces.append(f"{key}={v}")

                    if not pieces:
                        for k, v in list(data.items())[:6]:
                            if v:
                                pieces.append(f"{k}={v}")

                    desc = " ".join(pieces)[:400]

                    out.append(
                        {
                            "timestamp": ts_obj.isoformat(),
                            "sort_ts": ts_obj,
                            "unknown_time": False,
                            "source": "evtx",
                            "channel": channel,
                            "computer": computer,
                            "event_id": eid,
                            "description": desc,
                        }
                    )
        except Exception:
            continue

    return out


def _load_registry_events(case_dir: str) -> List[Dict[str, Any]]:
    reg_dir = os.path.join(case_dir, "artifacts", "registry")
    if not os.path.isdir(reg_dir):
        return []

    out: List[Dict[str, Any]] = []

    for filename in os.listdir(reg_dir):
        if not filename.lower().endswith(".jsonl"):
            continue

        path = os.path.join(reg_dir, filename)
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        evt = json.loads(line)
                    except Exception:
                        continue

                    hive = evt.get("hive") or "UNKNOWN_HIVE"
                    category = evt.get("category") or "registry"
                    key_path = evt.get("key_path") or ""
                    value_name = evt.get("value_name") or ""
                    value = evt.get("value", "")

                    ts_obj = _parse_timestamp(evt.get("last_write")) if isinstance(evt.get("last_write"), str) else None
                    unknown = False
                    if ts_obj is None:
                        unknown = True
                        ts_obj = datetime(MAXYEAR, 12, 31)
                        ts_str = "UNKNOWN_TIME"
                    else:
                        ts_str = ts_obj.isoformat()

                    desc = (
                        f"category={category} HIVE={hive} Key={key_path} "
                        f"Name={value_name} Value={value}"
                    )[:400]

                    out.append(
                        {
                            "timestamp": ts_str,
                            "sort_ts": ts_obj,
                            "unknown_time": unknown,
                            "source": "registry",
                            "channel": "",
                            "computer": "",
                            "event_id": None,
                            "description": desc,
                        }
                    )
        except Exception:
            continue

    return out


def build_timeline(case_dir: str, limit: int = 200, descending: bool = True) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    events.extend(_load_evtx_events(case_dir))
    events.extend(_load_registry_events(case_dir))

    # Keep UNKNOWN_TIME entries always at the bottom (even when descending)
    known = [e for e in events if not e.get("unknown_time")]
    unknown = [e for e in events if e.get("unknown_time")]

    known.sort(key=lambda e: e["sort_ts"], reverse=descending)
    # unknown already has MAXYEAR sort_ts; keep it last
    unknown.sort(key=lambda e: e["sort_ts"])

    merged = known + unknown

    # Trim for demo
    merged = merged[: max(1, min(int(limit), 2000))]

    for e in merged:
        e.pop("sort_ts", None)
        e.pop("unknown_time", None)

    return merged
