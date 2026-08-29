/**
 * Round 19 H3 · 玩关精美度三件套。
 *
 * CharPlayStage 的视觉升级都从这里进出，探针也认这里的可执行标记：
 *
 *   1. multiBeatTimeline   —— 入场至少三拍（氛围 → 标题 → 主体）
 *   2. propHitFeedback     —— 点中/点错道具的涟漪环 + 轻弹
 *   3. themeAtmosphere     —— 按主题色铺一层氛围光斑与主题 emoji 微粒
 *
 * reduced-motion / 家长「减少动效」时：不建 GSAP timeline，氛围层静态就位，
 * 命中只留瞬时 class，跳过按钮与通关判定一字不动。
 */

import { onBeforeUnmount, ref } from 'vue'
import gsap from 'gsap'

/** 可执行探针标记（禁止只写在注释里）。 */
export const ROUND19_H3 = 'ROUND19_H3'

/** 三类可感知升级的机读清单；check:round19 H3 会扫这些键名。 */
export const PLAY_POLISH = Object.freeze({
  probe: ROUND19_H3,
  multiBeatTimeline: true,
  propHitFeedback: true,
  themeAtmosphere: true
})

/**
 * @param {object} opts
 * @param {import('vue').Ref<boolean>|import('vue').ComputedRef<boolean>} opts.reduced
 * @param {import('vue').Ref<HTMLElement|null>} opts.stageRef
 */
