# Harness

Built with an AI coding agent. Three mechanisms, each chosen for a specific failure I wanted to prevent.

| Mechanism | Where | Why |
|---|---|---|
| Hooks | `hooks/guard.py` (PreToolUse), `hooks/test_on_edit.py` (PostToolUse); wired in `settings.json` | A written rule can be forgotten; a hook cannot. `guard.py` blocks any write to `dossier/`. `test_on_edit.py` runs the suite after every Python edit, which caught a real bug (summing an empty list gave an `int`, not a `Decimal`). |
| Skill | `skills/cite-check/` | The brief penalises untraceable numbers most. `check_paths.py` fails if a cited file does not exist; the skill file adds the manual recompute step. |
| Connector permissions | `mcp/README.md` | The Gmail connector was used to read the recruiter thread and, at the end, to save the submission email as an unsent draft. Send, reply, forward and trash were denied. |

Both hooks were pipe-tested with synthetic payloads (5 blocked, 5 allowed) before being relied on. `guard.py` blocks writes to `dossier/`; commits and pushes happen only when I ask.

The session transcript is not committed, because it contains the brief, dossier excerpts and my email address. I am sending it separately with the submission.
