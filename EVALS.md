# EVALS

All numbers below were produced by running the code in this repo (`python evals/run_evals.py`, `python -m pytest -q`; raw output in `evals/RESULTS.md` / `evals/results.json`). Mode: **offline / extractive, against the 17-page SYNTHETIC fallback corpus.** No LLM, no live docs, no real humans were involved in any score.

## Read these caveats before the numbers
1. **I wrote the corpus, the questions, the emails and the labels.** Scores are optimistic and measure *mechanics*, not real-world accuracy. The Brain has never been evaluated on the real Brilliant Directions docs.
2. **Tuning contamination.** After the first run I changed the Brain's gate once (details below). The main set was used to motivate it, and I had seen the held-out set's *baseline* results before tuning, so the held-out set is no longer a clean test.
3. Human reviewer, customer feedback and "audit" corrections in Task 2 are **scripted simulations**.
4. No model comparison was performed (no LLM available), so none is claimed.

## Summary
| Task | Evaluation | Cases | Result |
|---|---|---|---|
| 1 Brain | Main question set (answerable / unanswerable / human-escalation) | 37 | **34 pass** |
| 1 Brain | Held-out-ish set | 11 | **10 pass** |
| 1 Brain | Other tests (API, escalation lifecycle, update detection, crawler parsing, fallback logic, LLM-path stubs) | 11 | 11 pass |
| 2 Inbox | Classifier on self-authored emails | 77 | 77 correct |
| 2 Inbox | Classifier on a deliberately hard set | 20 | **12 correct** |
| 2 Inbox | Policy/learning/safety tests (streak, reset, enable, sensitive categories, suspension, rollback, re-earn, brain-down, ...) | 23 | 23 pass |
| 2 Inbox | End-to-end simulation over 77 emails | 1 | passes (see below) |
| 3 SOW | Requirement-extraction cases | 25 | 25 pass |
| 3 SOW | Pipeline / approval-gate / budget / failure tests | 19 | 19 pass |

`pytest` total: **199 passed, 4 xfailed** (the 4 xfails are the known Brain misses below, marked `strict` so a future fix is noticed).

## Task 1 - Knowledge Brain
Safety metrics (what matters most for an honest assistant):
* **Fabricated answers on unanswerable questions: 0 / 9 (main) and 0 / 3 (held-out)**. Weather, capital cities, SAP, Kubernetes, WhatsApp, QuickBooks, i18n, etc. all returned `unknown` with no citations.
* Human-escalation phrasing: 3/3 detected; regression case "real estate **agent** profiles" correctly *not* escalated.
* Answerable questions: main 21/24, held-out 7/8 correct *with a citation to the expected page*. **All 4 misses are false "unknown"** (over-cautious), none was a wrong answer: B02 "free plan", B10 "accept credit cards with Stripe", B13 "upgrade mid billing cycle", V01 "sign up without waiting for approval". Cause: words like *accept*, *middle*, *waiting* are absent from the tiny corpus and BM25 has no synonyms.
* The demo also shows phrasing sensitivity: "Why does my browser say my site is not secure?" is answered in the eval set (B07) but refused in `run_demo.py`'s equivalent wording.

History (reported so you can see the tuning):
| Step | Main (37) | Held-out (11) |
|---|---|---|
| First run | 32 (5 false-unknown) | 7 (3 false-unknown + **1 wrong-doc answer**: V11 "mobile app" answered with the Webhooks page because "app" matched "other apps") |
| After change: ignore unseen *generic* words; stricter threshold when a *distinctive unseen* word is present | **34** | **10** |
One regression from that change: B10 now fails ("accept" is unseen). A bug found *before* evaluation by code inspection: the escalation regex matched the bare word "agent" (fixed, case H04 added).

Update detection is tested by copying the docs, then changing one page, adding one and deleting one: `/refresh`-equivalent reports exactly 1 changed / 1 added / 1 removed, new knowledge becomes answerable, removed knowledge becomes `unknown`, and an unchanged refresh reports `reindexed: false`.
**Not tested:** the real network crawl of `support.brilliantdirectories.com` (blocked in the sandbox); only `parse_sitemap`, `extract_page` and `crawl_live` with a fake HTTP session were tested.

## Task 2 - Inbox Agent
* **Classifier:** 77/77 on my own emails (written to be unambiguous, so this is nearly meaningless). On the **hard set of 20** (ambiguous / multi-intent) it gets **12/20**. Misses: H02 refund timing → sales; H04 GDPR question → how_to; H05 "can't log in" → how_to; H06 cancel extra seat → cancellation; H09 "where is my invoice" → how_to; H11 newsletter → feature_request; H15 vague churn threat → other; H18 "can you add a field" → how_to. Rules were not adjusted after seeing these. An LLM classifier is the obvious next step; not built.
* **Policy behaviour (unit tests with a fake Brain):** 19 unchanged ≠ enabled, 20th enables; an edit resets the streak; unknown/low-confidence drafts never count and never auto-send; billing/cancellation/complaint never auto-send even after 30 unchanged; spam archived; learned sign-off / greeting (`{first}` placeholder) / suppressed line are applied to the next draft; 1 bad outcome does not suspend, 2 bad within the window do; suspension resets the streak and forces human review; rollback discards rules learned after enabling; auto-send can be re-earned; bad outcomes from an old epoch don't re-trigger; Brain outage yields a safe holding draft; double-review and reviewing an auto-sent mail are rejected.
* **End-to-end simulation (real Brain API over HTTP in `run_demo.py`, `TestClient` in evals):** 77 emails → 70 needs_review, 4 auto_sent, 3 archived_spam. how_to: 47 emails, 34 eligible (Brain answered with confidence ≥ 0.55), **13 got `unknown` from the Brain** (only 3 were *meant* to be unknown, so ~10 are false-unknowns from the gate). Event trail for how_to: edit learned → streak reset → edit learned (greeting preference change) → streak reset → **auto_send_enabled after 20 unchanged** → audit correction learned → **auto_send_suspended_rolled_back (2 bad of 4 auto-sent)**.
* The scenario is scripted (the reviewer's preferences, which auto-sent mails turn out bad). It proves the machinery works, not that real reviewers/customers behave this way.

## Task 3 - Meeting-to-SOW
* 25 extraction cases: 13 in-scope features, 4 out-of-scope, 2 unmapped, 2 non-requirements, 2 drop requests, 2 constraints - all pass. (One real bug was found earlier by running the pipeline: "Marco's team **needs** staff accounts" was missed by the cue regex; fixed and covered by S10.)
* On the sample meetings: 12 in-scope features (all verified by the Brain against the synthetic docs), 3 out-of-scope (native app, SAP, WhatsApp - Brain returned *unknown* for each), reviews removed by the follow-up, 2 requests not estimated (waitlist, Excel export), constraints updated by the follow-up (budget $18,000 → $16,000, deadline January 31 → February 28). The estimate (173.3 h, $16,464 at a **placeholder** $95/h) **exceeds the $16,000 budget** and the SOW flags this as an open item.
* Approval gate: `finalize` refused with no approval; approval requires acknowledging open items and a non-empty approver; an edit after approval invalidates it; CLI exits with code 2 when refused.
* Limits: extraction is keyword/regex based and only handles the phrasing patterns in the catalog; hour estimates are assumptions, not measurements; a different client's wording would need catalog updates. Not evaluated on any real transcript.

## How to reproduce
```bash
python -m pytest -q          # 199 passed, 4 xfailed
python evals/run_evals.py    # regenerates evals/RESULTS.md
python run_demo.py           # regenerates samples/output/
```
