/**
 * 外观 / 朗读设置的门面。
 *
 * 真正的状态只有一份，存在 progress store 的 `state.settings` 里
 * （连同学习进度一起持久化、一起导出）。这里不再自己存一份，
 * 否则顶栏切主题和家长面板切主题会各改各的，`<html data-theme>` 被两边抢着写。
 *
 * 保留这个 store 是因为界面层用「soundOn / reduceMotion / dailyLimitMinutes」
 * 这类面向使用者的说法更好读，而底层字段名是 sound / motion / restReminderMin。
 * 门面只做这层命名映射，不持有任何状态。
 */

import { computed } from 'vue'
import { defineStore } from 'pinia'
import { useProgressStore } from './progress.js'

export const THEMES = [
  { id: 'sunny', name: '明亮童趣', emoji: '🌞', desc: '色彩鲜艳，白天使用' },
  { id: 'care', name: '护眼模式', emoji: '🍃', desc: '暖纸色低蓝光，久看不累' },
  { id: 'night', name: '夜间模式', emoji: '🌙', desc: '睡前故事时间' },
  { id: 'aurora', name: '极光模式', emoji: '🌌', desc: '青紫极光，沉浸探索' }
]

export const FONT_SCALES = [
  { id: 'small', name: '小' },
  { id: 'normal', name: '标准' },
  { id: 'large', name: '大' },
  { id: 'huge', name: '超大' }
]

/** 这两项底层没有默认值，读的时候兜底，写的时候直接落到 state.settings 上。 */
const DEFAULT_SPEECH_RATE = 0.85
const DEFAULT_BREAK_REMINDER = true

export const useSettingsStore = defineStore('settings', () => {
  const progress = useProgressStore()
  const raw = () => progress.state.settings

  const theme = computed(() => raw().theme)
  const fontScale = computed(() => raw().fontScale)
  const reduceMotion = computed(() => raw().motion === 'reduced')
  const soundOn = computed(() => raw().sound)
  const speechOn = computed(() => raw().speech)
  const showPinyin = computed(() => raw().showPinyin)
  const speechRate = computed(() => raw().speechRate ?? DEFAULT_SPEECH_RATE)
  const dailyLimitMinutes = computed(() => raw().restReminderMin)
  /** 学习计划：每天新字上限（0 = 不限）与计划覆盖的单元（空 = 全部）。 */
  const dailyNewCharLimit = computed(() => raw().dailyNewLimit ?? 0)
  const planUnits = computed(() => raw().planUnits ?? [])
  const listenSkin = computed(() => raw().listenSkin ?? 'fish')
  const breakReminder = computed(() => raw().breakReminder ?? DEFAULT_BREAK_REMINDER)
  const childName = computed(() => progress.state.childName)

  const themeMeta = computed(() => THEMES.find((t) => t.id === theme.value) ?? THEMES[0])
  const isEyeCare = computed(() => theme.value === 'care')

  /** 界面用词 → 底层字段。只转换出现过的键，其余原样透传。 */
  function update(patch = {}) {
    const next = {}
    for (const [key, value] of Object.entries(patch)) {
      switch (key) {
        case 'reduceMotion':
          next.motion = value ? 'reduced' : 'full'
          break
        case 'soundOn':
          next.sound = value
          break
        case 'speechOn':
          next.speech = value
          break
        case 'dailyLimitMinutes':
          next.restReminderMin = value
          break
        case 'dailyNewCharLimit':
          next.dailyNewLimit = Math.max(0, Math.round(Number(value) || 0))
          break
        case 'planUnits':
          next.planUnits = [...new Set(value ?? [])]
          break
        case 'childName':
          progress.setProfile({ childName: value })
          break
        default:
          next[key] = value
      }
    }
    if (Object.keys(next).length) progress.updateSettings(next)
  }

  function setTheme(id) {
    progress.updateSettings({ theme: id })
  }

  function cycleTheme() {
    progress.cycleTheme()
  }

  function toggleEyeCare() {
    progress.toggleEyeCare()
  }

  /** 只恢复外观相关设置，学习进度不动。 */
  function reset() {
    progress.updateSettings({
      theme: 'sunny',
      fontScale: 'normal',
      motion: 'full',
      sound: true,
      speech: true,
      showPinyin: true,
      restReminderMin: 20,
      speechRate: DEFAULT_SPEECH_RATE,
      breakReminder: DEFAULT_BREAK_REMINDER,
      listenSkin: 'fish',
      dailyNewLimit: 8,
      planUnits: []
    })
  }

  /** 勾选 / 取消一个计划单元。取消到一个不剩就回到「全部单元」。 */
  function togglePlanUnit(unitId) {
    const picked = new Set(planUnits.value)
    if (picked.has(unitId)) picked.delete(unitId)
    else picked.add(unitId)
    update({ planUnits: [...picked] })
  }

  function clearPlanUnits() {
    update({ planUnits: [] })
  }

  /** 兼容旧调用：外观在 progress store 初始化时已经应用过了。 */
  function load() {
    progress.applyAppearance()
  }

  return {
    theme,
    fontScale,
    reduceMotion,
    soundOn,
    speechOn,
    showPinyin,
    speechRate,
    dailyLimitMinutes,
    dailyNewCharLimit,
    planUnits,
    listenSkin,
    breakReminder,
    childName,
    themeMeta,
    isEyeCare,

    update,
    togglePlanUnit,
    clearPlanUnits,
    setTheme,
    cycleTheme,
    toggleEyeCare,
    reset,
    load
  }
})
