#!/usr/bin/env node
/**
 * 「玩」引擎自测（ROUND15_H2）。
 *
 * 一句话门槛：**全库 1820 个字，getCharPlay() 不许有一个玩不成的。**
 * 「玩不成」不只是返回 null，道具缺一件（找一找没有目标、拼一拼没有正确项、
 * 接一接的落物里一个都接不到）同样算，因为孩子会卡在一张点不动的卡片上。
 *
 * 所以这里逐模板校验道具，而不是只数 template 字段有没有值：
 * 探针能被一行 `return { template: 'x' }` 骗过去，孩子不能。
 *
 *   node scripts/test-char-play.mjs          全库
 *   node scripts/test-char-play.mjs --sample=50   抽样（本地快跑）
 */

import { CHAR_INDEX } from '../src/data/char-index.js'
import {
  PLAY_TEMPLATE_IDS,
  countRichPlays,
  findPlayHoles,
  getCharPlay
} from '../src/data/char-play.js'

const sampleArg = process.argv.find((a) => a.startsWith('--sample='))
const sampleSize = sampleArg ? Number(sampleArg.split('=')[1]) : 0

const failures = []
const fail = (msg) => failures.push(msg)

const chars = CHAR_INDEX.map((c) => c.char)
const targets = sampleSize
  ? chars.filter((_, i) => i % Math.max(1, Math.ceil(chars.length / sampleSize)) === 0)
  : chars

/** 每个模板「玩得成」的最低道具要求。 */
const VALIDATORS = {
  'tap-reveal'(p) {
    const items = p.props?.items
    if (!Array.isArray(items) || items.length < 2) return '盖子少于 2 个'
    if (items.some((i) => !i?.id || !i?.emoji || !i?.label)) return '盖子缺 id / 图标 / 说明'
    if (new Set(items.map((i) => i.id)).size !== items.length) return '盖子 id 重复'
    return null
  },
  'morph-story'(p) {
    const frames = p.props?.frames
    if (!Array.isArray(frames) || frames.length < 2) return '帧少于 2'
    if (frames.some((f) => !f?.caption)) return '帧缺配文'
    if (!frames[frames.length - 1]?.glyph) return '最后一帧不是字'
    return null
  },
  'emoji-hunt'(p) {
    const { cells, need, target } = p.props ?? {}
    if (!target) return '没有要找的目标'
    if (!Array.isArray(cells) || cells.length < 4) return '格子少于 4 个'
    if (cells.filter((c) => c.hit).length < need) return `可找到的目标少于 ${need} 个`
    return null
  },
  'drag-parts'(p) {
    const { options, whole, answer } = p.props ?? {}
    if (!whole || !answer) return '缺整字或答案偏旁'
    if (!Array.isArray(options) || options.length < 2) return '选项少于 2 个'
    const right = options.filter((o) => o.correct)
    if (right.length !== 1) return `正确选项 ${right.length} 个（应为 1）`
    if (right[0].glyph !== answer) return '正确选项与答案对不上'
    if (options.some((o) => !o.glyph || !o.name)) return '选项缺字形或名字'
    return null
  },
  'rain-catch'(p) {
    const { drops, need, staticCells } = p.props ?? {}
    if (!Array.isArray(drops) || drops.filter((d) => d.hit).length < need) {
      return `能接住的落物少于 ${need} 个`
    }
    if (drops.some((d) => typeof d.x !== 'number' || typeof d.duration !== 'number')) {
      return '落物缺落点或时长'
    }
    // 减少动态时舞台不下雨，改用这批静止道具；缺了那一档就没得玩
    if (!Array.isArray(staticCells) || staticCells.filter((c) => c.hit).length < need) {
      return '减少动态的静止道具不够'
    }
    return null
  }
}

/* ---------------------------------------------------- 1. 全库零空洞 */

const holes = findPlayHoles(targets)
if (holes.length) fail(`findPlayHoles 报告 ${holes.length} 个空洞：${holes.slice(0, 8).join('')}…`)

const templateCount = new Map()
let fallbackCount = 0

for (const char of targets) {
  const play = getCharPlay(char)
  if (!play) {
    fail(`「${char}」getCharPlay 返回空`)
    continue
  }
  if (!PLAY_TEMPLATE_IDS.includes(play.template)) {
    fail(`「${char}」模板 ${play.template} 舞台不认识`)
    continue
  }
  if (!play.narration || play.narration.length < 4) fail(`「${char}」旁白太短`)
  if (!play.theme || !play.accent) fail(`「${char}」缺主题或配色`)
  const flaw = VALIDATORS[play.template](play)
  if (flaw) fail(`「${char}」${play.template}：${flaw}`)
  templateCount.set(play.template, (templateCount.get(play.template) ?? 0) + 1)
  if (play.templateFallback) fallbackCount += 1
}

/* ---------------------------------------------------- 2. 模板不能只剩一种 */

if (templateCount.size < 4) {
  fail(`只用到 ${templateCount.size} 种模板（要求 ≥ 4），全库会长成同一张脸`)
}

/* ---------------------------------------------------- 3. 同一个字每次一样 */

for (const char of ['日', '森', '龘', '妈'].concat(targets.slice(0, 12))) {
  const a = JSON.stringify(getCharPlay(char))
  const b = JSON.stringify(getCharPlay(char))
  if (a !== b) fail(`「${char}」两次取到的关卡不一样（补齐必须是纯函数）`)
}

/* ---------------------------------------------------- 4. 字表外的字也能玩 */

for (const odd of ['龘', '𠀋', 'A', '7', '汉字', ' ', '', null, undefined]) {
  const play = getCharPlay(odd)
  if (!play?.template) {
    fail(`字表外输入 ${JSON.stringify(odd)} 没拿到玩法`)
    continue
  }
  const flaw = VALIDATORS[play.template]?.(play)
  if (flaw) fail(`字表外输入 ${JSON.stringify(odd)} 的 ${play.template}：${flaw}`)
}

/* ---------------------------------------------------- 5. 富脚本确实压过模板 */

const rich = countRichPlays()
if (rich < 1) fail('一条富脚本都没有：char-play-rich.js 没被收进注册表')
const richSample = getCharPlay('日')
if (richSample.templateFallback !== false) fail('「日」有富脚本却仍标成模板补齐')

/* ---------------------------------------------------- 报告 */

const spread = [...templateCount.entries()]
  .sort((a, b) => b[1] - a[1])
  .map(([id, n]) => `${id} ${n}`)
  .join(' / ')

console.log(`char-play 自测：${targets.length} 字，模板分布 ${spread}`)
console.log(`富脚本 ${rich} 条，模板补齐 ${fallbackCount} 字，空洞 ${holes.length}`)

if (failures.length) {
  console.error(`\n✗ ${failures.length} 处不合格：`)
  for (const line of failures.slice(0, 20)) console.error(`  - ${line}`)
  if (failures.length > 20) console.error(`  …还有 ${failures.length - 20} 条`)
  process.exit(1)
}

console.log('✓ 全库每个字都有玩得完的场景')
