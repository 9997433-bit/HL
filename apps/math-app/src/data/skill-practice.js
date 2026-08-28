/**
 * 推荐 → 开练入口。
 *
 * 技能图谱的推荐是只读的（见 data/skill-graph.js）：它只回答「接下来该练哪个技能」，
 * 排完序就结束了。这里回答紧接着的那个问题——「点下去落到哪儿」。
 *
 * 三种落点，按「手上欠着的先还」排：
 *
 *   1. wrongBook —— 这个技能还欠着错题，先把欠账重做掉，比再做一批新题划算；
 *   2. daily     —— 每日冒险的题型能出这个技能的题，就按日期 + 技能生成一份专项冒险；
 *   3. planet    —— 前两条都不适用（比如数独、七巧板），回它自己的星球按原玩法练。
 *
 * 全是纯函数：入口只由「推荐项 + 错题本快照」算出来，既不写进度也不落盘。
 * 推荐本身的排序、理由、路线一个字都不改——换个落点不该换掉建议。
 */
import { canDailyFocus } from '@/data/daily.js'
import { SKILLS, SKILL_MAP } from '@/data/curriculum.js'

/** R10 探针：推荐 → 开练入口的冻结信号（check-round10 H3）。 */
export const ROUND10_H3 = 'practice-entry'
/** R12 探针：34 个图谱节点都有专项或页内定位。 */
export const ROUND12_H5 = 'allSkills-practice-entry'

/** 落点种类，顺序即优先级。 */
export const PRACTICE_KINDS = [
  { id: 'wrongBook', label: '重练错题', icon: '📕' },
  { id: 'daily', label: '日冒险开练', icon: '🗓️' },
  { id: 'planet', label: '去星球练', icon: '🚀' },
]

export const PRACTICE_KIND_MAP = Object.fromEntries(PRACTICE_KINDS.map((k) => [k.id, k]))

/**
 * 日冒险暂时出不了的 24 个技能，落到已有玩法里最具体的位置。
 *
 * skill 参数让目标页显示「正在练哪一点」，能切档的页面还会据此预选范围；
 * hash 则把页面滚到真正可操作的区域，而不是停在星球介绍上。
 */
const focusTo = (path, skill, hash = '#practice-stage', query = {}) => ({
  path,
  query: { ...query, skill },
  hash,
})

export const PLANET_SKILL_TARGETS = {
  'number-trace': focusTo('/number-sense', 'number-trace'),
  'compose-ten': focusTo('/compose-ten', 'compose-ten'),
  'add-within-100': focusTo('/arithmetic', 'add-within-100'),
  'sub-within-100': focusTo('/arithmetic', 'sub-within-100'),
  'mul-table': focusTo('/visual-demos', 'mul-table', '#visual-practice', {
    demo: 'multiplication',
  }),
  'div-basic': focusTo('/visual-demos', 'div-basic', '#visual-practice', {
    demo: 'division',
  }),
  'shape-2d': focusTo('/geometry', 'shape-2d'),
  'tangram-basic': focusTo('/tangram', 'tangram-basic'),
  symmetry: focusTo('/tangram', 'symmetry'),
  'shape-3d': focusTo('/geometry', 'shape-3d'),
  'pattern-abab': focusTo('/logic', 'pattern-abab'),
  'pattern-number': focusTo('/logic', 'pattern-number'),
  classify: focusTo('/memory-pairs', 'classify'),
  'maze-condition': focusTo('/maze', 'maze-condition'),
  deduction: focusTo('/logic', 'deduction'),
  'sudoku-4': focusTo('/sudoku', 'sudoku-4'),
  'sudoku-6': focusTo('/sudoku', 'sudoku-6'),
  'sudoku-9': focusTo('/sudoku', 'sudoku-9'),
  'wp-combine': focusTo('/word-problems', 'wp-combine'),
  'wp-remain': focusTo('/word-problems', 'wp-remain'),
  'wp-diff': focusTo('/word-problems', 'wp-diff'),
  'wp-times': focusTo('/word-problems', 'wp-times'),
  'wp-share': focusTo('/word-problems', 'wp-share'),
  'wp-two-step': focusTo('/word-problems', 'wp-two-step'),
}

