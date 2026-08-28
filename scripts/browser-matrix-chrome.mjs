/**
 * SOTA C-6 evidence probe: exercise both production privacy routes in real Chrome.
 *
 * Prerequisite: npm run build:all
 * Output: .agent_workspace/evidence/r10/browser-matrix-chrome.json + four screenshots.
 */

import { createServer } from 'node:http'
import { existsSync } from 'node:fs'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { extname, join, normalize, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import puppeteer from 'puppeteer-core'

const root = resolve(fileURLToPath(new URL('..', import.meta.url)))
const evidenceDir = join(root, '.agent_workspace/evidence/r10')
const chromePath = process.env.CHROME_PATH ?? '/usr/local/bin/google-chrome'
const apps = [
  {
    id: 'literacy',
    name: '快乐识字',
    dist: join(root, 'apps/literacy-app/dist'),
  },
  {
    id: 'math',
    name: 'MathQuest',
    dist: join(root, 'apps/math-app/dist'),
  },
]
const profiles = [
  { id: 'desktop', viewport: { width: 1440, height: 1000 } },
  {
    id: 'mobile',
    viewport: { width: 390, height: 844, isMobile: true, hasTouch: true },
  },
]
const mime = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2',
}

for (const app of apps) {
  if (!existsSync(join(app.dist, 'index.html'))) {
    throw new Error(`${app.name} 缺少生产构建，请先运行 npm run build:all`)
  }
}
if (!existsSync(chromePath)) throw new Error(`找不到 Chrome: ${chromePath}`)

await mkdir(evidenceDir, { recursive: true })

function staticServer(dist) {
  return createServer(async (request, response) => {
    const url = new URL(request.url, 'http://localhost')
    let file = join(dist, normalize(decodeURIComponent(url.pathname)))
    if (url.pathname === '/' || !existsSync(file)) file = join(dist, 'index.html')

    try {
      const body = await readFile(file)
      response.writeHead(200, {
        'cache-control': 'no-store',
        'content-type': mime[extname(file)] ?? 'application/octet-stream',
      })
      response.end(body)
    } catch {
      response.writeHead(404).end('not found')
    }
  })
}

const browser = await puppeteer.launch({
  executablePath: chromePath,
  headless: 'new',
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--mute-audio'],
})
const browserVersion = await browser.version()
const userAgent = await browser.userAgent()
const results = []

try {
  for (const app of apps) {
    const server = staticServer(app.dist)
    await new Promise((accept) => server.listen(0, '127.0.0.1', accept))
    const origin = `http://127.0.0.1:${server.address().port}`

    try {
      for (const profile of profiles) {
        const page = await browser.newPage()
        await page.setViewport(profile.viewport)
        const errors = []
        const requests = []

        page.on('console', (message) => {
          if (message.type() === 'error' && !/favicon/i.test(message.text())) {
            errors.push(`[console] ${message.text()}`)
          }
        })
        page.on('pageerror', (error) => errors.push(`[pageerror] ${error.message}`))
        page.on('request', (request) => requests.push(request.url()))

        try {
          await page.goto(`${origin}/#/`, { waitUntil: 'networkidle0' })
          const footerLink = await page.$('footer a[href="#/privacy"]')
          if (!footerLink) throw new Error('全局页脚没有 /privacy 入口')

          await footerLink.click()
          await page.waitForSelector(`[data-privacy-page="${app.id}"]`)
          await page.waitForFunction(() => location.hash === '#/privacy')

          const facts = await page.$eval('[data-privacy-page]', (node) => ({
            h1: node.querySelector('h1')?.textContent?.trim() ?? '',
            policySections: node.querySelectorAll('section').length,
            text: node.textContent ?? '',
            title: document.title,
          }))
          const externalRequests = requests.filter((requestUrl) => {
            const parsed = new URL(requestUrl)
            return ['http:', 'https:'].includes(parsed.protocol) && parsed.origin !== origin
          })

          if (!facts.h1.includes('隐私政策')) throw new Error(`标题异常: ${facts.h1}`)
          if (!facts.title.includes('隐私政策')) throw new Error(`document.title 异常: ${facts.title}`)
          if (facts.policySections < 6) throw new Error(`政策分节不足: ${facts.policySections}`)
          if (!facts.text.includes('1.0.0')) throw new Error('页面未显示统一版本 1.0.0')
          if (!facts.text.includes('不要求注册')) throw new Error('页面缺少零账号声明')
          if (externalRequests.length) {
            throw new Error(`隐私页出现外部请求: ${externalRequests.join(', ')}`)
          }
          if (errors.length) throw new Error(errors.join('; '))

          const screenshot = `browser-matrix-${app.id}-${profile.id}.png`
          await page.screenshot({
            path: join(evidenceDir, screenshot),
            fullPage: true,
          })
          results.push({
            app: app.name,
            appId: app.id,
            profile: profile.id,
            viewport: profile.viewport,
            route: '/privacy',
            title: facts.title,
            policySections: facts.policySections,
            externalRequests: 0,
            consoleErrors: 0,
            screenshot,
            status: 'PASS',
          })
        } catch (error) {
          results.push({
            app: app.name,
            appId: app.id,
            profile: profile.id,
            viewport: profile.viewport,
            route: '/privacy',
            status: 'FAIL',
            error: error instanceof Error ? error.message : String(error),
          })
        } finally {
          await page.close()
        }
      }
    } finally {
      await new Promise((accept, reject) =>
        server.close((error) => (error ? reject(error) : accept())),
      )
    }
  }
} finally {
  await browser.close()
}

const report = {
  criterion: 'SOTA C-6 browser matrix — Chrome actual run',
  generatedAt: new Date().toISOString(),
  chromePath,
  browserVersion,
  userAgent,
  results,
  passed: results.filter((row) => row.status === 'PASS').length,
  total: results.length,
}
await writeFile(
  join(evidenceDir, 'browser-matrix-chrome.json'),
  `${JSON.stringify(report, null, 2)}\n`,
)

for (const row of results) {
  console.log(`${row.status === 'PASS' ? '✓' : '✗'} ${row.app} ${row.profile} /privacy`)
  if (row.error) console.log(`  ${row.error}`)
}
console.log(`Chrome C-6: ${report.passed}/${report.total} profiles passed (${browserVersion})`)
process.exitCode = report.passed === report.total ? 0 : 1
