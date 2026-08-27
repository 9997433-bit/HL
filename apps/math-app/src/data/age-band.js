/**
 * 年龄档 L1–L5 → 各玩法的默认难度。
 *
 * 家长在家长中心里选一次档位，孩子进任何一个玩法都从对应难度起步；
 * 玩法页里的档位按钮仍然照常可用，这张表只决定「从哪儿起步」。
 *
 * 六个玩法读的都是这一份表，别在各自的视图里再写一份映射，
 * 否则家长改了档位，只有其中几个玩法会跟着动。
 */

/** 规律环带的题型 id（= LogicView 里 MAKERS 的键），档位只能从这里挑。 */
export const LOGIC_PATTERN_IDS = [
  'arith',
  'decrease',
  'double',
  'gap',
  'zigzag',
  'emoji',
  'group',
  'rotate',
  'shape',
]

/** 形状卫星的题型 id（= GeometryView 里 MAKERS 的键）。 */
export const GEOMETRY_QUESTION_IDS = ['find', 'name', 'sides', 'real', 'odd']

/** 数量星云的题型 id，也是 counting.mix 的键。 */
export const COUNTING_QUESTION_IDS = ['drag', 'count', 'seq', 'compare']

/** 家长页与玩法徽标共用的模块清单，顺序即家长页的展示顺序。 */
export const AGE_BAND_MODULES = [
  { key: 'counting', name: '数量星云' },
  { key: 'arithmetic', name: '算术恒星' },
  { key: 'geometry', name: '形状卫星' },
  { key: 'logic', name: '规律环带' },
  { key: 'sudoku', name: '数独空间站' },
  { key: 'word', name: '生活行星' },
]

/**
 * defaults 各字段的含义：
 * - counting.ceilings  数量星云前 3 题 / 之后的数值上限
 * - counting.dragCap   装货题最多摆几个货物（再多就点不过来）
 * - counting.steps     数序题允许的公差
 * - counting.mix       四种题型的抽取权重（相对值，不必凑成 100）
 * - geometry.scope     形状卫星默认的图形范围：2d / 3d / all
 * - geometry.makers    允许出的题型；立体范围下会再自动去掉「数边数」「找不同」
 * - logic              规律环带的题型池，重复的 id 就是加权
 * - arithmetic         算术恒星的默认档位与运算类型
 * - word               生活行星默认停在哪个难度档
 * - sudoku             数独默认的棋盘与挖洞档
 */
export const AGE_BANDS = [
  {
    id: 'L1',
    name: '3–4 岁',
    desc: '点数与图形认知',
    defaults: {
      counting: {
        ceilings: [5, 8],
        dragCap: 8,
        steps: [1],
        mix: { drag: 55, count: 30, seq: 5, compare: 10 },
      },
      geometry: { scope: '2d', makers: ['find', 'name', 'real'] },
      logic: ['emoji', 'emoji', 'group', 'shape'],
      arithmetic: { level: 10, op: 'add' },
      word: 'one',
      sudoku: { size: 4, difficulty: 'easy' },
    },
    hints: {
      counting: '数到 8',
      arithmetic: '10 以内加法',
      geometry: '平面图形',
      logic: '图案循环',
      sudoku: '4×4 简单',
      word: '一步应用题',
    },
  },
  {
    id: 'L2',
    name: '4–6 岁',
    desc: '10 以内加减',
    defaults: {
      counting: {
        ceilings: [10, 20],
        dragCap: 12,
        steps: [1, 1, 2],
        mix: { drag: 46, count: 22, seq: 17, compare: 15 },
      },
      geometry: { scope: '2d', makers: ['find', 'name', 'sides', 'real'] },
      logic: ['emoji', 'emoji', 'group', 'shape', 'rotate', 'arith'],
      arithmetic: { level: 10, op: 'mix' },
      word: 'one',
      sudoku: { size: 4, difficulty: 'easy' },
    },
    hints: {
      counting: '数到 20',
      arithmetic: '10 以内加减',
      geometry: '平面图形',
      logic: '图案与简单数列',
      sudoku: '4×4 简单',
      word: '一步应用题',
    },
  },
  {
    id: 'L3',
    name: '6–8 岁',
    desc: '20 以内进位退位',
    defaults: {
      counting: {
        ceilings: [20, 20],
        dragCap: 15,
        steps: [1, 2, 5],
        mix: { drag: 30, count: 20, seq: 30, compare: 20 },
      },
      geometry: { scope: 'all', makers: ['find', 'name', 'sides', 'real', 'odd'] },
      logic: ['arith', 'decrease', 'emoji', 'group', 'rotate', 'shape'],
      arithmetic: { level: 20, op: 'mix' },
      word: 'all',
      sudoku: { size: 6, difficulty: 'easy' },
    },
    hints: {
      counting: '数到 20 · 跳着数',
      arithmetic: '20 以内进退位',
      geometry: '平面 + 立体',
      logic: '数列与循环',
      sudoku: '6×6 简单',
      word: '全部题型',
    },
  },
  {
    id: 'L4',
    name: '8–10 岁',
    desc: '100 以内与乘除',
    defaults: {
      counting: {
        ceilings: [20, 40],
        dragCap: 15,
        steps: [2, 3, 5, 10],
        mix: { drag: 15, count: 20, seq: 40, compare: 25 },
      },
      geometry: { scope: '3d', makers: ['find', 'name', 'sides', 'real', 'odd'] },
      logic: ['arith', 'decrease', 'double', 'gap', 'group', 'rotate', 'shape', 'zigzag'],
      arithmetic: { level: 100, op: 'mix' },
      word: 'two',
      sudoku: { size: 6, difficulty: 'normal' },
    },
    hints: {
      counting: '数到 40 · 跳着数',
      arithmetic: '100 以内加减',
      geometry: '立体图形',
      logic: '倍数与复合规律',
      sudoku: '6×6 普通',
      word: '两步应用题',
    },
  },
  {
    id: 'L5',
    name: '10–12 岁',
    desc: '两步应用题与数独',
    defaults: {
      counting: {
        ceilings: [40, 60],
        dragCap: 15,
        steps: [3, 5, 10, 20],
        mix: { drag: 10, count: 15, seq: 45, compare: 30 },
      },
      geometry: { scope: 'all', makers: ['find', 'name', 'sides', 'real', 'odd'] },
      logic: ['arith', 'decrease', 'double', 'gap', 'zigzag', 'zigzag', 'rotate', 'shape'],
      arithmetic: { level: 100, op: 'mix' },
      word: 'multi',
      sudoku: { size: 9, difficulty: 'easy' },
    },
    hints: {
      counting: '数到 60 · 大跨步',
      arithmetic: '100 以内加减',
      geometry: '平面 + 立体',
      logic: '复合与交替规律',
      sudoku: '9×9 简单',
      word: '进阶多步题',
    },
  },
]

export const DEFAULT_AGE_BAND = 'L2'

export const AGE_BAND_IDS = AGE_BANDS.map((band) => band.id)

/** 取一个档位；传进来的 id 不认识就回落到默认档，调用方不用自己兜底。 */
export function bandOf(id) {
  return (
    AGE_BANDS.find((band) => band.id === id) ??
    AGE_BANDS.find((band) => band.id === DEFAULT_AGE_BAND)
  )
}

/** 一句话概括某个档位在全部玩法里的默认难度，家长页与徽标的 title 用。 */
export function bandSummary(id) {
  const band = bandOf(id)
  return AGE_BAND_MODULES.map((m) => `${m.name} ${band.hints[m.key]}`).join(' · ')
}
