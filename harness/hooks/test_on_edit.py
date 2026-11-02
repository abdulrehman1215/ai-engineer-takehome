#!/usr/bin/env python3
"""PostToolUse hook: when a Python file in this repo changes, run the test suite.

A failure exits with code 2, so the agent sees the output and fixes it before moving on.
"""
import json
import os
import subprocess
import sys

try:
    data = json.load(sys.stdin)
except ValueError:
    sys.exit(0)
path = (data.get("tool_input") or {}).get("file_path", "")
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if not path.endswith(".py") or not os.path.abspath(path).startswith(os.path.abspath(root)):
    sys.exit(0)
done = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-q"],
                      cwd=root, capture_output=True, text=True)
if done.returncode:
    print("tests failed after editing " + path + "\n" + (done.stderr or done.stdout)[-3000:], file=sys.stderr)
    sys.exit(2)
