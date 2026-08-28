/**
 * 识字 App 的正反馈入口。
 *
 * 通用逻辑（粒子、震动降级、reduced-motion 合流）都在 shared/composables/useFeedback.js，
 * 这里只做接线：把识字自己的音效实现和家长设置接进去，再补两个识字特有的动作
 * （笔顺的 stroke、连对递进的 correct）。玩法组件只认这一个入口，
 * 不用再自己判断「现在能不能动 / 该不该响」。
 */

import { getCurrentScope, onScopeDispose } from 'vue'
import { createFeedback } from '@shared/composables/useFeedback.js'
import { sfx } from '@/utils/sfx.js'
import { useSettingsStore } from '@/stores/settings.js'

/** 识字用暖色系的星星与花瓣，跟绘本插画一个调子。 */
const LITERACY_PARTICLES = {
  glyphs: ['⭐', '🌟', '✨', '🎉', '🏅'],
  count: 16
}

export function useFeedback({ particles, ...overrides } = {}) {
  // 家长面板里的「减少动效」；在组件外调用（单测、工具脚本）时退回系统偏好
  let settings = null
  try {
    settings = useSettingsStore()
  } catch {
    settings = null
  }

  const feedback = createFeedback({
    sound: {
      tap: () => sfx.tap(),
      /** 连对越多音越高：把最新连对数当 cueArg 传进来就行。 */
      correct: (streak) => (Number(streak) > 1 ? sfx.streak(streak) : sfx.correct()),
      wrong: () => sfx.wrong(),
      star: () => sfx.star(),
      celebrate: () => sfx.celebrate(),
      /** 写对一笔：笔序越靠后音越高。 */
      stroke: (index) => sfx.stroke(Number(index) || 0)
    },
    reducedMotion: () => settings?.reduceMotion === true,
    ...overrides,
    particles: { ...LITERACY_PARTICLES, ...particles }
  })

  /** 写对一笔的轻反馈：一声 + 一下轻震，不放粒子——一个字十几笔，撒不起。 */
  const stroke = (index = 0) => feedback.cue('stroke', null, { cueArg: index, particles: false })

  // 组件卸载 / 路由切走时把还没落地的粒子层收干净
  if (getCurrentScope()) onScopeDispose(() => feedback.dispose())

  return { ...feedback, stroke }
}

export default useFeedback
