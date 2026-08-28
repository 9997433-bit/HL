<script setup>
/**
 * 环形进度条。数值变化时由 CSS 补间 stroke-dashoffset，
 * 避免为了一个简单过渡把动画运行时放进首屏脚本。
 */
import { computed } from 'vue'

const props = defineProps({
  /** 0 ~ 1 */
  value: { type: Number, default: 0 },
  size: { type: Number, default: 72 },
  thickness: { type: Number, default: 8 },
  color: { type: String, default: 'var(--brand)' },
  trackColor: { type: String, default: 'var(--stroke-hint)' },
  /** 圆环中心显示的内容，留空则用插槽 */
  label: { type: String, default: '' },
  sublabel: { type: String, default: '' }
})

const radius = computed(() => (props.size - props.thickness) / 2)
const circumference = computed(() => 2 * Math.PI * radius.value)
const normalizedValue = computed(() => Math.min(1, Math.max(0, props.value)))
const offset = computed(() => circumference.value * (1 - normalizedValue.value))
const percent = computed(() => Math.round(normalizedValue.value * 100))
</script>

<template>
  <div class="ring" :style="{ width: `${size}px`, height: `${size}px` }">
    <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`" aria-hidden="true">
      <circle
        :cx="size / 2"
        :cy="size / 2"
        :r="radius"
        fill="none"
        :stroke="trackColor"
        :stroke-width="thickness"
      />
      <circle
        class="ring__bar"
        :cx="size / 2"
        :cy="size / 2"
        :r="radius"
        fill="none"
        :stroke="color"
        :stroke-width="thickness"
        stroke-linecap="round"
        :stroke-dasharray="circumference"
        :stroke-dashoffset="offset"
        :transform="`rotate(-90 ${size / 2} ${size / 2})`"
      />
    </svg>

    <div class="ring__center">
      <slot>
        <strong class="ring__label">{{ label || `${percent}%` }}</strong>
        <small v-if="sublabel" class="ring__sub">{{ sublabel }}</small>
      </slot>
    </div>
  </div>
</template>

<style scoped>
.ring {
  position: relative;
  display: inline-grid;
  place-items: center;
  flex: none;
}

.ring svg {
  position: absolute;
  inset: 0;
}

.ring__bar {
  transition:
    stroke var(--dur-mid) ease,
    stroke-dashoffset 0.7s var(--ease-pop);
  filter: drop-shadow(0 1px 3px rgba(0, 0, 0, 0.12));
}

.ring__center {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  line-height: 1.1;
  text-align: center;
}

.ring__label {
  font-size: 0.95rem;
  font-weight: 800;
  color: var(--text-strong);
}

.ring__sub {
  font-size: 0.65rem;
  color: var(--text-soft);
}
</style>
