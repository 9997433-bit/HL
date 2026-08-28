/**
 * Round 17 H6 · 走查证据包的截图机。
 *
 * 走查报告要能被人复核，就不能只写「我看过了」。这个脚本把两个 App 的 dist
 * 各挂一台静态服务，用真 Chrome 走一遍四条要交差的路径，每到一个值得看的
 * 画面就落一张 PNG 到 .agent_workspace/evidence/r17/walkthrough/：
 *
 *   ① 无字源认步   识字 /learn/<无字源的字> 的「认」这一步（IntroFallbackStage 三幕）
 *   ② 学演示       数学玩法页里点开的学演示弹层，以及演示中心里的算式态
 *   ③ 应用题剖析   数学应用题的「剖析这道题」面板（图示 + 分步 + 变式）
 *   ④ 家长周报     两个 App 家长中心的周报卡片
 *   ⑤ 降动效       学演示在 prefers-reduced-motion 下的样子（验收 G4）
 *
 * 周报那两张刻意排在最后：前面几幕答的题会真的落进本机存档，周报读的就是
 * 那一份，所以截出来的弱项和建议是走查过程本身产生的，不是手搓的假数据。
 * 也因此数学侧全程共用一个浏览器上下文，中途不清 localStorage。
 *
 * 用法：npm run build && node scripts/walkthrough-shots.mjs
 * 只跑其中几幕：node scripts/walkthrough-shots.mjs intro-fallback wp-analysis
 */

import { createServer } from 'node:http'
import { constants } from 'node:fs'
import { access, mkdir, readFile, stat, writeFile } from 'node:fs/promises'
import { extname, resolve, sep } from 'node:path'
import puppeteer from 'puppeteer-core'

const ROOT = resolve(import.meta.dirname, '..')
const OUT_DIR = resolve(ROOT, '.agent_workspace/evidence/r17/walkthrough')
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

/**
 * 「认」这一步要拿一个**确实没有字源语料**的字，不能挑一个看着冷门的就写死——
 * 语料是会长的，今天没有的字明天可能就有了，那样截出来的就不是回退舞台。
 * 所以现查一遍索引，取第一个既没字源、又有组词的常用字。
 */
