/**
 * 家长周报：一句话说清这周的弱项，再给最多三件今晚就能做的事。
 *
 * 家长中心已经有热力图、单元条、错字墙，数据不缺——缺的是「所以呢」。
 * 这里就负责把那些图表压成一句人话：先按优先级挑出**一个**最该管的弱项
 * （没来 > 复习欠账 > 错字扎堆 > 记不牢 > 只认不写 > 没输出），
 * 再给这个弱项配 1–3 条带落点的练习，每条都能直接点过去。
 *
 * 只挑一个弱项是刻意的：列五条家长一条也不会做。
 *
 * 纯函数、不 import Vue、不读 store——组件、测试、Node 探针都能直接调它。
 * 数据全部来自本机存档，不上传也不需要联网。
 */

/** 周报数据契约的版本标记，随报告一起返回。 */
export const ROUND16_H7_WEEKLY_REPORT = 'ROUND16_H7'

/** 一条建议练习最多给三条，多了家长不会做。 */
export const MAX_DRILLS = 3

const num = (v, fallback = 0) => (Number.isFinite(Number(v)) ? Number(v) : fallback)

const charLink = (char) => `/learn/${encodeURIComponent(char)}`

/** '2026-08-28' → '8 月 28 日'；解析不了就原样返回。 */
function humanDay(key) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(key ?? '')
  return m ? `${Number(m[2])} 月 ${Number(m[3])} 日` : (key ?? '')
}

/**
 * 汇总最近 7 天：来了几天、一共多少分钟、认下几个新字。
 * 「来过」的口径和连续天数保持一致：认了新字，或者坐够一分钟。
 */
function summarizeWeek(days) {
  const list = Array.isArray(days) ? days : []
  const seconds = list.reduce((n, d) => n + num(d?.seconds), 0)
  const newChars = list.reduce((n, d) => n + num(d?.newChars), 0)
  const activeDays = list.filter((d) => num(d?.newChars) > 0 || num(d?.seconds) > 60).length
  return {
    activeDays,
    minutes: Math.round(seconds / 60),
    newChars,
    range: list.length
      ? `${humanDay(list[0]?.key)} 至 ${humanDay(list[list.length - 1]?.key)}`
      : '最近 7 天'
  }
}

/** 错得最多的几个字，按「错的次数多、对的次数少」排。 */
function errorChars(chars, limit = 3) {
  return Object.entries(chars ?? {})
    .map(([char, s]) => ({
      char,
      wrong: num(s?.wrong ?? s?.quizWrong),
      correct: num(s?.correct ?? s?.quizRight),
      traced: num(s?.traced),
      level: num(s?.level)
    }))
    .filter((c) => c.wrong > 0)
    .sort((a, b) => b.wrong - a.wrong || a.correct - b.correct)
    .slice(0, limit)
}

/** 学过、但一次都没描过红的字——「只认得出，写不出来」的那一批。 */
function neverTraced(chars, limit = 3) {
  return Object.entries(chars ?? {})
    .map(([char, s]) => ({ char, traced: num(s?.traced), level: num(s?.level) }))
    .filter((c) => c.level >= 1 && c.traced === 0)
    .slice(0, limit)
}

/** 记忆强度最低的几个字。 */
function fadingChars(memoryCards, limit = 3) {
  return (Array.isArray(memoryCards) ? memoryCards : [])
    .map((c) => ({ char: c?.char, retention: num(c?.retention), isDue: Boolean(c?.isDue) }))
    .filter((c) => c.char)
    .sort((a, b) => a.retention - b.retention)
    .slice(0, limit)
}

/**
 * 弱项判定表。
 *
 * 顺序即优先级，第一条命中的就是这周的弱项——所以「这周压根没来」
 * 排在最前面：孩子没来，讨论他哪个字写不好没有意义。
 */
