/**
 * 技能图谱 —— 把 curriculum.js 的技能点和它们的 deps 铺成一张画得出来的图。
 *
 * 这里不新增任何「技能」事实：节点来自 curriculum.SKILLS，连线来自 deps，
 * 星球元数据来自 modules.js，母题条数来自 wordProblems.js。图谱只做两件事：
 *
 *   1. 布局 —— 按「模块泳道 × 依赖深度」算出每个节点的坐标，视图照着摆就行；
 *   2. 判读 —— 把一份 mastery 存档和一个年龄档翻译成节点状态，供只读展示。
 *
 * 判读全是纯函数，图谱页只看不写：孩子的掌握度只能由玩法页经 progress store 写入，
 * 图谱上点一下不该让进度动，否则「看一眼图谱」就变成了刷进度的捷径。
 */
import { SKILLS, SKILL_MAP } from './curriculum.js'
import { MODULES } from './modules.js'
import { AGE_BAND_IDS, DEFAULT_AGE_BAND } from './age-band.js'
import { WORD_PROBLEMS } from './wordProblems.js'
import { MASTERY_THRESHOLD } from '@/utils/mastery.js'

/* ------------------------------------------------------------------ 布局尺寸 */

const NODE_W = 152
const NODE_H = 58
const COL_GAP = 48
const ROW_GAP = 22
/** 两条模块泳道之间留的空档，也是泳道底色的分隔线位置。 */
const LANE_GAP = 26
const PAD_X = 28
const PAD_Y = 26

const COL_W = NODE_W + COL_GAP
const ROW_H = NODE_H + ROW_GAP

/* ------------------------------------------------------------------ 依赖深度 */

const depthCache = new Map()

/**
 * 技能在依赖 DAG 里的深度 = 到某个无前置技能的最长路径长度。
 * 用最长路径而不是最短：一个技能只要还有一条前置链没走完就不该往左挪，
 * 否则连线会从右往左倒着画。
 */
function depthOf(id, trail = new Set()) {
  if (depthCache.has(id)) return depthCache.get(id)
  const skill = SKILL_MAP[id]
  // 认不出的 id 或成环时退回 0：图的完整性由 check:content 兜底，这里只求画得出来
  if (!skill || trail.has(id)) return 0
  trail.add(id)
  const deps = skill.deps ?? []
  const depth = deps.length ? Math.max(...deps.map((dep) => depthOf(dep, trail) + 1)) : 0
  trail.delete(id)
  depthCache.set(id, depth)
  return depth
}

/* ------------------------------------------------------------------ 节点与泳道 */

/** curriculum 模块 id → 学习地图上的星球，两者的对应关系写在 modules.js。 */
const PLANET_BY_MODULE = Object.fromEntries(MODULES.map((m) => [m.curriculumId, m]))

/** 泳道顺序跟着学习地图的星球顺序走；没有星球的模块排在后面，也不会被漏掉。 */
const MODULE_ORDER = [
  ...MODULES.map((m) => m.curriculumId),
  ...[...new Set(SKILLS.map((s) => s.module))].filter((id) => !PLANET_BY_MODULE[id]),
]

/** 技能 id → 生活行星母题条数，图谱上「这个技能有多少道题可练」显示的就是它。 */
const WORD_PROBLEMS_BY_SKILL = WORD_PROBLEMS.reduce((acc, problem) => {
  if (problem.skill) acc[problem.skill] = (acc[problem.skill] ?? 0) + 1
  return acc
}, {})

function buildLayout() {
  const nodes = []
  const lanes = []
  let laneTop = PAD_Y

  for (const moduleId of MODULE_ORDER) {
    const members = SKILLS.filter((skill) => skill.module === moduleId)
    if (!members.length) continue

    const planet = PLANET_BY_MODULE[moduleId] ?? null
    // 同一列里挤了几个技能就往下叠几行，行号即该列已占用的格子数
    const usedRows = new Map()
    const placed = members.map((skill) => {
      const col = depthOf(skill.id)
      const row = usedRows.get(col) ?? 0
      usedRows.set(col, row + 1)
      return { skill, col, row }
    })
    const rows = Math.max(...usedRows.values())
    const laneHeight = rows * ROW_H - ROW_GAP

    for (const { skill, col, row } of placed) {
      nodes.push({
        id: skill.id,
        name: skill.name,
        level: skill.level,
        module: moduleId,
        moduleName: planet?.name ?? moduleId,
        planetId: planet?.id ?? null,
        route: planet?.route ?? '/',
        emoji: planet?.emoji ?? '✨',
        color: planet?.color ?? '#5ee7ff',
        deps: [...(skill.deps ?? [])],
        depth: col,
        wordProblems: WORD_PROBLEMS_BY_SKILL[skill.id] ?? 0,
        x: PAD_X + col * COL_W,
        y: laneTop + row * ROW_H,
        w: NODE_W,
        h: NODE_H,
      })
    }

    lanes.push({
      module: moduleId,
      name: planet?.name ?? moduleId,
      planetId: planet?.id ?? null,
      route: planet?.route ?? '/',
      emoji: planet?.emoji ?? '✨',
      color: planet?.color ?? '#5ee7ff',
      top: laneTop - ROW_GAP / 2,
      height: laneHeight + ROW_GAP,
      skills: members.map((skill) => skill.id),
    })
    laneTop += laneHeight + LANE_GAP
  }

  return { nodes, lanes, height: Math.round(laneTop - LANE_GAP + PAD_Y) }
}

const layout = buildLayout()

/** 图谱节点，一个技能点一个，坐标已经算好。 */
export const SKILL_NODES = layout.nodes

