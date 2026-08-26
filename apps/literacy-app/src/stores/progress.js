/**
 * 全局进度与设置。
 *
 * 设计要点：
 *  - 一切都存在 localStorage，不上传任何数据，家长面板里可一键导出/清空；
 *  - 每个字有 0-3 四级掌握度，是首页地图、复习推荐和家长报表的共同数据源；
 *  - 主题 / 字号 / 动效这些「外观」设置直接写到 <html> 的 data-* 上，
 *    由 styles/theme.css 接管，组件里不需要各自判断。
 */

import { computed, reactive, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { CHARACTERS, TOTAL_CHARACTERS, UNITS } from '@/data/characters.js'
import { BOOKS } from '@/data/books.js'
import { IDIOMS } from '@/data/idioms.js'
import { RADICALS } from '@/data/radicals.js'
import { setSoundEnabled, setSpeechEnabled } from '@/utils/audio.js'

const STORAGE_KEY = 'happy-literacy:v1'

export const MASTERY_THRESHOLD = 3

/** 掌握度四级，界面文案与颜色都从这里取。 */
export const MASTERY = [
  { level: 0, label: '没学过', short: '新', color: 'var(--stroke-hint)' },
  { level: 1, label: '认识了', short: '认', color: 'var(--seed-sky)' },
  { level: 2, label: '会写了', short: '写', color: 'var(--seed-mint)' },
  { level: 3, label: '真掌握', short: '棒', color: 'var(--seed-mango)' }
]

/** 升到下一级需要的经验，随等级线性增长。 */
const xpForLevel = (level) => 60 + (level - 1) * 40

function emptyChar() {
  return {
    seen: 0,
    heard: 0,
    traced: 0,
    quizRight: 0,
    quizWrong: 0,
    level: 0,
    firstAt: null,
    lastAt: null
  }
}

function todayKey(ts = Date.now()) {
  const d = new Date(ts)
  const m = `${d.getMonth() + 1}`.padStart(2, '0')
  const day = `${d.getDate()}`.padStart(2, '0')
  return `${d.getFullYear()}-${m}-${day}`
}

function defaultState() {
  return {
    childName: '小朋友',
    avatar: '🐣',

    settings: {
      theme: 'sunny',
      fontScale: 'normal',
      motion: 'full',
      sound: true,
      speech: true,
      showPinyin: true,
      /** 连续使用多少分钟后弹护眼休息提醒；0 表示关闭。 */
      restReminderMin: 20,
      /** 每天目标学字数，家长面板可调。 */
      dailyGoal: 5,
      /** 听音识字的场景皮肤：card / fish / mole。 */
      listenSkin: 'fish'
    },

    stars: 0,
    xp: 0,
    level: 1,

    chars: {},
    books: {},
    idioms: {},
    radicals: {},

    listen: { rounds: 0, right: 0, wrong: 0, bestStreak: 0 },

    /** 按天聚合：{ '2026-08-26': { seconds, chars: [...], stars, quizRight, quizWrong } } */
    daily: {},

    createdAt: Date.now()
  }
}

function migrate(saved) {
  const base = defaultState()
  if (!saved || typeof saved !== 'object') return base
  return {
    ...base,
    ...saved,
    settings: { ...base.settings, ...(saved.settings || {}) },
    chars: { ...(saved.chars || {}) },
    books: { ...(saved.books || {}) },
    idioms: { ...(saved.idioms || {}) },
    radicals: { ...(saved.radicals || {}) },
    listen: { ...base.listen, ...(saved.listen || {}) },
    daily: { ...(saved.daily || {}) }
  }
}

function loadState() {
  if (typeof localStorage === 'undefined') return defaultState()
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? migrate(JSON.parse(raw)) : defaultState()
  } catch {
    return defaultState()
  }
}

