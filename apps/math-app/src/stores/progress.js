/**
 * 进度 store — 掌握度 / 星星 / 经验等级 / 成就 / 打卡 / 错因统计 / 错题本，localStorage 持久化。
 *
 * 同时满足两套调用契约：
 *  - 架构契约：mastery / stars / dailyStreak / moduleProgress / recordAnswer(question, ok) / exportReport
 *  - 玩法契约：combo(连击) / xp / level / moduleStat / achievements / finishSession(...)
 */
import { computed, reactive, ref, watch } from 'vue'
import { defineStore } from 'pinia'
import { updateMastery, MASTERY_THRESHOLD } from '@/utils/mastery.js'
import { isKnownSkill, SKILLS } from '@/data/curriculum.js'
import { CURRICULUM_ID, MODULES } from '@/data/modules.js'
import { ACHIEVEMENTS, ACHIEVEMENT_MAP } from '@/data/achievements.js'
import { DAILY_SIZE, dailyDateKey } from '@/data/daily.js'

const STORAGE_KEY = 'mathquest/progress'

/** 家长页导出文件的身份标记，导入时用来挡掉别的 App 的备份。 */
const BACKUP_APP = 'mathquest'
const BACKUP_VERSION = 1

/** 每日明细只留最近 30 天，够画 7 天曲线也不会把 localStorage 撑爆。 */
const DAILY_KEEP_DAYS = 30

/** 错题本只留最近错的 60 道：再多孩子也刷不完，反而看着发怵。 */
const WRONG_BOOK_MAX = 60

/**
 * 错题本的键：模块 + 题目 id。
 * 不同玩法的题目 id 各自成体系（口算是「7+5」，应用题是母题 id），
 * 不加模块前缀迟早会撞在一起。
 */
export const wrongBookKey = (moduleId, questionId) => `${moduleId || 'unknown'}:${questionId}`

/** 升级所需经验随等级递增：level n -> n × 40。 */
const xpForLevel = (level) => level * 40

const dateKey = (date = new Date()) => date.toISOString().slice(0, 10)

const emptyModuleStat = () => ({
  answered: 0,
  correct: 0,
  stars: 0,
  sessions: 0,
  bestScore: 0,
  lastPlayed: null,
})

const emptyDay = () => ({ seconds: 0, answered: 0, correct: 0, stars: 0 })

/**
 * 今日冒险的进度。date 是这份记录属于哪一天，跨天后自动归零，
 * streak / lastCompletedDate 跨天保留，用来算「连续完成多少天」。
 */
const emptyDailyQuest = () => ({
  date: '',
  done: 0,
  correct: 0,
  total: DAILY_SIZE,
  completedAt: 0,
  streak: 0,
  bestStreak: 0,
  lastCompletedDate: '',
})

function defaultState() {
  return {
    pilotName: '小小宇航员',
    avatar: '🧑‍🚀',
    stars: 0,
    xp: 0,
    level: 1,
    totalAnswered: 0,
    totalCorrect: 0,
    bestStreak: 0,
    mastery: {},
    dailyStreak: 0,
    lastPlayedDate: '',
    errorTagCounts: {},
    /** questionId -> { skill, errorTag, attempts, lastAt, ... }，答错入库、重做答对出库 */
    wrongBook: {},
    modules: Object.fromEntries(MODULES.map((m) => [m.id, emptyModuleStat()])),
    counters: { arithmeticHardCorrect: 0, sudokuSolved: 0, perfectRuns: 0, dailyQuests: 0 },
    dailyQuest: emptyDailyQuest(),
    achievements: {},
    settings: { sound: true, animations: true },
    history: [],
    /** 'YYYY-MM-DD' -> { seconds, answered, correct, stars }，家长页时长曲线的数据源 */
    daily: {},
  }
}

/** 把任意来源的「id -> 数值」字典洗成有限数，脏数据不会变成界面上的 NaN。 */
function numberMap(raw, max = Number.POSITIVE_INFINITY) {
  const out = {}
  for (const [key, value] of Object.entries(raw ?? {})) {
    const n = Number(value)
    if (Number.isFinite(n)) out[key] = Math.min(max, Math.max(0, n))
  }
  return out
}

/** 错题本超量时按「最后错的时间」淘汰最旧的几条。 */
function trimWrongBook(book) {
  const keys = Object.keys(book)
  if (keys.length <= WRONG_BOOK_MAX) return book
  const stale = keys
    .sort((a, b) => (book[a].lastAt ?? 0) - (book[b].lastAt ?? 0))
    .slice(0, keys.length - WRONG_BOOK_MAX)
  for (const key of stale) delete book[key]
  return book
}

