import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, mkdir } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import puppeteer from 'puppeteer'

// Exercise both business apps against an isolated hub and fresh SQLite files.
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')
const stateDir = await mkdtemp(join(tmpdir(), 'portfolio-business-apps-'))
const screenshots = join(root, 'projects/delivery-desk/.local/screenshots')
await mkdir(screenshots, { recursive: true })
const port = process.env.PORTFOLIO_TEST_PORT || '3102'
const origin = `http://127.0.0.1:${port}`
const env = { ...process.env, PORTFOLIO_STATE_DIR: stateDir, RAG_STATE_DIR: join(stateDir, 'rag'), DATA_QUALITY_STATE_FILE: join(stateDir, 'orbit.json'), CAPACITY_STATE_FILE: join(stateDir, 'capacity.json'), DELIVERY_DESK_DB: join(stateDir, 'delivery.sqlite3'), STOCKROOM_INVENTORY_DB: join(stateDir, 'stockroom.sqlite3') }
let server, browser, serverLog = '', passes = 0
const pass = (label) => { passes++; console.log(`PASS ${label}`) }

async function startServer() {
  server = spawn('python3', ['-m', 'uvicorn', 'hub.app:app', '--host', '127.0.0.1', '--port', port], { cwd: root, env, stdio: ['ignore', 'pipe', 'pipe'] })
  server.on('error', (error) => { serverLog += error.message })
  server.stdout.on('data', (data) => { serverLog += data })
  server.stderr.on('data', (data) => { serverLog += data })
  for (let attempt = 0; attempt < 600; attempt++) { // the hub imports every project, allow up to 60 s
    if (server.exitCode !== null) throw new Error(`Test server exited: ${serverLog}`)
    try { if ((await fetch(`${origin}/health`)).ok) return } catch { /* startup */ }
    await new Promise((resolve) => setTimeout(resolve, 100))
  }
  throw new Error(`Test server did not become ready: ${serverLog}`)
}
async function stopServer() {
  if (server && server.exitCode === null) {
    server.kill('SIGTERM')
    await new Promise((resolve) => server.once('exit', resolve))
  }
}
async function fill(page, selector, value) {
  await page.focus(selector)
  await page.keyboard.down('Control')
  await page.keyboard.press('A')
  await page.keyboard.up('Control')
  await page.keyboard.press('Backspace')
  if (value) await page.type(selector, String(value))
}
async function loaded(page, selector) {
  await page.waitForFunction((selector) => document.querySelector(selector)?.getAttribute('aria-busy') === 'false', {}, selector)
}
async function mobileFits(page, dialog) {
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'Page fits the mobile viewport')
  if (dialog) assert.ok(await page.$eval(dialog, (element) => element.scrollWidth <= element.clientWidth), 'Dialog fits the mobile viewport')
}
const api = async (slug, path) => {
  const response = await fetch(`${origin}/api/projects/${slug}/api${path}`)
  assert.equal(response.status, 200)
  return response.json()
}

