/**
 * 自适应出题引擎 — 决定「下一题练什么、要多难」。
 *
 * 掌握度沿用 utils/mastery.js 的指数移动平均（EMA）：答对往 1 靠，答错往 0 掉。
 * 选题时把每道候选题折算成一个权重：
 *   · 掌握度越低权重越高（弱项优先，从没练过的技能按「新技能」给中等权重）
 *   · 进过错题本的技能与题目再加成，欠得越多加成越大
 *   · 刚出过的技能降权，避免连着五道都是同一个技能点
 *   · 难度档离当前档位越远，权重衰减越多
 * 再按权重随机抽一道。之所以不直接取最弱的那道，是因为「永远给最不会的」
 * 会让孩子连着撞同一类题，挫败感上来就不想练了。
 *
 * 难度档由连对/连错驱动：连对 streakUp 题升一档，连错 streakDown 题降一档，
 * 升降之后 streak 归零，不会一路升到顶。
 *
 * 纯函数 + 可注入随机源（rng），check:content 用固定种子做回归。
 */
import { MASTERY_THRESHOLD, updateMastery } from '@/utils/mastery.js'

export const ADAPTIVE_DEFAULTS = Object.freeze({
  /** 掌握度为 0 时权重放大到 1 + weakBoost 倍 */
  weakBoost: 4,
  /** 没有任何记录的新技能权重 */
  freshWeight: 1.4,
  /** 已达标技能只留少量复习权重 */
  masteredWeight: 0.3,
  /** 错题本命中时的最大加成倍数 */
  wrongBookBoost: 2.4,
  /** 攒到几次错就吃满加成 */
  wrongBookCap: 3,
  /** 刚出过的技能降到几成权重 */
  repeatPenalty: 0.35,
  /** 「刚出过」看最近几题 */
  recentWindow: 2,
  /** 难度档每差一级权重乘以多少 */
  mismatchPenalty: 0.45,
  /** 连对几题升一档 */
  streakUp: 3,
  /** 连错几题降一档 */
  streakDown: 2,
})

const optionsOf = (options) => ({ ...ADAPTIVE_DEFAULTS, ...(options ?? {}) })

/** 题目 → 错题本 key 的默认取法；调用方通常要按模块前缀覆盖它。 */
const defaultWrongKeyOf = (question) => question?.wrongKey ?? question?.id ?? null

/** 错题本里这个技能一共欠了多少次（把每条错题的 attempts 加起来）。 */
export function wrongLoadOfSkill(skillId, wrongBook) {
  if (!skillId || !wrongBook) return 0
  let load = 0
  for (const entry of Object.values(wrongBook)) {
    if (entry?.skill === skillId) load += Math.max(1, Number(entry.attempts) || 1)
  }
  return load
}

/** 加成倍数：欠 0 次不加成，欠满 cap 次吃满 boost。 */
function boostOf(load, { wrongBookBoost, wrongBookCap }) {
  if (load <= 0) return 1
  return 1 + (wrongBookBoost - 1) * Math.min(1, load / wrongBookCap)
}

/**
 * 单个技能点的调度权重。
 * @param {string|null} skillId
 * @param {{mastery?: Object, wrongBook?: Object, recent?: string[], options?: Object}} ctx
 */
export function skillWeight(skillId, ctx = {}) {
  const options = optionsOf(ctx.options)
  const mastery = ctx.mastery ?? {}
  const m = skillId ? mastery[skillId] : undefined

  let weight
  if (!Number.isFinite(m)) weight = options.freshWeight
  else if (m >= MASTERY_THRESHOLD) weight = options.masteredWeight
  else weight = 1 + options.weakBoost * ((MASTERY_THRESHOLD - m) / MASTERY_THRESHOLD)

  weight *= boostOf(wrongLoadOfSkill(skillId, ctx.wrongBook), options)

  const recent = ctx.recent ?? []
  if (skillId && recent.slice(-options.recentWindow).includes(skillId)) {
    weight *= options.repeatPenalty
  }

  return Math.max(0.01, weight)
}

