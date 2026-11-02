import csv
import io as stdio
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from pathlib import Path

import run
from data.synthetic import generate
from xgroup import engineering as eng
from xgroup.io import SchemaError

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "dossier" / "case_d"


def build():
    d = tempfile.mkdtemp()
    generate.write_engineering(d)
    return d


def rewrite(folder, name, edit):
    path = Path(folder) / name
    with open(path, newline="") as fh:
        rows = list(csv.reader(fh))
    with open(path, "w", newline="") as fh:
        csv.writer(fh).writerows(edit(rows))


class TriageTests(unittest.TestCase):
    def setUp(self):
        d = build()
        prs, _, _ = eng.load(d)
        self.t = {p["pr_id"]: eng.triage(p) for p in prs}

    def test_tiers_and_scores(self):
        got = {k: (v.tier, v.risk_score) for k, v in self.t.items()}
        self.assertEqual(got, {
            "PR-1": ("strict", 3), "PR-2": ("strict", 2), "PR-3": ("low", 0), "PR-4": ("high", 1),
            "PR-5": ("low", 0), "PR-6": ("low", 0), "PR-7": ("high", 1), "PR-8": ("high", 1)})

    def test_sensitive_changes_need_two_approvers_including_security(self):
        for k in ("PR-1", "PR-2"):
            self.assertEqual((self.t[k].required_approvals, self.t[k].security_approver), (2, True))
        for k in ("PR-3", "PR-4", "PR-7"):
            self.assertEqual((self.t[k].required_approvals, self.t[k].security_approver), (1, False))

    def test_size_is_not_a_risk_term_but_suggests_a_split(self):
        self.assertTrue(self.t["PR-1"].split_suggested)
        self.assertFalse(self.t["PR-4"].split_suggested)       # 600 lines: large, not split-sized
        self.assertIn("large_change", self.t["PR-4"].flags)
        self.assertEqual(self.t["PR-6"].tier, "low")

    def test_self_review_is_flagged(self):
        self.assertIn("self_review", self.t["PR-5"].flags)
        self.assertNotIn("self_review", self.t["PR-3"].flags)

    def test_restricted_services_are_marked(self):
        eng.RESTRICTED_SERVICES.add("reporting")
        try:
            prs, _, _ = eng.load(build())
            flags = {p["pr_id"]: eng.triage(p).flags for p in prs}
        finally:
            eng.RESTRICTED_SERVICES.discard("reporting")
        self.assertIn("client_restricted_no_external_services", flags["PR-3"])

    def test_the_tool_has_no_approve_or_merge_surface(self):
        public = {n for n in dir(eng) if not n.startswith("_")}
        self.assertFalse({n for n in public if "approve" in n.lower() or "merge" in n.lower()} - {"controls_report"})


class MetricTests(unittest.TestCase):
    def test_auc_perfect_none_and_undefined(self):
        self.assertEqual(eng.auc({0: (0, 10), 1: (10, 10)}), 1.0)
        self.assertEqual(eng.auc({0: (5, 10), 1: (5, 10)}), 0.5)
        self.assertIsNone(eng.auc({0: (0, 10), 1: (0, 10)}))

    def test_working_days_skip_weekends(self):
        self.assertEqual(eng.add_working_days(date(2026, 7, 3), 1), date(2026, 7, 6))     # Friday to Monday
        self.assertEqual(eng.add_working_days(date(2026, 7, 6), 10), date(2026, 7, 20))

    def test_evaluation_on_synthetic_rows(self):
        prs, _, _ = eng.load(build())
        ev = eng.evaluate_triage(prs, [eng.triage(p) for p in prs])
        self.assertEqual(ev["revert_rate_by_tier"]["strict"]["revert_rate"], 0.5)   # PR-1 reverted, PR-2 not
        self.assertEqual(ev["revert_rate_by_tier"]["low"]["revert_rate"], 0.0)
        self.assertEqual(ev["prs"], 8)


