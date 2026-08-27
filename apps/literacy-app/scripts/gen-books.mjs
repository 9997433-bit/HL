/**
 * 分级绘本生成器。
 *
 * 绘本从 30 本扩到 130 本以后，逐本手写拼音已经不现实了：一本 8 页、
 * 一页一句，光注音就是上千个音节，手抄一定会漂。所以正文只手写汉字，
 * 拼音、重点字、配色、分级名全部在这里算出来，再落成 src/data 下的数据文件。
 *
 * 三条硬约束，任何一条不满足都直接退出、不写文件：
 *   1. 正文只能用字表（char-index.js）里的字，一个越界字都不许有；
 *   2. 多音字必须被 book-pinyin.mjs 的词条覆盖，不许拿本音蒙；
 *   3. 每本书的页数、重点字、封面渐变都得齐。
 *
 * 用法：node scripts/gen-books.mjs
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { CHAR_INDEX } from '../src/data/char-index.js'
import { CORE_BOOKS } from '../src/data/books/core.js'
import { STRICT, WORDS } from './data/book-pinyin.mjs'
import { BOOK_SEED } from './data/book-seed.mjs'

const here = path.dirname(fileURLToPath(import.meta.url))
const dataDir = path.resolve(here, '..', 'src', 'data')

const PINYIN = new Map(CHAR_INDEX.map((c) => [c.char, c.pinyin]))

const PUNCT = {
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

const MAX_WORD = Math.max(...Object.keys(WORDS).map((w) => w.length))

const errors = []

/** 汉字串 → 音节串。词典最长匹配优先，退回单字本音。 */
function toPinyin(text, where) {
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

/* 重点字挑「这本书里出现的、不算烂熟的字」，太常见的虚词挑出来没意义。 */
const TOO_COMMON = new Set(
  '一二三四五六七八九十个们的了是有在不也都和很就又还没太真最别但因为所以我你他她这那什么要能想用做给把让上下里外前后中大小多少来去看说好人天日月水'
)

function pickNewChars(pages, wanted = 8) {
  const seen = new Set()
  const strong = []
  const weak = []
  for (const page of pages) {
    for (const ch of page.text) {
      if (PUNCT[ch] !== undefined || seen.has(ch)) continue
      seen.add(ch)
      ;(TOO_COMMON.has(ch) ? weak : strong).push(ch)
    }
  }
  return [...strong, ...weak].slice(0, wanted)
}

/* 封面渐变从固定色板里按序号取，保证书架上相邻两本不撞色。 */
const PALETTES = [
  ['#ffe6b3', '#c8ebff'],
  ['#d9f6f3', '#ffe0e6'],
  ['#e8e0ff', '#fff1cf'],
  ['#ffe0c2', '#e6f5c9'],
  ['#c8ebff', '#e8e0ff'],
  ['#ffd6d6', '#d9f6f3'],
  ['#e6f5c9', '#ffe6b3'],
  ['#fff1cf', '#ffd6d6'],
  ['#c8ebff', '#e6f5c9'],
  ['#ffe0e6', '#fff1cf'],
  ['#d9f6f3', '#ffe0c2'],
  ['#e8e0ff', '#c8ebff'],
  ['#ffe6b3', '#ffd6d6'],
  ['#e6f5c9', '#c8ebff'],
  ['#ffd6d6', '#e8e0ff'],
  ['#fff1cf', '#d9f6f3'],
  ['#ffe0c2', '#c8ebff'],
  ['#c8ebff', '#ffe6b3']
]

const MIN_PAGES = { 1: 5, 2: 6, 3: 7, 4: 8, 5: 9, 6: 10 }

const usedIds = new Set(CORE_BOOKS.map((b) => b.id))
const usedTitles = new Set(CORE_BOOKS.map((b) => b.title))

const books = BOOK_SEED.map((seed, index) => {
  const id = `bx${index + 1}`
  const where = `${id}《${seed.t}》`
  if (usedIds.has(id)) errors.push(`${where}：id 撞车`)
  usedIds.add(id)
  if (usedTitles.has(seed.t)) errors.push(`${where}：书名重复`)
  usedTitles.add(seed.t)

  const pages = seed.pages.map(([emoji, text]) => ({
    emoji,
    text,
    p: toPinyin(text, where)
  }))

  const need = MIN_PAGES[seed.level] ?? 5
  if (pages.length < need) errors.push(`${where}：第 ${seed.level} 级要 ≥ ${need} 页，只有 ${pages.length} 页`)
  if (!seed.summary) errors.push(`${where}：缺简介`)
  if (!seed.cover) errors.push(`${where}：缺封面图标`)
  if (!seed.sub) errors.push(`${where}：缺分级副标题`)

  return {
    id,
    title: seed.t,
    pinyin: toPinyin(seed.t, `${where} 书名`),
    level: seed.level,
    levelName: `第 ${seed.level} 级 · ${seed.sub}`,
    cover: seed.cover,
    palette: PALETTES[index % PALETTES.length],
    summary: seed.summary,
    newChars: pickNewChars(pages),
    pages
  }
})

if (errors.length) {
  console.error('绘本生成失败：')
  errors.slice(0, 60).forEach((e) => console.error('  ✗', e))
  if (errors.length > 60) console.error(`  …… 还有 ${errors.length - 60} 条`)
  process.exit(1)
}

/* ------------------------------------------------------------- 落盘 */

const q = (s) => `'${s.replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'`

function renderBook(b) {
  const pages = b.pages
    .map((p) => `      { emoji: ${q(p.emoji)}, text: ${q(p.text)}, p: ${q(p.p)} }`)
    .join(',\n')
  return `  {
    id: ${q(b.id)},
    title: ${q(b.title)},
    pinyin: ${q(b.pinyin)},
    level: ${b.level},
    levelName: ${q(b.levelName)},
    cover: ${q(b.cover)},
    palette: [${b.palette.map(q).join(', ')}],
    summary: ${q(b.summary)},
    newChars: [${b.newChars.map(q).join(', ')}],
    pages: [
${pages}
    ]
  }`
}

const byLevel = new Map()
for (const b of books) {
  if (!byLevel.has(b.level)) byLevel.set(b.level, [])
  byLevel.get(b.level).push(b)
}
const levels = [...byLevel.keys()].sort((a, b) => a - b)

const booksDir = path.join(dataDir, 'books')
fs.mkdirSync(booksDir, { recursive: true })

for (const level of levels) {
  const list = byLevel.get(level)
  const file = `/**
 * 第 ${level} 级扩展绘本 —— 由 scripts/gen-books.mjs 生成，请勿手改。
 * 正文改动请编辑 scripts/data/book-seed-*.mjs 后重新生成。
 */

export const LEVEL_${level}_BOOKS = [
${list.map(renderBook).join(',\n')}
]
`
  fs.writeFileSync(path.join(booksDir, `l${level}.js`), file)
}

const barrel = `/**
 * 扩展绘本汇总 —— 由 scripts/gen-books.mjs 生成，请勿手改。
 */

${levels.map((l) => `import { LEVEL_${l}_BOOKS } from './l${l}.js'`).join('\n')}

export const EXTENDED_BOOKS = [
${levels.map((l) => `  ...LEVEL_${l}_BOOKS`).join(',\n')}
]
`
fs.writeFileSync(path.join(booksDir, 'extended.js'), barrel)

/* 首屏只需要「有几本、都是什么 id」，正文一页都不该跟着进主包。 */
const all = [...CORE_BOOKS, ...books].sort((a, b) => a.level - b.level)
const index = `/**
 * 绘本轻量索引 —— 由 scripts/gen-books.mjs 生成，请勿手改。
 *
 * 首页的进度环和 progress store 只要数得清「读完几本 / 一共几本」，
 * 从 books.js 拿这个数会把 130 本书的正文一起拽进主包，所以另开这一层。
 */

export const BOOK_IDS = [
${all.map((b) => `  ${q(b.id)}`).join(',\n')}
]

export const TOTAL_BOOKS = ${all.length}
`
fs.writeFileSync(path.join(dataDir, 'book-index.js'), index)

const pageCount = books.reduce((n, b) => n + b.pages.length, 0)
const charCount = new Set(books.flatMap((b) => b.pages.flatMap((p) => [...p.text]))).size
console.log(
  `生成 ${books.length} 本扩展绘本（共 ${pageCount} 页，${charCount} 个不重复符号），` +
    `连同原有 ${CORE_BOOKS.length} 本共 ${all.length} 本。`
)
console.log(
  `分级分布：${levels.map((l) => `L${l}×${byLevel.get(l).length}`).join(' / ')}`
)
