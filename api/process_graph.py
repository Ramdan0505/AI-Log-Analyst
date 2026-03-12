import re
from typing import Dict, Any, List, Set

from api.timeline import build_timeline


PROCESS_NAME_RE = re.compile(r'([A-Za-z0-9_\-]+\.exe)', re.IGNORECASE)


def _extract_process_names(text: str) -> List[str]:
    if not text:
        return []
    return list({m.group(1).upper() for m in PROCESS_NAME_RE.finditer(text)})


def build_process_execution_graph(case_dir: str, limit: int = 200) -> Dict[str, Any]:
    """
    Build a simple process execution graph from the merged timeline.

    Sources:
    - Prefetch execution events
    - EVTX process-related descriptions
    - Registry persistence events
    """
    timeline = build_timeline(case_dir, limit=limit, descending=False)

    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    seen_nodes: Set[str] = set()

    ordered_entities: List[Dict[str, Any]] = []

    for evt in timeline:
        source = evt.get("source", "")
        desc = evt.get("description", "") or ""
        timestamp = evt.get("timestamp")

        if source == "prefetch":
            proc_names = _extract_process_names(desc)
            for proc in proc_names:
                ordered_entities.append({
                    "id": proc,
                    "label": proc,
                    "type": "process",
                    "timestamp": timestamp,
                    "source": "prefetch",
                })

        elif source == "evtx":
            proc_names = _extract_process_names(desc)
            for proc in proc_names:
                ordered_entities.append({
                    "id": proc,
                    "label": proc,
                    "type": "process",
                    "timestamp": timestamp,
                    "source": "evtx",
                })

        elif source == "registry":
            lowered = desc.lower()
            if "run" in lowered or "runonce" in lowered or "services" in lowered:
                node_id = f"registry:{hash(desc)}"
                ordered_entities.append({
                    "id": node_id,
                    "label": "Registry Persistence",
                    "type": "persistence",
                    "timestamp": timestamp,
                    "source": "registry",
                    "description": desc[:120],
                })

    # Build unique nodes
    for item in ordered_entities:
        if item["id"] not in seen_nodes:
            nodes.append({
                "id": item["id"],
                "label": item["label"],
                "type": item["type"],
                "source": item["source"],
            })
            seen_nodes.add(item["id"])

    # Connect chronologically adjacent relevant entities
    for i in range(len(ordered_entities) - 1):
        a = ordered_entities[i]
        b = ordered_entities[i + 1]

        if a["id"] == b["id"]:
            continue

        edges.append({
            "source": a["id"],
            "target": b["id"],
            "reason": "chronological_proximity",
            "from_source": a["source"],
            "to_source": b["source"],
            "from_time": a.get("timestamp"),
            "to_time": b.get("timestamp"),
        })

    return {
        "nodes": nodes,
        "edges": edges,
        "entity_count": len(ordered_entities),
    }