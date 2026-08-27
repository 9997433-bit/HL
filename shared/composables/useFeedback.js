/**
 * 统一正反馈 —— 两个 App 共用一份「答对 / 答错时到底发生什么」。
 *
 * 在这之前，识字和数学各写各的：识字用 StarBurst + sfx，数学用 GSAP + sound，
 * 于是「答对」在两边的手感、时长、要不要震动都不一样，减少动效开关也只关掉了一半。
 * 这里把三条通道收成一处，各 App 只负责把自己的音效实现和设置项接进来：
 *
 *   粒子   仅用 Web Animations API，不依赖 GSAP，Node 里也能跑单测；
 *   音效   通过钩子注入（对象映射或单个函数），composable 自己不认识任何音频实现；
 *   震动   navigator.vibrate 逐级降级：不支持 → 静默跳过，减少动效 → 缩成一次轻震；
 *   动效   系统 prefers-reduced-motion 与 App 自己的「减少动效」开关取并集。
 *
 * 三条通道各自独立降级：没有震动能力不影响粒子，关掉动效不影响音效，
 * 所以任何一档降级下「答对了」这件事都仍然有反馈。
 */

/** 每种反馈的震动节奏（毫秒）。降级档只取第一段，见 haptic()。 */
export const HAPTIC_PATTERNS = {
  tap: [10],
  correct: [18, 40, 24],
  wrong: [40, 70, 40],
  star: [12, 30, 12],
  celebrate: [24, 40, 24, 40, 70]
}

/** 粒子默认长相：星星与亮片各半，够喜庆又不至于糊住题面。 */
export const DEFAULT_PARTICLES = {
  glyphs: ['⭐', '✨', '🌟', '💫'],
  /** 逐个循环取用；留空表示沿用元素自己的颜色（emoji 粒子就该留空）。 */
  colors: [],
  count: 14,
  spread: 130,
  rise: 34,
  duration: 900,
  size: [14, 26]
}

const isBrowser = () => typeof window !== 'undefined' && typeof document !== 'undefined'

const asBool = (value, fallback) => {
  if (typeof value === 'function') return !!value()
  if (value == null) return fallback
  return !!value
}

const rand = (min, max) => min + Math.random() * (max - min)

/** 组件实例、ref、原生节点都能当靶子传进来。 */
const unwrap = (target) => {
  const el = target?.$el ?? target?.value ?? target
  return el && typeof el.getBoundingClientRect === 'function' ? el : null
}

/** 系统层面的「减少动态效果」。 */
export function systemReducedMotion() {
  if (!isBrowser()) return false
  return window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches === true
}

/** 这台设备到底能不能震。桌面浏览器与 iOS Safari 都不能，属于常态而非异常。 */
export function canVibrate() {
  return typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function'
}

/** 本页有没有过真实手势。没有 userActivation 的浏览器靠这个兜底。 */
let sawGesture = false
let gestureWatched = false

function watchFirstGesture() {
  if (gestureWatched || !isBrowser()) return
  gestureWatched = true
  const mark = () => {
    sawGesture = true
  }
  for (const type of ['pointerdown', 'touchstart', 'keydown']) {
    window.addEventListener(type, mark, { once: true, passive: true, capture: true })
  }
}

/**
 * 孩子还没碰过屏幕就震动，Chrome 会拒绝执行并在控制台报一条错误
 * （见 chromestatus 5644273861001216）。自动衔接、定时提示这类非手势路径
 * 因此必须先问一句「这一页被点过吗」，没点过就安静跳过。
 */
export function hasUserActivation() {
  if (typeof navigator === 'undefined') return false
  const activation = navigator.userActivation
  if (activation && typeof activation.hasBeenActive === 'boolean') return activation.hasBeenActive
  return sawGesture
}

