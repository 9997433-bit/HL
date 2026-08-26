import gsap from 'gsap'

const unwrap = (target) => target?.$el ?? target

const reducedMotion = () =>
  typeof window !== 'undefined' &&
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches === true

const targetsOf = (targets) => {
  if (!targets) return []
  const list =
    typeof targets === 'string'
      ? typeof document === 'undefined'
        ? []
        : [...document.querySelectorAll(targets)]
      : gsap.utils.toArray(targets)
  return list.map(unwrap).filter(Boolean)
}

const revealImmediately = (targets) => {
  const elements = targetsOf(targets)
  if (elements.length) gsap.set(elements, { autoAlpha: 1, x: 0, y: 0, scale: 1 })
  return elements
}

/**
 * 元素错落上浮入场。开启“减少动态效果”时只恢复元素可见性。
 */
export function entrance(targets, options = {}) {
  const elements = targetsOf(targets)
  if (!elements.length) return null
  if (reducedMotion()) {
    revealImmediately(elements)
    return null
  }

  const {
    y = 28,
    duration = 0.55,
    stagger = 0.08,
    delay = 0,
    ease = 'back.out(1.35)',
  } = options

  return gsap.fromTo(
    elements,
    { autoAlpha: 0, y, scale: 0.96 },
    {
      autoAlpha: 1,
      y: 0,
      scale: 1,
      duration,
      stagger,
      delay,
      ease,
      clearProps: 'opacity,visibility,transform',
      overwrite: 'auto',
    },
  )
}

/**
 * 庆祝预设：目标弹跳并旋转一周，可配合 sounds.celebration() 使用。
 */
export function celebration(targets, options = {}) {
  const elements = targetsOf(targets)
  if (!elements.length) return null
  if (reducedMotion()) {
    revealImmediately(elements)
    return null
  }

  const {
    duration = 0.75,
    stagger = 0.06,
    rotation = 360,
    scale = 1.2,
  } = options

  const timeline = gsap.timeline({ defaults: { overwrite: 'auto' } })
  timeline
    .fromTo(
      elements,
      { autoAlpha: 0, y: 24, scale: 0.5, rotation: -12 },
      {
        autoAlpha: 1,
        y: -12,
        scale,
        rotation,
        duration,
        stagger,
        ease: 'back.out(1.8)',
      },
    )
    .to(elements, {
      y: 0,
      scale: 1,
      rotation: 0,
      duration: 0.3,
      stagger,
      ease: 'bounce.out',
      clearProps: 'opacity,visibility,transform',
    })

  return timeline
}

/**
 * 错误反馈左右摇晃，不修改元素的初始 translate。
 */
export function shake(target, options = {}) {
  const element = unwrap(target)
  if (!element || reducedMotion()) return null

  const { distance = 12, duration = 0.42 } = options
  return gsap.to(element, {
    keyframes: [
      { x: `-=${distance}` },
      { x: `+=${distance * 2}` },
      { x: `-=${distance * 1.65}` },
      { x: `+=${distance * 1.1}` },
      { x: `-=${distance * 0.45}` },
    ],
    duration,
    ease: 'power2.out',
    overwrite: 'auto',
  })
}

/**
 * 正确反馈弹跳，可选择循环次数；默认只播放一次。
 */
export function bounce(targets, options = {}) {
  const elements = targetsOf(targets)
  if (!elements.length || reducedMotion()) return null

  const { height = 20, duration = 0.5, repeat = 0, stagger = 0.05 } = options
  return gsap.fromTo(
    elements,
    { y: 0 },
    {
      keyframes: [
        { y: -height, scaleX: 0.96, scaleY: 1.04, ease: 'power2.out' },
        { y: 0, scaleX: 1.05, scaleY: 0.95, ease: 'bounce.out' },
        { scaleX: 1, scaleY: 1, ease: 'power1.out' },
      ],
      duration,
      repeat,
      stagger,
      overwrite: 'auto',
      clearProps: 'transform',
    },
  )
}

export const animationPresets = {
  entrance,
  celebration,
  shake,
  bounce,
}

export { reducedMotion as prefersReducedMotion }
export default animationPresets
