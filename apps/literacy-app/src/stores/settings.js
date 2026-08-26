import { defineStore } from 'pinia'
import { setSfxMuted } from '@/utils/sfx.js'

const STORAGE_KEY = 'literacy.settings.v1'

export const THEMES = [
  { id: 'sunny', name: '明亮童趣', emoji: '🌞', desc: '色彩鲜艳，白天使用' },
  { id: 'care', name: '护眼模式', emoji: '🍃', desc: '暖纸色低蓝光，久看不累' },
  { id: 'night', name: '夜间模式', emoji: '🌙', desc: '睡前故事时间' }
]

export const FONT_SCALES = [
  { id: 'small', name: '小' },
  { id: 'normal', name: '标准' },
  { id: 'large', name: '大' },
  { id: 'huge', name: '超大' }
]

function readStored() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
  } catch {
    return {}
  }
}

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    theme: 'sunny',
    fontScale: 'normal',
    reduceMotion: false,
    soundOn: true,
    speechOn: true,
    speechRate: 0.75,
    showPinyin: true,
    /** 家长设定的每日建议时长（分钟），0 表示不限制 */
    dailyLimitMinutes: 20,
    /** 达到时长后是否强制提示休息 */
    breakReminder: true,
    childName: '',
    _loaded: false
  }),

  getters: {
    themeMeta: (s) => THEMES.find((t) => t.id === s.theme) || THEMES[0],
    isEyeCare: (s) => s.theme === 'care'
  },

  actions: {
    load() {
      Object.assign(this.$state, readStored(), { _loaded: true })
      this.apply()
    },

    apply() {
      const root = document.documentElement
      root.dataset.theme = this.theme
      root.dataset.fontScale = this.fontScale
      root.dataset.motion = this.reduceMotion ? 'reduced' : 'full'
      setSfxMuted(!this.soundOn)
      const meta = document.querySelector('meta[name="theme-color"]')
      if (meta) {
        meta.setAttribute(
          'content',
          getComputedStyle(root).getPropertyValue('--bg-page-solid').trim() || '#ffb84d'
        )
      }
    },

    persist() {
      const { _loaded, ...rest } = this.$state
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(rest))
      } catch {
        /* 隐私模式下 localStorage 可能不可用，忽略即可 */
      }
    },

    setTheme(id) {
      this.theme = id
      this.apply()
      this.persist()
    },

    cycleTheme() {
      const idx = THEMES.findIndex((t) => t.id === this.theme)
      this.setTheme(THEMES[(idx + 1) % THEMES.length].id)
    },

    update(patch) {
      Object.assign(this.$state, patch)
      this.apply()
      this.persist()
    },

    reset() {
      this.$reset()
      this._loaded = true
      this.apply()
      this.persist()
    }
  }
})
