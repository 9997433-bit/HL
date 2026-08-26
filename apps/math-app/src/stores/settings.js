/**
 * 设置 store — 音效开关 / 护眼模式 / 年龄档,localStorage 持久化。
 */
import { defineStore } from 'pinia'

const STORAGE_KEY = 'mathquest/settings'

function load() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) ?? {}
  } catch {
    return {}
  }
}

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    soundOn: true,
    eyeCare: false,        // 护眼模式:降低饱和度/暖色滤镜(CSS 类切换)
    ageBand: 'L2',         // L1-L5,影响默认推荐模块与生成器参数
    dailyGoal: 5,          // 每日冒险题数,对标都都"每日 5 题"
    ...load()
  }),
  actions: {
    toggle(key) {
      this[key] = !this[key]
      this.persist()
    },
    set(key, value) {
      this[key] = value
      this.persist()
    },
    persist() {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          soundOn: this.soundOn,
          eyeCare: this.eyeCare,
          ageBand: this.ageBand,
          dailyGoal: this.dailyGoal
        })
      )
    }
  }
})
