/**
 * 冒烟测试：用无头 Chrome 把 dist 里的每条路由都走一遍，
 * 收集控制台报错、未捕获异常和 Vue 警告，并顺手做几个交互。
 *
 * 用法：npm run build && node scripts/smoke.mjs
 */

import { createServer } from 'node:http'
import { readdir, readFile } from 'node:fs/promises'
import { existsSync, statSync } from 'node:fs'
import { extname, join, normalize, sep } from 'node:path'
import { fileURLToPath } from 'node:url'
import puppeteer from 'puppeteer-core'

import {
  BOOKS,
  ROUND12_H3,
  ROUND13_H3,
  SCENE_BOOK_IDS,
  TOTAL_SCENE_PAGES,
  scenePages
} from '../src/data/books.js'
import { ROUND12_H4, SONGS } from '../src/data/songs.js'

const ROOT = fileURLToPath(new URL('..', import.meta.url))
const DIST = join(ROOT, 'dist')
const CHROME = '/usr/local/bin/google-chrome'

const routerSource = await readFile(join(ROOT, 'src/router/index.js'), 'utf8')
const sourceRoutePaths = [
  ...routerSource
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '')
    .matchAll(/\bpath\s*:\s*(['"])(.*?)\1/g)
].map((match) => match[2])
const findStaticRoute = (pattern) =>
  sourceRoutePaths.find((route) => !route.includes(':') && pattern.test(route))
const round6PoemRoute = findStaticRoute(/\/(?:poems?|poetry|classics?)(?:\/|$)/i)
const round6SpeechRoute = findStaticRoute(
  /\/(?:follow[-/]?read|speech[-/]?(?:eval|assess)|read[-/]?aloud)(?:\/|$)/i
)

// check:round6 会验证这两个 stub 仍在。功能路由合入后，它们自动进入真实浏览器回归。
const ROUND6_H3_SMOKE = round6PoemRoute
const ROUND6_H4_SMOKE = round6SpeechRoute
const ROUND8_H5_SMOKE = round6SpeechRoute ?? '/follow-read'
const round6Routes = [
  ...(ROUND6_H3_SMOKE ? [['古诗国学（Round 6）', `/#${ROUND6_H3_SMOKE}`]] : []),
  ...(ROUND6_H4_SMOKE ? [['跟读评测（Round 6）', `/#${ROUND6_H4_SMOKE}`]] : [])
]

/**
 * Round 8 H2：儿歌小舞台。
 * 路由是 `/songs/:id?`（歌单和展开的那一首共用一条），`findStaticRoute` 拿不到，
 * 所以这里按前缀取它不带参数的形态。
 */
const ROUND8_H2_SMOKE = sourceRoutePaths
  .map((route) => route.match(/^(\/(?:songs?|nursery|儿歌))(?:\/|$)/i)?.[1])
  .find(Boolean)
const round8Routes = ROUND8_H2_SMOKE ? [['儿歌小舞台（Round 8）', `/#${ROUND8_H2_SMOKE}`]] : []

/**
 * ROUND9_H1_SMOKE：儿歌 v2 的曲库与歌词-旋律同步动画。
 * 走同一条路由，但验的是 v1 没有的四件事——曲库规模、预备拍、进度/留痕、音高抬升。
 */
const ROUND9_H1_SMOKE = ROUND8_H2_SMOKE
const ROUND9_H1_MIN_SONGS = 10
const ROUND10_H5_SMOKE = SONGS.filter(
  (song) => song?.audio && /\.(?:mp3|ogg)$/i.test(String(song.audio))
)
const ROUND10_H5_MIN_AUDIO = 3
const ROUND12_H4_MIN_AUDIO = 13
const ROUND12_H4_MIN_BYTES = 10_240
const ROUND12_H4_VOCAL = SONGS.find(
  (song) => song?.vocal && /\.(?:mp3|ogg)$/i.test(String(song.vocal))
)
if (ROUND12_H4 !== 'thirteen-offline-melodies-with-vocal-pilot') {
  console.error(`ROUND12_H4_SMOKE：能力标记不对（${ROUND12_H4 || '缺失'}）`)
  process.exit(1)
}

/**
 * ROUND10_H1_SMOKE：跟读 v3 —— 离线 ASR（sherpa-onnx WASM Worker）接线。
 * 走跟读那条路由，验的是四档降级契约和隐私默认：
 * 第一档失败时必须落到录音档，不许悄悄改用可能联网的浏览器识别。
 */
const ROUND10_H1_SMOKE = ROUND8_H5_SMOKE
const ROUND10_H1_TIERS = ['offline-asr', 'recognition', 'recording', 'listen-only']
const ROUND10_H1_MODES = ['recognition', 'recording', 'listen-only']

/**
 * ROUND11_H1_SMOKE：跟读产品化 —— 冻结清单与五层门槛随包发出去。
 *
 * R10 那条验的是「四档降级不塌」；这一条验的是「凭什么把 available 置成 true」
 * 那套东西真的到了用户机器上：页面读得到冻结清单和五层门槛表，
 * 结论没转绿之前 available 必须是 false，dist 里一个模型字节都不许有。
 * 清单结构和 Go/No-Go 判定由 scripts/test-asr-eval-set.mjs 在 Node 里守，
 * 这里守的是「构建产物里的那一份」——两边对不上就是打包漏了。
 */
const ROUND11_H1_SMOKE = ROUND8_H5_SMOKE
const ROUND11_H1_MIN_FREEZE = 8
const ROUND11_H1_LAYERS = ['文本层', '诊断层', '性能层', '资源层', '可靠性层']
/** dist/asr 顶层随包发的只有这两个文件：清单和采音 worklet。模型都在 models/ 下。 */
const ROUND11_H1_SHIPPED = ['manifest.json', 'pcm-capture.worklet.js']

/**
 * ROUND12_H1_SMOKE：模型真落库之后，孩子那一侧还是不许变。
 *
 * R11 守的是「清单发出去了」，这一条守的是**落库与放行的那道缝没被抹掉**：
 * 35 MiB 的模型现在确实躺在 dist 里，可是
 *
 *   - 首屏一次都不许请求它（家长不点「下载」，一个字节都不动）；
 *   - 清单 files[] 每一项都要能被页面按同源地址取到、取回来的字节数与 bytes 对得上
 *     （抽最大和最小两个文件各取一次，够钉住「路径写错 / 没随包发出去」）；
 *   - available 还是 false，所以界面必须继续停在录音档、入口上写的还是「下载」；
 *   - 家长点了下载：这一版清单不放行，界面必须落到 failed 并说明原因，
 *     且全程 0 个跨源请求——落库不是偷偷放行的后门。
 */
const ROUND12_H1_SMOKE = ROUND8_H5_SMOKE
const ROUND12_H1_PACK_DIR = 'models'
const ROUND12_H1_MAX_PACK_BYTES = 60 * 1024 * 1024
const ROUND12_H1_ROLES = [
  'wasm-glue',
  'wasm-binary',
  'asr-api',
  'model-encoder',
  'model-decoder',
  'model-joiner',
  'tokens'
]

/**
 * ROUND11_H4_SMOKE：绘本页级场景。
 * 书是从数据里挑的，不写死 id——样板换本书，测试跟着走。
 * 验四件事：摆出了多件元素、都落在画框里、翻页换整幅、减少动态时一动不动；
 * 外加一本没升级的书仍旧退回单 emoji（一百多本扩充绘本靠这条兜底）。
 */
const ROUND11_H4_SMOKE = BOOKS.find((book) => scenePages(book).length >= 3) ?? null
const ROUND11_H4_PLAIN = BOOKS.find((book) => scenePages(book).length === 0) ?? null
const ROUND11_H4_MIN_ITEMS = 3

/**
 * ROUND13_H3_SMOKE：场景铺到 33 本 209 页之后的抽检。
 *
 * R11 那条验的是「一本样板画得对」；铺开之后要防的是另一件事——
 * 数据里堆够了页数，渲染却没跟上：某一页少画两件、坐标写错飘出画框、
 * 或者哪本书的 `scene` 被别的改动吃回单 emoji。逐页比对
 * 「数据声明几件 / DOM 上的 data-scene-items 几件 / 真的画出来几件」，
 * 三个数对不齐就是渲染没兑现数据。
 *
 * 抽样而不是全量：33 本 209 页翻一遍要十几分钟，冒烟没这个预算。
 * R12 那版按下标取首尾和中间两本，铺到三个分级之后这么取会整级漏掉——
 * L2 的扩充绘本正好落在两个采样点之间。改成每级取头尾：手写的 core、
 * 生成的 l1/l2 和每个分级的边界书都在里面，五本三十来页仍在预算内。
 */
const ROUND13_H3_SAMPLE = (() => {
  const scened = BOOKS.filter((book) => scenePages(book).length)
  const picked = new Set()
  for (const level of new Set(scened.map((book) => book.level))) {
    const inLevel = scened.filter((book) => book.level === level)
    picked.add(inLevel[0])
    picked.add(inLevel[inLevel.length - 1])
  }
  return scened.filter((book) => picked.has(book))
})()

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.ogg': 'audio/ogg',
  '.mp3': 'audio/mpeg',
  '.woff2': 'font/woff2'
}

if (!existsSync(DIST)) {
  console.error('先跑 npm run build')
  process.exit(1)
}

/**
 * Round 10 H5：数据里的“有音频”不能只是一个字符串。dist 中必须真有至少三份
 * 可解码格式的静态资产；Ogg/MP3 魔数与最小体积一起挡住空文件和 HTML 404。
 */
const songAudioAssets = []
for (const song of ROUND10_H5_SMOKE) {
  const relative = String(song.audio).replace(/^\.?\//, '')
  const extension = extname(relative).toLowerCase()
  let bytes
  try {
    if (relative.includes('..')) throw new Error('路径不能包含 ..')
    bytes = await readFile(join(DIST, relative))
  } catch (error) {
    console.error(`ROUND10_H5_SMOKE：${song.id} 音频不存在（${relative}）：${error.message}`)
    process.exit(1)
  }
  const signature =
    (extension === '.ogg' && bytes.subarray(0, 4).toString('ascii') === 'OggS') ||
    (extension === '.mp3' &&
      (bytes.subarray(0, 3).toString('ascii') === 'ID3' ||
        (bytes[0] === 0xff && (bytes[1] & 0xe0) === 0xe0)))
  if (bytes.length < ROUND12_H4_MIN_BYTES || !signature) {
    console.error(
      `ROUND12_H4_SMOKE：${song.id} 不是有效且 ≥10KB 的 ${extension} 音频（${bytes.length} bytes）`
    )
    process.exit(1)
  }
  songAudioAssets.push({ id: song.id, relative, bytes: bytes.length })
}
if (songAudioAssets.length < ROUND10_H5_MIN_AUDIO) {
  console.error(
    `ROUND10_H5_SMOKE：真实 Ogg/MP3 只有 ${songAudioAssets.length}/${ROUND10_H5_MIN_AUDIO} 首`
  )
  process.exit(1)
}
const distinctSongAudio = new Set(songAudioAssets.map((asset) => asset.relative))
if (
  songAudioAssets.length < ROUND12_H4_MIN_AUDIO ||
  distinctSongAudio.size < ROUND12_H4_MIN_AUDIO
) {
  console.error(
    `ROUND12_H4_SMOKE：离线旋律只有 ${songAudioAssets.length} 首 / ` +
      `${distinctSongAudio.size} 份去重资产，要求 13/13`
  )
  process.exit(1)
}

let vocalPilotAsset = null
if (ROUND12_H4_VOCAL) {
  const relative = String(ROUND12_H4_VOCAL.vocal).replace(/^\.?\//, '')
  const extension = extname(relative).toLowerCase()
  try {
    if (relative.includes('..')) throw new Error('路径不能包含 ..')
    const bytes = await readFile(join(DIST, relative))
    const signature =
      (extension === '.ogg' && bytes.subarray(0, 4).toString('ascii') === 'OggS') ||
      (extension === '.mp3' &&
        (bytes.subarray(0, 3).toString('ascii') === 'ID3' ||
          (bytes[0] === 0xff && (bytes[1] & 0xe0) === 0xe0)))
    if (bytes.length < ROUND12_H4_MIN_BYTES || !signature) {
      throw new Error(`${bytes.length} bytes / ${extension || '无扩展名'}`)
    }
    vocalPilotAsset = { id: ROUND12_H4_VOCAL.id, relative, bytes: bytes.length }
  } catch (error) {
    console.error(`ROUND12_H4_SMOKE：范唱资产无效（${relative}）：${error.message}`)
    process.exit(1)
  }
}
if (!vocalPilotAsset) {
  console.error('ROUND12_H4_SMOKE：13 首中没有可播放的离线范唱试点')
  process.exit(1)
}

/**
 * Round 11 H1 / ROUND12_H1：模型不进首屏这件事，只能在 dist 上验。
 *
 * 清单里可以写「不进首屏 precache」，vite.config.js 里也可以写 exclude，
 * 但真正决定用户第一次打开要下多少字节的，是 dist/asr 里躺着什么、
 * sw.js 的预缓存清单里列了什么。
 *
 * R11 那会儿仓库里一个模型字节都没有，所以这条写成「dist/asr 里除了清单和 worklet
 * 不许有第三个文件」。R12 模型真落库之后，那句话字面上必然不成立——真正要守的
 * 从来不是「包里没有模型」，而是**「模型在包里，但没人替访客提前下载它」**：
 *
 *   1. dist/asr 顶层还是只有清单和 worklet，模型一律在 models/ 子目录下；
 *   2. models/ 的字节数与清单 files[] 逐项对得上，且整包 ≤ 60 MiB；
 *   3. sw.js 的预缓存清单里不许出现 asr/models/；
 *   4. 首屏跑完浏览器一次都没请求过模型——这条在下面的交互用例里量。
 */
const asrDistDir = join(DIST, 'asr')
const asrShipped = existsSync(asrDistDir) ? await readdir(asrDistDir, { recursive: true }) : []
let asrStrayBytes = 0
let asrModelBytes = 0
for (const entry of asrShipped) {
  const full = join(asrDistDir, entry)
  if (!statSync(full).isFile()) continue
  const relative = entry.split(sep).join('/')
  if (ROUND11_H1_SHIPPED.includes(relative)) continue
  if (relative.startsWith(`${ROUND12_H1_PACK_DIR}/`)) asrModelBytes += statSync(full).size
  else asrStrayBytes += statSync(full).size
}
if (asrStrayBytes > 0) {
  console.error(
    `ROUND11_H1_SMOKE：dist/asr 顶层多出 ${asrStrayBytes} 字节` +
      `（只该有 ${ROUND11_H1_SHIPPED.join('、')}，模型一律放 ${ROUND12_H1_PACK_DIR}/）`
  )
  process.exit(1)
}
const asrDistManifest = JSON.parse(await readFile(join(asrDistDir, 'manifest.json'), 'utf8'))
const asrDeclaredBytes = (asrDistManifest.files ?? []).reduce((n, file) => n + (file.bytes ?? 0), 0)
if (asrDeclaredBytes !== asrModelBytes) {
  console.error(
    `ROUND12_H1_SMOKE：dist 里的模型 ${asrModelBytes} 字节，清单声明 ${asrDeclaredBytes} 字节——` +
      '发出去的和冻结的不是同一份'
  )
  process.exit(1)
}
if (asrModelBytes > ROUND12_H1_MAX_PACK_BYTES) {
  console.error(
    `ROUND12_H1_SMOKE：整包 ${(asrModelBytes / 1048576).toFixed(2)} MiB 超过 60 MiB 预算`
  )
  process.exit(1)
}
const swSource = await readFile(join(DIST, 'sw.js'), 'utf8')
if (/asr\/models\//.test(swSource)) {
  console.error('ROUND11_H1_SMOKE：离线评测包被写进了 sw.js 的预缓存清单，首屏会被拖垮')
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
  ['首页地图', '/#/'],
  ['字表', '/#/learn'],
  ['单字详情 日', `/#/learn/${encodeURIComponent('日')}`],
  ['单字详情 说', `/#/learn/${encodeURIComponent('说')}`],
  ['听音识字', '/#/listen'],
  ['听音识字(旧路径)', '/#/game/listen'],
  ['拍照识字', '/#/ocr'],
  ['小游戏大厅', '/#/games'],
  ['字迷宫', '/#/games/maze'],
  ['配对记忆', '/#/games/memory'],
  ['找不同', '/#/games/spot'],
  ['拼音拼字', '/#/games/spell'],
  ['接字大冒险', '/#/games/catch'],
  ['偏旁部首', '/#/radicals'],
  ['偏旁详情', '/#/radicals/shui'],
  ['绘本书架', '/#/books'],
  // 绘本从数据表生成：书目一多，漏测某一本比路由写错更容易发生。
  ...BOOKS.map((b) => [`绘本 ${b.id} L${b.level}《${b.title}》`, `/#/books/${b.id}`]),
  ['成语列表', '/#/idioms'],
  ['成语 守株待兔', '/#/idioms/szdt'],
  ['成语 画蛇添足', '/#/idioms/hstz'],
  ['成语 水滴石穿', '/#/idioms/sdsc'],
  ['成语 举一反三', '/#/idioms/jyfs'],
  ['成语 愚公移山', '/#/idioms/ygys'],
  ['成语 盲人摸象', '/#/idioms/mrmx'],
  ['成语 五颜六色', '/#/idioms/wyls'],
  ...round6Routes,
  ...round8Routes,
  ['字源馆', '/#/etymology'],
  ['字源 日（象形）', `/#/etymology/${encodeURIComponent('日')}`],
  ['字源 明（会意）', `/#/etymology/${encodeURIComponent('明')}`],
  ['家长中心', '/#/parent'],
  ['隐私政策', '/#/privacy'],
  ['未知路由回落', '/#/nope/nope']
]

const IGNORE = [
  /Failed to load resource/i, // 离线环境下 CDN 兜底请求
  /net::ERR_/i,
  /favicon/i
]

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: 'new',
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--mute-audio']
})

const problems = []
const rows = []

for (const [name, path] of ROUTES) {
  const page = await browser.newPage()
  await page.setViewport({ width: 420, height: 860, isMobile: true, hasTouch: true })
  const found = []

  page.on('console', (m) => {
    if (!['error', 'warning'].includes(m.type())) return
    const text = m.text()
    if (IGNORE.some((re) => re.test(text))) return
    found.push(`[${m.type()}] ${text}`)
  })
  page.on('pageerror', (e) => found.push(`[pageerror] ${e.message}`))

  try {
    await page.goto(base + path, { waitUntil: 'networkidle2', timeout: 20000 })
    // 路由组件是按需 chunk，networkidle2 之后还要等它挂上来
    await page
      .waitForFunction(() => (document.querySelector('#app')?.innerText ?? '').length > 40, {
        timeout: 8000
      })
      .catch(() => {})
    await new Promise((r) => setTimeout(r, 400))

    const info = await page.evaluate(() => {
      const app = document.querySelector('#app')
      const txt = app?.innerText ?? ''
      return {
        mounted: !!app && app.children.length > 0,
        chars: txt.replace(/\s+/g, '').length,
        // 明显的渲染事故：模板里漏出 NaN / undefined
        broken: /NaN|undefined|\[object Object\]/.test(txt),
        hash: location.hash,
        title: document.title
      }
    })

    // 详情页被重定向回列表，通常意味着 id 对不上（内容改名后最常见的回归）
    const want = path.slice(path.indexOf('#') + 1)
    if (info.hash && info.hash.slice(1) !== want && !path.includes('nope') && !path.includes('game/listen')) {
      found.push(`[route] 期望停在 ${want}，实际跳到 ${info.hash.slice(1)}`)
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

/* ------------------------------------------------ 交互：听音识字玩一局 */
const inter = []
async function interact(label, path, fn) {
  const page = await browser.newPage()
  await page.setViewport({ width: 420, height: 860, isMobile: true, hasTouch: true })
  const errs = []
  page.on('console', (m) => {
    if (m.type() === 'error' && !IGNORE.some((re) => re.test(m.text()))) errs.push(m.text())
  })
  page.on('pageerror', (e) => errs.push(e.message))
  try {
    await page.goto(base + path, { waitUntil: 'networkidle2', timeout: 20000 })
    await new Promise((r) => setTimeout(r, 500))
    const note = await fn(page)
    inter.push({ label, ok: errs.length === 0, note, errs })
  } catch (err) {
    inter.push({ label, ok: false, note: err.message, errs })
  }
  await page.close()
}

const clickText = async (page, text) => {
  const done = await page.evaluate((t) => {
    const el = [...document.querySelectorAll('button, a')].find((b) =>
      b.innerText.replace(/\s+/g, '').includes(t)
    )
    if (!el) return false
    el.click()
    return true
  }, text)
  await new Promise((r) => setTimeout(r, 450))
  return done
}

await interact('FSRS：到期卡进入复习队列，未到期卡不进入', `/#/learn/${encodeURIComponent('日')}`, async (page) => {
  await page.evaluate(() => localStorage.clear())
  await page.reload({ waitUntil: 'networkidle2' })
  await new Promise((r) => setTimeout(r, 500))

  if (!(await clickText(page, '我认识这个字'))) {
    throw new Error('单字页缺少“我认识这个字”评分入口')
  }
  await page.goto(`${base}/#/learn/${encodeURIComponent('月')}`, {
    waitUntil: 'networkidle2',
    timeout: 20000
  })
  await new Promise((r) => setTimeout(r, 500))
  if (!(await clickText(page, '我认识这个字'))) {
    throw new Error('第二张单字卡无法提交评分')
  }

  const seeded = await page.evaluate(() => {
    const now = Date.now()
    const storageKeys = Object.keys(localStorage)

    for (const key of storageKeys) {
      let value
      try {
        value = JSON.parse(localStorage.getItem(key))
      } catch {
        continue
      }

      const cards = []
      const seen = new Set()
      const walk = (node, path = '$') => {
        if (!node || typeof node !== 'object' || seen.has(node)) return
        seen.add(node)
        if (
          typeof node.charId === 'string' &&
          Number.isFinite(node.due) &&
          Number.isFinite(node.stability)
        ) {
          cards.push({ node, path })
        }
        for (const [name, child] of Object.entries(node)) walk(child, `${path}.${name}`)
      }
      walk(value)

      const due = cards.find(({ node }) => node.charId === '日')
      const future = cards.find(({ node }) => node.charId === '月')
      if (!due || !future) continue

      due.node.due = now - 60_000
      future.node.due = now + 7 * 24 * 60 * 60 * 1000
      localStorage.setItem(key, JSON.stringify(value))
      return {
        key,
        count: cards.length,
        duePath: due.path,
        futurePath: future.path
      }
    }
    return null
  })

  if (!seeded) {
    throw new Error('作答后未在持久化进度中找到日、月两张 FSRS 卡')
  }

  // 改到期时间是直接写 localStorage 的，只切 hash 不会重新读档；
  // 刷新一次既能让改动生效，也顺带验证了记忆卡确实是从存档里恢复出来的。
  await page.goto(`${base}/#/learn`, { waitUntil: 'networkidle2', timeout: 20000 })
  await page.reload({ waitUntil: 'networkidle2', timeout: 20000 })
  await new Promise((r) => setTimeout(r, 600))
  if (!(await clickText(page, '要复习'))) {
    throw new Error('字表缺少“要复习”筛选入口')
  }
  await page
    .waitForFunction(
      () =>
        [...document.querySelectorAll('.cc')].some(
          (node) => node.querySelector('.cc__char')?.textContent?.trim() === '日'
        ),
      { timeout: 3000 }
    )
    .catch(() => {})

  const visible = await page.evaluate(() =>
    [...document.querySelectorAll('.cc')]
      .filter((node) => {
        const style = getComputedStyle(node)
        return style.display !== 'none' && style.visibility !== 'hidden' && node.getClientRects().length > 0
      })
      .map((node) => node.querySelector('.cc__char')?.textContent?.trim())
      .filter(Boolean)
  )
  if (!visible.includes('日')) throw new Error(`到期卡“日”没有进入复习队列：${visible.join('、')}`)
  if (visible.includes('月')) throw new Error('未到期卡“月”错误进入复习队列')

  const opened = await page.evaluate(() => {
    const card = [...document.querySelectorAll('.cc')].find(
      (node) => node.querySelector('.cc__char')?.textContent?.trim() === '日'
    )
    if (!card || card.getAttribute('aria-disabled') === 'true') return false
    card.click()
    return true
  })
  if (!opened) throw new Error('到期卡“日”在复习队列中不可打开')
  await page.waitForFunction(
    () => location.hash === `#/learn/${encodeURIComponent('日')}`,
    { timeout: 5000 }
  )

  return `持久化卡=${seeded.count}，到期“日”可见且可打开，未来“月”已排除`
})

await interact('字表：分页渲染且所有字可达', '/#/learn', async (page) => {
  const snapshot = () =>
    page.evaluate(() => {
      const text = document.body.innerText
      const total = Number(text.match(/共\s*(\d+)\s*个常用字/)?.[1] ?? 0)
      const chars = [...document.querySelectorAll('.cc')]
        .filter((node) => {
          const style = getComputedStyle(node)
          return (
            style.display !== 'none' &&
            style.visibility !== 'hidden' &&
            node.getClientRects().length > 0
          )
        })
        .map((node) => node.querySelector('.cc__char')?.textContent?.trim())
        .filter(Boolean)
      return { total, chars }
    })

  const first = await snapshot()
  if (first.total < 500) throw new Error(`字库规模只有 ${first.total}，Round 4 要求至少 500 字`)
  if (!first.chars.length) throw new Error('字表首屏没有渲染单字卡')
  if (first.chars.length >= first.total) {
    throw new Error(`首屏一次挂载 ${first.chars.length}/${first.total} 张卡片，未启用分页`)
  }

  const reached = new Set(first.chars)
  let mountedMax = first.chars.length
  let turns = 0
  let unchanged = 0
  let previous = first.chars.join('|')

  // 字表按单元翻页，单元数会随字库增长；上限只是防死循环，留足余量即可。
  while (reached.size < first.total && turns < 150) {
    const clicked = await page.evaluate(() => {
      const nextPattern = /下一页|下一批|加载更多|显示更多|查看更多|更多汉字/
      const controls = [...document.querySelectorAll('button, a')].filter((node) => {
        const style = getComputedStyle(node)
        return (
          !node.disabled &&
          node.getAttribute('aria-disabled') !== 'true' &&
          style.display !== 'none' &&
          style.visibility !== 'hidden' &&
          node.getClientRects().length > 0
        )
      })
      const control = controls.find((node) =>
        nextPattern.test(`${node.innerText} ${node.getAttribute('aria-label') ?? ''}`)
      )
      if (!control) return ''
      const label = control.innerText.trim() || control.getAttribute('aria-label') || '下一页'
      control.click()
      return label
    })
    if (!clicked) break

    turns += 1
    await new Promise((r) => setTimeout(r, 350))
    const current = await snapshot()
    mountedMax = Math.max(mountedMax, current.chars.length)
    current.chars.forEach((char) => reached.add(char))
    const signature = current.chars.join('|')
    unchanged = signature === previous ? unchanged + 1 : 0
    previous = signature
    if (unchanged >= 2) break
  }

  if (mountedMax > 50) {
    throw new Error(`分页过程中同时挂载 ${mountedMax} 张卡片，超过 50 张 DOM 预算`)
  }
  if (reached.size < first.total) {
    throw new Error(`分页只覆盖 ${reached.size}/${first.total} 个字（翻页 ${turns} 次）`)
  }

  return `总数=${first.total}，首屏=${first.chars.length}，最大挂载=${mountedMax}，翻页=${turns}`
})

await interact('听音识字：开始并答 3 题', '/#/listen', async (page) => {
  const started = await clickText(page, '开始')
  let answered = 0
  for (let i = 0; i < 3; i++) {
    const ok = await page.evaluate(() => {
      const cards = [...document.querySelectorAll('button')].filter(
        (b) => /^[\u4e00-\u9fa5]$/.test(b.innerText.trim().split('\n')[0])
      )
      if (!cards.length) return false
      cards[0].click()
      return true
    })
    if (ok) answered++
    await new Promise((r) => setTimeout(r, 1700))
  }
  return `开始按钮=${started}，作答 ${answered} 次`
})

await interact('绘本：连续翻页到读完', '/#/books/b1', async (page) => {
  let turns = 0
  for (let i = 0; i < 8; i++) {
    if (await clickText(page, '下一页')) turns++
    else if (await clickText(page, '读完啦')) {
      turns++
      break
    } else break
  }
  const done = await page.evaluate(() => document.body.innerText.includes('读完'))
  return `翻页 ${turns} 次，出现读完页=${done}`
})

await interact('成语：走完小剧场', '/#/idioms/szdt', async (page) => {
  let n = 0
  for (let i = 0; i < 8; i++) {
    const advanced =
      (await clickText(page, '接下来')) ||
      (await clickText(page, '下一幕')) ||
      (await clickText(page, '看懂了')) ||
      (await clickText(page, '后来呢'))
    if (!advanced) break
    n++
  }
  const shown = await page.evaluate(() => {
    const t = document.body.innerText
    return /告诉我们|寓意|想一想|懂了/.test(t)
  })
  return `推进 ${n} 步，剧场走到结尾=${shown}`
})

await interact('听音识字：换皮到地鼠草地', '/#/listen', async (page) => {
  const picked = await clickText(page, '地鼠草地')
  await clickText(page, '开始')
  const scene = await page.evaluate(() => ({
    board: !!document.querySelector('.board--mole'),
    moles: document.querySelectorAll('.opt--mole').length,
    fish: document.querySelectorAll('.opt--fish').length
  }))
  if (!picked) throw new Error('找不到「地鼠草地」换皮按钮')
  if (!scene.board || scene.moles !== 4) {
    throw new Error(`换皮没生效：board--mole=${scene.board}，地鼠 ${scene.moles} 只`)
  }
  if (scene.fish) throw new Error('换皮后还残留着钓鱼池的皮')
  return `选中地鼠草地=${picked}，渲染 ${scene.moles} 只地鼠`
})

/* ---------------------------------------------- 交互：三款识字小游戏各走一局 */

await interact('字迷宫：只用键盘走到目标字并踩中', '/#/games/maze', async (page) => {
  if (!(await clickText(page, '进迷宫'))) throw new Error('字迷宫缺少「进迷宫」入口')
  await page.waitForSelector('.maze__cell[data-player="true"]', { timeout: 8000 })

  // 开局焦点要自己落到迷宫上，键盘用户不该先按一串 Tab 才能走第一步
  const focused = await page.evaluate(
    () => document.activeElement?.classList.contains('maze__stage') ?? false
  )
  if (!focused) throw new Error('进迷宫后焦点没有落到迷宫区，键盘走不了')

  const readMaze = () =>
    page.evaluate(() => {
      const maze = document.querySelector('.maze')
      if (!maze) return null
      const cells = [...maze.querySelectorAll('.maze__cell')].map((node) => ({
        x: Number(node.dataset.x),
        y: Number(node.dataset.y),
        wall: node.dataset.wall === 'true',
        char: node.dataset.char ?? '',
        player: node.dataset.player === 'true'
      }))
      const hud = document.body.innerText
      return {
        cols: Number(maze.dataset.cols),
        rows: Number(maze.dataset.rows),
        cells,
        target: document.querySelector('.quest__char')?.textContent.trim() ?? '',
        score: Number(hud.match(/⭐\s*(\d+)/)?.[1] ?? 0)
      }
    })

  const board = await readMaze()
  if (!board) throw new Error('迷宫没有渲染出来')
  if (board.cells.length !== board.cols * board.rows) {
    throw new Error(`迷宫格子数 ${board.cells.length} 与 ${board.cols}×${board.rows} 对不上`)
  }
  if (!board.cells.some((c) => c.wall)) throw new Error('迷宫里一堵墙都没有，等于没有迷宫')
  if (!board.target) throw new Error('题面没有显示要找的字')

  const me = board.cells.find((c) => c.player)
  const goal = board.cells.find((c) => c.char === board.target)
  if (!goal) throw new Error(`目标字「${board.target}」没有摆进迷宫`)

  // 迷宫是完美迷宫（无环全连通），BFS 出来的就是唯一那条路
  const key = (x, y) => `${x},${y}`
  const open = new Map(board.cells.filter((c) => !c.wall).map((c) => [key(c.x, c.y), c]))
  const prev = new Map([[key(me.x, me.y), null]])
  const queue = [me]
  while (queue.length) {
    const cur = queue.shift()
    if (cur.x === goal.x && cur.y === goal.y) break
    for (const [dx, dy] of [
      [0, -1],
      [0, 1],
      [-1, 0],
      [1, 0]
    ]) {
      const next = open.get(key(cur.x + dx, cur.y + dy))
      if (!next || prev.has(key(next.x, next.y))) continue
      prev.set(key(next.x, next.y), cur)
      queue.push(next)
    }
  }
  if (!prev.has(key(goal.x, goal.y))) throw new Error('目标字所在的格子走不到，迷宫不连通')

  const path = []
  for (let node = goal; node; node = prev.get(key(node.x, node.y))) path.unshift(node)

  const KEY_OF = { '0,-1': 'ArrowUp', '0,1': 'ArrowDown', '-1,0': 'ArrowLeft', '1,0': 'ArrowRight' }
  for (let i = 1; i < path.length; i += 1) {
    const step = KEY_OF[`${path[i].x - path[i - 1].x},${path[i].y - path[i - 1].y}`]
    await page.keyboard.press(step)
    await new Promise((r) => setTimeout(r, 90))
  }

  await page.waitForFunction(
    () => Number(document.body.innerText.match(/⭐\s*(\d+)/)?.[1] ?? 0) >= 1,
    { timeout: 6000 }
  )
  const said = await page.evaluate(
    () => document.querySelector('.maze-game .sr-only[aria-live="polite"]')?.innerText ?? ''
  )
  if (!/踩中了|已经找到/.test(said)) throw new Error(`踩中目标字后没有播报：「${said}」`)

  // 撞墙也要有反馈，否则读屏用户只会觉得按键失灵
  await page.keyboard.press('ArrowUp')
  await page.keyboard.press('ArrowLeft')
  await new Promise((r) => setTimeout(r, 200))

  return `迷宫 ${board.cols}×${board.rows}，键盘走 ${path.length - 1} 步踩中「${board.target}」`
})

await interact('配对记忆：翻牌配对直到全清', '/#/games/memory', async (page) => {
  if (!(await clickText(page, '开始翻牌'))) throw new Error('配对记忆缺少「开始翻牌」入口')
  await page.waitForSelector('.mcard', { timeout: 8000 })

  const snapshot = () =>
    page.evaluate(() =>
      [...document.querySelectorAll('.mcard')].map((node) => ({
        state: node.dataset.state ?? '',
        face: node.dataset.face ?? '',
        char: node.dataset.char ?? ''
      }))
    )

  const opening = await snapshot()
  if (!opening.length) throw new Error('牌桌上一张牌都没有')
  if (opening.some((card) => card.char)) {
    throw new Error('盖着的牌把汉字写进了 DOM，读屏会直接把答案念出来')
  }

  /** 一律走键盘：聚焦那张牌，回车翻开——顺带证明牌是真的可聚焦按钮。 */
  const flipCard = async (index) => {
    const focused = await page.evaluate((i) => {
      const node = document.querySelectorAll('.mcard')[i]
      if (!node || node.disabled) return false
      node.focus()
      return document.activeElement === node
    }, index)
    if (!focused) return false
    await page.keyboard.press('Enter')
    return true
  }

  /** 像人一样玩：翻开过的牌记在 known 里，凑齐一对就去收。 */
  const known = new Map()
  let flips = 0
  for (let turn = 0; turn < 40; turn += 1) {
    const cards = await snapshot()
    if (!cards.length) break

    cards.forEach((card, i) => {
      if (card.char) known.set(i, `${card.char}|${card.face}`)
    })
    const down = cards
      .map((card, i) => ({ ...card, i }))
      .filter((card) => card.state === 'down')
    if (!down.length) break

    const remembered = down.filter((card) => known.has(card.i))
    const pair = remembered.find((a) =>
      remembered.some(
        (b) =>
          b.i !== a.i &&
          known.get(b.i).split('|')[0] === known.get(a.i).split('|')[0] &&
          known.get(b.i).split('|')[1] !== known.get(a.i).split('|')[1]
      )
    )

    let first
    let second
    if (pair) {
      first = pair.i
      second = remembered.find(
        (b) =>
          b.i !== pair.i &&
          known.get(b.i).split('|')[0] === known.get(pair.i).split('|')[0] &&
          known.get(b.i).split('|')[1] !== known.get(pair.i).split('|')[1]
      ).i
    } else {
      first = (down.find((card) => !known.has(card.i)) ?? down[0]).i
    }

    if (!(await flipCard(first))) break
    flips += 1
    await new Promise((r) => setTimeout(r, 260))

    if (second === undefined) {
      const afterFirst = await snapshot()
      afterFirst.forEach((card, i) => {
        if (card.char) known.set(i, `${card.char}|${card.face}`)
      })
      const face = known.get(first)
      const partner = afterFirst
        .map((card, i) => ({ ...card, i }))
        .find(
          (card) =>
            card.i !== first &&
            card.state === 'down' &&
            known.has(card.i) &&
            known.get(card.i).split('|')[0] === face?.split('|')[0] &&
            known.get(card.i).split('|')[1] !== face?.split('|')[1]
        )
      second =
        partner?.i ??
        afterFirst
          .map((card, i) => ({ ...card, i }))
          .find((card) => card.i !== first && card.state === 'down' && !known.has(card.i))?.i
    }
    if (second === undefined) break

    if (!(await flipCard(second))) break
    flips += 1
    await new Promise((r) => setTimeout(r, 300))

    const settled = await snapshot()
    settled.forEach((card, i) => {
      if (card.char) known.set(i, `${card.char}|${card.face}`)
    })
    // 配错了要等它盖回去，锁着的时候点什么都没用
    if (settled[first]?.state !== 'matched') await new Promise((r) => setTimeout(r, 950))
  }

  // 最后一对配上之后，结算页要过一小会儿才顶上来
  await page
    .waitForFunction(() => document.body.innerText.includes('全部配对完成'), { timeout: 4000 })
    .catch(() => {})
  const done = await page.evaluate(() => document.body.innerText.includes('全部配对完成'))
  if (!done) throw new Error(`翻了 ${flips} 次还没配完，牌桌没有清空`)

  return `只用回车翻 ${flips} 次清空牌桌，盖着的牌不泄露答案`
})

await interact('找不同：找出唯一不同的字，键盘连过 3 关', '/#/games/spot', async (page) => {
  if (!(await clickText(page, '开始找'))) throw new Error('找不同缺少「开始找」入口')
  await page.waitForSelector('.spot__cell', { timeout: 8000 })

  let solved = 0
  for (let r = 0; r < 3; r += 1) {
    await page.waitForFunction(
      () => document.querySelector('.spot')?.dataset.answered === 'false',
      { timeout: 8000 }
    )
    const board = await page.evaluate(() => {
      const cells = [...document.querySelectorAll('.spot__cell')]
      const counts = {}
      for (const node of cells) counts[node.dataset.char] = (counts[node.dataset.char] ?? 0) + 1
      const odd = Object.keys(counts).find((char) => counts[char] === 1)
      return {
        total: cells.length,
        kinds: Object.keys(counts).length,
        odd,
        index: cells.findIndex((node) => node.dataset.char === odd)
      }
    })
    if (board.total < 9) throw new Error(`格子只有 ${board.total} 个，题面太小`)
    if (board.kinds !== 2 || !board.odd) {
      throw new Error(`一关里出现 ${board.kinds} 种字，「找不同」应当只有 1 个字与众不同`)
    }

    // 只用键盘作答：聚焦那个格子，回车提交
    await page.evaluate((i) => document.querySelectorAll('.spot__cell')[i].focus(), board.index)
    await page.keyboard.press('Enter')
    await new Promise((r2) => setTimeout(r2, 450))

    const said = await page.evaluate(
      () => document.querySelector('.spot-game .sr-only[aria-live="polite"]')?.innerText ?? ''
    )
    if (!/答对了/.test(said)) throw new Error(`第 ${r + 1} 关按回车没有判对：「${said}」`)
    solved += 1
    await new Promise((r2) => setTimeout(r2, 900))
  }

  const score = await page.evaluate(() =>
    Number(document.body.innerText.match(/⭐\s*(\d+)/)?.[1] ?? 0)
  )
  if (score < solved) throw new Error(`连过 ${solved} 关但计分只有 ${score}`)

  return `键盘连过 ${solved} 关，计分 ${score}`
})

await interact('拼音拼字：只用键盘拼完一关', '/#/games/spell', async (page) => {
  if (!(await clickText(page, '开始拼'))) throw new Error('拼音拼字缺少「开始拼」入口')
  await page.waitForSelector('.spell__key', { timeout: 8000 })

  // 题面上的拼音是带调的，牌面是不带调的；对照之前先把调去掉
  const readRound = () =>
    page.evaluate(() => {
      const TONES = {
        ā: 'a', á: 'a', ǎ: 'a', à: 'a',
        ē: 'e', é: 'e', ě: 'e', è: 'e',
        ī: 'i', í: 'i', ǐ: 'i', ì: 'i',
        ō: 'o', ó: 'o', ǒ: 'o', ò: 'o',
        ū: 'u', ú: 'u', ǔ: 'u', ù: 'u',
        ǖ: 'ü', ǘ: 'ü', ǚ: 'ü', ǜ: 'ü'
      }
      const pinyin = document.querySelector('.quest__pinyin')?.textContent.trim() ?? ''
      return {
        char: document.querySelector('.quest__char')?.textContent.trim() ?? '',
        answer: [...pinyin]
          .map((ch) => TONES[ch] ?? ch.toLowerCase())
          .filter((ch) => /[a-zü]/.test(ch)),
        slots: document.querySelectorAll('.spell__slot').length,
        keys: [...document.querySelectorAll('.spell__key')].map((node) => node.dataset.letter)
      }
    })

  const first = await readRound()
  if (!first.answer.length) throw new Error('题面上没有拼音，拼不出来')
  if (first.slots !== first.answer.length) {
    throw new Error(`「${first.char}」有 ${first.answer.length} 个字母，却摆了 ${first.slots} 个格子`)
  }
  if (first.keys.length <= first.answer.length) {
    throw new Error('字母牌里没有混干扰牌，把牌全按一遍就能过关')
  }

  // 先摆一张错牌：答案里用不上的那张，必须被拒收
  const wrong = first.keys.find((letter) => !first.answer.includes(letter))
  if (!wrong) throw new Error('找不到干扰牌')
  await page.evaluate((letter) => {
    document.querySelector(`.spell__key[data-letter="${letter}"]`)?.click()
  }, wrong)
  await new Promise((r) => setTimeout(r, 250))
  const refused = await page.evaluate(
    () => document.querySelector('.spell__slots')?.dataset.filled === '0'
  )
  if (!refused) throw new Error('摆错的字母也被放进了格子里')

  // 再只用键盘拼完：聚焦牌、回车摆牌
  for (const letter of first.answer) {
    const ok = await page.evaluate((want) => {
      const node = [...document.querySelectorAll('.spell__key')].find(
        (btn) => btn.dataset.letter === want && !btn.disabled
      )
      if (!node) return false
      node.focus()
      return document.activeElement === node
    }, letter)
    if (!ok) throw new Error(`牌面上找不到还没用过的「${letter}」`)
    await page.keyboard.press('Enter')
    await new Promise((r) => setTimeout(r, 180))
  }

  const said = await page.evaluate(
    () => document.querySelector('.spell-game .sr-only[aria-live="polite"]')?.innerText ?? ''
  )
  if (!/拼对啦/.test(said)) throw new Error(`拼完整个拼音没有判对：「${said}」`)

  // 判对后要自己接上下一关
  await page.waitForFunction(
    () => /第\s*2\s*\/\s*\d+\s*关/.test(document.body.innerText),
    { timeout: 6000 }
  )
  const score = await page.evaluate(() =>
    Number(document.body.innerText.match(/⭐\s*(\d+)/)?.[1] ?? 0)
  )
  if (score < 1) throw new Error('拼对一关但计分还是 0')

  return `键盘拼出「${first.char}」= ${first.answer.join('')}（${first.keys.length} 张牌，含干扰牌），错牌被拒收`
})

await interact('接字大冒险：键盘挪篮子接住目标字', '/#/games/catch', async (page) => {
  if (!(await clickText(page, '开始接字'))) throw new Error('接字大冒险缺少「开始接字」入口')
  await page.waitForSelector('.catch__field', { timeout: 8000 })

  const readField = () =>
    page.evaluate(() => {
      const stage = document.querySelector('.catch')
      return {
        alive: !!stage,
        lane: Number(stage?.dataset.lane ?? -1),
        basket: !!document.querySelector('.catch__basket'),
        score: Number(stage?.dataset.score ?? 0),
        lives: Number(stage?.dataset.lives ?? 0),
        items: [...document.querySelectorAll('.catch__item')].map((node) => ({
          char: node.dataset.char,
          lane: Number(node.dataset.lane),
          row: Number(node.dataset.row),
          target: node.dataset.target === 'true'
        }))
      }
    })

  const opening = await readField()
  if (!opening.basket) throw new Error('轨道上没有篮子')
  if (opening.lives !== 3) throw new Error(`开局应当有 3 颗心，实际 ${opening.lives}`)

  const focused = await page.evaluate(
    () => document.activeElement?.classList.contains('catch') ?? false
  )
  if (!focused) throw new Error('开局焦点没有落到轨道上，键盘挪不动篮子')

  // 一直跟着最靠下的那个目标字挪篮子，接住一个就够证明这条链路是通的
  let moves = 0
  let caught = 0
  for (let step = 0; step < 80 && !caught; step += 1) {
    const field = await readField()
    if (field.score >= 1) {
      caught = field.score
      break
    }
    if (!field.alive) throw new Error('还没接到目标字，牌面就没了（多半是心用完了）')

    const chase = field.items.filter((it) => it.target).sort((a, b) => b.row - a.row)[0]
    // 目标字之前先落到篮子里的干扰字，要提前躲开，别把心浪费掉
    const danger = field.items
      .filter((it) => !it.target && it.lane === field.lane)
      .sort((a, b) => b.row - a.row)[0]

    let key = null
    if (chase && chase.lane !== field.lane && (!danger || danger.row <= chase.row)) {
      key = chase.lane > field.lane ? 'ArrowRight' : 'ArrowLeft'
    } else if (danger && (!chase || chase.lane !== field.lane || danger.row > chase.row)) {
      key = field.lane < 3 ? 'ArrowRight' : 'ArrowLeft'
    }

    if (key) {
      await page.keyboard.press(key)
      moves += 1
      continue
    }
    await new Promise((r) => setTimeout(r, 200))
  }

  if (!caught) throw new Error(`挪了 ${moves} 次篮子也没接到目标字`)
  const said = await page.evaluate(
    () => document.querySelector('.catch-game .sr-only[aria-live="polite"]')?.innerText ?? ''
  )
  if (!/接住|这一波/.test(said)) throw new Error(`接住之后没有播报：「${said}」`)

  return `键盘挪 ${moves} 次篮子接住 ${caught} 个目标字`
})

await interact('接字大冒险：减少动效时节拍放慢且不做过渡', '/#/games/catch', async (page) => {
  await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }])
  await page.reload({ waitUntil: 'networkidle2', timeout: 20000 })
  await new Promise((r) => setTimeout(r, 400))

  const noticed = await page.evaluate(
    () => document.querySelector('.catch__calm')?.dataset.quiet === 'true'
  )
  if (!noticed) throw new Error('系统要求减少动态，开始页却没有说明节奏已经放慢')

  if (!(await clickText(page, '开始接字'))) throw new Error('减少动效下进不去游戏')
  await page.waitForSelector('.catch__field', { timeout: 8000 })
  await page.waitForSelector('.catch__item', { timeout: 8000 })

  const quiet = await page.evaluate(() => {
    const stage = document.querySelector('.catch')
    const item = document.querySelector('.catch__item')
    const basket = document.querySelector('.catch__basket')
    return {
      flagged: stage?.classList.contains('catch--quiet') ?? false,
      item: item ? getComputedStyle(item).transitionProperty : 'none',
      basket: basket ? getComputedStyle(basket).transitionProperty : 'none'
    }
  })
  if (!quiet.flagged) throw new Error('减少动态时舞台没有切到安静模式')
  if (quiet.item !== 'none') throw new Error(`掉落的字还挂着过渡：${quiet.item}`)
  if (quiet.basket !== 'none') throw new Error(`篮子还挂着过渡：${quiet.basket}`)

  // 慢节拍下一拍要 1.25 秒，600 毫秒内不该出现两次下落
  const before = await page.evaluate(() =>
    [...document.querySelectorAll('.catch__item')].map((n) => `${n.dataset.char}:${n.dataset.row}`)
  )
  await new Promise((r) => setTimeout(r, 600))
  const after = await page.evaluate(() =>
    [...document.querySelectorAll('.catch__item')].map((n) => `${n.dataset.char}:${n.dataset.row}`)
  )
  const dropped = after.filter((sig) => !before.includes(sig)).length
  if (dropped > 2) throw new Error(`慢节拍 600ms 内掉了 ${dropped} 格，节奏没有放慢`)

  return `安静模式：字与篮子都无过渡，600ms 内只挪 ${dropped} 格`
})

await interact('绘本：逐句朗读高亮 + 点字发音', '/#/books/b1', async (page) => {
  await clickText(page, '读给我听')
  await new Promise((r) => setTimeout(r, 600))

  const lit = await page.evaluate(() => {
    const marked = [...document.querySelectorAll('.glyph.is-reading')]
    const all = document.querySelectorAll('.glyph').length
    return { marked: marked.length, all, text: marked.map((n) => n.innerText).join('') }
  })
  if (!lit.marked) throw new Error('点了「读给我听」但没有任何字被高亮')
  if (lit.marked >= lit.all) throw new Error('整页都高亮了，说明没有逐句只是整页刷色')

  // 点一个字：应当停下逐句朗读，并弹出这个字的拼音释义
  const tapped = await page.evaluate(() => {
    const g = [...document.querySelectorAll('.glyph')].find(
      (n) => !n.classList.contains('glyph--punct')
    )
    if (!g) return null
    g.click()
    return g.innerText.trim()
  })
  await new Promise((r) => setTimeout(r, 350))
  const peek = await page.evaluate(() => {
    const box = document.querySelector('.peek')
    return box ? box.innerText.replace(/\s+/g, ' ').trim() : ''
  })
  if (!peek.includes(tapped)) throw new Error(`点「${tapped}」没有弹出发音卡片`)

  return `高亮 ${lit.marked}/${lit.all} 字（「${lit.text}」），点「${tapped}」弹出：${peek}`
})

await interact('成语头图：跟着 data-theme 换色', '/#/idioms/szdt', async (page) => {
  const read = () =>
    page.evaluate(() => {
      const hero = document.querySelector('.hero')
      return hero ? getComputedStyle(hero).backgroundImage : ''
    })
  const sunny = await read()
  await page.evaluate(() => {
    document.documentElement.dataset.theme = 'night'
  })
  await new Promise((r) => setTimeout(r, 350))
  const night = await read()

  if (!sunny || sunny === 'none') throw new Error('头图没有渐变背景')
  if (sunny === night) throw new Error('切到夜间主题后头图配色没变，说明还是写死的调色板')
  return '明亮 / 夜间两套主题下头图背景各不相同'
})

// 用 b3：前面的绘本用例已经把 b1 读完了，而「第一次读完」才发庆祝
await interact('庆祝动画：播报完整且可以立刻跳过', '/#/books/b3', async (page) => {
  await page.waitForSelector('.reader .spread', { timeout: 10000 })
  for (let i = 0; i < 8; i++) {
    if (await clickText(page, '下一页')) continue
    if (await clickText(page, '读完啦')) break
    break
  }
  await page.waitForSelector('.cel', { timeout: 5000 })

  const before = await page.evaluate(() => ({
    open: !!document.querySelector('.cel'),
    skip: !!document.querySelector('.cel__skip'),
    live: document.querySelector('.cel [aria-live="polite"]')?.innerText.trim() ?? '',
    prohibited: !!document.querySelector('.cel span[aria-label]:not([role])')
  }))
  if (!before.open) throw new Error('读完整本没有弹出庆祝层')
  if (!before.skip) throw new Error('庆祝层没有跳过按钮')
  if (!before.live.includes('跳过')) throw new Error('庆祝播报没有告诉用户可以跳过')
  if (before.prohibited) throw new Error('庆祝层里有 span 直接挂 aria-label（axe aria-prohibited-attr）')

  await page.evaluate(() => document.querySelector('.cel__skip').click())
  await new Promise((r) => setTimeout(r, 250))
  const gone = await page.evaluate(() => !document.querySelector('.cel'))
  if (!gone) throw new Error('点了跳过但庆祝层还在')

  // 跳过后状态要和播完一样：奖励的星星已经进账，读完页正常显示
  const settled = await page.evaluate(() => document.body.innerText.includes('读完啦'))
  if (!settled) throw new Error('跳过庆祝后没有回到读完页')
  return `播报「${before.live.slice(0, 18)}…」→ 点跳过 → 立即回到读完页`
})

await interact('家长中心：过验证并切主题', '/#/parent', async (page) => {
  const solved = await page.evaluate(() => {
    const label = document.body.innerText.match(/(\d+)\s*\+\s*(\d+)/)
    const input = document.querySelector('input[type="number"]')
    if (!label || !input) return false
    const setter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype,
      'value'
    ).set
    setter.call(input, String(Number(label[1]) + Number(label[2])))
    input.dispatchEvent(new Event('input', { bubbles: true }))
    return true
  })
  await new Promise((r) => setTimeout(r, 200))
  await clickText(page, '进入')
  const inside = await page.evaluate(() => document.body.innerText.includes('使用设置'))
  const switched = await clickText(page, '护眼模式')
  await new Promise((r) => setTimeout(r, 350))
  const theme = await page.evaluate(() => document.documentElement.dataset.theme)
  // 主题要能写进 localStorage，刷新后保持
  await page.reload({ waitUntil: 'networkidle2' })
  await new Promise((r) => setTimeout(r, 400))
  const after = await page.evaluate(() => document.documentElement.dataset.theme)
  return `解锁=${solved && inside}，点护眼=${switched}，theme=${theme}，刷新后=${after}`
})

