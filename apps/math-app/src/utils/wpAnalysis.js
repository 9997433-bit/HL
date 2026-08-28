/**
 * 应用题剖析（ROUND16_H5 的数据层）。
 *
 * 把一道已经实例化的应用题拆成孩子看得懂的四件事：
 *   1. 已知——题面里出现的数量（数字 + 紧跟的量词）
 *   2. 求什么——题面最后那句问句
 *   3. 图示——按数量长短画的条形/线段图（视觉上先分清「谁多谁少、谁是要求的」）
 *   4. 分步——把 equation 按运算优先级拆成一次只算一步的序列
 *
 * 分步靠解析 equation 字符串来做，而不是让每道母题各写一份解析脚本：
 * 母题库是「语义模板 × 场景皮肤」笛卡尔积扩出来的，逐题手写解析扩不动。
 * equation 里可能出现的记号只有 0-9、+ − × ÷、括号、逗号分句和「……」余数，
 * 遇到解析不了的写法一律返回空步骤，由界面退回显示原始算式，不猜。
 */

/** 运算符统一成题面里用的那套符号，顺带带上「为什么用它」的一句话。 */
const OPS = {
  '+': { sign: '+', why: '两部分要合成一个总数，用加法。', apply: (a, b) => a + b },
  '−': { sign: '−', why: '从总数里去掉一部分，用减法。', apply: (a, b) => a - b },
  '×': { sign: '×', why: '几份同样多的数量，用乘法比一次次相加快。', apply: (a, b) => a * b },
  '÷': { sign: '÷', why: '把总数平均分成几份，用除法。', apply: (a, b) => a / b },
}

const ALIAS = { '-': '−', '*': '×', '/': '÷' }
const normalizeOp = (ch) => ALIAS[ch] ?? ch

/** 量词后面常跟的这些字不是单位，切掉免得 chip 上写出「12 个苹果，下午」。 */
const NOT_UNIT = new Set(['和', '又', '再', '还', '共', '一', '每', '比', '的', '了', '是'])

function tokenize(src) {
  const tokens = []
  let i = 0
  while (i < src.length) {
    const ch = src[i]
    if (/\s/.test(ch)) {
      i += 1
      continue
    }
    if (/[0-9]/.test(ch)) {
      let j = i
      while (j < src.length && /[0-9]/.test(src[j])) j += 1
      tokens.push({ type: 'num', value: Number(src.slice(i, j)) })
      i = j
      continue
    }
    if (ch === '(' || ch === '（') {
      tokens.push({ type: '(' })
      i += 1
      continue
    }
    if (ch === ')' || ch === '）') {
      tokens.push({ type: ')' })
      i += 1
      continue
    }
    const op = normalizeOp(ch)
    if (OPS[op]) {
      tokens.push({ type: 'op', op })
      i += 1
      continue
    }
    return null
  }
  return tokens.length ? tokens : null
}

/** 递归下降求值，边算边把每一次二元运算记成一步。括号里的自然先记。 */
function parse(tokens) {
  let pos = 0
  const steps = []
  const peek = () => tokens[pos]

  const record = (op, a, b) => {
    const value = OPS[op].apply(a, b)
    steps.push({ kind: 'calc', op, expr: `${a} ${op} ${b}`, value, why: OPS[op].why })
    return value
  }

  function factor() {
    const t = peek()
    if (!t) return null
    if (t.type === 'num') {
      pos += 1
      return t.value
    }
    if (t.type === '(') {
      pos += 1
      const inner = expr()
      if (inner === null || peek()?.type !== ')') return null
      pos += 1
      return inner
    }
    return null
  }

  function term() {
    let left = factor()
    if (left === null) return null
    while (peek()?.type === 'op' && (peek().op === '×' || peek().op === '÷')) {
      const op = tokens[pos++].op
      const right = factor()
      if (right === null) return null
      left = record(op, left, right)
    }
    return left
  }

  function expr() {
    let left = term()
    if (left === null) return null
    while (peek()?.type === 'op' && (peek().op === '+' || peek().op === '−')) {
      const op = tokens[pos++].op
      const right = term()
      if (right === null) return null
      left = record(op, left, right)
    }
    return left
  }

  const value = expr()
  if (value === null || pos !== tokens.length) return null
  return { value, steps }
}

/**
 * 把 equation 拆成分步序列。
 * 返回的每一步：{ expr, display, value, asked, why }，asked 的那一步是「答案所在」，
 * 界面在判题前要把它盖住，否则剖析就成了不扣星的答案。
 */
