/**
 * Round 5 内容硬门槛。
 *
 * 标准见 .agent_workspace/ROUND5-ACCEPTANCE.md
 * 运行：node scripts/check-round5.mjs
 */

import fs from 'node:fs'
import path from 'node:path'
import { register } from 'node:module'
import { fileURLToPath } from 'node:url'

// App 源码里的 `@/` 走 Vite 别名，Node 直接 import 时得自己还原
register('./alias-loader.mjs', import.meta.url)

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const fails = []
const notes = []

const check = (ok, msg) => (ok ? notes.push(`✓ ${msg}`) : fails.push(`✗ ${msg}`))

const TARGET_CHARS = 1000
const TARGET_BOOKS = 30
const TARGET_IDIOMS = 60
const TARGET_PROBLEMS = 100
const TARGET_VISUAL_DEMOS = 7

try {
  const mod = await import('../apps/literacy-app/src/data/characters.js')
  const total = mod.TOTAL_CHARACTERS ?? 0
  check(total >= TARGET_CHARS, `字库 ${total} 字（Round 5 要求 ≥ ${TARGET_CHARS}）`)
} catch (err) {
  check(false, `无法读取字库：${err.message}`)
}

try {
  const { BOOKS } = await import('../apps/literacy-app/src/data/books.js')
  check(BOOKS.length >= TARGET_BOOKS, `绘本 ${BOOKS.length} 本（Round 5 要求 ≥ ${TARGET_BOOKS}）`)
} catch (err) {
  check(false, `无法读取绘本：${err.message}`)
}

try {
  const { IDIOMS } = await import('../apps/literacy-app/src/data/idioms.js')
  check(IDIOMS.length >= TARGET_IDIOMS, `成语 ${IDIOMS.length} 个（Round 5 要求 ≥ ${TARGET_IDIOMS}）`)
} catch (err) {
  check(false, `无法读取成语：${err.message}`)
}

try {
  const wp = await import('../apps/math-app/src/data/wordProblems.js')
  const count = wp.WORD_PROBLEMS?.length ?? wp.default?.length ?? 0
  check(count >= TARGET_PROBLEMS, `应用题母题 ${count} 个（Round 5 要求 ≥ ${TARGET_PROBLEMS}）`)
} catch (err) {
  check(false, `无法读取应用题母题：${err.message}`)
}

// 数形演示：约定目录或注册表
const demoPaths = [
  'apps/math-app/src/data/visualDemos.js',
  'apps/math-app/src/core/visual-demos/index.js'
]
const demoFile = demoPaths.find((p) => fs.existsSync(path.join(root, p)))
if (demoFile) {
  try {
    const mod = await import(`../${demoFile}`)
    const demos = mod.VISUAL_DEMOS ?? mod.default ?? []
    const n = Array.isArray(demos) ? demos.length : Object.keys(demos).length
    check(n >= TARGET_VISUAL_DEMOS, `数形演示 ${n} 类（Round 5 要求 ≥ ${TARGET_VISUAL_DEMOS}）`)
  } catch (err) {
    check(false, `数形演示注册表读取失败：${err.message}`)
  }
} else {
  check(false, `数形演示未接线（期望 ${demoPaths[0]} 或等价注册表）`)
}

notes.forEach((n) => console.log(' ', n))
if (fails.length) {
  console.log('')
  fails.forEach((f) => console.log(' ', f))
}
console.log(`\nRound 5 内容门禁：${notes.length} 项通过，${fails.length} 项失败。`)
process.exit(fails.length ? 1 : 0)
