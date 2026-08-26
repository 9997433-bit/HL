/**
 * Round 5 内容硬门槛。
 *
 * 标准见 .agent_workspace/ROUND5-ACCEPTANCE.md §4：
 *   - 六项硬门槛（FAIL 即退出码 1）：字库 ≥1000 / 绘本 ≥30（零越界）/ 成语 ≥60 /
 *     数学母题 ≥100 / 数形演示 ≥7 类 / 新识字小游戏 ≥3 款。
 *     当前基线（aacd996）六项**预期全 FAIL**，这是有意为之的红灯，
 *     由 Round 5 各责任分支逐项转绿。
 *   - 探针（PENDING，不计失败）：字源动画 pipeline / 七巧板 / 分与合 / 竖式专题。
 *     对应功能合入时，责任分支必须在同一 PR 内把探针升级为硬门槛。
 *
 * 运行：npm run check:round5（无需浏览器与构建产物）
 * 注册表约定见 ROUND5-ACCEPTANCE.md §5：纯数据模块、不得 import .vue。
 */

import fs from 'node:fs'
import path from 'node:path'
import { register } from 'node:module'
import { fileURLToPath } from 'node:url'

// App 源码里的 `@/` 走 Vite 别名，Node 直接 import 时得自己还原
register('./alias-loader.mjs', import.meta.url)

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

/* ---------------------------------------------------------------- alias hook
 * 应用源码内部用 Vite 别名 `@/` 指向各自 src/。为了让本脚本在 Node 里直接
 * import 数据模块（如 wordProblems.js -> '@/utils/random'），这里注册一个
 * resolve hook：按「导入方所在 apps/<app>/src/」把 `@/` 还原成绝对路径。
 */
const aliasHook = `
export function resolve(specifier, context, nextResolve) {
  if (specifier.startsWith('@/') && context.parentURL) {
    const m = context.parentURL.match(/^(.*\\/apps\\/[^/]+\\/src)\\//)
    if (m) {
      let target = m[1] + '/' + specifier.slice(2)
      if (!/\\.(js|mjs|json)$/.test(target)) target += '.js'
      return nextResolve(target, context)
    }
  }
  return nextResolve(specifier, context)
}
`
register(`data:text/javascript;base64,${Buffer.from(aliasHook).toString('base64')}`)

const fails = []
const notes = []
const pendings = []

const check = (ok, msg) => (ok ? notes.push(`✓ ${msg}`) : fails.push(`✗ ${msg}`))
const pending = (msg) => pendings.push(`… ${msg}`)
const existsAny = (...rel) => rel.find((p) => fs.existsSync(path.join(root, p)))
const readIfExists = (rel) => {
  try {
    return fs.readFileSync(path.join(root, rel), 'utf8')
  } catch {
    return ''
  }
}

const TARGET_CHARS = 1000
const TARGET_BOOKS = 30
const TARGET_IDIOMS = 60
const TARGET_PROBLEMS = 100
const TARGET_VISUAL_DEMOS = 7
const TARGET_NEW_GAMES = 3
const TARGET_ETYMOLOGY = 50

/* ------------------------------------------- H1 字库 ≥ 1000（L-M1） */
try {
  const mod = await import('../apps/literacy-app/src/data/characters.js')
  const idx = await import('../apps/literacy-app/src/data/character-index.js').catch(() => ({}))
  const total = Math.max(mod.TOTAL_CHARACTERS ?? 0, idx.TOTAL_CHARACTERS ?? 0)
  check(
    total >= TARGET_CHARS,
    total >= TARGET_CHARS
      ? `H1 字库 ${total} 字（要求 ≥ ${TARGET_CHARS}）`
      : `H1 字库 ${total}/${TARGET_CHARS} 字 —— 由 r5-literacy-1000chars 脚本化扩充` +
          `（character-index.js + chars/uN.js 懒加载分片，保持 check:data 全过）`
  )
} catch (err) {
  check(false, `H1 无法读取字库：${err.message}`)
}

