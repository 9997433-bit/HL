/**
 * 冒烟测试：用无头 Chrome 把 dist 里的每条路由都走一遍，
 * 收集控制台报错、未捕获异常和 Vue 警告，并把每个玩法真的玩几题。
 *
 * 用法：npm run build && node scripts/smoke.mjs
 */

import { createServer } from 'node:http'
import { mkdtemp, readFile, writeFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { extname, join, normalize } from 'node:path'
import { fileURLToPath } from 'node:url'
import puppeteer from 'puppeteer-core'
// 技能图谱的断言对着课程表算期望值，别在这儿抄一份会过期的数字
import { SKILLS } from '../src/data/curriculum.js'

const ROOT = fileURLToPath(new URL('..', import.meta.url))
const DIST = join(ROOT, 'dist')
const CHROME = process.env.CHROME_PATH ?? '/usr/local/bin/google-chrome'
const ANDROID_SIM_UA = process.env.ANDROID_SIM_UA?.trim() ?? ''

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
    const body = await readFile(file)
    res.writeHead(200, { 'content-type': MIME[extname(file)] ?? 'application/octet-stream' })
    res.end(body)
  } catch {
    res.writeHead(404).end('not found')
  }
})

await new Promise((r) => server.listen(0, r))
const base = `http://127.0.0.1:${server.address().port}`

const ROUTES = [
  ['学习地图', '/#/'],
  ['今日冒险', '/#/daily'],
  ['数量星云', '/#/number-sense'],
  ['比大小擂台', '/#/compare'],
  ['10 的分与合', '/#/compose-ten'],
  ['算术恒星', '/#/arithmetic'],
  ['竖式工坊', '/#/column-arithmetic'],
  ['形状卫星', '/#/geometry'],
  ['七巧板实验室', '/#/tangram'],
  ['数形演示中心', '/#/visual-demos'],
  ['规律环带', '/#/logic'],
  ['配对记忆', '/#/memory-pairs'],
  ['逻辑迷宫', '/#/maze'],
  ['数独空间站', '/#/sudoku'],
  ['生活行星', '/#/word-problems'],
  ['技能图谱', '/#/skill-graph'],
  ['成就墙', '/#/progress'],
  ['家长中心', '/#/parent'],
  ['隐私政策', '/#/privacy'],
  ['未知路由回落', '/#/nope/nope'],
]

const ROUND9_H3_SMOKE = '/skill-graph'
const ROUND10_H3_SMOKE = '/skill-graph'
const ROUND11_H3_SMOKE = '/skill-graph'
const ROUND12_H5_SMOKE = '/skill-graph'
const ROUND13_H5_SMOKE = '/parent'

const IGNORE = [/Failed to load resource/i, /net::ERR_/i, /favicon/i, /AudioContext/i]

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: 'new',
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--mute-audio'],
})

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const problems = []
const rows = []
let observedUserAgent = ''

async function newPage(collect) {
  const page = await browser.newPage()
  if (ANDROID_SIM_UA) await page.setUserAgent(ANDROID_SIM_UA)
  await page.setViewport({ width: 420, height: 900, isMobile: true, hasTouch: true })
  page.on('console', (m) => {
    if (!['error', 'warning'].includes(m.type())) return
    const text = m.text()
    if (IGNORE.some((re) => re.test(text))) return
    collect.push(`[${m.type()}] ${text}`)
  })
  page.on('pageerror', (e) => collect.push(`[pageerror] ${e.message}`))
  return page
}

/* ------------------------------------------------------------ 路由渲染 */
for (const [name, path] of ROUTES) {
  const found = []
  const page = await newPage(found)
  try {
    await page.goto(base + path, { waitUntil: 'networkidle2', timeout: 20000 })
    await page
      .waitForFunction(() => (document.querySelector('#app')?.innerText ?? '').length > 40, {
        timeout: 8000,
      })
      .catch(() => {})
    await sleep(500)

    const info = await page.evaluate(() => {
      const app = document.querySelector('#app')
      const txt = app?.innerText ?? ''
      return {
        mounted: !!app && app.children.length > 0,
        chars: txt.replace(/\s+/g, '').length,
        broken: /NaN|undefined|\[object Object\]/.test(txt),
        title: document.title,
        userAgent: navigator.userAgent,
      }
    })

    if (!observedUserAgent) observedUserAgent = info.userAgent
    if (ANDROID_SIM_UA && info.userAgent !== ANDROID_SIM_UA) {
      found.push(`[user-agent] 期望 ${ANDROID_SIM_UA}，实际 ${info.userAgent}`)
    }
    if (!info.mounted) found.push('[render] #app 为空，组件没挂载')
    if (info.broken) found.push('[render] 页面里出现 NaN / undefined / [object Object]')
    if (info.chars < 20) found.push(`[render] 页面内容过少（${info.chars} 字）`)

    rows.push({ name, path, chars: info.chars, issues: found.length })
  } catch (err) {
    found.push(`[navigate] ${err.message}`)
    rows.push({ name, path, chars: 0, issues: found.length })
  }
  if (found.length) problems.push({ name, path, found: [...new Set(found)] })
  await page.close()
}

/* -------------------------------------------------------------- 交互 */
const inter = []

async function interact(label, path, fn) {
  const errs = []
  const page = await newPage(errs)
  try {
    await page.goto(base + path, { waitUntil: 'networkidle2', timeout: 20000 })
    await sleep(700)
    const note = await fn(page)
    inter.push({ label, ok: errs.length === 0, note, errs })
  } catch (err) {
    inter.push({ label, ok: false, note: err.message, errs })
  }
  await page.close()
}

const starCount = (page) =>
  page.evaluate(() => {
    const el = document.querySelector('[data-star-counter]')
    return Number((el?.innerText ?? '0').replace(/\D/g, '')) || 0
  })

const CHOICE_SELECTOR = '.opt, .opt-card, .opt-btn, .rock, .shape-cell, .tile'

/** 等到出现可点击的选项为止（答题反馈期间选项是禁用的）。 */
async function waitForChoice(page, timeout = 12000) {
  const deadline = Date.now() + timeout
  while (Date.now() < deadline) {
    const ready = await page.evaluate(
      (sel) => [...document.querySelectorAll(sel)].some((b) => !b.disabled),
      CHOICE_SELECTOR,
    )
    if (ready) return true
    await sleep(250)
  }
  return false
}

/** 点一个选项 → 等反馈 → 如果出现「提交 / 下一题」之类推进按钮就点掉。 */
async function answerOnce(page) {
  if (!(await waitForChoice(page))) return false
  const clicked = await page.evaluate((sel) => {
    const opts = [...document.querySelectorAll(sel)].filter((b) => !b.disabled)
    if (!opts.length) return false
    opts[Math.floor(Math.random() * opts.length)].click()
    return true
  }, CHOICE_SELECTOR)
  if (!clicked) return false
  await sleep(350)
  await page.evaluate(() => {
    const el = [...document.querySelectorAll('button')].find(
      (b) => /提交|确认|检查|下一题|继续|发射/.test(b.innerText) && !b.disabled,
    )
    if (el) el.click()
  })
  await sleep(900)
  return true
}

/**
 * 数量星云的装货题：用真实鼠标事件按提示数量点货物，再点发射。
 * 这里不能用 element.click()，货物按钮走的是 pointer 事件，
 * 合成 click 不会触发装货逻辑，测出来的结果没有意义。
 */
async function loadCargo(page) {
  const need = await page.evaluate(() => {
    // 只认真正有货物池的装货题：应用题里也会出现「把 N 个…」的句子
    if (!document.querySelector('.pool .cargo')) return 0
    const m = document.body.innerText.match(/把\s*(\d+)\s*个/)
    return m ? Number(m[1]) : 0
  })
  if (!need) return false
  for (let i = 0; i < need; i++) {
    const box = await page.evaluate(() => {
      const it = [...document.querySelectorAll('.pool .cargo')].filter((b) => !b.disabled)[0]
      if (!it) return null
      const r = it.getBoundingClientRect()
      return { x: r.x + r.width / 2, y: r.y + r.height / 2 }
    })
    if (!box) break
    await page.mouse.click(box.x, box.y)
    await sleep(70)
  }
  await page.evaluate(() => {
    const go = [...document.querySelectorAll('button')].find((b) => /发射/.test(b.innerText))
    if (go) go.click()
  })
  return true
}

async function playChoiceModule(page, rounds) {
  const before = await starCount(page)
  let answered = 0
  for (let i = 0; i < rounds; i++) {
    if (await loadCargo(page)) {
      answered++
      await sleep(1400)
      continue
    }
    if (await answerOnce(page)) answered++
    else {
      // 轮次结束时会弹出总结卡，点「再来一轮」继续
      const again = await page.evaluate(() => {
        const el = [...document.querySelectorAll('button')].find((b) => /再来一轮|再来一局|下一轮/.test(b.innerText))
        if (!el) return false
        el.click()
        return true
      })
      await sleep(700)
      if (!again) break
    }
  }
  const after = await starCount(page)
  return { answered, before, after }
}

await interact('数形演示：8 类 + 跳过到算式', '/#/visual-demos', async (page) => {
  await page.waitForSelector('[data-demo-id]')
  const before = await page.evaluate(() => ({
    count: document.querySelectorAll('[data-demo-select]').length,
    stage: document.querySelector('[data-demo-id]')?.dataset.demoStage ?? '',
  }))
  if (before.count < 7) throw new Error(`数形演示只有 ${before.count} 类`)
  if (before.stage !== 'object') throw new Error(`演示首段应是实物，实际 ${before.stage}`)
  await page.click('[data-demo-skip]')
  await sleep(250)
  const after = await page.evaluate(() => ({
    stage: document.querySelector('[data-demo-id]')?.dataset.demoStage ?? '',
    text: document.querySelector('.equation-panel .equation')?.innerText.trim() ?? '',
  }))
  if (after.stage !== 'equation') throw new Error(`跳过后没有到算式段：${after.stage}`)
  if (!/=|½|^\d+$/.test(after.text)) throw new Error(`算式段没有算式：${after.text}`)
  return `${before.count} 类，${before.stage} → ${after.stage}`
})

await interact('七巧板：Canvas + 7 块选择与旋转', '/#/tangram', async (page) => {
  await page.waitForSelector('canvas[data-piece-count="7"]')
  const before = await page.evaluate(() => ({
    canvas: !!document.querySelector('.tangram-canvas'),
    pieces: document.querySelectorAll('[data-piece-select]').length,
    solved: document.querySelector('[data-tangram-solved]')?.innerText.trim() ?? '',
  }))
  if (!before.canvas || before.pieces !== 7) {
    throw new Error(`七巧板应有 Canvas / 7 块，实际 canvas=${before.canvas} pieces=${before.pieces}`)
  }
  await page.click('[data-piece-select="large-a"]')
  await page.click('[data-tangram-rotate]')
  await sleep(200)
  const selected = await page.evaluate(
    () => document.querySelector('[data-piece-select="large-a"]')?.getAttribute('aria-pressed'),
  )
  if (selected !== 'true') throw new Error('点选拼板后没有进入选中态')
  return `Canvas 就绪，拼板 ${before.pieces} 块，初始归位 ${before.solved}`
})

await interact('配对记忆：Canvas 牌桌 + 配错回盖 + 整副配完', '/#/memory-pairs', async (page) => {
  await page.waitForSelector('canvas[data-memory-cards]')
  const deck = await page.evaluate(() => ({
    cards: Number(document.querySelector('canvas[data-memory-cards]')?.dataset.memoryCards ?? 0),
    hits: document.querySelectorAll('[data-card-index]').length,
    pairs: [...document.querySelectorAll('[data-card-index]')].map((b) => b.dataset.cardPair),
    labelled: [...document.querySelectorAll('[data-card-index]')].every((b) =>
      (b.getAttribute('aria-label') ?? '').length > 4,
    ),
  }))
  if (!deck.cards || deck.hits !== deck.cards) {
    throw new Error(`牌桌 ${deck.cards} 张卡，命中层只有 ${deck.hits} 个按钮`)
  }
  if (!deck.labelled) throw new Error('有卡片按钮没有无障碍名称')

  const groups = new Map()
  deck.pairs.forEach((pairId, index) => {
    if (!groups.has(pairId)) groups.set(pairId, [])
    groups.get(pairId).push(index)
  })
  const couples = [...groups.values()]
  if (couples.length !== deck.cards / 2) throw new Error(`卡片没有两两成对：${couples.length} 组`)

  const clickCard = (index) =>
    page.evaluate((i) => document.querySelector(`[data-card-index="${i}"]`).click(), index)
  const stateOf = (index) =>
    page.evaluate(
      (i) => document.querySelector(`[data-card-index="${i}"]`).dataset.cardState,
      index,
    )

  // 先故意配错一对：两张牌必须自己盖回去，且这期间不能再翻牌
  await clickCard(couples[0][0])
  await clickCard(couples[1][0])
  await sleep(250)
  const midFlip = await stateOf(couples[0][0])
  if (midFlip === 'down') throw new Error('翻开的卡片没有进入翻开态')
  await sleep(1400)
  const afterMiss = await Promise.all([stateOf(couples[0][0]), stateOf(couples[1][0])])
  if (afterMiss.some((s) => s !== 'down')) throw new Error(`配错后没有盖回去：${afterMiss}`)

  for (const [a, b] of couples) {
    await clickCard(a)
    await clickCard(b)
    await sleep(160)
  }
  await sleep(600)

  const result = await page.evaluate(() => {
    const store = JSON.parse(localStorage.getItem('mathquest/progress') || '{}')
    return {
      matched: document.querySelector('[data-memory-matched]')?.innerText.trim() ?? '',
      summary: document.body.innerText.includes('配对记忆完成'),
      answered: store.modules?.['memory-pairs']?.answered ?? 0,
      classify: store.mastery?.classify ?? 0,
    }
  })
  if (!result.summary) throw new Error(`全部配完后没有出现总结卡：${result.matched}`)
  if (result.answered < couples.length) {
    throw new Error(`只记了 ${result.answered} 次作答，应至少 ${couples.length} 次`)
  }
  if (!(result.classify > 0)) throw new Error('配对记忆没有写入 classify 掌握度')
  return `${deck.cards} 张卡 / ${couples.length} 对，配错自动回盖，${result.matched}，classify=${result.classify.toFixed(2)}`
})

