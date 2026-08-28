/**
 * 每日冒险题库 —— 每天固定 5 题，覆盖点数 / 加法 / 减法 / 比大小 / 数序。
 *
 * 一整天的题目只由日期决定：第 slot 题的种子是 `YYYY-MM-DD#slot`，
 * 题目 id 是 `${templateId}:${seed}`。所以同一天、同一台设备刷新页面，
 * 甚至换一台设备，看到的都是同一套题——孩子做到一半被打断也能接着做完，
 * 家长也能拿着题目 id 复现孩子今天到底做了什么。
 *
 * 除了这份「今天的 5 题」，同一批模板还能按技能点开一份**专项冒险**：
 * 技能图谱推荐「先补 20 以内进位加」，就用 `${日期}#${技能}#${slot}` 当种子
 * 生成 5 道只练这一点的题（见 buildFocusDailyQuestions）。种子里带着技能，
 * 所以专项冒险同样是「同一天同一套题」，且和当天的常规 5 题互不覆盖。
 */
import { createRng, numericOptions, questionId } from '@/utils/random.js'
import { arithmeticSkill, countingSkill } from '@/data/skill-mapping.js'
import { makeCompareQuestion } from '@/data/compare.js'

/** 每日冒险的题量。 */
export const DAILY_SIZE = 5

/** 全部答对的额外奖励。 */
export const DAILY_PERFECT_BONUS = 3

const ICONS = [
  { icon: '💎', name: '能量水晶' },
  { icon: '🍎', name: '太空苹果' },
  { icon: '🔋', name: '能量电池' },
  { icon: '🌟', name: '星尘' },
  { icon: '🥚', name: '外星蛋' },
  { icon: '🍄', name: '星球蘑菇' },
]

export const dailyDateKey = (date = new Date()) => date.toISOString().slice(0, 10)

export const dailySeed = (dateKey, slot) => `${dateKey}#${slot}`

/**
 * 专项冒险的取值窗口：每个技能一条，取完的数必须让 skill-mapping 判回这个技能，
 * 否则「去练 20 以内进位加」出的却是 10 以内的题，练了也不算在那一点上。
 * 没有窗口的技能走原来的默认取值，也就是常规每日冒险的老样子。
 */
const ADD_FOCUS = {
  'add-within-10': (rng) => {
    const a = rng.int(1, 8)
    return [a, rng.int(1, 10 - a)]
  },
  // 两个加数都压成一位数、和又必须过 10，凑十这一步就绕不过去
  'add-carry-20': (rng) => {
    const a = rng.int(4, 9)
    return [a, rng.int(11 - a, 9)]
  },
}

const SUB_FOCUS = {
  'sub-within-10': (rng) => {
    const a = rng.int(4, 10)
    return [a, rng.int(1, a - 1)]
  },
  // 减数的个位大于被减数的个位，才是真的退位减
  'sub-borrow-20': (rng) => {
    const a = rng.int(11, 18)
    return [a, rng.int((a % 10) + 1, 9)]
  },
}

const COUNT_FOCUS = {
  'count-to-5': [3, 5],
  'count-to-10': [6, 10],
  'count-to-20': [11, 20],
}

const COMPARE_FOCUS = {
  'compare-to-10': { floor: 1, ceiling: 10 },
  'compare-to-20': { floor: 11, ceiling: 20 },
}

const addQuestion = (rng, skill) => {
  const [a, b] = ADD_FOCUS[skill]?.(rng) ?? [rng.int(2, 9), rng.int(2, 11)]
  const answer = a + b
  const toTen = 10 - a
  const hints = [`从 ${a} 开始，往后数 ${b} 步。`]
  if (b > toTen) hints.push(`凑十法：${a} + ${toTen} = 10，再加剩下的 ${b - toTen}。`)
  return {
    type: 'equation',
    a,
    b,
    sign: '+',
    answer,
    options: numericOptions(answer, { count: 4, spread: 3, min: 0, max: 25, rng }),
    prompt: `${a} + ${b} = ?`,
    skill: arithmeticSkill({ level: answer > 10 ? 20 : 10, kind: 'add' }),
    hints,
    errorTags: (answered) =>
      answered === a - b ? ['wrong-op'] : (a % 10) + (b % 10) >= 10 ? ['carry'] : ['miscalc'],
    stars: 1,
    xp: 12,
  }
}

const defaultSubTerms = (rng) => {
  const a = rng.int(6, 20)
  return [a, rng.int(2, a - 1)]
}

const subQuestion = (rng, skill) => {
  const [a, b] = SUB_FOCUS[skill]?.(rng) ?? defaultSubTerms(rng)
  const answer = a - b
  const ones = a % 10
  const hints = [`从 ${a} 开始，往前数 ${b} 步。`]
  if (a > 10 && b > ones) hints.push(`破十法：先减 ${ones} 退到 ${a - ones}，再减剩下的 ${b - ones}。`)
  return {
    type: 'equation',
    a,
    b,
    sign: '−',
    answer,
    options: numericOptions(answer, { count: 4, spread: 3, min: 0, max: 20, rng }),
    prompt: `${a} − ${b} = ?`,
    skill: arithmeticSkill({ level: a > 10 ? 20 : 10, kind: 'sub' }),
    hints,
    errorTags: (answered) =>
      answered === a + b ? ['wrong-op'] : a % 10 < b % 10 ? ['borrow'] : ['miscalc'],
    stars: 1,
    xp: 12,
  }
}

