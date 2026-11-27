"""Reading and writing audit CSV files, and the item catalogue."""

from __future__ import annotations

import csv
import io
import json
from importlib import resources
from pathlib import Path

from .stats import COLUMNS, STREAMS, Row

REQUIRED = tuple(c for c in COLUMNS if c not in ("grams", "phase"))


class AuditFileError(ValueError):
    """Raised when an audit CSV cannot be used."""


def _row(d: dict[str, str], line: int) -> Row:
    where = f" (line {line})"
    bin_stream = (d.get("bin_stream") or "").strip().lower()
    item_stream = (d.get("item_stream") or "").strip().lower()
    if bin_stream not in STREAMS:
        raise AuditFileError(f'Unknown bin_stream "{d.get("bin_stream")}"{where}')
    if item_stream not in STREAMS:
        raise AuditFileError(f'Unknown item_stream "{d.get("item_stream")}"{where}')
    raw_count = (d.get("count") or "").strip()
    try:
        count = int(raw_count) if raw_count else 1
    except ValueError as e:
        raise AuditFileError(f"count must be a whole number{where}") from e
    if count < 0:
        raise AuditFileError(f"count must be a whole number{where}")
    raw_g = (d.get("grams") or "").strip()
    try:
        grams = float(raw_g) if raw_g else None
    except ValueError as e:
        raise AuditFileError(f"grams must be a number{where}") from e
    if grams is not None and grams < 0:
        raise AuditFileError(f"grams must be a number{where}")
    return Row(
        audit_id=(d.get("audit_id") or "").strip(),
        date=(d.get("date") or "").strip(),
        site=(d.get("site") or "").strip(),
        bin_stream=bin_stream,
        phase=(d.get("phase") or "").strip(),
        item=(d.get("item") or "").strip(),
        item_stream=item_stream,
        count=count,
        grams=grams,
    )


def parse_csv(text: str) -> list[Row]:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return []
    reader.fieldnames = [f.strip().lower() for f in reader.fieldnames]
    missing = [c for c in REQUIRED if c not in reader.fieldnames]
    if missing:
        raise AuditFileError("CSV is missing columns: " + ", ".join(missing))
    rows = []
    for n, d in enumerate(reader, start=2):
        if not any((v or "").strip() for v in d.values() if isinstance(v, str)):
            continue
        rows.append(_row(d, n))
    return rows


def read_csv(path: str | Path) -> list[Row]:
    return parse_csv(Path(path).read_text(encoding="utf-8-sig"))


def _fmt_grams(g: float | None) -> str:
    if g is None:
        return ""
    return str(int(g)) if float(g).is_integer() else repr(g)


def to_csv(rows: list[Row]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(COLUMNS)
    for r in rows:
        w.writerow([r.audit_id, r.date, r.site, r.bin_stream, r.phase, r.item, r.item_stream, r.count, _fmt_grams(r.grams)])
    return buf.getvalue()


def load_catalogue() -> dict:
    """The bundled item catalogue (same file as web/data/items.json)."""
    text = resources.files("binaudit").joinpath("data/items.json").read_text(encoding="utf-8")
    return json.loads(text)


def lookup(name: str, catalogue: dict | None = None) -> list[dict]:
    """Catalogue entries whose name contains every word of the query."""
    cat = catalogue or load_catalogue()
    words = name.lower().split()
    return [i for i in cat["items"] if all(w in i["name"].lower() for w in words)]