const text = (value, fallback = '') => (typeof value === 'string' ? value : fallback)

/**
 * 洗一份外部错题本：没有正确答案的条目直接丢掉——重做流程验不了答案，
 * 留着只会在界面上变成一行点不动的死记录。
 */
function mergeWrongBook(raw) {
  const out = {}
  for (const [key, value] of Object.entries(raw ?? {})) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) continue
    const answer = value.answer
    if (typeof answer !== 'number' && typeof answer !== 'string') continue
    if (typeof answer === 'number' && !Number.isFinite(answer)) continue

    const attempts = Math.round(Number(value.attempts))
    const retries = Math.round(Number(value.retries))
    const lastAt = Number(value.lastAt)
    const addedAt = Number(value.addedAt)
    out[key] = {
      id: key,
      module: text(value.module),
      skill: isKnownSkill(value.skill) ? value.skill : null,
      errorTag: text(value.errorTag, 'miscalc'),
      errorTags: Array.isArray(value.errorTags) ? value.errorTags.filter((t) => text(t)) : [],
      title: text(value.title),
      answer,
      options: Array.isArray(value.options) ? value.options.slice(0, 8) : [],
      unit: text(value.unit),
      hint: text(value.hint),
      lastWrong: value.lastWrong ?? null,
      attempts: Number.isFinite(attempts) ? Math.max(1, attempts) : 1,
      retries: Number.isFinite(retries) ? Math.max(0, retries) : 0,
      addedAt: Number.isFinite(addedAt) ? addedAt : Date.now(),
      lastAt: Number.isFinite(lastAt) ? lastAt : Date.now(),
    }
  }
  return trimWrongBook(out)
}

function mergeDaily(raw) {
  const out = {}
  for (const [key, value] of Object.entries(raw ?? {})) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(key)) continue
    out[key] = { ...emptyDay(), ...numberMap(value) }
  }
  return out
}

/**
 * 合并一份外部快照（localStorage 或家长页导入的备份）到默认结构上。
 * 缺字段回落默认值、脏字段丢弃，保证 store 永远是完整形状。
 */
function mergeState(saved) {
  const base = defaultState()
  if (!saved || typeof saved !== 'object' || Array.isArray(saved)) return base

  const modules = { ...base.modules }
  for (const [id, stat] of Object.entries(saved.modules ?? {})) {
    modules[id] = { ...emptyModuleStat(), ...(stat && typeof stat === 'object' ? stat : {}) }
  }

  return {
    ...base,
    ...saved,
    mastery: numberMap(saved.mastery, 1),
    errorTagCounts: numberMap(saved.errorTagCounts),
    wrongBook: mergeWrongBook(saved.wrongBook),
    modules,
    counters: { ...base.counters, ...numberMap(saved.counters) },
    dailyQuest: {
      ...base.dailyQuest,
      ...(saved.dailyQuest && typeof saved.dailyQuest === 'object' ? saved.dailyQuest : {}),
      total: DAILY_SIZE,
    },
    achievements: { ...(saved.achievements || {}) },
    settings: { ...base.settings, ...(saved.settings || {}) },
    history: Array.isArray(saved.history) ? saved.history.slice(0, 40) : [],
    daily: mergeDaily(saved.daily),
  }
}