class PostmortemTests(unittest.TestCase):
    def setUp(self):
        self.dir = build()
        prs, incs, _ = eng.load(self.dir)
        self.tl = eng.parse_timelines(Path(self.dir) / "incident_timelines.md")
        self.gaps, self.drafts = eng.postmortem_gaps(
            incs, self.tl, {p["pr_id"]: p for p in prs}, date(2026, 7, 21))
        self.g = {g["incident_id"]: g for g in self.gaps}

    def test_status_and_due_date(self):
        self.assertEqual((self.g["INC-1"]["status"], str(self.g["INC-1"]["due"])), ("overdue", "2026-07-20"))
        self.assertEqual(self.g["INC-2"]["status"], "written")
        self.assertEqual(self.g["INC-3"]["status"], "open")
        self.assertEqual((self.g["INC-4"]["status"], self.g["INC-4"]["required_by_clause_4"]),
                         ("not_required_sev3_plus", "N"))

    def test_drafts_only_for_missing_required_postmortems(self):
        self.assertEqual(sorted(self.drafts), ["INC-1", "INC-3"])

    def test_timeline_anomalies_are_reported_not_fixed(self):
        self.assertIn("out of order", self.g["INC-1"]["timeline_issues"])
        self.assertIn("recorded duration is 30", self.g["INC-3"]["timeline_issues"])
        self.assertEqual(self.g["INC-2"]["timeline_issues"], "")

    def test_draft_holds_facts_and_leaves_findings_to_a_human(self):
        d = self.drafts["INC-1"]
        self.assertIn("DRAFT", d)
        self.assertEqual(d.count("TODO (human)"), 5)
        self.assertIn("minutes alert to restore: 75", d)
        self.assertIn("DATA ISSUE", d)

    def test_repeat_link_states_whether_the_original_had_a_postmortem(self):
        self.assertIn("Repeat of | INC-2: postmortem written", self.drafts["INC-3"])

    def test_related_pr_facts_are_copied_from_the_record(self):
        prs, incs, _ = eng.load(self.dir)
        gaps, drafts = eng.postmortem_gaps(incs, self.tl, {p["pr_id"]: p for p in prs}, date(2026, 12, 1))
        self.assertNotIn("Related PR", drafts["INC-3"])
        # INC-2 is written so it gets no draft; use a direct draft to check the PR line
        text = eng.draft_postmortem(incs[1], self.tl["INC-2"], eng.timeline_facts(self.tl["INC-2"]),
                                    prs[0], date(2026, 7, 22), "open", None)
        self.assertIn("PR-1: agent-assisted, 900 lines, service auth-service", text)

    def test_hostile_timeline_text_is_inert_and_fenced(self):
        d = self.drafts["INC-3"]
        self.assertEqual(self.g["INC-3"]["postmortem_written"], "N")
        self.assertEqual(self.g["INC-3"]["status"], "open")
        fences = [i for i, l in enumerate(d.splitlines()) if l == "```"]
        line = next(i for i, l in enumerate(d.splitlines()) if "IGNORE PREVIOUS" in l)
        self.assertTrue(fences[0] < line < fences[1])

    def test_backticks_in_untrusted_text_cannot_close_the_fence(self):
        self.assertNotIn("```x", eng._fence("```x"))

    def test_missing_timeline_is_reported_not_invented(self):
        (Path(self.dir) / "incident_timelines.md").unlink()
        prs, incs, _ = eng.load(self.dir)
        gaps, drafts = eng.postmortem_gaps(incs, eng.parse_timelines(Path(self.dir) / "incident_timelines.md"),
                                           {}, date(2026, 7, 21))
        g = {x["incident_id"]: x for x in gaps}
        self.assertEqual(g["INC-1"]["timeline_found"], "N")
        self.assertIn("(none)", drafts["INC-1"])
        self.assertNotIn("minutes alert to restore", drafts["INC-1"])


class InputTests(unittest.TestCase):
    def test_missing_column_fails_loudly(self):
        d = build()
        rewrite(d, "pull_requests.csv", lambda rows: [r[:5] + r[6:] for r in rows])   # drop lines_changed
        with self.assertRaises(SchemaError) as cm:
            eng.load(d)
        self.assertIn("lines_changed", str(cm.exception))

    def test_bad_rows_are_quarantined_not_dropped_silently(self):
        d = build()
        rewrite(d, "pull_requests.csv", lambda rows: rows + [
            ["PR-9", "2026-07", "T", "A", "maybe", "10", "reporting", "x", "1", "R", "Y", "N"],
            ["PR-10", "2026-07", "T", "A", "Y", "-5", "reporting", "x", "1", "R", "Y", "N"]])
        prs, _, quarantine = eng.load(d)
        self.assertEqual((len(prs), len(quarantine)), (8, 2))

    def test_blank_review_time_is_allowed(self):
        d = build()
        rewrite(d, "pull_requests.csv", lambda rows: [r[:8] + [""] + r[9:] if r[0] == "PR-3" else r for r in rows])
        prs, _, quarantine = eng.load(d)
        self.assertEqual(quarantine, [])
        self.assertIsNone(next(p for p in prs if p["pr_id"] == "PR-3")["hours_to_first_review"])