/* ------------------------- H2 绘本 ≥ 30 且 verifyBookCoverage 零越界（L-M5） */
try {
  const { BOOKS, verifyBookCoverage } = await import('../apps/literacy-app/src/data/books.js')
  const n = BOOKS.length
  check(
    n >= TARGET_BOOKS,
    n >= TARGET_BOOKS
      ? `H2 绘本 ${n} 本（要求 ≥ ${TARGET_BOOKS}）`
      : `H2 绘本 ${n}/${TARGET_BOOKS} 本 —— 由 r5-literacy-books 交付（正文仅用已学字）`
  )
  const violations = typeof verifyBookCoverage === 'function' ? verifyBookCoverage() : []
  check(
    violations.length === 0,
    violations.length === 0
      ? 'H2 verifyBookCoverage 零越界'
      : `H2 绘本越界 ${violations.length} 本：` +
          violations.map((v) => `《${v.book}》缺 ${v.missing.join('')}`).join('；')
  )
} catch (err) {
  check(false, `H2 无法读取绘本：${err.message}`)
}

/* ------------------------------------------- H3 成语 ≥ 60（L-M8） */
try {
  const { IDIOMS } = await import('../apps/literacy-app/src/data/idioms.js')
  const n = IDIOMS.length
  check(
    n >= TARGET_IDIOMS,
    n >= TARGET_IDIOMS
      ? `H3 成语 ${n} 个（要求 ≥ ${TARGET_IDIOMS}）`
      : `H3 成语 ${n}/${TARGET_IDIOMS} 个 —— 由 r5-literacy-idioms-etymology 交付`
  )
} catch (err) {
  check(false, `H3 无法读取成语：${err.message}`)
}

/* --------------------------------------- H4 应用题母题 ≥ 100（M-M3） */
try {
  await import('../apps/math-app/scripts/register-alias.mjs')
  const wp = await import('../apps/math-app/src/data/wordProblems.js')
  const n = wp.WORD_PROBLEMS?.length ?? wp.default?.length ?? 0
  check(
    n >= TARGET_PROBLEMS,
    n >= TARGET_PROBLEMS
      ? `H4 应用题母题 ${n} 个（要求 ≥ ${TARGET_PROBLEMS}）`
      : `H4 应用题母题 ${n}/${TARGET_PROBLEMS} 个 —— 由 r5-math-problems-100 交付` +
          `（语义模板 × 场景皮肤，check:content 校验）`
  )
} catch (err) {
  check(false, `H4 无法读取应用题母题：${err.message}`)
}

/* -------------------------------------- H5 数形演示 ≥ 7 类（M-M8） */
const demoFile = existsAny(
  'apps/math-app/src/data/visualDemos.js',
  'apps/math-app/src/core/visual-demos/index.js'
)
if (demoFile) {
  try {
    const mod = await import(`../${demoFile}`)
    const demos = mod.VISUAL_DEMOS ?? mod.default ?? []
    const n = Array.isArray(demos) ? demos.length : Object.keys(demos).length
    check(
      n >= TARGET_VISUAL_DEMOS,
      n >= TARGET_VISUAL_DEMOS
        ? `H5 数形演示 ${n} 类（要求 ≥ ${TARGET_VISUAL_DEMOS}）`
        : `H5 数形演示 ${n}/${TARGET_VISUAL_DEMOS} 类 —— 由 r5-math-manipulatives 交付`
    )
  } catch (err) {
    check(false, `H5 数形演示注册表读取失败（须为纯数据模块，不得 import .vue）：${err.message}`)
  }
} else {
  check(
    false,
    `H5 数形演示未接线 —— 期望 apps/math-app/src/data/visualDemos.js 导出 VISUAL_DEMOS` +
      `（≥ ${TARGET_VISUAL_DEMOS} 类，实物→图形→算式三段，约定见 ROUND5-ACCEPTANCE.md §5）`
  )
}

