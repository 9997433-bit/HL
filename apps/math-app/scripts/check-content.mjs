/**
 * 内容自检：不开浏览器，直接把题库和生成器跑上几千次，
 * 确认不会出现负数答案、NaN 文案、重复选项、无解或多解的数独。
 *
 * 用法：node --import ./scripts/register-alias.mjs scripts/check-content.mjs
 */
import { WORD_PROBLEMS } from '../src/data/wordProblems.js'
import { BOARD_SPECS, generatePuzzle, solve, conflictsOf } from '../src/utils/sudoku.js'
import { numericOptions } from '../src/utils/random.js'
import { CUES, noteToFreq } from '../src/utils/sound.js'

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
// solve() 走的是随机化回溯：题面若有第二个解，随机顺序迟早会先撞上它，
// 因此「解出来的盘和挖洞前的完整解一模一样」既验了有解，也验了唯一解。
// 4×4 是目前上线的档位，6×6 / 9×9 先把引擎守住，等对应界面接上来。
const SUDOKU_ROUNDS = { 4: 200, 6: 60, 9: 20 }
// 界面上「简单 / 普通 / 挑战」三档给定数，一并验证极端挖洞下仍然唯一解
const CLUE_LEVELS = { 4: [9, 7, 5], 6: [null], 9: [null] }

for (const [sizeKey, rounds] of Object.entries(SUDOKU_ROUNDS)) {
  const size = Number(sizeKey)
  const total = BOARD_SPECS[size].size ** 2
  let solvedSame = 0
  let clean = 0
  let clueMin = total
  for (let i = 0; i < rounds; i++) {
    const clues = CLUE_LEVELS[size][i % CLUE_LEVELS[size].length]
    const { puzzle, solution } = generatePuzzle(clues === null ? { size } : { size, clues })
    const s = solve(puzzle)
    if (s && s.join() === solution.join()) solvedSame++
    else fail(`${size}×${size} 第 ${i} 局数独解不唯一或无解`)
    if (puzzle.every((v, idx) => !v || conflictsOf(puzzle, idx).length === 0)) clean++
    else fail(`${size}×${size} 第 ${i} 局数独题面自带冲突`)
    clueMin = Math.min(clueMin, puzzle.filter(Boolean).length)
  }
  console.log(
    `数独 ${size}×${size} ${rounds} 局：唯一解 ${solvedSame}，题面无冲突 ${clean}，最少给定数 ${clueMin}/${total}`,
  )
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

/* ------------------------------------------------ 音效谱面 */
// Web Audio 合成器在 Node 里跑不起来，但音名解析是纯函数，
// 打错一个音名会让那个音直接消失，这里把五段谱面都验一遍。
if (Math.abs(noteToFreq('A4') - 440) > 1e-9) fail(`A4 应为 440Hz，实际 ${noteToFreq('A4')}`)
if (Math.abs(noteToFreq('C5') - 523.2511) > 1e-3) fail(`C5 频率不对：${noteToFreq('C5')}`)
if (!(noteToFreq('Eb4') < noteToFreq('E4'))) fail('Eb4 应低于 E4')
if (noteToFreq('H4') !== null) fail('非法音名应返回 null')

let noteCount = 0
for (const [name, cue] of Object.entries(CUES)) {
  if (!cue.notes.length) fail(`音效 ${name} 没有音符`)
  if (!(cue.gap >= 0)) fail(`音效 ${name} 的间隔非法：${cue.gap}`)
  for (const note of cue.notes) {
    noteCount++
    const f = noteToFreq(note)
    if (f === null) fail(`音效 ${name} 里的音名无法解析：${note}`)
    else if (!(f > 20 && f < 8000)) fail(`音效 ${name} 的 ${note} 超出可听范围：${f}Hz`)
  }
}
console.log(`音效谱面 ${Object.keys(CUES).length} 段共 ${noteCount} 个音：音名全部可解析`)

console.log(failures ? `\n${failures} 项不通过。` : '\n全部通过。')
process.exit(failures ? 1 : 0)
