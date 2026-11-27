"""Contamination statistics. Mirrors web/js/stats.js number for number."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

STREAMS = ("wet", "dry", "hazardous")
COLUMNS = ("audit_id", "date", "site", "bin_stream", "phase", "item", "item_stream", "count", "grams")
SMALL_AUDITS = 5
SMALL_ITEMS = 30
_M = 0xFFFFFFFF


def _imul(a: int, b: int) -> int:
    return ((a & _M) * (b & _M)) & _M


def mulberry32(seed: int):
    """Seeded generator of floats in [0, 1); same sequence as the JavaScript version."""
    state = seed & _M

    def rand() -> float:
        nonlocal state
        state = (state + 0x6D2B79F5) & _M
        a = state
        t = _imul(a ^ (a >> 15), 1 | a)
        t = ((t + _imul(t ^ (t >> 7), 61 | t)) & _M) ^ t
        return ((t ^ (t >> 14)) & _M) / 4294967296

    return rand


def quantile(sorted_values: list[float], q: float) -> float:
    """Hyndman-Fan type 7 quantile of an already sorted list."""
    if not sorted_values:
        return math.nan
    h = (len(sorted_values) - 1) * q
    lo = math.floor(h)
    hi = min(lo + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (h - lo) * (sorted_values[hi] - sorted_values[lo])


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Wilson score interval for k successes out of n, 95% by default."""
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    d = 1 + (z * z) / n
    c = (p + (z * z) / (2 * n)) / d
    m = (z * math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n))) / d
    return (max(0.0, c - m), min(1.0, c + m))


@dataclass
class Row:
    audit_id: str
    date: str
    site: str
    bin_stream: str
    phase: str
    item: str
    item_stream: str
    count: int = 1
    grams: float | None = None

    @property
    def misplaced(self) -> bool:
        return self.item_stream != self.bin_stream


@dataclass
class AuditTotal:
    audit_id: str
    date: str
    wrong: int = 0
    total: int = 0
    wrong_g: float = 0.0
    total_g: float = 0.0
    has_all_grams: bool = True


def audit_totals(rows: list[Row]) -> list[AuditTotal]:
    audits: dict[str, AuditTotal] = {}
    for r in rows:
        a = audits.get(r.audit_id)
        if a is None:
            a = audits[r.audit_id] = AuditTotal(r.audit_id, r.date)
        a.total += r.count
        if r.misplaced:
            a.wrong += r.count
        if r.grams is None:
            a.has_all_grams = False
        else:
            a.total_g += r.grams
            if r.misplaced:
                a.wrong_g += r.grams
    return [a for a in audits.values() if a.total > 0]


def _pooled(audits: list[AuditTotal], idx, mass: bool = False) -> float:
    num = den = 0
    for i in idx:
        a = audits[i]
        num += a.wrong_g if mass else a.wrong
        den += a.total_g if mass else a.total
    return math.nan if den == 0 else num / den


def _resample(n: int, rand) -> list[int]:
    return [math.floor(rand() * n) for _ in range(n)]


def bootstrap_rate(audits: list[AuditTotal], B: int = 2000, seed: int = 7) -> tuple[float, float]:
    """Cluster bootstrap over audits, percentile 95% interval."""
    n = len(audits)
    if n == 0:
        return (math.nan, math.nan)
    rand = mulberry32(seed)
    out = []
    for _ in range(B):
        r = _pooled(audits, _resample(n, rand))
        if not math.isnan(r):
            out.append(r)
    out.sort()
    return (quantile(out, 0.025), quantile(out, 0.975))


@dataclass
class Summary:
    site: str
    bin_stream: str
    phase: str
    audits: int
    items: int
    misplaced: int
    rate: float
    ci_bootstrap: tuple[float, float]
    ci_wilson: tuple[float, float]
    mass_rate: float | None
    first_date: str
    last_date: str
    small_sample: bool


