/**
 * 进度 store — 掌握度 / 星星 / 经验等级 / 成就 / 打卡 / 错因统计，localStorage 持久化。
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

const STORAGE_KEY = 'mathquest/progress'

/** 升级所需经验随等级递增：level n -> n × 40。 */
const xpForLevel = (level) => level * 40

const emptyModuleStat = () => ({
  answered: 0,
  correct: 0,
  stars: 0,
  sessions: 0,
  bestScore: 0,
  lastPlayed: null,
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
    modules: Object.fromEntries(MODULES.map((m) => [m.id, emptyModuleStat()])),
    counters: { arithmeticHardCorrect: 0, sudokuSolved: 0, perfectRuns: 0 },
    achievements: {},
    settings: { sound: true, animations: true },
    history: [],
  }
}

function loadState() {
  const base = defaultState()
  if (typeof localStorage === 'undefined') return base
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
    if (!saved) return base
    return {
      ...base,
      ...saved,
      mastery: { ...(saved.mastery || {}) },
      errorTagCounts: { ...(saved.errorTagCounts || {}) },
      modules: { ...base.modules, ...(saved.modules || {}) },
      counters: { ...base.counters, ...(saved.counters || {}) },
      achievements: { ...(saved.achievements || {}) },
      settings: { ...base.settings, ...(saved.settings || {}) },
      history: Array.isArray(saved.history) ? saved.history : [],
    }
  } catch {
    return base
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

    if (isCorrect) {
      stat.correct += 1
      state.totalCorrect += 1
      combo.value += 1
      state.bestStreak = Math.max(state.bestStreak, combo.value)

      const gained = opts.stars ?? 1
      stat.stars += gained
      state.stars += gained
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
    addStars,
    bumpCounter,
    recordAnswer,
    finishSession,
    resetCombo,
    // 兼容早期调用点的别名
    resetStreak: resetCombo,
    takeUnlock,
    resetAll,
    exportReport,
    persist,
  }
})
