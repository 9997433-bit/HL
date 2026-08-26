/**
 * 小游戏的出题池。
 *
 * 规则只有一条：**只出已经学过的字**。小游戏是复习场，出没见过的字
 * 既打击信心又教不会东西。已学字不够开一局时（比如刚装上应用），
 * 才退回课程最前面的几个字，并让界面挂一句说明——这跟听音识字
 * （ListenGameView）的做法保持一致，孩子在两处看到的规则是同一套。
 *
 * 到期要复习的字会被排到前面：谁快忘了谁先出场。
 */

import { computed } from 'vue'
import { CHARACTERS } from '@/data/characters.js'
import { useProgressStore } from '@/stores/progress.js'

export function useCharPool(minSize = 4) {
  const progress = useProgressStore()

  const learned = computed(() => CHARACTERS.filter((c) => progress.isLearned(c.char)))

  /** 已学字不够开一局，这一局用课程最前面的字顶上。 */
  const usingFallback = computed(() => learned.value.length < minSize)

  const pool = computed(() =>
    usingFallback.value ? CHARACTERS.slice(0, Math.max(minSize, 8)) : learned.value
  )

  /**
   * 出题顺序：到期复习的字排前面，其余随机跟在后面。
   * 返回的是一个函数而不是 computed，因为每一关都要重新抽一次。
   */
  function drawPool() {
    const list = pool.value
    const due = progress.reviewQueue.filter((c) => list.some((x) => x.char === c.char))
    const rest = list.filter((c) => !due.some((d) => d.char === c.char))
    return { due, rest, all: list }
  }

  return { pool, learned, usingFallback, drawPool }
}
