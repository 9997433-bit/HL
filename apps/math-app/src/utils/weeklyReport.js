/**
 * 家长周报：一句话说清这周的弱项，再给最多三件今晚就能做的事。
 *
 * 家长中心已经有技能雷达、错因统计、周计划痕迹，数据不缺——缺的是「所以呢」。
 * 这里把那几张图压成一句人话：先按优先级挑出**一个**最该管的弱项
 * （没来 > 错题欠账 > 某一类错因反复出现 > 技能点卡住 > 正确率低 > 只玩一颗星球），
 * 再给这个弱项配 1–3 条带落点的练习，每条都能直接点过去。
 *
 * 只挑一个弱项是刻意的：列五条家长一条也不会做。
 *
 * 纯函数、不 import Vue、不读 store，也不 import 课程与错因词典——
 * 那些由调用方喂进来（见 composables/useWeeklyReport.js），
 * 所以组件、测试、Node 探针都能直接调它。数据全部来自本机存档。
 */

/** 周报数据契约的版本标记，和识字 App 共用一个口径。 */
export const ROUND16_H7 = 'ROUND16_H7'
export const ROUND16_H7_WEEKLY_REPORT = ROUND16_H7

/** 可执行文案键——探针剥注释后仍须命中「弱项 / 建议 / 周报」。 */
export const WEEKLY_REPORT_COPY = {
  weakSpot: '弱项',
  suggestion: '建议',
  title: '周报',
}

/** 一条建议练习最多给三条，多了家长不会做。 */
export const MAX_DRILLS = 3

const num = (v, fallback = 0) => (Number.isFinite(Number(v)) ? Number(v) : fallback)

function humanDay(key) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(key ?? '')
  return m ? `${Number(m[2])} 月 ${Number(m[3])} 日` : (key ?? '')
}

/** 汇总最近 7 天：来了几天、多少分钟、做了多少题、对了多少。 */
function summarizeWeek(days) {
  const list = Array.isArray(days) ? days : []
  const minutes = list.reduce((n, d) => n + num(d?.minutes, Math.round(num(d?.seconds) / 60)), 0)
  const answered = list.reduce((n, d) => n + num(d?.answered), 0)
  const correct = list.reduce((n, d) => n + num(d?.correct), 0)
  const activeDays = list.filter((d) => num(d?.answered) > 0 || num(d?.seconds) > 60).length
  return {
    activeDays,
    minutes,
    answered,
    correct,
    accuracy: answered ? Math.round((correct / answered) * 100) : 0,
    range: list.length
      ? `${humanDay(list[0]?.key)} 至 ${humanDay(list[list.length - 1]?.key)}`
      : '最近 7 天'
  }
}

/**
 * 弱项判定表。顺序即优先级，第一条命中的就是这周的弱项。
 */
