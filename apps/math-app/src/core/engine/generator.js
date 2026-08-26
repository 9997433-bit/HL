/**
 * 题目生成器 — 所有模块统一输出「题目协议」:
 * { id, skill, type, prompt: { text, speech, visual }, answer, choices?, meta: { difficulty, errorTags } }
 * 纯函数、无框架依赖。Round 2 在此扩展各模块生成器。
 */

export function randInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min
}

export function shuffle(arr) {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

let seq = 0
const nextId = (prefix) => `${prefix}-${Date.now().toString(36)}-${++seq}`

/** 构造干扰项:基于典型错因(错因归因的基础),保证互不相同且非负 */
function distractors(answer, tags = {}) {
  const pool = new Set()
  if (tags.carry) pool.add(answer - 10)      // 忘进位
  if (tags.borrow) pool.add(answer + 10)     // 忘退位
  pool.add(answer + 1)                        // 数感偏差 ±1
  pool.add(answer - 1)
  pool.add(answer + randInt(2, 5))
  const list = [...pool].filter((n) => n >= 0 && n !== answer)
  return shuffle(list).slice(0, 3)
}

/** M1 数感:点数(数一数有几个) */
export function genCountObjects({ max = 10, emoji = '🍎' } = {}) {
  const n = randInt(1, max)
  return {
    id: nextId('ns-count'),
    skill: `count-to-${max}`,
    type: 'choice',
    prompt: { text: `数一数,有几个?`, speech: `数一数,一共有几个?`, visual: { kind: 'objects', emoji, count: n } },
    answer: n,
    choices: shuffle([n, ...distractors(n)]),
    meta: { difficulty: n / max, errorTags: [] }
  }
}

/** M1 数感:比大小 */
export function genCompare({ max = 20 } = {}) {
  let a = randInt(0, max)
  let b = randInt(0, max)
  if (a === b) b = (b + 1) % (max + 1)
  return {
    id: nextId('ns-cmp'),
    skill: `compare-to-${max}`,
    type: 'choice',
    prompt: { text: `哪边更多?`, speech: `${a} 和 ${b},哪个更大?`, visual: { kind: 'compare', a, b } },
    answer: Math.max(a, b),
    choices: [a, b],
    meta: { difficulty: 1 - Math.abs(a - b) / max, errorTags: [] }
  }
}

/** M2 计算:加法(可控制是否进位) */
export function genAdd({ max = 20, carry = null } = {}) {
  let a, b
  do {
    a = randInt(1, max - 1)
    b = randInt(1, max - a)
  } while (carry !== null && ((a % 10) + (b % 10) >= 10) !== carry)
  const ans = a + b
  const hasCarry = (a % 10) + (b % 10) >= 10
  return {
    id: nextId('ar-add'),
    skill: hasCarry ? 'add-carry' : 'add-no-carry',
    type: 'choice',
    prompt: { text: `${a} + ${b} = ?`, speech: `${a} 加 ${b} 等于几?`, visual: { kind: 'expr', a, b, op: '+' } },
    answer: ans,
    choices: shuffle([ans, ...distractors(ans, { carry: hasCarry })]),
    meta: { difficulty: ans / max, errorTags: hasCarry ? ['carry'] : [] }
  }
}

/** M2 计算:减法(可控制是否退位) */
export function genSub({ max = 20, borrow = null } = {}) {
  let a, b
  do {
    a = randInt(2, max)
    b = randInt(1, a - 1)
  } while (borrow !== null && (a % 10 < b % 10) !== borrow)
  const ans = a - b
  const hasBorrow = a % 10 < b % 10
  return {
    id: nextId('ar-sub'),
    skill: hasBorrow ? 'sub-borrow' : 'sub-no-borrow',
    type: 'choice',
    prompt: { text: `${a} - ${b} = ?`, speech: `${a} 减 ${b} 等于几?`, visual: { kind: 'expr', a, b, op: '-' } },
    answer: ans,
    choices: shuffle([ans, ...distractors(ans, { borrow: hasBorrow })]),
    meta: { difficulty: a / max, errorTags: hasBorrow ? ['borrow'] : [] }
  }
}

/** M2 计算:乘法口诀 */
export function genMul({ maxFactor = 9 } = {}) {
  const a = randInt(2, maxFactor)
  const b = randInt(2, maxFactor)
  const ans = a * b
  const near = shuffle([a * (b + 1), a * (b - 1), (a + 1) * b]).filter((n) => n !== ans && n > 0)
  return {
    id: nextId('ar-mul'),
    skill: `mul-table-${a}`,
    type: 'choice',
    prompt: { text: `${a} × ${b} = ?`, speech: `${a} 乘 ${b} 等于几?`, visual: { kind: 'expr', a, b, op: '×' } },
    answer: ans,
    choices: shuffle([ans, ...near.slice(0, 3)]),
    meta: { difficulty: (a * b) / (maxFactor * maxFactor), errorTags: ['mul-table'] }
  }
}

/** 生成器注册表:curriculum 技能点通过名字引用生成器 */
export const generators = {
  countObjects: genCountObjects,
  compare: genCompare,
  add: genAdd,
  sub: genSub,
  mul: genMul
}
