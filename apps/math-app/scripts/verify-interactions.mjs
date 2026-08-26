/**
 * 针对性验证共享冒烟测试里报告存疑的两处核心交互：
 *  1. 数独：选中空格 → 点数字键，数字是否真的落进格子
 *  2. 算术：切到键盘输入模式后，能否用数字键盘作答
 * 用法：node scripts/verify-interactions.mjs [baseUrl]
 */
import puppeteer from 'puppeteer-core'

const BASE = process.argv[2] ?? 'http://localhost:4183'
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const results = []
const check = (name, ok, detail) => {
  results.push({ name, ok, detail })
  console.log(`${ok ? '✓' : '✗'} ${name} — ${detail}`)
}

const browser = await puppeteer.launch({
  executablePath: process.env.CHROME_PATH ?? '/usr/local/bin/google-chrome',
  headless: 'new',
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--mute-audio'],
})
const page = await browser.newPage()
await page.setViewport({ width: 1280, height: 900 })
const errors = []
page.on('pageerror', (e) => errors.push(e.message))

// ---------- 数独：真正往空格里填数 ----------
await page.goto(`${BASE}/#/sudoku`, { waitUntil: 'networkidle2' })
await sleep(900)

const emptyIdx = await page.evaluate(
  () => [...document.querySelectorAll('.cell')].findIndex((c) => !c.innerText.trim()),
)
check('数独有空格可填', emptyIdx >= 0, `第一个空格下标 ${emptyIdx}`)

await page.evaluate((i) => document.querySelectorAll('.cell')[i].click(), emptyIdx)
await sleep(300)
const selected = await page.evaluate(
  (i) => document.querySelectorAll('.cell')[i].classList.contains('sel'),
  emptyIdx,
)
check('点击空格能选中', selected, `cell[${emptyIdx}] 带 .sel`)

const padEnabled = await page.evaluate(
  () => [...document.querySelectorAll('.numkey')].filter((b) => !b.disabled).length,
)
check('选中后数字键可用', padEnabled >= 4, `${padEnabled} 个键可用`)

// 依次试 1-4，冲突的会被红框标记但仍会落格，取第一个能落进去的
await page.evaluate(() => document.querySelectorAll('.numkey')[0].click())
await sleep(400)
const filled = await page.evaluate(
  (i) => document.querySelectorAll('.cell')[i].innerText.trim(),
  emptyIdx,
)
check('点数字键后格子显示数字', filled === '1', `格子内容 "${filled}"`)

// 再点同一个数字应当取消填入
await page.evaluate(() => document.querySelectorAll('.numkey')[0].click())
await sleep(400)
const cleared = await page.evaluate(
  (i) => document.querySelectorAll('.cell')[i].innerText.trim(),
  emptyIdx,
)
check('再点同一数字可取消', cleared === '', `格子内容 "${cleared}"`)

// 键盘输入
await page.evaluate((i) => document.querySelectorAll('.cell')[i].click(), emptyIdx)
await page.keyboard.press('2')
await sleep(400)
const viaKeyboard = await page.evaluate(
  (i) => document.querySelectorAll('.cell')[i].innerText.trim(),
  emptyIdx,
)
check('键盘数字键也能填', viaKeyboard === '2', `格子内容 "${viaKeyboard}"`)

// ---------- 算术：键盘输入模式 ----------
await page.goto(`${BASE}/#/arithmetic`, { waitUntil: 'networkidle2' })
await sleep(900)

const toggled = await page.evaluate(() => {
  const btn = [...document.querySelectorAll('button')].find((b) => /改为输入/.test(b.innerText))
  if (!btn) return '找不到切换按钮'
  btn.click()
  return 'clicked'
})
await sleep(600)
const keypadShown = await page.evaluate(() => document.querySelectorAll('.key').length)
check('能切换到键盘输入模式', keypadShown >= 12, `${toggled}，出现 ${keypadShown} 个按键`)

const answer = await page.evaluate(() => {
  const t = [...document.querySelectorAll('.term')].map((e) => Number(e.innerText))
  const sign = document.querySelector('.sign')?.innerText
  return sign === '+' ? t[0] + t[1] : t[0] - t[1]
})
for (const ch of String(answer)) {
  await page.evaluate((d) => {
    const k = [...document.querySelectorAll('.key')].find((b) => b.innerText.trim() === d)
    k?.click()
  }, ch)
  await sleep(150)
}
const slotText = await page.evaluate(() => document.querySelector('.slot')?.innerText.trim())
check('数字键能输入到答题框', slotText === String(answer), `框内 "${slotText}"，应为 ${answer}`)

await page.evaluate(() => {
  const ok = [...document.querySelectorAll('.key')].find((b) => /确定/.test(b.innerText))
  ok?.click()
})
await sleep(1200)
const marked = await page.evaluate(() => document.querySelectorAll('.dot.ok').length)
check('提交正确答案被判对', marked >= 1, `进度条上有 ${marked} 个绿点`)

check('全程无未捕获异常', errors.length === 0, errors.join(' | ') || '无')

await browser.close()
const failed = results.filter((r) => !r.ok)
console.log(`\n${results.length - failed.length}/${results.length} 项通过`)
process.exit(failed.length ? 1 : 0)
