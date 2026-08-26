/**
 * 动效总开关 —— 和 sound.setEnabled 一个套路：
 * App 根组件把家长设置同步到这里，动画代码只问「现在能不能动」，
 * 不用每处都去 import store，也就不会有组件外调用 pinia 的问题。
 */

let enabled = true

export const motion = {
  setEnabled(value) {
    enabled = !!value
  },
}

/** 家长关掉动效，或系统开了 prefers-reduced-motion，都算「要减少动画」。 */
export function reducedMotion() {
  if (!enabled) return true
  return (
    typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches === true
  )
}