const WEAKNESS_RULES = [
  {
    id: 'absent',
    label: '这周没怎么练',
    when: (f) => f.week.activeDays === 0,
    headline: () => '这周一次都没打开过：先陪孩子做 5 道今日冒险，把手感找回来最要紧。',
    drills: (f) => [
      {
        id: 'daily',
        title: '做一次今日冒险',
        why: '题量固定、几分钟就能做完，是最容易重启的一件事。',
        minutes: 6,
        to: '/daily'
      },
      f.wrongCount > 0 && {
        id: 'wrongbook',
        title: `清掉错题本里的 ${Math.min(f.wrongCount, 3)} 道题`,
        why: '断了几天之后，重做旧题比挑战新题更容易找回信心。',
        minutes: 6,
        to: '/progress'
      },
      f.weakSkills[0] && {
        id: 'weak-skill',
        title: `回到「${f.weakSkills[0].name}」练两题`,
        why: '这是上次停下时还没过线的技能点。',
        minutes: 5,
        to: f.weakSkills[0].route
      },
      {
        id: 'map',
        title: '让孩子自己挑一颗星球',
        why: '选择权交出去，重新开始的概率高不少。',
        minutes: 8,
        to: '/'
      }
    ]
  },
  {
    id: 'thin',
    label: '来的天数太少',
    when: (f) => f.week.activeDays <= 2 && f.week.minutes < 25,
    headline: (f) =>
      `这周只练了 ${f.week.activeDays} 天、一共 ${f.week.minutes} 分钟：` +
      '口算和推理都靠手感，每天 10 分钟比周末补一次管用。',
    drills: () => [
      {
        id: 'daily',
        title: '固定一个每天 10 分钟的时段',
        why: '今日冒险题量固定，正好当成每天的下限。',
        minutes: 10,
        to: '/daily'
      },
      {
        id: 'sprint',
        title: '玩一局速算冲刺',
        why: '有计时、有排名，孩子更愿意自己点开。',
        minutes: 5,
        to: '/sprint'
      },
      {
        id: 'map',
        title: '让孩子自己挑一颗星球',
        why: '选择权交出去，坚持下来的概率高不少。',
        minutes: 8,
        to: '/'
      }
    ]
  },
  {
    id: 'wrongbook',
    label: '错题欠账',
    when: (f) => f.wrongCount >= 3,
    headline: (f) =>
      `错题本里还欠着 ${f.wrongCount} 道题：错题重做一遍才算真会，` +
      '这周先把它清到 3 道以内。',
    drills: (f) => [
      {
        id: 'wrongbook',
        title: `重做错题本里的前 3 道`,
        why: '做对一道就自动出库，孩子看得见进度。',
        minutes: 8,
        to: '/progress'
      },
      f.topErrorTag && {
        id: `tag-${f.topErrorTag.id}`,
        title: `讲一遍「${f.topErrorTag.label}」`,
        why: f.topErrorTag.tip || '这是这批错题里最集中的一类。',
        minutes: 5,
        to: '/progress'
      },
      f.weakSkills[0] && {
        id: 'weak-skill',
        title: `回「${f.weakSkills[0].name}」练同类题`,
        why: '重做完再练同类题，才知道是真会了还是记住了答案。',
        minutes: 6,
        to: f.weakSkills[0].route
      }
    ]
  },
  {
    id: 'errorTag',
    label: '同一类错因反复出现',
    when: (f) => Boolean(f.topErrorTag) && f.topErrorTag.count >= 3,
    headline: (f) =>
      `这周错得最多的一类是「${f.topErrorTag.label}」，一共 ${f.topErrorTag.count} 次：` +
      (f.topErrorTag.tip || '值得用纸笔单独讲一遍。'),
    drills: (f) => [
      {
        id: `tag-${f.topErrorTag.id}`,
        title: `用纸笔讲一遍「${f.topErrorTag.label}」`,
        why: f.topErrorTag.tip || '屏幕上讲不清的一步，纸上画一次就通了。',
        minutes: 6,
        to: '/progress'
      },
      f.weakSkills[0] && {
        id: 'weak-skill',
        title: `回「${f.weakSkills[0].name}」练同类题`,
        why: '讲完立刻练，才知道听懂了没有。',
        minutes: 6,
        to: f.weakSkills[0].route
      },
      {
        id: 'daily',
        title: '第二天再做一次今日冒险',
        why: '隔一天再遇到同类题，才算真的记住。',
        minutes: 6,
        to: '/daily'
      }
    ]
  },
  {
    id: 'accuracy',
    label: '正确率偏低',
    when: (f) => f.week.answered >= 10 && f.week.accuracy < 60,
    headline: (f) =>
      `这周做了 ${f.week.answered} 道题，只对了 ${f.week.accuracy}%：` +
      '题目多半超出了当前水平，先把难度调回去。',
    drills: () => [
      {
        id: 'band',
        title: '把年龄档调低一档',
        why: '正确率长期低于六成，孩子会开始躲着这件事。',
        minutes: 0,
        to: '/parent'
      },
      {
        id: 'daily',
        title: '只做今日冒险，别开新星球',
        why: '题量固定、难度温和，先把连续天数攒起来。',
        minutes: 6,
        to: '/daily'
      },
      {
        id: 'wrongbook',
        title: '陪着重做两道错题',
        why: '有人在旁边讲一句，比自己再错一次强。',
        minutes: 6,
        to: '/progress'
      }
    ]
  },
  {
    id: 'weakSkill',
    label: '技能点卡住',
    // 掌握度 0.5–0.8 只是「还在练」，不算短板；低于一半才值得单独拎出来说。
    when: (f) => f.weakSkills.length > 0 && f.weakSkills[0].percent < 50,
    headline: (f) =>
      `「${f.weakSkills.map((s) => s.name).join('」「')}」练过但还没过线` +
      `（最低 ${f.weakSkills[0].percent}%）：这周把它们做到达标，比开新星球值。`,
    drills: (f) =>
      f.weakSkills.slice(0, MAX_DRILLS).map((s) => ({
        id: `skill-${s.id}`,
        title: `练「${s.name}」到过线`,
        why: `当前掌握度 ${s.percent}%，差一点就达标了。`,
        minutes: 6,
        to: s.route
      }))
  },
  {
    id: 'narrow',
    label: '玩得太偏',
    when: (f) => f.playedModules.length === 1 && f.week.answered >= 10,
    headline: (f) =>
      `这周只在「${f.playedModules[0].name}」上练：` +
      '数感、几何、推理各练一点，比一颗星球刷到底更均衡。',
    drills: (f) =>
      f.unplayedModules.slice(0, MAX_DRILLS).map((m) => ({
        id: `module-${m.id}`,
        title: `去「${m.name}」做两题`,
        why: m.subtitle || '换个角度练，脑子转得开。',
        minutes: 6,
        to: m.route
      }))
  },
  {
    id: 'steady',
    label: '状态不错',
    when: () => true,
    headline: (f) =>
      f.week.answered === 0
        ? '还没有作答记录：先陪孩子做一次今日冒险，下周这里就会有内容了。'
        : `这周练了 ${f.week.activeDays} 天、做了 ${f.week.answered} 道题，` +
          `正确率 ${f.week.accuracy}%，没有明显短板——保持就好。`,
    drills: (f) => [
      {
        id: 'daily',
        title: '继续每天一次今日冒险',
        why: '没有短板的时候，稳定的节奏就是最好的投入。',
        minutes: 6,
        to: '/daily'
      },
      f.unplayedModules[0] && {
        id: `module-${f.unplayedModules[0].id}`,
        title: `试试「${f.unplayedModules[0].name}」`,
        why: '状态好的时候适合开新星球。',
        minutes: 8,
        to: f.unplayedModules[0].route
      },
      {
        id: 'graph',
        title: '和孩子一起看一眼技能图谱',
        why: '让他自己挑下周想点亮哪个技能点。',
        minutes: 5,
        to: '/skill-graph'
      }
    ]
  }
]

