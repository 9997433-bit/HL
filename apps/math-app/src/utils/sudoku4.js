/**
 * 4×4 数独生成与求解（宫为 2×2）。
 * 网格用长度 16 的一维数组表示，0 代表空格。
 */
import { shuffle } from '@/utils/random'

const SIZE = 4
const BASE = [1, 2, 3, 4, 3, 4, 1, 2, 2, 1, 4, 3, 4, 3, 2, 1]

const rc = (r, c) => r * SIZE + c

/** 判断在 index 处填 value 是否与行、列、宫冲突。 */
export function isSafe(grid, index, value) {
  const r = Math.floor(index / SIZE)
  const c = index % SIZE
  for (let i = 0; i < SIZE; i++) {
    if (i !== c && grid[rc(r, i)] === value) return false
    if (i !== r && grid[rc(i, c)] === value) return false
  }
  const br = Math.floor(r / 2) * 2
  const bc = Math.floor(c / 2) * 2
  for (let i = br; i < br + 2; i++) {
    for (let j = bc; j < bc + 2; j++) {
      if (rc(i, j) !== index && grid[rc(i, j)] === value) return false
    }
  }
  return true
}

/** 返回与该格冲突的所有同伴格下标（行/列/宫内数字重复）。 */
export function conflictsOf(grid, index) {
  const value = grid[index]
  if (!value) return []
  const r = Math.floor(index / SIZE)
  const c = index % SIZE
  const br = Math.floor(r / 2) * 2
  const bc = Math.floor(c / 2) * 2
  const peers = new Set()
  for (let i = 0; i < SIZE; i++) {
    peers.add(rc(r, i))
    peers.add(rc(i, c))
  }
  for (let i = br; i < br + 2; i++) for (let j = bc; j < bc + 2; j++) peers.add(rc(i, j))
  peers.delete(index)
  return [...peers].filter((p) => grid[p] === value)
}

/** 统计解的个数，最多数到 limit（用于唯一解校验）。 */
function countSolutions(grid, limit = 2) {
  const work = [...grid]
  let found = 0

  const solve = () => {
    const idx = work.indexOf(0)
    if (idx === -1) {
      found += 1
      return found >= limit
    }
    for (let v = 1; v <= SIZE; v++) {
      if (!isSafe(work, idx, v)) continue
      work[idx] = v
      if (solve()) {
        work[idx] = 0
        return true
      }
      work[idx] = 0
    }
    return false
  }

  solve()
  return found
}

export function solve(grid) {
  const work = [...grid]
  const run = () => {
    const idx = work.indexOf(0)
    if (idx === -1) return true
    for (let v = 1; v <= SIZE; v++) {
      if (!isSafe(work, idx, v)) continue
      work[idx] = v
      if (run()) return true
      work[idx] = 0
    }
    return false
  }
  return run() ? work : null
}

/** 通过合法变换打乱基础解，得到一个新的完整棋盘。 */
function makeSolution() {
  let g = [...BASE]

  const digits = shuffle([1, 2, 3, 4])
  g = g.map((v) => digits[v - 1])

  const swapRows = (a, b) => {
    for (let c = 0; c < SIZE; c++) {
      const t = g[rc(a, c)]
      g[rc(a, c)] = g[rc(b, c)]
      g[rc(b, c)] = t
    }
  }
  const swapCols = (a, b) => {
    for (let r = 0; r < SIZE; r++) {
      const t = g[rc(r, a)]
      g[rc(r, a)] = g[rc(r, b)]
      g[rc(r, b)] = t
    }
  }

  if (Math.random() < 0.5) swapRows(0, 1)
  if (Math.random() < 0.5) swapRows(2, 3)
  if (Math.random() < 0.5) {
    swapRows(0, 2)
    swapRows(1, 3)
  }
  if (Math.random() < 0.5) swapCols(0, 1)
  if (Math.random() < 0.5) swapCols(2, 3)
  if (Math.random() < 0.5) {
    swapCols(0, 2)
    swapCols(1, 3)
  }
  if (Math.random() < 0.5) {
    const t = [...g]
    for (let r = 0; r < SIZE; r++) for (let c = 0; c < SIZE; c++) g[rc(r, c)] = t[rc(c, r)]
  }

  return g
}

/**
 * 生成一道保证唯一解的题目。
 * @param {number} clues 期望保留的提示数（4×4 最少 4 个才可能唯一）
 */
export function generatePuzzle(clues = 7) {
  const solution = makeSolution()
  const puzzle = [...solution]
  const order = shuffle([...Array(16).keys()])
  let remaining = 16

  for (const idx of order) {
    if (remaining <= clues) break
    const backup = puzzle[idx]
    puzzle[idx] = 0
    if (countSolutions(puzzle) !== 1) {
      puzzle[idx] = backup
    } else {
      remaining -= 1
    }
  }

  return { puzzle, solution, clues: remaining }
}

/** 找到一个还没填的格子，返回 { index, value }，用于「提示」按钮。 */
export function nextHint(grid, solution) {
  const empties = shuffle([...Array(16).keys()]).filter(
    (i) => grid[i] === 0 || grid[i] !== solution[i],
  )
  if (!empties.length) return null
  const idx = empties[0]
  return { index: idx, value: solution[idx] }
}
