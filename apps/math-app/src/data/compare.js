/**
 * 比大小题（> < =）的唯一出题处。
 *
 * 数量星云的比大小玩法和每日冒险都从这里取题，题面文案、符号顺序、
 * 判定规则只有一份，孩子在两处看到的规则完全一致。
 * 生成过程只依赖传入的随机流，同一个 seed 永远得到同一道题。
 */
import { createRng, questionId } from '@/utils/random.js'
import { countingSkill } from '@/data/skill-mapping.js'

/** 选项固定按数轴顺序排列：小 → 相等 → 大，位置本身也是一种提示。 */
export const COMPARE_SYMBOLS = ['<', '=', '>']

export const COMPARE_NAME = { '<': '小于', '=': '等于', '>': '大于' }

export const compareSymbol = (left, right) => (left > right ? '>' : left < right ? '<' : '=')

/** 每 4 题里安排一道「一样多」，否则孩子会以为等号是摆设。 */
const EQUAL_RATE = 0.25

/**
 * 生成一道比大小题。
 * @param {Function} rng createRng() 返回的随机流
 * @param {{ ceiling?: number, icons?: Array<{icon: string, name: string}> }} opts
 */
export function makeCompareQuestion(rng, { ceiling = 10, icons = [] } = {}) {
  const cargo = icons.length ? rng.sample(icons) : null
  const left = rng.int(1, ceiling)
  let right = left
  if (!rng.chance(EQUAL_RATE)) {
    // 数值域至少有 2 个数，循环必定在几次内取到不同值；guard 只是兜底
    for (let guard = 0; guard < 20 && right === left; guard++) right = rng.int(1, ceiling)
    if (right === left) right = left === ceiling ? left - 1 : left + 1
  }

  const target = compareSymbol(left, right)
  const max = Math.max(left, right)
  return {
    type: 'compare',
    cargo,
    left,
    right,
    target,
    max,
    answerText: `${left} ${target} ${right}`,
    options: [...COMPARE_SYMBOLS],
    prompt: `${left} 和 ${right}，中间该填哪个符号？`,
    hint:
      target === '='
        ? '两边一样多的时候用等号 =。'
        : '开口对着大的数：> 和 < 的大嘴巴永远朝着多的那一边。',
    skill: countingSkill({ type: 'compare', target, max }),
    stars: max >= 11 ? 2 : 1,
    xp: 10 + max,
  }
}

/** 带稳定 id 的比大小题：id 里写着 seed，凭 id 就能重建同一道题。 */
export function compareQuestion(seed, opts = {}) {
  const q = makeCompareQuestion(createRng(seed), opts)
  return { ...q, id: questionId('compare', seed), templateId: 'compare', seed }
}
