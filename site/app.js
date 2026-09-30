"use strict";
/* Showcase site: vanilla JavaScript, no build step. Data comes from data/*.json,
   generated from the projects by build_data.py. */

// Where the source lives once the repository is published. Change REPO_NAME if the repository is named differently.
const REPO_NAME = "showcase";
const REPLAY_CAP = 60;
const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const pct = (value, digits = 1) => value === null || value === undefined ? "—" : `${(value * 100).toFixed(digits)}%`;

async function load(name) {
  const response = await fetch(`data/${name}.json`);
  if (!response.ok) throw new Error(`Could not load ${name}`);
  return response.json();
}

function toast(message) {
  const el = $("#toast");
  el.textContent = message; el.hidden = false;
  clearTimeout(toast.timer); toast.timer = setTimeout(() => { el.hidden = true; }, 2600);
}

/* ---------- Theme, progress, navigation, reveal ---------- */
function setupChrome() {
  const root = document.documentElement;
  let saved = null;
  try { saved = localStorage.getItem("theme"); } catch { /* storage unavailable */ }
  const apply = (theme) => {
    root.dataset.theme = theme;
    $("#theme").setAttribute("aria-label", theme === "dark" ? "Switch to light theme" : "Switch to dark theme");
    $('meta[name="theme-color"]').content = theme === "dark" ? "#0b0f14" : "#f6f4ef";
  };
  apply(saved || (matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark"));
  $("#theme").addEventListener("click", () => {
    const next = root.dataset.theme === "dark" ? "light" : "dark";
    apply(next);
    try { localStorage.setItem("theme", next); } catch { /* ignore */ }
  });

  const onScroll = () => {
    const max = document.documentElement.scrollHeight - innerHeight;
    $("#progress").style.width = `${max > 0 ? (scrollY / max) * 100 : 0}%`;
    $("#nav").classList.toggle("scrolled", scrollY > 10);
  };
  addEventListener("scroll", onScroll, { passive: true }); onScroll();

  const sections = $$("main section[id]");
  const links = new Map($$(".nav nav a").map((a) => [a.getAttribute("href").slice(1), a]));
  const spy = new IntersectionObserver((entries) => {
    for (const entry of entries) if (entry.isIntersecting) {
      links.forEach((a) => a.classList.remove("active"));
      links.get(entry.target.id)?.classList.add("active");
    }
  }, { rootMargin: "-45% 0px -50% 0px" });
  sections.forEach((s) => spy.observe(s));

  const reveal = new IntersectionObserver((entries) => {
    for (const entry of entries) if (entry.isIntersecting) { entry.target.classList.add("in"); reveal.unobserve(entry.target); }
  }, { rootMargin: "0px 0px -8% 0px" });
  $$(".reveal").forEach((el, i) => { el.style.transitionDelay = `${Math.min(i % 4, 3) * 70}ms`; reveal.observe(el); });

  const counters = new IntersectionObserver((entries) => {
    for (const entry of entries) if (entry.isIntersecting) { countUp(entry.target); counters.unobserve(entry.target); }
  });
  $$("[data-count]").forEach((el) => counters.observe(el));
  $("#year").textContent = new Date().getFullYear();
}

function countUp(el) {
  const target = Number(el.dataset.count), suffix = el.dataset.suffix || "";
  if (reducedMotion) { el.textContent = target + suffix; return; }
  const start = performance.now(), duration = 1400;
  const tick = (now) => {
    const t = Math.min(1, (now - start) / duration), eased = 1 - Math.pow(1 - t, 3);
    el.textContent = Math.round(target * eased) + (t === 1 ? suffix : "");
    if (t < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

/* ---------- Hero: a live routing simulation ---------- */
function setupNetwork() {
  const canvas = $("#network"), ctx = canvas.getContext("2d");
  let width = 0, height = 0, nodes = [], edges = [], adjacency = [], packets = [], pointer = null, running = true;
  const color = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

  function build() {
    const dpr = Math.min(devicePixelRatio || 1, 2);
    width = canvas.clientWidth; height = canvas.clientHeight;
    canvas.width = width * dpr; canvas.height = height * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const count = Math.round(Math.min(70, Math.max(26, (width * height) / 26000)));
    nodes = []; let guard = 0;
    while (nodes.length < count && guard++ < 5000) {
      const node = { x: 30 + Math.random() * (width - 60), y: 30 + Math.random() * (height - 60) };
      if (nodes.every((n) => Math.hypot(n.x - node.x, n.y - node.y) > Math.min(width, height) / 9)) nodes.push(node);
    }
    edges = []; adjacency = nodes.map(() => []);
    nodes.forEach((a, i) => {
      nodes.map((b, j) => ({ j, d: Math.hypot(a.x - b.x, a.y - b.y) })).filter((n) => n.j !== i).sort((p, q) => p.d - q.d).slice(0, 3)
        .forEach(({ j, d }) => {
          if (!adjacency[i].some((e) => e.to === j)) {
            const edge = { a: i, b: j, length: d, heat: 0 };
            edges.push(edge); adjacency[i].push({ to: j, edge }); adjacency[j].push({ to: i, edge });
          }
        });
    });
    packets = [];
  }

  // Link cost = length plus congestion near the pointer, so shortest paths bend around it.
  function cost(edge) {
    if (!pointer) return edge.length;
    const mx = (nodes[edge.a].x + nodes[edge.b].x) / 2, my = (nodes[edge.a].y + nodes[edge.b].y) / 2;
    const near = Math.max(0, 1 - Math.hypot(mx - pointer.x, my - pointer.y) / 180);
    return edge.length * (1 + 12 * near * near);
  }

  function route(from, to) {
    const dist = nodes.map(() => Infinity), prev = nodes.map(() => null), done = nodes.map(() => false);
    dist[from] = 0;
    for (let k = 0; k < nodes.length; k++) {
      let u = -1;
      for (let i = 0; i < nodes.length; i++) if (!done[i] && (u < 0 || dist[i] < dist[u])) u = i;
      if (u < 0 || dist[u] === Infinity) break;
      done[u] = true;
      for (const { to: v, edge } of adjacency[u]) {
        const alt = dist[u] + cost(edge);
        if (alt < dist[v]) { dist[v] = alt; prev[v] = { node: u, edge }; }
      }
    }
    const path = []; let at = to;
    while (prev[at]) { path.unshift({ from: prev[at].node, to: at, edge: prev[at].edge }); at = prev[at].node; }
    return at === from ? path : [];
  }

  function spawn() {
    const from = Math.floor(Math.random() * nodes.length); let to = from;
    while (to === from) to = Math.floor(Math.random() * nodes.length);
    const path = route(from, to);
    if (path.length) packets.push({ path, hop: 0, t: 0, speed: 1.6 + Math.random() * 1.2, hue: Math.random() < 0.25 });
  }

  function frame() {
    if (!running) return;
    ctx.clearRect(0, 0, width, height);
    const ink = color("--ink"), accent = color("--accent"), warm = color("--warm");
    edges.forEach((e) => { e.heat *= 0.96; });
    if (packets.length < nodes.length * 0.9 && Math.random() < 0.5) spawn();
    packets = packets.filter((p) => {
      const leg = p.path[p.hop];
      p.t += p.speed / leg.edge.length * 1.6;
      leg.edge.heat = Math.min(1, leg.edge.heat + 0.05);
      if (p.t >= 1) { p.t = 0; p.hop++; if (p.hop >= p.path.length) return false; }
      return true;
    });
    for (const e of edges) {
      ctx.strokeStyle = ink; ctx.globalAlpha = 0.06 + e.heat * 0.22; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(nodes[e.a].x, nodes[e.a].y); ctx.lineTo(nodes[e.b].x, nodes[e.b].y); ctx.stroke();
    }
    ctx.globalAlpha = 0.35; ctx.fillStyle = ink;
    for (const n of nodes) { ctx.beginPath(); ctx.arc(n.x, n.y, 2.2, 0, Math.PI * 2); ctx.fill(); }
    for (const p of packets) {
      const leg = p.path[p.hop], a = nodes[leg.from], b = nodes[leg.to];
      const x = a.x + (b.x - a.x) * p.t, y = a.y + (b.y - a.y) * p.t;
      ctx.globalAlpha = 0.9; ctx.fillStyle = p.hue ? warm : accent;
      ctx.shadowColor = ctx.fillStyle; ctx.shadowBlur = 10;
      ctx.beginPath(); ctx.arc(x, y, 2.4, 0, Math.PI * 2); ctx.fill();
      ctx.shadowBlur = 0;
    }
    if (pointer) {
      const glow = ctx.createRadialGradient(pointer.x, pointer.y, 0, pointer.x, pointer.y, 180);
      glow.addColorStop(0, warm); glow.addColorStop(1, "transparent");
      ctx.globalAlpha = 0.08; ctx.fillStyle = glow; ctx.beginPath(); ctx.arc(pointer.x, pointer.y, 180, 0, Math.PI * 2); ctx.fill();
    }
    ctx.globalAlpha = 1;
    requestAnimationFrame(frame);
  }

  build();
  addEventListener("resize", () => { clearTimeout(build.t); build.t = setTimeout(build, 200); });
  const hero = $(".hero");
  hero.addEventListener("pointermove", (event) => {
    const rect = canvas.getBoundingClientRect(); pointer = { x: event.clientX - rect.left, y: event.clientY - rect.top };
  });
  hero.addEventListener("pointerleave", () => { pointer = null; });
  new IntersectionObserver(([entry]) => {
    const visible = entry.isIntersecting;
    if (visible && !running) { running = true; requestAnimationFrame(frame); }
    if (!visible) running = false;
  }).observe(hero);
  if (reducedMotion) {
    for (let i = 0; i < 40; i++) spawn();
    running = true; frame(); running = false;
  } else {
    requestAnimationFrame(frame);
  }
}

/* ---------- Case study: PPO replays ---------- */
function setupPPO(data) {
  let task = "key_door", index = 0, timer = null;
  const names = { random: "Random", ppo: "Trained agent", oracle: "Optimal" };
  const evalRow = (policy) => data.evaluation.find((row) => row.task === task && row.policy === policy);

  function stats() {
    const ppo = evalRow("ppo_sampled"), random = evalRow("random");
    $("#ppo-stats").innerHTML = `
      <div class="ppo"><b>${pct(ppo.success_rate)}</b><span>solved by the agent</span></div>
      <div class="ppo"><b>${pct(ppo.optimality)}</b><span>of optimal path length</span></div>
      <div><b>${pct(random.success_rate)}</b><span>solved by a random agent</span></div>`;
    $("#ppo-fine").textContent = `${data.evaluation[0].episodes} unseen layouts per task · ${data.training.updates} updates · ${(data.parameters / 1000).toFixed(0)}k parameters · ${data.minutes} minutes of CPU training`;
  }

  function board(frame, trail) {
    const rows = frame.rows, n = rows.length;
    let html = `<div class="board" style="grid-template-columns:repeat(${n},1fr)">`;
    rows.forEach((row, r) => [...row].forEach((ch, c) => {
      const kind = { "#": "wall", A: "agent-cell", G: "goal", K: "key" }[ch] || (trail.has(`${r},${c}`) ? "trail" : "");
      html += `<div class="cell ${kind}"></div>`;
    }));
    return html + "</div>";
  }

  function render(step) {
    const episode = data.replays[task][index];
    $("#replay").innerHTML = Object.entries(episode.runs).map(([name, run]) => {
      const i = Math.min(step, run.frames.length - 1), done = i === run.frames.length - 1;
      const trail = new Set();
      for (let k = 0; k <= i; k++) run.frames[k].rows.forEach((row, r) => { const c = row.indexOf("A"); if (c >= 0) trail.add(`${r},${c}`); });
      const status = done ? (run.success ? `Solved in ${run.steps} steps` : `Gave up after ${run.steps}`) : step >= REPLAY_CAP ? `Still searching after ${i} steps` : `Step ${i}`;
      return `<div class="agent ${done ? (run.success ? "won" : "lost") : ""}"><h4><span>${names[name]}</span><span>${run.frames[i].has_key ? "has key" : ""}</span></h4>${board(run.frames[i], trail)}<p>${status}${done && run.success ? ` · optimal ${run.optimal_steps}` : ""}</p></div>`;
    }).join("");
  }

  function play() {
    clearInterval(timer);
    const episode = data.replays[task][index];
    const longest = Math.min(Math.max(...Object.values(episode.runs).map((run) => run.frames.length)), REPLAY_CAP);
    if (reducedMotion) { render(longest); return; }
    let step = 0; render(0);
    timer = setInterval(() => { step++; render(step); if (step >= longest) clearInterval(timer); }, 150);
  }

  $$('[data-task]').forEach((button) => button.addEventListener("click", () => {
    task = button.dataset.task; index = 0;
    $$('[data-task]').forEach((b) => b.setAttribute("aria-selected", String(b === button)));
    stats(); play();
  }));
  $("#replay-play").addEventListener("click", play);
  $("#replay-next").addEventListener("click", () => { index = (index + 1) % data.replays[task].length; play(); });
  stats(); render(0);
  new IntersectionObserver(([entry], observer) => { if (entry.isIntersecting) { play(); observer.disconnect(); } }, { threshold: 0.3 }).observe($("#replay"));
}

/* ---------- Case study: NeuroFlow load explorer ---------- */
function setupNeuroFlow(rows) {
  const loads = [...new Set(rows.map((r) => r.load))].sort((a, b) => a - b);
  const policies = [["Shortest path", "sp"], ["Load-aware distance vector", "dv"], ["Q-routing", "q"]];
  const insights = [
    "At light load every policy is equivalent. Learned routing has converged to the shortest paths, so there is nothing to gain yet.",
    "Queues start to build on the shortest-path bottleneck. Adaptive policies begin to spread traffic, and the distance vector pulls ahead.",
    "Near saturation, static routing doubles its delay. Both adaptive policies route around the bottleneck; the distance vector halves the delay.",
    "Past the point where shortest paths are stable, static routing collapses. Adaptive routing keeps delays in the tens because other paths still have capacity.",
    "Deep overload. The distance vector chases momentarily short queues and oscillates, doubling path length. Q-routing, which learns from smoothed delays, is the only policy that stays usable.",
  ];
  const max = Math.log10(Math.max(...rows.map((r) => r.mean_latency)) * 1.2), min = Math.log10(5);
  const input = $("#nf-load");
  input.max = String(loads.length - 1);

  function render() {
    const load = loads[Number(input.value)];
    $("#nf-load-out").textContent = `${Math.round(load * 100)}%`;
    $("#nf-bars").innerHTML = policies.map(([label, key]) => {
      const row = rows.find((r) => r.agent === label && r.load === load);
      const width = Math.max(3, ((Math.log10(row.mean_latency) - min) / (max - min)) * 100);
      return `<div class="bar-row"><span>${label}</span><div class="bar-track"><div class="bar-fill ${key}" style="width:${width}%"></div></div><span class="bar-value">${row.mean_latency.toFixed(1)}<small>±${row.ci95.toFixed(1)} · ${row.mean_hops.toFixed(1)} hops</small></span></div>`;
    }).join("");
    $("#nf-note").textContent = insights[Math.min(Number(input.value), insights.length - 1)];
  }
  input.addEventListener("input", render);
  render();
}

/* ---------- Case study: quant results ---------- */
function setupQuant(data) {
  const names = { random_walk: "Random walk (baseline)", historical_mean: "Historical mean", ridge: "Ridge regression", random_forest: "Random forest", gradient_boosting: "Gradient boosting" };
  $("#q-models").innerHTML = data.scores.map((row) => {
    const worse = row.dm_statistic !== null && row.dm_statistic > 0 && row.dm_p_value < 0.05;
    const verdict = row.model === "random_walk" ? ["Baseline", "base"] : worse ? ["Significantly worse", "bad"] : ["No significant edge", ""];
    return `<div class="model-row"><span>${names[row.model] || row.model}</span><code>RMSE ${row.rmse.toFixed(5)}</code><span class="verdict ${verdict[1]}">${verdict[0]}</span></div>`;
  }).join("");

  const svg = $("#q-equity"), w = 600, h = 320, pad = { l: 44, r: 118, t: 16, b: 30 };
  const points = data.equity, max = Math.max(...points.map((p) => Math.max(p.strategy, p.buy_and_hold)));
  const x = (i) => pad.l + (i / (points.length - 1)) * (w - pad.l - pad.r);
  const y = (v) => pad.t + (1 - Math.log(v) / Math.log(max * 1.05)) * (h - pad.t - pad.b);
  const path = (key) => points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p[key]).toFixed(1)}`).join("");
  const ticks = [1, 2, 4, 8].filter((v) => v <= max * 1.05);
  svg.insertAdjacentHTML("beforeend", `
    <defs><linearGradient id="fade" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--accent)" stop-opacity="0.35"/><stop offset="1" stop-color="var(--accent)" stop-opacity="0"/></linearGradient></defs>
    ${ticks.map((v) => `<line class="axis" x1="${pad.l}" x2="${w - pad.r}" y1="${y(v)}" y2="${y(v)}" stroke-dasharray="2 4"/><text x="${pad.l - 8}" y="${y(v) + 4}" text-anchor="end">$${v}</text>`).join("")}
    <text x="${pad.l}" y="${h - 8}">${points[0].date.slice(0, 4)}</text><text x="${w - pad.r}" y="${h - 8}" text-anchor="end">${points.at(-1).date.slice(0, 4)}</text>
    <path class="area" d="${path("strategy")}L${x(points.length - 1)},${h - pad.b}L${x(0)},${h - pad.b}Z"/>
    <path class="s-hold draw" d="${path("buy_and_hold")}"/><path class="s-strat draw" d="${path("strategy")}"/>
    <text x="${x(points.length - 1) + 8}" y="${y(points.at(-1).buy_and_hold) + 4}">Buy and hold $${points.at(-1).buy_and_hold.toFixed(2)}</text>
    <text x="${x(points.length - 1) + 8}" y="${y(points.at(-1).strategy) + 4}" style="fill:var(--accent)">Signal $${points.at(-1).strategy.toFixed(2)}</text>`);
  $$("path.draw", svg).forEach((p) => p.style.setProperty("--len", Math.ceil(p.getTotalLength())));
  new IntersectionObserver(([entry], observer) => { if (entry.isIntersecting) { svg.classList.add("visible"); observer.disconnect(); } }, { threshold: 0.3 }).observe(svg);
  const s = data.strategy, b = data.buy_and_hold;
  $("#q-fine").textContent = `Signal: ${pct(s.cagr)} a year, ${pct(s.annual_volatility)} volatility, ${pct(s.max_drawdown)} worst drawdown · Buy and hold: ${pct(b.cagr)}, ${pct(b.annual_volatility)}, ${pct(b.max_drawdown)} · ${data.evaluation.test_rows.toLocaleString()} out-of-sample days`;
}

/* ---------- Project gallery ---------- */
function setupProjects(catalog, repoUrl) {
  const projects = catalog.projects;
  const order = ["All", "AI & knowledge", "Data & analytics", "Research", "Platform & security", "Network systems", "Product engineering", "Tools & web"];
  const categories = order.filter((c) => c === "All" || projects.some((p) => p.category === c));
  let active = "All", query = "";

  $("#chips").innerHTML = categories.map((c) => `<button type="button" data-cat="${escapeHTML(c)}" aria-pressed="${c === active}">${escapeHTML(c)}</button>`).join("");
  const visual = (p) => p.image
    ? `<img src="${p.image}" alt="${escapeHTML(p.title)} interface" loading="lazy" decoding="async" width="1280" height="800">`
    : `<div class="terminal" aria-hidden="true"><b>$</b> <i>python smart_scraper.py --course …/6-0001/</i><br>Processing course 6-0001<br>119 sections · 114 caption files<br>Created master PDF <i>(1,110 pages)</i><br><b>✓</b> Processed 1 of 1 courses</div>`;

  function render() {
    const q = query.trim().toLowerCase();
    const list = projects.filter((p) => (active === "All" || p.category === active)
      && (!q || `${p.title} ${p.summary} ${p.category} ${p.stack.join(" ")}`.toLowerCase().includes(q)));
    $("#grid").innerHTML = list.map((p) => `<li class="card"><button type="button" data-slug="${p.slug}" aria-label="${escapeHTML(p.title)}: open details">
      <div class="thumb">${visual(p)}</div>
      <div class="card-body"><span class="card-meta">${escapeHTML(p.category)}</span><h3>${escapeHTML(p.title)}</h3><p>${escapeHTML(p.summary)}</p>
      <div class="pills">${p.stack.slice(0, 4).map((s) => `<span>${escapeHTML(s)}</span>`).join("")}</div></div></button></li>`).join("");
    $("#count").textContent = `${list.length} of ${projects.length} projects`;
  }

  $("#chips").addEventListener("click", (event) => {
    const button = event.target.closest("[data-cat]"); if (!button) return;
    active = button.dataset.cat;
    $$("[data-cat]").forEach((b) => b.setAttribute("aria-pressed", String(b === button)));
    render();
  });
  $("#search").addEventListener("input", (event) => { query = event.target.value; render(); });

  const dialog = $("#project-dialog");
  $("#grid").addEventListener("click", (event) => {
    const button = event.target.closest("[data-slug]"); if (!button) return;
    const p = projects.find((item) => item.slug === button.dataset.slug);
    $("#dialog-body").innerHTML = `${p.image ? `<div class="dialog-image"><img src="${p.image}" alt="${escapeHTML(p.title)} interface"></div>` : ""}
      <div class="dialog-content"><span class="card-meta">${escapeHTML(p.category)} · ${escapeHTML(p.mode)}</span><h2 id="dialog-title">${escapeHTML(p.title)}</h2><p>${escapeHTML(p.summary)}</p>
      <div class="dialog-columns"><div><h3>Problem</h3><p>${escapeHTML(p.problem)}</p></div><div><h3>Approach</h3><p>${escapeHTML(p.approach)}</p></div></div>
      <div><h3>Highlights</h3><ul>${p.highlights.map((h) => `<li>${escapeHTML(h)}</li>`).join("")}</ul></div>
      <div class="pills">${p.stack.map((s) => `<span>${escapeHTML(s)}</span>`).join("")}</div>
      <div class="actions"><a class="button small" href="${repoUrl}/tree/main/${p.path}" target="_blank" rel="noopener">Source and README <span aria-hidden="true">↗</span></a></div></div>`;
    dialog.showModal();
  });
  dialog.addEventListener("click", (event) => { if (event.target === dialog || event.target.closest("[data-close]")) dialog.close(); });
  render();
}

/* ---------- Contact ---------- */
function setupContact(profile) {
  $$("[data-github]").forEach((a) => { a.href = profile.github; a.target = "_blank"; a.rel = "noopener"; });
  $("#email-text").textContent = profile.email;
  $("#copy-email").addEventListener("click", async () => {
    try { await navigator.clipboard.writeText(profile.email); toast("Email copied to the clipboard"); }
    catch { toast(profile.email); }
  });
}

/* ---------- Start ---------- */
setupChrome();
setupNetwork();
Promise.all([load("projects"), load("ppo"), load("neuroflow"), load("quant")]).then(([catalog, ppo, neuroflow, quant]) => {
  const repoUrl = `${catalog.profile.github}/${REPO_NAME}`;
  setupContact(catalog.profile);
  setupProjects(catalog, repoUrl);
  setupPPO(ppo);
  setupNeuroFlow(neuroflow);
  setupQuant(quant);
}).catch((error) => {
  console.error(error);
  toast("Some interactive content could not load. Refresh to try again.");
});
