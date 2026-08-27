/**
 * Round 8 深度超越硬门槛。
 * 标准：.agent_workspace/ROUND8-ACCEPTANCE.md（探针细则见 §2）
 *
 * 固定输出 8 个结果：H1–H8。
 * 基线（Round 7 闭合后、R8 功能未合入）预期 1/8（仅 H8 绿）。
 *
 * `--json` 输出机读汇总（passed/failed/results）供编排器聚合。
 */

import fs from 'node:fs'
import path from 'node:path'
import { register } from 'node:module'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'

register('./alias-loader.mjs', import.meta.url)

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const asJson = process.argv.includes('--json')
const results = []
const fails = []
const notes = []

const check = (id, ok, passMsg, failMsg = passMsg) => {
  const msg = ok ? passMsg : failMsg
  results.push({ id, status: ok ? 'pass' : 'fail', msg })
  ;(ok ? notes : fails).push(`${ok ? '✓' : '✗'} ${msg}`)
}
const readIfExists = (rel) => {
  try {
    return fs.readFileSync(path.join(root, rel), 'utf8')
  } catch {
    return ''
  }
}
const exists = (rel) => fs.existsSync(path.join(root, rel))
const existsAny = (...rel) => rel.find((p) => exists(p))
const stripComments = (src) =>
  src
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '')

