from pathlib import Path

import pytest

from binaudit.io import read_csv

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "web" / "data" / "sample-audits.csv"


@pytest.fixture
def sample_rows():
    return read_csv(SAMPLE)
