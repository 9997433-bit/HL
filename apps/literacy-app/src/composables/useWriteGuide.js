/**
 * 「写一写」的引导：先看老师写一遍，再自己描红。
 *
 * 写这一步原来是把田字格一扔就让孩子上手——没见过笔顺的字，孩子只能乱涂，
 * 连错三次才等来一笔示范。现在把洪恩那两拍固定下来：整字慢放一遍笔顺，
 * 播完自动接描红测验。一个挂在「写」步上的小状态机：
 *
 *   idle → demo（老师写一遍）→ trace（轮到你写）→ done（这一遍有结果了）
 *
 * 四条规矩，和 CharDetailView 那台五步状态机一脉相承：
 *  1. 示范不是必修课。「我会了，开始写」随时把示范掐掉直接进描红；
 *     孩子自己点田字格里的「我来写」也算数（`noteQuizStarted`）。
 *  2. 开了「减少动态」就没有示范这一拍：进写步直接可写。
 *  3. 笔顺数据还在路上就先等它一会儿，别对着空格子「示范」；
 *     等超时或者数据压根没来，照样放孩子进描红，不把人卡在这儿。
 *  4. 动画的完成回调不能全信（标签页转后台、数据被回收都会让它不回来），
 *     所以按笔画数估一个时长当兜底闹钟，到点自动进描红。
 */
import { computed, onBeforeUnmount, ref } from 'vue'

/** 探针锚点：写步「先示范再描红」的编排标记（check:round15 H6）。 */
export const ROUND15_H6 = 'demo-then-trace'

/**
 * 「写一写」这一步的 id。
 * 五步改名成玩·认·练·写·说之后这一步可能叫 `write`，老的 `trace` 也照旧认，
 * 免得步骤条一改名引导就跟着失灵。
 */
export const WRITE_PHASE_IDS = Object.freeze(['trace', 'write', 'writing'])

/** 这个步骤 id 是不是「写一写」。 */
export const isWritePhase = (id) => WRITE_PHASE_IDS.includes(id)

/** 拿不到笔画数时按这个笔数估示范时长。 */
const FALLBACK_STROKES = 8
/** 兜底闹钟：一笔按这么久算，加一点起手的余量，再长也不超过 MAX_DEMO_MS。 */
const MS_PER_STROKE = 1100
const DEMO_LEAD_IN = 700
const MAX_DEMO_MS = 14000
/** 等笔顺数据的上限，以及每次回头看的间隔。 */
const READY_WAIT_MS = 6000
const READY_POLL_MS = 120

/**
 * @param {object} options
 * @param {import('vue').Ref} options.box       HanziStrokeBox 的组件 ref
 * @param {() => boolean} options.reduceMotion  家长开了「减少动态」没有
 * @param {(text: string) => void} options.announce  写进播报区的一句话
 * @param {number} options.leadIn               进写步到开播示范之间的停顿
 */
