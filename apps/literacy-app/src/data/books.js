/**
 * 分级绘本。
 *
 * 硬性约束：正文只允许使用 characters.js 里已收录的汉字 + 标点。
 * `verifyBookCoverage()` 会在 dev 模式下逐字校验，越界的字会在控制台报警，
 * 这样以后加新绘本时不会不小心用到孩子还没学过的字。
 */

import { CHARACTER_MAP } from './characters.js'

const PUNCTUATION = new Set([
  '，', '。', '！', '？', '：', '、', '；', '「', '」', '《', '》', '…', '—', ' ', '\n'
])

export const BOOKS = [
  {
    id: 'b1',
    title: '我看大自然',
    pinyin: 'wǒ kàn dà zì rán',
    level: 1,
    levelName: '第 1 级 · 十个字就能读',
    cover: '🌄',
    palette: ['#ffe6b3', '#c8ebff'],
    summary: '天上有什么？山下有什么？跟着小主人公看一看。',
    newChars: ['天', '日', '月', '山', '水', '田', '土', '木', '花'],
    pages: [
      { emoji: '🌅', text: '天上有日，天上有月。', p: 'tiān shàng yǒu rì, tiān shàng yǒu yuè.' },
      { emoji: '⛰️', text: '山下有水，水上有花。', p: 'shān xià yǒu shuǐ, shuǐ shàng yǒu huā.' },
      { emoji: '🌾', text: '田中有土，土上有木。', p: 'tián zhōng yǒu tǔ, tǔ shàng yǒu mù.' },
      { emoji: '🙋', text: '我在山下，我看天上的月。', p: 'wǒ zài shān xià, wǒ kàn tiān shàng de yuè.' },
      { emoji: '🌸', text: '大山，小花，我也会看！', p: 'dà shān, xiǎo huā, wǒ yě huì kàn!' }
    ]
  },
  {
    id: 'b2',
    title: '小牛和小羊',
    pinyin: 'xiǎo niú hé xiǎo yáng',
    level: 2,
    levelName: '第 2 级 · 有对话的小故事',
    cover: '🐄',
    palette: ['#d9f6f3', '#ffe0e6'],
    summary: '小牛想上山，小羊说「我也会」。它们在山上看到了什么？',
    newChars: ['牛', '羊', '说', '会', '也', '去', '来'],
    pages: [
      { emoji: '🐄', text: '山上有小牛，山下有小羊。', p: 'shān shàng yǒu xiǎo niú, shān xià yǒu xiǎo yáng.' },
      { emoji: '🗣️', text: '小牛说：我会上山。', p: 'xiǎo niú shuō: wǒ huì shàng shān.' },
      { emoji: '🐑', text: '小羊说：我也会，我来了！', p: 'xiǎo yáng shuō: wǒ yě huì, wǒ lái le!' },
      { emoji: '🌼', text: '小牛小羊上山去，山上有花，花下有水。', p: 'xiǎo niú xiǎo yáng shàng shān qù, shān shàng yǒu huā, huā xià yǒu shuǐ.' },
      { emoji: '👀', text: '小牛看小羊，小羊看小牛。', p: 'xiǎo niú kàn xiǎo yáng, xiǎo yáng kàn xiǎo niú.' },
      { emoji: '🎉', text: '天上有日。小牛小羊说：好，好！', p: 'tiān shàng yǒu rì. xiǎo niú xiǎo yáng shuō: hǎo, hǎo!' }
    ]
  },
  {
    id: 'b3',
    title: '我的小手和小口',
    pinyin: 'wǒ de xiǎo shǒu hé xiǎo kǒu',
    level: 2,
    levelName: '第 2 级 · 认识自己',
    cover: '✋',
    palette: ['#e8e0ff', '#fff1cf'],
    summary: '手会做什么？口会做什么？我是一个小小的我。',
    newChars: ['手', '口', '目', '耳', '心', '是', '的', '不'],
    pages: [
      { emoji: '✋', text: '我有手，我有口。', p: 'wǒ yǒu shǒu, wǒ yǒu kǒu.' },
      { emoji: '🫰', text: '手是我的，口也是我的。', p: 'shǒu shì wǒ de, kǒu yě shì wǒ de.' },
      { emoji: '👂', text: '我的耳，我的目，我的心。', p: 'wǒ de ěr, wǒ de mù, wǒ de xīn.' },
      { emoji: '👀', text: '我会看，我也会说。', p: 'wǒ huì kàn, wǒ yě huì shuō.' },
      { emoji: '🧒', text: '我不是大人，我是小小的我！', p: 'wǒ bù shì dà rén, wǒ shì xiǎo xiǎo de wǒ!' }
    ]
  }
]

export const BOOK_MAP = new Map(BOOKS.map((b) => [b.id, b]))

export function getBook(id) {
  return BOOK_MAP.get(id) || null
}

/** 绘本里出现的所有生字（去重、保持出现顺序）。 */
export function charsInBook(book) {
  const seen = []
  const set = new Set()
  for (const page of book.pages) {
    for (const ch of page.text) {
      if (PUNCTUATION.has(ch) || set.has(ch)) continue
      set.add(ch)
      seen.push(ch)
    }
  }
  return seen
}

/** 开发期自检：绘本用到的字必须都在语料库里。 */
export function verifyBookCoverage() {
  const problems = []
  for (const book of BOOKS) {
    const missing = charsInBook(book).filter((ch) => !CHARACTER_MAP.has(ch))
    if (missing.length) problems.push({ book: book.title, missing })
  }
  return problems
}
