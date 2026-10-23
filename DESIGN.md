# DESIGN

## Architecture
```
 docs site / local fallback ──► crawler ─► chunker ─► BM25 index ─┐
                                                                   ▼
 user / Task 2 / Task 3 ──HTTP──► FastAPI ──► KnowledgeBrain.ask ──► {answer, citations, confidence, status}
                                     │            │ gate: coverage + BM25 floor  → unknown ─► escalation offer
                                     │            └ intent: "talk to a human"    → ticket
                                     ├─ /refresh ─► re-ingest, hash diff, reindex, log
                                     └─ SQLite: escalations, update history

 Task 2: email ─► classifier ─► Brain API ─► draft (+learned style rules) ─► human review ─► learn
                                   policy: 20 consecutive unchanged ⇒ auto-send; quality window ⇒ suspend + rollback
 Task 3: transcripts ─► extractor ─► catalog mapping ─► Brain API verification ─► tasks/hours ─► DRAFT proposal
                                   └──────────── human approval (hash-bound) ────────────► FINAL proposal
```
Tasks 2 and 3 talk to the Brain **only through its HTTP API** (`common/brain_client.py`), so they are genuinely integrated, and tests can swap in a FastAPI `TestClient` (same interface, no network) or a fake.

## Key decisions
1. **Retrieval = BM25, no embeddings.** Zero model downloads, deterministic, fast, explainable, easy to test. Cost: no synonym understanding ("upload" vs "import"), which shows up as over-cautious "unknown" answers.
2. **Honesty gate.** Answer only if (a) best chunk contains >= 60% of the question's IDF mass and BM25 >= 2.0, or (b) >= 85% if the question contains a *distinctive word the docs never mention* (e.g. "mobile", "Kubernetes"). Unseen generic English words are ignored (`COMMON_WORDS`). Rationale: a wrong confident answer is worse than "I don't know + human". The gate is tuned on my own small eval set, see EVALS.md.
3. **Extractive answers by default.** Sentences are copied from the cited chunk, so the answer cannot say anything the docs don't. Optional LLM mode is constrained to numbered sources and must output `INSUFFICIENT` otherwise (then we fall back to extractive).
4. **Source transparency.** `corpus_source` (`live|cache|fallback`) is returned by `/ask` and `/health`; fallback is never presented as live. Fallback URLs use `local://fallback/...` so they cannot be mistaken for real links.
5. **Update detection = content hash per page**, diff of added/changed/removed, reindex only if something changed, every refresh logged.
6. **Inbox learning = explainable style rules** (greeting, sign-off, suppressed lines, added lines) per category, not fine-tuning. Each learned change is an audited event. It does not learn to change documented *content*.
7. **Auto-send policy** (all in `inbox_agent/agent.py`): per-category streak of 20 *eligible* drafts approved unchanged; eligible = Brain `answered` with confidence >= 0.55 and category not in {billing, cancellation, complaint, spam}; any edit resets the streak. Quality monitor: >= 2 bad outcomes within the last 5 auto-sent (current *epoch*) ⇒ suspend, **restore the rule snapshot taken when auto-send was enabled**, reset streak, bump epoch (old bad outcomes can't re-trigger). Must be re-earned.
8. **SOW agent is rule-based + catalog-driven.** Requirements come only from *client* speakers; constraints (budget/deadline) are tracked with change history so the follow-up overrides earlier meetings; drop requests remove features. Anything that doesn't map to the catalog is **not estimated** and goes to the human list. Every in-scope feature and every out-of-scope request is checked against the Brain; "unknown" on an in-scope feature becomes an open item.
9. **Human approval gate.** `finalize` refuses unless `approval.json` exists and its hash equals the current `sow.json`; approving requires acknowledging open items.
10. **Python for all tasks** (see README caveat about TypeScript).

## Data model (SQLite)
Brain: `escalations(id, created, question, contact, reason, status, notes)`, `updates(id, ts, source, summary)`.
Inbox: `mails(email_id, seq, category, decision, draft, final, brain_status, confidence, eligible, edited, sent, auto_sent, epoch, outcome)`, `state(category, streak, auto_enabled, suspended, epoch, snapshot, rules)`, `events(ts, category, kind, detail)`.

## Failure modes handled
Brain down → Task 2 produces a safe holding reply (needs review, never eligible); Task 3 marks everything unverified. Live crawl fails → cache → fallback (labelled). LLM error → extractive. Unknown question → no citations, ticket offered. Spam → archived, no draft.

## Not done / future work
Embedding or hybrid retrieval; LLM classifier for emails; scheduled refresh; auth on the API; real mail integration; real reviewer UI; TypeScript port of Task 2; PDF/DOCX proposal export.