await interact('逻辑迷宫：撞墙拦截 + 顺序收集 + 跟着提示通关', '/#/maze', async (page) => {
  await page.waitForSelector('canvas[data-maze-size]')
  const DIR = { 上: 'up', 下: 'down', 左: 'left', 右: 'right' }
  const read = () =>
    page.evaluate(() => ({
      size: document.querySelector('[data-maze-size]')?.dataset.mazeSize ?? '',
      pos: document.querySelector('[data-maze-pos]')?.dataset.mazePos ?? '',
      collected: document.querySelector('[data-maze-collected]')?.innerText.trim() ?? '',
      status: document.querySelector('[data-maze-status]')?.innerText.trim() ?? '',
      next: !!document.querySelector('[data-maze-next]'),
    }))
  const press = (dir) =>
    page.evaluate((d) => document.querySelector(`[data-maze-move="${d}"]`).click(), dir)

  const start = await read()
  const [cols, rows] = start.size.split('x').map(Number)
  if (!(cols >= 5 && rows >= 5)) throw new Error(`迷宫尺寸不对：${start.size}`)
  if (start.pos !== `0,${rows - 1}`) throw new Error(`飞船没有停在左下角发射台：${start.pos}`)

  // 左下角至少有两面外墙，往左/往下一定撞墙且位置不能变
  await press('left')
  await sleep(200)
  const bumped = await read()
  if (bumped.pos !== start.pos) throw new Error(`撞墙后飞船还是动了：${start.pos} → ${bumped.pos}`)
  if (!/墙/.test(bumped.status)) throw new Error(`撞墙没有给出提示：${bumped.status}`)

  // 跟着提示一路开到空间站：提示文案里写着下一步该往哪走
  let moved = 0
  let guard = 0
  let state = bumped
  while (!state.next && guard++ < 400) {
    await page.evaluate(() => document.querySelector('[data-maze-hint]').click())
    await sleep(60)
    const status = await page.evaluate(
      () => document.querySelector('[data-maze-status]')?.innerText ?? '',
    )
    const dir = DIR[status.match(/先往(.)走/)?.[1]]
    if (!dir) throw new Error(`提示没给出方向：${status}`)
    await press(dir)
    moved++
    await sleep(60)
    state = await read()
  }
  if (!state.next) throw new Error(`走了 ${moved} 步仍没通关：${state.status}`)
  if (!/通关/.test(state.status)) throw new Error(`通关文案不对：${state.status}`)

  const store = await page.evaluate(() => {
    const s = JSON.parse(localStorage.getItem('mathquest/progress') || '{}')
    return { answered: s.modules?.maze?.answered ?? 0, mastery: s.mastery?.['maze-condition'] ?? 0 }
  })
  if (!(store.mastery > 0)) throw new Error('通关后没有写入 maze-condition 掌握度')

  await page.evaluate(() => document.querySelector('[data-maze-next]').click())
  await sleep(500)
  const stage2 = await read()
  if (stage2.next) throw new Error('点了下一关但还停在通关面板上')
  if (stage2.pos !== `0,${rows - 1}`) throw new Error(`第二关没有回到发射台：${stage2.pos}`)
  return `${start.size} 迷宫，撞墙被拦下，${moved} 步通关（${state.collected}），maze-condition=${store.mastery.toFixed(2)}`
})

/**
 * 两个 Canvas 小游戏的动效降级：靠「点完立刻截一张画布 + 等它稳定后再截一张」
 * 来判断中间有没有补间。正常档两张必须不一样（说明是逐帧动出来的），
 * reduced-motion 档两张必须一模一样（说明一步到位、一帧都没动）。
 */
const canvasShot = (page, selector) =>
  page.evaluate((sel) => document.querySelector(sel).toDataURL(), selector)

const useReducedMotion = async (page) => {
  await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }])
  await page.reload({ waitUntil: 'networkidle2' })
  await sleep(700)
}

await interact('配对记忆：reduced-motion 下翻牌一步到位', '/#/memory-pairs', async (page) => {
  const flip = async () => {
    await page.waitForSelector('[data-card-index="0"]')
    await page.evaluate(() => document.querySelector('[data-card-index="0"]').click())
    const immediate = await canvasShot(page, '.board-canvas')
    await sleep(500)
    return { immediate, settled: await canvasShot(page, '.board-canvas') }
  }

  const animated = await flip()
  if (animated.immediate === animated.settled) throw new Error('动效开着却看不到翻牌补间')

  await useReducedMotion(page)
  const reduced = await flip()
  if (reduced.immediate !== reduced.settled) throw new Error('reduced-motion 下翻牌仍在跑补间')
  return '正常档逐帧翻牌，reduced-motion 档一帧落位'
})

await interact('逻辑迷宫：reduced-motion 下飞船一步到位', '/#/maze', async (page) => {
  const posOf = () =>
    page.evaluate(() => document.querySelector('[data-maze-pos]').dataset.mazePos)

  /** 挨个方向试，直到真的走动一格，再比较两张画布。 */
  const walk = async () => {
    await page.waitForSelector('[data-maze-move="up"]')
    for (const dir of ['up', 'right', 'down', 'left']) {
      const before = await posOf()
      await page.evaluate((d) => document.querySelector(`[data-maze-move="${d}"]`).click(), dir)
      const immediate = await canvasShot(page, '.maze-canvas')
      await sleep(500)
      if ((await posOf()) === before) continue
      return { immediate, settled: await canvasShot(page, '.maze-canvas') }
    }
    throw new Error('四个方向都走不动，迷宫把飞船封死了')
  }

  const animated = await walk()
  if (animated.immediate === animated.settled) throw new Error('动效开着却看不到飞船补间')

  await useReducedMotion(page)
  const reduced = await walk()
  if (reduced.immediate !== reduced.settled) throw new Error('reduced-motion 下飞船仍在跑补间')
  return '正常档飞船滑行，reduced-motion 档直接落格'
})

await interact('分与合：移动弹珠并写入 compose-ten', '/#/compose-ten', async (page) => {
  await page.waitForSelector('[data-compose-check]')
  for (let guard = 0; guard < 10; guard++) {
    const state = await page.evaluate(() => ({
      known: Number(document.querySelector('[data-known]')?.dataset.known),
      left: Number(document.querySelector('[data-compose-left]')?.innerText),
    }))
    if (state.left === state.known) break
    const selector = state.left < state.known ? '[data-bead-side="right"]' : '[data-bead-side="left"]'
    await page.click(selector)
    await sleep(80)
  }
  await page.click('[data-compose-check]')
  await sleep(350)
  const result = await page.evaluate(() => {
    const state = JSON.parse(localStorage.getItem('mathquest/progress') || '{}')
    return {
      mastery: state.mastery?.['compose-ten'],
      next: !!document.querySelector('[data-compose-next]'),
      equation: document.querySelector('.equation')?.innerText.replace(/\s+/g, ' ').trim(),
    }
  })
  if (!result.next) throw new Error('正确分好 10 后没有进入完成态')
  if (!(result.mastery > 0)) throw new Error('compose-ten 掌握度没有写入进度')
  return `${result.equation}，compose-ten=${result.mastery}`
})

await interact('竖式：进位错因 + 两步完成', '/#/column-arithmetic', async (page) => {
  await page.waitForSelector('[data-column-step-option]')
  await page.evaluate(() => {
    const wrong = [...document.querySelectorAll('[data-column-step-option]')].find(
      (button) => button.dataset.correct !== 'true',
    )
    wrong?.click()
  })
  await sleep(250)
  const errorCount = await page.evaluate(() => {
    const state = JSON.parse(localStorage.getItem('mathquest/progress') || '{}')
    return state.errorTagCounts?.carry ?? 0
  })
  if (errorCount < 1) throw new Error('故意漏进位后没有记录 carry 错因')
  await page.click('[data-column-step-option][data-correct="true"]')
  await sleep(180)
  await page.click('[data-column-answer-option][data-correct="true"]')
  await sleep(300)
  const done = await page.evaluate(() => ({
    next: !!document.querySelector('[data-column-next]'),
    text: document.querySelector('.message')?.innerText ?? '',
  }))
  if (!done.next || !/算对/.test(done.text)) throw new Error(`竖式没有完成：${done.text}`)
  return `carry 错因 ${errorCount} 次；两步完成`
})

for (const [label, path] of [
  ['数量星云', '/#/number-sense'],
  ['算术恒星', '/#/arithmetic'],
  ['形状卫星', '/#/geometry'],
  ['规律环带', '/#/logic'],
  ['生活行星', '/#/word-problems'],
]) {
  await interact(`${label}：连答 6 题`, path, async (page) => {
    const r = await playChoiceModule(page, 6)
    if (r.answered === 0) throw new Error('没有找到可点击的选项')
    return `作答 ${r.answered} 次，星星 ${r.before} → ${r.after}`
  })
}

await interact('学习地图：今日冒险入口 + 推荐星球呼吸高亮', '/#/', async (page) => {
  const info = await page.evaluate(() => {
    const cta = document.querySelector('[data-daily-cta]')
    const planet = document.querySelector('.planet.is-next')
    const body = planet?.querySelector('.planet-body')
    return {
      cta: cta?.innerText.trim() ?? '',
      card: !!document.querySelector('.mod-card.is-next'),
      pips: document.querySelectorAll('.daily-pip').length,
      animation: body ? getComputedStyle(body).animationName : '',
    }
  })
  if (!info.cta) throw new Error('首页 hero 里没有今日冒险入口')
  if (!/今日冒险/.test(info.cta)) throw new Error(`今日冒险 CTA 文案不对：${info.cta}`)
  // 做完当天 5 题后进度点会收起，只有未完成时才该出现
  if (!/已完成/.test(info.cta) && info.pips !== 5) {
    throw new Error(`今日冒险进度点应有 5 个，实际 ${info.pips}`)
  }
  if (!info.card) throw new Error('模块卡片里没有标出推荐下一站')
  if (!/breathe/.test(info.animation)) {
    throw new Error(`推荐星球缺少呼吸高亮动画，animation-name=${info.animation || '(无)'}`)
  }

  await page.evaluate(() => document.querySelector('[data-daily-cta]').click())
  await sleep(600)
  const landed = await page.evaluate(() => location.hash)
  if (landed !== '#/daily') throw new Error(`点击今日冒险跳到了 ${landed}`)
  return `CTA「${info.cta}」，进度点 ${info.pips} 个，呼吸动画 ${info.animation}`
})

await interact('今日冒险：5 题 · 刷新不换题 · 完成打卡', '/#/daily', async (page) => {
  const readPrompt = () =>
    page.evaluate(() => document.querySelector('.quiz-prompt')?.innerText.replace(/\s+/g, ' ').trim() ?? '')

  const before = await readPrompt()
  if (!before) throw new Error('今日冒险没有渲染题目')

  // 同一天的题只由日期决定，刷新（重新生成）必须还是同一道
  await page.reload({ waitUntil: 'networkidle2' })
  await sleep(700)
  const after = await readPrompt()
  if (before !== after) throw new Error(`刷新后换题了：「${before}」→「${after}」`)

  const total = await page.evaluate(() => {
    const m = document.body.innerText.match(/今日\s*(\d+)\s*\/\s*(\d+)/)
    return m ? Number(m[2]) : 0
  })
  if (total !== 5) throw new Error(`今日冒险应是 5 题，页面显示 ${total}`)

  let answered = 0
  for (let i = 0; i < 6; i++) {
    if (!(await answerOnce(page))) break
    answered++
  }
  await sleep(1200)

  const quest = await page.evaluate(
    () => JSON.parse(localStorage.getItem('mathquest/progress') || '{}').dailyQuest ?? {},
  )
  if (answered < 5) throw new Error(`只答了 ${answered} 题就没有可点的选项了`)
  if (!quest.completedAt) throw new Error(`答完 5 题却没有打卡：${JSON.stringify(quest)}`)
  if (quest.done !== 5) throw new Error(`打卡记录里的题数是 ${quest.done}，应为 5`)
  if (quest.streak < 1) throw new Error('完成今日冒险后连续天数仍为 0')

  await page.goto(base + '/#/', { waitUntil: 'networkidle2' })
  await sleep(500)
  const cta = await page.evaluate(
    () => document.querySelector('[data-daily-cta]')?.innerText.trim() ?? '',
  )
  if (!/已完成/.test(cta)) throw new Error(`打卡后首页 CTA 没有变成已完成：${cta}`)
  return `刷新不换题「${before}」，答 ${answered} 题后打卡 done=${quest.done} 连续 ${quest.streak} 天`
})