const countQuestion = (rng, skill) => {
  const cargo = rng.sample(ICONS)
  const [low, high] = COUNT_FOCUS[skill] ?? [5, 14]
  const answer = rng.int(low, high)
  return {
    type: 'count',
    cargo,
    answer,
    options: numericOptions(answer, { count: 4, spread: 3, min: 1, max: 20, rng }),
    prompt: `数一数，有几个${cargo.name}？`,
    skill: countingSkill({ type: 'count', target: answer }),
    hints: ['用手指点着一个一个数，别数漏也别数重复。'],
    errorTags: () => ['off-by-one'],
    stars: 1,
    xp: 10,
  }
}

const seqQuestion = (rng) => {
  const step = rng.sample([1, 2, 2, 5])
  const start = rng.int(1, Math.max(1, 20 - step * 4))
  const seq = [0, 1, 2, 3, 4].map((i) => start + i * step)
  const blank = rng.int(1, 3)
  const answer = seq[blank]
  return {
    type: 'seq',
    seq,
    blank,
    answer,
    options: numericOptions(answer, { count: 4, spread: Math.max(2, step + 1), min: 1, max: 40, rng }),
    prompt: step === 1 ? '这串数字少了哪一个？' : `每次加 ${step}，缺的是几？`,
    skill: countingSkill({ type: 'seq', target: answer }),
    hints: ['看看相邻两个数差了多少，规律就出来了。'],
    errorTags: () => ['off-by-one'],
    stars: 1,
    xp: 12,
  }
}

const compareItem = (rng, skill) => {
  const range = COMPARE_FOCUS[skill] ?? { ceiling: 20 }
  const q = makeCompareQuestion(rng, { ...range, icons: ICONS })
  return { ...q, answer: q.target, hints: [q.hint], errorTags: () => ['reversed'] }
}

/**
 * 题序固定：每天都按同样的顺序走完 5 类题，孩子知道会遇到什么。
 * skills 是这类题能专练的技能点，专项冒险靠它把「技能 → 模板」认回来。
 */
const TEMPLATES = [
  {
    id: 'daily-count',
    label: '数一数',
    build: countQuestion,
    skills: ['count-to-5', 'count-to-10', 'count-to-20'],
  },
  { id: 'daily-add', label: '加法', build: addQuestion, skills: ['add-within-10', 'add-carry-20'] },
  {
    id: 'daily-compare',
    label: '比大小',
    build: compareItem,
    skills: ['compare-to-10', 'compare-to-20'],
  },
  { id: 'daily-sub', label: '减法', build: subQuestion, skills: ['sub-within-10', 'sub-borrow-20'] },
  { id: 'daily-seq', label: '数序', build: seqQuestion, skills: ['number-order'] },
]

export const DAILY_TEMPLATE_IDS = TEMPLATES.map((t) => t.id)

/** 按 slot 生成第 n 题；单独导出方便测试逐题复现。 */
export function buildDailyQuestion(slot, dateKey = dailyDateKey()) {
  const tpl = TEMPLATES[slot % TEMPLATES.length]
  const seed = dailySeed(dateKey, slot)
  return {
    ...tpl.build(createRng(seed)),
    id: questionId(tpl.id, seed),
    templateId: tpl.id,
    label: tpl.label,
    seed,
    slot,
  }
}

/** 某一天的完整 5 题。 */
export function buildDailyQuestions(dateKey = dailyDateKey()) {
  return Array.from({ length: DAILY_SIZE }, (_, slot) => buildDailyQuestion(slot, dateKey))
}

/* --------------------------------------------------------- 专项冒险 */

/** 技能点 → 能出这道技能的题的模板。 */
const FOCUS_TEMPLATE = Object.fromEntries(
  TEMPLATES.flatMap((tpl) => (tpl.skills ?? []).map((skill) => [skill, tpl])),
)

/** 每日冒险的题型能专练的技能点；图谱推荐到这些技能才给得出「日冒险开练」。 */
export const DAILY_FOCUS_SKILLS = Object.keys(FOCUS_TEMPLATE)

export const canDailyFocus = (skill) => Object.hasOwn(FOCUS_TEMPLATE, skill)

/** 专项冒险的种子：日期 + 技能 + 题号，三者任一变了才换题。 */
export const dailyFocusSeed = (skill, dateKey, slot) => `${dateKey}#${skill}#${slot}`

/**
 * 按技能出第 slot 道专项题；技能出不了题时返回 null，由调用方回落到常规冒险。
 */
export function buildFocusDailyQuestion(slot, { skill, dateKey = dailyDateKey() } = {}) {
  const tpl = FOCUS_TEMPLATE[skill]
  if (!tpl) return null
  const seed = dailyFocusSeed(skill, dateKey, slot)
  return {
    ...tpl.build(createRng(seed), skill),
    id: questionId(tpl.id, seed),
    templateId: tpl.id,
    label: tpl.label,
    focusSkill: skill,
    seed,
    slot,
  }
}

/**
 * 一份专项冒险：题量与每日冒险一致，5 道题全部落在同一个技能点上。
 * 认不出的技能返回空数组——推荐位不会给出这种入口，真给了也不该硬凑题。
 */
export function buildFocusDailyQuestions({
  skill,
  dateKey = dailyDateKey(),
  size = DAILY_SIZE,
} = {}) {
  if (!canDailyFocus(skill)) return []
  return Array.from({ length: size }, (_, slot) => buildFocusDailyQuestion(slot, { skill, dateKey }))
}
