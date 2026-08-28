/**
 * 应用题「声明步数 ↔ 剖析步数」对账（ROUND18_H4）。
 *
 * 母题自己写着 steps: 2，剖析面板却只摊得出一步——孩子看到的两个数字对不上，
 * 先信哪个都是错的。Round 18 之前这种题有 56 道（214 道母题里 26%），
 * 大头是两类：有余数除法被压成一行只记一步，以及「和差倍 / 相遇」把难度档
 * 写进了 steps 字段（声明 3 步，算式上只有 2 步）。
 *
 * 这份文件只做计数，不做判断：谁对谁错交给调用方（内容自检、门禁探针、报表）。
 * 抽成纯函数是因为已经有三处各写一份 for 循环了，各算各的迟早算出三个数。
 *
 * 计数口径：一个母题算「对齐」，要它在若干次随机取值下**每次**都拆出声明的步数。
 * 只抽一次会漏掉那种「取值碰巧才多一步」的母题（例如某些分支会退化成整除）。
 */
import { buildAnalysis, ROUND18_H4 } from '@/utils/wpAnalysis.js'
import { reseed } from '@/utils/random.js'

export { ROUND18_H4 }

/** 对齐率的验收线：214 道母题里至少 193 道对得上。 */
export const STEPS_ALIGN_TARGET = 0.9

/** 母题声明的步数；没写按一步算，和 WORD_PROBLEM_TIERS 的兜底保持一致。 */
export function declaredSteps(template) {
  const n = Number(template?.steps ?? 1)
  return Number.isInteger(n) && n >= 1 ? n : 1
}

/** 一次实例化能拆出几步。带上 id 是因为手写剖析靠它对号入座。 */
export function analyzedSteps(template) {
  const question = { ...template.make(), id: template.id }
  return { count: buildAnalysis(question).steps.length, question }
}

/**
 * 逐个母题对账。
 *
 * @param templates 母题数组（WORD_PROBLEMS 或它的子集）
 * @param tries     每个母题抽几次，默认 40
 * @param seed      给随机流的种子；给了就每次跑出一模一样的结果
 * @returns { total, aligned, rate, mismatched: [{ id, declared, analyzed, equation }] }
 *          analyzed 是这个母题出现过的所有步数（升序去重），一般只有一个值。
 */
export function auditStepAlignment(templates, { tries = 40, seed = null } = {}) {
  const list = Array.isArray(templates) ? templates : []
  if (seed !== null) reseed(seed)

  const rows = []
  for (const template of list) {
    if (typeof template?.make !== 'function') continue
    const declared = declaredSteps(template)
    const seen = new Set()
    let sample = ''
    for (let i = 0; i < Math.max(1, tries); i++) {
      const { count, question } = analyzedSteps(template)
      seen.add(count)
      // 留一份对不上的算式当样例：报表和证据都要指着它说话
      if (count !== declared && !sample) sample = String(question.equation ?? '')
    }
    const analyzed = [...seen].sort((a, b) => a - b)
    rows.push({
      id: template.id,
      declared,
      analyzed,
      aligned: analyzed.length === 1 && analyzed[0] === declared,
      equation: sample,
    })
  }

  const mismatched = rows.filter((row) => !row.aligned)
  const aligned = rows.length - mismatched.length
  return {
    total: rows.length,
    aligned,
    rate: rows.length ? aligned / rows.length : 1,
    rows,
    mismatched,
    tries,
  }
}

/** 步数分布：{ 声明步数或剖析步数 → 母题数 }，报表按它画两行柱子。 */
export function stepHistogram(rows, key) {
  const out = new Map()
  for (const row of rows) {
    const n = key === 'declared' ? row.declared : row.analyzed[0]
    out.set(n, (out.get(n) ?? 0) + 1)
  }
  return [...out.entries()].sort((a, b) => a[0] - b[0])
}
