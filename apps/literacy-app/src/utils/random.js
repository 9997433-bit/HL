/**
 * 小游戏共用的随机工具。
 *
 * 出题都要「洗牌 + 抽几个不重复的」，三款小游戏各写一遍很容易写歪
 * （最常见的是 sort(() => Math.random() - 0.5) 那种分布不均的洗法），
 * 所以统一放在这里，用标准的 Fisher–Yates。
 */

/** 洗牌，返回新数组，不改原数组。 */
export function shuffle(list) {
  const out = [...list]
  for (let i = out.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[out[i], out[j]] = [out[j], out[i]]
  }
  return out
}

/** 随机取一个；空数组返回 null。 */
export function pick(list) {
  return list.length ? list[Math.floor(Math.random() * list.length)] : null
}

/** 随机取 n 个不重复的；不够就有多少给多少。 */
export function sample(list, n) {
  return shuffle(list).slice(0, Math.max(0, n))
}
