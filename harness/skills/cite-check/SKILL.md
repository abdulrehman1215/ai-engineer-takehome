---
name: cite-check
description: Check that every claim in docs/submission.md traces to a dossier file or a URL. Use before finishing any edit to the submission document.
---

The brief penalises a number you cannot trace more than an honest gap. Run this before calling the document done.

1. Run `python3 harness/skills/cite-check/check_paths.py docs/submission.md`. Every missing path is a broken citation: fix the path or delete the claim.
2. For each number in the document, find the file it came from and recompute it from that file (not from memory or from `docs/evidence_notes.md`). Figures about the slices come from `out/*/summary.json`; re-run `python3 run.py ...` first so they are current.
3. A number with no source gets a source, a stated assumption in the register, or is removed.
4. External claims need a URL that was opened, with the claim worded as the page words it.
5. Report what was checked and what could not be.
