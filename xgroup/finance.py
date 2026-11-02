"""Case A: check invoices before they go out.

For each invoice, work out what the source records support (approved timesheet hours times the
rate in force on the entry date, plus certified milestones due that month) and compare it with the
system draft. Code does all the arithmetic and every figure keeps the id of its source record.
No model is used.

The billing rules were read off the sample (see docs/submission.md):
  - only `approved` timesheet lines are billable
  - a line with the same employee, contract, date, role and hours as an earlier one is a duplicate
  - the rate is the latest entry in contract_rates or contract_amendments on or before the entry date
  - a milestone is billed in its due month, and only when a certificate is on file
"""
import json
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

from . import io

CENT = Decimal("0.01")
APPROVED, PENDING, REJECTED = "approved", "pending", "rejected"

REASONS = {
    "rate_amendment_not_in_table": "an amendment changed the rate but contract_rates still has the old one",
    "pending_hours": "draft includes timesheet hours not yet approved",
    "duplicate_timesheet": "draft includes a line repeated in the timesheets",
    "uncertified_milestone": "draft bills a milestone with no certificate on file",
    "no_source_records": "draft has an amount but no source record supports it",
    "unexplained_difference": "draft differs from source records and no known cause accounts for it",
}

# Finance's free-text review notes (in the sample only), mapped to the reason codes used here.
NOTE_TO_REASON = {
    "Rate per amendment not in rate table; recalculated": "rate_amendment_not_in_table",
    "Amended rate applied after checking client email": "rate_amendment_not_in_table",
    "Pending hours taken out, resubmitted next cycle": "pending_hours",
    "Removed unapproved timesheet hours": "pending_hours",
    "Milestone certificate missing, removed from invoice": "uncertified_milestone",
    "Double-entered hours, one line deleted": "duplicate_timesheet",
    "Duplicate timesheet entry removed": "duplicate_timesheet",
}

SCHEMAS = {
    "contracts.csv": {"contract_id": io.text, "currency": io.text},
    "contract_rates.csv": {"contract_id": io.text, "role": io.text,
                           "rate_usd_per_hour": io.non_negative_decimal,
                           "effective_from": io.iso_date},
    "contract_amendments.csv": {"amendment_id": io.text, "contract_id": io.text, "role": io.text,
                                "effective_date": io.iso_date,
                                "new_rate_usd_per_hour": io.non_negative_decimal},
    "timesheets.csv": {"timesheet_id": io.text, "entry_date": io.iso_date, "month": io.text,
                       "employee_id": io.text, "contract_id": io.text, "role": io.text,
                       "hours": io.non_negative_decimal,
                       "approval_status": io.choice(APPROVED, PENDING, REJECTED)},
    "milestones.csv": {"contract_id": io.text, "milestone": io.text, "due_month": io.text,
                       "amount_usd": io.non_negative_decimal,
                       "certificate_on_file": io.choice("Y", "N")},
    "invoices.csv": {"invoice_id": io.text, "work_month": io.text, "contract_id": io.text,
                     "system_draft_total_usd": io.non_negative_decimal},
}


@dataclass
class Line:
    source_type: str          # timesheet | milestone
    source_id: str
    source_file: str
    detail: str
    hours: Decimal | None
    rate: Decimal | None
    rate_source: str
    amount: Decimal           # what the draft would bill for this line
    billable_amount: Decimal  # what the source records support
    reason: str = ""          # why billable_amount differs from amount


@dataclass
class Result:
    invoice_id: str
    contract_id: str
    work_month: str
    draft_total: Decimal
    expected_total: Decimal | None
    verdict: str              # ok | flag | blocked
    reasons: list = field(default_factory=list)
    blocked_because: str = ""
    lines: list = field(default_factory=list)

    @property
    def delta(self):
        return None if self.expected_total is None else self.draft_total - self.expected_total


@dataclass
class Inputs:
    tables: dict
    quarantine: list


def load(folder):
    tables, quarantine = {}, []
    for name, schema in SCHEMAS.items():
        rows, bad = io.read_table(folder, name, schema)
        tables[name], quarantine = rows, quarantine + bad
    return Inputs(tables, quarantine)


def _money(x):
    return x.quantize(CENT)


