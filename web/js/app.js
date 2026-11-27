// binaudit browser app. State lives in localStorage; numbers come from stats.js.
import { STREAMS, bins, compare, normaliseRow, parseCSV, phases, summarise, toCSV, topMisplaced, auditTotals } from "./stats.js";

const KEY = "binaudit.rows.v1";
const SAMPLE_KEY = "binaudit.sample.v1";
const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pct = (x, d = 1) => (x == null || Number.isNaN(x) ? "n/a" : (100 * x).toFixed(d) + "%");
const pp = (x) => (x >= 0 ? "+" : "\u2212") + Math.abs(100 * x).toFixed(1) + " pp";
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

let rows = load();
let draft = [];
let catalogue = { items: [] };

function load() {
  try { return (JSON.parse(localStorage.getItem(KEY)) || []).map((r) => normaliseRow(r)); }
  catch { return []; }
}
function save() {
  localStorage.setItem(KEY, JSON.stringify(rows));
  render();
}
const isSample = () => localStorage.getItem(SAMPLE_KEY) === "1";

// ---------- navigation ----------
const SECTIONS = ["log", "results", "signs", "data", "method"];
function route() {
  const id = SECTIONS.includes(location.hash.slice(1)) ? location.hash.slice(1) : "log";
  for (const s of SECTIONS) $(s).hidden = s !== id;
  document.querySelectorAll("nav a").forEach((a) => a.setAttribute("aria-current", a.getAttribute("href") === "#" + id ? "page" : "false"));
}
window.addEventListener("hashchange", route);

// ---------- helpers ----------
function fillSelect(sel, values, labels = values, keep = true) {
  const prev = sel.value;
  sel.innerHTML = values.map((v, i) => `<option value="${esc(v)}">${esc(labels[i])}</option>`).join("");
  if (keep && values.includes(prev)) sel.value = prev;
}
function sites() { return [...new Set(rows.map((r) => r.site))].sort(); }

function ciBar(lo, hi, point, { min = 0, max = 1, zero = false } = {}) {
  const W = 160, H = 16, x = (v) => 4 + ((Math.min(max, Math.max(min, v)) - min) / (max - min)) * (W - 8);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => min + t * (max - min));
  return `<svg class="ci" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${pct(point)} (${pct(lo)} to ${pct(hi)})">
    <line class="axis" x1="4" x2="${W - 4}" y1="${H / 2}" y2="${H / 2}"/>
    ${ticks.map((t) => `<line class="tick" x1="${x(t)}" x2="${x(t)}" y1="${H / 2 - 3}" y2="${H / 2 + 3}"/>`).join("")}
    ${zero ? `<line class="zero" x1="${x(0)}" x2="${x(0)}" y1="1" y2="${H - 1}"/>` : ""}
    ${Number.isNaN(lo) ? "" : `<line class="range" x1="${x(lo)}" x2="${x(hi)}" y1="${H / 2}" y2="${H / 2}"/>`}
    <line class="point" x1="${x(point)}" x2="${x(point)}" y1="2" y2="${H - 2}"/>
  </svg>`;
}

