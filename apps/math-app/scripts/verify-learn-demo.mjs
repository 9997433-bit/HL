/**
 * ROUND16_H4 / ROUND17_H3 学演示的定点验收。
 *
 * scripts/smoke.mjs 会把 19 条路由 + 全部玩法都跑一遍，几分钟起步；改学演示时
 * 想要的只是那三条断言。这个脚本只开一个浏览器、只走演示相关的路径，
 * 便于在改注册表或播放壳时快速回归。smoke 里的对应用例仍是权威门禁，
 * 这里的断言与那边保持同一套 data-* 钩子。
 *
 * 用法：npm run build && node scripts/verify-learn-demo.mjs
 */

import { createServer } from 'node:http'
import { readFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { extname, join, normalize } from 'node:path'
import { fileURLToPath } from 'node:url'
import puppeteer from 'puppeteer-core'
import { LEARN_DEMO_SKILLS } from '../src/data/learn-demo-index.js'

const ROOT = fileURLToPath(new URL('..', import.meta.url))
const DIST = join(ROOT, 'dist')
const CHROME = process.env.CHROME_PATH ?? '/usr/local/bin/google-chrome'

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2',
}

if (!existsSync(DIST)) {
  console.error('先跑 npm run build')
  process.exit(1)
}

const server = createServer(async (req, res) => {
  const url = new URL(req.url, 'http://localhost')
  let file = join(DIST, normalize(decodeURIComponent(url.pathname)))
  if (url.pathname === '/' || !existsSync(file)) file = join(DIST, 'index.html')
  try {
    res.writeHead(200, { 'content-type': MIME[extname(file)] ?? 'application/octet-stream' })
    res.end(await readFile(file))
  } catch {
    res.writeHead(404).end('not found')
  }
})

await new Promise((r) => server.listen(0, r))
const base = `http://127.0.0.1:${server.address().port}`

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: 'new',
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--mute-audio'],
})

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const results = []

async function check(label, path, fn) {
  const page = await browser.newPage()
  await page.setViewport({ width: 420, height: 900, isMobile: true, hasTouch: true })
  try {
    await page.goto(base + path, { waitUntil: 'networkidle2', timeout: 20000 })
    await sleep(600)
    results.push({ label, ok: true, note: await fn(page) })
  } catch (err) {
    results.push({ label, ok: false, note: err.message })
  }
  await page.close().catch(() => {})
}

/** 演示壳当前在屏幕上真正能读到的东西。 */
const readDemo = (page, scope = '') =>
  page.evaluate((sel) => {
    const root = document.querySelector(`${sel}[data-demo-id]`)
    if (!root) throw new Error('页面上找不到学演示')
    return {
      id: root.dataset.demoId,
      skill: root.dataset.demoSkill,
      stage: root.dataset.demoStage,
      motion: root.dataset.demoMotion,
      panels: [...root.querySelectorAll('.demo-panel')].map((el) =>
        Number(getComputedStyle(el).opacity),
      ),
      lines: [...root.querySelectorAll('[data-demo-narration] li, [data-demo-narration] p')]
        .map((el) => el.innerText.trim())
        .filter(Boolean),
      equation: root.querySelector('.equation-panel .equation')?.innerText.trim() ?? '',
      replay: !!root.querySelector('[data-demo-replay]'),
      skillName: root.querySelector('[data-demo-skill-name]')?.innerText.trim() ?? '',
    }
  }, scope)

await check(`演示中心：${LEARN_DEMO_SKILLS.length} 个技能点 + 跳过到算式`, '/#/visual-demos', async (page) => {
  await page.waitForSelector('[data-demo-id]')
  const tabs = await page.evaluate(() =>
    [...document.querySelectorAll('[data-demo-select-skill]')].map(
      (el) => el.dataset.demoSelectSkill,
    ),
  )
  if (tabs.length < 27) throw new Error(`只有 ${tabs.length} 个技能点，少于 27`)
  if (new Set(tabs).size !== tabs.length) throw new Error('有技能点挂了不止一条演示')
  const missing = LEARN_DEMO_SKILLS.filter((skill) => !tabs.includes(skill))
  if (missing.length) throw new Error(`清单里的技能点没上屏：${missing.join('、')}`)

  const before = await readDemo(page)
  if (before.motion !== 'play') throw new Error(`默认应是播放态，实际 ${before.motion}`)
  if (before.stage !== 'object') throw new Error(`首段应是实物，实际 ${before.stage}`)
  await page.click('[data-demo-skip]')
  await sleep(250)
  const after = await readDemo(page)
  if (after.stage !== 'equation') throw new Error(`跳过后没到算式段：${after.stage}`)
  if (!/=|½|^\d+$/.test(after.equation)) throw new Error(`算式段没有算式：${after.equation}`)
  return `${tabs.length} 个技能点，object → ${after.stage}（${after.equation}）`
})

await check('演示中心：换一条演示重新从实物段播', '/#/visual-demos', async (page) => {
  await page.waitForSelector('[data-demo-select="division"]')
  await page.click('[data-demo-select="division"]')
  await sleep(250)
  const picked = await readDemo(page)
  if (picked.id !== 'division') throw new Error(`选中的不是 division：${picked.id}`)
  if (picked.stage !== 'object') throw new Error(`换条演示应从实物段重播，实际 ${picked.stage}`)
  return `division / ${picked.skill} 从 ${picked.stage} 段重播`
})