const routerEntries = (src) => {
  const clean = stripComments(src)
  const matches = [...clean.matchAll(/\bpath\s*:\s*(['"])(.*?)\1/g)]
  return matches.map((match, index) => ({
    path: match[2],
    source: clean.slice(match.index, matches[index + 1]?.index ?? clean.length)
  }))
}

const dynamicView = (entry) =>
  entry?.source.match(
    /\bcomponent\s*:\s*\(\)\s*=>\s*import\(\s*['"]@\/((?:views|modules)\/[^'"]+\.vue)['"]\s*\)/
  )?.[1]

const TARGET_ETYMOLOGY = 800
const TARGET_UNIT_STORIES = 99
const TARGET_SONGS = 3
const TARGET_LH_PERF = 95
const EXPECTED_RESULTS = 8

const literacyRoutes = routerEntries(readIfExists('apps/literacy-app/src/router/index.js'))
const mathRoutes = routerEntries(readIfExists('apps/math-app/src/router/index.js'))
const literacySmoke = stripComments(readIfExists('apps/literacy-app/scripts/smoke.mjs'))

/* H1 字源 800 */
try {
  const mod = await import('../apps/literacy-app/src/data/etymology-index.js')
  const chars = Array.from(mod.ETYMOLOGY_CHARS ?? '')
  const n = chars.length
  const unique = new Set(chars).size === n
  check(
    'H1',
    n >= TARGET_ETYMOLOGY && unique,
    `H1 字源动画 ${n} 字（要求 ≥ ${TARGET_ETYMOLOGY}，无重复）`,
    `H1 字源动画 ${n}/${TARGET_ETYMOLOGY} 字` +
      `${unique ? '' : '；存在重复'} —— 由 r8-literacy-etymology 交付`
  )
} catch (e) {
  check('H1', false, '', `H1 字源读取失败：${e.message}`)
}

/* H2 单元剧情 u59–u99 + 儿歌 */
{
  const storiesSrc = readIfExists('apps/literacy-app/src/data/unit-stories.js')
  const storyKeys = [...storiesSrc.matchAll(/\bu(\d+)\s*:/g)].map((m) => `u${m[1]}`)
  const storySet = new Set(storyKeys)
  const u59to99 = Array.from({ length: 41 }, (_, i) => `u${i + 59}`)
  const missingUnits = u59to99.filter((id) => !storySet.has(id))
  const songRoute =
    literacyRoutes.some((e) => /song|儿歌|music|nursery/i.test(e.path)) ||
    /儿歌|nursery|SongsView|SongList/i.test(storiesSrc + readIfExists('apps/literacy-app/src/router/index.js'))
  const songsData = exists('apps/literacy-app/src/data/songs.js')
  const songCount = songsData
    ? (readIfExists('apps/literacy-app/src/data/songs.js').match(/\bid\s*:/g) || []).length
    : 0
  check(
    'H2',
    storySet.size >= TARGET_UNIT_STORIES && missingUnits.length === 0 && songCount >= TARGET_SONGS && songRoute,
    `H2 单元剧情 ${storySet.size} 条（u59–u99 全覆盖）+ 儿歌 ${songCount} 首`,
    `H2 单元剧情/儿歌未闭环：STORIES=${storySet.size}/${TARGET_UNIT_STORIES}，` +
      `缺 u59–u99=${missingUnits.length ? missingUnits.slice(0, 5).join('、') + '…' : '无'}，` +
      `儿歌=${songCount}/${TARGET_SONGS}，路由=${songRoute ? '有' : '缺失'} —— 由 r8-literacy-stories 交付`
  )
}

/* H3 技能图谱 */
{
  const graphEntry = mathRoutes.find(
    (e) => /skill|图谱|map-graph/i.test(e.path) && dynamicView(e)
  )
  const viewRel = graphEntry && `apps/math-app/src/${dynamicView(graphEntry)}`
  const dataFile = existsAny(
    'apps/math-app/src/data/skill-graph.js',
    'apps/math-app/src/data/skills.js'
  )
  const graphData = dataFile && /nodes|skills|edges/i.test(readIfExists(dataFile))
  check(
    'H3',
    Boolean(viewRel) && exists(viewRel) && graphData,
    `H3 技能图谱已接线（${graphEntry?.path} + ${dataFile ? path.basename(dataFile) : 'data'}）`,
    `H3 技能图谱未闭环：路由=${graphEntry?.path ?? '缺失'}，` +
      `视图=${viewRel && exists(viewRel) ? '有' : '缺失'}，` +
      `数据=${graphData && dataFile ? path.basename(dataFile) : '缺失'} —— 由 r8-math-skillgraph 交付`
  )
}

/* H4 OCR 精度基准 */
{
  const accuracyScript = exists('apps/literacy-app/scripts/test-ocr-accuracy.mjs')
  const ocrTest = stripComments(readIfExists('apps/literacy-app/scripts/test-ocr.mjs'))
  const hasBenchmark =
    accuracyScript ||
    (/\bROUND8_H4\b/.test(ocrTest) && /benchmark|accuracy|基准|sample-photo/i.test(ocrTest))
  const quizWired = (() => {
    const src = stripComments(readIfExists('apps/literacy-app/src/views/CharDetailView.vue'))
    return (
      /from\s+['"]@\/utils\/distractors(?:\.js)?['"]/.test(src) &&
      /\b(?:buildOptions|similarDistractors)\s*\(/.test(src)
    )
  })()
  check(
    'H4',
    hasBenchmark && quizWired,
    'H4 OCR 精度基准脚本与 CharDetailView 形近测验均已接线',
    `H4 OCR/测验未闭环：精度脚本=${hasBenchmark ? '有' : '缺失'}，` +
      `CharDetailView 形近池=${quizWired ? '有' : '缺失'} —— 由 r8-literacy-ocr-quality 交付`
  )
}

/* H5 跟读 v2 */
{
  const followSrc =
    stripComments(readIfExists('apps/literacy-app/src/composables/useSpeechEval.js')) +
    stripComments(readIfExists('apps/literacy-app/src/views/FollowReadView.vue')) +
    stripComments(readIfExists('apps/literacy-app/src/components/MascotCompanion.vue'))
  const v2Features =
    /phoneme|音素|tone|声调|companion.*(?:chat|dialog|reply)|学伴.*对话|ROUND8_H5/i.test(
      followSrc
    )
  const v2Smoke = /\bROUND8_H5_SMOKE\b/.test(literacySmoke)
  check(
    'H5',
    v2Features && v2Smoke,
    'H5 跟读 v2（音素/声调或学伴对话）与 smoke 已接线',
    `H5 跟读 v2 未闭环：v2 能力=${v2Features ? '有' : '缺失'}，` +
      `smoke=${v2Smoke ? '有' : '缺失'} —— 由 r8-literacy-followread 交付`
  )
}

/* H6 Lighthouse Perf ≥ 95 */
{
  const log = readIfExists('.agent_workspace/acceptance-log-round8.md')
  const perfBlock = log.match(/识字[\s\S]*?(\d{2,3})\s*\/\s*(\d{2,3})\s*\/\s*(\d{2,3})/i)
  const mathBlock = log.match(/数学[\s\S]*?(\d{2,3})\s*\/\s*(\d{2,3})\s*\/\s*(\d{2,3})/i)
  const litP = perfBlock ? Number(perfBlock[1]) : 0
  const mathP = mathBlock ? Number(mathBlock[1]) : 0
  const evidenceDir = exists('.agent_workspace/evidence/r8')
  check(
    'H6',
    litP >= TARGET_LH_PERF && mathP >= TARGET_LH_PERF && evidenceDir,
    `H6 Lighthouse Perf 识字 ${litP} / 数学 ${mathP}（均 ≥ ${TARGET_LH_PERF}）+ 证据包`,
    `H6 Perf 未达标：识字 P=${litP || '未回填'}，数学 P=${mathP || '未回填'}（要求 ≥ ${TARGET_LH_PERF}），` +
      `证据包=${evidenceDir ? '有' : '缺失'} —— 由 r8-perf-lighthouse 交付`
  )
}

/* H7 全局报告 Round 8 */
{
  const report = readIfExists('.agent_workspace/GLOBAL-SUMMARY-REPORT.md')
  const isRound8 = /Round\s*8/i.test(report)
  const redCrosses = (report.match(/❌/g) || []).length
  const placeholders = (report.match(/⬜|待回填|\[P\/F\]/gi) || []).length
  const hasEvidence = /evidence\/r8|证据包/i.test(report)
  check(
    'H7',
    report.length > 4000 && isRound8 && redCrosses === 0 && placeholders === 0 && hasEvidence,
    'H7 GLOBAL-SUMMARY-REPORT Round 8 终验 + 证据包索引',
    `H7 全局报告未终验：Round8=${isRound8 ? '有' : '缺失'}，` +
      `❌=${redCrosses}，占位=${placeholders}，证据索引=${hasEvidence ? '有' : '缺失'} —— 由 r8-global-report 交付`
  )
}

/* H8 Round 7 不退化 */
{
  const r7 = spawnSync(process.execPath, ['scripts/check-round7.mjs'], {
    cwd: root,
    encoding: 'utf8'
  })
  const r7Ok = r7.status === 0 && /8\/8/.test(r7.stdout + r7.stderr)
  check(
    'H8',
    r7Ok,
    'H8 Round 7 门禁 8/8 无退化',
    `H8 Round 7 退化：check:round7 退出码 ${r7.status ?? '?'} —— 功能分支合并时不得破坏 R7`
  )
}

if (results.length !== EXPECTED_RESULTS) {
  const msg = `门禁自身结果数异常：${results.length}/${EXPECTED_RESULTS}，请修复 check-round8.mjs`
  results.push({ id: 'meta', status: 'fail', msg })
  fails.push(`✗ ${msg}`)
}

if (asJson) {
  console.log(JSON.stringify({ passed: notes.length, failed: fails.length, results }, null, 2))
} else {
  notes.forEach((n) => console.log(' ', n))
  if (fails.length) {
    console.log('')
    fails.forEach((f) => console.log(' ', f))
  }
  console.log(
    `\nRound 8 深度门禁：${notes.length}/${EXPECTED_RESULTS} 项通过，${fails.length} 项失败。`
  )
  if (fails.length) {
    console.log('说明：R8 功能分支尚未全部合并时 FAIL 属预期红灯；集成后必须 8/8。')
  }
}
process.exit(fails.length ? 1 : 0)
