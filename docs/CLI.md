# Command line

The Python package reads the CSV that the web app exports and prints the same numbers.

```
binaudit summary FILE [--json] [--draws N] [--seed S]
binaudit compare FILE [--before PHASE] [--after PHASE] [--json] [--draws N] [--seed S]
binaudit report  FILE [-o report.md] [--draws N] [--seed S]
binaudit lookup  ITEM...
binaudit sample  [-o file.csv] [--seed S]
```

`python -m binaudit` works the same way as `binaudit`.

## Examples

```console
$ binaudit compare web/data/sample-audits.csv
Hostel A, floor 2, wet bin: 33.8% (6 audits, before sign) to 13.7% (6 audits, after sign). Difference -20.1 pp, 95% interval -30.0 pp to -10.3 pp: fewer misplaced items after.
Hostel A, floor 2, dry bin: 33.1% (6 audits, before sign) to 25.2% (6 audits, after sign). Difference -8.0 pp, 95% interval -17.8 pp to +2.1 pp: no clear change.
...
```

These numbers are from the synthetic sample, not from real bins.

```console
$ binaudit lookup tube light
tube light: hazardous  Contains mercury.
```

## Exit codes

| Code | Meaning |
|---|---|
| 0 | success |
| 1 | `lookup` found nothing |
| 2 | the CSV could not be read; the message names the column or line |
