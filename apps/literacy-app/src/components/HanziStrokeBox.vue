<script setup>
/**
 * 笔顺动画盒子。
 *
 * hanzi-writer 从 CDN 按需加载（见 utils/hanziWriter.js）。加载失败时
 * 不阻塞学习流程：退化成田字格里的静态大字 + 一句提示，其余功能照常。
 */
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { loadHanziWriter } from '@/utils/hanziWriter.js'
import { sfx } from '@/utils/sfx.js'
import { useSettingsStore } from '@/stores/settings.js'

const props = defineProps({
  char: { type: String, required: true },
  size: { type: Number, default: 260 },
  autoplay: { type: Boolean, default: true }
})

const emit = defineEmits(['quiz-complete', 'quiz-mistake'])

const settings = useSettingsStore()

const host = ref(null)
const status = ref('idle') // idle | loading | ready | failed
const mode = ref('watch') // watch | quiz
const quizResult = ref(null) // { mistakes }
const hint = ref('')

let writer = null
let disposed = false

function cssColor(name, fallback) {
  if (typeof window === 'undefined') return fallback
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

function destroyWriter() {
  if (!writer) return
  try {
    writer.cancelQuiz()
  } catch {
    /* 未处于测验状态时会抛错，忽略 */
  }
  writer = null
  if (host.value) host.value.innerHTML = ''
}

async function build() {
  destroyWriter()
  quizResult.value = null
  mode.value = 'watch'
  status.value = 'loading'
  hint.value = ''

  let HanziWriter
  try {
    HanziWriter = await loadHanziWriter()
  } catch {
    if (!disposed) status.value = 'failed'
    return
  }
  if (disposed) return

  await nextTick()
  if (!host.value) return

  try {
    writer = HanziWriter.create(host.value, props.char, {
      width: props.size,
      height: props.size,
      padding: 14,
      showOutline: true,
      showCharacter: true,
      strokeAnimationSpeed: settings.reduceMotion ? 3 : 1.1,
      delayBetweenStrokes: settings.reduceMotion ? 120 : 420,
      delayBetweenLoops: 1400,
      strokeColor: cssColor('--stroke-ink', '#3d2f1f'),
      radicalColor: cssColor('--brand-strong', '#f57c00'),
      outlineColor: cssColor('--stroke-hint', '#e6ded2'),
      drawingColor: cssColor('--accent', '#4ecdc4'),
      highlightColor: cssColor('--star', '#ffc93c'),
      drawingWidth: 26
    })
    status.value = 'ready'
    if (props.autoplay) play()
  } catch {
    status.value = 'failed'
  }
}

function play() {
  if (!writer) return
  sfx.tap()
  mode.value = 'watch'
  quizResult.value = null
  try {
    writer.cancelQuiz()
  } catch {
    /* 非测验态 */
  }
  writer.showCharacter()
  writer.animateCharacter()
}

function loop() {
  if (!writer) return
  sfx.tap()
  mode.value = 'watch'
  writer.loopCharacterAnimation()
}

function startQuiz() {
  if (!writer) return
  sfx.tap()
  mode.value = 'quiz'
  quizResult.value = null
  hint.value = '用手指或鼠标，按顺序写一写吧！'
  writer.quiz({
    showHintAfterMisses: 2,
    onCorrectStroke({ strokesRemaining }) {
      sfx.tap()
      hint.value = strokesRemaining > 0 ? `太棒了，还剩 ${strokesRemaining} 笔` : '完成啦！'
    },
    onMistake({ strokeNum }) {
      sfx.wrong()
      hint.value = `第 ${strokeNum + 1} 笔再试一次～`
      emit('quiz-mistake', strokeNum)
    },
    onComplete({ totalMistakes }) {
      sfx.correct()
      quizResult.value = { mistakes: totalMistakes }
      hint.value = totalMistakes === 0 ? '一笔不错，满分！' : `写完啦，错了 ${totalMistakes} 次，再来一遍会更好！`
      emit('quiz-complete', { mistakes: totalMistakes })
    }
  })
}

function exitQuiz() {
  if (!writer) return
  try {
    writer.cancelQuiz()
  } catch {
    /* 非测验态 */
  }
  writer.showCharacter()
  mode.value = 'watch'
  hint.value = ''
  quizResult.value = null
}

watch(() => props.char, build, { immediate: true })
watch(
  () => settings.theme,
  () => {
    if (status.value === 'ready') build()
  }
)

onBeforeUnmount(() => {
  disposed = true
  destroyWriter()
})

const boxStyle = computed(() => ({ width: `${props.size}px`, height: `${props.size}px` }))

defineExpose({ play, startQuiz })
</script>

<template>
  <div class="hz">
    <div class="hz__stage tianzige" :style="boxStyle">
      <div v-show="status === 'ready'" ref="host" class="hz__host" />

      <div v-if="status === 'loading'" class="hz__overlay">
        <span class="hz__spinner" aria-hidden="true" />
        <p class="hz__note">正在准备笔顺…</p>
      </div>

      <div v-else-if="status === 'failed'" class="hz__overlay hz__overlay--static">
        <span class="hz__fallback">{{ char }}</span>
        <p class="hz__note">笔顺动画需要联网加载，先看看字形吧</p>
      </div>
    </div>

    <p v-if="hint" class="hz__hint" :class="{ 'is-done': quizResult }">{{ hint }}</p>

    <div class="hz__actions">
      <button class="btn btn--primary" type="button" :disabled="status !== 'ready'" @click="play">
        ▶️ 看笔顺
      </button>
      <button class="btn btn--ghost" type="button" :disabled="status !== 'ready'" @click="loop">
        🔁 循环
      </button>
      <button
        v-if="mode !== 'quiz'"
        class="btn btn--accent"
        type="button"
        :disabled="status !== 'ready'"
        @click="startQuiz"
      >
        ✍️ 我来写
      </button>
      <button v-else class="btn btn--ghost" type="button" @click="exitQuiz">↩️ 退出练习</button>
      <button
        v-if="status === 'failed'"
        class="btn btn--ghost"
        type="button"
        @click="build"
      >
        🔄 重新加载
      </button>
    </div>
  </div>
</template>

<style scoped>
.hz {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--gap-md);
}

.hz__stage {
  position: relative;
  display: grid;
  place-items: center;
  max-width: 100%;
  box-shadow: var(--shadow-md);
}

.hz__host {
  position: relative;
  z-index: 1;
  touch-action: none;
}

.hz__host :deep(svg) {
  display: block;
}

.hz__overlay {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: var(--gap-md);
  text-align: center;
}

.hz__fallback {
  font-size: clamp(5rem, 26vw, 9rem);
  line-height: 1;
  font-weight: 700;
  color: var(--stroke-ink);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', serif;
}

.hz__note {
  font-size: 0.82rem;
  color: var(--text-soft);
}

.hz__spinner {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: 4px solid var(--stroke-hint);
  border-top-color: var(--brand);
  animation: hz-spin 0.9s linear infinite;
}

@keyframes hz-spin {
  to {
    transform: rotate(360deg);
  }
}

.hz__hint {
  min-height: 1.6em;
  font-weight: 700;
  color: var(--text);
  text-align: center;
}

.hz__hint.is-done {
  color: var(--success);
}

.hz__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--gap-sm);
}
</style>