export function analyzeEquation(equation) {
  const clauses = String(equation ?? '')
    .split(/[，,]/)
    .map((s) => s.trim())
    .filter(Boolean)
  if (!clauses.length) return []

  const out = []
  for (const clause of clauses) {
    const parts = clause.split('=').map((s) => s.trim())
    if (parts.length !== 2) return []
    const [lhs, rhs] = parts
    const tokens = tokenize(lhs)
    if (!tokens) return []

    // 有余数的除法：商和余数得一起报，孩子才分得清「问的是几份还是剩几个」
    if (rhs.includes('……')) {
      if (tokens.length !== 3 || tokens[1].type !== 'op' || tokens[1].op !== '÷') return []
      const a = tokens[0].value
      const b = tokens[2].value
      if (!b) return []
      const quotient = Math.floor(a / b)
      const remainder = a % b
      const asked = rhs.includes('?')
      const asksRemainder = /……\s*\?/.test(rhs)
      out.push({
        kind: 'calc',
        op: '÷',
        expr: `${a} ÷ ${b}`,
        display: `${quotient} …… ${remainder}`,
        masked: asksRemainder ? `${quotient} …… ?` : '?',
        value: asksRemainder ? remainder : quotient,
        asked,
        why: `${b} 个一份地分，分得出 ${quotient} 份，分不完的 ${remainder} 就是余数。`,
      })
      continue
    }

    const parsed = parse(tokens)
    if (!parsed) return []
    const asked = rhs.includes('?')
    parsed.steps.forEach((step, i) => {
      const last = i === parsed.steps.length - 1
      out.push({
        ...step,
        display: String(step.value),
        masked: '?',
        asked: asked && last,
      })
    })
  }
  return out
}

/** 题面里的数量：数字 + 紧跟的一个量词，够孩子指着说「这个数是干嘛的」。 */
export function extractKnowns(text) {
  const out = []
  const seen = new Set()
  for (const m of String(text ?? '').matchAll(/(\d+)\s*([\u4e00-\u9fa5])?/g)) {
    const num = m[1]
    const tail = m[2] && !NOT_UNIT.has(m[2]) ? m[2] : ''
    const label = `${num}${tail}`
    if (seen.has(label)) continue
    seen.add(label)
    out.push({ num: Number(num), unit: tail, label })
    if (out.length >= 6) break
  }
  return out
}

/** 求什么：题面最后一句问句，问不出来就退回整句题面。 */
export function extractAsk(text) {
  const src = String(text ?? '').trim()
  if (!src) return ''
  const sentences = src.split(/(?<=[。？?！!])/).filter((s) => s.trim())
  const asking = [...sentences].reverse().find((s) => /[？?]/.test(s))
  return (asking ?? sentences.at(-1) ?? src).trim()
}

/** 最外层那个运算决定这道题「整体在干嘛」，图示说明按它来写。 */
function topOperator(equation) {
  const lhs = String(equation ?? '').split(/[，,]/)[0]?.split('=')[0] ?? ''
  const tokens = tokenize(lhs)
  if (!tokens) return ''
  let depth = 0
  let low = ''
  let high = ''
  for (const t of tokens) {
    if (t.type === '(') depth += 1
    else if (t.type === ')') depth -= 1
    else if (t.type === 'op' && depth === 0) {
      if (t.op === '+' || t.op === '−') low = t.op
      else high = high || t.op
    }
  }
  return low || high
}

const CAPTIONS = {
  '+': '两条已知的接起来，接出来的长度就是要求的那一条。',
  '−': '长的那条里划掉一段，剩下没划掉的才是要求的。',
  '×': '几条一样长的接在一起，看看一共有多长。',
  '÷': '把长的那条平均剪成几段，看看一段有多长。',
}

/**
 * 图示：优先用母题自带的 visual.groups（题面画的就是这几堆），
 * 没有就退回算式里的前几个数，长度按最大值归一化，短条也留 8% 免得看不见。
 */
export function buildDiagram(question) {
  const visual = question?.visual ?? null
  const groups = Array.isArray(visual?.groups)
    ? visual.groups.filter((n) => Number.isFinite(n) && n > 0)
    : []
  let values = groups
  if (!values.length) {
    const lhs = String(question?.equation ?? '').split(/[，,]/)[0]?.split('=')[0] ?? ''
    values = (tokenize(lhs) ?? [])
      .filter((t) => t.type === 'num' && t.value > 0)
      .map((t) => t.value)
      .slice(0, 3)
  }
  const max = Math.max(1, ...values)
  const strike = Number(visual?.strike ?? 0)
  return {
    icon: visual?.icon ?? '',
    caption: CAPTIONS[topOperator(question?.equation)] ?? '先把已知的数量画出来，再看要求的是哪一段。',
    bars: values.map((value, i) => ({
      label: `已知 ${i + 1}`,
      value,
      percent: Math.max(8, Math.round((value / max) * 100)),
      // 「剩余」类母题在第一堆上划掉一截，图上要能看出被拿走的部分
      strikePercent: i === 0 && strike > 0 ? Math.min(100, Math.round((strike / value) * 100)) : 0,
    })),
  }
}

/** 一道题的完整剖析数据；界面只管渲染，不再自己算。 */
export function buildAnalysis(question) {
  return {
    knowns: extractKnowns(question?.text),
    ask: extractAsk(question?.text),
    diagram: buildDiagram(question),
    steps: analyzeEquation(question?.equation),
    equation: String(question?.equation ?? ''),
    unit: question?.unit ?? '',
    why: question?.hint ?? '',
  }
}
