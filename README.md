# AI Tech Consultant Capstone - Knowledge Brain, Inbox Agent, Meeting-to-SOW

Three integrated Python tasks:

| Task | What it does | Code |
|---|---|---|
| 1. Knowledge Brain | Ingests documentation, answers with citations, says "I don't know" honestly, escalates to a human, detects doc updates, exposes an HTTP API | `knowledge_brain/` |
| 2. Inbox Agent | Classifies 77 synthetic emails, drafts replies **by calling the Brain API**, learns from human edits, earns auto-send after 20 consecutive unchanged drafts, suspends + rolls back if quality drops | `inbox_agent/` |
| 3. Meeting-to-SOW | Reads 3 meeting transcripts + a follow-up, extracts requirements, checks them against the Brain API, flags out-of-scope items, builds tasks/hours and a proposal, **requires human approval** | `sow_agent/` |

> ## Read this first - honest status
> * **The original assignment brief was not available to me** (the project folder was empty). I followed the summary you gave me. Compare against the real brief and adjust - especially file names, TypeScript vs Python for Task 2, and any required formats.
> * **The live Brilliant Directions Solution Center could not be reached** from the build environment (DNS blocked). A real sitemap crawler is implemented and unit-tested on *mock* data only. The demo runs on **17 SYNTHETIC documentation pages I wrote** (`data/fallback_docs/`). They are *not* real Brilliant Directions documentation and may contradict it. **Run `python run_demo.py --live` on your own machine to try the real site** - I have not verified that path.
> * **No LLM key was available.** The Brain runs in deterministic *extractive* mode (still cited). The optional Claude mode (`ANTHROPIC_API_KEY`) is implemented but **untested**.
> * **Task 2 is in Python, not TypeScript.** I could not confirm Python is allowed by the brief. Reasons: shared test suite/launcher and direct reuse of the Brain client. If TypeScript is required, the Brain API is plain HTTP/JSON, so porting `inbox_agent/` is mechanical, but I have not done it.
> * The "human reviewer" and "customer feedback" in the Task 2 demo are **scripted simulations** (`inbox_agent/simulate.py`). No email is ever sent.
> * **Nothing has been pushed to GitHub.** See "Publish to GitHub" below.
> * Full numbers and caveats: [EVALS.md](EVALS.md).

## Quick start (beginner friendly)

You need Python 3.10+ (check with `python3 --version`).

```bash
./run.sh            # creates a virtual env (.venv), installs packages, copies .env.example to .env, runs the demo
./run.sh --test     # same, but runs the automated tests first
```

What the commands mean:
* `python3 -m venv .venv` makes a private folder of Python packages so nothing else on your computer is touched.
* `pip install -r requirements.txt` installs the libraries listed in that file.
* `python run_demo.py` starts the Brain API on a local port, then runs Tasks 1-3 against it and writes results to `samples/output/`.

Manual equivalent:
```bash
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                     # optional: add keys
python run_demo.py            # offline demo (synthetic docs)
python run_demo.py --live     # try the real sitemap first (needs internet)
python run_demo.py --serve    # only run the API at http://127.0.0.1:8000  (interactive docs at /docs)
python -m pytest -q           # automated tests
python evals/run_evals.py     # scored evaluations -> evals/RESULTS.md
```

## Using each task on its own

**Task 1 API** (start with `python run_demo.py --serve`, or `uvicorn knowledge_brain.api:app --port 8000`):

| Endpoint | Purpose |
|---|---|
| `POST /ask {"question": "..."}` | Answer + citations + confidence. `status` is `answered`, `unknown`, or `escalation_requested` |
| `POST /escalate {"question","contact"}` | Open a human-support ticket |
| `GET /escalations?status=open`, `POST /escalations/{id}/resolve` | Review/close tickets |
| `POST /refresh` | Re-ingest docs, report added/changed/removed pages, reindex |
| `GET /updates` | History of refreshes |
| `GET /sources`, `GET /health` | Indexed pages / status (shows whether docs are `live`, `cache`, or `fallback`) |

```bash
curl -s -X POST localhost:8000/ask -H 'content-type: application/json' \
  -d '{"question":"How do I connect a custom domain?"}'
```

**Task 2:** `python run_demo.py` runs the simulation. In code: `InboxAgent(BrainClient(...)).process(email)` then `.review(id, final_text_or_None)`, `.report_outcome(id, good)`, `.audit(id, corrected)`.

**Task 3** (Brain API must be running):
```bash
python -m sow_agent.cli run                                   # writes samples/output/sow/ (DRAFT)
python -m sow_agent.cli finalize                              # REFUSED until a human approves
python -m sow_agent.cli approve --approver "Your Name" --ack-open-items
python -m sow_agent.cli finalize                              # writes proposal_FINAL.md
```
Approval is bound to the SOW's content hash: editing `sow.json` after approval invalidates it.

## Repository layout
```
knowledge_brain/   crawler.py index.py (BM25) brain.py (answer/gate/escalate/refresh) store.py api.py
inbox_agent/       emails.py classifier.py rules.py (learning) agent.py (policy) simulate.py
sow_agent/         catalog.py extract.py pipeline.py cli.py
common/            brain_client.py   (shared HTTP client; used by Tasks 2 & 3)
data/fallback_docs/ 17 SYNTHETIC doc pages        samples/ emails.json, meetings/, output/ (generated)
tests/ evals/      pytest suite; scored eval cases + runner
README.md DESIGN.md EVALS.md AI_LOG.md .env.example requirements.txt run.sh run_demo.py
```

## Configuration (`.env`, never committed)
See `.env.example`: `ANTHROPIC_API_KEY` (optional), `BRAIN_LLM_MODEL`, `BRAIN_API_URL`, `BRAIN_SOURCE` (`auto|live|fallback`), `BRAIN_SITEMAP_URL`, `BRAIN_MAX_PAGES`, `SOW_HOURLY_RATE`.
`.gitignore` excludes `.env`, `.venv`, databases and crawl caches.

## Known limitations
* Fallback docs are synthetic; evaluation scores therefore measure retrieval *mechanics*, not accuracy on the real docs.
* Live crawl is untested against the real site (selectors in `extract_page` are generic guesses).
* The honesty gate is conservative and phrasing-sensitive: it refuses some answerable questions (4 of 32 answerable eval questions) rather than risk a wrong answer.
* Email classifier is keyword rules (12/20 on a deliberately hard set).
* Hour estimates are catalog assumptions; the hourly rate is a placeholder.
* Doc-update detection runs on demand (`/refresh`), not on a schedule - add a cron job calling `POST /refresh` for that.
* API has no authentication; SQLite is single-process; escalation tickets are stored but nobody is notified.

## Publish to GitHub (you must do this - I have not)
```bash
cd capstone
git init && git add . && git commit -m "Capstone: Knowledge Brain, Inbox Agent, Meeting-to-SOW"
# create an empty repo on github.com, then:
git remote add origin https://github.com/<you>/<repo>.git
git branch -M main && git push -u origin main
```
Before pushing, confirm `git status` does not list `.env`.
