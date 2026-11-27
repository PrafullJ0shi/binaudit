"""Plain-text and Markdown reports."""

from __future__ import annotations

import math

from .stats import Comparison, Row, Summary, bins, compare, phases, summarise, top_misplaced


def pct(x: float | None, digits: int = 1) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    return f"{100 * x:.{digits}f}%"


def interval(ci: tuple[float, float]) -> str:
    return f"{pct(ci[0])} to {pct(ci[1])}"


def signed_pp(x: float) -> str:
    return f"{100 * x:+.1f} pp"


def summary_table(summaries: list[Summary]) -> str:
    head = "| Site | Bin | Phase | Audits | Items | Misplaced | Rate | 95% interval (audits resampled) |"
    lines = [head, "|---|---|---|---:|---:|---:|---:|---|"]
    for s in summaries:
        flag = " (small sample)" if s.small_sample else ""
        ci = "needs 2+ audits" if s.audits < 2 else interval(s.ci_bootstrap) + flag
        lines.append(
            f"| {s.site} | {s.bin_stream} | {s.phase or '-'} | {s.audits} | {s.items} | {s.misplaced} | "
            f"{pct(s.rate)} | {ci} |"
        )
    return "\n".join(lines)


def comparison_line(c: Comparison) -> str:
    return (
        f"{c.site}, {c.bin_stream} bin: {pct(c.rate_before)} ({c.audits_before} audits, {c.before}) to "
        f"{pct(c.rate_after)} ({c.audits_after} audits, {c.after}). Difference {signed_pp(c.difference)}, "
        f"95% interval {signed_pp(c.ci[0])} to {signed_pp(c.ci[1])}: {c.verdict}."
    )


def markdown_report(rows: list[Row], B: int = 2000, seed: int = 7, title: str = "Bin audit report") -> str:
    sums = summarise(rows, B=B, seed=seed)
    out = [f"# {title}", ""]
    audits = len({r.audit_id for r in rows})
    out.append(f"{audits} audits, {sum(r.count for r in rows)} items, {len(sums)} site/bin/phase groups.")
    out += ["", "## Contamination by bin", "", summary_table(sums), ""]
    out.append(
        "Rate = misplaced items / all items in that bin. The interval resamples whole audits "
        f"({B} bootstrap draws, seed {seed}), because items from one bin on one day are not independent."
    )
    ph = phases(rows)
    if len(ph) >= 2:
        out += ["", f"## {ph[0]} versus {ph[-1]}", ""]
        for s in bins(rows):
            c = compare(rows, s[0], s[1], ph[0], ph[-1], B=B, seed=seed)
            if c:
                out.append(f"- {comparison_line(c)}")
    out += ["", "## Most common misplaced items", ""]
    for s in bins(rows):
        top = top_misplaced(rows, s[0], s[1], phase=ph[-1] if ph else None)
        if top:
            items = "; ".join(f"{m.item} ({m.count}, belongs in {m.belongs_in})" for m in top)
            out.append(f"- {s[0]}, {s[1]} bin: {items}")
    return "\n".join(out) + "\n"
