#!/usr/bin/env node

/**
 * ROUND11_H6 数学 Lighthouse 趋势冻结。
 *
 * R8/R9 是同一 Lighthouse 版本与 mobile profile，允许做数学差分；R10 是
 * desktop profile，只作为独立基线，禁止把 desktop 的更小耗时冒充跨轮改进。
 *
 * 用法：
 *   node scripts/check-r11-perf-trend.mjs --write
 *   node scripts/check-r11-perf-trend.mjs
 */

import crypto from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const evidencePath = path.join(
  root,
  '.agent_workspace/evidence/r11/math-lighthouse-trend.json'
)
const write = process.argv.includes('--write')
const LIGHTHOUSE_VERSION = '12.8.2'
const MIN_PERFORMANCE = 0.95
const MAX_SCORE_REGRESSION_PP = 3

const metricBudgets = {
  'first-contentful-paint': {
    unit: 'ms',
    ceiling: 1800,
    maxRelativeRegressionPercent: 10,
  },
  'largest-contentful-paint': {
    unit: 'ms',
    ceiling: 2500,
    maxRelativeRegressionPercent: 10,
  },
  'speed-index': {
    unit: 'ms',
    ceiling: 3000,
    maxRelativeRegressionPercent: 10,
  },
  'total-blocking-time': {
    unit: 'ms',
    ceiling: 200,
    maxRelativeRegressionPercent: 10,
  },
  'cumulative-layout-shift': {
    unit: 'score',
    ceiling: 0.1,
    maxRelativeRegressionPercent: 0,
  },
  interactive: {
    unit: 'ms',
    ceiling: 3500,
    maxRelativeRegressionPercent: 10,
  },
  'total-byte-weight': {
    unit: 'bytes',
    ceiling: 180 * 1024,
    maxRelativeRegressionPercent: 5,
  },
}

const reportSpecs = [
  {
    id: 'r8-mobile',
    round: 8,
    profile: 'mobile',
    relativePath: '.agent_workspace/evidence/r8/lighthouse-math-app.json',
  },
  {
    id: 'r9-mobile',
    round: 9,
    profile: 'mobile',
    relativePath: '.agent_workspace/evidence/r9/lighthouse-math-app.json',
  },
  {
    id: 'r10-desktop',
    round: 10,
    profile: 'desktop',
    relativePath: '.agent_workspace/evidence/r10/lighthouse-math-app-desktop.json',
  },
]

const round = (value, digits = 6) => Number(value.toFixed(digits))
const sha256 = (buffer) => crypto.createHash('sha256').update(buffer).digest('hex')

const readReport = (spec) => {
  const absolute = path.join(root, spec.relativePath)
  const raw = fs.readFileSync(absolute)
  const report = JSON.parse(raw)
  if (report.lighthouseVersion !== LIGHTHOUSE_VERSION) {
    throw new Error(
      `${spec.id} Lighthouse=${report.lighthouseVersion ?? 'missing'}，期望 ${LIGHTHOUSE_VERSION}`
    )
  }
  if (report.configSettings?.formFactor !== spec.profile) {
    throw new Error(
      `${spec.id} formFactor=${report.configSettings?.formFactor ?? 'missing'}，` +
        `期望 ${spec.profile}`
    )
  }

  const metrics = {}
  for (const metric of Object.keys(metricBudgets)) {
    const value = report.audits?.[metric]?.numericValue
    if (!Number.isFinite(value)) throw new Error(`${spec.id} 缺少数值指标 ${metric}`)
    metrics[metric] = round(value)
  }

  const categories = {}
  for (const category of ['performance', 'accessibility', 'best-practices']) {
    const score = report.categories?.[category]?.score
    if (!Number.isFinite(score)) throw new Error(`${spec.id} 缺少分类分数 ${category}`)
    categories[category] = score
  }

  return {
    id: spec.id,
    round: spec.round,
    profile: spec.profile,
    source: spec.relativePath,
    sourceSha256: sha256(raw),
    fetchTime: report.fetchTime,
    lighthouseVersion: report.lighthouseVersion,
    benchmarkIndex: report.environment?.benchmarkIndex ?? null,
    categories,
    metrics,
  }
}

const comparableMetric = (from, to, budget) => {
  const delta = to - from
  const relativeDeltaPercent =
    from === 0 ? (to === 0 ? 0 : null) : round((delta / from) * 100)
  const withinRelativeBudget =
    relativeDeltaPercent === null
      ? to <= budget.ceiling
      : relativeDeltaPercent <= budget.maxRelativeRegressionPercent
  const withinCeiling = to <= budget.ceiling
  return {
    from,
    to,
    delta: round(delta),
    relativeDeltaPercent,
    ceiling: budget.ceiling,
    maxRelativeRegressionPercent: budget.maxRelativeRegressionPercent,
    withinCeiling,
    withinRelativeBudget,
    status: withinCeiling && withinRelativeBudget ? 'pass' : 'fail',
  }
}

