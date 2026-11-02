#!/usr/bin/env python3
"""PreToolUse hook: block writes to dossier/, which is read-only evidence.

Reads the hook JSON on stdin. Exit code 2 blocks the call and shows the message to the agent.
Commits and pushes are fine when I ask for them in the session.
"""
import json
import re
import sys

WRITE_VERBS = r"(?:rm|mv|chmod|chown|tee|truncate|touch|ln)"


def block(message):
    print(f"BLOCKED by harness/hooks/guard.py: {message}", file=sys.stderr)
    sys.exit(2)


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return                                  # not a payload for this hook; leave it alone
    tool, args = data.get("tool_name", ""), data.get("tool_input", {}) or {}
    if tool == "Bash":
        cmd = args.get("command", "")
        if (re.search(rf"\b{WRITE_VERBS}\b[^;&|]*\bdossier\b", cmd)
                or re.search(r">>?\s*\S*dossier/", cmd)
                or re.search(r"\bsed\s+-i[^;&|]*dossier", cmd)
                or re.search(r"\bcp\b[^;&|]*\s\S*dossier/?\s*$", cmd)):
            block("dossier/ is read-only evidence")
    elif tool in ("Edit", "Write", "NotebookEdit"):
        path = args.get("file_path", "") or args.get("notebook_path", "")
        if "/dossier/" in path or path.startswith("dossier/"):
            block("dossier/ is read-only evidence")


if __name__ == "__main__":
    main()
