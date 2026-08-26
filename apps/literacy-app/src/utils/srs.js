/**
 * FSRS-lite 记忆曲线调度 — 纯函数,无副作用,便于单测。
 *
 * 参数经简化,行为对标 open-spaced-repetition/ts-fsrs 的核心思想:
 * 稳定性(stability,天)随成功复习指数增长,失败则大幅回退并提升难度。
 *
 * 调用方是 stores/progress.js:
 *   - 每次描红 / 答题都会 schedule(card, rating) 更新记忆卡;
 *   - 复习队列 = dueCards(cards);
 *   - 家长中心用 retention(card) 渲染记忆强度热力图。
 */

const DAY_MS = 24 * 60 * 60 * 1000

/** 一次复习的四种评价。 */
export const RATING = { AGAIN: 1, HARD: 2, GOOD: 3, EASY: 4 }

/** 各评分对应的稳定性增长倍率。 */
const GROWTH = { 2: 1.4, 3: 2.3, 4: 3.2 }

/** 失败后稳定性保留比例。 */
const LAPSE_KEEP = 0.4

export function createCard(charId, now = Date.now()) {
  return {
    charId,
    due: now,
    stability: 0,
    difficulty: 5,
    reps: 0,
    lapses: 0,
    lastRating: 0,
    lastReviewAt: 0
  }
}

/**
 * 一次复习后返回新的记忆卡(不修改入参)。
 * 难度越高增长越慢;评分好于 good 会缓慢降低难度。
 */
export function schedule(card, rating, now = Date.now()) {
  const next = {
    ...card,
    reps: card.reps + 1,
    lastRating: rating,
    lastReviewAt: now
  }

  if (rating <= 1) {
    next.lapses = card.lapses + 1
    next.stability = Math.max(0.5, card.stability * LAPSE_KEEP)
    next.difficulty = clamp(card.difficulty + 0.8, 1, 10)
  } else {
    const growth = GROWTH[rating] ?? GROWTH[3]
    const difficultyPenalty = 1 - (card.difficulty - 5) * 0.05
    next.stability = Math.max(0.5, (card.stability || 0.5) * growth * difficultyPenalty)
    next.difficulty = clamp(card.difficulty - (rating - 3) * 0.3, 1, 10)
  }

  next.due = now + Math.round(next.stability * DAY_MS)
  return next
}

export function isDue(card, now = Date.now()) {
  return card.due <= now
}

/** 到期卡片,最久未复习的排最前。 */
export function dueCards(cards, now = Date.now()) {
  return Object.values(cards)
    .filter((c) => isDue(c, now))
    .sort((a, b) => a.due - b.due)
}

/**
 * 0~1 的当前记忆保持率估计(指数遗忘),供热力图着色。
 * 未复习过的字返回 0。
 */
export function retention(card, now = Date.now()) {
  if (!card.lastReviewAt || card.stability <= 0) return 0
  const elapsedDays = (now - card.lastReviewAt) / DAY_MS
  return Math.exp((-0.9 * elapsedDays) / card.stability)
}

function clamp(v, lo, hi) {
  return Math.min(hi, Math.max(lo, v))
}
