<script setup>
/**
 * hanzi-writer 的 Vue 封装：田字格 + 笔顺动画 + 描红测验。
 *
 * 两个需要注意的地方：
 *  1. hanzi-writer 只认十六进制 / rgb() 颜色，不认 CSS 变量，
 *     所以这里要把主题变量 getComputedStyle 出来喂给它，并在换主题时重刷；
 *  2. 笔顺数据走 utils/hanziData.js 的加载器，优先用打包进来的离线数据。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import HanziWriterLib from 'hanzi-writer'
import { gsap } from 'gsap'

import { charDataLoader } from '@/utils/hanziData.js'
import { sfx } from '@/utils/audio.js'
import { useProgressStore } from '@/stores/progress.js'

const props = defineProps({
  char: { type: String, required: true },
  size: { type: Number, default: 240 },
  /** animate: 只看笔顺；quiz: 描红练习；still: 静态展示 */
  mode: { type: String, default: 'animate' },
  autoStart: { type: Boolean, default: true },
  loop: { type: Boolean, default: false },
  /** 1 为库的默认速度，孩子看得慢一点更好 */
  speed: { type: Number, default: 0.8 },
  showGrid: { type: Boolean, default: true },
  /** 描红时答错几次后高亮提示 */
  hintAfterMisses: { type: Number, default: 2 }
})

const emit = defineEmits([
  'ready',
  'stroke',
  'mistake',
  'animation-complete',
  'quiz-complete',
  'unavailable'
])

const progress = useProgressStore()

const host = ref(null)
const wrapper = ref(null)
const writer = ref(null)
const status = ref('loading') // loading | ready | unavailable
const mistakes = ref(0)
const strokesDone = ref(0)

