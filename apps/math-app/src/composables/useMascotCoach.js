/**
 * 小算的陪跑：把进度变成一句话，并接上数学 App 的音效与朗读。
 *
 * 页面只要写 `const { line, mood, next } = useMascotCoach('home')`，
 * 把三个值绑到 <MascotBot> 上，吉祥物就从摆设变成会说话的伙伴。
 *
 * 答题页还可以把「这一下答错没有」传进来：
 *
 *   const coach = useMascotCoach('daily', { recentWrong })
 *
 * 连击数不用传——它本来就在 progress store 里。
 */
import { computed, unref } from 'vue'
import { useMascotCompanion } from '@shared/composables/useMascotCompanion.js'
import { mascotLines, pickMascotStage } from '@/data/mascotLines.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { sound } from '@/utils/sound'
import { speak } from '@/utils/speech'

const DAY = 864e5

/** 距离上一次做题隔了几天；存档里没记过就当作今天来过。 */
function daysSince(dateKey, now = Date.now()) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dateKey ?? '')) return 0
  const then = Date.parse(`${dateKey}T00:00:00Z`)
  if (!Number.isFinite(then)) return 0
  const today = Date.parse(`${new Date(now).toISOString().slice(0, 10)}T00:00:00Z`)
  return Math.max(0, Math.round((today - then) / DAY))
}

export function useMascotCoach(scene, moment = {}) {
  const progress = useProgressStore()
  const settings = useSettingsStore()

  const context = computed(() => {
    const quest = progress.dailyQuest
    return {
      stars: progress.state.stars,
      dailyDone: quest.done,
      dailyTotal: quest.total,
      dailyCompleted: quest.completed,
      streak: quest.streak,
      combo: unref(moment.combo) ?? progress.combo ?? 0,
      wrongCount: progress.wrongCount,
      todayMinutes: progress.todayMinutes,
      daysAway: daysSince(progress.state.lastPlayedDate),
      recentWrong: unref(moment.recentWrong) ?? 0
    }
  })

  const stage = computed(() => pickMascotStage(context.value))
  const lines = computed(() => mascotLines(scene, context.value))

  const companion = useMascotCompanion({
    lines,
    speak: (text) => {
      sound.click()
      // 家长把声音关了，朗读跟着一起关——孩子还是能看见气泡里的字。
      if (settings.soundOn) speak(text)
    }
  })

  return { ...companion, stage, context }
}
