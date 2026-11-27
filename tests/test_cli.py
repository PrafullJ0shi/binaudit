import json

from binaudit.cli import main

from .conftest import SAMPLE


def test_summary_table(capsys):
    assert main(["summary", str(SAMPLE), "--draws", "200"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("| Site | Bin | Phase")
    assert out.count("Hostel A") == 12


def test_summary_json(capsys):
    main(["summary", str(SAMPLE), "--json", "--draws", "200"])
    data = json.loads(capsys.readouterr().out)
    assert {d["bin_stream"] for d in data} == {"wet", "dry", "hazardous"}


def test_compare_defaults_to_first_and_last_phase(capsys):
    assert main(["compare", str(SAMPLE), "--draws", "500"]) == 0
    out = capsys.readouterr().out
    assert "before sign" in out and "after sign" in out


def test_report_to_file(tmp_path):
    out = tmp_path / "r.md"
    assert main(["report", str(SAMPLE), "-o", str(out), "--draws", "200"]) == 0
    text = out.read_text(encoding="utf-8")
    assert text.startswith("# Bin audit report") and "Most common misplaced items" in text


def test_lookup_and_errors(capsys, tmp_path):
    assert main(["lookup", "tube", "light"]) == 0
    assert "hazardous" in capsys.readouterr().out
    assert main(["lookup", "unicorn"]) == 1
    bad = tmp_path / "bad.csv"
    bad.write_text("audit_id,date\n", encoding="utf-8")
    assert main(["summary", str(bad)]) == 2
    assert "missing columns" in capsys.readouterr().err
