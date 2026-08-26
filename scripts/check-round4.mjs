/**
 * Round 4 内容硬门槛（stub）。
 *
 * 标准见 .agent_workspace/ROUND4-ACCEPTANCE.md §4：
 *   - 硬门槛：识字字库 ≥ 500（L-M1）。当前基线只有 200 字，本脚本在
 *     r4-literacy-500chars 交付前 **预期 FAIL**，这是有意为之的红灯。
 *   - 探针（PENDING，不计失败）：错题本 / adaptive / 种子化 PRNG。
 *     对应功能合入时，责任分支必须在同一 PR 内把探针升级为硬门槛。
 *
 * 运行：node scripts/check-round4.mjs（无需浏览器与构建产物）
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

const fails = []
const notes = []
const pendings = []

const check = (ok, msg) => (ok ? notes.push(`✓ ${msg}`) : fails.push(`✗ ${msg}`))
const pending = (msg) => pendings.push(`… ${msg}`)
const existsAny = (...rel) => rel.some((p) => fs.existsSync(path.join(root, p)))

/* ------------------------------------------------ 硬门槛：字库 ≥ 500（L-M1） */
const TARGET_CHARS = 500
try {
  const mod = await import('../apps/literacy-app/src/data/characters.js')
  const idx = await import('../apps/literacy-app/src/data/character-index.js').catch(() => ({}))
  const TOTAL_CHARACTERS = mod.TOTAL_CHARACTERS ?? idx.TOTAL_CHARACTERS ?? 0
  check(
    TOTAL_CHARACTERS >= TARGET_CHARS,
    TOTAL_CHARACTERS >= TARGET_CHARS
      ? `字库 ${TOTAL_CHARACTERS} 字（Round 4 要求 ≥ ${TARGET_CHARS}）`
      : `字库 ${TOTAL_CHARACTERS}/${TARGET_CHARS} 字 —— Round 4 要求 ≥ ${TARGET_CHARS}（L-M1）。` +
          `请由 r4-literacy-500chars 分支脚本化扩充 apps/literacy-app/src/data/characters.js` +
          ` 与 shared/data/common-hanzi.json（保持 check:data 全过）后重跑本脚本。`
  )
} catch (err) {
  check(false, `无法读取字库（apps/literacy-app/src/data/characters.js）：${err.message}`)
}

/* --------------------------------- 探针（PENDING，不拦截；实现后升级为硬门槛） */

// M-M10 错题本：按 questionId 记录 + 重练答对移出
try {
  const progressSrc = fs.readFileSync(path.join(root, 'apps/math-app/src/stores/progress.js'), 'utf8')
  if (/wrongBook/.test(progressSrc) || existsAny('apps/math-app/src/components/WrongBook.vue')) {
    notes.push('✓ M-M10 错题本已接线（progress.wrongBook + WrongBook 组件）')
  } else {
    pending('M-M10 错题本未接线 —— 由 r4-math-wrongbook 交付')
  }
} catch {
  pending('M-M10 无法读取 progress store，跳过探针')
}

// M-M9 自适应调度：连对升档 / 连错降档 / 弱项优先
if (existsAny(
  'apps/math-app/src/core/engine/adaptive.js',
  'apps/math-app/src/utils/adaptive.js',
  'apps/math-app/src/core/adaptive.js'
)) {
  notes.push('✓ M-M9 adaptive.js 已接线')
} else {
  pending('M-M9 adaptive.js 未接线 —— 由 r4-math-wrongbook 交付')
}

// M-M2 / M-P9 种子化 PRNG：题目 ID = 母题 + seed，≥300 可复现
try {
  const randomSrc = fs.readFileSync(path.join(root, 'apps/math-app/src/utils/random.js'), 'utf8')
  if (/mulberry32|createRng|questionId/i.test(randomSrc)) {
    notes.push('✓ M-M2/M-P9 种子化 PRNG 已接线（random.js）')
  } else {
    pending('M-M2/M-P9 种子化 PRNG 未接线 —— 由 r4-math-seed-daily 交付')
  }
} catch {
  pending('M-M2/M-P9 无法读取 apps/math-app/src/utils/random.js，跳过探针')
}

/* ----------------------------------------------------------------- 输出 */
notes.forEach((n) => console.log(' ', n))
pendings.forEach((p) => console.log(' ', p))
if (fails.length) {
  console.log('')
  fails.forEach((f) => console.log(' ', f))
}

console.log(
  `\nRound 4 内容门禁：${notes.length} 项通过，${pendings.length} 项待接线（探针），${fails.length} 项失败。`
)
if (fails.length) {
  console.log('说明：在 Round 4 各分支交付前，本门禁 FAIL 属预期红灯，不代表 Round 3 基线回归。')
}

process.exit(fails.length ? 1 : 0)
