/**
 * Round 19 H6 · 走查证据包截图机。
 *
 * R19 四类场景：全库富玩抽查、精美舞台、剖析播放器、周报或学伴。
 * 编排启动基线时 H2–H5 功能可能尚未合入——脚本如实拍当下 UI，
 * 并把「未齐」写进 caption / meta，不伪造绿勾。
 *
 * 用法：
 *   PREVIEW_LITERACY=http://127.0.0.1:4173 PREVIEW_MATH=http://127.0.0.1:4174 \
 *     npm run walkthrough:shots:r19
 *   或先 npm run build，再 npm run walkthrough:shots:r19（自挂静态服）
 */

import { createServer } from 'node:http'
import { constants } from 'node:fs'
import { access, mkdir, readFile, stat, writeFile } from 'node:fs/promises'
import { extname, resolve, sep } from 'node:path'
import puppeteer from 'puppeteer-core'

const ROOT = resolve(import.meta.dirname, '..')
const OUT_DIR = resolve(ROOT, '.agent_workspace/evidence/r19')
const DISTS = {
  literacy: resolve(ROOT, 'apps/literacy-app/dist'),
  math: resolve(ROOT, 'apps/math-app/dist'),
}

const MIME = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.mp3': 'audio/mpeg',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.webmanifest': 'application/manifest+json',
  '.woff2': 'font/woff2',
}

const wait = (ms) => new Promise((done) => setTimeout(done, ms))

async function loadLiteracyData() {
  const { register } = await import('node:module')
  register('./alias-loader.mjs', import.meta.url)
  const { CHAR_INDEX } = await import(resolve(ROOT, 'apps/literacy-app/src/data/char-index.js'))
  const play = await import(resolve(ROOT, 'apps/literacy-app/src/data/char-play.js'))
  if (typeof play.loadAllRichPlays === 'function') await play.loadAllRichPlays()
  return { CHAR_INDEX, play }
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

function serve(dist) {
  return createServer(async (request, response) => {
    try {
      const pathname = decodeURIComponent(new URL(request.url, 'http://local/').pathname)
      let file = resolve(dist, pathname.replace(/^\/+/, '') || 'index.html')
      if (file !== dist && !file.startsWith(`${dist}${sep}`)) file = resolve(dist, 'index.html')
      if (!(await stat(file).catch(() => null))?.isFile()) file = resolve(dist, 'index.html')
      response.writeHead(200, {
        'cache-control': 'no-store',
        'content-type': MIME[extname(file)] ?? 'application/octet-stream',
      })
      response.end(await readFile(file))
    } catch (error) {
      response.writeHead(500, { 'content-type': 'text/plain; charset=utf-8' })
      response.end(String(error))
    }
  })
}

async function listen(dist) {
  const server = serve(dist)
  await new Promise((done) => server.listen(0, '127.0.0.1', done))
  return { server, base: `http://127.0.0.1:${server.address().port}` }
}

async function clickText(page, needle) {
  const hit = await page.evaluate((text) => {
    const el = [...document.querySelectorAll('button, a')].find((node) =>
      node.innerText.replace(/\s+/g, '').includes(text),
    )
    if (!el) return false
    el.click()
    return true
  }, needle)
  if (hit) await wait(350)
  return hit
}

async function answerRound(page, rounds, { deliberateWrong = false } = {}) {
  let answered = 0
  for (let i = 0; i < rounds; i += 1) {
    const ready = await page
      .waitForFunction(
        () =>
          document.querySelector('.opt:not([disabled])') ||
          document.querySelector('.key:not([disabled])'),
        { timeout: 12_000 },
      )
      .then(() => true)
      .catch(() => false)
    if (!ready) break

    const ok = await page.evaluate((wrong) => {
      const opts = [...document.querySelectorAll('.opt:not([disabled])')]
      if (opts.length) {
        ;(wrong ? opts[opts.length - 1] : opts[0]).click()
        return true
      }
      const keys = [...document.querySelectorAll('.key:not([disabled])')]
      const digit = keys.find((k) => k.textContent.trim() === (wrong ? '9' : '1'))
      const submit = keys.find((k) => k.textContent.trim() === '确定')
      if (digit && submit) {
        digit.click()
        submit.click()
        return true
      }
      return false
    }, deliberateWrong)
    if (!ok) break
    answered += 1
    await wait(1500)
  }
  return answered
}

async function openParentGate(page) {
  const solved = await page.evaluate(() => {
    const label = document.body.innerText.match(/(\d+)\s*\+\s*(\d+)/)
    const input = document.querySelector('input[type="number"]')
    if (!label || !input) return false
    const setter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype,
      'value',
    ).set
    setter.call(input, String(Number(label[1]) + Number(label[2])))
    input.dispatchEvent(new Event('input', { bubbles: true }))
    return true
  })
  if (!solved) throw new Error('家长中心没有出现口算门')
  await clickText(page, '进入')
  await wait(600)
}

