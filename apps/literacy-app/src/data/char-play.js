/**
 * ROUND15_H2 · 每字玩法（Play）——「玩」这一步的数据入口。
 *
 * 洪恩的做法是进字之前先玩一个跟字义相关的小互动。要把这件事铺到 1820 个字，
 * 手写脚本是铺不满的，所以这里定的是一条**永不落空**的契约：
 *
 *   getCharPlay(char) → { char, theme, template, narration, props, templateFallback }
 *
 * 任何字都拿得到一份玩法。手写富脚本（`templateFallback: false`）优先；
 * 没有手写脚本的字，按「部首 → 主题 → 模板」推出来一份，
 * 打上 `templateFallback: true`，好让统计能把两者分开数（H3 只数富脚本）。
 *
 * 这一份是**薄壳**：模板运行时（GSAP / OpenMoji 舞台）由 CharPlayStage 负责，
 * 富脚本目录由 char-play-rich.js 负责。两边任何一方到位后，
 * 这里只需要把 RICH_PLAY 换成真目录，接口不动。
 */

import { CHARACTER_MAP } from './characters.js'

/**
 * 手写富脚本目录。空数组不是占位敷衍：契约要求「缺了自动补」，
 * 所以富脚本是加分项，不是玩法能不能出来的前提。
 */
export const RICH_PLAY = []

const RICH_MAP = new Map(RICH_PLAY.map((p) => [p.char, p]))

/** 部首 → 主题。主题决定用哪一类模板，也决定舞台的配色和道具。 */
const THEME_BY_RADICAL = {
  shui: 'nature',
  mu: 'nature',
  ri: 'nature',
  yue: 'nature',
  cao: 'nature',
  huo: 'nature',
  shan: 'nature',
  tu: 'nature',
  tian: 'nature',
  he: 'nature',
  xi: 'nature',
  feng: 'nature',
  shitou: 'nature',
  chong: 'animal',
  niao: 'animal',
  yu: 'animal',
  ma: 'animal',
  niu: 'animal',
  yang: 'animal',
  quan: 'animal',
  yutou: 'animal',
  kou: 'body',
  shou: 'body',
  xin: 'body',
  yan: 'body',
  er: 'body',
  zu: 'body',
  mubu: 'body',
  ren: 'family',
  renzitou: 'family',
  nv: 'family',
  zi: 'family',
  fu: 'family',
  muqin: 'family',
  lao: 'family',
  zhua: 'action',
  zhiwen: 'action',
  che: 'action',
  gong: 'action',
  jin: 'action',
  jiaosi: 'action',
  mian: 'place',
  men: 'place',
  wei: 'place',
  mibao: 'place'
}

/**
 * 每个主题两套模板，靠字本身的哈希二选一。
 * 只留两套是有意的：孩子连着学同一单元的字时，玩法要眼熟到不用重新学规则，
 * 又不能一整个单元长得一模一样。
 */
const TEMPLATES_BY_THEME = {
  nature: ['rain-catch', 'emoji-hunt'],
  animal: ['emoji-hunt', 'tap-reveal'],
  body: ['tap-reveal', 'morph-story'],
  family: ['morph-story', 'tap-reveal'],
  action: ['drag-parts', 'tap-reveal'],
  place: ['emoji-hunt', 'drag-parts'],
  word: ['tap-reveal', 'emoji-hunt']
}

const NARRATION = {
  'rain-catch': (c, e) => `${e} 一个一个落下来，接住带「${c}」的那几个！`,
  'emoji-hunt': (c, e) => `${e} 藏在画面里啦，找出跟「${c}」是一伙的。`,
  'tap-reveal': (c, e) => `点一点 ${e}，看看「${c}」躲在哪儿。`,
  'morph-story': (c, e) => `${e} 会慢慢变成「${c}」，点一下往下看。`,
  'drag-parts': (c, e) => `把零件拼起来，就成了「${c}」${e}。`
}

/** 字符串哈希：同一个字每次都要选到同一套模板，不能靠 Math.random。 */
function hashOf(str) {
  let h = 0
  for (let i = 0; i < str.length; i += 1) h = (h * 31 + str.charCodeAt(i)) | 0
  return Math.abs(h)
}

export function themeOf(char) {
  const entry = CHARACTER_MAP.get(char)
  return THEME_BY_RADICAL[entry?.radical] ?? 'word'
}

/**
 * 取一个字的玩法。**任何非空字符串都拿得到结果**，字表外的字也一样——
 * 拍照识字认出生字、家长自建字表都会走到这里，返回 null 等于当场白屏。
 */
export function getCharPlay(char) {
  if (typeof char !== 'string' || !char) return null
  const rich = RICH_MAP.get(char)
  if (rich) return { templateFallback: false, ...rich }

  const entry = CHARACTER_MAP.get(char)
  const emoji = entry?.emoji ?? '✨'
  const theme = themeOf(char)
  const pool = TEMPLATES_BY_THEME[theme] ?? TEMPLATES_BY_THEME.word
  const template = pool[hashOf(char) % pool.length]

  return {
    char,
    theme,
    template,
    narration: (NARRATION[template] ?? NARRATION['tap-reveal'])(char, emoji),
    props: {
      emoji,
      pinyin: entry?.pinyin ?? '',
      /** 要点满几下才算玩过一轮。三下够孩子玩出手感，又不至于拖住流程。 */
      taps: 3
    },
    templateFallback: true
  }
}

/** 富脚本条数——H3 只认这个数，模板补齐的不算。 */
export function countRichPlays() {
  return RICH_PLAY.length
}

export default { getCharPlay, countRichPlays, themeOf, RICH_PLAY }
