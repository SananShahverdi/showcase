"use strict";
const API = location.pathname.startsWith("/demos/") ? "/api/projects/stockroom-inventory/api" : "/api";
const $ = (selector) => document.querySelector(selector);
const escapeHTML = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
let view = "catalog", catalog = [], editing = null, sequence = 0, searchTimer, savingItem = false, savingMovement = false, movementRequest = null;
async function request(path, options = {}) {
  let response;
  try { response = await fetch(API + path, { ...options, headers: { "Content-Type": "application/json", ...options.headers } }); }
  catch { throw new Error("The local service is unreachable. Check that it is running, then try again."); }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(Array.isArray(data.detail) ? data.detail.map((issue) => `${issue.loc.at(-1)}: ${issue.msg}`).join("; ") : data.detail || `Request failed (${response.status}). Try again.`);
  return data;
}
function notice(message, error = false) { $("#notice").hidden = false; $("#notice").textContent = message; $("#notice").dataset.error = error; }
function option(item) { return `<option value="${item.id}">${escapeHTML(item.name)} · ${escapeHTML(item.sku)}</option>`; }
function itemRow(item) {
  const state = item.quantity === 0 ? "out" : item.quantity <= item.reorder_level ? "low" : "healthy";
  const stockLabel = { out: "Out of stock", low: "Reorder needed", healthy: "In stock" }[state];
  return `<tr><td data-label="Item"><button class="item-name" data-edit="${item.id}">${escapeHTML(item.name)}</button><span class="sku">${escapeHTML(item.sku)}</span></td><td data-label="Category" class="category-cell">${escapeHTML(item.category)}</td><td data-label="Shelf"><span class="shelf">${escapeHTML(item.location)}</span></td><td data-label="On hand"><span class="quantity">${item.quantity.toLocaleString()}<span class="unit">${escapeHTML(item.unit)}</span></span><span class="stock-status ${state}">${stockLabel}</span></td><td data-label="Reorder at">${item.reorder_level.toLocaleString()} <span class="unit">${escapeHTML(item.unit)}</span></td><td data-label="Actions"><div class="row-actions"><button class="row-action" data-stock="${item.id}" data-kind="receive" aria-label="Receive ${escapeHTML(item.name)}"><span aria-hidden="true">+</span> Receive</button><button class="row-action dispatch" data-stock="${item.id}" data-kind="dispatch" aria-label="Dispatch ${escapeHTML(item.name)}">− Dispatch</button></div></td></tr>`;
}
function renderCatalog(items) {
  $("#catalog-caption").textContent = `${items.length} ${items.length === 1 ? "item" : "items"}${view === "low" ? " need attention" : " shown"}`;
  if (!items.length) {
    const empty = catalog.length === 0;
    $("#records").innerHTML = `<p class="empty"><strong>${empty ? "Your shelves are ready." : view === "low" ? "No low-stock items match." : "No matching items."}</strong>${empty ? "Add your first item or use Add sample inventory to explore the workspace." : "Change the filters or choose All items to see more of your catalog."}</p>`;
    return;
  }
  $("#records").innerHTML = `<table><caption class="sr-only">${view === "low" ? "Items at or below reorder level" : "Inventory catalog"}</caption><thead><tr><th scope="col">Item / SKU</th><th scope="col" class="category-cell">Category</th><th scope="col">Shelf</th><th scope="col">On hand</th><th scope="col">Reorder at</th><th scope="col">Move stock</th></tr></thead><tbody>${items.map(itemRow).join("")}</tbody></table>`;
}
function renderLedger(data) {
  $("#ledger-caption").textContent = `Showing ${data.items.length} of ${data.total} movements · latest first`;
  if (!data.items.length) { $("#records").innerHTML = '<p class="empty"><strong>No movements in this view.</strong>Receive or dispatch stock to create a record, or change the item filter.</p>'; return; }
  $("#records").innerHTML = `<table class="ledger"><caption class="sr-only">Stock movement ledger, latest first</caption><thead><tr><th scope="col">Item / SKU</th><th scope="col">Movement</th><th scope="col">Balance after</th><th scope="col">Reason / reference</th><th scope="col">Recorded</th></tr></thead><tbody>${data.items.map((movement) => {
    const date = new Date(movement.created_at);
    return `<tr><td data-label="Item"><span class="item-name">${escapeHTML(movement.name)}</span><span class="sku">${escapeHTML(movement.sku)}</span></td><td data-label="Movement"><span class="amount ${movement.kind}">${movement.kind === "receive" ? "+" : "−"}${movement.quantity.toLocaleString()}</span><span class="movement-kind">${movement.kind === "receive" ? "Received" : "Dispatched"}</span></td><td data-label="Balance after"><span class="quantity">${movement.balance_after.toLocaleString()}</span> <span class="unit">${escapeHTML(movement.unit)}</span></td><td data-label="Reason" class="ledger-reason">${escapeHTML(movement.reason)}${movement.reference ? `<small>Ref: ${escapeHTML(movement.reference)}</small>` : ""}</td><td data-label="Recorded"><time class="ledger-date" datetime="${escapeHTML(movement.created_at)}">${escapeHTML(date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }))}<br>${escapeHTML(date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" }))}</time></td></tr>`;
  }).join("")}</tbody></table>`;
}
async function load() {
  const current = ++sequence;
  $("#records").setAttribute("aria-busy", "true");
  try {
    const data = await request("/items");
    if (current !== sequence) return;
    catalog = data.items;
    const selectedCategory = $("#category-filter").value;
    $("#category-filter").innerHTML = '<option value="">All categories</option>' + data.categories.map((category) => `<option value="${escapeHTML(category)}">${escapeHTML(category)}</option>`).join("");
    $("#category-filter").value = data.categories.includes(selectedCategory) ? selectedCategory : "";
    $("#category-options").innerHTML = data.categories.map((category) => `<option value="${escapeHTML(category)}"></option>`).join("");
    const selectedItem = $("#ledger-item").value;
    $("#ledger-item").innerHTML = '<option value="">All items</option>' + catalog.map(option).join("");
    $("#ledger-item").value = catalog.some((item) => String(item.id) === selectedItem) ? selectedItem : "";
    $("#item-count").textContent = data.summary.item_count;
    $("#low-count").textContent = data.summary.low_stock_count;
    $("#out-count").textContent = data.summary.out_of_stock_count;
    $("#movement-count").textContent = data.summary.movement_count;
    if (view === "ledger") {
      const filters = new URLSearchParams({ limit: "50" });
      if ($("#ledger-item").value) filters.set("item_id", $("#ledger-item").value);
      if ($("#ledger-kind").value) filters.set("kind", $("#ledger-kind").value);
      const movements = await request(`/movements?${filters}`);
      if (current === sequence) renderLedger(movements);
    } else {
      const filters = new URLSearchParams({ q: $("#search").value, category: $("#category-filter").value, low_stock: String(view === "low") });
      const filtered = await request(`/items?${filters}`);
      if (current === sequence) renderCatalog(filtered.items);
    }
  } catch (error) {
    if (current !== sequence) return;
    notice(error.message, true);
    if (!$("#records table")) $("#records").innerHTML = '<p class="empty">Inventory could not load. Use Refresh to try again.</p>';
  } finally { if (current === sequence) $("#records").setAttribute("aria-busy", "false"); }
}
function setView(nextView) {
  view = nextView;
  document.querySelectorAll("[data-view]").forEach((button) => { button.classList.toggle("active", button.dataset.view === view); button.setAttribute("aria-pressed", String(button.dataset.view === view)); });
  $("#catalog-filters").hidden = view === "ledger";
  $("#ledger-filters").hidden = view !== "ledger";
  load();
}
async function openItem(id = null) {
  try {
    editing = id ? await request(`/items/${id}`) : null;
    const form = $("#item-form");
    form.reset(); $("#item-error").hidden = true;
    $("#item-dialog-title").textContent = editing ? "Edit item" : "Add an item";
    $("#item-reference").textContent = editing ? `${editing.sku} · Version ${editing.version}` : "Catalog";
    $("#save-item").textContent = editing ? "Save changes" : "Add item";
    form.elements.sku.disabled = Boolean(editing);
    form.elements.unit.disabled = Boolean(editing);
    form.elements.quantity.disabled = Boolean(editing);
    $("#opening-field").hidden = Boolean(editing);
    if (editing) for (const field of ["name", "sku", "category", "location", "unit", "quantity", "reorder_level"]) form.elements[field].value = editing[field];
    if (!$("#item-dialog").open) $("#item-dialog").showModal();
  } catch (error) { notice(error.message, true); }
}
function stockPreview() {
  const item = catalog.find((record) => record.id === Number($("#movement-item").value));
  $("#available-stock").innerHTML = item ? `<strong>${item.quantity.toLocaleString()}</strong> ${escapeHTML(item.unit)} on hand · shelf ${escapeHTML(item.location)}<br>Stock is checked again when you record the movement.` : "Select an item to see available stock.";
  $("#save-movement").textContent = $("#movement-kind").value === "receive" ? "Record receipt" : "Record dispatch";
}
async function openMovement(id = null, kind = "receive") {
  try {
    const data = await request("/items"); catalog = data.items;
    if (!catalog.length) { notice("Add an item before recording a stock movement."); return; }
    $("#movement-form").reset(); $("#movement-error").hidden = true; movementRequest = null;
    $("#movement-item").innerHTML = catalog.map(option).join("");
    if (id) $("#movement-item").value = String(id);
    $("#movement-kind").value = kind;
    stockPreview();
    if (!$("#movement-dialog").open) $("#movement-dialog").showModal();
  } catch (error) { notice(error.message, true); }
}
$("#item-form").addEventListener("submit", async (event) => {
  event.preventDefault(); if (savingItem) return;
  const payload = Object.fromEntries(new FormData(event.currentTarget));
  payload.reorder_level = Number(payload.reorder_level);
  if (editing) payload.version = editing.version; else payload.quantity = Number(payload.quantity);
  savingItem = true; $("#save-item").disabled = true; $("#item-error").hidden = true;
  try { await request(editing ? `/items/${editing.id}` : "/items", { method: editing ? "PATCH" : "POST", body: JSON.stringify(payload) }); notice(editing ? "Item changes saved." : "Item added to the catalog."); $("#item-dialog").close(); await load(); }
  catch (error) { $("#item-error").textContent = error.message; $("#item-error").hidden = false; }
  finally { savingItem = false; $("#save-item").disabled = false; }
});
$("#movement-form").addEventListener("submit", async (event) => {
  event.preventDefault(); if (savingMovement) return;
  const payload = Object.fromEntries(new FormData(event.currentTarget));
  payload.item_id = Number(payload.item_id); payload.quantity = Number(payload.quantity);
  const fingerprint = JSON.stringify(payload);
  if (!movementRequest || movementRequest.fingerprint !== fingerprint) movementRequest = { fingerprint, id: crypto.randomUUID() };
  payload.request_id = movementRequest.id;
  savingMovement = true; $("#save-movement").disabled = true; $("#movement-error").hidden = true;
  try {
    const movement = await request("/movements", { method: "POST", body: JSON.stringify(payload) });
    const item = catalog.find((record) => record.id === payload.item_id);
    notice(`${payload.kind === "receive" ? "Receipt" : "Dispatch"} recorded. ${item.name} now has ${movement.balance_after.toLocaleString()} ${item.unit} on hand.`);
    $("#movement-dialog").close(); await load();
  } catch (error) { $("#movement-error").textContent = error.message; $("#movement-error").hidden = false; }
  finally { savingMovement = false; $("#save-movement").disabled = false; }
});
$("#records").addEventListener("click", (event) => {
  const edit = event.target.closest("[data-edit]"); if (edit) { openItem(Number(edit.dataset.edit)); return; }
  const stock = event.target.closest("[data-stock]"); if (stock) openMovement(Number(stock.dataset.stock), stock.dataset.kind);
});
document.querySelectorAll("[data-view]").forEach((button) => button.addEventListener("click", () => setView(button.dataset.view)));
document.querySelectorAll("[data-close]").forEach((button) => button.addEventListener("click", () => { if (!savingItem && !savingMovement) document.getElementById(button.dataset.close).close(); }));
for (const selector of ["#item-dialog", "#movement-dialog"]) $(selector).addEventListener("cancel", (event) => { if (savingItem || savingMovement) event.preventDefault(); });
$("#new-item").addEventListener("click", () => openItem());
$("#record-movement").addEventListener("click", () => openMovement());
$("#show-low").addEventListener("click", () => { $("#search").value = ""; $("#category-filter").value = ""; setView("low"); });
$("#search").addEventListener("input", () => { clearTimeout(searchTimer); searchTimer = setTimeout(load, 220); });
for (const selector of ["#category-filter", "#ledger-item", "#ledger-kind"]) $(selector).addEventListener("change", load);
for (const selector of ["#movement-item", "#movement-kind"]) $(selector).addEventListener("change", stockPreview);
$("#refresh").addEventListener("click", load);
$("#seed").addEventListener("click", async () => { $("#seed").disabled = true; try { const result = await request("/demo/seed", { method: "POST" }); notice(result.message); await load(); } catch (error) { notice(error.message, true); } finally { $("#seed").disabled = false; } });
load();
