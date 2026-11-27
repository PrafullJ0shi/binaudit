"""A labelled synthetic data set for demos and tests.

Nothing here is a measurement. The numbers are drawn from fixed probabilities with a
seeded generator so that the demo, the screenshots and the tests are reproducible.
"""

from __future__ import annotations

from datetime import date, timedelta

from .io import load_catalogue
from .stats import STREAMS, Row, mulberry32

# Probability that an item found in a bin belongs to another stream.
# Floor 2 gets a sign after the fourth week; floor 3 does not (a control).
PLAN = {
    ("Hostel A, floor 2", "before sign"): {"wet": 0.30, "dry": 0.35, "hazardous": 0.50},
    ("Hostel A, floor 2", "after sign"): {"wet": 0.15, "dry": 0.20, "hazardous": 0.45},
    ("Hostel A, floor 3", "before sign"): {"wet": 0.28, "dry": 0.33, "hazardous": 0.50},
    ("Hostel A, floor 3", "after sign"): {"wet": 0.27, "dry": 0.32, "hazardous": 0.48},
}
WEEKS_PER_PHASE = 6
START = date(2026, 11, 2)


def make_sample(seed: int = 2026) -> list[Row]:
    rand = mulberry32(seed)
    items = load_catalogue()["items"]
    by_stream = {s: [i for i in items if i["stream"] == s] for s in STREAMS}

    def pick(pool):
        return pool[int(rand() * len(pool))]

    rows: list[Row] = []
    for (site, phase), p_wrong in PLAN.items():
        offset = 0 if phase == "before sign" else WEEKS_PER_PHASE
        floor = site.split()[-1]
        for week in range(WEEKS_PER_PHASE):
            day = START + timedelta(weeks=week + offset)
            for bin_stream in STREAMS:
                audit_id = f"F{floor}-{bin_stream[:3].upper()}-{day:%m%d}"
                n_items = 4 + int(rand() * 9) if bin_stream == "hazardous" else 18 + int(rand() * 15)
                found: dict[str, Row] = {}
                for _ in range(n_items):
                    if rand() < p_wrong[bin_stream]:
                        others = [s for s in STREAMS if s != bin_stream]
                        stream = others[int(rand() * len(others))]
                    else:
                        stream = bin_stream
                    it = pick(by_stream[stream])
                    if it["name"] in found:
                        found[it["name"]].count += 1
                    else:
                        found[it["name"]] = Row(audit_id, day.isoformat(), site, bin_stream, phase, it["name"], stream, 1)
                rows.extend(found.values())
    return rows