const reports = reportSpecs.map(readReport)
const r8 = reports.find((report) => report.id === 'r8-mobile')
const r9 = reports.find((report) => report.id === 'r9-mobile')
const desktop = reports.find((report) => report.id === 'r10-desktop')

if (r8.profile !== r9.profile || r8.lighthouseVersion !== r9.lighthouseVersion) {
  throw new Error('R8/R9 报告口径不一致，不能计算趋势。')
}

const scoreDeltaPercentagePoints = round(
  (r9.categories.performance - r8.categories.performance) * 100
)
const scoreGate = {
  from: r8.categories.performance,
  to: r9.categories.performance,
  deltaPercentagePoints: scoreDeltaPercentagePoints,
  minimum: MIN_PERFORMANCE,
  maxRegressionPercentagePoints: MAX_SCORE_REGRESSION_PP,
  status:
    r9.categories.performance >= MIN_PERFORMANCE &&
    scoreDeltaPercentagePoints >= -MAX_SCORE_REGRESSION_PP
      ? 'pass'
      : 'fail',
}

const metricTrend = Object.fromEntries(
  Object.entries(metricBudgets).map(([metric, budget]) => [
    metric,
    {
      unit: budget.unit,
      ...comparableMetric(r8.metrics[metric], r9.metrics[metric], budget),
    },
  ])
)

const desktopGate = {
  performanceMinimum: MIN_PERFORMANCE,
  performance: desktop.categories.performance,
  largestContentfulPaintCeilingMs: metricBudgets['largest-contentful-paint'].ceiling,
  largestContentfulPaintMs: desktop.metrics['largest-contentful-paint'],
  totalBlockingTimeCeilingMs: metricBudgets['total-blocking-time'].ceiling,
  totalBlockingTimeMs: desktop.metrics['total-blocking-time'],
  cumulativeLayoutShiftCeiling: metricBudgets['cumulative-layout-shift'].ceiling,
  cumulativeLayoutShift: desktop.metrics['cumulative-layout-shift'],
}
desktopGate.status =
  desktopGate.performance >= desktopGate.performanceMinimum &&
  desktopGate.largestContentfulPaintMs <= desktopGate.largestContentfulPaintCeilingMs &&
  desktopGate.totalBlockingTimeMs <= desktopGate.totalBlockingTimeCeilingMs &&
  desktopGate.cumulativeLayoutShift <= desktopGate.cumulativeLayoutShiftCeiling
    ? 'pass'
    : 'fail'

const allGates = [scoreGate.status, ...Object.values(metricTrend).map((item) => item.status)]
const evidence = {
  modelSlug: 'gpt-5.6-sol',
  marker: 'ROUND11_H6',
  evidenceVersion: 1,
  generatedFromFetchTime: desktop.fetchTime,
  methodology: {
    comparableTrend: 'R8 mobile -> R9 mobile',
    formulas: {
      scoreDeltaPercentagePoints: '(newScore - oldScore) * 100',
      relativeDeltaPercent: '((newValue - oldValue) / oldValue) * 100',
      zeroBaseline: '0 -> 0 is 0%; 0 -> nonzero is null and must satisfy the absolute ceiling',
    },
    profileRule:
      'Only equal Lighthouse versions and equal formFactor values are differenced; R10 desktop is an independent baseline.',
  },
  sourceReports: reports,
  mobileTrend: {
    performanceScore: scoreGate,
    metrics: metricTrend,
    status: allGates.every((status) => status === 'pass') ? 'pass' : 'fail',
  },
  desktopBaseline: desktopGate,
}
evidence.status =
  evidence.mobileTrend.status === 'pass' && evidence.desktopBaseline.status === 'pass'
    ? 'pass'
    : 'fail'

const serialized = `${JSON.stringify(evidence, null, 2)}\n`
if (write) {
  fs.mkdirSync(path.dirname(evidencePath), { recursive: true })
  fs.writeFileSync(evidencePath, serialized)
  console.log(`ROUND11_H6 evidence written: ${path.relative(root, evidencePath)}`)
} else {
  if (!fs.existsSync(evidencePath)) {
    console.error(`ROUND11_H6 FAIL: 缺少 ${path.relative(root, evidencePath)}；请先加 --write。`)
    process.exit(1)
  }
  const committed = fs.readFileSync(evidencePath, 'utf8')
  if (committed !== serialized) {
    console.error('ROUND11_H6 FAIL: Lighthouse 源报告与冻结 evidence 不一致；请复核后加 --write。')
    process.exit(1)
  }
  console.log(
    `ROUND11_H6 PASS: mobile trend=${evidence.mobileTrend.status}; ` +
      `desktop baseline=${evidence.desktopBaseline.status}; evidence frozen`
  )
}

process.exit(evidence.status === 'pass' ? 0 : 1)
