/**
 * Play 场景生成器（ROUND15_H5「缺了自动补」）—— 给字表里的每一个字配一场「玩」。
 *
 * 洪恩的互动是精选的几百个字；开源版要的是**全库同密度**：1820 个字，
 * 谁都不能点开只看到一张空白卡。手写的富脚本永远优先，剩下的字由这里
 * 按「字表 + 部首 + 卡片图标 + 单元主题 + 字源」推出一场能玩完的模板互动，
 * 打上 `templateFallback: true`，好和真正手写的那批区分开。
 *
 * 读：
 *   src/data/char-index.js        字、拼音、部首、笔画、卡片图标、单元
 *   src/data/unit-index.js        单元名（部首推不出主题时的第二线索）
 *   src/data/radicals.js          部首字形与名字
 *   src/data/chars/uN.js          字义与组词（拿来写线索句、出「补词语」）
 *   src/data/etymology.js         字源小图与部件（「图变字」「拼零件」的料）
 *   富脚本（可选，有哪份读哪份）：
 *     src/data/play-rich/uN.js          一单元一片，导出 UNIT_RICH_PLAYS / default
 *     scripts/data/char-play-rich.json  数组或 { 字: 条目 }
 *     scripts/data/char-play-seed.txt   汉字|主题|模板|旁白[|题面]
 *
 * 写：
 *   src/data/char-play-generated.js
 *
 * 用法：
 *   npm run gen:char-play            重新生成
 *   npm run gen:char-play -- --check 只校验生成物是不是最新的（CI 用，不落盘）
 *
 * 富脚本是后落地的：富脚本合进来之后**重跑一次**这个生成器，
 * 它们就会被烤进生成物并盖掉同名的模板条目（H3 的计数也跟着上去）。
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

import { CHAR_INDEX } from '../src/data/char-index.js'
import { UNITS } from '../src/data/unit-index.js'
import { getRadical } from '../src/data/radicals.js'
import { ETYMOLOGY_MAP } from '../src/data/etymology.js'
import {
  DEFAULT_TEMPLATE,
  PLAY_TEMPLATE_MAP,
  PLAY_THEME_MAP,
  templateForChar,
  themeForChar
} from '../src/data/char-play-templates.js'

const here = path.dirname(fileURLToPath(import.meta.url))
const appDir = path.resolve(here, '..')
const dataDir = path.join(appDir, 'src', 'data')
const outFile = path.join(dataDir, 'char-play-generated.js')
const CHECK = process.argv.includes('--check')

const warns = []

/* ------------------------------------------------------------- 输入：课文 */

/** 单元详情包里的字义和组词。全部 99 包都读，字表里每个字都能查到。 */
async function loadDetails() {
  const detail = new Map()
  for (const unit of UNITS) {
    const file = path.join(dataDir, 'chars', `${unit.id}.js`)
    if (!fs.existsSync(file)) {
      warns.push(`${unit.id}：没有详情包，这一单元的字只能用模板线索`)
      continue
    }
    const pack = await import(pathToFileURL(file).href).then((m) => m.default)
    for (const [char, entry] of Object.entries(pack)) detail.set(char, entry)
  }
  return detail
}

/**
 * 字义 → 一句短线索。旁白开头会念它，孩子先知道这个字在说什么再玩。
 * 太长的（一行念不完）宁可不要，模板自己的话已经成句。
 */
const HINT_MAX = 16
function hintFrom(meaning) {
  if (!meaning) return ''
  let text = meaning.replace(/[。！？]+$/, '').trim()
  if (text.length > HINT_MAX && text.includes('，')) text = text.split('，')[0]
  if (text.length > HINT_MAX) return ''
  if (/[|;=\n]/.test(text)) return ''
  return text
}

/** 「补词语」要一个含这个字的短词，两个字的最好念。 */
function wordFrom(entry, char) {
  const words = (entry?.words ?? []).map((w) => w.w ?? w.text ?? '').filter(Boolean)
  const usable = words.filter((w) => w !== char && w.includes(char) && !/[|;=]/.test(w))
  return usable.find((w) => [...w].length === 2) ?? usable.find((w) => [...w].length === 3) ?? ''
}