class RunTests(unittest.TestCase):
    def call(self, *argv):
        out, err = stdio.StringIO(), stdio.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = run.main(["run.py", *argv])
        return code, out.getvalue(), err.getvalue()

    def test_run_writes_outputs(self):
        d, out = build(), tempfile.mkdtemp()
        code, _, _ = self.call("engineering", d, out, "--as-of", "2026-07-21")
        self.assertEqual(code, 0)
        for n in ("pr_triage.csv", "postmortem_gaps.csv", "summary.json", "quarantine.csv"):
            self.assertTrue((Path(out) / n).is_file(), n)
        self.assertEqual(sorted(p.name for p in (Path(out) / "postmortem_drafts").iterdir()),
                         ["INC-1.md", "INC-3.md"])
        s = json.loads((Path(out) / "summary.json").read_text())
        self.assertEqual(s["tiers"], {"strict": 2, "high": 3, "low": 3})

    def test_bad_schema_exits_2(self):
        d = build()
        (Path(d) / "incidents.csv").unlink()
        code, _, err = self.call("engineering", d, tempfile.mkdtemp())
        self.assertEqual(code, 2)
        self.assertIn("INPUT ERROR", err)

    def test_quarantine_exits_3(self):
        d = build()
        rewrite(d, "incidents.csv", lambda rows: rows + [["INC-9", "bad-date", "x", "1", "1", "", "N", "", ""]])
        code, _, err = self.call("engineering", d, tempfile.mkdtemp())
        self.assertEqual(code, 3)

    def test_reruns_do_not_leave_stale_drafts(self):
        d, out = build(), tempfile.mkdtemp()
        self.call("engineering", d, out, "--as-of", "2026-07-21")
        rewrite(d, "incidents.csv", lambda rows: [r[:6] + ["Y"] + r[7:] if r[0] == "INC-1" else r for r in rows])
        self.call("engineering", d, out, "--as-of", "2026-07-21")
        self.assertEqual([p.name for p in (Path(out) / "postmortem_drafts").iterdir()], ["INC-3.md"])


@unittest.skipUnless(SAMPLE.is_dir(), "dossier sample not present")
class SampleDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.summary, cls.code = eng.run(SAMPLE, tempfile.mkdtemp())

    def test_counts(self):
        s = self.summary
        self.assertEqual((s["prs"], s["incidents"]), (2700, 22))
        self.assertEqual(s["tiers"], {"strict": 581, "high": 974, "low": 1145})
        self.assertEqual(self.code, 0)

    def test_agent_assisted_prs_revert_more_in_both_service_groups(self):
        a = self.summary["triage_evaluation"]["agent_vs_human_revert_rate"]
        for group in ("sensitive_services", "other_services"):
            self.assertGreater(a[group]["agent"]["revert_rate"], 1.5 * a[group]["human"]["revert_rate"])

    def test_postmortem_gaps_match_the_incident_log(self):
        p = self.summary["postmortem_evaluation"]
        self.assertEqual((p["not_written_any_severity"], p["required_sev1_2"], p["required_missing"]), (9, 18, 9))
        self.assertEqual(p["timelines_parsed"], 22)

    def test_self_reviews_are_found(self):
        self.assertEqual(len(self.summary["controls"]["self_reviewed_prs"]), 8)

    def test_row_order_does_not_change_the_result(self):
        import os, random, shutil
        d = Path(tempfile.mkdtemp()) / "shuffled"
        shutil.copytree(SAMPLE, d, copy_function=shutil.copyfile)
        os.chmod(d, 0o755)
        for name in ("pull_requests.csv", "incidents.csv"):
            os.chmod(d / name, 0o644)
            with open(d / name, newline="", encoding="utf-8-sig") as fh:
                rows = list(csv.reader(fh))
            body = rows[1:]
            random.Random(7).shuffle(body)
            with open(d / name, "w", newline="") as fh:
                csv.writer(fh).writerows([rows[0]] + body)
        shuffled, _ = eng.run(d, tempfile.mkdtemp())
        self.assertEqual(shuffled["tiers"], self.summary["tiers"])
        self.assertEqual(shuffled["triage_evaluation"], self.summary["triage_evaluation"])
        self.assertEqual(shuffled["postmortem_evaluation"], self.summary["postmortem_evaluation"])


if __name__ == "__main__":
    unittest.main()
