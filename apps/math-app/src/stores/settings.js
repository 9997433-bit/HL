/**
 * 设置 store — 音效开关 / 护眼模式 / 年龄档 / 防沉迷时长,localStorage 持久化。
 */
import { defineStore } from 'pinia'
import { AGE_BAND_IDS, DEFAULT_AGE_BAND } from '@/data/age-band.js'

const STORAGE_KEY = 'mathquest/settings'

/**
 * 年龄档 —— 家长在家长中心里选，决定各玩法进来时的默认难度。
 * 孩子在玩法页里仍然可以自己切档，这里只是「从哪儿起步」。
 * 档位清单和它在六个玩法里对应的默认难度都写在 data/age-band.js。
 */
export { AGE_BANDS } from '@/data/age-band.js'

const DEFAULTS = {
  soundOn: true,
  eyeCare: false,          // 护眼模式:降低饱和度/暖色滤镜(CSS 类切换)
  ageBand: DEFAULT_AGE_BAND, // L1-L5,驱动六个玩法的默认难度
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
  out.ageBand = AGE_BAND_IDS.includes(out.ageBand) ? out.ageBand : DEFAULTS.ageBand
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
