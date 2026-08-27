import { getCurrentScope, onScopeDispose } from 'vue'
import gsap from 'gsap'
import { createFeedback } from '@shared/composables/useFeedback.js'
import { sfx } from '@/utils/sound'
import { reducedMotion as prefersReducedMotion } from '@/utils/motion'

const unwrap = (target) => (target && target.$el) || target

/** 数学的粒子是几何感更强的四角星，配色跟着霓虹主题走。 */
const MATH_PARTICLES = {
  glyphs: ['★', '✦', '✧', '✩'],
  colors: ['#ffce4d', '#5ee7ff', '#ff7ac6', '#55e6a5'],
  count: 14,
  size: [8, 18],
  spread: 130
}

/**
 * 全局答题反馈集合。
 *
 * 音效 / 震动 / 粒子这三条通道跟识字共用 shared/composables/useFeedback.js，
 * 两个 App 的降级行为因此完全一致；这里额外保留几个吃 GSAP 的数学专属动画
 * （发光、飞星、入场、数字滚动）。所有函数都对 null / 未挂载元素安全，
 * 动画在 reduced-motion 下自动降级。
 */
export function useFeedback() {
  const base = createFeedback({
    sound: {
      tap: () => sfx.tap(),
      /** 连对越多音越高；cueArg 就是最新连对数。 */
      correct: (streak) => sfx.streak(Number(streak) || 1),
      wrong: () => sfx.wrong(),
      star: () => sfx.star(),
      celebrate: () => sfx.levelUp()
    },
    reducedMotion: prefersReducedMotion,
    particles: MATH_PARTICLES
  })

  function pop(target, { scale = 1.14 } = {}) {
    const el = unwrap(target)
    if (!el) return
    if (prefersReducedMotion()) return
    gsap.fromTo(
      el,
      { scale: 1 },
      { scale, duration: 0.16, yoyo: true, repeat: 1, ease: 'power2.out', overwrite: 'auto' },
    )
  }

  /**
   * 答对反馈：音效 + 震动交给共用实现，发光留给 GSAP。
   * streak 可选，未传时仍播放第一档答对音；
   * 玩法层只需在已有连击数时传入，不必为了音效维护额外状态。
   * 粒子由玩法层显式调 burst()，这里不重复撒。
   */
  function correct(target, { sound = true, streak = 1 } = {}) {
    base.correct(target, { sound, cueArg: streak, particles: false })
    const el = unwrap(target)
    if (!el || prefersReducedMotion()) return
    const tl = gsap.timeline()
    tl.fromTo(
      el,
      { scale: 1, boxShadow: '0 0 0 rgba(85,230,165,0)' },
      {
        scale: 1.08,
        boxShadow: '0 0 34px rgba(85,230,165,0.65)',
        duration: 0.18,
        ease: 'back.out(3)',
      },
    ).to(el, { scale: 1, boxShadow: '0 0 0 rgba(85,230,165,0)', duration: 0.42, ease: 'power2.out' })
    return tl
  }

  function wrong(target, { sound = true } = {}) {
    // 抖动这一路仍走 GSAP，共用实现只负责音效与震动
    base.wrong(target, { sound, shake: false })
    const el = unwrap(target)
    if (!el || prefersReducedMotion()) return
    return gsap.fromTo(
      el,
      { x: 0 },
      {
        keyframes: { x: [-12, 11, -8, 7, -4, 0] },
        duration: 0.46,
        ease: 'power2.out',
        overwrite: 'auto',
      },
    )
  }

  /** 从元素中心迸发出一圈小星星（共用粒子实现，用完自动移除）。 */
  function burst(target, options = {}) {
    return base.burst(target, options)
  }

  /** 通关 / 全对时的大庆祝：欢呼声 + 加倍粒子 + 一串震动。 */
  function celebrate(target, options = {}) {
    return base.celebrate(target, options)
  }

  /** 从起点元素飞一颗星星到终点元素（通常是顶部星星计数器）。 */
  function flyStar(fromTarget, toSelector = '[data-star-counter]', { onArrive } = {}) {
    const from = unwrap(fromTarget)
    const to = typeof document !== 'undefined' ? document.querySelector(toSelector) : null
    if (!from || !to || prefersReducedMotion()) {
      onArrive?.()
      return
    }
    const a = from.getBoundingClientRect()
    const b = to.getBoundingClientRect()
    const star = document.createElement('div')
    star.textContent = '⭐'
    star.style.cssText = `position:fixed;left:${a.left + a.width / 2}px;top:${
      a.top + a.height / 2
    }px;font-size:26px;pointer-events:none;z-index:9999;will-change:transform;`
    document.body.appendChild(star)
    gsap.to(star, {
      x: b.left + b.width / 2 - (a.left + a.width / 2),
      y: b.top + b.height / 2 - (a.top + a.height / 2),
      scale: 0.5,
      duration: 0.75,
      ease: 'power2.inOut',
      onComplete: () => {
        star.remove()
        base.star(to, { particles: false })
        onArrive?.()
        gsap.fromTo(to, { scale: 1 }, { scale: 1.25, duration: 0.14, yoyo: true, repeat: 1 })
      },
    })
  }

  /** 元素入场：错落上浮。 */
  function enter(targets, { stagger = 0.06, y = 18, delay = 0 } = {}) {
    if (prefersReducedMotion()) return
    const list = Array.isArray(targets) ? targets.map(unwrap).filter(Boolean) : unwrap(targets)
    if (!list || (Array.isArray(list) && list.length === 0)) return
    return gsap.fromTo(
      list,
      { opacity: 0, y },
      { opacity: 1, y: 0, duration: 0.42, stagger, delay, ease: 'power2.out', clearProps: 'opacity,transform' },
    )
  }

  /** 数字滚动到目标值。 */
  function countTo(obj, key, value, { duration = 0.6 } = {}) {
    if (prefersReducedMotion()) {
      obj[key] = value
      return
    }
    gsap.to(obj, { [key]: value, duration, ease: 'power2.out', snap: { [key]: 1 } })
  }

  // 路由切走时把还挂在 body 上的粒子层收干净
  if (getCurrentScope()) onScopeDispose(() => base.dispose())

  return {
    pop,
    correct,
    wrong,
    burst,
    celebrate,
    flyStar,
    enter,
    countTo,
    haptic: base.haptic,
    prefersReducedMotion
  }
}
