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
export function pickMany(arr, n) {
  return shuffle(arr).slice(0, n)
}

let seq = 0
export const uid = () => `${Date.now().toString(36)}-${(seq++).toString(36)}`

/**
 * 生成一组干扰项：围绕正确答案，全部为非负整数且互不相同。
 */
export function distractors(answer, count = 3, { min = 0, max = 999, spread = 5 } = {}) {
  const set = new Set([answer])
  let guard = 0
  while (set.size < count + 1 && guard++ < 200) {
    let delta = randInt(-spread, spread)
    if (delta === 0) delta = 1
    const cand = answer + delta
    if (cand >= min && cand <= max) set.add(cand)
  }
  while (set.size < count + 1) set.add(randInt(min, Math.max(min + count + 1, max)))
  return shuffle([...set])
}
