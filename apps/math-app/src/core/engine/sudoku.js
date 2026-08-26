/**
 * 数独引擎 — 支持 4×4 / 6×6 / 9×9 三档棋盘。
 * 生成流程:随机化回溯生成完整盘 → 挖洞 → 每挖一格用解计数器验证唯一解。
 * 盘面用一维数组表示,0 = 空格。纯函数、无框架依赖。
 */

/** 各档位的宫格布局:size = 边长,boxW/boxH = 宫的宽高 */
export const BOARD_SPECS = {
  4: { size: 4, boxW: 2, boxH: 2 },
  6: { size: 6, boxW: 3, boxH: 2 },
  9: { size: 9, boxW: 3, boxH: 3 }
}

function shuffled(arr) {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

/** 取档位规格；传入未知档位直接抛错，避免静默退化成 4×4。 */
export function specOf(sizeKey) {
  const spec = BOARD_SPECS[sizeKey]
  if (!spec) throw new Error(`不支持的棋盘档位: ${sizeKey}`)
  return spec
}

/** 某格的全部同伴格（同行、同列、同宫，不含自己）。 */
export function peersOf(spec, idx) {
  const { size, boxW, boxH } = spec
  const row = Math.floor(idx / size)
  const col = idx % size
  const peers = new Set()
  for (let c = 0; c < size; c++) peers.add(row * size + c)
  for (let r = 0; r < size; r++) peers.add(r * size + col)
  const br = Math.floor(row / boxH) * boxH
  const bc = Math.floor(col / boxW) * boxW
  for (let r = br; r < br + boxH; r++) {
    for (let c = bc; c < bc + boxW; c++) peers.add(r * size + c)
  }
  peers.delete(idx)
  return peers
}

/** 与该格数字重复的同伴格下标，用于冲突高亮。 */
export function conflictsOf(board, spec, idx) {
  const val = board[idx]
  if (!val) return []
  return [...peersOf(spec, idx)].filter((p) => board[p] === val)
}

/** 该空格在当前盘面下还能填哪些数字（候选数笔记）。 */
export function candidatesOf(board, spec, idx) {
  if (board[idx]) return []
  const used = new Set([...peersOf(spec, idx)].map((p) => board[p]).filter(Boolean))
  const out = []
  for (let v = 1; v <= spec.size; v++) if (!used.has(v)) out.push(v)
  return out
}

/**
 * 「提示」按钮用：随机挑一个还没填对的格子，给出它的正确数字。
 * 已经填错的格子也算在内，这样提示能顺手帮孩子纠错。
 */
export function nextHint(board, solution) {
  const wrong = shuffled([...Array(board.length).keys()]).filter((i) => board[i] !== solution[i])
  if (!wrong.length) return null
  return { index: wrong[0], value: solution[wrong[0]] }
}

export function isValidPlacement(board, spec, idx, val) {
  const { size, boxW, boxH } = spec
  const row = Math.floor(idx / size)
  const col = idx % size
  for (let c = 0; c < size; c++) if (board[row * size + c] === val) return false
  for (let r = 0; r < size; r++) if (board[r * size + col] === val) return false
  const br = Math.floor(row / boxH) * boxH
  const bc = Math.floor(col / boxW) * boxW
  for (let r = br; r < br + boxH; r++) {
    for (let c = bc; c < bc + boxW; c++) {
      if (board[r * size + c] === val) return false
    }
  }
  return true
}

/** 随机化回溯填满整盘;返回 true 表示成功(原地修改 board) */
function fillBoard(board, spec) {
  const idx = board.indexOf(0)
  if (idx === -1) return true
  for (const val of shuffled([...Array(spec.size)].map((_, i) => i + 1))) {
    if (isValidPlacement(board, spec, idx, val)) {
      board[idx] = val
      if (fillBoard(board, spec)) return true
      board[idx] = 0
    }
  }
  return false
}

/** 解计数器:最多数到 limit 个解即提前返回(唯一解校验只需 limit=2) */
export function countSolutions(board, spec, limit = 2) {
  let count = 0
  const work = [...board]
  const dfs = () => {
    if (count >= limit) return
    const idx = work.indexOf(0)
    if (idx === -1) {
      count++
      return
    }
    for (let val = 1; val <= spec.size; val++) {
      if (isValidPlacement(work, spec, idx, val)) {
        work[idx] = val
        dfs()
        work[idx] = 0
        if (count >= limit) return
      }
    }
  }
  dfs()
  return count
}

export function solve(board, spec) {
  const work = [...board]
  return fillBoard(work, spec) ? work : null
}

/**
 * 生成一道保证唯一解的数独。
 * @param {4|6|9} sizeKey 棋盘档位
 * @param {number} holes 目标挖洞数(实际可能略少,以保证唯一解)
 * @returns {{ puzzle: number[], solution: number[], spec, holes: number }}
 */
export function generateSudoku(sizeKey = 4, holes = null) {
  const spec = specOf(sizeKey)
  const total = spec.size * spec.size
  const targetHoles = holes ?? Math.floor(total * 0.5)

  const solution = new Array(total).fill(0)
  fillBoard(solution, spec)

  const puzzle = [...solution]
  let dug = 0
  for (const idx of shuffled([...Array(total)].map((_, i) => i))) {
    if (dug >= targetHoles) break
    const backup = puzzle[idx]
    puzzle[idx] = 0
    if (countSolutions(puzzle, spec, 2) !== 1) {
      puzzle[idx] = backup // 破坏唯一性则回填
    } else {
      dug++
    }
  }
  return { puzzle, solution, spec, holes: dug }
}
