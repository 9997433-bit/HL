/**
 * 周计划 —— 把「今天练什么」摊成「这一周怎么练」。
 *
 * 图谱的 recommend() 只回答当下这一刻的排序（见 data/skill-graph.js），
 * skill-practice.js 回答「点下去落到哪儿」。两者都只看当前存档，所以家长问
 * 「那我这周该怎么安排」时，页面只能把同一份建议重复念七遍。周计划补的就是这一段：
 *
 *   1. 排一天 —— 拿当天的存档跑一次 recommend，挑前 N 个技能当今天的功课；
 *   2. 往前推 —— 假设孩子照着练了一次，按掌握度模型把这几个技能推到明天的值；
 *   3. 再排一天 —— 用推出来的存档再跑一次 recommend。
 *
 * 所以计划是滚动的：练到第三天某个技能过了线，它就从后面几天里消失，被它挡着的
 * 新技能自动补进来。这也是它和「把今天的推荐复制七份」的区别。
 *
 * 全程纯函数。第 2 步推的是一份**副本**，传进来的 mastery 一个字节都不会动，
 * 更不会写回 progress——计划只是一份「照着练大概会怎样」的推演，
 * 孩子练没练、练成什么样，仍然只由玩法页答题时记的那份存档说了算。
 * 推演用的还是 utils/mastery.js 里那套记分模型，不另起一套乐观的算法。
 */
import { DAILY_SIZE, dailyDateKey } from '@/data/daily.js'
import { DEFAULT_AGE_BAND } from '@/data/age-band.js'
import { RECOMMEND_REASON_MAP, recommend } from '@/data/skill-graph.js'
import { practiceEntry, wrongCountsBySkill } from '@/data/skill-practice.js'
import { MASTERY_THRESHOLD, updateMastery } from '@/utils/mastery.js'

/** R11 探针：推荐 → 周计划的冻结信号（check-round11 H3）。 */
export const ROUND11_H3 = 'week-plan'

/** 一份计划排几天。 */
export const WEEK_PLAN_DAYS = 7

/** 一天安排几个技能点。两个封顶：再多孩子一天练不完，计划就变成了摆设。 */
export const WEEK_PLAN_PER_DAY = 2

/** 一个技能一天练一场，一场按每日冒险的题量估 8 分钟——只是给家长一个量级。 */
export const SESSION_MINUTES = 8

/**
 * 推演一场练习的口径：五道题里先记一次答错，再记四次答对。
 *
 * 先扣后加是故意的——掌握度是指数移动平均，答错的衰减比答对的增益重，
 * 把错题排在前面算出来的是**保守值**。宁可让计划显得慢一点，
 * 也不要让家长照着一份「三天就能全部过线」的乐观时间表去要求孩子。
 */
const MISSES_PER_SESSION = 1
const HITS_PER_SESSION = DAILY_SIZE - MISSES_PER_SESSION

/** recommend 多要几条备选，好让「先还错题账」有得挑。 */
const PICK_SLACK = 2

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']

const DATE_KEY = /^\d{4}-\d{2}-\d{2}$/

/**
 * 练一场之后这个技能大概到哪儿。
 * 用的是 updateMastery 本身，答题时怎么记分，这里就怎么推。
 */
export function projectSession(value = 0) {
  let next = value
  for (let i = 0; i < MISSES_PER_SESSION; i++) next = updateMastery(next, false)
  for (let i = 0; i < HITS_PER_SESSION; i++) next = updateMastery(next, true)
  return next
}

const normalizeDateKey = (value) =>
  DATE_KEY.test(value) && Number.isFinite(Date.parse(`${value}T00:00:00Z`))
    ? value
    : dailyDateKey()

/** 从某一天往后数 offset 天；只认 YYYY-MM-DD，认不出来就从今天起算。 */
export function shiftDateKey(dateKey, offset = 0) {
  const base = Date.parse(`${normalizeDateKey(dateKey)}T00:00:00Z`)
  return new Date(base + offset * 864e5).toISOString().slice(0, 10)
}

/** 日历上的称呼：头两天说「今天/明天」，再往后按星期几称呼。 */
function dayLabel(dateKey, index) {
  if (index === 0) return '今天'
  if (index === 1) return '明天'
  return `周${WEEKDAYS[new Date(`${dateKey}T00:00:00Z`).getUTCDay()]}`
}

/**
 * 从当天的备选里挑出今天的功课：欠着错题的排前面，其余按推荐原本的顺序。
 * 只是把顺序挪一挪，不改推荐的判读——欠账先还，是排期的事，不是推荐的事。
 */
