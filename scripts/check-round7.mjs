/**
 * Round 7 全面超越终验硬门槛。
 * 标准：.agent_workspace/ROUND7-ACCEPTANCE.md
 */

import fs from 'node:fs'
import path from 'node:path'
import { register } from 'node:module'
import { fileURLToPath } from 'node:url'

register('./alias-loader.mjs', import.meta.url)

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const fails = []
const notes = []

const check = (ok, msg) => (ok ? notes.push(`✓ ${msg}`) : fails.push(`✗ ${msg}`))
const read = (rel) => {
  try {
    return fs.readFileSync(path.join(root, rel), 'utf8')
  } catch {
    return ''
  }
}
const exists = (rel) => fs.existsSync(path.join(root, rel))

/* H1 拍照识字 */
const ocrRoute =
  /camera|ocr|photo/i.test(read('apps/literacy-app/src/router/index.js')) ||
  exists('apps/literacy-app/src/views/CameraOcrView.vue')
const ocrMod =
  exists('apps/literacy-app/src/utils/ocr.js') ||
  exists('apps/literacy-app/src/composables/useOcr.js') ||
  /tesseract/i.test(read('apps/literacy-app/package.json'))
check(
  ocrRoute && ocrMod,
  ocrRoute && ocrMod
    ? 'H1 拍照识字 pipeline 已接线'
    : 'H1 拍照识字未接线 —— 由 r7-literacy-ocr 交付'
)

/* H2 形近干扰 */
const listenSrc = read('apps/literacy-app/src/views/ListenGameView.vue')
const charDetailSrc = read('apps/literacy-app/src/views/CharDetailView.vue')
const similarDistractors =
  /similar|shapeLike|confusable|形近|NEIGHBORS|distractorPool/i.test(
    listenSrc + charDetailSrc + read('apps/literacy-app/src/data/similar-chars.js')
  ) && !/shuffle\(list\.filter/.test(listenSrc)
check(
  similarDistractors,
  similarDistractors
    ? 'H2 听音/测验形近干扰项已接线'
    : 'H2 形近干扰未接线 —— 由 r7-literacy-distractors 交付'
)

/* H3 字源动画 */
try {
  const { ETYMOLOGY_CHARS } = await import('../apps/literacy-app/src/data/etymology-index.js')
  const n = ETYMOLOGY_CHARS?.length ?? 0
  check(n >= 200, `H3 字源动画 ${n} 字（要求 ≥ 200）`)
} catch (e) {
  fails.push(`✗ H3 字源读取失败：${e.message}`)
}

/* H4 年龄档联动 */
const mathSrc = [
  'apps/math-app/src/modules/number-sense/NumberSenseView.vue',
  'apps/math-app/src/modules/geometry/GeometryView.vue',
  'apps/math-app/src/modules/logic/LogicView.vue',
  'apps/math-app/src/modules/word-problems/WordProblemsView.vue',
  'apps/math-app/src/modules/sudoku/SudokuView.vue',
  'apps/math-app/src/modules/arithmetic/ArithmeticView.vue'
]
const ageBandHits = mathSrc.filter((f) => /ageBand|AGE_BAND/i.test(read(f))).length
check(ageBandHits >= 5, `H4 年龄档联动 ${ageBandHits}/5 模块（要求 ≥ 5）`)

/* H5 逻辑小游戏 */
const logicGame =
  /pair|memory|maze|配对|迷宫/i.test(read('apps/math-app/src/router/index.js')) &&
  exists('apps/math-app/src/modules/logic/LogicView.vue')
check(
  logicGame,
  logicGame ? 'H5 逻辑配对/迷宫已接线' : 'H5 逻辑小游戏未接线 —— 由 r7-math-logic-games 交付'
)

/* H6 第 4 主题 */
const themeSrc =
  read('apps/literacy-app/src/stores/settings.js') +
  read('apps/math-app/src/stores/settings.js') +
  read('shared/styles/design-tokens.css')
check(
  /aurora/i.test(themeSrc) && /theme.*aurora|aurora.*theme/i.test(themeSrc),
  /aurora/i.test(themeSrc)
    ? 'H6 第 4 主题 aurora 已接线'
    : 'H6 第 4 主题未接线 —— 由 r7-theme-aurora 交付'
)

/* H7 全局报告 */
const report = read('.agent_workspace/GLOBAL-SUMMARY-REPORT.md')
const badRows = (report.match(/\|[^|\n]*❌[^|\n]*\|/g) || []).length
check(
  report.length > 500 && badRows === 0,
  report.length > 500
    ? badRows === 0
      ? 'H7 GLOBAL-SUMMARY-REPORT 全表无 ❌'
      : `H7 GLOBAL-SUMMARY-REPORT 仍有 ${badRows} 行 ❌`
    : 'H7 GLOBAL-SUMMARY-REPORT 未生成 —— 由 r7-global-report 交付'
)

notes.forEach((n) => console.log(' ', n))
if (fails.length) {
  console.log('')
  fails.forEach((f) => console.log(' ', f))
}
console.log(`\nRound 7 终验门禁：${notes.length} 项通过，${fails.length} 项失败。`)
process.exit(fails.length ? 1 : 0)
