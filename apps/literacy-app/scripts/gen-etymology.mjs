/**
 * 字源语料生成器 —— 形声字那一大半，是算出来的，不是手搓的。
 *
 * 手写的六十多个字（etymology.js 里的 PICTURES / COMPOUNDS）每个都带一张小图或者
 * 一段独有的故事，那部分只能一个一个写。但汉字里绝大多数是形声字，它们的讲法
 * 高度同构，永远是同一句话的三个空：
 *
 *   「<意思> + 带「<形旁>」的字，<这一类是干什么的> + 「<声旁>」管读音」
 *
 * 既然结构固定，就没有理由抄一百遍。种子文件里每个形声字只写两样东西
 * ——声旁是谁、声旁本来念什么——剩下的全部派生：
 *
 *   形旁     取自字表索引的部首（char-index.js，本来就是生成的）
 *   形旁语义 SEMANTIC 表按形旁字形查（三点水 = 和水有关）
 *   字义     取自单元详情包里那句给孩子看的释义
 *   读音     取自字表索引的带调拼音；和声旁读音比对，决定要不要写「A → B」
 *
 * 会意字没有这种通用结构（「休」和「泪」的故事没法套同一个模子），
 * 所以种子里连零件带两句话一起写，生成器只负责校验和排版。
 *
 * 输出：
 *   src/data/etymology-derived.js   派生出来的字源条目
 *   src/data/etymology-index.js     单字页用的轻量索引（手写 + 派生，顺序一致）
 *
 * 用法：node scripts/gen-etymology.mjs
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { CHARACTER_MAP, loadAllCharacters } from '../src/data/characters.js'
import { getRadical } from '../src/data/radicals.js'
import { HANDWRITTEN } from '../src/data/etymology.js'

const here = path.dirname(fileURLToPath(import.meta.url))
const appDir = path.resolve(here, '..')
const seedFile = path.join(here, 'data', 'etymology-seed.txt')
const derivedOut = path.join(appDir, 'src', 'data', 'etymology-derived.js')
const indexOut = path.join(appDir, 'src', 'data', 'etymology-index.js')

/* ------------------------------------------------------------- 形旁语义表
 *
 * note 是零件卡片上那一行小字（要短，孩子一眼扫过去）；
 * line 是「本来是什么」里那半句话（要成句）。
 * 部首本身的讲解在 radicals.js，那边只覆盖重点讲的 18 个，这里得管全。
 */
