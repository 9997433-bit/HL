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
import { SKILL_MAP } from '@/data/curriculum.js'

/** R10 探针：推荐 → 开练入口的冻结信号（check-round10 H3）。 */
export const ROUND10_H3 = 'practice-entry'

/** 落点种类，顺序即优先级。 */
export const PRACTICE_KINDS = [
  { id: 'wrongBook', label: '重练错题', icon: '📕' },
  { id: 'daily', label: '日冒险开练', icon: '🗓️' },
  { id: 'planet', label: '去星球练', icon: '🚀' },
]

export const PRACTICE_KIND_MAP = Object.fromEntries(PRACTICE_KINDS.map((k) => [k.id, k]))

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

  return {
    ...base,
    kind: 'planet',
    to: { path: planet.route },
    label: `去${planet.name}练`,
    hint: `「${name}」的题在${planet.name}里，按原来的玩法练`,
  }
}

/** 一次算完整份推荐的落点，错题本只统计一遍。 */
export function practiceEntries(items = [], { wrongBook } = {}) {
  const wrongCounts = wrongCountsBySkill(wrongBook)
  return items.map((item) => practiceEntry(item, { wrongCounts })).filter(Boolean)
}
