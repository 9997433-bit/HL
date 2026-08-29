<script setup>
/**
 * WpAnalysisPanel — 应用题剖析壳。
 *
 * 洪恩那类课把应用题讲成一段视频；我们做成孩子自己能点开、点到哪一步算哪一步的面板：
 *   图示理解 → 分步提示 → 变式入口
 *
 * Round 19 起加「讲解播放」（ROUND19_H4）：程序化时间轴自动按步推进，
 * 可播/可暂停/有进度，可选 TTS 读 why；不塞真实 MP4。
 * reduced-motion（系统偏好或家长关动效）下降级为手动点步，不自动播。
 *
 * 三条约束：
 *   1. 剖析是给卡住的孩子的台阶，不是所有人的必经流程——由玩法页按需挂载，
 *      面板自己只管「挂上来就是摊开的」，跳过按钮把收起的决定交回玩法页。
 *   2. 判题前最后一步的得数一律盖住。剖析不扣星，露答案就等于绕开提示的星星代价。
 *   3. 变式只换数字不换结构，看完还能顺手要一轮同类题接着练。
 *
 * 面板上的两个标记不是一回事：`data-explain` 说的是「这一道题这次讲的是手写的」，
 * 随题变；`data-explain-chain` 说的是「接进来的是哪一版讲解链」，跟着构建走。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { buildAnalysis, ROUND16_H5, ROUND17_H4, ROUND19_H4, ROUND19_H5 } from '@/utils/wpAnalysis'
import {
  buildExplainTimeline,
  progressOf,
  shownStepsForCue,
} from '@/utils/wpExplainPlayer.js'
import { reducedMotion } from '@/utils/motion.js'
import { cancelSpeech, speak } from '@/utils/speech.js'
import { sound } from '@/utils/sound'

const props = defineProps({
  question: { type: Object, required: true },
  /** 判完题才允许显示最后一步的得数。 */
  reveal: { type: Boolean, default: false },
  /** 返回同结构新实例（母题的 make()）；不给就不显示变式入口。 */
  makeVariant: { type: Function, default: null },
  /** 讲解播放时是否尝试 TTS 读 why；失败静默。 */
  tts: { type: Boolean, default: true },
})

const emit = defineEmits(['skip', 'practice'])

/** 已经摊开几步；一次只多给一步，孩子才有「自己往下想」的余地。 */
const shown = ref(1)
const variant = ref(null)

/** idle | playing | paused | ended | manual（manual = reduced-motion 手动点步） */
const playerState = ref('idle')
const cueIndex = ref(0)
const cueElapsed = ref(0)
const progressTick = ref(0)
const ttsOn = ref(props.tts)
/** reduced-motion：不自动播，只保留手动点步。 */
const manualOnly = ref(false)

let advanceTimer = null
let progressTimer = null
let mediaQuery = null

const analysis = computed(() => buildAnalysis(props.question))
const steps = computed(() => analysis.value.steps)
const timeline = computed(() => buildExplainTimeline(analysis.value))
const visibleSteps = computed(() => steps.value.slice(0, shown.value))
const restCount = computed(() => Math.max(0, steps.value.length - shown.value))
const currentCue = computed(() => timeline.value[cueIndex.value] ?? null)
const progress = computed(() => {
  // progressTick 只用来在播放中触发重算
  void progressTick.value
  return progressOf(timeline.value, cueIndex.value, cueElapsed.value)
})
const progressPct = computed(() => Math.round(progress.value * 100))
const cueLabel = computed(() => currentCue.value?.label ?? '讲解')
const motionMode = computed(() => (manualOnly.value ? 'manual' : 'auto'))

const variantAnalysis = computed(() => (variant.value ? buildAnalysis(variant.value) : null))

function resultOf(step) {
  return step.asked && !props.reveal ? step.masked : step.display
}

function clearTimers() {
  if (advanceTimer) {
    clearTimeout(advanceTimer)
    advanceTimer = null
  }
  if (progressTimer) {
    clearInterval(progressTimer)
    progressTimer = null
  }
}

