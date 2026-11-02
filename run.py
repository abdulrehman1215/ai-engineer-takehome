#!/usr/bin/env python3
"""Run a slice.  python3 run.py finance <case_a_dir> [out_dir]
                python3 run.py engineering <case_d_dir> [out_dir] [--as-of YYYY-MM-DD]

Exit codes: 0 ok, 2 input has the wrong shape (nothing written), 3 ran but some rows were quarantined.
"""
import json
import sys

from xgroup import engineering, finance
from xgroup.io import SchemaError

SLICES = {"finance": finance, "engineering": engineering}


def main(argv):
    if len(argv) < 3 or argv[1] not in SLICES:
        print(__doc__)
        return 2
    args = list(argv[1:])
    as_of = None
    if "--as-of" in args:                      # engineering only: date to judge postmortem deadlines against
        i = args.index("--as-of")
        as_of = args[i + 1] if i + 1 < len(args) else None
        del args[i:i + 2]
    name, data = args[0], args[1]
    out = args[2] if len(args) > 2 else f"out/{name}"
    try:
        kwargs = {"as_of": as_of} if (as_of and name == "engineering") else {}
        summary, code = SLICES[name].run(data, out, **kwargs)
    except SchemaError as exc:
        print(f"INPUT ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(summary, indent=2))
    if code:
        print(f"WARNING: {summary['quarantined_rows']} input row(s) quarantined; see {out}/quarantine.csv",
              file=sys.stderr)
    print(f"outputs in {out}/")
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