await interact('小算陪跑：首页与今日冒险常驻，点一下换鼓励语并朗读', '/#/', async (page) => {
  /** 无头环境没有中文嗓音，把 speak 换成记录，验的是「点了会说话」这条线。 */
  const patchSpeech = () =>
    page.evaluate(() => {
      window.__spoken = []
      const synth = window.speechSynthesis
      if (synth) synth.speak = (utter) => window.__spoken.push(utter.text)
    })

  await page.waitForSelector('.hero-bot button.mascot', { timeout: 8000 })
  await patchSpeech()
  const homeBefore = await page.evaluate(() => {
    const btn = document.querySelector('.hero-bot button.mascot')
    const box = btn.getBoundingClientRect()
    return {
      label: btn.getAttribute('aria-label') ?? '',
      line: document.querySelector('.hero-bot .bot-say')?.innerText.trim() ?? '',
      tap: Math.round(Math.min(box.width, box.height)),
    }
  })
  if (!homeBefore.label) throw new Error('首页小算按钮没有无障碍名称')
  if (homeBefore.tap < 44) throw new Error(`首页小算命中区只有 ${homeBefore.tap}px`)
  if (!homeBefore.line) throw new Error('首页小算没有鼓励语')

  await page.evaluate(() => document.querySelector('.hero-bot button.mascot').click())
  await sleep(350)
  const homeAfter = await page.evaluate(() => ({
    line: document.querySelector('.hero-bot .bot-say').innerText.trim(),
    spoken: window.__spoken ?? [],
  }))
  if (homeAfter.line === homeBefore.line) throw new Error('点了首页小算但鼓励语没换')
  if (!homeAfter.spoken.includes(homeAfter.line)) {
    throw new Error(`首页气泡换成「${homeAfter.line}」却没有把它读出来`)
  }

  await page.goto(base + '/#/daily', { waitUntil: 'networkidle2' })
  await page.waitForSelector('.stage-head button.mascot', { timeout: 8000 })
  await sleep(500)
  await patchSpeech()
  const dailyBefore = await page.evaluate(
    () => document.querySelector('.stage-head .say')?.innerText.trim() ?? '',
  )
  await page.evaluate(() => document.querySelector('.stage-head button.mascot').click())
  await sleep(350)
  const dailyAfter = await page.evaluate(() => ({
    say: document.querySelector('.stage-head .say').innerText.trim(),
    spoken: window.__spoken ?? [],
  }))
  if (dailyAfter.say === dailyBefore) throw new Error('点了答题页小算但台词没换')
  if (!dailyAfter.spoken.includes(dailyAfter.say)) {
    throw new Error(`答题页台词换成「${dailyAfter.say}」却没有把它读出来`)
  }

  return `首页「${homeAfter.line.slice(0, 12)}…」/ 今日冒险「${dailyAfter.say.slice(0, 12)}…」，两处都朗读`
})

await interact('比大小擂台：> < = 三个符号', '/#/compare', async (page) => {
  await page.waitForSelector('.opt.sym', { timeout: 8000 })
  const info = await page.evaluate(() => ({
    symbols: [...document.querySelectorAll('.opt.sym')].map((b) => b.innerText.trim()),
    numbers: [...document.querySelectorAll('.cmp-num')].map((e) => Number(e.innerText)),
    slot: document.querySelector('.cmp-slot')?.innerText.trim() ?? '',
  }))
  if (info.symbols.join('') !== '<=>') throw new Error(`选项应为 < = >，实际 ${info.symbols.join('')}`)
  if (info.numbers.length !== 2 || info.numbers.some((n) => !Number.isInteger(n))) {
    throw new Error(`比大小题应展示两个整数，实际 ${JSON.stringify(info.numbers)}`)
  }
  if (info.slot !== '?') throw new Error(`未作答时中间应是问号，实际「${info.slot}」`)

  const [left, right] = info.numbers
  const expected = left > right ? '>' : left < right ? '<' : '='
  await page.evaluate((symbol) => {
    const el = [...document.querySelectorAll('.opt.sym')].find((b) => b.innerText.trim() === symbol)
    el.click()
  }, expected)
  await sleep(600)
  const filled = await page.evaluate(() => document.querySelector('.cmp-slot')?.innerText.trim() ?? '')
  if (filled !== expected) throw new Error(`答对后中间应显示 ${expected}，实际「${filled}」`)

  const graded = await page.evaluate(
    () => document.querySelectorAll('.session-bar .dot.ok').length,
  )
  if (graded < 1) throw new Error('答对了但进度条上没有记一题')
  return `${left} ${expected} ${right} 判定正确，本轮已判 ${graded} 题`
})

await interact('算术恒星：数字键盘输入', '/#/arithmetic', async (page) => {
  // 点完切换按钮要等一拍再查 DOM，同一个 evaluate 里 Vue 还没重渲染出键盘
  const toggled = await page.evaluate(() => {
    const toggle = [...document.querySelectorAll('button')].find((b) => /键盘|输入/.test(b.innerText))
    if (!toggle) return false
    toggle.click()
    return true
  })
  await sleep(400)
  const hasKeypad = await page.evaluate(() => document.querySelectorAll('.key').length > 0)
  if (!hasKeypad) throw new Error(`没切出数字键盘（找到切换按钮=${toggled}）`)

  const typed = await page.evaluate(() => {
    const digit = [...document.querySelectorAll('.key')].find((k) => /^\d$/.test(k.innerText.trim()))
    if (!digit) return null
    digit.click()
    return digit.innerText.trim()
  })
  await sleep(300)
  if (!typed) throw new Error('数字键盘上没有可按的数字键')
  const echoed = await page.evaluate(() => document.querySelector('.equation .slot')?.innerText?.trim() ?? '')
  if (echoed !== typed) throw new Error(`按下「${typed}」但算式里显示的是「${echoed}」`)
  return `切到键盘=${hasKeypad}，按下「${typed}」后算式回显「${echoed}」`
})

await interact('数独空间站：填格 + 提示直到完成', '/#/sudoku', async (page) => {
  const cells = await page.evaluate(() => document.querySelectorAll('.cell').length)
  // 选格与按数字要分两拍：数字键在选中格子之前是禁用的，
  // 同一个 evaluate 里查不到 Vue 刚更新的 disabled 状态
  const emptyBefore = await page.evaluate(
    () => [...document.querySelectorAll('.cell')].filter((c) => !c.innerText.trim()).length,
  )
  await page.evaluate(() => {
    const empty = [...document.querySelectorAll('.cell')].find((c) => !c.innerText.trim())
    if (empty) empty.click()
  })
  await sleep(250)
  await page.evaluate(() => {
    const pad = [...document.querySelectorAll('.numkey:not(.erase)')].find((b) => !b.disabled)
    if (pad) pad.click()
  })
  await sleep(400)
  const emptyAfter = await page.evaluate(
    () => [...document.querySelectorAll('.cell')].filter((c) => !c.innerText.trim()).length,
  )
  const filled = emptyAfter === emptyBefore - 1
  if (!filled) throw new Error(`填数没生效：空格 ${emptyBefore} → ${emptyAfter}`)

  let hints = 0
  for (let i = 0; i < 20; i++) {
    const clicked = await page.evaluate(() => {
      const el = [...document.querySelectorAll('button')].find(
        (b) => /提示/.test(b.innerText) && !b.disabled,
      )
      if (!el) return false
      el.click()
      return true
    })
    if (!clicked) break
    hints++
    await sleep(220)
    const done = await page.evaluate(() => /完成|通关|太棒|恭喜/.test(document.body.innerText))
    if (done) break
  }
  const solved = await page.evaluate(() => /完成|通关|太棒|恭喜/.test(document.body.innerText))
  return `格子数=${cells}，填入成功=${filled}，提示 ${hints} 次，出现完成态=${solved}`
})

await interact('成就墙：改名 / 导出 / 清空进度', '/#/progress', async (page) => {
  const clickText = (t) =>
    page.evaluate((text) => {
      const el = [...document.querySelectorAll('button')].find((b) => b.innerText.includes(text))
      if (!el) return false
      el.click()
      return true
    }, t)

  const renamed = await clickText('改名')
  await sleep(200)
  await page.evaluate(() => {
    const input = document.querySelector('input[type="text"], .name-input')
    if (!input) return
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
    setter.call(input, '测试船长')
    input.dispatchEvent(new Event('input', { bubbles: true }))
  })
  await clickText('保存')
  await sleep(300)
  const nameShown = await page.evaluate(() => document.body.innerText.includes('测试船长'))

  const exported = await clickText('导出')
  await sleep(400)

  await clickText('重置')
  await sleep(250)
  const reset = await clickText('确认清空')
  await sleep(500)
  const starsAfter = await starCount(page)
  if (reset && starsAfter !== 0) throw new Error(`清空后星星仍为 ${starsAfter}`)
  return `改名=${renamed && nameShown}，导出按钮=${exported}，清空=${reset}，清空后星星=${starsAfter}`
})

await interact('家长面板：家长门 / 报表 / 设置持久化', '/#/parent', async (page) => {
  await page.evaluate(() => {
    const now = Date.now()
    localStorage.setItem(
      'mathquest/progress',
      JSON.stringify({
        pilotName: '回归测试员',
        stars: 24,
        xp: 30,
        level: 2,
        totalAnswered: 10,
        totalCorrect: 8,
        bestStreak: 5,
        mastery: { 'add-within-20': 0.82, 'shape-2d': 0.64 },
        dailyStreak: 3,
        lastPlayedDate: new Date(now).toISOString().slice(0, 10),
        errorTagCounts: { calculation: 2 },
        modules: {
          arithmetic: {
            answered: 10,
            correct: 8,
            stars: 20,
            sessions: 1,
            bestScore: 80,
            lastPlayed: now,
          },
        },
        counters: { arithmeticHardCorrect: 2, sudokuSolved: 0, perfectRuns: 0 },
        achievements: {},
        settings: { sound: true, animations: true },
        history: [
          {
            moduleId: 'arithmetic',
            correct: 8,
            total: 10,
            score: 80,
            durationMs: 12 * 60 * 1000,
            at: now,
          },
        ],
        totalStudyMs: 12 * 60 * 1000,
      }),
    )
  })
  await page.reload({ waitUntil: 'networkidle2' })
  await sleep(500)

  const gate = await page.evaluate(() => {
    const match = document.body.innerText.match(/(\d+)\s*([+＋\-−xX×*])\s*(\d+)/)
    const input = document.querySelector(
      'input[type="number"], input[inputmode="numeric"], input[pattern*="[0-9]"]',
    )
    if (!match || !input) return null

    const left = Number(match[1])
    const right = Number(match[3])
    const operator = match[2]
    const answer = /[-−]/.test(operator)
      ? left - right
      : /[xX×*]/.test(operator)
        ? left * right
        : left + right
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
    setter.call(input, String(answer))
    input.dispatchEvent(new Event('input', { bubbles: true }))
    input.dispatchEvent(new Event('change', { bubbles: true }))
    return { expression: match[0], answer }
  })
  if (!gate) throw new Error('家长面板没有口算家长门')

  const entered = await page.evaluate(() => {
    const button = [...document.querySelectorAll('button')].find(
      (node) => /进入|验证|确认|解锁|提交/.test(node.innerText) && !node.disabled,
    )
    if (!button) return false
    button.click()
    return true
  })
  if (!entered) throw new Error('填写口算答案后找不到进入按钮')
  await sleep(600)

  const panel = await page.evaluate(() => {
    const text = document.body.innerText.replace(/\s+/g, ' ')
    const checks = {
      accuracy: /正确率/.test(text),
      duration: /学习时长|练习时长|累计时长|学习时间/.test(text),
      ability: /能力|掌握度|技能|薄弱|模块表现/.test(text),
      difficulty: /难度|年龄档|年龄段|练习范围/.test(text),
      sound: /音量|声音|音效|语音/.test(text),
      motion: /动效|动画/.test(text),
      timeLimit: /时长提醒|使用时长|休息提醒|防沉迷/.test(text),
      export: /导出/.test(text),
    }
    return { checks, text: text.slice(0, 300) }
  })
  const missing = Object.entries(panel.checks)
    .filter(([, present]) => !present)
    .map(([name]) => name)
  if (missing.length) {
    throw new Error(`解锁后家长面板缺少：${missing.join('、')}；页面：${panel.text}`)
  }

  const storageBefore = await page.evaluate(() => Object.fromEntries(Object.entries(localStorage)))
  const toggled = await page.evaluate(() => {
    const controls = [...document.querySelectorAll('button, input, select')]
    const control = controls.find((node) => {
      const label = node.closest('label')
      const text = [
        node.innerText,
        node.getAttribute('aria-label'),
        node.getAttribute('title'),
        label?.innerText,
      ]
        .filter(Boolean)
        .join(' ')
      return /动效|动画/.test(text) && !node.disabled
    })
    if (!control) return false
    control.click()
    return true
  })
  if (!toggled) throw new Error('家长面板缺少可操作的动效设置')
  await sleep(300)

  const storageAfter = await page.evaluate(() => Object.fromEntries(Object.entries(localStorage)))
  const changedKeys = Object.keys(storageAfter).filter(
    (key) => storageAfter[key] !== storageBefore[key],
  )
  if (!changedKeys.length) throw new Error('切换动效后没有持久化任何设置')

  await page.reload({ waitUntil: 'networkidle2' })
  await sleep(400)
  const persisted = await page.evaluate(
    (expected) => expected.every(([key, value]) => localStorage.getItem(key) === value),
    changedKeys.map((key) => [key, storageAfter[key]]),
  )
  if (!persisted) throw new Error(`刷新后设置存档发生变化：${changedKeys.join('、')}`)

  return `口算 ${gate.expression}=${gate.answer}；报表/设置/导出齐全；持久化 ${changedKeys.join('、')}`
})

