/**
 * 识字 App 的「状态级」无障碍扫描。
 *
 * scripts/axe-check.mjs 扫的是每条路由刚打开、默认主题下的样子。真正出问题的
 * 地方恰恰不在那里：描红练习、答题反馈、庆祝浮层都要先操作几步才出现，而护眼
 * 与夜间主题换的是另一整套颜色。这个脚本把「三套主题 × 页面/交互态」全铺开，
 * critical 与 serious 都必须为 0。
 *
 * 用法：npm --prefix apps/literacy-app run build && node scripts/axe-states.mjs
 */

import { createServer } from 'node:http'
import { constants } from 'node:fs'
import { access, readFile, stat } from 'node:fs/promises'
import { extname, resolve, sep } from 'node:path'
import axeCore from 'axe-core'
import puppeteer from 'puppeteer-core'

const ROOT = resolve(import.meta.dirname, '..')
const DIST = resolve(ROOT, 'apps/literacy-app/dist')
const WCAG_TAGS = ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']
const THEMES = ['sunny', 'care', 'night']
/** 主题切换带 280ms 过渡，量颜色前要等它落定，否则量到的是过渡中的插值。 */
const THEME_SETTLE_MS = 700

const MIME = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2',
}

const wait = (ms) => new Promise((resolveWait) => setTimeout(resolveWait, ms))

async function clickText(page, text) {
  const clicked = await page.evaluate((needle) => {
    const el = [...document.querySelectorAll('button, a')].find((node) =>
      node.innerText.replace(/\s+/g, '').includes(needle),
    )
    if (!el) return false
    el.click()
    return true
  }, text)
  await wait(350)
  return clicked
}

/** 每个用例 = [名字, 路由, 可选的「走到那个状态」的步骤]。 */
const CASES = [
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
  [
    '描红练习中',
    `/#/learn/${encodeURIComponent('日')}`,
    async (page) => {
      await page.waitForSelector('.hz__host svg', { timeout: 8_000 })
      if (!(await clickText(page, '我来写'))) throw new Error('找不到「我来写」入口')
      await page.keyboard.press('Space')
      await wait(400)
    },
  ],
  [
    '答题反馈',
    '/#/listen',
    async (page) => {
      if (!(await clickText(page, '开始游戏'))) throw new Error('找不到「开始游戏」')
      await wait(500)
      await page.evaluate(() => document.querySelector('.opt')?.click())
      await wait(500)
    },
  ],
  [
    '庆祝浮层',
    '/#/books/b3',
    async (page) => {
      for (let i = 0; i < 8; i += 1) {
        if (await clickText(page, '下一页')) continue
        if (await clickText(page, '读完啦')) break
        break
      }
      await wait(500)
      if (!(await page.evaluate(() => !!document.querySelector('.cel')))) {
        throw new Error('读完整本没有弹出庆祝层')
      }
    },
  ],
]

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

function createStaticServer() {
  return createServer(async (request, response) => {
    try {
      const pathname = decodeURIComponent(new URL(request.url, 'http://local/').pathname)
      let file = resolve(DIST, pathname.replace(/^\/+/, '') || 'index.html')
      if (file !== DIST && !file.startsWith(`${DIST}${sep}`)) file = resolve(DIST, 'index.html')
      if (!(await stat(file).catch(() => null))?.isFile()) file = resolve(DIST, 'index.html')
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

if (!(await stat(resolve(DIST, 'index.html')).catch(() => null))?.isFile()) {
  console.error('axe-states: 缺少 apps/literacy-app/dist；请先构建识字 App。')
  process.exit(1)
}

const server = createStaticServer()
await new Promise((resolveListen) => server.listen(0, '127.0.0.1', resolveListen))
const base = `http://127.0.0.1:${server.address().port}`

const browser = await puppeteer.launch({
  executablePath: await findChrome(),
  headless: 'new',
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--mute-audio'],
})

let critical = 0
let serious = 0
let errors = 0

for (const theme of THEMES) {
  console.log(`\n---------- data-theme=${theme}`)
  for (const [name, route, step] of CASES) {
    const page = await browser.newPage()
    await page.setViewport({ width: 420, height: 860, isMobile: true, hasTouch: true })
    try {
      // 每个用例都从空存档开始：庆祝、解锁这类「只发生一次」的状态才可复现
      await page.goto(base + route, { waitUntil: 'networkidle2', timeout: 20_000 })
      await page.evaluate(() => localStorage.clear())
      await page.reload({ waitUntil: 'networkidle2', timeout: 20_000 })
      await page.waitForFunction(() => document.querySelector('#app')?.children.length > 0, {
        timeout: 8_000,
      })
      await wait(250)
      if (step) await step(page)
      await page.evaluate((value) => {
        document.documentElement.dataset.theme = value
      }, theme)
      await wait(THEME_SETTLE_MS)

      await page.addScriptTag({ content: axeCore.source })
      const violations = await page.evaluate(async (tags) => {
        const audit = await globalThis.axe.run(document, {
          resultTypes: ['violations'],
          runOnly: { type: 'tag', values: tags },
        })
        return audit.violations.map((violation) => ({
          id: violation.id,
          nodes: violation.nodes
            .map((node) => ({
              impact: node.impact ?? violation.impact,
              target: node.target,
              html: node.html,
              summary: node.failureSummary,
            }))
            .filter((node) => ['critical', 'serious'].includes(node.impact)),
        }))
      }, WCAG_TAGS)

      const bad = violations.filter((violation) => violation.nodes.length)
      const caseCritical = bad.reduce(
        (total, violation) =>
          total + violation.nodes.filter((node) => node.impact === 'critical').length,
        0,
      )
      const caseSerious = bad.reduce(
        (total, violation) =>
          total + violation.nodes.filter((node) => node.impact === 'serious').length,
        0,
      )
      critical += caseCritical
      serious += caseSerious

      console.log(
        `${caseCritical + caseSerious === 0 ? 'PASS' : 'FAIL'} ${name.padEnd(10)} ` +
          `critical=${caseCritical}, serious=${caseSerious}`,
      )
      for (const violation of bad) {
        for (const node of violation.nodes) {
          console.log(`    [${node.impact}] ${violation.id} @ ${node.target.join(' ')}`)
          console.log(`      ${node.html.slice(0, 140)}`)
          console.log(`      ${(node.summary ?? '').replace(/\s*\n\s*/g, ' | ')}`)
        }
      }
    } catch (error) {
      errors += 1
      console.error(`ERROR ${name}（${theme}）：${error.message}`)
    }
    await page.close()
  }
}

await browser.close()
await new Promise((resolveClose) => server.close(resolveClose))

console.log(
  `\naxe 状态扫描：${THEMES.length} 套主题 × ${CASES.length} 个状态，` +
    `critical=${critical}, serious=${serious}, 运行失败=${errors}。`,
)
process.exit(critical + serious + errors === 0 ? 0 : 1)
