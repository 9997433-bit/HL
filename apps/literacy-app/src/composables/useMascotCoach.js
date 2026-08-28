/**
 * 墨墨的陪跑：把学习进度变成一句话，并接上识字 App 的音效与朗读。
 *
 * 页面只要写 `const { line, mood, next } = useMascotCoach('home')`，
 * 把三个值绑到 <MascotCompanion> 上就有了一个会说话的学伴。
 *
 * 答题页还可以把「刚才连对了几个」「这一下答错没有」传进来：
 *
 *   const coach = useMascotCoach('learn', { combo, recentWrong, char })
 *
 * 传了之后墨墨会自动换到对应的阶段剧本（连对夸一句、答错先安慰），
 * 不传就只按进度里已有的信息判断——两种写法都不会让它没话说。
 */
import { computed, unref } from 'vue'
import { useMascotCompanion } from '@shared/composables/useMascotCompanion.js'
import { mascotLines, pickMascotStage } from '@/data/mascotLines.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { sfx, speak } from '@/utils/audio.js'

const DAY = 86400000

const dayKey = (ts) => {
  const d = new Date(ts)
  return `${d.getFullYear()}-${`${d.getMonth() + 1}`.padStart(2, '0')}-${`${d.getDate()}`.padStart(2, '0')}`
}

/**
 * 距离上一次真正学过东西隔了几天。
 *
 * 只认「有学过字或坐够一分钟」的日子：孩子昨天点进来又立刻退出去，
 * 不该让墨墨今天开口就说「好久不见」。
 */
function daysSinceLastVisit(daily, now = Date.now()) {
  const active = Object.entries(daily ?? {})
    .filter(([, d]) => (d?.chars?.length ?? 0) > 0 || (d?.seconds ?? 0) > 60)
    .map(([key]) => key)
    .sort()
  const last = active[active.length - 1]
  if (!last) return 0
  for (let i = 0; i < 400; i += 1) {
    if (dayKey(now - i * DAY) === last) return i
  }
  return 400
}

export function useMascotCoach(scene, moment = {}) {
  const progress = useProgressStore()
  const settings = useSettingsStore()

  /** 阶段判断要用的上下文：进度里有的自己取，页面才知道的由 moment 传。 */
  const context = computed(() => ({
    name: settings.childName,
    learned: progress.learnedCount,
    mastered: progress.masteredCount,
    due: progress.dueCount,
    streak: progress.streakDays,
    books: progress.booksFinished,
    idioms: progress.idiomsSeen,
    poems: progress.poemsRead,
    songs: progress.songsSung,
    nextChar: progress.nextChar?.char ?? '',
    newCharsToday: progress.newCharsToday,
    dailyLimitReached: progress.dailyLimitReached,
    sessionMinutes: Math.floor(progress.sessionSeconds / 60),
    restDue: progress.restDue,
    daysAway: daysSinceLastVisit(progress.daily),
    combo: unref(moment.combo) ?? 0,
    recentWrong: unref(moment.recentWrong) ?? 0,
    justMastered: Boolean(unref(moment.justMastered)),
    lastChar: unref(moment.char) ?? ''
  }))

  const stage = computed(() => pickMascotStage(context.value))
  const lines = computed(() => mascotLines(scene, context.value))

  const companion = useMascotCompanion({
    lines,
    speak: (text) => {
      // 朗读总开关在 progress store 里统一管，这里不再判一次。
      sfx.tap()
      speak(text, { rate: settings.speechRate })
    }
  })

  return { ...companion, stage, context }
}
