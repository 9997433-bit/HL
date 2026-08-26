<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import gsap from 'gsap'
import { useProgressStore } from '@/stores/progress'
import { sfx } from '@/utils/sound'

const progress = useProgressStore()
const current = ref(null)
const card = ref(null)
let timer = null
let busy = false

function showNext() {
  if (busy) return
  const next = progress.takeUnlock()
  if (!next) return
  busy = true
  current.value = next
  sfx.levelUp()

  requestAnimationFrame(() => {
    const el = card.value
    if (el) {
      gsap.fromTo(
        el,
        { y: -90, opacity: 0, scale: 0.85 },
        { y: 0, opacity: 1, scale: 1, duration: 0.5, ease: 'back.out(1.8)' },
      )
    }
  })

  timer = setTimeout(dismiss, 3200)
}

function dismiss() {
  clearTimeout(timer)
  const el = card.value
  const finish = () => {
    current.value = null
    busy = false
    setTimeout(showNext, 250)
  }
  if (!el) return finish()
  gsap.to(el, { y: -80, opacity: 0, duration: 0.3, ease: 'power2.in', onComplete: finish })
}

watch(
  () => progress.pendingUnlocks.length,
  (n) => {
    if (n > 0) showNext()
  },
  { immediate: true },
)

onBeforeUnmount(() => clearTimeout(timer))
</script>

<template>
  <div class="toast-layer" aria-live="polite">
    <div v-if="current" ref="card" class="toast" role="status" @click="dismiss">
      <div class="badge">{{ current.emoji }}</div>
      <div class="text">
        <p class="kicker">🎉 解锁新成就</p>
        <p class="name">{{ current.name }}</p>
        <p class="desc">{{ current.desc }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.toast-layer {
  position: fixed;
  top: 14px;
  left: 0;
  right: 0;
  display: flex;
  justify-content: center;
  z-index: 200;
  pointer-events: none;
}

.toast {
  pointer-events: auto;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 22px 14px 14px;
  border-radius: 22px;
  background: linear-gradient(135deg, rgba(255, 206, 77, 0.96), rgba(255, 122, 198, 0.94));
  color: var(--text-invert);
  box-shadow: 0 18px 44px rgba(0, 0, 0, 0.45);
  max-width: min(92vw, 420px);
}

.badge {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 28px;
  background: rgba(255, 255, 255, 0.68);
  flex: none;
  animation: spin-pop 1.4s ease-in-out infinite;
}

@keyframes spin-pop {
  0%,
  100% {
    transform: scale(1) rotate(-6deg);
  }
  50% {
    transform: scale(1.1) rotate(8deg);
  }
}

.kicker {
  font-size: 12px;
  font-weight: 800;
  opacity: 0.75;
}

.name {
  font-size: 19px;
  font-weight: 900;
}

.desc {
  font-size: 13px;
  opacity: 0.8;
}
</style>
