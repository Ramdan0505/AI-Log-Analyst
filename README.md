# AI-Log-Analyst 
** AI-Log-Analyst  (MVP)**

AI-Log-Analyst is a **case-centric, AI-assisted DFIR investigation platform** designed to accelerate *early-stage incident triage*.  
It ingests forensic artifacts (logs, EVTX, registry, files), builds a **semantic evidence index**, and enables analysts to search, explain, timeline, and map activity to **MITRE ATT&CK**.

This is an **MVP** focused on *understanding what happened*, not automated remediation.

---

## Why This Project Exists

Early DFIR work is slow because:
- Logs are large and noisy
- Analysts rely on manual keyword search
- Context is fragmented across tools
- AI is often used *without grounding*

Lab Investigator addresses this by:
- Treating investigations as **persistent cases**
- Normalizing artifacts into searchable text
- Using **vector search** instead of grep
- Applying AI **only after evidence is indexed**

---

## High-Level Workflow

1. **Ingest evidence**
   - Raw text (alerts, notes, findings)
   - Forensic bundles (ZIP with EVTX, registry, files)

2. **Create a case**
   - Each ingest creates a unique case ID
   - Artifacts and metadata persist across restarts

3. **Investigate**
   - Semantic search across evidence
   - Timeline reconstruction
   - AI-generated case explanation
   - MITRE ATT&CK technique extraction

4. **Iterate**
   - Search → analyze → explain → refine hypotheses

---

## Core Concepts

### What Is a Case?
A **case** is a persistent investigation workspace identified by a UUID.

A case contains:
- Ingest metadata
- Extracted forensic artifacts
- EVTX and registry summaries
- Vector embeddings for search
- AI analysis outputs

Cases persist until explicitly deleted.

---

## Ingest Methods

### 1. Text Ingest
Used for:
- Analyst notes
- Alerts from other tools
- Manual findings

**What happens**
- Text is embedded into the vector database
- Metadata is attached
- Case becomes immediately searchable

---

### 2. File / ZIP Ingest
Used for:
- Forensic bundles
- Windows EVTX logs
- Registry hives
- Collected files

**What happens**
- ZIP is extracted by the worker
- EVTX files are parsed into:
  - Structured JSON
  - One-line text summaries
- Registry artifacts are parsed (when present)
- All derived text is embedded
- Case becomes searchable, explorable, and explainable

---

## Search (Semantic, Not Keyword)

Search is powered by a **vector database (ChromaDB)**.

### What This Means
- Queries are embedded into vectors
- Evidence text is embedded into vectors
- Results are ranked by **semantic similarity**
- Irrelevant matches are filtered by distance threshold

### Good Search Queries
- `Event ID 4104`
- `PowerShell script execution`
- `failed logon`
- `service installed`
- `NT AUTHORITY\SYSTEM`
- `registry modification`

### Expected Behavior
- Meaningful queries return results
- Nonsense queries (`zzzzzz`) return `[]`
- This is correct and desirable

---

## Timeline

The timeline is built from:
- Parsed EVTX events
- Registry changes (when timestamps exist)

Each entry includes:
- Timestamp
- Source (evtx / registry)
- Event ID
- Human-readable description

Purpose:
- Reconstruct sequence of activity
- Support narrative investigation
- Identify suspicious clusters

---

## AI Explain Case

The **Explain Case** feature:
- Reads *actual case artifacts*
- Produces a structured DFIR report
- Explicitly calls out data gaps
- Avoids hallucination by grounding on evidence

AI is used as an **analysis accelerator**, not an authority.

---

## MITRE ATT&CK Mapping

After explanation:
- Clearly supported ATT&CK techniques are extracted
- Each technique includes:
  - Technique ID
  - Name
  - Tactic
  - Evidence-based justification

If no techniques apply, the result is `[]` by design.

---

## Architecture

Browser UI
|
v
FastAPI (API container)
|
+--> ChromaDB (vector search)
|
+--> Worker (background extraction)


### Components

#### API (FastAPI)
- Case management
- Ingest endpoints
- Search
- Timeline
- AI explanation
- MITRE extraction

#### Worker
- ZIP extraction
- EVTX parsing
- Registry parsing
- Text normalization
- Embedding + indexing

#### ChromaDB
- Vector database
- One collection per case
- Persistent storage

#### UI
- Static HTML + JavaScript
- No React
- Served via FastAPI

---

## Technology Stack

- **Python** (FastAPI, worker pipeline)
- **SentenceTransformers** (embeddings)
- **ChromaDB** (vector database)
- **Docker & Docker Compose**
- **PowerShell** (local testing)
- **HTML / JS / CSS** (UI)
- **OpenAI GPT-5.1** (analysis & MITRE tagging)

---

## Why Docker?

Docker provides:
- Reproducible environments
- Service isolation
- Reliable demos
- Persistent data volumes

`localhost:8080` exists because:
- Docker maps container port `8000 → 8080`
- Browser communicates with the API through that mapping

---

## Running the Project

```bash
docker compose up --build
