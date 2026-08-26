/**
 * 数形结合演示注册表。
 *
 * 每项都遵循同一个三段契约：object（实物）→ visual（图形模型）→
 * equation（算式）。VisualMathDemo.vue 只负责播放，新增概念时只需在这里
 * 登记数据，不必再造一套计时器和跳过逻辑。
 */
export const VISUAL_DEMOS = [
  {
    id: 'counting',
    module: 'number-sense',
    skill: 'count-to-10',
    title: '点数变数字',
    subtitle: '一个一个数，把实物抽象成数量',
    object: { emoji: '🍎', count: 5, label: '5 个苹果' },
    visual: { groups: [5], label: '5 个圆点' },
    equation: '5',
    narration: ['先看见 5 个苹果。', '每个苹果对应一个圆点。', '5 个圆点可以写成数字 5。'],
  },
  {
    id: 'addition',
    module: 'arithmetic',
    skill: 'add-within-10',
    title: '合起来是加法',
    subtitle: '两群实物合成一个整体',
    object: { emoji: '🚀', groups: [3, 2], count: 5, label: '3 艘和 2 艘飞船' },
    visual: { groups: [3, 2], label: '两组圆点合在一起' },
    equation: '3 + 2 = 5',
    narration: ['先有 3 艘飞船，又来了 2 艘。', '画成 3 个点和 2 个点。', '合起来用加法：3 + 2 = 5。'],
  },
  {
    id: 'subtraction',
    module: 'arithmetic',
    skill: 'sub-within-10',
    title: '拿走就是减法',
    subtitle: '从整体里去掉一部分',
    object: { emoji: '⭐', count: 6, removed: 2, label: '6 颗星拿走 2 颗' },
    visual: { groups: [4, 2], crossedGroup: 1, label: '划掉最后 2 个圆点' },
    equation: '6 − 2 = 4',
    narration: ['这里原来有 6 颗星。', '拿走的 2 颗用斜线划掉。', '还剩 4 颗：6 − 2 = 4。'],
  },
  {
    id: 'compose-ten',
    module: 'number-sense',
    skill: 'compose-ten',
    title: '10 的分与合',
    subtitle: '同一个整体可以分成两部分',
    object: { emoji: '🔵', groups: [6, 4], count: 10, label: '10 颗弹珠分两舱' },
    visual: { groups: [6, 4], label: '十格框里 6 格和 4 格' },
    equation: '6 + 4 = 10',
    narration: ['一共有 10 颗弹珠。', '把它们分成 6 颗和 4 颗。', '6 和 4 合成 10：6 + 4 = 10。'],
  },
  {
    id: 'comparison',
    module: 'number-sense',
    skill: 'compare-to-10',
    title: '一一对应比大小',
    subtitle: '配对后看哪边还有剩余',
    object: { emoji: '🍪', groups: [5, 3], count: 8, label: '5 块和 3 块饼干' },
    visual: { groups: [5, 3], label: '上下配对，5 这一边多 2 个' },
    equation: '5 > 3',
    narration: ['左边 5 块，右边 3 块。', '一一配对后，左边还多 2 块。', '所以 5 大于 3，写作 5 > 3。'],
  },
  {
    id: 'multiplication',
    module: 'arithmetic',
    skill: 'mul-table',
    title: '几个几是乘法',
    subtitle: '相同数量的组可以简写',
    object: { emoji: '🌼', groups: [3, 3], count: 6, label: '2 盆花，每盆 3 朵' },
    visual: { groups: [3, 3], label: '2 组，每组 3 个圆点' },
    equation: '2 × 3 = 6',
    narration: ['有 2 盆花，每盆都是 3 朵。', '画成同样多的 2 组圆点。', '2 个 3 可以写成 2 × 3 = 6。'],
  },
  {
    id: 'division',
    module: 'arithmetic',
    skill: 'div-basic',
    title: '平均分是除法',
    subtitle: '把整体分成同样多的几份',
    object: { emoji: '🍓', groups: [2, 2, 2], count: 6, label: '6 颗草莓平均放 3 盘' },
    visual: { groups: [2, 2, 2], label: '3 个圈，每圈 2 个圆点' },
    equation: '6 ÷ 3 = 2',
    narration: ['把 6 颗草莓平均放进 3 个盘子。', '每个圈里都画 2 个点。', '每盘 2 颗：6 ÷ 3 = 2。'],
  },
  {
    id: 'fraction',
    module: 'geometry',
    skill: 'shape-2d',
    title: '一半是二分之一',
    subtitle: '把一个整体平均分',
    object: { emoji: '🍕', count: 1, label: '一张完整的披萨' },
    visual: { groups: [1, 1], fraction: true, label: '平均分成 2 份，取其中 1 份' },
    equation: '1 ÷ 2 = ½',
    narration: ['先看一张完整的披萨。', '把整体平均切成相同的 2 份。', '其中 1 份叫二分之一，写作 ½。'],
  },
]

export const VISUAL_DEMO_MAP = Object.fromEntries(VISUAL_DEMOS.map((demo) => [demo.id, demo]))

export function visualDemoById(id) {
  return VISUAL_DEMO_MAP[id] ?? null
}

export default VISUAL_DEMOS
