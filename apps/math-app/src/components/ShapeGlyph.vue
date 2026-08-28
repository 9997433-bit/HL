<script setup>
import { computed } from 'vue'

const props = defineProps({
  shape: { type: String, required: true },
  size: { type: Number, default: 100 },
  color: { type: String, default: 'var(--brand)' },
  spin: { type: Number, default: 0 }, // 额外旋转角度，用于「旋转规律」类题目
  outline: { type: Boolean, default: false },
  label: { type: String, default: '' },
})

/** 圆 / 椭圆用两段圆弧拼成，保证所有图形都能统一用 <path> 按顺序绘制。 */
const ellipsePath = (cx, cy, rx, ry) =>
  `M${cx - rx} ${cy}a${rx} ${ry} 0 1 0 ${rx * 2} 0a${rx} ${ry} 0 1 0 ${-rx * 2} 0Z`

function regularPath(n, r = 40, cx = 50, cy = 52, startDeg = -90) {
  const pts = Array.from({ length: n }, (_, i) => {
    const a = ((startDeg + (360 * i) / n) * Math.PI) / 180
    return `${(cx + r * Math.cos(a)).toFixed(2)} ${(cy + r * Math.sin(a)).toFixed(2)}`
  })
  return `M${pts.join('L')}Z`
}

function starPath(spikes = 5, outer = 44, inner = 18, cx = 50, cy = 52) {
  const pts = []
  for (let i = 0; i < spikes * 2; i++) {
    const r = i % 2 === 0 ? outer : inner
    const a = ((-90 + (360 * i) / (spikes * 2)) * Math.PI) / 180
    pts.push(`${(cx + r * Math.cos(a)).toFixed(2)} ${(cy + r * Math.sin(a)).toFixed(2)}`)
  }
  return `M${pts.join('L')}Z`
}

/** 每个图形返回一组按绘制顺序排列的 path。tone: main / light / dark / line */
const GEOMETRY = {
  circle: () => [{ d: ellipsePath(50, 52, 40, 40), tone: 'main' }],
  oval: () => [{ d: ellipsePath(50, 52, 44, 29), tone: 'main' }],
  semicircle: () => [{ d: 'M8 66A42 42 0 0 1 92 66Z', tone: 'main' }],
  sector: () => [{ d: 'M50 52L92 52A42 42 0 0 1 21.4 82.7Z', tone: 'main' }],
  triangle: () => [{ d: regularPath(3, 44), tone: 'main' }],
  rightTriangle: () => [{ d: 'M16 86H86V22Z', tone: 'main' }],
  square: () => [{ d: 'M16 18H84V86H16Z', tone: 'main' }],
  rectangle: () => [{ d: 'M8 26H92V78H8Z', tone: 'main' }],
  rhombus: () => [{ d: 'M50 10L88 52L50 94L12 52Z', tone: 'main' }],
  trapezoid: () => [{ d: 'M26 24H74L92 82H8Z', tone: 'main' }],
  parallelogram: () => [{ d: 'M30 24H94L70 82H6Z', tone: 'main' }],
  pentagon: () => [{ d: regularPath(5, 44), tone: 'main' }],
  hexagon: () => [{ d: regularPath(6, 44), tone: 'main' }],
  octagon: () => [{ d: regularPath(8, 44, 50, 52, -67.5), tone: 'main' }],
  star: () => [{ d: starPath(), tone: 'main' }],

  cube: () => [
    { d: 'M22 40H70V88H22Z', tone: 'main' },
    { d: 'M22 40L44 18H92L70 40Z', tone: 'light' },
    { d: 'M70 40L92 18V66L70 88Z', tone: 'dark' },
  ],
  cuboid: () => [
    { d: 'M10 46H68V84H10Z', tone: 'main' },
    { d: 'M10 46L30 26H88L68 46Z', tone: 'light' },
    { d: 'M68 46L88 26V64L68 84Z', tone: 'dark' },
  ],
  sphere: () => [
    { d: ellipsePath(50, 52, 40, 40), tone: 'main' },
    { d: 'M10 52a40 15 0 1 0 80 0a40 15 0 1 0 -80 0', tone: 'line' },
    { d: ellipsePath(37, 38, 11, 8), tone: 'light' },
  ],
  cylinder: () => [
    { d: 'M18 32L18 72A32 12 0 0 0 82 72L82 32Z', tone: 'main' },
    { d: ellipsePath(50, 32, 32, 12), tone: 'light' },
  ],
  cone: () => [
    { d: 'M50 12L84 76A34 12 0 0 1 16 76Z', tone: 'main' },
    { d: 'M16 76a34 12 0 0 0 68 0a34 12 0 0 0 -68 0', tone: 'light' },
  ],
  pyramid: () => [
    { d: 'M50 12L14 74L50 92Z', tone: 'main' },
    { d: 'M50 12L50 92L86 74Z', tone: 'dark' },
  ],
}

const uid = `sg-${Math.random().toString(36).slice(2, 9)}`

const parts = computed(() => (GEOMETRY[props.shape] ?? GEOMETRY.circle)())
</script>

<template>
  <svg
    class="glyph"
    :width="size"
    :height="size"
    viewBox="0 0 100 104"
    role="img"
    :aria-label="label || shape"
    :style="{ transform: spin ? `rotate(${spin}deg)` : undefined, '--c': color }"
  >
    <defs>
      <linearGradient :id="`${uid}-main`" x1="0" y1="0" x2="0.4" y2="1">
        <stop offset="0%" :stop-color="color" stop-opacity="0.95" />
        <stop offset="100%" :stop-color="color" stop-opacity="0.55" />
      </linearGradient>
    </defs>

    <path
      v-for="(p, i) in parts"
      :key="i"
      :d="p.d"
      :fill="
        outline
          ? 'none'
          : p.tone === 'light'
            ? color
            : p.tone === 'dark'
              ? 'rgba(6,10,34,0.45)'
              : p.tone === 'line'
                ? 'none'
                : `url(#${uid}-main)`
      "
      :fill-opacity="p.tone === 'light' ? 0.85 : 1"
      :stroke="p.tone === 'line' ? 'rgba(255,255,255,0.45)' : 'rgba(255,255,255,0.55)'"
      :stroke-width="p.tone === 'line' ? 1.4 : 2.4"
      stroke-linejoin="round"
    />
  </svg>
</template>

<style scoped>
.glyph {
  display: block;
  filter: drop-shadow(0 6px 14px rgba(0, 0, 0, 0.35));
  transition: transform 0.3s ease;
}
</style>
