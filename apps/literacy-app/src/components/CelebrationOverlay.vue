<script setup>
/**
 * 可跳过的庆祝浮层。
 *
 * 设计规范 §6.2 给庆祝定了节奏：主体 ≤ 1.2s，后面的彩带尾巴随时可以被跳过，
 * 而且「跳过后状态与播完完全一致」——所以这里只有一个出口 `finish()`，
 * 自动收场和手动跳过走的是同一条路，`done` 事件保证只发一次。
 *
 * 跳过的方式给足三种：点浮层任意处、点右上角的跳过按钮、按 Esc / 回车 / 空格，
 * 键盘用户不会被一个 3 秒的彩带卡住。
 * 动效设成「减弱」时不放彩带，降级成静态卡片 + 音效（规范 §6.3）。
 */
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import gsap from 'gsap'
import { sfx } from '@/utils/audio.js'
import OpenMojiIcon from '@shared/components/OpenMojiIcon.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  emoji: { type: String, default: '🎉' },
  title: { type: String, default: '真棒！' },
  subtitle: { type: String, default: '' },
  /** 想突出的一个字/词，比如刚学会的汉字。 */
  highlight: { type: String, default: '' },
  /** 星星数量，0 表示不显示星排。 */
  stars: { type: Number, default: 0 },
  /** 尾巴自动收场的时长；主体动画固定在 1.2s 内跑完。 */
  holdMs: { type: Number, default: 2600 },
  reduceMotion: { type: Boolean, default: false },
  /** 是否自己放庆祝音效；调用方已经放过就传 false。 */
  playSound: { type: Boolean, default: true }
})

const emit = defineEmits(['done'])

const CONFETTI_COLORS = [
  'var(--seed-mango)',
  'var(--seed-coral)',
  'var(--seed-mint)',
  'var(--seed-sky)',
  'var(--seed-grape)',
  'var(--seed-leaf)'
]

/** 主体动画预算（ms）：卡片弹入 + 星星三连，合计不超过规范给的 1.2s。 */
const HERO_MS = 900
const STAR_STAGGER = 0.06

const layer = ref(null)
const cardEl = ref(null)
const skipEl = ref(null)
const pieces = ref([])
const litStars = ref(0)

/**
 * 播报文案。
 *
 * 浮层是随庆祝一起插进 DOM 的，读屏对「新插入时就带内容的 live region」
 * 不一定会念；所以这里先挂空的 live region，等浮层挂上去之后再写内容，
 * 顺手把星数和跳过方式也说清楚。
 */
const liveText = ref('')

const spoken = computed(() =>
  [
    props.title,
    props.highlight,
    props.subtitle,
    props.stars > 0 ? `获得 ${props.stars} 颗星` : '',
    '按 Esc 或回车可以跳过'
  ]
    .filter(Boolean)
    // 标题本身常带感叹号，拼接前先削掉，免得读屏念出「读完啦！，获得」
    .map((part) => part.replace(/[，。！？、]+$/, ''))
    .join('，')
)

let tail = null
let starCalls = []
let settled = true

const systemReduced = computed(
  () =>
    typeof window !== 'undefined' &&
    !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
)

const quiet = computed(() => props.reduceMotion || systemReduced.value)

function buildPieces(count) {
  return Array.from({ length: count }, (_, i) => ({
    id: `${Date.now()}-${i}`,
    color: CONFETTI_COLORS[i % CONFETTI_COLORS.length],
    left: Math.random() * 100,
    size: 8 + Math.random() * 10,
    round: Math.random() > 0.6
  }))
}

function fling() {
  const nodes = layer.value?.querySelectorAll('.cel__piece')
  if (!nodes?.length) return
  nodes.forEach((node) => {
    gsap.set(node, { y: -40, opacity: 1, rotate: Math.random() * 360 })
    gsap.to(node, {
      y: window.innerHeight + 80,
      x: (Math.random() - 0.5) * 220,
      rotate: `+=${(Math.random() - 0.5) * 900}`,
      duration: 1.6 + Math.random() * 1.2,
      delay: Math.random() * 0.4,
      ease: 'power1.in',
      opacity: 0
    })
  })
}

function popCard() {
  if (!cardEl.value) return
  gsap.fromTo(
    cardEl.value,
    { scale: 0.62, y: 24, opacity: 0 },
    { scale: 1, y: 0, opacity: 1, duration: HERO_MS / 1000, ease: 'back.out(1.8)' }
  )
}

/** 星星逐颗点亮，配升调三连音；减弱动效时一次点满。 */
function litUpStars() {
  if (!props.stars) return
  if (quiet.value) {
    litStars.value = props.stars
    return
  }
  litStars.value = 0
  starCalls = Array.from({ length: props.stars }, (_, i) =>
    gsap.delayedCall(0.18 + i * STAR_STAGGER, () => {
      litStars.value = i + 1
      sfx.star()
    })
  )
}

async function run() {
  settled = false
  litStars.value = 0
  if (props.playSound) sfx.celebrate()

  pieces.value = quiet.value ? [] : buildPieces(48)

  await nextTick()
  if (!props.open) return
  liveText.value = spoken.value
  popCard()
  litUpStars()
  if (!quiet.value) fling()
  skipEl.value?.focus?.({ preventScroll: true })

  clearTail()
  tail = window.setTimeout(finish, quiet.value ? 1200 : props.holdMs)
}

