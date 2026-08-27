/**
 * 绘本正文的用字与注音底座。
 *
 * 生成器（gen-books.mjs）和投稿导入器（../../scripts/import-book-submission.mjs）
 * 必须对同一句话给出同一个判决：投稿在导入前说「这本能过」，重跑生成器时就不能炸。
 * 所以字表、标点表、切词注音这三件事只在这里写一遍，两边都从这里拿。
 */

import { CHAR_INDEX } from '../src/data/char-index.js'
import { STRICT, WORDS } from './data/book-pinyin.mjs'

/** 正文允许的全角标点 → 拼音串里对应的符号。这张表之外的符号一律算越界。 */
export const PUNCT = {
  '，': ',',
  '。': '.',
  '！': '!',
  '？': '?',
  '：': ':',
  '、': ',',
  '；': ';',
  '…': '…',
  '—': '—'
}

/** 字 → 本音。 */
export const PINYIN = new Map(CHAR_INDEX.map((c) => [c.char, c.pinyin]))

/** 各分级的页数下限。 */
export const MIN_PAGES = { 1: 5, 2: 6, 3: 7, 4: 8, 5: 9, 6: 10 }

const MAX_WORD = Math.max(...Object.keys(WORDS).map((w) => w.length))

/**
 * 用字越界检查要独立于注音走一遍。
 * 注音是按词切的，词典里有「尾巴」就不会去查「巴」，而「巴」根本不在字表里——
 * 只靠注音那条路，越界字会从词条底下溜过去，一直漏到 verifyBookCoverage 才炸。
 */
export function checkChars(text, where, errors) {
  for (const ch of text) {
    if (PUNCT[ch] === undefined && !PINYIN.has(ch)) {
      errors.push(`${where}：「${ch}」不在字表里（${text}）`)
    }
  }
}

/** 汉字串 → 音节串。词典最长匹配优先，退回单字本音。 */
export function toPinyin(text, where, errors) {
  checkChars(text, where, errors)
  let out = ''
  let i = 0
  const pushSyllable = (s) => {
    out += out ? ` ${s}` : s
  }
  while (i < text.length) {
    const ch = text[i]
    if (PUNCT[ch] !== undefined) {
      out += PUNCT[ch]
      i += 1
      continue
    }
    let hit = null
    for (let len = Math.min(MAX_WORD, text.length - i); len >= 1; len -= 1) {
      const word = text.slice(i, i + len)
      if (WORDS[word]) {
        hit = { word, syllables: WORDS[word] }
        break
      }
    }
    if (hit) {
      hit.syllables.forEach(pushSyllable)
      i += hit.word.length
      continue
    }
    if (!PINYIN.has(ch)) {
      errors.push(`${where}：「${ch}」不在字表里（${text}）`)
      i += 1
      continue
    }
    if (STRICT.has(ch)) {
      errors.push(`${where}：多音字「${ch}」没有词条定音（${text}）`)
    }
    pushSyllable(PINYIN.get(ch))
    i += 1
  }
  return out
}