const shots = []

async function shoot(target, name, caption) {
  const file = resolve(OUT_DIR, name)
  await target.screenshot({ path: file, captureBeyondViewport: false })
  const size = (await stat(file)).size
  shots.push({ name, caption, bytes: size })
  console.log(`  📸 ${name}（${(size / 1024).toFixed(0)} KB）— ${caption}`)
}

async function shootElement(page, selector, name, caption) {
  const handle = await page.waitForSelector(selector, { timeout: 15_000 })
  await handle.evaluate((el) => el.scrollIntoView({ block: 'center' }))
  await wait(400)
  await shoot(handle, name, typeof caption === 'function' ? await caption() : caption)
}

async function shootPanel(browser, name, caption, { title, subtitle, rows, note }) {
  const page = await browser.newPage()
  await page.setViewport({ width: 900, height: 200, deviceScaleFactor: 2 })
  await page.setContent(
    `<!doctype html><meta charset="utf-8"><style>
      :root { color-scheme: light }
      body { margin: 0; padding: 24px; font: 15px/1.6 "Noto Sans CJK SC", "Source Han Sans", sans-serif;
             background: #f6f7fb; color: #1c2333 }
      h1 { margin: 0 0 4px; font-size: 20px }
      p.sub { margin: 0 0 16px; color: #5b6478; font-size: 13px }
      table { border-collapse: collapse; width: 100%; background: #fff; border-radius: 10px; overflow: hidden;
              box-shadow: 0 1px 3px rgba(20,30,60,.12) }
      th, td { padding: 8px 12px; text-align: left; border-bottom: 1px solid #eceff5; font-variant-numeric: tabular-nums }
      th { background: #eef1f8; font-weight: 600; font-size: 13px; color: #33405c }
      tr:last-child td { border-bottom: none }
      td.num { text-align: right }
      tr.total td { font-weight: 700; background: #fbfcff }
      p.note { margin: 14px 0 0; font-size: 13px; color: #5b6478 }
    </style>
    <h1>${title}</h1><p class="sub">${subtitle}</p>
    <table><thead><tr>${rows[0].map((c) => `<th>${c}</th>`).join('')}</tr></thead><tbody>
    ${rows
      .slice(1)
      .map(
        (r) =>
          `<tr class="${String(r[0]).startsWith('合计') || String(r[0]).startsWith('距') ? 'total' : ''}">` +
          r.map((c, i) => `<td class="${i ? 'num' : ''}">${c}</td>`).join('') +
          '</tr>',
      )
      .join('')}
    </tbody></table>${note ? `<p class="note">${note}</p>` : ''}`,
    { waitUntil: 'load' },
  )
  await wait(300)
  const height = await page.evaluate(() => document.body.scrollHeight + 24)
  await page.setViewport({ width: 900, height, deviceScaleFactor: 2 })
  await wait(200)
  await shoot(page, name, caption)
  await page.close()
}

/* -------------------------------------------------------------- 走查场景 */

