/**
 * Round 6 内容硬门槛。
 * 标准：.agent_workspace/ROUND6-ACCEPTANCE.md
 *
 * 固定输出 7 个结果：H1 / H2 数量 / H2 越界 / H3 / H4 / H5 / H6。
 * Round 6 已定义为硬门槛，因此文件存在但不可读取、视图存在但未接路由等情况
 * 一律 FAIL，不以 PENDING 放行。
 */

import fs from 'node:fs'
import path from 'node:path'
import { register } from 'node:module'
import { fileURLToPath } from 'node:url'

register('./alias-loader.mjs', import.meta.url)

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const fails = []
const notes = []

const check = (ok, passMsg, failMsg = passMsg) =>
  (ok ? notes : fails).push(`${ok ? '✓' : '✗'} ${ok ? passMsg : failMsg}`)
const readIfExists = (rel) => {
  try {
    return fs.readFileSync(path.join(root, rel), 'utf8')
  } catch {
    return ''
  }
}
const existsAny = (...rel) => rel.find((p) => fs.existsSync(path.join(root, p)))
const stripComments = (src) =>
  src
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '')

const routerEntries = (src) => {
  const clean = stripComments(src)
  const matches = [...clean.matchAll(/\bpath\s*:\s*(['"])(.*?)\1/g)]
  return matches.map((match, index) => ({
    path: match[2],
    source: clean.slice(match.index, matches[index + 1]?.index ?? clean.length)
  }))
}

const dynamicView = (entry) =>
  entry?.source.match(/\bcomponent\s*:\s*\(\)\s*=>\s*import\(\s*['"]@\/views\/([^'"]+\.vue)['"]\s*\)/)?.[1]

const TARGET_CHARS = 1800
const TARGET_BOOKS = 130
const TARGET_POEMS = 20
const TARGET_GAMES = 5
const TARGET_PROBLEMS = 185
const EXPECTED_RESULTS = 7

const literacyRouter = readIfExists('apps/literacy-app/src/router/index.js')
const literacyRoutes = routerEntries(literacyRouter)
const literacySmoke = stripComments(readIfExists('apps/literacy-app/scripts/smoke.mjs'))

/* H1 字库 */
try {
  const mod = await import('../apps/literacy-app/src/data/characters.js')
  const total = mod.TOTAL_CHARACTERS ?? 0
  check(
    total >= TARGET_CHARS,
    `H1 字库 ${total} 字（要求 ≥ ${TARGET_CHARS}）`,
    `H1 字库 ${total}/${TARGET_CHARS} 字`
  )
} catch (e) {
  check(false, '', `H1 字库读取失败：${e.message}`)
}

/* H2 绘本 */
try {
  const { BOOKS, verifyBookCoverage } = await import('../apps/literacy-app/src/data/books.js')
  const n = Array.isArray(BOOKS) ? BOOKS.length : 0
  check(
    n >= TARGET_BOOKS,
    `H2 绘本 ${n} 本（要求 ≥ ${TARGET_BOOKS}）`,
    `H2 绘本 ${n}/${TARGET_BOOKS} 本`
  )
  try {
    const coverageAvailable = typeof verifyBookCoverage === 'function'
    const bad = coverageAvailable ? verifyBookCoverage() : null
    check(
      coverageAvailable && Array.isArray(bad) && bad.length === 0,
      'H2 verifyBookCoverage 零越界',
      !coverageAvailable
        ? 'H2 缺少 verifyBookCoverage 导出'
        : !Array.isArray(bad)
          ? 'H2 verifyBookCoverage 必须返回数组'
          : `H2 绘本越界 ${bad.length} 本`
    )
  } catch (e) {
    check(false, '', `H2 verifyBookCoverage 执行失败：${e.message}`)
  }
} catch (e) {
  check(false, '', `H2 绘本读取失败：${e.message}`)
  check(false, '', 'H2 verifyBookCoverage 无法执行（绘本模块读取失败）')
}

/* H3 古诗 */
const poemFile = existsAny(
  'apps/literacy-app/src/data/poems.js',
  'apps/literacy-app/src/data/poetry.js'
)
if (poemFile) {
  try {
    const mod = await import(`../${poemFile}`)
    const poems = mod.POEMS ?? mod.default ?? []
    const n = Array.isArray(poems) ? poems.length : Object.keys(poems).length
    check(
      n >= TARGET_POEMS,
      `H3 古诗 ${n} 首（要求 ≥ ${TARGET_POEMS}）`,
      `H3 古诗 ${n}/${TARGET_POEMS} 首`
    )
  } catch (e) {
    check(false, '', `H3 古诗读取失败：${e.message}`)
  }
} else {
  check(false, '', `H3 古诗未接线（要求 ≥ ${TARGET_POEMS} 首）`)
}

/* H4 跟读评测：必须同时有真实路由、评测 pipeline 与浏览器 smoke 断言。 */
const speechEntry = literacyRoutes.find(
  (entry) =>
    /(?:follow[-/]?read|speech[-/]?(?:eval|assess)|read[-/]?aloud)/i.test(entry.path) &&
    dynamicView(entry)
)
const speechView = dynamicView(speechEntry)
const speechViewFile = speechView && `apps/literacy-app/src/views/${speechView}`
const speechPipelineFile = existsAny(
  'apps/literacy-app/src/composables/useSpeechEval.js',
  'apps/literacy-app/src/composables/useFollowRead.js',
  'apps/literacy-app/src/utils/speechEval.js',
  'apps/literacy-app/src/utils/speechRecognition.js'
)
const speechSource = stripComments(
  [speechPipelineFile, speechViewFile].filter(Boolean).map(readIfExists).join('\n')
)
const speechPipeline =
  Boolean(speechPipelineFile || speechViewFile) &&
  /(?:webkit)?SpeechRecognition|SpeechRecognitionEvent/i.test(speechSource) &&
  /MediaRecorder|mediaDevices|getUserMedia|recordedBlob|audioUrl/i.test(speechSource)
const speechRoute =
  Boolean(speechEntry && speechViewFile) && fs.existsSync(path.join(root, speechViewFile))
const speechSmoke =
  /\bROUND6_H4_SMOKE\b/.test(literacySmoke) &&
  /(?:follow[-/]?read|speech[-/]?(?:eval|assess)|read[-/]?aloud|跟读评测)/i.test(literacySmoke)
check(
  speechRoute && speechPipeline && speechSmoke,
  `H4 跟读评测路由、识别/录音降级 pipeline 与 smoke 已接线（${speechEntry?.path}）`,
  `H4 跟读评测未闭环：路由=${speechRoute ? speechEntry.path : '缺失'}，` +
    `识别/录音降级=${speechPipeline ? '齐全' : '缺失'}，smoke=${speechSmoke ? '有' : '缺失'}`
)

/* H5 小游戏 ≥5：注册表每项必须有唯一 id/route/view，且 route 精确接到真实视图。 */
try {
  const games = await import('../apps/literacy-app/src/data/games.js')
  const list = games.GAMES ?? games.default ?? []
  const fresh = Array.isArray(list) ? list.filter((game) => game?.id !== 'listen') : []
  const ids = fresh.map((game) => game?.id).filter(Boolean)
  const routes = fresh.map((game) => game?.route).filter(Boolean)
  const shapeOk = fresh.every(
    (game) =>
      game &&
      ['id', 'name', 'route', 'skill', 'view'].every(
        (field) => typeof game[field] === 'string' && game[field].trim()
      )
  )
  const unique = new Set(ids).size === fresh.length && new Set(routes).size === fresh.length
  const unwired = fresh.filter((game) => {
    const entry = literacyRoutes.find((candidate) => candidate.path === game.route)
    const view = dynamicView(entry)
    return (
      !entry ||
      view !== `${game.view}.vue` ||
      !fs.existsSync(path.join(root, 'apps/literacy-app/src/views', `${game.view}.vue`))
    )
  })
  const ok =
    fresh.length >= TARGET_GAMES &&
    shapeOk &&
    unique &&
    unwired.length === 0
  const wiring = unwired.length
    ? `；未精确接线 ${unwired.map((game) => `${game?.id ?? '?'}(${game?.route ?? '?'})`).join('、')}`
    : ''
  const registry = !shapeOk ? '；注册表字段不完整' : !unique ? '；id/route 不唯一' : ''
  check(
    ok,
    `H5 识字小游戏 ${fresh.length} 款，注册表路由全部精确接线（要求 ≥ ${TARGET_GAMES}，不含 listen）`,
    `H5 识字小游戏 ${fresh.length}/${TARGET_GAMES} 款（不含 listen）${registry}${wiring}`
  )
} catch (e) {
  check(false, '', `H5 小游戏读取失败：${e.message}`)
}

/* H6 母题 */
try {
  const wp = await import('../apps/math-app/src/data/wordProblems.js')
  const n = wp.WORD_PROBLEM_COUNT ?? wp.WORD_PROBLEMS?.length ?? 0
  check(
    n >= TARGET_PROBLEMS,
    `H6 应用题母题 ${n} 个（要求 ≥ ${TARGET_PROBLEMS}）`,
    `H6 应用题母题 ${n}/${TARGET_PROBLEMS} 个`
  )
} catch (e) {
  check(false, '', `H6 母题读取失败：${e.message}`)
}

if (notes.length + fails.length !== EXPECTED_RESULTS) {
  fails.push(
    `✗ 门禁自身结果数异常：${notes.length + fails.length}/${EXPECTED_RESULTS}，请修复 check-round6.mjs`
  )
}

notes.forEach((n) => console.log(' ', n))
if (fails.length) {
  console.log('')
  fails.forEach((f) => console.log(' ', f))
}
console.log(
  `\nRound 6 内容门禁：${notes.length}/${EXPECTED_RESULTS} 项通过，${fails.length} 项失败。`
)
process.exit(fails.length ? 1 : 0)