/** 「数一数」只给真的数得清的数字字。 */
const COUNTABLE = { 一: 1, 二: 2, 两: 2, 三: 3, 四: 4, 五: 5, 六: 6, 七: 7, 八: 8, 九: 9, 十: 10 }

/* ------------------------------------------------------------- 输入：富脚本 */

const RICH_SOURCES = [
  // 一单元一片（ROUND18_H3 之后的落点）：整个目录当一份源读
  { rel: 'src/data/play-rich', kind: 'shards' },
  { rel: 'src/data/char-play-catalog.js', kind: 'module' },
  { rel: 'scripts/data/char-play-rich.json', kind: 'json' },
  { rel: 'scripts/data/char-play-seed.txt', kind: 'text' }
]

/** 分片目录里除 index.js（manifest，没有条目）之外的每一片。 */
async function loadShardDir(dir) {
  const list = []
  for (const name of fs.readdirSync(dir).sort()) {
    if (!name.endsWith('.js') || name === 'index.js') continue
    const mod = await import(pathToFileURL(path.join(dir, name)).href)
    const raw = mod.UNIT_RICH_PLAYS ?? mod.default
    if (Array.isArray(raw)) list.push(...raw)
  }
  return list
}

async function loadRich() {
  const out = new Map()
  for (const source of RICH_SOURCES) {
    const file = path.join(appDir, source.rel)
    if (!fs.existsSync(file)) continue
    let list = []
    if (source.kind === 'shards') {
      list = await loadShardDir(file)
    } else if (source.kind === 'module') {
      const mod = await import(pathToFileURL(file).href)
      const raw = mod.RICH_PLAYS ?? mod.CHAR_PLAY_RICH ?? mod.richPlays ?? mod.default
      list = Array.isArray(raw) ? raw : Object.values(raw ?? {})
    } else if (source.kind === 'json') {
      const raw = JSON.parse(fs.readFileSync(file, 'utf8'))
      list = Array.isArray(raw) ? raw : Object.values(raw)
    } else {
      list = fs
        .readFileSync(file, 'utf8')
        .split('\n')
        .map((l) => l.trim())
        .filter((l) => l && !l.startsWith('#'))
        .map((l) => {
          const [char, theme, template, narration, prompt] = l.split('|')
          return { char, theme, template, narration, prompt }
        })
    }
    for (const entry of list) {
      if (!entry?.char) continue
      out.set(entry.char, { ...entry, from: source.rel })
    }
  }
  return out
}

/* ----------------------------------------------------------------- 生成 */

const details = await loadDetails()
const rich = await loadRich()

const rows = []
const stats = { theme: new Map(), template: new Map(), hint: 0, rich: 0 }
const bump = (map, key) => map.set(key, (map.get(key) ?? 0) + 1)

for (const c of CHAR_INDEX) {
  const detail = details.get(c.char)
  const ety = ETYMOLOGY_MAP.get(c.char)
  const unit = UNITS.find((u) => u.id === c.unit)
  const theme = themeForChar({ radical: c.radical, unitName: unit?.name })

  const extra = {}
  if (ety?.sketch) extra.sketch = true
  const parts = (ety?.parts ?? []).map((p) => p.g).filter((g) => g && g !== c.char)
  if (parts.length >= 2) extra.parts = parts.slice(0, 3)
  const word = wordFrom(detail, c.char)
  if (word) extra.word = word
  if (COUNTABLE[c.char]) extra.count = COUNTABLE[c.char]
  if (ety?.kind) extra.kind = ety.kind

  const template = templateForChar({ char: c.char, theme, extra })
  const hint = hintFrom(detail?.meaning)
  if (hint) stats.hint += 1
  bump(stats.theme, theme)
  bump(stats.template, template)

  // 只留这一场用得上的料，生成物才小
  const used = {}
  const tpl = PLAY_TEMPLATE_MAP.get(template)
  if (tpl?.need === 'parts') used.parts = extra.parts.join(',')
  if (tpl?.need === 'word') used.word = extra.word
  if (tpl?.need === 'count') used.count = String(extra.count)
  if (tpl?.need === 'sketch') used.kind = extra.kind ?? 'xiang'

  rows.push({ char: c.char, theme, template, hint, extra: used })
}

