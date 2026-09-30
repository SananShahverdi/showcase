import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, mkdir } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import puppeteer from 'puppeteer'

// This test owns an isolated server and database; it never resets the user's demo state.
const root = dirname(dirname(fileURLToPath(import.meta.url)))
const stateDir = await mkdtemp(join(tmpdir(), 'portfolio-browser-'))
const screenshots = join(root, '.local', 'screenshots')
await mkdir(screenshots, { recursive: true })
const port = process.env.PORTFOLIO_TEST_PORT || '3100'
const origin = `http://127.0.0.1:${port}`
let serverLog = ''
const server = spawn('python3', ['-m', 'uvicorn', 'hub.app:app', '--host', '127.0.0.1', '--port', port], {
  cwd: root, stdio: ['ignore', 'pipe', 'pipe'],
  env: { ...process.env, PORTFOLIO_STATE_DIR: stateDir, RAG_STATE_DIR: join(stateDir, 'rag'), DATA_QUALITY_STATE_FILE: join(stateDir, 'orbit.json'), CAPACITY_STATE_FILE: join(stateDir, 'capacity.json'), DELIVERY_DESK_DB: join(stateDir, 'delivery.sqlite3'), STOCKROOM_INVENTORY_DB: join(stateDir, 'stockroom.sqlite3') },
})
server.stdout.on('data', (data) => { serverLog += data })
server.stderr.on('data', (data) => { serverLog += data })
let browser
try {
  for (let attempt = 0; attempt < 100; attempt++) {
    if (server.exitCode !== null) throw new Error(`Test server exited: ${serverLog}`)
    try { if ((await fetch(`${origin}/health`)).ok) break } catch { /* wait for startup */ }
    if (attempt === 99) throw new Error(`Test server did not become ready: ${serverLog}`)
    await new Promise((resolve) => setTimeout(resolve, 150))
  }
  browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox'] })
  const page = await browser.newPage()
  const errors = []
  page.on('pageerror', (error) => errors.push(error.message))
  page.setDefaultTimeout(15000)
  await page.setViewport({ width: 1440, height: 1000, deviceScaleFactor: 1 })
  await page.goto(origin, { waitUntil: 'networkidle0' })
  await page.waitForFunction(() => document.querySelectorAll('.project-row').length === 19)
  assert.equal(await page.$$eval('.project-card', (cards) => cards.length), 4)
  await page.waitForFunction(() => document.querySelector('#system-status').textContent.includes('19/19 APIs ready'))
  await page.screenshot({ path: join(screenshots, 'portfolio-desktop.png'), fullPage: true })
  console.log('PASS catalog, live project status, and desktop layout')

  await page.type('#project-search', 'SQLite')
  await page.waitForFunction(() => document.querySelectorAll('.project-row').length === 2)
  await page.$eval('#project-search', (input) => { input.value = ''; input.dispatchEvent(new Event('input', { bubbles: true })) })
  // Locators wait until the element stops moving, so smooth scrolling cannot make a click land elsewhere.
  await page.locator('[data-category="Network systems"]').click()
  await page.waitForFunction(() => document.querySelectorAll('.project-row').length === 2)
  await page.locator('[data-category="All work"]').click()
  await page.locator('.project-card [data-save="delivery-desk"]').click()
  await page.waitForFunction(() => document.querySelector('#saved-count').textContent === '1')
  await page.reload({ waitUntil: 'networkidle0' })
  await page.click('#saved-filter')
  assert.equal(await page.$$eval('.project-row', (rows) => rows.length), 1)
  assert.match(await page.$eval('.project-row', (row) => row.textContent), /Delivery Desk/)
  await page.click('#saved-filter')
  console.log('PASS search, category filters, and saved projects across reload')

  await page.click('.card-title [data-project="compliance-aware-rag-knowledge-base"]')
  await page.waitForSelector('#project-dialog[open]')
  assert.match(page.url(), /\/projects\/compliance-aware-rag-knowledge-base$/)
  await page.click('[data-tab="source"]')
  await page.waitForSelector('#source-file')
  const appFile = await page.$$eval('#source-file option', (options) => options.find((option) => option.value.endsWith('api/app.py')).value)
  await page.select('#source-file', appFile)
  await page.waitForFunction(() => document.querySelector('#source-code').textContent.includes('FastAPI'))
  await page.click('[data-tab="readme"]')
  await page.waitForSelector('.readme-view')
  assert.match(await page.$eval('.readme-view', (element) => element.textContent), /Deployment boundaries/)
  await page.reload({ waitUntil: 'networkidle0' })
  await page.waitForSelector('#project-dialog[open]')
  await page.keyboard.press('Escape')
  await page.waitForFunction(() => !document.querySelector('#project-dialog').open)
  console.log('PASS case study, source reader, README, deep links, and keyboard dismiss')

  await page.type('[name="name"]', 'Browser reviewer')
  await page.type('[name="email"]', 'local@example.com')
  const note = '<img src=x onerror="window.injected=true"> A local browser verification note.'
  await page.type('[name="message"]', note)
  await page.click('#note-form button[type="submit"]')
  await page.waitForFunction(() => document.querySelector('#note-status').textContent.includes('Note saved'))
  assert.equal(await page.$eval('[name="message"]', (input) => input.value), '')
  await page.click('#view-notes')
  await page.waitForSelector('.note-entry')
  assert.equal(await page.$eval('.note-entry p', (element) => element.textContent), note)
  assert.equal(await page.evaluate(() => window.injected), undefined)
  await page.keyboard.press('Escape')
  console.log('PASS persistent note submission and safe text rendering')

  await page.setViewport({ width: 390, height: 844, deviceScaleFactor: 1 })
  await page.goto(origin, { waitUntil: 'networkidle0' })
  await page.waitForSelector('.project-card')
  await page.screenshot({ path: join(screenshots, 'portfolio-mobile.png'), fullPage: true })
  const overflow = await page.evaluate(() => [...document.querySelectorAll('body *')].filter((element) => {
    const box = element.getBoundingClientRect()
    return box.width && (box.right > innerWidth + 1 || box.left < -1)
  }).map((element) => ({ tag: element.tagName, class: element.className, width: element.getBoundingClientRect().width, right: element.getBoundingClientRect().right })))
  assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Mobile page does not overflow horizontally: ${JSON.stringify(overflow)}`)
  await page.click('.card-title [data-project="delivery-desk"]')
  await page.waitForSelector('#project-dialog[open]')
  assert.ok(await page.$eval('#project-dialog', (element) => element.scrollWidth <= element.clientWidth), 'Mobile dialog fits its viewport')
  await page.keyboard.press('Escape')
  await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }])
  assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).scrollBehavior), 'auto')
  assert.deepEqual(errors, [])
  console.log('PASS mobile layout, dialog, reduced motion, and no browser runtime errors')
  console.log(`Screenshots: ${screenshots}`)
} finally {
  if (browser) await browser.close()
  server.kill('SIGTERM')
  await new Promise((resolve) => { if (server.exitCode !== null) resolve(); else server.once('exit', resolve) })
}