/** 单道候选题的权重：技能权重 × 这道题自己的错题本加成 × 难度档匹配度。 */
export function questionWeight(question, ctx = {}) {
  if (!question) return 0
  const options = optionsOf(ctx.options)
  let weight = skillWeight(question.skill ?? null, ctx)

  const key = (ctx.wrongKeyOf ?? defaultWrongKeyOf)(question)
  const entry = key ? ctx.wrongBook?.[key] : null
  if (entry) weight *= boostOf(Math.max(1, Number(entry.attempts) || 1), options)

  const steps = ctx.steps ?? []
  const here = ctx.difficulty
  if (steps.length && question.difficulty !== undefined && here !== undefined && here !== null) {
    const from = steps.indexOf(here)
    const to = steps.indexOf(question.difficulty)
    if (from >= 0 && to >= 0 && from !== to) {
      weight *= options.mismatchPenalty ** Math.abs(to - from)
    }
  }

  return Math.max(0, weight)
}

/** 这道题是被什么理由选中的，供界面上给孩子一句解释。 */
export function pickSource(question, ctx = {}) {
  const key = (ctx.wrongKeyOf ?? defaultWrongKeyOf)(question)
  if (key && ctx.wrongBook?.[key]) return 'wrong-book'
  const m = ctx.mastery?.[question?.skill]
  if (!Number.isFinite(m)) return 'fresh'
  return m >= MASTERY_THRESHOLD ? 'review' : 'weak'
}

export const SOURCE_LABEL = {
  'wrong-book': '错题重练',
  weak: '弱项巩固',
  fresh: '新技能',
  review: '熟练复习',
}

/**
 * 从候选池里按权重抽下一题。
 * @param {Array} pool 候选题目（元素需带 skill，可选 difficulty / id）
 * @param {Object} ctx { mastery, wrongBook, recent, difficulty, steps, options, rng, wrongKeyOf }
 * @returns {{question: Object, index: number, weight: number, weights: number[], source: string, difficulty: *}|null}
 */
export function pickNextQuestion(pool, ctx = {}) {
  const list = Array.isArray(pool) ? pool : []
  if (!list.length) return null

  const rng = typeof ctx.rng === 'function' ? ctx.rng : Math.random
  const weights = list.map((question) => questionWeight(question, ctx))
  const total = weights.reduce((sum, w) => sum + w, 0)

  // 权重全是 0（池子里都是空位）时退化为均匀抽样，绝不返回 null 让调用方卡住
  let index = weights.indexOf(Math.max(...weights))
  if (total > 0) {
    let roll = rng() * total
    for (let i = 0; i < weights.length; i++) {
      roll -= weights[i]
      if (roll < 0) {
        index = i
        break
      }
    }
  } else {
    index = Math.min(list.length - 1, Math.floor(rng() * list.length))
  }

  const question = list[index]
  if (!question) return null
  return {
    question,
    index,
    weight: weights[index],
    weights,
    source: pickSource(question, ctx),
    difficulty: ctx.difficulty ?? null,
  }
}

/**
 * 按连对/连错决定下一题的难度档。
 * @param {*} current 当前档位（必须是 steps 里的值，否则回落到最低档）
 * @param {{streak?: number, missStreak?: number}} run
 * @param {{steps?: Array, options?: Object}} config
 */
export function nextDifficulty(current, run = {}, config = {}) {
  const options = optionsOf(config.options)
  const steps = config.steps ?? []
  if (!steps.length) return current

  const found = steps.indexOf(current)
  const at = found < 0 ? 0 : found
  const { streak = 0, missStreak = 0 } = run

  if (streak >= options.streakUp && at < steps.length - 1) return steps[at + 1]
  if (missStreak >= options.streakDown && at > 0) return steps[at - 1]
  return steps[at]
}

/**
 * 按权重排出「最该补的技能点」，家长/进度页用它给一句建议。
 * @param {Array<{id: string}|string>} skills
 * @param {Object} ctx 同 skillWeight
 * @param {number} limit
 */
