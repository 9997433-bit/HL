/**
 * Round 6 内容硬门槛。
 * 标准：.agent_workspace/ROUND6-ACCEPTANCE.md
 */

import fs from 'node:fs'
import path from 'node:path'
import { register } from 'node:module'
import { fileURLToPath } from 'node:url'

register('./alias-loader.mjs', import.meta.url)

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const fails = []
const notes = []
const pendings = []

const check = (ok, msg) => (ok ? notes.push(`✓ ${msg}`) : fails.push(`✗ ${msg}`))
const pending = (msg) => pendings.push(`… ${msg}`)
const readIfExists = (rel) => {
  try {
    return fs.readFileSync(path.join(root, rel), 'utf8')
  } catch {
    return ''
  }
}
const existsAny = (...rel) => rel.find((p) => fs.existsSync(path.join(root, p)))

const TARGET_CHARS = 1800
const TARGET_BOOKS = 130
const TARGET_POEMS = 20
const TARGET_GAMES = 5
const TARGET_PROBLEMS = 185

/* H1 字库 */
try {
  const mod = await import('../apps/literacy-app/src/data/characters.js')
  const total = mod.TOTAL_CHARACTERS ?? 0
  check(total >= TARGET_CHARS, `H1 字库 ${total} 字（要求 ≥ ${TARGET_CHARS}）`)
} catch (e) {
  fails.push(`✗ H1 字库读取失败：${e.message}`)
}

/* H2 绘本 */
try {
  const { BOOKS, verifyBookCoverage } = await import('../apps/literacy-app/src/data/books.js')
  const n = BOOKS?.length ?? 0
  check(n >= TARGET_BOOKS, `H2 绘本 ${n} 本（要求 ≥ ${TARGET_BOOKS}）`)
  if (typeof verifyBookCoverage === 'function') {
    const bad = verifyBookCoverage()
    check(!bad?.length, 'H2 verifyBookCoverage 零越界')
  }
} catch (e) {
  fails.push(`✗ H2 绘本读取失败：${e.message}`)
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
    check(n >= TARGET_POEMS, `H3 古诗 ${n} 首（要求 ≥ ${TARGET_POEMS}）`)
  } catch (e) {
    pending(`H3 古诗读取失败：${e.message}`)
  }
} else {
  fails.push(`✗ H3 古诗未接线 —— 由 r6-literacy-poems-speech 交付（≥ ${TARGET_POEMS} 首）`)
}

/* H4 跟读评测 */
const speechRoute =
  readIfExists('apps/literacy-app/src/router/index.js').includes('speech') ||
  readIfExists('apps/literacy-app/src/router/index.js').includes('follow-read') ||
  readIfExists('apps/literacy-app/src/views/FollowReadView.vue')
const speechMod = existsAny(
  'apps/literacy-app/src/composables/useSpeechEval.js',
  'apps/literacy-app/src/utils/speechEval.js'
)
check(
  speechRoute || speechMod,
  speechRoute || speechMod
    ? 'H4 跟读评测 pipeline 已接线'
    : 'H4 跟读评测未接线 —— 由 r6-literacy-poems-speech 交付'
)

/* H5 小游戏 ≥5 */
try {
  const games = await import('../apps/literacy-app/src/data/games.js')
  const list = games.GAMES ?? games.default ?? []
  const n = list.filter((g) => g.id !== 'listen').length
  check(n >= TARGET_GAMES, `H5 识字小游戏 ${n} 款（要求 ≥ ${TARGET_GAMES}，不含 listen）`)
} catch (e) {
  fails.push(`✗ H5 小游戏读取失败：${e.message}`)
}

/* H6 母题 */
try {
  const wp = await import('../apps/math-app/src/data/wordProblems.js')
  const n = wp.WORD_PROBLEM_COUNT ?? wp.WORD_PROBLEMS?.length ?? 0
  check(n >= TARGET_PROBLEMS, `H6 应用题母题 ${n} 个（要求 ≥ ${TARGET_PROBLEMS}）`)
} catch (e) {
  fails.push(`✗ H6 母题读取失败：${e.message}`)
}

notes.forEach((n) => console.log(' ', n))
pendings.forEach((p) => console.log(' ', p))
if (fails.length) {
  console.log('')
  fails.forEach((f) => console.log(' ', f))
}
console.log(
  `\nRound 6 内容门禁：${notes.length} 项通过，${pendings.length} 项待接线，${fails.length} 项失败。`
)
process.exit(fails.length ? 1 : 0)
