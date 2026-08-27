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
import {
  CHARACTER_MAP,
  CHARACTERS,
  TOTAL_CHARACTERS,
  UNITS
} from '@/data/characters.js'
import { BADGES, TOTAL_BADGES } from '@/data/badges.js'
import { BOOKS } from '@/data/books.js'
import { RADICALS } from '@/data/radicals.js'
import { setSoundEnabled, setSpeechEnabled } from '@/utils/audio.js'
import { RATING, createCard, dueCards, retention, schedule } from '@/utils/srs.js'

const STORAGE_KEY = 'happy-literacy:v1'

export const MASTERY_THRESHOLD = 3

/** 掌握度四级，界面文案与颜色都从这里取。 */
export const MASTERY = [
  { level: 0, label: '没学过', short: '新', color: 'var(--stroke-hint)' },
  { level: 1, label: '认识了', short: '认', color: 'var(--sky-400)' },
  { level: 2, label: '会写了', short: '写', color: 'var(--mint-400)' },
  { level: 3, label: '真掌握', short: '棒', color: 'var(--mango-400)' }
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
    /** 完整走完「认—写—听—考—奖」五步的次数。 */
    flows: 0,
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
      /**
       * 学习计划（家长面板设置）：
       *  - dailyNewLimit 每天最多学几个新字，0 表示不设上限；
       *  - planUnits     只学这几个单元，空数组表示按课程顺序学全部。
       * 计划只影响「今天学什么」的推荐，不会锁住孩子已经学过的字，
       * 也不会拦住到期的复习——复习是记忆曲线说了算的。
       */
      dailyNewLimit: 8,
      planUnits: [],
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

    /** 已解锁的徽章：{ 'first-step': { unlockedAt } }，定义见 data/badges.js。 */
    badges: {},

    /**
     * 单元地图上「解锁过场已经演过」的单元 id。
     * null 表示这份存档还没记过：读档时按「当前已解锁的都算看过」补一遍，
     * 老存档才不会一进字表就被十几段过场连着轰。
     */
    seenUnits: null,
    /** 单字五步闭环的完成总次数，「五步全通」徽章看它。 */
    flowsCompleted: 0,

    /** FSRS 记忆卡：{ '人': { charId, due, stability, difficulty, reps, lapses, ... } } */
    srs: {},

    listen: { rounds: 0, right: 0, wrong: 0, bestStreak: 0 },

    /** 按天聚合：{ '2026-08-26': { seconds, chars: [...], stars, quizRight, quizWrong } } */
    daily: {},

    createdAt: Date.now()
  }
}

/**
 * 老存档（FSRS 接线之前的版本）里只有掌握度，没有记忆卡。
 * 直接按掌握度反推一张初始卡，孩子的历史进度就不会因为升级被清零：
 * 认识 → 半天后复习，会写 → 一天半，掌握 → 四天。
 */
const SEED_STABILITY = [0, 0.5, 1.5, 4]

function seedCards(chars) {
  const out = {}
  for (const [char, s] of Object.entries(chars)) {
    const level = s?.level ?? 0
    if (level < 1) continue
    const stability = SEED_STABILITY[Math.min(level, 3)]
    const lastReviewAt = s.lastAt ?? s.firstAt ?? Date.now()
    out[char] = {
      ...createCard(char, lastReviewAt),
      stability,
      reps: (s.quizRight ?? 0) + (s.traced ?? 0),
      lapses: s.quizWrong ?? 0,
      lastReviewAt,
      due: lastReviewAt + stability * 24 * 60 * 60 * 1000
    }
  }
  return out
}

