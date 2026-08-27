/**
 * Round 8 深度超越硬门槛。
 * 标准：.agent_workspace/ROUND8-ACCEPTANCE.md（探针细则见 §2，逐项与本文件对齐）
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
const TARGET_SKILL_NODES = 10
const TARGET_LH_PERF = 95
const TARGET_LH_SECONDARY = 90
const TARGET_EVIDENCE_JSON = 2
const EXPECTED_RESULTS = 8

const literacyRoutes = routerEntries(readIfExists('apps/literacy-app/src/router/index.js'))
const mathRoutes = routerEntries(readIfExists('apps/math-app/src/router/index.js'))
const literacySmoke = stripComments(readIfExists('apps/literacy-app/scripts/smoke.mjs'))

/* H1 字源 800：计数 + 无重复 + 全汉字 + TOTAL_ETYMOLOGY 一致（§2.1） */
try {
  const mod = await import('../apps/literacy-app/src/data/etymology-index.js')
  const chars = Array.from(mod.ETYMOLOGY_CHARS ?? '')
  const n = chars.length
  const unique = new Set(chars).size === n
  const allHan = chars.every((c) => /\p{Script=Han}/u.test(c))
  const declared = mod.TOTAL_ETYMOLOGY
  const consistent = declared === undefined || declared === n
  check(
    'H1',
    n >= TARGET_ETYMOLOGY && unique && allHan && consistent,
    `H1 字源动画 ${n} 字（要求 ≥ ${TARGET_ETYMOLOGY}，无重复，全汉字）`,
    `H1 字源动画 ${n}/${TARGET_ETYMOLOGY} 字` +
      `${unique ? '' : '；存在重复凑数'}${allHan ? '' : '；混入非汉字'}` +
      `${consistent ? '' : `；TOTAL_ETYMOLOGY=${declared} 与实际不符`} —— 由 r8-literacy-etymology 交付`
  )
} catch (e) {
  check('H1', false, '', `H1 字源读取失败：${e.message}`)
}

/* H2 单元剧情 u59–u99（功能探针，兜底文案不算数）+ 儿歌数据与真实路由（§2.2） */
{
  const SENTINEL = '__R8_PROBE_DESC__'
  let declared = 0
  let missing = []
  const empty = []
  let storyErr = ''
  try {
    const mod = await import('../apps/literacy-app/src/data/unit-stories.js')
    declared = Number(mod.TOTAL_UNIT_STORIES ?? 0)
    for (let i = 59; i <= 99; i += 1) {
      const id = `u${i}`
      const text = mod.unitStory({ id, name: '探针', desc: SENTINEL })
      if (typeof text !== 'string' || !text.trim()) empty.push(id)
      else if (text.includes(SENTINEL)) missing.push(id)
    }
  } catch (e) {
    storyErr = e.message
    missing = ['import 失败']
  }
  let songCount = 0
  try {
    const songsMod = await import('../apps/literacy-app/src/data/songs.js')
    const list = songsMod.SONGS ?? songsMod.default ?? []
    const seen = new Set()
    songCount = Array.isArray(list)
      ? list.filter((s) => {
          if (!s || typeof s !== 'object' || !s.id || seen.has(s.id)) return false
          seen.add(s.id)
          return Boolean(s.title ?? s.name) && Boolean(s.lyrics ?? s.lines ?? s.audio ?? s.src)
        }).length
      : 0
  } catch {
    songCount = 0
  }
  const songEntry = literacyRoutes.find(
    (e) => /song|儿歌|music|nursery/i.test(e.path) && dynamicView(e)
  )
  const songViewRel = songEntry && `apps/literacy-app/src/${dynamicView(songEntry)}`
  const songRoute = Boolean(songViewRel) && exists(songViewRel)
  const storiesOk =
    !storyErr && declared >= TARGET_UNIT_STORIES && missing.length === 0 && empty.length === 0
  check(
    'H2',
    storiesOk && songCount >= TARGET_SONGS && songRoute,
    `H2 单元剧情 ${declared} 条（u59–u99 手写全覆盖）+ 儿歌 ${songCount} 首（路由 ${songEntry?.path}）`,
    `H2 单元剧情/儿歌未闭环：STORIES=${declared}/${TARGET_UNIT_STORIES}` +
      `${storyErr ? `（读取失败：${storyErr}）` : ''}，` +
      `u59–u99 兜底/缺失=${missing.length ? missing.slice(0, 5).join('、') + (missing.length > 5 ? '…' : '') : '无'}，` +
      `${empty.length ? `空文案=${empty.slice(0, 5).join('、')}，` : ''}` +
      `儿歌=${songCount}/${TARGET_SONGS}，儿歌路由=${songRoute ? songEntry.path : '缺失'} —— 由 r8-literacy-stories 交付`
  )
}

