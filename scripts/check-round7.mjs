/**
 * Round 7 全面超越终验硬门槛。
 * 标准：.agent_workspace/ROUND7-ACCEPTANCE.md（探针细则见 §2）
 *
 * 固定输出 8 个结果：H1 / H2 字库 / H2 接线 / H3 / H4 / H5 / H6 / H7。
 * Round 7 是终验硬门槛：模块不可读取、视图未接路由、smoke 无断言等
 * 一律 FAIL，不设 PENDING 放行。结果数 ≠ 8 时门禁自身 FAIL（防探针被静默削减）。
 *
 * `--json` 输出机读汇总（passed/failed/results）供编排器聚合。
 * 数据探针经 alias-loader 直接 import 应用数据模块（`@/` 可解析，勿删 register 行）；
 * 接线探针为纯静态分析（fs + 正则，剥注释后匹配）；
 * H2 额外带功能探针（实际调用 similarDistractors 断言干扰项含形近字、非纯随机）。
 */

import fs from 'node:fs'
import path from 'node:path'
import { register } from 'node:module'
import { fileURLToPath } from 'node:url'

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

/** 动态导入的视图，返回 `views/….vue` 或 `modules/….vue`（相对 src/）。 */
const dynamicView = (entry) =>
  entry?.source.match(
    /\bcomponent\s*:\s*\(\)\s*=>\s*import\(\s*['"]@\/((?:views|modules)\/[^'"]+\.vue)['"]\s*\)/
  )?.[1]

const TARGET_ETYMOLOGY = 200
const TARGET_SIMILAR_GROUPS = 100
const TARGET_AGEBAND_MODULES = 5
const EXPECTED_RESULTS = 8

const literacyRoutes = routerEntries(readIfExists('apps/literacy-app/src/router/index.js'))
const mathRoutes = routerEntries(readIfExists('apps/math-app/src/router/index.js'))
const literacySmoke = stripComments(readIfExists('apps/literacy-app/scripts/smoke.mjs'))
const mathSmoke = stripComments(readIfExists('apps/math-app/scripts/smoke.mjs'))

