#!/usr/bin/env node
/**
 * 无字源认步自测（ROUND16_H2）。
 *
 * 一句话门槛：**全库 1820 个字，走到「认一认」都不许只剩一行释义。**
 *
 * 有字源的字这一步是 EtymologyStage 自动播演变动画；没有字源语料的那一千来个字
 * 交给 data/intro-fallback.js 算出的三幕（部首 → 零件 → 组词）。舞台演什么全看
 * 这三幕，所以逐字扫的就是它：三幕齐不齐、每幕说的话够不够长、三幕会不会
 * 其实是同一句话换了个位置。
 *
 * 顺带守住两件容易走偏的事：
 *   1. 拆零件不许瞎认。我们没有可靠的拆字语料，只认得部首那一半，
 *      另一半必须留成问号——编一个部件名比不讲更糟。
 *   2. 部首就是它自己的字（牙、瓜、羽…）得反过来讲，
 *      不能对孩子说「「牙」的部首是「牙」」。
 *
 *   node scripts/test-intro-fallback.mjs                全库（含课文详情）
 *   node scripts/test-intro-fallback.mjs --sample=80    抽样（本地快跑）
 */

import { CHAR_INDEX } from '../src/data/char-index.js'
import { loadAllCharacters } from '../src/data/characters.js'
import { hasEtymology } from '../src/data/etymology-index.js'
import { INTRO_FALLBACK_SCENES, buildIntroFallback } from '../src/data/intro-fallback.js'
import { getRadical } from '../src/data/radicals.js'

const sampleArg = process.argv.find((a) => a.startsWith('--sample='))
const sampleSize = sampleArg ? Number(sampleArg.split('=')[1]) : 0

const failures = []
const fail = (msg) => failures.push(msg)

/** 一幕至少要说这么多字，不然「有三幕」只是把一行释义切成了三段。 */
const MIN_LINE = 8
/** 三幕加起来的讲解量下限：比原来那一行释义厚实得看得出来。 */
const MIN_TOTAL = 60

const all = await loadAllCharacters()
const detailed = new Map(all.map((c) => [c.char, c]))
const targets = sampleSize
  ? CHAR_INDEX.filter((_, i) => i % Math.max(1, Math.ceil(CHAR_INDEX.length / sampleSize)) === 0)
  : CHAR_INDEX

let noEty = 0
let withFamily = 0
let withWords = 0
let withSentence = 0
let selfRadical = 0
let thinnest = { char: '', total: Infinity }

