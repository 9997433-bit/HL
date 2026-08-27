/**
 * 设置 store — 音效开关 / 护眼模式 / 年龄档 / 防沉迷时长,localStorage 持久化。
 */
import { defineStore } from 'pinia'

const STORAGE_KEY = 'mathquest/settings'

/**
 * 年龄档 —— 家长在家长中心里选，决定各玩法进来时的默认难度。
 * 孩子在玩法页里仍然可以自己切档，这里只是「从哪儿起步」。
 */
export const AGE_BANDS = [
  { id: 'L1', name: '3–4 岁', desc: '点数与图形认知' },
  { id: 'L2', name: '4–6 岁', desc: '10 以内加减' },
  { id: 'L3', name: '6–8 岁', desc: '20 以内进位退位' },
  { id: 'L4', name: '8–10 岁', desc: '100 以内与乘除' },
  { id: 'L5', name: '10–12 岁', desc: '两步应用题与数独' }
]

/** 双 App 共用 aurora 令牌；数学 App 保留 cosmos 作为默认品牌主题。 */
export const THEMES = [
  { id: 'cosmos', name: '深空模式', emoji: '🚀', desc: '经典蓝紫星空' },
  { id: 'aurora', name: '极光模式', emoji: '🌌', desc: '青绿极光与柔和紫光' }
]

const DEFAULTS = {
  theme: 'cosmos',
  soundOn: true,
  eyeCare: false,          // 护眼模式:降低饱和度/暖色滤镜(CSS 类切换)
  ageBand: 'L2',           // L1-L5,影响默认推荐模块与生成器参数
  dailyGoal: 5,            // 每日冒险题数,对标都都"每日 5 题"
  dailyLimitMinutes: 20,   // 每日建议时长(分钟),0 表示不限制
  breakReminder: true,     // 到点后弹出护眼休息提醒
  animations: true         // 动效总开关,对动画敏感的孩子可以关掉
}

/** 家长页会把这些值直接写进来，越界的输入在这里挡掉，不让它进 localStorage。 */
function sanitize(saved) {
  const out = { ...DEFAULTS, ...saved }
  const limit = Number(out.dailyLimitMinutes)
  out.dailyLimitMinutes = Number.isFinite(limit) ? Math.min(120, Math.max(0, Math.round(limit))) : DEFAULTS.dailyLimitMinutes
  const goal = Number(out.dailyGoal)
  out.dailyGoal = Number.isFinite(goal) ? Math.min(50, Math.max(1, Math.round(goal))) : DEFAULTS.dailyGoal
  out.ageBand = AGE_BANDS.some((band) => band.id === out.ageBand) ? out.ageBand : DEFAULTS.ageBand
  out.theme = THEMES.some((theme) => theme.id === out.theme) ? out.theme : DEFAULTS.theme
  out.soundOn = !!out.soundOn
  out.eyeCare = !!out.eyeCare
  out.breakReminder = !!out.breakReminder
  out.animations = !!out.animations
  return out
}

function load() {
  try {
    return sanitize(JSON.parse(localStorage.getItem(STORAGE_KEY)) ?? {})
  } catch {
    return { ...DEFAULTS }
  }
}

export const useSettingsStore = defineStore('settings', {
  state: () => load(),
  actions: {
    toggle(key) {
      this[key] = !this[key]
      this.persist()
    },
    set(key, value) {
      this[key] = value
      this.persist()
    },
    reset() {
      this.$patch({ ...DEFAULTS })
      this.persist()
    },
    persist() {
      const clean = sanitize(this.$state)
      this.$patch(clean)
      localStorage.setItem(STORAGE_KEY, JSON.stringify(clean))
    }
  }
})
