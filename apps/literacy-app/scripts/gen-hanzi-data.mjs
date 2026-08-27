/**
 * 从 hanzi-writer-data（devDependency）中裁剪出本应用真正会用到的汉字笔顺数据，
 * 输出到 public/hanzi-data/ 。
 *
 * 为什么不直接用 hanzi-writer 默认的 CDN 加载？
 *   1. 本应用要求完全离线可用；
 *   2. 完整数据包有 9500+ 个字（几十 MB），全量打进 dist 不现实。
 * 裁剪之后是三百多个字、一两兆，随包发布即可。
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
import { BOOKS } from '../src/data/books.js'

const require = createRequire(import.meta.url)
const here = path.dirname(fileURLToPath(import.meta.url))
const appDir = path.resolve(here, '..')
const outDir = path.join(appDir, 'public', 'hanzi-data')
const baselineFile = path.resolve(appDir, '..', '..', 'shared', 'data', 'common-hanzi.json')

const isHan = (ch) => /\p{Script=Han}/u.test(ch)

/**
 * monorepo 共享字库。它是字表的事实基线，即使某个字暂时被移出课程单元，
 * 笔顺数据也照样带上，免得别的 App 引用同一份基线时缺字。
 */
function baselineChars() {
  try {
    const doc = JSON.parse(fs.readFileSync(baselineFile, 'utf8'))
    return (doc.characters ?? []).map((c) => c.character).filter(Boolean)
  } catch {
    return []
  }
}

/** 课程字表：这些字必须有离线笔顺数据，缺一个就算构建失败。 */
function requiredChars() {
  const set = new Set([...CHARACTERS.map((c) => c.char), ...baselineChars()])
  return [...set].filter(isHan).sort()
}

/**
 * 顺带收进来的字：部首讲解里的示例、成语拆解、绘本正文。
 * 缺了只是少一段动画，不阻断构建。
 */
function extraChars() {
  const set = new Set()
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
  // 绘本正文可以点字听音，点到的字最好也能看笔顺
  for (const b of BOOKS) {
    for (const page of b.pages ?? []) {
      for (const ch of page.text ?? '') set.add(ch)
    }
  }
  const required = new Set(requiredChars())
  return [...set].filter((ch) => isHan(ch) && !required.has(ch)).sort()
}

function resolveDataDir() {
  try {
    return path.dirname(require.resolve('hanzi-writer-data/package.json'))
  } catch {
    return null
  }
}

/**
 * 笔顺数据受 Arphic Public License 约束，再分发（含裁剪后的衍生数据）必须随附
 * 许可证全文，因此每次重建输出目录都要把 ARPHICPL.TXT 一起放进去。
 * 优先取上游包内的副本，包里缺失时退回仓库 shared/assets 的存档。
 */
function copyArphicLicense(dataDir) {
  const candidates = [
    path.join(dataDir, 'ARPHICPL.TXT'),
    path.resolve(appDir, '..', '..', 'shared', 'assets', 'hanzi-writer-data', 'ARPHICPL.TXT'),
  ]
  const src = candidates.find((p) => fs.existsSync(p))
  if (!src) {
    console.error('[hanzi-data] 找不到 ARPHICPL.TXT，笔顺数据不得在缺失许可证的情况下分发。')
    process.exitCode = 1
    return
  }
  fs.copyFileSync(src, path.join(outDir, 'ARPHICPL.TXT'))
}

function main() {
  const required = requiredChars()
  const extra = extraChars()
  const chars = [...required, ...extra].sort()
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

  copyArphicLicense(dataDir)

  const kb = (bytes / 1024).toFixed(0)
  console.log(
    `[hanzi-data] 已生成 ${written.length} 个字的离线笔顺数据（约 ${kb} KB）：` +
      `课程字 ${required.length} 个 + 部首/成语/绘本用字 ${extra.length} 个。`
  )

  // 课程字缺笔顺 = 学习页的核心环节直接残废，必须让构建红掉；
  // 其余来源缺字只是少一段动画，提示一下就好。
  const missingRequired = missing.filter((ch) => required.includes(ch))
  const missingExtra = missing.filter((ch) => !required.includes(ch))
  if (missingExtra.length) {
    console.warn(`[hanzi-data] 数据包中缺失 ${missingExtra.length} 个非课程字：${missingExtra.join(' ')}`)
  }
  if (missingRequired.length) {
    console.error(
      `[hanzi-data] 字表里有 ${missingRequired.length} 个字在 hanzi-writer-data 中找不到：` +
        `${missingRequired.join(' ')}\n` +
        '            请换字或补数据，否则这些字的「写一写」无法离线使用。'
    )
    process.exitCode = 1
  }
}

main()
