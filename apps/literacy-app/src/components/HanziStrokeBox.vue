<script setup>
/**
 * 笔顺动画盒子。
 *
 * 笔顺数据优先用打包进来的离线数据，缺字才回退 CDN（见 utils/hanziData.js）。
 * 两边都拿不到时不阻塞学习流程：退化成田字格里的静态大字 + 一句提示。
 *
 * 描红本身是一个纯指针动作：要在田字格里按笔顺拖出每一笔。用键盘、开关设备
 * 或只能点大按钮的孩子做不到这件事，所以这一环节额外给了两条出口，两条都不
 * 需要拖拽（WCAG 2.1 §2.1.1 / §2.5.1）：
 *   1. 替代通道「写下一笔」——按空格 / 回车 / → 或点按钮，由程序补上当前一笔，
 *      写满全部笔画同样算完成，掌握度照常升级；
 *   2. 跳过通道「跳过描红」——按 Esc 或点按钮直接离开描红，不留下半途状态。
 * 每一步的进度都写进 hz__hint 这个 live region，读屏能听到还剩几笔。
 *
 * 同一笔连错 `demoAfterMistakes`（默认 3）次，就不再让孩子继续撞墙：
 * 自动把那一笔慢放示范一遍，再从这一笔接着写。hanzi-writer 的 animateStroke()
 * 会顺手取消当前测验，所以示范完要用 quizStartStrokeNum 从原地把测验接回来；
 * 错误总数、已辅助笔数这些账都记在组件自己手里，重启测验不会把它们清零。
 */
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { loadHanziWriter } from '@/utils/hanziWriter.js'
import { charDataLoader } from '@/utils/hanziData.js'
import { useFeedback } from '@/composables/useFeedback.js'
import { useSettingsStore } from '@/stores/settings.js'

const props = defineProps({
  char: { type: String, required: true },
  size: { type: Number, default: 260 },
  autoplay: { type: Boolean, default: true },
  /** 同一笔连错几次就自动示范这一笔；设成 0 表示不自动示范。 */
  demoAfterMistakes: { type: Number, default: 3 }
})

const emit = defineEmits(['quiz-complete', 'quiz-mistake', 'quiz-skip', 'quiz-start', 'stroke-demo'])

const settings = useSettingsStore()
/** 描红的每一笔都从这里取反馈：笔音、错笔轻晃、写完撒星星，降级规则与答题一致。 */
const feedback = useFeedback()

const host = ref(null)
const stage = ref(null)
const status = ref('idle') // idle | loading | ready | failed
const mode = ref('watch') // watch | quiz
const quizResult = ref(null) // { mistakes }
const hint = ref('')
/** 本字总笔画数，用于「还剩几笔」的播报；拿不到数据时为 0。 */
const strokeCount = ref(0)
/** 已经由键盘/按钮替程序写掉的笔数。 */
const assisted = ref(0)
/** 本轮描红的错误总数；示范后重启测验也不清零，由组件自己记账。 */
const mistakes = ref(0)
/** 本轮自动示范过几笔。 */
const demoCount = ref(0)
/** 正在示范的笔序（0 开始）；-1 表示没有在示范。 */
const demoStroke = ref(-1)

let writer = null
let disposed = false
/** 每一笔各错了几次，key 是笔序；这一笔写对之后清零。 */
let strokeMistakes = new Map()

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
  strokeCount.value = 0
  resetQuizTally()

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
      charDataLoader,
      showOutline: true,
      showCharacter: true,
      strokeAnimationSpeed: settings.reduceMotion ? 3 : 1.1,
      delayBetweenStrokes: settings.reduceMotion ? 120 : 420,
      delayBetweenLoops: 1400,
      strokeColor: cssColor('--stroke-ink', '#3d2f1f'), // token-ok: non-DOM fallback mirrors sunny token
      radicalColor: cssColor('--brand-strong', '#f57c00'), // token-ok: non-DOM fallback mirrors sunny token
      outlineColor: cssColor('--stroke-hint', '#e6ded2'), // token-ok: non-DOM fallback mirrors sunny token
      drawingColor: cssColor('--accent', '#4ecdc4'), // token-ok: non-DOM fallback mirrors sunny token
      highlightColor: cssColor('--star', '#ffc93c'), // token-ok: non-DOM fallback mirrors sunny token
      drawingWidth: 26
    })
    status.value = 'ready'
    writer
      ?.getCharacterData()
      .then((data) => {
        if (!disposed) strokeCount.value = data?.strokes?.length ?? 0
      })
      .catch(() => {
        strokeCount.value = 0
      })
    if (props.autoplay) play()
  } catch {
    status.value = 'failed'
  }
}

