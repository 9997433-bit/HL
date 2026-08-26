/**
 * 应用题母题模板引擎 — 骨架。
 * 母题 = 语义模板(占位符文本) × 参数约束(保证整数/正数解) × 场景皮肤。
 * Round 2 在此实现完整 DSL:多步题、线段图(Pictorial)描述、分步引导脚本。
 */
import { randInt } from './generator.js'

/**
 * 实例化一道应用题。
 * @param {Object} template data/word-problems.js 中的模板对象
 * @returns 题目协议对象(type: 'input')
 */
export function instantiate(template) {
  const skin = template.skins[randInt(0, template.skins.length - 1)]
  // 最多重试 50 次采样参数,直到满足模板约束(如整除、差为正)
  let params = null
  for (let i = 0; i < 50; i++) {
    const candidate = {}
    for (const [key, [min, max]] of Object.entries(template.params)) {
      candidate[key] = randInt(min, max)
    }
    if (!template.constraint || template.constraint(candidate)) {
      params = candidate
      break
    }
  }
  if (!params) throw new Error(`模板 ${template.id} 参数采样失败,请检查约束`)

  const fill = (str) =>
    str.replace(/\{(\w+)\}/g, (_, k) => params[k] ?? skin[k] ?? `{${k}}`)

  return {
    id: `wp-${template.id}-${Date.now().toString(36)}`,
    skill: template.skill,
    type: 'input',
    prompt: {
      text: fill(template.text),
      speech: fill(template.text),
      visual: { kind: 'story', category: template.category, skin: skin.name }
    },
    answer: template.solve(params),
    meta: { difficulty: template.difficulty, errorTags: [template.category], steps: template.steps ?? 1 }
  }
}