export const SKILL_NODE_MAP = Object.fromEntries(SKILL_NODES.map((node) => [node.id, node]))

/** 模块泳道：图谱按星球分带，家长一眼能看出某颗星球练到哪儿了。 */
export const SKILL_LANES = layout.lanes

/** 依赖连线：from 是前置技能，to 是后继技能，path 直接喂给 <path d>。 */
export const SKILL_EDGES = SKILL_NODES.flatMap((node) =>
  node.deps
    .filter((dep) => SKILL_NODE_MAP[dep])
    .map((dep) => {
      const from = SKILL_NODE_MAP[dep]
      const x1 = from.x + from.w
      const y1 = from.y + from.h / 2
      const x2 = node.x
      const y2 = node.y + node.h / 2
      const mx = Math.round((x1 + x2) / 2)
      return {
        id: `${dep}->${node.id}`,
        from: dep,
        to: node.id,
        path: `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`,
      }
    }),
)

export const GRAPH_SIZE = {
  width: Math.max(...SKILL_NODES.map((node) => node.x + node.w)) + PAD_X,
  height: layout.height,
}

/* ------------------------------------------------------------------ 状态判读 */

/**
 * 四种节点状态，顺序即图例顺序：
 *  - mastered 掌握度过线，可以只当复习；
 *  - learning 练过但还没过线；
 *  - ready    前置都过线了、自己一次没练过，是最该开的新技能；
 *  - locked   还有前置没过线，图上画成暗的。
 */
export const SKILL_STATUSES = [
  { id: 'mastered', label: '已掌握', color: '#55e6a5' },
  { id: 'learning', label: '练习中', color: '#ffce4d' },
  { id: 'ready', label: '可开练', color: '#5ee7ff' },
  { id: 'locked', label: '待解锁', color: '#7c86a8' },
]

export const STATUS_MAP = Object.fromEntries(SKILL_STATUSES.map((s) => [s.id, s]))

export function skillStatus(id, mastery = {}) {
  const node = SKILL_NODE_MAP[id]
  if (!node) return 'locked'
  const value = mastery[id] ?? 0
  if (value >= MASTERY_THRESHOLD) return 'mastered'
  if (value > 0) return 'learning'
  return node.deps.every((dep) => (mastery[dep] ?? 0) >= MASTERY_THRESHOLD) ? 'ready' : 'locked'
}

const DEFAULT_RANK = AGE_BAND_IDS.indexOf(DEFAULT_AGE_BAND)

/** 档位/等级在 L1–L5 里的序号，认不出来的等级排在最后（永远算「超前」）。 */
const rankOf = (id) => {
  const index = AGE_BAND_IDS.indexOf(id)
  return index < 0 ? AGE_BAND_IDS.length : index
}

const bandRank = (id) => {
  const index = AGE_BAND_IDS.indexOf(id)
  return index < 0 ? DEFAULT_RANK : index
}

/**
 * 把存档翻译成一张可渲染的图。
 *
 * @param {{ mastery?: Record<string, number>, ageBand?: string }} input
 *   mastery 直接传 progress store 的那份，ageBand 传 settings.ageBand。
 * @returns 节点/连线/泳道都带上了状态，外加一份统计与「接下来练什么」的建议。
 */
export function buildSkillGraph({ mastery = {}, ageBand = DEFAULT_AGE_BAND } = {}) {
  const rank = bandRank(ageBand)
  const bandId = AGE_BAND_IDS[rank]

  const nodes = SKILL_NODES.map((node) => {
    const value = mastery[node.id] ?? 0
    return {
      ...node,
      mastery: value,
      percent: Math.round(value * 100),
      status: skillStatus(node.id, mastery),
      /** 本档及以下：这些是当前年龄档「该会」的技能，图上正常亮。 */
      inBand: rankOf(node.level) <= rank,
      /** 正好落在当前档：家长页选的那一档主推的技能，图上再描一圈。 */
      focus: node.level === bandId,
    }
  })
  const statusOf = Object.fromEntries(nodes.map((node) => [node.id, node.status]))

  const edges = SKILL_EDGES.map((edge) => ({
    ...edge,
    open: statusOf[edge.from] === 'mastered',
  }))

  const tally = (list) => {
    const mastered = list.filter((n) => n.status === 'mastered').length
    return {
      total: list.length,
      mastered,
      learning: list.filter((n) => n.status === 'learning').length,
      ready: list.filter((n) => n.status === 'ready').length,
      locked: list.filter((n) => n.status === 'locked').length,
      percent: list.length ? Math.round((mastered / list.length) * 100) : 0,
    }
  }

  const lanes = SKILL_LANES.map((lane) => ({
    ...lane,
    ...tally(nodes.filter((node) => node.module === lane.module)),
  }))

  return {
    band: bandId,
    nodes,
    edges,
    lanes,
    size: GRAPH_SIZE,
    stats: { ...tally(nodes), inBand: tally(nodes.filter((node) => node.inBand)) },
    next: nextSkills(nodes),
  }
}

/**
 * 「接下来练什么」：先补练过但没过线的，再开前置已通的新技能；
 * 本档内的排在超前的前面，同等条件下越靠依赖链上游、掌握度越低的越先练。
 */
export function nextSkills(nodes, limit = 4) {
  const score = (node) => (node.status === 'learning' ? 0 : 1) + (node.inBand ? 0 : 4)
  return nodes
    .filter((node) => node.status === 'learning' || node.status === 'ready')
    .sort(
      (a, b) => score(a) - score(b) || a.depth - b.depth || a.mastery - b.mastery,
    )
    .slice(0, limit)
}
