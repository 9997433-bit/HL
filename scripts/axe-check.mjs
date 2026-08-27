import { createServer } from 'node:http'
import { constants } from 'node:fs'
import { access, readFile, stat } from 'node:fs/promises'
import { extname, resolve, sep } from 'node:path'
import axeCore from 'axe-core'
import puppeteer from 'puppeteer-core'

const ROOT = resolve(import.meta.dirname, '..')
const WCAG_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']
const APPS = [
  {
    name: 'literacy-app',
    dist: resolve(ROOT, 'apps/literacy-app/dist'),
    routes: [
      ['首页地图', '/#/'],
      ['字表', '/#/learn'],
      ['单字详情', `/#/learn/${encodeURIComponent('日')}`],
      ['听音识字', '/#/listen'],
      ['偏旁部首', '/#/radicals'],
      ['偏旁详情', '/#/radicals/shui'],
      ['绘本书架', '/#/books'],
      ['绘本详情', '/#/books/b1'],
      ['成语列表', '/#/idioms'],
      ['成语详情', '/#/idioms/szdt'],
      ['家长中心', '/#/parent'],
    ],
  },
  {
    name: 'math-app',
    dist: resolve(ROOT, 'apps/math-app/dist'),
    routes: [
      ['学习地图', '/#/'],
      ['数量星云', '/#/number-sense'],
      ['算术恒星', '/#/arithmetic'],
      ['形状卫星', '/#/geometry'],
      ['规律环带', '/#/logic'],
      ['数独空间站', '/#/sudoku'],
      ['生活行星', '/#/word-problems'],
      ['成就墙', '/#/progress'],
      ['家长中心', '/#/parent', unlockParentGate],
    ],
  },
]

/**
 * 家长中心默认被一道口算题挡着，直接扫只能扫到门口那一屏。
 * 这里先把题算对进门，让报告正文也进入扫描范围。
 */
async function unlockParentGate(page) {
  const sum = await page.evaluate(() => {
    const label = document.querySelector('label[for="parent-gate"]')?.textContent ?? ''
    const match = label.match(/(\d+)\s*\+\s*(\d+)/)
    return match ? Number(match[1]) + Number(match[2]) : null
  })
  if (sum === null) throw new Error('家长中心没有找到口算门')
  await page.type('#parent-gate', String(sum))
  await page.click('.gate-form button[type="submit"]')
  await page.waitForFunction(() => !document.querySelector('#parent-gate'), { timeout: 5_000 })
}

const MIME = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.ico': 'image/x-icon',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.webp': 'image/webp',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
}

async function executable(path) {
  if (!path) return false
  try {
    await access(path, constants.X_OK)
    return true
  } catch {
    return false
  }
}

async function findChrome() {
  const candidates = [
    process.env.CHROME_PATH,
    '/usr/local/bin/google-chrome',
    '/usr/bin/google-chrome',
    '/usr/bin/google-chrome-stable',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
  ]
  for (const candidate of candidates) {
    if (await executable(candidate)) return candidate
  }
  throw new Error('未找到可执行的 Chrome/Chromium；可通过 CHROME_PATH 指定。')
}

async function assertDist(app) {
  const indexPath = resolve(app.dist, 'index.html')
  if (!(await stat(indexPath).catch(() => null))?.isFile()) {
    throw new Error(`${app.name} 缺少 ${indexPath}；请先构建双 App。`)
  }
}

function createStaticServer(dist) {
  return createServer(async (request, response) => {
    try {
      const pathname = decodeURIComponent(new URL(request.url, 'http://local/').pathname)
      const relative = pathname.replace(/^\/+/, '')
      let file = resolve(dist, relative || 'index.html')
      if (file !== dist && !file.startsWith(`${dist}${sep}`)) file = resolve(dist, 'index.html')
      if (!(await stat(file).catch(() => null))?.isFile()) file = resolve(dist, 'index.html')
      const body = await readFile(file)
      response.writeHead(200, {
        'cache-control': 'no-store',
        'content-type': MIME[extname(file)] ?? 'application/octet-stream',
      })
      response.end(body)
    } catch (error) {
      response.writeHead(500, { 'content-type': 'text/plain; charset=utf-8' })
      response.end(String(error))
    }
  })
}

async function listen(server) {
  await new Promise((resolveListen, rejectListen) => {
    server.once('error', rejectListen)
    server.listen(0, '127.0.0.1', resolveListen)
  })
  return `http://127.0.0.1:${server.address().port}`
}

async function closeServer(server) {
  await new Promise((resolveClose, rejectClose) => {
    server.close((error) => (error ? rejectClose(error) : resolveClose()))
    // Chrome may keep idle HTTP/1.1 sockets alive after the final route scan.
    // Stop accepting requests first, then close those sockets so the gate exits.
    server.closeAllConnections?.()
  })
}

