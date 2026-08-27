/**
 * 随机数工具 —— 全部走可复现的 mulberry32 伪随机数发生器。
 *
 * 出题一旦用 Math.random，同一道题就再也回放不出来：家长报告里的错题没法重现，
 * 每日冒险也没法保证「同一天同一套题」。这里把随机源收成 createRng(seed)，
 * 题目只要记住 seed 就能一模一样地重建，questionId() 负责把 seed 写进题目 id。
 *
 * 模块级的 randInt / sample / shuffle 仍然是「随手要一个随机数」的入口，
 * 只是底下换成了一条启动时随机播种的 mulberry32 流，行为与之前一致。
 */

const UINT32 = 4294967296

/** 任意 seed（数字 / 字符串 / undefined）折成 32 位无符号整数。 */
export function hashSeed(seed) {
  if (typeof seed === 'number' && Number.isFinite(seed)) return Math.abs(Math.trunc(seed)) >>> 0
  let h = 2166136261 >>> 0
  const text = String(seed ?? '')
  for (let i = 0; i < text.length; i++) {
    h ^= text.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return h >>> 0
}

/** mulberry32：32 位状态、无依赖、跨引擎逐位一致，适合做题目复现。 */
export function mulberry32(state) {
  let a = state >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / UINT32
  }
}

/** 进程启动时的种子：有 crypto 用 crypto，没有就退回时间戳。 */
function entropySeed() {
  const buf = globalThis.crypto?.getRandomValues?.(new Uint32Array(1))
  if (buf) return buf[0]
  return (Date.now() ^ (Math.trunc(globalThis.performance?.now?.() ?? 0) * 65537)) >>> 0
}

/**
 * 建一条独立的随机流。返回值本身是 () => [0,1) 的函数，同时挂着常用取样方法，
 * 既能当 Math.random 的替身传下去，又能 rng.int(1, 6) 这样直接用。
 * @param {number|string} [seed] 缺省时随机播种
 */
export function createRng(seed) {
  const state = seed === undefined ? entropySeed() : hashSeed(seed)
  const next = mulberry32(state)

  next.seed = seed === undefined ? state : seed
  next.int = (min, max) => Math.floor(next() * (max - min + 1)) + min
  next.sample = (arr) => arr[Math.floor(next() * arr.length)]
  next.shuffle = (arr) => {
    const a = [...arr]
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(next() * (i + 1))
      ;[a[i], a[j]] = [a[j], a[i]]
    }
    return a
  }
  next.pick = (arr, n) => next.shuffle(arr).slice(0, n)
  next.chance = (p) => next() < p
  next.options = (answer, opts = {}) => numericOptions(answer, { ...opts, rng: next })
  /** 派生子流：同一个母种子下，不同用途各走各的序列，互不串扰。 */
  next.derive = (tag) => createRng(`${next.seed}#${tag}`)
  return next
}

/**
 * 题目 id：模板 id + 生成时用的种子。
 * 记住这个 id 就能用 createRng(seed) 把同一道题一字不差地重建出来。
 */
export const questionId = (templateId, seed) => `${templateId}:${seed}`

/** 从题目 id 里拆回 { templateId, seed }；模板 id 里的冒号按第一个分隔符切。 */
export function parseQuestionId(id) {
  const at = String(id ?? '').indexOf(':')
  if (at < 0) return { templateId: String(id ?? ''), seed: '' }
  return { templateId: id.slice(0, at), seed: id.slice(at + 1) }
}

/** 模块级默认随机流：启动时随机播种，行为等价于以前的 Math.random。 */
let ambient = createRng()

/** 把默认流换成指定种子，整个 App 的「随手随机」就变成可复现的。 */
export function reseed(seed) {
  ambient = createRng(seed)
  return ambient
}

export const random = () => ambient()

export const randInt = (min, max) => ambient.int(min, max)

export const sample = (arr) => ambient.sample(arr)

export function shuffle(arr) {
  return ambient.shuffle(arr)
}

/** 从候选池中随机取 n 个不重复元素。 */
export function pick(arr, n) {
  return ambient.pick(arr, n)
}

export const pickMany = pick

let seq = 0
export const uid = () => `${Date.now().toString(36)}-${(seq++).toString(36)}`

/**
 * 生成一组数字选项：包含正确答案，其余为围绕它的干扰项，全部互不相同。
 * @param {number} answer 正确答案
 * @param {{count?: number, spread?: number, min?: number, max?: number, rng?: Function}} opts
 *        count 为选项总数（含正确答案），spread 为干扰项与答案的最大距离，
 *        rng 传入 createRng() 的随机流即可让选项跟着题目一起复现
 * @returns {number[]} 打乱顺序的选项数组
 */
export function numericOptions(
  answer,
  { count = 4, spread = 5, min = 0, max = 999, rng = ambient } = {},
) {
  const set = new Set([answer])
  let guard = 0
  let reach = spread
  while (set.size < count && guard++ < 300) {
    let delta = rng.int(-reach, reach)
    if (delta === 0) delta = 1
    const cand = answer + delta
    if (cand >= min && cand <= max) set.add(cand)
    // 候选区间太窄时逐步放宽，避免死循环后落到随机值上
    if (guard % 40 === 0) reach += 1
  }
  while (set.size < count) set.add(rng.int(min, Math.max(min + count, max)))
  return rng.shuffle([...set])
}

/** numericOptions 的旧签名别名：distractors(answer, extraCount, opts)。 */
export function distractors(answer, count = 3, opts = {}) {
  return numericOptions(answer, { ...opts, count: count + 1 })
}