export function usePlayPolish({ reduced, stageRef }) {
  /** 当前入场拍节：0 未开 / 1 氛围 / 2 标题 / 3 主体（或已跳过）。 */
  const beatIndex = ref(0)
  /** 最近一次命中反馈的时间戳，模板可拿来做瞬时高亮。 */
  const hitStamp = ref(0)
  const lastHitOk = ref(true)

  let introTl = null
  const hitTweens = []
  let hitClearTimer = 0

  function isReduced() {
    return reduced?.value === true
  }

  function killPolishMotion() {
    introTl?.kill()
    introTl = null
    for (const tw of hitTweens) tw.kill()
    hitTweens.length = 0
    if (hitClearTimer) {
      window.clearTimeout(hitClearTimer)
      hitClearTimer = 0
    }
  }

  /**
   * 多拍节入场 timeline。减少动效时直接把三拍标成完成、元素就位，不建 timeline。
   * @returns {gsap.core.Timeline|null}
   */
  function playMultiBeatTimeline() {
    killPolishMotion()
    beatIndex.value = 0
    const root = stageRef?.value
    if (!root) return null

    const atmosphere = root.querySelector('[data-polish-atmosphere]')
    const head = root.querySelector('.play__head')
    const body = root.querySelector('[data-polish-body]')

    if (isReduced()) {
      beatIndex.value = 3
      if (atmosphere) gsap.set(atmosphere, { opacity: 1, clearProps: 'transform' })
      if (head) gsap.set(head, { opacity: 1, y: 0, clearProps: 'transform' })
      if (body) gsap.set(body, { opacity: 1, scale: 1, clearProps: 'transform' })
      root.setAttribute('data-polish-beats', 'skipped')
      return null
    }

    root.setAttribute('data-polish-beats', 'running')
    introTl = gsap.timeline({
      defaults: { ease: 'power2.out', overwrite: 'auto' },
      onComplete() {
        beatIndex.value = 3
        root.setAttribute('data-polish-beats', 'done')
      }
    })

    // 拍 1：主题氛围层淡入
    introTl.call(() => {
      beatIndex.value = 1
    })
    if (atmosphere) {
      introTl.fromTo(atmosphere, { opacity: 0 }, { opacity: 1, duration: 0.34 }, 0)
    } else {
      introTl.to({}, { duration: 0.2 }, 0)
    }

    // 拍 2：标题 / 旁白就位
    introTl.call(() => {
      beatIndex.value = 2
    }, 0.28)
    if (head) {
      introTl.fromTo(
        head,
        { y: 12, opacity: 0.35 },
        { y: 0, opacity: 1, duration: 0.32 },
        0.28
      )
    }

    // 拍 3：互动主体轻弹入场
    introTl.call(() => {
      beatIndex.value = 3
    }, 0.52)
    if (body) {
      introTl.fromTo(
        body,
        { scale: 0.94, opacity: 0.45 },
        { scale: 1, opacity: 1, duration: 0.4, ease: 'back.out(1.6)' },
        0.52
      )
    }

    return introTl
  }

  /**
   * 道具命中反馈增强：在舞台坐标系里炸一圈涟漪，并给靶子一次轻弹。
   * 不改 taken / need / finish 判定，只做观感。
   * @param {Element|null|undefined} el
   * @param {{ ok?: boolean }} [opts]
   */
  function playPropHitFeedback(el, { ok = true } = {}) {
    const root = stageRef?.value
    if (!root || !el) return

    lastHitOk.value = ok
    hitStamp.value = Date.now()
    root.classList.toggle('play--hit-ok', ok)
    root.classList.toggle('play--hit-bad', !ok)
    if (hitClearTimer) window.clearTimeout(hitClearTimer)
    hitClearTimer = window.setTimeout(() => {
      root.classList.remove('play--hit-ok', 'play--hit-bad')
      hitClearTimer = 0
    }, isReduced() ? 180 : 520)

    if (isReduced()) {
      el.classList.add(ok ? 'is-hit-ok-static' : 'is-hit-bad-static')
      window.setTimeout(() => {
        el.classList.remove('is-hit-ok-static', 'is-hit-bad-static')
      }, 200)
      return
    }

    const rootRect = root.getBoundingClientRect()
    const rect = el.getBoundingClientRect()
    const burst = document.createElement('span')
    burst.className = ok ? 'play__hit-burst' : 'play__hit-burst play__hit-burst--bad'
    burst.setAttribute('aria-hidden', 'true')
    burst.style.left = `${rect.left + rect.width / 2 - rootRect.left}px`
    burst.style.top = `${rect.top + rect.height / 2 - rootRect.top}px`
    root.appendChild(burst)

    const ring = document.createElement('span')
    ring.className = 'play__hit-burst-ring'
    burst.appendChild(ring)
    for (let i = 0; i < 5; i += 1) {
      const spark = document.createElement('span')
      spark.className = 'play__hit-burst-spark'
      spark.style.setProperty('--spark-i', String(i))
      burst.appendChild(spark)
    }

    const tw = gsap.timeline({
      onComplete() {
        burst.remove()
      }
    })
    tw.fromTo(
      el,
      { scale: 1 },
      { scale: ok ? 1.14 : 0.92, duration: 0.12, yoyo: true, repeat: 1, ease: 'power2.out' },
      0
    )
    tw.fromTo(
      ring,
      { scale: 0.35, opacity: 0.95 },
      { scale: 1.85, opacity: 0, duration: 0.48, ease: 'power1.out' },
      0
    )
    tw.fromTo(
      burst.querySelectorAll('.play__hit-burst-spark'),
      { scale: 0.2, opacity: 1 },
      {
        scale: 1,
        opacity: 0,
        duration: 0.42,
        stagger: 0.03,
        ease: 'power2.out',
        x: (i) => Math.cos((i / 5) * Math.PI * 2) * 28,
        y: (i) => Math.sin((i / 5) * Math.PI * 2) * 28
      },
      0.02
    )
    hitTweens.push(tw)
  }

  onBeforeUnmount(killPolishMotion)

  return {
    ROUND19_H3,
    PLAY_POLISH,
    beatIndex,
    hitStamp,
    lastHitOk,
    playMultiBeatTimeline,
    playPropHitFeedback,
    killPolishMotion
  }
}

export default usePlayPolish
