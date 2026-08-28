/**
 * 识字语料库 —— 学前到小学中段的高频字，按「单元」分组。
 *
 * 字表以 `shared/data/common-hanzi.json` 为事实基线：那份 JSON 里的每个字都必须
 * 在这里出现，且拼音一致，`npm run check:data` 会守住这条。这里比基线多出来的
 * 字段（声调、部首、组词、例句、卡片图标）是识字 App 的教学包装。
 *
 * 字表长到上千个字之后，整份语料一次性进主包已经不合适了，于是拆成两层：
 *
 *   char-index.js   每个字的「轻」信息（拼音 / 声调 / 单元 / 部首 / 笔画 / 图标），
 *                   首页地图、字表卡片、复习队列、家长报表都只需要这一层，
 *                   它随主包一起加载，由 scripts/gen-char-corpus.mjs 生成。
 *   chars/uN.js     每个单元的「重」内容（释义 / 组词 / 例句），
 *                   由下面的加载器 import() 进来，翻到哪个单元才下载哪一包。
 *
 * 两层的字必须一一对应，check:data 会核对，缺一个都算失败。
 * 单元名录（unit-index.js）同样由 seed 生成，单元多了也不必手工登记。
 *
 * 字段用途：
 *   char      汉字本体
 *   pinyin    带声调拼音
 *   tone      声调（1-4，5 表示轻声），用于拼音色彩标注
 *   radical   部首（与 radicals.js 的 id 对应）
 *   strokes   笔画数（用于田字格提示，笔顺动画由 hanzi-writer 运行时提供）
 *   emoji     卡片图标，替代插画资源
 *   unit      所属单元
 *   meaning   儿童能懂的一句话释义     ← 详情层
 *   words     组词，每条含拼音          ← 详情层
 *   sentence  例句 + 拼音               ← 详情层
 *
 * 绘本（books.js）中出现的所有汉字都必须在这里能查到，
 * `verifyBookCoverage()` 会在开发模式下校验这一点。
 */

import { CHAR_INDEX } from './char-index.js'
import { UNITS, DETAIL_LOADERS } from './unit-index.js'

export { UNITS }

export const UNIT_MAP = new Map(UNITS.map((u) => [u.id, u]))

/** 全部汉字的轻量信息，顺序即课程顺序。 */
export const CHARACTERS = CHAR_INDEX

export const CHARACTER_MAP = new Map(CHARACTERS.map((c) => [c.char, c]))

export const TOTAL_CHARACTERS = CHARACTERS.length

export function charsOfUnit(unitId) {
  return CHARACTERS.filter((c) => c.unit === unitId)
}

/** 轻量条目（没有释义 / 组词 / 例句）。需要课文内容请用 loadCharacter()。 */
export function getCharacter(char) {
  return CHARACTER_MAP.get(char) ?? null
}

/** 已经下载过的单元详情：unitId → { 汉字: { meaning, words, sentence } }。 */
const detailCache = new Map()
const inFlight = new Map()

export async function loadUnitDetails(unitId) {
  if (detailCache.has(unitId)) return detailCache.get(unitId)
  const load = DETAIL_LOADERS[unitId]
  if (!load) return null
  if (!inFlight.has(unitId)) {
    inFlight.set(
      unitId,
      load().then((mod) => {
        detailCache.set(unitId, mod.default)
        inFlight.delete(unitId)
        return mod.default
      })
    )
  }
  return inFlight.get(unitId)
}

/** 已经加载进内存的单元详情；没加载过返回 null，不会触发下载。 */
export function getUnitDetails(unitId) {
  return detailCache.get(unitId) ?? null
}

/** 轻量条目 + 课文内容。字不在表里时返回 null。 */
export async function loadCharacter(char) {
  const base = CHARACTER_MAP.get(char)
  if (!base) return null
  const details = await loadUnitDetails(base.unit)
  return { ...base, ...(details?.[char] ?? {}) }
}

/** 同上，但只看已经下载过的包，适合渲染时的乐观读取。 */
export function getLoadedCharacter(char) {
  const base = CHARACTER_MAP.get(char)
  if (!base) return null
  const details = detailCache.get(base.unit)
  return details?.[char] ? { ...base, ...details[char] } : null
}

/** 整份语料（会把所有详情包全下下来），内容自检和导出报表用。 */
export async function loadAllCharacters() {
  const units = [...new Set(CHARACTERS.map((c) => c.unit))]
  await Promise.all(units.map((unit) => loadUnitDetails(unit)))
  return CHARACTERS.map((c) => ({ ...c, ...(detailCache.get(c.unit)?.[c.char] ?? {}) }))
}