function pickDay(items, owed, perDay) {
  return [...items]
    .map((item, index) => ({ item, index, owed: owed[item.id] ?? 0 }))
    .sort((a, b) => (b.owed > 0) - (a.owed > 0) || a.index - b.index)
    .slice(0, perDay)
}

/**
 * 排一份多日滚动的练习计划。
 *
 * @param {{ mastery?: Record<string, number>, ageBand?: string, wrongBook?: object,
 *           days?: number, perDay?: number, startDate?: string }} input
 *   mastery / wrongBook 直接传 progress store 的那两份，函数不会改写它们。
 * @returns {{ band, startDate, days: Array, skills: Array, stats: object,
 *             goal: object|null, path: Array, projected: true }}
 */
export function buildWeekPlan({
  mastery = {},
  ageBand = DEFAULT_AGE_BAND,
  wrongBook = {},
  days = WEEK_PLAN_DAYS,
  perDay = WEEK_PLAN_PER_DAY,
  startDate = dailyDateKey(),
} = {}) {
  const span = Math.max(1, Math.round(days))
  const width = Math.max(1, Math.round(perDay))
  const first = normalizeDateKey(startDate)
  // 推演在副本上滚，传进来的存档只读不写
  const working = { ...mastery }
  const owed = wrongCountsBySkill(wrongBook)

  let band = ageBand
  let goal = null
  let path = []
  const schedule = []

  for (let index = 0; index < span; index++) {
    const dateKey = shiftDateKey(first, index)
    const view = recommend({ mastery: working, ageBand, limit: width + PICK_SLACK })
    if (index === 0) {
      band = view.band
      goal = view.goal
      path = view.path
    }

    // 第一天的落点看真实错题本；后面几天按「当天的账当天还清」推，
    // 否则计划会一路把同一笔欠账重复算到周末
    const picks = pickDay(view.items, index === 0 ? owed : {}, width)
    const skills = picks.map(({ item, owed: wrongCount }) => {
      const before = working[item.id] ?? 0
      const after = projectSession(before)
      working[item.id] = after
      return {
        id: item.id,
        name: item.name,
        emoji: item.emoji,
        level: item.level,
        module: item.module,
        moduleName: item.moduleName,
        planetId: item.planetId,
        route: item.route,
        reason: item.reason,
        reasonLabel: item.reasonLabel,
        reasonHint: RECOMMEND_REASON_MAP[item.reason]?.hint ?? '',
        why: item.why,
        day: index + 1,
        minutes: SESSION_MINUTES,
        wrongCount,
        mastery: before,
        percent: Math.round(before * 100),
        /** 照着练完这一场，掌握度大概到哪儿——预计值，不是成绩。 */
        projected: after,
        projectedPercent: Math.round(after * 100),
        willPass: before < MASTERY_THRESHOLD && after >= MASTERY_THRESHOLD,
        entry: practiceEntry(item, { wrongCounts: index === 0 ? owed : {} }),
      }
    })

    schedule.push({
      day: index + 1,
      index,
      dateKey,
      label: dayLabel(dateKey, index),
      weekday: `周${WEEKDAYS[new Date(`${dateKey}T00:00:00Z`).getUTCDay()]}`,
      today: index === 0,
      skills,
      minutes: skills.reduce((sum, skill) => sum + skill.minutes, 0),
      /** 没得可排的一天：图上该练的都过线了，留给自由练和复习。 */
      rest: skills.length === 0,
      note: skills.length ? '' : '这一天没有该补的新技能，自由练或复习都行',
    })
  }

  // 同一个技能可能连着排好几天，汇总成一行，家长看的是「这周要拿下谁」
  const byId = new Map()
  for (const day of schedule) {
    for (const skill of day.skills) {
      const row = byId.get(skill.id)
      if (!row) {
        byId.set(skill.id, {
          ...skill,
          days: [skill.day],
          sessions: 1,
          from: skill.mastery,
          fromPercent: skill.percent,
          to: skill.projected,
          toPercent: skill.projectedPercent,
          passOnDay: skill.willPass ? skill.day : 0,
        })
        continue
      }
      row.days.push(skill.day)
      row.sessions += 1
      row.to = skill.projected
      row.toPercent = skill.projectedPercent
      if (!row.passOnDay && skill.willPass) row.passOnDay = skill.day
    }
  }
  const skills = [...byId.values()]

  const byReason = Object.values(RECOMMEND_REASON_MAP)
    .map((reason) => ({
      ...reason,
      count: skills.filter((skill) => skill.reason === reason.id).length,
      sessions: skills
        .filter((skill) => skill.reason === reason.id)
        .reduce((sum, skill) => sum + skill.sessions, 0),
    }))
    .filter((reason) => reason.count > 0)

  return {
    band,
    startDate: first,
    days: schedule,
    skills,
    stats: {
      days: schedule.length,
      restDays: schedule.filter((day) => day.rest).length,
      sessions: schedule.reduce((sum, day) => sum + day.skills.length, 0),
      skills: skills.length,
      minutes: schedule.reduce((sum, day) => sum + day.minutes, 0),
      passing: skills.filter((skill) => skill.passOnDay).length,
      byReason,
    },
    goal,
    path,
    /** 计划里的掌握度全是推演值，界面上必须说清楚这一点。 */
    projected: true,
  }
}