/* ------------------------------- H6 新识字小游戏 ≥ 3 款（L-M12） */
const GAMES_REGISTRY = 'apps/literacy-app/src/data/games.js'
if (existsAny(GAMES_REGISTRY)) {
  try {
    const mod = await import(`../${GAMES_REGISTRY}`)
    const games = mod.GAMES ?? mod.default ?? []
    const fresh = games.filter((g) => g.id !== 'listen')
    check(
      fresh.length >= TARGET_NEW_GAMES,
      fresh.length >= TARGET_NEW_GAMES
        ? `H6 新识字小游戏 ${fresh.length} 款（要求 ≥ ${TARGET_NEW_GAMES}，不含 listen）`
        : `H6 新识字小游戏 ${fresh.length}/${TARGET_NEW_GAMES} 款 —— 由 r5-literacy-minigames 交付`
    )
    const routerSrc = readIfExists('apps/literacy-app/src/router/index.js')
    const unwired = fresh.filter((g) => g.route && !routerSrc.includes(g.route))
    check(
      unwired.length === 0,
      unwired.length === 0
        ? 'H6 GAMES 注册表路由全部接线'
        : `H6 小游戏路由未接线：${unwired.map((g) => `${g.id}(${g.route})`).join('、')}`
    )
  } catch (err) {
    check(false, `H6 GAMES 注册表读取失败（须为纯数据模块）：${err.message}`)
  }
} else {
  const views = fs
    .readdirSync(path.join(root, 'apps/literacy-app/src/views'))
    .filter((f) => /GameView\.vue$/.test(f) && f !== 'ListenGameView.vue')
  check(
    false,
    `H6 小游戏注册表未接线 —— 期望 ${GAMES_REGISTRY} 导出 GAMES` +
      `（每项 id/name/route/skill/view，约定见 ROUND5-ACCEPTANCE.md §5）；` +
      `当前新增 *GameView.vue 视图 ${views.length} 个（要求 ≥ ${TARGET_NEW_GAMES}）`
  )
}

/* --------------------------------- 探针（PENDING，不拦截；合入后升级为硬门槛） */

// L-M6 字源动画 pipeline：≥ 50 字可演示
const etymologyFile = existsAny(
  'apps/literacy-app/src/data/etymology.js',
  'apps/literacy-app/src/data/etymology/index.js'
)
if (etymologyFile) {
  try {
    const mod = await import(`../${etymologyFile}`)
    const chars = mod.ETYMOLOGY_CHARS ?? mod.default ?? []
    const n = Array.isArray(chars) ? chars.length : Object.keys(chars).length
    if (n >= TARGET_ETYMOLOGY) notes.push(`✓ L-M6 字源动画 ${n} 字（要求 ≥ ${TARGET_ETYMOLOGY}）`)
    else pending(`L-M6 字源动画 ${n}/${TARGET_ETYMOLOGY} 字 —— 由 r5-literacy-idioms-etymology 补足`)
  } catch (err) {
    pending(`L-M6 字源注册表读取失败：${err.message}`)
  }
} else {
  pending('L-M6 字源动画 pipeline 未接线 —— 由 r5-literacy-idioms-etymology 交付（≥50 字）')
}

// M-M5 七巧板 / M-M13 分与合 / M-M11 竖式专题
const manipulatives = [
  ['M-M5 七巧板', ['apps/math-app/src/modules/tangram']],
  ['M-M13 分与合', ['apps/math-app/src/modules/compose-ten', 'apps/math-app/src/modules/compose']],
  ['M-M11 竖式专题', ['apps/math-app/src/modules/vertical', 'apps/math-app/src/modules/vertical-arithmetic']]
]
const modulesSrc = readIfExists('apps/math-app/src/data/modules.js')
for (const [label, dirs] of manipulatives) {
  const found = existsAny(...dirs)
  if (found) {
    const slug = path.basename(found)
    if (modulesSrc.includes(slug)) notes.push(`✓ ${label} 已接线（${found}）`)
    else pending(`${label} 目录存在但未注册进 modules.js —— 补齐后升级为硬门槛`)
  } else {
    pending(`${label} 未接线 —— 由 r5-math-manipulatives 交付（期望 ${dirs[0]}/）`)
  }
}

/* ----------------------------------------------------------------- 输出 */
notes.forEach((n) => console.log(' ', n))
pendings.forEach((p) => console.log(' ', p))
if (fails.length) {
  console.log('')
  fails.forEach((f) => console.log(' ', f))
}

console.log(
  `\nRound 5 内容门禁：${notes.length} 项通过，${pendings.length} 项待接线（探针），${fails.length} 项失败。`
)
if (fails.length) {
  console.log('说明：在 Round 5 各分支交付前，本门禁 FAIL 属预期红灯，不代表 Round 4 基线回归。')
}

process.exit(fails.length ? 1 : 0)