/** ① 全库富玩抽查：手写富脚本关 + 覆盖率实测面板（R19 H2 目标 ≥1820）。 */
async function sceneRichSpot(browser, base) {
  console.log('\n① 全库富玩抽查')
  const { CHAR_INDEX, play } = await loadLiteracyData()
  const rich = CHAR_INDEX.filter((c) => play.hasRichPlay(c.char))
  const plain = CHAR_INDEX.filter((c) => !play.hasRichPlay(c.char))
  const plays = play.countRichPlays()
  const coverage = play.richPlayCoverage()
  const goal = 1820
  const gap = Math.max(0, goal - plays)
  console.log(`  富脚本 ${plays} / 字表 ${CHAR_INDEX.length}；距 R19 H2 全库差 ${gap}`)
  if (!rich.length) throw new Error('字表里一个富脚本都没有')

  const page = await browser.newPage()
  await page.setViewport({ width: 460, height: 940, deviceScaleFactor: 2 })

  const richChar = (rich.find((c) => c.unit >= 40) ?? rich[rich.length - 1]).char
  await page.goto(`${base}/#/learn/${encodeURIComponent(richChar)}`, {
    waitUntil: 'networkidle2',
    timeout: 30_000,
  })
  await page.evaluate(() => localStorage.clear())
  await page.reload({ waitUntil: 'networkidle2', timeout: 30_000 })
  await page.waitForSelector('.page.detail', { timeout: 15_000 })
  await page.click('.rail__step[data-step="play"]').catch(() => {})
  await page.waitForSelector('[data-char-play]', { timeout: 15_000 })
  await wait(1200)
  const one = await page.$eval('[data-char-play]', (el) => ({
    template: el.dataset.playTemplate,
    fallback: el.dataset.fallback,
    narration: el.querySelector('.play__narration')?.textContent.trim() ?? '',
  }))
  if (one.fallback !== 'false') throw new Error(`「${richChar}」不是手写富脚本关`)

  await shootElement(
    page,
    '[data-panel="play"]',
    'r19-01-rich-spot.png',
    `全库富玩抽查：手写关「${richChar}」（template=${one.template}、fallback=${one.fallback}），` +
      `旁白「${one.narration}」——库内富脚本 ${plays}/${CHAR_INDEX.length}` +
      (gap > 0 ? `，距 H2 全库还差 ${gap}（未齐）` : '，已达全库'),
  )
  await page.close()

  await shootPanel(
    browser,
    'r19-02-rich-coverage.png',
    `全库富玩覆盖率实测：${plays}/${CHAR_INDEX.length}（R19 H2 阈值 ≥${goal}）` +
      (gap > 0 ? ` · 未齐，差 ${gap}` : ' · 已齐'),
    {
      title: '全库富 Play 覆盖 · 走查实测',
      subtitle: `口径 countRichPlays() / CHAR_INDEX · ${new Date().toISOString()}`,
      rows: [
        ['指标', '数值', '备注'],
        ['字表规模', CHAR_INDEX.length, 'CHAR_INDEX'],
        ['手写富脚本', plays, 'hasRichPlay=true'],
        ['旁白去重', coverage.narrations ?? '—', 'richPlayCoverage().narrations'],
        ['模板回填缺口', plain.length, '仍吃 fallback 的字'],
        ['距 R19 H2（≥1820）', gap === 0 ? '已达标' : `差 ${gap}`, gap ? '功能未齐' : '齐'],
      ],
      note:
        gap > 0
          ? `编排启动基线：R19 H2「全库富 Play ≥1820」尚未合入。本包抽查的是现网 ${plays} 条手写关；` +
            `缺口 ${plain.length} 字仍走模板回填（样本起自「${plain[0]?.char ?? '—'}」）。`
          : '全库手写富脚本已齐，抽查样本代表全表。',
    },
  )

  return {
    richChar,
    template: one.template,
    plays,
    chars: CHAR_INDEX.length,
    narrations: coverage.narrations,
    plainLeft: plain.length,
    h2Gap: gap,
    h2Ready: gap === 0,
  }
}

/**
 * ② 精美舞台：锁定玩关舞台面板（R19 H3 精美度升级未合入时拍基线舞台）。
 */
async function scenePolishStage(browser, base) {
  console.log('\n② 精美舞台')
  const { CHAR_INDEX, play } = await loadLiteracyData()
  const rich = CHAR_INDEX.filter((c) => play.hasRichPlay(c.char))
  // 挑 swipe-motion：舞台上有可推的马，精美度看道具与动效最直观
  const char = (rich.find((c) => c.char === '驰') || rich.find((c) => c.unit >= 40) || rich[rich.length - 1])
    .char

  const page = await browser.newPage()
  await page.setViewport({ width: 460, height: 940, deviceScaleFactor: 2 })
  await page.goto(`${base}/#/learn/${encodeURIComponent(char)}`, {
    waitUntil: 'networkidle2',
    timeout: 30_000,
  })
  await page.evaluate(() => localStorage.clear())
  await page.reload({ waitUntil: 'networkidle2', timeout: 30_000 })
  await page.waitForSelector('.page.detail', { timeout: 15_000 })
  await page.click('.rail__step[data-step="play"]').catch(() => {})
  await page.waitForSelector('[data-char-play]', { timeout: 15_000 })
  await wait(1000)

  // 把玩关面板滚到视口中央，再推一下道具让舞台有状态
  await page.$eval('[data-panel="play"]', (el) => el.scrollIntoView({ block: 'center' }))
  await wait(400)
  await page.evaluate(() => {
    const btn = [...document.querySelectorAll('[data-char-play] button')].find((b) =>
      /往右|推|划/.test(b.innerText),
    )
    btn?.click()
  }).catch(() => {})
  await wait(700)

  const meta = await page.$eval('[data-char-play]', (el) => ({
    template: el.dataset.playTemplate,
    fallback: el.dataset.fallback,
    state: el.dataset.state,
    narration: el.querySelector('.play__narration')?.textContent.trim() ?? '',
    progress: el.innerText.match(/已往右\s*\d+\s*\/\s*\d+/)?.[0] ?? '',
  }))

  await shootElement(
    page,
    '[data-panel="play"]',
    'r19-03-polish-stage.png',
    `精美舞台基线：「${char}」玩关舞台（template=${meta.template}、state=${meta.state}` +
      `${meta.progress ? `、${meta.progress}` : ''}）。` +
      'R19 H3 精美度升级尚未合入——拍的是编排启动时的舞台外观（未齐）。',
  )
  await page.close()
  return { char, ...meta, h3Ready: false }
}

