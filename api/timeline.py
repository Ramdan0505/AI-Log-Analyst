# api/timeline.py

import os
import json
from datetime import datetime, MAXYEAR
from typing import Any, Dict, List, Optional


# -----------------------------
# Timestamp parsing
# -----------------------------
def _parse_timestamp(ts: Optional[str]) -> Optional[datetime]:
    """
    Parse timestamp string into a naive datetime.
    This avoids mixing timezone-aware and naive datetimes.
    """
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt
    except Exception:
        return None


# -----------------------------
# EVTX → timeline entries
# -----------------------------
def _load_evtx_events(case_dir: str) -> List[Dict[str, Any]]:
    evtx_dir = os.path.join(case_dir, "artifacts", "evtx")
    if not os.path.isdir(evtx_dir):
        return []

    timeline: List[Dict[str, Any]] = []

    for filename in os.listdir(evtx_dir):
        if not filename.lower().endswith(".jsonl"):
            continue

        path = os.path.join(evtx_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
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
                    if key in data and data[key]:
                        pieces.append(f"{key}={data[key]}")

                if not pieces:
                    for k, v in list(data.items())[:5]:
                        if v:
                            pieces.append(f"{k}={v}")

                timeline.append(
                    {
                        "timestamp": ts_obj.isoformat(),
                        "sort_ts": ts_obj,
                        "source": "evtx",
                        "channel": evt.get("channel") or "",
                        "computer": evt.get("computer") or "",
                        "event_id": evt.get("event_id"),
                        "description": " ".join(pieces),
                    }
                )

    return timeline


# -----------------------------
# Registry → timeline entries
# -----------------------------
def _load_registry_events(case_dir: str) -> List[Dict[str, Any]]:
    reg_dir = os.path.join(case_dir, "artifacts", "registry")
    if not os.path.isdir(reg_dir):
        return []

    events: List[Dict[str, Any]] = []

    for filename in os.listdir(reg_dir):
        if not filename.lower().endswith(".jsonl"):
            continue

        path = os.path.join(reg_dir, filename)
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue

                try:
                    evt = json.loads(line)
                except Exception:
                    continue

                ts_obj = _parse_timestamp(evt.get("last_write"))
                if ts_obj is None:
                    ts_obj = datetime(MAXYEAR, 12, 31)
                    ts_str = "UNKNOWN_TIME"
                else:
                    ts_str = ts_obj.isoformat()

                events.append(
                    {
                        "timestamp": ts_str,
                        "sort_ts": ts_obj,
                        "source": "registry",
                        "channel": "",
                        "computer": "",
                        "event_id": None,
                        "description": (
                            f"category={evt.get('category')} "
                            f"HIVE={evt.get('hive')} "
                            f"Key={evt.get('key_path')} "
                            f"Name={evt.get('value_name')} "
                            f"Value={evt.get('value')}"
                        ),
                    }
                )

    return events


# -----------------------------
# Public API
# -----------------------------
def build_timeline(case_dir: str) -> List[Dict[str, Any]]:
    """
    Build a DFIR timeline for a case.
    Returns at most 200 most recent events (demo-safe).
    """
    events: List[Dict[str, Any]] = []

    events.extend(_load_evtx_events(case_dir))
    events.extend(_load_registry_events(case_dir))

    # Sort chronologically
    events.sort(key=lambda e: e["sort_ts"])

    # Keep only the most recent 200 events
    events = events[-200:]

    # Remove internal sort key
    for e in events:
        e.pop("sort_ts", None)

    return events