/* 富脚本盖在模板上。舞台拿到的一定是完整条目：富脚本没写 props 的，
   仍按它指定的模板展开一份能玩的 props，只把文案换成手写的。 */
const richEntries = []
for (const [char, entry] of rich) {
  const row = rows.find((r) => r.char === char)
  if (!row) warns.push(`富脚本「${char}」不在字表里，仍会收进索引`)
  const theme = PLAY_THEME_MAP.has(entry.theme) ? entry.theme : (row?.theme ?? 'word')
  const template = PLAY_TEMPLATE_MAP.has(entry.template)
    ? entry.template
    : (() => {
        if (entry.template) warns.push(`富脚本「${char}」的模板 ${entry.template} 不认识，按主题重挑`)
        return row?.template ?? DEFAULT_TEMPLATE
      })()
  richEntries.push({
    char,
    theme,
    template,
    hint: entry.hint ?? row?.hint ?? '',
    narration: entry.narration ?? '',
    prompt: entry.prompt ?? '',
    props: entry.props ?? null,
    extra: row?.extra ?? {}
  })
  stats.rich += 1
}
const richChars = new Set(richEntries.map((e) => e.char))

/* ----------------------------------------------------------------- 落盘 */

const encodeExtra = (extra) =>
  Object.entries(extra)
    .map(([k, v]) => `${k}=${v}`)
    .join(';')

const rowLine = (r) => [r.char, r.theme, r.template, r.hint, encodeExtra(r.extra)].join('|').replace(/\|+$/, '')

const topList = (map, n) =>
  [...map.entries()]
    .filter(([k]) => !k.startsWith('rich:'))
    .sort((a, b) => b[1] - a[1])
    .slice(0, n)
    .map(([k, v]) => `${k} ${v}`)
    .join('，')

function render() {
  const body = rows
    .filter((r) => !richChars.has(r.char))
    .map(rowLine)
    .join('\n')
  const richBody = richEntries
    .map((e) => `  ${JSON.stringify(e)}`)
    .join(',\n')
  return `/**
 * 全库 Play 索引 —— 每个字一场「玩」，由 scripts/gen-char-play.mjs 生成，请勿手改。
 *
 * 每行：汉字|主题|模板|一句话线索|额外料（k=v;k=v，没有就空着）
 * 旁白、题面、选项都不存在这里，由 char-play-templates.js 按行展开，
 * 生成物只留「这个字玩什么」这一点信息。
 *
 * 模板条目一律 templateFallback: true；RICH_PLAYS 是手写的富脚本，
 * 展开后 templateFallback: false，运行时盖在同名的模板条目上。
 *
 * 覆盖：${rows.length} 字（富脚本 ${richEntries.length}，模板 ${rows.length - richChars.size}）
 * 主题分布：${topList(stats.theme, 6)}
 * 模板分布：${topList(stats.template, 6)}
 */

export const PLAY_ROWS = \`
${body}
\`

export const RICH_PLAYS = [
${richBody}
]

export const TOTAL_GENERATED_PLAYS = ${rows.length - richChars.size}
export const TOTAL_RICH_PLAYS = ${richEntries.length}
`
}

const rendered = render()

if (CHECK) {
  const current = fs.existsSync(outFile) ? fs.readFileSync(outFile, 'utf8') : ''
  if (current !== rendered) {
    console.error('✗ char-play-generated.js 和生成器对不上，请跑 npm run gen:char-play')
    process.exit(1)
  }
  console.log(`✓ char-play-generated.js 是最新的（${rows.length} 字）`)
} else {
  fs.writeFileSync(outFile, rendered)
  warns.forEach((w) => console.warn(' !', w))
  console.log(
    `Play 场景已生成：${rows.length} 字全覆盖` +
      `（模板 ${rows.length - richChars.size}，富脚本 ${richEntries.length}，带字义线索 ${stats.hint}）。`
  )
  console.log(`  主题 ${stats.theme.size} 类：${topList(stats.theme, 8)}`)
  console.log(`  模板 ${stats.template.size} 种：${topList(stats.template, 12)}`)
}