function stopNarration() {
  try {
    cancelSpeech()
  } catch {
    /* 静默：个别环境 cancel 会抛 */
  }
}

function narrate(text) {
  if (!ttsOn.value || !text) return
  try {
    speak(text)
  } catch {
    /* TTS 失败静默，时间轴照走 */
  }
}

function applyCue(index) {
  const cue = timeline.value[index]
  if (!cue) return
  cueIndex.value = index
  cueElapsed.value = 0
  shown.value = shownStepsForCue(cue)
  narrate(cue.speakText)
}

function scheduleAdvance() {
  clearTimers()
  if (playerState.value !== 'playing') return
  const cue = timeline.value[cueIndex.value]
  if (!cue) {
    playerState.value = 'ended'
    return
  }
  const baseElapsed = cueElapsed.value
  const startedAt = performance.now()
  progressTimer = setInterval(() => {
    cueElapsed.value = baseElapsed + (performance.now() - startedAt)
    progressTick.value += 1
  }, 80)
  const remain = Math.max(0, cue.durationMs - baseElapsed)
  advanceTimer = setTimeout(() => {
    cueElapsed.value = cue.durationMs
    const next = cueIndex.value + 1
    if (next >= timeline.value.length) {
      clearTimers()
      playerState.value = 'ended'
      stopNarration()
      // 播完摊齐（判题前仍盖答案）
      shown.value = steps.value.length
      return
    }
    applyCue(next)
    scheduleAdvance()
  }, remain)
}

function playExplain() {
  if (manualOnly.value) return
  sound.click()
  if (playerState.value === 'paused') {
    playerState.value = 'playing'
    narrate(currentCue.value?.speakText ?? '')
    scheduleAdvance()
    return
  }
  // 从头或重播
  playerState.value = 'playing'
  applyCue(0)
  scheduleAdvance()
}

function pauseExplain() {
  if (playerState.value !== 'playing') return
  sound.click()
  playerState.value = 'paused'
  clearTimers()
  stopNarration()
}

function togglePlay() {
  if (manualOnly.value) return
  if (playerState.value === 'playing') pauseExplain()
  else playExplain()
}

function resetPlayer() {
  clearTimers()
  stopNarration()
  cueIndex.value = 0
  cueElapsed.value = 0
  progressTick.value = 0
  if (manualOnly.value) {
    playerState.value = 'manual'
    shown.value = Math.min(1, steps.value.length)
  } else {
    playerState.value = 'idle'
    shown.value = Math.min(1, steps.value.length)
  }
}

function applyMotionPreference() {
  const reduce = reducedMotion()
  manualOnly.value = reduce
  if (reduce) {
    clearTimers()
    stopNarration()
    playerState.value = 'manual'
    // 手动档：保持「先看一步」的既有体验，不自动推进
    if (shown.value < 1 && steps.value.length) shown.value = 1
  } else if (playerState.value === 'manual') {
    playerState.value = 'idle'
  }
}

function skip() {
  sound.click()
  clearTimers()
  stopNarration()
  emit('skip', props.question?.id ?? '')
}

function nextStep() {
  if (!restCount.value) return
  sound.click()
  // 手动点步时若在播，先停掉自动轴，避免和手动打架
  if (playerState.value === 'playing') pauseExplain()
  shown.value += 1
  if (manualOnly.value || playerState.value === 'manual') {
    const idx = shown.value - 1
    const cue = timeline.value.find((c) => c.stepIndex === idx)
    if (cue) {
      cueIndex.value = timeline.value.indexOf(cue)
      cueElapsed.value = 0
    }
  }
}

function showAllSteps() {
  if (!restCount.value) return
  sound.click()
  if (playerState.value === 'playing') pauseExplain()
  shown.value = steps.value.length
}

function drawVariant() {
  if (!props.makeVariant) return
  sound.click()
  variant.value = props.makeVariant() ?? null
}

function practiceSame() {
  sound.click()
  emit('practice', props.question?.skill ?? '')
}

function onMediaChange() {
  applyMotionPreference()
}

// 换题就把分步和变式收回起点：新题的第二步不该跟着上一道一起摊开
watch(
  () => props.question?.text,
  () => {
    variant.value = null
    resetPlayer()
  },
)