await interact('进度追踪：学过的字刷新后仍在', `/#/learn/${encodeURIComponent('山')}`, async (page) => {
  await new Promise((r) => setTimeout(r, 800))
  const stored = await page.evaluate(() => {
    const key = Object.keys(localStorage).find((k) => (localStorage.getItem(k) ?? '').includes('"chars"'))
    if (!key) return null
    const data = JSON.parse(localStorage.getItem(key))
    const s = data.data ?? data
    return { key, chars: Object.keys(s.chars ?? {}) }
  })
  if (!stored) return '没有找到进度存档'

  // 换个字再回来，确认累加而不是覆盖
  await page.goto(page.url().replace(/#.*$/, `#/learn/${encodeURIComponent('水')}`))
  await new Promise((r) => setTimeout(r, 800))
  await page.reload({ waitUntil: 'networkidle2' })
  await new Promise((r) => setTimeout(r, 800))

  const after = await page.evaluate((key) => {
    const data = JSON.parse(localStorage.getItem(key))
    const s = data.data ?? data
    return Object.keys(s.chars ?? {})
  }, stored.key)

  const ok = after.includes('山') && after.includes('水')
  return `存档键=${stored.key}，刷新后记录了 ${after.length} 个字（山+水 都在=${ok}）`
})

await interact('描红：键盘替代通道可以写完整个字', `/#/learn/${encodeURIComponent('日')}`, async (page) => {
  await page.evaluate(() => localStorage.clear())
  await page.reload({ waitUntil: 'networkidle2' })
  await page.waitForSelector('.hz__host svg', { timeout: 8000 })

  if (!(await clickText(page, '我来写'))) throw new Error('单字页缺少「我来写」描红入口')
  await new Promise((r) => setTimeout(r, 400))

  const staged = await page.evaluate(() => {
    const stage = document.querySelector('.hz__stage')
    return {
      focusable: stage?.getAttribute('tabindex') === '0',
      focused: document.activeElement === stage,
      labelled: (stage?.getAttribute('aria-label') ?? '').includes('Esc'),
      live: document.querySelector('.hz__hint')?.getAttribute('aria-live') === 'polite'
    }
  })
  if (!staged.focusable) throw new Error('描红时田字格不可聚焦，键盘进不去')
  if (!staged.focused) throw new Error('进入描红后焦点没有落到田字格上')
  if (!staged.labelled) throw new Error('描红区没有说明键盘怎么用')
  if (!staged.live) throw new Error('描红提示不是 aria-live 播报区')

  // 「日」四笔：只用键盘，一笔一笔写完
  for (let i = 0; i < 6; i++) {
    const done = await page.evaluate(() => /满分|写完啦/.test(document.querySelector('.hz__hint')?.innerText ?? ''))
    if (done) break
    await page.keyboard.press('Space')
    await new Promise((r) => setTimeout(r, 320))
  }

  const finished = await page.evaluate(() => ({
    hint: document.querySelector('.hz__hint')?.innerText.trim() ?? '',
    traced: JSON.parse(localStorage.getItem('happy-literacy:v1') ?? '{}')?.chars?.['日']?.traced ?? 0
  }))
  if (!/满分|写完啦/.test(finished.hint)) {
    throw new Error(`键盘写完全部笔画后没有完成提示：「${finished.hint}」`)
  }
  if (finished.traced < 1) throw new Error('键盘写完一个字没有记进「会写了」')

  // 跳过通道：再进一次描红，按 Esc 应当直接退出
  if (!(await clickText(page, '我来写'))) throw new Error('完成后无法再次进入描红')
  await new Promise((r) => setTimeout(r, 300))
  await page.keyboard.press('Escape')
  await new Promise((r) => setTimeout(r, 300))
  const escaped = await page.evaluate(() => ({
    quizOff: document.querySelector('.hz__stage')?.getAttribute('tabindex') !== '0',
    hint: document.querySelector('.hz__hint')?.innerText ?? ''
  }))
  if (!escaped.quizOff) throw new Error('按 Esc 之后还停在描红状态')
  if (!escaped.hint.includes('跳过')) throw new Error('跳过描红没有给出提示')

  return `键盘写完「日」（traced=${finished.traced}），Esc 可跳过`
})

/** 在田字格里拖一笔；坐标是 svg 内的相对位置（0-1）。 */
const drawStroke = async (page, from, to) => {
  const box = await page.evaluate(() => {
    const svg = document.querySelector('.hz__host svg')
    if (!svg) return null
    const r = svg.getBoundingClientRect()
    return { x: r.x, y: r.y, w: r.width, h: r.height }
  })
  if (!box) throw new Error('田字格里没有 svg，无法模拟书写')
  const at = (t) => ({ x: box.x + t.x * box.w, y: box.y + t.y * box.h })
  const a = at(from)
  const b = at(to)
  await page.mouse.move(a.x, a.y)
  await page.mouse.down()
  for (let i = 1; i <= 8; i += 1) {
    await page.mouse.move(a.x + ((b.x - a.x) * i) / 8, a.y + ((b.y - a.y) * i) / 8)
  }
  await page.mouse.up()
  await new Promise((r) => setTimeout(r, 220))
}

const phaseOf = (page) => page.evaluate(() => document.querySelector('.detail')?.dataset.phase ?? '')

const waitPhase = (page, want, timeout = 12000) =>
  page.waitForFunction(
    (id) => document.querySelector('.detail')?.dataset.phase === id,
    { timeout },
    want
  )

await interact('单字五步状态机：认→写→听→考→奖自动衔接', `/#/learn/${encodeURIComponent('日')}`, async (page) => {
  await page.evaluate(() => localStorage.clear())
  await page.reload({ waitUntil: 'networkidle2' })
  await page.waitForSelector('.rail__step', { timeout: 8000 })

  const rail = await page.evaluate(() =>
    [...document.querySelectorAll('.rail__step')].map((n) => n.dataset.step)
  )
  const want = ['intro', 'trace', 'listen', 'quiz', 'reward']
  if (rail.join(',') !== want.join(',')) {
    throw new Error(`步骤条不是五步 ${want.join('→')}，实际是 ${rail.join('→')}`)
  }
  if ((await phaseOf(page)) !== 'intro') throw new Error('进页面没有停在「认一认」')

  // 认一认：听一次读音就应当自动排上「写一写」
  if (!(await clickText(page, '怎么读'))) throw new Error('「认一认」缺少听读音按钮')
  const queued = await page.evaluate(() => document.querySelector('.autonext')?.innerText ?? '')
  if (!queued.includes('写一写')) throw new Error(`听完读音没有预告下一步：「${queued}」`)
  if (!queued.includes('等一下')) throw new Error('自动衔接没有给「等一下」的按停出口')
  await waitPhase(page, 'trace')

  // 写一写：进入这一步田字格会自己开始描红，用「写下一笔」写完
  await page.waitForFunction(
    () => document.querySelector('.hz__stage')?.getAttribute('tabindex') === '0',
    { timeout: 8000 }
  )
  for (let i = 0; i < 8; i += 1) {
    const done = await page.evaluate(() =>
      /满分|写完啦/.test(document.querySelector('.hz__hint')?.innerText ?? '')
    )
    if (done) break
    if (!(await clickText(page, '写下一笔'))) break
  }
  await waitPhase(page, 'listen')

  // 听一听 / 考一考：都选正确项，每一步作答后自动进入下一步
  const pickAnswer = async (label) => {
    await page.waitForSelector('.opt[data-char="日"]', { timeout: 8000 })
    const ok = await page.evaluate(() => {
      const btn = document.querySelector('.opt[data-char="日"]')
      if (!btn || btn.disabled) return false
      btn.click()
      return true
    })
    if (!ok) throw new Error(`「${label}」里点不到正确选项`)
  }
  await pickAnswer('听一听')
  await waitPhase(page, 'quiz')
  await pickAnswer('考一考')
  await waitPhase(page, 'reward')

  const settled = await page.evaluate(() => {
    const saved = JSON.parse(localStorage.getItem('happy-literacy:v1') ?? '{}')
    return {
      flows: saved.flowsCompleted ?? 0,
      charFlows: saved.chars?.['日']?.flows ?? 0,
      traced: saved.chars?.['日']?.traced ?? 0,
      steps: [...document.querySelectorAll('.rail__step.is-done')].map((n) => n.dataset.step),
      reward: document.querySelector('.reward')?.innerText.replace(/\s+/g, ' ').trim() ?? ''
    }
  })
  if (settled.flows < 1) throw new Error('走完五步没有记下一次完整闭环')
  if (settled.charFlows < 1) throw new Error('「日」自己的闭环次数没有加上')
  if (settled.traced < 1) throw new Error('五步里的描红没有记进「会写了」')
  for (const step of ['intro', 'trace', 'listen', 'quiz']) {
    if (!settled.steps.includes(step)) throw new Error(`步骤条上「${step}」没有标成已完成`)
  }
  if (!settled.reward) throw new Error('「领奖励」这一步是空的')

  // 手动回跳：点步骤条应当能回到前面的步骤
  await page.evaluate(() => document.querySelector('.rail__step[data-step="listen"]')?.click())
  await waitPhase(page, 'listen', 5000)

  return `五步自动衔接完成（闭环 ${settled.flows} 次，描红 ${settled.traced} 遍），步骤条可回跳`
})

await interact('描红：同一笔连错 3 次自动示范这一笔', `/#/learn/${encodeURIComponent('日')}`, async (page) => {
  await page.evaluate(() => localStorage.clear())
  await page.reload({ waitUntil: 'networkidle2' })
  await page.waitForSelector('.hz__host svg', { timeout: 8000 })

  if (!(await clickText(page, '我来写'))) throw new Error('单字页缺少「我来写」描红入口')
  await new Promise((r) => setTimeout(r, 400))

  // 「日」第一笔是左边的竖；沿着顶边横着划三次，三次都不该被判对
  for (let i = 0; i < 3; i += 1) {
    await drawStroke(page, { x: 0.15, y: 0.08 }, { x: 0.85, y: 0.08 })
  }
  await page.waitForFunction(() => Number(document.querySelector('.hz')?.dataset.demos ?? 0) >= 1, {
    timeout: 8000
  })

  const state = await page.evaluate(() => ({
    demos: Number(document.querySelector('.hz')?.dataset.demos ?? 0),
    mistakes: Number(document.querySelector('.hz')?.dataset.mistakes ?? 0),
    hint: document.querySelector('.hz__hint')?.innerText.trim() ?? '',
    label: document.querySelector('.hz__stage')?.getAttribute('aria-label') ?? ''
  }))
  if (state.mistakes < 3) throw new Error(`只记到 ${state.mistakes} 次错笔，没能连错 3 次`)
  if (!/示范|看我写/.test(state.hint)) throw new Error(`自动示范没有播报出来：「${state.hint}」`)
  if (!state.label.includes('示范')) throw new Error('描红区没有说明连错会自动示范')

  // 示范完要把测验接回原处：还能继续写，写满全部笔画照样算完成
  await page.waitForFunction(
    () => !/示范|看我写/.test(document.querySelector('.hz__hint')?.innerText ?? ''),
    { timeout: 8000 }
  )
  for (let i = 0; i < 8; i += 1) {
    const done = await page.evaluate(() =>
      /满分|写完啦/.test(document.querySelector('.hz__hint')?.innerText ?? '')
    )
    if (done) break
    if (!(await clickText(page, '写下一笔'))) break
  }
  const finished = await page.evaluate(() => ({
    hint: document.querySelector('.hz__hint')?.innerText.trim() ?? '',
    traced: JSON.parse(localStorage.getItem('happy-literacy:v1') ?? '{}')?.chars?.['日']?.traced ?? 0
  }))
  if (!/写完啦|满分/.test(finished.hint)) {
    throw new Error(`示范后接不回测验，没写完：「${finished.hint}」`)
  }
  if (finished.traced < 1) throw new Error('示范后写完的这一遍没有记进「会写了」')
  if (!/错了\s*\d+\s*次/.test(finished.hint)) {
    throw new Error(`示范前的错笔数被重启测验清零了：「${finished.hint}」`)
  }

  return `连错 ${state.mistakes} 次触发 ${state.demos} 次自动示范，接回测验后写完（${finished.hint}）`
})

await interact('徽章：学会第一个字就点亮，首页与家长中心都看得见', '/#/', async (page) => {
  await page.evaluate(() => localStorage.clear())
  await page.goto(`${page.url().replace(/#.*$/, '')}#/learn/${encodeURIComponent('日')}`, {
    waitUntil: 'networkidle2'
  })
  await new Promise((r) => setTimeout(r, 700))

  // 徽章是单字页加载完详情包之后才落的账，机器忙的时候这一步会晚几百毫秒；
  // 等到存档里出现它再读，读不到就等满 5 秒，照样按「没解锁」报出来
  const badgesOf = () =>
    Object.keys(JSON.parse(localStorage.getItem('happy-literacy:v1') ?? '{}').badges ?? {})
  await page
    .waitForFunction(`(${badgesOf.toString()})().includes('first-step')`, { timeout: 5000 })
    .catch(() => {})

  const stored = await page.evaluate(badgesOf)
  if (!stored.includes('first-step')) {
    throw new Error(`学会第一个字后没有解锁「启蒙芽」，存档里只有：${stored.join('、') || '空'}`)
  }

  await page.goto(page.url().replace(/#.*$/, '#/'), { waitUntil: 'networkidle2' })
  await new Promise((r) => setTimeout(r, 500))
  const home = await page.evaluate(() => ({
    shelf: !!document.querySelector('.badges'),
    lit: document.querySelectorAll('.badge[data-unlocked="true"]').length,
    first: document.querySelector('.badge[data-badge="first-step"]')?.dataset.unlocked,
    chip: /徽章\s*\d+\/\d+/.test(document.body.innerText)
  }))
  if (!home.shelf) throw new Error('首页没有徽章架')
  if (home.first !== 'true') throw new Error('首页徽章架上「启蒙芽」还是灰的')
  if (!home.chip) throw new Error('首页顶部没有徽章数量')

  await page.goto(page.url().replace(/#.*$/, '#/parent'), { waitUntil: 'networkidle2' })
  // 家长中心是按需 chunk，机器忙的时候几百毫秒挂不上来；等口算门真出现再答题
  await page.waitForSelector('input[type="number"]', { timeout: 10000 })
  await page.evaluate(() => {
    const label = document.body.innerText.match(/(\d+)\s*\+\s*(\d+)/)
    const input = document.querySelector('input[type="number"]')
    if (!label || !input) return
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
    setter.call(input, String(Number(label[1]) + Number(label[2])))
    input.dispatchEvent(new Event('input', { bubbles: true }))
  })
  await new Promise((r) => setTimeout(r, 200))
  await clickText(page, '进入')
  await page.waitForSelector('.badge', { timeout: 10000 }).catch(() => {})

  const parent = await page.evaluate(() => ({
    total: document.querySelectorAll('.badge').length,
    lit: document.querySelectorAll('.badge[data-unlocked="true"]').length,
    locked: document.querySelectorAll('.badge[data-unlocked="false"] .badge__fill').length,
    wall: document.body.innerText.includes('成就徽章墙')
  }))
  if (!parent.wall) throw new Error('家长中心没有徽章墙')
  if (parent.total < 5) throw new Error(`徽章种类只有 ${parent.total} 种，Round 4 要求至少 5 种`)
  if (parent.lit < 1) throw new Error('家长中心徽章墙上一枚都没点亮')
  if (!parent.locked) throw new Error('未解锁的徽章没有显示进度条')

  return `首页点亮 ${home.lit} 枚；家长中心共 ${parent.total} 枚（点亮 ${parent.lit}，${parent.locked} 枚带进度条）`
})

await interact('播报：答题有 aria-live', '/#/listen', async (page) => {
  await clickText(page, '开始游戏')
  await new Promise((r) => setTimeout(r, 600))

  const region = await page.evaluate(() => {
    const node = [...document.querySelectorAll('[aria-live="polite"]')].find((n) =>
      n.classList.contains('sr-only')
    )
    return node ? node.innerText.trim() : ''
  })
  if (!/第\s*\d+\s*关/.test(region)) throw new Error(`答题开始没有播报关卡：「${region}」`)

  await page.evaluate(() => document.querySelector('.opt')?.click())
  await new Promise((r) => setTimeout(r, 500))
  const answered = await page.evaluate(
    () =>
      [...document.querySelectorAll('.sr-only[aria-live="polite"]')]
        .map((n) => n.innerText.trim())
        .join(' ')
  )
  if (!/答对了|正确答案/.test(answered)) throw new Error(`作答后没有播报对错：「${answered}」`)

  return `答题播报「${region.slice(0, 14)}…」，作答反馈「${answered.slice(0, 18)}…」`
})

await interact('设计令牌：识字 App 用的是共享令牌层', '/#/', async (page) => {
  const tokens = await page.evaluate(() => {
    const cs = getComputedStyle(document.documentElement)
    const read = (name) => cs.getPropertyValue(name).trim()
    return {
      shared: read('--tap-hero'),
      palette: read('--mango-500'),
      textSoft: read('--text-soft'),
      artTint: read('--art-tint')
    }
  })
  if (!tokens.shared || !tokens.palette) {
    throw new Error('没有读到 shared/styles/design-tokens.css 里的令牌，说明没接进来')
  }
  if (!tokens.artTint) throw new Error('识字 App 自己的 --art-tint 丢了')
  return `共享令牌 --tap-hero=${tokens.shared}，--mango-500=${tokens.palette}，--text-soft=${tokens.textSoft}`
})

await interact('学伴：核心路由常驻，点一下换鼓励语并朗读', '/#/', async (page) => {
  const visited = []
  for (const [name, route] of [
    ['首页', '/#/'],
    ['字表', '/#/learn'],
    ['小游戏', '/#/games'],
    ['绘本', '/#/books'],
    ['成语', '/#/idioms']
  ]) {
    await page.goto(base + route, { waitUntil: 'networkidle2', timeout: 20000 })
    await page.waitForSelector('.mascot-dock button', { timeout: 8000 })
    // 路由切换有淡入淡出，太早点会点在正在离场的那一只身上
    await new Promise((r) => setTimeout(r, 700))
    /**
     * 学伴入场是一段 600ms 的 scale(.6) → scale(1)，而它要等路由分块加载完才挂上来。
     * 机器慢一点（字表、绘本这两条重路由上最明显）时，固定等 700ms 量到的就是动画
     * 中途的尺寸——72px 的命中区会被量成 43px，断言假红。等入场动画自己跑完再量：
     * 常驻的呼吸动画 iterations 是 Infinity，finished 永远不会兑现，得挑出来跳过。
     */
    await page.evaluate(async () => {
      const dock = document.querySelector('.mascot-dock')
      const entrances = dock
        .getAnimations({ subtree: true })
        .filter((animation) => animation.effect?.getComputedTiming().iterations !== Infinity)
      await Promise.all(entrances.map((animation) => animation.finished.catch(() => {})))
    })

    const before = await page.evaluate(() => {
      // 朗读在无头环境里没有嗓音，换成记录调用，验的是「点了会说话」这条线
      window.__spoken = []
      const synth = window.speechSynthesis
      if (synth && !synth.__patched) {
        synth.__patched = true
        synth.speak = (utter) => window.__spoken.push(utter.text)
      }
      const dock = document.querySelector('.mascot-dock')
      const btn = dock.querySelector('button')
      const bubble = dock.querySelector('[role="status"] p')
      const box = btn.getBoundingClientRect()
      return {
        label: btn.getAttribute('aria-label') ?? '',
        line: bubble?.innerText.trim() ?? '',
        tap: Math.round(Math.min(box.width, box.height))
      }
    })
    if (!before.label) throw new Error(`${name}：学伴按钮没有无障碍名称`)
    if (before.tap < 44) throw new Error(`${name}：学伴命中区只有 ${before.tap}px`)
    if (!before.line) throw new Error(`${name}：学伴气泡里没有鼓励语`)

    await page.evaluate(() => document.querySelector('.mascot-dock button').click())
    await new Promise((r) => setTimeout(r, 350))
    const after = await page.evaluate(() => ({
      line: document.querySelector('.mascot-dock [role="status"] p').innerText.trim(),
      spoken: window.__spoken ?? []
    }))
    if (after.line === before.line) throw new Error(`${name}：点了学伴但鼓励语没换`)
    if (!after.spoken.includes(after.line)) {
      throw new Error(`${name}：气泡换成「${after.line}」却没有把它读出来`)
    }
    visited.push(name)
  }
  return `${visited.length} 条路由常驻学伴（${visited.join('、')}），点触换句并朗读`
})

/* ------------------------------------------------------------ 字源演变 */

/** 等演变动画走到收尾状态，再把舞台上的东西数一遍。 */
const readStage = (page) =>
  page.evaluate(() => {
    const el = document.querySelector('.ety')
    if (!el) return null
    const strokes = [...el.querySelectorAll('.ety__stroke')]
    const frames = [...el.querySelectorAll('.ety__frame')]
    return {
      stage: el.dataset.stage,
      kind: el.dataset.kind,
      ink: el.querySelectorAll('.ety__ink').length,
      parts: el.querySelectorAll('.ety__part').length,
      strokes: strokes.length,
      masked: strokes.filter((p) => p.getAttribute('mask')).length,
      reveals: el.querySelectorAll('.ety__reveal').length,
      visibleFrames: frames.filter((f) => Number(getComputedStyle(f).opacity) > 0.9).length,
      text: el.querySelector('.ety__text')?.innerText.replace(/\s+/g, ' ').trim() ?? '',
      live: el.querySelector('.sr-only[aria-live="polite"]')?.innerText.trim() ?? ''
    }
  })

const waitStageDone = (page) =>
  page.waitForFunction(
    () => ['done', 'static'].includes(document.querySelector('.ety')?.dataset.stage),
    { timeout: 20000 }
  )

await interact(
  '字源馆：象形字从小图演变到笔画',
  `/#/etymology/${encodeURIComponent('日')}`,
  async (page) => {
    await page.waitForSelector('.ety[data-ready="true"]', { timeout: 12000 })
    await waitStageDone(page)
    const s = await readStage(page)
    if (s.kind !== 'xiang') throw new Error(`「日」应当归在象形，实际是 ${s.kind}`)
    if (s.ink < 2) throw new Error(`第一帧的小图只画出了 ${s.ink} 笔`)
    if (s.strokes < 3) throw new Error(`第二帧只画出了 ${s.strokes} 笔，笔顺数据没接上`)
    if (s.masked !== s.strokes) throw new Error('笔画没有挂上遮罩，「一笔一笔写」的动画不会生效')
    if (s.reveals !== s.strokes) throw new Error(`遮罩 ${s.reveals} 条对不上 ${s.strokes} 笔`)
    if (!s.text.includes('象形')) throw new Error(`配文里没有说明这是什么字：「${s.text}」`)
    if (!s.live) throw new Error('演变过程没有任何 aria-live 播报')
    return `象形「日」：小图 ${s.ink} 笔 → 楷书 ${s.strokes} 笔（${s.masked} 笔逐笔显出）`
  }
)

await interact(
  '字源馆：形声字先拆零件，切字后重新演一遍',
  `/#/etymology/${encodeURIComponent('河')}`,
  async (page) => {
    await page.waitForSelector('.ety[data-ready="true"]', { timeout: 12000 })
    await waitStageDone(page)
    const he = await readStage(page)
    if (he.kind !== 'xing') throw new Error(`「河」应当归在形声，实际是 ${he.kind}`)
    if (he.parts !== 2) throw new Error(`形声字第一帧应当摆出两个零件，实际 ${he.parts} 个`)
    if (he.ink !== 0) throw new Error('形声字不该画小图')
    if (!he.strokes) throw new Error('形声字第二帧没有笔画')

    // 换一个字：舞台要重新从「看图」演起，而不是停在上一个字的收尾状态
    const picked = await page.evaluate(() => {
      const btn = [...document.querySelectorAll('.glyphbtn')].find((b) => b.innerText.trim() === '山')
      if (!btn) return false
      btn.click()
      return true
    })
    if (!picked) throw new Error('字表里点不到「山」')
    await page.waitForFunction(() => document.querySelector('.ety')?.dataset.char === '山', {
      timeout: 8000
    })
    await waitStageDone(page)
    const shan = await readStage(page)
    if (shan.kind !== 'xiang') throw new Error('换到「山」以后分类没跟着换')
    if (!shan.ink) throw new Error('换字后第一帧的小图没有重新画出来')
    return `形声「河」拆成 ${he.parts} 个零件；换到象形「山」后重演（小图 ${shan.ink} 笔）`
  }
)

await interact(
  '字源馆：系统要求减少动态时降级成两幅静图',
  `/#/etymology/${encodeURIComponent('日')}`,
  async (page) => {
    await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }])
    await page.reload({ waitUntil: 'networkidle2', timeout: 20000 })
    await page.waitForSelector('.ety[data-ready="true"]', { timeout: 12000 })
    await new Promise((r) => setTimeout(r, 600))

    const s = await readStage(page)
    if (s.stage !== 'static') throw new Error(`减少动态时应当直接进静止模式，实际 stage=${s.stage}`)
    if (s.masked !== 0) throw new Error('静止模式下笔画还挂着遮罩，会有一半笔画显不出来')
    if (s.visibleFrames < 2) throw new Error(`静止模式要把两幅图都摆出来，实际只看得到 ${s.visibleFrames} 幅`)
    if (!s.ink || !s.strokes) throw new Error('静止模式下小图或字形是空的')
    if (!s.text.includes('象形')) throw new Error('静止模式下配文丢了')

    // 不动，但该说的一句不能少：文字说明和播报都要还在
    if (!s.live.includes('减少动态')) {
      throw new Error(`静止模式没有告诉用户动画为什么没播：「${s.live}」`)
    }
    const noReplay = await page.evaluate(() =>
      [...document.querySelectorAll('.ety__acts .btn')].every((b) => !b.innerText.includes('再演一遍'))
    )
    if (!noReplay) throw new Error('减少动态时还留着「再演一遍」按钮')
    return `静止模式：两幅图并排（小图 ${s.ink} 笔 + 楷书 ${s.strokes} 笔），无遮罩、无时间线`
  }
)

await interact(
  '单字页：字源动画点开才下载',
  `/#/learn/${encodeURIComponent('山')}`,
  async (page) => {
    const isStageChunk = (url) => {
      const file = url.split('/').pop() ?? ''
      return /^EtymologyStage-/.test(file) || /^etymology-(?!index-)/.test(file)
    }
    const asked = []
    page.on('request', (r) => {
      if (isStageChunk(r.url())) asked.push(r.url().split('/').pop())
    })

    await page.reload({ waitUntil: 'networkidle2', timeout: 20000 })
    await page.waitForSelector('#char-origin-panel', { timeout: 8000 })
    await new Promise((r) => setTimeout(r, 400))
    if (asked.length) throw new Error(`还没点就下载了字源分块：${asked.join('、')}`)

    const collapsed = await page.evaluate(() => {
      const btn = document.querySelector('[aria-controls="char-origin-panel"]')
      return { expanded: btn?.getAttribute('aria-expanded'), stage: !!document.querySelector('.ety') }
    })
    if (collapsed.expanded !== 'false') throw new Error('入口按钮没有正确标注 aria-expanded')
    if (collapsed.stage) throw new Error('还没点开，演变舞台就已经挂在页面上了')

    await page.evaluate(() => document.querySelector('[aria-controls="char-origin-panel"]').click())
    await page.waitForSelector('.ety[data-ready="true"]', { timeout: 12000 })
    await waitStageDone(page)

    if (!asked.length) throw new Error('点开之后也没有请求字源分块，说明它被打进了主包')
    const s = await readStage(page)
    if (!s.ink || !s.strokes) throw new Error('单字页里的演变舞台是空的')
    const expanded = await page.evaluate(
      () => document.querySelector('[aria-controls="char-origin-panel"]')?.getAttribute('aria-expanded')
    )
    if (expanded !== 'true') throw new Error('展开后 aria-expanded 没有跟着变')

    return `点开前 0 个请求，点开后加载 ${asked.length} 个分块（${asked.join('、')}）并演完`
  }
)

await interact('拍照识字：示例照片认出字库里的字，引擎点了才下载', '/#/ocr', async (page) => {
  // worker / wasm 内核 / 语言包合起来 5.5 MB，只有真的去认字才准下载
  const isEnginePart = (url) => /\/ocr\/(?:worker\.min|tesseract-core|chi_sim)/.test(url)
  const asked = []
  page.on('request', (r) => {
    if (isEnginePart(r.url())) asked.push(r.url().split('/').pop())
  })

  await page.reload({ waitUntil: 'networkidle2', timeout: 20000 })
  await page.waitForSelector('.ocr[data-phase="idle"]', { timeout: 8000 })
  await new Promise((r) => setTimeout(r, 500))
  if (asked.length) throw new Error(`还没开始认字就下载了引擎：${asked.join('、')}`)

  const ready = await page.evaluate(
    () => document.querySelector('.ocr__pack')?.dataset.ready === 'true'
  )
  if (!ready) throw new Error('识字包清单没读到，public/ocr/ 少东西（跑一遍 npm run gen:ocr）')

  if (!(await clickText(page, '试一张示例'))) throw new Error('拍照识字缺少「试一张示例」入口')
  await page.waitForFunction(
    () => ['done', 'error'].includes(document.querySelector('.ocr')?.dataset.phase),
    { timeout: 90000 }
  )

  // 讲解在单元详情包里，认出哪个字才去下哪一包，比识别本身晚一拍到
  await page
    .waitForFunction(
      () =>
        [...document.querySelectorAll('.ocr__hit')].every((n) => n.dataset.ready === 'true'),
      { timeout: 10000 }
    )
    .catch(() => {})

  const out = await page.evaluate(() => ({
    phase: document.querySelector('.ocr')?.dataset.phase,
    hits: [...document.querySelectorAll('.ocr__hit')].map((n) => n.dataset.char),
    meanings: [...document.querySelectorAll('.ocr__hit-meaning')].map((n) => n.innerText.trim()),
    live: document.querySelector('.ocr__live')?.innerText.trim() ?? ''
  }))
  if (out.phase !== 'done') throw new Error('示例照片没认成，OCR 流水线断在半路')

  // 示例图印的就是这四个字，认得出三个才算这条链路真的通了
  const wanted = ['日', '月', '山', '水'].filter((c) => out.hits.includes(c))
  if (wanted.length < 3) {
    throw new Error(`示例图里的日月山水只认出 ${wanted.join('') || '零个'}`)
  }
  if (out.meanings.some((text) => !text || text.includes('正在翻'))) {
    throw new Error('认出来的字没有配上字库讲解')
  }
  if (!/认出了\s*\d+\s*个字/.test(out.live)) throw new Error(`认完没有播报结果：「${out.live}」`)

  for (const part of ['worker.min.js', 'chi_sim.traineddata.gz']) {
    if (!asked.some((f) => f === part)) throw new Error(`认字过程中没有请求 ${part}`)
  }
  if (!asked.some((f) => /^tesseract-core/.test(f))) throw new Error('认字过程中没有加载 wasm 内核')

  // 认出来的字要能一路点进单字页，不然「认出来了」也没下文
  await page.evaluate(() => document.querySelector('.ocr__hit').click())
  await page.waitForFunction(
    (char) => location.hash === `#/learn/${encodeURIComponent(char)}`,
    { timeout: 5000 },
    out.hits[0]
  )

  return `点开前 0 个引擎请求 → 认出「${out.hits.join('')}」（下了 ${asked.length} 个文件），可点进单字页`
})

await interact('单字页：笔顺数据可用', `/#/learn/${encodeURIComponent('日')}`, async (page) => {
  await new Promise((r) => setTimeout(r, 1500))
  return await page.evaluate(() => {
    const paths = document.querySelectorAll('#app svg path')
    const note = document.body.innerText.includes('需要联网') ? '显示了离线提示' : '无离线提示'
    return `svg path 数=${paths.length}，${note}`
  })
})

if (ROUND6_H3_SMOKE) {
  await interact('Round 6 H3：古诗入口渲染内容与点读控件', `/#${ROUND6_H3_SMOKE}`, async (page) => {
    const state = await page.evaluate(() => {
      const text = document.body.innerText.replace(/\s+/g, ' ').trim()
      const controls = [...document.querySelectorAll('button, a')].map((node) =>
        `${node.innerText} ${node.getAttribute('aria-label') ?? ''}`.trim()
      )
      return {
        hasPoemCopy: /古诗|诗词|作者|朝代/.test(text),
        hasReadingControl: controls.some((label) => /朗读|播放|点读|听/.test(label))
      }
    })
    if (!state.hasPoemCopy) throw new Error('古诗页没有可识别的诗词/作者内容')
    if (!state.hasReadingControl) throw new Error('古诗页缺少朗读或点读控件')
    return '诗词内容与朗读/点读入口均可见'
  })
}

if (ROUND6_H4_SMOKE) {
  await interact('Round 6 H4：跟读评测入口与降级提示', `/#${ROUND6_H4_SMOKE}`, async (page) => {
    const state = await page.evaluate(() => {
      const text = document.body.innerText.replace(/\s+/g, ' ').trim()
      const controls = [...document.querySelectorAll('button')].map((node) =>
        `${node.innerText} ${node.getAttribute('aria-label') ?? ''}`.trim()
      )
      return {
        hasEvalCopy: /跟读|语音评测|朗读评测|录音/.test(text),
        hasStartControl: controls.some((label) => /开始|跟读|录音|重试|播放/.test(label)),
        hasStatus: Boolean(document.querySelector('[aria-live], [role="status"]'))
      }
    })
    if (!state.hasEvalCopy) throw new Error('跟读页没有评测或录音说明')
    if (!state.hasStartControl) throw new Error('跟读页缺少开始/录音/重试控件')
    if (!state.hasStatus) throw new Error('跟读结果缺少 aria-live/status 播报区域')
    return '评测文案、操作入口与无障碍状态播报均可见'
  })
}

if (ROUND8_H5_SMOKE) {
  await interact('Round 8 H5：跟读三档与离线学伴对话', `/#${ROUND8_H5_SMOKE}`, async (page) => {
    const state = await page.evaluate(() => {
      const panel = document.querySelector('.fr')
      const chat = document.querySelector('.companion-chat')
      return {
        mode: panel?.dataset.mode ?? '',
        chatText: chat?.innerText.replace(/\s+/g, ' ').trim() ?? '',
        replies: [...(chat?.querySelectorAll('.mascot__quick-btn') ?? [])].map((node) =>
          node.innerText.trim()
        )
      }
    })
    if (!['recognition', 'recording', 'listen-only'].includes(state.mode)) {
      throw new Error(`跟读没有落在三档降级契约中：${state.mode || '缺少 data-mode'}`)
    }
    if (!/学伴小对话/.test(state.chatText) || !/离线规则/.test(state.chatText)) {
      throw new Error('跟读页缺少离线学伴对话说明')
    }
    if (!state.replies.includes('我准备好了') || !state.replies.includes('我有点紧张')) {
      throw new Error(`学伴开场快捷回复不完整：${state.replies.join('、') || '无'}`)
    }

    await page.evaluate(() => {
      const nervous = [...document.querySelectorAll('.companion-chat .mascot__quick-btn')].find(
        (node) => node.innerText.includes('有点紧张')
      )
      nervous?.click()
    })
    await page.waitForFunction(
      () => document.querySelector('.companion-chat .mascot__bubble p')?.innerText.includes('没关系'),
      { timeout: 3000 }
    )
    return `降级档=${state.mode}；离线快捷回复可触发规则化回应`
  })
}

if (ROUND10_H1_SMOKE) {
  await interact(
    'ROUND10_H1：跟读 v3 —— 离线 ASR 四档降级，失败仍降录音档且不联网',
    `/#${ROUND10_H1_SMOKE}`,
    async (page) => {
      await page.waitForSelector('.fr[data-tier]', { timeout: 8000 })
      // 探测只读清单和本机缓存，等它落定再看，别把「正在查」当成结论
      await page.waitForFunction(
        () => !['unknown', 'checking'].includes(document.querySelector('.fr__pack')?.dataset.status),
        { timeout: 8000 }
      )

      const opening = await page.evaluate(() => {
        const fr = document.querySelector('.fr')
        const pack = document.querySelector('.fr__pack')
        const optIn = document.querySelector('.fr__opt input[type="checkbox"]')
        return {
          tier: fr?.dataset.tier ?? '',
          mode: fr?.dataset.mode ?? '',
          source: fr?.dataset.source ?? '',
          status: pack?.dataset.status ?? '',
          text: pack?.innerText.replace(/\s+/g, ' ').trim() ?? '',
          optIn: optIn ? optIn.checked : false,
          install: !!document.querySelector('.fr__pack-get')
        }
      })

      if (!ROUND10_H1_TIERS.includes(opening.tier)) {
        throw new Error(`跟读没有落在四档降级契约里：${opening.tier || '缺少 data-tier'}`)
      }
      if (!ROUND10_H1_MODES.includes(opening.mode)) {
        throw new Error(`对外 mode 不再是三档：${opening.mode || '缺少 data-mode'}`)
      }
      const wantMode = opening.tier === 'offline-asr' ? 'recognition' : opening.tier
      if (opening.mode !== wantMode) {
        throw new Error(`第 ${opening.tier} 档映射成了 mode=${opening.mode}`)
      }
      if (!opening.source) throw new Error('结果来源没有标出来（缺少 data-source）')
      if (opening.optIn) throw new Error('浏览器语音识别默认是开的，隐私默认被改坏了')
      if (opening.status === 'ready') throw new Error('没人点下载，离线评测包却已经装上了')
      if (!opening.install) throw new Error('没有「下载离线评测包」入口，家长无从选择')
      if (!/不上传/.test(opening.text)) throw new Error(`离线评测包说明没有讲清去向：「${opening.text}」`)

      // 装包失败要当场降回录音档：既不能卡住，也不能顺手改用可能联网的识别
      const foreign = []
      const origin = new URL(page.url()).origin
      page.on('request', (request) => {
        if (new URL(request.url()).origin !== origin) foreign.push(request.url())
      })

      await page.evaluate(() => document.querySelector('.fr__pack-get').click())
      await page.waitForFunction(
        () => document.querySelector('.fr__pack')?.dataset.status === 'failed',
        { timeout: 8000 }
      )

      const after = await page.evaluate(() => {
        const fr = document.querySelector('.fr')
        const optIn = document.querySelector('.fr__opt input[type="checkbox"]')
        return {
          tier: fr?.dataset.tier ?? '',
          mode: fr?.dataset.mode ?? '',
          note: document.querySelector('.fr__pack-note')?.innerText.replace(/\s+/g, ' ').trim() ?? '',
          optIn: optIn ? optIn.checked : false
        }
      })
      if (after.tier === 'offline-asr') throw new Error('离线包没装上，却还停在离线档')
      if (after.tier === 'recognition' && opening.tier !== 'recognition') {
        throw new Error('离线包失败后自己切到了浏览器识别，违反「失败只降录音档」')
      }
      if (after.optIn) throw new Error('离线包失败后替家长打开了浏览器语音识别')
      if (!ROUND10_H1_MODES.includes(after.mode)) throw new Error(`降级后 mode 不合法：${after.mode}`)
      if (!after.note.includes('没装上')) throw new Error(`失败原因没有告诉家长：「${after.note}」`)
      if (foreign.length) throw new Error(`离线评测包走了第三方地址：${foreign.slice(0, 2).join('、')}`)

      return `四档=${opening.tier}（mode=${opening.mode}，来源=${opening.source}）；装包失败后降到 ${after.tier}，0 个跨源请求`
    }
  )
}

if (ROUND11_H1_SMOKE) {
  await interact(
    'ROUND11_H1：跟读产品化 —— 冻结清单 + 五层门槛随包发出，结论没绿就不许 available',
    `/#${ROUND11_H1_SMOKE}`,
    async (page) => {
      // 从页面自己去取：清单必须和路由同源、能被 fetch 到，不然家长界面上的
      // 「离线评测包」状态就是编的
      const pack = await page.evaluate(async () => {
        const response = await fetch(new URL('asr/manifest.json', document.baseURI).href, {
          cache: 'no-cache'
        })
        return { ok: response.ok, status: response.status, body: await response.text() }
      })
      if (!pack.ok) throw new Error(`页面读不到离线评测包清单（HTTP ${pack.status}）`)

      const manifest = JSON.parse(pack.body)
      const freeze = manifest.freezeChecklist ?? []
      if (freeze.length < ROUND11_H1_MIN_FREEZE) {
        throw new Error(`冻结清单只剩 ${freeze.length} 条（下限 ${ROUND11_H1_MIN_FREEZE}）`)
      }
      for (const item of freeze) {
        for (const field of ['id', 'layer', 'must', 'evidence', 'status', 'blocks']) {
          if (!item?.[field]) throw new Error(`冻结项 ${item?.id ?? '?'} 缺 ${field}`)
        }
      }
      const layers = (manifest.goNoGo?.layers ?? []).map((layer) => layer.name)
      const missingLayer = ROUND11_H1_LAYERS.filter((name) => !layers.includes(name))
      if (missingLayer.length) throw new Error(`五层门槛少了：${missingLayer.join('、')}`)
      if (manifest.goNoGo.layers.some((layer) => !layer.gates?.length)) {
        throw new Error('有一层门槛一条阈值都没写')
      }

      // 只要还有冻结项没做完，这一档就不许对外宣称可用
      const pending = freeze.filter((item) => item.status !== 'done')
      if (pending.length && manifest.available !== false) {
        throw new Error(`还有 ${pending.length} 条冻结项没做完，available 却是 ${manifest.available}`)
      }
      if (pending.length && manifest.goNoGo.verdict !== 'no-go') {
        throw new Error(`冻结项没做完，结论却是 ${manifest.goNoGo.verdict}`)
      }
      // 界面这边要和清单一致：没冻结就不该出现离线档，也不该显示「已就绪」
      const ui = await page.evaluate(() => ({
        tier: document.querySelector('.fr')?.dataset.tier ?? '',
        status: document.querySelector('.fr__pack')?.dataset.status ?? ''
      }))
      if (manifest.available !== true && ui.tier === 'offline-asr') {
        throw new Error('清单说这一档还不可用，界面却停在离线档')
      }
      if (manifest.available !== true && ui.status === 'ready') {
        throw new Error('清单说这一档还不可用，界面却说离线评测包已就绪')
      }

      const done = freeze.filter((item) => item.status === 'done').length
      return (
        `冻结清单 ${done}/${freeze.length} 条完成，五层门槛齐全，` +
        `结论=${manifest.goNoGo.verdict}，available=${manifest.available}；` +
        `dist/asr 模型字节 ${asrModelBytes}，档位=${ui.tier || '未标注'}`
      )
    }
  )
}

if (ROUND12_H1_SMOKE) {
  await interact(
    'ROUND12_H1：模型真落库 —— 首屏一个模型字节都不下，界面照旧停在录音档',
    `/#${ROUND12_H1_SMOKE}`,
    async (page) => {
      const origin = new URL(page.url()).origin
      const modelRequests = []
      const foreign = []
      page.on('request', (request) => {
        const url = request.url()
        if (/\/asr\/models\//.test(url)) modelRequests.push(url)
        // 内联的 data: 图标不是「出网」，只有真正的 http(s) 才算跨源
        if (/^https?:/.test(url) && new URL(url).origin !== origin) foreign.push(url)
      })

      await page.reload({ waitUntil: 'networkidle2', timeout: 20000 })
      await page.waitForSelector('.fr[data-tier]', { timeout: 8000 })
      await page.waitForFunction(
        () => !['unknown', 'checking'].includes(document.querySelector('.fr__pack')?.dataset.status),
        { timeout: 8000 }
      )
      if (modelRequests.length) {
        throw new Error(
          `首屏就去取模型了（${modelRequests.length} 次，如 ${modelRequests[0]}）——` +
            '家长还没点下载，流量已经花出去了'
        )
      }

      const manifest = await page.evaluate(async () => {
        const response = await fetch(new URL('asr/manifest.json', document.baseURI).href, {
          cache: 'no-cache'
        })
        return response.json()
      })
      const roles = (manifest.files ?? []).map((file) => file.role)
      const missing = ROUND12_H1_ROLES.filter((role) => !roles.includes(role))
      if (missing.length) throw new Error(`落库的整包缺角色：${missing.join('、')}`)
      for (const file of manifest.files) {
        if (!/^[a-f0-9]{64}$/.test(String(file.sha256))) {
          throw new Error(`${file.path} 没有冻结 sha256`)
        }
        if (!Number.isInteger(file.bytes) || file.bytes <= 0) {
          throw new Error(`${file.path} 的 bytes 不合法：${file.bytes}`)
        }
      }
      const total = manifest.files.reduce((n, file) => n + file.bytes, 0)
      if (total > ROUND12_H1_MAX_PACK_BYTES) {
        throw new Error(`整包 ${(total / 1048576).toFixed(2)} MiB 超过 60 MiB 预算`)
      }

      // 抽最大和最小的两个文件，按同源地址真取一次：路径写错或没发出去，这里当场红
      const sorted = [...manifest.files].sort((a, b) => a.bytes - b.bytes)
      const probes = [sorted[0], sorted[sorted.length - 1]]
      const fetched = await page.evaluate(async (list) => {
        const out = []
        for (const file of list) {
          const url = new URL(file.path, document.baseURI).href
          const response = await fetch(url, { cache: 'no-store' })
          const buffer = response.ok ? await response.arrayBuffer() : new ArrayBuffer(0)
          out.push({ path: file.path, ok: response.ok, bytes: buffer.byteLength })
        }
        return out
      }, probes)
      for (const [index, probe] of fetched.entries()) {
        if (!probe.ok) throw new Error(`${probe.path} 没随包发出去（同源取不到）`)
        if (probe.bytes !== probes[index].bytes) {
          throw new Error(
            `${probe.path} 发出去 ${probe.bytes} 字节，清单写 ${probes[index].bytes} 字节`
          )
        }
      }

      // 落库不等于放行：清单没转绿，界面必须还停在录音档，入口还是「下载」
      const before = await page.evaluate(() => ({
        tier: document.querySelector('.fr')?.dataset.tier ?? '',
        status: document.querySelector('.fr__pack')?.dataset.status ?? '',
        cta: document.querySelector('.fr__pack-get')?.innerText.replace(/\s+/g, ' ').trim() ?? ''
      }))
      if (manifest.available !== false) {
        throw new Error(`冻结集还没录，available 却是 ${manifest.available}`)
      }
      if (before.tier === 'offline-asr') throw new Error('模型只是落了库，界面就自己升到了离线档')
      if (before.status === 'ready') throw new Error('没人点下载，界面却说离线评测包已就绪')
      if (!before.cta) throw new Error('「下载离线评测包」入口不见了')

      // 家长真点一次：这一版不放行，必须落到 failed 并讲清原因，也不许改用在线识别
      await page.evaluate(() => document.querySelector('.fr__pack-get').click())
      await page.waitForFunction(
        () => document.querySelector('.fr__pack')?.dataset.status === 'failed',
        { timeout: 8000 }
      )
      const after = await page.evaluate(() => ({
        tier: document.querySelector('.fr')?.dataset.tier ?? '',
        note: document.querySelector('.fr__pack-note')?.innerText.replace(/\s+/g, ' ').trim() ?? '',
        optIn: document.querySelector('.fr__opt input[type="checkbox"]')?.checked ?? false
      }))
      if (after.tier === 'offline-asr') throw new Error('这一版没放行，档位却升到了离线')
      if (after.optIn) throw new Error('装包失败后替家长打开了浏览器语音识别')
      if (!after.note) throw new Error('装包失败却没告诉家长为什么')
      if (foreign.length) throw new Error(`跟读页走了第三方地址：${foreign.slice(0, 2).join('、')}`)

      return (
        `整包 ${(total / 1048576).toFixed(2)} MiB / ${manifest.files.length} 个文件（${roles.length} 个角色）` +
        `，首屏 0 次模型请求；抽验 ${probes.map((p) => p.path.split('/').pop()).join('、')} 同源可取且字节对得上；` +
        `available=${manifest.available}，档位 ${before.tier}→${after.tier}，0 个跨源请求`
      )
    }
  )
}

if (ROUND8_H2_SMOKE) {
  await interact(
    'Round 8 H2：儿歌唱一遍，逐字高亮跟着走并记进进度',
    `/#${ROUND8_H2_SMOKE}`,
    async (page) => {
      await page.evaluate(() => localStorage.clear())
      await page.reload({ waitUntil: 'networkidle2', timeout: 20000 })
      await new Promise((r) => setTimeout(r, 600))

      const opened = await page.evaluate(() => {
        const head = document.querySelector('.song__head')
        if (!head) return false
        head.click()
        return true
      })
      if (!opened) throw new Error('儿歌页没有渲染出任何一首歌')
      await page.waitForSelector('.lyrics__line', { timeout: 5000 })

      const sheet = await page.evaluate(() => ({
        lines: document.querySelectorAll('.lyrics__line').length,
        chars: document.querySelectorAll('.cell__char').length,
        pinyin: [...document.querySelectorAll('.cell__pinyin')].filter((n) => n.innerText.trim())
          .length
      }))
      if (sheet.lines < 4) throw new Error(`展开的儿歌只有 ${sheet.lines} 句`)
      if (sheet.chars < sheet.pinyin || sheet.pinyin === 0) {
        throw new Error(`歌词逐字拼音没渲染出来（${sheet.pinyin} / ${sheet.chars}）`)
      }

      if (!(await clickText(page, '唱一唱'))) throw new Error('儿歌页缺少「唱一唱」控件')

      // 逐字高亮是「唱到哪个字」的唯一可见证据，只看它亮起来不够——
      // 还要看它真的往后走了，不然一个卡在第一个字的定时器也能骗过测试。
      await page.waitForSelector('.cell.is-on', { timeout: 5000 })
      const walked = await page.evaluate(async () => {
        const at = () => {
          const cells = [...document.querySelectorAll('.cell')]
          return cells.findIndex((node) => node.classList.contains('is-on'))
        }
        const first = at()
        for (let i = 0; i < 40; i += 1) {
          await new Promise((r) => setTimeout(r, 200))
          if (at() > first) return { first, later: at() }
        }
        return { first, later: at() }
      })
      if (walked.later <= walked.first) {
        throw new Error(`高亮停在第 ${walked.first} 个字没有往下走`)
      }

      // 整首唱完才算「唱过」，中途停下不记账——等它自己走到头。
      await page.waitForFunction(
        () => /唱完啦|又唱了一遍/.test(document.querySelector('.player__status')?.innerText ?? ''),
        { timeout: 60000 }
      )
      const done = await page.evaluate(() => ({
        status: document.querySelector('.player__status')?.innerText.trim() ?? '',
        shelf: document.body.innerText.replace(/\s+/g, ' ').match(/唱过 (\d+) \/ (\d+)/)?.[1] ?? '0',
        stored: JSON.parse(localStorage.getItem('happy-literacy:v1') ?? '{}')?.songs ?? {}
      }))
      if (done.shelf !== '1') throw new Error(`唱完一首后计数是 ${done.shelf}，应为 1`)
      const sung = Object.values(done.stored).filter((s) => s?.sung).length
      if (sung !== 1) throw new Error(`存档里记进了 ${sung} 首已唱儿歌，应为 1`)

      return `${sheet.lines} 句 ${sheet.chars} 字，高亮第 ${walked.first} → ${walked.later} 个字，唱完记进存档`
    }
  )
}

if (ROUND9_H1_SMOKE) {
  await interact(
    'ROUND9_H1：儿歌 v2 —— 曲库 ≥10 首，预备拍 + 进度 + 留痕 + 音高抬升',
    `/#${ROUND9_H1_SMOKE}`,
    async (page) => {
      await page.evaluate(() => localStorage.clear())
      await page.reload({ waitUntil: 'networkidle2', timeout: 20000 })
      await new Promise((r) => setTimeout(r, 600))

      const shelf = await page.evaluate(() => ({
        songs: document.querySelectorAll('.song').length,
        themes: document.querySelectorAll('.tabs__btn').length,
        counter: document.body.innerText.replace(/\s+/g, ' ').match(/唱过 \d+ \/ (\d+)/)?.[1] ?? '0'
      }))
      if (shelf.songs < ROUND9_H1_MIN_SONGS) {
        throw new Error(`曲库只渲染出 ${shelf.songs} 首，v2 要求 ≥ ${ROUND9_H1_MIN_SONGS}`)
      }
      if (Number(shelf.counter) !== shelf.songs) {
        throw new Error(`歌单计数 ${shelf.counter} 与渲染出的 ${shelf.songs} 首对不上`)
      }

      await page.evaluate(() => document.querySelector('.song__head').click())
      await page.waitForSelector('.lyrics__line', { timeout: 5000 })

      // 音高带是 v2 的旋律可视化：没在唱的时候先摊出第一句，点数要和第一句字数一致。
      const ready = await page.evaluate(() => {
        const pitches = [...document.querySelectorAll('.ribbon__dot')].map((n) =>
          Number(n.style.getPropertyValue('--pitch'))
        )
        return {
          dots: pitches.length,
          spread: pitches.length ? Math.max(...pitches) - Math.min(...pitches) : 0,
          firstLineChars: document.querySelector('.lyrics__line')?.querySelectorAll('.cell:not(.cell--punct)').length ?? 0,
          version: document.querySelector('.player')?.dataset.songSync ?? ''
        }
      })
      if (ready.version !== 'v2') throw new Error(`播放器没有标出 v2（data-song-sync=${ready.version}）`)
      if (ready.dots !== ready.firstLineChars) {
        throw new Error(`音高带 ${ready.dots} 个点对不上第一句的 ${ready.firstLineChars} 个字`)
      }
      if (!(ready.spread > 0.05)) {
        throw new Error(`音高带是平的（高低差 ${ready.spread}），--pitch 没接上`)
      }

      if (!(await clickText(page, '唱一唱'))) throw new Error('儿歌页缺少「唱一唱」控件')

      // 预备拍：点完按钮先数拍子，这几百毫秒里一个字都不该亮。
      const countIn = await page.evaluate(() => ({
        text: document.querySelector('.track__countin')?.innerText.trim() ?? '',
        lit: document.querySelectorAll('.cell.is-on').length
      }))
      if (!/预备\s*\d/.test(countIn.text)) throw new Error(`没有预备拍倒数（读到「${countIn.text}」）`)
      if (countIn.lit !== 0) throw new Error('预备拍还没数完就开始高亮歌词了')

      await page.waitForSelector('.cell.is-on', { timeout: 8000 })

      // 进度条、留痕、音高抬升三样都要「随着唱往前走」，取两帧比一比。
      const walked = await page.evaluate(async () => {
        const snap = () => {
          const on = document.querySelector('.cell.is-on')
          return {
            progress: Number(document.querySelector('.track__bar')?.dataset.progress ?? -1),
            sung: document.querySelectorAll('.cell.is-sung').length,
            pitch: on ? Number(on.style.getPropertyValue('--pitch')) : -1,
            lift: on ? getComputedStyle(on).transform : 'none'
          }
        }
        const first = snap()
        const pitches = new Set([first.pitch])
        const lifts = new Set([first.lift])
        let last = first
        for (let i = 0; i < 30; i += 1) {
          await new Promise((r) => setTimeout(r, 200))
          last = snap()
          if (last.pitch >= 0) pitches.add(last.pitch)
          lifts.add(last.lift)
          if (last.sung > first.sung && last.progress > first.progress && pitches.size >= 3) break
        }
        return {
          first,
          last,
          pitches: pitches.size,
          lifts: lifts.size,
          // 「减少动态」下位移本来就该是 none，这时候只验音高变量，不验位移。
          quiet: matchMedia('(prefers-reduced-motion: reduce)').matches
        }
      })
      if (!(walked.last.progress > walked.first.progress)) {
        throw new Error(`进度条卡在 ${walked.first.progress}% 没动`)
      }
      if (!(walked.last.sung > walked.first.sung)) {
        throw new Error(`唱过的字没有留痕（is-sung 一直是 ${walked.first.sung} 个）`)
      }
      if (walked.pitches < 3) throw new Error(`高亮只走过 ${walked.pitches} 种音高，--pitch 没跟着旋律变`)
      if (!walked.quiet && walked.lifts < 3) {
        throw new Error(`字的抬升只有 ${walked.lifts} 种，音高没换算成位移`)
      }

      // 停一停要把动画状态一次清干净：高亮、预备拍、句号都不能留在屏幕上。
      if (!(await clickText(page, '停一停'))) throw new Error('儿歌页缺少「停一停」控件')
      await new Promise((r) => setTimeout(r, 400))
      const stopped = await page.evaluate(() => ({
        on: document.querySelectorAll('.cell.is-on').length,
        sung: document.querySelectorAll('.cell.is-sung').length,
        progress: Number(document.querySelector('.track__bar')?.dataset.progress ?? -1)
      }))
      if (stopped.on || stopped.sung || stopped.progress !== 0) {
        throw new Error(
          `停一停之后还剩 ${stopped.on} 个高亮 / ${stopped.sung} 个留痕 / 进度 ${stopped.progress}%`
        )
      }

      return (
        `${shelf.songs} 首 ${shelf.themes} 个分区；预备拍「${countIn.text}」；` +
        `进度 ${walked.first.progress}%→${walked.last.progress}%，留痕 ${walked.first.sung}→${walked.last.sung} 字，` +
        `${walked.pitches} 种音高 / ${walked.quiet ? '减少动态档' : `${walked.lifts} 种抬升`}`
      )
    }
  )
}

if (ROUND8_H2_SMOKE && songAudioAssets.length >= ROUND10_H5_MIN_AUDIO) {
  const first = ROUND10_H5_SMOKE[0]
  await interact(
    'ROUND10_H5：≥3 首真实 Ogg/MP3，文件优先 + 合成音降级',
    `/#${ROUND8_H2_SMOKE}/${first.id}`,
    async (page) => {
      await page.waitForSelector('.player[data-song-audio="file"]', { timeout: 5000 })

      const controls = await page.$$('.player__controls button')
      if (controls.length < 3) throw new Error('儿歌播放器控件不完整')
      await controls[0].click()
      await page.waitForFunction(
        () => document.querySelector('.player')?.dataset.playbackSource === 'file',
        { timeout: 8000 }
      )
      const preferred = await page.evaluate(() => ({
        source: document.querySelector('.player')?.dataset.playbackSource ?? '',
        label: document.querySelector('.player__source')?.innerText.trim() ?? ''
      }))
      if (preferred.source !== 'file') {
        throw new Error(`有效静态音频没有被优先播放（source=${preferred.source}）`)
      }

      await controls[2].click()
      await page.waitForFunction(
        () => (document.querySelector('.player')?.dataset.playbackSource ?? '') === '',
        { timeout: 3000 }
      )

      // 模拟平台无法解码/播放静态文件，必须无须重新点击就切到 WebAudio。
      await page.evaluate(() => {
        class BrokenAudio {
          constructor(src) {
            this.src = src
            this.currentTime = 0
            this.volume = 1
            this.paused = true
            this.onerror = null
          }
          play() {
            this.paused = false
            return Promise.reject(new Error('expected ROUND10_H5 fallback'))
          }
          pause() {
            this.paused = true
          }
          load() {}
          removeAttribute() {}
        }
        Object.defineProperty(window, 'Audio', { configurable: true, value: BrokenAudio })
      })

      const fallbackControls = await page.$$('.player__controls button')
      await fallbackControls[0].click()
      await page.waitForFunction(
        () => document.querySelector('.player')?.dataset.playbackSource === 'synth',
        { timeout: 5000 }
      )
      const fallback = await page.evaluate(() => ({
        source: document.querySelector('.player')?.dataset.playbackSource ?? '',
        status: document.querySelector('.player__status')?.innerText.trim() ?? ''
      }))
      if (fallback.source !== 'synth' || !/自动换成合成旋律/.test(fallback.status)) {
        throw new Error(`静态文件失败后没有合成降级：${JSON.stringify(fallback)}`)
      }
      await fallbackControls[2].click()

      const totalBytes = songAudioAssets.reduce((sum, asset) => sum + asset.bytes, 0)
      return `${songAudioAssets.length} 首 / ${totalBytes} bytes；优先=${preferred.source}，降级=${fallback.source}`
    }
  )
}

if (ROUND8_H2_SMOKE && vocalPilotAsset) {
  await interact(
    'ROUND12_H4：13/13 离线旋律 + 可播放的 Piper「啦」音范唱',
    `/#${ROUND8_H2_SMOKE}/${vocalPilotAsset.id}`,
    async (page) => {
      await page.waitForSelector('.player[data-song-vocal="file"]', { timeout: 5000 })
      const opened = await page.evaluate(() => ({
        audio: document.querySelector('.player')?.dataset.songAudio ?? '',
        vocal: document.querySelector('.player')?.dataset.songVocal ?? '',
        button: [...document.querySelectorAll('.player__controls button')].some((node) =>
          node.innerText.includes('啦')
        )
      }))
      if (opened.audio !== 'file' || opened.vocal !== 'file' || !opened.button) {
        throw new Error(`范唱接线不完整：${JSON.stringify(opened)}`)
      }

      if (!(await clickText(page, '听「啦」音范唱'))) throw new Error('页面上点不到范唱按钮')
      await page.waitForFunction(
        () => document.querySelector('.player')?.dataset.vocalSource === 'file',
        { timeout: 5000 }
      )
      const playing = await page.evaluate(() => ({
        source: document.querySelector('.player')?.dataset.vocalSource ?? '',
        status: document.querySelector('.player__status')?.innerText.trim() ?? ''
      }))
      if (playing.source !== 'file' || !playing.status.includes('离线「啦」音范唱')) {
        throw new Error(`范唱未进入播放态：${JSON.stringify(playing)}`)
      }

      if (!(await clickText(page, '停一停'))) throw new Error('范唱播放时无法停止')
      await page.waitForFunction(
        () => (document.querySelector('.player')?.dataset.vocalSource ?? '') === '',
        { timeout: 3000 }
      )
      return (
        `${songAudioAssets.length}/13 首、${distinctSongAudio.size} 份旋律；` +
        `范唱 ${vocalPilotAsset.bytes} bytes，可播放且可停止`
      )
    }
  )
}

if (ROUND11_H4_SMOKE) {
  await interact(
    'ROUND11_H4：绘本页级场景 —— 多元素落在画框内，翻页换整幅，减少动态时不动',
    `/#/books/${ROUND11_H4_SMOKE.id}`,
    async (page) => {
      await page.waitForSelector('.scene[data-scene="dsl"]', { timeout: 8000 })

      /** 一幅场景的可见形状：摆了几件、有没有飘出画框、读屏念什么。 */
      const snapshot = () =>
        page.evaluate(() => {
          const stage = document.querySelector('.scene')
          const box = stage.getBoundingClientRect()
          const items = [...stage.querySelectorAll('.scene__item')].map((node) => {
            const rect = node.getBoundingClientRect()
            return {
              e: node.innerText.trim(),
              cx: (rect.left + rect.width / 2 - box.left) / box.width,
              cy: (rect.top + rect.height / 2 - box.top) / box.height,
              size: Math.round(rect.width),
              anim: getComputedStyle(node).animationName
            }
          })
          return {
            kind: stage.dataset.scene,
            bg: stage.dataset.sceneBg,
            declared: Number(stage.dataset.sceneItems ?? 0),
            role: stage.getAttribute('role') ?? '',
            label: stage.getAttribute('aria-label') ?? '',
            solo: stage.querySelectorAll('.scene__solo').length,
            items
          }
        })

      const first = await snapshot()
      if (first.items.length < ROUND11_H4_MIN_ITEMS) {
        throw new Error(
          `首页场景只摆出 ${first.items.length} 件元素，样板要求 ≥ ${ROUND11_H4_MIN_ITEMS}`
        )
      }
      if (first.items.length !== first.declared) {
        throw new Error(`场景声明 ${first.declared} 件元素，实际渲染 ${first.items.length} 件`)
      }
      // 坐标是百分比，写错了不会报错，只会让半只小鸟挂在画框外边。
      const strayed = first.items.filter((i) => i.cx < 0 || i.cx > 1 || i.cy < 0 || i.cy > 1)
      if (strayed.length) {
        throw new Error(`${strayed.length} 件元素落在画框外：${strayed.map((i) => i.e).join('')}`)
      }
      // 一样大就是没吃到 s，多元素也就退化成一排贴纸。
      if (new Set(first.items.map((i) => i.size)).size < 2) {
        throw new Error('场景元素大小完全一致，--s 没接上')
      }
      if (first.role !== 'img' || first.label.length < 4) {
        throw new Error(`场景没给读屏留话（role=${first.role}，aria-label=「${first.label}」）`)
      }
      if (first.solo) throw new Error('场景页还留着单 emoji 兜底层')

      if (!(await clickText(page, '下一页'))) throw new Error('绘本页缺少「下一页」控件')
      await new Promise((r) => setTimeout(r, 700))
      const second = await snapshot()
      const unchanged =
        second.items.map((i) => i.e).join('') === first.items.map((i) => i.e).join('') &&
        second.label === first.label
      if (unchanged) throw new Error('翻到下一页，场景没跟着换')

      // 「减少动态」下场景照样摆满，只是不动——动效不该是理解画面的唯一通道。
      await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }])
      await page.reload({ waitUntil: 'networkidle2', timeout: 20000 })
      await page.waitForSelector('.scene[data-scene="dsl"]', { timeout: 8000 })
      const quiet = await snapshot()
      const moving = quiet.items.filter((i) => i.anim && i.anim !== 'none')
      if (moving.length) {
        throw new Error(`减少动态时仍有 ${moving.length} 件元素在动（${moving[0].anim}）`)
      }
      if (quiet.items.length < ROUND11_H4_MIN_ITEMS) {
        throw new Error(`减少动态时场景掉到 ${quiet.items.length} 件元素`)
      }
      await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'no-preference' }])

      // 没升级的书必须原样退回单 emoji，不能被场景改造顺手打碎。
      let plain = null
      if (ROUND11_H4_PLAIN) {
        await page.goto(`${base}/#/books/${ROUND11_H4_PLAIN.id}`, {
          waitUntil: 'networkidle2',
          timeout: 20000
        })
        await page.waitForSelector('.scene[data-scene="emoji"]', { timeout: 8000 })
        plain = await snapshot()
        if (plain.solo !== 1 || plain.items.length) {
          throw new Error(
            `《${ROUND11_H4_PLAIN.title}》的兜底插图不对：solo=${plain.solo}，items=${plain.items.length}`
          )
        }
      }

      return (
        `《${ROUND11_H4_SMOKE.title}》${scenePages(ROUND11_H4_SMOKE).length} 页场景；` +
        `首页 ${first.items.length} 件（${first.bg}）→ 次页 ${second.items.length} 件（${second.bg}）；` +
        `读屏「${first.label}」；减少动态 ${quiet.items.length} 件静止` +
        (plain ? `；《${ROUND11_H4_PLAIN.title}》仍是单 emoji` : '')
      )
    }
  )
}

