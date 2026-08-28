/**
 * ROUND16_H2 · 没有字源的字，「认一认」这一步讲什么。
 *
 * 全库 1820 个字里有 1012 个不在字源语料里。有字源的字走到「认」这一步，
 * 迎面是一整段演变动画（ROUND15_H4）；没字源的字原来只剩一行释义加一个
 * 朗读按钮——同一步、同一个孩子，密度差了一整个数量级，翻到冷门字就像
 * 掉进了空房间。
 *
 * 补法不是给它们编一段来历：编出来的字源是假的，教给孩子更糟。改讲三件
 * 手头真有、且每个字都有的事，串成三幕：
 *
 *   radical 部首讲解  「洗」的部首是「氵」，带三点水的字几乎都和水有关，
 *                     一家子还有海、河、湖；部首就是它自己的字反过来讲——
 *                     「牙」自己是个部首，芽、呀都借它当零件
 *   parts   零件暗示  「洗」= 部首「氵」+ 剩下的部分。我们没有可靠的拆字语料，
 *                     所以只点破「有一块你已经认识了」，剩下的留成问号，不瞎认
 *                     它是什么——暗示到此为止，比编一个部件名诚实
 *   word    组词情境  这个字放进词里、放进句子里长什么样
 *
 * 这里只算「讲什么」，「怎么演」在 components/IntroFallbackStage.vue。
 * 分开是为了能逐字扫：scripts/test-intro-fallback.mjs 拿这个函数把全库过一遍，
 * 保证没有哪个字走到「认」这一步只剩一行释义。
 *
 * 三幕都只用轻索引 + 单元详情包里已经有的字段，不引入新语料，也不下载新东西。
 */

import { CHARACTERS, getCharacter } from './characters.js'
import { getRadical } from './radicals.js'
import { similarChars } from './similar-chars.js'

/** 这一轮的标记，接线处（CharDetailView / 舞台组件）都引它，方便回溯。 */
export const ROUND16_H2 = 'intro-fallback-stage'

/** 三幕的固定顺序。舞台按这个顺序演，读屏也按这个顺序念。 */
export const INTRO_FALLBACK_SCENES = ['radical', 'parts', 'word']

/** 部首 id → 字表里带这个部首的字，按课程顺序（越靠前越常用）。 */
let familyIndex = null

function familyOf(radicalId, char, limit) {
  if (!familyIndex) {
    familyIndex = new Map()
    for (const entry of CHARACTERS) {
      const list = familyIndex.get(entry.radical)
      if (list) list.push(entry.char)
      else familyIndex.set(entry.radical, [entry.char])
    }
  }
  return (familyIndex.get(radicalId) ?? []).filter((c) => c !== char).slice(0, limit)
}

/** 形近字：拿来提醒「别认混了」，取前几个最像的。 */
function lookalikesOf(char, limit) {
  return [...similarChars(char)].slice(0, limit)
}

/** 「，一共 9 笔」——笔画数是字表里的字才有，没有就整句不提。 */
function strokeTail(base) {
  return base.strokes ? `，一共 ${base.strokes} 笔` : ''
}

function radicalScene(base, radical, { self, family }) {
  const { char } = base
  const glyph = radical?.glyph ?? char
  const name = radical?.name ?? '部首'

  // 字表外的字（拍照识字认错、地址栏里手打的生字）：部首都不知道，别硬讲
  if (!radical) {
    return {
      id: 'radical',
      mode: 'plain',
      title: '先看清楚',
      glyph: char,
      name: '这个字',
      emoji: '🔍',
      strokes: base.strokes ?? 0,
      family: [],
      familyLabel: '',
      line: `「${char}」不在课本的字表里，我们先把它的样子看清楚。`,
      note: '一笔一笔看过去，记住它的轮廓，回头在书上再遇到就认得出来。'
    }
  }

  if (self) {
    return {
      id: 'radical',
      mode: 'seed',
      title: '先认部首',
      glyph,
      name,
      emoji: radical.emoji ?? base.emoji ?? '🧩',
      strokes: base.strokes ?? 0,
      family,
      familyLabel: family.length ? '别的字借它当零件：' : '',
      line: `「${char}」自己就是一个部首，叫${name}${strokeTail(base)}。`,
      note: radical.meaning ?? `记住「${char}」这个样子，别的字里再遇到它就认得出来。`
    }
  }

  return {
    id: 'radical',
    mode: 'split',
    title: '先认部首',
    glyph,
    name,
    emoji: radical?.emoji ?? '🧩',
    strokes: base.strokes ?? 0,
    family,
    familyLabel: family.length ? '一家子还有：' : '',
    line: `「${char}」的部首是「${glyph}」，叫${name}。`,
    note:
      radical.meaning ??
      radical.hint ??
      `「${glyph}」是「${char}」身上的零件，别的字里再见到它就眼熟了。`
  }
}

