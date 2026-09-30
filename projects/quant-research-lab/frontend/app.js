"use strict";
const API = location.pathname.startsWith("/demos/") ? "/api/projects/quant-research-lab/api" : "/api";
const $ = (selector) => document.querySelector(selector);
const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
const pct = (value, digits = 2) => value === null || value === undefined ? "n/a" : `${(value * 100).toFixed(digits)}%`;
const num = (value, digits = 3) => value === null || value === undefined ? "n/a" : Number(value).toFixed(digits);
const MODEL_NAMES = { random_walk: "Random walk (baseline)", historical_mean: "Historical mean", ridge: "Ridge regression", random_forest: "Random forest", gradient_boosting: "Gradient boosting" };
let datasets = [];
let riskFor = null, activeRuns = 0;
const runTokens = {};

async function request(path, options = {}) {
  let response;
  try { response = await fetch(API + path, { ...options, headers: { "Content-Type": "application/json", ...options.headers } }); }
  catch { throw new Error("The research service is unreachable. Check that it is running, then try again."); }
  const text = await response.text();
  let data = {};
  try { data = text ? JSON.parse(text) : {}; } catch { data = text; }
  if (!response.ok) {
    const detail = data.detail;
    throw new Error(Array.isArray(detail) ? detail.map((issue) => `${issue.loc.at(-1)}: ${issue.msg}`).join("; ") : detail || `Request failed (${response.status}).`);
  }
  return data;
}
function notice(message, error = false) { const el = $("#notice"); el.hidden = !message; el.textContent = message; el.dataset.error = error; }
const datasetId = () => $("#dataset").value;
const current = () => datasets.find((item) => item.id === datasetId());

function lineChart(points, series, { height = 260, label }) {
  const width = 900, pad = { l: 56, r: 16, t: 16, b: 28 };
  const values = points.flatMap((point) => series.map((item) => point[item.key])).filter(Number.isFinite);
  if (!values.length) return "";
  let min = Math.min(...values), max = Math.max(...values);
  if (min === max) { min -= 1; max += 1; }
  const x = (i) => pad.l + (i / Math.max(points.length - 1, 1)) * (width - pad.l - pad.r);
  const y = (v) => pad.t + (1 - (v - min) / (max - min)) * (height - pad.t - pad.b);
  const ticks = [0, 0.5, 1].map((f) => min + f * (max - min));
  const grid = ticks.map((v) => `<line x1="${pad.l}" x2="${width - pad.r}" y1="${y(v)}" y2="${y(v)}" class="grid"/><text x="${pad.l - 8}" y="${y(v) + 4}" text-anchor="end">${v.toFixed(v >= 100 ? 0 : 2)}</text>`).join("");
  const dates = [0, points.length - 1].map((i) => `<text x="${x(i)}" y="${height - 6}" text-anchor="${i ? "end" : "start"}">${points[i].date}</text>`).join("");
  const lines = series.map((item) => `<polyline class="${item.className}" points="${points.map((p, i) => `${x(i).toFixed(1)},${y(p[item.key]).toFixed(1)}`).join(" ")}"/>`).join("");
  const legend = series.map((item) => `<span class="legend-item ${item.className}">${escapeHTML(item.label)}</span>`).join("");
  return `<figure class="chart"><svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHTML(label)}">${grid}${lines}${dates}</svg><figcaption>${legend}</figcaption></figure>`;
}

function renderDatasets() {
  $("#dataset").innerHTML = datasets.map((item) => `<option value="${escapeHTML(item.id)}">${escapeHTML(item.name)}</option>`).join("");
  describe();
}
function describe() {
  const item = current();
  $("#dataset-meta").textContent = item ? `${item.rows.toLocaleString()} rows · ${item.start} to ${item.end} · ${item.periods_per_year} trading days/year · ${item.source}` : "";
}
async function loadDatasets(select) {
  datasets = await request("/datasets");
  renderDatasets();
  if (select) $("#dataset").value = select;
  describe();
}

function formValues(form) {
  return Object.fromEntries([...new FormData(form)].map(([key, value]) => [key, Number(value)]));
}
function setRunning(delta) {
  activeRuns += delta;
  for (const button of document.querySelectorAll("button.primary")) button.disabled = activeRuns > 0;
}
// Each result box renders only its latest run, so a slow reply for a previous dataset never replaces newer output.
async function run(target, action, render, message = "Running…") {
  const box = $(target), token = (runTokens[target] = (runTokens[target] || 0) + 1);
  box.setAttribute("aria-busy", "true");
  box.innerHTML = `<p class="loading">${escapeHTML(message)}</p>`;
  setRunning(1);
  try {
    const html = render(await action());
    if (token === runTokens[target]) { box.innerHTML = html; notice(""); }
  } catch (error) { if (token === runTokens[target]) box.innerHTML = `<p class="error" role="alert">${escapeHTML(error.message)}</p>`; }
  finally { if (token === runTokens[target]) box.setAttribute("aria-busy", "false"); setRunning(-1); }
}