class RateBook:
    """Rate in force for (contract, role, date), with the id of the record that sets it."""

    def __init__(self, rates, amendments):
        self.table, self.full = defaultdict(list), defaultdict(list)
        for r in rates:
            entry = (r["effective_from"], 0, r["rate_usd_per_hour"],
                     f"contract_rates.csv:{r['contract_id']}/{r['role']}@{r['effective_from']}")
            self.table[(r["contract_id"], r["role"])].append(entry)
            self.full[(r["contract_id"], r["role"])].append(entry)
        for a in amendments:
            entry = (a["effective_date"], 1, a["new_rate_usd_per_hour"],
                     f"contract_amendments.csv:{a['amendment_id']}")
            self.full[(a["contract_id"], a["role"])].append(entry)

    @staticmethod
    def _pick(entries, on):
        live = [e for e in entries if e[0] <= on]
        return max(live, key=lambda e: (e[0], e[1])) if live else None

    def in_force(self, contract, role, on):
        return self._pick(self.full.get((contract, role), []), on)

    def in_table(self, contract, role, on):
        return self._pick(self.table.get((contract, role), []), on)


def _timesheet_lines(rows, book):
    """Lines for one contract-month. Returns (lines, blocked_because)."""
    lines, seen = [], set()
    for t in sorted(rows, key=lambda r: r["timesheet_id"]):
        key = (t["employee_id"], t["contract_id"], t["entry_date"], t["role"], t["hours"])
        duplicate = key in seen
        seen.add(key)
        live = book.in_force(t["contract_id"], t["role"], t["entry_date"])
        if live is None:
            return lines, f"no rate for {t['contract_id']}/{t['role']} on {t['entry_date']} ({t['timesheet_id']})"
        tabled = book.in_table(t["contract_id"], t["role"], t["entry_date"])
        draft_rate = tabled[2] if tabled else live[2]   # what a table-driven draft bills
        reason = ""
        if duplicate:
            reason = "duplicate_timesheet"
        elif t["approval_status"] == PENDING:
            reason = "pending_hours"
        elif t["approval_status"] == REJECTED:
            reason = ""   # the sample's draft already leaves rejected hours out (12 of 12), so no cause to flag
        elif draft_rate != live[2]:
            reason = "rate_amendment_not_in_table"
        in_draft = t["approval_status"] != REJECTED
        billable = Decimal(0) if (reason in ("duplicate_timesheet", "pending_hours")
                                  or t["approval_status"] == REJECTED) else t["hours"] * live[2]
        lines.append(Line(
            "timesheet", t["timesheet_id"], "timesheets.csv",
            f"{t['entry_date']} {t['role']} {t['employee_id']} {t['approval_status']}",
            t["hours"], live[2], live[3],
            _money(t["hours"] * draft_rate) if in_draft else Decimal("0.00"), _money(billable), reason))
    return lines, ""


def _milestone_lines(rows):
    lines = []
    for m in rows:
        certified = m["certificate_on_file"] == "Y"
        lines.append(Line(
            "milestone", f"{m['contract_id']}/{m['milestone']}", "milestones.csv",
            f"due {m['due_month']} certificate={m['certificate_on_file']}",
            None, None, f"milestones.csv:{m['contract_id']}/{m['milestone']}",
            _money(m["amount_usd"]), _money(m["amount_usd"]) if certified else Decimal("0.00"),
            "" if certified else "uncertified_milestone"))
    return lines


def check(inputs):
    """Return a Result per invoice, plus contract-months that have source records but no invoice."""
    t = inputs.tables
    book = RateBook(t["contract_rates.csv"], t["contract_amendments.csv"])
    contracts = {c["contract_id"]: c for c in t["contracts.csv"]}
    ts_by, ms_by = defaultdict(list), defaultdict(list)
    for r in t["timesheets.csv"]:
        ts_by[(r["contract_id"], r["month"])].append(r)
    for r in t["milestones.csv"]:
        ms_by[(r["contract_id"], r["due_month"])].append(r)

    # A quarantined row on a contract blocks all of its invoices, since its numbers can't be trusted.
    tainted = {q.row.get("contract_id", "").strip() for q in inputs.quarantine} - {""}
    tainted_unknown = any(not q.row.get("contract_id", "").strip() for q in inputs.quarantine
                          if q.file != "invoices.csv")

    results, seen_ids, invoiced = [], set(), set()
    for inv in t["invoices.csv"]:
        key = (inv["contract_id"], inv["work_month"])
        invoiced.add(key)
        res = Result(inv["invoice_id"], inv["contract_id"], inv["work_month"],
                     inv["system_draft_total_usd"], None, "blocked")
        results.append(res)
        if inv["invoice_id"] in seen_ids:
            res.blocked_because = "duplicate invoice_id"
            continue
        seen_ids.add(inv["invoice_id"])
        contract = contracts.get(inv["contract_id"])
        if contract is None:
            res.blocked_because = f"contract {inv['contract_id']} not in contracts.csv"
            continue
        if contract["currency"].upper() != "USD":
            res.blocked_because = f"currency {contract['currency']} not supported"
            continue
        if inv["contract_id"] in tainted or tainted_unknown:
            res.blocked_because = "an input row for this contract failed validation (see quarantine.csv)"
            continue
        lines, why = _timesheet_lines(ts_by.get(key, []), book)
        if why:
            res.blocked_because = why
            continue
        lines += _milestone_lines(ms_by.get(key, []))
        res.lines = lines
        res.expected_total = _money(sum((l.billable_amount for l in lines), Decimal(0)))
        res.draft_total = _money(inv["system_draft_total_usd"])
        delta = res.draft_total - res.expected_total
        if delta == 0:
            res.verdict = "ok"
            continue
        res.verdict = "flag"
        # Explain the difference line by line. The draft total is rebuilt from the same lines.
        explained = Decimal(0)
        for l in lines:
            if l.reason:
                explained += l.amount - l.billable_amount
                if l.reason not in res.reasons:
                    res.reasons.append(l.reason)
        if not lines:
            res.reasons.append("no_source_records")
        elif explained != delta:
            res.reasons.append("unexplained_difference")
    missing = sorted(k for k, rows in ts_by.items()
                     if k not in invoiced and any(r["approval_status"] == APPROVED for r in rows))
    return results, missing