async function scanPage(browser, app, base, route) {
  const [routeName, routePath, prepare] = route
  const page = await browser.newPage()
  await page.setViewport({ width: 420, height: 860, isMobile: true, hasTouch: true })

  try {
    const response = await page.goto(base + routePath, {
      waitUntil: 'networkidle2',
      timeout: 20_000,
    })
    if (!response?.ok()) {
      throw new Error(`HTTP ${response?.status() ?? 'unknown'}`)
    }
    await page.waitForFunction(
      () => {
        const root = document.querySelector('#app')
        return root && root.children.length > 0
      },
      { timeout: 8_000 },
    )
    await new Promise((resolveWait) => setTimeout(resolveWait, 200))
    // 有些页面要先走一步交互才能看到正文（例如家长中心的口算门）
    if (prepare) {
      await prepare(page)
      await new Promise((resolveWait) => setTimeout(resolveWait, 300))
    }
    await page.addScriptTag({ content: axeCore.source })

    const result = await page.evaluate(async (tags) => {
      const audit = await globalThis.axe.run(document, {
        resultTypes: ['violations'],
        runOnly: { type: 'tag', values: tags },
      })
      return audit.violations.map((violation) => ({
        help: violation.help,
        helpUrl: violation.helpUrl,
        id: violation.id,
        impact: violation.impact ?? 'unknown',
        nodes: violation.nodes.map((node) => ({
          failureSummary: node.failureSummary,
          html: node.html,
          impact: node.impact ?? violation.impact ?? 'unknown',
          target: node.target,
        })),
      }))
    }, WCAG_TAGS)

    return { app: app.name, routeName, routePath, violations: result }
  } finally {
    await page.close()
  }
}

function impactCount(scans, impact) {
  return scans.reduce(
    (total, scan) =>
      total +
      scan.violations.reduce(
        (routeTotal, violation) =>
          routeTotal + violation.nodes.filter((node) => node.impact === impact).length,
        0,
      ),
    0,
  )
}

function printDetails(scans) {
  for (const scan of scans) {
    const affected = scan.violations.filter((violation) =>
      violation.nodes.some((node) => ['critical', 'serious'].includes(node.impact)),
    )
    if (affected.length === 0) continue

    console.log(`\n[${scan.app}] ${scan.routeName} ${scan.routePath}`)
    for (const violation of affected) {
      const critical = violation.nodes.filter((node) => node.impact === 'critical').length
      const serious = violation.nodes.filter((node) => node.impact === 'serious').length
      console.log(
        `  - ${violation.id} (${violation.impact}): critical=${critical}, serious=${serious}`,
      )
      console.log(`    ${violation.help} — ${violation.helpUrl}`)
      for (const node of violation.nodes
        .filter((item) => ['critical', 'serious'].includes(item.impact))
        .slice(0, 3)) {
        console.log(`    ${node.impact}: ${node.target.join(' ')}`)
      }
    }
  }
}

let browser
const servers = []
const scans = []
const failures = []

try {
  for (const app of APPS) await assertDist(app)
  const chrome = await findChrome()
  browser = await puppeteer.launch({
    executablePath: chrome,
    headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage', '--mute-audio'],
  })

  for (const app of APPS) {
    const server = createStaticServer(app.dist)
    servers.push(server)
    const base = await listen(server)

    for (const route of app.routes) {
      try {
        const scan = await scanPage(browser, app, base, route)
        scans.push(scan)
        const critical = scan.violations
          .flatMap((violation) => violation.nodes)
          .filter((node) => node.impact === 'critical').length
        const serious = scan.violations
          .flatMap((violation) => violation.nodes)
          .filter((node) => node.impact === 'serious').length
        console.log(
          `${critical === 0 ? 'PASS' : 'FAIL'} ${app.name.padEnd(13)} ${route[0].padEnd(10)} ` +
            `critical=${critical}, serious=${serious}`,
        )
      } catch (error) {
        failures.push(`${app.name} ${route[0]}: ${error.message}`)
        console.error(`FAIL ${app.name} ${route[0]}: ${error.message}`)
      }
    }
    await closeServer(server)
    servers.pop()
  }

  printDetails(scans)

  const critical = impactCount(scans, 'critical')
  const serious = impactCount(scans, 'serious')
  console.log(
    `\naxe 汇总：${scans.length}/${APPS.reduce((sum, app) => sum + app.routes.length, 0)} ` +
      `页面完成，critical=${critical}, serious=${serious}。`,
  )
  if (serious > 0) {
    console.log('提示：serious 当前仅记录；本轮自动化硬门槛为 critical=0。')
  }
  if (failures.length > 0) {
    console.error(`扫描运行失败 ${failures.length} 项：`)
    for (const failure of failures) console.error(`  - ${failure}`)
  }
  process.exitCode = critical === 0 && failures.length === 0 ? 0 : 1
} catch (error) {
  console.error(`axe-check: ${error.stack ?? error.message}`)
  process.exitCode = 1
} finally {
  if (browser) await browser.close()
  for (const server of servers) await closeServer(server)
}
