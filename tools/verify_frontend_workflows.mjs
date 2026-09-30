import assert from 'node:assert/strict'
import { mkdtemp, readFile, readdir } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import puppeteer from 'puppeteer'

// Run against the local hub: node tools/verify_frontend_workflows.mjs
// All submitted content is synthetic; demo seed actions reset demo datasets.
const origin = process.env.PORTFOLIO_URL ?? 'http://127.0.0.1:3000'
const slugs = [
  'agentic-ba-automation-platform', 'self-healing-public-data-intelligence-pipeline',
  'network-digital-twin-rl-routing-optimizer', 'local-ai-inference-gateway-llmops-console',
  'aiops-incident-assistant-human-approval', 'ai-code-review-test-gatekeeper',
  'internal-developer-portal-golden-paths', 'real-time-fraud-risk-stream-analytics',
  'ai-security-playground-llm-applications', 'post-quantum-crypto-migration-scanner',
  'process-mining-workflow-automation-analyzer', 'edge-wasm-plugin-runtime-data-network-rules',
  'smart-network-capacity-planner', 'autonomous-data-quality-observatory',
  'compliance-aware-rag-knowledge-base',
]
const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox'] })
const downloads = await mkdtemp(join(tmpdir(), 'portfolio-frontend-downloads-'))
const results = []

async function open(page, slug) {
  const response = await page.goto(`${origin}/demos/${slug}/`, { waitUntil: 'networkidle0' })
  assert.equal(response.status(), 200)
  await page.waitForSelector('h1')
}

async function click(page, label) {
  await page.waitForFunction((text) => [...document.querySelectorAll('button')].some((button) => (button.getAttribute('aria-label') === text || button.textContent.trim() === text) && !button.disabled), {}, label)
  await page.evaluate((text) => [...document.querySelectorAll('button')].find((button) => (button.getAttribute('aria-label') === text || button.textContent.trim() === text) && !button.disabled).click(), label)
}

async function text(page, value) {
  await page.waitForFunction((expected) => document.body.innerText.includes(expected), {}, value)
}

async function fill(page, selector, value) {
  await page.waitForSelector(selector)
  await page.focus(selector)
  await page.keyboard.down('Control')
  await page.keyboard.press('A')
  await page.keyboard.up('Control')
  await page.keyboard.type(value)
}

async function clearErrors(page) {
  assert.deepEqual(await page.$$eval('[role="alert"]', (elements) => elements.map((element) => element.textContent)), [])
}

async function test(name, action) {
  const context = await browser.createBrowserContext()
  const page = await context.newPage()
  await page.setViewport({ width: 1440, height: 1000 })
  page.setDefaultTimeout(15000)
  const errors = []
  page.on('pageerror', (error) => errors.push(error.message))
  try {
    await action(page)
    assert.deepEqual(errors, [], 'Browser runtime errors')
    results.push({ name, status: 'pass' })
    console.log(`PASS ${name}`)
  } catch (error) {
    results.push({ name, status: 'fail', error: error.message })
    console.error(`FAIL ${name}: ${error.message}`)
  } finally { await context.close() }
}