const WEAKNESS_RULES = [
  {
    id: 'absent',
    label: '这周没怎么练',
    when: (f) => f.week.activeDays === 0,
    headline: () => '这周一次都没打开过：先陪孩子认 3 个字，把手感找回来最要紧。',
    drills: (f) => [
      {
        id: 'restart',
        title: '陪孩子认 3 个新字',
        why: '断得越久越难重启，先做一件最短的事。',
        minutes: 6,
        to: '/learn'
      },
      f.due.length && {
        id: 'due',
        title: `复习到期的 ${f.dueCount} 个字`,
        why: '这些字按记忆曲线已经该忘了，今天捞一次还来得及。',
        minutes: 5,
        to: '/learn',
        chars: f.due.map((c) => c.char)
      },
      {
        id: 'book',
        title: '一起读一本绘本',
        why: '绘本只用学过的字，读一本就是一次无痛复习。',
        minutes: 8,
        to: '/books'
      }
    ]
  },
  {
    id: 'thin',
    label: '来的天数太少',
    when: (f) => f.week.activeDays <= 2 && f.week.minutes < 25,
    headline: (f) =>
      `这周只练了 ${f.week.activeDays} 天、一共 ${f.week.minutes} 分钟：` +
      '识字最怕断，每天 10 分钟比周末补一次管用。',
    drills: (f) => [
      {
        id: 'daily',
        title: '固定一个每天 10 分钟的时段',
        why: '短而频繁的复习正好卡在遗忘发生之前。',
        minutes: 10,
        to: '/learn'
      },
      f.due.length && {
        id: 'due',
        title: `先把到期的 ${f.dueCount} 个字过一遍`,
        why: '欠着的复习会越滚越多，先清掉再学新字。',
        minutes: 5,
        to: '/learn',
        chars: f.due.map((c) => c.char)
      },
      {
        id: 'listen',
        title: '玩一局听音识字',
        why: '游戏门槛低，孩子更愿意自己点开。',
        minutes: 5,
        to: '/listen'
      }
    ]
  },
  {
    id: 'backlog',
    label: '复习欠账',
    when: (f) => f.dueCount >= 5,
    headline: (f) =>
      `有 ${f.dueCount} 个字到了该复习的点还没复习：先还这笔账，再学新字更划算。`,
    drills: (f) => [
      {
        id: 'due',
        title: `复习到期的前 ${Math.min(f.dueCount, 8)} 个字`,
        why: '按记忆曲线，这些字今天复习一次能顶好几天。',
        minutes: 8,
        to: '/learn',
        chars: f.due.map((c) => c.char)
      },
      f.due[0] && {
        id: 'due-first',
        title: `从「${f.due[0].char}」开始`,
        why: '它是记得最淡的一个，先救它。',
        minutes: 3,
        to: charLink(f.due[0].char)
      },
      {
        id: 'pause-new',
        title: '这两天先不加新字',
        why: '新字加得比复习快，队列只会越排越长。',
        minutes: 0,
        to: '/parent'
      }
    ]
  },
  {
    id: 'errors',
    label: '错字扎堆',
    when: (f) => f.errors.length > 0 && f.errors[0].wrong >= 2,
    headline: (f) =>
      `「${f.errors.map((c) => c.char).join('」「')}」这几个字反复答错，` +
      '多半是长得像或者读音接近，值得单独拎出来讲一遍。',
    drills: (f) =>
      f.errors.slice(0, MAX_DRILLS).map((c) => ({
        id: `char-${c.char}`,
        title: `重认「${c.char}」并描一遍红`,
        why: `已经错了 ${c.wrong} 次，对 ${c.correct} 次；写一遍比看十遍管用。`,
        minutes: 3,
        to: charLink(c.char),
        chars: [c.char]
      }))
  },
  {
    id: 'fading',
    label: '记不牢',
    when: (f) => f.learnedCount >= 6 && f.averageRetention > 0 && f.averageRetention < 0.6,
    headline: (f) =>
      `学过的字平均只记得 ${Math.round(f.averageRetention * 100)}%：认得快、忘得也快，` +
      '这周把重点放在回头看。',
    drills: (f) => [
      f.fading[0] && {
        id: 'fading-first',
        title: `先看「${f.fading[0].char}」`,
        why: '它是这批字里记得最淡的一个。',
        minutes: 3,
        to: charLink(f.fading[0].char)
      },
      {
        id: 'listen',
        title: '玩一局听音识字',
        why: '听音选字会强迫孩子从记忆里把字捞出来，比重看一遍有效。',
        minutes: 6,
        to: '/listen'
      },
      {
        id: 'book',
        title: '读一本只用学过字的绘本',
        why: '在句子里再遇到一次，字才真的粘住。',
        minutes: 8,
        to: '/books'
      }
    ]
  },
  {
    id: 'writing',
    label: '只认不写',
    when: (f) => f.untraced.length >= 3 && f.masteredCount < f.learnedCount,
    headline: (f) =>
      `学过的字里有 ${f.untracedCount} 个一次都没写过：认得出不等于写得出，这周补写。`,
    drills: (f) =>
      f.untraced.slice(0, MAX_DRILLS).map((c) => ({
        id: `trace-${c.char}`,
        title: `跟着笔顺写一遍「${c.char}」`,
        why: '描红一遍就能把这个字从「认识」推到「会写」。',
        minutes: 3,
        to: charLink(c.char),
        chars: [c.char]
      }))
  },
  {
    id: 'output',
    label: '缺少输出',
    when: (f) => f.learnedCount >= 10 && f.booksFinished === 0 && f.poemsRead === 0,
    headline: (f) =>
      `已经认识 ${f.learnedCount} 个字，但一本绘本、一首诗都还没读完：` +
      '字要放回句子里才算学会。',
    drills: () => [
      {
        id: 'book',
        title: '读完一本分级绘本',
        why: '绘本只用学过的字，读得下来会给孩子很大的信心。',
        minutes: 8,
        to: '/books'
      },
      {
        id: 'poem',
        title: '读一首短古诗',
        why: '四句二十个字，读三遍就能背，成就感来得快。',
        minutes: 6,
        to: '/poems'
      },
      {
        id: 'song',
        title: '唱一首儿歌',
        why: '唱出来的字比看过的字记得久。',
        minutes: 5,
        to: '/songs'
      }
    ]
  },
  {
    id: 'steady',
    label: '状态不错',
    when: () => true,
    headline: (f) =>
      f.learnedCount === 0
        ? '还没有学习记录：先陪孩子认 3 个字，下周这里就会有内容了。'
        : `这周练了 ${f.week.activeDays} 天、认下 ${f.week.newChars} 个新字，` +
          `正确率 ${f.accuracy}%，没有明显短板——保持就好。`,
    drills: (f) => [
      f.due.length && {
        id: 'due',
        title: `顺手复习到期的 ${f.dueCount} 个字`,
        why: '没有短板的时候，把复习跟上就是最好的投入。',
        minutes: 5,
        to: '/learn',
        chars: f.due.map((c) => c.char)
      },
      {
        id: 'next',
        title: '按计划再认几个新字',
        why: '状态好的时候可以多推一点。',
        minutes: 10,
        to: '/learn'
      },
      {
        id: 'book',
        title: '读一本绘本收尾',
        why: '把这周学的字放回句子里过一遍。',
        minutes: 8,
        to: '/books'
      }
    ]
  }
]

