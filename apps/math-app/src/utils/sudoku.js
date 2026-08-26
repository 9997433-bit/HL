/**
 * 数独引擎 —— 全应用唯一的数独入口，支持 4×4 / 6×6 / 9×9 三档棋盘。
 *
 * 盘面一律用一维数组表示，0 代表空格；棋盘档位由数组长度推断，
 * 所以调用方只在需要生成新题时才关心 size。
 *
 * 生成流程：随机化回溯填出完整解 → 打乱顺序逐格挖洞 → 每挖一格用解计数器
 * 验证仍然唯一解，破坏唯一性就把数字填回去。这样出的题永远只有一个答案。
 */
import { shuffle } from '@/utils/random'

/** 各档位的宫格布局：size = 边长，boxW/boxH = 宫的宽高 */
export const BOARD_SPECS = {
  4: { size: 4, boxW: 2, boxH: 2 },
  6: { size: 6, boxW: 3, boxH: 2 },
  9: { size: 9, boxW: 3, boxH: 3 },
}

/** 从盘面长度反推档位，让 solve / conflictsOf 这类调用不必传 spec。 */
export function specOf(board) {
  const size = Math.round(Math.sqrt(board.length))
  const spec = BOARD_SPECS[size]
  if (!spec) throw new Error(`不支持的盘面长度: ${board.length}`)
  return spec
}

const rowOf = (spec, idx) => Math.floor(idx / spec.size)
const colOf = (spec, idx) => idx % spec.size

/** 同一行、同一列、同一宫里的其它格子下标。 */
function peersOf(spec, idx) {
  const { size, boxW, boxH } = spec
  const r = rowOf(spec, idx)
  const c = colOf(spec, idx)
  const peers = new Set()
  for (let i = 0; i < size; i++) {
    peers.add(r * size + i)
    peers.add(i * size + c)
  }
  const br = Math.floor(r / boxH) * boxH
  const bc = Math.floor(c / boxW) * boxW
  for (let i = br; i < br + boxH; i++) {
    for (let j = bc; j < bc + boxW; j++) peers.add(i * size + j)
  }
  peers.delete(idx)
  return peers
}

/** 在 idx 处填 val 是否与行、列、宫都不冲突。 */
export function isValidPlacement(board, spec, idx, val) {
  for (const p of peersOf(spec, idx)) {
    if (board[p] === val) return false
  }
  return true
}

/** 与该格数字重复的所有同伴格下标，用于界面上的红色高亮。 */
export function conflictsOf(board, idx, spec = specOf(board)) {
  const value = board[idx]
  if (!value) return []
  return [...peersOf(spec, idx)].filter((p) => board[p] === value)
}

/** 随机化回溯填满整盘；返回 true 表示成功（原地修改 board）。 */
function fillBoard(board, spec) {
  const idx = board.indexOf(0)
  if (idx === -1) return true
  for (const val of shuffle(Array.from({ length: spec.size }, (_, i) => i + 1))) {
    if (isValidPlacement(board, spec, idx, val)) {
      board[idx] = val
      if (fillBoard(board, spec)) return true
      board[idx] = 0
    }
  }
  return false
}

/** 解计数器：最多数到 limit 个解就提前收工（唯一解校验只需 limit = 2）。 */
export function countSolutions(board, spec = specOf(board), limit = 2) {
  const work = [...board]
  let count = 0
  const dfs = () => {
    const idx = work.indexOf(0)
    if (idx === -1) {
      count++
      return
    }
    for (let val = 1; val <= spec.size; val++) {
      if (!isValidPlacement(work, spec, idx, val)) continue
      work[idx] = val
      dfs()
      work[idx] = 0
      if (count >= limit) return
    }
  }
  dfs()
  return count
}

/** 求解；无解返回 null。 */
export function solve(board, spec = specOf(board)) {
  const work = [...board]
  return fillBoard(work, spec) ? work : null
}

/**
 * 生成一道保证唯一解的题目。
 * @param {{ size?: 4|6|9, clues?: number }} opts
 *        clues 为期望保留的提示数；挖到某一格会破坏唯一解时会填回去，
 *        所以实际提示数可能略多于期望值，返回值里的 clues 是实际数量。
 * @returns {{ puzzle: number[], solution: number[], spec: object, clues: number }}
 */
export function generatePuzzle({ size = 4, clues } = {}) {
  const spec = BOARD_SPECS[size]
  if (!spec) throw new Error(`不支持的棋盘档位: ${size}`)
  const total = spec.size * spec.size
  const keep = clues ?? Math.ceil(total * 0.5)

  const solution = new Array(total).fill(0)
  fillBoard(solution, spec)

  const puzzle = [...solution]
  let remaining = total
  for (const idx of shuffle([...Array(total).keys()])) {
    if (remaining <= keep) break
    const backup = puzzle[idx]
    puzzle[idx] = 0
    if (countSolutions(puzzle, spec) !== 1) puzzle[idx] = backup
    else remaining -= 1
  }

  return { puzzle, solution, spec, clues: remaining }
}

/** 找一个还没填对的格子，返回 { index, value }，供「提示」按钮使用。 */
export function nextHint(board, solution) {
  const wrong = shuffle([...Array(board.length).keys()]).filter(
    (i) => board[i] === 0 || board[i] !== solution[i],
  )
  if (!wrong.length) return null
  const index = wrong[0]
  return { index, value: solution[index] }
}
