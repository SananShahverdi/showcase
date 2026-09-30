import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { mkdtemp, mkdir, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import puppeteer from 'puppeteer'

// Drives the Multi-Task PPO Lab console inside an isolated portfolio hub.
const root = resolve(dirname(fileURLToPath(import.meta.url)), '../../..')
const stateDir = await mkdtemp(join(tmpdir(), 'portfolio-ppo-lab-'))
const screenshots = join(root, 'projects/multitask-ppo-lab/.local/screenshots')
await mkdir(screenshots, { recursive: true })
const port = process.env.PORTFOLIO_TEST_PORT || '3104'
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
  page.setDefaultTimeout(60000)
  await page.setViewport({ width: 1440, height: 1000 })
  await page.goto(`${origin}/demos/multitask-ppo-lab/`, { waitUntil: 'networkidle0' })
  await page.waitForSelector('#evaluation table')
  assert.equal(await page.$$eval('#evaluation tbody tr', (rows) => rows.length), 8)
  assert.equal(await page.$$eval('#curves svg', (charts) => charts.length), 4)
  pass('summary renders evaluation table and four learning curves')

  await page.waitForFunction(() => document.querySelectorAll('#boards .episode').length === 3)
  await page.waitForFunction(() => document.querySelectorAll('#boards .episode.won, #boards .episode.lost').length === 3, { timeout: 60000 })
  const optimal = await page.$$eval('#boards .episode', (cards) => cards[2].textContent)
  assert.match(optimal, /Solved in \d+ steps/)
  pass('replay animates random, PPO, and optimal agents to completion')

  assert.match(await page.$eval('#replay-status', (el) => el.textContent), /^Key and door, layout 2/)
  await page.screenshot({ path: join(screenshots, 'ppo-lab-key-door.png'), fullPage: true })
  await page.select('#task', 'navigation')
  await page.waitForFunction(() => /^Navigation/.test(document.querySelector('#replay-status').textContent))
  await page.waitForFunction(() => document.querySelectorAll('#boards .episode.won, #boards .episode.lost').length === 3, { timeout: 60000 })
  pass('first view shows the key-and-door task; switching to navigation replays that task')

  await page.click('#shuffle')
  await page.waitForFunction(() => document.querySelectorAll('#boards .episode').length === 3)
  pass('new layout button replays on another held-out layout')

  await page.setViewport({ width: 390, height: 844, isMobile: true })
  await page.reload({ waitUntil: 'networkidle0' })
  await page.waitForSelector('#evaluation table')
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
  assert.ok(overflow <= 1, `page overflows horizontally by ${overflow}px`)
  await page.screenshot({ path: join(screenshots, 'ppo-lab-mobile.png'), fullPage: true })
  assert.deepEqual(errors, [])
  pass('mobile layout has no horizontal overflow and no runtime errors')
} finally {
  await browser?.close()
  server.kill('SIGTERM')
}
