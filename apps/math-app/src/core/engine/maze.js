/**
 * 条件迷宫引擎 —— 生成、求解、关卡编排，纯函数无框架依赖。
 *
 * 迷宫用「完美迷宫」（任意两格之间恰有一条通路）的随机化深度优先回溯生成，
 * 每格存一个四位掩码表示四个方向能不能走通，因此不需要额外的墙数组，
 * 画布只要读掩码就能把墙画出来。
 *
 * 「条件」这一层是关卡编排给的：路上撒 N 个按顺序编号的能量块，
 * 必须①→②→③依次收齐，终点的舱门才会打开。能量块按到起点的 BFS 距离分位挑，
 * 保证越靠后的编号越远、必须绕路，而不是顺手就能一路捡完。
 *
 * 随机源走 utils/random 的 createRng(seed)，同一个种子出同一座迷宫，
 * check:content 才能对生成结果做回归。
 */
import { createRng } from '@/utils/random.js'

export const DIRECTIONS = Object.freeze([
  { id: 'up', name: '上', arrow: '↑', dx: 0, dy: -1, bit: 1 },
  { id: 'right', name: '右', arrow: '→', dx: 1, dy: 0, bit: 2 },
  { id: 'down', name: '下', arrow: '↓', dx: 0, dy: 1, bit: 4 },
  { id: 'left', name: '左', arrow: '←', dx: -1, dy: 0, bit: 8 },
])

export const DIRECTION_MAP = Object.freeze(Object.fromEntries(DIRECTIONS.map((d) => [d.id, d])))

const OPPOSITE = Object.freeze({ up: 'down', down: 'up', left: 'right', right: 'left' })

export const CHECKPOINT_MARKS = Object.freeze(['①', '②', '③', '④', '⑤'])

/** 各年龄档的迷宫规模与能量块个数。 */
export const MAZE_LEVELS = Object.freeze({
  L1: { cols: 5, rows: 5, checkpoints: 1 },
  L2: { cols: 7, rows: 5, checkpoints: 2 },
  L3: { cols: 9, rows: 7, checkpoints: 3 },
  L4: { cols: 11, rows: 8, checkpoints: 3 },
  L5: { cols: 13, rows: 9, checkpoints: 4 },
})

export const mazeLevelOf = (ageBand) => MAZE_LEVELS[ageBand] ?? MAZE_LEVELS.L3

export const cellIndex = (maze, x, y) => y * maze.cols + x

export const inBounds = (maze, x, y) => x >= 0 && y >= 0 && x < maze.cols && y < maze.rows

export const samePos = (a, b) => !!a && !!b && a.x === b.x && a.y === b.y

/** 随机化 DFS 回溯：挖出一座没有环、没有孤岛的完美迷宫。 */
export function generateMaze({ cols = 9, rows = 7, seed } = {}) {
  const rng = createRng(seed)
  const maze = { cols, rows, open: new Array(cols * rows).fill(0) }
  const visited = new Array(cols * rows).fill(false)
  const stack = [{ x: 0, y: rows - 1 }]
  visited[cellIndex(maze, stack[0].x, stack[0].y)] = true

  while (stack.length) {
    const cur = stack[stack.length - 1]
    const options = rng
      .shuffle(DIRECTIONS)
      .filter((d) => {
        const nx = cur.x + d.dx
        const ny = cur.y + d.dy
        return inBounds(maze, nx, ny) && !visited[cellIndex(maze, nx, ny)]
      })
    if (!options.length) {
      stack.pop()
      continue
    }
    const dir = options[0]
    const next = { x: cur.x + dir.dx, y: cur.y + dir.dy }
    maze.open[cellIndex(maze, cur.x, cur.y)] |= dir.bit
    maze.open[cellIndex(maze, next.x, next.y)] |= DIRECTION_MAP[OPPOSITE[dir.id]].bit
    visited[cellIndex(maze, next.x, next.y)] = true
    stack.push(next)
  }
  return maze
}

/** 这一格朝这个方向能不能走：既要没墙，也不能走出边界。 */
export function canMove(maze, from, dirId) {
  const dir = DIRECTION_MAP[dirId]
  if (!dir || !from || !inBounds(maze, from.x, from.y)) return false
  if ((maze.open[cellIndex(maze, from.x, from.y)] & dir.bit) === 0) return false
  return inBounds(maze, from.x + dir.dx, from.y + dir.dy)
}

export function step(from, dirId) {
  const dir = DIRECTION_MAP[dirId]
  return dir ? { x: from.x + dir.dx, y: from.y + dir.dy } : { ...from }
}

/** 从起点出发的 BFS 距离场，附带回溯用的前驱表。 */
export function distanceField(maze, from) {
  const total = maze.cols * maze.rows
  const dist = new Array(total).fill(-1)
  const prev = new Array(total).fill(-1)
  const queue = [from]
  dist[cellIndex(maze, from.x, from.y)] = 0
  for (let head = 0; head < queue.length; head++) {
    const cur = queue[head]
    const at = cellIndex(maze, cur.x, cur.y)
    for (const dir of DIRECTIONS) {
      if (!canMove(maze, cur, dir.id)) continue
      const next = step(cur, dir.id)
      const to = cellIndex(maze, next.x, next.y)
      if (dist[to] !== -1) continue
      dist[to] = dist[at] + 1
      prev[to] = at
      queue.push(next)
    }
  }
  return { dist, prev }
}

