# api/timeline.py

import os
import json
from datetime import datetime, MAXYEAR
from typing import Any, Dict, List, Optional


def _parse_timestamp(ts: Optional[str]) -> Optional[datetime]:
    """
    Parse timestamp string into a *naive* datetime (no timezone).

    This avoids mixing offset-aware (+00:00) and naive datetimes when sorting.
    """
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(ts)
        # If the datetime is offset-aware (has tzinfo), drop the tz to make it naive.
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

                ts = _parse_timestamp(evt.get("timestamp"))
                if ts is None:
                    continue  # EVTX should always have a timestamp

                eid = evt.get("event_id")
                channel = evt.get("channel") or ""
                computer = evt.get("computer") or ""
                data = evt.get("data") or {}

                pieces = []

                # Common interesting fields:
                for key in (
                    "SubjectUserName",
                    "SubjectDomainName",
                    "TargetUserName",
                    "IpAddress",
                    "ProcessName",
                    "CommandLine",
                    "ServiceName",
                    "EventType",
                    "LogonType",
                ):
                    if key in data and data[key]:
                        pieces.append(f"{key}={data[key]}")

                if not pieces:
                    for k, v in list(data.items())[:5]:
                        if v:
                            pieces.append(f"{k}={v}")

                description = " ".join(pieces)

                timeline.append(
                    {
                        "timestamp": ts.isoformat(),
                        "sort_ts": ts,
                        "source": "evtx",
                        "channel": channel,
                        "computer": computer,
                        "event_id": eid,
                        "description": description,
                    }
                )

    return timeline


# -----------------------------
# Registry → timeline entries
# -----------------------------
def _load_registry_events(case_dir: str) -> List[Dict[str, Any]]:
    """
    Load registry events from artifacts/registry/*.jsonl and convert them
    into generic timeline entries.

    For binary hives with last_write timestamps: we use them.
    For .reg exports (SOFTWARE.reg): last_write is usually None → we push
    those to the end of the timeline with timestamp 'UNKNOWN_TIME'.
    """
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

                hive = evt.get("hive") or "UNKNOWN_HIVE"
                category = evt.get("category") or "registry"
                key_path = evt.get("key_path") or ""
                value_name = evt.get("value_name") or ""
                value = evt.get("value", "")

                # Try to use last_write as timestamp
                ts_obj = None
                lw = evt.get("last_write")
                if isinstance(lw, str):
                    ts_obj = _parse_timestamp(lw)

                if ts_obj is None:
                    # No reliable time → put these at the end of the timeline
                    ts_obj = datetime(MAXYEAR, 12, 31)
                    ts_str = "UNKNOWN_TIME"
                else:
                    ts_str = ts_obj.isoformat()

                description = (
                    f"category={category} HIVE={hive} Key={key_path} "
                    f"Name={value_name} Value={value}"
                )

                events.append(
                    {
                        "timestamp": ts_str,
                        "sort_ts": ts_obj,
                        "source": "registry",
                        "channel": "",
                        "computer": "",
                        "event_id": None,
                        "description": description,
                    }
                )

    return events


# -----------------------------
# Public API
# -----------------------------
def build_timeline(case_dir: str) -> List[Dict[str, Any]]:
    """
    Build a simple DFIR timeline for a case.

    Currently:
      - EVTX events (Security/Application/etc.)
      - Registry events (SOFTWARE.reg + any future binary hives)

    Returns a list of dicts sorted by timestamp ascending.
    """
    events: List[Dict[str, Any]] = []

    # 1) EVTX-based events
    events.extend(_load_evtx_events(case_dir))

    # 2) Registry-based events
    events.extend(_load_registry_events(case_dir))

    # Sort by real timestamp (registry entries with UNKNOWN_TIME go last)
    events.sort(key=lambda e: e["sort_ts"])

    # Drop internal sort field before returning
    for e in events:
        e.pop("sort_ts", None)

    return events
