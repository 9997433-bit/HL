/**
 * 单字学习页上的墨墨。
 *
 * `useMascotCoach` 已经会按孩子的状态挑阶段台词了，但它挑的是「今天整体怎么样」；
 * 单字页还有一层更近的「此刻」——刚走到第几步、上一题答对没有、这个字是不是
 * 刚刚掌握。这层信息只有页面知道，所以这里在陪跑外面再包一拍：
 *
 *   const coach = useCharCoach({ combo, recentWrong, justMastered, char })
 *   coach.enterStep('listen')          // 走到「练一练」，先说这一步要干什么
 *   coach.judge('wrong')               // 判完一题，让阶段台词接话
 *
 * 两拍的分工：进新一步时页面自己的话在前（孩子要先知道现在干什么），
 * 判完一题时阶段台词在前（连对该夸、答错该安慰，这些阶段那一层已经判过了）。
 * 临时顶上来的那句叫 `cue`，孩子点一下墨墨就把它丢掉，回到轮换台词。
 */
import { computed, ref } from 'vue'
import { useMascotCoach } from '@/composables/useMascotCoach.js'
import { mascotStageLines, pickMascotStage } from '@/data/mascotLines.js'

/** 关键路径接线的版本标记；页面挂在 data- 属性上，探针与走查都认它。 */
export const ROUND17_H5 = 'ROUND17_H5'

/** 五步各自的开场白：说清楚这一步要干什么，比一句「加油」有用。 */
const STEP_LINES = {
  play: [
    '先陪这个字玩一小会儿，玩过了它就不陌生了。',
    '这一步不考你，随便点随便试。',
    '玩不玩都能往下走，想直接认字也行。'
  ],
  intro: [
    '来看看这个字长什么样，它当初是照着什么画出来的。',
    '先看形状，再听读音，认字就是这个顺序。',
    '看完记得点一下喇叭，听我读一遍给你听。'
  ],
  listen: [
    '这一步考耳朵：听清楚了再从三个字里挑。',
    '三个字长得很像，别急着按，先听完。',
    '没听清就再点一次「再听一次」，听几遍都行。'
  ],
  trace: [
    '轮到手了，在田字格里按笔顺写一遍。',
    '写慢一点没关系，笔顺对了字就好看。',
    '写不动就按空格键，我帮你起个头。'
  ],
  speak: [
    '最后一步：说说看这个字是什么意思。',
    '答完这一题，这一趟的星星就到手了。',
    '意思记不准就先读一遍例句，答案常常藏在里面。'
  ]
}

/** 判完一题、写完一遍之后自己这一拍的话；阶段台词没什么特别时才轮到它。 */
const BEAT_LINES = {
  right: [
    '对了，这个字你是真记住了。',
    '答得又快又准，继续。',
    '就是它，我们接着往下走。'
  ],
  wrong: [
    '再看一遍这个字，这次一定能记住。',
    '认岔了不要紧，形近的字本来就容易看混。',
    '别急，我们把它拆开看看哪里不一样。'
  ],
  traced: [
    '写完啦，笔顺走对了字就立得住。',
    '这一遍写得比上一遍稳，手记住了。',
    '写过一遍的字，比只看过的记得久得多。'
  ],
  reward: [
    '一整趟都走完了，星星拿好。',
    '玩认练写说五步都做全了，这才叫真学过一遍。',
    '这个字今天算是交给你了，下次见到别装不认识。'
  ]
}

/** 这些阶段是「此刻」真正要紧的事，判完一题时让它们先开口。 */
const URGENT_STAGES = new Set(['comeback', 'fatigue', 'mastered', 'combo', 'encourage'])

/** 每一拍的表情；没写的拍子跟着陪跑本来的表情走。 */
const BEAT_MOODS = {
  right: 'happy',
  wrong: 'sad',
  traced: 'happy',
  mastered: 'cheer',
  reward: 'cheer'
}

export function useCharCoach(moment = {}) {
  const coach = useMascotCoach('learn', moment)

  /** 关键路径上临时顶上来的那一句；空字符串表示照常轮换台词。 */
  const cue = ref('')
  const beatMood = ref('')
  let turn = 0

  const line = computed(() => cue.value || coach.line.value)
  const mood = computed(() => beatMood.value || coach.mood.value)

  const pick = (list) => {
    const usable = list.filter((text) => typeof text === 'string' && text.trim())
    if (!usable.length) return ''
    turn += 1
    return usable[turn % usable.length]
  }

  /** 当前该说哪一类话，以及那一类里有些什么。 */
  const stageLines = () => {
    const ctx = coach.context.value
    return mascotStageLines(pickMascotStage(ctx).id, ctx)
  }

  /** 走到新一步：先说这一步要干什么，没写台词的步骤退回阶段台词。 */
  function enterStep(id) {
    beatMood.value = ''
    cue.value = pick([...(STEP_LINES[id] ?? []), ...stageLines()])
  }

  /** 判完一题：连对、答错、刚掌握这些都在阶段那一层判过了，让它先说。 */
  function judge(beat) {
    const own = BEAT_LINES[beat] ?? []
    const staged = stageLines()
    const urgent = URGENT_STAGES.has(pickMascotStage(coach.context.value).id)
    beatMood.value = BEAT_MOODS[beat] ?? ''
    cue.value = pick(urgent ? [...staged, ...own] : [...own, ...staged])
  }

  /** 点一下墨墨：丢掉临时那句，回到轮换台词并读出来。 */
  function next() {
    cue.value = ''
    beatMood.value = ''
    return coach.next()
  }

  /** 重新走一遍：把这一趟攒下的「此刻」清空。 */
  function reset() {
    cue.value = ''
    beatMood.value = ''
  }

  return { ...coach, line, mood, next, enterStep, judge, reset, script: ROUND17_H5 }
}
