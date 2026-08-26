<script setup>
/**
 * 全屏庆祝层：彩带 + 一张奖状式卡片。
 *
 * 彩带用 GSAP 直接补间绝对定位的小方块，不用 canvas——
 * 数量控制在 60 片以内，性能足够，而且能跟着主题变量换色。
 * 家长把动效设成「减弱」时只显示卡片，不放彩带。
 */
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { gsap } from 'gsap'
import { useProgressStore } from '@/stores/progress.js'
import { sfx } from '@/utils/audio.js'

const progress = useProgressStore()

const layer = ref(null)
const cardEl = ref(null)
const pieces = ref([])
const visible = ref(false)

const COLORS = [
  'var(--seed-mango)',
  'var(--seed-coral)',
  'var(--seed-mint)',
  'var(--seed-sky)',
  'var(--seed-grape)',
  'var(--seed-leaf)'
]

const event = computed(() => progress.pendingCelebration)

const reducedMotion = computed(
  () =>
    progress.state.settings.motion === 'reduced' ||
    (typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-reduced-motion: reduce)').matches)
)

let hideTimer = null

function buildPieces(count) {
  pieces.value = Array.from({ length: count }, (_, i) => ({
    id: `${Date.now()}-${i}`,
    color: COLORS[i % COLORS.length],
    left: Math.random() * 100,
    size: 8 + Math.random() * 10,
    round: Math.random() > 0.6
  }))
}

function fling() {
  if (!layer.value) return
  const nodes = layer.value.querySelectorAll('.celebrate__piece')
  nodes.forEach((node) => {
    gsap.set(node, { y: -40, opacity: 1, rotate: Math.random() * 360 })
    gsap.to(node, {
      y: window.innerHeight + 80,
      x: (Math.random() - 0.5) * 220,
      rotate: `+=${(Math.random() - 0.5) * 900}`,
      duration: 1.7 + Math.random() * 1.4,
      delay: Math.random() * 0.5,
      ease: 'power1.in',
      opacity: 0
    })
  })
}

function popCard() {
  if (!cardEl.value) return
  gsap.fromTo(
    cardEl.value,
    { scale: 0.6, y: 24, opacity: 0 },
    { scale: 1, y: 0, opacity: 1, duration: 0.6, ease: 'back.out(1.8)' }
  )
}

async function run() {
  visible.value = true
  sfx.celebrate()

  if (!reducedMotion.value) buildPieces(56)
  else pieces.value = []

  await nextTick()
  popCard()
  if (!reducedMotion.value) fling()

  if (hideTimer) clearTimeout(hideTimer)
  hideTimer = window.setTimeout(dismiss, 2800)
}

function dismiss() {
  if (hideTimer) clearTimeout(hideTimer)
  hideTimer = null
  if (!cardEl.value) {
    visible.value = false
    progress.clearCelebration()
    return
  }
  gsap.to(cardEl.value, {
    scale: 0.85,
    opacity: 0,
    duration: 0.25,
    ease: 'power2.in',
    onComplete: () => {
      visible.value = false
      pieces.value = []
      progress.clearCelebration()
    }
  })
}

watch(event, (e) => {
  if (e) run()
})

onBeforeUnmount(() => {
  if (hideTimer) clearTimeout(hideTimer)
  gsap.killTweensOf(cardEl.value)
})
</script>

<template>
  <div v-if="visible && event" ref="layer" class="celebrate" @click="dismiss">
    <div
      v-for="p in pieces"
      :key="p.id"
      class="celebrate__piece"
      :style="{
        left: `${p.left}%`,
        width: `${p.size}px`,
        height: `${p.size * (p.round ? 1 : 1.6)}px`,
        background: p.color,
        borderRadius: p.round ? '50%' : '2px'
      }"
    ></div>

    <div ref="cardEl" class="celebrate__card" role="status" aria-live="polite">
      <div class="celebrate__emoji">{{ event.emoji || '🎉' }}</div>
      <strong class="celebrate__title">{{ event.title }}</strong>
      <span v-if="event.char" class="celebrate__char">{{ event.char }}</span>
      <small class="celebrate__hint">点一下继续</small>
    </div>
  </div>
</template>

<style scoped>
.celebrate {
  position: fixed;
  inset: 0;
  z-index: 90;
  overflow: hidden;
  display: grid;
  place-items: center;
  background: rgba(20, 14, 6, 0.18);
  backdrop-filter: blur(2px);
}

.celebrate__piece {
  position: absolute;
  top: 0;
  will-change: transform, opacity;
  pointer-events: none;
}

.celebrate__card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 28px 40px;
  border-radius: var(--radius-xl);
  background: var(--surface-strong);
  box-shadow: var(--shadow-lg);
  border: 3px solid var(--brand);
  text-align: center;
}

.celebrate__emoji {
  font-size: 3.4rem;
  line-height: 1;
  animation: float-y 1.6s ease-in-out infinite;
}

.celebrate__title {
  font-size: 1.35rem;
  font-weight: 900;
  color: var(--text-strong);
}

.celebrate__char {
  font-size: 3rem;
  font-weight: 800;
  color: var(--brand-strong);
  line-height: 1.1;
}

.celebrate__hint {
  color: var(--text-soft);
  font-size: 0.8rem;
}
</style>