const SEMANTIC = {
  氵: { note: '和水有关', line: '几乎都和水有关' },
  艹: { note: '和草木有关', line: '差不多都是花草树木' },
  木: { note: '和树木有关', line: '大多和树木、木头有关' },
  扌: { note: '是手上的动作', line: '几乎都是手做的动作' },
  忄: { note: '和心情有关', line: '多半和心情、想法有关' },
  口: { note: '和嘴巴有关', line: '常常和嘴巴、说话、吃东西有关' },
  讠: { note: '和说话有关', line: '基本都和说话有关' },
  女: { note: '和女性、家人有关', line: '常和女性、家里人有关' },
  亻: { note: '和人有关', line: '多半和人有关' },
  日: { note: '和太阳、时间有关', line: '多和太阳、天光、时间有关' },
  月: { note: '和身体有关', line: '大多是身体上的部位' },
  火: { note: '和火有关', line: '都和火、和热有关' },
  土: { note: '和泥土、地面有关', line: '多和泥土、土地有关' },
  目: { note: '和眼睛有关', line: '都和眼睛、看有关' },
  山: { note: '和山有关', line: '多和山、和高处有关' },
  宀: { note: '和房子有关', line: '多和房子、屋里的事有关' },
  纟: { note: '和线、布有关', line: '多和线、布、颜色有关' },
  犭: { note: '是一种动物', line: '几乎都是有毛的走兽' },
  雨: { note: '和天气有关', line: '都和天上落下来的东西有关' },
  钅: { note: '和金属有关', line: '都是金属做的东西' },
  虫: { note: '是一种虫子', line: '多半是小虫小兽' },
  足: { note: '和脚有关', line: '都和脚、和走跑有关' },
  车: { note: '和车有关', line: '都和车有关' },
  鸟: { note: '是一种鸟', line: '都是鸟' },
  禾: { note: '和庄稼有关', line: '都和庄稼、粮食有关' },
  米: { note: '和粮食有关', line: '都和米、和粮食有关' },
  饣: { note: '和吃的有关', line: '都和吃的有关' },
  衤: { note: '和衣服有关', line: '都和衣服有关' },
  石: { note: '和石头有关', line: '多和石头、硬东西有关' },
  王: { note: '和玉石有关', line: '大多和玉石、宝贝有关' },
  彳: { note: '和走路有关', line: '多和走路、道路有关' },
  辶: { note: '和走路有关', line: '都和走、和路上的事有关' },
  门: { note: '和门有关', line: '都和门有关' },
  贝: { note: '和钱财有关', line: '古时候贝壳当钱用，所以多和钱财有关' },
  页: { note: '和头有关', line: '本来画的是人头，所以多和脑袋有关' },
  刂: { note: '和刀有关', line: '都和刀、和切开有关' },
  攵: { note: '是手上的动作', line: '本来画的是手拿棍子，多和做事、管教有关' },
  '⺮': { note: '和竹子有关', line: '都是竹子做的东西' },
  穴: { note: '和洞、屋子有关', line: '多和洞、和住的地方有关' },
  疒: { note: '和生病有关', line: '都和生病、不舒服有关' },
  广: { note: '和房子有关', line: '多和房子、大屋子有关' },
  尸: { note: '和身体有关', line: '本来画的是侧身坐着的人' },
  舟: { note: '和船有关', line: '都和船有关' },
  马: { note: '和马有关', line: '都和马有关' },
  力: { note: '和力气有关', line: '都和使劲、出力有关' },
  心: { note: '和心情有关', line: '多半和心情、想法有关' },
  竹: { note: '和竹子有关', line: '都是竹子做的东西' },
  鱼: { note: '是一种鱼', line: '都和鱼有关' },
  金: { note: '和金属有关', line: '都是金属做的东西' },
  阝: { note: '和地方有关', line: '多和土坡、城镇这些地方有关' },
  巾: { note: '和布有关', line: '多是布做的东西' },
  田: { note: '和田地有关', line: '多和田地、种地有关' },
  礻: { note: '和求福有关', line: '古人写它是为了拜神求福，所以多和福气、祭祀有关' },
  见: { note: '和看有关', line: '都和看、和眼睛有关' },
  欠: { note: '和张嘴出气有关', line: '本来画的是人张着嘴出气，多和出声、想要有关' },
  走: { note: '和走跑有关', line: '都和走、和跑有关' },
  立: { note: '和站有关', line: '多和站着、立起来有关' },
  冫: { note: '和冰、冷有关', line: '两点是冰碴，都和冷有关' },
  牛: { note: '和牛有关', line: '多和牛、和牲口有关' },
  子: { note: '和孩子有关', line: '多和小孩、和家里的孩子有关' },
  弓: { note: '和弓箭有关', line: '都和弓、和箭有关' },
  灬: { note: '和火有关', line: '四个点是火苗，都和火、和热有关' },
  皿: { note: '和碗盘有关', line: '都是碗、盘、盆这类装东西的家什' },
  耳: { note: '和耳朵有关', line: '都和耳朵、和听有关' },
  羊: { note: '和羊有关', line: '多和羊有关' },
  酉: { note: '和酒有关', line: '「酉」是个酒坛子，这些字多和酒、和发酵有关' },
  身: { note: '和身体有关', line: '都和身子有关' },
  斤: { note: '和斧头有关', line: '「斤」本来画的是斧子，多和砍、和劈有关' },
  户: { note: '和门有关', line: '「户」是单扇门，这些字多和门窗有关' }
}

/* ---------------------------------------------------------------- 拼音工具 */

