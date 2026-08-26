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
  ['数量星云', '/#/number-sense'],
  ['算术恒星', '/#/arithmetic'],
  ['形状卫星', '/#/geometry'],
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