await interact('无障碍：键盘也能装货', '/#/number-sense', async (page) => {
  // 先跳到一道装货题（装货题的货物也带 .opt 类，所以这里不能用 answerOnce 盲点）
  const isCargoQuestion = () =>
    page.evaluate(() => /把\s*\d+\s*个/.test(document.body.innerText))
  let found = await isCargoQuestion()
  for (let i = 0; i < 8 && !found; i++) {
    if (!(await answerOnce(page))) break
    await sleep(1600)
    found = await isCargoQuestion()
  }
  if (!found) return '本轮没抽到装货题，跳过'

  // 上一题的反馈期内货物是锁住的，等它过去再测键盘
  await page.waitForFunction(
    () => {
      const go = [...document.querySelectorAll('button')].find((b) => /发射/.test(b.innerText))
      return go && !go.disabled
    },
    { timeout: 5000 },
  )

  const before = await page.evaluate(
    () => Number(document.querySelector('.counter-num')?.innerText ?? -1),
  )
  const focusable = await page.evaluate(() => {
    const it = [...document.querySelectorAll('.pool .cargo')].filter((b) => !b.disabled)[0]
    if (!it) return false
    it.focus()
    return document.activeElement === it
  })
  await page.keyboard.press('Enter')
  await sleep(300)
  const after = await page.evaluate(
    () => Number(document.querySelector('.counter-num')?.innerText ?? -1),
  )
  if (!(after === before + 1)) throw new Error(`回车没有装货：${before} → ${after}`)
  return `可聚焦=${focusable}，回车装货 ${before} → ${after}`
})

await interact('进度持久化：答题后刷新仍在', '/#/geometry', async (page) => {
  // 星星只在答对时才涨，而脚本是随机点选项的，拿星星当断言可能恒等于 0；
  // totalAnswered 答对答错都会加，是这里唯一稳定可判的量。
  const answeredCount = () =>
    page.evaluate(
      () => JSON.parse(localStorage.getItem('mathquest/progress') || '{}').totalAnswered ?? 0,
    )

  await playChoiceModule(page, 4)
  const before = await answeredCount()
  const starsBefore = await starCount(page)
  if (before === 0) throw new Error('答了 4 题但 totalAnswered 仍是 0，进度根本没写入')

  await page.goto(base + '/#/', { waitUntil: 'networkidle2' })
  await page.reload({ waitUntil: 'networkidle2' })
  await sleep(700)
  const after = await answeredCount()
  const starsAfter = await starCount(page)
  if (after !== before) throw new Error(`刷新后作答数从 ${before} 变成 ${after}`)
  if (starsAfter !== starsBefore) throw new Error(`刷新后星星从 ${starsBefore} 变成 ${starsAfter}`)
  return `刷新前后作答数都是 ${after}，星星都是 ${starsAfter}`
})

/* --------------------------------------------------- QuizShell 通用答题壳 */

await interact('QuizShell：数字键选项 + 进度条推进', '/#/arithmetic', async (page) => {
  await page.waitForSelector('.opt')
  const read = () =>
    page.evaluate(() => ({
      judged: document.querySelectorAll('.session-bar .dot.ok, .session-bar .dot.no').length,
      width: document.querySelector('.progress-fill')?.style.width ?? '',
    }))

  const before = await read()
  if (!before.width) throw new Error('没有找到 QuizShell 的进度条')
  await page.keyboard.press('1')
  await sleep(600)
  const after = await read()
  if (after.judged !== before.judged + 1) {
    throw new Error(`按数字键 1 没有作答：已判定 ${before.judged} → ${after.judged}`)
  }
  await sleep(1200)
  const moved = await read()
  if (parseInt(moved.width, 10) <= parseInt(before.width, 10)) {
    throw new Error(`进度条没有推进：${before.width} → ${moved.width}`)
  }
  return `数字键作答 ${before.judged} → ${after.judged} 题，进度条 ${before.width} → ${moved.width}`
})

await interact('QuizShell：答错给出错因标签', '/#/arithmetic', async (page) => {
  await page.waitForSelector('.opt')
  // 先算出正确答案，才能故意点一个错的，随机点有可能刚好点对
  const picked = await page.evaluate(() => {
    const terms = [...document.querySelectorAll('.equation .term')].map((e) => Number(e.innerText))
    const sign = document.querySelector('.equation .sign')?.innerText ?? '+'
    const answer = sign === '+' ? terms[0] + terms[1] : terms[0] - terms[1]
    const wrong = [...document.querySelectorAll('.opt')].find((b) => Number(b.innerText) !== answer)
    if (!wrong) return null
    const chosen = Number(wrong.innerText)
    wrong.click()
    return { answer, chosen }
  })
  if (!picked) throw new Error('这道题的选项里找不到错误项')
  await sleep(500)
  const tags = await page.evaluate(() =>
    [...document.querySelectorAll('.why-chip')].map((e) => e.innerText.trim()),
  )
  if (!tags.length) {
    throw new Error(`答错 ${picked.chosen}（正确 ${picked.answer}）却没有显示错因标签`)
  }
  const stored = await page.evaluate(
    () => Object.keys(JSON.parse(localStorage.getItem('mathquest/progress') || '{}').errorTagCounts ?? {}).length,
  )
  if (!stored) throw new Error('错因标签没有写进 progress.errorTagCounts')
  return `故意答错 ${picked.chosen}（正确 ${picked.answer}），错因「${tags.join('/')}」，已入库 ${stored} 类`
})

await interact('错题本：答错入库 → 进度页重做出库', '/#/arithmetic', async (page) => {
  // 前面几项是随机作答，攒下的错题会让这里的条数断言失准，先清干净
  await page.evaluate(() => localStorage.clear())
  await page.reload({ waitUntil: 'networkidle2' })
  await sleep(700)
  await page.waitForSelector('.opt')

  const picked = await page.evaluate(() => {
    const terms = [...document.querySelectorAll('.equation .term')].map((e) => Number(e.innerText))
    const sign = document.querySelector('.equation .sign')?.innerText ?? '+'
    const answer = sign === '+' ? terms[0] + terms[1] : terms[0] - terms[1]
    const wrong = [...document.querySelectorAll('.opt')].find((b) => Number(b.innerText) !== answer)
    if (!wrong) return null
    wrong.click()
    return { answer, chosen: Number(wrong.innerText) }
  })
  if (!picked) throw new Error('这道题的选项里找不到错误项')
  await sleep(600)

  const readBook = () =>
    page.evaluate(
      () => JSON.parse(localStorage.getItem('mathquest/progress') || '{}').wrongBook ?? {},
    )

  const book = await readBook()
  const keys = Object.keys(book)
  if (keys.length !== 1) throw new Error(`答错 1 题后错题本应有 1 条，实际 ${keys.length}`)
  const entry = book[keys[0]]
  if (entry.answer !== picked.answer) {
    throw new Error(`错题本记下的答案是 ${entry.answer}，应为 ${picked.answer}`)
  }
  if (!entry.skill) throw new Error('错题本条目没有技能点')
  if (!entry.errorTag) throw new Error('错题本条目没有错因标签')
  if (entry.attempts !== 1) throw new Error(`首次入库 attempts 应为 1，实际 ${entry.attempts}`)

  await page.goto(base + '/#/progress', { waitUntil: 'networkidle2' })
  await sleep(800)
  const listed = await page.evaluate(() => document.querySelectorAll('.wb-item').length)
  if (listed !== 1) throw new Error(`进度页错题本应列出 1 条，实际 ${listed}`)

  const openRetry = () =>
    page.evaluate(() => {
      const btn = document.querySelector('.wb-item .btn--primary')
      if (!btn) return false
      btn.click()
      return true
    })
  if (!(await openRetry())) throw new Error('错题本没有重做入口')
  await sleep(350)

  // 先故意再错一次：条目要留下，attempts 继续累加
  const missed = await page.evaluate((answer) => {
    const opt = [...document.querySelectorAll('.wb-opt')].find(
      (b) => Number(b.innerText) !== answer && !b.disabled,
    )
    if (!opt) return false
    opt.click()
    return true
  }, picked.answer)
  if (!missed) throw new Error('重做面板里没有可点的错误选项')
  await sleep(400)
  const afterMiss = await readBook()
  if (Object.keys(afterMiss).length !== 1) throw new Error('重做答错不该把题移出错题本')
  if (afterMiss[keys[0]].attempts !== 2) {
    throw new Error(`重做答错后 attempts 应为 2，实际 ${afterMiss[keys[0]].attempts}`)
  }

  const hit = await page.evaluate((answer) => {
    const opt = [...document.querySelectorAll('.wb-opt')].find(
      (b) => Number(b.innerText) === answer && !b.disabled,
    )
    if (!opt) return false
    opt.click()
    return true
  }, picked.answer)
  if (!hit) throw new Error('重做面板里没有正确选项')
  await sleep(500)

  const afterHit = await readBook()
  if (Object.keys(afterHit).length !== 0) throw new Error('重做答对后错题没有移出错题本')
  const rows = await page.evaluate(() => ({
    items: document.querySelectorAll('.wb-item').length,
    text: document.body.innerText.includes('错题本是空的'),
  }))
  if (rows.items !== 0) throw new Error(`重做答对后列表仍有 ${rows.items} 条`)
  if (!rows.text) throw new Error('错题本清空后没有显示空状态')

  // 刷新后仍然是空的，说明出库也落了盘
  await page.reload({ waitUntil: 'networkidle2' })
  await sleep(600)
  const persisted = Object.keys(await readBook()).length
  if (persisted !== 0) throw new Error(`刷新后错题本又冒出 ${persisted} 条`)
  return `答错 ${picked.chosen}（正确 ${picked.answer}）入库，重做再错 attempts=2，答对后出库并落盘`
})

await interact('生活行星：母题规模与进阶档', '/#/word-problems', async (page) => {
  const bank = await page.evaluate(() => {
    const m = document.body.innerText.match(/母题\s*(\d+)\s*\/\s*(\d+)\s*道/)
    return m ? Number(m[2]) : 0
  })
  if (bank < 185) throw new Error(`母题只有 ${bank} 类，少于要求的 185 类`)

  const switched = await page.evaluate(() => {
    const el = [...document.querySelectorAll('.seg-btn')].find((b) => b.innerText.includes('进阶'))
    if (!el) return false
    el.click()
    return true
  })
  if (!switched) throw new Error('没有「进阶题」难度档')
  await sleep(700)
  const marked = await page.evaluate(
    () => document.querySelector('.problem')?.innerText.includes('进阶') ?? false,
  )
  if (!marked) throw new Error('切到进阶档后题面上没有「进阶」标记')
  return `母题 ${bank} 类，进阶档题面标记正常`
})

await interact('数独空间站：切换 9×9 档位', '/#/sudoku', async (page) => {
  const switched = await page.evaluate(() => {
    const el = [...document.querySelectorAll('.seg-btn')].find((b) => b.innerText.includes('9×9'))
    if (!el) return false
    el.click()
    return true
  })
  if (!switched) throw new Error('没有 9×9 档位按钮')
  await sleep(1200)

  const info = await page.evaluate(() => ({
    cells: document.querySelectorAll('.cell').length,
    keys: document.querySelectorAll('.numkey:not(.erase)').length,
    empty: [...document.querySelectorAll('.cell')].filter((c) => !c.innerText.trim()).length,
  }))
  if (info.cells !== 81) throw new Error(`9×9 棋盘应有 81 格，实际 ${info.cells}`)
  if (info.keys !== 9) throw new Error(`9×9 应有 1–9 九个数字键，实际 ${info.keys}`)

  await page.evaluate(() => {
    const e = [...document.querySelectorAll('.cell')].find((c) => !c.innerText.trim())
    if (e) e.click()
  })
  await sleep(250)
  await page.evaluate(() => {
    const k = [...document.querySelectorAll('.numkey:not(.erase)')].find((b) => !b.disabled)
    if (k) k.click()
  })
  await sleep(350)
  const emptyAfter = await page.evaluate(
    () => [...document.querySelectorAll('.cell')].filter((c) => !c.innerText.trim()).length,
  )
  if (emptyAfter !== info.empty - 1) {
    throw new Error(`9×9 填数没生效：空格 ${info.empty} → ${emptyAfter}`)
  }
  return `81 格 / 9 个数字键，空格 ${info.empty} → ${emptyAfter}`
})

