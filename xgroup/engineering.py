"""Case D: pull request triage and postmortem gaps.

Two jobs, both advisory and both done in plain code.

1. Triage. Score each pull request from metadata only (service, agent-assisted) and route it to a
   tier. The tool never approves or merges anything and never reads code, so repositories in
   client-controlled environments can be included.
2. Postmortems. Find severity 1 and 2 incidents with no postmortem (clause 4 gives ten working
   days) and write a draft that holds only facts, for a person to finish.

Assumptions, also listed in docs/submission.md:
  - `auth-service` and `patient-records` stand in for "authentication, authorisation or
    patient-data handling" in clause 2. The sample has no path or label for that.
  - RESTRICTED_SERVICES is empty because the sample has no Schedule 2 list. Set it per client.
"""
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from statistics import median

from . import io

SECURITY_SENSITIVE = {"auth-service", "patient-records"}
RESTRICTED_SERVICES = set()
LARGE_LINES = 500
SPLIT_LINES = 800
POSTMORTEM_WORKING_DAYS = 10

PR_SCHEMA = {
    "pr_id": io.text, "month": io.text, "team": io.text, "author_id": io.text,
    "agent_assisted": io.choice("Y", "N"), "lines_changed": io.non_negative_decimal,
    "service": io.text, "first_reviewer_id": io.optional_text,
    "merged": io.choice("Y", "N"), "reverted_or_hotfixed": io.choice("Y", "N"),
}
INCIDENT_SCHEMA = {
    "incident_id": io.text, "date": io.iso_date, "service": io.text,
    "severity": io.choice("1", "2", "3", "4"), "duration_minutes": io.non_negative_decimal,
    "root_cause_category": io.optional_text, "postmortem_written": io.choice("Y", "N"),
    "repeat_of": io.optional_text, "related_pr": io.optional_text,
}


def _optional_hours(v):
    v = (v or "").strip()
    return None if not v else io.non_negative_decimal(v)


@dataclass
class Triage:
    pr_id: str
    risk_score: int
    tier: str
    required_approvals: int
    security_approver: bool
    reviewer_pool: str
    split_suggested: bool
    flags: list = field(default_factory=list)
    why: str = ""


def score(pr):
    """Risk score 0..3 from metadata: sensitive service 2, agent-assisted 1.

    Size is left out on purpose. An earlier version added a point for 500+ lines, but on the sample
    large and small agent-assisted PRs revert at the same rate (7.8% each), so size only affects review
    effort (see `large_change` and `split_suggested`). I changed the rule after looking at outcomes,
    so read the evaluation as descriptive, not as a holdout.
    """
    return (2 if pr["service"] in SECURITY_SENSITIVE else 0) + (1 if pr["agent_assisted"] == "Y" else 0)


def triage(pr):
    s = score(pr)
    sensitive = pr["service"] in SECURITY_SENSITIVE
    flags = []
    if pr["first_reviewer_id"] and pr["first_reviewer_id"] == pr["author_id"]:
        flags.append("self_review")
    if pr["service"] in RESTRICTED_SERVICES:
        flags.append("client_restricted_no_external_services")
    if pr["lines_changed"] >= LARGE_LINES:
        flags.append("large_change")
    if sensitive:
        tier, approvals, pool = "strict", 2, "senior+security_group"
    elif s >= 1:
        tier, approvals, pool = "high", 1, "senior"
    else:
        tier, approvals, pool = "low", 1, "any_qualified"
    parts = []
    if sensitive:
        parts.append(f"{pr['service']} is security-sensitive (second approver from security group)")
    if pr["agent_assisted"] == "Y":
        parts.append("agent-assisted")
    if pr["lines_changed"] >= LARGE_LINES:
        parts.append(f"{int(pr['lines_changed'])} lines (slower to review)")
    return Triage(pr["pr_id"], s, tier, approvals, sensitive, pool,
                  pr["lines_changed"] >= SPLIT_LINES, flags, "; ".join(parts) or "small human-written change")