function renderForecast(data) {
  const ev = data.evaluation;
  const rows = data.scores.map((row) => {
    const better = row.dm_statistic !== null && row.dm_statistic < 0 && row.dm_p_value < 0.05;
    const worse = row.dm_statistic !== null && row.dm_statistic > 0 && row.dm_p_value < 0.05;
    const verdict = row.model === "random_walk" ? "Baseline" : better ? "Beats baseline" : worse ? "Worse than baseline" : "No significant difference";
    return `<tr><th scope="row">${escapeHTML(MODEL_NAMES[row.model] || row.model)}</th><td>${num(row.rmse, 5)}</td><td>${pct(row.directional_accuracy, 1)}</td><td>${num(row.r2_vs_random_walk, 4)}</td><td>${num(row.dm_p_value)}</td><td><span class="verdict ${better ? "good" : worse ? "bad" : ""}">${verdict}</span></td><td>${pct(row.strategy_return, 1)}</td><td>${num(row.strategy_sharpe, 2)}</td></tr>`;
  }).join("");
  const winners = data.scores.filter((row) => row.dm_statistic !== null && row.dm_statistic < 0 && row.dm_p_value < 0.05);
  return `<div class="finding"><strong>${winners.length ? `${winners.length} model(s) beat the random walk at the 5% level.` : "No model beats the random walk at the 5% level."}</strong> ${ev.test_rows.toLocaleString()} out-of-sample days (${ev.test_start} to ${ev.test_end}), retrained every ${ev.retrain_every} rows on an expanding window. Buy and hold over the same days: ${pct(ev.buy_and_hold_return, 1)}.</div>
  <div class="table-wrap"><table><caption class="sr-only">Out-of-sample model scores</caption><thead><tr><th scope="col">Model</th><th scope="col">RMSE</th><th scope="col">Direction hit rate</th><th scope="col">R² vs random walk</th><th scope="col">Diebold-Mariano p</th><th scope="col">Verdict</th><th scope="col">Long-when-positive return</th><th scope="col">Sharpe</th></tr></thead><tbody>${rows}</tbody></table></div>
  <p class="meta">Features at each date use only data up to that close: ${ev.features.map(escapeHTML).join(", ")}. The target is the next day's log return.</p>`;
}

function renderStrategy(data) {
  const s = data.strategy, b = data.buy_and_hold;
  const metric = (label, a, c, fmt) => `<tr><th scope="row">${label}</th><td>${fmt(a)}</td><td>${fmt(c)}</td></tr>`;
  return `${lineChart(data.equity, [{ key: "strategy", label: "TTPS strategy", className: "series-a" }, { key: "buy_and_hold", label: "Buy and hold", className: "series-b" }], { label: "Growth of 1 unit invested" })}
  <div class="table-wrap narrow"><table><caption class="sr-only">Strategy and benchmark performance</caption><thead><tr><th></th><th scope="col">Strategy</th><th scope="col">Buy and hold</th></tr></thead><tbody>
  ${metric("Total return", s.total_return, b.total_return, (v) => pct(v, 1))}${metric("CAGR", s.cagr, b.cagr, (v) => pct(v, 1))}${metric("Annual volatility", s.annual_volatility, b.annual_volatility, (v) => pct(v, 1))}${metric("Sharpe", s.sharpe, b.sharpe, (v) => num(v, 2))}${metric("Max drawdown", s.max_drawdown, b.max_drawdown, (v) => pct(v, 1))}${metric("Time in market", s.exposure, b.exposure, (v) => pct(v, 0))}${metric("Position changes", s.trades, b.trades, String)}
  </tbody></table></div>
  <p class="meta">Signals are computed at each close and traded on the next bar. Weights are fixed inputs, not tuned on this data; tuning them here would overfit the backtest.</p>`;
}

function renderRisk(data) {
  const g = data.garch;
  const card = (label, value, hint) => `<div class="stat"><span>${label}</span><strong>${value}</strong><small>${hint}</small></div>`;
  return `${lineChart(data.prices, [{ key: "close", label: "Close", className: "series-a" }], { label: "Closing price" })}
  <div class="stats">
    ${card("Annual volatility", pct(data.annual_volatility, 1), `annual return ${pct(data.annual_return, 1)}`)}
    ${card("95% one-day VaR", pct(data.var_95.historical_var), `expected shortfall ${pct(data.var_95.historical_cvar)}`)}
    ${card("99% one-day VaR", pct(data.var_99.historical_var), `Gaussian estimate ${pct(data.var_99.gaussian_var)}`)}
    ${card("GARCH 5-day vol", pct(g.forecast_daily_volatility), `daily · long-run ${pct(g.long_run_daily_volatility)}`)}
    ${card("GARCH persistence", num(g.persistence), `α ${num(g.alpha)} · β ${num(g.beta)}`)}
    ${card("Hurst exponent", num(data.hurst, 2), "≈0.5 no memory · >0.5 trending")}
    ${card("Tails", num(data.excess_kurtosis, 2), `excess kurtosis · skew ${num(data.skew, 2)}`)}
  </div>
  <p class="meta">${data.observations.toLocaleString()} daily log returns. GARCH(1,1) is fitted by Gaussian maximum likelihood${g.converged ? "" : " (optimizer did not fully converge)"}.</p>`;
}

