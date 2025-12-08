# api/timeline.py

import os
import json
from datetime import datetime
from typing import Any, Dict, List, Optional


def _parse_timestamp(ts: Optional[str]) -> Optional[datetime]:
    """
    Parse EVTX timestamp string into datetime.
    We expect ISO-like strings from generate_evtx_derivatives, e.g.:
        2025-12-03T14:53:51.818457+00:00
    """
    if not ts:
        return None
    try:
        # Python 3.11: fromisoformat handles offsets like +00:00
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def _load_evtx_events(case_dir: str) -> List[Dict[str, Any]]:
    """
    Load structured EVTX events from artifacts/evtx/*.jsonl and convert them
    into generic timeline entries.
    """
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
                    continue

                eid = evt.get("event_id")
                channel = evt.get("channel") or ""
                computer = evt.get("computer") or ""
                data = evt.get("data") or {}

                # Build a compact description from key fields
                # You can tune this over time.
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

                # Fallback: include a few arbitrary k=v pairs if nothing chosen
                if not pieces:
                    for k, v in list(data.items())[:5]:
                        if v:
                            pieces.append(f"{k}={v}")

                description = " ".join(pieces)

                timeline.append(
                    {
                        "timestamp": ts.isoformat(),
                        "source": "evtx",
                        "channel": channel,
                        "computer": computer,
                        "event_id": eid,
                        "description": description,
                    }
                )

    return timeline


def build_timeline(case_dir: str) -> List[Dict[str, Any]]:
    """
    Build a simple DFIR timeline for a case.

    Currently:
      - EVTX events from artifacts/evtx/*.jsonl
    Future:
      - Registry last-write times
      - Prefetch execution times
      - File system timestamps

    Returns a list of dicts sorted by timestamp ascending.
    """
    events: List[Dict[str, Any]] = []

    # 1) EVTX-based events
    events.extend(_load_evtx_events(case_dir))

    # TODO: add registry/prefetch/file events here later

    # Sort by timestamp
    events.sort(key=lambda e: e["timestamp"])
    return events