/* H3 技能图谱：真实路由 + 视图 + 数据（≥10 节点含边关系）+ 视图联动（§2.3） */
{
  const graphEntry = mathRoutes.find(
    (e) => /skill|图谱|map-graph/i.test(e.path) && dynamicView(e)
  )
  const viewRel = graphEntry && `apps/math-app/src/${dynamicView(graphEntry)}`
  const dataFile = existsAny(
    'apps/math-app/src/data/skill-graph.js',
    'apps/math-app/src/data/skills.js'
  )
  const dataSrc = dataFile ? stripComments(readIfExists(dataFile)) : ''
  const nodeCount = (dataSrc.match(/\bid\s*:/g) || []).length
  const hasEdges = /edges|links|prereq|requires|unlocks|parents?|children/i.test(dataSrc)
  const graphData = nodeCount >= TARGET_SKILL_NODES && hasEdges
  const viewSrc = viewRel && exists(viewRel) ? stripComments(readIfExists(viewRel)) : ''
  const viewWired = /skill|图谱/i.test(viewSrc) && /ageBand|AGE_BAND|progress|topics?|母题/i.test(viewSrc)
  check(
    'H3',
    Boolean(viewRel) && exists(viewRel) && graphData && viewWired,
    `H3 技能图谱已接线（${graphEntry?.path} + ${dataFile ? path.basename(dataFile) : 'data'}：${nodeCount} 节点含边关系，视图联动进度/年龄档）`,
    `H3 技能图谱未闭环：路由=${graphEntry?.path ?? '缺失'}，` +
      `视图=${viewRel && exists(viewRel) ? '有' : '缺失'}，` +
      `数据=${dataFile ? `${path.basename(dataFile)}（节点 ${nodeCount}/${TARGET_SKILL_NODES}，边关系=${hasEdges ? '有' : '缺失'}）` : '缺失'}，` +
      `视图联动=${viewWired ? '有' : '缺失'} —— 由 r8-math-skillgraph 交付`
  )
}

/* H4 OCR 精度基准：脚本须真实调用识别、计算精度、带阈值断言（§2.4） */
{
  const accSrc = stripComments(readIfExists('apps/literacy-app/scripts/test-ocr-accuracy.mjs'))
  const ocrTest = stripComments(readIfExists('apps/literacy-app/scripts/test-ocr.mjs'))
  const benchSrc = accSrc || (/\bROUND8_H4\b/.test(ocrTest) ? ocrTest : '')
  const recogOk = /recogni[sz]e|createWorker|tesseract|ocr/i.test(benchSrc)
  const metricOk = /accuracy|正确率|命中率|recall|召回率/i.test(benchSrc)
  const gateOk = /process\.exit|assert/i.test(benchSrc)
  const hasBenchmark = Boolean(benchSrc) && recogOk && metricOk && gateOk
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
    'H4 OCR 精度基准（识别调用 + accuracy 计算 + 阈值断言）与 CharDetailView 形近测验均已接线',
    `H4 OCR/测验未闭环：精度脚本=${
      benchSrc
        ? `有（识别调用=${recogOk ? '有' : '缺失'}，accuracy=${metricOk ? '有' : '缺失'}，阈值断言=${gateOk ? '有' : '缺失'}）`
        : '缺失'
    }，CharDetailView 形近池=${quizWired ? '有' : '缺失'} —— 由 r8-literacy-ocr-quality 交付`
  )
}