// Round 17 补的这 6 条挂在原先没有演示的技能点上，逐条点开确认不是只进了清单
await check('演示中心：ROUND17_H3 新增的 6 条逐条点得开', '/#/visual-demos', async (page) => {
  await page.waitForSelector('[data-demo-id]')
  const added = ['shape-3d', 'classify', 'wp-diff', 'wp-times', 'wp-share', 'wp-two-step']
  const seen = []
  for (const skill of added) {
    const tab = `[data-demo-select-skill="${skill}"]`
    if (!(await page.$(tab))) throw new Error(`演示中心没有 ${skill} 的卡片`)
    await page.click(tab)
    await sleep(200)
    const demo = await readDemo(page)
    if (demo.skill !== skill) throw new Error(`点 ${skill} 打开的却是 ${demo.skill}`)
    if (demo.stage !== 'object') throw new Error(`${skill} 没有从实物段重播：${demo.stage}`)
    await page.click('[data-demo-skip]')
    await sleep(200)
    const done = await readDemo(page)
    if (done.stage !== 'equation' || !done.equation) {
      throw new Error(`${skill} 跳过后没落到算式段：${done.stage} / ${done.equation}`)
    }
    seen.push(`${skill} ${done.equation}`)
  }
  return seen.join('；')
})

await check('演示中心：?skill= 深链直接定位', '/#/visual-demos?skill=symmetry', async (page) => {
  await page.waitForSelector('[data-demo-id]')
  const demo = await readDemo(page)
  if (demo.skill !== 'symmetry') throw new Error(`深链没定位到 symmetry：${demo.skill}`)
  return `?skill=symmetry → ${demo.id}`
})

await check('reduced-motion：静态三态仍可读', '/#/visual-demos', async (page) => {
  await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }])
  await page.reload({ waitUntil: 'networkidle2' })
  await page.waitForSelector('[data-demo-motion="static"]')
  const still = await readDemo(page)
  if (still.stage !== 'equation') throw new Error(`静态态应停在算式段，实际 ${still.stage}`)
  if (still.panels.length !== 3) throw new Error(`静态态少了面板：${still.panels.length}/3`)
  if (still.panels.some((opacity) => opacity < 0.99)) {
    throw new Error(`静态态仍有面板压暗着：${still.panels.join('/')}`)
  }
  if (still.lines.length !== 3) throw new Error(`静态态只列出 ${still.lines.length} 句旁白`)
  if (!still.equation) throw new Error('静态态读不到算式')
  if (still.replay) throw new Error('静态态不该再给「重播」')
  return `三面板不透明度 ${still.panels.join('/')}，旁白 ${still.lines.length} 句全列，算式 ${still.equation}`
})

for (const [name, path] of [
  ['算术恒星', '/#/arithmetic'],
  ['生活行星', '/#/word-problems'],
  ['数量星云', '/#/number-sense'],
  ['形状卫星', '/#/geometry'],
  ['规律环带', '/#/logic'],
  ['配对记忆', '/#/memory-pairs'],
  ['10 的分与合', '/#/compose-ten'],
]) {
  await check(`${name}：练习入口就地弹出演示`, path, async (page) => {
    await page.waitForSelector('[data-learn-demo-open]', { timeout: 15000 })
    const skill = await page.evaluate(
      () => document.querySelector('[data-learn-demo-open]').dataset.learnDemoSkill,
    )
    if (!LEARN_DEMO_SKILLS.includes(skill)) throw new Error(`入口挂在没有演示的技能点上：${skill}`)

    await page.click('[data-learn-demo-open]')
    await page.waitForSelector('[data-learn-demo-layer] [data-demo-id]', { timeout: 8000 })
    const opened = await readDemo(page, '[data-learn-demo-layer] ')
    if (opened.skill !== skill) throw new Error(`弹出的技能点对不上：${opened.skill} ≠ ${skill}`)
    if (!opened.skillName) throw new Error('演示没标出正在讲哪个技能点')
    // 弹层只是盖上去，玩法页本身还在，收起来就能接着练
    if (!(await page.evaluate(() => !!document.querySelector('main.page')))) {
      throw new Error('看个演示把整个玩法页顶掉了')
    }

    await page.click('[data-demo-dismiss]')
    await sleep(250)
    if (await page.evaluate(() => !!document.querySelector('[data-learn-demo-layer]'))) {
      throw new Error('演示收不起来')
    }
    return `${skill}（${opened.skillName}）弹出并收起，练习壳还在`
  })
}

await check('技能图谱：只给有演示的技能点挂链接', '/#/skill-graph', async (page) => {
  const probe = async (skill) => {
    await page.evaluate((id) => {
      const node = document.querySelector(`[data-skill-node="${id}"]`)
      if (!node) throw new Error(`图谱上找不到节点 ${id}`)
      node.click()
    }, skill)
    await sleep(250)
    return page.evaluate(() => {
      const link = document.querySelector('[data-learn-demo-link]')
      return link ? link.dataset.learnDemoLink : null
    })
  }
  await page.waitForSelector('[data-skill-node]', { timeout: 15000 })
  const covered = await probe('mul-table')
  if (covered !== 'mul-table') throw new Error(`有演示的技能点没给链接：${covered}`)
  const uncovered = await probe('sudoku-4')
  if (uncovered !== null) throw new Error(`没演示的技能点摆了死链接：${uncovered}`)
  return 'mul-table 有「先看演示」，sudoku-4 没有'
})

await browser.close()
server.close()

const failed = results.filter((r) => !r.ok)
for (const r of results) console.log(` ${r.ok ? '✓' : '✗'} ${r.label} —— ${r.note}`)
console.log(
  `\nROUND16_H4 / ROUND17_H3 学演示定点验收：${results.length - failed.length}/${results.length} 通过。`,
)
process.exit(failed.length ? 1 : 0)
