"""CSV loading and schema checks, shared by both slices.

A missing file or column raises SchemaError. A bad row comes back as a Quarantine entry, so the
caller can block whatever depends on it and report the row.
"""
import csv
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path


class SchemaError(Exception):
    """The input does not have the shape the slice needs."""


@dataclass
class Quarantine:
    file: str
    line: int
    reason: str
    row: dict


def text(v):
    v = (v or "").strip()
    if not v:
        raise ValueError("empty")
    return v


def optional_text(v):
    return (v or "").strip()


def decimal(v):
    try:
        d = Decimal((v or "").strip())
    except InvalidOperation:
        raise ValueError(f"not a number: {v!r}")
    if not d.is_finite():
        raise ValueError(f"not finite: {v!r}")
    return d


def non_negative_decimal(v):
    d = decimal(v)
    if d < 0:
        raise ValueError(f"negative: {v!r}")
    return d


def integer(v):
    try:
        return int((v or "").strip())
    except ValueError:
        raise ValueError(f"not an integer: {v!r}")


def choice(*allowed):
    def parse(v):
        v = (v or "").strip()
        if v not in allowed:
            raise ValueError(f"{v!r} not one of {list(allowed)}")
        return v
    return parse


def iso_date(v):
    from datetime import date
    v = (v or "").strip()
    try:
        return date.fromisoformat(v)
    except ValueError:
        raise ValueError(f"not an ISO date: {v!r}")


def read_table(folder, name, schema):
    """Read folder/name. `schema` maps column -> parser. Returns (rows, quarantine).

    Extra columns are kept as raw strings under their own name. A row whose
    values fail a parser is quarantined with the reason.
    """
    path = Path(folder) / name
    if not path.is_file():
        raise SchemaError(f"missing file: {path}")
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
        missing = [c for c in schema if c not in header]
        if missing:
            raise SchemaError(f"{name}: missing column(s) {missing}; found {header}")
        rows, bad = [], []
        for i, raw in enumerate(reader, start=2):
            if None in raw:
                bad.append(Quarantine(name, i, "more fields than header", raw))
                continue
            try:
                row = dict(raw)
                for col, parse in schema.items():
                    row[col] = parse(raw[col])
            except ValueError as exc:
                bad.append(Quarantine(name, i, f"{col}: {exc}", raw))
                continue
            row["_line"] = i
            rows.append(row)
    return rows, bad


def write_csv(path, fieldnames, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