await interact('年龄档：L1 与 L5 的起步难度贯穿六个玩法', '/#/', async (page) => {
  /** [路由, 徽标里必须出现的默认难度, 高亮档位里必须出现的字样（没有档位按钮就传 null）] */
  const CASES = {
    L1: [
      ['/#/number-sense', '数到 8', null],
      ['/#/arithmetic', '10 以内加法', '10 以内'],
      ['/#/geometry', '平面图形', '平面图形'],
      ['/#/logic', '图案循环', null],
      ['/#/word-problems', '一步应用题', '一步题'],
      ['/#/sudoku', '4×4 简单', '4×4'],
    ],
    L5: [
      ['/#/number-sense', '数到 60', null],
      ['/#/arithmetic', '100 以内加减', '100 以内'],
      ['/#/geometry', '平面 + 立体', '全部混合'],
      ['/#/logic', '复合与交替规律', null],
      ['/#/word-problems', '进阶多步题', '进阶题'],
      ['/#/sudoku', '9×9 简单', '9×9'],
    ],
  }
  const SUDOKU_CELLS = { L1: 16, L5: 81 }

  const done = []
  for (const [bandId, cases] of Object.entries(CASES)) {
    await page.evaluate((band) => {
      localStorage.setItem('mathquest/settings', JSON.stringify({ ageBand: band }))
    }, bandId)
    // 档位是 App 启动时从 localStorage 读进 store 的，改完要重新加载才生效
    await page.reload({ waitUntil: 'networkidle2' })
    await sleep(400)

    for (const [path, hint, active] of cases) {
      await page.goto(base + path, { waitUntil: 'networkidle2' })
      await sleep(800)
      const seen = await page.evaluate(() => ({
        badge: document.querySelector('.band-badge')?.innerText.replace(/\s+/g, ' ').trim() ?? '',
        on: [...document.querySelectorAll('.seg-btn.on')].map((b) => b.innerText.trim()).join(' / '),
        cells: document.querySelectorAll('.cell').length,
      }))
      if (!seen.badge.includes(hint)) {
        throw new Error(`${bandId} 下 ${path} 的年龄档徽标是「${seen.badge}」，应含「${hint}」`)
      }
      if (active && !seen.on.includes(active)) {
        throw new Error(`${bandId} 下 ${path} 高亮的档位是「${seen.on}」，应含「${active}」`)
      }
      if (path === '/#/sudoku' && seen.cells !== SUDOKU_CELLS[bandId]) {
        throw new Error(`${bandId} 下数独应有 ${SUDOKU_CELLS[bandId]} 格，实际 ${seen.cells}`)
      }
    }
    done.push(`${bandId} 六个玩法全部跟档`)
  }

  await page.evaluate(() => localStorage.removeItem('mathquest/settings'))
  return done.join('；')
})

/* ---------------------------------------------------------- 技能图谱 */

/**
 * ROUND8_H3_SMOKE — 技能图谱是只读视图：
 * 图上的节点与连线必须和 curriculum 一一对应，状态必须由存档里的掌握度推出来，
 * 年龄档只改「本档该会」的标注、不改状态，逛一圈也不能把进度写脏。
 */
await interact('技能图谱：依赖成图、状态跟着存档走、只读不写进度', '/#/skill-graph', async (page) => {
  const SEED_MASTERY = { 'count-to-5': 0.95, 'count-to-10': 0.9, 'add-within-10': 0.4 }
  const expectedNodes = SKILLS.length
  const expectedEdges = SKILLS.reduce((sum, s) => sum + (s.deps?.length ?? 0), 0)
  const inBandCount = (band) => {
    const rank = ['L1', 'L2', 'L3', 'L4', 'L5'].indexOf(band)
    return SKILLS.filter((s) => ['L1', 'L2', 'L3', 'L4', 'L5'].indexOf(s.level) <= rank).length
  }

  const load = async (band) => {
    await page.evaluate(
      (mastery, ageBand) => {
        localStorage.setItem('mathquest/progress', JSON.stringify({ stars: 5, mastery }))
        localStorage.setItem('mathquest/settings', JSON.stringify({ ageBand }))
      },
      SEED_MASTERY,
      band,
    )
    await page.reload({ waitUntil: 'networkidle2' })
    await sleep(700)
  }

  await load('L2')

  const shape = await page.evaluate(() => ({
    nodes: document.querySelectorAll('[data-skill-node]').length,
    edges: document.querySelectorAll('[data-skill-edge]').length,
    lanes: document.querySelectorAll('[data-skill-lane]').length,
    openEdges: document.querySelectorAll('[data-skill-edge].open').length,
    mastered: document.querySelector('[data-graph-stat="mastered"]')?.innerText ?? '',
  }))
  if (shape.nodes !== expectedNodes) {
    throw new Error(`图上有 ${shape.nodes} 个技能节点，课程表里是 ${expectedNodes} 个`)
  }
  if (shape.edges !== expectedEdges) {
    throw new Error(`图上有 ${shape.edges} 条依赖连线，课程表里是 ${expectedEdges} 条`)
  }
  if (shape.lanes !== 6) throw new Error(`应有 6 条星球泳道，实际 ${shape.lanes}`)
  if (!shape.mastered.includes(`2/${expectedNodes}`)) {
    throw new Error(`概览里的已掌握数是「${shape.mastered}」，存档里达标的是 2 个`)
  }
  if (shape.openEdges < 1) throw new Error('前置已达标，却没有一条连线被点亮')

  const statusOf = (id) =>
    page.evaluate(
      (skill) => document.querySelector(`[data-skill-node="${skill}"]`)?.dataset.skillStatus ?? '',
      id,
    )
  const WANT = {
    'count-to-5': 'mastered',
    'count-to-10': 'mastered',
    'count-to-20': 'ready',
    'add-within-10': 'learning',
    'sub-within-10': 'locked',
  }
  for (const [id, want] of Object.entries(WANT)) {
    const got = await statusOf(id)
    if (got !== want) throw new Error(`「${id}」的状态是 ${got || '空'}，按存档应该是 ${want}`)
  }

  // 点节点只展开详情：前置、后继与去练入口都要真的渲染出来
  await page.click('[data-skill-node="count-to-20"]')
  await sleep(300)
  const detail = await page.evaluate(() => {
    const panel = document.querySelector('[data-skill-detail]')
    return {
      text: panel?.innerText.replace(/\s+/g, ' ') ?? '',
      deps: [...document.querySelectorAll('[data-skill-dep]')].map((el) => el.dataset.skillDep),
      link: panel?.querySelector('a')?.getAttribute('href') ?? '',
    }
  })
  if (!detail.text.includes('20以内点数')) throw new Error('详情卡没有显示选中的技能名')
  if (!detail.deps.includes('count-to-10')) {
    throw new Error(`详情卡的前置是 ${detail.deps.join('、') || '空'}，应含 count-to-10`)
  }
  if (!detail.link.includes('/number-sense')) {
    throw new Error(`「去练」应指向数量星云，实际 ${detail.link || '没有链接'}`)
  }

  // 年龄档只影响「本档该会」的标注，节点状态一个都不许变
  const bandView = async (band) => {
    await load(band)
    return page.evaluate(() => ({
      inBand: document.querySelectorAll('[data-in-band="1"]').length,
      statuses: [...document.querySelectorAll('[data-skill-node]')]
        .map((el) => `${el.dataset.skillNode}:${el.dataset.skillStatus}`)
        .join(','),
    }))
  }
  const low = await bandView('L1')
  const high = await bandView('L5')
  if (low.inBand !== inBandCount('L1')) {
    throw new Error(`L1 档标为本档的有 ${low.inBand} 个，课程表里是 ${inBandCount('L1')} 个`)
  }
  if (high.inBand !== expectedNodes) {
    throw new Error(`L5 档应覆盖全部 ${expectedNodes} 个技能，实际 ${high.inBand} 个`)
  }
  if (low.statuses !== high.statuses) throw new Error('切换年龄档改变了技能状态，图谱判读被污染')

  // 「只看本档」是页面内的筛选：压暗超前技能，但不写回家长中心的档位
  await load('L1')
  await page.click('[data-band-filter]')
  await sleep(300)
  const filtered = await page.evaluate(() => ({
    faded: document.querySelectorAll('[data-skill-node].faded').length,
    band: JSON.parse(localStorage.getItem('mathquest/settings') || '{}').ageBand,
  }))
  if (filtered.faded !== expectedNodes - inBandCount('L1')) {
    throw new Error(
      `只看 L1 应压暗 ${expectedNodes - inBandCount('L1')} 个超前技能，实际 ${filtered.faded} 个`,
    )
  }
  if (filtered.band !== 'L1') throw new Error(`筛选改写了家长中心的档位：${filtered.band}`)

  await page.click('[data-band-filter]')
  await sleep(200)
  await page.click('[data-module-filter="arithmetic"]')
  await sleep(300)
  const byModule = await page.evaluate(() => ({
    faded: document.querySelectorAll('[data-skill-node].faded').length,
    total: document.querySelectorAll('[data-skill-node]').length,
  }))
  const arithmeticSkills = SKILLS.filter((s) => s.module === 'arithmetic').length
  if (byModule.faded !== byModule.total - arithmeticSkills) {
    throw new Error(
      `按算术恒星筛选后压暗了 ${byModule.faded} 个，应为 ${byModule.total - arithmeticSkills} 个`,
    )
  }

  // 逛完一圈，存档里的掌握度必须原封不动
  const after = await page.evaluate(
    () => JSON.parse(localStorage.getItem('mathquest/progress') || '{}').mastery,
  )
  for (const [id, value] of Object.entries(SEED_MASTERY)) {
    if (after?.[id] !== value) throw new Error(`图谱把「${id}」的掌握度改成了 ${after?.[id]}`)
  }
  if (Object.keys(after ?? {}).length !== Object.keys(SEED_MASTERY).length) {
    throw new Error('图谱往掌握度里塞了新的技能点')
  }

  await page.evaluate(() => {
    localStorage.removeItem('mathquest/settings')
    localStorage.removeItem('mathquest/progress')
  })
  return (
    `${shape.nodes} 节点 / ${shape.edges} 连线 / ${shape.lanes} 泳道，` +
    `本档覆盖 L1 ${low.inBand} → L5 ${high.inBand}，` +
    `只看本档压暗 ${filtered.faded} 个、按星球筛选压暗 ${byModule.faded} 个，掌握度未被改写`
  )
})

/**
 * ROUND9_H3_SMOKE — 技能图谱的「推荐下一步」：
 * 推荐只能从存档里长出来（练过没过线的先补、待解锁的不许上榜），
 * 排序要跟着年龄档动、判读不许跟着年龄档动，
 * 而且从头到尾不能往 progress 里写一个字节——它是建议，不是打卡。
 */