/** ③ 剖析播放器：现有剖析面板（R19 H4 视频级播放器未合入时拍静态面板）。 */
async function sceneAnalysisPlayer(browser, base) {
  console.log('\n③ 剖析播放器')
  const page = await browser.newPage()
  await page.setViewport({ width: 900, height: 1250, deviceScaleFactor: 2 })
  await page.goto(`${base}/#/word-problems`, { waitUntil: 'networkidle2', timeout: 30_000 })
  await page.waitForSelector('.analysis-open', { timeout: 15_000 })
  await page.click('.analysis-open')
  await page.waitForSelector('[data-analysis]', { timeout: 15_000 })
  await wait(600)

  const unfolded = await clickText(page, '全部摊开')
  await clickText(page, '看一道同结构的变式')
  await wait(800)

  const shown = await page.$eval(
    '[data-analysis] .steps',
    (ol) => ol.querySelectorAll('.step').length,
  )
  const playerBits = await page.evaluate(() => {
    const root = document.querySelector('[data-analysis]')
    if (!root) return { hasVideo: false, hasTimeline: false, hasPlayBtn: false }
    const text = root.innerText
    return {
      hasVideo: Boolean(root.querySelector('video')),
      hasTimeline: /时间轴|播放进度|timeline/i.test(text + root.className),
      hasPlayBtn: [...root.querySelectorAll('button')].some((b) =>
        /播放|暂停|▶|❚❚/.test(b.innerText),
      ),
      skippable: Boolean(
        [...root.querySelectorAll('button')].find((b) => /跳过|✕|关闭/.test(b.innerText)),
      ),
    }
  })

  const videoReady = playerBits.hasVideo || playerBits.hasTimeline
  await shootElement(
    page,
    '[data-analysis]',
    'r19-04-analysis-player.png',
    `剖析播放器：图示 + 分步（摊开 ${shown} 步` +
      `${unfolded ? '，点过全部摊开' : ''}）+ 变式。` +
      (videoReady
        ? '已检出视频/时间轴控件。'
        : '未检出 <video>/时间轴——R19 H4 视频级播放器尚未合入，拍的是静态剖析面板（未齐）。'),
  )

  const done = await answerRound(page, 8, { deliberateWrong: true })
  console.log(`  ↳ 剖析后继续作答 ${done} 题，落进本机存档供周报`)
  // 不关 page——周报要共用上下文；由调用方关闭
  return {
    page,
    shownSteps: shown,
    answered: done,
    playerBits,
    h4Ready: videoReady,
  }
}

/** ④ 周报：读本次走查答出来的存档。 */
async function sceneParentWeekly(browser, base, sharedPage) {
  console.log('\n④ 家长周报')
  const page = sharedPage || (await browser.newPage())
  if (!sharedPage) {
    await page.setViewport({ width: 760, height: 1100, deviceScaleFactor: 2 })
  } else {
    await page.setViewport({ width: 760, height: 1100, deviceScaleFactor: 2 })
  }
  await page.goto(`${base}/#/parent`, { waitUntil: 'networkidle2', timeout: 30_000 })
  await wait(600)
  await openParentGate(page)
  const meta = await page.$eval('[data-weekly-report]', (el) => ({
    weakness: el.dataset.weakness,
    headline: el.querySelector('[data-weekly-headline]')?.textContent.trim() ?? '',
  }))
  await shootElement(
    page,
    '[data-weekly-report]',
    'r19-05-math-parent-weekly.png',
    `数学家长周报：弱项 ${meta.weakness} —— ${meta.headline}`,
  )
  await page.close()
  return meta
}

