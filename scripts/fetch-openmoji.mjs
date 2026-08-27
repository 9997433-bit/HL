#!/usr/bin/env node
/**
 * 从 OpenMoji 官方 npm 包拉取 color SVG，保存到 shared/assets/openmoji/。
 * 用法：node scripts/fetch-openmoji.mjs [--force]
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const OUT_DIR = path.join(ROOT, 'shared/assets/openmoji')
const OPENMOJI_VERSION = '15.1.0'
const BASE = `https://cdn.jsdelivr.net/npm/openmoji@${OPENMOJI_VERSION}/color/svg`

/** 语义文件名 → Unicode 码点（与界面 emoji 一一对应） */
const ICONS = {
  apple: '1F34E',
  target: '1F3AF',
  'open-book': '1F4D6',
  numbers: '1F522',
  abacus: '1F9EE',
  star: '2B50',
  house: '1F3E0',
  pencil: '1F4DD',
  ear: '1F442',
  lantern: '1F3EE',
  trophy: '1F3C6',
  rocket: '1F680',
  locked: '1F512',
  seedling: '1F331',
  sparkles: '2728',
  fire: '1F525',
  speaker: '1F50A',
  'light-bulb': '1F4A1',
  party: '1F389',
  headphones: '1F3A7',
  'world-map': '1F5FA',
  books: '1F4DA',
  family: '1F46A',
  'puzzle-piece': '1F9E9',
  globe: '1F30D',
  sun: '1F31E',
  'ringed-planet': '1FA90',
  satellite: '1F6F0',
  cyclone: '1F300',
  'performing-arts': '1F3AD',
  medal: '1F947',
  repeat: '1F501',
  'japanese-beginner': '1F238',
  'green-book': '1F4D7',
  microphone: '1F3A4',
  scroll: '1F4DC',
}

const force = process.argv.includes('--force')
fs.mkdirSync(OUT_DIR, { recursive: true })

let ok = 0
let skip = 0

for (const [name, codepoint] of Object.entries(ICONS)) {
  const dest = path.join(OUT_DIR, `${name}.svg`)
  if (!force && fs.existsSync(dest) && fs.statSync(dest).size > 100) {
    skip++
    continue
  }
  const url = `${BASE}/${codepoint.toUpperCase()}.svg`
  const res = await fetch(url)
  if (!res.ok) {
    console.error(`[openmoji] FAIL ${name} (${url}): HTTP ${res.status}`)
    process.exitCode = 1
    continue
  }
  const svg = await res.text()
  if (!svg.includes('<svg')) {
    console.error(`[openmoji] FAIL ${name}: not SVG`)
    process.exitCode = 1
    continue
  }
  fs.writeFileSync(dest, svg)
  ok++
  console.log(`[openmoji] ${name}.svg ← ${codepoint}`)
}

console.log(`[openmoji] done: ${ok} fetched, ${skip} skipped, ${Object.keys(ICONS).length} total`)