// ---------- log an audit ----------
function findItem(name) {
  const n = name.trim().toLowerCase();
  return catalogue.items.find((i) => i.name.toLowerCase() === n);
}
$("f-item").addEventListener("input", () => {
  const hit = findItem($("f-item").value);
  if (hit) { $("f-stream").value = hit.stream; $("item-hint").textContent = hit.note ? `${cap(hit.stream)}. ${hit.note}` : `${cap(hit.stream)} under the catalogue.`; }
  else $("item-hint").textContent = $("f-item").value.trim() ? "Not in the catalogue. Choose where it belongs." : "";
});
$("item-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const item = $("f-item").value.trim();
  if (!item) return;
  const count = Math.max(1, parseInt($("f-count").value, 10) || 1);
  const g = $("f-grams").value === "" ? null : Number($("f-grams").value);
  const same = draft.find((d) => d.item.toLowerCase() === item.toLowerCase() && d.item_stream === $("f-stream").value);
  if (same) { same.count += count; if (g != null) same.grams = (same.grams || 0) + g; }
  else draft.push({ item, item_stream: $("f-stream").value, count, grams: g });
  $("f-item").value = ""; $("f-count").value = 1; $("f-grams").value = ""; $("item-hint").textContent = "";
  $("f-item").focus();
  renderDraft();
});
function renderDraft() {
  const bin = $("f-bin").value;
  const tb = $("draft-table").querySelector("tbody");
  $("draft-table").hidden = !draft.length;
  tb.innerHTML = draft.map((d, i) => {
    const wrong = d.item_stream !== bin;
    return `<tr><td>${esc(d.item)}</td><td class="${wrong ? "mis" : ""}">${cap(d.item_stream)}${wrong ? " (wrong bin)" : ""}</td>
      <td class="num">${d.count}</td><td class="num">${d.grams ?? ""}</td>
      <td><button class="link" data-rm="${i}" aria-label="Remove ${esc(d.item)}">Remove</button></td></tr>`;
  }).join("");
  const total = draft.reduce((s, d) => s + d.count, 0);
  const wrong = draft.filter((d) => d.item_stream !== bin).reduce((s, d) => s + d.count, 0);
  $("draft-tally").innerHTML = total ? `${total} items, <span class="mis">${wrong} misplaced</span> (${pct(wrong / total)}) in the ${bin} bin` : "";
  $("save-audit").disabled = !total;
}
$("draft-table").addEventListener("click", (e) => {
  const i = e.target.dataset.rm;
  if (i != null) { draft.splice(Number(i), 1); renderDraft(); }
});
$("f-bin").addEventListener("change", renderDraft);
$("save-audit").addEventListener("click", () => {
  const site = $("f-site").value.trim();
  const date = $("f-date").value;
  const bin = $("f-bin").value;
  const phase = $("f-phase").value.trim();
  if (!site || !date) { $("save-hint").textContent = "Add a site and a date first."; return; }
  if (isSample()) { rows = []; localStorage.removeItem(SAMPLE_KEY); }
  const initials = site.replace(/[^A-Za-z0-9]+/g, " ").trim().split(" ").map((w) => w[0]).join("").toUpperCase().slice(0, 4);
  const id = `${initials}-${bin.slice(0, 3).toUpperCase()}-${date.replace(/-/g, "").slice(4)}-${Math.random().toString(36).slice(2, 6)}`;
  for (const d of draft) rows.push(normaliseRow({ audit_id: id, date, site, bin_stream: bin, phase, ...d }));
  const n = draft.reduce((s, d) => s + d.count, 0);
  draft = [];
  save();
  renderDraft();
  $("save-hint").textContent = `Saved ${n} items as audit ${id}.`;
});