await interact('技能图谱：推荐下一步跟着掌握度与年龄档走，且只读', `/#${ROUND9_H3_SMOKE}`, async (page) => {
  const SEED_MASTERY = { 'count-to-5': 0.95, 'count-to-10': 0.9, 'add-within-10': 0.4 }
  const skillMap = Object.fromEntries(SKILLS.map((s) => [s.id, s]))
  const MASTERED = new Set(
    Object.entries(SEED_MASTERY)
      .filter(([, value]) => value >= 0.8)
      .map(([id]) => id),
  )

  const load = async (band) => {
    await page.evaluate(
      (mastery, ageBand) => {
        localStorage.setItem('mathquest/progress', JSON.stringify({ stars: 5, mastery }))
        localStorage.setItem('mathquest/settings', JSON.stringify({ ageBand }))
      },
      SEED_MASTERY,
      band,
    )
    await page.reload({ waitUntil: 'networkidle2' })
    await sleep(700)
    return page.evaluate(() => ({
      items: [...document.querySelectorAll('[data-reco-item]')].map((el) => ({
        id: el.dataset.recoItem,
        reason: el.dataset.recoReason,
        rank: Number(el.dataset.recoRank),
        text: el.innerText.replace(/\s+/g, ' ').trim(),
        href: el.querySelector('a')?.getAttribute('href') ?? '',
        planetHref: el.querySelector('[data-reco-planet]')?.getAttribute('href') ?? '',
      })),
      goal: document.querySelector('[data-reco-goal]')?.dataset.recoGoal ?? '',
      path: [...document.querySelectorAll('[data-reco-step]')].map((el) => el.dataset.recoStep),
      // 图上描圈的推荐位：节点按布局顺序排在 DOM 里，只能按 id 对序号
      ringed: Object.fromEntries(
        [...document.querySelectorAll('[data-skill-node][data-reco-rank]')].map((el) => [
          el.dataset.skillNode,
          Number(el.dataset.recoRank),
        ]),
      ),
      status: Object.fromEntries(
        [...document.querySelectorAll('[data-skill-node]')].map((el) => [
          el.dataset.skillNode,
          el.dataset.skillStatus,
        ]),
      ),
      readOnlyNote: document.querySelector('[data-reco-readonly]')?.innerText.trim() ?? '',
    }))
  }

  /** 「技能:序号」按 id 排序拼成一行，图上和列表的 DOM 顺序不同，只能这么比。 */
  const canonRanks = (map) =>
    Object.keys(map)
      .sort()
      .map((id) => `${id}:${map[id]}`)
      .join(',')

  /** 一份推荐自身必须成立的部分，三个档位都要过一遍。 */
  const audit = (band, view) => {
    if (!view.items.length) throw new Error(`${band} 档没有给出任何推荐`)
    if (view.items.length > 4) throw new Error(`${band} 档一口气推了 ${view.items.length} 条`)
    if (!view.readOnlyNote.includes('不写进度')) {
      throw new Error(`${band} 档的推荐位没有标明只读：「${view.readOnlyNote}」`)
    }
    view.items.forEach((item, index) => {
      const status = view.status[item.id]
      if (status !== 'learning' && status !== 'ready') {
        throw new Error(`${band} 档推荐了 ${status} 的「${item.id}」，只能推能立刻练的`)
      }
      if (item.rank !== index + 1) throw new Error(`${band} 档推荐位的序号乱了：${item.rank}`)
      if (!item.reason) throw new Error(`${band} 档的「${item.id}」没有给出推荐理由`)
      if (item.text.length < 12) throw new Error(`${band} 档的「${item.id}」没有理由文案`)
      if (!item.href) throw new Error(`${band} 档的「${item.id}」没有去练的入口`)
    })
    // 图上描圈的节点必须和列表一一对应（连序号都要对上），否则家长照着图走会走岔
    const ringed = canonRanks(view.ringed)
    const listed = canonRanks(Object.fromEntries(view.items.map((item) => [item.id, item.rank])))
    if (ringed !== listed) throw new Error(`${band} 档图上描圈的是 ${ringed}，列表是 ${listed}`)
    // 超前的技能不许插到本档技能前面
    const lastInBand = view.items.reduce(
      (last, item, index) => (item.reason === 'ahead' ? last : index),
      -1,
    )
    const firstAhead = view.items.findIndex((item) => item.reason === 'ahead')
    if (firstAhead >= 0 && firstAhead < lastInBand) {
      throw new Error(`${band} 档把超前技能「${view.items[firstAhead].id}」排到了本档技能前面`)
    }

    if (!view.goal) throw new Error(`${band} 档没有给出本档目标`)
    if (!view.path.length) throw new Error(`${band} 档的目标「${view.goal}」没有路线`)
    if (view.path.at(-1) !== view.goal) {
      throw new Error(`${band} 档路线的终点是「${view.path.at(-1)}」，目标却是「${view.goal}」`)
    }
    const walked = new Set(MASTERED)
    for (const id of view.path) {
      if (MASTERED.has(id)) throw new Error(`${band} 档的路线里混进了已掌握的「${id}」`)
      for (const dep of skillMap[id]?.deps ?? []) {
        if (!walked.has(dep)) {
          throw new Error(`${band} 档路线上「${id}」排在了它的前置「${dep}」前面`)
        }
      }
      walked.add(id)
    }
  }

  const mid = await load('L2')
  audit('L2', mid)
  // 练过没过线的那个最该补，它必须占住第一条
  if (mid.items[0].id !== 'add-within-10' || mid.items[0].reason !== 'finish') {
    throw new Error(`存档里 add-within-10 练到 40%，推荐首条却是 ${mid.items[0].id}/${mid.items[0].reason}`)
  }
  // R10 起首选入口改成了「日冒险专项 / 错题重练」（见 ROUND10_H3_SMOKE），
  // 回星球的那条退成次入口，这里验的仍是「推荐认得它属于算术恒星」
  if (!mid.items[0].planetHref.includes('/arithmetic')) {
    throw new Error(`「去算术恒星」入口不对：${mid.items[0].planetHref || '没有链接'}`)
  }

  const low = await load('L1')
  audit('L1', low)
  const high = await load('L4')
  audit('L4', high)

  // 年龄档只换排法，不换判读
  const reasonOf = (view, id) => view.items.find((item) => item.id === id)?.reason ?? '(未上榜)'
  if (reasonOf(low, 'shape-2d') === reasonOf(high, 'shape-2d')) {
    throw new Error(`L1 与 L4 对 shape-2d 给的理由一样（${reasonOf(low, 'shape-2d')}），推荐没跟着档位动`)
  }
  if (low.goal === high.goal) throw new Error(`L1 与 L4 的本档目标都是「${low.goal}」`)
  if (high.path.length <= low.path.length) {
    throw new Error(`L4 的路线 ${high.path.length} 步，不该短于 L1 的 ${low.path.length} 步`)
  }
  const statusLine = (view) => Object.entries(view.status).map(([k, v]) => `${k}:${v}`).join(',')
  if (statusLine(low) !== statusLine(high)) {
    throw new Error('切换年龄档改变了技能状态，推荐污染了判读')
  }

  // 点推荐位、点节点、点筛选，逛完一圈存档必须一个字节都没动
  await page.click('[data-skill-node="add-within-10"]')
  await sleep(200)
  await page.click('[data-band-filter]')
  await sleep(200)
  const after = await page.evaluate(
    () => JSON.parse(localStorage.getItem('mathquest/progress') || '{}'),
  )
  for (const [id, value] of Object.entries(SEED_MASTERY)) {
    if (after.mastery?.[id] !== value) {
      throw new Error(`推荐把「${id}」的掌握度改成了 ${after.mastery?.[id]}`)
    }
  }
  if (Object.keys(after.mastery ?? {}).length !== Object.keys(SEED_MASTERY).length) {
    throw new Error('推荐往掌握度里塞了新的技能点')
  }
  if (after.stars !== 5) throw new Error(`推荐把星星改成了 ${after.stars}`)

  await page.evaluate(() => {
    localStorage.removeItem('mathquest/settings')
    localStorage.removeItem('mathquest/progress')
  })
  return (
    `L2 首推 ${mid.items[0].id}（${mid.items[0].reason}），` +
    `L1/L4 目标 ${low.goal}→${high.goal}、路线 ${low.path.length}→${high.path.length} 步，` +
    `图上描圈 ${Object.keys(mid.ringed).length} 个与列表一致，掌握度未被改写`
  )
})

/**
 * ROUND10_H3_SMOKE — 推荐 → 开练的闭环：
 * 图谱推荐排完序之后，「去练」必须落到真能练这一点的地方，而不是把孩子丢回星球首页。
 * 空错题本时可出题的技能落到「日冒险专项」（题目按日期 + 技能定死，刷新不换题、
 * 不占当天打卡），出不了题的落回它自己的星球；一旦欠下错题，同一条推荐立刻改走
 * 「错题重练」，点进去的错题本只列这一个技能的题。
 */
await interact('推荐闭环：一键落到日冒险专项 / 错题重练', `/#${ROUND10_H3_SMOKE}`, async (page) => {
  const SEED_MASTERY = { 'count-to-5': 0.95, 'count-to-10': 0.9, 'add-within-10': 0.4 }
  const FOCUS = 'add-within-10'

  const readEntries = () =>
    page.evaluate(() =>
      [...document.querySelectorAll('[data-reco-item]')].map((el) => {
        const cta = el.querySelector('[data-reco-entry]')
        return {
          id: el.dataset.recoItem,
          kind: cta?.dataset.recoEntry ?? '',
          href: cta?.getAttribute('href') ?? '',
          label: cta?.innerText.replace(/\s+/g, ' ').trim() ?? '',
          hint: el.querySelector('[data-reco-entry-hint]')?.innerText.trim() ?? '',
          planetHref: el.querySelector('[data-reco-planet]')?.getAttribute('href') ?? '',
        }
      }),
    )
  const store = () =>
    page.evaluate(() => JSON.parse(localStorage.getItem('mathquest/progress') || '{}'))

  await page.evaluate((mastery) => {
    localStorage.setItem('mathquest/progress', JSON.stringify({ stars: 5, mastery }))
    localStorage.setItem('mathquest/settings', JSON.stringify({ ageBand: 'L2' }))
  }, SEED_MASTERY)
  await page.reload({ waitUntil: 'networkidle2' })
  await sleep(700)

  /* ---- 一、空错题本：能出题的落到日冒险，出不了题的落回星球 ---- */
  const fresh = await readEntries()
  if (!fresh.length) throw new Error('推荐位一条建议都没有，谈不上开练入口')
  for (const entry of fresh) {
    if (!['daily', 'wrongBook', 'planet'].includes(entry.kind)) {
      throw new Error(`「${entry.id}」的落点是 ${entry.kind || '空'}，只认这三种`)
    }
    if (!entry.href) throw new Error(`「${entry.id}」的开练入口没有链接`)
    if (!entry.label || !entry.hint) throw new Error(`「${entry.id}」的入口没有文案`)
    if (entry.kind !== 'planet' && !entry.planetHref) {
      throw new Error(`「${entry.id}」深链到了 ${entry.kind}，却没留回星球的次入口`)
    }
  }
  if (fresh.some((entry) => entry.kind === 'wrongBook')) {
    throw new Error('错题本还是空的，却有推荐落到了错题重练')
  }

  const daily = fresh.find((entry) => entry.id === FOCUS)
  if (daily?.kind !== 'daily') throw new Error(`${FOCUS} 的落点应是日冒险，实际 ${daily?.kind}`)
  if (daily.href !== `#/daily?focus=${FOCUS}`) {
    throw new Error(`日冒险入口应带上技能点，实际 ${daily.href}`)
  }
  const planet = fresh.find((entry) => entry.kind === 'planet')
  if (!planet) throw new Error('每日冒险出不了的技能没有落回星球')
  if (planet.href.includes('/daily') || planet.href.includes('/progress')) {
    throw new Error(`星球落点指到了 ${planet.href}`)
  }

  // 只是把图看一遍、把落点算出来，存档一个字节都不该动
  const beforeClick = await store()
  if (JSON.stringify(beforeClick.mastery) !== JSON.stringify(SEED_MASTERY)) {
    throw new Error('算开练入口时改写了掌握度')
  }
  if (Object.keys(beforeClick.wrongBook ?? {}).length) throw new Error('算入口时凭空写出了错题')

  /* ---- 二、点进日冒险专项：只出这一个技能的题，刷新不换题，不占打卡 ---- */
  await page.evaluate((skill) => document.querySelector(`[data-reco-entry-skill="${skill}"]`).click(), FOCUS)
  await sleep(900)
  const landed = await page.evaluate(() => location.hash)
  if (landed !== `#/daily?focus=${FOCUS}`) throw new Error(`点「去练」跳到了 ${landed}`)

  const readFocus = () =>
    page.evaluate(() => ({
      chip: document.querySelector('[data-daily-focus]')?.dataset.dailyFocus ?? '',
      note: document.body.innerText.includes('不占今天的打卡'),
      prompt: document.querySelector('.quiz-prompt')?.innerText.replace(/\s+/g, ' ').trim() ?? '',
    }))
  const first = await readFocus()
  if (first.chip !== FOCUS) throw new Error(`专项页没有标出练的是哪一点：${first.chip || '空'}`)
  if (!first.note) throw new Error('专项冒险没有说明它不占当天打卡')
  if (!first.prompt) throw new Error('专项冒险没有渲染题目')

  await page.reload({ waitUntil: 'networkidle2' })
  await sleep(700)
  const again = await readFocus()
  if (again.prompt !== first.prompt) {
    throw new Error(`专项冒险刷新后换题了：「${first.prompt}」→「${again.prompt}」`)
  }

  // 故意答错两道：它们会进错题本，正好把下一段的落点从日冒险换成错题重练
  const missOnce = () =>
    page.evaluate(() => {
      const terms = [...document.querySelectorAll('.equation .term')].map((e) =>
        Number(e.innerText),
      )
      const sign = document.querySelector('.equation .sign')?.innerText ?? '+'
      const answer = sign === '+' ? terms[0] + terms[1] : terms[0] - terms[1]
      if (!Number.isInteger(answer)) return null
      const wrong = [...document.querySelectorAll('.opt')].find(
        (b) => Number(b.innerText) !== answer && !b.disabled,
      )
      if (!wrong) return null
      wrong.click()
      return { answer, chosen: Number(wrong.innerText) }
    })

  const missed = []
  for (let i = 0; i < 2; i++) {
    const miss = await missOnce()
    if (!miss) throw new Error(`专项冒险第 ${i + 1} 题不是可判定的算式题`)
    missed.push(miss)
    await sleep(1800)
  }

  const afterPractice = await store()
  const book = Object.values(afterPractice.wrongBook ?? {})
  if (book.length !== missed.length) {
    throw new Error(`答错 ${missed.length} 题，错题本却收了 ${book.length} 条`)
  }
  if (book.some((entry) => entry.skill !== FOCUS)) {
    throw new Error(`专项冒险记到了别的技能：${book.map((e) => e.skill).join('、')}`)
  }
  if (afterPractice.mastery?.[FOCUS] === SEED_MASTERY[FOCUS]) {
    throw new Error('答了专项题，掌握度却一点没动')
  }
  const strayed = Object.keys(afterPractice.mastery ?? {}).filter((id) => !(id in SEED_MASTERY))
  if (strayed.length) throw new Error(`专项冒险练到了别的技能：${strayed.join('、')}`)
  if (afterPractice.dailyQuest?.done || afterPractice.dailyQuest?.completedAt) {
    throw new Error(`专项练习不该占今天的打卡：${JSON.stringify(afterPractice.dailyQuest)}`)
  }

  /* ---- 三、欠下错题后，同一条推荐改走错题重练 ---- */
  await page.goto(base + `/#${ROUND10_H3_SMOKE}`, { waitUntil: 'networkidle2' })
  await sleep(800)
  const owedEntries = await readEntries()
  const owed = owedEntries.find((entry) => entry.id === FOCUS)
  if (owed?.kind !== 'wrongBook') {
    throw new Error(`欠着 ${book.length} 道错题，${FOCUS} 的落点却是 ${owed?.kind}`)
  }
  if (owed.href !== `#/progress?wrong=${FOCUS}`) {
    throw new Error(`错题重练入口应带上技能点，实际 ${owed.href}`)
  }
  if (!owed.label.includes(String(book.length))) {
    throw new Error(`入口没有说明欠着几道：「${owed.label}」`)
  }

  await page.evaluate((skill) => document.querySelector(`[data-reco-entry-skill="${skill}"]`).click(), FOCUS)
  await sleep(900)
  const atBook = await page.evaluate(() => ({
    hash: location.hash,
    filter: document.querySelector('[data-wrong-filter]')?.dataset.wrongFilter ?? '',
    shown: document.querySelectorAll('.wb-item').length,
    retryFirst: !!document.querySelector('[data-wrong-retry-first]'),
  }))
  if (atBook.hash !== `#/progress?wrong=${FOCUS}`) throw new Error(`错题入口跳到了 ${atBook.hash}`)
  if (atBook.filter !== FOCUS) throw new Error(`错题本没有按技能筛选：${atBook.filter || '空'}`)
  if (atBook.shown !== book.length) {
    throw new Error(`筛选后应列出 ${book.length} 道，实际 ${atBook.shown}`)
  }
  if (!atBook.retryFirst) throw new Error('筛选后没有「从第一道开始重练」的入口')

  // 一键重练：列表按最近错的排，打开的就是最后错的那道；答对该把它放走
  const latest = [...book].sort((a, b) => (b.lastAt ?? 0) - (a.lastAt ?? 0))[0]
  await page.evaluate(() => document.querySelector('[data-wrong-retry-first]').click())
  await sleep(400)
  const solved = await page.evaluate((answer) => {
    const opt = [...document.querySelectorAll('.wb-opt')].find(
      (b) => Number(b.innerText) === answer && !b.disabled,
    )
    if (!opt) return false
    opt.click()
    return true
  }, latest.answer)
  if (!solved) throw new Error('重练面板里没有正确选项')
  await sleep(600)
  const cleared = await page.evaluate(
    () => Object.keys(JSON.parse(localStorage.getItem('mathquest/progress') || '{}').wrongBook ?? {}).length,
  )
  if (cleared !== book.length - 1) {
    throw new Error(`重练答对后错题应剩 ${book.length - 1} 道，实际 ${cleared}`)
  }
  const stillShown = await page.evaluate(() => document.querySelectorAll('.wb-item').length)
  if (stillShown !== cleared) {
    throw new Error(`筛选下的列表应剩 ${cleared} 条，实际 ${stillShown}`)
  }

  await page.evaluate(() => document.querySelector('[data-wrong-filter-clear]').click())
  await sleep(400)
  const unfiltered = await page.evaluate(() => ({
    hash: location.hash,
    filter: !!document.querySelector('[data-wrong-filter]'),
  }))
  if (unfiltered.hash.includes('wrong=')) throw new Error(`清筛选后地址仍是 ${unfiltered.hash}`)
  if (unfiltered.filter) throw new Error('清了筛选，筛选条还在')

  await page.evaluate(() => {
    localStorage.removeItem('mathquest/settings')
    localStorage.removeItem('mathquest/progress')
  })
  return (
    `空错题本时 ${FOCUS} 落到日冒险专项（刷新不换题、不占打卡），` +
    `「${planet.id}」落回星球 ${planet.href}；欠下 ${book.length} 道错题后同一条推荐改走` +
    `错题重练，筛选列出 ${atBook.shown} 道、重练答对后剩 ${cleared} 道`
  )
})

