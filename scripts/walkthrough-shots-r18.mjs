/**
 * Round 18 H6 · 走查证据包的截图机。
 *
 * R17 的 walkthrough-shots.mjs 拍的是「认步 / 学演示 / 剖析 / 周报」四条路径；
 * R18 换了四张牌：富玩、拆包后的单字关键路径、剖析步数对齐、周报与学伴。
 * 这个脚本把两个 App 的 dist 各挂一台静态服务，用真 Chrome 走一遍，
 * 每到一个值得看的画面就落一张 PNG 到 .agent_workspace/evidence/r18/：
 *
 *   ① 富玩       手写富脚本的「玩」这一关（data-fallback=false）
 *   ② 富玩缺口   仍吃模板回填的字（data-fallback=true）—— R18 H2 要翻的就是这批
 *   ③ 单字首屏   单字详情页本身
 *   ④ 拆包实测   打开单字详情时**真的**下载了哪些 JS 分片、各多少字节
 *   ⑤ 剖析       应用题剖析面板（图示 + 分步 + 变式）
 *   ⑥ 步数对齐   全库 template.steps 与 buildAnalysis().steps.length 的一致率实测
 *   ⑦ 家长周报   数学家长中心的周报卡片（读的是本次走查自己答出来的存档）
 *   ⑧ 学伴       识字侧学伴气泡
 *
 * ④⑥ 两张是**实测面板**：数字由本进程当场量出来（CDP 网络事件 / 直接跑
 * buildAnalysis），再渲染成表格拍照，不是手搓的图。
 *
 * 用法：npm run build && npm run walkthrough:shots:r18
 * 只跑其中几幕：npm run walkthrough:shots:r18 -- play-rich wp-steps
 */

import { createServer } from 'node:http'
import { constants } from 'node:fs'
import { access, mkdir, readFile, stat, writeFile } from 'node:fs/promises'
import { extname, resolve, sep } from 'node:path'
import puppeteer from 'puppeteer-core'

const ROOT = resolve(import.meta.dirname, '..')
const OUT_DIR = resolve(ROOT, '.agent_workspace/evidence/r18')
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
  // R18 H3 之后富脚本按单元分片，不 await 就一条都查不到（UI 那边是按需拉的，
  // 这里是走查在挑样本，得先把全库装上才知道哪个字是手写关）
  if (typeof play.loadAllRichPlays === 'function') await play.loadAllRichPlays()
  return { CHAR_INDEX, play }
}

