/**
 * 内容自检：不开浏览器，直接把题库和生成器跑上几千次，
 * 确认不会出现负数答案、NaN 文案、重复选项、无解或多解的数独。
 *
 * 用法：node --import ./scripts/register-alias.mjs scripts/check-content.mjs
 */
import { WORD_PROBLEMS, WORD_PROBLEM_TAGS, problemsOfTier } from '../src/data/wordProblems.js'
import {
  conflictsOf,
  countSolutions,
  generateSudoku,
  solve,
  specOf,
} from '../src/core/engine/sudoku.js'
import { numericOptions } from '../src/utils/random.js'
import { ERROR_TAGS } from '../src/data/errorTags.js'

const MIN_TEMPLATES = 25

let failures = 0
const fail = (msg) => {
  failures++
  console.log(`  ✗ ${msg}`)
}

/* ------------------------------------------------ 应用题母题 */
console.log(`应用题母题 ${WORD_PROBLEMS.length} 个：`)
if (WORD_PROBLEMS.length < MIN_TEMPLATES) {
  fail(`母题只有 ${WORD_PROBLEMS.length} 个，少于要求的 ${MIN_TEMPLATES} 个`)
}

const ids = new Set()
const scenes = new Set()
const byStep = { 1: 0, 2: 0, 3: 0 }

for (const tpl of WORD_PROBLEMS) {
  if (ids.has(tpl.id)) fail(`母题 id 重复：${tpl.id}`)
  ids.add(tpl.id)
  scenes.add(tpl.scene)
  byStep[Math.min(3, tpl.steps ?? 1)] += 1
  if (typeof tpl.make !== 'function') {
    fail(`${tpl.id} 没有 make() 生成器`)
    continue
  }
  for (let i = 0; i < 2000; i++) {
    let q
    try {
      q = tpl.make()
    } catch (err) {
      fail(`${tpl.id} 第 ${i} 次生成抛错：${err.message}`)
      break
    }
    if (!Number.isInteger(q.answer)) fail(`${tpl.id} 答案不是整数：${q.answer}`)
    if (q.answer < 0) fail(`${tpl.id} 出现负数答案：${q.answer}`)
    if (/NaN|undefined|\{/.test(q.text)) fail(`${tpl.id} 题干渲染异常：${q.text}`)
    if (/NaN|undefined/.test(q.equation)) fail(`${tpl.id} 算式渲染异常：${q.equation}`)
    if (!q.equation || !q.unit) fail(`${tpl.id} 缺少算式或单位`)
    if (!q.hint) fail(`${tpl.id} 缺少提示文案`)
  }
}
console.log(
  `  ${WORD_PROBLEM_TAGS.length} 类语义标签 / ${scenes.size} 种场景，` +
    `一步 ${byStep[1]} · 两步 ${byStep[2]} · 进阶 ${byStep[3]}，每个母题各生成 2000 道`,
)

for (const tierId of ['one', 'two', 'multi']) {
  if (problemsOfTier(tierId).length === 0) fail(`难度档「${tierId}」一道母题都没有`)
}

/* ------------------------------------------------ 数独三档 */
for (const [sizeKey, holes, rounds] of [
  [4, 11, 200],
  [6, 24, 60],
  [9, 52, 12],
]) {
  const spec = specOf(sizeKey)
  let unique = 0
  let clean = 0
  let clueMin = Infinity
  let worstMs = 0
  for (let i = 0; i < rounds; i++) {
    const t0 = performance.now()
    const { puzzle, solution } = generateSudoku(sizeKey, holes)
    worstMs = Math.max(worstMs, performance.now() - t0)

    const s = solve(puzzle, spec)
    if (s && s.join() === solution.join()) unique += 1
    else fail(`${sizeKey}×${sizeKey} 第 ${i} 局回填出的解和答案不一致`)
    if (countSolutions(puzzle, spec, 2) !== 1) fail(`${sizeKey}×${sizeKey} 第 ${i} 局解不唯一`)

    if (puzzle.every((v, idx) => !v || conflictsOf(puzzle, spec, idx).length === 0)) clean += 1
    else fail(`${sizeKey}×${sizeKey} 第 ${i} 局题面自带冲突`)
    clueMin = Math.min(clueMin, puzzle.filter(Boolean).length)
  }
  console.log(
    `数独 ${sizeKey}×${sizeKey} ${rounds} 局：唯一解 ${unique}，题面无冲突 ${clean}，` +
      `最少给定数 ${clueMin}，最慢生成 ${worstMs.toFixed(1)}ms`,
  )
  // 9×9 生成走的是「挖一格校验一次唯一解」，超过 1 秒就说明挖洞数需要下调
  if (worstMs > 1000) fail(`${sizeKey}×${sizeKey} 生成最慢 ${worstMs.toFixed(0)}ms，会卡住界面`)
}

/* ------------------------------------------------ 选项生成器 */
let optOk = 0
const TRIES = 5000
for (let i = 0; i < TRIES; i++) {
  const ans = Math.floor(Math.random() * 100)
  const opts = numericOptions(ans, { count: 4, spread: 5, min: 0, max: 100 })
  if (
    opts.length === 4 &&
    new Set(opts).size === 4 &&
    opts.includes(ans) &&
    opts.every((n) => Number.isInteger(n) && n >= 0 && n <= 100)
  ) {
    optOk++
  }
}
if (optOk !== TRIES) fail(`numericOptions ${TRIES - optOk} 次不合规`)
console.log(`选项生成器 ${TRIES} 次：合规 ${optOk}`)

/* ------------------------------------------------ 错因标签词典 */
for (const [id, info] of Object.entries(ERROR_TAGS)) {
  if (!info.label || !info.tip) fail(`错因标签 ${id} 缺少文案`)
}
console.log(`错因标签 ${Object.keys(ERROR_TAGS).length} 条`)

console.log(failures ? `\n${failures} 项不通过。` : '\n全部通过。')
process.exit(failures ? 1 : 0)