/** 给验收与家长侧复核用的覆盖快照，不能靠手写「34」冒充覆盖。 */
export function practiceCoverage() {
  const daily = SKILLS.filter((skill) => canDailyFocus(skill.id)).map((skill) => skill.id)
  const planet = SKILLS.filter((skill) => PLANET_SKILL_TARGETS[skill.id]).map((skill) => skill.id)
  const missing = SKILLS.filter(
    (skill) => !canDailyFocus(skill.id) && !PLANET_SKILL_TARGETS[skill.id],
  ).map((skill) => skill.id)
  return { total: SKILLS.length, daily, planet, covered: daily.length + planet.length, missing }
}

export const ALL_SKILLS_PRACTICE_COVERED = practiceCoverage().missing.length === 0

/** 错题本里每个技能还欠着几道题；没有技能点的条目不参与统计。 */
export function wrongCountsBySkill(wrongBook = {}) {
  const counts = {}
  for (const entry of Object.values(wrongBook ?? {})) {
    const skill = entry?.skill
    if (skill) counts[skill] = (counts[skill] ?? 0) + 1
  }
  return counts
}

const skillName = (id, fallback = '这个技能') => SKILL_MAP[id]?.name ?? fallback

/**
 * 一条推荐的开练入口。
 *
 * @param {{ id: string, name?: string, route?: string, moduleName?: string }} item
 *   直接传 recommend().items 里的一项即可；只用到 id / route / 名称，不回写。
 * @param {{ wrongBook?: object, wrongCounts?: Record<string, number> }} ctx
 *   wrongBook 传 progress.state.wrongBook；一次渲染多条时传算好的 wrongCounts 省一轮统计。
 * @returns {{ skill, kind, to, label, hint, wrongCount, planet }|null}
 */
export function practiceEntry(item, { wrongBook, wrongCounts } = {}) {
  const skill = typeof item === 'string' ? item : item?.id
  if (!skill) return null

  const counts = wrongCounts ?? wrongCountsBySkill(wrongBook)
  const wrongCount = counts[skill] ?? 0
  const name = (typeof item === 'object' && item?.name) || skillName(skill)
  const planet = {
    name: (typeof item === 'object' && item?.moduleName) || '对应星球',
    route: (typeof item === 'object' && item?.route) || '/',
  }
  const base = { skill, wrongCount, planet }

  if (wrongCount > 0) {
    return {
      ...base,
      kind: 'wrongBook',
      to: { path: '/progress', query: { wrong: skill } },
      label: `📕 重练 ${wrongCount} 道错题`,
      hint: `「${name}」还欠着 ${wrongCount} 道错题，重做答对就放它走`,
    }
  }

  if (canDailyFocus(skill)) {
    return {
      ...base,
      kind: 'daily',
      to: { path: '/daily', query: { focus: skill } },
      label: '🗓️ 日冒险开练',
      hint: `按今天的日期生成 5 道「${name}」专项题，刷新不换题`,
    }
  }

  const target = PLANET_SKILL_TARGETS[skill] ?? focusTo(planet.route, skill)
  return {
    ...base,
    kind: 'planet',
    to: target,
    label: `打开「${name}」`,
    hint: `已定位到${planet.name}里能练「${name}」的专项或操作区`,
  }
}

/** 一次算完整份推荐的落点，错题本只统计一遍。 */
export function practiceEntries(items = [], { wrongBook } = {}) {
  const wrongCounts = wrongCountsBySkill(wrongBook)
  return items.map((item) => practiceEntry(item, { wrongCounts })).filter(Boolean)
}