function partsScene(base, radical, { self, family }) {
  const { char } = base
  const glyph = radical?.glyph ?? char
  const name = radical?.name ?? '部首'
  const strokes = base.strokes ?? 0
  const lookalikes = lookalikesOf(char, 3)
  const mixUp = lookalikes.length
    ? `跟它长得像的有 ${lookalikes.join('、')}，别认混了。`
    : '一笔一笔看清楚，写的时候就不容易漏掉哪一笔。'

  // 字表外的字：连部首都不知道，更不该替它拆零件
  if (!radical) {
    return {
      id: 'parts',
      mode: 'plain',
      title: '拆成零件',
      glyph: char,
      name: '',
      strokes,
      pieces: [],
      family: [],
      lookalikes,
      line: `「${char}」课本里还没讲到，先把它当成一整块记住，别急着拆。`,
      note: mixUp
    }
  }

  if (self) {
    return {
      id: 'parts',
      mode: 'seed',
      title: '拆成零件',
      glyph,
      name,
      strokes,
      pieces: [],
      family,
      lookalikes,
      line: family.length
        ? `「${char}」是一整块的零件，写进别的字里就成了它们的一半：${family.slice(0, 4).join('、')}。`
        : `「${char}」是一整块的字，拆不开${strokeTail(base)}。`,
      note: mixUp
    }
  }

  return {
    id: 'parts',
    mode: 'split',
    title: '拆成零件',
    glyph,
    name,
    strokes,
    // 剩下的那块留成问号：没有可靠的拆字语料，宁可不认，也不给孩子编一个部件名
    pieces: [
      { key: 'known', glyph, label: name, known: true },
      { key: 'rest', glyph: '？', label: '剩下的部分', known: false }
    ],
    family,
    lookalikes,
    line: `拆开看：其中一块是部首「${glyph}」，剩下的部分合起来，就是「${char}」。`,
    note: lookalikes.length
      ? `一共 ${strokes} 笔。跟它长得像的有 ${lookalikes.join('、')}，别认混了。`
      : `一共 ${strokes} 笔，写的时候一个零件一个零件地看。`
  }
}

/**
 * 第三幕：把字放回它常待的地方。
 * 组词和例句在单元详情包里，是异步到的——包还没到也得有话说，
 * 不然孩子正好这时候翻到，第三幕就是一块空地。
 */
function wordScene(base) {
  const { char } = base
  const words = Array.isArray(base.words) ? base.words.slice(0, 3) : []
  const sentence = base.sentence ?? null
  const meaning = base.meaning ?? ''
  const pinyin = base.pinyin ?? ''

  let line = `「${char}」的课文还没收进来，先照着样子把它记住。`
  if (meaning) line = `「${char}」的意思是：${meaning}`
  else if (pinyin) line = `「${char}」读作 ${pinyin}，跟着老师读一遍。`

  let note = '在书上、路牌上再遇到它，就想想今天看过的样子。'
  if (words.length) note = `它常跟这些字做朋友：${words.map((w) => w.w).join('、')}。`
  else if (sentence) note = `课文里这样用它：${sentence.text}`
  else if (pinyin) note = `读作 ${pinyin}${strokeTail(base)}，组词和例句马上就到。`

  return {
    id: 'word',
    mode: words.length ? 'words' : 'plain',
    title: '放进词里',
    emoji: base.emoji ?? '💬',
    pinyin,
    meaning,
    words,
    sentence,
    line,
    note
  }
}

/**
 * 一个字在「认一认」这一步能讲的三幕。
 *
 * @param {string} char 汉字
 * @param {object} [item] 已经加载好的字条目（带释义 / 组词 / 例句）。
 *        不传就退回轻索引，只是第三幕少了课文内容，三幕仍然齐。
 * @returns {{char: string, scenes: object[]}} 永远有三幕，每幕都有话说
 */
export function buildIntroFallback(char, item = null) {
  const base = item?.char === char ? item : (getCharacter(char) ?? { char })
  const radical = base.radical ? getRadical(base.radical) : null
  // 部首就是这个字本身（牙、瓜、羽…）：讲法要反过来，不然「它的部首是它自己」很怪
  const self = !radical || radical.glyph === base.char
  const family = familyOf(base.radical, base.char, 5)

  return {
    char,
    scenes: [
      radicalScene(base, radical, { self, family }),
      partsScene(base, radical, { self, family }),
      wordScene(base)
    ]
  }
}
