/**
 * 拍照识字的取字规则自检。
 *
 * OCR 那一半（wasm、语言包、识别精度）由 scripts/smoke.mjs 在真浏览器里跑；
 * 这里只守住它前后两段纯逻辑：识别文本里挑哪些字、哪些字讲得了。
 * 这两段一旦跑偏，孩子看到的就是一屏标点符号或者一堆没有释义的空卡片。
 *
 * 用法：node scripts/test-ocr.mjs
 */

import assert from 'node:assert/strict'
import { existsSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

import { CHARACTER_MAP } from '../src/data/characters.js'
import { extractHanzi, OCR_PACK, splitByLibrary } from '../src/utils/ocr.js'

const tests = []
const test = (name, fn) => tests.push({ name, fn })

test('标点、拼音、数字和空白都不算识别出来的字', () => {
  assert.deepEqual(extractHanzi('日  月，shān 水。123 ABC'), ['日', '月', '水'])
})

test('同一个字在照片里出现多次，只列一次，且保持出现顺序', () => {
  assert.deepEqual(extractHanzi('山 水 山 日 水'), ['山', '水', '日'])
})

test('识别成一片噪声时给出空结果，而不是抛错', () => {
  assert.deepEqual(extractHanzi(''), [])
  assert.deepEqual(extractHanzi(null), [])
  assert.deepEqual(extractHanzi('|||~~~ ...'), [])
})

test('一屏最多列 24 个字，整版书页不会把结果页刷爆', () => {
  const wall = Array.from({ length: 400 }, (_, i) => String.fromCodePoint(0x4e00 + i)).join('')
  assert.equal(extractHanzi(wall).length, 24)
  assert.equal(extractHanzi(wall, { limit: 6 }).length, 6)
})

test('字库里有的才进讲解区，其余如实归到「还没进字库」', () => {
  const { known, unknown } = splitByLibrary(['日', '月', '𠀀', '龘'])
  assert.deepEqual(known, ['日', '月'])
  assert.deepEqual(unknown, ['𠀀', '龘'])
})

test('讲解区里的每个字都查得到拼音，卡片不会是空的', () => {
  const { known } = splitByLibrary(extractHanzi('日月山水，天上人间。'))
  assert.ok(known.length >= 6, `示例句只匹配到 ${known.length} 个字`)
  for (const char of known) {
    assert.ok(CHARACTER_MAP.get(char)?.pinyin, `「${char}」在字库里没有拼音`)
  }
})

test('示例照片和语言包都在，点「试一张示例」不会 404', () => {
  const dir = new URL('../public/ocr/', import.meta.url)
  for (const file of [OCR_PACK.sample, 'chi_sim.traineddata.gz']) {
    const path = fileURLToPath(new URL(file, dir))
    assert.ok(existsSync(path), `public/ocr/${file} 不见了`)
    assert.ok(statSync(path).size > 1024, `public/ocr/${file} 是个空壳`)
  }
})

let failed = 0
for (const { name, fn } of tests) {
  try {
    await fn()
    console.log(`  ✓ ${name}`)
  } catch (err) {
    failed += 1
    console.log(`  ✗ ${name}\n      ${err.message}`)
  }
}
console.log(`\n拍照识字取字规则：${tests.length - failed} / ${tests.length} 通过。`)
process.exit(failed ? 1 : 0)
