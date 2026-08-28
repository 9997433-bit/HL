/**
 * 构建产物体检：字表长到 500 个字之后，最容易悄悄回归的就是
 * 「有人在主包里 import 了详情包」——一行 import 就能把 33 个单元的课文
 * 重新塞回首屏。这里在 dist 上直接验：
 *
 *   1. 每个单元都切出了自己的 chars-uN 块；
 *   2. 首屏同步加载的块里一个课文包都没有，字义也没被顺手打包进去；
 *   3. 入口块（含它同步依赖的块）的体积还在预算之内；
 *   4. 玩步的手写剧本也一单元一块（play-rich-uN，ROUND18_H3），
 *   5. 而且首屏和**单字详情**的同步闭包里都读不到剧本正文。
 *
 * 第 5 条按内容指纹判，不按文件名判：改个块名骗得过文件名，骗不过
 * 原文里那句旁白。拆包最怕的不是没拆，是拆完过两周被人一行静态 import 缝回去。
 *
 * 用法：npm run build && node scripts/check-bundle.mjs
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { UNITS } from '../src/data/characters.js'
import { RICH_PLAY_MANIFEST } from '../src/data/play-rich/index.js'

const here = path.dirname(fileURLToPath(import.meta.url))
const dist = path.resolve(here, '..', 'dist')
const assets = path.join(dist, 'assets')

/** 入口块加上它同步 import 的块，就是首屏必须下载的 JS。 */
const ENTRY_JS_BUDGET_KB = 420

const fails = []
const notes = []
const check = (ok, msg) => (ok ? notes.push(`✓ ${msg}`) : fails.push(`✗ ${msg}`))

if (!fs.existsSync(dist)) {
  console.error('先跑 npm run build')
  process.exit(1)
}

const html = fs.readFileSync(path.join(dist, 'index.html'), 'utf8')
const entryName = html.match(/src="\.?\/?(assets\/[^"]+\.js)"/)?.[1]
if (!entryName) {
  console.error('index.html 里找不到入口脚本')
  process.exit(1)
}

/** 顺着入口的静态 import 走一遍，动态 import() 出来的块不算首屏。 */
function collectSync(startFile) {
  const seen = new Set()
  const queue = [startFile]
  while (queue.length) {
    const file = queue.shift()
    if (seen.has(file)) continue
    seen.add(file)
    const code = fs.readFileSync(path.join(dist, file), 'utf8')
    for (const m of code.matchAll(/(?:^|[^.\w])(?:import|export)[^'"]*?from\s*["']\.\/([\w.-]+\.js)["']/g)) {
      queue.push(path.posix.join(path.posix.dirname(file), m[1]))
    }
  }
  return [...seen]
}

const entryFiles = collectSync(entryName)
const entryCode = entryFiles.map((f) => fs.readFileSync(path.join(dist, f), 'utf8')).join('\n')
const entryKb = entryFiles.reduce((n, f) => n + fs.statSync(path.join(dist, f)).size, 0) / 1024

const chunks = fs.readdirSync(assets)
const unitChunks = chunks.filter((f) => /^chars-u\d+-.*\.js$/.test(f))
check(
  unitChunks.length === UNITS.length,
  `每个单元都切出了自己的课文块（${unitChunks.length} / ${UNITS.length}）`
)

const syncPacks = entryFiles.filter((f) => /chars-u\d+-/.test(f))
check(
  syncPacks.length === 0,
  `首屏没有同步加载课文包${syncPacks.length ? `（${syncPacks.join('、')}）` : ''}`
)

// 短字义在成语/绘本里也可能撞车，用「字 + 字义 + 首组词拼音」的详情包指纹判断有没有被同步打包。
function unitFingerprint(pack) {
  const [char, entry] = Object.entries(pack)[0] ?? []
  const word = entry?.words?.[0]
  if (!char || !entry?.meaning || !word) return null
  return `${char}:{meaning:"${entry.meaning}",words:[{w:"${word.w}",p:"${word.p}"`
}

const leaked = []
for (const unit of UNITS) {
  const pack = await import(`../src/data/chars/${unit.id}.js`).then((m) => m.default)
  const fingerprint = unitFingerprint(pack)
  if (fingerprint && entryCode.includes(fingerprint)) leaked.push(unit.id)
}
check(
  leaked.length === 0,
  `首屏 JS 里没有夹带字义${leaked.length ? `（${leaked.join('、')}）` : ''}`
)

check(
  entryKb < ENTRY_JS_BUDGET_KB,
  `首屏 JS ${entryKb.toFixed(0)} KB（预算 ${ENTRY_JS_BUDGET_KB} KB，共 ${entryFiles.length} 个块）`
)

/* --------------------------------- 玩步手写剧本按单元拆包（ROUND18_H3） */

const playChunks = chunks.filter((f) => /^play-rich-u\d+-.*\.js$/.test(f))
check(
  playChunks.length === RICH_PLAY_MANIFEST.units.length,
  `每个单元的手写剧本都切出了自己的块（${playChunks.length} / ${RICH_PLAY_MANIFEST.units.length}）`
)

/**
 * 剧本正文有没有被同步拉进某条关键路径 —— 拿 u1 第一条的旁白当指纹。
 *
 * 一句二十来字的旁白只可能来自剧本本身，压缩器改不动它、改块名也躲不掉；
 * 反过来只数文件名的话，谁把分片 import 进详情块都看不出来。
 */
const richFingerprint = (
  await import('../src/data/play-rich/u1.js')
).UNIT_RICH_PLAYS?.[0]?.narration

const syncClosures = [['首屏', entryFiles]]
const charDetail = chunks.find((f) => /^CharDetailView-.*\.js$/.test(f))
if (charDetail) syncClosures.push(['单字详情', collectSync(path.posix.join('assets', charDetail))])
check(Boolean(charDetail), `dist 里找到单字详情块${charDetail ? `（${charDetail}）` : ''}`)

if (richFingerprint) {
  for (const [label, files] of syncClosures) {
    const dirty = files.filter((f) =>
      fs.readFileSync(path.join(dist, f), 'utf8').includes(richFingerprint)
    )
    check(
      dirty.length === 0,
      `${label}同步闭包里没有手写剧本正文${dirty.length ? `（${dirty.join('、')}）` : ''}`
    )
  }
} else {
  fails.push('✗ 取不到手写剧本指纹（play-rich/u1.js 空了？）')
}

notes.forEach((n) => console.log(' ', n))
fails.forEach((f) => console.log(' ', f))
console.log(`\n构建产物体检：${notes.length} 项通过，${fails.length} 项失败。`)
process.exit(fails.length ? 1 : 0)
