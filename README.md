# Invoice check and review triage

Two small tools for the X Group take-home: a pre-send invoice check (Case A, finance) and a pull request triage with postmortem gaps (Case D, engineering). Python 3.10 or newer, standard library only, no model calls.

The dossier is not in this repo. Put its folder at `./dossier` first, then run these from this folder:

```
python3 -m unittest discover -s tests -t .          # 1. tests
python3 run.py finance dossier/case_a                # 2. invoice check   -> out/finance/
python3 run.py engineering dossier/case_d            # 3. review triage   -> out/engineering/
```

Commands 2 and 3 accept any folder with the same file names and columns. Exit code 0 means ok. Exit code 2 means the input has the wrong shape: nothing is written and the reason goes to stderr. Exit code 3 means it ran but quarantined some rows (see `quarantine.csv`). `--as-of YYYY-MM-DD` sets the date postmortem deadlines are judged against.

## What each one does

Finance recomputes every invoice from the source records (approved, de-duplicated hours times the rate in force on the entry date, plus certified milestones due that month) and compares the result with the system draft. It writes `invoice_check.csv` (verdict and reasons), `trace.csv` (every figure with its source record id), `approval_queue.csv` and `summary.json`.

Engineering scores each pull request from metadata (sensitive service, agent-assisted) and puts it in a tier: strict, high or low. It also lists severity 1 and 2 incidents with no postmortem and writes a facts-only draft for each. Outputs are `pr_triage.csv`, `postmortem_gaps.csv`, `postmortem_drafts/` and `summary.json`.

## How I evaluated them

I designed these checks myself; the results are in each `summary.json`.

- Finance: on the 780 sample invoices, does the check flag every invoice that finance changed by hand (224) or that got a credit note later (16), and nothing else? It flags 240 of 240 with no false flags, and its reason codes match finance's own notes 216 times out of 216. The catch is that I read the rules off this sample, so the result shows they explain it and says nothing about unseen data. Edge cases (bad rows, missing rates, non-USD contracts, hostile text) are tested on labelled synthetic data.
- Engineering: do the tiers separate the PRs that get reverted or hotfixed? Revert rates are 13.3% for strict, 7.8% for high and 4.0% for low, against 7.4% overall. AUC is 0.64, and strict plus high covers 58% of PRs and 77% of reverts. Agent-assisted PRs revert 1.9 times as often in other services (7.8% vs 4.0%) and 3.4 times as often in sensitive ones (16.1% vs 4.8%). I changed the rule once after seeing outcomes (size is no longer a risk term), so treat this as descriptive and not as a holdout.
- Postmortems: all 22 timelines parsed. Seven have data issues, such as a cause stamped after the restore or a duration that disagrees with the log. The tool reports them and never corrects them.

## Controls, and why
| Control | Why |
|---|---|
| Amounts use `Decimal` and come from code only; no model anywhere in finance | Audit rule 1 and the CFO's "it can read, it can flag, it doesn't compute" |
| `trace.csv` gives a source id and rate source for every figure | Auditors sample 40 invoices a year and ask for the trail |
| Missing rate, non-USD contract, duplicate invoice id, or any bad input row for a contract: the invoice is `blocked`, never guessed | A wrong number in a financial record is worse than a late one |
| `ApprovalLedger`: preparer cannot approve; an adjustment needs amount, reason and author; approval needs draft + adjustments = computed total | Audit rules 2 and 3 |
| Triage reads metadata only, never code, and has no approve or merge function (tested) | Client code in Schedule 2 cannot leave the client environment; every merge needs a human approver |
| `strict` tier = 2 approvals including the security group; `RESTRICTED_SERVICES` marks client-restricted repos | Change-management clause 2 and 3 |
| Self-reviewed PRs are flagged (8 in the sample) | Clause 1: approver must not be the author |
| Incident text is untrusted: fenced in drafts, never acted on; drafts say TODO (human) for root cause and actions | Free text can carry instructions; a postmortem finding must be owned by a person |
| Bad rows are quarantined and counted; wrong shape stops the run | The slice will meet data I have not seen |

Layout: `xgroup/` code, `tests/`, `data/synthetic/` (labelled SYNTHETIC test data and its generator), `docs/submission.md`, `harness/`.
