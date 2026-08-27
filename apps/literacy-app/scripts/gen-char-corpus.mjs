/**
 * 字库生成器 —— 字表的唯一真源是 scripts/data/char-seed.txt，
 * 索引、单元课文包和共享基线都由这里生成，不允许手改生成物。
 *
 * 生成：
 *   src/data/char-index.js            全部汉字的索引行（主包唯一带的一层）
 *   src/data/chars/uN.js              带课文的单元详情包（只生成 seed 里写了课文的单元）
 *   ../../shared/data/common-hanzi.json  monorepo 共享字库基线
 *
 * 派生字段一律算出来，不手写：
 *   声调    从带调拼音里解析
 *   笔画    数 hanzi-writer-data 里的笔画条数（离线笔顺用的就是这份数据，天然对齐）
 *   部首    cnchar 的部首字形，再映射到 radicals.js 的 id
 *   组词/例句拼音   pinyin-pro 标注（含变调和轻声）
 *
 * 后三项要联网装的工具包才算得出来，所以结果落在 scripts/data/derived-cache.json，
 * 平时生成只读缓存、不依赖任何额外依赖。改了 seed 之后用
 *
 *   node scripts/gen-char-corpus.mjs --refresh
 *
 * 重新派生（需要能 import 到 cnchar / cnchar-radical / pinyin-pro，
 * 可以用 TOOLS_DIR=/path/to/node_modules 指到临时装的一份）。
 */

import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import { pathToFileURL, fileURLToPath } from 'node:url'

import { getRadical } from '../src/data/radicals.js'

const here = path.dirname(fileURLToPath(import.meta.url))
const appDir = path.resolve(here, '..')
const repoRoot = path.resolve(appDir, '..', '..')
const seedFile = path.join(here, 'data', 'char-seed.txt')
const cacheFile = path.join(here, 'data', 'derived-cache.json')
const indexOut = path.join(appDir, 'src', 'data', 'char-index.js')
const charsDir = path.join(appDir, 'src', 'data', 'chars')
const baselineOut = path.join(repoRoot, 'shared', 'data', 'common-hanzi.json')

const REFRESH = process.argv.includes('--refresh')

/* --------------------------------------------------------------- seed 解析 */

/**
 * 每行是一个字，字段用 | 分隔：
 *   汉字|拼音|部首 id（- 表示自动派生）|卡片图标[|释义|组词|例句]
 * 只有前四段的行属于「老单元」，课文仍在手写的 chars/uN.js 里；
 * 写满七段的行由本脚本生成课文包。
 * 组词用逗号分隔，组词和例句都可以用 `文本=拼音` 手动指定拼音。
 */
function parseSeed(text) {
  const units = []
  let unit = null
  text.split('\n').forEach((raw, i) => {
    const line = raw.trim()
    if (!line || line.startsWith('#')) return
    const at = i + 1
    if (line.startsWith('@unit ')) {
      const [id, name, emoji, color, desc] = line.slice(6).split('|')
      if (!id || !name || !emoji || !color || !desc) throw new Error(`第 ${at} 行单元头字段不全`)
      unit = { id, name, emoji, color, desc, rows: [] }
      units.push(unit)
      return
    }
    if (!unit) throw new Error(`第 ${at} 行出现在任何 @unit 之前`)
    const f = line.split('|')
    if (f.length !== 4 && f.length !== 7) throw new Error(`第 ${at} 行应有 4 或 7 段，实际 ${f.length}`)
    const [char, pinyin, radical, emoji, meaning, words, sentence] = f
    if ([...char].length !== 1) throw new Error(`第 ${at} 行「${char}」不是单个汉字`)
    unit.rows.push({
      line: at,
      char,
      pinyin,
      radical: radical === '-' ? null : radical,
      emoji,
      detail:
        f.length === 7
          ? { meaning, words: words.split(',').map(splitOverride), sentence: splitOverride(sentence) }
          : null
    })
  })
  return units
}

/** `文本=拼音` → { text, pinyin }，没写拼音就留空等派生。 */
function splitOverride(field) {
  const at = field.indexOf('=')
  return at === -1
    ? { text: field, pinyin: null }
    : { text: field.slice(0, at), pinyin: field.slice(at + 1) }
}

/* ----------------------------------------------------------------- 派生层 */

const TONE_ROWS = ['āēīōūǖ', 'áéíóúǘ', 'ǎěǐǒǔǚ', 'àèìòùǜ']
const TONELESS = 'aeiouv'

