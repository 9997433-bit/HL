/**
 * Play 补齐索引生成器（ROUND15_H5「缺了自动补」）。
 *
 * 「玩」这一步有三层，一层盖一层：
 *
 *   富脚本   char-play-rich.js       人工写的情境，一字一稿
 *   生成层   char-play-generated.js  ← 本脚本产出：全库 1820 字一字一行
 *   运行时   char-play.js            连生成层都没有的字（绘本生字、搜索进来的
 *                                    生僻字）现算一关，绝不空场
 *
 * 中间这一层解决的是「模板补齐说不出这个字在讲什么」：运行时只看得到主包里的
 * 字表索引（拼音 / 部首 / 卡片图标），说不出「铃」是叮叮当当响的小铃铛，也不
 * 知道「明」的字源是日和月。这两样都在按需加载的课文包和字源语料里，等孩子
 * 点进「玩」再去下载就晚了，所以在这里离线算好，压成一行：
 *
 *   汉字|模板|一句话线索
 *
 * 模板只用舞台认得的那几个（char-play.js 的 PLAY_TEMPLATE_IDS），
 * 并且只在**有把握比轮转更合适**时才写死：
 *
 *   有字源小图的象形 / 指事字 → morph-story（图变字，本来就是照着东西画的）
 *   形声 / 会意字且形旁不是字本身 → drag-parts（把管意思的偏旁拼回去）
 *   其余                        → 沿用运行时的主题轮转，不跟它抢
 *
 * 线索句取字义的前半句（太长的宁可不要），运行时拼在旁白前面，
 * 于是 1820 个字每一场的第一句话都是这个字自己的话，而不是同一张空白卡。
 *
 * 用法：
 *   npm run gen:char-play              重新生成
 *   npm run verify:char-play           只校验生成物是不是最新的（check:data 会跑）
 *
 * 字表、课文、字源任何一边改了都要重跑；忘了重跑 check:data 会红。
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

import { CHAR_INDEX } from '../src/data/char-index.js'
import { UNITS } from '../src/data/unit-index.js'
import { ETYMOLOGY_MAP } from '../src/data/etymology.js'
import { PLAY_TEMPLATE_IDS, defaultPlayPlan } from '../src/data/char-play.js'

const here = path.dirname(fileURLToPath(import.meta.url))
const appDir = path.resolve(here, '..')
const dataDir = path.join(appDir, 'src', 'data')
const outFile = path.join(dataDir, 'char-play-generated.js')
const CHECK = process.argv.includes('--check')

const warns = []

/* ----------------------------------------------------------------- 输入 */

/** 单元详情包里的字义。99 个包全读一遍，字表里每个字都能查到自己的解释。 */
async function loadMeanings() {
  const meanings = new Map()
  for (const unit of UNITS) {
    const file = path.join(dataDir, 'chars', `${unit.id}.js`)
    if (!fs.existsSync(file)) {
      warns.push(`${unit.id}：没有详情包，这一单元的字只能用通用旁白`)
      continue
    }
    const pack = await import(pathToFileURL(file).href).then((m) => m.default)
    for (const [char, entry] of Object.entries(pack)) {
      if (entry?.meaning) meanings.set(char, entry.meaning)
    }
  }
  return meanings
}

/**
 * 字义 → 一句短线索。旁白开头念它，孩子先知道这个字在说什么再玩。
 * 念不完一口气的宁可不要——模板自己那句话已经成句，缺了线索也不会读不通。
 */
const HINT_MAX = 16
function hintFrom(meaning) {
  if (!meaning) return ''
  let text = meaning.replace(/[。！？\s]+$/, '').trim()
  if (text.length > HINT_MAX && text.includes('，')) text = text.split('，')[0]
  if (text.length > HINT_MAX) return ''
  if (/[|\n]/.test(text)) return ''
  return text
}

/* ----------------------------------------------------------------- 选模板 */

const templateSet = new Set(PLAY_TEMPLATE_IDS)
const pickTemplate = (id, fallback) => (templateSet.has(id) ? id : fallback)