async function loadMathData() {
  const { register } = await import('node:module')
  register('./alias-loader.mjs', import.meta.url)
  const { WORD_PROBLEMS } = await import(resolve(ROOT, 'apps/math-app/src/data/wordProblems.js'))
  const { buildAnalysis } = await import(resolve(ROOT, 'apps/math-app/src/utils/wpAnalysis.js'))
  return { WORD_PROBLEMS, buildAnalysis }
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

/** hash 路由 + 静态资源：找不到的路径一律回 index.html。 */
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

/** 点第一个文字里含 needle 的按钮/链接。 */
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

/** 答一轮题；deliberateWrong 让这一轮有对有错，周报才判得出弱项。 */
async function answerRound(page, rounds, { deliberateWrong = false } = {}) {
  let answered = 0
  for (let i = 0; i < rounds; i += 1) {
    // 上一题锁着的时候选项是 disabled 的，等它放开再点，否则一轮只答得掉一题
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

/** 家长中心的口算门：读题面算出答案填进去。 */
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

/**
 * caption 可以传函数：自动播的画面在滚动定位那 400ms 里就已经走了，
 * 说明文字要在滚完之后、快门之前才现读一次 DOM，图文才对得上。
 */
async function shootElement(page, selector, name, caption) {
  const handle = await page.waitForSelector(selector, { timeout: 15_000 })
  await handle.evaluate((el) => el.scrollIntoView({ block: 'center' }))
  await wait(400)
  await shoot(handle, name, typeof caption === 'function' ? await caption() : caption)
}

/** 把当场量出来的数字渲染成一张表再拍照——每个格子都来自本次运行。 */
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
          `<tr class="${String(r[0]).startsWith('合计') || String(r[0]).startsWith('一致率') ? 'total' : ''}">` +
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

/**
 * ①② 富玩：一张手写富脚本关，一张仍吃模板回填的关。
 * 后者不是失败截图，是 R18 H2（富 Play ≥1200）要翻的那批字长什么样。
 */
async function scenePlayRich(browser, base) {
  console.log('\n① / ② 富玩')
  const { CHAR_INDEX, play } = await loadLiteracyData()
  const rich = CHAR_INDEX.filter((c) => play.hasRichPlay(c.char))
  const plain = CHAR_INDEX.filter((c) => !play.hasRichPlay(c.char))
  const coverage = play.richPlayCoverage()
  console.log(
    `  富脚本 ${play.countRichPlays()} 条 / 字表 ${CHAR_INDEX.length} 字；旁白去重 ${coverage.narrations}`,
  )
  if (!rich.length) throw new Error('字表里一个富脚本都没有')

  const page = await browser.newPage()
  await page.setViewport({ width: 460, height: 940, deviceScaleFactor: 2 })

  const openPlay = async (char) => {
    await page.goto(`${base}/#/learn/${encodeURIComponent(char)}`, {
      waitUntil: 'networkidle2',
      timeout: 30_000,
    })
    await page.evaluate(() => localStorage.clear())
    await page.reload({ waitUntil: 'networkidle2', timeout: 30_000 })
    await page.waitForSelector('.page.detail', { timeout: 15_000 })
    await page.click('.rail__step[data-step="play"]').catch(() => {})
    await page.waitForSelector('[data-char-play]', { timeout: 15_000 })
    await wait(1200)
    return page.$eval('[data-char-play]', (el) => ({
      template: el.dataset.playTemplate,
      fallback: el.dataset.fallback,
      state: el.dataset.state,
      narration: el.querySelector('.play__narration')?.textContent.trim() ?? '',
    }))
  }

  // 挑靠后的单元：前几个单元早就是手写关了，看不出这一轮富脚本铺到哪儿
  const richChar = (rich.find((c) => c.unit >= 40) ?? rich[rich.length - 1]).char
  const one = await openPlay(richChar)
  if (one.fallback !== 'false') throw new Error(`「${richChar}」不是手写富脚本关`)
  await shootElement(
    page,
    '[data-panel="play"]',
    'r18-01-play-rich.png',
    `富玩：手写富脚本的玩关「${richChar}」（data-play-template=${one.template}、` +
      `data-fallback=${one.fallback}），旁白「${one.narration}」`,
  )

  let gap = null
  if (plain.length) {
    const plainChar = plain[0].char
    gap = await openPlay(plainChar)
    await shootElement(
      page,
      '[data-panel="play"]',
      'r18-02-play-template-gap.png',
      `富玩缺口：字「${plainChar}」目前落在模板回填关（data-fallback=${gap.fallback}、` +
        `模板 ${gap.template}），旁白「${gap.narration}」——R18 H2 要把这批字续写成手写关`,
    )
    gap.char = plainChar
  }
  await page.close()
  return {
    richChar,
    richTemplate: one.template,
    plays: play.countRichPlays(),
    narrations: coverage.narrations,
    chars: CHAR_INDEX.length,
    probe: play.RICH_PLAY_PROBE,
    gap,
  }
}

/**
 * ③④ 拆包 / 单字关键路径：冷开一次单字详情，用 CDP 记下真下载的每一个 JS 分片。
 * R18 H3 要求 rich 不再整包同步进单字关键路径——这里量的就是它现在有多大。
 */
async function sceneBundle(browser, base) {
  console.log('\n③ / ④ 拆包与单字关键路径')
  const { CHAR_INDEX, play } = await loadLiteracyData()
  const char = (CHAR_INDEX.find((c) => play.hasRichPlay(c.char)) ?? CHAR_INDEX[0]).char

  const page = await browser.newPage()
  await page.setViewport({ width: 460, height: 940, deviceScaleFactor: 2 })
  await page.setCacheEnabled(false)

  const seen = new Map()
  let phase = 'cold'
  const cdp = await page.createCDPSession()
  await cdp.send('Network.enable')
  const urls = new Map()
  cdp.on('Network.responseReceived', (e) => {
    urls.set(e.requestId, e.response.url)
  })
  cdp.on('Network.loadingFinished', (e) => {
    const url = urls.get(e.requestId)
    if (!url) return
    const file = url.split('/').pop().split('?')[0]
    if (!file.endsWith('.js')) return
    const prev = seen.get(file)
    seen.set(file, {
      bytes: Math.max(prev?.bytes ?? 0, e.encodedDataLength ?? 0),
      phase: prev?.phase ?? phase,
    })
  })

  await page.goto(`${base}/#/learn/${encodeURIComponent(char)}`, {
    waitUntil: 'networkidle2',
    timeout: 30_000,
  })
  await page.waitForSelector('.page.detail', { timeout: 15_000 })
  await wait(2500)

  await page.evaluate(() => window.scrollTo(0, 0))
  await wait(400)
  const rail = await page.$$eval('.rail__step', (els) =>
    els.map((el) => el.innerText.replace(/\s+/g, '')).join(' → '),
  )
  await shoot(
    page,
    'r18-03-char-detail-single-char.png',
    `拆包场景的落点：单字详情「${char}」冷开首屏（步骤条 ${rail}），` +
      '这条就是 R18 H3 要减负的单字关键路径',
  )

  // 拆包拆没拆干净，光看首屏体积说不全：再切到一个**别的单元**的字，
  // 看它是不是只补拉那一个单元的分片。整包同步的写法这里会一片都不拉。
  phase = 'switch'
  const other =
    CHAR_INDEX.find((c) => play.hasRichPlay(c.char) && c.unit !== CHAR_INDEX[0].unit) ?? null
  if (other) {
    await page.goto(`${base}/#/learn/${encodeURIComponent(other.char)}`, {
      waitUntil: 'networkidle2',
      timeout: 30_000,
    })
    await page.waitForSelector('[data-char-play]', { timeout: 15_000 })
    await wait(1500)
  }

  const all = [...seen.entries()].map(([file, info]) => ({ file, ...info }))
  const cold = all.filter((r) => r.phase === 'cold').sort((a, b) => b.bytes - a.bytes)
  const later = all.filter((r) => r.phase === 'switch').sort((a, b) => b.bytes - a.bytes)
  const total = cold.reduce((sum, r) => sum + r.bytes, 0)
  const top = cold.slice(0, 8)
  const laterBytes = later.reduce((sum, r) => sum + r.bytes, 0)
  await shootPanel(
    browser,
    'r18-04-bundle-network.png',
    `拆包实测：冷开单字详情「${char}」真实下载 ${cold.length} 个 JS 分片 / ` +
      `${(total / 1024).toFixed(0)} KB；切到别的单元的字「${other?.char ?? '—'}」再补拉 ` +
      `${later.length} 片 / ${(laterBytes / 1024).toFixed(1)} KB`,
    {
      title: '单字关键路径 · 实测 JS 分片（Chrome CDP 采集）',
      subtitle:
        `路由 #/learn/${char} · 禁用缓存冷开 · 首屏 ${cold.length} 片 / ` +
        `${(total / 1024).toFixed(1)} KB 传输字节 · 采集时间 ${new Date().toISOString()}`,
      rows: [
        ['分片文件', '传输字节', 'KB'],
        ...top.map((r) => [r.file, r.bytes.toLocaleString('en-US'), (r.bytes / 1024).toFixed(1)]),
        ['合计（冷开全部分片）', total.toLocaleString('en-US'), (total / 1024).toFixed(1)],
        [
          `切到「${other?.char ?? '—'}」（${other?.unit ?? '—'}）后补拉`,
          later.length ? later.map((r) => r.file).join('、') : '（没有新分片）',
          (laterBytes / 1024).toFixed(1),
        ],
      ],
      note: later.length
        ? '换一个单元的字只补拉了它那一片富脚本，别的单元的剧本没有跟着下来——' +
          '这就是 R18 H3 的按单元懒加载在真浏览器里的样子。'
        : '换单元没有补拉任何分片：要么富脚本还是整包同步进来的，要么这个字没有手写剧本。',
    },
  )
  await page.close()
  return {
    char,
    coldChunks: cold.length,
    coldBytes: total,
    switchedTo: other ? { char: other.char, unit: other.unit } : null,
    switchChunks: later.map((r) => ({ file: r.file, bytes: r.bytes })),
    top: top.map((r) => ({ file: r.file, bytes: r.bytes })),
  }
}

/** ⑤ 剖析面板：图示 + 分步 + 变式，右上角可跳过。 */
async function sceneWpAnalysis(browser, base) {
  console.log('\n⑤ 应用题剖析')
  const page = await browser.newPage()
  await page.setViewport({ width: 900, height: 1250, deviceScaleFactor: 2 })
  await page.goto(`${base}/#/word-problems`, { waitUntil: 'networkidle2', timeout: 30_000 })
  await page.waitForSelector('.analysis-open', { timeout: 15_000 })
  await page.click('.analysis-open')
  await page.waitForSelector('[data-analysis]', { timeout: 15_000 })
  await wait(600)

  // 多步题默认只摊到倒数第二步，「全部摊开」才给完整推理链；单步题没有这个按钮
  const unfolded = await clickText(page, '全部摊开')
  await clickText(page, '看一道同结构的变式')
  await wait(800)
  // 变式那一段自己也挂一份 .steps，只数第一份才是本题的推理链
  const shown = await page.$eval(
    '[data-analysis] .steps',
    (ol) => ol.querySelectorAll('.step').length,
  )
  await shootElement(
    page,
    '[data-analysis]',
    'r18-05-wp-analysis.png',
    `应用题剖析面板：图示理解 + 分步提示（本题摊开 ${shown} 步，` +
      `${unfolded ? '点过「全部摊开」' : '没有「全部摊开」按钮，步骤已全在'}）+ 变式，` +
      '右上角「跳过 ✕」全程可退',
  )

  // 剖析看完照样能答题——顺手把这一轮答掉，给后面的周报攒真实作答记录
  const done = await answerRound(page, 8, { deliberateWrong: true })
  console.log(`  ↳ 剖析后继续作答 ${done} 题（有对有错），落进本机存档供周报判定`)
  await page.close()
  return { shownSteps: shown, answered: done }
}

/**
 * ⑥ 步数对齐：全库跑一遍 template.steps ↔ buildAnalysis().steps.length，
 * 把一致率和典型不一致题号摆出来。R18 H4 的阈值是 ≥90%。
 */
async function sceneStepsAudit(browser) {
  console.log('\n⑥ 剖析步数对齐实测')
  const { WORD_PROBLEMS, buildAnalysis } = await loadMathData()
  let match = 0
  const bad = []
  const oneStepOnly = []
  const byDeclared = new Map()
  for (const item of WORD_PROBLEMS) {
    const q = typeof item.make === 'function' ? item.make() : item
    const got = buildAnalysis(q).steps.length
    const tier = byDeclared.get(item.steps) ?? { total: 0, same: 0 }
    tier.total += 1
    if (got === item.steps) {
      match += 1
      tier.same += 1
    } else bad.push({ id: item.id, declared: item.steps, got })
    byDeclared.set(item.steps, tier)
    if (got <= 1) oneStepOnly.push(item.id)
  }
  const rate = (match / WORD_PROBLEMS.length) * 100
  console.log(
    `  一致 ${match}/${WORD_PROBLEMS.length}（${rate.toFixed(1)}%），仅 1 步剖析 ${oneStepOnly.length} 题`,
  )

  await shootPanel(
    browser,
    'r18-06-wp-steps-audit.png',
    `剖析步数对齐实测：一致率 ${rate.toFixed(1)}%（R18 H4 阈值 ≥90%）`,
    {
      title: '应用题「几步题」与剖析步数一致性 · 全库实测',
      subtitle:
        `WORD_PROBLEMS 共 ${WORD_PROBLEMS.length} 题 · 口径 template.steps ↔ ` +
        `buildAnalysis(make()).steps.length · 采集时间 ${new Date().toISOString()}`,
      // 全对的时候列不一致样本只会剩一行空表；那就改成按声明步数分档摊开
      rows: bad.length
        ? [
            ['题号（不一致样本）', '题面标称步数', '剖析实际步数'],
            ...bad.slice(0, 12).map((r) => [r.id, r.declared, r.got]),
            ['一致率', `${match} / ${WORD_PROBLEMS.length}`, `${rate.toFixed(1)}%`],
          ]
        : [
            ['声明步数分档', '母题数', '剖析拆出同样步数'],
            ...[...byDeclared.entries()]
              .sort((a, b) => a[0] - b[0])
              .map(([steps, tier]) => [`${steps} 步题`, tier.total, tier.same]),
            ['一致率', `${match} / ${WORD_PROBLEMS.length}`, `${rate.toFixed(1)}%`],
          ],
      note: bad.length
        ? `不一致共 ${bad.length} 题（上表只列前 ${Math.min(12, bad.length)} 条），` +
          `剖析只有 1 步的共 ${oneStepOnly.length} 题。孩子会看到「标着三步题、剖析只讲两句」——` +
          '这正是 R18 H4 要修的。'
        : `全库对得上：没有一道题出现「标着几步、剖析讲另一个步数」。剖析只有 1 步的共 ` +
          `${oneStepOnly.length} 题，它们的题面也都声明 1 步，属实。`,
    },
  )
  return {
    total: WORD_PROBLEMS.length,
    match,
    rate,
    mismatched: bad.length,
    oneStepOnly: oneStepOnly.length,
    byDeclared: Object.fromEntries([...byDeclared.entries()].sort((a, b) => a[0] - b[0])),
    sample: bad.slice(0, 12),
  }
}

/** ⑦ 家长周报：读的是本次走查自己答出来的那份存档。 */
async function sceneParentWeekly(browser, base, app) {
  console.log(`\n⑦ 家长周报（${app}）`)
  const page = await browser.newPage()
  await page.setViewport({ width: 760, height: 1100, deviceScaleFactor: 2 })
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
    `r18-07-${app}-parent-weekly.png`,
    `${app === 'math' ? '数学' : '识字'} App 家长周报：弱项判定 ${meta.weakness} —— ${meta.headline}`,
  )
  await page.close()
  return meta
}

/** ⑧ 学伴：识字首页的学伴气泡（台词随进度变，不是死文案）。 */
async function sceneMascot(browser, base) {
  console.log('\n⑧ 学伴')
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
    'r18-08-literacy-mascot.png',
    `识字 App 学伴：点一下学伴后的气泡台词「${say.slice(0, 60)}」`,
  )
  await page.close()
  return { say }
}

/* ------------------------------------------------------------------ 主流程 */

for (const [app, dist] of Object.entries(DISTS)) {
  if (!(await stat(resolve(dist, 'index.html')).catch(() => null))?.isFile()) {
    console.error(`walkthrough-shots-r18: 缺少 ${app} 的 dist；请先 npm run build。`)
    process.exit(1)
  }
}

await mkdir(OUT_DIR, { recursive: true })

const literacy = await listen(DISTS.literacy)
const math = await listen(DISTS.math)
const browser = await puppeteer.launch({
  executablePath: await findChrome(),
  headless: 'new',
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--mute-audio', '--font-render-hinting=none'],
})

const only = process.argv.slice(2)
const want = (id) => only.length === 0 || only.includes(id)
const meta = {}
const failures = []

/** 一幕塌了不该把整包带走：记下来接着走，最后在 json 里认账。 */
const run = async (id, label, fn) => {
  if (!want(id)) return
  try {
    meta[id] = await fn()
  } catch (error) {
    failures.push(`${label}：${error.message}`)
    console.error(`\n✗ ${label} 中断：${error.message}`)
  }
}

await run('play-rich', '富玩', () => scenePlayRich(browser, literacy.base))
await run('bundle', '拆包 / 单字', () => sceneBundle(browser, literacy.base))
await run('wp-analysis', '应用题剖析', () => sceneWpAnalysis(browser, math.base))
await run('wp-steps', '步数对齐', () => sceneStepsAudit(browser))
// 数学侧共用一个浏览器上下文：剖析那一幕答的题就落在这份存档里，周报读的是它
await run('parent-weekly', '家长周报', () => sceneParentWeekly(browser, math.base, 'math'))
await run('mascot', '学伴', () => sceneMascot(browser, literacy.base))

await browser.close()
await new Promise((done) => literacy.server.close(done))
await new Promise((done) => math.server.close(done))

await writeFile(
  resolve(OUT_DIR, 'walkthrough-shots.json'),
  `${JSON.stringify(
    {
      round: 18,
      generatedAt: new Date().toISOString(),
      chrome: await findChrome(),
      node: process.version,
      shots,
      meta,
      failures,
    },
    null,
    2,
  )}\n`,
)

console.log(`\n共落盘 ${shots.length} 张截图到 .agent_workspace/evidence/r18/`)
if (failures.length) console.log(`未完成的幕：${failures.length} —— ${failures.join('；')}`)
process.exit(failures.length === 0 && shots.length >= 4 ? 0 : 1)
