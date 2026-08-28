#!/usr/bin/env node
/**
 * 种子候选提案器 —— 「下一批该收哪些形声字」这个问题，也不该靠人翻字表。
 *
 * gen-etymology.mjs 负责把种子里的一行变成一条字源，但种子那一行本身
 * （「这个字的声旁是谁」）从哪来？靠人一个一个想，字表一千八百个字翻不完，
 * 也很难保证不漏。这里把这一步也算出来：
 *
 *   1. 从 CHISE/cjkvi 的 IDS 拆字数据里取这个字的部件树；
 *   2. 形旁按字表部首定（和生成器同一个口径），剩下的部件就是声旁候选；
 *   3. 声旁必须**本身也是字表里的字**——孩子不认得的偏旁（㐬、𢦏、巠…）
 *      拆开讲反而添乱，这也是种子文件一开始就定下的规矩；
 *   4. 拿声旁在字表里的读音和这个字比：同音、同韵、声母同组才留下，
 *      挡掉那些「部件对得上但根本不管读音」的会意字。
 *
 * 输出的是**候选**，不是成品：形声字的判定有例外，讲解还得和字义对得上
 * （「熊」的形旁是四点底，可它跟火没关系），所以最后一关仍然是人过一遍，
 * 挑剩下的才贴进 scripts/data/etymology-seed.txt。这个脚本不写任何数据文件。
 *
 * 用法：
 *   node scripts/propose-etymology-seed.mjs            # 打印候选种子行
 *   node scripts/propose-etymology-seed.mjs --rejects  # 顺带打印落选的字和原因
 *
 * IDS 数据（约 4 MB）首次运行时下载并缓存到 scripts/data/.cache/，之后离线可用。
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { CHARACTER_MAP, loadAllCharacters } from '../src/data/characters.js'
import { getRadical } from '../src/data/radicals.js'
import { HANDWRITTEN } from '../src/data/etymology.js'

const here = path.dirname(fileURLToPath(import.meta.url))
const seedFile = path.join(here, 'data', 'etymology-seed.txt')
const cacheDir = path.join(here, 'data', '.cache')
const idsFile = path.join(cacheDir, 'ids.txt')
const IDS_URL = 'https://raw.githubusercontent.com/cjkvi/cjkvi-ids/master/ids.txt'

const showRejects = process.argv.includes('--rejects')

/* --------------------------------------------------------------- IDS 数据 */

async function loadIds() {
  if (!fs.existsSync(idsFile)) {
    process.stderr.write(`[propose] 下载 IDS 拆字数据：${IDS_URL}\n`)
    const res = await fetch(IDS_URL)
    if (!res.ok) throw new Error(`IDS 下载失败：HTTP ${res.status}`)
    fs.mkdirSync(cacheDir, { recursive: true })
    fs.writeFileSync(idsFile, await res.text())
  }
  const map = new Map()
  for (const line of fs.readFileSync(idsFile, 'utf8').split('\n')) {
    if (!line || line.startsWith('#')) continue
    const [, char, ...forms] = line.split('\t')
    if (char?.length !== 1) continue
    const clean = forms.map((f) => f.replace(/\[[A-Z]+\]$/, '')).filter(Boolean)
    if (clean.length) map.set(char, clean)
  }
  return map
}

const IDC = /[\u2FF0-\u2FFB]/

/** 把一条 IDS 串解析成部件树，返回 [节点, 没吃完的串]。 */
function parseIds(s) {
  const head = [...s][0]
  if (!head) return [null, '']
  let rest = s.slice(head.length)
  if (IDC.test(head)) {
    const arity = head === '\u2FF2' || head === '\u2FF3' ? 3 : 2
    const kids = []
    for (let i = 0; i < arity; i++) {
      const [kid, tail] = parseIds(rest)
      kids.push(kid)
      rest = tail
    }
    return [{ kids }, rest]
  }
  return [{ leaf: head }, rest]
}

const flatten = (node) => (node.leaf ? node.leaf : node.kids.map(flatten).join(''))

/** 这个字能拆出来的所有部件（声旁有时藏在第二、第三层）。 */
function componentsOf(char, ids) {
  const out = new Set()
  for (const form of ids.get(char) ?? []) {
    if (form === char || !IDC.test(form)) continue
    const [tree] = parseIds(form)
    if (!tree?.kids) continue
    const walk = (node, depth) => {
      if (depth > 4) return
      out.add(flatten(node))
      node.kids?.forEach((kid) => walk(kid, depth + 1))
    }
    tree.kids.forEach((kid) => walk(kid, 1))
  }
  return [...out]
}

/* ------------------------------------------------------------ 读音像不像 */

const bare = (pinyin) =>
  pinyin
    .normalize('NFD')
    .replace(/[\u0304\u0301\u030c\u0300]/g, '')
    .normalize('NFC')
    .replace(/ü/g, 'v')