def _rate(rows):
    return round(sum(r["reverted_or_hotfixed"] == "Y" for r in rows) / len(rows), 4) if rows else None


def auc(by_score):
    """AUC of the integer risk score for the revert label, ties count half. by_score: {score: (reverts, total)}."""
    pos = sum(r for r, _ in by_score.values())
    neg = sum(t - r for r, t in by_score.values())
    if not pos or not neg:
        return None
    wins = 0.0
    for s, (r, _t) in by_score.items():
        for s2, (r2, t2) in by_score.items():
            wins += r * (t2 - r2) * (1.0 if s > s2 else 0.5 if s == s2 else 0.0)
    return round(wins / (pos * neg), 4)


def evaluate_triage(prs, triaged):
    """Do the tiers point review effort at the changes that go wrong? Retrospective, on the sample.

    The rules came from policy and from reading the data once, not from fitting, but this is still
    not a clean holdout. Months are reported separately so you can see whether the pattern holds in each.
    """
    by_id = {t.pr_id: t for t in triaged}
    tiers = defaultdict(list)
    bands = defaultdict(lambda: [0, 0])
    for p in prs:
        t = by_id[p["pr_id"]]
        tiers[t.tier].append(p)
        bands[t.risk_score][1] += 1
        bands[t.risk_score][0] += p["reverted_or_hotfixed"] == "Y"
    reverts = sum(p["reverted_or_hotfixed"] == "Y" for p in prs)
    attention = [p for p in prs if by_id[p["pr_id"]].tier in ("strict", "high")]
    attention_reverts = sum(p["reverted_or_hotfixed"] == "Y" for p in attention)
    low = tiers.get("low", [])
    per_month = {}
    for m in sorted({p["month"] for p in prs}):
        rows = [p for p in prs if p["month"] == m]
        top = [p for p in rows if by_id[p["pr_id"]].tier in ("strict", "high")]
        rest = [p for p in rows if by_id[p["pr_id"]].tier not in ("strict", "high")]
        per_month[m] = {"strict_high_revert_rate": _rate(top), "other_revert_rate": _rate(rest), "prs": len(rows)}
    def cell(rows):
        return {"prs": len(rows), "revert_rate": _rate(rows)}
    agent_vs_human = {
        name: {"agent": cell([p for p in prs if p["agent_assisted"] == "Y" and (p["service"] in SECURITY_SENSITIVE) == sens]),
               "human": cell([p for p in prs if p["agent_assisted"] == "N" and (p["service"] in SECURITY_SENSITIVE) == sens])}
        for name, sens in (("sensitive_services", True), ("other_services", False))}
    reviewed = [p for p in prs if p["first_reviewer_id"]]
    load = defaultdict(int)
    for p in reviewed:
        load[p["first_reviewer_id"]] += 1
    top_n = sorted(load.values(), reverse=True)[:9]
    low_by_top = sum(1 for p in reviewed if by_id[p["pr_id"]].tier == "low"
                     and load[p["first_reviewer_id"]] in top_n)
    return {
        "prs": len(prs), "base_revert_rate": _rate(prs),
        "revert_rate_by_tier": {k: {"prs": len(v), "revert_rate": _rate(v)} for k, v in sorted(tiers.items())},
        "revert_rate_by_score": {str(k): {"prs": v[1], "revert_rate": round(v[0] / v[1], 4)}
                                 for k, v in sorted(bands.items())},
        "auc_risk_score": auc({k: tuple(v) for k, v in bands.items()}),
        "senior_attention_share_of_prs": round(len(attention) / len(prs), 4) if prs else None,
        "senior_attention_share_of_reverts": round(attention_reverts / reverts, 4) if reverts else None,
        "low_tier_revert_rate": _rate(low),
        "agent_vs_human_revert_rate": agent_vs_human,
        "per_month": per_month,
        "scenario_low_tier_reviews_by_busiest_nine": low_by_top,
        "scenario_note": "reviews by the nine busiest reviewers that were low-tier: an upper bound on what could "
                         "move to other reviewers if they have capacity. Not measured.",
        "limit": "metadata only; revert/hotfix is a proxy for 'went wrong'; not a clean holdout",
    }


