"use strict";
const API = location.pathname.startsWith("/demos/") ? "/api/projects/delivery-desk/api" : "/api";
const $ = (selector) => document.querySelector(selector);
const stages = { backlog: "Backlog", in_progress: "In progress", review: "In review", done: "Done" };
const next = { backlog: "in_progress", in_progress: "review", review: "done" };
const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
let items = [], editing = null, loadSequence = 0, searchTimer, saving = false;

async function request(path, options = {}) {
  let response;
  try { response = await fetch(API + path, { ...options, headers: { "Content-Type": "application/json", ...options.headers } }); }
  catch { throw new Error("The local service is unreachable. Check that it is running, then try again."); }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data.detail;
    throw new Error(Array.isArray(detail) ? detail.map((issue) => `${issue.loc.at(-1)}: ${issue.msg}`).join("; ") : detail || `Request failed (${response.status}). Try again.`);
  }
  return data;
}
function notice(message, error = false) { $("#notice").hidden = false; $("#notice").textContent = message; $("#notice").dataset.error = error; }
function dateLabel(value) { return new Date(`${value}T12:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" }); }
const fieldNames = { status: "Stage", priority: "Priority", due_date: "Due date", title: "Title", description: "Description", project: "Project", assignee: "Assignee" };
function historyValue(field, value) {
  if (!value) return field === "assignee" ? "unassigned" : "empty";
  if (field === "status") return stages[value] || value;
  if (field === "due_date") return dateLabel(value);
  if (field === "description" && value.length > 60) return `${value.slice(0, 57)}…`;
  return value;
}
function today() { const date = new Date(); return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`; }
function card(task) {
  const overdue = task.due_date && task.due_date < today() && task.status !== "done";
  return `<article class="task"><p class="task-project">${escapeHTML(task.project)} · #${task.id}</p><button class="task-title" data-edit="${task.id}">${escapeHTML(task.title)}</button><div class="task-meta"><span class="priority priority-${task.priority}">${task.priority} priority</span>${task.due_date ? `<span class="due ${overdue ? "overdue" : ""}">${overdue ? "Overdue · " : "Due "}${dateLabel(task.due_date)}</span>` : ""}</div><div class="task-bottom"><span class="assignee">${escapeHTML(task.assignee || "Unassigned")}</span>${next[task.status] ? `<button class="move" data-move="${task.id}" aria-label="Move ${escapeHTML(task.title)} to ${stages[next[task.status]]}">${task.status === "backlog" ? "Start" : task.status === "in_progress" ? "Review" : "Complete"} →</button>` : '<span class="assignee">✓ Delivered</span>'}</div></article>`;
}
async function load() {
  const sequence = ++loadSequence;
  $("#board").setAttribute("aria-busy", "true");
  try {
    const filters = new URLSearchParams({ q: $("#search").value });
    for (const [key, selector] of [["project", "#project-filter"], ["priority", "#priority-filter"]]) {
      if ($(selector).value) filters.set(key, $(selector).value);
    }
    const data = await request(`/tasks?${filters}`);
    if (sequence !== loadSequence) return;
    items = data.items;
    const selected = $("#project-filter").value;
    $("#project-filter").innerHTML = '<option value="">All projects</option>' + data.projects.map((project) => `<option value="${escapeHTML(project)}">${escapeHTML(project)}</option>`).join("");
    $("#project-filter").value = data.projects.includes(selected) ? selected : "";
    $("#project-options").innerHTML = data.projects.map((project) => `<option value="${escapeHTML(project)}"></option>`).join("");
    $("#active-count").textContent = data.counts.in_progress;
    $("#done-count").textContent = data.counts.done;
    const total = Object.values(data.counts).reduce((sum, count) => sum + count, 0);
    $("#total-count").textContent = total;
    $("#board").innerHTML = Object.entries(stages).map(([status, label]) => {
      const tasks = items.filter((task) => task.status === status);
      return `<section class="column column-${status}" aria-label="${label}"><h2 class="column-title">${label}<span>${tasks.length}</span></h2>${tasks.map(card).join("") || `<p class="empty">${total ? "No matching tasks in this stage." : "Your next task starts here.<br>Create a task or add samples."}</p>`}</section>`;
    }).join("");
  } catch (error) {
    if (sequence !== loadSequence) return;
    notice(error.message, true);
    if (!$("#board .column")) $("#board").innerHTML = '<p class="loading">The board could not load. Use Refresh to try again.</p>';
  } finally { if (sequence === loadSequence) $("#board").setAttribute("aria-busy", "false"); }
}
async function openEditor(id = null) {
  try {
    editing = id ? await request(`/tasks/${id}`) : null;
    $("#task-form").reset();
    $("#form-error").hidden = true;
    $("#dialog-title").textContent = editing ? "Task details" : "Create a task";
    $("#task-reference").textContent = editing ? `Task #${editing.id} · Version ${editing.version}` : "New work";
    $("#save").textContent = editing ? "Save changes" : "Create task";
    if (editing) for (const field of ["title", "description", "project", "assignee", "status", "priority", "due_date"]) $("#task-form").elements[field].value = editing[field] || "";
    $("#history-section").hidden = !editing;
    $("#history").innerHTML = editing ? editing.history.map((event) => {
      const changes = event.action === "created" ? "Task created" : Object.entries(event.changes).map(([field, change]) => `${fieldNames[field] || field.replaceAll("_", " ")}: ${historyValue(field, change.from)} → ${historyValue(field, change.to)}`).join(" · ");
      return `<li><time datetime="${escapeHTML(event.created_at)}">${escapeHTML(new Date(event.created_at).toLocaleString())}</time><p>${escapeHTML(changes)}</p></li>`;
    }).join("") : "";
    if (!$("#task-dialog").open) $("#task-dialog").showModal();
  } catch (error) { notice(error.message, true); }
}
$("#task-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (saving) return;
  const payload = Object.fromEntries(new FormData(event.currentTarget));
  payload.due_date = payload.due_date || null;
  if (editing) payload.version = editing.version;
  saving = true; $("#save").disabled = true; $("#form-error").hidden = true;
  try {
    await request(editing ? `/tasks/${editing.id}` : "/tasks", { method: editing ? "PATCH" : "POST", body: JSON.stringify(payload) });
    notice(editing ? "Task changes saved." : "Task created.");
    $("#task-dialog").close();
    await load();
  } catch (error) { $("#form-error").textContent = error.message; $("#form-error").hidden = false; }
  finally { saving = false; $("#save").disabled = false; }
});
$("#board").addEventListener("click", async (event) => {
  const edit = event.target.closest("[data-edit]");
  if (edit) { await openEditor(Number(edit.dataset.edit)); return; }
  const move = event.target.closest("[data-move]");
  if (!move) return;
  const task = items.find((item) => item.id === Number(move.dataset.move));
  if (!task || !next[task.status]) return;
  move.disabled = true;
  try { await request(`/tasks/${task.id}`, { method: "PATCH", body: JSON.stringify({ version: task.version, status: next[task.status] }) }); notice(`Task moved to ${stages[next[task.status]].toLowerCase()}.`); await load(); }
  catch (error) { notice(error.message, true); await load(); }
  finally { move.disabled = false; }
});
$("#new-task").addEventListener("click", () => openEditor());
for (const selector of ["#close-dialog", "#cancel"]) $(selector).addEventListener("click", () => { if (!saving) $("#task-dialog").close(); });
$("#task-dialog").addEventListener("cancel", (event) => { if (saving) event.preventDefault(); });
$("#search").addEventListener("input", () => { clearTimeout(searchTimer); searchTimer = setTimeout(load, 220); });
for (const selector of ["#project-filter", "#priority-filter"]) $(selector).addEventListener("change", load);
$("#refresh").addEventListener("click", load);
$("#seed").addEventListener("click", async () => {
  $("#seed").disabled = true;
  try { const data = await request("/demo/seed", { method: "POST" }); notice(data.message); await load(); }
  catch (error) { notice(error.message, true); }
  finally { $("#seed").disabled = false; }
});
load();
