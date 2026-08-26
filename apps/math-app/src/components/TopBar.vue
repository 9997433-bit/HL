<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useProgressStore } from '@/stores/progress'
import { sfx } from '@/utils/sound'

const route = useRoute()
const router = useRouter()
const progress = useProgressStore()

const isHome = computed(() => route.name === 'home')
const title = computed(() => route.meta?.title ?? '星际数学冒险')
const ringDash = computed(() => `${Math.round(progress.levelProgress * 100)}, 100`)

function goBack() {
  sfx.tap()
  router.push('/')
}
</script>

<template>
  <header class="topbar">
    <button v-if="!isHome" class="round-btn" aria-label="返回学习地图" @click="goBack">←</button>
    <div v-else class="logo" aria-hidden="true">🚀</div>

    <div class="titles">
      <h1 class="title">{{ title }}</h1>
      <p class="sub dim">{{ progress.state.pilotName }} · Lv.{{ progress.state.level }}</p>
    </div>

    <div class="spacer" />

    <div class="level-ring" :title="`等级 ${progress.state.level}`">
      <svg viewBox="0 0 36 36" width="42" height="42">
        <path
          class="ring-bg"
          d="M18 2.5a15.5 15.5 0 1 1 0 31 15.5 15.5 0 0 1 0-31"
          fill="none"
          stroke-width="3.4"
        />
        <path
          class="ring-fg"
          d="M18 2.5a15.5 15.5 0 1 1 0 31 15.5 15.5 0 0 1 0-31"
          fill="none"
          stroke-width="3.4"
          stroke-linecap="round"
          :stroke-dasharray="ringDash"
        />
      </svg>
      <span class="level-num">{{ progress.state.level }}</span>
    </div>

    <div class="stars" data-star-counter>
      <span class="star-icon">⭐</span>
      <span class="star-num">{{ progress.state.stars }}</span>
    </div>

    <RouterLink to="/achievements" class="round-btn trophy" aria-label="成就墙">🏆</RouterLink>
  </header>
</template>

<style scoped>
.topbar {
  position: sticky;
  top: 0;
  z-index: 40;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  backdrop-filter: blur(14px);
  background: linear-gradient(180deg, rgba(9, 13, 40, 0.92), rgba(9, 13, 40, 0.6));
  border-bottom: 1px solid rgba(140, 158, 255, 0.16);
}

.round-btn {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 20px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.16);
  transition: transform 0.14s ease, background 0.14s ease;
  flex: none;
}

.round-btn:hover {
  transform: translateY(-2px);
  background: rgba(255, 255, 255, 0.16);
}

.logo {
  font-size: 26px;
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  flex: none;
  animation: hover-bob 3.2s ease-in-out infinite;
}

@keyframes hover-bob {
  0%,
  100% {
    transform: translateY(0) rotate(-6deg);
  }
  50% {
    transform: translateY(-5px) rotate(4deg);
  }
}

.titles {
  min-width: 0;
}

.title {
  font-size: 19px;
  font-weight: 900;
  letter-spacing: 0.6px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sub {
  font-size: 12px;
  white-space: nowrap;
}

.level-ring {
  position: relative;
  display: grid;
  place-items: center;
  flex: none;
}

.level-ring svg {
  transform: rotate(-90deg);
}

.ring-bg {
  stroke: rgba(255, 255, 255, 0.14);
}

.ring-fg {
  stroke: url(#lvl);
  stroke: var(--cyan);
  filter: drop-shadow(0 0 5px rgba(94, 231, 255, 0.7));
  transition: stroke-dasharray 0.5s ease;
}

.level-num {
  position: absolute;
  font-size: 13px;
  font-weight: 900;
}

.stars {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: 999px;
  background: linear-gradient(135deg, rgba(255, 206, 77, 0.24), rgba(255, 159, 69, 0.18));
  border: 1px solid rgba(255, 206, 77, 0.45);
  font-weight: 900;
  flex: none;
}

.star-icon {
  font-size: 15px;
}

.star-num {
  font-size: 16px;
  min-width: 18px;
  text-align: center;
}

.trophy {
  font-size: 18px;
}

@media (max-width: 560px) {
  .topbar {
    padding: 10px 12px;
    gap: 8px;
  }

  .title {
    font-size: 16px;
  }

  .sub {
    display: none;
  }

  .level-ring {
    display: none;
  }
}
</style>
