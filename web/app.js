const $ = (selector, root = document) => root.querySelector(selector)
const escape = (value) => String(value).replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char])
const state = { projects: [], saved: [], category: 'All work', query: '', savedOnly: false, current: null, tab: 'overview', viewVersion: 0 }
const dialog = $('#project-dialog')
let toastTimer

async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { 'Content-Type': 'application/json', ...options.headers } })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const detail = Array.isArray(data.detail) ? data.detail.map((error) => `${error.loc.at(-1)}: ${error.msg}`).join('. ') : data.detail
    throw new Error(detail || `Request failed (${response.status}). Try again.`)
  }
  return data
}

function toast(message) {
  clearTimeout(toastTimer)
  $('#toast').textContent = message
  $('#toast').hidden = false
  toastTimer = setTimeout(() => { $('#toast').hidden = true }, 4000)
}

function savedButton(project) {
  const saved = state.saved.includes(project.slug)
  return `<button class="save-button" data-save="${project.slug}" aria-label="${saved ? 'Unsave' : 'Save'} ${escape(project.title)}" aria-pressed="${saved}" title="${saved ? 'Remove from saved' : 'Save project'}">${saved ? '★' : '☆'}</button>`
}

function artwork(project) {
  // Small, illustrative workflow diagrams, not screenshots or fabricated metrics.
  const label = '<span class="art-label">WORKFLOW SKETCH</span>'
  if (project.slug === 'compliance-aware-rag-knowledge-base') return `<div class="project-art evidence" aria-hidden="true">${label}<div class="art-window"><div class="art-bar"><i></i><i></i><i></i><span>evidence / ask</span></div><div class="art-body"><div class="art-answer"><b>What does the source actually say?</b><div class="quote-line"></div><div class="quote-line short"></div></div><span class="citation-tag">[1] permitted source</span></div></div></div>`
  if (project.slug === 'autonomous-data-quality-observatory') return `<div class="project-art orbit" aria-hidden="true">${label}<div class="orbit-diagram"><div class="orbit-core"><span>◎</span></div><div class="orbit-signals"><span>Profile <b>→</b></span><span>Compare baseline <b>→</b></span><span>Resolve incidents <b>✓</b></span></div></div></div>`
  if (project.slug === 'delivery-desk') return `<div class="project-art delivery" aria-hidden="true">${label}<div class="mini-board"><div class="mini-column"><b>TO DO</b><div class="mini-ticket"><span class="ticket-tag"></span>Define the workflow</div><div class="mini-ticket"><span class="ticket-tag"></span>Review edge cases</div></div><div class="mini-column"><b>IN PROGRESS</b><div class="mini-ticket"><span class="ticket-tag"></span>Connect the API</div></div><div class="mini-column"><b>DONE</b><div class="mini-ticket"><span class="ticket-tag"></span>Keep the history</div></div></div></div>`
  return `<div class="project-art stockroom" aria-hidden="true">${label}<div class="stock-grid"><div class="box-stack"><span></span><span></span><span></span><span></span></div><div class="stock-ledger"><b>MOVEMENT LEDGER</b><div>Receive <em>+ stock</em></div><div>Dispatch <em>− stock</em></div><div>Reconcile <em>= balance</em></div></div></div></div>`
}

function renderFeatured() {
  $('#featured-grid').innerHTML = state.projects.filter((project) => project.featured).map((project) => `<article class="project-card">${artwork(project)}<div class="card-body"><div class="card-meta"><span class="eyebrow">${escape(project.category.toUpperCase())}</span>${savedButton(project)}</div><h3 class="card-title"><button data-project="${project.slug}">${escape(project.title)}</button></h3><p class="card-summary">${escape(project.summary)}</p><div class="card-footer"><div class="tag-list">${project.stack.slice(0, 3).map((item) => `<span>${escape(item)}</span>`).join('')}</div><button class="text-link" data-project="${project.slug}">Explore project <span aria-hidden="true">↗</span></button></div></div></article>`).join('')
}