/**
 * 生成周报。
 *
 * @param {object} input 见文件头的数据契约；缺字段一律按 0 / 空处理，
 *                       所以新装的 App 也能拿到一份「还没有记录」的完整周报。
 * @returns {{script: string, range: string, week: object, weakness: object,
 *            headline: string, drills: Array}}
 */
export function buildWeeklyReport(input = {}) {
  const chars = input.chars ?? {}
  const week = summarizeWeek(input.days)
  const due = fadingChars(
    (input.memoryCards ?? []).filter((c) => c?.isDue),
    8
  )
  const facts = {
    week,
    chars,
    due,
    dueCount: num(input.dueCount, due.length),
    errors: errorChars(chars),
    untraced: neverTraced(chars),
    untracedCount: Object.values(chars).filter(
      (s) => num(s?.level) >= 1 && num(s?.traced) === 0
    ).length,
    fading: fadingChars(input.memoryCards),
    averageRetention: num(input.averageRetention),
    accuracy: num(input.accuracy),
    learnedCount: num(input.learnedCount),
    masteredCount: num(input.masteredCount),
    booksFinished: num(input.booksFinished),
    poemsRead: num(input.poemsRead),
    streakDays: num(input.streakDays)
  }

  const rule = WEAKNESS_RULES.find((r) => r.when(facts)) ?? WEAKNESS_RULES[WEAKNESS_RULES.length - 1]
  const drills = (rule.drills(facts) || [])
    .filter(Boolean)
    .slice(0, MAX_DRILLS)
    .map((d) => ({ minutes: 5, chars: [], ...d }))

  return {
    script: ROUND16_H7_WEEKLY_REPORT,
    range: week.range,
    week,
    weakness: { id: rule.id, label: rule.label },
    headline: rule.headline(facts),
    drills
  }
}
