export const randInt = (min, max) => Math.floor(Math.random() * (max - min + 1)) + min

export const sample = (arr) => arr[Math.floor(Math.random() * arr.length)]

export function shuffle(arr) {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

/** 从候选池中随机取 n 个不重复元素。 */
export function pick(arr, n) {
  return shuffle(arr).slice(0, n)
}

export const pickMany = pick

let seq = 0
export const uid = () => `${Date.now().toString(36)}-${(seq++).toString(36)}`

/**
 * 生成一组数字选项：包含正确答案，其余为围绕它的干扰项，全部互不相同。
 * @param {number} answer 正确答案
 * @param {{count?: number, spread?: number, min?: number, max?: number}} opts
 *        count 为选项总数（含正确答案），spread 为干扰项与答案的最大距离
 * @returns {number[]} 打乱顺序的选项数组
 */
export function numericOptions(answer, { count = 4, spread = 5, min = 0, max = 999 } = {}) {
  const set = new Set([answer])
  let guard = 0
  let reach = spread
  while (set.size < count && guard++ < 300) {
    let delta = randInt(-reach, reach)
    if (delta === 0) delta = 1
    const cand = answer + delta
    if (cand >= min && cand <= max) set.add(cand)
    // 候选区间太窄时逐步放宽，避免死循环后落到随机值上
    if (guard % 40 === 0) reach += 1
  }
  while (set.size < count) set.add(randInt(min, Math.max(min + count, max)))
  return shuffle([...set])
}

/** numericOptions 的旧签名别名：distractors(answer, extraCount, opts)。 */
export function distractors(answer, count = 3, opts = {}) {
  return numericOptions(answer, { ...opts, count: count + 1 })
}
