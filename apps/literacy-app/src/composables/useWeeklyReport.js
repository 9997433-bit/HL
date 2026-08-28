/**
 * 把进度 store 接到家长周报上。
 *
 * 组件里写 `const report = useWeeklyReport()`，拿到的是一个 computed：
 * `report.value.headline` 是本周弱项那一句话，`report.value.drills` 是
 * 最多三条建议练习。算法在 utils/weeklyReport.js，那边不认识 Vue 也不认识 store，
 * 这里只负责喂数据。
 */
import { computed } from 'vue'
import { buildWeeklyReport } from '@/utils/weeklyReport.js'
import { useProgressStore } from '@/stores/progress.js'

export function useWeeklyReport() {
  const progress = useProgressStore()

  return computed(() =>
    buildWeeklyReport({
      days: progress.last7Days,
      chars: progress.chars,
      memoryCards: progress.memoryCards,
      dueCount: progress.dueCount,
      averageRetention: progress.averageRetention,
      accuracy: progress.accuracy,
      learnedCount: progress.learnedCount,
      masteredCount: progress.masteredCount,
      booksFinished: progress.booksFinished,
      poemsRead: progress.poemsRead,
      streakDays: progress.streakDays
    })
  )
}
