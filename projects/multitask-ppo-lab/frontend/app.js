"use strict";
const API = location.pathname.startsWith("/demos/") ? "/api/projects/multitask-ppo-lab/api" : "/api";
const $ = (selector) => document.querySelector(selector);
const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
const pct = (value) => value === null || value === undefined ? "n/a" : `${(value * 100).toFixed(1)}%`;
const TASK_NAMES = { navigation: "Navigation", key_door: "Key and door" };
const POLICY_NAMES = { random: "Random", ppo_sampled: "PPO (sampled)", ppo_greedy: "PPO (greedy)", ppo: "PPO agent", oracle: "Optimal (BFS)" };
const REPLAY_POLICIES = ["random", "ppo", "oracle"];
let playback = null, replayToken = 0;

async function request(path, options = {}) {
  let response;
  try { response = await fetch(API + path, { ...options, headers: { "Content-Type": "application/json", ...options.headers } }); }
  catch { throw new Error("The service is unreachable. Check that it is running, then try again."); }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(Array.isArray(data.detail) ? data.detail.map((d) => d.msg).join("; ") : data.detail || `Request failed (${response.status}).`);
  return data;
}
function notice(message, error = false) { const el = $("#notice"); el.hidden = !message; el.textContent = message; el.dataset.error = error; }

function board(frame) {
  const cells = frame.rows.map((row) => [...row].map((ch) => {
    const kind = { "#": "wall", A: "agent", G: "goal", K: "key", ".": "floor" }[ch];
    return `<span class="cell ${kind}">${ch === "A" || ch === "G" || ch === "K" ? ch : ""}</span>`;
  }).join("")).join("");
  return `<div class="grid" style="--n:${frame.rows.length}" aria-hidden="true">${cells}</div>`;
}

function renderEpisodes(episodes, index) {
  $("#boards").innerHTML = episodes.map((ep) => {
    const i = Math.min(index, ep.frames.length - 1);
    const done = i === ep.frames.length - 1;
    const status = done ? (ep.success ? `Solved in ${ep.steps} steps` : `Gave up after ${ep.steps} steps`) : `Step ${i} · ${escapeHTML(ep.actions[i - 1] ?? "start")}`;
    return `<article class="episode ${done ? (ep.success ? "won" : "lost") : ""}"><h3>${POLICY_NAMES[ep.policy]}</h3>${board(ep.frames[i])}
      <p class="status">${status}${ep.frames[i].has_key ? " · carrying key" : ""}</p><p class="meta">Optimal: ${ep.optimal_steps} steps</p></article>`;
  }).join("");
}

function stopPlayback() { if (playback) clearInterval(playback); playback = null; }
function announce(episodes) {
  $("#replay-status").textContent = `${TASK_NAMES[episodes[0].task]}, layout ${episodes[0].seed}: ` + episodes.map((ep) =>
    `${POLICY_NAMES[ep.policy]} ${ep.success ? `solved it in ${ep.steps} steps` : `gave up after ${ep.steps} steps`}`).join("; ") + `. Optimal: ${episodes[0].optimal_steps} steps.`;
}

async function play(event) {
  event?.preventDefault();
  // Only the latest request may animate; a slower earlier reply must not start a second animation.
  const token = ++replayToken;
  stopPlayback();
  const task = $("#task").value, seed = Number($("#seed").value);
  $("#play").disabled = true;
  $("#boards").setAttribute("aria-busy", "true");
  try {
    const episodes = await Promise.all(REPLAY_POLICIES.map((policy) => request("/episodes", { method: "POST", body: JSON.stringify({ task, policy, seed }) })));
    if (token !== replayToken) return;
    const longest = Math.max(...episodes.map((ep) => ep.frames.length));
    const limit = Math.min(longest, 80);
    let index = 0;
    notice("");
    renderEpisodes(episodes, 0);
    const finish = () => { stopPlayback(); renderEpisodes(episodes, longest - 1); announce(episodes); };
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) { finish(); return; }
    playback = setInterval(() => {
      index += 1;
      if (index >= limit) finish(); else renderEpisodes(episodes, index);
    }, 140);
  } catch (error) { if (token === replayToken) notice(error.message, true); }
  finally { if (token === replayToken) { $("#play").disabled = false; $("#boards").setAttribute("aria-busy", "false"); } }
}

