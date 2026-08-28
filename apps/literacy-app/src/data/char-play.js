/**
 * 「玩」这一步的数据入口 —— `getCharPlay(char)` 永远给得出一场能玩的互动。
 *
 * 三层，前面的盖后面的：
 *
 *   1. 富脚本   手写的定制互动（char-play-generated.js 里的 RICH_PLAYS，
 *               或运行时 registerRichPlays() 注册进来的），templateFallback: false
 *   2. 模板     生成器按部首 / 主题 / 卡片图标 / 字源自动配的那一场，
 *               全库 1820 字一个不落，templateFallback: true
 *   3. 终极兜底 字表里查不到的字（新加的、外部传进来的）也照样给一场接字雨，
 *               templateFallback: true，source: 'fallback'
 *
 * 所以这个函数**不会返回 null**：单字页的「玩」步不需要判空，也就不会出现空白卡。
 * 具体的旁白、选项、动画帧由 char-play-templates.js 按行展开，见那份文件的说明。
 */

import { CHAR_INDEX } from './char-index.js'
import { getRadical } from './radicals.js'
import { PLAY_ROWS, RICH_PLAYS, TOTAL_RICH_PLAYS } from './char-play-generated.js'
import {
  DEFAULT_THEME,
  PLAY_TEMPLATES,
  PLAY_THEMES,
  buildPlay,
  hashSeed
} from './char-play-templates.js'

export { PLAY_TEMPLATES, PLAY_THEMES }

/* ------------------------------------------------------------- 行 → 结构 */

/** 额外料：`parts=氵,先;kind=xing` → { parts: ['氵','先'], kind: 'xing' }。 */
function parseExtra(text) {
  const extra = {}
  if (!text) return extra
  for (const pair of text.split(';')) {
    const at = pair.indexOf('=')
    if (at === -1) continue
    const key = pair.slice(0, at)
    const value = pair.slice(at + 1)
    extra[key] = key === 'parts' ? value.split(',') : value
  }
  return extra
}

const ROW_MAP = new Map()
for (const raw of PLAY_ROWS.split('\n')) {
  const line = raw.trim()
  if (!line) continue
  const [char, theme, template, hint = '', extra = ''] = line.split('|')
  ROW_MAP.set(char, { char, theme, template, hint, extra: parseExtra(extra) })
}

/* --------------------------------------------------------------- 字表信息 */

const CHAR_MAP = new Map(CHAR_INDEX.map((c) => [c.char, c]))

/** 同单元的同学，用来出「像样的」干扰项（同一课的字，不是天南海北抓来的）。 */
const UNIT_MATES = new Map()
for (const c of CHAR_INDEX) {
  if (!UNIT_MATES.has(c.unit)) UNIT_MATES.set(c.unit, [])
  UNIT_MATES.get(c.unit).push(c)
}

const mateOf = (c) => ({
  char: c.char,
  emoji: c.emoji,
  pinyin: c.pinyin,
  strokes: c.strokes,
  radicalGlyph: getRadical(c.radical)?.glyph ?? ''
})

/** 字表外的字没有同学，从字表里按种子借六个来凑一场，照样玩得成。 */
function borrowedMates(char) {
  const start = hashSeed(char) % Math.max(1, CHAR_INDEX.length - 8)
  return CHAR_INDEX.slice(start, start + 8)
    .filter((c) => c.char !== char)
    .slice(0, 6)
    .map(mateOf)
}

function infoOf(char) {
  const entry = CHAR_MAP.get(char)
  if (!entry) return { emoji: '', pinyin: '', strokes: 0, siblings: borrowedMates(char) }
  const radical = getRadical(entry.radical)
  return {
    emoji: entry.emoji,
    pinyin: entry.pinyin,
    strokes: entry.strokes,
    unit: entry.unit,
    radicalGlyph: radical?.glyph ?? '',
    radicalName: radical?.name ?? '',
    siblings: (UNIT_MATES.get(entry.unit) ?? []).filter((c) => c.char !== char).map(mateOf)
  }
}

/* ----------------------------------------------------------------- 富脚本 */

/**
 * 富脚本可以只写文案、不写 props：那就照它指定的模板展开一份能玩的 props，
 * 只把旁白和题面换成手写的。手写的一套 props 也可以整个替换掉。
 */
function expandRich(entry) {
  const play = buildPlay(
    {
      char: entry.char,
      theme: entry.theme ?? DEFAULT_THEME,
      template: entry.template,
      hint: entry.hint ?? '',
      extra: entry.extra ?? {}
    },
    infoOf(entry.char),
    { source: 'rich', templateFallback: false }
  )
  if (entry.narration) play.narration = entry.narration
  if (entry.prompt) play.prompt = entry.prompt
  if (entry.props) {
    play.props = entry.props
    play.steps = entry.props.rounds ?? play.steps
  }
  return play
}

const richMap = new Map()
for (const entry of RICH_PLAYS) richMap.set(entry.char, entry)

const cache = new Map()

/**
 * 再挂一批富脚本（富脚本单独成模块、或做实验时用）。
 * 生成器会把落库的富脚本烤进 RICH_PLAYS，平时不必调用这个。
 */
export function registerRichPlays(plays = []) {
  for (const entry of plays) {
    if (!entry?.char) continue
    richMap.set(entry.char, entry)
    cache.delete(entry.char)
  }
  return richMap.size
}

/* ------------------------------------------------------------------- API */

/**
 * 这个字的「玩」怎么玩。字表里没有的字也给一场兜底互动，**不会返回 null**。
 *
 * @param {string} char 汉字
 * @returns {object} CharPlay：{ char, theme, template, interaction, narration,
 *                               prompt, props, steps, templateFallback, source }
 */
export function getCharPlay(char) {
  if (!char) return null
  const hit = cache.get(char)
  if (hit) return hit

  const rich = richMap.get(char)
  const row = ROW_MAP.get(char)
  const play = rich
    ? expandRich(rich)
    : row
      ? buildPlay(row, infoOf(char), { source: 'generated', templateFallback: true })
      : buildPlay(
          { char, theme: DEFAULT_THEME, template: 'rain-catch', hint: '', extra: {} },
          infoOf(char),
          { source: 'fallback', templateFallback: true }
        )
  cache.set(char, play)
  return play
}

/** 这个字有没有手写的富脚本（对着 H3 的口径：模板补的不算）。 */
export function hasRichPlay(char) {
  return richMap.has(char)
}

/** 富脚本条数。 */
export function countRichPlays() {
  return richMap.size
}

/** 整库的 Play 条目，内容自检和统计用（会把每个字都展开一遍）。 */
export function listCharPlays() {
  return [...ROW_MAP.keys(), ...richMap.keys()]
    .filter((char, i, all) => all.indexOf(char) === i)
    .map((char) => getCharPlay(char))
}

/** 索引里登记了几个字（富脚本 + 模板，去重后）。 */
export const TOTAL_CHAR_PLAYS = new Set([...ROW_MAP.keys(), ...richMap.keys()]).size

export { TOTAL_RICH_PLAYS }