function play() {
  if (!writer) return
  feedback.tap()
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
  feedback.tap()
  mode.value = 'watch'
  writer.loopCharacterAnimation()
}

function resetQuizTally() {
  assisted.value = 0
  mistakes.value = 0
  demoCount.value = 0
  demoStroke.value = -1
  strokeMistakes = new Map()
}

/**
 * 真正把 hanzi-writer 的测验跑起来。
 * `from` 不是 0 时表示从示范过的那一笔接着写：前面写好的笔画照旧留在格子里。
 */
function runQuiz(from = 0) {
  if (!writer) return
  writer.quiz({
    quizStartStrokeNum: from,
    showHintAfterMisses: 2,
    onCorrectStroke({ strokeNum, strokesRemaining }) {
      feedback.stroke(strokeNum)
      strokeMistakes.delete(strokeNum)
      hint.value = strokesRemaining > 0 ? `太棒了，还剩 ${strokesRemaining} 笔` : '完成啦！'
    },
    onMistake({ strokeNum }) {
      const missed = (strokeMistakes.get(strokeNum) ?? 0) + 1
      strokeMistakes.set(strokeNum, missed)
      mistakes.value += 1
      emit('quiz-mistake', { strokeNum, mistakesOnStroke: missed, total: mistakes.value })
      if (props.demoAfterMistakes > 0 && missed >= props.demoAfterMistakes) {
        demonstrateStroke(strokeNum)
        return
      }
      // 田字格轻晃一下就够了，别把整页晃起来
      feedback.wrong(stage.value, { shakeOptions: { distance: 6, duration: 300 } })
      hint.value = `第 ${strokeNum + 1} 笔再试一次～`
    },
    onComplete() {
      const total = mistakes.value
      // 一笔不错的话音再高一档，星星也一起撒出来
      feedback.correct(stage.value, { cueArg: total === 0 ? 3 : 1 })
      quizResult.value = { mistakes: total }
      hint.value = total === 0 ? '一笔不错，满分！' : `写完啦，错了 ${total} 次，再来一遍会更好！`
      mode.value = 'watch'
      demoStroke.value = -1
      emit('quiz-complete', { mistakes: total, assisted: assisted.value, demos: demoCount.value })
    }
  })
}

function startQuiz() {
  if (!writer) return
  feedback.tap()
  mode.value = 'quiz'
  quizResult.value = null
  resetQuizTally()
  hint.value = `用手指或鼠标按顺序写一写；也可以按空格或「写下一笔」，让我帮你写。${
    strokeCount.value ? `一共 ${strokeCount.value} 笔。` : ''
  }`
  runQuiz(0)
  emit('quiz-start')
  nextTick(() => stage.value?.focus?.({ preventScroll: true }))
}

/**
 * 同一笔连错够了次数：慢放示范这一笔，再把测验接回原处。
 * 示范期间田字格不接受书写（animateStroke 已经取消了测验），
 * 所以要挡住键盘的「写下一笔」，免得孩子在示范中途把这一笔跳掉。
 */