function curveChart(points, key, label) {
  const width = 460, height = 170, pad = { l: 40, r: 10, t: 12, b: 24 };
  const values = points.map((p) => p[key]).filter(Number.isFinite);
  if (!values.length) return "";
  const min = key === "success_rate" ? 0 : Math.min(...values), max = key === "success_rate" ? 1 : Math.max(...values);
  const span = max - min || 1;
  const x = (i) => pad.l + (i / Math.max(points.length - 1, 1)) * (width - pad.l - pad.r);
  const y = (v) => pad.t + (1 - (v - min) / span) * (height - pad.t - pad.b);
  const line = points.map((p, i) => Number.isFinite(p[key]) ? `${x(i).toFixed(1)},${y(p[key]).toFixed(1)}` : "").filter(Boolean).join(" ");
  const fmt = (v) => key === "success_rate" ? `${Math.round(v * 100)}%` : v.toFixed(1);
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${escapeHTML(label)}"><line class="grid" x1="${pad.l}" x2="${width - pad.r}" y1="${y(max)}" y2="${y(max)}"/><line class="grid" x1="${pad.l}" x2="${width - pad.r}" y1="${y(min)}" y2="${y(min)}"/><text x="${pad.l - 6}" y="${y(max) + 4}" text-anchor="end">${fmt(max)}</text><text x="${pad.l - 6}" y="${y(min) + 4}" text-anchor="end">${fmt(min)}</text><polyline points="${line}"/><text x="${pad.l}" y="${height - 6}">update 1</text><text x="${width - pad.r}" y="${height - 6}" text-anchor="end">update ${points.at(-1).update}</text></svg>`;
}

function renderSummary(data) {
  const t = data.training;
  const minutes = data.training_seconds ? `${(data.training_seconds / 60).toFixed(1)} min on CPU` : "n/a";
  const steps = data.env_steps ?? t.updates * t.num_envs * t.rollout_steps * t.tasks.length;
  $("#facts").innerHTML = [["Environment steps", steps.toLocaleString()], ["Training time", minutes], ["Parameters", data.parameters.toLocaleString()], ["Grid", `${t.size} × ${t.size}`]]
    .map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join("");
  const rows = data.evaluation.map((r) => `<tr class="${r.policy.startsWith("ppo") ? "highlight" : ""}"><th scope="row">${TASK_NAMES[r.task]}</th><td>${POLICY_NAMES[r.policy]}</td><td>${pct(r.success_rate)}</td><td>${r.mean_steps.toFixed(1)}</td><td>${r.optimality === null ? "n/a" : pct(r.optimality)}</td><td>${r.mean_return.toFixed(2)}</td></tr>`).join("");
  $("#evaluation").innerHTML = `<table><caption class="sr-only">Evaluation on held-out layouts</caption><thead><tr><th scope="col">Task</th><th scope="col">Policy</th><th scope="col">Success</th><th scope="col">Mean steps</th><th scope="col">Optimality</th><th scope="col">Mean return</th></tr></thead><tbody>${rows}</tbody></table>`;
  $("#curves").innerHTML = `<div class="curves">${Object.entries(data.curves).map(([task, points]) => `<figure><figcaption>${TASK_NAMES[task]} · training success rate</figcaption>${curveChart(points, "success_rate", `${TASK_NAMES[task]} success rate by update`)}</figure><figure><figcaption>${TASK_NAMES[task]} · policy entropy</figcaption>${curveChart(points, "entropy", `${TASK_NAMES[task]} entropy by update`)}</figure>`).join("")}</div>`;
}

$("#replay-form").addEventListener("submit", play);
$("#shuffle").addEventListener("click", () => { $("#seed").value = Math.floor(Math.random() * 100000); play(); });
$("#task").addEventListener("change", () => play());
request("/summary").then((data) => { renderSummary(data); play(); }).catch((error) => {
  notice(error.message, true);
  for (const id of ["#evaluation", "#curves"]) $(id).innerHTML = "";
  $("#facts").innerHTML = "<div><dt>Status</dt><dd>No trained policy</dd></div>";
});
