/**
 * 每日冒险题库 —— 每天固定 5 题，覆盖点数 / 加法 / 减法 / 比大小 / 数序。
 *
 * 一整天的题目只由日期决定：第 slot 题的种子是 `YYYY-MM-DD#slot`，
 * 题目 id 是 `${templateId}:${seed}`。所以同一天、同一台设备刷新页面，
 * 甚至换一台设备，看到的都是同一套题——孩子做到一半被打断也能接着做完，
 * 家长也能拿着题目 id 复现孩子今天到底做了什么。
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

const addQuestion = (rng) => {
  const a = rng.int(2, 9)
  const b = rng.int(2, 11)
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

const subQuestion = (rng) => {
  const a = rng.int(6, 20)
  const b = rng.int(2, a - 1)
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

const countQuestion = (rng) => {
  const cargo = rng.sample(ICONS)
  const answer = rng.int(5, 14)
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

const compareItem = (rng) => {
  const q = makeCompareQuestion(rng, { ceiling: 20, icons: ICONS })
  return { ...q, answer: q.target, hints: [q.hint], errorTags: () => ['reversed'] }
}

/** 题序固定：每天都按同样的顺序走完 5 类题，孩子知道会遇到什么。 */
const TEMPLATES = [
  { id: 'daily-count', label: '数一数', build: countQuestion },
  { id: 'daily-add', label: '加法', build: addQuestion },
  { id: 'daily-compare', label: '比大小', build: compareItem },
  { id: 'daily-sub', label: '减法', build: subQuestion },
  { id: 'daily-seq', label: '数序', build: seqQuestion },
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
