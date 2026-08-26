/**
 * 内容自检：不开浏览器，直接把题库和生成器跑上几千次，
 * 确认不会出现负数答案、NaN 文案、重复选项、无解或多解的数独。
 *
 * 用法：node --import ./scripts/register-alias.mjs scripts/check-content.mjs
 */
import { WORD_PROBLEMS } from '../src/data/wordProblems.js'
import { generatePuzzle, solve, conflictsOf } from '../src/utils/sudoku4.js'
import { numericOptions } from '../src/utils/random.js'

let failures = 0
const fail = (msg) => {
  failures++
  console.log(`  ✗ ${msg}`)
}

/* ------------------------------------------------ 应用题母题 */
console.log(`应用题母题 ${WORD_PROBLEMS.length} 个：`)
const scenes = new Set()
let oneStep = 0
let twoStep = 0

for (const tpl of WORD_PROBLEMS) {
  scenes.add(tpl.scene)
  if (tpl.steps === 2) twoStep++
  else oneStep++
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
    if (!q.equation || !q.unit) fail(`${tpl.id} 缺少算式或单位`)
  }
}
console.log(`  场景 ${scenes.size} 种，一步 ${oneStep} 个 / 两步 ${twoStep} 个，每个母题各生成 2000 道`)

/* ------------------------------------------------ 数独 */
const ROUNDS = 200
let solvedSame = 0
let clean = 0
let clueMin = 99
for (let i = 0; i < ROUNDS; i++) {
  const { puzzle, solution } = generatePuzzle()
  const s = solve(puzzle)
  if (s && s.join() === solution.join()) solvedSame++
  else fail(`第 ${i} 局数独解不唯一或无解`)
  if (puzzle.every((v, idx) => !v || conflictsOf(puzzle, idx).length === 0)) clean++
  else fail(`第 ${i} 局数独题面自带冲突`)
  clueMin = Math.min(clueMin, puzzle.filter(Boolean).length)
}
console.log(`数独 ${ROUNDS} 局：唯一解 ${solvedSame}，题面无冲突 ${clean}，最少给定数 ${clueMin}`)

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

console.log(failures ? `\n${failures} 项不通过。` : '\n全部通过。')
process.exit(failures ? 1 : 0)
