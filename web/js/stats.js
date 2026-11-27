// binaudit statistics core. Pure functions, no DOM.
// The Python package (src/binaudit/stats.py) implements the same arithmetic;
// tests/test_parity.py checks that both give identical numbers.

export const STREAMS = ["wet", "dry", "hazardous"];
export const COLUMNS = ["audit_id", "date", "site", "bin_stream", "phase", "item", "item_stream", "count", "grams"];
export const SMALL_AUDITS = 5;
export const SMALL_ITEMS = 30;

// ---------- CSV ----------

export function parseCSV(text) {
  const rows = [];
  let field = "", row = [], quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (c === '"') quoted = false;
      else field += c;
    } else if (c === '"') quoted = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n" || c === "\r") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      row.push(field); field = "";
      if (row.some((v) => v !== "")) rows.push(row);
      row = [];
    } else field += c;
  }
  row.push(field);
  if (row.some((v) => v !== "")) rows.push(row);
  if (!rows.length) return [];
  const head = rows[0].map((h) => h.trim().toLowerCase());
  const missing = COLUMNS.filter((c) => c !== "grams" && c !== "phase" && !head.includes(c));
  if (missing.length) throw new Error("CSV is missing columns: " + missing.join(", "));
  return rows.slice(1).map((r, n) => {
    const o = {};
    head.forEach((h, j) => { o[h] = (r[j] ?? "").trim(); });
    return normaliseRow(o, n + 2);
  });
}

export function normaliseRow(o, line = 0) {
  const where = line ? ` (line ${line})` : "";
  const bin = String(o.bin_stream || "").toLowerCase();
  const item = String(o.item_stream || "").toLowerCase();
  if (!STREAMS.includes(bin)) throw new Error(`Unknown bin_stream "${o.bin_stream}"${where}`);
  if (!STREAMS.includes(item)) throw new Error(`Unknown item_stream "${o.item_stream}"${where}`);
  const count = Number(o.count === "" || o.count == null ? 1 : o.count);
  if (!Number.isInteger(count) || count < 0) throw new Error(`count must be a whole number${where}`);
  const g = o.grams === "" || o.grams == null ? null : Number(o.grams);
  if (g !== null && !(g >= 0)) throw new Error(`grams must be a number${where}`);
  return {
    audit_id: String(o.audit_id || "").trim(),
    date: String(o.date || "").trim(),
    site: String(o.site || "").trim(),
    bin_stream: bin,
    phase: String(o.phase || "").trim(),
    item: String(o.item || "").trim(),
    item_stream: item,
    count,
    grams: g,
  };
}

function csvCell(v) {
  const s = v == null ? "" : String(v);
  return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
}

export function toCSV(rows) {
  const lines = [COLUMNS.join(",")];
  for (const r of rows) lines.push(COLUMNS.map((c) => csvCell(r[c])).join(","));
  return lines.join("\n") + "\n";
}

// ---------- random numbers ----------

// mulberry32: small, seedable, and easy to reproduce exactly in Python.
export function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a) >>> 0;
    t = (((t + Math.imul(t ^ (t >>> 7), 61 | t)) >>> 0) ^ t) >>> 0;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Hyndman-Fan type 7 quantile of a sorted array (the default in R and NumPy).
export function quantile(sorted, q) {
  if (!sorted.length) return NaN;
  const h = (sorted.length - 1) * q;
  const lo = Math.floor(h);
  const hi = Math.min(lo + 1, sorted.length - 1);
  return sorted[lo] + (h - lo) * (sorted[hi] - sorted[lo]);
}

// Wilson score interval for a binomial proportion, 95%.
export function wilson(k, n, z = 1.959963984540054) {
  if (n === 0) return [NaN, NaN];
  const p = k / n;
  const d = 1 + (z * z) / n;
  const c = (p + (z * z) / (2 * n)) / d;
  const m = (z * Math.sqrt((p * (1 - p)) / n + (z * z) / (4 * n * n))) / d;
  return [Math.max(0, c - m), Math.min(1, c + m)];
}

// ---------- grouping ----------

export function groupKey(site, bin, phase) {
  return [site, bin, phase].join("\u001f");
}

// One entry per audit: misplaced items, all items, misplaced grams, all grams.
export function auditTotals(rows) {
  const audits = new Map();
  for (const r of rows) {
    let a = audits.get(r.audit_id);
    if (!a) {
      a = { audit_id: r.audit_id, date: r.date, wrong: 0, total: 0, wrongG: 0, totalG: 0, hasAllGrams: true };
      audits.set(r.audit_id, a);
    }
    const wrong = r.item_stream !== r.bin_stream;
    a.total += r.count;
    if (wrong) a.wrong += r.count;
    if (r.grams == null) a.hasAllGrams = false;
    else { a.totalG += r.grams; if (wrong) a.wrongG += r.grams; }
  }
  return [...audits.values()].filter((a) => a.total > 0);
}

