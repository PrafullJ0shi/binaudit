"""The browser and the CLI must give the same numbers for the same CSV."""

import json
import math
import shutil
import subprocess
from dataclasses import asdict

import pytest

from binaudit.stats import bins, compare, phases, summarise, top_misplaced

from .conftest import ROOT, SAMPLE

node = shutil.which("node")
pytestmark = pytest.mark.skipif(node is None, reason="Node.js is not installed")


def close(a, b):
    if isinstance(a, (list, tuple)):
        return len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        if a is None or b is None:
            return a is b
        return (math.isnan(a) and math.isnan(b)) or abs(a - b) <= 1e-12
    return a == b


def test_js_and_python_agree(sample_rows):
    js = json.loads(subprocess.run([node, str(ROOT / "scripts" / "js_summary.mjs"), str(SAMPLE)],
                                   capture_output=True, text=True, check=True).stdout)
    py = [asdict(s) for s in summarise(sample_rows)]
    assert len(js["summary"]) == len(py) == 12
    for j, p in zip(js["summary"], py):
        for key, value in p.items():
            assert close(j[key], value), (key, j[key], value)
    ph = phases(sample_rows)
    for j, (site, b) in zip(js["compare"], bins(sample_rows)):
        p = asdict(compare(sample_rows, site, b, ph[0], ph[-1]))
        for key, value in p.items():
            assert close(j[key], value), (key, j[key], value)
    for j, (site, b) in zip(js["top"], bins(sample_rows)):
        assert [(m["item"], m["count"]) for m in j] == [(m.item, m.count) for m in top_misplaced(sample_rows, site, b)]
