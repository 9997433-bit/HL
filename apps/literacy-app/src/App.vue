<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'
import AppHeader from '@/components/AppHeader.vue'
import BottomNav from '@/components/BottomNav.vue'
import BreakReminder from '@/components/BreakReminder.vue'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'

const route = useRoute()
const router = useRouter()
const progress = useProgressStore()
const settings = useSettingsStore()

const showBreak = ref(false)
let tickTimer = null
let lastTick = Date.now()
let breakShownForDay = null

/** 只有页面处于前台时才计时，避免把「开着标签页去吃饭」算成学习时长。 */
function tick() {
  const now = Date.now()
  const delta = (now - lastTick) / 1000
  lastTick = now
  if (document.hidden || delta > 120) return
  progress.addSeconds(delta)
  checkBreak()
}

function checkBreak() {
  const limit = settings.dailyLimitMinutes
  if (!settings.breakReminder || !limit) return
  const day = progress.todayStats.seconds / 60
  const today = progress.lastActiveDay
  if (day >= limit && breakShownForDay !== today) {
    breakShownForDay = today
    showBreak.value = true
  }
}

function onVisibility() {
  lastTick = Date.now()
}

onMounted(() => {
  tickTimer = setInterval(tick, 15000)
  document.addEventListener('visibilitychange', onVisibility)
})

onBeforeUnmount(() => {
  clearInterval(tickTimer)
  document.removeEventListener('visibilitychange', onVisibility)
})

const isHome = computed(() => route.name === 'home')

function dismissBreak(action) {
  showBreak.value = false
  if (action === 'stop') router.push('/')
}
</script>

<template>
  <div class="app-shell">
    <div class="app-bg" aria-hidden="true">
      <span class="blob blob--a" />
      <span class="blob blob--b" />
      <span class="blob blob--c" />
      <span class="app-bg__veil" />
    </div>

    <AppHeader :compact="!isHome" />

    <main class="app-main">
      <RouterView v-slot="{ Component }">
        <Transition name="fade-slide" mode="out-in">
          <component :is="Component" :key="route.fullPath" />
        </Transition>
      </RouterView>
    </main>

    <BottomNav />

    <BreakReminder v-if="showBreak" @close="dismissBreak" />
  </div>
</template>

<style scoped>
.app-shell {
  position: relative;
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  isolation: isolate;
}

.app-bg {
  position: fixed;
  inset: 0;
  z-index: -1;
  background: var(--bg-page);
  overflow: hidden;
  transition: background var(--dur-slow) ease;
}

.app-bg__veil {
  position: absolute;
  inset: 0;
  background: radial-gradient(
    120% 90% at 50% -10%,
    transparent 40%,
    color-mix(in srgb, var(--bg-page-solid) 55%, transparent) 100%
  );
}

.blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  animation: float-y 12s ease-in-out infinite;
}

.blob--a {
  width: 46vmax;
  height: 46vmax;
  top: -14vmax;
  left: -10vmax;
  background: var(--bg-blob-a);
}

.blob--b {
  width: 40vmax;
  height: 40vmax;
  bottom: -16vmax;
  right: -12vmax;
  background: var(--bg-blob-b);
  animation-delay: -4s;
  animation-duration: 15s;
}

.blob--c {
  width: 30vmax;
  height: 30vmax;
  top: 40%;
  left: 55%;
  background: var(--bg-blob-c);
  animation-delay: -8s;
  animation-duration: 18s;
}

.app-main {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
}
</style>
