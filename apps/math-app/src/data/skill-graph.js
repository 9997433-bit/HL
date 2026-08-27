/**
 * 技能图谱 —— 把 curriculum.js 的技能点和它们的 deps 铺成一张画得出来的图。
 *
 * 这里不新增任何「技能」事实：节点来自 curriculum.SKILLS，连线来自 deps，
 * 星球元数据来自 modules.js，母题条数来自 wordProblems.js。图谱只做三件事：
 *
 *   1. 布局 —— 按「模块泳道 × 依赖深度」算出每个节点的坐标，视图照着摆就行；
 *   2. 判读 —— 把一份 mastery 存档和一个年龄档翻译成节点状态，供只读展示；
 *   3. 推荐 —— 由掌握度与年龄档共同排出「接下来练哪几个」和「通往目标的路线」。
 *
 * 三件事全是纯函数，图谱页只看不写：孩子的掌握度只能由玩法页经 progress store 写入，
 * 图谱上点一下不该让进度动，否则「看一眼图谱」就变成了刷进度的捷径。推荐同理，
 * 它只是把存档重新排了个序，既不预约也不落盘，换个档位再看又是另一份建议。
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

/* ------------------------------------------------------------------ 下游影响 */

/** 技能 id → 直接后继（把它当前置的那些技能）。 */
const NEXT_IDS = SKILLS.reduce((acc, skill) => {
  for (const dep of skill.deps ?? []) (acc[dep] ??= []).push(skill.id)
  return acc
}, {})

/** 某个技能的全部下游技能；成环时按已走过的节点截断，只求算得出来。 */
function descendantsOf(id, trail = new Set()) {
  if (trail.has(id)) return new Set()
  trail.add(id)
  const out = new Set()
  for (const next of NEXT_IDS[id] ?? []) {
    out.add(next)
    for (const deep of descendantsOf(next, trail)) out.add(deep)
  }
  trail.delete(id)
  return out
}

/**
 * 技能 id → 下游闭包大小。推荐排序拿它当「练熟这一点的收益」：
 * 挡着五个技能的点数，比挡着零个技能的描红更值得先练。
 */
const REACH = Object.fromEntries(SKILLS.map((skill) => [skill.id, descendantsOf(skill.id).size]))

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
        /** 直接后继：练熟这一点，紧接着能开的是它们。 */
        nextIds: [...(NEXT_IDS[skill.id] ?? [])],
        /** 下游总共有多少技能被它挡着。 */
        reach: REACH[skill.id] ?? 0,
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

