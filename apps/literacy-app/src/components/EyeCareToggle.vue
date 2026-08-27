<script setup>
/**
 * 护眼 / 主题切换。
 *
 * 四档循环：明亮 → 护眼 → 夜间 → 极光。
 * 护眼档降低蓝光和对比度（纸质暖色），夜间档给睡前故事时间用。
 * 同时兼作「已连续用眼 N 分钟」的提示位——按钮上的小圆点会随时长变色。
 */
import { computed } from 'vue'
import { useProgressStore } from '@/stores/progress.js'
import { sfx } from '@/utils/audio.js'

const props = defineProps({
  /** compact 只显示图标，用于顶栏；full 显示四个并排的选项，用于家长面板。 */
  variant: { type: String, default: 'compact' }
})

const progress = useProgressStore()

const THEMES = [
  { id: 'sunny', icon: '☀️', name: '明亮', desc: '白天使用，色彩鲜明' },
  { id: 'care', icon: '🌿', name: '护眼', desc: '暖纸色，降低蓝光' },
  { id: 'night', icon: '🌙', name: '夜间', desc: '睡前故事，深色低亮' },
  { id: 'aurora', icon: '🌌', name: '极光', desc: '青紫极光，沉浸探索' }
]

const current = computed(() => THEMES.find((t) => t.id === progress.state.settings.theme) ?? THEMES[0])

/** 连续用眼时长，用来给圆点上色：<10 分钟绿，<20 分钟黄，超过则红。 */
const strainLevel = computed(() => {
  const min = progress.sessionSeconds / 60
  if (min < 10) return 'ok'
  if (min < 20) return 'warn'
  return 'high'
})

const minutes = computed(() => Math.floor(progress.sessionSeconds / 60))

function cycle() {
  sfx.tap()
  progress.cycleTheme()
}

function pick(id) {
  sfx.tap()
  progress.updateSettings({ theme: id })
}
</script>

<template>
  <button
    v-if="props.variant === 'compact'"
    class="eye-toggle"
    type="button"
    :title="`当前：${current.name}模式（已连续用眼 ${minutes} 分钟）`"
    :aria-label="`切换显示模式，当前为${current.name}模式`"
    @click="cycle"
  >
    <span class="eye-toggle__icon">{{ current.icon }}</span>
    <span class="eye-toggle__dot" :data-level="strainLevel"></span>
  </button>

  <div v-else class="theme-picker" role="radiogroup" aria-label="显示模式">
    <button
      v-for="t in THEMES"
      :key="t.id"
      class="theme-picker__item"
      type="button"
      role="radio"
      :aria-checked="progress.state.settings.theme === t.id"
      :class="{ 'is-active': progress.state.settings.theme === t.id }"
      @click="pick(t.id)"
    >
      <span class="theme-picker__icon">{{ t.icon }}</span>
      <strong>{{ t.name }}</strong>
      <small>{{ t.desc }}</small>
    </button>
  </div>
</template>

<style scoped>
.eye-toggle {
  position: relative;
  display: grid;
  place-items: center;
  width: 48px;
  height: 48px;
  border-radius: var(--radius-pill);
  background: var(--surface-strong);
  box-shadow: var(--shadow-sm);
  transition: transform var(--dur-fast) var(--ease-pop);
}

.eye-toggle:active {
  transform: scale(0.92);
}

.eye-toggle__icon {
  font-size: 1.35rem;
  line-height: 1;
}

.eye-toggle__dot {
  position: absolute;
  right: 6px;
  bottom: 6px;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  border: 2px solid var(--surface-strong);
}

.eye-toggle__dot[data-level='ok'] {
  background: var(--success);
}
.eye-toggle__dot[data-level='warn'] {
  background: var(--star);
}
.eye-toggle__dot[data-level='high'] {
  background: var(--danger);
  animation: pulse-dot 1.4s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.35);
  }
}

.theme-picker {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: var(--gap-sm);
}

.theme-picker__item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 12px 14px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  border: 2px solid transparent;
  text-align: left;
  transition: border-color var(--dur-fast) ease, transform var(--dur-fast) var(--ease-pop);
}

.theme-picker__item:active {
  transform: scale(0.98);
}

.theme-picker__item.is-active {
  border-color: var(--brand);
  background: var(--brand-soft);
}

.theme-picker__icon {
  font-size: 1.5rem;
  line-height: 1;
}

.theme-picker__item strong {
  color: var(--text-strong);
  font-size: 0.98rem;
}

.theme-picker__item small {
  color: var(--text-soft);
  font-size: 0.75rem;
  line-height: 1.35;
}
</style>
