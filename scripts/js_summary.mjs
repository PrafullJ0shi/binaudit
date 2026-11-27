// Prints the browser core's results for a CSV file as JSON. Used by tests/test_parity.py.
// Usage: node scripts/js_summary.mjs path/to/audits.csv
import { readFileSync } from "node:fs";
import { bins, compare, parseCSV, phases, summarise, topMisplaced } from "../web/js/stats.js";

const rows = parseCSV(readFileSync(process.argv[2], "utf8"));
const ph = phases(rows);
const out = {
  summary: summarise(rows),
  compare: ph.length > 1 ? bins(rows).map(([site, bin_stream]) => compare(rows, { site, bin_stream, before: ph[0], after: ph[ph.length - 1] })) : [],
  top: bins(rows).map(([site, bin_stream]) => topMisplaced(rows, { site, bin_stream })),
};
process.stdout.write(JSON.stringify(out));
