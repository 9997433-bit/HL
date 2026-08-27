/**
 * 今日冒险：每天三件小事。
 *
 * 这里没有新的学习内容，只是给已有玩法一个「今天先做哪三件」的说法：
 * 学新字、复习、绘本或成语、小游戏。孩子一睁眼就知道从哪儿开始，
 * 做完一件能亲手打上勾。
 *
 * 完成判定有两条腿：
 *  - 应用自己数得出来的（今天学了几个新字、答了几道题、读完几本绘本）
 *    会自动打勾。判定全部从 progress store 的既有 computed 派生，
 *    业务视图里一行都不用改——学字、读绘本、玩游戏的代码不知道有这张卡片；
 *  - 孩子也可以自己勾。在纸上读的绘本、和家长玩的字卡游戏，应用数不到，
 *    别让这些白做。手动勾选优先于自动判定，取消勾选同样算数。
 *
 * 进度单独存一份 localStorage：任务是「今天」的事，隔天就该换一批，
 * 而学习进度要一直留着，两者不该挤在同一个存档里。
 *
 * 接口与存档形状见 .agent_workspace/round5b-play-architecture.md §1。
 */

import { computed, reactive, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { useProgressStore } from './progress.js'

const STORAGE_KEY = 'happy-literacy:daily-quest:v1'

/** 每天摆出几件事。三件是刻意的：少到做得完，多到像一次小冒险。 */
export const DAILY_TASK_COUNT = 3

/** 第三个槽位在这三类里按天轮换，一周内绘本、成语、小游戏都会轮到。 */
const ROTATING_SLOT = ['story', 'idiom', 'game']

/**
 * 任务文案与判定规则。`metric` 指向下面 metrics 里的一项计数，
 * `daily` 为真表示这项计数本身就是「今天的量」，不必再减去当天开始时的基线。
 */
const TASK_SPECS = {
  learn: {
    emoji: '🈶',
    metric: 'newChars',
    daily: true,
    unit: '个',
    title: (n) => `学会 ${n} 个新字`,
    desc: '认一认、写一写，跟着墨墨走完一遍',
    to: '/learn',
    cta: '去学字'
  },
  review: {
    emoji: '🔁',
    metric: 'practices',
    unit: '次',
    title: (n) => `练 ${n} 次学过的字`,
    desc: '描红或答题都算，快忘掉的字要接住',
    to: '/learn',
    cta: '去复习'
  },
  story: {
    emoji: '📖',
    metric: 'books',
    unit: '本',
    title: () => '读完 1 本绘本',
    desc: '只用学过的字，从头读到尾',
    to: '/books',
    cta: '去读书'
  },
  idiom: {
    emoji: '🎭',
    metric: 'idioms',
    unit: '个',
    title: () => '看 1 个成语小剧场',
    desc: '四格故事，看懂一个成语',
    to: '/idioms',
    cta: '去看戏'
  },
  game: {
    emoji: '🎧',
    metric: 'gameRounds',
    unit: '局',
    title: (n) => `小游戏玩 ${n} 局`,
    desc: '听音识字，听一听就把字捞上来',
    to: '/listen',
    cta: '去玩'
  }
}

function todayKey(ts = Date.now()) {
  const d = new Date(ts)
  const m = `${d.getMonth() + 1}`.padStart(2, '0')
  const day = `${d.getDate()}`.padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

/** 「距 1970 年的第几天」，跨天自然 +1，用它给第三个槽位排轮次。 */
function dayIndexOf(key) {
  const [y, m, d] = key.split('-').map(Number)
  return Math.floor(Date.UTC(y, m - 1, d) / 86400000)
}

function defaultState() {
  return {
    dateKey: '',
    /** 今天这三件事的 id，第三件按天轮换。 */
    ids: [],
    /** 每件事的目标数，发任务时按当天情况定死，中途不再变。 */
    goals: {},
    /** 发任务那一刻的累计计数，用来只数「今天新做的那些」。 */
    base: {},
    /** 首次达成的时间戳；没达成是 null。 */
    doneAt: {},
    /** 孩子手动勾选的结果，true 勾上、false 取消，会盖过自动判定。 */
    manual: {},
    /** 已经撒过星星的任务，回到首页不会为同一件事重复庆祝。 */
    cheered: [],
    /** 三件全做完的奖励领过没有；每天一次。 */
    celebratedAt: null
  }
}

function loadState() {
  if (typeof localStorage === 'undefined') return defaultState()
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return defaultState()
    const saved = JSON.parse(raw)
    const base = defaultState()
    return {
      ...base,
      ...saved,
      goals: { ...(saved?.goals ?? {}) },
      base: { ...(saved?.base ?? {}) },
      doneAt: { ...(saved?.doneAt ?? {}) },
      manual: { ...(saved?.manual ?? {}) },
      cheered: [...(saved?.cheered ?? [])]
    }
  } catch {
    return defaultState()
  }
}

export const useDailyQuestStore = defineStore('dailyQuest', () => {
  const progress = useProgressStore()
  const state = reactive(loadState())

  /** 刚刚完成的那一件，卡片拿它放微庆祝；不持久化，看过就算。 */
  const justCompleted = ref(null)

  /**
   * 任务判定只认这一张计数表，取的全是 progress store 已经导出的东西。
   * 不为了这张卡片去动 progress 的导出面，也不在业务视图里插钩子。
   */
  const metrics = computed(() => {
    let quiz = 0
    for (const c of Object.values(progress.chars)) {
      quiz += (c.correct ?? 0) + (c.wrong ?? 0)
    }
    return {
      newChars: progress.newCharsToday,
      practices: quiz + progress.badgeStats.traced,
      books: progress.booksFinished,
      idioms: progress.idiomsSeen,
      gameRounds: progress.game.rounds
    }
  })

  /** 换了一天（或存档是空的）就重新发一批任务。 */
  function refresh() {
    const key = todayKey()
    if (state.dateKey === key && state.ids.length === DAILY_TASK_COUNT) return
    const rotating = ROTATING_SLOT[dayIndexOf(key) % ROTATING_SLOT.length]
    state.dateKey = key
    state.ids = ['learn', 'review', rotating]
    state.goals = {
      learn: Math.min(3, progress.dailyNewLimit || 3),
      // 没有到期的字就别硬凑，练三次也是练。
      review: progress.dueCount > 0 ? 5 : 3,
      story: 1,
      idiom: 1,
      game: 3
    }
    state.base = { ...metrics.value }
    state.doneAt = {}
    state.manual = {}
    state.cheered = []
    state.celebratedAt = null
  }

  const tasks = computed(() =>
    state.ids
      .filter((id) => TASK_SPECS[id])
      .map((id) => {
        const spec = TASK_SPECS[id]
        const goal = state.goals[id] ?? 1
        const raw = metrics.value[spec.metric] ?? 0
        const base = spec.daily ? 0 : (state.base[spec.metric] ?? 0)
        const value = Math.max(0, Math.min(goal, raw - base))
        const manual = state.manual[id]
        return {
          id,
          emoji: spec.emoji,
          title: spec.title(goal),
          desc: spec.desc,
          to: spec.to,
          cta: spec.cta,
          unit: spec.unit,
          goal,
          progress: value,
          percent: Math.round((value / goal) * 100),
          done: manual === true || (manual !== false && value >= goal),
          doneAt: state.doneAt[id] ?? null
        }
      })
  )

  const completedIds = computed(() => tasks.value.filter((t) => t.done).map((t) => t.id))
  const completedCount = computed(() => completedIds.value.length)
  const allDone = computed(
    () => tasks.value.length > 0 && completedCount.value === tasks.value.length
  )
  const percent = computed(() =>
    tasks.value.length ? Math.round((completedCount.value / tasks.value.length) * 100) : 0
  )

  /** 达成时间由 store 自己记，什么时候都不会漏。 */
  function stampDoneAt() {
    for (const id of completedIds.value) {
      if (!state.doneAt[id]) state.doneAt[id] = Date.now()
    }
  }

  /**
   * 领走还没庆祝过的那一件，没有就返回 null。
   *
   * 庆祝由卡片来领而不是 store 自己放，是因为大多数任务是在别的页面上完成的：
   * 孩子读完绘本、看完成语，回到首页这张卡片才刚挂上来，那一刻才轮到星星。
   * store 只记「哪些已经庆祝过了」，于是同一件事不会撒两次。
   */
  function flushCompletions() {
    stampDoneAt()
    const now = completedIds.value
    const fresh = now.filter((id) => !state.cheered.includes(id))
    state.cheered = [...now]
    if (!fresh.length) return null
    const latest = fresh[fresh.length - 1]
    const task = tasks.value.find((t) => t.id === latest)
    justCompleted.value = { id: latest, title: task?.title ?? '', at: Date.now() }
    return justCompleted.value
  }

  /** 三件全做完且今天还没领过奖 → 记账并返回 true。重复调用只会成功一次。 */
  function claimCelebration() {
    if (!allDone.value || state.celebratedAt) return false
    state.celebratedAt = Date.now()
    return true
  }

  /** 孩子亲手勾一件事；返回勾完之后是不是「已完成」。 */
  function toggle(id) {
    const task = tasks.value.find((t) => t.id === id)
    if (!task) return false
    state.manual[id] = !task.done
    return state.manual[id]
  }

  /** 家长中心「今天重来」用：擦掉手动勾选，任务本身不换。 */
  function clearChecks() {
    state.manual = {}
    state.cheered = [...completedIds.value]
  }

  function persist() {
    if (typeof localStorage === 'undefined') return
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
    } catch {
      /* 隐私模式 / 配额用尽，静默失败，不影响本次使用 */
    }
  }

  // 先挂监听再发任务，翻天重置也就跟着落盘了。
  watch(() => JSON.stringify(state), persist, { flush: 'post' })
  watch(completedIds, stampDoneAt)
  refresh()

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
    flushCompletions,
    claimCelebration,
    toggle,
    clearChecks
  }
})