/* ------------------------------------------------------------ 家长中心 */

/** 读口算门上的题面并算出答案；进门后题面消失，返回 null。 */
const gateSum = (page) =>
  page.evaluate(() => {
    const label = document.querySelector('label[for="parent-gate"]')?.innerText ?? ''
    const m = label.match(/(\d+)\s*\+\s*(\d+)/)
    return m ? Number(m[1]) + Number(m[2]) : null
  })

await interact('家长中心：口算门挡住孩子', '/#/parent', async (page) => {
  const sum = await gateSum(page)
  if (sum === null) throw new Error('家长中心没有口算门')

  await page.type('#parent-gate', String(sum + 7))
  await page.click('.gate-form button[type="submit"]')
  await sleep(400)
  if ((await gateSum(page)) === null) throw new Error('口算门答错也放行了')

  const retry = await gateSum(page)
  await page.type('#parent-gate', String(retry))
  await page.click('.gate-form button[type="submit"]')
  await sleep(600)
  if ((await gateSum(page)) !== null) throw new Error('答对了却没进家长中心')

  const panel = await page.evaluate(() => ({
    radar: !!document.querySelector('.radar-shape'),
    axes: document.querySelectorAll('.axis-row').length,
    sections: [...document.querySelectorAll('.panel-title')].map((h) => h.innerText.trim()),
  }))
  if (!panel.radar) throw new Error('没有渲染技能雷达')
  if (panel.axes !== 6) throw new Error(`技能雷达应有 6 根轴，实际 ${panel.axes}`)
  for (const need of ['时长提醒', '技能雷达', '错因统计', '进度备份']) {
    if (!panel.sections.some((title) => title.includes(need))) {
      throw new Error(`家长中心缺少「${need}」板块`)
    }
  }
  return `答错被拦下，答对后进入；雷达 ${panel.axes} 轴，板块 ${panel.sections.length} 个`
})

await interact('家长中心：导入 JSON 覆盖进度', '/#/parent', async (page) => {
  const dir = await mkdtemp(join(tmpdir(), 'mathquest-'))
  const file = join(dir, 'backup.json')
  await writeFile(
    file,
    JSON.stringify({
      app: 'mathquest',
      version: 1,
      progress: {
        pilotName: '备份船长',
        stars: 42,
        level: 3,
        totalAnswered: 99,
        totalCorrect: 80,
        mastery: { 'add-within-10': 0.9 },
        errorTagCounts: { carry: 5, borrow: 2 },
        daily: { '2026-01-01': { seconds: 600, answered: 12, correct: 9 } },
      },
    }),
  )

  const sum = await gateSum(page)
  await page.type('#parent-gate', String(sum))
  await page.click('.gate-form button[type="submit"]')
  await sleep(500)

  const input = await page.$('input[type="file"]')
  if (!input) throw new Error('家长中心没有导入入口')
  await input.uploadFile(file)
  await sleep(700)

  const stored = await page.evaluate(() =>
    JSON.parse(localStorage.getItem('mathquest/progress') || '{}'),
  )
  if (stored.totalAnswered !== 99 || stored.stars !== 42) {
    throw new Error(`导入没有写进 store：题数 ${stored.totalAnswered}，星星 ${stored.stars}`)
  }
  if (stored.mastery?.['add-within-10'] !== 0.9) throw new Error('导入丢了掌握度')

  const shown = await starCount(page)
  if (shown !== 42) throw new Error(`导入后顶栏星星显示 ${shown}，应为 42`)

  const rendered = await page.evaluate(() => ({
    errors: document.querySelectorAll('.error-row').length,
    text: document.body.innerText,
  }))
  if (rendered.errors !== 2) throw new Error(`错因统计应有 2 条，实际 ${rendered.errors}`)
  if (!rendered.text.includes('99')) throw new Error('累计题数没有刷新到 99')

  // 导入的是整档备份，导出必须能原样还回去
  const roundTrip = await page.evaluate(() => {
    const raw = localStorage.getItem('mathquest/progress')
    return JSON.parse(raw).errorTagCounts
  })
  if (roundTrip.carry !== 5) throw new Error('错因计数在导入后被改写')

  await page.evaluate(() => {
    const el = [...document.querySelectorAll('button')].find((b) => b.innerText.includes('导出'))
    if (el) el.click()
  })
  await sleep(300)
  return `导入 99 题 / 42 星生效，错因 ${rendered.errors} 条，顶栏星星 ${shown}`
})

/**
 * ROUND11_H3_SMOKE — 推荐 → 周计划：
 *
 * 图谱除了「今天练什么」，还得排得出「这一周怎么练」：七天逐天有功课、有理由，
 * 照着练预计过线的技能必须从后面几天里退场，把位置让给被它挡着的新技能——
 * 否则所谓周计划就只是把今天的推荐抄了七遍。欠着错题的先还账，落点走错题重练；
 * 家长中心看的是同一份计划的另一面：推荐理由与采纳痕迹。
 *
 * 全程只读：逛完计划、进过家长中心，存档必须一个字节都没动。
 */
await interact('周计划：七天滚动 + 家长侧理由与采纳痕迹', `/#${ROUND11_H3_SMOKE}`, async (page) => {
  const SEED_MASTERY = { 'count-to-5': 0.95, 'count-to-10': 0.9, 'add-within-10': 0.4 }
  const OWED = 'add-within-10'
  const SEED_BOOK = {
    'arithmetic:7+3': {
      id: 'arithmetic:7+3',
      module: 'arithmetic',
      skill: OWED,
      answer: 10,
      attempts: 2,
      lastAt: 1,
    },
  }

  const seed = (band) =>
    page.evaluate(
      (mastery, wrongBook, ageBand) => {
        localStorage.setItem(
          'mathquest/progress',
          JSON.stringify({ stars: 5, mastery, wrongBook }),
        )
        localStorage.setItem('mathquest/settings', JSON.stringify({ ageBand }))
      },
      SEED_MASTERY,
      SEED_BOOK,
      band,
    )
  const store = () =>
    page.evaluate(() => JSON.parse(localStorage.getItem('mathquest/progress') || '{}'))

  const readPlan = () =>
    page.evaluate(() => ({
      readonly: !!document.querySelector('[data-week-readonly]'),
      summary: document.querySelector('[data-week-summary]')?.innerText.replace(/\s+/g, ' ') ?? '',
      days: [...document.querySelectorAll('[data-week-day]')].map((el) => ({
        day: Number(el.dataset.weekDay),
        date: el.dataset.weekDate,
        rest: el.dataset.weekRest === '1',
        label: el.querySelector('.day-head strong')?.innerText.trim() ?? '',
        skills: [...el.querySelectorAll('[data-week-skill]')].map((row) => ({
          id: row.dataset.weekSkill,
          reason: row.dataset.weekReason,
          projected: Number(row.querySelector('[data-week-projected]')?.dataset.weekProjected ?? 0),
          text: row.innerText.replace(/\s+/g, ' ').trim(),
          pass: !!row.querySelector('[data-week-pass]'),
          entry: row.querySelector('[data-week-entry]')?.dataset.weekEntry ?? '',
          href: row.querySelector('[data-week-entry]')?.getAttribute('href') ?? '',
        })),
      })),
    }))

  await seed('L2')
  await page.reload({ waitUntil: 'networkidle2' })
  await sleep(800)

  const plan = await readPlan()
  if (!plan.days.length) throw new Error('技能图谱没有排出周计划')
  if (plan.days.length < 5) throw new Error(`周计划只排了 ${plan.days.length} 天`)
  if (!plan.readonly) throw new Error('周计划没有标明它是只读的推演')
  if (plan.days[0].label !== '今天') throw new Error(`第一天叫「${plan.days[0].label}」`)

  // 一天一格，日期得真的往后走，不能七天都是同一天
  plan.days.forEach((day, index) => {
    if (day.day !== index + 1) throw new Error(`第 ${index + 1} 格标成了第 ${day.day} 天`)
    if (index === 0) return
    const gap = Date.parse(`${day.date}T00:00:00Z`) - Date.parse(`${plan.days[index - 1].date}T00:00:00Z`)
    if (gap !== 864e5) throw new Error(`${plan.days[index - 1].date} 的下一天成了 ${day.date}`)
  })

  // 每一场功课都要有理由、有预计值；预计值必须标成预计，不能冒充成绩
  for (const day of plan.days) {
    if (!day.rest && !day.skills.length) throw new Error(`第 ${day.day} 天既不是休息日也没有功课`)
    for (const skill of day.skills) {
      if (!skill.reason) throw new Error(`第 ${day.day} 天「${skill.id}」没有推荐理由`)
      if (!(skill.projected > 0)) throw new Error(`第 ${day.day} 天「${skill.id}」没有预计掌握度`)
      if (!skill.text.includes('预计')) throw new Error(`第 ${day.day} 天「${skill.id}」没把推演值标成预计`)
    }
  }

  /* ---- 一、滚动：过了线就退场，后面的日子让给别的技能 ---- */
  const scheduled = plan.days.flatMap((day) => day.skills.map((skill) => skill.id))
  const distinct = [...new Set(scheduled)]
  if (distinct.length < 3) {
    throw new Error(`一周只排了 ${distinct.length} 个技能，等于把今天的推荐抄了七遍`)
  }
  const lastDay = plan.days.at(-1).skills.map((s) => s.id).join(',')
  if (lastDay === plan.days[0].skills.map((s) => s.id).join(',')) {
    throw new Error('第一天和最后一天排的是同一批技能，计划没有滚动')
  }
  for (const day of plan.days) {
    for (const skill of day.skills.filter((s) => s.pass)) {
      const later = plan.days.filter(
        (d) => d.day > day.day && d.skills.some((s) => s.id === skill.id),
      )
      if (later.length) {
        throw new Error(`「${skill.id}」预计第 ${day.day} 天过线，第 ${later[0].day} 天还排着`)
      }
    }
  }

  /* ---- 二、欠着错题的先还账，且只有今天的功课能一键开练 ---- */
  const first = plan.days[0].skills[0]
  if (first.id !== OWED) throw new Error(`欠着错题的技能没排在第一场，实际 ${first.id}`)
  if (first.entry !== 'wrongBook') throw new Error(`第一场的落点是 ${first.entry || '空'}`)
  if (first.href !== `#/progress?wrong=${OWED}`) throw new Error(`错题重练入口是 ${first.href}`)
  if (plan.days.slice(1).some((day) => day.skills.some((skill) => skill.entry))) {
    throw new Error('后面几天的落点还没到那天就给了按钮')
  }

  /* ---- 三、换个年龄档就该换一份计划 ---- */
  await seed('L4')
  await page.reload({ waitUntil: 'networkidle2' })
  await sleep(800)
  const high = await readPlan()
  const flatten = (view) => view.days.flatMap((day) => day.skills.map((s) => s.id)).join(',')
  if (flatten(high) === flatten(plan)) throw new Error('L2 与 L4 排出的周计划一模一样')

  /* ---- 四、家长中心：同一份计划的推荐理由与采纳痕迹 ---- */
  await seed('L2')
  // 换页只是改 hash，store 还留在内存里；必须重载一次才会读到刚写回去的档位
  await page.goto(base + '/#/parent', { waitUntil: 'networkidle2' })
  await page.reload({ waitUntil: 'networkidle2' })
  await sleep(700)
  const sum = await gateSum(page)
  if (sum === null) throw new Error('家长中心没有口算门')
  await page.type('#parent-gate', String(sum))
  await page.click('.gate-form button[type="submit"]')
  await sleep(600)

  const parent = await page.evaluate(() => ({
    panel: !!document.querySelector('[data-parent-reco]'),
    summary: document.querySelector('[data-adoption-summary]')?.innerText.replace(/\s+/g, ' ') ?? '',
    reasons: [...document.querySelectorAll('[data-reco-reason-row]')].map((el) => ({
      id: el.dataset.recoReasonRow,
      text: el.innerText.replace(/\s+/g, ' ').trim(),
    })),
    rows: [...document.querySelectorAll('[data-adoption-row]')].map((el) => ({
      id: el.dataset.adoptionRow,
      state: el.dataset.adoptionState,
      text: el.innerText.replace(/\s+/g, ' ').trim(),
    })),
  }))
  if (!parent.panel) throw new Error('家长中心没有推荐理由与采纳痕迹面板')
  if (!parent.reasons.length) throw new Error('家长中心没有列出推荐理由')
  for (const reason of parent.reasons) {
    if (!/个技能/.test(reason.text)) throw new Error(`理由「${reason.id}」没说清覆盖几个技能`)
  }
  if (parent.rows.length !== distinct.length) {
    throw new Error(`计划里 ${distinct.length} 个技能，采纳痕迹只列了 ${parent.rows.length} 行`)
  }
  for (const row of parent.rows) {
    if (!distinct.includes(row.id)) throw new Error(`采纳痕迹里混进了计划外的「${row.id}」`)
    if (!row.state) throw new Error(`「${row.id}」没有标出痕迹状态`)
    if (!/第 .* 天安排/.test(row.text)) throw new Error(`「${row.id}」没说明排在第几天`)
  }
  const owedRow = parent.rows.find((row) => row.id === OWED)
  if (owedRow?.state !== 'owed') throw new Error(`欠着错题的技能痕迹是 ${owedRow?.state}`)
  const fresh = parent.rows.filter((row) => row.state === 'untouched')
  if (!fresh.length) throw new Error('存档里没练过的技能没有被标成「还没开练」')
  if (!/查得到记录/.test(parent.summary)) throw new Error(`采纳统计没有给出总览：${parent.summary}`)

  /* ---- 五、看了一圈，存档一个字节都不该动 ---- */
  const after = await store()
  for (const [id, value] of Object.entries(SEED_MASTERY)) {
    if (after.mastery?.[id] !== value) {
      throw new Error(`周计划把「${id}」的掌握度改成了 ${after.mastery?.[id]}`)
    }
  }
  if (Object.keys(after.mastery ?? {}).length !== Object.keys(SEED_MASTERY).length) {
    throw new Error('周计划往掌握度里塞了新的技能点')
  }
  if (Object.keys(after.wrongBook ?? {}).length !== 1) throw new Error('周计划动了错题本')
  if (after.stars !== 5) throw new Error(`周计划把星星改成了 ${after.stars}`)

  await page.evaluate(() => {
    localStorage.removeItem('mathquest/settings')
    localStorage.removeItem('mathquest/progress')
  })
  return (
    `七天 ${scheduled.length} 场 ${distinct.length} 个技能（首场 ${first.id} 走 ${first.entry}），` +
    `过线即退场、换档换计划；家长侧 ${parent.reasons.length} 条理由、` +
    `${parent.rows.length} 行痕迹（${fresh.length} 个还没开练）`
  )
})

