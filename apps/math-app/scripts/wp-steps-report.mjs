/**
 * 应用题 steps 对齐报表（ROUND18_H4 的可复现入口）。
 *
 *   npm run --workspace apps/math-app report:wp-steps
 *   node --import ./scripts/register-alias.mjs scripts/wp-steps-report.mjs [--json] [--tries=40]
 *
 * 报表自己不判对错，只把 utils/wpSteps.js 的对账结果打出来——门禁、探针和这份报表
 * 共用同一个 auditStepAlignment()，免得三处各算各的算出三个数。
 */
import { WORD_PROBLEMS, tierOf } from '../src/data/wordProblems.js'
import { auditStepAlignment, stepHistogram, STEPS_ALIGN_TARGET } from '../src/utils/wpSteps.js'

const arg = (name, fallback) => {
  const hit = process.argv.find((a) => a.startsWith(`--${name}=`))
  return hit ? Number(hit.slice(name.length + 3)) : fallback
}

const report = auditStepAlignment(WORD_PROBLEMS, { tries: arg('tries', 40), seed: arg('seed', 20250418) })
const pct = (n) => `${(n * 100).toFixed(1)}%`

if (process.argv.includes('--json')) {
  console.log(JSON.stringify(report, null, 2))
} else {
  console.log(
    `ROUND18_H4 应用题 steps 对齐：${report.aligned}/${report.total}（${pct(report.rate)}），` +
      `验收线 ${pct(STEPS_ALIGN_TARGET)}，每个母题抽 ${report.tries} 次`,
  )
  const line = (label, key) =>
    `  ${label}：${stepHistogram(report.rows, key)
      .map(([n, c]) => `${n} 步 ×${c}`)
      .join(' · ')}`
  console.log(line('声明步数分布', 'declared'))
  console.log(line('剖析步数分布', 'analyzed'))

  const tiers = new Map()
  for (const tpl of WORD_PROBLEMS) {
    const t = tierOf(tpl)
    tiers.set(t, (tiers.get(t) ?? 0) + 1)
  }
  console.log(
    `  难度档分布：一步 ${tiers.get('one') ?? 0} · 两步 ${tiers.get('two') ?? 0} · 进阶 ${tiers.get('multi') ?? 0}`,
  )

  for (const row of report.mismatched) {
    console.log(
      `  ✗ ${row.id}：声明 ${row.declared} 步 / 剖析 ${row.analyzed.join('、')} 步 —— ${row.equation}`,
    )
  }
  if (!report.mismatched.length) console.log('  ✓ 每一道母题声明的步数都和剖析拆出来的一致')
}