# Approval

class ApprovalError(Exception):
    pass


class ApprovalLedger:
    """Tracks who prepared, adjusted and approved each invoice.

    The preparer can't approve their own invoice, and every adjustment needs an amount, a reason and
    an author. An invoice is approved only when the draft plus its adjustments equals the computed total.
    """

    def __init__(self):
        self.prepared, self.adjustments, self.approved = {}, defaultdict(list), {}
        self.events = []

    def prepare(self, invoice_id, preparer):
        if not preparer.strip():
            raise ApprovalError("preparer required")
        self.prepared[invoice_id] = preparer
        self.events.append(("prepared", invoice_id, preparer, ""))

    def adjust(self, invoice_id, amount, reason, by):
        if not (reason or "").strip() or not (by or "").strip():
            raise ApprovalError("an adjustment needs a reason and who made it")
        amount = Decimal(amount)
        self.adjustments[invoice_id].append((amount, reason.strip(), by.strip()))
        self.events.append(("adjusted", invoice_id, by, f"{amount} {reason.strip()}"))

    def approve(self, result, approver):
        inv = result.invoice_id
        if result.verdict == "blocked":
            raise ApprovalError(f"{inv} is blocked: {result.blocked_because}")
        if inv not in self.prepared:
            raise ApprovalError(f"{inv} has no recorded preparer")
        if not approver.strip() or approver.strip() == self.prepared[inv]:
            raise ApprovalError(f"{inv}: approver must be a different person from the preparer")
        final = result.draft_total + sum((a for a, _, _ in self.adjustments[inv]), Decimal(0))
        if final != result.expected_total:
            raise ApprovalError(
                f"{inv}: draft {result.draft_total} with adjustments is {final}, "
                f"source records support {result.expected_total}")
        self.approved[inv] = approver
        self.events.append(("approved", inv, approver, str(final)))


# Evaluation

def evaluate(results, invoices):
    """Score the check against the sample's ground truth, if those columns exist.

    A wrong draft is one finance changed before sending (final differs from draft). A wrong sent
    invoice is one that got a credit note afterwards. I read the billing rules off this same sample,
    so a good score here shows the rules explain the data and says nothing about unseen data.
    The tests cover the edge cases.
    """
    cols = {"final_invoiced_total_usd", "status", "finance_review_note"}
    if not invoices or not cols <= set(invoices[0]):
        return {"available": False, "note": "ground-truth columns absent in this data"}
    by_id = {i["invoice_id"]: i for i in invoices}
    computable = [r for r in results if r.verdict != "blocked"]
    hand_fixed = {r.invoice_id for r in computable
                  if Decimal(by_id[r.invoice_id]["final_invoiced_total_usd"]) != r.draft_total}
    credited = {r.invoice_id for r in computable if by_id[r.invoice_id]["status"] == "credit_note_issued"}
    flagged = {r.invoice_id for r in computable if r.verdict == "flag"}
    wrong = hand_fixed | credited

    wrong_sent = {r.invoice_id for r in computable
                  if r.expected_total != _money(Decimal(by_id[r.invoice_id]["final_invoiced_total_usd"]))}
    reason_hits = reason_total = 0
    for r in computable:
        mapped = NOTE_TO_REASON.get(by_id[r.invoice_id]["finance_review_note"])
        if mapped:
            reason_total += 1
            reason_hits += mapped in r.reasons
    caught = sum((r.draft_total - r.expected_total for r in computable
                  if r.invoice_id in credited and r.draft_total > r.expected_total), Decimal(0))
    div = lambda a, b: round(a / b, 4) if b else None
    return {
        "available": True,
        "invoices_checked": len(computable),
        "wrong_drafts_known": len(wrong),
        "flagged": len(flagged),
        "recall_wrong_drafts": div(len(flagged & wrong), len(wrong)),
        "precision_flags": div(len(flagged & wrong), len(flagged)),
        "hand_fixed": len(hand_fixed),
        "hand_fixed_flagged": len(flagged & hand_fixed),
        "credit_noted": len(credited),
        "credit_noted_flagged": len(flagged & credited),
        "sent_invoices_with_final_not_equal_expected": len(wrong_sent),
        "sent_wrong_matches_credit_notes": wrong_sent == credited,
        "reason_agreement": div(reason_hits, reason_total),
        "reason_notes_compared": reason_total,
        "overbilled_usd_on_credit_noted": str(_money(caught)),
        "limit": "rules were read from this sample; this shows they explain it, not that they generalise",
    }