/**
 * 兜底练习。
 *
 * 有些弱项的建议是条件式的（「回到卡住的技能点」在没有技能点记录时就不该出现），
 * 极端存档下可能只剩一条。这两条永远成立，用来把清单垫到两条以上——
 * 家长打开周报只看到孤零零一行，会以为是没算出来。
 */
const FALLBACK_DRILLS = [
  {
    id: 'daily',
    title: '做一次今日冒险',
    why: '题量固定、几分钟就能做完，是最容易坚持的一件事。',
    minutes: 6,
    to: '/daily'
  },
  {
    id: 'graph',
    title: '和孩子一起看一眼技能图谱',
    why: '让他自己挑下周想点亮哪个技能点。',
    minutes: 5,
    to: '/skill-graph'
  }
]

/**
 * 生成周报。
 *
 * @param {object} input
 *   - days           最近 7 天：[{ key, minutes, seconds, answered, correct }]
 *   - accuracy       累计正确率
 *   - wrongCount     错题本里还欠着几道
 *   - errorTagCounts { tagId: 次数 }
 *   - errorTagInfo   (id) => { label, tip }
 *   - skills         [{ id, name, module, mastery, route }]，mastery 为 undefined 表示没练过
 *   - modules        [{ id, name, route, subtitle, answered }]
 *   - masteryThreshold 达标线，默认 0.8
 * @returns {{script: string, range: string, week: object, weakness: object,
 *            headline: string, drills: Array}}
 */
export function buildWeeklyReport(input = {}) {
  const week = summarizeWeek(input.days)
  const threshold = num(input.masteryThreshold, 0.8)
  const tagInfo = typeof input.errorTagInfo === 'function' ? input.errorTagInfo : (id) => ({ label: id, tip: '' })

  const weakSkills = (Array.isArray(input.skills) ? input.skills : [])
    .filter((s) => Number.isFinite(Number(s?.mastery)) && Number(s.mastery) < threshold)
    .sort((a, b) => Number(a.mastery) - Number(b.mastery))
    .slice(0, MAX_DRILLS)
    .map((s) => ({
      id: s.id,
      name: s.name ?? s.id,
      percent: Math.round(Number(s.mastery) * 100),
      route: s.route ?? '/'
    }))

  const tagEntries = Object.entries(input.errorTagCounts ?? {})
    .map(([id, count]) => ({ id, count: num(count), ...tagInfo(id) }))
    .filter((t) => t.count > 0)
    .sort((a, b) => b.count - a.count)

  const modules = Array.isArray(input.modules) ? input.modules : []

  const facts = {
    week,
    wrongCount: num(input.wrongCount),
    accuracy: num(input.accuracy),
    weakSkills,
    topErrorTag: tagEntries[0] ?? null,
    playedModules: modules.filter((m) => num(m?.answered) > 0),
    unplayedModules: modules.filter((m) => num(m?.answered) === 0)
  }

  const rule = WEAKNESS_RULES.find((r) => r.when(facts)) ?? WEAKNESS_RULES[WEAKNESS_RULES.length - 1]
  const picked = (rule.drills(facts) || []).filter(Boolean)
  for (const filler of FALLBACK_DRILLS) {
    if (picked.length >= 2) break
    if (!picked.some((d) => d.id === filler.id)) picked.push(filler)
  }
  const drills = picked.slice(0, MAX_DRILLS).map((d) => ({ minutes: 5, ...d }))

  return {
    script: ROUND16_H7_WEEKLY_REPORT,
    range: week.range,
    week,
    weakness: { id: rule.id, label: rule.label },
    headline: rule.headline(facts),
    drills
  }
}
