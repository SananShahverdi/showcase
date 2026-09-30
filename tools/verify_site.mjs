// Browser checks for the static overview site in site/: data loads, every
// interactive section renders, and the layout holds at desktop and phone widths.
import { createServer } from 'node:http'
import { readFile } from 'node:fs/promises'
import { extname, join, normalize } from 'node:path'
import { fileURLToPath } from 'node:url'
import puppeteer from 'puppeteer'

const root = fileURLToPath(new URL('../site/', import.meta.url))
const types = { '.html': 'text/html', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.svg': 'image/svg+xml', '.webp': 'image/webp', '.pdf': 'application/pdf' }
const server = createServer(async (request, response) => {
  let path = normalize(decodeURIComponent(new URL(request.url, 'http://x').pathname)).replace(/^([/\\])+/, '')
  if (!path || path === '.' || path.endsWith('/')) path += 'index.html'
  if (path.startsWith('..')) return response.writeHead(403).end()
  try {
    const body = await readFile(join(root, path))
    response.writeHead(200, { 'content-type': types[extname(path)] || 'application/octet-stream' }).end(body)
  } catch { response.writeHead(404).end() }
}).listen(0, '127.0.0.1')
await new Promise((resolve) => server.once('listening', resolve))
const url = `http://127.0.0.1:${server.address().port}/`

const failures = []
const check = (condition, message) => { if (!condition) failures.push(message) }
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
const browser = await puppeteer.launch({ headless: true, args: ['--no-sandbox'] })
try {
  for (const [name, width, height, isMobile] of [['desktop', 1440, 900, false], ['mobile', 390, 844, true]]) {
    const page = await browser.newPage()
    const errors = []
    page.on('pageerror', (error) => errors.push(error.message))
    page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()) })
    page.on('requestfailed', (request) => { if (!request.url().includes('fonts.g')) errors.push(`request failed: ${request.url()}`) })
    await page.setViewport({ width, height, isMobile })
    await page.goto(url, { waitUntil: 'networkidle0' })
    await page.waitForSelector('#grid li')

    const state = await page.evaluate(() => ({
      overflow: document.documentElement.scrollWidth - innerWidth,
      cards: document.querySelectorAll('#grid li').length,
      boards: document.querySelectorAll('#replay .board').length,
      bars: document.querySelectorAll('#nf-bars .bar-row').length,
      models: document.querySelectorAll('#q-models .model-row').length,
      equity: document.querySelectorAll('#q-equity path.draw').length,
      stats: document.querySelector('#ppo-stats').textContent,
      github: document.querySelector('[data-github]').href,
    }))
    check(state.overflow <= 0, `${name}: page scrolls horizontally by ${state.overflow}px`)
    check(state.cards === 23, `${name}: expected 23 project cards, found ${state.cards}`)
    check(state.boards === 3, `${name}: expected 3 replay boards, found ${state.boards}`)
    check(state.bars === 3 && state.models === 5 && state.equity === 2, `${name}: case-study charts incomplete`)
    check(/\d+(\.\d)?%/.test(state.stats), `${name}: PPO statistics missing`)
    check(state.github.startsWith('https://github.com/'), `${name}: GitHub link not set`)

    await page.click('[data-task="navigation"]')
    check(await page.$eval('[data-task="navigation"]', (b) => b.getAttribute('aria-selected')) === 'true', `${name}: task toggle did not select`)
    const before = await page.$eval('#nf-bars', (el) => el.textContent)
    await page.$eval('#nf-load', (input) => { input.value = '4'; input.dispatchEvent(new Event('input')) })
    check(await page.$eval('#nf-load-out', (el) => el.textContent) === '130%', `${name}: load slider output did not update`)
    check(await page.$eval('#nf-bars', (el) => el.textContent) !== before, `${name}: load slider did not change the bars`)

    await page.click('[data-cat="Research"]')
    const research = await page.$$eval('#grid li', (items) => items.length)
    check(research > 0 && research < 23, `${name}: category filter returned ${research} cards`)
    await page.click('[data-cat="All"]')
    await page.type('#search', 'PyTorch')
    check(await page.$$eval('#grid li', (items) => items.length) >= 1, `${name}: search for PyTorch found nothing`)
    await page.$eval('#search', (input) => { input.value = ''; input.dispatchEvent(new Event('input')) })

    await page.$eval('[data-slug]', (button) => button.click())
    await wait(300)
    check(await page.$eval('#project-dialog', (d) => d.open && d.querySelector('h2')?.textContent.length > 0), `${name}: project dialog did not open`)
    await page.keyboard.press('Escape')
    check(!(await page.$eval('#project-dialog', (d) => d.open)), `${name}: dialog did not close on Escape`)

    const theme = await page.$eval('html', (el) => el.dataset.theme)
    await page.click('#theme')
    check(await page.$eval('html', (el) => el.dataset.theme) !== theme, `${name}: theme toggle did nothing`)

    check(errors.length === 0, `${name}: ${errors.join('; ')}`)
    await page.close()
  }
} finally {
  await browser.close()
  server.close()
}
if (failures.length) { console.error(failures.map((f) => `FAIL ${f}`).join('\n')); process.exit(1) }
console.log('Overview site: all checks passed at desktop and mobile widths.')
