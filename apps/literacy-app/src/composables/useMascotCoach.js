/**
 * 墨墨的陪跑：把学习进度变成一句话，并接上识字 App 的音效与朗读。
 *
 * 页面只要写 `const { line, mood, next } = useMascotCoach('home')`，
 * 把三个值绑到 <MascotCompanion> 上就有了一个会说话的学伴。
 */
import { computed } from 'vue'
import { useMascotCompanion } from '@shared/composables/useMascotCompanion.js'
import { mascotLines } from '@/data/mascotLines.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { sfx, speak } from '@/utils/audio.js'

export function useMascotCoach(scene) {
  const progress = useProgressStore()
  const settings = useSettingsStore()

  const lines = computed(() =>
    mascotLines(scene, {
      name: settings.childName,
      learned: progress.learnedCount,
      mastered: progress.masteredCount,
      due: progress.dueCount,
      streak: progress.streakDays,
      books: progress.booksFinished,
      idioms: progress.idiomsSeen,
      nextChar: progress.nextChar?.char ?? ''
    })
  )

  return useMascotCompanion({
    lines,
    speak: (text) => {
      // 朗读总开关在 progress store 里统一管，这里不再判一次。
      sfx.tap()
      speak(text, { rate: settings.speechRate })
    }
  })
}
