import math

from binaudit.stats import Row, audit_totals, bootstrap_rate, compare, mulberry32, quantile, summarise, top_misplaced, wilson


def row(audit, bin_s, item_s, count=1, phase="", site="S", item="x", grams=None):
    return Row(audit, "2026-11-02", site, bin_s, phase, item, item_s, count, grams)


def test_mulberry32_is_deterministic_and_in_range():
    a, b = mulberry32(7), mulberry32(7)
    xs = [a() for _ in range(1000)]
    assert xs == [b() for _ in range(1000)]
    assert all(0 <= x < 1 for x in xs)
    assert abs(sum(xs) / len(xs) - 0.5) < 0.05


def test_mulberry32_known_values():
    # Same values as the JavaScript implementation prints for seed 7.
    r = mulberry32(7)
    assert [r(), r(), r()] == [0.011704753153026104, 0.06195825757458806, 0.97690763277933]


def test_quantile_type7_matches_numpy_default():
    xs = [1.0, 2.0, 3.0, 4.0]
    assert quantile(xs, 0.5) == 2.5
    assert quantile(xs, 0.025) == 1.075
    assert math.isnan(quantile([], 0.5))


def test_wilson_reference_value():
    lo, hi = wilson(10, 100)
    assert round(lo, 4) == 0.0552
    assert round(hi, 4) == 0.1744
    assert wilson(0, 10)[0] == 0.0


def test_rate_counts_misplaced_items():
    rows = [row("a", "wet", "wet", 7), row("a", "wet", "dry", 3)]
    (s,) = summarise(rows, B=200)
    assert (s.items, s.misplaced, s.rate) == (10, 3, 0.3)
    assert s.small_sample


def test_mass_rate_only_when_every_row_is_weighed():
    rows = [row("a", "dry", "dry", grams=90), row("a", "dry", "wet", grams=10)]
    assert summarise(rows, B=50)[0].mass_rate == 0.1
    rows.append(row("a", "dry", "dry"))
    assert summarise(rows, B=50)[0].mass_rate is None


def test_audits_with_no_items_are_dropped():
    rows = [row("a", "wet", "wet", 0), row("b", "wet", "wet", 2)]
    assert len(audit_totals(rows)) == 1


def test_bootstrap_interval_contains_rate_and_single_audit_is_degenerate():
    rows = [row(f"a{i}", "wet", "dry" if i % 3 == 0 else "wet", 1 + i % 4) for i in range(30)]
    s = summarise(rows)[0]
    assert s.ci_bootstrap[0] <= s.rate <= s.ci_bootstrap[1]
    one = audit_totals([row("a", "wet", "dry", 2), row("a", "wet", "wet", 8)])
    assert bootstrap_rate(one, B=100) == (0.2, 0.2)


def test_compare_detects_a_large_drop_and_not_noise():
    before = [row(f"b{i}", "dry", "wet", 5, "before") for i in range(8)] + [row(f"b{i}", "dry", "dry", 5, "before") for i in range(8)]
    after = [row(f"a{i}", "dry", "wet", 1, "after") for i in range(8)] + [row(f"a{i}", "dry", "dry", 9, "after") for i in range(8)]
    c = compare(before + after, "S", "dry", "before", "after")
    assert c.difference == -0.4
    assert c.verdict == "fewer misplaced items after"
    same = compare(before + [Row(r.audit_id + "x", r.date, r.site, r.bin_stream, "after", r.item, r.item_stream, r.count) for r in before], "S", "dry", "before", "after")
    assert same.verdict == "no clear change"
    assert compare(before, "S", "dry", "before", "after") is None


def test_top_misplaced_ranks_by_count():
    rows = [row("a", "dry", "wet", 2, item="tea leaves"), row("a", "dry", "wet", 5, item="peels"),
            row("b", "dry", "hazardous", 2, item="battery"), row("b", "dry", "dry", 9, item="paper")]
    top = top_misplaced(rows, "S", "dry")
    assert [(m.item, m.count) for m in top] == [("peels", 5), ("battery", 2), ("tea leaves", 2)]
    assert top[1].belongs_in == "hazardous"


def test_sample_shows_the_planted_effect(sample_rows):
    c = compare(sample_rows, "Hostel A, floor 2", "wet", "before sign", "after sign")
    assert c.verdict == "fewer misplaced items after"
    control = compare(sample_rows, "Hostel A, floor 3", "dry", "before sign", "after sign")
    assert control.verdict == "no clear change"
