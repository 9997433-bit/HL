/**
 * 冒烟测试：用无头 Chrome 把 dist 里的每条路由都走一遍，
 * 收集控制台报错、未捕获异常和 Vue 警告，并把每个玩法真的玩几题。
 *
 * 用法：npm run build && node scripts/smoke.mjs
 */

import { createServer } from 'node:http'
import { readFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
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
async function waitForChoice(page, timeout = 5000) {
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
  const hasKeypad = await page.evaluate(() => {
    const toggle = [...document.querySelectorAll('button')].find((b) => /键盘|输入/.test(b.innerText))
    if (toggle) toggle.click()
    return !!document.querySelector('.key')
  })
  await sleep(400)
  const typed = await page.evaluate(() => {
    const keys = [...document.querySelectorAll('.key')]
    const digit = keys.find((k) => /^\d$/.test(k.innerText.trim()))
    if (!digit) return false
    digit.click()
    return true
  })
  await sleep(300)
  return `切到键盘=${hasKeypad}，按键可用=${typed}`
})

await interact('数独空间站：填格 + 提示直到完成', '/#/sudoku', async (page) => {
  const cells = await page.evaluate(() => document.querySelectorAll('.cell').length)
  const filled = await page.evaluate(() => {
    const empty = [...document.querySelectorAll('.cell')].find((c) => !c.innerText.trim())
    if (!empty) return false
    empty.click()
    const pad = [...document.querySelectorAll('.pad-key, .pad button, .num-key')].find(
      (b) => !b.disabled,
    )
    if (!pad) return false
    pad.click()
    return true
  })
  await sleep(500)

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
  await playChoiceModule(page, 4)
  const before = await starCount(page)
  await page.goto(base + '/#/', { waitUntil: 'networkidle2' })
  await page.reload({ waitUntil: 'networkidle2' })
  await sleep(700)
  const after = await starCount(page)
  if (before > 0 && after !== before) throw new Error(`刷新后星星从 ${before} 变成 ${after}`)
  return `刷新前 ${before} 星，刷新后 ${after} 星`
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