// 判完题再把剩下的步骤一次摊开，讲评时看到的是完整思路而不是半截
watch(
  () => props.reveal,
  (on) => {
    if (on) {
      if (playerState.value === 'playing') pauseExplain()
      shown.value = steps.value.length
    }
  },
)

watch(
  () => props.tts,
  (on) => {
    ttsOn.value = on
    if (!on) stopNarration()
  },
)

onMounted(() => {
  applyMotionPreference()
  mediaQuery = window.matchMedia?.('(prefers-reduced-motion: reduce)')
  mediaQuery?.addEventListener?.('change', onMediaChange)
})

onBeforeUnmount(() => {
  clearTimers()
  stopNarration()
  mediaQuery?.removeEventListener?.('change', onMediaChange)
})
</script>

<template>
  <section
    class="panel"
    role="region"
    aria-label="应用题剖析"
    :data-analysis="ROUND16_H5"
    :data-explain="analysis.handwritten ? ROUND17_H4 : ''"
    :data-explain-chain="ROUND19_H5"
    :data-lesson-player="ROUND19_H4"
    :data-wp-player="ROUND19_H4"
    :data-wp-player-state="playerState"
    :data-wp-player-motion="motionMode"
    :data-wp-player-progress="progressPct"
  >
    <header class="panel-head">
      <span class="chip chip-on">🔍 剖析</span>
      <!-- 手写剖析链讲的是「这道题为什么先算它」，值得让孩子知道这段是老师写的 -->
      <span v-if="analysis.handwritten" class="chip chip-hand">✍️ 老师讲法</span>
      <p class="dim">看懂「为什么这样列式」，再回去作答。</p>
      <div class="spacer" />
      <button class="btn btn--ghost btn--sm" @click="skip">跳过 ✕</button>
    </header>

    <!-- 讲解播放：程序化时间轴（图示 → 分步 why），不是真实 MP4 -->
    <section
      class="player"
      aria-label="讲解播放"
      :data-wp-player-cues="timeline.length"
    >
      <div class="player-row">
        <button
          v-if="!manualOnly"
          class="btn btn--ghost btn--sm"
          data-wp-play-toggle
          :aria-pressed="playerState === 'playing'"
          @click="togglePlay"
        >
          <template v-if="playerState === 'playing'">⏸ 暂停</template>
          <template v-else-if="playerState === 'paused'">▶ 继续</template>
          <template v-else-if="playerState === 'ended'">↻ 重播讲解</template>
          <template v-else>▶ 播放讲解</template>
        </button>
        <span v-else class="chip chip-manual" data-wp-manual>
          减弱动效 · 请手动点步
        </span>
        <label v-if="!manualOnly" class="tts-toggle">
          <input v-model="ttsOn" type="checkbox" data-wp-tts />
          朗读 why
        </label>
        <span class="player-cue dim" data-wp-cue-label>{{ cueLabel }}</span>
      </div>
      <div
        class="progress"
        role="progressbar"
        :aria-valuenow="progressPct"
        aria-valuemin="0"
        aria-valuemax="100"
        :aria-label="`讲解进度 ${progressPct}%`"
        data-wp-progress
      >
        <span class="progress-fill" :style="{ width: `${progressPct}%` }" />
      </div>
      <p class="dim caption player-hint">
        <template v-if="manualOnly">
          系统要减少动效，讲解改为手动「再看一步」，不自动播放。
        </template>
        <template v-else>
          讲解播放按图示 → 分步自动推进（约 {{ Math.round(timeline.reduce((s, c) => s + c.durationMs, 0) / 1000) }} 秒），可随时暂停。
        </template>
      </p>
    </section>

    <!-- 一 · 图示理解：先把数量画成长短，再说要求的是哪一段 -->
    <section
      class="block"
      :class="{ 'block-active': currentCue?.kind === 'diagram' && playerState === 'playing' }"
      data-wp-stage="diagram"
    >
      <h3 class="block-title">① 图示理解</h3>
      <div v-if="analysis.knowns.length" class="knowns">
        <span class="chip">已知</span>
        <span v-for="k in analysis.knowns" :key="k.label" class="chip num">{{ k.label }}</span>
      </div>
      <p v-if="analysis.ask" class="ask">❓ {{ analysis.ask }}</p>
      <div class="bars" role="img" :aria-label="`图示：${analysis.diagram.caption}`">
        <div v-for="(bar, i) in analysis.diagram.bars" :key="i" class="bar-row">
          <span class="bar-label">{{ analysis.diagram.icon || '▮' }} {{ bar.value }}</span>
          <span class="bar-track">
            <span class="bar-fill" :style="{ width: `${bar.percent}%` }">
              <span
                v-if="bar.strikePercent"
                class="bar-gone"
                :style="{ width: `${bar.strikePercent}%` }"
              />
            </span>
          </span>
        </div>
        <div class="bar-row">
          <span class="bar-label ask-label">? 要求的</span>
          <span class="bar-track"><span class="bar-fill unknown" /></span>
        </div>
      </div>
      <p class="dim caption">{{ analysis.diagram.caption }}</p>
    </section>

    <!-- 二 · 分步提示：一次只放一步，最后一步的得数判题前盖住 -->
    <section
      class="block"
      :class="{ 'block-active': currentCue?.kind === 'step' && playerState === 'playing' }"
      data-wp-stage="steps"
    >
      <h3 class="block-title">② 分步提示</h3>
      <p v-if="analysis.why" class="why">💬 {{ analysis.why }}</p>
      <ol v-if="steps.length && shown > 0" class="steps">
        <li
          v-for="(step, i) in visibleSteps"
          :key="i"
          class="step"
          :class="{ 'step-current': currentCue?.stepIndex === i && playerState === 'playing' }"
        >
          <span class="step-expr">{{ step.expr }} = {{ resultOf(step) }}</span>
          <span class="step-why">{{ step.why }}</span>
        </li>
      </ol>
      <p v-else-if="!steps.length" class="fallback">整道题的算式：{{ analysis.equation }}</p>
      <p v-else-if="playerState === 'playing' || playerState === 'paused'" class="dim caption">
        正在讲图示，下一步会摊开算式……
      </p>
      <p v-else class="dim caption">点「播放讲解」按步自动推进，或直接「再看一步」。</p>
      <div v-if="restCount" class="step-actions">
        <button class="btn btn--ghost btn--sm" data-wp-next-step @click="nextStep">
          再看一步（还剩 {{ restCount }} 步）
        </button>
        <button class="btn btn--ghost btn--sm" @click="showAllSteps">全部摊开</button>
      </div>
      <p v-else-if="steps.length && !reveal && shown > 0" class="dim caption">
        最后一步的得数先盖着 —— 算出来再回去选答案。
      </p>
    </section>

    <!-- 三 · 变式入口：同结构换数字，看完可以直接要一轮同类题 -->
    <section v-if="makeVariant" class="block">
      <h3 class="block-title">③ 变式</h3>
      <div class="variant-actions">
        <button class="btn btn--ghost btn--sm" @click="drawVariant">
          {{ variant ? '再换一道变式' : '看一道同结构的变式' }}
        </button>
        <button class="btn btn--ghost btn--sm" @click="practiceSame">换一轮同类题练</button>
      </div>
      <div v-if="variant && variantAnalysis" class="variant">
        <p class="variant-text">{{ variant.text }}</p>
        <!-- 变式是讲给卡住的孩子看的范例，所以它的每一步都摊开，不盖得数 -->
        <ol v-if="variantAnalysis.steps.length" class="steps">
          <li v-for="(step, i) in variantAnalysis.steps" :key="i" class="step">
            <span class="step-expr">{{ step.expr }} = {{ step.display }}</span>
          </li>
        </ol>
        <p class="variant-eq">
          {{ variantAnalysis.equation.replace('?', String(variant.answer)) }}
        </p>
        <p class="dim caption">结构和上面这道一模一样，只换了数字和说法。</p>
      </div>
    </section>
  </section>
