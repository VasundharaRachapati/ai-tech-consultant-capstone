# AI_LOG

## Tools and process
* **Assistant:** Claude (Anthropic), working in a sandboxed Linux environment with file-editing and shell tools, following a single detailed instruction from the student ("implement all three tasks now, don't fabricate results"). Claude's chat environment was used, not the separate Claude Code CLI.
* The AI wrote essentially all code, tests and documentation in one session. The student's role: set the requirements, supply the brief (not supplied), and must review, run and understand everything before submitting.

## Timeline of what actually happened
1. Inspected environment: no assignment brief in `/mnt/user-data/uploads` (empty); Python 3.12, Node 22; docs site **unreachable** (DNS blocked); no `ANTHROPIC_API_KEY`. Decisions: local synthetic fallback corpus, deterministic offline Brain, optional LLM mode, Python for Task 2.
2. Built Brain (crawler, BM25, gate, API). Smoke test showed a wrongly refused SSL question.
3. Wrote a 37-question eval set *before* tuning. First run 32/37. Wrote an 11-question held-out set and ran a baseline (7/11, including one **wrong-doc answer** for "mobile app").
4. Changed the gate (generic-word filter + stricter threshold for distinctive unseen words) → 34/37 and 10/11. Disclosed the contamination in EVALS.md.
5. Built Inbox Agent. First end-to-end run enabled auto-send too late to exercise suspension; expanded the sample set (69 → 77 emails) and moved a scripted preference change earlier so the whole path (learn → reset → enable → bad outcomes → suspend → rollback) was exercised.
6. Built SOW agent. First run revealed a missed requirement (cue regex didn't match "needs <noun>"); fixed.
7. Wrote 203 tests (199 pass, 4 documented xfail), launcher, evals runner, docs. Verified the CLI approval flow and `uvicorn knowledge_brain.api:app` by actually running them.

## Mistakes the AI made or nearly made (and how they were caught)
* Escalation regex matched the word "agent" (would have opened tickets for "real estate agent" questions) - caught by reading the code, added regression test H04.
* Gate gave a confident wrong answer for "mobile app" (V11) - caught by the held-out set.
* SOW cue regex missed "needs staff accounts" - caught by inspecting pipeline output, not by a test; test S10 added after.
* Demo scenario initially never exercised suspension/rollback - caught by inspecting the event log.

## Things that are NOT verified (do not claim otherwise)
* Live crawl against support.brilliantdirectories.com; the real docs' structure/URLs.
* The Anthropic LLM mode (`BRAIN_LLM_MODEL` default `claude-sonnet-4-5` is an unverified guess - check your account) and the model's actual answer quality.
* Anything with real humans, real email, real customers.
* That the original brief's file names/format/language requirements are met (brief unseen).
* GitHub submission: **not performed**.

## Prompt summary (this session)
Single instruction asking to inspect the brief, implement three tasks with ≥20 evals each, produce README/DESIGN/EVALS/AI_LOG, a one-command demo, tests, no fabricated results, no claim of GitHub submission.

## Student reflections (fill in before submitting)
* What I understood / changed myself:
* What I would do differently:
* Where AI output was wrong and I corrected it:
