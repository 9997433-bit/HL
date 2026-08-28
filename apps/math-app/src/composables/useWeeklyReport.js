/**
 * 把进度 store 接到家长周报上。
 *
 * 组件里写 `const report = useWeeklyReport()`，拿到的是一个 computed：
 * `report.value.headline` 是本周弱项那一句话，`report.value.drills` 是
 * 最多三条建议练习。算法在 utils/weeklyReport.js，那边不认识 Vue、也不认识
 * curriculum 与错因词典，全靠这里喂数据——所以那边能被 Node 直接跑起来测。
 */
import { computed } from 'vue'
import { buildWeeklyReport } from '@/utils/weeklyReport.js'
import { SKILLS } from '@/data/curriculum.js'
import { MODULES } from '@/data/modules.js'
import { errorTagInfo } from '@/data/errorTags.js'
import { MASTERY_THRESHOLD } from '@/utils/mastery.js'
import { useProgressStore } from '@/stores/progress.js'

/** curriculum 模块 id → 星球路由，弱项技能点靠它给出「点这里去练」。 */
const routeOfCurriculum = (curriculumId) =>
  MODULES.find((m) => m.curriculumId === curriculumId)?.route ?? '/'

export function useWeeklyReport() {
  const progress = useProgressStore()

  return computed(() =>
    buildWeeklyReport({
      days: progress.last7Days,
      accuracy: progress.accuracy,
      wrongCount: progress.wrongCount,
      errorTagCounts: progress.errorTagCounts,
      errorTagInfo,
      masteryThreshold: MASTERY_THRESHOLD,
      skills: SKILLS.map((s) => ({
        id: s.id,
        name: s.name,
        mastery: progress.mastery[s.id],
        route: routeOfCurriculum(s.module)
      })),
      modules: MODULES.map((m) => ({
        id: m.id,
        name: m.name,
        subtitle: m.subtitle,
        route: m.route,
        answered: progress.moduleStat(m.id).answered
      }))
    })
  )
}
