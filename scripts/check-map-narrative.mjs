/**
 * Round 5B P4「地图叙事解锁」的运行时验收。
 *
 * check-round5b.mjs 对 P4 只做源码文本探针，而「未解锁灰显 + 一句话剧情 + 解锁过渡」
 * 是三件必须在浏览器里才看得出真假的事：灰调是算出来的 filter，剧情要真的渲染出来，
 * 过场则要在解锁那一刻恰好演一次、演完记账、刷新不重播。这里把两张地图都跑一遍。
 *
 * 用法（先 npm run build 生成两个 dist）：
 *   npm run check:map-narrative
 */
import { createServer } from 'node:http'
import { readFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { join, extname, normalize, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import puppeteer from 'puppeteer-core'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const CHROME = process.env.CHROME_PATH || '/usr/local/bin/google-chrome'
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2'
}

function serve(dist) {
  const server = createServer(async (req, res) => {
    const url = new URL(req.url, 'http://localhost')
    let file = join(dist, normalize(decodeURIComponent(url.pathname)))
    if (url.pathname === '/' || !existsSync(file)) file = join(dist, 'index.html')
    try {
      const body = await readFile(file)
      res.writeHead(200, { 'content-type': MIME[extname(file)] ?? 'application/octet-stream' })
      res.end(body)
    } catch {
      res.writeHead(404).end('not found')
    }
  })
  return new Promise((r) => server.listen(0, () => r({ server, port: server.address().port })))
}

/** 想看截图时传 SHOTS_DIR=/tmp，默认只判定不落盘。 */
const SHOTS = process.env.SHOTS_DIR || ''

const fails = []
function check(ok, msg) {
  console.log(`${ok ? '  ✓' : '  ✗'} ${msg}`)
  if (!ok) fails.push(msg)
}

const shoot = async (page, name) => {
  if (SHOTS) await page.screenshot({ path: join(SHOTS, name) })
}

for (const app of ['literacy-app', 'math-app']) {
  if (!existsSync(join(root, 'apps', app, 'dist', 'index.html'))) {
    console.error(`缺少 apps/${app}/dist，先跑 npm run build`)
    process.exit(1)
  }
}

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: 'new',
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--mute-audio']
})

