/**
 * 技能「学」演示注册表（Round 16 H4 的数据契约，见 .agent_workspace/round16-architecture.md §2）。
 *
 * 每条演示都是同一个三段协议：object（实物）→ visual（图形模型）→ equation（算式），
 * 播放器沿用 VisualMathDemo.vue（自带跳过 / 重播 / 逐步，reduced-motion 合规），
 * 这里只登记「哪个技能点、演什么」。
 *
 * 实现岗（r16-math-learn-demo）要做的：
 *   1. 把 visualDemos.js 现有 8 条迁进来，字段名 skill 改成 skillId（探针按
 *      「skillId 冒号」的字面量计数，每条必须写死，不许解构 / 循环生成糊过去）；
 *      visualDemos.js 改从本文件 re-export，旧引用不炸；
 *   2. 新增补到 ≥12 条（优先 add-carry-20 / sub-borrow-20 / pattern-abab / wp-combine）；
 *   3. 数值写死在条目里（演示不是刷题），narration 每句 ≤20 字，
 *      实物、图形、算式各至少一句。
 *
 * @typedef {Object} LearnDemo
 * @property {string} skillId    curriculum.js SKILLS 的 id
 * @property {string} id         demo id（/visual-demos?demo= 路由参数，全表唯一）
 * @property {string} title
 * @property {string} subtitle
 * @property {Object} object     实物段  { emoji, count|groups, removed?, label }
 * @property {Object} visual     图形段  { groups, crossedGroup?, fraction?, label }
 * @property {string} equation   算式段
 * @property {string[]} narration
 */

/** R16 探针：技能学演示注册表的冻结信号（check-round16 H4）。 */
export const ROUND16_H4 = 'learn-demo-registry'

/** @type {LearnDemo[]} 实现岗填 ≥12 条；空表期间所有查询都稳定返回 null / 0。 */
export const LEARN_DEMOS = []

export const LEARN_DEMO_MAP = new Map(LEARN_DEMOS.map((demo) => [demo.id, demo]))

const BY_SKILL = new Map()
for (const demo of LEARN_DEMOS) {
  if (!BY_SKILL.has(demo.skillId)) BY_SKILL.set(demo.skillId, demo)
}

/**
 * 主包只准 import 这份 id 清单来判断「有没有演示」（比如 skill-practice.js 给
 * practiceEntry 补 demoTo），不许把 LEARN_DEMOS 全表拖出 visual-demos 路由 chunk。
 */
export const LEARN_DEMO_SKILLS = [...BY_SKILL.keys()]

/** 唯一查询入口。null = 这个技能还没有演示，调用方渲染「无演示」态，不许硬凑。 */
export function learnDemoForSkill(skillId) {
  return BY_SKILL.get(skillId) ?? null
}

export function learnDemoById(id) {
  return LEARN_DEMO_MAP.get(id) ?? null
}

/** 按 skillId 去重后的覆盖数（H4 的备用计数口径）。 */
export function countLearnDemos() {
  return BY_SKILL.size
}