function renderFilters() {
  const categories = ['All work', ...new Set(state.projects.map((project) => project.category))]
  $('#category-filters').innerHTML = categories.map((category) => `<button data-category="${escape(category)}" aria-pressed="${state.category === category}">${escape(category)}</button>`).join('')
}

function renderDirectory() {
  const query = state.query.toLocaleLowerCase().trim()
  const filtered = state.projects.filter((project) => (state.category === 'All work' || project.category === state.category) && (!state.savedOnly || state.saved.includes(project.slug)) && `${project.title} ${project.slug} ${project.summary} ${project.category} ${project.stack.join(' ')}`.toLocaleLowerCase().includes(query))
  $('#project-total').textContent = `${state.projects.length} projects`
  $('#saved-count').textContent = state.saved.length
  $('#saved-filter').setAttribute('aria-pressed', state.savedOnly)
  $('#result-count').textContent = `${filtered.length} ${filtered.length === 1 ? 'project' : 'projects'}${state.savedOnly ? ' saved' : ''}${query ? ` matching “${state.query}”` : ''}`
  const symbols = { 'AI & knowledge': '✳', 'Data & analytics': '▦', 'Product engineering': '⊞', 'Platform & security': '⌘', 'Network systems': '⋈' }
  $('#project-list').innerHTML = filtered.length ? filtered.map((project) => `<article class="project-row"><span class="row-symbol" aria-hidden="true">${symbols[project.category] || '{ }'}</span><button class="row-description" data-project="${project.slug}"><h3>${escape(project.title)}</h3><p>${escape(project.summary)}</p></button><span class="row-category">${escape(project.category)}</span><a class="row-open" href="${project.demo_url}" aria-label="Open ${escape(project.title)} demo" ${!project.available || !project.console_ready ? 'aria-disabled="true" tabindex="-1"' : ''}>Open <span aria-hidden="true">↗</span></a>${savedButton(project)}</article>`).join('') : `<div class="empty-state"><h3>${state.savedOnly ? 'No saved projects here yet.' : 'No projects match this search.'}</h3><p>${state.savedOnly ? 'Use the star on a project to keep it in your local collection.' : 'Try another technology or explore all disciplines.'}</p><button class="button secondary" id="clear-filters">Show all projects</button></div>`
}

async function loadProjects() {
  try {
    const data = await api('/api/projects')
    state.projects = data.projects
    state.saved = data.saved
    renderFeatured()
    renderFilters()
    renderDirectory()
    const slug = location.pathname.match(/^\/projects\/([^/]+)$/)?.[1]
    if (slug) openProject(slug, false)
  } catch (error) {
    $('#featured-grid').innerHTML = `<div class="empty-state" role="alert"><h3>The project collection is unavailable.</h3><p>${escape(error.message)}</p><button id="retry-projects" class="button secondary">Try again</button></div>`
  }
}

async function refreshStatus() {
  $('#refresh-status').disabled = true
  try {
    const data = await api('/api/status')
    const projects = Object.values(data.projects)
    const ready = projects.filter((project) => project.status === 'ready').length
    const consoles = projects.filter((project) => project.console_ready).length
    $('#system-status').innerHTML = `<i class="status-dot ${ready < projects.length ? 'pending' : ''}"></i>${ready}/${projects.length} APIs ready · ${consoles} consoles built`
  } catch {
    $('#system-status').innerHTML = '<i class="status-dot error"></i>Cannot reach the local server. Try refreshing.'
  } finally {
    $('#refresh-status').disabled = false
  }
}