def controls_report(prs, triaged):
    by_id = {t.pr_id: t for t in triaged}
    strict = [p for p in prs if by_id[p["pr_id"]].tier == "strict"]
    return {
        "self_reviewed_prs": [p["pr_id"] for p in prs if "self_review" in by_id[p["pr_id"]].flags],
        "strict_prs": len(strict),
        "strict_prs_merged": sum(p["merged"] == "Y" for p in strict),
        "second_approver_verifiable": False,
        "note": "the sample records only the first reviewer, so the security-group second approval "
                "required by clause 2 cannot be checked from this data",
    }


# Postmortems

def add_working_days(start, n):
    d = start
    while n > 0:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


HEAD = re.compile(r"^## (INC-[\w-]+):\s*(.+?)\s*$")
EVENT = re.compile(r"^- (\d{1,2}):(\d{2}) (.+?)\s*$")
SEV = re.compile(r"^- Severity (\d+), duration (\d+) minutes\s*$")


def parse_timelines(path):
    """{incident_id: {"service", "events": [(minutes, text)], "severity", "duration"}}. Text stays verbatim."""
    out, cur = {}, None
    p = Path(path)
    if not p.is_file():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        h = HEAD.match(line)
        if h:
            cur = out[h.group(1)] = {"service": h.group(2), "events": [], "severity": None, "duration": None}
            continue
        if cur is None:
            continue
        s = SEV.match(line)
        if s:
            cur["severity"], cur["duration"] = int(s.group(1)), int(s.group(2))
            continue
        e = EVENT.match(line)
        if e and int(e.group(1)) < 24 and int(e.group(2)) < 60:
            cur["events"].append((int(e.group(1)) * 60 + int(e.group(2)), e.group(3)))
    return out


def _find(events, prefix):
    for m, text in events:
        if text.lower().startswith(prefix):
            return m
    return None


def timeline_facts(tl):
    """Derived minutes and anomalies for one parsed timeline. Never invents a missing time."""
    if not tl or not tl["events"]:
        return {"anomalies": ["no timeline found"]}
    ev = tl["events"]
    alert, ack = _find(ev, "alert"), _find(ev, "on-call acknowledges")
    cause, restored = _find(ev, "suspected cause"), _find(ev, "service restored")
    facts, anomalies = {}, []
    wrap = lambda a, b: b - a + (1440 if b < a else 0)
    if alert is not None and ack is not None:
        facts["minutes_to_acknowledge"] = wrap(alert, ack)
    if alert is not None and restored is not None:
        facts["minutes_alert_to_restore"] = wrap(alert, restored)
    if alert is not None and cause is not None:
        facts["minutes_to_suspected_cause"] = wrap(alert, cause)
    if cause is not None and restored is not None and wrap(alert or 0, cause) > wrap(alert or 0, restored):
        anomalies.append("suspected cause is stamped after service restored (timestamps out of order)")
    if tl["duration"] is not None and "minutes_alert_to_restore" in facts \
            and facts["minutes_alert_to_restore"] != tl["duration"]:
        anomalies.append(f"timeline gives {facts['minutes_alert_to_restore']} min alert to restore; "
                         f"recorded duration is {tl['duration']} min")
    for need, label in ((alert, "alert"), (ack, "acknowledgement"), (cause, "suspected cause"), (restored, "restore")):
        if need is None:
            anomalies.append(f"no {label} event")
    facts["anomalies"] = anomalies
    return facts


def _fence(text):
    return text.replace("```", "'''")


