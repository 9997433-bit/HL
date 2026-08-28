<script setup>
/**
 * ROUND15_H2 · 「玩」这一步的舞台（薄壳版）。
 *
 * 洪恩每个字前面都有一个跟字义相关的小互动。这一版先把**接口和最低可玩性**
 * 立起来：从 getCharPlay(char) 拿到玩法描述，按 props.taps 摆出几个道具，
 * 全部点完就算玩过一轮，往下一步走。
 *
 * 为什么先做薄壳：CharDetailView 的五步已经改成「玩→认→练→写→说」，
 * 第一步没有舞台就是一屏空白。宁可先给一个点得动、点得完、能跳过的舞台，
 * 也不能让孩子撞上白屏。模板运行时（GSAP 时间线 / OpenMoji 素材 / 富脚本）
 * 由 play-engine 分支接管，届时替换 <template> 里的舞台实现即可，
 * 对外的 props / emits 不变。
 *
 * 两条底线跟全站一致：
 *  1. 「减少动态」开着就不建时间线，道具静止排开，照样点得完（WCAG 2.3.3）。
 *  2. 永远留一个「先不玩了」，玩不下去的孩子不会被卡在第一步（G5）。
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import gsap from 'gsap'
import { getCharPlay } from '@/data/char-play.js'
import { useSettingsStore } from '@/stores/settings.js'
import { useFeedback } from '@/composables/useFeedback.js'

const props = defineProps({
  char: { type: String, required: true }
})

const emit = defineEmits(['done', 'skip'])

const settings = useSettingsStore()
const feedback = useFeedback()

const stageRef = ref(null)
const caught = ref([])
const finished = ref(false)

const play = computed(() => getCharPlay(props.char))
const emoji = computed(() => play.value?.props?.emoji ?? '✨')
const total = computed(() => Math.max(1, Number(play.value?.props?.taps) || 3))
const targets = computed(() => Array.from({ length: total.value }, (_, i) => i))
const left = computed(() => total.value - caught.value.length)

/** 家长中心的开关和系统偏好任意一个开着就不动。 */
const reduced = computed(
  () =>
    settings.reduceMotion ||
    (typeof window !== 'undefined' &&
      !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches)
)

let tween = null

function stopFloat() {
  tween?.kill()
  tween = null
}

function startFloat() {
  stopFloat()
  if (reduced.value || !stageRef.value) return
  const nodes = stageRef.value.querySelectorAll('.playstage__target')
  if (!nodes.length) return
  tween = gsap.to(nodes, {
    y: -10,
    duration: 0.9,
    ease: 'sine.inOut',
    repeat: -1,
    yoyo: true,
    stagger: 0.18
  })
}

function reset() {
  caught.value = []
  finished.value = false
  requestAnimationFrame(startFloat)
}

watch(() => props.char, reset, { immediate: true })
onBeforeUnmount(stopFloat)

function onTap(i, event) {
  if (finished.value || caught.value.includes(i)) return
  caught.value = [...caught.value, i]
  feedback.correct(event?.currentTarget, { cueArg: caught.value.length })
  if (caught.value.length >= total.value) {
    finished.value = true
    stopFloat()
    emit('done')
  }
}

function onSkip() {
  stopFloat()
  emit('skip')
}
</script>

<template>
  <div ref="stageRef" class="playstage" :data-template="play?.template" :data-theme="play?.theme">
    <p class="playstage__narration">{{ play?.narration }}</p>

    <div class="playstage__field" :class="{ 'is-still': reduced }">
      <button
        v-for="i in targets"
        :key="i"
        class="playstage__target"
        :class="{ 'is-caught': caught.includes(i) }"
        type="button"
        :disabled="caught.includes(i)"
        :aria-label="`第 ${i + 1} 个 ${char}`"
        @click="onTap(i, $event)"
      >
        <span aria-hidden="true">{{ caught.includes(i) ? char : emoji }}</span>
      </button>
    </div>

    <p class="playstage__status" role="status" aria-live="polite">
      {{ finished ? `玩过一轮啦，「${char}」认识你了 🎉` : `还差 ${left} 个` }}
    </p>

    <button class="btn btn--ghost btn--sm playstage__skip" type="button" @click="onSkip">
      先不玩了，去认字 →
    </button>
  </div>
</template>

<style scoped>
.playstage {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
  align-self: stretch;
}

.playstage__narration {
  font-size: 1.05rem;
  font-weight: 800;
  color: var(--text-strong);
}

.playstage__field {
  display: flex;
  flex-wrap: wrap;
  gap: var(--gap-sm);
  justify-content: center;
  padding: var(--gap-md) var(--gap-sm);
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
}

.playstage__target {
  display: grid;
  place-items: center;
  width: 76px;
  height: 76px;
  border-radius: 50%;
  background: var(--surface-strong);
  border: 3px solid transparent;
  font-size: 2.1rem;
  box-shadow: var(--shadow-sm);
  transition: transform var(--dur-fast) var(--ease-pop), border-color var(--dur-fast) ease;
}

.playstage__target:active:not(:disabled) {
  transform: scale(0.92);
}

.playstage__target.is-caught {
  border-color: var(--success);
  background: color-mix(in srgb, var(--success) 18%, var(--surface-strong));
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
  opacity: 1;
}

.playstage__status {
  font-weight: 700;
  color: var(--text-soft);
}

.playstage__skip {
  align-self: flex-end;
}
</style>
