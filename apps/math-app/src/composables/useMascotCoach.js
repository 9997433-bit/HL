/**
 * 小算的陪跑：把进度变成一句话，并接上数学 App 的音效与朗读。
 *
 * 页面只要写 `const { line, mood, next } = useMascotCoach('home')`，
 * 把三个值绑到 <MascotBot> 上，吉祥物就从摆设变成会说话的伙伴。
 */
import { computed } from 'vue'
import { useMascotCompanion } from '@shared/composables/useMascotCompanion.js'
import { mascotLines } from '@/data/mascotLines.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { sound } from '@/utils/sound'
import { speak } from '@/utils/speech'

export function useMascotCoach(scene) {
  const progress = useProgressStore()
  const settings = useSettingsStore()

  const lines = computed(() => {
    const quest = progress.dailyQuest
    return mascotLines(scene, {
      stars: progress.state.stars,
      dailyDone: quest.done,
      dailyTotal: quest.total,
      dailyCompleted: quest.completed,
      streak: quest.streak
    })
  })

  return useMascotCompanion({
    lines,
    speak: (text) => {
      sound.click()
      // 家长把声音关了，朗读跟着一起关——孩子还是能看见气泡里的字。
      if (settings.soundOn) speak(text)
    }
  })
}