function loadState() {
  if (typeof localStorage === 'undefined') return defaultState()
  try {
    return mergeState(JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null'))
  } catch {
    return defaultState()
  }
}

export const useProgressStore = defineStore('progress', () => {
  const state = reactive(loadState())

  /** 本次会话的连击数，不持久化。 */
  const combo = ref(0)
  /** 刚解锁、尚未弹窗展示的成就 id 队列。 */
  const pendingUnlocks = ref([])

  // ---------- 派生数据 ----------

  const accuracy = computed(() =>
    state.totalAnswered === 0 ? 0 : Math.round((state.totalCorrect / state.totalAnswered) * 100),
  )
  const xpToNext = computed(() => xpForLevel(state.level))
  const levelProgress = computed(() => Math.min(1, state.xp / xpToNext.value))

  const masteredCount = computed(
    () => Object.values(state.mastery).filter((m) => m >= MASTERY_THRESHOLD).length,
  )
  const totalSkills = computed(() => SKILLS.length)
  const badges = computed(() => Object.keys(state.achievements))

  const unlockedAchievements = computed(() =>
    ACHIEVEMENTS.filter((a) => state.achievements[a.id]).map((a) => ({
      ...a,
      unlockedAt: state.achievements[a.id],
    })),
  )
  const lockedAchievements = computed(() => ACHIEVEMENTS.filter((a) => !state.achievements[a.id]))

  const moduleStat = (moduleId) => state.modules[moduleId] ?? emptyModuleStat()

  // ---------- 错题本 ----------

  /** 最近错的排在最前，界面直接按这个顺序渲染。 */
  const wrongList = computed(() =>
    Object.values(state.wrongBook).sort((a, b) => (b.lastAt ?? 0) - (a.lastAt ?? 0)),
  )
  const wrongCount = computed(() => wrongList.value.length)
  const wrongOfModule = (moduleId) => wrongList.value.filter((e) => e.module === moduleId)

  // ---------- 使用时长 ----------

  const todaySeconds = computed(() => state.daily[dateKey()]?.seconds ?? 0)
  const todayMinutes = computed(() => Math.floor(todaySeconds.value / 60))
  const totalMinutes = computed(() =>
    Math.round(Object.values(state.daily).reduce((sum, d) => sum + (d.seconds || 0), 0) / 60),
  )

  const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']

  /** 最近 7 天（含今天）的时长与答题量，缺的日子补 0，家长页直接画柱子。 */
  const last7Days = computed(() =>
    Array.from({ length: 7 }, (_, i) => {
      const date = new Date(Date.now() - (6 - i) * 864e5)
      const key = dateKey(date)
      const day = state.daily[key] ?? emptyDay()
      return {
        key,
        label: `周${WEEKDAYS[date.getUTCDay()]}`,
        minutes: Math.round(day.seconds / 60),
        ...day,
      }
    }),
  )

  /**
   * 模块掌握度 0..1。技能图谱上有该模块的技能点时取平均掌握度，
   * 否则退化为该模块的答题正确率，保证地图上的进度环始终有值。
   */
  const moduleProgress = (moduleId) => {
    const curriculumId = CURRICULUM_ID[moduleId] ?? moduleId
    const skills = SKILLS.filter((k) => k.module === curriculumId)
    const tracked = skills.filter((k) => state.mastery[k.id] !== undefined)
    if (tracked.length) {
      return tracked.reduce((acc, k) => acc + state.mastery[k.id], 0) / tracked.length
    }
    const stat = state.modules[moduleId]
    return stat && stat.answered ? stat.correct / stat.answered : 0
  }

  const isModuleUnlocked = (moduleId) => {
    const mod = MODULES.find((m) => m.id === moduleId)
    return !mod || state.stars >= mod.starsToUnlock
  }

  // ---------- 内部工具 ----------

  function persist() {
    if (typeof localStorage === 'undefined') return
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
    } catch {
      /* 隐私模式写入失败时静默降级为内存态 */
    }
  }

  function checkAchievements() {
    const snapshot = {
      stars: state.stars,
      totalAnswered: state.totalAnswered,
      totalCorrect: state.totalCorrect,
      bestStreak: state.bestStreak,
      modules: state.modules,
      counters: state.counters,
    }
    for (const a of ACHIEVEMENTS) {
      if (state.achievements[a.id]) continue
      let ok = false
      try {
        ok = !!a.test(snapshot)
      } catch {
        ok = false
      }
      if (ok) {
        state.achievements[a.id] = Date.now()
        pendingUnlocks.value.push(a.id)
      }
    }
  }

  function addXp(amount) {
    state.xp += amount
    while (state.xp >= xpForLevel(state.level)) {
      state.xp -= xpForLevel(state.level)
      state.level += 1
    }
  }

  /** 取今天的明细桶，顺手清掉 30 天以前的记录。 */
  function dayBucket() {
    const key = dateKey()
    if (!state.daily[key]) {
      state.daily[key] = emptyDay()
      const keys = Object.keys(state.daily).sort()
      for (const stale of keys.slice(0, Math.max(0, keys.length - DAILY_KEEP_DAYS))) {
        delete state.daily[stale]
      }
    }
    return state.daily[key]
  }

  /* ---------- 今日冒险 ---------- */

  /** 跨天后把今日冒险归零；连续天数与历史完成日不动。 */
  function rollDailyQuest() {
    const today = dateKey()
    const quest = state.dailyQuest
    if (quest.date !== today) {
      quest.date = today
      quest.done = 0
      quest.correct = 0
      quest.completedAt = 0
    }
    quest.total = DAILY_SIZE
    return quest
  }

  const dailyQuest = computed(() => {
    const quest = state.dailyQuest
    const fresh = quest.date === dateKey()
    return {
      date: quest.date,
      done: fresh ? quest.done : 0,
      correct: fresh ? quest.correct : 0,
      total: DAILY_SIZE,
      completed: fresh && quest.completedAt > 0,
      completedAt: fresh ? quest.completedAt : 0,
      streak: quest.streak,
      bestStreak: quest.bestStreak,
    }
  })

  const dailyQuestDone = computed(() => dailyQuest.value.completed)

  /** 进入今日冒险时调用，返回今天该做的题号（断点续做用）。 */
  function startDailyQuest() {
    const quest = rollDailyQuest()
    persist()
    return { date: quest.date, done: quest.done, total: quest.total }
  }

  /** 每答一题记一步。答题本身的星星 / 掌握度仍走 recordAnswer。 */
  function recordDailyStep(isCorrect) {
    const quest = rollDailyQuest()
    quest.done = Math.min(quest.total, quest.done + 1)
    if (isCorrect) quest.correct = Math.min(quest.total, quest.correct + 1)
    return { done: quest.done, total: quest.total }
  }

  /**
   * 今日冒险收尾：记完成时间、算连续天数、发完成奖励。
   * 同一天重复完成不再发奖，否则刷「再来一轮」就能白拿星星。
   */
  function finishDailyQuest({ correct = 0, bonusStars = 2 } = {}) {
    const quest = rollDailyQuest()
    if (quest.completedAt) return { alreadyDone: true, streak: quest.streak, stars: 0 }

    const today = quest.date
    const yesterday = dailyDateKey(new Date(Date.now() - 864e5))
    quest.streak = quest.lastCompletedDate === yesterday ? quest.streak + 1 : 1
    quest.bestStreak = Math.max(quest.bestStreak, quest.streak)
    quest.lastCompletedDate = today
    quest.completedAt = Date.now()
    quest.done = quest.total
    quest.correct = Math.min(quest.total, correct)

    state.counters.dailyQuests = (state.counters.dailyQuests ?? 0) + 1
    if (bonusStars > 0) state.stars += bonusStars

    touchStreak()
    checkAchievements()
    return { alreadyDone: false, streak: quest.streak, stars: bonusStars }
  }

  function touchStreak() {
    const today = new Date().toISOString().slice(0, 10)
    if (state.lastPlayedDate === today) return
    const yesterday = new Date(Date.now() - 864e5).toISOString().slice(0, 10)
    state.dailyStreak = state.lastPlayedDate === yesterday ? state.dailyStreak + 1 : 1
    state.lastPlayedDate = today
  }

  // ---------- 对外动作 ----------

  function addStars(count) {
    if (count <= 0) return
    state.stars += count
    checkAchievements()
  }

  /**
   * 累计一段在线时长（秒）。App 每 15 秒在页面可见时报一次，
   * 家长页的「今日时长 / 最近 7 天」和防沉迷提醒都读这份数据。
   */
  function recordUsage(seconds) {
    const delta = Number(seconds)
    if (!Number.isFinite(delta) || delta <= 0) return
    dayBucket().seconds += Math.round(delta)
  }

  function bumpCounter(name, delta = 1) {
    state.counters[name] = (state.counters[name] ?? 0) + delta
    checkAchievements()
  }

  /**
   * 记录一次作答。支持两种调用方式：
   *   recordAnswer('geometry', true, { stars: 1, xp: 10, skill: 'shape-2d' })
   *   recordAnswer({ module: 'arithmetic', skill: 'add-carry-20', meta: { errorTags: ['carry'] } }, false)
   *
   * skill 必须是 curriculum 里存在的技能点：技能雷达、地图进度环、掌握数统计
   * 都只认图谱里的 id，写错的 id 会变成一条谁也看不到的掌握度记录，
   * 表现为「明明练了，进度环却不动」。这里直接拦下并在开发期报出来。
   */
  function recordAnswer(target, isCorrect, opts = {}) {
    const isQuestion = typeof target === 'object' && target !== null
    const moduleId = isQuestion ? (target.module ?? opts.module) : target
    const rawSkillId = isQuestion ? target.skill : opts.skill
    const errorTags = isQuestion ? (target.meta?.errorTags ?? []) : (opts.errorTags ?? [])

    const skillId = rawSkillId && isKnownSkill(rawSkillId) ? rawSkillId : null
    if (rawSkillId && !skillId && import.meta.env?.DEV) {
      console.warn(`[progress] 技能点「${rawSkillId}」不在 curriculum 里，本次掌握度未记录`)
    }
    if (skillId) state.mastery[skillId] = updateMastery(state.mastery[skillId], isCorrect)

    const stat = state.modules[moduleId] ?? (state.modules[moduleId] = emptyModuleStat())
    stat.answered += 1
    stat.lastPlayed = Date.now()
    state.totalAnswered += 1

    const day = dayBucket()
    day.answered += 1

    if (isCorrect) {
      stat.correct += 1
      state.totalCorrect += 1
      day.correct += 1
      combo.value += 1
      state.bestStreak = Math.max(state.bestStreak, combo.value)

      const gained = opts.stars ?? 1
      stat.stars += gained
      state.stars += gained
      day.stars += gained
      addXp(opts.xp ?? 10)

      if (opts.tag === 'arithmetic-hard') state.counters.arithmeticHardCorrect += 1
    } else {
      combo.value = 0
      addXp(2)
      for (const tag of errorTags) {
        state.errorTagCounts[tag] = (state.errorTagCounts[tag] ?? 0) + 1
      }
    }

    touchStreak()
    checkAchievements()
    return { combo: combo.value }
  }

  /**
   * 答错入错题本。同一道题再错一次只累加 attempts，不会刷出两行。
   * 除了统计字段，还存下题面/选项/答案，进度页的重做流程才能离线复现这道题。
   */
  function recordWrong(entry) {
    const id = text(entry?.id)
    const answer = entry?.answer
    if (!id) return null
    if (typeof answer !== 'number' && typeof answer !== 'string') return null
    if (typeof answer === 'number' && !Number.isFinite(answer)) return null

    const now = Date.now()
    const prev = state.wrongBook[id]
    const tags = [...new Set([...(entry.errorTags ?? [])].filter((t) => text(t)))]
    const next = {
      id,
      module: text(entry.module, prev?.module ?? ''),
      skill: isKnownSkill(entry.skill) ? entry.skill : (prev?.skill ?? null),
      errorTag: text(entry.errorTag, tags[0] ?? prev?.errorTag ?? 'miscalc'),
      errorTags: tags.length ? tags : (prev?.errorTags ?? []),
      title: text(entry.title, prev?.title ?? ''),
      answer,
      options: Array.isArray(entry.options) ? entry.options.slice(0, 8) : (prev?.options ?? []),
      unit: text(entry.unit, prev?.unit ?? ''),
      hint: text(entry.hint, prev?.hint ?? ''),
      lastWrong: entry.lastWrong ?? null,
      attempts: (prev?.attempts ?? 0) + 1,
      retries: prev?.retries ?? 0,
      addedAt: prev?.addedAt ?? now,
      lastAt: now,
    }
    state.wrongBook[id] = next
    trimWrongBook(state.wrongBook)
    return next
  }

  /** 从错题本移出一道题；返回是否真的移出了，方便调用方决定要不要报喜。 */
  function clearWrong(id) {
    if (!id || !state.wrongBook[id]) return false
    delete state.wrongBook[id]
    return true
  }

  /**
   * 错题本里重做一道题。
   * 答对：掌握度上调、移出错题本、奖 1 颗星；答错：留在本子里，attempts 再 +1。
   * 这里不走 recordAnswer，重做不该把「总题数 / 正确率」这些主统计冲淡。
   */
  function retryWrong(id, isCorrect) {
    const entry = state.wrongBook[id]
    if (!entry) return null
    if (entry.skill) state.mastery[entry.skill] = updateMastery(state.mastery[entry.skill], isCorrect)
    entry.retries += 1
    entry.lastAt = Date.now()

    if (!isCorrect) {
      entry.attempts += 1
      return { cleared: false, entry }
    }
    delete state.wrongBook[id]
    addXp(6)
    addStars(1)
    return { cleared: true, entry }
  }

  function clearWrongBook() {
    state.wrongBook = {}
  }

  /** 记录一轮练习结束，用于历史曲线与「完美通关」成就。 */
  function finishSession(moduleId, { correct = 0, total = 0, bonusStars = 0 } = {}) {
    const stat = state.modules[moduleId] ?? (state.modules[moduleId] = emptyModuleStat())
    stat.sessions += 1
    const score = total > 0 ? Math.round((correct / total) * 100) : 0
    stat.bestScore = Math.max(stat.bestScore, score)

    if (total >= 5 && correct === total) state.counters.perfectRuns += 1
    if (bonusStars > 0) {
      stat.stars += bonusStars
      state.stars += bonusStars
    }

    state.history.unshift({ moduleId, correct, total, score, at: Date.now() })
    state.history = state.history.slice(0, 40)

    touchStreak()
    checkAchievements()
    return { score }
  }

  function resetCombo() {
    combo.value = 0
  }

  function takeUnlock() {
    const id = pendingUnlocks.value.shift()
    return id ? ACHIEVEMENT_MAP[id] : null
  }

  function resetAll() {
    Object.assign(state, defaultState())
    pendingUnlocks.value = []
    combo.value = 0
    persist()
  }

  /**
   * 家长页整档备份：导出的就是 store 的完整状态，导入后能原样还原。
   * exportReport() 只导出摘要，换设备时要用这个。
   */
  function exportJson() {
    return JSON.stringify(
      {
        app: BACKUP_APP,
        version: BACKUP_VERSION,
        exportedAt: new Date().toISOString(),
        progress: JSON.parse(JSON.stringify(state)),
      },
      null,
      2,
    )
  }

  const NUMERIC_FIELDS = [
    'stars',
    'xp',
    'level',
    'totalAnswered',
    'totalCorrect',
    'bestStreak',
    'dailyStreak',
  ]

  /**
   * 导入一份 exportJson() 的备份，整档覆盖当前进度。
   * 也接受直接是 state 形状的老文件；认不出来的文件抛错，
   * 绝不能把「导错文件」变成「进度被清空」。
   */
  function importJson(text) {
    let parsed
    try {
      parsed = JSON.parse(text)
    } catch {
      throw new Error('这不是一个有效的 JSON 文件')
    }
    if (parsed?.app && parsed.app !== BACKUP_APP) {
      throw new Error(`这是「${parsed.app}」的备份，不是星际数学冒险的`)
    }
    const payload = parsed?.progress ?? parsed
    if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
      throw new Error('文件里没有找到进度数据')
    }
    if (!NUMERIC_FIELDS.some((field) => Number.isFinite(Number(payload[field])))) {
      throw new Error('文件里没有可识别的进度字段')
    }

    Object.assign(state, mergeState(payload))
    pendingUnlocks.value = []
    combo.value = 0
    persist()
    return {
      answered: state.totalAnswered,
      stars: state.stars,
      skills: Object.keys(state.mastery).length,
    }
  }

  /** 家长页 JSON 导出 */
  function exportReport() {
    return JSON.stringify(
      {
        exportedAt: new Date().toISOString(),
        pilotName: state.pilotName,
        level: state.level,
        stars: state.stars,
        accuracy: accuracy.value,
        dailyStreak: state.dailyStreak,
        bestStreak: state.bestStreak,
        mastery: state.mastery,
        modules: state.modules,
        errorTagCounts: state.errorTagCounts,
        wrongBook: wrongList.value.map(({ id, module, skill, errorTag, attempts, lastAt }) => ({
          id,
          module,
          skill,
          errorTag,
          attempts,
          lastAt,
        })),
        achievements: Object.keys(state.achievements),
        history: state.history,
      },
      null,
      2,
    )
  }

  watch(() => JSON.stringify(state), persist)

  return {
    state,
    combo,
    pendingUnlocks,
    // 架构契约别名
    stars: computed(() => state.stars),
    dailyStreak: computed(() => state.dailyStreak),
    mastery: computed(() => state.mastery),
    errorTagCounts: computed(() => state.errorTagCounts),
    // 错题本
    wrongBook: computed(() => state.wrongBook),
    wrongList,
    wrongCount,
    wrongOfModule,
    recordWrong,
    clearWrong,
    retryWrong,
    clearWrongBook,
    badges,
    masteredCount,
    totalSkills,
    moduleProgress,
    // 玩法契约
    accuracy,
    xpToNext,
    levelProgress,
    unlockedAchievements,
    lockedAchievements,
    isModuleUnlocked,
    moduleStat,
    // 使用时长
    todaySeconds,
    todayMinutes,
    totalMinutes,
    last7Days,
    recordUsage,
    // 今日冒险
    dailyQuest,
    dailyQuestDone,
    startDailyQuest,
    recordDailyStep,
    finishDailyQuest,
    addStars,
    bumpCounter,
    recordAnswer,
    finishSession,
    resetCombo,
    // 兼容早期调用点的别名
    resetStreak: resetCombo,
    takeUnlock,
    resetAll,
    exportJson,
    importJson,
    exportReport,
    persist,
  }
})