def summarise(rows: list[Row], B: int = 2000, seed: int = 7) -> list[Summary]:
    groups: dict[tuple[str, str, str], list[Row]] = {}
    for r in rows:
        groups.setdefault((r.site, r.bin_stream, r.phase), []).append(r)
    out = []
    for (site, bin_stream, phase), g in groups.items():
        audits = audit_totals(g)
        if not audits:
            continue
        idx = range(len(audits))
        wrong = sum(a.wrong for a in audits)
        total = sum(a.total for a in audits)
        mass_ok = all(a.has_all_grams for a in audits) and any(a.total_g > 0 for a in audits)
        dates = sorted(a.date for a in audits if a.date)
        out.append(
            Summary(
                site=site,
                bin_stream=bin_stream,
                phase=phase,
                audits=len(audits),
                items=total,
                misplaced=wrong,
                rate=_pooled(audits, idx),
                ci_bootstrap=bootstrap_rate(audits, B=B, seed=seed),
                ci_wilson=wilson(wrong, total),
                mass_rate=_pooled(audits, idx, mass=True) if mass_ok else None,
                first_date=dates[0] if dates else "",
                last_date=dates[-1] if dates else "",
                small_sample=len(audits) < SMALL_AUDITS or total < SMALL_ITEMS,
            )
        )
    order = phases(rows)
    out.sort(key=lambda s: (s.site, STREAMS.index(s.bin_stream), order.index(s.phase)))
    return out


@dataclass
class Misplaced:
    item: str
    belongs_in: str
    count: int


def top_misplaced(rows: list[Row], site: str, bin_stream: str, phase: str | None = None, k: int = 3) -> list[Misplaced]:
    tally: dict[str, Misplaced] = {}
    for r in rows:
        if r.site != site or r.bin_stream != bin_stream:
            continue
        if phase is not None and r.phase != phase:
            continue
        if not r.misplaced or r.count == 0:
            continue
        e = tally.setdefault(r.item.lower(), Misplaced(r.item, r.item_stream, 0))
        e.count += r.count
    return sorted(tally.values(), key=lambda m: (-m.count, m.item))[:k]


@dataclass
class Comparison:
    site: str
    bin_stream: str
    before: str
    after: str
    audits_before: int
    audits_after: int
    rate_before: float
    rate_after: float
    difference: float
    ci: tuple[float, float]
    verdict: str = field(default="no clear change")


def compare(rows: list[Row], site: str, bin_stream: str, before: str, after: str, B: int = 2000, seed: int = 7) -> Comparison | None:
    """Difference in contamination rate, after minus before, with a cluster bootstrap 95% interval."""

    def pick(ph: str) -> list[AuditTotal]:
        return audit_totals([r for r in rows if r.site == site and r.bin_stream == bin_stream and r.phase == ph])

    a, b = pick(before), pick(after)
    if not a or not b:
        return None
    ra, rb = _pooled(a, range(len(a))), _pooled(b, range(len(b)))
    rand = mulberry32(seed)
    diffs = []
    for _ in range(B):
        x = _pooled(a, _resample(len(a), rand))
        y = _pooled(b, _resample(len(b), rand))
        if not (math.isnan(x) or math.isnan(y)):
            diffs.append(y - x)
    diffs.sort()
    ci = (quantile(diffs, 0.025), quantile(diffs, 0.975))
    verdict = "no clear change"
    if ci[1] < 0:
        verdict = "fewer misplaced items after"
    elif ci[0] > 0:
        verdict = "more misplaced items after"
    return Comparison(site, bin_stream, before, after, len(a), len(b), ra, rb, rb - ra, ci, verdict)


def bins(rows: list[Row]) -> list[tuple[str, str]]:
    """(site, bin_stream) pairs, sorted by site then stream order."""
    return sorted({(r.site, r.bin_stream) for r in rows}, key=lambda p: (p[0], STREAMS.index(p[1])))


def phases(rows: list[Row]) -> list[str]:
    seen: list[str] = []
    for r in rows:
        if r.phase not in seen:
            seen.append(r.phase)
    return seen
