import gsap from 'gsap'
import { sfx } from '@/utils/sound'
import { reducedMotion as prefersReducedMotion } from '@/utils/motion'

const unwrap = (target) => (target && target.$el) || target

/**
 * 全局答题反馈动画集合（GSAP）。
 * 所有函数都对 null / 未挂载元素安全，动画在 reduced-motion 下自动降级。
 */
export function useFeedback() {
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
   * 答对反馈。streak 可选，未传时仍播放第一档答对音；
   * 玩法层只需在已有连击数时传入，不必为了音效维护额外状态。
   */
  function correct(target, { sound = true, streak = 1 } = {}) {
    if (sound) sfx.streak(streak)
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
    if (sound) sfx.wrong()
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

  /** 从元素中心迸发出一圈小星星（纯 DOM 粒子，用完自动移除）。 */
  function burst(target, { count = 14, colors = ['#ffce4d', '#5ee7ff', '#ff7ac6', '#55e6a5'] } = {}) {
    const el = unwrap(target)
    if (!el || prefersReducedMotion() || typeof document === 'undefined') return
    const rect = el.getBoundingClientRect()
    const cx = rect.left + rect.width / 2
    const cy = rect.top + rect.height / 2
    const layer = document.createElement('div')
    layer.style.cssText =
      'position:fixed;inset:0;pointer-events:none;z-index:9999;contain:layout style paint;'
    document.body.appendChild(layer)

    for (let i = 0; i < count; i++) {
      const dot = document.createElement('span')
      const size = 8 + Math.random() * 10
      dot.textContent = Math.random() > 0.45 ? '★' : '✦'
      dot.style.cssText = `position:absolute;left:${cx}px;top:${cy}px;font-size:${size}px;color:${
        colors[i % colors.length]
      };will-change:transform,opacity;`
      layer.appendChild(dot)
      const angle = (Math.PI * 2 * i) / count + Math.random() * 0.5
      const dist = 60 + Math.random() * 110
      gsap.to(dot, {
        x: Math.cos(angle) * dist,
        y: Math.sin(angle) * dist - 30,
        opacity: 0,
        rotation: Math.random() * 360,
        scale: 0.3,
        duration: 0.7 + Math.random() * 0.4,
        ease: 'power2.out',
      })
    }
    gsap.delayedCall(1.3, () => layer.remove())
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
        sfx.star()
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

  return { pop, correct, wrong, burst, flyStar, enter, countTo, prefersReducedMotion }
}
