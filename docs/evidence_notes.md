# Evidence notes (working file, not the submission)

All paths relative to `dossier/`. Figures recomputed from the files, not taken from the brief.

## Spend and adoption
| Finding | Evidence |
|---|---|
| Spend $17.3k Jul, $17.9k Aug, $22.3k Sep (avg $19.2k). Matches "$19k". | `vendor_invoices/*` |
| Three vendors, two of them chat tools: Lumen Assist (240 seats × $30 = $7.2k) and Hearth Workspace ($6k flat, "built-in chat assistant"). Duplicate capability. | `vendor_invoices/lumen_*`, `hearth_*` |
| Hearth: 240 provisioned, 41 → 39 → 36 monthly active (15%). Auto-renews 13 Nov 2026 unless notice ≥14 days before, i.e. by 30 Oct 2026. | `vendor_invoices/hearth_workspace_2026-09.txt` |
| Chat assistant active users 130 → 110 → 92 (54% → 38%). Active ≥5 days: 67 → 37. 110 of 240 seats unused all quarter. HR and admin flat at 20%. | `ai_usage_export.csv` |
| ForgeCode overage $1.7k → $2.3k → $6.7k. One person (P005, Platform) used 815M tokens in Sep with a 61-hour session: the weekend runaway loop. That's ≈$4.1k of Sep's overage at $5/M. No spend limit set. | `ai_usage_export.csv`, `vendor_invoices/forgecode_2026-09.txt`, `interview_notes/engineering_lead_ravi_menon.md` |
| Nobody owns spend: CEO guesses, CFO "not sure who signed which", Controller doesn't know who approved the Sep overage. | `interview_notes/ceo_*`, `cfo_*`, `controller_*` |
| Company tools are too slow or blocked at home, so people use personal consumer accounts with client data and CVs (Ayesha, Jonas, Lena, an AP clerk). Nobody told consultants what's allowed. | `interview_notes/consultant_*`, `recruiter_lena_voss.md`, `controller_priya_nair.md` |
| Both incidents were treated as individual mistakes; neither led to a control. Incident 1 (Northgate contract into a personal chatbot) is likely a breach of Northgate 14.1 (no AI provider on Schedule 4); it was told to Northgate only verbally. Corvane 9.3 needs notice within 72h of a suspected disclosure. | `incident_log.md`, `policies/client_data_handling.md` |

## Case A: finance (sample: 780 invoices, Jun to Aug 2026 work)
- Close: first closed day 6 every month, final day 8 to 10 (mean 9.0). The CFO's "6" is the first close. `case_a/close_calendar.csv`
- 224 of 780 invoices (≈75/month) changed between draft and final. Reasons: rate amendment not in rate table 102; pending/unapproved hours 67; milestone not certified 30; duplicate timesheet lines 25. All four can be checked by rules. `case_a/invoices.csv`
- 40 of 94 amendments never reached the rate table. `case_a/contract_amendments.csv` vs `contract_rates.csv`
- 16 credit notes (2.05%), $10,250 written off in a quarter (≈$41k a year). Each had no review note, so finance missed it. Recomputing from source (approved, de-duplicated hours × rate incl. amendments + certified milestones) matches all 764 clean finals and flags all 16 credit-noted invoices. Write-off ≠ the size of the error (e.g. INV-2607-0005 overbilled $45,000, $5,440 written off).

## Case B: HR (sample: 200 screened applicants, 4 quarters)
- Sam: 72 of 81 rejections (89%) have no reason recorded, which breaches hiring policy 2. Lena: 0 missing. `case_b/screening_outcomes.csv`, `policies/hiring_policy.md`
- Disability disclosed: 0 of 7 advanced (vs 26% for "no"). Gender: female 21% vs male 25% advance. n is small. `case_b/applicant_monitoring.csv`
- Sam advanced Westbridge 1 of 1 and Kellner 78%, and calls them "almost always good". The two recruiters use incompatible criteria (Sam's scorecard scores institution and gaps; Lena's checklist does neither). `case_b/scorecard_*.md`, `interview_notes/recruiter_sam_okafor.md`
- Female applicants have career gaps more often (23% vs 11%), so penalising gaps hits them harder.
- The Head of HR wants to "train a model on past hires" from outcomes this biased. Only 25 hires.
- CVs come in 3 sentence templates, with explicit skills lists.

## Case C: proposals
- Log confirms 14 a month, 22.0 senior hours, 23.8% win, $420k average, 18.0 months. `case_c/proposal_log.csv`
- "35% rebuilt" is self-reported (n=18, mean 35, range 17 to 55). Ayesha: "I haven't counted." `case_c/consultant_survey.csv`
- Meridian and Crestline (named competitors of each other) share the folder `Acute Care Group`, and the pricing models hold competitively sensitive notes. Jonas saw Crestline material while searching for Meridian. `case_c/archive/README.txt`, `interview_notes/consultant_jonas_pell.md`
- The fake "34%" benchmark went to Corvane, but the archive holds a real Corvane figure (12% pilot). `case_c/client_deck_excerpt_june.md`, `case_c/archive/sharepoint/Corvane Ministry of Health/corvane_proposal_2026_01.md`
- Partners "skim" before signing. `interview_notes/managing_partner_henrik_alder.md`

## Case D: engineering
- PRs 640 → 915/month, deployments flat at ≈310, rollback rate 5.0% → 9.1%, time to first review 13h → 31h. `case_d/monthly_engineering_baseline.csv`
- Agent-assisted PRs: median 426 lines vs 189, revert/hotfix 10.4% vs 4.1%. `case_d/pull_requests.csv`
- 9 named reviewers do 67% of first reviews. 8 PRs were first-reviewed by their own author.
- Sev 1 and 2: 9 of 18 have no postmortem, which breaches change-management clause 4. auth-service had 8 of 22 incidents, and 9 of 22 incidents were "token expiry". 3 incidents repeat an earlier one. `case_d/incidents.csv`, `policies/change_management_clause.md`
- Incident timelines have out-of-order timestamps (cause found after restore). `case_d/incident_timelines.md`
- VP Eng wants more seats; Ravi says that's not the answer.

## $125k target arithmetic
- Need +$6M/year revenue. The log shows ≈$1.4M won a month ($4.2M over its three months), about $23.9k a month of revenue per won contract.
- An extra win in month m adds ≈$23.9k × (12 − m) inside the year (assumes revenue is recognised evenly over delivery, starting at once).
- Henrik's "+5 points" = 0.7 extra wins/month. From month 3 that is 0.7 × $23.9k × 45 ≈ $0.75M in-year.
- Even +5 wins/month from month 3 (win rate 24% → 60%) gives ≈ $5.4M, still short of $6M, and needs delivery capacity the fixed 90 consultants may not have.
- No figure on consultant utilisation or delivery capacity anywhere in the dossier. Open question.