/** 去掉声调符号，只留音节：比较「声旁和这个字读得像不像」用。 */
function bareSyllable(pinyin) {
  return pinyin
    .normalize('NFD')
    .replace(/[\u0304\u0301\u030c\u0300]/g, '')
    .normalize('NFC')
}

/* ------------------------------------------------------------------ 种子解析 */

/**
 * 每行一个字，用 | 分段，第一段是六书归类：
 *
 *   xing|妹|未|wèi
 *     形声。只写声旁和声旁的读音，其余全部派生。
 *
 *   xing|洞|同|tóng|水冲穿了一个窟窿，所以带「氵」；后来凡是凹进去通得过的口都叫洞。
 *     形声 + 「本来是什么」的手写覆盖。形旁模板讲的是这一类字的共性，
 *     可有些字的今义早就跑出了那个共性（洞不再说水、汽被汽车借走、艺不再指种地）。
 *     这时候套模板会当着孩子的面自相矛盾：「凹进去的一个口。带「氵」的字都和水有关。」
 *     第五段就是给这种字留的——只覆盖 origin，形旁、声旁、读音仍然全部派生。
 *
 *   hui|泪|氵=水+目=眼睛|眼睛里淌出来的水，就是眼泪。|「氵」加「目」，一看就知道在哭。
 *     会意。零件用 + 分开、每个零件写「字形=这个零件在说什么」，
 *     后面两段分别是「本来是什么」和「怎么变的」。
 */
function parseSeed(text) {
  const rows = []
  text.split('\n').forEach((raw, i) => {
    const line = raw.trim()
    if (!line || line.startsWith('#')) return
    const at = i + 1
    const f = line.split('|')
    const kind = f[0]

    if (kind === 'xing') {
      if (f.length !== 4 && f.length !== 5) {
        throw new Error(`第 ${at} 行形声应有 4 段（可选第 5 段覆盖「本来是什么」），实际 ${f.length}`)
      }
      if (f.length === 5 && !f[4].trim()) throw new Error(`第 ${at} 行第 5 段是空的`)
      rows.push({ at, kind, char: f[1], phonetic: f[2], phoneticPinyin: f[3], origin: f[4] })
      return
    }
    if (kind === 'hui') {
      if (f.length !== 5) throw new Error(`第 ${at} 行会意应有 5 段，实际 ${f.length}`)
      const parts = f[2].split('+').map((p) => {
        const [g, m] = p.split('=')
        if (!g || !m) throw new Error(`第 ${at} 行零件「${p}」应写成 字形=说明`)
        return { g, m }
      })
      if (parts.length < 2) throw new Error(`第 ${at} 行会意至少要两个零件`)
      rows.push({ at, kind, char: f[1], parts, origin: f[3], evolve: f[4] })
      return
    }
    throw new Error(`第 ${at} 行不认识的类别「${kind}」`)
  })
  return rows
}

/* -------------------------------------------------------------------- 派生 */

const full = new Map((await loadAllCharacters()).map((c) => [c.char, c]))
const seed = parseSeed(fs.readFileSync(seedFile, 'utf8'))
const taken = new Set(HANDWRITTEN.map((e) => e.c))

const problems = []
const derived = []

for (const row of seed) {
  const light = CHARACTER_MAP.get(row.char)
  if (!light) {
    problems.push(`第 ${row.at} 行「${row.char}」不在字表里`)
    continue
  }
  if (taken.has(row.char)) {
    problems.push(`第 ${row.at} 行「${row.char}」和手写语料重复`)
    continue
  }
  taken.add(row.char)

  if (row.kind === 'hui') {
    derived.push({ c: row.char, kind: 'hui', origin: row.origin, evolve: row.evolve, parts: row.parts })
    continue
  }

  const glyph = getRadical(light.radical)?.glyph
  const sense = SEMANTIC[glyph]
  if (!sense) {
    problems.push(`第 ${row.at} 行「${row.char}」的形旁「${glyph ?? light.radical}」还没写进 SEMANTIC 表`)
    continue
  }

  const meaning = full.get(row.char)?.meaning
  if (!meaning) {
    problems.push(`第 ${row.at} 行「${row.char}」在单元详情包里没有释义`)
    continue
  }

  const cp = light.pinyin
  const pp = row.phoneticPinyin
  const same = bareSyllable(pp) === bareSyllable(cp)

  derived.push({
    c: row.char,
    kind: 'xing',
    origin: row.origin ?? `${meaning}带「${glyph}」的字，${sense.line}。`,
    evolve: same
      ? `「${glyph}」管意思，「${row.phonetic}」管读音，念 ${cp}。`
      : `「${glyph}」管意思，「${row.phonetic}」管读音——「${row.phonetic}」本身念 ${pp}，到了这个字里念 ${cp}。`,
    parts: [
      { g: glyph, m: sense.note },
      { g: row.phonetic, m: same ? `读音 ${pp}` : `读音 ${pp} → ${cp}` }
    ]
  })
}