// ---------- results ----------
function renderResults() {
  const all = sites();
  fillSelect($("r-site"), all);
  const site = $("r-site").value;
  const mine = rows.filter((r) => r.site === site);
  const sums = summarise(mine);
  $("summary-empty").hidden = sums.length > 0;
  $("summary-table").hidden = !sums.length;
  $("summary-table").querySelector("tbody").innerHTML = sums.map((s) => `<tr>
    <td>${cap(s.bin_stream)}</td><td>${esc(s.phase || "-")}</td>
    <td class="num">${s.audits}</td><td class="num">${s.items}</td><td class="num mis">${s.misplaced}</td>
    <td class="num">${pct(s.rate)}</td>
    <td class="num">${s.audits < 2 ? '<span class="flag">needs 2+ audits</span>' : `${pct(s.ci_bootstrap[0])} to ${pct(s.ci_bootstrap[1])}${s.small_sample ? ' <span class="flag">small sample</span>' : ""}`}</td>
    <td>${s.audits < 2 ? ciBar(NaN, NaN, s.rate) : ciBar(s.ci_bootstrap[0], s.ci_bootstrap[1], s.rate)}</td></tr>`).join("");

  const ph = phases(mine);
  fillSelect($("c-before"), ph, ph.map((p) => p || "(no phase)"));
  fillSelect($("c-after"), ph, ph.map((p) => p || "(no phase)"));
  if (ph.length > 1 && $("c-before").value === $("c-after").value) { $("c-before").value = ph[0]; $("c-after").value = ph[ph.length - 1]; }
  const before = $("c-before").value, after = $("c-after").value;
  const cmps = before !== after ? STREAMS.map((b) => compare(mine, { site, bin_stream: b, before, after })).filter(Boolean) : [];
  $("compare-empty").hidden = cmps.length > 0;
  $("compare-table").hidden = !cmps.length;
  $("compare-table").querySelector("tbody").innerHTML = cmps.map((c) => `<tr>
    <td>${cap(c.bin_stream)}</td>
    <td class="num">${pct(c.rate_before)} <span class="muted">(${c.audits_before})</span></td>
    <td class="num">${pct(c.rate_after)} <span class="muted">(${c.audits_after})</span></td>
    <td class="num">${pp(c.difference)}</td>
    <td class="num">${pp(c.ci[0])} to ${pp(c.ci[1])}</td>
    <td>${ciBar(c.ci[0], c.ci[1], c.difference, { min: -0.5, max: 0.5, zero: true })}</td>
    <td>${c.verdict}</td></tr>`).join("");

  const latest = ph[ph.length - 1];
  const top = STREAMS.flatMap((b) => topMisplaced(mine, { site, bin_stream: b, phase: latest ?? null }).map((m) => ({ ...m, bin: b })));
  $("top-table").querySelector("tbody").innerHTML = top.length
    ? top.map((m) => `<tr><td>${cap(m.bin)}</td><td>${esc(m.item)}</td><td class="mis">${cap(m.belongs_in)}</td><td class="num">${m.count}</td></tr>`).join("")
    : `<tr><td colspan="4" class="empty">Nothing misplaced yet.</td></tr>`;
}
["r-site", "c-before", "c-after"].forEach((id) => $(id).addEventListener("change", renderResults));

// ---------- signs ----------
function renderSign() {
  fillSelect($("s-site"), sites());
  const site = $("s-site").value;
  const binsHere = STREAMS.filter((b) => rows.some((r) => r.site === site && r.bin_stream === b));
  if (binsHere.length && !binsHere.includes($("s-bin").value)) $("s-bin").value = binsHere[0];
  const bin = $("s-bin").value;
  const mine = rows.filter((r) => r.site === site && r.bin_stream === bin);
  const ph = phases(mine);
  const prev = $("s-phase").value;
  fillSelect($("s-phase"), ph, ph.map((p) => p || "(no phase)"), false);
  $("s-phase").value = ph.includes(prev) ? prev : ph[ph.length - 1] ?? "";
  const phase = $("s-phase").value;
  const used = mine.filter((r) => r.phase === phase);
  const top = topMisplaced(used, { site, bin_stream: bin, phase });
  const audits = auditTotals(used);
  const dates = audits.map((a) => a.date).filter(Boolean).sort();
  const total = audits.reduce((s, a) => s + a.total, 0);
  $("print-sign").disabled = !top.length;
  if (!site) { $("sign").innerHTML = '<p class="empty">No audits yet.</p>'; return; }
  if (!top.length) { $("sign").innerHTML = `<p class="empty">No misplaced items found in the ${bin} bin for this phase.</p>`; return; }
  $("sign").innerHTML = `<article class="sign" aria-label="Printable sign">
    <div class="kicker">${esc(site)}</div>
    <h4>${cap(bin)} waste only</h4>
    <p class="lead">Most often put here by mistake:</p>
    <ol>${top.map((m) => `<li><b>${esc(m.item)}</b><span>goes in the ${m.belongs_in} bin</span></li>`).join("")}</ol>
    <div class="rest">Based on ${audits.length} audit${audits.length === 1 ? "" : "s"} of this bin (${total} items)${dates.length ? `, ${dates[0]} to ${dates[dates.length - 1]}` : ""}.${isSample() ? " Synthetic sample data." : ""}<br>Made with binaudit.</div>
  </article>`;
}
["s-site", "s-bin", "s-phase"].forEach((id) => $(id).addEventListener("change", renderSign));
$("print-sign").addEventListener("click", () => window.print());

