# Roadmap

## 0.1.0 (now)

- Log audits in the browser, offline, with item suggestions from a 60-item catalogue.
- Contamination rate per bin with a cluster bootstrap interval.
- Before/after comparison with a plain reading.
- Printable A5 sign built from a bin's own most common mistakes.
- CSV export and import; Python command line tool with the same numbers.

## Next

- **Control comparison.** Difference-in-differences between a signed bin and an unsigned
  bin over the same weeks, so the app itself reports whether the change is larger than
  the background drift.
- **Per-site catalogue overrides.** A site can mark items that its municipality sorts
  differently, and every rate uses the override.
- **Shared audits.** Several people audit different floors and merge their CSVs without
  duplicate audit IDs (import already skips repeated IDs).
- **QR code on each sign** that opens the log page with the site and bin filled in.
- **Hindi and other Indian language signs**, using the same layout.
- **Mass-based results in the browser** when audits record grams.
- **Accessibility pass**: screen reader labels for the interval bars and keyboard-only
  logging tested end to end.

## Not planned

- Accounts or a server. Data stays with whoever ran the audit.
- Photo classification of items. The point is a careful count by a person, not a guess.
