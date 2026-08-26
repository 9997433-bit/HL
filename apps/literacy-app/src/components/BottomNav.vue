<script setup>
import { useRoute } from 'vue-router'
import { sfx } from '@/utils/sfx.js'

const route = useRoute()

const items = [
  { to: '/', emoji: '🗺️', label: '地图', match: ['home'] },
  { to: '/learn', emoji: '🈶', label: '识字', match: ['learn', 'char'] },
  { to: '/game/listen', emoji: '🎧', label: '游戏', match: ['listen-game'] },
  { to: '/books', emoji: '📖', label: '绘本', match: ['books', 'book'] },
  { to: '/parent', emoji: '👨‍👩‍👧', label: '家长', match: ['parent'] }
]

function isActive(item) {
  return item.match.includes(route.name)
}
</script>

<template>
  <nav class="nav" aria-label="主导航">
    <RouterLink
      v-for="item in items"
      :key="item.to"
      :to="item.to"
      class="nav__item"
      :class="{ 'is-active': isActive(item) }"
      @click="sfx.tap()"
    >
      <span class="nav__emoji" aria-hidden="true">{{ item.emoji }}</span>
      <span class="nav__label">{{ item.label }}</span>
    </RouterLink>
  </nav>
</template>

<style scoped>
.nav {
  position: fixed;
  left: 50%;
  bottom: max(12px, env(safe-area-inset-bottom));
  transform: translateX(-50%);
  z-index: 30;
  display: flex;
  gap: 4px;
  padding: 7px;
  border-radius: var(--radius-pill);
  background: color-mix(in srgb, var(--surface-strong) 92%, transparent);
  border: 1px solid var(--surface-border);
  box-shadow: var(--shadow-lg);
  backdrop-filter: blur(14px);
  max-width: calc(100vw - 20px);
}

.nav__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1px;
  min-width: 62px;
  min-height: 54px;
  padding: 4px 8px;
  border-radius: var(--radius-pill);
  color: var(--text-soft);
  font-weight: 700;
  transition: background var(--dur-fast) ease, color var(--dur-fast) ease,
    transform var(--dur-fast) var(--ease-pop);
}

.nav__item:active {
  transform: scale(0.93);
}

.nav__item.is-active {
  background: linear-gradient(180deg, var(--brand) 0%, var(--brand-strong) 100%);
  color: var(--text-invert);
  box-shadow: var(--shadow-sm);
}

.nav__emoji {
  font-size: 1.35rem;
  line-height: 1.1;
}

.nav__label {
  font-size: 0.7rem;
  letter-spacing: 0.05em;
}

@media (max-width: 380px) {
  .nav__item {
    min-width: 54px;
  }
}
</style>
