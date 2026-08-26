/**
 * 进度 store — 掌握度 / 星星 / 徽章 / 打卡,localStorage 持久化。
 */
import { defineStore } from 'pinia'
import { updateMastery, MASTERY_THRESHOLD } from '@/core/engine/adaptive.js'
import { SKILLS } from '@/data/curriculum.js'

const STORAGE_KEY = 'mathquest/progress'

function load() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) ?? {}
  } catch {
    return {}
  }
}

export const useProgressStore = defineStore('progress', {
  state: () => ({
    mastery: {},        // { skillId: 0..1 }
    stars: 0,
    badges: [],         // 徽章 id 列表
    streak: 0,          // 连续打卡天数
    lastPlayedDate: '', // YYYY-MM-DD
    errorTagCounts: {}, // { carry: 3, borrow: 1 } 错因统计,家长报告用
    ...load()
  }),

  getters: {
    masteredCount: (s) =>
      Object.values(s.mastery).filter((m) => m >= MASTERY_THRESHOLD).length,
    totalSkills: () => SKILLS.length,
    moduleProgress: (s) => (moduleId) => {
      const skills = SKILLS.filter((k) => k.module === moduleId)
      if (!skills.length) return 0
      const sum = skills.reduce((acc, k) => acc + (s.mastery[k.id] ?? 0), 0)
      return sum / skills.length
    }
  },

  actions: {
    /** 答题结果上报:更新掌握度、错因统计、星星与打卡 */
    recordAnswer(question, isCorrect) {
      const skillId = question.skill
      this.mastery[skillId] = updateMastery(this.mastery[skillId], isCorrect)
      if (isCorrect) {
        this.stars += 1
      } else {
        for (const tag of question.meta?.errorTags ?? []) {
          this.errorTagCounts[tag] = (this.errorTagCounts[tag] ?? 0) + 1
        }
      }
      this.touchStreak()
      this.persist()
    },

    touchStreak() {
      const today = new Date().toISOString().slice(0, 10)
      if (this.lastPlayedDate === today) return
      const yesterday = new Date(Date.now() - 864e5).toISOString().slice(0, 10)
      this.streak = this.lastPlayedDate === yesterday ? this.streak + 1 : 1
      this.lastPlayedDate = today
    },

    /** 家长页 JSON 导出 */
    exportReport() {
      return JSON.stringify(
        {
          exportedAt: new Date().toISOString(),
          mastery: this.mastery,
          stars: this.stars,
          streak: this.streak,
          errorTagCounts: this.errorTagCounts
        },
        null,
        2
      )
    },

    persist() {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          mastery: this.mastery,
          stars: this.stars,
          badges: this.badges,
          streak: this.streak,
          lastPlayedDate: this.lastPlayedDate,
          errorTagCounts: this.errorTagCounts
        })
      )
    }
  }
})