function openProject(slug, push = true) {
  const project = state.projects.find((item) => item.slug === slug)
  if (!project) return
  state.current = project
  state.tab = 'overview'
  $('#dialog-category').textContent = `${project.category.toUpperCase()} / CASE STUDY`
  $('#dialog-content').innerHTML = `<h2 id="dialog-title">${escape(project.title)}</h2><p class="dialog-summary">${escape(project.summary)}</p><div class="dialog-actions">${project.available && project.console_ready ? `<a class="button primary" href="${project.demo_url}">Open working demo <span aria-hidden="true">↗</span></a>` : '<span class="muted">This console needs a local build before it can open.</span>'}<a class="button secondary" href="${project.docs_url}" target="_blank" rel="noopener">API reference ↗</a>${savedButton(project)}</div><div class="dialog-tabs" role="group" aria-label="Project details"><button data-tab="overview" aria-pressed="true">Overview</button><button data-tab="source" aria-pressed="false">Source code</button><button data-tab="readme" aria-pressed="false">README</button></div><div id="case-content" aria-live="polite"></div>`
  void renderCase('overview')
  if (!dialog.open) dialog.showModal()
  if (push) history.pushState({ project: slug }, '', `/projects/${slug}`)
  document.title = `${project.title} — Sanan Shahverdi`
}

async function renderCase(tab) {
  const project = state.current
  const version = ++state.viewVersion
  state.tab = tab
  dialog.querySelectorAll('[data-tab]').forEach((button) => button.setAttribute('aria-pressed', button.dataset.tab === tab))
  const container = $('#case-content')
  if (tab === 'overview') {
    container.innerHTML = `<div class="case-grid"><div class="case-block"><h3>The problem</h3><p>${escape(project.problem)}</p></div><div class="case-block"><h3>The approach</h3><p>${escape(project.approach)}</p></div></div><div class="case-highlights"><h3>What you can try</h3><ul>${project.highlights.map((item) => `<li>${escape(item)}</li>`).join('')}</ul><div class="tag-list">${project.stack.map((item) => `<span>${escape(item)}</span>`).join('')}</div></div><div class="case-boundary"><strong>Implementation scope:</strong> ${escape(project.mode)}. Read the README for the storage, provider, and production boundaries. Sample data loads from inside each demo.</div>`
    return
  }
  container.innerHTML = '<p class="muted">Loading project files…</p>'
  try {
    if (tab === 'readme') {
      const data = await api(`${project.api_url}/readme`)
      if (version !== state.viewVersion) return
      container.innerHTML = `<p class="muted">${escape(data.path)}</p><pre class="code-view readme-view">${escape(data.content)}</pre>`
    } else {
      const data = await api(`${project.api_url}/files`)
      if (version !== state.viewVersion) return
      if (!data.files.length) { container.innerHTML = '<p class="muted">No source files are available.</p>'; return }
      const initial = data.files.find((path) => path.endsWith('/api/app.py')) || data.files[0]
      container.innerHTML = `<label class="source-selector">Inspect a source file<select id="source-file">${data.files.map((path) => `<option value="${escape(path)}" ${path === initial ? 'selected' : ''}>${escape(path)}</option>`).join('')}</select></label><pre id="source-code" class="code-view" tabindex="0" aria-label="Source code">Loading…</pre>`
      await loadSource(initial)
    }
  } catch (error) {
    if (version === state.viewVersion) container.innerHTML = `<p role="alert" class="muted">${escape(error.message)}</p><button class="text-link" data-tab="${tab}">Try again</button>`
  }
}

let sourceVersion = 0
async function loadSource(path) {
  const version = ++sourceVersion
  const slug = state.current.slug
  const code = $('#source-code')
  code.textContent = 'Loading…'
  try {
    const data = await api(`${state.current.api_url}/source?path=${encodeURIComponent(path)}`)
    if (version === sourceVersion && state.current.slug === slug) code.textContent = data.content
  } catch (error) {
    if (version === sourceVersion) code.textContent = error.message
  }
}

const saving = new Set()
async function toggleSave(slug) {
  if (saving.has(slug)) return
  saving.add(slug)
  const enabled = !state.saved.includes(slug)
  try {
    const data = await api(`/api/saved/${slug}`, { method: 'PUT', body: JSON.stringify({ saved: enabled }) })
    state.saved = data.saved
    // Update buttons in place, keeping the focused element intact.
    document.querySelectorAll(`[data-save="${slug}"]`).forEach((button) => {
      const title = state.projects.find((project) => project.slug === slug).title
      button.setAttribute('aria-pressed', enabled)
      button.setAttribute('aria-label', `${enabled ? 'Unsave' : 'Save'} ${title}`)
      button.title = enabled ? 'Remove from saved' : 'Save project'
      button.textContent = enabled ? '★' : '☆'
    })
    $('#saved-count').textContent = state.saved.length
    if (state.savedOnly) renderDirectory()
    toast(enabled ? 'Saved to your local collection.' : 'Removed from saved projects.')
  } catch (error) { toast(error.message) }
  finally { saving.delete(slug) }
}