const INITIALS = [
  'zh', 'ch', 'sh', 'b', 'p', 'm', 'f', 'd', 't', 'n', 'l',
  'g', 'k', 'h', 'j', 'q', 'x', 'r', 'z', 'c', 's', 'y', 'w'
]
const cut = (syllable) => {
  const initial = INITIALS.find((i) => syllable.startsWith(i)) ?? ''
  return { initial, rime: syllable.slice(initial.length) }
}

/** 形声字里常见的声母通转（帮滂并、端透定、见溪群…）。 */
const ONSET_GROUPS = [
  ['b', 'p', 'm', 'f'],
  ['d', 't', 'n', 'l'],
  ['g', 'k', 'h'],
  ['j', 'q', 'x', 'y'],
  ['z', 'c', 's'],
  ['zh', 'ch', 'sh', 'r'],
  ['z', 'zh'], ['c', 'ch'], ['s', 'sh'],
  ['j', 'g'], ['q', 'k'], ['x', 'h'],
  ['y', ''], ['w', ''], ['w', 'h'], ['y', 'x'], ['y', 'j']
]
const onsetAlike = (a, b) => a === b || ONSET_GROUPS.some((g) => g.includes(a) && g.includes(b))

/** 韵母相近：一样，或只差一个介音 / 只差鼻音韵尾。 */
const rimeCore = (rime) => rime.replace(/^(i|u|v)(?=[aeo])/, '').replace(/ng$/, 'n')
const rimeAlike = (a, b) => a === b || rimeCore(a) === rimeCore(b)

/** 0 = 不像（不要），5 = 完全同音。 */
function soundScore(charPinyin, phoneticPinyin) {
  const a = bare(charPinyin)
  const b = bare(phoneticPinyin)
  if (a === b) return 5
  const x = cut(a)
  const y = cut(b)
  if (rimeAlike(x.rime, y.rime) && onsetAlike(x.initial, y.initial)) return 4
  if (x.rime === y.rime) return 3
  if (rimeAlike(x.rime, y.rime)) return 2
  return 0
}

/* ------------------------------------------------------------------ 提案 */

const ids = await loadIds()
const semantic = new Set(
  (() => {
    const src = fs.readFileSync(path.join(here, 'gen-etymology.mjs'), 'utf8')
    const start = src.indexOf('const SEMANTIC = {')
    const block = src.slice(start, src.indexOf('\n}', start))
    return [...block.matchAll(/^\s+'?(.)'?:\s*\{/gm)].map((m) => m[1])
  })()
)

const seedChars = fs
  .readFileSync(seedFile, 'utf8')
  .split('\n')
  .filter((line) => /^(xing|hui)\|/.test(line))
  .map((line) => line.split('|')[1])
const taken = new Set([...HANDWRITTEN.map((e) => e.c), ...seedChars])
const full = new Map((await loadAllCharacters()).map((c) => [c.char, c]))

const proposals = []
const rejects = []

for (const light of CHARACTER_MAP.values()) {
  if (taken.has(light.char)) continue
  const glyph = getRadical(light.radical)?.glyph
  if (!glyph || !semantic.has(glyph)) continue
  if (!full.get(light.char)?.meaning) continue

  const best = componentsOf(light.char, ids)
    .filter((part) => part.length === 1 && part !== light.char && part !== glyph)
    .map((part) => ({ part, entry: CHARACTER_MAP.get(part) }))
    .filter(({ entry }) => entry)
    .map(({ part, entry }) => ({ part, pinyin: entry.pinyin, score: soundScore(light.pinyin, entry.pinyin) }))
    .filter((c) => c.score >= 2)
    .sort((a, b) => b.score - a.score)[0]

  if (!best) {
    rejects.push(`${light.char}（${light.pinyin}，形旁 ${glyph}）：拆件 ${componentsOf(light.char, ids).join('/') || '无'}`)
    continue
  }
  proposals.push({ ...light, glyph, ...best })
}

const grouped = new Map()
for (const p of proposals) {
  const name = getRadical(p.radical).name
  if (!grouped.has(name)) grouped.set(name, [])
  grouped.get(name).push(p)
}

for (const [name, list] of [...grouped].sort((a, b) => b[1].length - a[1].length)) {
  console.log(`\n# ${'-'.repeat(64)} ${name}`)
  for (const p of list) {
    console.log(`xing|${p.char}|${p.part}|${p.pinyin}   # ${p.char} 念 ${CHARACTER_MAP.get(p.char).pinyin}，读音相似度 ${p.score}/5`)
  }
}

if (showRejects) {
  console.log(`\n# 落选 ${rejects.length} 个（多半是声旁不在字表，或者根本不是形声）：`)
  rejects.forEach((r) => console.log(`#   ${r}`))
}

console.error(
  `[propose] 字表 ${CHARACTER_MAP.size} 字，已收 ${taken.size} 字，` +
    `提出候选 ${proposals.length} 个（覆盖 ${grouped.size} 个形旁），落选 ${rejects.length} 个。`
)