try {
  for (const slug of slugs) {
    await test(`console: ${slug}`, async (page) => {
      const badAssets = []
      const wrongApis = []
      page.on('response', (response) => {
        const url = new URL(response.url())
        if (/\.(js|css|svg)$/.test(url.pathname) && response.status() >= 400) badAssets.push(url.pathname)
        if (url.pathname.startsWith('/api/') && !url.pathname.startsWith(`/api/projects/${slug}/`)) wrongApis.push(url.pathname)
      })
      await open(page, slug)
      assert.notEqual(await page.title(), 'frontend')
      assert.equal(await page.$eval('#portfolio-back-link', (link) => link.getAttribute('href')), '/')
      assert.deepEqual(badAssets, [])
      assert.deepEqual(wrongApis, [])
    })
  }

  await test('requirements: new selection, approval, and JSON download', async (page) => {
    await open(page, slugs[0])
    await click(page, 'Seed demo workspace')
    await text(page, 'Demo evidence indexed')
    await page.select('.generate select', 'acceptance_criteria')
    await click(page, 'Generate')
    await text(page, 'New source-backed artifact is ready')
    assert.match(await page.$eval('.review h2', (element) => element.textContent), /acceptance criteria/)
    await click(page, 'Approve')
    await text(page, 'Artifact approved and export unlocked')
    const client = await page.createCDPSession()
    await client.send('Page.setDownloadBehavior', { behavior: 'allow', downloadPath: downloads })
    await click(page, 'Export Jira JSON')
    await text(page, 'Jira-compatible export created and audited')
    await page.waitForNetworkIdle()
    let files = await readdir(downloads)
    for (let attempt = 0; !files.some((file) => file.endsWith('.json')) && attempt < 10; attempt++) {
      await new Promise((resolve) => setTimeout(resolve, 100))
      files = await readdir(downloads)
    }
    const file = files.find((item) => item.endsWith('.json'))
    assert.ok(file, 'Export writes a JSON download')
    assert.ok(Object.keys(JSON.parse(await readFile(join(downloads, file), 'utf8'))).length)
    await clearErrors(page)
  })

  await test('pipeline: quarantine, replay, and repair activation', async (page) => {
    await open(page, slugs[1])
    await click(page, 'Load fixture fleet')
    await text(page, 'one quarantined')
    await click(page, 'Propose repair')
    await text(page, 'proposal is ready for replay')
    await click(page, 'Run replay')
    await text(page, 'Replay passed')
    await click(page, 'Approve & activate')
    await text(page, 'Recipe version 2 activated')
    await clearErrors(page)
  })

  await test('routing: train, compare, and link failure', async (page) => {
    await open(page, slugs[2])
    await click(page, 'Run complete demo')
    await text(page, 'Seeded six-node lab trained')
    assert.equal(await page.$$eval('.benchmark .row:not(.head)', (rows) => rows.length), 4)
    await click(page, 'Fail n0 → n1')
    await text(page, 'Link n0 → n1 failed')
    await clearErrors(page)
  })

  await test('gateway: mounted chat and embeddings routes', async (page) => {
    await open(page, slugs[3])
    await click(page, 'Seed secure demo')
    await text(page, 'one-time API key are ready')
    await click(page, 'Send chat')
    await text(page, 'Private chat completed')
    await click(page, 'Create embedding')
    await text(page, 'Embedding normalized')
    assert.match(await page.$eval('.response pre', (element) => element.textContent), /^\[/)
    await clearErrors(page)
  })

  await test('incident: detail status refreshes after analysis and decision', async (page) => {
    await open(page, slugs[4])
    await click(page, 'Generate incident')
    await click(page, 'Analyze telemetry & runbooks')
    await page.waitForSelector('.action-card')
    await page.waitForFunction(() => document.querySelector('.detail-panel .panel-heading .badge')?.textContent !== 'open')
    await click(page, 'Approve & execute')
    await page.waitForSelector('.success-output')
    await clearErrors(page)
  })

  await test('review: changed coverage creates fresh policy evidence', async (page) => {
    await open(page, slugs[5])
    await click(page, 'Run policy gate')
    await page.waitForSelector('.result-panel .status')
    const before = await page.$$eval('.history-list > button', (buttons) => buttons.length)
    await page.$eval('input[type="range"]', (input) => {
      const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set
      setter.call(input, '25')
      input.dispatchEvent(new Event('input', { bubbles: true }))
    })
    await text(page, '25%')
    await click(page, 'Run policy gate')
    await page.waitForFunction((count) => document.querySelectorAll('.history-list > button').length > count, {}, before)
    await clearErrors(page)
  })

  await test('developer portal: preview, archive, and invalidated form result', async (page) => {
    await open(page, slugs[6])
    await fill(page, '.form-grid input', `browser-${Date.now()}`)
    await click(page, 'Preview files')
    await text(page, 'Validated file manifest')
    await click(page, 'Generate artifact')
    await page.waitForSelector('a.download')
    const url = await page.$eval('a.download', (link) => link.href)
    assert.ok(url.startsWith(`${origin}/api/projects/${slugs[6]}/api/download/`))
    const response = await fetch(url)
    assert.equal(response.status, 200)
    assert.match(response.headers.get('content-type'), /zip/)
    await fill(page, '.form-grid input', `changed-${Date.now()}`)
    assert.equal(await page.$('a.download'), null)
    await clearErrors(page)
  })

  await test('fraud: analyst feedback updates selected alert', async (page) => {
    await open(page, slugs[7])
    await click(page, 'Seed known scenario')
    await click(page, 'Confirm fraud')
    await page.waitForSelector('.reviewed')
    assert.match(await page.$eval('.detail-panel .panel-heading .decision', (element) => element.textContent), /true positive|true_positive/)
    await clearErrors(page)
  })

  await test('security: both mode results and full assessment', async (page) => {
    await open(page, slugs[8])
    await click(page, 'Compare both modes')
    await page.waitForFunction(() => document.querySelectorAll('.result pre').length === 2)
    await click(page, 'Run full assessment')
    await page.waitForFunction(() => document.querySelector('.metrics .safe')?.textContent.includes('%'))
    await clearErrors(page)
  })

  await test('crypto: inventory and migration evidence', async (page) => {
    await open(page, slugs[9])
    await click(page, 'Load & scan demo estate')
    await page.waitForSelector('.evidence-table .table-row')
    assert.equal(await page.$$eval('.catalog .service', (services) => services.length), 2)
    await clearErrors(page)
  })

  await test('process: CSV discovery and variants', async (page) => {
    await open(page, slugs[10])
    await click(page, 'Analyze event log')
    await page.waitForSelector('.flow')
    await click(page, 'Variants')
    await page.waitForSelector('.variant-list article')
    await clearErrors(page)
  })

  await test('edge: seed and execute typed plugin', async (page) => {
    await open(page, slugs[11])
    await click(page, 'Seed trusted examples')
    await click(page, 'Execute active version')
    await page.waitForSelector('.result .pill.good')
    await clearErrors(page)
  })

  await test('capacity: repeated demo loading and async scenario form', async (page) => {
    await open(page, slugs[12])
    await click(page, 'Load demo portfolio')
    await page.waitForSelector('.chart svg')
    await click(page, 'Load demo portfolio')
    await page.waitForFunction(() => document.querySelector('#forecast h2')?.textContent !== 'Select a link')
    await fill(page, '.scenario-panel input[name="name"]', 'Browser regression capacity plan')
    await click(page, 'Run and save scenario')
    await text(page, 'Scenario “Browser regression capacity plan” saved and compared.')
    assert.equal(await page.$eval('.scenario-panel input[name="name"]', (input) => input.value), '')
    await clearErrors(page)
  })

  await test('observatory: baseline, drift, and incident resolution', async (page) => {
    await open(page, slugs[13])
    await click(page, '↻ Load clean demo')
    await text(page, 'Two healthy datasets')
    await click(page, 'Introduce demo drift')
    await page.waitForSelector('.incident')
    await click(page, 'Resolve')
    await text(page, 'Resolved “')
    await clearErrors(page)
  })

  await test('knowledge: upload, redaction form, and keyboard query', async (page) => {
    await open(page, slugs[14])
    await click(page, 'Load governed demo')
    await text(page, 'governed demo documents added')
    await click(page, 'Documents')
    await page.$eval('input[type="file"]', (input) => {
      const transfer = new DataTransfer()
      transfer.items.add(new File(['The browser regression handbook requires clear release ownership and a recorded approval.'], 'browser-regression.txt', { type: 'text/plain' }))
      input.files = transfer.files
      input.dispatchEvent(new Event('change', { bubbles: true }))
    })
    await fill(page, 'input[name="title"]', `Browser regression handbook ${Date.now()}`)
    await click(page, 'Parse, classify & index')
    await text(page, 'Document parsed, classified, chunked, indexed, and audited.')
    assert.equal(await page.$eval('input[name="title"]', (input) => input.value), '')
    await click(page, 'Governance')
    await fill(page, 'input[name="name"]', `Browser redaction ${Date.now()}`)
    await fill(page, 'input[name="pattern"]', 'BROWSER-SECRET-[0-9]+')
    await click(page, 'Validate & enable')
    await text(page, 'Redaction rule validated, versioned, and enabled.')
    assert.equal(await page.$eval('input[name="name"]', (input) => input.value), '')
    await click(page, 'Ask')
    await page.focus('textarea[aria-label="Question"]')
    await page.keyboard.down('Control')
    await page.keyboard.press('Enter')
    await page.keyboard.up('Control')
    await page.waitForSelector('.answer')
    await clearErrors(page)
  })
} finally { await browser.close() }

console.log(JSON.stringify({ passed: results.filter((result) => result.status === 'pass').length, failed: results.filter((result) => result.status === 'fail'), downloads }, null, 2))
if (results.some((result) => result.status === 'fail')) process.exitCode = 1
