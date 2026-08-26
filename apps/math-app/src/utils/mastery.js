/**
 * 自适应难度引擎 — 掌握度模型(简化贝叶斯/指数移动平均)。
 * 每个技能点 mastery ∈ [0,1];调度策略保持「最近发展区」:
 *   70% 弱项巩固(0.3 < m < 0.8) / 20% 新技能(依赖达标) / 10% 熟练复习(m > 0.8)。
 */

const ALPHA = 0.25 // 答对增益
const BETA = 0.35  // 答错衰减
export const MASTERY_THRESHOLD = 0.8

export function updateMastery(current, isCorrect) {
  const m = current ?? 0
  const next = isCorrect ? m + ALPHA * (1 - m) : m - BETA * m
  return Math.min(1, Math.max(0, Number(next.toFixed(4))))
}

/** 技能是否解锁:所有前置依赖 mastery ≥ 阈值 */
export function isUnlocked(skill, masteryMap) {
  return (skill.deps || []).every((d) => (masteryMap[d] ?? 0) >= MASTERY_THRESHOLD)
}

/**
 * 从技能列表中选择下一个训练技能。
 * @param {Array} skills curriculum 技能点数组
 * @param {Object} masteryMap { skillId: mastery }
 */
export function pickNextSkill(skills, masteryMap) {
  const unlocked = skills.filter((s) => isUnlocked(s, masteryMap))
  if (!unlocked.length) return skills[0] ?? null

  const weak = unlocked.filter((s) => {
    const m = masteryMap[s.id] ?? 0
    return m > 0 && m < MASTERY_THRESHOLD
  })
  const fresh = unlocked.filter((s) => (masteryMap[s.id] ?? 0) === 0)
  const mastered = unlocked.filter((s) => (masteryMap[s.id] ?? 0) >= MASTERY_THRESHOLD)

  const roll = Math.random()
  const pickFrom = (arr) => arr[Math.floor(Math.random() * arr.length)]
  if (roll < 0.7 && weak.length) return pickFrom(weak)
  if (roll < 0.9 && fresh.length) return pickFrom(fresh)
  if (mastered.length) return pickFrom(mastered)
  return pickFrom(weak.length ? weak : fresh.length ? fresh : unlocked)
}

/** 复习间隔(天):掌握后按遗忘曲线安排,与识字应用记忆曲线逻辑对齐 */
export const REVIEW_INTERVALS = [1, 3, 7, 14, 30]