export const useProgressStore = defineStore('progress', () => {
  const state = reactive(loadState())

  /** 待播放的庆祝事件，由 App.vue 的彩带层消费。 */
  const pendingCelebration = ref(null)
  /** 本次打开页面已连续学习的秒数，用于护眼提醒；不持久化。 */
  const sessionSeconds = ref(0)
  const restDue = ref(false)

  /* ---------------------------------------------------------------- 派生 */

  const charStat = (char) => state.chars[char] ?? emptyChar()

  const learnedChars = computed(() =>
    CHARACTERS.filter((c) => (state.chars[c.char]?.level ?? 0) >= 1)
  )

  const masteredChars = computed(() =>
    CHARACTERS.filter((c) => (state.chars[c.char]?.level ?? 0) >= 3)
  )

  const learnedCount = computed(() => learnedChars.value.length)

  const overallProgress = computed(() =>
    TOTAL_CHARACTERS === 0 ? 0 : learnedCount.value / TOTAL_CHARACTERS
  )

  const xpToNext = computed(() => xpForLevel(state.level))
  const levelProgress = computed(() => Math.min(1, state.xp / xpToNext.value))

  const unitProgress = (unitId) => {
    const chars = CHARACTERS.filter((c) => c.unit === unitId)
    if (!chars.length) return { total: 0, learned: 0, done: 0, mastered: 0, ratio: 0, percent: 0 }
    const learned = chars.filter((c) => (state.chars[c.char]?.level ?? 0) >= 1).length
    const mastered = chars.filter((c) => (state.chars[c.char]?.level ?? 0) >= 3).length
    const ratio = learned / chars.length
    return {
      total: chars.length,
      learned,
      /** `done` 是 `learned` 的别名，给按「完成了几个」叙述的界面用。 */
      done: learned,
      mastered,
      ratio,
      percent: Math.round(ratio * 100)
    }
  }

  /**
   * 单元解锁：第一单元永远开着，后面的单元要求上一单元学会 60%。
   * 门槛不高，目的是给孩子一个「按顺序推进」的暗示，而不是真的拦住他。
   */
  const unlockedUnits = computed(() => {
    const out = {}
    let open = true
    for (const u of UNITS) {
      out[u.id] = open
      open = open && unitProgress(u.id).ratio >= 0.6
    }
    return out
  })

  const booksFinished = computed(() => BOOKS.filter((b) => state.books[b.id]?.finishedAt).length)
  const idiomsRead = computed(() => IDIOMS.filter((i) => state.idioms[i.id]?.read).length)
  const radicalsSeen = computed(() => RADICALS.filter((r) => state.radicals[r.id]?.seen).length)

  const quizTotals = computed(() => {
    let right = 0
    let wrong = 0
    for (const s of Object.values(state.chars)) {
      right += s.quizRight ?? 0
      wrong += s.quizWrong ?? 0
    }
    return { right, wrong, total: right + wrong }
  })

  const accuracy = computed(() => {
    const { right, total } = quizTotals.value
    return total === 0 ? 0 : Math.round((right / total) * 100)
  })

  const today = computed(() => state.daily[todayKey()] ?? { seconds: 0, chars: [], stars: 0 })

  const todayNewChars = computed(() => today.value.chars?.length ?? 0)

  const dailyGoalReached = computed(() => todayNewChars.value >= state.settings.dailyGoal)

  /** 最近 14 天的学习曲线，家长面板画柱状图用。 */
  const recentDays = computed(() => {
    const out = []
    for (let i = 13; i >= 0; i -= 1) {
      const key = todayKey(Date.now() - i * 86400000)
      const d = state.daily[key]
      out.push({
        key,
        label: key.slice(5),
        minutes: Math.round((d?.seconds ?? 0) / 60),
        chars: d?.chars?.length ?? 0,
        stars: d?.stars ?? 0
      })
    }
    return out
  })

  /** 连续学习天数。 */
  const streakDays = computed(() => {
    let n = 0
    for (let i = 0; i < 400; i += 1) {
      const key = todayKey(Date.now() - i * 86400000)
      const d = state.daily[key]
      const active = (d?.chars?.length ?? 0) > 0 || (d?.seconds ?? 0) > 60
      if (active) n += 1
      else if (i > 0) break
    }
    return n
  })

  /**
   * 复习推荐：优先挑「学过但还没掌握」的字，
   * 其次按最久没碰过排序——这是最省事也最有效的间隔重复近似。
   */
  const reviewQueue = computed(() => {
    const now = Date.now()
    return CHARACTERS.filter((c) => {
      const s = state.chars[c.char]
      return s && s.level >= 1 && s.level < 3
    })
      .sort((a, b) => {
        const sa = state.chars[a.char]
        const sb = state.chars[b.char]
        const wa = (now - (sa.lastAt ?? 0)) * (4 - sa.level)
        const wb = (now - (sb.lastAt ?? 0)) * (4 - sb.level)
        return wb - wa
      })
      .slice(0, 12)
  })

  /** 下一个还没学的字，首页「继续学习」按钮用。 */
  const nextChar = computed(
    () => CHARACTERS.find((c) => (state.chars[c.char]?.level ?? 0) === 0) ?? CHARACTERS[0]
  )

  /* ---------------------------------------------------------------- 内部 */

  function ensureChar(char) {
    if (!state.chars[char]) state.chars[char] = emptyChar()
    const s = state.chars[char]
    if (!s.firstAt) s.firstAt = Date.now()
    s.lastAt = Date.now()
    return s
  }

  function ensureToday() {
    const key = todayKey()
    if (!state.daily[key]) state.daily[key] = { seconds: 0, chars: [], stars: 0 }
    return state.daily[key]
  }

  function markNewCharToday(char) {
    const d = ensureToday()
    if (!d.chars.includes(char)) d.chars.push(char)
  }

  function addXp(amount) {
    state.xp += amount
    let leveled = false
    while (state.xp >= xpForLevel(state.level)) {
      state.xp -= xpForLevel(state.level)
      state.level += 1
      leveled = true
    }
    if (leveled) celebrate({ kind: 'level', title: `升到 ${state.level} 级啦！`, emoji: '🎉' })
  }

  function addStars(n) {
    if (n <= 0) return
    state.stars += n
    ensureToday().stars += n
  }

  /**
   * 重新计算某个字的掌握度。
   * 认识（听过或看过）→ 1；描红成功过 → 2；测验答对 2 次以上且正确率过半 → 3。
   */
  function recomputeLevel(char) {
    const s = state.chars[char]
    if (!s) return 0
    let level = 0
    if (s.seen > 0 || s.heard > 0) level = 1
    if (level >= 1 && s.traced > 0) level = 2
    if (level >= 2 && s.quizRight >= 2 && s.quizRight > s.quizWrong) level = 3
    const before = s.level
    s.level = level
    if (level > before) {
      if (before === 0) markNewCharToday(char)
      addStars(level - before)
      addXp((level - before) * 12)
      if (level === 3) {
        celebrate({ kind: 'master', title: `「${char}」掌握啦！`, emoji: '🏆', char })
      }
    }
    return level
  }

  /* ---------------------------------------------------------------- 动作 */

  /** 打开了某个字的学习页。 */
  function markSeen(char) {
    const s = ensureChar(char)
    s.seen += 1
    recomputeLevel(char)
  }

  /** 听了这个字的读音。 */
  function markHeard(char) {
    const s = ensureChar(char)
    s.heard += 1
    recomputeLevel(char)
  }

  /** 描红完成一遍。 */
  function markTraced(char) {
    const s = ensureChar(char)
    s.traced += 1
    recomputeLevel(char)
    addXp(8)
  }

  /** 记录一次测验作答（听音识字、成语小测都走这里）。 */
  function recordQuiz(char, correct) {
    const s = ensureChar(char)
    if (correct) {
      s.quizRight += 1
      addXp(6)
    } else {
      s.quizWrong += 1
      addXp(1)
    }
    recomputeLevel(char)
  }

  function recordListenRound({ right = 0, wrong = 0, bestStreak = 0 } = {}) {
    state.listen.rounds += 1
    state.listen.right += right
    state.listen.wrong += wrong
    state.listen.bestStreak = Math.max(state.listen.bestStreak, bestStreak)
    if (right > 0) addStars(Math.ceil(right / 2))
  }

  function markBookPage(bookId, pageIndex) {
    const b = state.books[bookId] ?? (state.books[bookId] = { pagesRead: 0, finishedAt: null })
    b.pagesRead = Math.max(b.pagesRead, pageIndex + 1)
    b.lastAt = Date.now()
  }

  function finishBook(bookId) {
    const b = state.books[bookId] ?? (state.books[bookId] = { pagesRead: 0, finishedAt: null })
    if (!b.finishedAt) {
      b.finishedAt = Date.now()
      addStars(5)
      addXp(30)
      celebrate({ kind: 'book', title: '一本绘本读完啦！', emoji: '📖', stars: 5 })
    }
    b.times = (b.times ?? 0) + 1
  }

  function markIdiomRead(idiomId) {
    const i = state.idioms[idiomId] ?? (state.idioms[idiomId] = { read: false, quizRight: 0 })
    if (!i.read) {
      i.read = true
      addStars(2)
      addXp(12)
    }
    i.seen = true
    i.lastAt = Date.now()
  }

  function recordIdiomQuiz(idiomId, correct) {
    const i = state.idioms[idiomId] ?? (state.idioms[idiomId] = { read: true, quizRight: 0 })
    if (correct) {
      i.quizRight += 1
      addStars(1)
      addXp(8)
    } else {
      i.quizWrong = (i.quizWrong ?? 0) + 1
      addXp(2)
    }
  }

  function markRadicalSeen(radicalId) {
    const r = state.radicals[radicalId] ?? (state.radicals[radicalId] = { seen: 0 })
    r.seen += 1
    if (r.seen === 1) addXp(5)
  }

  /**
   * 累计学习时长并在坐得太久时触发护眼提醒。
   * 传秒数是为了让「每 15 秒对一次表」这种低频计时器也能算准。
   */
  function addSeconds(delta = 1) {
    const secs = Math.max(0, Math.round(delta))
    if (!secs) return
    sessionSeconds.value += secs
    ensureToday().seconds += secs
    const limit = state.settings.restReminderMin
    if (limit > 0 && sessionSeconds.value >= limit * 60) restDue.value = true
  }

  /** 计时器每秒调一次。 */
  function tickSecond() {
    addSeconds(1)
  }

  function acknowledgeRest() {
    restDue.value = false
    sessionSeconds.value = 0
  }

  function celebrate(payload) {
    pendingCelebration.value = { ...payload, at: Date.now() }
  }

  function clearCelebration() {
    pendingCelebration.value = null
  }

  /* -------------------------------------------------------------- 设置 */

  function applyAppearance() {
    if (typeof document === 'undefined') return
    const root = document.documentElement
    root.dataset.theme = state.settings.theme
    root.dataset.fontScale = state.settings.fontScale
    root.dataset.motion = state.settings.motion
    setSoundEnabled(state.settings.sound)
    setSpeechEnabled(state.settings.speech)
  }

  function updateSettings(patch) {
    Object.assign(state.settings, patch)
    applyAppearance()
  }

  /** 护眼模式开关：在明亮与护眼之间切换，夜间模式单独选。 */
  function toggleEyeCare() {
    updateSettings({ theme: state.settings.theme === 'care' ? 'sunny' : 'care' })
  }

  function cycleTheme() {
    const order = ['sunny', 'care', 'night']
    const next = order[(order.indexOf(state.settings.theme) + 1) % order.length]
    updateSettings({ theme: next })
  }

  function setProfile({ childName, avatar }) {
    if (typeof childName === 'string' && childName.trim()) state.childName = childName.trim().slice(0, 12)
    if (avatar) state.avatar = avatar
  }

  /* -------------------------------------------------------- 持久化 / 导出 */

  function persist() {
    if (typeof localStorage === 'undefined') return
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
    } catch {
      /* 隐私模式 / 配额用尽，静默失败，不影响本次使用 */
    }
  }

  function exportJson() {
    return JSON.stringify({ app: 'happy-literacy', version: 1, data: state }, null, 2)
  }

  function importJson(text) {
    try {
      const parsed = JSON.parse(text)
      const payload = parsed?.data ?? parsed
      Object.assign(state, migrate(payload))
      applyAppearance()
      persist()
      return true
    } catch {
      return false
    }
  }

  function resetProgress() {
    const keepSettings = { ...state.settings }
    const keepName = state.childName
    const keepAvatar = state.avatar
    Object.assign(state, defaultState())
    state.settings = keepSettings
    state.childName = keepName
    state.avatar = keepAvatar
    applyAppearance()
    persist()
  }

  function resetAll() {
    Object.assign(state, defaultState())
    applyAppearance()
    persist()
  }

  /* ------------------------------------------------------------ 扁平视图层
   *
   * 上面那套接口围绕 `state` 组织，适合写 store 逻辑；页面组件则更愿意直接问
   * 「这个字学过没有」「绘本读到百分之几」。下面这一层就是把同一份数据换个说法
   * 讲一遍：只读的部分做成 computed，动作则是上面动作的薄封装。
   * 两套接口共享同一份 state，怎么混用都不会出现两个互相打架的进度。
   */

  const totalChars = TOTAL_CHARACTERS
  const masteredCount = computed(() => masteredChars.value.length)
  const overallPercent = computed(() => Math.round(overallProgress.value * 100))

  const isLearned = (char) => (state.chars[char]?.level ?? 0) >= 1
  const isMastered = (char) => (state.chars[char]?.level ?? 0) >= MASTERY_THRESHOLD

  /** 逐字统计，字段名换成页面惯用的说法。 */
  const chars = computed(() => {
    const out = {}
    for (const [char, s] of Object.entries(state.chars)) {
      out[char] = { ...s, views: s.seen ?? 0, correct: s.quizRight ?? 0, wrong: s.quizWrong ?? 0 }
    }
    return out
  })

  const books = computed(() => {
    const out = {}
    for (const [id, b] of Object.entries(state.books)) {
      out[id] = { ...b, finished: Boolean(b.finishedAt) }
    }
    return out
  })

  const idioms = computed(() => {
    const out = {}
    for (const [id, i] of Object.entries(state.idioms)) {
      out[id] = { ...i, seen: Boolean(i.seen || i.read) }
    }
    return out
  })

  const stars = computed(() => state.stars)
  const level = computed(() => state.level)
  const daily = computed(() => state.daily)
  const todayStats = today
  const idiomsSeen = idiomsRead
  const lastActiveDay = computed(() => todayKey())

  const last7Days = computed(() => {
    const out = []
    for (let i = 6; i >= 0; i -= 1) {
      const key = todayKey(Date.now() - i * 86400000)
      const d = state.daily[key]
      out.push({
        key,
        label: key.slice(5),
        seconds: d?.seconds ?? 0,
        newChars: d?.chars?.length ?? 0,
        stars: d?.stars ?? 0
      })
    }
    return out
  })

  const game = computed(() => ({
    plays: state.listen.rounds,
    rounds: state.listen.rounds,
    correct: state.listen.right,
    right: state.listen.right,
    wrong: state.listen.wrong,
    bestStreak: state.listen.bestStreak
  }))

  const gameAccuracy = computed(() => {
    const { right, wrong } = state.listen
    return right + wrong === 0 ? 0 : Math.round((right / (right + wrong)) * 100)
  })

  /** 打开某个字的学习页。 */
  const visitChar = markSeen

  /** 看过某个偏旁的讲解。 */
  const viewRadical = markRadicalSeen

  const markIdiomSeen = markIdiomRead

  function markIdiomQuiz(idiomId, correct = true) {
    recordIdiomQuiz(idiomId, correct)
  }

  /** 记一次作答，并告诉调用方这一下是不是刚好把字练成了「掌握」。 */
  function recordAnswer(char, correct = true) {
    const before = state.chars[char]?.level ?? 0
    recordQuiz(char, correct)
    const after = state.chars[char]?.level ?? 0
    return {
      level: after,
      justMastered: before < MASTERY_THRESHOLD && after >= MASTERY_THRESHOLD
    }
  }

  function recordGameRound({ correct = false, streak = 0 } = {}) {
    state.listen.rounds += 1
    if (correct) {
      state.listen.right += 1
      addStars(1)
    } else {
      state.listen.wrong += 1
    }
    state.listen.bestStreak = Math.max(state.listen.bestStreak, streak)
  }

  /** 读到绘本第 pageIndex 页；读到最后一页时顺手结本，并说明是不是第一次读完。 */
  function readPage(bookId, pageIndex, total) {
    const firstTimeFinishing =
      total != null && pageIndex >= total - 1 && !state.books[bookId]?.finishedAt
    markBookPage(bookId, pageIndex)
    if (firstTimeFinishing) finishBook(bookId)
    return { firstFinish: firstTimeFinishing }
  }

  function bookPercent(bookId, totalPages) {
    if (!totalPages) return 0
    const read = state.books[bookId]?.pagesRead ?? 0
    return Math.min(100, Math.round((read / totalPages) * 100))
  }

  applyAppearance()
  watch(() => JSON.stringify(state), persist, { flush: 'post' })

  return {
    state,
    pendingCelebration,
    sessionSeconds,
    restDue,

    charStat,
    learnedChars,
    masteredChars,
    learnedCount,
    overallProgress,
    xpToNext,
    levelProgress,
    unitProgress,
    booksFinished,
    idiomsRead,
    radicalsSeen,
    quizTotals,
    accuracy,
    today,
    todayNewChars,
    dailyGoalReached,
    recentDays,
    streakDays,
    reviewQueue,
    nextChar,

    markSeen,
    markHeard,
    markTraced,
    recordQuiz,
    recordListenRound,
    markBookPage,
    finishBook,
    markIdiomRead,
    recordIdiomQuiz,
    markRadicalSeen,
    tickSecond,
    acknowledgeRest,
    celebrate,
    clearCelebration,

    applyAppearance,
    updateSettings,
    toggleEyeCare,
    cycleTheme,
    setProfile,

    exportJson,
    importJson,
    resetProgress,
    resetAll,

    /* ---------------------------------------------------------- 扁平视图层 */
    totalChars,
    masteredCount,
    overallPercent,
    unlockedUnits,
    isLearned,
    isMastered,
    chars,
    books,
    idioms,
    stars,
    level,
    daily,
    todayStats,
    lastActiveDay,
    last7Days,
    idiomsSeen,
    game,
    gameAccuracy,

    addSeconds,
    visitChar,
    viewRadical,
    markIdiomSeen,
    markIdiomQuiz,
    recordAnswer,
    recordGameRound,
    readPage,
    bookPercent,

    exportJSON: exportJson,
    importJSON: importJson
  }
})