/** 带调拼音 → 声调（1-4，轻声算 5）。 */
function toneOf(pinyin) {
  for (const ch of pinyin) {
    const at = TONE_ROWS.findIndex((row) => row.includes(ch))
    if (at !== -1) return at + 1
  }
  return 5
}

/** 去掉声调符号，用来比对同一个音节的不同标调习惯。 */
function stripTone(syllable) {
  return [...syllable]
    .map((ch) => {
      const row = TONE_ROWS.find((r) => r.includes(ch))
      return row ? TONELESS[row.indexOf(ch)] : ch
    })
    .join('')
}

const emptyCache = () => ({ strokes: {}, radical: {}, pinyin: {} })

function loadCache() {
  if (!fs.existsSync(cacheFile)) return emptyCache()
  return { ...emptyCache(), ...JSON.parse(fs.readFileSync(cacheFile, 'utf8')) }
}

/**
 * 派生工具只在 --refresh 时用得上。默认从应用自己的 node_modules 找，
 * 也可以用 TOOLS_DIR 指到临时装的一份，免得把纯生成期的包塞进仓库依赖。
 */
async function loadTools() {
  const from = process.env.TOOLS_DIR
    ? path.join(process.env.TOOLS_DIR, 'package.json')
    : path.join(appDir, 'package.json')
  const req = createRequire(from)
  // 这几个包发的都是 CommonJS，从 ESM 里 import 进来时真正的导出可能挂在 default 上。
  const load = async (name) => {
    const mod = await import(pathToFileURL(req.resolve(name)).href)
    return mod.default?.default ?? mod.default ?? mod
  }
  const { pinyin } = await load('pinyin-pro')
  const cnchar = await load('cnchar')
  cnchar.use(await load('cnchar-radical'))
  return {
    pinyin: (text) => pinyin(text, { toneType: 'symbol', type: 'string', nonZh: 'consecutive' }),
    radicalGlyph: (char) => cnchar.radical(char)[0]?.radical ?? null
  }
}

function strokeCounter() {
  const req = createRequire(path.join(appDir, 'package.json'))
  const dir = path.dirname(req.resolve('hanzi-writer-data/package.json'))
  return (char) => {
    const file = path.join(dir, `${char}.json`)
    if (!fs.existsSync(file)) return null
    return JSON.parse(fs.readFileSync(file, 'utf8')).strokes?.length ?? null
  }
}

/** 例句里的中文标点在拼音行里换成半角，并去掉标点前多出来的空格。 */
const PUNCT = { '。': '.', '，': ',', '！': '!', '？': '?', '、': ',', '：': ':', '；': ';' }
function tidyPinyin(text) {
  let out = text
  for (const [zh, ascii] of Object.entries(PUNCT)) out = out.split(zh).join(ascii)
  return out.replace(/\s+([.,!?:;])/g, '$1').replace(/\s+/g, ' ').trim()
}

/**
 * 名词后缀「子」读轻声（箱子 xiāng zi），标注器只在词典里收了的词上做对，
 * 「裤子」「笛子」这类没收进去的就会退回本音 zǐ。这是一条稳定的普通话规则，
 * 在这里统一补上；「子」当实词讲（莲子的籽、石子的小石头）的词列在例外里。
 */
const ZI_KEEPS_TONE = new Set(['莲子', '石子', '瓜子', '种子', '亲子'])
function neutralizeZi(text, pinyin) {
  const chars = [...text].filter((c) => /\p{Script=Han}/u.test(c))
  const tokens = pinyin.split(' ')
  if (chars.length !== tokens.length) return pinyin
  chars.forEach((c, i) => {
    if (c !== '子' || i === 0) return
    if (ZI_KEEPS_TONE.has(chars[i - 1] + '子')) return
    tokens[i] = tokens[i].replace(/^zǐ/, 'zi')
  })
  return tokens.join(' ')
}

/* ------------------------------------------------------------------- 生成 */

const jsString = (s) => `'${s.replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'`

function renderIndex(units, entries) {
  const rows = []
  for (const unit of units) {
    rows.push(`  // ${unit.id} ${unit.name}`)
    for (const row of unit.rows) {
      const e = entries.get(row.char)
      rows.push(
        `  [${[jsString(e.char), jsString(e.pinyin), e.tone, jsString(unit.id), jsString(e.radical), e.strokes, jsString(e.emoji)].join(', ')}],`
      )
    }
  }
  return `/**
 * 字表索引 —— ${entries.size} 个字的「轻」信息，主包里只留这一份。
 *
 * 释义、组词、例句这些「重」内容按单元拆在 chars/ 目录下，
 * 由 characters.js 里的加载器按需 import()，主包不会一次背上整份课文。
 * 两边的字必须一一对应，\`npm run check:data\` 会核对。
 *
 * 每行的字段顺序：[汉字, 拼音, 声调, 单元, 部首 id, 笔画, 卡片图标]
 *
 * 本文件由 scripts/gen-char-corpus.mjs 从 scripts/data/char-seed.txt 生成，请勿手改。
 */

const ROWS = [
${rows.join('\n')}
]

export const CHAR_INDEX = ROWS.map(([char, pinyin, tone, unit, radical, strokes, emoji]) => ({
  char,
  pinyin,
  tone,
  unit,
  radical,
  strokes,
  emoji
}))
`
}

