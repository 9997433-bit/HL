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
  ['数独空间站', '/#/sudoku'],
  ['生活行星', '/#/word-problems'],
  ['成就墙', '/#/progress'],
  ['家长中心', '/#/parent'],
  ['未知路由回落', '/#/nope/nope'],
]

const IGNORE = [/Failed to load resource/i, /net::ERR_/i, /favicon/i, /AudioContext/i]

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: 'new',
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--mute-audio'],
})

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const problems = []
const rows = []

async function newPage(collect) {
  const page = await browser.newPage()
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
      }
    })

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
  if (bank < 25) throw new Error(`母题只有 ${bank} 类，少于要求的 25 类`)

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
console.log(`\n共 ${ROUTES.length} 条路由 + ${inter.length} 项交互，${failed} 项有问题。`)
process.exit(failed ? 1 : 0)
