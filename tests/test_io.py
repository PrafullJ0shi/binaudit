import json

import pytest

from binaudit.io import AuditFileError, load_catalogue, lookup, parse_csv, to_csv
from binaudit.sample import make_sample

from .conftest import ROOT, SAMPLE

HEAD = "audit_id,date,site,bin_stream,phase,item,item_stream,count,grams\n"


def test_roundtrip_is_lossless():
    rows = make_sample()
    assert parse_csv(to_csv(rows)) == rows


def test_committed_sample_matches_generator():
    assert SAMPLE.read_text(encoding="utf-8") == to_csv(make_sample())


def test_quoted_fields_and_defaults():
    rows = parse_csv(HEAD + 'a1,2026-11-02,"Hostel B, floor 1",DRY,,"cup, paper",wet,,\n')
    (r,) = rows
    assert r.site == "Hostel B, floor 1" and r.item == "cup, paper"
    assert r.bin_stream == "dry" and r.count == 1 and r.grams is None


@pytest.mark.parametrize(
    "line, message",
    [
        ("a,2026-11-02,S,blue,,x,wet,1,", "bin_stream"),
        ("a,2026-11-02,S,wet,,x,plastic,1,", "item_stream"),
        ("a,2026-11-02,S,wet,,x,wet,1.5,", "count"),
        ("a,2026-11-02,S,wet,,x,wet,1,heavy", "grams"),
    ],
)
def test_bad_rows_name_the_problem_and_line(line, message):
    with pytest.raises(AuditFileError, match=message) as e:
        parse_csv(HEAD + line + "\n")
    assert "line 2" in str(e.value)


def test_missing_columns():
    with pytest.raises(AuditFileError, match="missing columns: item_stream"):
        parse_csv("audit_id,date,site,bin_stream,item,count\n")


def test_catalogue_is_valid_and_in_sync_with_the_web_copy():
    cat = load_catalogue()
    web = json.loads((ROOT / "web" / "data" / "items.json").read_text(encoding="utf-8"))
    assert cat == web
    names = [i["name"] for i in cat["items"]]
    assert len(names) == len(set(names))
    assert {i["stream"] for i in cat["items"]} == set(cat["streams"])


def test_lookup_matches_all_words():
    assert [h["name"] for h in lookup("milk")] == ["milk pouch"]
    assert lookup("battery")[0]["stream"] == "hazardous"
    assert lookup("unicorn") == []