async function pickCharWithoutEtymology() {
  const { register } = await import('node:module')
  register('./alias-loader.mjs', import.meta.url)
  const { CHAR_INDEX } = await import(
    resolve(ROOT, 'apps/literacy-app/src/data/char-index.js')
  )
  const { hasEtymology } = await import(
    resolve(ROOT, 'apps/literacy-app/src/data/etymology-index.js')
  )
  const none = CHAR_INDEX.filter((c) => !hasEtymology(c.char))
  if (!none.length) throw new Error('字表里已经没有「没有字源」的字了')
  // 笔画太少的字三幕都摊不开，挑一个有部首、有几笔可写的，画面才说明得了问题
  return (none.find((c) => c.strokes >= 6 && c.emoji) ?? none[0]).char
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

/**
 * 答一轮题。deliberateWrong 为真时专挑不是正确答案的那个选项——
 * 周报的弱项判定要有错题才走得出「状态不错」以外的分支。
 */
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
        // 正确答案要答完才进 DOM，答之前挑不出「哪个一定是错的」；
        // 固定挑末位即可让一轮里既有对也有错，够周报判出弱项。
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
    await wait(1600)
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

/** 落一张图：整页或某个元素，顺带把它记进清单好写进报告。 */
async function shoot(target, name, caption) {
  const file = resolve(OUT_DIR, name)
  await target.screenshot({ path: file, captureBeyondViewport: false })
  const size = (await stat(file)).size
  shots.push({ name, caption, bytes: size })
  console.log(`  📸 ${name}（${(size / 1024).toFixed(0)} KB）— ${caption}`)
}

/**
 * caption 可以传一个函数。自动播放的演示每两秒换一段，滚动定位那 400ms 里
 * 画面就已经走了——所以说明文字要在滚完之后、快门之前才现读一次 DOM，
 * 否则报告里写的 stage 和图上亮着的那一段对不上。
 */
async function shootElement(page, selector, name, caption) {
  const handle = await page.waitForSelector(selector, { timeout: 15_000 })
  await handle.evaluate((el) => el.scrollIntoView({ block: 'center' }))
  await wait(400)
  await shoot(handle, name, typeof caption === 'function' ? await caption() : caption)
}

/* -------------------------------------------------------------- 四条路径 */

async function sceneIntroFallback(browser, base) {
  const char = await pickCharWithoutEtymology()
  console.log(`\n① 无字源认步 —— 取字「${char}」（etymology-index 查无此字）`)
  const page = await browser.newPage()
  await page.setViewport({ width: 460, height: 940, deviceScaleFactor: 2 })
  const route = `${base}/#/learn/${encodeURIComponent(char)}`
  await page.goto(route, { waitUntil: 'networkidle2', timeout: 30_000 })
  await page.evaluate(() => localStorage.clear())
  await page.reload({ waitUntil: 'networkidle2', timeout: 30_000 })
  await page.waitForSelector('.page.detail', { timeout: 15_000 })

  // 第一步是「玩」，从步骤条跳到「认」；跳得动本身就证明这一步没被锁住
  await page.click('.rail__step[data-step="intro"]')
  await page.waitForSelector('.page.detail[data-phase="intro"]', { timeout: 10_000 })

  // 有字源的字这里是 'etymology'；回退舞台报的是 data/intro-fallback.js 的 ROUND16_H2
  const stage = await page.$eval('.page.detail', (el) => el.dataset.introStage)
  if (stage === 'etymology') {
    throw new Error(`「${char}」挂的是字源舞台，不是无字源回退舞台`)
  }
  await page.waitForSelector('.ifs[data-act], .ifs', { timeout: 15_000 })

  await page.waitForFunction(
    () => document.querySelector('.ifs')?.dataset.scene === 'radical',
    { timeout: 15_000 },
  )
  await wait(1200)
  await shootElement(
    page,
    '[data-panel="intro"]',
    'r17-literacy-intro-fallback-radical.png',
    async () => {
      const scene = await page.$eval('.ifs', (el) => el.dataset.scene)
      return (
        `无字源字「${char}」认步第一幕（data-scene=${scene}）：部首牌登场 + 同部首兄弟字，` +
        `整步挂在 data-intro-stage=${stage} 这个回退舞台上`
      )
    },
  )

  // 三幕自动演，演完这一步会挂着「马上进入下一步」的倒计时自己往前走。
  // 走查要停在第三幕看清楚，所以一边等组词那一幕，一边把冒出来的倒计时按住。
  let onWord = false
  for (let i = 0; i < 200 && !onWord; i += 1) {
    onWord = await page.evaluate(() => {
      document.querySelector('.autonext .btn')?.click()
      return ['word', 'static'].includes(document.querySelector('.ifs')?.dataset.scene)
    })
    if (!onWord) await wait(200)
  }
  if (!onWord) throw new Error('回退舞台没有演到组词那一幕')
  await wait(1200)
  await page.evaluate(() => document.querySelector('.autonext .btn')?.click())
  await shootElement(
    page,
    '[data-panel="intro"]',
    'r17-literacy-intro-fallback-word.png',
    async () => {
      const scene = await page.$eval('.ifs', (el) => el.dataset.scene)
      return `无字源字「${char}」认步第三幕（data-scene=${scene}）：组词情境，目标字在词里点亮`
    },
  )
  await page.close()
}

async function sceneLearnDemo(browser, base) {
  console.log('\n② 学演示')
  const page = await browser.newPage()
  await page.setViewport({ width: 900, height: 1150, deviceScaleFactor: 2 })

  // 先在玩法页里点开弹层：这是孩子卡住时真正会走的入口
  await page.goto(`${base}/#/number-sense`, { waitUntil: 'networkidle2', timeout: 30_000 })
  await page.waitForSelector('[data-learn-demo-open]', { timeout: 15_000 })
  const skill = await page.$eval('[data-learn-demo-open]', (el) => el.dataset.learnDemoSkill)
  await page.click('[data-learn-demo-open]')
  await page.waitForSelector('[data-learn-demo-layer] [data-demo-id]', { timeout: 15_000 })
  await wait(1400)
  await shootElement(
    page,
    '[data-learn-demo-layer] [data-demo-id]',
    'r17-math-learn-demo-overlay.png',
    async () => {
      const now = await page.$eval('[data-demo-id]', (el) => ({
        id: el.dataset.demoId,
        stage: el.dataset.demoStage,
        motion: el.dataset.demoMotion,
      }))
      return (
        `玩法页「数量星云」里点开的学演示弹层（技能 ${skill} / 演示 ${now.id}），` +
        `data-demo-motion=${now.motion} 自动播到 data-demo-stage=${now.stage}`
      )
    },
  )

  // 再把三态走到底，证明「实物 → 图形 → 算式」不是只画了第一张
  for (let i = 0; i < 6; i += 1) {
    const next = await page.$('[data-demo-next]')
    if (!next) break
    await next.click()
    await wait(900)
  }
  await shootElement(
    page,
    '[data-demo-id]',
    'r17-math-learn-demo-equation.png',
    async () => {
      const stage = await page.$eval('[data-demo-id]', (el) => el.dataset.demoStage)
      return `同一个演示走到末态（data-demo-stage=${stage}），三态并排且「跳过演示」全程常驻`
    },
  )

  // 收起弹层接着练：既证明演示不接管这一轮，也给后面的周报攒真实作答记录
  await clickText(page, '收起，继续练')
  await wait(600)
  const done = await answerRound(page, 8, { deliberateWrong: true })
  console.log(`  ↳ 收起演示后继续作答 ${done} 题（有对有错）`)
  await page.close()
}

/**
 * 验收 G4 要求「reduced-motion 可完成」。演示本身是逐段播的，降动效下
 * LearnDemo 会走静态分支：不再定时推进，三段一次铺开、stage 直接停在算式。
 * 这一幕就是去拍那个分支——不是把动画截个尾帧冒充。
 */
async function sceneReducedMotion(browser, base) {
  console.log('\n⑤ 降动效下的学演示')
  const page = await browser.newPage()
  await page.setViewport({ width: 900, height: 1150, deviceScaleFactor: 2 })
  await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }])
  await page.goto(`${base}/#/number-sense`, { waitUntil: 'networkidle2', timeout: 30_000 })
  await page.waitForSelector('[data-learn-demo-open]', { timeout: 15_000 })
  await page.click('[data-learn-demo-open]')
  await page.waitForSelector('[data-learn-demo-layer] [data-demo-id]', { timeout: 15_000 })
  await wait(900)

  const state = await page.$eval('[data-demo-id]', (el) => ({
    id: el.dataset.demoId,
    motion: el.dataset.demoMotion,
    stage: el.dataset.demoStage,
    hasNext: Boolean(el.querySelector('[data-demo-next]')),
  }))
  if (state.motion !== 'static') {
    throw new Error(`降动效下 data-demo-motion=${state.motion}，没走静态分支`)
  }
  await shootElement(
    page,
    '[data-learn-demo-layer] [data-demo-id]',
    'r17-math-learn-demo-reduced-motion.png',
    // 挑到哪条演示取决于当时题面上的技能点，未必和第 ② 幕是同一条
    `演示「${state.id}」在 prefers-reduced-motion: reduce 下：data-demo-motion=${state.motion}、` +
      `一进来就停在 data-demo-stage=${state.stage}，三段同时铺开、` +
      `${state.hasNext ? '仍留有「下一步」' : '不再有「下一步」等着点'}，「跳过演示」照常在`,
  )
  await page.close()
}

