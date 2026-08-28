/**
 * ROUND16_H4 / ROUND17_H3 学演示的「有没有」索引。
 *
 * 练习壳只需要回答一个问题：当前这道题的技能点，有没有配套演示？
 * 为这一个布尔值把整份注册表（含全部旁白文案）拖进玩法块并不划算——
 * 各玩法路由都有 gzip 预算（见 scripts/check-route-budget.mjs）。
 * 所以这里只留技能 id 清单，真正的数据和播放壳等到点开时再动态加载。
 *
 * 这份清单和 data/learn-demos.js 必须一字不差地对上，
 * 由 scripts/check-content.mjs 逐项核对，漏改一边就红。
 */
export const LEARN_DEMO_SKILLS = [
  'count-to-5',
  'count-to-10',
  'count-to-20',
  'number-order',
  'compare-to-10',
  'compare-to-20',
  'compose-ten',
  'add-within-10',
  'sub-within-10',
  'add-carry-20',
  'sub-borrow-20',
  'add-within-100',
  'sub-within-100',
  'mul-table',
  'div-basic',
  'shape-2d',
  'symmetry',
  'shape-3d',
  'pattern-abab',
  'pattern-number',
  'classify',
  'wp-combine',
  'wp-remain',
  'wp-diff',
  'wp-times',
  'wp-share',
  'wp-two-step',
]

const COVERED = new Set(LEARN_DEMO_SKILLS)

export const hasLearnDemo = (skill) => COVERED.has(skill)

/** 演示中心里定位到这个技能的深链；技能没演示就返回 null，别给死链接。 */
export function learnDemoRoute(skill) {
  return hasLearnDemo(skill)
    ? { path: '/visual-demos', query: { skill }, hash: '#visual-practice' }
    : null
}