</template>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px 18px;
  border-radius: var(--radius-md);
  background:
    radial-gradient(90% 120% at 100% 0%, rgba(94, 231, 255, 0.12), transparent 62%),
    rgba(6, 9, 30, 0.42);
  border: 1px solid rgba(94, 231, 255, 0.32);
}

.panel-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.spacer {
  flex: 1;
}

.player {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  background: rgba(94, 231, 255, 0.08);
  border: 1px solid rgba(94, 231, 255, 0.28);
}

.player-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.player-cue {
  margin-left: auto;
  font-size: 12px;
  font-weight: 700;
}

.tts-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  user-select: none;
}

.chip-manual {
  background: rgba(255, 206, 77, 0.14);
  border-color: rgba(255, 206, 77, 0.4);
  color: var(--star);
  font-weight: 800;
}

.progress {
  height: 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  overflow: hidden;
}

.progress-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--brand), var(--accent));
  transition: width 0.08s linear;
}

.player-hint {
  margin: 0;
}

.block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-radius: var(--radius-sm);
  transition: box-shadow 0.25s ease, background 0.25s ease;
}

.block-active {
  background: rgba(94, 231, 255, 0.06);
  box-shadow: inset 0 0 0 1px rgba(94, 231, 255, 0.35);
  padding: 8px 10px;
}

