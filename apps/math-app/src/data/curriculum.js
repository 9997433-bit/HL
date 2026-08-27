/**
 * 课程技能图谱 — L1(3-4岁) L2(4-6岁) L3(6-8岁) L4(8-10岁) L5(10-12岁)。
 * 每个技能点:{ id, module, level, name, deps }，deps 构成解锁 DAG。
 * Round 1 提供代表性骨架节点,Round 2 按人教版课标扩展至全量。
 *
 * 这里的 module 是「学科模块 id」；玩法侧的星球 id 见 data/modules.js，
 * 两者由 modules.js 的 CURRICULUM_ID 建立映射，星球元数据只在那一处定义。
 *
 * 出题目前由各玩法视图自己负责，题目落到哪个技能点由 data/skill-mapping.js
 * 统一裁决；这份图谱只描述「有哪些技能、谁依赖谁」，不描述怎么出题。
 */

export const SKILLS = [
  // ── M1 数与量启蒙 ──
  { id: 'count-to-5', module: 'number-sense', level: 'L1', name: '5以内点数', deps: [] },
  { id: 'count-to-10', module: 'number-sense', level: 'L1', name: '10以内点数', deps: ['count-to-5'] },
  { id: 'count-to-20', module: 'number-sense', level: 'L2', name: '20以内点数', deps: ['count-to-10'] },
  { id: 'number-order', module: 'number-sense', level: 'L2', name: '数序与相邻数', deps: ['count-to-10'] },
  { id: 'compare-to-10', module: 'number-sense', level: 'L1', name: '10以内比大小', deps: ['count-to-5'] },
  { id: 'compare-to-20', module: 'number-sense', level: 'L2', name: '20以内比大小', deps: ['compare-to-10'] },
  { id: 'compose-ten', module: 'number-sense', level: 'L2', name: '10的分与合', deps: ['count-to-10'] },
  { id: 'number-trace', module: 'number-sense', level: 'L1', name: '数字描红0-9', deps: [] },

  // ── M2 加减乘除 ──
  { id: 'add-within-10', module: 'arithmetic', level: 'L2', name: '10以内加法', deps: ['count-to-10'] },
  { id: 'sub-within-10', module: 'arithmetic', level: 'L2', name: '10以内减法', deps: ['add-within-10'] },
  { id: 'add-carry-20', module: 'arithmetic', level: 'L3', name: '20以内进位加', deps: ['add-within-10'] },
  { id: 'sub-borrow-20', module: 'arithmetic', level: 'L3', name: '20以内退位减', deps: ['sub-within-10'] },
  { id: 'add-within-100', module: 'arithmetic', level: 'L3', name: '100以内加法', deps: ['add-carry-20'] },
  { id: 'sub-within-100', module: 'arithmetic', level: 'L3', name: '100以内减法', deps: ['sub-borrow-20'] },
  { id: 'mul-table', module: 'arithmetic', level: 'L4', name: '乘法口诀', deps: ['add-within-100'] },
  { id: 'div-basic', module: 'arithmetic', level: 'L4', name: '表内除法', deps: ['mul-table'] },

  // ── M3 几何空间 ──
  { id: 'shape-2d', module: 'geometry', level: 'L1', name: '认识平面图形', deps: [] },
  { id: 'tangram-basic', module: 'geometry', level: 'L2', name: '七巧板入门', deps: ['shape-2d'] },
  { id: 'symmetry', module: 'geometry', level: 'L3', name: '对称图形', deps: ['shape-2d'] },
  { id: 'shape-3d', module: 'geometry', level: 'L4', name: '立体图形与展开图', deps: ['symmetry'] },

  // ── M4 逻辑推理 ──
  { id: 'pattern-abab', module: 'logic', level: 'L1', name: '循环规律(ABAB)', deps: [] },
  { id: 'pattern-number', module: 'logic', level: 'L3', name: '数列规律', deps: ['pattern-abab'] },
  { id: 'classify', module: 'logic', level: 'L2', name: '分类大师', deps: [] },
  { id: 'maze-condition', module: 'logic', level: 'L3', name: '条件迷宫', deps: ['pattern-abab'] },
  { id: 'deduction', module: 'logic', level: 'L4', name: '真假侦探', deps: ['classify'] },

  // ── M5 数独 ──
  { id: 'sudoku-4', module: 'sudoku', level: 'L2', name: '4宫图案数独', deps: ['count-to-5'] },
  { id: 'sudoku-6', module: 'sudoku', level: 'L3', name: '6宫数独', deps: ['sudoku-4'] },
  { id: 'sudoku-9', module: 'sudoku', level: 'L4', name: '9宫标准数独', deps: ['sudoku-6'] },

  // ── M6 应用题(母题模板见 data/wordProblems.js) ──
  { id: 'wp-combine', module: 'word-problems', level: 'L2', name: '合并问题', deps: ['add-within-10'] },
  { id: 'wp-remain', module: 'word-problems', level: 'L2', name: '剩余问题', deps: ['sub-within-10'] },
  { id: 'wp-diff', module: 'word-problems', level: 'L3', name: '比较差问题', deps: ['sub-borrow-20'] },
  { id: 'wp-times', module: 'word-problems', level: 'L4', name: '倍数与几个几', deps: ['mul-table'] },
  { id: 'wp-share', module: 'word-problems', level: 'L4', name: '平均分与包含除', deps: ['div-basic'] },
  { id: 'wp-two-step', module: 'word-problems', level: 'L4', name: '两步混合问题', deps: ['wp-combine', 'wp-remain'] },
]

export const SKILL_MAP = Object.fromEntries(SKILLS.map((s) => [s.id, s]))

export const skillsOfModule = (moduleId) => SKILLS.filter((s) => s.module === moduleId)

export const isKnownSkill = (id) => Object.hasOwn(SKILL_MAP, id)
