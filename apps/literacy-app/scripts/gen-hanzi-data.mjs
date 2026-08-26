/**
 * 从 hanzi-writer-data（devDependency）中裁剪出本应用真正会用到的汉字笔顺数据，
 * 输出到 public/hanzi-data/ 。
 *
 * 为什么不直接用 hanzi-writer 默认的 CDN 加载？
 *   1. 本应用要求完全离线可用；
 *   2. 完整数据包有 9500+ 个字（几十 MB），全量打进 dist 不现实。
 * 裁剪之后只有一百多个字，几百 KB，随包发布即可。
 *
 * 文件名用码位（u82b1.json）而不是汉字本身，避免不同文件系统 / zip 工具
 * 处理非 ASCII 文件名时出现编码问题。
 *
 * 用法：node scripts/gen-hanzi-data.mjs
 * 已挂在 package.json 的 prebuild / predev 钩子上，无需手动执行。
 */

import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'
import fs from 'node:fs'
import path from 'node:path'

import { CHARACTERS } from '../src/data/characters.js'
import { RADICALS } from '../src/data/radicals.js'
import { IDIOMS } from '../src/data/idioms.js'

const require = createRequire(import.meta.url)
const here = path.dirname(fileURLToPath(import.meta.url))
const appDir = path.resolve(here, '..')
const outDir = path.join(appDir, 'public', 'hanzi-data')

/** 收集全部需要笔顺数据的汉字。 */
function collectChars() {
  const set = new Set()
  for (const c of CHARACTERS) set.add(c.char)
  for (const r of RADICALS) {
    for (const c of r.chars ?? []) set.add(c)
    for (const c of r.more ?? []) set.add(c)
    // 部首字形本身有时也是独体字（口、木、日…），能取到就一起收进来
    if (r.glyph) set.add(r.glyph)
    if (r.from) set.add(r.from)
  }
  for (const idiom of IDIOMS) {
    for (const ch of idiom.word) set.add(ch)
    for (const item of idiom.chars ?? []) set.add(item.c)
  }
  return [...set].filter((ch) => /\p{Script=Han}/u.test(ch)).sort()
}

function resolveDataDir() {
  try {
    return path.dirname(require.resolve('hanzi-writer-data/package.json'))
  } catch {
    return null
  }
}

function main() {
  const chars = collectChars()
  const dataDir = resolveDataDir()

  if (!dataDir) {
    console.warn(
      '[hanzi-data] 未找到 hanzi-writer-data，跳过离线数据生成。\n' +
        '            运行时会自动回退到 CDN，但将无法离线使用笔顺动画。'
    )
    return
  }

  fs.rmSync(outDir, { recursive: true, force: true })
  fs.mkdirSync(outDir, { recursive: true })

  const written = []
  const missing = []
  let bytes = 0

  for (const ch of chars) {
    const src = path.join(dataDir, `${ch}.json`)
    if (!fs.existsSync(src)) {
      missing.push(ch)
      continue
    }
    // 只保留 hanzi-writer 需要的两个字段，丢掉可能存在的冗余键。
    const raw = JSON.parse(fs.readFileSync(src, 'utf8'))
    const slim = JSON.stringify({ strokes: raw.strokes, medians: raw.medians })
    const name = `u${ch.codePointAt(0).toString(16)}.json`
    fs.writeFileSync(path.join(outDir, name), slim)
    written.push(ch)
    bytes += Buffer.byteLength(slim)
  }

  // 索引文件让运行时可以先判断「本地有没有」，避免无谓的 404。
  // 刻意不写生成时间：这些文件是入库的，带时间戳会让每次构建都把工作区弄脏。
  fs.writeFileSync(path.join(outDir, 'index.json'), JSON.stringify({ chars: written }))

  const kb = (bytes / 1024).toFixed(0)
  console.log(`[hanzi-data] 已生成 ${written.length} 个字的离线笔顺数据（约 ${kb} KB）。`)
  if (missing.length) {
    console.warn(`[hanzi-data] 数据包中缺失 ${missing.length} 个字：${missing.join(' ')}`)
  }
}

main()