for (const entry of targets) {
  const char = entry.char
  const who = `「${char}」`
  const item = detailed.get(char) ?? entry
  const { scenes } = buildIntroFallback(char, item)
  const bare = !hasEtymology(char)
  if (bare) noEty += 1

  const ids = scenes.map((s) => s.id)
  if (ids.join(',') !== INTRO_FALLBACK_SCENES.join(',')) {
    fail(`${who} 三幕不齐或顺序不对：${ids.join('→') || '空'}`)
    continue
  }

  let total = 0
  const said = new Set()
  for (const scene of scenes) {
    if (!scene.title) fail(`${who} ${scene.id} 幕没有标题`)
    if (!scene.line || scene.line.length < MIN_LINE) {
      fail(`${who} ${scene.id} 幕的旁白太短：「${scene.line ?? ''}」`)
    }
    if (!scene.note || scene.note.length < MIN_LINE) {
      fail(`${who} ${scene.id} 幕缺少补充说明：「${scene.note ?? ''}」`)
    }
    if (/undefined|null|NaN/.test(`${scene.line}${scene.note}`)) {
      fail(`${who} ${scene.id} 幕的话里漏了字段：「${scene.line} ${scene.note}」`)
    }
    if (said.has(scene.line)) fail(`${who} ${scene.id} 幕和别的幕说的是同一句话`)
    said.add(scene.line)
    total += scene.line.length + scene.note.length
  }
  if (total < MIN_TOTAL) {
    fail(`${who} 三幕加起来只有 ${total} 个字（要求 ≥ ${MIN_TOTAL}），还是太像一行释义`)
  }
  if (total < thinnest.total) thinnest = { char, total }

  const [radicalScene, partsScene, wordScene] = scenes
  const radical = getRadical(entry.radical)

  // 部首幕：讲法必须跟着「这个字本身是不是部首」走
  const isSelf = !radical || radical.glyph === char
  if (isSelf) {
    selfRadical += 1
    if (radicalScene.mode !== 'seed') fail(`${who} 本身就是部首，却仍按「它的部首是…」讲`)
    if (new RegExp(`「${char}」的部首是「${char}」`).test(radicalScene.line)) {
      fail(`${who} 对孩子说了「它的部首是它自己」`)
    }
  } else {
    if (radicalScene.mode !== 'split') fail(`${who} 有独立部首却按独体字讲`)
    if (!radicalScene.line.includes(radical.glyph)) {
      fail(`${who} 部首幕没有把部首「${radical.glyph}」说出来`)
    }
  }
  if (radicalScene.family.length) withFamily += 1
  if (radicalScene.family.includes(char)) fail(`${who} 一家子里把自己也算了进去`)

  // 零件幕：认得的那一半照实说，不认得的那一半留问号，绝不编部件名
  if (partsScene.mode === 'split') {
    const known = partsScene.pieces.filter((p) => p.known)
    const rest = partsScene.pieces.filter((p) => !p.known)
    if (known.length !== 1 || known[0].glyph !== radical.glyph) {
      fail(`${who} 零件幕认得的那一半不是部首`)
    }
    if (rest.length !== 1 || rest[0].glyph !== '？') {
      fail(`${who} 零件幕给不认得的那一半编了个名字：${rest.map((p) => p.glyph).join('')}`)
    }
  } else if (partsScene.pieces.length) {
    fail(`${who} 独体字不该摆出拆字算式`)
  }

  // 组词幕：课文包在手就必须用上，别让孩子看一句「读作 xx」
  const words = Array.isArray(item.words) ? item.words : []
  if (words.length) {
    withWords += 1
    if (wordScene.mode !== 'words') fail(`${who} 有组词却没进第三幕`)
    if (!wordScene.words.length) fail(`${who} 第三幕一个词都没摆出来`)
    for (const w of wordScene.words) {
      if (!w.w?.includes(char)) fail(`${who} 第三幕的词「${w.w}」里没有这个字`)
    }
  }
  if (item.sentence?.text) {
    withSentence += 1
    if (!wordScene.sentence) fail(`${who} 有例句却没摆进第三幕`)
  }

  // 同一个字每次讲的必须一样，不然孩子回头再看是另一套说法
  if (JSON.stringify(buildIntroFallback(char, item)) !== JSON.stringify({ char, scenes })) {
    fail(`${who} 两次算出来的三幕不一样（必须是纯函数）`)
  }
}

/* ------------------------------------------- 只有轻索引时也不许塌成一行 */

for (const char of ['牙', '我', '洗', '的', '瓜', '扯']) {
  const { scenes } = buildIntroFallback(char)
  if (scenes.length !== INTRO_FALLBACK_SCENES.length) {
    fail(`「${char}」课文包还没到就少了一幕（详情是异步加载的，这一步不能等）`)
  }
  if (scenes.some((s) => !s.line || s.line.length < MIN_LINE)) {
    fail(`「${char}」课文包还没到时有一幕没话说`)
  }
}

/* ---------------------------------------------------- 字表外的字也别炸 */

for (const odd of ['龘', '𠀋', 'A', '7']) {
  const { scenes } = buildIntroFallback(odd)
  if (scenes.length !== INTRO_FALLBACK_SCENES.length) fail(`字表外输入「${odd}」少了一幕`)
}

/* -------------------------------------------------------------- 报告 */

console.log(`无字源认步自测：${targets.length} 字（其中没有字源语料的 ${noEty} 字）`)
console.log(`  部首一家子 ${withFamily} 字 / 本身就是部首 ${selfRadical} 字`)
console.log(`  第三幕拿到组词 ${withWords} 字、例句 ${withSentence} 字`)
console.log(`  讲得最少的是「${thinnest.char}」，三幕共 ${thinnest.total} 字`)

if (failures.length) {
  console.error(`\n✗ ${failures.length} 处不合格：`)
  for (const line of failures.slice(0, 20)) console.error(`  - ${line}`)
  if (failures.length > 20) console.error(`  …还有 ${failures.length - 20} 条`)
  process.exit(1)
}

console.log('✓ 全库每个字走到「认一认」都有三幕可讲，没有只剩一行释义的字')
