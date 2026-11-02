# Problem map (working file, not the submission)

Figures come from `evidence_notes.md`; paths are relative to `dossier/`.

## Problem statement and key challenges

```mermaid
flowchart TD
    G["CEO promise: AI-native in 12 months<br/>$100k to $125k revenue per head<br/>240 heads, +$6M revenue"]
    R["Rules: no headcount growth, cuts don't count,<br/>no quality loss, no client-contract or audit breach"]
    G --- R

    Q["Board question: what did $19k a month buy?<br/>Nobody can answer"]
    G --> Q

    subgraph WHY["Why the spend hasn't paid off (task 1)"]
        direction TB
        W1["No owner, no spend limit<br/>3 vendors, nobody signed for them<br/>ForgeCode Sep overage $6.7k"]
        W2["Low and falling adoption<br/>Chat active 54% to 38%<br/>Hearth 15% active, renews 13 Nov"]
        W3["Tools not tied to a bottleneck<br/>PRs +43% but deploys flat,<br/>rollbacks 5% to 9%"]
        W4["Shadow AI on personal accounts<br/>client data and CVs leave the company<br/>incidents treated as individual mistakes"]
        W5["Root causes aren't chat problems<br/>amendments never reach the rate table,<br/>archive mixes competing clients"]
        W6["No measurement<br/>CEO sees it 'in Slack'<br/>leaders' figures differ from the files"]
    end
    Q --> WHY

    subgraph CASES["Pick 2 of 4 (task 3)"]
        direction TB
        A["A Finance<br/>75 of 260 invoices a month fixed by hand<br/>close is 9 days, not 6<br/>$41k a year written off"]
        B["B HR<br/>2,280 CVs a quarter, 11 min each<br/>inconsistent recruiters, 0 of 7 disclosed<br/>disability advanced"]
        C["C Consulting<br/>308 senior hours a month<br/>fake benchmark reached a client<br/>Meridian and Crestline share a folder"]
        D["D Engineering<br/>review is the bottleneck, 31h to first review<br/>9 of 22 postmortems missing<br/>agent PRs revert 10.4% vs 4.1%"]
    end
    WHY --> CASES

    subgraph HARD["Non-negotiable constraints"]
        direction TB
        HA["A: code computes amounts, never a model<br/>every figure traces to a record<br/>preparer is not approver"]
        HB["B: human decides every advance or reject<br/>reason recorded and shareable<br/>gender and disability monitoring"]
        HC["C: no cross-client leakage<br/>partner signs off<br/>wrong facts reach clients"]
        HD["D: human approver on every merge<br/>client code stays in client environment<br/>auth and patient data need a second approver"]
    end
    A --- HA
    B --- HB
    C --- HC
    D --- HD

    subgraph OUT["What to deliver"]
        direction TB
        O1["Document: diagnosis, 3 testable AI-native statements,<br/>$125k verdict, case choice, 30-day plan, 5-row register"]
        O2["Repo: 2 thin slices, tested, own evaluation,<br/>README of 1 page, runs in 3 commands"]
        O3["harness/: 2 or more mechanisms and why"]
    end
    CASES --> OUT

    T["Traps<br/>4 hours hard cap, padding is penalised<br/>untraceable numbers count against<br/>slices are run on unseen data<br/>live session may change the situation"]
    OUT --- T
```

## Notes on the map
- The leaders' figures mostly hold up (260 invoices, 14 proposals, 22 hours, $420k, 24% win rate). The gaps are in how they are framed: the books close finally on day 9, not 6; the 40% rise in PRs came with flat deployments and a higher rollback rate; both incidents were closed with no control added; and "35% rebuilt" comes from a survey of 18 people.
- Hearth renews on 13 Nov 2026 unless notice arrives at least 14 days earlier, which is 30 Oct. The dossier is dated 1 Oct 2026, so there is still time to serve notice or cut seats. `vendor_invoices/hearth_workspace_2026-09.txt`
