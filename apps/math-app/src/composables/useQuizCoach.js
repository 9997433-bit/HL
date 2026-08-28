/**
 * 答题壳里的小算。
 *
 * QuizShell 判完题只会说「正确答案是 7，已记进错题本」——这句是判词，不是陪跑。
 * 判完之后停顿那一下、切到下一题的那一下，本该有人接一句话，而「该接哪一句」
 * 恰好就是阶段台词在管的事：连着答错要安慰，连着答对要提醒别飘，错题欠多了
 * 要提一句，坐太久了要劝歇。
 *
 * 缺的接线是 `recentWrong`：连着答错几道只有答题壳自己知道，不传进去，
 * 小算永远走不到「算错了」那组台词。所以这里把它接上，再给出两个出口：
 *
 *   coach.opener()   下一题开口前的那句话；此刻没什么特别要说的就返回空串，
 *                    让答题壳照旧用自己的题间鼓励语，不硬塞
 *   coach.next()     孩子点了小算：换一句、读出来
 */
import { useMascotCoach } from '@/composables/useMascotCoach.js'
import { mascotStageLines, pickMascotStage } from '@/data/mascotLines.js'

/** 关键路径接线的版本标记；答题壳挂在 data- 属性上，探针与走查都认它。 */
export const ROUND17_H5 = 'ROUND17_H5'

/**
 * 只有这几个阶段值得抢下一题的开场白。
 * 「今日冒险还差几道」「今天够了」这类话在首页说才合适，答题当中说等于打断。
 */
const SPEAKING_STAGES = new Set(['comeback', 'fatigue', 'combo', 'wrongBook', 'encourage'])

export function useQuizCoach(moment = {}) {
  const coach = useMascotCoach('daily', moment)
  let turn = 0

  /** 下一题的开场白；此刻没什么特别要说的就返回空串。 */
  function opener() {
    const ctx = coach.context.value
    const stage = pickMascotStage(ctx)
    if (!SPEAKING_STAGES.has(stage.id)) return ''
    const lines = mascotStageLines(stage.id, ctx).filter((text) => text && text.trim())
    if (!lines.length) return ''
    turn += 1
    return lines[turn % lines.length]
  }

  return { ...coach, opener, script: ROUND17_H5 }
}