export function useWriteGuide({
  box,
  reduceMotion = () => false,
  announce = () => {},
  leadIn = 0
} = {}) {
  /** idle 没在写步 | demo 老师在写 | trace 轮到孩子写 | done 这一遍写完或跳过了 */
  const stage = ref('idle')
  /** 这一趟有没有跳过示范：孩子自己按的，或者「减少动态」替他按的。 */
  const demoSkipped = ref(false)

  const demoing = computed(() => stage.value === 'demo')
  const tracing = computed(() => stage.value === 'trace')

  /** 每次进出写步都换一个号，过期的动画回调和闹钟认号作废。 */
  let run = 0
  let timer = null
  let wake = null

  function clearTimer() {
    if (timer) window.clearTimeout(timer)
    timer = null
    // 叫醒正在等的那一拍，让它自己看见号变了再退出，别把 Promise 吊在那里
    if (wake) {
      const resume = wake
      wake = null
      resume()
    }
  }

  const sleep = (ms) =>
    new Promise((resolve) => {
      clearTimer()
      wake = resolve
      timer = window.setTimeout(() => {
        timer = null
        wake = null
        resolve()
      }, ms)
    })

  /** 离开写步、换字、卸载：把引导收回 idle，别让旧回调追着新的一轮跑。 */
  function reset() {
    run += 1
    clearTimer()
    stage.value = 'idle'
    demoSkipped.value = false
  }

  /**
   * 轮到孩子写。
   * `reason === 'self'` 表示描红是孩子自己在田字格里点开的，这里就别再开一次。
   */
  function toTrace(reason) {
    clearTimer()
    if (stage.value === 'trace' || stage.value === 'done') return
    stage.value = 'trace'
    if (reason !== 'self') box.value?.startQuiz?.()
    if (reason === 'demo-end') announce('看完啦，轮到你在田字格里写一遍。')
  }

  /** 笔顺数据可能还在路上，等它一会儿再示范；等不到就返回 false。 */
  async function waitForBox(token) {
    const startedAt = Date.now()
    while (token === run) {
      const api = box.value
      if (api?.status === 'ready') return true
      if (api?.status === 'failed') return false
      if (Date.now() - startedAt >= READY_WAIT_MS) return false
      await sleep(READY_POLL_MS)
    }
    return false
  }

  /** 整字慢放一遍。返回值表示这一遍是完整播完的（被打断/超时都算没播完）。 */
  async function playDemo(token) {
    const api = box.value
    if (!api?.play) return false
    const strokes = Number(api.strokeCount) || FALLBACK_STROKES
    const budget = Math.min(MAX_DEMO_MS, DEMO_LEAD_IN + strokes * MS_PER_STROKE)
    const demo = Promise.resolve()
      .then(() => api.play({ quiet: true }))
      .catch(() => null)
    const res = await Promise.race([demo, sleep(budget).then(() => null)])
    clearTimer()
    return token === run && res?.canceled === false
  }

  /** 进「写一写」：示范一遍，播完自动接描红。 */
  async function enter({ manual = false } = {}) {
    reset()
    const token = run

    if (reduceMotion()) {
      // 减少动态下不放长动画：进来就能写，笔顺想看再自己点「看笔顺」
      demoSkipped.value = true
      announce('已按「减少动态」跳过笔顺示范，直接在田字格里写就行。')
      toTrace('reduce-motion')
      return
    }

    stage.value = 'demo'
    announce('先看老师写一遍笔顺，写完自动轮到你；等不及就点「我会了，开始写」。')

    // 自己点步骤条进来的孩子已经等过一次页面切换了，别再让他干看着
    const lead = manual ? 0 : leadIn
    if (lead > 0) {
      await sleep(lead)
      if (token !== run) return
    }

    if (!(await waitForBox(token))) {
      if (token !== run) return
      announce('笔顺动画没加载出来，先直接在田字格里写吧。')
      toTrace('no-data')
      return
    }

    const played = await playDemo(token)
    if (token !== run) return
    toTrace(played ? 'demo-end' : 'demo-cut')
  }

  /** 「我会了，开始写」：示范不看了，直接进描红。 */
  function skipDemo() {
    if (stage.value !== 'demo') return
    // 换号，还在跑的那一遍示范收尾时认不出来，就不会再抢一次描红
    run += 1
    clearTimer()
    demoSkipped.value = true
    toTrace('skip')
    announce('好，直接开始写。写不动随时点「写下一笔」。')
  }

  /**
   * 描红中途想再看一遍笔顺。
   * hanzi-writer 的 animateCharacter() 会顺手取消测验，所以看完得把描红接回来。
   */
  async function replayDemo() {
    if (stage.value === 'idle') return
    run += 1
    const token = run
    stage.value = 'demo'
    announce('再看一遍笔顺。')
    await playDemo(token)
    if (token !== run) return
    toTrace('replay')
  }

  /** 田字格里的「我来写」是孩子自己按的：引导跟着走到描红，别再插一脚。 */
  function noteQuizStarted() {
    if (stage.value !== 'demo') return
    run += 1
    clearTimer()
    demoSkipped.value = true
    stage.value = 'trace'
  }

  /** 这一遍描红有结果了（写完或跳过）：引导退场，别再自动开下一轮。 */
  function finish() {
    run += 1
    clearTimer()
    stage.value = 'done'
  }

  onBeforeUnmount(reset)

  return {
    stage,
    demoing,
    tracing,
    demoSkipped,
    enter,
    skipDemo,
    replayDemo,
    noteQuizStarted,
    finish,
    reset
  }
}