def draft_postmortem(inc, tl, facts, pr, due, status, repeat_row):
    hh = lambda m: f"{m // 60:02d}:{m % 60:02d}"
    lines = [
        f"# DRAFT postmortem: {inc['incident_id']} ({inc['service']})", "",
        "> Facts below are copied from the incident log and timeline. Nothing here is a finding.",
        "> Root cause, impact and actions must be written and signed by the incident owner. Not reviewed.", "",
        "| Field | Value (source) |", "|---|---|",
        f"| Date | {inc['date']} (incidents.csv) |",
        f"| Severity | {inc['severity']} (incidents.csv) |",
        f"| Recorded duration | {int(inc['duration_minutes'])} min (incidents.csv) |",
        f"| Recorded root-cause category | {_fence(inc['root_cause_category'] or 'not recorded')} (incidents.csv) |",
        f"| Postmortem due | {due} ({POSTMORTEM_WORKING_DAYS} working days, change_management_clause.md #4) |",
        f"| Status | {status} |",
    ]
    if pr:
        lines.append(f"| Related PR | {pr['pr_id']}: {'agent-assisted' if pr['agent_assisted'] == 'Y' else 'human-written'}, "
                     f"{int(pr['lines_changed'])} lines, service {pr['service']}, first reviewer "
                     f"{pr['first_reviewer_id'] or 'none recorded'} (pull_requests.csv) |")
    elif inc["related_pr"]:
        lines.append(f"| Related PR | {inc['related_pr']} (not found in pull_requests.csv) |")
    if inc["repeat_of"]:
        prior = "postmortem written" if repeat_row and repeat_row["postmortem_written"] == "Y" \
            else "NO postmortem written" if repeat_row else "not found in incidents.csv"
        lines.append(f"| Repeat of | {inc['repeat_of']}: {prior} (incidents.csv) |")
    lines += ["", "## Derived from the timeline"]
    for k in ("minutes_to_acknowledge", "minutes_to_suspected_cause", "minutes_alert_to_restore"):
        if k in facts:
            lines.append(f"- {k.replace('_', ' ')}: {facts[k]}")
    for a in facts.get("anomalies", []):
        lines.append(f"- DATA ISSUE: {a}")
    lines += ["", "## Timeline as recorded (verbatim, untrusted text)", "```"]
    if tl:
        lines += [_fence(f"{hh(m)} {t}") for m, t in tl["events"]]
    else:
        lines.append("(none)")
    lines += ["```", ""]
    for h in ("Impact", "Root cause", "What went well", "What went badly", "Actions (owner, due date)"):
        lines += [f"## {h}", "TODO (human)", ""]
    return "\n".join(lines)


def postmortem_gaps(incidents, timelines, prs_by_id, as_of):
    by_id = {i["incident_id"]: i for i in incidents}
    rows, drafts = [], {}
    for inc in incidents:
        required = inc["severity"] in ("1", "2")
        due = add_working_days(inc["date"], POSTMORTEM_WORKING_DAYS)
        if inc["postmortem_written"] == "Y":
            status = "written"
        elif not required:
            status = "not_required_sev3_plus"
        else:
            status = "overdue" if as_of > due else "open"
        tl = timelines.get(inc["incident_id"])
        facts = timeline_facts(tl)
        rows.append({
            "incident_id": inc["incident_id"], "date": inc["date"], "service": inc["service"],
            "severity": inc["severity"], "postmortem_written": inc["postmortem_written"],
            "required_by_clause_4": "Y" if required else "N", "due": due, "status": status,
            "repeat_of": inc["repeat_of"], "timeline_found": "Y" if tl else "N",
            "timeline_issues": "; ".join(facts.get("anomalies", [])),
        })
        if status in ("overdue", "open"):
            drafts[inc["incident_id"]] = draft_postmortem(
                inc, tl, facts, prs_by_id.get(inc["related_pr"]), due, status, by_id.get(inc["repeat_of"]))
    return rows, drafts