/* H5 跟读 v2：音素/声调级或学伴对话面 + smoke 标记（§2.5） */
{
  const followSrc =
    stripComments(readIfExists('apps/literacy-app/src/composables/useSpeechEval.js')) +
    stripComments(readIfExists('apps/literacy-app/src/views/FollowReadView.vue')) +
    stripComments(readIfExists('apps/literacy-app/src/components/MascotCompanion.vue'))
  const v2Features =
    /\bphonemes?\b|音素|\btones?\b|声调|声母|韵母|\bROUND8_H5\b/i.test(followSrc) ||
    /companion[\s\S]{0,80}?(?:chat|dialog|reply|对话)|学伴[\s\S]{0,40}?对话/i.test(followSrc)
  const v2Smoke = /\bROUND8_H5_SMOKE\b/.test(literacySmoke)
  check(
    'H5',
    v2Features && v2Smoke,
    'H5 跟读 v2（音素/声调或学伴对话）与 smoke 已接线',
    `H5 跟读 v2 未闭环：v2 能力=${v2Features ? '有' : '缺失'}，` +
      `smoke=${v2Smoke ? '有' : '缺失'} —— 由 r8-literacy-followread 交付`
  )
}

/* H6 Lighthouse：双 App P ≥ 95 且 A/BP ≥ 90（表格行锚定）+ 证据包 ≥ 2 份 JSON（§2.6） */
{
  const log = readIfExists('.agent_workspace/acceptance-log-round8.md').replace(
    /<!--[\s\S]*?-->/g,
    ''
  )
  const row = (label) =>
    log.match(
      new RegExp(
        `^\\|[^|\\n]*${label}[^|\\n]*\\|\\s*(\\d{2,3})\\s*/\\s*(\\d{2,3})\\s*/\\s*(\\d{2,3})`,
        'm'
      )
    )
  const scoreOk = (m) =>
    Boolean(m) &&
    Number(m[1]) >= TARGET_LH_PERF &&
    Number(m[2]) >= TARGET_LH_SECONDARY &&
    Number(m[3]) >= TARGET_LH_SECONDARY
  const lit = row('识字')
  const math = row('数学')
  const fmt = (m) => (m ? `${m[1]}/${m[2]}/${m[3]}` : '未回填')
  const evidenceJson = (() => {
    try {
      return fs
        .readdirSync(path.join(root, '.agent_workspace/evidence/r8'), { recursive: true })
        .filter((f) => /\.json$/i.test(String(f))).length
    } catch {
      return 0
    }
  })()
  check(
    'H6',
    scoreOk(lit) && scoreOk(math) && evidenceJson >= TARGET_EVIDENCE_JSON,
    `H6 Lighthouse 识字 ${fmt(lit)} / 数学 ${fmt(math)}（P ≥ ${TARGET_LH_PERF}，A/BP ≥ ${TARGET_LH_SECONDARY}）+ 证据包 ${evidenceJson} 份 JSON`,
    `H6 Perf 未达标：识字 P/A/BP=${fmt(lit)}，数学 P/A/BP=${fmt(math)}` +
      `（要求 P ≥ ${TARGET_LH_PERF}、A/BP ≥ ${TARGET_LH_SECONDARY}，按 log §2.1 表格行回填），` +
      `evidence/r8 JSON=${evidenceJson}/${TARGET_EVIDENCE_JSON} —— 由 r8-perf-lighthouse 交付`
  )
}

/* H7 全局报告 Round 8：零 ❌ 零占位 + evidence/r8 证据索引（§2.7） */
{
  const report = readIfExists('.agent_workspace/GLOBAL-SUMMARY-REPORT.md')
  const isRound8 = /Round\s*8/i.test(report)
  const redCrosses = (report.match(/❌/g) || []).length
  const placeholders = (report.match(/⬜|待回填|\[P\/F\]/gi) || []).length
  const hasEvidence = /evidence\/r8/i.test(report)
  check(
    'H7',
    report.length > 4000 && isRound8 && redCrosses === 0 && placeholders === 0 && hasEvidence,
    'H7 GLOBAL-SUMMARY-REPORT Round 8 终验 + evidence/r8 证据索引',
    `H7 全局报告未终验：Round8=${isRound8 ? '有' : '缺失'}，` +
      `❌=${redCrosses}，占位=${placeholders}，evidence/r8 索引=${hasEvidence ? '有' : '缺失'} —— 由 r8-global-report 交付`
  )
}

/* H8 Round 7 不退化（§2.8） */
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
