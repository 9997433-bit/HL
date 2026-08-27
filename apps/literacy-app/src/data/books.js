/**
 * 分级绘本。
 *
 * 硬性约束：正文只允许使用 characters.js 里已收录的汉字 + 标点。
 * `verifyBookCoverage()` 会在 dev 模式下逐字校验，越界的字会在控制台报警，
 * 这样以后加新绘本时不会不小心用到孩子还没学过的字。
 *
 * 分级的意思是句子长度和情节复杂度，不是「新字数量」：
 * 第 1 级一句一行、第 2 级出现对话、第 3 级有完整的一天、
 * 第 4 级开始有起承转合、第 5 级是多角色的故事、第 6 级接近小小章节书。
 *
 * 书目分两摞：
 *   books/core.js        最早手写的 30 本，注音逐句校过，是语感基准；
 *   books/extended.js    批量扩充的那一百多本，由 scripts/gen-books.mjs
 *                        从 scripts/data/book-seed-*.mjs 生成，注音也是算出来的。
 * 两摞的字段完全一致，读者侧感知不到区别。
 *
 * 首页和进度 store 只需要「一共几本」，别从这里 import——正文会跟着进主包，
 * 那两处用 book-index.js。
 */

import { CHARACTER_MAP } from './characters.js'
import { CORE_BOOKS } from './books/core.js'
import { EXTENDED_BOOKS } from './books/extended.js'

const PUNCTUATION = new Set([
  '，', '。', '！', '？', '：', '、', '；', '「', '」', '《', '》', '…', '—', ' ', '\n'
])

/** 书架按分级排，同级内保持「先手写、后扩充」的原始顺序。 */
export const BOOKS = [...CORE_BOOKS, ...EXTENDED_BOOKS].sort((a, b) => a.level - b.level)

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