.block-title {
  font-size: 14px;
  font-weight: 900;
  letter-spacing: 0.5px;
  color: var(--brand);
}

.knowns {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}

.num {
  background: rgba(255, 206, 77, 0.16);
  border-color: rgba(255, 206, 77, 0.45);
  font-weight: 900;
}

.chip-hand {
  background: rgba(85, 230, 165, 0.14);
  border-color: rgba(85, 230, 165, 0.42);
  color: var(--success);
  font-weight: 800;
}

.ask {
  font-size: 15px;
  font-weight: 800;
  line-height: 1.7;
}

.bars {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.bar-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.bar-label {
  min-width: 76px;
  font-size: 13px;
  font-weight: 800;
}

.ask-label {
  color: var(--star);
}

.bar-track {
  flex: 1;
  height: 16px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.07);
  overflow: hidden;
}

.bar-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--brand), var(--accent));
  transition: width 0.3s ease;
}

.bar-gone {
  display: block;
  height: 100%;
  margin-left: auto;
  border-radius: 999px;
  background: repeating-linear-gradient(
    45deg,
    rgba(6, 9, 30, 0.65),
    rgba(6, 9, 30, 0.65) 5px,
    rgba(255, 255, 255, 0.12) 5px,
    rgba(255, 255, 255, 0.12) 10px
  );
}

.bar-fill.unknown {
  width: 46%;
  background: transparent;
  border: 2px dashed rgba(255, 206, 77, 0.6);
}

.caption {
  font-size: 12px;
}

.why {
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  background: rgba(255, 206, 77, 0.1);
  border: 1px solid rgba(255, 206, 77, 0.32);
  font-size: 14px;
}

.steps {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 0;
  padding-left: 20px;
}

.step {
  display: flex;
  flex-direction: column;
  gap: 2px;
  border-radius: var(--radius-sm);
  transition: background 0.2s ease;
}

.step-current {
  background: rgba(255, 206, 77, 0.1);
  padding: 4px 8px;
  margin-left: -8px;
}

.step-expr {
  font-size: 19px;
  font-weight: 900;
  color: var(--brand);
}

.step-why {
  font-size: 13px;
  color: var(--text);
}

.fallback {
  font-size: 18px;
  font-weight: 900;
  color: var(--brand);
}

.step-actions,
.variant-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.variant {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.05);
  border: 1px dashed rgba(255, 255, 255, 0.2);
}

.variant-text {
  font-size: 15px;
  line-height: 1.7;
}

.variant-eq {
  align-self: flex-start;
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  background: rgba(85, 230, 165, 0.14);
  border: 1px solid rgba(85, 230, 165, 0.42);
  font-size: 18px;
  font-weight: 900;
  color: var(--success);
}

@media (prefers-reduced-motion: reduce) {
  .progress-fill,
  .bar-fill,
  .block,
  .step {
    transition: none;
  }
}
</style>