/** 最短路径（含起终点）；走不通返回 null。 */
export function solveMaze(maze, from, to) {
  const { dist, prev } = distanceField(maze, from)
  const target = cellIndex(maze, to.x, to.y)
  if (dist[target] === -1) return null
  const path = []
  for (let at = target; at !== -1; at = prev[at]) {
    path.unshift({ x: at % maze.cols, y: Math.floor(at / maze.cols) })
  }
  return path
}

/**
 * 按到起点的距离分位挑能量块：第 i 个落在第 i+1 个分位附近，
 * 于是编号越大离起点越远，孩子必须一路深入、而不是原地打转把它们都捡了。
 */
function pickCheckpoints(maze, start, goal, count, rng) {
  const { dist } = distanceField(maze, start)
  const goalAt = cellIndex(maze, goal.x, goal.y)
  const startAt = cellIndex(maze, start.x, start.y)
  const candidates = dist
    .map((d, at) => ({ at, d }))
    .filter((c) => c.d > 0 && c.at !== goalAt && c.at !== startAt)
    .sort((a, b) => a.d - b.d || a.at - b.at)

  const picked = []
  const taken = new Set()
  for (let i = 0; i < count && candidates.length; i++) {
    const anchor = Math.floor(((i + 1) * candidates.length) / (count + 1))
    const span = Math.max(1, Math.floor(candidates.length / (count + 2) / 2))
    let choice = -1
    for (let tries = 0; tries < 12 && choice < 0; tries++) {
      const at = Math.min(candidates.length - 1, Math.max(0, anchor + rng.int(-span, span)))
      if (!taken.has(candidates[at].at)) choice = at
    }
    if (choice < 0) choice = candidates.findIndex((c) => !taken.has(c.at))
    if (choice < 0) break
    taken.add(candidates[choice].at)
    picked.push(candidates[choice])
  }

  return picked
    .sort((a, b) => a.d - b.d)
    .map((c, order) => ({
      x: c.at % maze.cols,
      y: Math.floor(c.at / maze.cols),
      order,
      mark: CHECKPOINT_MARKS[order] ?? `${order + 1}`,
    }))
}

/**
 * 编排一关：左下角发射台出发，依次收齐能量块，再飞到右上角空间站。
 * optimalSteps 是「起点 →①→②…→终点」这条必经路线的步数，用来评星和给提示。
 */
export function buildMazeStage({ cols = 9, rows = 7, checkpoints = 3, seed } = {}) {
  const maze = generateMaze({ cols, rows, seed })
  const rng = createRng(`${seed ?? 'maze'}#checkpoints`)
  const start = { x: 0, y: rows - 1 }
  const goal = { x: cols - 1, y: 0 }
  const marks = pickCheckpoints(maze, start, goal, checkpoints, rng)

  const route = [start, ...marks, goal]
  let optimalSteps = 0
  for (let i = 1; i < route.length; i++) {
    const leg = solveMaze(maze, route[i - 1], route[i])
    if (!leg) return null
    optimalSteps += leg.length - 1
  }

  return { maze, start, goal, checkpoints: marks, optimalSteps, seed }
}

/** 当前该去哪儿：还没收齐就去下一个能量块，收齐了才是终点。 */
export function nextObjective(stage, collected = 0) {
  const pending = stage.checkpoints[collected]
  if (pending) return { kind: 'checkpoint', ...pending }
  return { kind: 'goal', ...stage.goal, mark: '🛰️', order: stage.checkpoints.length }
}

/** 提示：朝当前目标迈出的第一步。 */
export function hintDirection(stage, from, collected = 0) {
  const target = nextObjective(stage, collected)
  const path = solveMaze(stage.maze, from, { x: target.x, y: target.y })
  if (!path || path.length < 2) return null
  const [cur, next] = path
  return DIRECTIONS.find((d) => cur.x + d.dx === next.x && cur.y + d.dy === next.y)?.id ?? null
}

/** 还差几步：用来评星，也用来告诉孩子「快到了」。 */
export function remainingSteps(stage, from, collected = 0) {
  const route = [from, ...stage.checkpoints.slice(collected), stage.goal]
  let total = 0
  for (let i = 1; i < route.length; i++) {
    const leg = solveMaze(stage.maze, route[i - 1], route[i])
    if (!leg) return Infinity
    total += leg.length - 1
  }
  return total
}

/** 走了 steps 步、用了 hints 次提示，值几颗星（0–3）。 */
export function rateRun(stage, { steps = 0, hints = 0 } = {}) {
  if (!stage?.optimalSteps) return 0
  const ratio = steps / stage.optimalSteps
  const base = ratio <= 1.15 ? 3 : ratio <= 1.6 ? 2 : 1
  return Math.max(1, base - Math.min(2, hints))
}