/* ------------------------------------------------------------- 识字字表 */
{
  const { server, port } = await serve(join(root, 'apps/literacy-app/dist'))
  const base = `http://127.0.0.1:${port}`
  const page = await browser.newPage()
  await page.setViewport({ width: 900, height: 1000 })
  page.on('pageerror', (e) => fails.push(`literacy pageerror: ${e.message}`))

  console.log('\n[识字] 单元地图')
  await page.goto(`${base}/#/learn`, { waitUntil: 'networkidle2' })
  await new Promise((r) => setTimeout(r, 900))

  const initial = await page.evaluate(() => ({
    stops: document.querySelectorAll('.unitmap .stop').length,
    locked: document.querySelectorAll('.unitmap .stop.is-locked').length,
    story: document.querySelector('.unitmap__story')?.innerText.trim() ?? '',
    lockedGray: getComputedStyle(document.querySelector('.stop.is-locked')).filter,
    cheer: !!document.querySelector('.cheer')
  }))
  check(initial.stops === 58, `地图铺开 ${initial.stops} 站（应为 58）`)
  check(initial.locked === 57, `未解锁 ${initial.locked} 站（新存档只开第 1 站）`)
  check(/grayscale/.test(initial.lockedGray), `未解锁站点灰显：filter=${initial.lockedGray}`)
  check(initial.story.length > 8, `当前站剧情：「${initial.story}」`)
  check(!initial.cheer, '新存档不弹解锁过场（已解锁的都算看过）')

  // 点第 3 站：锁着也能翻过去看，页码要跟着走
  await page.evaluate(() => document.querySelector('[data-unit="u3"]').click())
  await new Promise((r) => setTimeout(r, 600))
  const jumped = await page.evaluate(() => ({
    at: document.querySelector('.pager__at')?.innerText.trim() ?? '',
    current: document.querySelector('.stop.is-current')?.dataset.unit ?? '',
    story: document.querySelector('.unitmap__story')?.innerText.trim() ?? ''
  }))
  check(jumped.current === 'u3', `点第 3 站后地图光标在 ${jumped.current}`)
  check(/第 3 \//.test(jumped.at), `翻页器同步到「${jumped.at}」`)
  check(jumped.story.includes('学完上一站'), `锁着的站讲预告：「${jumped.story.slice(0, 24)}…」`)

  // 造一份「第 1 单元学到 60%」的存档：u2 该解锁，且过场没演过
  await page.evaluate(() => {
    const key = 'happy-literacy:v1'
    const save = JSON.parse(localStorage.getItem(key) ?? '{}')
    save.chars = save.chars ?? {}
    for (const ch of ['一', '二', '三', '上', '下', '人', '口', '大']) {
      save.chars[ch] = { seen: 1, heard: 0, traced: 0, quizRight: 0, quizWrong: 0, level: 1, firstAt: Date.now(), lastAt: Date.now() }
    }
    save.seenUnits = ['u1']
    localStorage.setItem(key, JSON.stringify(save))
  })
  await page.reload({ waitUntil: 'networkidle2' })
  await new Promise((r) => setTimeout(r, 1800))

  const cheer = await page.evaluate(() => ({
    open: !!document.querySelector('.cheer'),
    line: document.querySelector('.cheer__line')?.innerText.trim() ?? '',
    live: document.querySelector('.cheer')?.getAttribute('aria-live') ?? '',
    current: document.querySelector('.stop.is-current')?.dataset.unit ?? '',
    u2locked: !!document.querySelector('[data-unit="u2"]')?.classList.contains('is-locked'),
    seen: JSON.parse(localStorage.getItem('happy-literacy:v1')).seenUnits
  }))
  check(cheer.open, '第 1 单元学到 60% 后弹出解锁过场')
  check(cheer.line.includes('大自然'), `过场台词：「${cheer.line}」`)
  check(cheer.live === 'polite', '过场是 aria-live 播报区')
  check(cheer.current === 'u2', `地图自动滚到新解锁的 ${cheer.current}`)
  check(!cheer.u2locked, '第 2 站已经不再灰显')
  check(!cheer.seen.includes('u2'), '按「进去看看」之前不记账，刷新还能再看一次')

  await shoot(page, 'map-narrative-literacy.png')

  await page.evaluate(() => [...document.querySelectorAll('button')].find((b) => b.innerText.includes('进去看看')).click())
  await new Promise((r) => setTimeout(r, 500))
  const closed = await page.evaluate(() => ({
    open: !!document.querySelector('.cheer'),
    seen: JSON.parse(localStorage.getItem('happy-literacy:v1')).seenUnits
  }))
  check(!closed.open, '点「进去看看」后过场收场')
  check(closed.seen.includes('u2'), `解锁记进存档：seenUnits=${closed.seen.join(',')}`)

  await page.reload({ waitUntil: 'networkidle2' })
  await new Promise((r) => setTimeout(r, 1600))
  check(
    !(await page.evaluate(() => !!document.querySelector('.cheer'))),
    '刷新后不再重播同一段过场'
  )

  await page.close()
  server.close()
}

/* ------------------------------------------------------------- 数学地图 */
{
  const { server, port } = await serve(join(root, 'apps/math-app/dist'))
  const base = `http://127.0.0.1:${port}`
  const page = await browser.newPage()
  await page.setViewport({ width: 1100, height: 1100 })
  page.on('pageerror', (e) => fails.push(`math pageerror: ${e.message}`))

  console.log('\n[数学] 星球地图')
  await page.goto(`${base}/#/`, { waitUntil: 'networkidle2' })
  await new Promise((r) => setTimeout(r, 1800))

  const initial = await page.evaluate(() => ({
    planets: document.querySelectorAll('.planet').length,
    locked: document.querySelectorAll('.planet.locked').length,
    gray: getComputedStyle(document.querySelector('.planet.locked .planet-body')).filter,
    stories: [...document.querySelectorAll('.mod-story')].map((n) => n.innerText.trim()),
    mapStory: document.querySelector('.map-story')?.innerText.trim() ?? '',
    scene: !!document.querySelector('.unlock-scene')
  }))
  check(initial.planets === 6, `地图上 ${initial.planets} 颗星球`)
  check(initial.locked === 5, `未解锁 ${initial.locked} 颗（新存档 0 星）`)
  check(/grayscale/.test(initial.gray), `未解锁星球灰显：filter=${initial.gray}`)
  check(initial.stories.length === 6 && initial.stories.every((s) => s.length > 8), '六张卡片各有一句话剧情')
  check(initial.mapStory.length > 8, `地图剧情条：「${initial.mapStory}」`)
  check(!initial.scene, '新存档不弹解锁过场')

  // 攒够 3 颗星：算术恒星该解锁，且过场没演过
  await page.evaluate(() => {
    const key = 'mathquest/progress'
    const save = JSON.parse(localStorage.getItem(key) ?? '{}')
    save.stars = 3
    save.seenPlanets = ['counting']
    localStorage.setItem(key, JSON.stringify(save))
  })
  await page.reload({ waitUntil: 'networkidle2' })
  await new Promise((r) => setTimeout(r, 2600))

  const scene = await page.evaluate(() => ({
    open: !!document.querySelector('.unlock-scene'),
    name: document.querySelector('.unlock-name')?.innerText.trim() ?? '',
    line: document.querySelector('.unlock-line')?.innerText.trim() ?? '',
    live: document.querySelector('.unlock-scene')?.getAttribute('aria-live') ?? '',
    highlighted: !!document.querySelector('.planet.is-unlocking'),
    seen: JSON.parse(localStorage.getItem('mathquest/progress')).seenPlanets
  }))
  check(scene.open, '攒够 3 颗星后弹出解锁过场')
  check(scene.name === '算术恒星', `过场主角：${scene.name}`)
  check(scene.line.length > 8, `过场台词：「${scene.line}」`)
  check(scene.live === 'polite', '过场是 aria-live 播报区')
  check(scene.highlighted, '地图上那颗球同步高亮')
  check(!scene.seen.includes('arithmetic'), '收场之前不记账')

  await shoot(page, 'map-narrative-math.png')

  await page.evaluate(() => [...document.querySelectorAll('button')].find((b) => b.innerText.includes('待会儿再去')).click())
  await new Promise((r) => setTimeout(r, 500))
  const closed = await page.evaluate(() => ({
    open: !!document.querySelector('.unlock-scene'),
    seen: JSON.parse(localStorage.getItem('mathquest/progress')).seenPlanets
  }))
  check(!closed.open, '点「待会儿再去」后过场收场')
  check(closed.seen.includes('arithmetic'), `解锁记进存档：seenPlanets=${closed.seen.join(',')}`)

  await page.reload({ waitUntil: 'networkidle2' })
  await new Promise((r) => setTimeout(r, 2600))
  check(
    !(await page.evaluate(() => !!document.querySelector('.unlock-scene'))),
    '刷新后不再重播同一段过场'
  )

  await page.close()
  server.close()
}

await browser.close()
console.log(`\n${fails.length ? `FAIL — ${fails.length} 项：\n  ${fails.join('\n  ')}` : 'PASS — 全部通过'}`)
process.exit(fails.length ? 1 : 0)