function clearFilters() {
  state.category = 'All work'
  state.query = ''
  state.savedOnly = false
  $('#project-search').value = ''
  renderFilters()
  renderDirectory()
}

document.addEventListener('click', (event) => {
  const target = event.target.closest('button')
  if (!target) return
  if (target.dataset.project) openProject(target.dataset.project)
  if (target.dataset.save) void toggleSave(target.dataset.save)
  if (target.dataset.category) {
    state.category = target.dataset.category
    document.querySelectorAll('[data-category]').forEach((button) => button.setAttribute('aria-pressed', button === target))
    renderDirectory()
  }
  if (target.dataset.tab) void renderCase(target.dataset.tab)
  if (target.classList.contains('close-dialog')) target.closest('dialog').close()
  if (target.id === 'clear-filters') clearFilters()
  if (target.id === 'retry-projects') void loadProjects()
})

$('#project-search').addEventListener('input', (event) => { state.query = event.target.value; renderDirectory() })
$('#saved-filter').addEventListener('click', () => { state.savedOnly = !state.savedOnly; renderDirectory() })
$('#refresh-status').addEventListener('click', refreshStatus)
dialog.addEventListener('change', (event) => { if (event.target.id === 'source-file') void loadSource(event.target.value) })
dialog.addEventListener('close', () => {
  ++state.viewVersion
  ++sourceVersion
  if (location.pathname.startsWith('/projects/')) history.replaceState(null, '', '/#work')
  document.title = 'Sanan Shahverdi — Full-stack & backend engineer'
})
window.addEventListener('popstate', () => {
  const slug = location.pathname.match(/^\/projects\/([^/]+)$/)?.[1]
  if (slug) openProject(slug, false)
  else if (dialog.open) dialog.close()
})
document.querySelectorAll('dialog').forEach((element) => {
  element.addEventListener('click', (event) => {
    if (event.target !== element) return
    const rect = element.getBoundingClientRect()
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) element.close()
  })
})

$('#copy-email').addEventListener('click', async () => {
  try { await navigator.clipboard.writeText('shahverdi.senan@gmail.com'); toast('Email address copied.') }
  catch { toast('Email: shahverdi.senan@gmail.com') }
})

$('#note-form').addEventListener('submit', async (event) => {
  event.preventDefault()
  const form = event.currentTarget
  const button = $('button[type=submit]', form)
  const status = $('#note-status')
  const data = Object.fromEntries(new FormData(form))
  button.disabled = true
  status.textContent = 'Saving locally…'
  status.className = ''
  try {
    await api('/api/notes', { method: 'POST', body: JSON.stringify(data) })
    form.reset()
    status.textContent = 'Note saved on this computer. No email was sent.'
  } catch (error) { status.className = 'error'; status.textContent = error.message }
  finally { button.disabled = false }
})

$('#view-notes').addEventListener('click', async () => {
  const notesDialog = $('#notes-dialog')
  $('#notes-list').innerHTML = '<p class="muted">Loading saved notes…</p>'
  notesDialog.showModal()
  try {
    const notes = await api('/api/notes')
    $('#notes-list').innerHTML = notes.length ? notes.map((note) => `<article class="note-entry"><div><strong>${escape(note.name)}</strong><small>${escape(note.created_at)} UTC</small></div><small>${escape(note.email)}</small><p>${escape(note.message)}</p></article>`).join('') : '<div class="empty-state"><h3>No notes saved yet.</h3><p>Save a note for your next portfolio review.</p></div>'
  } catch (error) { $('#notes-list').textContent = error.message }
})

void loadProjects()
void refreshStatus()
