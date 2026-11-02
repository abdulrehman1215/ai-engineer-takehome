# X Group: AI engineer take-home

Abdul Rehman Raja. Hours spent: 7 h 20 min (breakdown in `TIMELOG.md`). I built the slices with an AI coding agent; the harness notes are in `harness/`. Paths are relative to `dossier/` unless they start with `out/`, which the repo generates (see README). The weakest points are at the end.

## 1. Diagnosis: why the spend has not paid off

| # | Claim | Evidence |
|---|---|---|
| 1 | Nobody owns the spend, so nothing caps or reviews it. Spend is $17.3k, $17.9k, $22.3k a month (Jul to Sep). One ForgeCode user ran a 61-hour session using 815M tokens and drove September's $6.7k overage. A cap exists in the console and nobody set it. | `vendor_invoices/*`; `ai_usage_export.csv` (P005, Sep); `interview_notes/engineering_lead_ravi_menon.md`; CEO guesses "around 20K" (`ceo_elena_marsh.md`); Controller: "I don't know who approved the ForgeCode overage" (`controller_priya_nair.md`) |
| 2 | Seats were bought, not adopted, and use is falling. Chat assistant active users: 130, 110, 92 of 240 (54% to 38%). Users active 8+ days: 37, 22, 20. 110 seats were never opened in the quarter. Hearth ($6k a month) has 36 to 41 active users of 240 and duplicates the chat tool. | `ai_usage_export.csv`; `vendor_invoices/hearth_workspace_2026-09.txt`, `lumen_assist_2026-09.txt` |
| 3 | The coding agent speeds up the step that was not the bottleneck. PRs rose 640 to 915 a month (+43%) while deployments stayed flat (about 301 to 308), rollbacks went from 5.0% to 9.1%, and first-review wait from 13h to 31h. Agent-assisted PRs are bigger (median 426 vs 189 lines) and revert or hotfix more (10.4% vs 4.1%). DORA's 2024 report found the same direction across the industry. | `case_d/monthly_engineering_baseline.csv`; `case_d/pull_requests.csv`; [DORA 2024](https://cloud.google.com/blog/products/devops-sre/announcing-the-2024-dora-report): as AI adoption increased, "an estimated decrease in delivery throughput by 1.5%, and an estimated reduction in delivery stability by 7.2%" (correlational) |
| 4 | The billing losses come from process breaks that a chat tool cannot fix. 40 of 94 contract amendments never reached the rate table. About 75 invoices a month are changed by hand (224 of 780 in the sample), and 16 more went out wrong and got credit notes. The books close finally on day 9, not 6. | `case_a/contract_amendments.csv` vs `contract_rates.csv`; `out/finance/summary.json`; `case_a/close_calendar.csv` (final day 8 to 10, mean 9.0) |
| 5 | The company tools do not fit the work, so people use personal accounts with client data. An AP clerk pasted a Northgate contract into a consumer chatbot; a second AP colleague does the same; two consultants and one recruiter use personal accounts for transcripts, workshop notes and CVs. Northgate's Schedule 4 lists no AI provider. Both incidents were closed as individual mistakes with no control added. | `incident_log.md`; `interview_notes/controller_priya_nair.md`, `consultant_ayesha_rao.md`, `consultant_jonas_pell.md`, `recruiter_lena_voss.md`; `policies/client_data_handling.md` |
| 6 | Nothing is measured, so nobody can answer the board. The CEO sees use "in Slack"; usage data says otherwise. Several reported figures differ from the files (close time, "40% more PRs" with flat deployments, "35% rebuilt" from 18 self-reports). People's sense of AI speed-ups is also unreliable: in a randomised trial, developers expected AI to cut task time by 24% and it increased it by 19% ([METR, 2025](https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/); 16 developers, one setting, authors say it does not generalise). | `interview_notes/ceo_elena_marsh.md`; `ai_usage_export.csv`; `case_c/consultant_survey.csv` |

In short, the tools went out as seats. Nobody owned them, nobody measured them, and no rule covered client data, so they never got pointed at the few steps where X loses money or trust.

## 2. "AI-native" for X, and the $125k target

Three testable statements (thresholds are my proposals, not benchmarks):