const HEX = /^(#([0-9a-f]{3}){1,2}|rgba?\([\d.,\s]+\))$/i

/** 把 --xxx 主题变量解析成 hanzi-writer 能吃的颜色字符串。 */
function resolveColor(varName, fallback) {
  if (typeof window === 'undefined') return fallback
  const raw = getComputedStyle(document.documentElement).getPropertyValue(varName).trim()
  return HEX.test(raw) ? raw : fallback
}

function colorOptions() {
  return {
    strokeColor: resolveColor('--stroke-ink', '#3d2f1f'),
    radicalColor: resolveColor('--seed-coral', '#ff8a80'),
    outlineColor: resolveColor('--stroke-hint', '#e6ded2'),
    highlightColor: resolveColor('--seed-mango', '#ffb84d'),
    drawingColor: resolveColor('--seed-mint', '#4ecdc4')
  }
}

function destroyWriter() {
  if (!writer.value) return
  try {
    writer.value.cancelQuiz()
  } catch {
    /* 没有进行中的测验时会抛错 */
  }
  writer.value = null
  if (host.value) host.value.innerHTML = ''
}

function onQuizStroke(data) {
  strokesDone.value = data.strokeNum + 1
  sfx.stroke(data.strokeNum)
  emit('stroke', data)
}

function onQuizMistake(data) {
  mistakes.value = data.totalMistakes
  sfx.wrong()
  // 轻微抖一下，比单纯变红更直观
  if (wrapper.value) {
    gsap.fromTo(
      wrapper.value,
      { x: -6 },
      { x: 0, duration: 0.45, ease: 'elastic.out(1, 0.35)' }
    )
  }
  emit('mistake', data)
}

function onQuizComplete(summary) {
  sfx.celebrate()
  if (wrapper.value) {
    gsap.fromTo(
      wrapper.value,
      { scale: 1 },
      { scale: 1.06, duration: 0.2, yoyo: true, repeat: 1, ease: 'power2.out' }
    )
  }
  emit('quiz-complete', summary)
}

function createWriter() {
  if (!host.value || !props.char) return
  destroyWriter()
  status.value = 'loading'
  mistakes.value = 0
  strokesDone.value = 0

  const isQuiz = props.mode === 'quiz'

  const instance = HanziWriterLib.create(host.value, props.char, {
    width: props.size,
    height: props.size,
    padding: Math.round(props.size * 0.06),
    showCharacter: props.mode === 'still',
    showOutline: true,
    strokeAnimationSpeed: props.speed,
    delayBetweenStrokes: 420,
    delayBetweenLoops: 1400,
    strokeWidth: 3,
    outlineWidth: 2,
    drawingWidth: Math.max(14, Math.round(props.size * 0.075)),
    leniency: 1.25,
    showHintAfterMisses: props.hintAfterMisses,
    highlightOnComplete: true,
    acceptBackwardsStrokes: false,
    charDataLoader,
    onLoadCharDataSuccess: () => {
      status.value = 'ready'
      emit('ready')
      if (!props.autoStart) return
      if (isQuiz) startQuiz()
      else if (props.loop) instance.loopCharacterAnimation()
      else animate()
    },
    onLoadCharDataError: () => {
      status.value = 'unavailable'
      emit('unavailable', props.char)
    },
    ...colorOptions()
  })

  writer.value = instance
}

/* --------------------------------------------------------------- 对外方法 */

function animate() {
  if (!writer.value || status.value !== 'ready') return
  strokesDone.value = 0
  writer.value.animateCharacter({
    onComplete: () => emit('animation-complete')
  })
}

function loopAnimation() {
  if (!writer.value || status.value !== 'ready') return
  writer.value.loopCharacterAnimation()
}

function startQuiz() {
  if (!writer.value || status.value !== 'ready') return
  mistakes.value = 0
  strokesDone.value = 0
  writer.value.quiz({
    onCorrectStroke: onQuizStroke,
    onMistake: onQuizMistake,
    onComplete: onQuizComplete
  })
}

function cancelQuiz() {
  try {
    writer.value?.cancelQuiz()
  } catch {
    /* 无进行中测验 */
  }
}

/** 直接把当前这一笔演示出来（孩子卡住时的「教我一次」）。 */
function hintStroke() {
  if (!writer.value || status.value !== 'ready') return
  writer.value.highlightStroke(strokesDone.value)
}

function skipStroke() {
  writer.value?.skipQuizStroke()
}

function reveal() {
  writer.value?.showCharacter()
}

function hide() {
  writer.value?.hideCharacter()
}

defineExpose({
  animate,
  loopAnimation,
  startQuiz,
  cancelQuiz,
  hintStroke,
  skipStroke,
  reveal,
  hide,
  status,
  mistakes,
  strokesDone
})

/* ------------------------------------------------------------------ 生命周期 */

onMounted(() => {
  createWriter()
  if (wrapper.value) {
    gsap.from(wrapper.value, { scale: 0.85, opacity: 0, duration: 0.45, ease: 'back.out(1.6)' })
  }
})

onBeforeUnmount(() => {
  gsap.killTweensOf(wrapper.value)
  destroyWriter()
})

watch(() => [props.char, props.mode, props.size], createWriter)

// 换主题时笔画颜色要跟着换，否则夜间模式下墨色会看不见。
watch(
  () => progress.state.settings.theme,
  () => {
    const colors = colorOptions()
    for (const [name, value] of Object.entries(colors)) {
      writer.value?.updateColor(name, value, { duration: 0 })
    }
  }
)

const boxStyle = computed(() => ({ width: `${props.size}px`, height: `${props.size}px` }))
</script>

<template>
  <div class="hw">
    <div
      ref="wrapper"
      class="hw__box"
      :class="{ tianzige: showGrid }"
      :style="boxStyle"
    >
      <div ref="host" class="hw__host" :style="boxStyle"></div>

      <div v-if="status === 'loading'" class="hw__overlay">
        <span class="hw__spinner" aria-hidden="true"></span>
        <span class="sr-only">笔顺加载中</span>
      </div>

      <!-- 没有笔顺数据时至少要能看到这个字，不能是一片空白 -->
      <div v-else-if="status === 'unavailable'" class="hw__overlay hw__overlay--fallback">
        <span class="hw__plain">{{ char }}</span>
        <small class="muted">这个字暂时没有笔顺动画</small>
      </div>
    </div>

    <slot name="footer" :mistakes="mistakes" :strokes-done="strokesDone" :status="status" />
  </div>
</template>

<style scoped>
.hw {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--gap-sm);
}

.hw__box {
  position: relative;
  flex: none;
  touch-action: none; /* 描红时不要触发页面滚动 */
}

.hw__host {
  position: relative;
  z-index: 1;
}

.hw__host :deep(svg) {
  display: block;
}

.hw__overlay {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: color-mix(in srgb, var(--surface-strong) 88%, transparent);
  border-radius: inherit;
  text-align: center;
  padding: 8px;
}

.hw__overlay--fallback {
  background: transparent;
}

.hw__plain {
  font-size: 5rem;
  line-height: 1;
  font-weight: 700;
  color: var(--stroke-ink);
}

.hw__spinner {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: 4px solid var(--stroke-hint);
  border-top-color: var(--brand);
  animation: hw-spin 0.85s linear infinite;
}

@keyframes hw-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
