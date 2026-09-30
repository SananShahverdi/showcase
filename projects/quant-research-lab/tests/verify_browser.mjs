import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, mkdir, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import puppeteer from 'puppeteer'

// Drives the Quant Research Lab console inside an isolated portfolio hub.
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')
const stateDir = await mkdtemp(join(tmpdir(), 'portfolio-quant-lab-'))
const screenshots = join(root, 'projects/quant-research-lab/.local/screenshots')
await mkdir(screenshots, { recursive: true })
const port = process.env.PORTFOLIO_TEST_PORT || '3103'
const origin = `http://127.0.0.1:${port}`
const env = { ...process.env, PORTFOLIO_STATE_DIR: stateDir, RAG_STATE_DIR: join(stateDir, 'rag'), DATA_QUALITY_STATE_FILE: join(stateDir, 'orbit.json'), CAPACITY_STATE_FILE: join(stateDir, 'capacity.json'), DELIVERY_DESK_DB: join(stateDir, 'delivery.sqlite3'), STOCKROOM_INVENTORY_DB: join(stateDir, 'stockroom.sqlite3') }
const server = spawn('python3', ['-m', 'uvicorn', 'hub.app:app', '--host', '127.0.0.1', '--port', port], { cwd: root, env, stdio: ['ignore', 'pipe', 'pipe'] })
let serverLog = ''
server.stdout.on('data', (data) => { serverLog += data })
server.stderr.on('data', (data) => { serverLog += data })
const pass = (label) => console.log(`PASS ${label}`)
let browser
try {
  for (let attempt = 0; attempt < 150; attempt++) {
    if (server.exitCode !== null) throw new Error(`Test server exited: ${serverLog}`)
    try { if ((await fetch(`${origin}/health`)).ok) break } catch { /* startup */ }
    if (attempt === 149) throw new Error(`Test server did not become ready: ${serverLog}`)
    await new Promise((done) => setTimeout(done, 150))
  }
  browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox'] })
  const page = await browser.newPage()
  const errors = []
  page.on('pageerror', (error) => errors.push(error.message))
  page.setDefaultTimeout(90000)
  await page.setViewport({ width: 1440, height: 1000 })
  await page.goto(`${origin}/demos/quant-research-lab/`, { waitUntil: 'networkidle0' })
  await page.waitForFunction(() => document.querySelectorAll('#dataset option').length >= 2)
  assert.match(await page.$eval('#dataset-meta', (el) => el.textContent), /2,517 rows/)
  pass('console loads bundled datasets through the hub')

  await page.click('#forecast-form button[type="submit"]')
  await page.waitForFunction(() => document.querySelector('#forecast-result').getAttribute('aria-busy') === 'false' && document.querySelector('#forecast-result table'))
  const rows = await page.$$eval('#forecast-result tbody tr', (trs) => trs.length)
  assert.equal(rows, 5)
  assert.match(await page.$eval('.finding', (el) => el.textContent), /random walk at the 5% level/)
  pass('walk-forward study renders five model scores and a finding')

  await page.click('#tab-strategy')
  await page.click('#strategy-form button[type="submit"]')
  await page.waitForSelector('#strategy-result svg polyline.series-b')
  assert.match(await page.$eval('#strategy-result', (el) => el.textContent), /Max drawdown/)
  pass('strategy backtest renders equity chart and benchmark table')

  await page.click('#tab-risk')
  await page.waitForSelector('#risk-result .stats')
  assert.equal(await page.$$eval('#risk-result .stat', (cards) => cards.length), 7)
  await page.screenshot({ path: join(screenshots, 'quant-lab-risk.png'), fullPage: true })
  pass('risk view renders VaR, GARCH, and Hurst cards')

  const csvPath = join(stateDir, 'upload.csv')
  const lines = ['Date,Close,Volume']
  let price = 40
  for (let i = 0; i < 320; i++) {
    const day = new Date(Date.UTC(2021, 0, 4 + i))
    price *= 1 + Math.sin(i / 7) * 0.01
    lines.push(`${day.toISOString().slice(0, 10)},${price.toFixed(3)},${1000 + i}`)
  }
  await writeFile(csvPath, lines.join('\n'))
  await page.click('#upload-open')
  await page.waitForSelector('#upload-dialog[open]')
  await page.type('#upload-form [name="name"]', 'Browser upload')
  const input = await page.$('#upload-form [name="file"]')
  await input.uploadFile(csvPath)
  await page.click('#upload-submit')
  await page.waitForFunction(() => document.querySelector('#notice').textContent.includes('Browser upload added: 320 rows'))
  await page.waitForSelector('#risk-result .stats')
  assert.match(await page.$eval('#dataset-meta', (el) => el.textContent), /365 trading days\/year/)
  pass('CSV upload adds a dataset, selects it, and refreshes the risk view')

  await page.focus('#tab-risk')
  await page.keyboard.press('ArrowLeft')
  assert.equal(await page.evaluate(() => document.activeElement.id), 'tab-strategy')
  assert.equal(await page.$eval('#tab-strategy', (el) => el.getAttribute('aria-selected')), 'true')
  assert.equal(await page.$eval('#view-strategy', (el) => el.hidden), false)
  await page.keyboard.press('Home')
  assert.equal(await page.evaluate(() => document.activeElement.id), 'tab-forecast')
  assert.deepEqual(await page.$$eval('[role="tab"]', (tabs) => tabs.map((tab) => tab.tabIndex)), [0, -1, -1])
  pass('tabs follow the keyboard pattern: arrows and Home move focus and selection')

  await page.click('#forecast-form button[type="submit"]')
  await page.select('#dataset', 'aapl-daily')
  await page.waitForFunction(() => !document.querySelector('#forecast-form button[type="submit"]').disabled, { timeout: 60000 })
  assert.equal(await page.$('#forecast-result table'), null, 'a study for the previous dataset must not render after switching')
  assert.match(await page.$eval('#forecast-result', (el) => el.textContent), /Run the study/)
  pass('switching datasets mid-run discards the stale result')

  await page.setViewport({ width: 390, height: 844, isMobile: true })
  await page.reload({ waitUntil: 'networkidle0' })
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
  assert.ok(overflow <= 1, `page overflows horizontally by ${overflow}px`)
  await page.screenshot({ path: join(screenshots, 'quant-lab-mobile.png'), fullPage: true })
  assert.deepEqual(errors, [])
  pass('mobile layout has no horizontal overflow and no runtime errors')
} finally {
  await browser?.close()
  server.kill('SIGTERM')
}