/**
 * 正反馈工厂。
 *
 * @param {object} [adapters]
 * @param {object|Function} [adapters.sound]
 *        音效钩子：{ tap, correct, wrong, star, celebrate } 映射，或 (cue) => void 单函数。
 *        缺哪个 cue 就静默跳过哪个，composable 不关心底下是 WebAudio 还是音频文件。
 * @param {Function|boolean} [adapters.reducedMotion] App 自己的「减少动效」开关。
 * @param {Function|boolean} [adapters.haptics=true] 家长关掉震动时传 false。
 * @param {object} [adapters.particles] 覆盖 DEFAULT_PARTICLES 的任意字段。
 */
export function createFeedback(adapters = {}) {
  const {
    sound,
    reducedMotion: appReducedMotion,
    haptics = true,
    particles: particleOptions,
    zIndex = 9999
  } = adapters

  watchFirstGesture()

  const particleDefaults = { ...DEFAULT_PARTICLES, ...particleOptions }
  /** 还在场上的粒子层，卸载时一起收走，避免路由切走后留下孤儿节点。 */
  const layers = new Set()

  /** 系统偏好与 App 开关取并集：任意一边说「少动」就少动。 */
  const reduced = () => asBool(appReducedMotion, false) || systemReducedMotion()

  /**
   * 奏一声。cueArg 原样透传给钩子（识字用它传连对数，笔顺用它传笔序），
   * 音高怎么随连对递进由各 App 的音效实现决定，这里不做假设。
   */
  function playCue(cue, cueArg) {
    if (!sound) return false
    try {
      if (typeof sound === 'function') {
        sound(cue, cueArg)
        return true
      }
      const fn = sound[cue]
      if (typeof fn !== 'function') return false
      fn(cueArg)
      return true
    } catch {
      // 音频上下文没被手势激活时浏览器会抛错，反馈不该因此中断
      return false
    }
  }

  /**
   * 震动一下，逐级降级：
   * 关掉了 / 设备不支持 / 本页还没被点过 → 什么都不做；
   * 减少动效 → 只震最短的一下。
   * @returns {boolean} 是否真的震了
   */
  function haptic(cue) {
    if (!asBool(haptics, true) || !canVibrate() || !hasUserActivation()) return false
    const pattern = HAPTIC_PATTERNS[cue] ?? HAPTIC_PATTERNS.tap
    const eased = reduced() ? [pattern[0]] : pattern
    try {
      return navigator.vibrate(eased) !== false
    } catch {
      return false
    }
  }

  function dropLayer(layer) {
    layers.delete(layer)
    layer.remove()
  }

  /**
   * 从元素中心迸一圈粒子。用完即焚：动画结束或 1.5 秒兜底之后整层移除。
   * @returns {boolean} 是否真的放了粒子
   */
  function burst(target, options = {}) {
    const el = unwrap(target)
    if (!el || !isBrowser() || reduced()) return false

    const conf = { ...particleDefaults, ...options }
    const rect = el.getBoundingClientRect()
    const cx = rect.left + rect.width / 2
    const cy = rect.top + rect.height / 2

    const layer = document.createElement('div')
    layer.setAttribute('aria-hidden', 'true')
    layer.style.cssText =
      `position:fixed;inset:0;pointer-events:none;contain:layout style paint;z-index:${zIndex};`
    document.body.appendChild(layer)
    layers.add(layer)

    const [minSize, maxSize] = conf.size
    for (let i = 0; i < conf.count; i += 1) {
      const dot = document.createElement('span')
      dot.textContent = conf.glyphs[i % conf.glyphs.length]
      const color = conf.colors.length ? `color:${conf.colors[i % conf.colors.length]};` : ''
      dot.style.cssText =
        `position:absolute;left:${cx}px;top:${cy}px;font-size:${rand(minSize, maxSize)}px;` +
        `line-height:1;will-change:transform,opacity;${color}`
      layer.appendChild(dot)

      const angle = (Math.PI * 2 * i) / conf.count + rand(0, 0.5)
      const dist = conf.spread * rand(0.5, 1)
      dot.animate?.(
        [
          { transform: 'translate(-50%, -50%) scale(0.3)', opacity: 1 },
          {
            transform:
              `translate(calc(-50% + ${Math.cos(angle) * dist}px), ` +
              `calc(-50% + ${Math.sin(angle) * dist - conf.rise}px)) ` +
              `rotate(${rand(-180, 180)}deg) scale(1)`,
            opacity: 0
          }
        ],
        { duration: conf.duration * rand(0.75, 1.15), easing: 'cubic-bezier(.16,.84,.44,1)' }
      )
    }

    // WAAPI 不可用时上面的 animate?.() 直接跳过，这里照样把层收掉，绝不残留
    window.setTimeout(() => dropLayer(layer), conf.duration + 600)
    return true
  }

  /** 答错时的左右晃动；减少动效下自动跳过，只留音效与震动。 */
  function shake(target, { distance = 10, duration = 420 } = {}) {
    const el = unwrap(target)
    if (!el || reduced() || typeof el.animate !== 'function') return false
    el.animate(
      [
        { transform: 'translateX(0)' },
        { transform: `translateX(${-distance}px)` },
        { transform: `translateX(${distance * 0.85}px)` },
        { transform: `translateX(${-distance * 0.5}px)` },
        { transform: 'translateX(0)' }
      ],
      { duration, easing: 'ease-out' }
    )
    return true
  }

  /** 元素轻轻弹一下，用于「这一下点到了」的即时确认。 */
  function pop(target, { scale = 1.12, duration = 260 } = {}) {
    const el = unwrap(target)
    if (!el || reduced() || typeof el.animate !== 'function') return false
    el.animate(
      [
        { transform: 'scale(1)' },
        { transform: `scale(${scale})` },
        { transform: 'scale(1)' }
      ],
      { duration, easing: 'cubic-bezier(.34,1.56,.64,1)' }
    )
    return true
  }

  /**
   * 一次完整反馈：音效 + 震动 + 动效，三条通道各自降级、互不牵连。
   * @returns {{sound: boolean, haptics: boolean, particles: boolean, motion: boolean}}
   */
  function fire(cue, target, options = {}) {
    const {
      sound: withSound = true,
      haptics: withHaptics = true,
      cueArg,
      ...motionOptions
    } = options
    const played = withSound ? playCue(cue, cueArg) : false
    const buzzed = withHaptics ? haptic(cue) : false

    let particles = false
    let motion = false
    if (cue === 'wrong') {
      motion = motionOptions.shake === false ? false : shake(target, motionOptions.shakeOptions)
    } else if (motionOptions.particles !== false) {
      particles = burst(target, motionOptions.particleOptions)
    }

    return { sound: played, haptics: buzzed, particles, motion, reducedMotion: reduced() }
  }

  /** 收摊：把还挂在 body 上的粒子层清干净，组件 onUnmounted 里调。 */
  function dispose() {
    for (const layer of [...layers]) dropLayer(layer)
  }

  return {
    tap: (target, options) => fire('tap', target, { particles: false, ...options }),
    correct: (target, options) => fire('correct', target, options),
    wrong: (target, options) => fire('wrong', target, options),
    star: (target, options) => fire('star', target, options),
    celebrate: (target, options) =>
      fire('celebrate', target, {
        particleOptions: { count: particleDefaults.count + 10, spread: particleDefaults.spread * 1.4 },
        ...options
      }),
    /** 自定义 cue 的通用出口，App 层用它接自己特有的反馈（如笔顺的每一笔）。 */
    cue: fire,
    burst,
    shake,
    pop,
    haptic,
    reducedMotion: reduced,
    canVibrate,
    dispose
  }
}

/** 组合式写法的别名；App 层各自包一层，把自己的音效与设置接进来。 */
export function useFeedback(adapters) {
  return createFeedback(adapters)
}

export default useFeedback
