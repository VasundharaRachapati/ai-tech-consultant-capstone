#!/usr/bin/env python
"""One-command demo of all three tasks.

    python run_demo.py            # offline, deterministic (local SYNTHETIC docs), writes samples/output/
    python run_demo.py --live     # try the real Brilliant Directions sitemap first (needs internet)
    python run_demo.py --serve    # just run the Knowledge Brain API on http://127.0.0.1:8000
    python run_demo.py --test     # run the pytest suite, then the demo

Nothing here sends real email or calls any paid API unless ANTHROPIC_API_KEY is set (Brain answers only).
"""
import argparse, json, os, shutil, socket, subprocess, sys, threading, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
try:
    from dotenv import load_dotenv; load_dotenv(ROOT / ".env")
except Exception:
    pass

import httpx, uvicorn
from knowledge_brain.api import create_app
from knowledge_brain.brain import KnowledgeBrain
from common.brain_client import BrainClient
from inbox_agent.agent import InboxAgent
from inbox_agent import simulate
from sow_agent import pipeline

OUT = ROOT / "samples" / "output"
QA = ["How do I import members from a CSV file?", "How do I connect Stripe for payments?",
      "Why does my browser say my site is not secure?", "What is the weather in Paris today?",
      "Does the platform support native iOS apps?", "I want to talk to a human"]


def free_port(preferred=8000):
    with socket.socket() as s:
        return preferred if s.connect_ex(("127.0.0.1", preferred)) != 0 else 0


def start_server(brain, port):
    config = uvicorn.Config(create_app(brain), host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()
    for _ in range(100):
        try:
            if httpx.get(f"http://127.0.0.1:{port}/health", timeout=1).status_code == 200:
                return server
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("Brain API did not start")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true"); ap.add_argument("--serve", action="store_true")
    ap.add_argument("--test", action="store_true")
    a = ap.parse_args()
    if a.test:
        rc = subprocess.call([sys.executable, "-m", "pytest", "-q"], cwd=ROOT)
        if rc: sys.exit(rc)

    db = ROOT / "data" / "brain.db"
    if not a.serve and db.exists():
        db.unlink()                                  # fresh, reproducible demo
    brain = KnowledgeBrain(source_mode="auto" if a.live else "fallback", db_path=db).load()
    port = int(os.getenv("BRAIN_PORT", "8000")) if a.serve else (free_port() or 0)
    if a.serve:
        print(f"Knowledge Brain API on http://127.0.0.1:{port}  (docs: /docs)  source={brain.source}")
        uvicorn.run(create_app(brain), host="127.0.0.1", port=port); return
    port = port or free_port(8765) or 8766
    start_server(brain, port)
    client = BrainClient(base_url=f"http://127.0.0.1:{port}")
    health = client.health()
    print(f"[Task 1] Knowledge Brain API up on :{port} - {health['documents']} docs, source={health['corpus_source']}, mode={health['answer_mode']}")
    if health["corpus_source"] == "fallback":
        print("         NOTE: using the local SYNTHETIC fallback docs, not the real Brilliant Directions Solution Center.")
    shutil.rmtree(OUT, ignore_errors=True); OUT.mkdir(parents=True)

    qa = [client.ask(q) for q in QA]
    (OUT / "brain_qa.json").write_text(json.dumps(qa, indent=1))
    for r in qa:
        print(f"         {r['status']:<21} conf={r['confidence']:<5} {r['question']}")
    print(f"         refresh check: {json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in httpx.post(f'http://127.0.0.1:{port}/refresh').json().items()})}")

    # ---- Task 2 ----
    emails = json.loads((ROOT / "samples" / "emails.json").read_text())
    agent = InboxAgent(client, db_path=":memory:")
    res = simulate.run(agent, emails, OUT / "inbox")
    log = res["log"]
    drafts = {m["email_id"]: dict(m) for m in map(dict, agent.db.execute("SELECT * FROM mails"))}
    (OUT / "inbox" / "drafts.json").write_text(json.dumps(drafts, indent=1))
    from collections import Counter
    dec = Counter(x["decision"] for x in log)
    print(f"[Task 2] processed {len(log)} emails: {dict(dec)}")
    for e in res["events"]:
        if e["category"] == "how_to" and e["kind"] != "streak_reset":
            print(f"         how_to: {e['kind']}: {e['detail'][:100]}")
    # ---- Task 3 ----
    sow_dir = OUT / "sow"
    r = pipeline.run(ROOT / "samples" / "meetings", sow_dir, client)
    s = r["sow"]
    print(f"[Task 3] SOW: {len(s['in_scope'])} in-scope, {len(s['out_of_scope'])} out-of-scope, "
          f"{len(s['needs_clarification'])} need human decision, {s['totals']['total_hours']} h, ${s['totals']['estimated_cost']:,}")
    try:
        pipeline.finalize(sow_dir)
    except pipeline.ApprovalRequired as e:
        print(f"         finalize without approval -> REFUSED ({e})  [human approval gate works]")
    print(f"\nOutputs in {OUT.relative_to(ROOT)}/ . To approve the SOW as a human:\n"
          f"  python -m sow_agent.cli approve --approver \"Your Name\" --ack-open-items && python -m sow_agent.cli finalize")


if __name__ == "__main__":
    main()