function renderPack(unit, entries) {
  const body = unit.rows
    .map((row) => {
      const d = entries.get(row.char).detail
      const words = d.words
        .map((w) => `      { w: ${jsString(w.text)}, p: ${jsString(w.pinyin)} }`)
        .join(',\n')
      return `  ${jsString(row.char)}: {
    meaning: ${jsString(d.meaning)},
    words: [
${words}
    ],
    sentence: { text: ${jsString(d.sentence.text)}, p: ${jsString(d.sentence.pinyin)} }
  }`
    })
    .join(',\n')
  return `/**
 * 单元「${unit.name}」的字义、组词与例句。
 *
 * 只有真正翻到这个单元（或打开单元里某个字）时才会加载，
 * 字表索引在 ../char-index.js。
 *
 * 由 scripts/gen-char-corpus.mjs 生成，请勿手改。
 */

export default {
${body}
}
`
}

function renderBaseline(previous, units, entries) {
  const kept = new Map(previous.characters.map((c) => [c.character, c]))
  const lines = []
  for (const unit of units) {
    for (const row of unit.rows) {
      const e = entries.get(row.char)
      const old = kept.get(row.char)
      const entry = old ?? {
        character: e.char,
        pinyin: e.pinyin,
        meaning: e.detail.meaning.replace(/。$/, ''),
        example: e.detail.words[0].text
      }
      lines.push(
        `    {"character":${JSON.stringify(entry.character)},"pinyin":${JSON.stringify(entry.pinyin)},` +
          `"meaning":${JSON.stringify(entry.meaning)},"example":${JSON.stringify(entry.example)}}`
      )
    }
  }
  const head = { ...previous }
  delete head.characters
  const headLines = Object.entries(head).map(([k, v]) => `  ${JSON.stringify(k)}: ${JSON.stringify(v)}`)
  return `{\n${headLines.join(',\n')},\n  "characters": [\n${lines.join(',\n')}\n  ]\n}\n`
}

/* --------------------------------------------------------------------- 主 */

/** 部首字形 → radicals.js 的 id。cnchar 报出来的字形靠它落到本项目的 id 上。 */
const GLYPH_TO_ID = JSON.parse(
  fs.readFileSync(path.join(here, 'data', 'radical-glyphs.json'), 'utf8')
)

const units = parseSeed(fs.readFileSync(seedFile, 'utf8'))
const cache = loadCache()
const tools = REFRESH ? await loadTools() : null
const countStrokes = strokeCounter()

const fails = []
const warns = []
const entries = new Map()

const cachedPinyin = (text) => {
  if (tools && !cache.pinyin[text]) {
    cache.pinyin[text] = neutralizeZi(text, tidyPinyin(tools.pinyin(text)))
  }
  return cache.pinyin[text] ?? null
}

