<script setup>
/**
 * 底部主导航。
 *
 * 儿童端只放 5 个入口，图标大、命中区大（>= 64px），文字始终可见——
 * 这个年龄段还读不熟字，图标+文字双通道比纯图标可靠得多。
 * 家长中心不放在这里，避免孩子误入，入口在顶栏并有一道简单验证。
 */
import { useRoute } from 'vue-router'
import { sfx } from '@/utils/audio.js'

const route = useRoute()

const ITEMS = [
  { to: '/', name: 'home', icon: '🏡', label: '乐园' },
  { to: '/learn', name: 'learn', icon: '✏️', label: '学字' },
  { to: '/listen', name: 'listen', icon: '👂', label: '听音' },
  { to: '/books', name: 'books', icon: '📚', label: '绘本' },
  { to: '/idioms', name: 'idioms', icon: '🏮', label: '成语' }
]

const isActive = (item) => route.name === item.name
</script>

<template>
  <nav class="navbar" aria-label="主导航">
    <RouterLink
      v-for="item in ITEMS"
      :key="item.to"
      class="navbar__item"
      :class="{ 'is-active': isActive(item) }"
      :to="item.to"
      :aria-current="isActive(item) ? 'page' : undefined"
      @click="sfx.tap()"
    >
      <span class="navbar__icon">{{ item.icon }}</span>
      <span class="navbar__label">{{ item.label }}</span>
    </RouterLink>
  </nav>
</template>

<style scoped>
.navbar {
  position: fixed;
  left: 50%;
  bottom: max(12px, env(safe-area-inset-bottom));
  transform: translateX(-50%);
  z-index: 40;

  display: flex;
  align-items: stretch;
  gap: 2px;
  padding: 6px;
  width: min(560px, calc(100% - 24px));

  background: var(--surface);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-pill);
  box-shadow: var(--shadow-lg);
  backdrop-filter: blur(12px);
}

.navbar__item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1px;
  min-height: 58px;
  border-radius: var(--radius-pill);
  color: var(--text-soft);
  transition: background var(--dur-fast) ease, color var(--dur-fast) ease,
    transform var(--dur-fast) var(--ease-pop);
}

.navbar__item:active {
  transform: scale(0.94);
}

.navbar__item.is-active {
  background: var(--brand-soft);
  color: var(--text-strong);
}

.navbar__icon {
  font-size: 1.4rem;
  line-height: 1.1;
  transition: transform var(--dur-mid) var(--ease-pop);
}

.navbar__item.is-active .navbar__icon {
  transform: translateY(-1px) scale(1.14);
}

.navbar__label {
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.04em;
}

@media (max-width: 360px) {
  .navbar__label {
    font-size: 0.66rem;
  }
}
</style>
