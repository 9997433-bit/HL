<script setup>
import { computed } from 'vue'
import { SHAPE_MAP } from '@/data/shapes'
import { uid } from '@/utils/random'

const props = defineProps({
  shape: { type: String, required: true },
  color: { type: String, default: '#5ee7ff' },
  size: { type: Number, default: 88 },
  rotate: { type: Number, default: 0 },
})

const def = computed(() => SHAPE_MAP[props.shape] ?? SHAPE_MAP.circle)
const gid = uid()
const lighten = computed(() => `${props.color}dd`)
</script>

<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 100 100"
    :style="{ transform: `rotate(${rotate}deg)` }"
    role="img"
    :aria-label="def.name"
  >
    <defs>
      <linearGradient :id="`g-${gid}`" x1="0" y1="0" x2="0.4" y2="1">
        <stop offset="0%" stop-color="#ffffff" stop-opacity="0.85" />
        <stop offset="45%" :stop-color="color" />
        <stop offset="100%" :stop-color="lighten" />
      </linearGradient>
      <radialGradient :id="`s-${gid}`" cx="35%" cy="30%">
        <stop offset="0%" stop-color="#ffffff" />
        <stop offset="55%" :stop-color="color" />
        <stop offset="100%" stop-color="#0d1236" stop-opacity="0.85" />
      </radialGradient>
    </defs>

    <g :fill="`url(#g-${gid})`" stroke="rgba(9,14,44,0.45)" stroke-width="2" stroke-linejoin="round">
      <circle v-if="def.kind === 'circle'" cx="50" cy="50" r="42" />
      <ellipse v-else-if="def.kind === 'ellipse'" cx="50" cy="50" rx="45" ry="30" />
      <rect v-else-if="def.kind === 'rect'" v-bind="def.attrs" />
      <polygon v-else-if="def.kind === 'polygon'" :points="def.points" />
      <path v-else-if="def.kind === 'path'" :d="def.d" />

      <!-- 立体图形 -->
      <template v-else-if="def.kind === 'cube'">
        <polygon points="22,38 50,22 78,38 50,54" :fill="color" opacity="0.95" />
        <polygon points="22,38 50,54 50,86 22,70" :fill="color" opacity="0.7" />
        <polygon points="78,38 50,54 50,86 78,70" :fill="color" opacity="0.45" />
      </template>
      <circle v-else-if="def.kind === 'sphere'" cx="50" cy="50" r="40" :fill="`url(#s-${gid})`" />
      <template v-else-if="def.kind === 'cylinder'">
        <rect x="20" y="26" width="60" height="52" :fill="color" opacity="0.75" stroke="none" />
        <ellipse cx="50" cy="78" rx="30" ry="12" :fill="color" opacity="0.55" />
        <ellipse cx="50" cy="26" rx="30" ry="12" :fill="`url(#g-${gid})`" />
        <path d="M20 26 L20 78 M80 26 L80 78" fill="none" stroke="rgba(9,14,44,0.45)" stroke-width="2" />
      </template>
      <template v-else-if="def.kind === 'cone'">
        <path d="M50 14 L80 76 L20 76 Z" :fill="`url(#g-${gid})`" />
        <ellipse cx="50" cy="76" rx="30" ry="12" :fill="color" opacity="0.6" />
      </template>
    </g>
  </svg>
</template>

<style scoped>
svg {
  display: block;
  filter: drop-shadow(0 6px 14px rgba(0, 0, 0, 0.35));
}
</style>