try {
  await startServer()
  browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox'] })
  const page = await browser.newPage()
  page.setDefaultTimeout(10000)
  const errors = []
  page.on('pageerror', (error) => errors.push(error.message))
  await page.setViewport({ width: 1440, height: 1000 })
  await page.goto(`${origin}/demos/delivery-desk/`, { waitUntil: 'networkidle0' })
  await loaded(page, '#board')
  assert.equal(await page.$$eval('.column', (columns) => columns.length), 4, await page.$eval('#notice', (element) => element.textContent))
  assert.equal(await page.$eval('#total-count', (element) => element.textContent), '0')
  pass('Delivery Desk opens with All priorities selected and an empty board')

  const taskTitle = 'Browser task <img src=x onerror="window.injected=true">'
  await page.click('#new-task')
  await page.waitForSelector('#task-dialog[open]')
  await page.type('[name="title"]', taskTitle)
  await fill(page, '[name="project"]', 'Browser project')
  await page.type('[name="description"]', 'A real browser-created task with saved details.')
  await page.type('[name="assignee"]', 'Local reviewer')
  await page.select('[name="priority"]', 'high')
  await page.click('#save')
  await page.waitForSelector('.task-title')
  await loaded(page, '#board')
  assert.equal(await page.$eval('.task-title', (element) => element.textContent), taskTitle)
  assert.equal(await page.evaluate(() => window.injected), undefined)
  const taskId = (await api('delivery-desk', '/tasks')).items[0].id
  pass('Task creation persists its fields and safely renders user text')

  await page.click(`.column-backlog [data-move="${taskId}"]`)
  await page.waitForSelector(`.column-in_progress [data-edit="${taskId}"]`)
  await page.click(`[data-edit="${taskId}"]`)
  await page.waitForSelector('#task-dialog[open]')
  await fill(page, '[name="title"]', 'Release checklist complete')
  await page.select('[name="status"]', 'review')
  await page.click('#save')
  await page.waitForSelector(`.column-review [data-edit="${taskId}"]`)
  await page.click(`[data-move="${taskId}"]`)
  await page.waitForSelector(`.column-done [data-edit="${taskId}"]`)
  await page.reload({ waitUntil: 'networkidle0' })
  await page.waitForSelector(`.column-done [data-edit="${taskId}"]`)
  await page.click(`[data-edit="${taskId}"]`)
  await page.waitForSelector('#task-dialog[open]')
  assert.equal(await page.$$eval('#history li', (events) => events.length), 4)
  await page.keyboard.press('Escape')
  pass('Task edits, stage moves, history, and reload persistence')

  await page.select('#priority-filter', 'low')
  await page.waitForFunction(() => document.querySelectorAll('.task').length === 0)
  await page.select('#priority-filter', '')
  await page.waitForSelector('.task')
  await page.type('#search', 'does not exist')
  await page.waitForFunction(() => document.querySelectorAll('.task').length === 0)
  await fill(page, '#search', '')
  await page.waitForSelector('.task')
  await page.click('#seed')
  await page.waitForFunction(() => document.querySelector('#total-count').textContent === '7')
  await page.select('#project-filter', 'Browser project')
  await page.waitForFunction(() => document.querySelectorAll('.task').length === 1)
  await page.select('#project-filter', '')
  await page.waitForFunction(() => document.querySelectorAll('.task').length === 7)
  await page.screenshot({ path: join(screenshots, 'delivery-desktop.png'), fullPage: true })
  pass('Task search, priority reset, project filter, and sample workspace')

  await page.setOfflineMode(true)
  await page.click('#refresh')
  await page.waitForFunction(() => document.querySelector('#notice').textContent.includes('unreachable'))
  await page.setOfflineMode(false)
  await page.click('#refresh')
  await loaded(page, '#board')
  assert.equal(await page.$$eval('.task', (tasks) => tasks.length), 7)
  pass('Delivery Desk keeps the board usable after a recoverable service error')

  await page.setViewport({ width: 390, height: 844 })
  await page.reload({ waitUntil: 'networkidle0' })
  await page.waitForSelector('.task')
  await mobileFits(page)
  await page.screenshot({ path: join(screenshots, 'delivery-mobile.png'), fullPage: true })
  await page.click('#new-task')
  await page.waitForSelector('#task-dialog[open]')
  await mobileFits(page, '#task-dialog')
  await page.keyboard.press('Escape')
  pass('Delivery Desk mobile board, editor, and keyboard dismissal')

  await page.setViewport({ width: 1440, height: 1000 })
  await page.goto(`${origin}/demos/stockroom-inventory/`, { waitUntil: 'networkidle0' })
  await loaded(page, '#records')
  assert.equal(await page.$eval('#item-count', (element) => element.textContent), '0')
  await page.click('#new-item')
  await page.waitForSelector('#item-dialog[open]')
  await page.type('#item-form [name="name"]', 'Browser test adapter')
  await page.type('[name="sku"]', 'BROWSER-ADAPTER')
  await fill(page, '[name="location"]', 'A-99')
  await fill(page, '#item-form [name="quantity"]', '10')
  await page.click('#save-item')
  await page.waitForSelector('[data-edit]')
  await loaded(page, '#records')
  const itemId = (await api('stockroom-inventory', '/items')).items[0].id
  assert.equal((await api('stockroom-inventory', `/items/${itemId}`)).quantity, 10)
  assert.equal((await api('stockroom-inventory', '/movements')).total, 1)
  pass('Inventory item creation records opening stock in the ledger')

  await page.click(`[data-edit="${itemId}"]`)
  await page.waitForSelector('#item-dialog[open]')
  assert.ok(await page.$eval('[name="sku"]', (input) => input.disabled))
  assert.ok(await page.$eval('[name="unit"]', (input) => input.disabled))
  await fill(page, '[name="location"]', 'B-01')
  await page.click('#save-item')
  await page.waitForFunction(() => document.querySelector('.shelf')?.textContent === 'B-01')
  pass('Item editor saves catalog metadata and protects immutable fields')

  await page.click(`[data-stock="${itemId}"][data-kind="receive"]`)
  await page.waitForSelector('#movement-dialog[open]')
  await fill(page, '#movement-form [name="quantity"]', '4')
  await page.type('[name="reason"]', 'Supplier delivery')
  await page.type('[name="reference"]', 'PO-14')
  await page.click('#save-movement')
  await page.waitForFunction(() => document.querySelector('#notice').textContent.startsWith('Receipt recorded.') && document.querySelector('#notice').textContent.includes(' 14 units'))
  await loaded(page, '#records')
  await page.click(`[data-stock="${itemId}"][data-kind="dispatch"]`)
  await page.waitForSelector('#movement-dialog[open]')
  await fill(page, '#movement-form [name="quantity"]', '10')
  await page.type('[name="reason"]', 'Order packed')
  await page.click('#save-movement')
  await page.waitForFunction(() => document.querySelector('#notice').textContent.startsWith('Dispatch recorded.') && document.querySelector('#notice').textContent.includes(' 4 units'))
  await loaded(page, '#records')
  assert.match(await page.$eval('.stock-status', (element) => element.textContent), /Reorder needed/)
  pass('Receipt and dispatch update the balance and low-stock status')

  await page.click(`[data-stock="${itemId}"][data-kind="dispatch"]`)
  await page.waitForSelector('#movement-dialog[open]')
  await fill(page, '#movement-form [name="quantity"]', '5')
  await page.type('[name="reason"]', 'Should be rejected')
  await page.click('#save-movement')
  await page.waitForFunction(() => document.querySelector('#movement-error').textContent.includes('Only 4 units'))
  assert.equal((await api('stockroom-inventory', `/items/${itemId}`)).quantity, 4)
  assert.equal((await api('stockroom-inventory', '/movements')).total, 3)
  await page.keyboard.press('Escape')
  await page.click('[data-view="ledger"]')
  await page.waitForSelector('.ledger')
  assert.equal(await page.$$eval('.ledger tbody tr', (rows) => rows.length), 3)
  assert.match(await page.$eval('.ledger tbody tr', (row) => row.textContent), /Order packed/)
  await page.select('#ledger-kind', 'receive')
  await page.waitForFunction(() => document.querySelectorAll('.ledger tbody tr').length === 2)
  await page.select('#ledger-kind', '')
  await page.waitForFunction(() => document.querySelectorAll('.ledger tbody tr').length === 3)
  pass('Oversized dispatch is rejected without changing stock or ledger; ledger filters work')

  await page.click('[data-view="catalog"]')
  await page.waitForSelector('[data-edit]')
  await page.click('#seed')
  await page.waitForFunction(() => document.querySelector('#item-count').textContent === '7')
  await loaded(page, '#records')
  await page.type('#search', 'BROWSER-ADAPTER')
  await page.waitForFunction(() => document.querySelectorAll('#records tbody tr').length === 1)
  await fill(page, '#search', '')
  await page.waitForFunction(() => document.querySelectorAll('#records tbody tr').length === 7)
  await page.click('#show-low')
  await page.waitForFunction(() => document.querySelectorAll('#records tbody tr').length === 4)
  await page.click('[data-view="catalog"]')
  await page.waitForFunction(() => document.querySelectorAll('#records tbody tr').length === 7)
  await page.screenshot({ path: join(screenshots, 'stockroom-desktop.png'), fullPage: true })
  pass('Inventory search, low-stock view, and optional sample data')

  await page.setViewport({ width: 390, height: 844 })
  await page.reload({ waitUntil: 'networkidle0' })
  await page.waitForSelector('[data-edit]')
  await mobileFits(page)
  await page.screenshot({ path: join(screenshots, 'stockroom-mobile.png'), fullPage: true })
  await page.click('#new-item')
  await page.waitForSelector('#item-dialog[open]')
  await mobileFits(page, '#item-dialog')
  await page.keyboard.press('Escape')
  await page.click('#record-movement')
  await page.waitForSelector('#movement-dialog[open]')
  await mobileFits(page, '#movement-dialog')
  await page.keyboard.press('Escape')
  await page.click('[data-view="ledger"]')
  await page.waitForSelector('.ledger')
  await mobileFits(page)
  pass('Stockroom mobile catalog, ledger, item editor, and movement form')

  await stopServer()
  await startServer()
  assert.equal((await api('delivery-desk', `/tasks/${taskId}`)).title, 'Release checklist complete')
  assert.equal((await api('delivery-desk', `/tasks/${taskId}`)).history.length, 4)
  assert.equal((await api('stockroom-inventory', `/items/${itemId}`)).quantity, 4)
  assert.equal((await api('stockroom-inventory', `/movements?item_id=${itemId}`)).total, 3)
  pass('Task history, inventory balance, and ledger persist across a server restart')
  assert.deepEqual(errors, [])
  pass('Both apps complete their workflows without browser runtime errors')
  console.log(`${passes} browser checks passed. Screenshots: ${screenshots}`)
} finally {
  if (browser) await browser.close()
  await stopServer()
}