function pooled(list, idx, w, t) {
  let num = 0, den = 0;
  for (const i of idx) { num += list[i][w]; den += list[i][t]; }
  return den === 0 ? NaN : num / den;
}

function resample(n, rand) {
  const idx = new Array(n);
  for (let i = 0; i < n; i++) idx[i] = Math.floor(rand() * n);
  return idx;
}

// Cluster bootstrap: audits are resampled, because items from the same bin on the same
// day are not independent. Percentile interval, type 7 quantiles.
export function bootstrapRate(audits, { B = 2000, seed = 7, w = "wrong", t = "total" } = {}) {
  const n = audits.length;
  if (n === 0) return [NaN, NaN];
  const rand = mulberry32(seed);
  const out = [];
  for (let b = 0; b < B; b++) {
    const r = pooled(audits, resample(n, rand), w, t);
    if (!Number.isNaN(r)) out.push(r);
  }
  out.sort((x, y) => x - y);
  return [quantile(out, 0.025), quantile(out, 0.975)];
}

export function summarise(rows, opts = {}) {
  const groups = new Map();
  for (const r of rows) {
    const k = groupKey(r.site, r.bin_stream, r.phase);
    if (!groups.has(k)) groups.set(k, { site: r.site, bin_stream: r.bin_stream, phase: r.phase, rows: [] });
    groups.get(k).rows.push(r);
  }
  const out = [];
  for (const g of groups.values()) {
    const audits = auditTotals(g.rows);
    if (!audits.length) continue;
    const all = audits.map((_, i) => i);
    const wrong = audits.reduce((s, a) => s + a.wrong, 0);
    const total = audits.reduce((s, a) => s + a.total, 0);
    const massOk = audits.every((a) => a.hasAllGrams) && audits.some((a) => a.totalG > 0);
    const dates = audits.map((a) => a.date).filter(Boolean).sort();
    out.push({
      site: g.site,
      bin_stream: g.bin_stream,
      phase: g.phase,
      audits: audits.length,
      items: total,
      misplaced: wrong,
      rate: pooled(audits, all, "wrong", "total"),
      ci_bootstrap: bootstrapRate(audits, opts),
      ci_wilson: wilson(wrong, total),
      mass_rate: massOk ? pooled(audits, all, "wrongG", "totalG") : null,
      first_date: dates[0] || "",
      last_date: dates[dates.length - 1] || "",
      small_sample: audits.length < SMALL_AUDITS || total < SMALL_ITEMS,
    });
  }
  out.sort((a, b) =>
    a.site.localeCompare(b.site) || STREAMS.indexOf(a.bin_stream) - STREAMS.indexOf(b.bin_stream) || a.phase.localeCompare(b.phase));
  return out;
}

// Most common misplaced items in one bin, by item count.
export function topMisplaced(rows, { site, bin_stream, phase = null, k = 3 } = {}) {
  const tally = new Map();
  for (const r of rows) {
    if (r.site !== site || r.bin_stream !== bin_stream) continue;
    if (phase !== null && r.phase !== phase) continue;
    if (r.item_stream === r.bin_stream || r.count === 0) continue;
    const key = r.item.toLowerCase();
    const e = tally.get(key) || { item: r.item, belongs_in: r.item_stream, count: 0 };
    e.count += r.count;
    tally.set(key, e);
  }
  return [...tally.values()].sort((a, b) => b.count - a.count || a.item.localeCompare(b.item)).slice(0, k);
}

// Before/after comparison of one bin. Difference = after - before, so a negative
// difference means fewer misplaced items after.
export function compare(rows, { site, bin_stream, before, after, B = 2000, seed = 7 } = {}) {
  const pick = (ph) => auditTotals(rows.filter((r) => r.site === site && r.bin_stream === bin_stream && r.phase === ph));
  const a = pick(before), b = pick(after);
  if (!a.length || !b.length) return null;
  const ia = a.map((_, i) => i), ib = b.map((_, i) => i);
  const ra = pooled(a, ia, "wrong", "total"), rb = pooled(b, ib, "wrong", "total");
  const rand = mulberry32(seed);
  const diffs = [];
  for (let k = 0; k < B; k++) {
    const x = pooled(a, resample(a.length, rand), "wrong", "total");
    const y = pooled(b, resample(b.length, rand), "wrong", "total");
    if (!Number.isNaN(x) && !Number.isNaN(y)) diffs.push(y - x);
  }
  diffs.sort((x, y) => x - y);
  const ci = [quantile(diffs, 0.025), quantile(diffs, 0.975)];
  let verdict = "no clear change";
  if (ci[1] < 0) verdict = "fewer misplaced items after";
  else if (ci[0] > 0) verdict = "more misplaced items after";
  return {
    site, bin_stream, before, after,
    audits_before: a.length, audits_after: b.length,
    rate_before: ra, rate_after: rb, difference: rb - ra, ci, verdict,
  };
}

export function phases(rows) {
  const seen = [];
  for (const r of rows) if (!seen.includes(r.phase)) seen.push(r.phase);
  return seen;
}