# Run

def run(data_dir, out_dir):
    """Write the review outputs. Returns (summary, exit_code); the code is 3 if any input row was quarantined."""
    inputs = load(data_dir)
    results, unbilled = check(inputs)
    out = Path(out_dir)

    queue_rank = {"blocked": 0, "flag": 1, "ok": 2}
    ordered = sorted(results, key=lambda r: (queue_rank[r.verdict], -abs(r.delta or 0), r.invoice_id))
    io.write_csv(out / "invoice_check.csv",
                 ["invoice_id", "contract_id", "work_month", "verdict", "draft_total_usd",
                  "expected_total_usd", "delta_usd", "reasons", "blocked_because"],
                 [{"invoice_id": r.invoice_id, "contract_id": r.contract_id, "work_month": r.work_month,
                   "verdict": r.verdict, "draft_total_usd": r.draft_total,
                   "expected_total_usd": "" if r.expected_total is None else r.expected_total,
                   "delta_usd": "" if r.delta is None else r.delta,
                   "reasons": ";".join(r.reasons), "blocked_because": r.blocked_because}
                  for r in ordered])
    io.write_csv(out / "trace.csv",
                 ["invoice_id", "source_type", "source_id", "source_file", "detail", "hours",
                  "rate_usd_per_hour", "rate_source", "draft_amount_usd", "supported_amount_usd", "exclusion_reason"],
                 [{"invoice_id": r.invoice_id, "source_type": l.source_type, "source_id": l.source_id,
                   "source_file": l.source_file, "detail": l.detail, "hours": l.hours,
                   "rate_usd_per_hour": l.rate, "rate_source": l.rate_source,
                   "draft_amount_usd": l.amount, "supported_amount_usd": l.billable_amount,
                   "exclusion_reason": l.reason}
                  for r in results for l in r.lines])
    io.write_csv(out / "approval_queue.csv",
                 ["invoice_id", "verdict", "draft_total_usd", "expected_total_usd", "reasons",
                  "preparer", "approver", "adjustment_amount_usd", "adjustment_reason", "adjusted_by"],
                 [{"invoice_id": r.invoice_id, "verdict": r.verdict, "draft_total_usd": r.draft_total,
                   "expected_total_usd": "" if r.expected_total is None else r.expected_total,
                   "reasons": ";".join(r.reasons)} for r in ordered if r.verdict != "ok"])
    io.write_csv(out / "quarantine.csv", ["file", "line", "reason"],
                 [{"file": q.file, "line": q.line, "reason": q.reason} for q in inputs.quarantine])

    raw_invoices = _raw_invoices(data_dir)
    counts = {v: sum(r.verdict == v for r in results) for v in ("ok", "flag", "blocked")}
    reason_counts = defaultdict(int)
    for r in results:
        for x in r.reasons:
            reason_counts[x] += 1
    summary = {
        "invoices": len(results), **counts,
        "reasons": dict(sorted(reason_counts.items())),
        "quarantined_rows": len(inputs.quarantine),
        "contract_months_with_hours_but_no_invoice": [f"{c}/{m}" for c, m in unbilled],
        "evaluation": _safe_evaluate(results, raw_invoices),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary, (3 if inputs.quarantine else 0)


def _safe_evaluate(results, invoices):
    try:
        return evaluate(results, invoices)
    except (ArithmeticError, KeyError, ValueError) as exc:   # ground truth is optional and may be malformed
        return {"available": False, "note": f"ground truth unusable: {exc}"}


def _raw_invoices(folder):
    import csv
    with open(Path(folder) / "invoices.csv", newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))