if (problems.length) {
  console.error('[etymology] 种子有问题，没有生成任何文件：')
  problems.forEach((p) => console.error(`  ${p}`))
  process.exit(1)
}

/* -------------------------------------------------------------------- 落盘 */

const q = (s) => `'${s.replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'`
const entryLines = derived.map(
  (e) =>
    `  {\n` +
    `    c: ${q(e.c)},\n` +
    `    kind: ${q(e.kind)},\n` +
    `    origin: ${q(e.origin)},\n` +
    `    evolve: ${q(e.evolve)},\n` +
    `    parts: [\n` +
    e.parts.map((p) => `      { g: ${q(p.g)}, m: ${q(p.m)} }`).join(',\n') +
    `\n    ]\n` +
    `  }`
)

fs.writeFileSync(
  derivedOut,
  `/**
 * 派生出来的字源条目 —— 形声字的三个空由模板填，会意字的两句话来自种子。
 *
 * 真源是 scripts/data/etymology-seed.txt，本文件由 scripts/gen-etymology.mjs
 * 生成，请勿手改。字段含义见 etymology.js 顶部那段说明。
 */

export const DERIVED = [
${entryLines.join(',\n')}
]
`
)

const chars = [...HANDWRITTEN.map((e) => e.c), ...derived.map((e) => e.c)]
const CHUNK = 40
const packed = []
for (let i = 0; i < chars.length; i += CHUNK) {
  packed.push(`  '${chars.slice(i, i + CHUNK).join('')}'`)
}

fs.writeFileSync(
  indexOut,
  `/**
 * 字源语料的「轻」索引。
 *
 * 单字页要判断「这个字有没有字源可看」，才决定要不要显示那个入口按钮。
 * 为这一句判断把整份 etymology.js 拉进单字页的分块不值当——真正的语料
 * 连同 GSAP 演变动画一起，等孩子点了按钮再 import()。
 *
 * 这里只留一串汉字，顺序和 etymology.js 一致。本文件由
 * scripts/gen-etymology.mjs 生成，请勿手改；\`npm run check:data\` 会核对
 * 两边不会走散。
 */

/** 有字源动画的字，按 etymology.js 里的顺序排。 */
export const ETYMOLOGY_CHARS = [
${packed.join(' +\n')}
].join('')

const CHAR_SET = new Set(ETYMOLOGY_CHARS)

export const TOTAL_ETYMOLOGY = ETYMOLOGY_CHARS.length

/** 这个字有没有字源动画可看。 */
export function hasEtymology(char) {
  return CHAR_SET.has(char)
}
`
)

const byKind = derived.reduce((acc, e) => ({ ...acc, [e.kind]: (acc[e.kind] ?? 0) + 1 }), {})
const overrides = seed.filter((row) => row.kind === 'xing' && row.origin).length
console.log(
  `[etymology] 派生 ${derived.length} 个字（${Object.entries(byKind)
    .map(([k, n]) => `${k} ${n}`)
    .join(' / ')}），` + `连同手写的 ${HANDWRITTEN.length} 个，共 ${chars.length} 个字有字源演变。`
)
console.log(`[etymology] 其中 ${overrides} 个形声字手写覆盖了「本来是什么」，其余全部套模板。`)
