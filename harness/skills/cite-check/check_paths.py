#!/usr/bin/env python3
"""List cited file paths in a markdown file that don't exist.

Usage: python3 harness/skills/cite-check/check_paths.py docs/submission.md
A cited path is any `backticked` token that looks like a file (it has a known extension). It must
exist under dossier/ or the repo root. Globs and "a vs b" pairs are expanded. Exit code 1 if
anything is missing.
"""
import glob
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EXT = (".csv", ".md", ".txt", ".json", ".py")


def candidates(token):
    token = re.sub(r":.*$", "", token.strip())           # drop :line or :id suffixes
    for part in re.split(r"\s+vs\s+|,\s*", token):
        part = part.strip()
        if part.endswith(EXT) or "*" in part:
            yield part


def exists(rel, source):
    # a bare file name inherits the folder of the previous full path in the same line (e.g. `case_a/x.csv` vs `y.csv`)
    for base in (ROOT / "dossier", ROOT, source.parent):
        if glob.glob(str(base / rel)):
            return True
    return any(ROOT.joinpath("dossier").rglob(Path(rel).name)) if "/" not in rel else False


def main(path):
    src = Path(path).resolve()
    missing = []
    for lineno, line in enumerate(src.read_text(encoding="utf-8").splitlines(), 1):
        for token in re.findall(r"`([^`]+)`", line):
            for rel in candidates(token):
                if not exists(rel, src):
                    missing.append((lineno, rel))
    for lineno, rel in missing:
        print(f"{path}:{lineno}: cited path not found: {rel}")
    print(f"{len(missing)} missing citation(s)")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "docs/submission.md"))
