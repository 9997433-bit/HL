/**
 * 题目 → 技能点的唯一裁决处。
 *
 * 掌握度、家长报告的技能雷达、地图上的进度环全都读 curriculum 的技能 id，
 * 所以「这道题算哪个技能」必须只有一份答案。之前每个玩法视图各写一份映射表，
 * 于是出现了除法题记到「倍数问题」、100 以内减法记到「100以内加法」、
 * 数列题记到「真假侦探」这类互相打架的归类。
 *
 * 这里的函数覆盖各玩法的全部题型输入域，check:content 会穷举一遍，
 * 保证每个可能的返回值都真的存在于技能图谱里。
 */

/**
 * 数量星云：装货与点数题按数量分档，数序题单独算「数序与相邻数」。
 * @param {{ type: 'drag'|'count'|'seq', target: number }} q
 */
export function countingSkill({ type, target }) {
  if (type === 'seq') return 'number-order'
  if (target <= 5) return 'count-to-5'
  return target <= 10 ? 'count-to-10' : 'count-to-20'
}

/**
 * 算术恒星：先按位数档位，再按加/减分开。
 * 20 以内档专练进位加与退位减，10 以内与 100 以内档按运算种类归类。
 * @param {{ level: 10|20|100, kind: 'add'|'sub' }} q
 */
export function arithmeticSkill({ level, kind }) {
  const add = kind === 'add'
  if (level === 100) return add ? 'add-within-100' : 'sub-within-100'
  if (level === 20) return add ? 'add-carry-20' : 'sub-borrow-20'
  return add ? 'add-within-10' : 'sub-within-10'
}

/** 形状卫星：立体图形与平面图形是两个技能点。 */
export function geometrySkill({ dim }) {
  return dim === '3d' ? 'shape-3d' : 'shape-2d'
}

/**
 * 规律环带：循环型（图案/形状/旋转）练的是简单规律，
 * 数列与数量递增练的是归纳，两者掌握情况差别很大，不能混记。
 */
const LOGIC_SKILL_BY_TYPE = {
  emoji: 'pattern-abab',
  shape: 'pattern-abab',
  rotate: 'pattern-abab',
  number: 'pattern-number',
  group: 'pattern-number',
}

export const LOGIC_QUESTION_TYPES = Object.keys(LOGIC_SKILL_BY_TYPE)

export function logicSkill(type) {
  return LOGIC_SKILL_BY_TYPE[type] ?? 'pattern-abab'
}

/** 数独空间站：按棋盘档位。 */
export function sudokuSkill(size) {
  return `sudoku-${size}`
}

export const SUDOKU_SIZES = [4, 6, 9]

/**
 * 生活行星的技能写在母题模板上（data/wordProblems.js 的 skill 字段），
 * 因为「这道题在教什么」是母题自身的语义，不是运行时能推出来的。
 */
export const wordProblemSkill = (template) => template.skill