async function sceneWpAnalysis(browser, base) {
  console.log('\n③ 应用题剖析')
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
  await shootElement(
    page,
    '[data-analysis]',
    'r17-math-wp-analysis.png',
    '应用题剖析面板：① 图示理解（条形图 + 已知/所求）② 分步提示' +
      `（${unfolded ? '已「全部摊开」' : '本题一步到底，末步得数按设计盖住'}）③ 变式，` +
      '右上角「跳过 ✕」全程可退',
  )

  // 剖析看完照样能答题——顺手把这一轮答掉，给最后的周报攒真实数据
  const done = await answerRound(page, 8, { deliberateWrong: true })
  console.log(`  ↳ 剖析后继续作答 ${done} 题（有对有错），落进本机存档供周报判定`)
  await page.close()
}

async function sceneParentWeekly(browser, base, app) {
  console.log(`\n④ 家长周报（${app}）`)
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
    `r17-${app}-parent-weekly.png`,
    `${app === 'math' ? '数学' : '识字'} App 家长周报：弱项判定 ${meta.weakness} —— ${meta.headline}`,
  )
  await page.close()
  return meta
}

/* ------------------------------------------------------------------ 主流程 */

for (const [app, dist] of Object.entries(DISTS)) {
  if (!(await stat(resolve(dist, 'index.html')).catch(() => null))?.isFile()) {
    console.error(`walkthrough-shots: 缺少 ${app} 的 dist；请先 npm run build。`)
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
let failed = 0

try {
  if (want('intro-fallback')) await sceneIntroFallback(browser, literacy.base)
  if (want('learn-demo')) await sceneLearnDemo(browser, math.base)
  if (want('reduced-motion')) await sceneReducedMotion(browser, math.base)
  if (want('wp-analysis')) await sceneWpAnalysis(browser, math.base)
  // 数学侧共用一个浏览器上下文：上面答的题就落在这份存档里，周报读的是它
  if (want('parent-weekly')) {
    meta.math = await sceneParentWeekly(browser, math.base, 'math')
    meta.literacy = await sceneParentWeekly(browser, literacy.base, 'literacy')
  }
} catch (error) {
  failed += 1
  console.error(`\n走查中断：${error.message}\n${error.stack}`)
}

await browser.close()
await new Promise((done) => literacy.server.close(done))
await new Promise((done) => math.server.close(done))

await writeFile(
  resolve(OUT_DIR, 'shots.json'),
  `${JSON.stringify(
    { generatedAt: new Date().toISOString(), chrome: await findChrome(), shots, meta },
    null,
    2,
  )}\n`,
)

console.log(`\n共落盘 ${shots.length} 张截图到 .agent_workspace/evidence/r17/walkthrough/`)
process.exit(failed === 0 && shots.length >= 4 ? 0 : 1)