const TABS = ["forecast", "strategy", "risk"];
function selectTab(name, focus = false) {
  for (const tab of TABS) {
    $(`#tab-${tab}`).setAttribute("aria-selected", String(tab === name));
    $(`#tab-${tab}`).tabIndex = tab === name ? 0 : -1;
    $(`#view-${tab}`).hidden = tab !== name;
  }
  if (focus) $(`#tab-${name}`).focus();
  if (name === "risk" && riskFor !== datasetId()) {
    riskFor = datasetId();
    run("#risk-result", () => request(`/risk/${encodeURIComponent(datasetId())}`), renderRisk, "Fitting GARCH and computing tail risk…");
  }
}

$("#dataset").addEventListener("change", () => {
  describe(); riskFor = null;
  for (const id of ["#forecast-result", "#strategy-result", "#risk-result"]) { runTokens[id] = (runTokens[id] || 0) + 1; $(id).setAttribute("aria-busy", "false"); }
  for (const [id, text] of [["#forecast-result", "Run the study to compare models out of sample."], ["#strategy-result", "Run the backtest to compare the signal with buy and hold."], ["#risk-result", "Select the Risk tab to analyze the dataset."]]) $(id).innerHTML = `<p class="empty">${text}</p>`;
  if (!$("#view-risk").hidden) selectTab("risk");
});
for (const tab of TABS) $(`#tab-${tab}`).addEventListener("click", () => selectTab(tab));
$(".tabs").addEventListener("keydown", (event) => {
  const index = TABS.findIndex((tab) => $(`#tab-${tab}`).getAttribute("aria-selected") === "true");
  const next = { ArrowRight: index + 1, ArrowLeft: index - 1, Home: 0, End: TABS.length - 1 }[event.key];
  if (next === undefined) return;
  event.preventDefault();
  selectTab(TABS[(next + TABS.length) % TABS.length], true);
});
selectTab("forecast");
$("#forecast-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const body = JSON.stringify({ dataset_id: datasetId(), ...formValues(event.currentTarget) });
  run("#forecast-result", () => request("/forecast", { method: "POST", body }), renderForecast,
    "Running the walk-forward study… every model is retrained many times, which can take up to half a minute.");
});
$("#strategy-form").addEventListener("submit", (event) => {
  event.preventDefault();
  const body = JSON.stringify({ dataset_id: datasetId(), ...formValues(event.currentTarget) });
  run("#strategy-result", () => request("/strategy", { method: "POST", body }), renderStrategy, "Running the backtest…");
});
$("#report").addEventListener("click", async () => {
  const button = $("#report");
  button.disabled = true; notice("Building the report…");
  try {
    const text = await request(`/report/${encodeURIComponent(datasetId())}`);
    const link = Object.assign(document.createElement("a"), { href: URL.createObjectURL(new Blob([text], { type: "text/markdown" })), download: `${datasetId()}-report.md` });
    link.click(); URL.revokeObjectURL(link.href); notice("Report downloaded.");
  } catch (error) { notice(error.message, true); }
  finally { button.disabled = false; }
});
$("#upload-open").addEventListener("click", () => { $("#upload-form").reset(); $("#upload-error").hidden = true; $("#upload-dialog").showModal(); });
for (const button of document.querySelectorAll("[data-close]")) button.addEventListener("click", () => $("#upload-dialog").close());
$("#upload-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget, file = form.elements.file.files[0];
  if (file.size > 2_000_000) { $("#upload-error").textContent = "Choose a CSV smaller than 2 MB."; $("#upload-error").hidden = false; return; }
  $("#upload-submit").disabled = true;
  try {
    const created = await request("/datasets", { method: "POST", body: JSON.stringify({ name: form.elements.name.value, csv: await file.text() }) });
    $("#upload-dialog").close();
    await loadDatasets(created.id);
    $("#dataset").dispatchEvent(new Event("change"));
    notice(`${created.name} added: ${created.rows.toLocaleString()} rows.`);
  } catch (error) { $("#upload-error").textContent = error.message; $("#upload-error").hidden = false; }
  finally { $("#upload-submit").disabled = false; }
});

loadDatasets().catch((error) => { $("#dataset-meta").textContent = ""; notice(error.message, true); });