/** 给静态节点补上「这份存档下它是什么状态、在不在本档」。 */
function decorate(mastery, rank) {
  const bandId = AGE_BAND_IDS[rank]
  return SKILL_NODES.map((node) => {
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
}

/**
 * 把存档翻译成一张可渲染的图。
 *
 * @param {{ mastery?: Record<string, number>, ageBand?: string }} input
 *   mastery 直接传 progress store 的那份，ageBand 传 settings.ageBand。
 * @returns 节点/连线/泳道都带上了状态，外加一份统计与一份只读推荐。
 */
export function buildSkillGraph({ mastery = {}, ageBand = DEFAULT_AGE_BAND } = {}) {
  const rank = bandRank(ageBand)
  const bandId = AGE_BAND_IDS[rank]

  const nodes = decorate(mastery, rank)
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

  const reco = recommend({ nodes, ageBand: bandId })

  return {
    band: bandId,
    nodes,
    edges,
    lanes,
    size: GRAPH_SIZE,
    stats: { ...tally(nodes), inBand: tally(nodes.filter((node) => node.inBand)) },
    reco,
    next: reco.items,
  }
}

/* ------------------------------------------------------------------ 推荐 */

/**
 * 推荐理由。每条建议都得说得出「为什么是它」，家长才敢照着练；
 * 顺序即优先级，也是图例的展示顺序。
 */
export const RECOMMEND_REASONS = [
  { id: 'finish', label: '差一点', hint: '练过但还没过线，补几题最快见效' },
  { id: 'base', label: '补基础', hint: '低于当前年龄档、还欠着的底子' },
  { id: 'focus', label: '本档主推', hint: '正好是这个年龄档该练的新技能' },
  { id: 'ahead', label: '超前挑战', hint: '超出当前年龄档，学有余力再看' },
]

export const RECOMMEND_REASON_MAP = Object.fromEntries(RECOMMEND_REASONS.map((r) => [r.id, r]))

/** 各理由的起评分，差距要拉得够开：补基础永远排在超前挑战前面。 */
const REASON_BASE = { finish: 48, base: 34, focus: 30, ahead: 12 }

function reasonOf(node, rank) {
  // 练过就没有「新不新」可言了，先把手上这个补完，别摊子铺得到处都是
  if (node.status === 'learning') return 'finish'
  const gap = rankOf(node.level) - rank
  if (gap > 0) return 'ahead'
  return gap < 0 ? 'base' : 'focus'
}

function scoreOf(node, reason, rank) {
  const gap = rankOf(node.level) - rank
  let score = REASON_BASE[reason]
  // 越接近阈值，补完它的把握越大
  if (node.status === 'learning') score += Math.round((node.mastery / MASTERY_THRESHOLD) * 12)
  // 超前一档扣一截，别把三岁的孩子推去背乘法口诀
  if (gap > 0) score -= gap * 6
  // 挡着的后续技能越多，练熟它越划算；封顶免得长链一家独大
  score += Math.min(node.reach, 6) * 2
  // 同等条件下先练靠上游的
  return score - node.depth
}

function whyOf(node, reason, bandId) {
  if (reason === 'finish') return `已练到 ${node.percent}%，再补几题就过线`
  if (reason === 'base') return `${node.level} 的底子，补上了后面才走得动`
  if (reason === 'focus') return `${bandId} 该练的新技能，前置都通了`
  return `超出 ${bandId}，学有余力再挑战`
}

/**
 * 通往某个技能的补课路线：把它自己和所有还没过线的前置按依赖顺序排出来。
 * 已过线的前置不会出现在路线上——这是「还要练几步」，不是族谱。
 */
export function recommendPath(id, mastery = {}) {
  const steps = []
  const seen = new Set()
  const walk = (skillId) => {
    if (seen.has(skillId)) return
    seen.add(skillId)
    const node = SKILL_NODE_MAP[skillId]
    if (!node || (mastery[skillId] ?? 0) >= MASTERY_THRESHOLD) return
    node.deps.forEach(walk)
    steps.push(node)
  }
  walk(id)
  return steps
}

/**
 * 目标技能：本档里还没拿下、最靠依赖链下游的那个。
 * 挑最下游是因为它最能代表「这条线打通了」，路线上的每一步都顺带补掉。
 */
function pickGoal(nodes, rank) {
  const pending = nodes.filter((node) => node.status !== 'mastered' && rankOf(node.level) <= rank)
  if (!pending.length) return null
  const focus = pending.filter((node) => rankOf(node.level) === rank)
  const pool = focus.length ? focus : pending
  return [...pool].sort(
    (a, b) => b.depth - a.depth || b.reach - a.reach || a.id.localeCompare(b.id),
  )[0]
}

/**
 * 只读推荐：掌握度决定「哪些能练、补到哪儿了」，年龄档决定「先练哪个」。
 *
 * 同一份存档换个档位，推荐顺序会变，但节点状态一个都不会变——判读归 skillStatus，
 * 推荐只是重新排序。这里不写 progress、不预约、不落盘，刷新一次重算一次。
 *
 * @param {{ mastery?: Record<string, number>, ageBand?: string, limit?: number,
 *           nodes?: Array }} input
 *   nodes 是 buildSkillGraph 已经判读好的节点，传进来只为省一次重算。
 * @returns {{ band: string, items: Array, goal: object|null, path: Array }}
 */
export function recommend({
  mastery = {},
  ageBand = DEFAULT_AGE_BAND,
  limit = 4,
  nodes = null,
} = {}) {
  const rank = bandRank(ageBand)
  const bandId = AGE_BAND_IDS[rank]
  const list = nodes ?? decorate(mastery, rank)
  const masteryOf = nodes
    ? Object.fromEntries(nodes.map((node) => [node.id, node.mastery]))
    : mastery

  const items = list
    // 待解锁的练不了，已掌握的不用再排队，推荐只从这两种状态里挑
    .filter((node) => node.status === 'learning' || node.status === 'ready')
    .map((node) => {
      const reason = reasonOf(node, rank)
      return {
        ...node,
        reason,
        reasonLabel: RECOMMEND_REASON_MAP[reason].label,
        why: whyOf(node, reason, bandId),
        score: scoreOf(node, reason, rank),
      }
    })
    .sort(
      (a, b) =>
        b.score - a.score || a.depth - b.depth || a.mastery - b.mastery || a.id.localeCompare(b.id),
    )
    .slice(0, limit)

  const byId = Object.fromEntries(list.map((node) => [node.id, node]))
  const goal = pickGoal(list, rank)
  const path = goal
    ? recommendPath(goal.id, masteryOf).map((step, index) => ({
        ...(byId[step.id] ?? step),
        step: index + 1,
      }))
    : []

  return { band: bandId, items, goal, path }
}

/** 「接下来练什么」的短名，返回的就是 recommend().items；传数组按默认档排序。 */
export function nextSkills(input = {}, limit = 4) {
  return recommend(Array.isArray(input) ? { nodes: input, limit } : { ...input, limit }).items
}
