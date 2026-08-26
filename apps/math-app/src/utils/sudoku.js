import { shuffle } from './random'

export const N = 4
const BOX = 2

const idx = (r, c) => r * N + c

export function isValidPlacement(grid, r, c, v) {
  for (let i = 0; i < N; i++) {
    if (i !== c && grid[idx(r, i)] === v) return false
    if (i !== r && grid[idx(i, c)] === v) return false
  }
  const br = Math.floor(r / BOX) * BOX
  const bc = Math.floor(c / BOX) * BOX
  for (let i = br; i < br + BOX; i++) {
    for (let j = bc; j < bc + BOX; j++) {
      if ((i !== r || j !== c) && grid[idx(i, j)] === v) return false
    }
  }
  return true
}

/** 统计解的个数，最多数到 limit 就提前返回（用于唯一解判定）。 */
export function countSolutions(grid, limit = 2) {
  const work = [...grid]
  let found = 0

  const search = (pos) => {
    if (found >= limit) return
    if (pos === N * N) {
      found += 1
      return
    }
    if (work[pos] !== 0) return search(pos + 1)
    const r = Math.floor(pos / N)
    const c = pos % N
    for (let v = 1; v <= N; v++) {
      if (isValidPlacement(work, r, c, v)) {
        work[pos] = v
        search(pos + 1)
        work[pos] = 0
        if (found >= limit) return
      }
    }
  }

  search(0)
  return found
}

export function solve(grid) {
  const work = [...grid]
  const search = (pos) => {
    if (pos === N * N) return true
    if (work[pos] !== 0) return search(pos + 1)
    const r = Math.floor(pos / N)
    const c = pos % N
    for (const v of shuffle([1, 2, 3, 4])) {
      if (isValidPlacement(work, r, c, v)) {
        work[pos] = v
        if (search(pos + 1)) return true
        work[pos] = 0
      }
    }
    return false
  }
  return search(0) ? work : null
}

export function generateSolved() {
  return solve(new Array(N * N).fill(0))
}

const CLUES_BY_LEVEL = { easy: 9, normal: 7, hard: 6 }

/**
 * 生成一道保证唯一解的 4×4 数独。
 * @returns {{puzzle:number[], solution:number[], given:boolean[]}}
 */
export function generatePuzzle(level = 'easy') {
  const solution = generateSolved()
  const targetClues = CLUES_BY_LEVEL[level] ?? 8
  const puzzle = [...solution]
  const order = shuffle([...Array(N * N).keys()])

  let clues = N * N
  for (const pos of order) {
    if (clues <= targetClues) break
    const backup = puzzle[pos]
    puzzle[pos] = 0
    if (countSolutions(puzzle, 2) !== 1) {
      puzzle[pos] = backup
    } else {
      clues -= 1
    }
  }

  return { puzzle, solution, given: puzzle.map((v) => v !== 0) }
}

/** 返回与当前填写冲突的格子下标集合。 */
export function conflicts(grid) {
  const bad = new Set()
  for (let r = 0; r < N; r++) {
    for (let c = 0; c < N; c++) {
      const v = grid[idx(r, c)]
      if (!v) continue
      if (!isValidPlacement(grid, r, c, v)) bad.add(idx(r, c))
    }
  }
  return bad
}