1. Owned and capped. One named owner for AI spend; every usage-billed account has a cap; a seat idle for 60 days is reclaimed. *Test:* owner named by day 7; zero uncapped accounts; seat utilisation (1+ active day a month) from 38% to 70%, or seats cut to match.
2. First pass by code, finish by a named human, in the workflows that cost money. *Test, finance:* 100% of invoices checked before approval; wrong-amount invoices from 2.1% to 1.0% or less; hand-fixed invoices from about 75 to 30 or fewer a month; final close day 9 to 7. *Test, engineering:* every PR triaged on opening; median time to first review 31h to 20h; rollback rate 9.1% to 6.5%; no severity 1 or 2 incident without a postmortem after 10 working days (8 overdue at 26 Sep, the last incident date in the data).
3. Client data stays in approved tools. *Test:* every AI tool used on client or applicant data is on the client's approved list or has written approval; a quarterly sample audit finds zero client data on personal accounts; every external figure in a client deliverable has a checked source before partner sign-off (the "34%" benchmark in Incident 2 had none).

On $125k in 12 months, my answer is no, and AI alone will not close the gap. I expect $100k to about $106k a head. Revenue per head today is $24M / 240, so $125k needs another $6.0M (+25%) with no added heads.

| Lever | In-year effect | Basis |
|---|---|---|
| Win rate +5 points (Managing Partner's own "pays for everything") | +0.7 wins a month, about +$0.75M, so about $103k a head | 14 proposals a month, avg win $420k over 18 months ($23.9k a month per win), wins from month 3, revenue starting the month after signing. `case_c/proposal_log.csv` |
| Win rate +10 points | about +$1.5M, about $106k | same |
| Win rate doubled to 48% | about +$3.6M, about $115k, and needs delivery capacity I have no data on | same |
| Idle seats (110 x $30 x 12), Hearth ($6k x 12), a repeat of September's runaway | about $0.12M a year of cost saving, zero effect on revenue per head | `vendor_invoices/*`, `ai_usage_export.csv` |
| Invoice write-offs | $41k a year, 0.2% of revenue | `interview_notes/cfo_tom_radley.md`; sample `case_a/invoices.csv` |

The CEO said she can live with a small number if it is real (`ceo_elena_marsh.md`). I would give the board about $103k with the measured path above and say $125k is not supported by anything in the files. Confidence: moderate on the arithmetic, low on the win-rate assumption.

## 3. Where to start

Criteria, and why these:

- Evidence in the files, not the leader's claim. The dossier says leader figures are "not necessarily what the files show".
- Safe with deterministic code. No AI provider is approved for client data (Schedule 4), and the CFO wants no model on finance data.
- A baseline I can move in 30 days. A metric already in the dossier.
- Bounded harm, human stays in the loop.
- A leader who will change the process. I am least sure of this one, and it is the assumption that would change my choice (below).

Not used: size of prize in dollars (no cost-per-hour data in the dossier, and the largest figures are self-reported), and "most AI-shaped" (it picks the cases with the most client risk).

| Case | Evidence in files | Safe without a model | 30-day baseline | Bounded harm | Owner will act | Decision |
|---|---|---|---|---|---|---|
| A Finance | High | High | High | High | Mod. to high | Build |
| D Engineering | High | High (metadata only) | High | Medium | Low to mod. | Build |
| B HR | High | Low (CV text, personal data) | Medium | Low | Low to mod. | No model yet |
| C Consulting | Medium | Low (competing clients share a folder) | Low (14 proposals a month is noisy) | Low | Low | No model yet |

What I would do about the two I am not building:

- B, HR, no model for now. One written scorecard per role before applications open (hiring policy #3); a recorded reason on every rejection (one recruiter left 72 of 81 blank); monthly instead of quarterly gender and disability monitoring (0 of 7 disclosed-disability applicants advanced; small sample); gap penalties fall harder on women (23% of female applicants have a career break, 11% of male); stop pasting CVs into personal accounts. Do not train on past hires: only 25 hires, and the past screening is not neutral (one recruiter advanced 13 of 18 applicants from Westbridge or Kellner, 72%, against 21 of 97 others, 22%; the other 5 of 16 against 9 of 69). Revisit a model after two quarters of clean, labelled decisions. `case_b/screening_outcomes.csv`, `case_b/applicant_monitoring.csv`, `case_b/cvs/`, `recruiter_sam_okafor.md`.
- C, Consulting, no archive-wide AI. First separate the Meridian and Crestline folders and set permissions (a conflict clause, and a consultant already saw Crestline material while searching for Meridian). Add a rule that any external figure carries a checked source; the archive holds a real Corvane figure (12% pilot) next to the fake 34%. Then retrieval inside one client's workspace, with partner sign-off. `policies/client_data_handling.md`, `case_c/archive/README.txt`.

The assumption that would change my choice: the Controller and the VP Engineering will change their process. If the VP Engineering holds to "more seats, more speed", D has no owner and I would swap it for the C fixes above, whose owner (the Managing Partner) is exposed to the largest unpriced client risk.

## 4. Controls and slices

Both slices are in the repo; the controls and the reason for each are in `README.md`.

## 5. First 30 days

| When | Scope | Proposed owner | Metric (baseline) |
|---|---|---|---|
| Days 1 to 7 | Name one owner for AI spend. Set a ForgeCode cap. Decide on Hearth before its notice date (30 Oct for the 13 Nov renewal): 36 of 240 seats are active. Tell all staff what is allowed with client data. Ask Legal whether Incident 1 needs written notice to Northgate (clause 14). | CEO's office names owner; CFO proposed | Uncapped usage-billed accounts: 1. Seat utilisation: 38%. |
| Days 8 to 21 | A: run the pre-send check in shadow mode on the next billing run; Controller reviews every flag; preparer and approver logged. Document the change before go-live (audit rule 5). D: triage queue read-only for Platform and Clinical Apps; draft the 9 missing postmortems for owners to finish. | Controller; Platform lead (Ravi Menon) | A: hand-fixed invoices about 75 a month; wrong sent 2.1%; final close day 9.0. D: first review 31h; rollbacks 9.1%; 8 postmortems overdue (at 26 Sep). |
| Days 22 to 30 | Compare with baseline on the new run. Go, change or stop. | CEO's office with owners | same four metrics |

Risks: the billing rules were read from this sample (flag quality on real data is unproven); recruiters and engineers route around the tiers; scope creeps into sending client text to a model; no owner takes the controls.

Stop or change course if:

- (A) flag precision on the new run is under 90% when the Controller reviews it, or any figure cannot be traced to a record.
- (D) agent-assisted PRs do not revert at least 1.5x the human rate on new data, or time to first review does not fall.
- (Either) client-restricted code or data reaches an external service, or the audit objects to the process change.

## 6. Assumptions register

| Assumption | Why | Confidence | Test | If wrong |
|---|---|---|---|---|
| Billing rules (approved hours only, rate in force on entry date, milestones only with certificate) hold on unseen data | Reproduces all 764 clean finals and flags all 16 credit-noted ones | Moderate (rules read from the same sample) | Controller reviews 50 flags from the next run | More shadow time; rules revised |
| `auth-service` and `patient-records` are the "authentication and patient-data" changes of clause 2 | The sample has no path or label for it | Moderate | Security group lists the paths | Strict tier too wide or too narrow |
| Revenue is recognised evenly over delivery months with no capacity limit | Nothing else in the files | Low | Ask Finance for recognition policy and utilisation | $125k is even less reachable |
| No AI provider is approved for client data | Schedule 4 lists none; no other approval in the dossier | High | Legal checks the client schedules | Unlocks the text work in B and C |
| Revert or hotfix is a fair proxy for "went wrong", and agent PRs are riskier because of how they are made, not only what they touch | Agent PRs revert 1.9x as often in other services and 3.4x in sensitive ones | Moderate to low | Compare matched tasks | Tier weights and the whole D case change |

## Where this submission is weakest

- Finance evaluation is partly circular. I read the billing rules off the same sample I scored on, so 100% recall shows the rules explain the data, not that they generalise.
- Engineering score was changed after I saw outcomes, and discriminates only modestly (AUC 0.64). Senior attention to the strict and high tiers covers 58% of PRs and 77% of reverts. Useful for a fast lane (42% of PRs, 4.0% revert), weak as a predictor.
- The second approval in clause 2 cannot be checked from the data, and no cost-per-hour data exists, so I give no dollar value for time saved.
- B and C are analysed, not built, and the $125k verdict leans on one assumption (win rate) I could not test.