if (ROUND13_H3_SAMPLE.length) {
  await interact(
    'ROUND13_H3：绘本场景终局 —— 抽样逐页比对「数据声明 / DOM 声明 / 实际渲染」',
    `/#/books/${ROUND13_H3_SAMPLE[0].id}`,
    async (page) => {
      /** 台账写死在数据层，先确认它没跟数据脱节，再谈渲染。 */
      if (SCENE_BOOK_IDS.length !== ROUND13_H3.books || TOTAL_SCENE_PAGES !== ROUND13_H3.pages) {
        throw new Error(
          `场景台账对不上：数据 ${SCENE_BOOK_IDS.length} 本 / ${TOTAL_SCENE_PAGES} 页，` +
            `ROUND13_H3 声明 ${ROUND13_H3.books} 本 / ${ROUND13_H3.pages} 页`
        )
      }
      if (TOTAL_SCENE_PAGES < ROUND13_H3.target) {
        throw new Error(`场景只铺到 ${TOTAL_SCENE_PAGES} 页，门槛 ≥ ${ROUND13_H3.target}`)
      }
      // R12 的量当地板：这一轮加书不能顺手把上一轮铺过的书吃回单 emoji。
      if (SCENE_BOOK_IDS.length < ROUND12_H3.books || TOTAL_SCENE_PAGES < ROUND12_H3.pages) {
        throw new Error(
          `场景退回 ROUND12_H3 台账之下：${SCENE_BOOK_IDS.length}/${ROUND12_H3.books} 本、` +
            `${TOTAL_SCENE_PAGES}/${ROUND12_H3.pages} 页`
        )
      }

      /** 当前这一页画了什么：件数、有没有飘出画框、读屏念的是哪句。 */
      const readStage = () =>
        page.evaluate(() => {
          const stage = document.querySelector('.scene')
          if (!stage) return null
          const box = stage.getBoundingClientRect()
          const items = [...stage.querySelectorAll('.scene__item')].map((node) => {
            const rect = node.getBoundingClientRect()
            return {
              cx: (rect.left + rect.width / 2 - box.left) / box.width,
              cy: (rect.top + rect.height / 2 - box.top) / box.height
            }
          })
          return {
            kind: stage.dataset.scene,
            declared: Number(stage.dataset.sceneItems ?? 0),
            label: stage.getAttribute('aria-label') ?? '',
            drawn: items.length,
            strayed: items.filter((i) => i.cx < 0 || i.cx > 1 || i.cy < 0 || i.cy > 1).length
          }
        })

      let checkedPages = 0
      let checkedItems = 0
      for (const book of ROUND13_H3_SAMPLE) {
        await page.goto(`${base}/#/books/${book.id}`, { waitUntil: 'networkidle2', timeout: 20000 })
        await page.waitForSelector('.scene[data-scene="dsl"]', { timeout: 8000 })

        for (const [index, expected] of book.pages.entries()) {
          const at = `《${book.title}》p${index + 1}`
          const stage = await readStage()
          if (!stage) throw new Error(`${at} 没有插图舞台`)
          const want = expected.scene?.length ?? 0
          if (!want) throw new Error(`${at} 数据里没有场景，抽样书应当整本升级`)
          if (stage.kind !== 'dsl') throw new Error(`${at} 退回了单 emoji（data-scene=${stage.kind}）`)
          if (stage.declared !== want || stage.drawn !== want) {
            throw new Error(
              `${at} 三个数对不齐：数据 ${want} 件、DOM 声明 ${stage.declared} 件、实际画出 ${stage.drawn} 件`
            )
          }
          if (stage.strayed) throw new Error(`${at} 有 ${stage.strayed} 件元素落在画框外`)
          if (stage.label !== (expected.sceneAlt ?? '')) {
            throw new Error(`${at} 读屏念的是「${stage.label}」，数据写的是「${expected.sceneAlt}」`)
          }
          checkedPages++
          checkedItems += stage.drawn

          if (index < book.pages.length - 1 && !(await clickText(page, '下一页'))) {
            throw new Error(`${at} 之后翻不到下一页`)
          }
        }
      }

      const plainBooks = BOOKS.length - SCENE_BOOK_IDS.length
      return (
        `台账 ${ROUND13_H3.books} 本 / ${ROUND13_H3.pages} 页（门槛 ≥ ${ROUND13_H3.target}）；` +
        `抽样 ${ROUND13_H3_SAMPLE.length} 本逐页比对 ${checkedPages} 页 / ${checkedItems} 件，` +
        `声明与渲染一致；其余 ${plainBooks} 本仍走单 emoji`
      )
    }
  )
}

await browser.close()
server.close()

/* ------------------------------------------------------------------ 输出 */
console.log('\n路由渲染：')
for (const r of rows) {
  console.log(`  ${r.issues ? '✗' : '✓'} ${r.name.padEnd(18)} ${r.path.padEnd(30)} ${r.chars} 字`)
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
