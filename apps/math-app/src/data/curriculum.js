/**
 * 课程技能图谱 — L1(3-4岁) L2(4-6岁) L3(6-8岁) L4(8-10岁) L5(10-12岁)。
 * 每个技能点:{ id, module, level, name, deps, generator, params }
 * deps 构成 DAG,由 mastery.isUnlocked 判定解锁。
 * Round 1 提供代表性骨架节点,Round 2 按人教版课标扩展至全量。
 *
 * 这里的 module 是「学科模块 id」；玩法侧的星球 id 见 data/modules.js，
 * 两者由 modules.js 的 CURRICULUM_ID 建立映射，星球元数据只在那一处定义。
 */

export const SKILLS = [
  // ── M1 数与量启蒙 ──
  { id: 'count-to-5', module: 'number-sense', level: 'L1', name: '5以内点数', deps: [], generator: 'countObjects', params: { max: 5 } },
  { id: 'count-to-10', module: 'number-sense', level: 'L1', name: '10以内点数', deps: ['count-to-5'], generator: 'countObjects', params: { max: 10 } },
  { id: 'compare-to-10', module: 'number-sense', level: 'L1', name: '10以内比大小', deps: ['count-to-5'], generator: 'compare', params: { max: 10 } },
  { id: 'compose-ten', module: 'number-sense', level: 'L2', name: '10的分与合', deps: ['count-to-10'], generator: null, params: {} },
  { id: 'number-trace', module: 'number-sense', level: 'L1', name: '数字描红0-9', deps: [], generator: null, params: {} },

  // ── M2 加减乘除 ──
  { id: 'add-within-10', module: 'arithmetic', level: 'L2', name: '10以内加法', deps: ['count-to-10'], generator: 'add', params: { max: 10 } },
  { id: 'sub-within-10', module: 'arithmetic', level: 'L2', name: '10以内减法', deps: ['add-within-10'], generator: 'sub', params: { max: 10 } },
  { id: 'add-carry-20', module: 'arithmetic', level: 'L3', name: '20以内进位加', deps: ['add-within-10'], generator: 'add', params: { max: 20, carry: true } },
  { id: 'sub-borrow-20', module: 'arithmetic', level: 'L3', name: '20以内退位减', deps: ['sub-within-10'], generator: 'sub', params: { max: 20, borrow: true } },
  { id: 'add-within-100', module: 'arithmetic', level: 'L3', name: '100以内加减', deps: ['add-carry-20', 'sub-borrow-20'], generator: 'add', params: { max: 100 } },
  { id: 'mul-table', module: 'arithmetic', level: 'L4', name: '乘法口诀', deps: ['add-within-100'], generator: 'mul', params: { maxFactor: 9 } },
  { id: 'div-basic', module: 'arithmetic', level: 'L4', name: '表内除法', deps: ['mul-table'], generator: null, params: {} },

  // ── M3 几何空间 ──
  { id: 'shape-2d', module: 'geometry', level: 'L1', name: '认识平面图形', deps: [], generator: null, params: {} },
  { id: 'tangram-basic', module: 'geometry', level: 'L2', name: '七巧板入门', deps: ['shape-2d'], generator: null, params: {} },
  { id: 'symmetry', module: 'geometry', level: 'L3', name: '对称图形', deps: ['shape-2d'], generator: null, params: {} },
  { id: 'shape-3d', module: 'geometry', level: 'L4', name: '立体图形与展开图', deps: ['symmetry'], generator: null, params: {} },

  // ── M4 逻辑推理 ──
  { id: 'pattern-abab', module: 'logic', level: 'L1', name: '简单规律(ABAB)', deps: [], generator: null, params: {} },
  { id: 'classify', module: 'logic', level: 'L2', name: '分类大师', deps: [], generator: null, params: {} },
  { id: 'maze-condition', module: 'logic', level: 'L3', name: '条件迷宫', deps: ['pattern-abab'], generator: null, params: {} },
  { id: 'deduction', module: 'logic', level: 'L4', name: '真假侦探', deps: ['classify'], generator: null, params: {} },

  // ── M5 数独 ──
  { id: 'sudoku-4', module: 'sudoku', level: 'L2', name: '4宫图案数独', deps: ['count-to-5'], generator: null, params: { sizeKey: 4 } },
  { id: 'sudoku-6', module: 'sudoku', level: 'L3', name: '6宫数独', deps: ['sudoku-4'], generator: null, params: { sizeKey: 6 } },
  { id: 'sudoku-9', module: 'sudoku', level: 'L4', name: '9宫标准数独', deps: ['sudoku-6'], generator: null, params: { sizeKey: 9 } },

  // ── M6 应用题(引用 word-problems.js 模板) ──
  { id: 'wp-combine', module: 'word-problems', level: 'L2', name: '合并问题', deps: ['add-within-10'], generator: null, params: { template: 'combine' } },
  { id: 'wp-remain', module: 'word-problems', level: 'L2', name: '剩余问题', deps: ['sub-within-10'], generator: null, params: { template: 'remain' } },
  { id: 'wp-diff', module: 'word-problems', level: 'L3', name: '比较差问题', deps: ['sub-borrow-20'], generator: null, params: { template: 'diff' } },
  { id: 'wp-times', module: 'word-problems', level: 'L4', name: '倍数问题', deps: ['mul-table'], generator: null, params: { template: 'times' } }
]

export function skillsOfModule(moduleId) {
  return SKILLS.filter((s) => s.module === moduleId)
}