for (const unit of units) {
  for (const row of unit.rows) {
    const where = `${unit.id} ${row.char}（第 ${row.line} 行）`
    if (entries.has(row.char)) {
      fails.push(`${where}：与 ${entries.get(row.char).unit} 重复`)
      continue
    }

    if (tools && cache.strokes[row.char] === undefined) cache.strokes[row.char] = countStrokes(row.char)
    if (cache.strokes[row.char] === undefined) cache.strokes[row.char] = countStrokes(row.char)
    const strokes = cache.strokes[row.char]
    if (!strokes) fails.push(`${where}：hanzi-writer-data 里没有笔顺，数不出笔画`)

    let radical = row.radical
    if (!radical) {
      if (tools && !cache.radical[row.char]) {
        const glyph = tools.radicalGlyph(row.char)
        const id = radicalIdOf(glyph)
        if (!id) fails.push(`${where}：部首字形「${glyph}」在 radicals.js 里没有对应 id`)
        else cache.radical[row.char] = id
      }
      radical = cache.radical[row.char] ?? null
      if (!radical) fails.push(`${where}：部首未派生，请跑 --refresh`)
    }
    if (radical && !getRadical(radical)) fails.push(`${where}：部首 id「${radical}」查不到`)

    const tone = toneOf(row.pinyin)
    if (!(tone >= 1 && tone <= 5)) fails.push(`${where}：拼音「${row.pinyin}」解不出声调`)
    if (!row.emoji) fails.push(`${where}：缺卡片图标`)

    let detail = null
    if (row.detail) {
      const { meaning, words, sentence } = row.detail
      if (!meaning.endsWith('。')) fails.push(`${where}：释义要以句号结尾`)
      if (words.length < 2) fails.push(`${where}：至少要 2 个组词`)
      const annotate = (item, label) => {
        const p = item.pinyin ?? cachedPinyin(item.text)
        if (!p) fails.push(`${where}：${label}「${item.text}」缺拼音，请跑 --refresh`)
        return { text: item.text, pinyin: p ?? '' }
      }
      const outWords = words.map((w) => {
        if (!w.text.includes(row.char)) fails.push(`${where}：组词「${w.text}」里没有这个字`)
        return reconcile(where, row.char, row.pinyin, annotate(w, '组词'), '组词', warns)
      })
      const outSentence = reconcile(
        where,
        row.char,
        row.pinyin,
        annotate(sentence, '例句'),
        '例句',
        warns
      )
      if (!sentence.text.includes(row.char)) fails.push(`${where}：例句里没有这个字`)
      if (!/[。！？]$/.test(sentence.text)) fails.push(`${where}：例句要以中文句末标点结尾`)
      detail = { meaning, words: outWords, sentence: outSentence }
    }

    entries.set(row.char, {
      char: row.char,
      pinyin: row.pinyin,
      tone,
      unit: unit.id,
      radical,
      strokes,
      emoji: row.emoji,
      detail
    })
  }
  if (unit.rows.length < 5) fails.push(`${unit.id}：只有 ${unit.rows.length} 个字，少于 5`)
}

/**
 * 组词和例句里这个字读出来的音，应当和索引登记的读音是同一个音节。
 * 多音字最容易在这里露馅：标注器按词典挑读音，挑错了整条拼音就和字表打架。
 * 字表登记的读音是人定的，以它为准，这里就地把标注掰回来，并把改动报出来。
 */
function reconcile(where, char, declared, item, label, sink) {
  const chars = [...item.text].filter((c) => /\p{Script=Han}/u.test(c))
  const tokens = item.pinyin.split(' ')
  if (chars.length !== tokens.length) return item
  let changed = false
  chars.forEach((c, i) => {
    if (c !== char) return
    const trailing = tokens[i].match(/[^\p{Letter}]*$/u)[0]
    const got = trailing ? tokens[i].slice(0, -trailing.length) : tokens[i]
    // 词里读轻声（没有调号）是正常的，别的读音对不上才算挑错了音。
    if (got === declared || (toneOf(got) === 5 && stripTone(got) === stripTone(declared))) return
    sink.push(`${where}：${label}「${item.text}」标成了 ${got}，按字表改回 ${declared}`)
    tokens[i] = declared + trailing
    changed = true
  })
  return changed ? { ...item, pinyin: tokens.join(' ') } : item
}

function radicalIdOf(glyph) {
  return GLYPH_TO_ID[glyph] ?? null
}

if (fails.length) {
  fails.forEach((f) => console.error(' ✗', f))
  console.error(`\n字库生成中止：${fails.length} 项不合格。`)
  process.exit(1)
}

const generatedUnits = units.filter((u) => u.rows.every((r) => r.detail))
const legacyUnits = units.filter((u) => u.rows.every((r) => !r.detail))
if (generatedUnits.length + legacyUnits.length !== units.length) {
  console.error('✗ 有单元的课文写了一半，同一个单元要么全写、要么全不写。')
  process.exit(1)
}

fs.writeFileSync(indexOut, renderIndex(units, entries))
for (const unit of generatedUnits) {
  fs.writeFileSync(path.join(charsDir, `${unit.id}.js`), renderPack(unit, entries))
}
const previous = JSON.parse(fs.readFileSync(baselineOut, 'utf8'))
fs.writeFileSync(baselineOut, renderBaseline(previous, units, entries))
if (tools) fs.writeFileSync(cacheFile, JSON.stringify(cache, null, 2) + '\n')

warns.forEach((w) => console.warn(' !', w))
console.log(
  `字库已生成：${entries.size} 字 / ${units.length} 单元` +
    `（课文包 ${generatedUnits.length} 个由脚本生成，${legacyUnits.length} 个仍是手写稿）` +
    `${warns.length ? `，按字表校正了 ${warns.length} 处多音字标注` : ''}。`
)