/** 同一个字每次都换到同一个替补玩法。 */
function hashOf(text) {
  let h = 2166136261
  for (const ch of text) {
    h ^= ch.codePointAt(0)
    h = Math.imul(h, 16777619)
  }
  return h >>> 0
}

/**
 * 运行时的主题轮转本来就铺得开（五种玩法最多的一种也就四分之一），
 * 所以这里不重挑，只在字源明确说得上话的地方纠三处：
 *
 *   1. 有小图的象形 / 指事字：本来就是照着东西画的，「图变字」名副其实
 *   2. 形声 / 会意字轮到「图变字」：它不是画出来的，改成把管意思的形旁拼回去
 *   3. 轮到「拼一拼」却没有部件可讲：拼了也讲不出道理，换成找一找 / 点一点
 */
function templateFor(char, plan, ety) {
  const parts = (ety?.parts ?? []).filter((p) => p.g)
  const usableRadical = Boolean(plan.radicalGlyph) && plan.radicalGlyph !== char
  if (ety?.sketch) return pickTemplate('morph-story', plan.template)
  if (plan.template === 'morph-story' && parts.length >= 2 && usableRadical) {
    return pickTemplate('drag-parts', plan.template)
  }
  if (plan.template === 'drag-parts' && parts.length < 2) {
    return pickTemplate(hashOf(char) % 2 ? 'emoji-hunt' : 'tap-reveal', plan.template)
  }
  return plan.template
}

/* ----------------------------------------------------------------- 生成 */

const meanings = await loadMeanings()

const rows = []
const stats = { template: new Map(), theme: new Map(), hint: 0, override: 0 }
const bump = (map, key) => map.set(key, (map.get(key) ?? 0) + 1)

for (const c of CHAR_INDEX) {
  const plan = defaultPlayPlan(c.char)
  const ety = ETYMOLOGY_MAP.get(c.char)
  const template = templateFor(c.char, plan, ety)
  const hint = hintFrom(meanings.get(c.char))
  if (!hint) warns.push(`${c.char}：字义写不出一句短线索，这个字只有通用旁白`)
  if (hint) stats.hint += 1
  if (template !== plan.template) stats.override += 1
  bump(stats.template, template)
  bump(stats.theme, plan.theme)
  rows.push({ char: c.char, template, hint })
}

/* ----------------------------------------------------------------- 落盘 */

const rowLine = (r) => `${r.char}|${r.template}|${r.hint}`

const topList = (map, n) =>
  [...map.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, n)
    .map(([k, v]) => `${k} ${v}`)
    .join('，')

function render() {
  return `/**
 * 全库 Play 补齐索引 —— 每个字一行，由 scripts/gen-char-play.mjs 生成，请勿手改。
 *
 * 每行：汉字|模板|一句话线索
 *
 * 模板是舞台认得的那几个（见 char-play.js 的 PLAY_TEMPLATES）；线索取自单元详情
 * 包里的字义，运行时拼在旁白前面，让 1820 个字各说各的话。道具、乱序、落点仍由
 * char-play.js 现算，所以这份索引只有「玩什么 + 说什么」这么点东西。
 *
 * 覆盖 ${rows.length} 字（带字义线索 ${stats.hint}，按字源改写玩法 ${stats.override}）。
 * 模板分布：${topList(stats.template, 6)}
 */

export const PLAY_ROWS = \`
${rows.map(rowLine).join('\n')}
\`

export const TOTAL_GENERATED_PLAYS = ${rows.length}
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
  if (warns.length) console.warn(` ! ${warns.length} 个字没有线索句：${warns.slice(0, 5).join('；')}`)
  console.log(
    `Play 补齐索引已生成：${rows.length} 字全覆盖` +
      `（字义线索 ${stats.hint}，按字源改写玩法 ${stats.override}）。`
  )
  console.log(`  模板 ${stats.template.size} 种：${topList(stats.template, 8)}`)
  console.log(`  主题 ${stats.theme.size} 类：${topList(stats.theme, 8)}`)
}