/* H1 拍照识字：路由 + OCR pipeline + smoke 三重接线，缺一即 FAIL。 */
{
  const ocrEntry = literacyRoutes.find(
    (entry) => /camera|ocr|photo/i.test(entry.path) && dynamicView(entry)
  )
  const ocrViewRel = ocrEntry && `apps/literacy-app/src/${dynamicView(ocrEntry)}`
  const ocrRoute = Boolean(ocrViewRel) && exists(ocrViewRel)
  const ocrPipelineFiles = [
    'apps/literacy-app/src/composables/useOcr.js',
    'apps/literacy-app/src/utils/ocr.js'
  ].filter(exists)
  const ocrPipelineFile = ocrPipelineFiles[0]
  const ocrSource = stripComments(
    [...ocrPipelineFiles, ocrViewRel].filter(Boolean).map(readIfExists).join('\n')
  )
  const ocrDep = /tesseract/i.test(readIfExists('apps/literacy-app/package.json'))
  const ocrEngine = /createWorker|\.recognize\s*\(|\bTesseract\b/i.test(ocrSource)
  const ocrFallback =
    /getUserMedia|mediaDevices|capture=|type=['"]file|accept=|FileReader|createObjectURL/i.test(
      ocrSource
    )
  const ocrPipeline = Boolean(ocrPipelineFile) && ocrDep && ocrEngine && ocrFallback
  const ocrSmoke =
    /\bROUND7_H1_SMOKE\b/.test(literacySmoke) ||
    Boolean(ocrEntry && literacySmoke.includes(ocrEntry.path))
  check(
    'H1',
    ocrRoute && ocrPipeline && ocrSmoke,
    `H1 拍照识字路由、OCR pipeline 与 smoke 已接线（${ocrEntry?.path}）`,
    `H1 拍照识字未闭环：路由=${ocrRoute ? ocrEntry.path : '缺失'}，` +
      `pipeline=${ocrPipelineFile ? path.basename(ocrPipelineFile) : '缺失'}，` +
      `tesseract 依赖=${ocrDep ? '有' : '缺失'}，识别调用=${ocrEngine ? '有' : '缺失'}，` +
      `拍照/选图降级=${ocrFallback ? '有' : '缺失'}，smoke=${ocrSmoke ? '有' : '缺失'}` +
      ' —— 由 r7-literacy-ocr 交付'
  )
}

/* H2 形近干扰：字库 + 功能探针（H2.data）与听音/测验接线（H2.wiring）。 */
{
  const SIMILAR_FILE = 'apps/literacy-app/src/data/similar-chars.js'
  const DISTRACTOR_FILE = 'apps/literacy-app/src/utils/distractors.js'
  if (!exists(SIMILAR_FILE) || !exists(DISTRACTOR_FILE)) {
    check(
      'H2.data',
      false,
      '',
      `H2 形近字库未接线（缺 ${[SIMILAR_FILE, DISTRACTOR_FILE]
        .filter((f) => !exists(f))
        .map((f) => path.basename(f))
        .join('、')}）—— 由 r7-literacy-distractors 交付`
    )
  } else {
    try {
      const simMod = await import(`../${SIMILAR_FILE}`)
      const disMod = await import(`../${DISTRACTOR_FILE}`)
      const { CHARACTER_MAP } = await import('../apps/literacy-app/src/data/characters.js')
      const simMap =
        simMod.SIMILAR_MAP instanceof Map
          ? simMod.SIMILAR_MAP
          : new Map(Object.entries(simMod.SIMILAR_CHARS ?? {}))
      /* 值允许「字符串」或「字符数组」两种形状，统一成数组再断言。 */
      const toChars = (value) =>
        typeof value === 'string' ? Array.from(value) : Array.isArray(value) ? value : []
      const rawSimilar =
        typeof simMod.similarChars === 'function' ? simMod.similarChars : (c) => simMap.get(c)
      const similarChars = (c) => toChars(rawSimilar(c))
      const groups = [...simMap.entries()]
        .map(([char, sims]) => [char, toChars(sims)])
        .filter(
          ([char, sims]) =>
            typeof char === 'string' &&
            char &&
            sims.filter((c) => typeof c === 'string' && c && c !== char).length >= 1
        )
      const picker = disMod.similarDistractors
      let flaw =
        typeof picker !== 'function'
          ? 'utils/distractors.js 缺少 similarDistractors 导出'
          : typeof disMod.buildOptions !== 'function'
            ? 'utils/distractors.js 缺少 buildOptions 导出'
            : ''
      if (!flaw) {
        /* 功能探针：抽样断言干扰项去重、排除目标字、且形近字优先出现。 */
        const samples = groups
          .filter(
            ([char, sims]) => CHARACTER_MAP?.has(char) && sims.some((c) => CHARACTER_MAP.has(c))
          )
          .slice(0, 15)
        if (!samples.length) flaw = '形近字库与字表无交集，功能探针无从取样'
        for (const [target, sims] of samples) {
          let out
          try {
            out = picker(target, 3)
          } catch (e) {
            flaw = `similarDistractors('${target}') 抛异常：${e.message}`
            break
          }
          const chars = Array.isArray(out) ? out.map((entry) => entry?.char) : []
          const bag = new Set(chars)
          const ok =
            chars.length === 3 &&
            bag.size === 3 &&
            !bag.has(target) &&
            chars.every((c) => typeof c === 'string' && c) &&
            chars.some((c) => similarChars(target).includes(c))
          if (!ok) {
            flaw = `similarDistractors('${target}') 违约（须 3 个去重字表条目、排除目标字、含形近字）`
            break
          }
        }
      }
      check(
        'H2.data',
        groups.length >= TARGET_SIMILAR_GROUPS && !flaw,
        `H2 形近字库 ${groups.length} 组（要求 ≥ ${TARGET_SIMILAR_GROUPS}），similarDistractors 功能探针通过`,
        `H2 形近字库 ${groups.length}/${TARGET_SIMILAR_GROUPS} 组${flaw ? `；${flaw}` : ''}`
      )
    } catch (e) {
      check('H2.data', false, '', `H2 形近字库读取失败：${e.message}`)
    }
  }

  const usesDistractors = (rel) => {
    const src = stripComments(readIfExists(rel))
    return (
      /from\s+['"]@\/utils\/distractors(?:\.js)?['"]/.test(src) &&
      /\b(?:buildOptions|similarDistractors)\s*\(/.test(src)
    )
  }
  const listenWired = usesDistractors('apps/literacy-app/src/views/ListenGameView.vue')
  const quizWired = usesDistractors('apps/literacy-app/src/views/CharDetailView.vue')
  check(
    'H2.wiring',
    listenWired && quizWired,
    'H2 听音识字与单字测验干扰项均走形近字库（非纯随机）',
    `H2 干扰项接线不全：听音识字=${listenWired ? '已接' : '纯随机'}，` +
      `单字测验=${quizWired ? '已接' : '纯随机'}（须 import @/utils/distractors 并调用 ` +
      'buildOptions/similarDistractors）—— 由 r7-literacy-distractors 交付'
  )
}

/* H3 字源动画 ≥ 200 字，且无重复凑数、索引与声明一致。 */
try {
  const mod = await import('../apps/literacy-app/src/data/etymology-index.js')
  const chars = Array.from(mod.ETYMOLOGY_CHARS ?? '')
  const n = chars.length
  const unique = new Set(chars).size === n
  const declared = mod.TOTAL_ETYMOLOGY
  const consistent = declared === undefined || declared === n
  check(
    'H3',
    n >= TARGET_ETYMOLOGY && unique && consistent,
    `H3 字源动画 ${n} 字（要求 ≥ ${TARGET_ETYMOLOGY}，无重复）`,
    `H3 字源动画 ${n}/${TARGET_ETYMOLOGY} 字` +
      `${unique ? '' : '；存在重复字凑数'}${consistent ? '' : `；TOTAL_ETYMOLOGY=${declared} 与实际不符`}`
  )
} catch (e) {
  check('H3', false, '', `H3 字源读取失败：${e.message}`)
}

/* H4 年龄档联动：settings store 提供 ageBand，且 ≥5 个玩法模块读取。 */
{
  const mathModules = [
    'apps/math-app/src/modules/number-sense/NumberSenseView.vue',
    'apps/math-app/src/modules/geometry/GeometryView.vue',
    'apps/math-app/src/modules/logic/LogicView.vue',
    'apps/math-app/src/modules/word-problems/WordProblemsView.vue',
    'apps/math-app/src/modules/sudoku/SudokuView.vue',
    'apps/math-app/src/modules/arithmetic/ArithmeticView.vue'
  ]
  const storeHasAgeBand = /ageBand/i.test(
    stripComments(readIfExists('apps/math-app/src/stores/settings.js'))
  )
  const hitFlags = mathModules.map((f) => /ageBand|AGE_BAND/i.test(stripComments(readIfExists(f))))
  const hits = hitFlags.filter(Boolean).length
  const missing = mathModules.filter((_, i) => !hitFlags[i]).map((f) => path.basename(f, '.vue'))
  check(
    'H4',
    storeHasAgeBand && hits >= TARGET_AGEBAND_MODULES,
    `H4 年龄档联动 ${hits}/${mathModules.length} 模块读取 ageBand（要求 ≥ ${TARGET_AGEBAND_MODULES}）`,
    `H4 年龄档联动 ${hits}/${TARGET_AGEBAND_MODULES} 模块` +
      `${storeHasAgeBand ? '' : '；settings store 缺 ageBand'}` +
      `${missing.length ? `；未接线：${missing.join('、')}` : ''} —— 由 r7-math-ageband 交付`
  )
}

/* H5 逻辑配对/迷宫：数学 App 真实路由 + 视图文件 + smoke，缺一即 FAIL。 */
{
  const logicEntries = mathRoutes.filter((entry) => {
    if (!/pair|match|memory|maze|配对|迷宫/i.test(entry.path)) return false
    const view = dynamicView(entry)
    return Boolean(view) && exists(`apps/math-app/src/${view}`)
  })
  const logicSmoke =
    /\bROUND7_H5_SMOKE\b/.test(mathSmoke) ||
    logicEntries.some((entry) => mathSmoke.includes(entry.path))
  check(
    'H5',
    logicEntries.length >= 1 && logicSmoke,
    `H5 逻辑配对/迷宫路由与 smoke 已接线（${logicEntries.map((e) => e.path).join('、')}）`,
    `H5 逻辑小游戏未闭环：已接线路由=${
      logicEntries.length ? logicEntries.map((e) => e.path).join('、') : '缺失'
    }，smoke=${logicSmoke ? '有' : '缺失'} —— 由 r7-math-logic-games 交付`
  )
}

/* H6 第 4 主题 aurora：tokens 定义 + 双 App THEMES 注册（识字四主题可切换）。 */
{
  const tokens = readIfExists('shared/styles/design-tokens.css')
  const auroraBlock = tokens.match(/\[data-theme=['"]aurora['"]\][^{]*\{([^}]*)\}/)?.[1] ?? ''
  const auroraTokens = (auroraBlock.match(/--[\w-]+\s*:/g) || []).length
  const themesBlock =
    stripComments(readIfExists('apps/literacy-app/src/stores/settings.js')).match(
      /THEMES\s*=\s*\[([\s\S]*?)\]/
    )?.[1] ?? ''
  const themeCount = (themesBlock.match(/\bid\s*:/g) || []).length
  const literacyAurora = /['"]aurora['"]/.test(themesBlock)
  const mathAurora = /['"]aurora['"]/.test(
    stripComments(readIfExists('apps/math-app/src/stores/settings.js'))
  )
  check(
    'H6',
    auroraTokens >= 5 && literacyAurora && themeCount >= 4 && mathAurora,
    `H6 第 4 主题 aurora 已接线（tokens ${auroraTokens} 项，识字 THEMES ${themeCount} 款，数学已注册）`,
    `H6 第 4 主题未闭环：aurora tokens=${auroraTokens}（要求 ≥ 5），` +
      `识字 THEMES=${literacyAurora ? '有' : '缺失'}（${themeCount} 款，要求 ≥ 4），` +
      `数学注册=${mathAurora ? '有' : '缺失'} —— 由 r7-theme-aurora 交付`
  )
}

/* H7 全局报告：31 模块完整、审计引用、证据齐全。 */
{
  const report = readIfExists('.agent_workspace/GLOBAL-SUMMARY-REPORT.md')
  const expectedModuleIds = [
    ...Array.from({ length: 15 }, (_, index) => `L-M${index + 1}`),
    ...Array.from({ length: 16 }, (_, index) => `M-M${index + 1}`)
  ]
  const expectedModuleIdSet = new Set(expectedModuleIds)
  const moduleRows = report
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => /^\|\s*[LM]-M\d+\s*\|/.test(line))
    .map((line) => {
      const cells = line
        .split('|')
        .slice(1, -1)
        .map((cell) => cell.trim())
      return { id: cells[0], status: cells[2], evidence: cells[3] }
    })
  const moduleIdCounts = new Map()
  for (const row of moduleRows) {
    moduleIdCounts.set(row.id, (moduleIdCounts.get(row.id) ?? 0) + 1)
  }
  const missingModuleIds = expectedModuleIds.filter((id) => !moduleIdCounts.has(id))
  const duplicateModuleIds = [...moduleIdCounts]
    .filter(([id, count]) => expectedModuleIdSet.has(id) && count !== 1)
    .map(([id]) => id)
  const unexpectedModuleIds = moduleRows
    .map((row) => row.id)
    .filter((id) => !expectedModuleIdSet.has(id))
  const invalidModuleRows = moduleRows.filter(
    (row) =>
      !expectedModuleIdSet.has(row.id) ||
      (row.status !== '✅' &&
        !/^⏳\s*待 R(?:7|8) 子代理\s*#(?:[4-9]|10)\b/.test(row.status)) ||
      !row.evidence?.includes('`')
  )
  const firstLine = report.split(/\r?\n/, 1)[0]?.trim() ?? ''
  const modelSlugOk = /^Model slug:\s*[a-z0-9][a-z0-9.-]*$/i.test(firstLine)
  const auditRefsOk =
    report.includes('round6-hongen-module-audit.md') &&
    report.includes('round7-hongen-final-audit.md')
  const placeholders = report.match(/待回填|TODO|TBD|\[P\/F\]|⬜/gi) ?? []
  const redCrosses = report.match(/❌/g) ?? []
  const reportIssues = []
  if (report.length <= 4000) reportIssues.push(`正文过短（${report.length}/4000 字符）`)
  if (!modelSlugOk) reportIssues.push('首行缺少合法 Model slug')
  if (!auditRefsOk) reportIssues.push('未同时引用 Round 6 / Round 7 审计')
  if (moduleRows.length !== expectedModuleIds.length) {
    reportIssues.push(`模块行 ${moduleRows.length}/${expectedModuleIds.length}`)
  }
  if (missingModuleIds.length) reportIssues.push(`缺模块 ${missingModuleIds.join('、')}`)
  if (duplicateModuleIds.length) reportIssues.push(`重复模块 ${duplicateModuleIds.join('、')}`)
  if (unexpectedModuleIds.length) reportIssues.push(`未知模块 ${unexpectedModuleIds.join('、')}`)
  if (invalidModuleRows.length) {
    reportIssues.push(`状态或证据不合规 ${invalidModuleRows.map((row) => row.id).join('、')}`)
  }
  if (redCrosses.length) reportIssues.push(`仍含 ${redCrosses.length} 个红叉`)
  if (placeholders.length) reportIssues.push(`仍含 ${placeholders.length} 个占位符`)
  const pendingRows = moduleRows.filter((row) => row.status.startsWith('⏳')).length
  check(
    'H7',
    reportIssues.length === 0,
    `H7 GLOBAL-SUMMARY-REPORT 31/31 模块完整（${31 - pendingRows} 项当前口径达标、${pendingRows} 项后续轮次在途），审计引用与证据齐全`,
    `H7 GLOBAL-SUMMARY-REPORT 不合规：${reportIssues.join('；')} —— 由 r7-global-report 交付`
  )
}

if (results.length !== EXPECTED_RESULTS) {
  const msg = `门禁自身结果数异常：${results.length}/${EXPECTED_RESULTS}，请修复 check-round7.mjs`
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
    `\nRound 7 终验门禁：${notes.length}/${EXPECTED_RESULTS} 项通过，${fails.length} 项失败。`
  )
  if (fails.length) {
    console.log('说明：Round 7 功能分支尚未全部合并时 FAIL 属预期红灯；集成后必须 8/8。')
  }
}
process.exit(fails.length ? 1 : 0)