export function weakestSkills(skills, ctx = {}, limit = 3) {
  const mastery = ctx.mastery ?? {}
  const plain = { ...ctx, recent: [] }
  return (skills ?? [])
    .map((s) => (typeof s === 'string' ? { id: s } : s))
    .filter((s) => {
      const m = mastery[s.id]
      const weak = Number.isFinite(m) && m < MASTERY_THRESHOLD
      return weak || wrongLoadOfSkill(s.id, ctx.wrongBook) > 0
    })
    .map((s) => ({ ...s, mastery: mastery[s.id] ?? 0, weight: skillWeight(s.id, plain) }))
    .sort((a, b) => b.weight - a.weight)
    .slice(0, Math.max(0, limit))
}

/**
 * 有状态的引擎实例：记住这一轮的掌握度、连击与当前难度档。
 * QuizShell 每答一题调 record()，每要下一题调 pickNextQuestion()。
 *
 * mastery 传进来的是快照拷贝，引擎按同样的 EMA 公式自己推进，
 * 和 store 里的值保持一致；wrongBook 直接引用 store 的对象，随答随变。
 */
export function createAdaptiveEngine(config = {}) {
  const options = optionsOf(config.options)
  const steps = Array.isArray(config.steps) ? [...config.steps] : []
  const rng = typeof config.rng === 'function' ? config.rng : Math.random
  const wrongKeyOf = config.wrongKeyOf ?? defaultWrongKeyOf

  const state = {
    mastery: { ...(config.mastery ?? {}) },
    wrongBook: config.wrongBook ?? {},
    difficulty: steps.includes(config.difficulty) ? config.difficulty : (steps[0] ?? null),
    streak: 0,
    missStreak: 0,
    recent: [],
    answered: 0,
  }

  const context = (extra = {}) => ({
    mastery: state.mastery,
    wrongBook: state.wrongBook,
    recent: state.recent,
    difficulty: state.difficulty,
    steps,
    options,
    rng,
    wrongKeyOf,
    ...extra,
  })

  /** 记一次作答：推进掌握度 EMA 与连对/连错，必要时升降难度档。 */
  function record(skillId, isCorrect) {
    state.answered += 1
    if (skillId) state.mastery[skillId] = updateMastery(state.mastery[skillId], isCorrect)
    if (isCorrect) {
      state.streak += 1
      state.missStreak = 0
    } else {
      state.missStreak += 1
      state.streak = 0
    }

    const previous = state.difficulty
    const after = nextDifficulty(previous, state, { steps, options })
    const changed = after !== previous
    if (changed) {
      state.difficulty = after
      // 升降档后重新计数，否则连对 4 题会被连升两档
      state.streak = 0
      state.missStreak = 0
    }

    return {
      difficulty: state.difficulty,
      previous,
      changed,
      direction: changed
        ? steps.indexOf(after) > steps.indexOf(previous)
          ? 'up'
          : 'down'
        : 'hold',
      streak: state.streak,
      missStreak: state.missStreak,
      mastery: skillId ? state.mastery[skillId] : null,
    }
  }

  function pick(pool, extra = {}) {
    const picked = pickNextQuestion(pool, context(extra))
    if (picked?.question?.skill) {
      state.recent.push(picked.question.skill)
      if (state.recent.length > 8) state.recent.shift()
    }
    return picked
  }

  /** 从 store 重新拉一份掌握度/错题本（换一轮或导入进度后调用）。 */
  function sync({ mastery, wrongBook } = {}) {
    if (mastery) state.mastery = { ...mastery }
    if (wrongBook) state.wrongBook = wrongBook
    return state
  }

  function reset({ difficulty } = {}) {
    state.streak = 0
    state.missStreak = 0
    state.recent = []
    state.answered = 0
    if (difficulty !== undefined) {
      state.difficulty = steps.includes(difficulty) ? difficulty : (steps[0] ?? null)
    }
    return state
  }

  return {
    state,
    steps,
    options,
    context,
    record,
    pickNextQuestion: pick,
    sync,
    reset,
    get difficulty() {
      return state.difficulty
    },
    get streak() {
      return state.streak
    },
    get missStreak() {
      return state.missStreak
    },
  }
}
