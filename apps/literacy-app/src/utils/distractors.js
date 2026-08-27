/**
 * 选择题的干扰项。
 *
 * 以前听音识字和单字页的「考一考」都是从候选池里随机抽三个字当错误选项。
 * 随机抽出来的三个字通常和目标字八竿子打不着（「日」的干扰项抽到「蝴」
 * 「警」「藏」），孩子扫一眼轮廓就能排除，等于白出一道题——真正该练的
 * 「日 / 曰 / 旦」「未 / 末」「己 / 已」根本不会同时出现。
 *
 * 所以干扰项按四档往下找，找够为止：
 *
 *   1. 形近字库（data/similar-chars.js，由笔顺骨架算出 + 人工清单兜底）
 *   2. 同部首且笔画接近
 *   3. 笔画接近
 *   4. 候选池里剩下的字
 *
 * 第一档里最像的那个固定排在最前面，剩下的洗牌：最容易混的字每次都在，
 * 其余的换着来，重复出题不至于每次四个选项一模一样。
 */

import { CHARACTERS, CHARACTER_MAP } from '../data/characters.js'
import { similarChars } from '../data/similar-chars.js'
import { shuffle } from './random.js'

/** 笔画差在这个范围内才算「看着差不多长」。 */
const STROKE_GAP = 2

/**
 * 给一个字挑若干形近干扰项。
 *
 * @param {string} char 目标字
 * @param {number} count 要几个
 * @param {object} [options]
 * @param {Array} [options.pool] 候选范围（字表条目），默认整张字表
 * @param {(entry: object) => boolean} [options.reject] 额外排除，返回 true 的不要
 * @param {boolean} [options.poolOnly] 形近字也必须落在 pool 里（默认 false：
 *        宁可用池外的形近字，也不用池内不像的字——干扰项只需要认得出、不需要学过）
 * @returns {Array} 字表条目，最多 count 个
 */
export function similarDistractors(char, count, options = {}) {
  const { pool = CHARACTERS, reject = () => false, poolOnly = false } = options
  if (count <= 0) return []

  const target = CHARACTER_MAP.get(char) ?? null
  const usable = (entry) => Boolean(entry) && entry.char !== char && !reject(entry)

  const inPool = new Set(pool.map((entry) => entry.char))
  const near = similarChars(char)
    .map((c) => CHARACTER_MAP.get(c))
    .filter(usable)

  // 最像的那个不参与洗牌，保证每一轮都在场
  const shuffleTail = (list) => (list.length > 1 ? [list[0], ...shuffle(list.slice(1))] : list)

  const nearInPool = shuffleTail(near.filter((entry) => inPool.has(entry.char)))
  const nearOutside = poolOnly ? [] : shuffleTail(near.filter((entry) => !inPool.has(entry.char)))

  const rest = pool.filter(usable)
  const closeStrokes = (entry) =>
    target?.strokes && entry.strokes && Math.abs(entry.strokes - target.strokes) <= STROKE_GAP

  const tiers = [
    nearInPool,
    nearOutside,
    shuffle(rest.filter((entry) => target && entry.radical === target.radical && closeStrokes(entry))),
    shuffle(rest.filter(closeStrokes)),
    shuffle(rest)
  ]

  const out = []
  const seen = new Set([char])
  for (const tier of tiers) {
    for (const entry of tier) {
      if (out.length >= count) return out
      if (seen.has(entry.char)) continue
      seen.add(entry.char)
      out.push(entry)
    }
  }
  return out
}

/**
 * 目标字 + 干扰项，洗好牌直接当选项用。
 * 目标字本身由调用方给（它常常带着详情包里的释义，不能拿索引里的那份替）。
 */
export function buildOptions(target, count, options = {}) {
  const others = similarDistractors(target.char, count - 1, options)
  return shuffle([target, ...others])
}