def evaluate_postmortems(gaps, incidents):
    required = [g for g in gaps if g["required_by_clause_4"] == "Y"]
    missing = [g for g in required if g["postmortem_written"] == "N"]
    with_tl = [g for g in gaps if g["timeline_found"] == "Y"]
    by_service = defaultdict(int)
    for g in missing:
        by_service[g["service"]] += 1
    repeats = [g for g in gaps if g["repeat_of"]]
    return {
        "incidents": len(gaps), "not_written_any_severity": sum(g["postmortem_written"] == "N" for g in gaps),
        "required_sev1_2": len(required), "required_missing": len(missing),
        "overdue": sum(g["status"] == "overdue" for g in gaps),
        "timelines_parsed": len(with_tl),
        "timelines_with_data_issues": sum(bool(g["timeline_issues"]) for g in with_tl),
        "repeats": len(repeats),
        "repeats_without_postmortem": sum(g["postmortem_written"] == "N" for g in repeats),
        "missing_by_service": dict(sorted(by_service.items(), key=lambda kv: -kv[1])),
        "limit": "drafts hold facts only; whether a human-written postmortem would be better or faster "
                 "is untested here",
    }


# Run

def load(folder):
    prs, q1 = io.read_table(folder, "pull_requests.csv", {**PR_SCHEMA, "hours_to_first_review": _optional_hours})
    incidents, q2 = io.read_table(folder, "incidents.csv", INCIDENT_SCHEMA)
    return prs, incidents, q1 + q2


def run(data_dir, out_dir, as_of=None):
    """Write the review outputs. Returns (summary, exit_code); the code is 3 if any input row was quarantined."""
    prs, incidents, quarantine = load(data_dir)
    if as_of is None and incidents:
        as_of = max(i["date"] for i in incidents)
    elif isinstance(as_of, str):
        as_of = date.fromisoformat(as_of)
    out = Path(out_dir)

    triaged = [triage(p) for p in prs]
    order = {"strict": 0, "high": 1, "low": 2}
    queue = sorted(zip(prs, triaged), key=lambda x: (order[x[1].tier], -x[1].risk_score, x[0]["pr_id"]))
    io.write_csv(out / "pr_triage.csv",
                 ["pr_id", "month", "team", "service", "agent_assisted", "lines_changed", "risk_score", "tier",
                  "required_approvals", "security_second_approver", "reviewer_pool", "split_suggested", "flags", "why"],
                 [{"pr_id": p["pr_id"], "month": p["month"], "team": p["team"], "service": p["service"],
                   "agent_assisted": p["agent_assisted"], "lines_changed": p["lines_changed"],
                   "risk_score": t.risk_score, "tier": t.tier, "required_approvals": t.required_approvals,
                   "security_second_approver": "Y" if t.security_approver else "N",
                   "reviewer_pool": t.reviewer_pool, "split_suggested": "Y" if t.split_suggested else "N",
                   "flags": ";".join(t.flags), "why": t.why} for p, t in queue])

    timelines = parse_timelines(Path(data_dir) / "incident_timelines.md")
    gaps, drafts = postmortem_gaps(incidents, timelines, {p["pr_id"]: p for p in prs}, as_of) \
        if incidents else ([], {})
    io.write_csv(out / "postmortem_gaps.csv",
                 ["incident_id", "date", "service", "severity", "postmortem_written", "required_by_clause_4",
                  "due", "status", "repeat_of", "timeline_found", "timeline_issues"], gaps)
    folder = out / "postmortem_drafts"
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.md"):
        old.unlink()
    for iid, text in drafts.items():
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", iid)
        (folder / f"{safe}.md").write_text(text, encoding="utf-8")
    io.write_csv(out / "quarantine.csv", ["file", "line", "reason"],
                 [{"file": q.file, "line": q.line, "reason": q.reason} for q in quarantine])

    summary = {
        "prs": len(prs), "incidents": len(incidents), "as_of": str(as_of) if as_of else None,
        "tiers": {k: sum(t.tier == k for t in triaged) for k in order},
        "triage_evaluation": evaluate_triage(prs, triaged) if prs else {"available": False},
        "controls": controls_report(prs, triaged),
        "postmortem_evaluation": evaluate_postmortems(gaps, incidents) if gaps else {"available": False},
        "drafts_written": len(drafts),
        "quarantined_rows": len(quarantine),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    return summary, (3 if quarantine else 0)