function clearTail() {
  if (tail) clearTimeout(tail)
  tail = null
  starCalls.forEach((call) => call.kill())
  starCalls = []
}

/**
 * 唯一出口：把动画收干净、把最终状态摆好，再通知外面。
 * 自动收场和跳过都走这里，所以两种路径的结果完全一样。
 */
function finish() {
  if (settled) return
  settled = true
  clearTail()
  gsap.killTweensOf(cardEl.value)
  const nodes = layer.value?.querySelectorAll('.cel__piece')
  if (nodes?.length) gsap.killTweensOf(nodes)
  pieces.value = []
  litStars.value = props.stars
  emit('done')
}

function onKeydown(e) {
  if (['Escape', 'Enter', ' ', 'Spacebar'].includes(e.key)) {
    e.preventDefault()
    finish()
  }
}

watch(
  () => props.open,
  (open) => {
    if (open) run()
    else {
      clearTail()
      settled = true
      pieces.value = []
      liveText.value = ''
    }
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  clearTail()
  gsap.killTweensOf(cardEl.value)
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="open"
      ref="layer"
      class="cel"
      role="dialog"
      aria-modal="true"
      :aria-label="title"
      tabindex="-1"
      @click="finish"
      @keydown="onKeydown"
    >
      <span
        v-for="p in pieces"
        :key="p.id"
        class="cel__piece"
        aria-hidden="true"
        :style="{
          left: `${p.left}%`,
          width: `${p.size}px`,
          height: `${p.size * (p.round ? 1 : 1.6)}px`,
          background: p.color,
          borderRadius: p.round ? '50%' : '2px'
        }"
      />

      <p class="sr-only" role="status" aria-live="polite" aria-atomic="true">{{ liveText }}</p>

      <div ref="cardEl" class="cel__card">
        <OpenMojiIcon class="cel__emoji" :emoji="emoji" :size="48" />
        <strong class="cel__title">{{ title }}</strong>
        <span v-if="highlight" class="cel__highlight">{{ highlight }}</span>
        <span v-if="subtitle" class="cel__subtitle">{{ subtitle }}</span>

        <span v-if="stars > 0" class="cel__stars" role="img" :aria-label="`获得 ${stars} 颗星`">
          <span
            v-for="n in stars"
            :key="n"
            class="cel__star"
            :class="{ 'is-lit': n <= litStars }"
            aria-hidden="true"
          >⭐</span>
        </span>

        <slot />
      </div>

      <button ref="skipEl" class="cel__skip" type="button" @click.stop="finish">
        跳过 ⏭
      </button>
    </div>
  </Teleport>
</template>

<style scoped>
.cel {
  position: fixed;
  inset: 0;
  z-index: 90;
  overflow: hidden;
  display: grid;
  place-items: center;
  padding: var(--gap-md);
  background: rgba(20, 14, 6, 0.28);
  backdrop-filter: blur(2px);
  cursor: pointer;
}

.cel__piece {
  position: absolute;
  top: 0;
  will-change: transform, opacity;
  pointer-events: none;
}

.cel__card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  max-width: min(420px, 100%);
  padding: 28px 36px;
  border-radius: var(--radius-xl);
  background: var(--surface-strong);
  box-shadow: var(--shadow-lg);
  border: 3px solid var(--brand);
  text-align: center;
}

.cel__emoji {
  font-size: 3.4rem;
  line-height: 1;
  animation: float-y 1.6s ease-in-out infinite;
}

.cel__title {
  font-size: 1.35rem;
  font-weight: 900;
  color: var(--text-strong);
}

.cel__highlight {
  font-size: 3rem;
  font-weight: 800;
  line-height: 1.1;
  color: var(--brand-strong);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', serif;
}

.cel__subtitle {
  color: var(--text);
  font-size: 0.95rem;
  line-height: 1.7;
}

.cel__stars {
  display: flex;
  gap: 4px;
  margin-top: 4px;
}

.cel__star {
  font-size: 1.5rem;
  line-height: 1;
  opacity: 0.25;
  filter: grayscale(1);
  transform: scale(0.82);
  transition: opacity var(--dur-fast) ease, transform var(--dur-fast) var(--ease-pop),
    filter var(--dur-fast) ease;
}

.cel__star.is-lit {
  opacity: 1;
  filter: none;
  transform: scale(1);
}

.cel__skip {
  position: absolute;
  top: max(16px, env(safe-area-inset-top));
  right: 16px;
  min-width: 96px;
  min-height: var(--tap-min);
  padding: 0 20px;
  border-radius: var(--radius-pill);
  background: var(--surface-strong);
  box-shadow: var(--shadow-md);
  color: var(--text-strong);
  font-size: 0.95rem;
  font-weight: 700;
  transition: transform var(--dur-fast) var(--ease-pop);
}

.cel__skip:active {
  transform: scale(0.94);
}

.cel__skip:focus-visible {
  outline: 3px solid var(--brand);
  outline-offset: 3px;
}
</style>