function migrate(saved) {
  const base = defaultState()
  if (!saved || typeof saved !== 'object') return base
  const chars = { ...(saved.chars || {}) }
  return {
    ...base,
    ...saved,
    settings: { ...base.settings, ...(saved.settings || {}) },
    chars,
    books: { ...(saved.books || {}) },
    idioms: { ...(saved.idioms || {}) },
    radicals: { ...(saved.radicals || {}) },
    badges: { ...(saved.badges || {}) },
    seenUnits: Array.isArray(saved.seenUnits)
      ? saved.seenUnits.filter((id) => typeof id === 'string')
      : null,
    flowsCompleted: saved.flowsCompleted ?? 0,
    srs: saved.srs ? { ...saved.srs } : seedCards(chars),
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
  /**
   * 本次打开页面刚解锁的徽章，最新的排在最前面。
   * 单字页的「领奖励」一步和首页成就架都读它；不持久化，刷新即清空。
   */
  const recentBadges = ref([])
  /** 本次打开页面已连续学习的秒数，用于护眼提醒；不持久化。 */
  const sessionSeconds = ref(0)
  const restDue = ref(false)
  /**
   * 粗粒度的「现在」。遗忘曲线和到期判断都读它，
   * 这样孩子把页面开着不动，复习队列也会自己长出来，而不必每秒重算一遍。
   */
  const clock = ref(Date.now())

  function touchClock() {
    const now = Date.now()
    if (now - clock.value > 30000) clock.value = now
  }

  /* ---------------------------------------------------------------- 派生 */

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

  /* ------------------------------------------------------------ 地图叙事 */

  /**
   * 存档里没有记录时，把「此刻已解锁」的单元一次性记成看过。
   * 读档、导入、清档后都要走一遍，否则解锁过场会对着老进度重放一轮。
   */
  function ensureSeenUnits() {
    if (Array.isArray(state.seenUnits)) return
    state.seenUnits = UNITS.filter((u) => unlockedUnits.value[u.id]).map((u) => u.id)
  }

  /** 已经解锁、但过场还没演过的第一个单元；没有就是 null。 */
  const pendingUnitUnlock = computed(() => {
    const seen = new Set(state.seenUnits ?? [])
    return UNITS.find((u) => unlockedUnits.value[u.id] && !seen.has(u.id)) ?? null
  })

  /** 过场演完（或被跳过）后调用，同一个单元不会再演第二次。 */
  function markUnitSeen(unitId) {
    if (!unitId) return
    if (!Array.isArray(state.seenUnits)) state.seenUnits = []
    if (!state.seenUnits.includes(unitId)) state.seenUnits.push(unitId)
  }

  const booksFinished = computed(() => BOOKS.filter((b) => state.books[b.id]?.finishedAt).length)
  /**
   * 「学过几条成语」直接数存档，不去比对 IDIOMS。
   *
   * 进度 store 挂在应用外壳上，是首屏必然要下载的东西；从它 import 成语语料，
   * 六十条成语连故事带情景题就会一起被打进入口块。这里只需要一个数字，
   * 数存档里的记录就够了——语料改名换 id 的代价是可能多算一条旧记录，
   * 比让每个孩子先下载几十 KB 用不上的故事划算得多。
   */
  const idiomsRead = computed(() => Object.values(state.idioms).filter((i) => i?.read).length)
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
   * 复习推荐由 FSRS 记忆卡驱动：到期最久的排最前。
   * 和旧的「学过但还没掌握」规则相比，掌握过的字也会在遗忘曲线走低时重新回到队列，
   * 而刚练过的字不会反复出现——这正是间隔重复的意义。
   */
  const dueCharCards = computed(() => {
    const now = clock.value
    return dueCards(state.srs, now).filter((card) => CHARACTER_MAP.has(card.charId))
  })

  const reviewQueue = computed(() =>
    dueCharCards.value.slice(0, 12).map((card) => CHARACTER_MAP.get(card.charId))
  )

  const dueCount = computed(() => dueCharCards.value.length)

  /**
   * 学过的字 × 记忆强度，按记忆最弱的排在前面。
   * 这是家长中心热力图与「该复习了」提示的唯一数据源。
   */
  const memoryCards = computed(() =>
    learnedChars.value
      .map((c) => {
        const card = state.srs[c.char] ?? createCard(c.char, clock.value)
        return {
          char: c.char,
          unit: c.unit,
          stability: card.stability,
          difficulty: card.difficulty,
          reps: card.reps,
          lapses: card.lapses,
          due: card.due,
          retention: retention(card, clock.value),
          isDue: card.due <= clock.value
        }
      })
      .sort((a, b) => a.retention - b.retention || a.due - b.due)
  )

  const averageRetention = computed(() => {
    const list = memoryCards.value
    if (!list.length) return 0
    return list.reduce((n, c) => n + c.retention, 0) / list.length
  })

  /* ------------------------------------------------------------ 学习计划 */

  /** 计划覆盖的单元；家长没选就是全部单元。 */
  const planUnitIds = computed(() => {
    const picked = (state.settings.planUnits ?? []).filter((id) => UNITS.some((u) => u.id === id))
    return picked.length ? picked : UNITS.map((u) => u.id)
  })

  const isWholeCourse = computed(() => planUnitIds.value.length === UNITS.length)

  const planChars = computed(() => CHARACTERS.filter((c) => planUnitIds.value.includes(c.unit)))

  const planProgress = computed(() => {
    const total = planChars.value.length
    const learned = planChars.value.filter((c) => (state.chars[c.char]?.level ?? 0) >= 1).length
    return { total, learned, percent: total ? Math.round((learned / total) * 100) : 0 }
  })

  /** 0 表示家长没设上限。 */
  const dailyNewLimit = computed(() => state.settings.dailyNewLimit ?? 0)

  const newCharsToday = computed(() => today.value.chars?.length ?? 0)

  /** 今天还能学几个新字；没设上限时是 null，界面据此显示「不限」。 */
  const newCharsLeft = computed(() =>
    dailyNewLimit.value > 0 ? Math.max(0, dailyNewLimit.value - newCharsToday.value) : null
  )

  const dailyLimitReached = computed(() => newCharsLeft.value === 0)

  /**
   * 下一个还没学的字，首页「继续学习」按钮用。
   * 先在计划单元里找，计划里的字都学完了再回到整份字表，
   * 免得家长把计划缩到一个单元之后按钮直接变成死的。
   */
  const nextChar = computed(() => {
    const unlearned = (c) => (state.chars[c.char]?.level ?? 0) === 0
    return planChars.value.find(unlearned) ?? CHARACTERS.find(unlearned) ?? CHARACTERS[0]
  })

  /* ---------------------------------------------------------------- 徽章 */

  const tracedTotal = computed(() =>
    Object.values(state.chars).reduce((n, s) => n + (s.traced ?? 0), 0)
  )

  /** 徽章只认这一张指标表；data/badges.js 里的 metric 就是它的键。 */
  const badgeStats = computed(() => ({
    learned: learnedCount.value,
    mastered: masteredChars.value.length,
    traced: tracedTotal.value,
    flows: state.flowsCompleted ?? 0,
    listenStreak: state.listen.bestStreak,
    streak: streakDays.value,
    books: booksFinished.value,
    idioms: idiomsRead.value,
    radicals: radicalsSeen.value
  }))

  /** 全部徽章 × 当前进度，成就墙直接渲染这一份。 */
  const badges = computed(() =>
    BADGES.map((b) => {
      const raw = badgeStats.value[b.metric] ?? 0
      const record = state.badges[b.id] ?? null
      return {
        ...b,
        raw,
        value: Math.min(raw, b.goal),
        unlocked: Boolean(record),
        unlockedAt: record?.unlockedAt ?? null,
        percent: b.goal ? Math.min(100, Math.round((raw / b.goal) * 100)) : 0
      }
    })
  )

  const unlockedBadges = computed(() => badges.value.filter((b) => b.unlocked))
  const badgeCount = computed(() => unlockedBadges.value.length)
  const totalBadges = TOTAL_BADGES

  /** 差得最少的三枚未解锁徽章，用来告诉孩子「再做一点点就到手了」。 */
  const nextBadges = computed(() =>
    badges.value
      .filter((b) => !b.unlocked)
      .sort((a, b) => b.percent - a.percent || a.goal - b.goal)
      .slice(0, 3)
  )

  /**
   * 对一遍指标表，把够格的徽章记进存档。
   *
   * `silent` 用于读档时的补发：老存档里没有 badges 字段，第一次进来要把
   * 早就该拿到的徽章补上，但不该为此发星星、更不该弹一堆庆祝。
   */
  function refreshBadges({ silent = false } = {}) {
    const stats = badgeStats.value
    const fresh = []
    for (const b of BADGES) {
      if (state.badges[b.id]) continue
      if ((stats[b.metric] ?? 0) < b.goal) continue
      state.badges[b.id] = { unlockedAt: Date.now() }
      fresh.push(b)
    }
    if (!fresh.length || silent) return fresh
    recentBadges.value = [...fresh, ...recentBadges.value].slice(0, 8)
    addStars(fresh.length * 2)
    addXp(fresh.length * 15)
    return fresh
  }

  function clearRecentBadges() {
    recentBadges.value = []
  }

  /* ---------------------------------------------------------------- 内部 */

  function ensureChar(char) {
    if (!state.chars[char]) state.chars[char] = emptyChar()
    const s = state.chars[char]
    if (!s.firstAt) s.firstAt = Date.now()
    s.lastAt = Date.now()
    return s
  }

  function ensureCard(char) {
    if (!state.srs[char]) state.srs[char] = createCard(char)
    return state.srs[char]
  }

  /**
   * 把一次学习行为记进记忆卡。
   * 描红、答题都会调它，rating 决定下一次复习排在多久以后。
   */
  function reviewCard(char, rating) {
    const now = Date.now()
    state.srs[char] = schedule(ensureCard(char), rating, now)
    clock.value = now
    return state.srs[char]
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
    // 只是看见还不算复习：建卡但不排期，它会立刻出现在复习队列里等着被练。
    ensureCard(char)
    recomputeLevel(char)
  }

  /** 听了这个字的读音。 */
  function markHeard(char) {
    const s = ensureChar(char)
    s.heard += 1
    ensureCard(char)
    recomputeLevel(char)
  }

  /** 描红完成一遍。 */
  function markTraced(char) {
    const s = ensureChar(char)
    s.traced += 1
    reviewCard(char, RATING.GOOD)
    recomputeLevel(char)
    addXp(8)
  }

  /**
   * 单字页的五步闭环走完了一整轮（认一认 → 写一写 → 听一听 → 考一考 → 领奖励）。
   * 返回这一轮顺带解锁的徽章，好让「领奖励」那一步当场把它们摆出来。
   */
  function completeCharFlow(char) {
    const s = ensureChar(char)
    s.flows = (s.flows ?? 0) + 1
    state.flowsCompleted = (state.flowsCompleted ?? 0) + 1
    addStars(2)
    addXp(20)
    return { flows: s.flows, badges: refreshBadges() }
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
    // 已经掌握的字还能答对，说明记得很牢，间隔可以拉得更开。
    const rating = correct
      ? s.level >= MASTERY_THRESHOLD
        ? RATING.EASY
        : RATING.GOOD
      : RATING.AGAIN
    reviewCard(char, rating)
    recomputeLevel(char)
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

  function recordIdiomQuiz(idiomId, correct = true) {
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
    touchClock()
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
      ensureSeenUnits()
      refreshBadges({ silent: true })
      persist()
      return true
    } catch {
      return false
    }
  }

  function resetAll() {
    Object.assign(state, defaultState())
    applyAppearance()
    ensureSeenUnits()
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
  const markIdiomQuiz = recordIdiomQuiz

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
  ensureSeenUnits()
  // 读档时先把老存档欠下的徽章补齐（不发星星、不弹庆祝），之后指标一变就重新对表。
  refreshBadges({ silent: true })
  watch(badgeStats, () => refreshBadges())
  watch(() => JSON.stringify(state), persist, { flush: 'post' })

  return {
    state,
    pendingCelebration,
    recentBadges,
    sessionSeconds,
    restDue,

    learnedCount,
    overallProgress,
    levelProgress,
    unitProgress,
    booksFinished,
    radicalsSeen,
    accuracy,
    streakDays,
    reviewQueue,
    dueCount,
    memoryCards,
    averageRetention,
    nextChar,

    planUnitIds,
    isWholeCourse,
    planChars,
    planProgress,
    dailyNewLimit,
    newCharsToday,
    newCharsLeft,
    dailyLimitReached,

    badges,
    badgeStats,
    unlockedBadges,
    badgeCount,
    totalBadges,
    nextBadges,
    refreshBadges,
    clearRecentBadges,
    completeCharFlow,

    markHeard,
    markTraced,
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
    resetAll,

    /* ---------------------------------------------------------- 扁平视图层 */
    totalChars,
    masteredCount,
    unlockedUnits,
    pendingUnitUnlock,
    markUnitSeen,
    isLearned,
    isMastered,
    chars,
    books,
    idioms,
    stars,
    level,
    daily,
    todayStats,
    last7Days,
    idiomsSeen,
    game,
    gameAccuracy,

    visitChar,
    viewRadical,
    markIdiomSeen,
    markIdiomQuiz,
    recordAnswer,
    recordGameRound,
    readPage,
    bookPercent
  }
})