async function demonstrateStroke(strokeNum) {
  if (!writer || demoStroke.value >= 0) return
  demoStroke.value = strokeNum
  demoCount.value += 1
  strokeMistakes.set(strokeNum, 0)
  feedback.tap()
  hint.value = `第 ${strokeNum + 1} 笔连着错了 ${props.demoAfterMistakes} 次，先看我写一遍 ✍️`
  emit('stroke-demo', { strokeNum, demos: demoCount.value })

  try {
    await writer.animateStroke(strokeNum)
  } catch {
    /* 数据被回收或组件已卸载，下面的守卫会兜住 */
  }
  if (disposed || !writer || mode.value !== 'quiz') {
    demoStroke.value = -1
    return
  }

  runQuiz(strokeNum)
  hint.value = `看清楚啦？轮到你写第 ${strokeNum + 1} 笔`
  demoStroke.value = -1
  nextTick(() => stage.value?.focus?.({ preventScroll: true }))
}

/**
 * 替代通道：把当前这一笔补上。
 * hanzi-writer 的 skipQuizStroke() 走的是和「画对了」同一条收尾路径，
 * 最后一笔补完照样触发 onComplete，所以键盘用户拿到的结果与手写完全一致。
 */
function writeNextStroke() {
  if (!writer || mode.value !== 'quiz' || demoStroke.value >= 0) return
  feedback.tap()
  assisted.value += 1
  const remaining = strokeCount.value ? Math.max(strokeCount.value - assisted.value, 0) : null
  writer.skipQuizStroke()
  if (mode.value === 'quiz') {
    hint.value =
      remaining === null
        ? `帮你写好了第 ${assisted.value} 笔`
        : remaining > 0
          ? `帮你写好了第 ${assisted.value} 笔，还剩 ${remaining} 笔`
          : '最后一笔写好了'
  }
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
  resetQuizTally()
}

/** 跳过通道：离开描红，不给掌握度记账，也不留半截笔画。 */
function skipQuiz() {
  if (mode.value !== 'quiz') return
  feedback.tap()
  exitQuiz()
  hint.value = '已经跳过描红，想练的时候再点「我来写」'
  emit('quiz-skip')
}

function onStageKeydown(event) {
  if (mode.value !== 'quiz') return
  if (['Enter', ' ', 'Spacebar', 'ArrowRight'].includes(event.key)) {
    event.preventDefault()
    writeNextStroke()
  } else if (event.key === 'Escape') {
    event.preventDefault()
    skipQuiz()
  }
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

const stageLabel = computed(() =>
  mode.value === 'quiz'
    ? `「${props.char}」描红练习区${strokeCount.value ? `，共 ${strokeCount.value} 笔` : ''}：` +
      '可以直接在格子里写；按空格、回车或方向键右键，我帮你写下一笔；按 Esc 跳过描红。' +
      `同一笔连错 ${props.demoAfterMistakes} 次，我会先示范给你看。`
    : undefined
)

defineExpose({ play, startQuiz, writeNextStroke, skipQuiz, mode, demoCount, mistakes })
</script>

<template>
  <div class="hz" :data-demos="demoCount" :data-mistakes="mistakes">
    <div
      ref="stage"
      class="hz__stage tianzige"
      :class="{ 'is-quiz': mode === 'quiz', 'is-demo': demoStroke >= 0 }"
      :style="boxStyle"
      :tabindex="mode === 'quiz' ? 0 : undefined"
      :role="mode === 'quiz' ? 'group' : undefined"
      :aria-label="stageLabel"
      @keydown="onStageKeydown"
    >
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

    <p
      class="hz__hint"
      :class="{ 'is-done': quizResult }"
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      {{ hint }}
    </p>

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
      <template v-else>
        <button
          class="btn btn--accent"
          type="button"
          :disabled="demoStroke >= 0"
          @click="writeNextStroke"
        >
          ✏️ 写下一笔
        </button>
        <button class="btn btn--ghost" type="button" @click="skipQuiz">⏭ 跳过描红</button>
      </template>
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

/* 描红时格子本身可聚焦，键盘用户要看得见焦点落在哪 */
.hz__stage.is-quiz:focus-visible {
  outline: 3px solid var(--brand);
  outline-offset: 3px;
}

/* 自动示范这一笔时给格子镶一圈高亮，说明现在是「看」而不是「写」 */
.hz__stage.is-demo {
  outline: 3px dashed var(--star);
  outline-offset: 3px;
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
