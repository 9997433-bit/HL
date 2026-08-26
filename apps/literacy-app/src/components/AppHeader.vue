<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { sfx } from '@/utils/sfx.js'

defineProps({ compact: { type: Boolean, default: false } })

const route = useRoute()
const router = useRouter()
const progress = useProgressStore()
const settings = useSettingsStore()

const canGoBack = computed(() => route.name !== 'home')
const greeting = computed(() => {
  const h = new Date().getHours()
  const who = settings.childName?.trim() || '小朋友'
  if (h < 11) return `早上好，${who}！`
  if (h < 18) return `下午好，${who}！`
  return `晚上好，${who}！`
})

function goBack() {
  sfx.tap()
  if (window.history.length > 1) router.back()
  else router.push('/')
}

function toggleTheme() {
  sfx.tap()
  settings.cycleTheme()
}
</script>

<template>
  <header class="hdr" :class="{ 'hdr--compact': compact }">
    <div class="hdr__inner">
      <button v-if="canGoBack" class="hdr__back" type="button" aria-label="返回上一页" @click="goBack">
        <span aria-hidden="true">←</span>
      </button>
      <RouterLink v-else to="/" class="hdr__brand">
        <span class="hdr__logo" aria-hidden="true">🐣</span>
        <span class="hdr__brandtext">
          <strong>快乐识字</strong>
          <small v-if="!compact">{{ greeting }}</small>
        </span>
      </RouterLink>

      <h1 v-if="compact" class="hdr__title">{{ route.meta?.title || '快乐识字' }}</h1>

      <div class="hdr__right">
        <div class="hdr__stars" :title="`累计 ${progress.stars} 颗星`">
          <span aria-hidden="true">⭐</span>
          <strong>{{ progress.stars }}</strong>
        </div>
        <button
          class="hdr__icon"
          type="button"
          :aria-label="`切换主题，当前：${settings.themeMeta.name}`"
          :title="settings.themeMeta.name"
          @click="toggleTheme"
        >
          {{ settings.themeMeta.emoji }}
        </button>
      </div>
    </div>
  </header>
</template>

<style scoped>
.hdr {
  position: sticky;
  top: 0;
  z-index: 20;
  padding: 10px var(--gap-md);
  background: color-mix(in srgb, var(--bg-page-solid) 78%, transparent);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid color-mix(in srgb, var(--surface-border) 60%, transparent);
}

.hdr__inner {
  width: min(1080px, 100%);
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
}

.hdr__brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 48px;
}

.hdr__logo {
  font-size: 2rem;
  line-height: 1;
  animation: wiggle 3.4s ease-in-out infinite;
}

.hdr__brandtext {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.hdr__brandtext strong {
  font-size: 1.15rem;
  color: var(--text-strong);
  letter-spacing: 0.04em;
}

.hdr__brandtext small {
  font-size: 0.78rem;
  color: var(--text-soft);
}

.hdr__back {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border-radius: 50%;
  font-size: 1.4rem;
  font-weight: 800;
  color: var(--text-strong);
  background: var(--surface-strong);
  box-shadow: var(--shadow-sm);
  transition: transform var(--dur-fast) var(--ease-pop);
}

.hdr__back:active {
  transform: scale(0.92);
}

.hdr__title {
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--text-strong);
  margin-left: 2px;
}

.hdr__right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

.hdr__stars {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 7px 14px;
  border-radius: var(--radius-pill);
  background: var(--brand-soft);
  color: var(--text-strong);
  font-weight: 800;
  font-size: 0.95rem;
  box-shadow: var(--shadow-sm);
}

.hdr__icon {
  display: grid;
  place-items: center;
  width: 46px;
  height: 46px;
  border-radius: 50%;
  font-size: 1.3rem;
  background: var(--surface-strong);
  box-shadow: var(--shadow-sm);
  transition: transform var(--dur-fast) var(--ease-pop);
}

.hdr__icon:active {
  transform: scale(0.9) rotate(-12deg);
}

@media (max-width: 420px) {
  .hdr__title {
    font-size: 1rem;
  }
  .hdr__stars {
    padding: 6px 10px;
  }
}
</style>