/**
 * ROUND12_H5_SMOKE — 全图谱开练 + 推荐效果度量：
 * 逐个打开 34 个节点，详情里的专项入口必须携带技能定位；再真实点击一次推荐，
 * 验证 cohort 基线落盘、家长页能读出 adoptionRate/recoLift，且导出 JSON 带同名效果字段。
 */
await interact('推荐全覆盖：34/34 可开练 + 采纳/lift 进入家长导出', `/#${ROUND12_H5_SMOKE}`, async (page) => {
  await page.evaluate(() => {
    localStorage.removeItem('mathquest/progress')
    localStorage.setItem('mathquest/settings', JSON.stringify({ ageBand: 'L5' }))
  })
  await page.reload({ waitUntil: 'networkidle2' })
  await sleep(700)

  const entries = []
  for (const skill of SKILLS) {
    await page.evaluate((id) => document.querySelector(`[data-skill-node="${id}"]`)?.click(), skill.id)
    await sleep(30)
    const entry = await page.evaluate((id) => {
      const link = document.querySelector(`[data-skill-practice-entry="${id}"]`)
      return {
        id,
        kind: link?.dataset.skillPracticeKind ?? '',
        href: link?.getAttribute('href') ?? '',
      }
    }, skill.id)
    if (!entry.href) throw new Error(`「${skill.id}」详情没有专项开练入口`)
    const queryKey = entry.kind === 'daily' ? 'focus' : 'skill'
    if (!entry.href.includes(`${queryKey}=${encodeURIComponent(skill.id)}`)) {
      throw new Error(`「${skill.id}」没有携带 ${queryKey} 定位：${entry.href}`)
    }
    entries.push(entry)
  }
  const daily = entries.filter((entry) => entry.kind === 'daily')
  const planet = entries.filter((entry) => entry.kind === 'planet')
  if (entries.length !== SKILLS.length || SKILLS.length !== 34) {
    throw new Error(`开练覆盖 ${entries.length}/${SKILLS.length}，课程表应为 34 个节点`)
  }
  if (daily.length !== 10 || planet.length !== 24) {
    throw new Error(`落点分布应为 daily 10 / planet 定位 24，实际 ${daily.length}/${planet.length}`)
  }

  // 真点一次推荐：点击前不写曝光，点击时把同批候选的掌握度冻结成 cohort 基线。
  const offered = await page.evaluate(() =>
    [...document.querySelectorAll('[data-reco-item]')].map((row) => row.dataset.recoItem),
  )
  if (offered.length < 2) throw new Error(`推荐集合只有 ${offered.length} 项，无法建立同批对照`)
  const adopted = offered[0]
  await page.evaluate((id) => document.querySelector(`[data-reco-entry-skill="${id}"]`)?.click(), adopted)
  await sleep(600)
  const cohort = await page.evaluate(() => {
    const state = JSON.parse(localStorage.getItem('mathquest/progress') || '{}')
    return state.recommendationCohorts?.[0] ?? null
  })
  if (!cohort) throw new Error('点击推荐后没有保存 cohort 基线')
  if (cohort.offered.length !== offered.length || cohort.adopted?.[0]?.skill !== adopted) {
    throw new Error(`推荐 cohort 不完整：${JSON.stringify(cohort)}`)
  }

  // 模拟后续练习留下的掌握度变化；页面重载后必须从同一份本地 cohort 计算效果。
  await page.evaluate((picked) => {
    const state = JSON.parse(localStorage.getItem('mathquest/progress') || '{}')
    const offeredRows = state.recommendationCohorts[0].offered
    state.mastery = { ...(state.mastery ?? {}), [picked]: 0.45 }
    const control = offeredRows.find((row) => row.skill !== picked)?.skill
    if (control) state.mastery[control] = 0.1
    const priorAt = Date.now() - 864e5
    state.recommendationMetricHistory = [
      {
        date: new Date(priorAt).toISOString().slice(0, 10),
        recordedAt: priorAt,
        cohorts: 1,
        offers: offeredRows.length,
        adoptions: 1,
        controls: offeredRows.length - 1,
        adoptionRate: Math.round((1000 / offeredRows.length)) / 10,
        recoLift: 4,
        status: 'insufficient',
      },
    ]
    localStorage.setItem('mathquest/progress', JSON.stringify(state))
  }, adopted)

  await page.goto(base + `/#${ROUND13_H5_SMOKE}`, { waitUntil: 'networkidle2' })
  await page.reload({ waitUntil: 'networkidle2' })
  await sleep(500)
  const sum = await gateSum(page)
  if (sum === null) throw new Error('家长中心没有口算门')
  await page.type('#parent-gate', String(sum))
  await page.click('.gate-form button[type="submit"]')
  await sleep(500)

  const metrics = await page.evaluate(() => {
    const el = document.querySelector('[data-reco-metrics]')
    return {
      adoptionRate: Number(el?.dataset.adoptionRate),
      recoLift: Number(el?.dataset.recoLift),
      status: el?.dataset.recoStatus ?? '',
      definition: document.querySelector('[data-reco-metric-definition]')?.innerText ?? '',
      trend: [...document.querySelectorAll('[data-reco-trend-point]')].map((point) => ({
        date: point.dataset.recoTrendDate,
        adoptionRate: Number(point.dataset.recoTrendAdoptionRate),
        recoLift: Number(point.dataset.recoTrendLift),
      })),
    }
  })
  if (!(metrics.adoptionRate > 0) || !(metrics.recoLift > 0)) {
    throw new Error(`家长页度量无效：${JSON.stringify(metrics)}`)
  }
  if (!metrics.definition.includes('recommendationEffect')) {
    throw new Error('家长页没有说明效果度量会进入导出')
  }
  if (metrics.trend.length !== 2 || metrics.trend.at(-1)?.recoLift !== metrics.recoLift) {
    throw new Error(`ROUND13 准实验趋势没有保留历史并刷新今日点：${JSON.stringify(metrics.trend)}`)
  }

  // 截获“导出进度”生成的 Blob，验证不是只在页面上画了两个数字。
  await page.evaluate(() => {
    window.__round12Export = ''
    const create = URL.createObjectURL.bind(URL)
    URL.createObjectURL = (blob) => {
      blob.text().then((value) => {
        window.__round12Export = value
      })
      return create(blob)
    }
  })
  await page.evaluate(() => {
    const button = [...document.querySelectorAll('button')].find((el) => el.innerText.includes('导出进度'))
    button?.click()
  })
  await page.waitForFunction(() => window.__round12Export.length > 0, { timeout: 5000 })
  const exported = await page.evaluate(() => JSON.parse(window.__round12Export))
  if (exported.recommendationEffect?.recoLift !== metrics.recoLift) {
    throw new Error(`导出 recoLift=${exported.recommendationEffect?.recoLift}，页面=${metrics.recoLift}`)
  }
  if (!Array.isArray(exported.progress?.recommendationCohorts)) {
    throw new Error('整档导出没有保留 recommendationCohorts')
  }
  if (
    !Array.isArray(exported.recommendationTrend) ||
    exported.recommendationTrend.length !== metrics.trend.length ||
    exported.recommendationTrend.at(-1)?.recoLift !== metrics.recoLift
  ) {
    throw new Error(`导出 recommendationTrend 与家长页不一致：${JSON.stringify(exported)}`)
  }

  await page.evaluate(() => {
    localStorage.removeItem('mathquest/settings')
    localStorage.removeItem('mathquest/progress')
  })
  return (
    `${entries.length}/${SKILLS.length} 节点可开练（daily ${daily.length} + 定位 ${planet.length}）；` +
    `点击 ${adopted} 后采纳率 ${metrics.adoptionRate}%、recoLift +${metrics.recoLift}pp，` +
    `家长页/导出保留 ${metrics.trend.length} 日准实验趋势`
  )
})

await browser.close()
server.close()

/* ------------------------------------------------------------------ 输出 */
console.log('\n路由渲染：')
for (const r of rows) {
  console.log(`  ${r.issues ? '✗' : '✓'} ${r.name.padEnd(14)} ${r.path.padEnd(24)} ${r.chars} 字`)
}

console.log('\n交互：')
for (const i of inter) {
  console.log(`  ${i.ok ? '✓' : '✗'} ${i.label} — ${i.note}`)
  i.errs.slice(0, 3).forEach((e) => console.log(`      ! ${e}`))
}

if (problems.length) {
  console.log('\n问题明细：')
  for (const p of problems) {
    console.log(`  ${p.name} (${p.path})`)
    p.found.slice(0, 6).forEach((f) => console.log(`    - ${f}`))
  }
}

const failed = problems.length + inter.filter((i) => !i.ok).length
if (ANDROID_SIM_UA && observedUserAgent === ANDROID_SIM_UA) {
  console.log(`[ROUND13_H6] WebView UA smoke PASS: ${observedUserAgent}`)
}
console.log(`\n共 ${ROUTES.length} 条路由 + ${inter.length} 项交互，${failed} 项有问题。`)
process.exit(failed ? 1 : 0)
