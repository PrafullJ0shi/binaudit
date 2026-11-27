# Changelog

All notable changes to this project are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and versions follow
[Semantic Versioning](https://semver.org/).

## [0.1.0] - 2026-11-27

### Added

- Web app with four screens: log an audit, results, printable sign, data.
- Contamination rate per site, bin and phase with a cluster bootstrap 95% interval
  (2,000 draws, fixed seed) and a Wilson interval for reference.
- Before/after comparison with a plain-language reading.
- A5 sign generated from a bin's most common misplaced items.
- 60-item catalogue mapped to the streams in India's Solid Waste Management Rules, 2016.
- CSV import and export; data stored only in the browser.
- Python package and `binaudit` command: `summary`, `compare`, `report`, `lookup`, `sample`.
- Labelled synthetic sample data set and a generator for it.
- 27 tests, including a parity test between the JavaScript and Python implementations.
- `scripts/publish-pages.sh` to publish `web/` to the `gh-pages` branch for GitHub Pages.
