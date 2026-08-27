/**
 * 今日冒险：每天三件小事。
 *
 * 这里没有新的学习内容，只是给已有玩法一个「今天先做哪三件」的说法。
 * 四类任务——学新字、复习、绘本或成语、小游戏——每天轮着取三类，
 * 孩子一睁眼就知道从哪儿开始，做完一件能亲手打上勾。
 *
 * 完成判定有两条腿：
 *  - 应用自己数得出来的（今天学了几个新字、复习了几张记忆卡、读完几本绘本）
 *    会自动打勾，孩子玩着玩着任务就完成了，不必回来汇报；
 *  - 孩子也可以自己勾。在纸上读的绘本、和家长玩的字卡游戏，应用数不到，
 *    别让这些白做。手动勾选优先于自动判定，取消勾选同样算数。
 *
 * 进度单独存一份 localStorage，不混进学习存档：任务是「今天」的事，
 * 隔天就该换一批，而学习进度要一直留着。
 */

import { computed, reactive, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { useProgressStore } from './progress.js'

const STORAGE_KEY = 'happy-literacy:daily-quest:v1'

/** 每天摆出几件事。三件是刻意的：少到做得完，多到像一次小冒险。 */
export const DAILY_TASK_COUNT = 3

/** 四类任务轮着来，每天取相邻的三类，于是每天的组合都不一样。 */
const SLOT_ORDER = ['learn', 'review', 'story', 'play']

/**
 * 任务模板池。同一类里放两个的，会按天交替出现。
 *
 *  - `metric` 指向下面 metrics 里的一项计数；
 *  - `daily` 为真表示这项计数本身就是「今天的量」，不必再减去开始时的基线。
 */
export const DAILY_TASKS = [
  {
    id: 'learn-new',
    slot: 'learn',
    emoji: '🈶',
    metric: 'newChars',
    daily: true,
    goal: 2,
    unit: '个',
    title: (n) => `学会 ${n} 个新字`,
    desc: '认一认、写一写，跟着墨墨走完一遍',
    to: '/learn',
    cta: '去学字'
  },
  {
    id: 'review-due',
    slot: 'review',
    emoji: '🔁',
    metric: 'reviews',
    daily: true,
    goal: 3,
    unit: '个',
    title: (n) => `复习 ${n} 个学过的字`,
    desc: '快忘掉的字回来敲门了，接住它们',
    to: '/learn',
    cta: '去复习'
  },
  {
    id: 'read-book',
    slot: 'story',
    emoji: '📖',
    metric: 'books',
    goal: 1,
    unit: '本',
    title: () => '读完 1 本绘本',
    desc: '只用学过的字，从头读到尾',
    to: '/books',
    cta: '去读书'
  },
  {
    id: 'read-idiom',
    slot: 'story',
    emoji: '🎭',
    metric: 'idioms',
    goal: 1,
    unit: '个',
    title: () => '看 1 个成语小剧场',
    desc: '四格故事，看懂一个成语',
    to: '/idioms',
    cta: '去看戏'
  },
  {
    id: 'play-game',
    slot: 'play',
    emoji: '🎲',
    metric: 'answers',
    goal: 5,
    unit: '题',
    title: (n) => `在小游戏里答 ${n} 题`,
    desc: '迷宫、配对、找不同，随便挑一个',
    to: '/games',
    cta: '去玩'
  },
  {
    id: 'listen-quiz',
    slot: 'play',
    emoji: '🎧',
    metric: 'listenRight',
    goal: 4,
    unit: '次',
    title: (n) => `听音识字答对 ${n} 次`,
    desc: '听一听，把正确的字捞上来',
    to: '/listen',
    cta: '去闯关'
  }
]

const TASK_MAP = new Map(DAILY_TASKS.map((t) => [t.id, t]))

function todayKey(ts = Date.now()) {
  const d = new Date(ts)
  const m = `${d.getMonth() + 1}`.padStart(2, '0')
  const day = `${d.getDate()}`.padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

function startOfToday(ts = Date.now()) {
  const d = new Date(ts)
  d.setHours(0, 0, 0, 0)
  return d.getTime()
}

/** 「距 1970 年的第几天」，跨天自然 +1，用它给任务组合排轮次。 */
function dayIndexOf(key) {
  const [y, m, d] = key.split('-').map(Number)
  return Math.floor(Date.UTC(y, m - 1, d) / 86400000)
}

/** 取轮到的三类，再在每一类里按天挑一个模板。 */
export function pickTaskIds(index) {
  const slots = new Set()
  for (let i = 0; i < DAILY_TASK_COUNT; i += 1) {
    slots.add(SLOT_ORDER[(index + i) % SLOT_ORDER.length])
  }
  return SLOT_ORDER.filter((slot) => slots.has(slot)).map((slot) => {
    const pool = DAILY_TASKS.filter((t) => t.slot === slot)
    return pool[index % pool.length].id
  })
}

function defaultState() {
  return {
    day: '',
    ids: [],
    /** 生成任务那一刻的累计计数，用来只数「今天新做的那些」。 */
    baseline: {},
    /** 手动勾选结果：true 勾上、false 取消，没有记录就听自动判定的。 */
    checked: {},
    /** 已经为哪一天放过「三件全做完」的庆祝，避免刷新一次庆祝一次。 */
    celebratedDay: ''
  }
}

function loadState() {
  if (typeof localStorage === 'undefined') return defaultState()
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return defaultState()
    const saved = JSON.parse(raw)
    return {
      ...defaultState(),
      ...saved,
      baseline: { ...(saved?.baseline ?? {}) },
      checked: { ...(saved?.checked ?? {}) }
    }
  } catch {
    return defaultState()
  }
}

export const useDailyQuestStore = defineStore('dailyQuest', () => {
  const progress = useProgressStore()
  const state = reactive(loadState())

  /** 刚刚完成的那一件，界面拿它放微庆祝；不持久化，看过就算。 */
  const justCompleted = ref(null)

  /** 任务判定只认这一张计数表。 */
  const metrics = computed(() => {
    const saved = progress.state
    let answers = 0
    for (const c of Object.values(saved.chars)) {
      answers += (c.quizRight ?? 0) + (c.quizWrong ?? 0)
    }
    const since = startOfToday()
    let reviews = 0
    for (const card of Object.values(saved.srs)) {
      if ((card.lastReviewAt ?? 0) >= since) reviews += 1
    }
    return {
      newChars: progress.newCharsToday,
      reviews,
      answers,
      listenRight: saved.listen.right,
      books: progress.booksFinished,
      idioms: progress.idiomsSeen
    }
  })

  /** 换了一天（或存档是空的）就重新发一批任务。 */
  function refresh() {
    const key = todayKey()
    if (state.day === key && state.ids.length === DAILY_TASK_COUNT) return
    state.day = key
    state.ids = pickTaskIds(dayIndexOf(key))
    state.baseline = { ...metrics.value }
    state.checked = {}
  }

  refresh()

  const tasks = computed(() =>
    state.ids
      .map((id) => TASK_MAP.get(id))
      .filter(Boolean)
      .map((t) => {
        const raw = metrics.value[t.metric] ?? 0
        const base = t.daily ? 0 : (state.baseline[t.metric] ?? 0)
        const value = Math.max(0, Math.min(t.goal, raw - base))
        const auto = value >= t.goal
        const manual = state.checked[t.id]
        return {
          id: t.id,
          emoji: t.emoji,
          title: t.title(t.goal),
          desc: t.desc,
          to: t.to,
          cta: t.cta,
          goal: t.goal,
          unit: t.unit,
          value,
          percent: Math.round((value / t.goal) * 100),
          auto,
          done: manual === true || (manual !== false && auto)
        }
      })
  )

  const completedIds = computed(() => tasks.value.filter((t) => t.done).map((t) => t.id))
  const completedCount = computed(() => completedIds.value.length)
  const allDone = computed(() => tasks.value.length > 0 && completedCount.value === tasks.value.length)
  const percent = computed(() =>
    tasks.value.length ? Math.round((completedCount.value / tasks.value.length) * 100) : 0
  )

  /** 孩子亲手勾一件事；返回勾完之后是不是「已完成」。 */
  function toggle(id) {
    const task = tasks.value.find((t) => t.id === id)
    if (!task) return false
    state.checked[id] = !task.done
    return state.checked[id]
  }

  /** 家长中心「重来一次」用：把今天的勾全部擦掉，任务本身不换。 */
  function clearChecks() {
    state.checked = {}
  }

  watch(completedIds, (now, before = []) => {
    const fresh = now.find((id) => !before.includes(id))
    if (fresh) {
      const task = tasks.value.find((t) => t.id === fresh)
      justCompleted.value = { id: fresh, title: task?.title ?? '', at: Date.now() }
    }
    if (now.length === DAILY_TASK_COUNT && state.celebratedDay !== state.day) {
      state.celebratedDay = state.day
      progress.celebrate({
        kind: 'quest',
        emoji: '🏅',
        title: '今日冒险全部完成！',
        subtitle: '明天还有三件新的小事等着你'
      })
    }
  })

  function persist() {
    if (typeof localStorage === 'undefined') return
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
    } catch {
      /* 隐私模式 / 配额用尽，静默失败，不影响本次使用 */
    }
  }

  watch(() => JSON.stringify(state), persist, { flush: 'post' })

  return {
    state,
    tasks,
    metrics,
    justCompleted,
    completedIds,
    completedCount,
    allDone,
    percent,
    refresh,
    toggle,
    clearChecks
  }
})
