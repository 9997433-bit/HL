import { WORD_PROBLEMS } from '../src/data/wordProblems.js'
import { generatePuzzle, solve, conflictsOf } from '../src/utils/sudoku4.js'
import { numericOptions } from '../src/utils/random.js'

console.log('应用题数:', WORD_PROBLEMS.length)
const bad = WORD_PROBLEMS.filter(p => typeof p.answer !== 'number' || !p.text || !p.equation)
console.log('字段缺失:', bad.length, bad.map(b=>b.id))
console.log('一步/两步:', WORD_PROBLEMS.filter(p=>p.steps===1).length, '/', WORD_PROBLEMS.filter(p=>p.steps===2).length)
console.log('场景种类:', new Set(WORD_PROBLEMS.map(p=>p.scene)).size)
const dupIds = WORD_PROBLEMS.length - new Set(WORD_PROBLEMS.map(p=>p.id)).size
console.log('重复 id:', dupIds)

// 数独：随机生成 200 局，校验唯一解与题面合法
let ok = 0, uniq = 0
for (let i = 0; i < 200; i++) {
  const { puzzle, solution } = generatePuzzle()
  const s = solve(puzzle)
  if (s && s.join() === solution.join()) ok++
  const clues = puzzle.filter(v=>v).length
  const conflictFree = puzzle.every((v, idx) => !v || conflictsOf(puzzle, idx).size === 0)
  if (conflictFree && clues >= 4) uniq++
}
console.log('数独 200 局：解一致', ok, '题面无冲突', uniq)

// 选项生成器：不重复、含答案、数量正确
let optOk = 0
for (let i = 0; i < 3000; i++) {
  const ans = Math.floor(Math.random()*100)
  const o = numericOptions(ans, { count: 4, spread: 5, min: 0, max: 100 })
  if (o.length === 4 && new Set(o).size === 4 && o.includes(ans) && o.every(n=>n>=0&&n<=100)) optOk++
}
console.log('numericOptions 3000 次合规:', optOk)