/* ------------------------------------------------------------------ 采纳痕迹 */

/**
 * 一个被推荐过的技能，在存档里留下的痕迹。顺序即家长页的展示顺序。
 */
export const ADOPTION_STATES = [
  { id: 'passed', label: '已过线', hint: `掌握度到了 ${Math.round(MASTERY_THRESHOLD * 100)}%` },
  { id: 'owed', label: '欠着错题', hint: '这一点还有错题没还，先重做' },
  { id: 'practiced', label: '练过', hint: '存档里有这一点的记录，还没过线' },
  { id: 'untouched', label: '还没开练', hint: '存档里查不到这一点的记录' },
]

export const ADOPTION_STATE_MAP = Object.fromEntries(ADOPTION_STATES.map((s) => [s.id, s]))

function adoptionState(value, wrongCount) {
  if (value >= MASTERY_THRESHOLD) return 'passed'
  if (wrongCount > 0) return 'owed'
  return value > 0 ? 'practiced' : 'untouched'
}

function adoptionTrace(state, { percent, wrongCount, gap }) {
  if (state === 'passed') return `已到 ${percent}%，这周可以只当复习`
  if (state === 'owed') return `还欠 ${wrongCount} 道错题，练到 ${percent}%`
  if (state === 'practiced') return `练到 ${percent}%，离过线还差 ${gap} 个百分点`
  return '存档里还没有这一点的记录'
}

/**
 * 计划的采纳痕迹 —— 只读统计。
 *
 * 说清楚它是什么：App 不记录「孩子是不是照着推荐去练的」，也不该为了统计去记。
 * 这里能看到的只有存档本身——被推荐过的技能有没有掌握度记录、过没过线、
 * 还欠不欠错题、它那颗星球最近一次是什么时候玩的。所以这是**痕迹**，不是因果：
 * 技能动了，可能是照着计划练的，也可能是孩子自己逛到那颗星球上去了。
 *
 * @param {object} plan buildWeekPlan() 的返回值
 * @param {{ mastery?: object, wrongBook?: object, modules?: object }} snapshot
 *   直接传 progress.state 的那几份，函数只读不写。
 */
export function weekPlanAdoption(plan, { mastery = {}, wrongBook = {}, modules = {} } = {}) {
  const owed = wrongCountsBySkill(wrongBook)
  const rows = (plan?.skills ?? []).map((skill) => {
    const value = mastery[skill.id] ?? 0
    const wrongCount = owed[skill.id] ?? 0
    const percent = Math.round(value * 100)
    const state = adoptionState(value, wrongCount)
    return {
      id: skill.id,
      name: skill.name,
      emoji: skill.emoji,
      moduleName: skill.moduleName,
      planetId: skill.planetId,
      route: skill.route,
      reason: skill.reason,
      reasonLabel: skill.reasonLabel,
      why: skill.why,
      days: [...skill.days],
      sessions: skill.sessions,
      mastery: value,
      percent,
      wrongCount,
      state,
      stateLabel: ADOPTION_STATE_MAP[state].label,
      trace: adoptionTrace(state, {
        percent,
        wrongCount,
        gap: Math.max(1, Math.round(MASTERY_THRESHOLD * 100) - percent),
      }),
      /** 这颗星球最近一次被玩是什么时候；null 表示存档里没记过。 */
      lastPlayedAt: modules[skill.planetId]?.lastPlayed ?? null,
    }
  })

  const count = (state) => rows.filter((row) => row.state === state).length
  const touched = rows.filter((row) => row.state !== 'untouched').length

  return {
    total: rows.length,
    passed: count('passed'),
    owed: count('owed'),
    practiced: count('practiced'),
    untouched: count('untouched'),
    touched,
    touchedPercent: rows.length ? Math.round((touched / rows.length) * 100) : 0,
    byState: ADOPTION_STATES.map((state) => ({ ...state, count: count(state.id) })).filter(
      (state) => state.count > 0,
    ),
    byReason: (plan?.stats?.byReason ?? []).map((reason) => ({
      ...reason,
      touched: rows.filter((row) => row.reason === reason.id && row.state !== 'untouched').length,
      skills: rows.filter((row) => row.reason === reason.id).map((row) => row.name),
    })),
    rows,
  }
}