/** ④b 学伴（周报之外的备选覆盖）。 */
async function sceneMascot(browser, base) {
  console.log('\n④b 学伴')
  const page = await browser.newPage()
  await page.setViewport({ width: 460, height: 940, deviceScaleFactor: 2 })
  await page.goto(`${base}/#/`, { waitUntil: 'networkidle2', timeout: 30_000 })
  await page.waitForSelector('.mascot', { timeout: 15_000 })
  await page.click('.mascot__btn').catch(() => {})
  await wait(900)
  const say = await page
    .$eval('.mascot__bubble', (el) => el.innerText.replace(/\s+/g, ' ').trim())
    .catch(() => '')
  await shootElement(
    page,
    '.mascot',
    'r19-06-literacy-mascot.png',
    `识字学伴气泡「${say.slice(0, 60)}」`,
  )
  await page.close()
  return { say }
}

/* ------------------------------------------------------------------ 主流程 */

async function resolveBases() {
  const previewLit = process.env.PREVIEW_LITERACY
  const previewMath = process.env.PREVIEW_MATH
  if (previewLit && previewMath) {
    console.log(`使用 preview：识字 ${previewLit} · 数学 ${previewMath}`)
    return {
      literacy: { base: previewLit, server: null },
      math: { base: previewMath, server: null },
    }
  }
  for (const [app, dist] of Object.entries(DISTS)) {
    if (!(await stat(resolve(dist, 'index.html')).catch(() => null))?.isFile()) {
      console.error(
        `walkthrough-shots-r19: 缺少 ${app} dist，且未设 PREVIEW_*；请 npm run build 或接 :4173/:4174。`,
      )
      process.exit(1)
    }
  }
  return {
    literacy: await listen(DISTS.literacy),
    math: await listen(DISTS.math),
  }
}

await mkdir(OUT_DIR, { recursive: true })

const bases = await resolveBases()
const browser = await puppeteer.launch({
  executablePath: await findChrome(),
  headless: 'new',
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--mute-audio', '--font-render-hinting=none'],
})

const only = process.argv.slice(2)
const want = (id) => only.length === 0 || only.includes(id)
const meta = {}
const failures = []

const run = async (id, label, fn) => {
  if (!want(id)) return
  try {
    meta[id] = await fn()
  } catch (error) {
    failures.push(`${label}：${error.message}`)
    console.error(`\n✗ ${label} 中断：${error.message}`)
  }
}

await run('rich-spot', '全库富玩抽查', () => sceneRichSpot(browser, bases.literacy.base))
await run('polish-stage', '精美舞台', () => scenePolishStage(browser, bases.literacy.base))

let analysisPage = null
await run('analysis-player', '剖析播放器', async () => {
  const result = await sceneAnalysisPlayer(browser, bases.math.base)
  analysisPage = result.page
  const { page: _page, ...rest } = result
  return rest
})

await run('parent-weekly', '家长周报', async () => {
  // 共用剖析那一幕的浏览器上下文（localStorage）
  if (analysisPage) {
    return sceneParentWeekly(browser, bases.math.base, analysisPage)
  }
  return sceneParentWeekly(browser, bases.math.base, null)
})

await run('mascot', '学伴', () => sceneMascot(browser, bases.literacy.base))

await browser.close()
if (bases.literacy.server) await new Promise((done) => bases.literacy.server.close(done))
if (bases.math.server) await new Promise((done) => bases.math.server.close(done))

await writeFile(
  resolve(OUT_DIR, 'walkthrough-shots.json'),
  `${JSON.stringify(
    {
      round: 19,
      generatedAt: new Date().toISOString(),
      chrome: await findChrome(),
      node: process.version,
      preview: {
        literacy: process.env.PREVIEW_LITERACY || null,
        math: process.env.PREVIEW_MATH || null,
      },
      tree: 'cursor/r19-walkthrough-bundle-9f67 ← origin/cursor/r19-orchestration-9f67',
      shots,
      meta,
      failures,
    },
    null,
    2,
  )}\n`,
)

console.log(`\n共落盘 ${shots.length} 张截图到 .agent_workspace/evidence/r19/`)
if (failures.length) console.log(`未完成的幕：${failures.length} —— ${failures.join('；')}`)
process.exit(failures.length === 0 && shots.length >= 4 ? 0 : 1)