// ---------- data ----------
function renderData() {
  const audits = new Map();
  for (const r of rows) {
    const a = audits.get(r.audit_id) || { ...r, items: 0, wrong: 0 };
    a.items += r.count; if (r.item_stream !== r.bin_stream) a.wrong += r.count;
    audits.set(r.audit_id, a);
  }
  $("data-count").textContent = `${audits.size} audits, ${rows.reduce((s, r) => s + r.count, 0)} items, ${sites().length} sites.`;
  $("audit-table").querySelector("tbody").innerHTML = [...audits.values()].reverse().map((a) => `<tr>
    <td class="num" style="text-align:left">${esc(a.audit_id)}</td><td class="num" style="text-align:left">${esc(a.date)}</td><td>${esc(a.site)}</td>
    <td>${cap(a.bin_stream)}</td><td>${esc(a.phase || "-")}</td><td class="num">${a.items}</td><td class="num mis">${a.wrong}</td>
    <td><button class="link" data-del="${esc(a.audit_id)}">Delete</button></td></tr>`).join("");
}
$("audit-table").addEventListener("click", (e) => {
  const id = e.target.dataset.del;
  if (id && confirm(`Delete audit ${id}?`)) { rows = rows.filter((r) => r.audit_id !== id); save(); }
});
$("export-csv").addEventListener("click", () => {
  const blob = new Blob([toCSV(rows)], { type: "text/csv" });
  const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: `binaudit-${new Date().toISOString().slice(0, 10)}.csv` });
  a.click(); URL.revokeObjectURL(a.href);
});
$("import-csv").addEventListener("change", async (e) => {
  const f = e.target.files[0];
  if (!f) return;
  try {
    const add = parseCSV(await f.text());
    if (isSample()) { rows = []; localStorage.removeItem(SAMPLE_KEY); }
    const have = new Set(rows.map((r) => r.audit_id));
    const fresh = add.filter((r) => !have.has(r.audit_id));
    rows = rows.concat(fresh);
    save();
    $("data-hint").textContent = `Imported ${fresh.length} rows${fresh.length < add.length ? `; skipped ${add.length - fresh.length} rows from audits already here` : ""}.`;
  } catch (err) { $("data-hint").textContent = "Could not import: " + err.message; }
  e.target.value = "";
});
$("load-sample").addEventListener("click", async () => {
  if (rows.length && !isSample() && !confirm("Replace your data with the synthetic sample? Export it first if you want to keep it.")) return;
  rows = parseCSV(await (await fetch("data/sample-audits.csv")).text());
  localStorage.setItem(SAMPLE_KEY, "1");
  save();
  $("data-hint").textContent = "Loaded the synthetic sample.";
});
$("clear-data").addEventListener("click", () => {
  if (!rows.length || confirm("Delete every audit stored in this browser?")) { rows = []; localStorage.removeItem(SAMPLE_KEY); save(); $("data-hint").textContent = "Deleted."; }
});

// ---------- render ----------
function render() {
  $("sample-notice").hidden = !isSample();
  $("dl-sites").innerHTML = sites().map((s) => `<option value="${esc(s)}">`).join("");
  $("dl-phases").innerHTML = phases(rows).filter(Boolean).map((p) => `<option value="${esc(p)}">`).join("");
  renderResults(); renderSign(); renderData();
}

async function init() {
  $("f-date").value = new Date().toISOString().slice(0, 10);
  try { catalogue = await (await fetch("data/items.json")).json(); } catch { /* the app still works without suggestions */ }
  $("dl-items").innerHTML = catalogue.items.map((i) => `<option value="${esc(i.name)}">`).join("");
  if (!rows.length && !localStorage.getItem(KEY)) {
    try { rows = parseCSV(await (await fetch("data/sample-audits.csv")).text()); localStorage.setItem(SAMPLE_KEY, "1"); save(); } catch { /* offline first run */ }
  }
  route(); render(); renderDraft();
}
init();
