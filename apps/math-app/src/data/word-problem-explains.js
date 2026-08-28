/**
 * 应用题精品剖析登记表（Round 17 H4 的数据层）。
 *
 * wpAnalysis.js 的通用链是「解析 equation 逐步算」——式子念得对，讲不出
 * 「为什么先算这一步」。这张表给进阶母题（鸡兔同笼、相遇、和差倍……）
 * 一道道手写「老师讲题」的分步链；没登记的母题继续走通用链，两条路
 * 在 buildAnalysis 里汇合，剖析面板不用关心步骤是谁写的。
 *
 * 条目协议（协议全文见 .agent_workspace/round17-architecture.md 第 2 节）：
 *
 *   {
 *     masterId: 'chicken-rabbit',      // wordProblems.js 母题 id，每条字面量写 masterId:
 *     explain(made) {                  // made = 母题 make() 的产物
 *       return [
 *         { say: '假设全是鸡，先算假设下一共几只脚。', math: '35 × 2 = 70' },
 *         ...                          // ≥3 步，带 math 的 ≥2 步
 *       ]
 *     },
 *   }
 *
 * 每步两个字段：
 *   say   必填，8–60 字口语，讲「为什么这么算」；不许出现最终得数
 *   math  可选，本步算式 'a op b = c'，数字必须从 made 里取（母题出数是随机的）
 *
 * 最后一个带 math 的步会被规范化器自动标成 asked（判题前面板盖住它的得数），
 * 并强校验它算出的就是 made.answer——手写链不允许自己搞第二套遮罩。
 * explain 抛错、步数不足、得数对不上时 handExplainSteps 返回 null，
 * 调用方退回通用链，手写文案坏了也绝不白屏。
 */

/** H4 探针标记：手写剖析链登记表。 */
export const ROUND17_H4 = 'wp-hand-explains'

/** 少于这个步数的「剖析」讲不出思路，一律不认。 */
const MIN_STEPS = 3

/** 至少要有这么多步带算式，否则只是把 hint 抄了三遍。 */
const MIN_MATH_STEPS = 2

/**
 * 手写条目从这里登记（r17-wp-explain-hand 岗按协议填 ≥20 条）。
 * 表可以为空：空表时一切查询走 null / 0，面板自然全部退回通用链。
 */
export const WORD_PROBLEM_EXPLAINS = []

const BY_ID = new Map(
  WORD_PROBLEM_EXPLAINS.filter((e) => e && typeof e.masterId === 'string').map((e) => [
    e.masterId,
    e,
  ])
)

/** 手写剖析的母题数（按 masterId 去重），验收与证据回填直接读它。 */
export function countHandExplains() {
  return BY_ID.size
}

/** 某个母题的登记条目；没登记返回 null，调用方走通用链。 */
export function explainFor(masterId) {
  return BY_ID.get(masterId) ?? null
}

/** 把 'a op b = c' 按最后一个等号切成左式和得数；切不动就整串当左式。 */
function splitMath(math) {
  const src = String(math ?? '').trim()
  if (!src) return null
  const at = src.lastIndexOf('=')
  if (at < 0) return { expr: src, display: '' }
  return { expr: src.slice(0, at).trim(), display: src.slice(at + 1).trim() }
}

/** 一串文字里的数字 token；'5 …… 3' → ['5','3']，用来对齐带余数的得数。 */
const digitTokens = (src) => String(src ?? '').match(/\d+/g) ?? []

/**
 * 跑一条手写链并规范化成剖析面板已经会渲染的形状：
 *   { kind:'hand', say, expr, display, masked:'?', asked, why }
 *
 * 返回 null 表示「这条链不可用」（没登记 / 抛错 / 步数不足 / 得数对不上），
 * 调用方（wpAnalysis.buildAnalysis）此时退回通用算式解析链。
 */
export function handExplainSteps(masterId, made) {
  const entry = BY_ID.get(masterId)
  if (!entry || typeof entry.explain !== 'function') return null

  let raw
  try {
    raw = entry.explain(made)
  } catch {
    return null
  }
  if (!Array.isArray(raw) || raw.length < MIN_STEPS) return null

  const answer = String(made?.answer ?? '')
  const out = []
  let lastMathAt = -1
  for (const step of raw) {
    const say = String(step?.say ?? '').trim()
    if (!say) return null
    const math = splitMath(step?.math)
    if (math) lastMathAt = out.length
    out.push({
      kind: 'hand',
      say,
      expr: math?.expr ?? '',
      display: math?.display ?? '',
      masked: '?',
      asked: false,
      why: say,
    })
  }

  const mathSteps = out.filter((s) => s.expr).length
  if (mathSteps < MIN_MATH_STEPS || lastMathAt < 0) return null

  // 最后一个带算式的步就是「答案所在」：它的得数里必须出现这道实例的 answer
  // （按数字 token 对齐，'5 …… 3' 这类带余数的显示也认），面板的盖答案机制
  // （判题前显示 masked）才能原样生效。
  const asked = out[lastMathAt]
  if (answer && !digitTokens(asked.display).includes(answer)) return null
  asked.asked = true

  // 任何一步的 say 里写了最终得数，都等于绕开遮罩，直接判这条链不可用。
  // 所以 say 里尽量别放数字，把数字留给会被盖住的 math。
  if (answer && out.some((s) => digitTokens(s.say).includes(answer))) return null

  return out
}

/**
 * 全表体检：对每条登记跑 samples 个随机实例，收集所有会导致退回通用链的毛病。
 * masters 由调用方注入（wordProblems.js 的 WORD_PROBLEMS），数据文件之间不搞反向依赖。
 * 交活前在 Node 里断言返回 []。
 */
export function findExplainHoles(masters, samples = 3) {
  const byId = new Map((masters ?? []).map((m) => [m.id, m]))
  const holes = []
  for (const entry of WORD_PROBLEM_EXPLAINS) {
    const id = entry?.masterId ?? '(无 masterId)'
    const master = byId.get(id)
    if (!master) {
      holes.push(`${id}: wordProblems.js 里没有这个母题`)
      continue
    }
    for (let i = 0; i < samples; i += 1) {
      const made = master.make()
      if (!handExplainSteps(id, made)) {
        holes.push(`${id}: 第 ${i + 1} 个实例的手写链不可用（步数/算式/得数校验没过）`)
        break
      }
    }
  }
  return holes
}
