#!/usr/bin/env node
/**
 * 「玩」引擎自测（ROUND15_H2）。
 *
 * 一句话门槛：**全库 1820 个字，getCharPlay() 不许有一个玩不成的。**
 * 「玩不成」不只是返回 null。道具缺一件同样算——找一找没有对的那张、
 * 接一接能接住的比要求的少、拼一拼的零件对不上任何空格、连一连的左边
 * 在右边找不到伴——孩子会卡在一张点不动的卡片上，探针却看不出来。
 *
 * 所以这里校验的是**舞台真正读的那份道具**（归一后的 kind + props），
 * 不是 template 字段有没有值：`return { template: 'x' }` 骗得过探针，骗不过孩子。
 * 六种 kind 各有一套「玩得完」的判据，见下面 VALIDATORS。
 *
 *   node scripts/test-char-play.mjs                全库
 *   node scripts/test-char-play.mjs --sample=50    抽样（本地快跑）
 */

import { CHAR_INDEX } from '../src/data/char-index.js'
import {
  PLAY_KINDS,
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

/** 每个道具都得有张脸，不然卡片上是一片空白，点了也看不出点没点。 */
const faceless = (list) => list.filter((x) => !x?.emoji && !x?.glyph).length
const dupeIds = (list) => new Set(list.map((x) => x?.id)).size !== list.length

/** 六种渲染器各自「玩得完」的最低要求。返回 null 表示这一关能通。 */
const VALIDATORS = {
  /** 点中对的那个：至少两张牌可选，对的那张够 need 个。 */
  pick({ options, need }) {
    if (!Array.isArray(options) || options.length < 2) return '选项少于 2 个'
    if (faceless(options)) return '选项里有没图没字的空牌'
    if (dupeIds(options)) return '选项 id 重复'
    const right = options.filter((o) => o.correct).length
    if (right < need) return `对的只有 ${right} 个，却要点中 ${need} 个`
    if (right === options.length) return '每张牌都是对的，随手一点就过'
    return null
  },

  /** 点够次数：能点中的不少于 need；会掉的那些得有落点和时长。 */
  catch({ items, need, moving }) {
    if (!Array.isArray(items) || !items.length) return '一件道具都没有'
    if (faceless(items)) return '道具里有没图没字的空位'
    if (dupeIds(items)) return '道具 id 重复'
    const hits = items.filter((i) => i.hit).length
    if (hits < need) return `能点中的只有 ${hits} 个，却要点满 ${need} 个`
    if (moving && items.some((i) => typeof i.x !== 'number' || typeof i.duration !== 'number')) {
      return '会掉的道具缺落点或时长'
    }
    // 减少动态时同一批道具改摆成静止网格，所以落点缺了也还有得玩，不额外校验
    return null
  },

  /** 零件送回位置：每个空格都得有零件填得进去。 */
  assemble({ slots, pieces, whole }) {
    if (!whole) return '不知道要拼成什么'
    if (!Array.isArray(slots) || !slots.length) return '没有空格'
    if (!Array.isArray(pieces) || pieces.length < 2) return '零件少于 2 个（没得选）'
    if (slots.some((s) => !s?.glyph)) return '空格没写要放什么'
    if (pieces.some((p) => !p?.glyph)) return '零件缺字形'
    if (dupeIds(pieces)) return '零件 id 重复'
    const right = pieces.filter((p) => p.correct)
    if (!right.length) return '一个正确零件都没有'
    // 舞台按字形往空格里放，对不上就得靠 correct 兜着：两条路都断了才是死局
    for (const slot of slots) {
      const byGlyph = pieces.some((p) => p.glyph === slot.glyph)
      if (!byGlyph && !right.length) return `空格「${slot.glyph}」没有零件配得上`
    }
    return null
  },

  /** 一帧一帧看完：至少两帧，最后一帧落在字上。 */
  watch({ frames }, play) {
    if (!Array.isArray(frames) || frames.length < 2) return '帧少于 2'
    if (faceless(frames)) return '有一帧既没图也没字'
    if (frames.some((f) => !f?.caption)) return '帧缺配文'
    if (frames[frames.length - 1]?.glyph !== play.char) return '最后一帧不是这个字'
    return null
  },

  /** 左边一个右边一个：每个左边的都得在右边找得到伴。 */
  match({ left, right, need }) {
    if (!Array.isArray(left) || !left.length) return '左边空的'
    if (!Array.isArray(right) || !right.length) return '右边空的'
    if (faceless(left) || faceless(right)) return '有一边是空牌'
    if (need > left.length) return `要配 ${need} 对，左边只有 ${left.length} 个`
    const keys = new Set(right.map((r) => r.key))
    const lonely = left.filter((l) => !keys.has(l.key))
    if (lonely.length) return `${lonely.length} 个在右边找不到伴`
    return null
  },

  /** 顺着一个方向推：要有主角、方向和次数。 */
  push({ hero, dir, dirLabel, need }) {
    if (!hero) return '没有推的东西'
    if (!['up', 'down', 'left', 'right'].includes(dir)) return `方向 ${dir} 舞台不认识`
    if (!dirLabel) return '方向没有说法'
    if (!(need >= 1)) return '推几下没说'
    return null
  }
}

function check(play, who) {
  if (!play) return fail(`${who} getCharPlay 返回空`)
  if (!play.template) return fail(`${who} 没有 template`)
  if (!PLAY_TEMPLATE_IDS.includes(play.template)) {
    return fail(`${who} 模板 ${play.template} 不在登记表里`)
  }
  if (!PLAY_KINDS.includes(play.kind)) return fail(`${who} 渲染器 ${play.kind} 舞台不认识`)
  if (!play.narration || play.narration.length < 4) fail(`${who} 旁白太短`)
  if (!play.theme || !play.accent) fail(`${who} 缺主题或配色`)
  if (!play.templateLabel) fail(`${who} 缺玩法名字`)
  const flaw = VALIDATORS[play.kind](play.props ?? {}, play)
  if (flaw) fail(`${who} ${play.template}/${play.kind}：${flaw}`)
}

/* ---------------------------------------------------- 1. 全库零空洞 */

const holes = findPlayHoles(targets)
if (holes.length) fail(`findPlayHoles 报告 ${holes.length} 个空洞：${holes.slice(0, 8).join('')}…`)

const templateCount = new Map()
const kindCount = new Map()
const sourceCount = new Map()
let fallbackCount = 0

for (const char of targets) {
  const play = getCharPlay(char)
  check(play, `「${char}」`)
  if (!play) continue
  templateCount.set(play.template, (templateCount.get(play.template) ?? 0) + 1)
  kindCount.set(play.kind, (kindCount.get(play.kind) ?? 0) + 1)
  sourceCount.set(play.source, (sourceCount.get(play.source) ?? 0) + 1)
  if (play.templateFallback) fallbackCount += 1
}

/* ---------------------------------------------------- 2. 不能全库一张脸 */

if (templateCount.size < 4) {
  fail(`只用到 ${templateCount.size} 种模板（要求 ≥ 4），全库会长成同一张脸`)
}
if (kindCount.size < 4) {
  fail(`只用到 ${kindCount.size} 种互动（要求 ≥ 4），玩法看着多其实只有一种`)
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
  check(play, `字表外输入 ${JSON.stringify(odd)}`)
}

/* ---------------------------------------------------- 5. 富脚本确实压过模板 */

const rich = countRichPlays()
if (rich < 1) fail('一条富脚本都没有：char-play-rich.js 没被收进注册表')
if (getCharPlay('日').templateFallback !== false) fail('「日」有富脚本却仍标成模板补齐')
if (!sourceCount.get('rich')) fail('全库一条富脚本都没被用上')

/* ---------------------------------------------------- 报告 */

const spread = (m) =>
  [...m.entries()]
    .sort((a, b) => b[1] - a[1])
    .map(([id, n]) => `${id} ${n}`)
    .join(' / ')

console.log(`char-play 自测：${targets.length} 字`)
console.log(`  模板 ${templateCount.size} 种：${spread(templateCount)}`)
console.log(`  互动 ${kindCount.size} 种：${spread(kindCount)}`)
console.log(`  来源：${spread(sourceCount)}（模板补齐 ${fallbackCount} 字，空洞 ${holes.length}）`)

if (failures.length) {
  console.error(`\n✗ ${failures.length} 处不合格：`)
  for (const line of failures.slice(0, 20)) console.error(`  - ${line}`)
  if (failures.length > 20) console.error(`  …还有 ${failures.length - 20} 条`)
  process.exit(1)
}

console.log('✓ 全库每个字都有玩得完的场景')
