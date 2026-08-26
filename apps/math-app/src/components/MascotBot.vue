<script setup>
import { computed } from 'vue'

const props = defineProps({
  mood: { type: String, default: 'idle' }, // idle | happy | sad | think | cheer
  size: { type: Number, default: 96 },
})

const bodyColor = computed(
  () =>
    ({
      idle: 'var(--brand)',
      happy: 'var(--success)',
      cheer: 'var(--star)',
      sad: 'var(--danger)',
      think: 'var(--accent)',
    })[props.mood] || 'var(--brand)',
)
</script>

<template>
  <div class="mascot" :class="`mood-${mood}`" :style="{ width: `${size}px`, height: `${size}px` }">
    <svg viewBox="0 0 120 120" :width="size" :height="size" role="img" aria-label="小机器人伙伴">
      <defs>
        <radialGradient :id="`glow-${mood}`" cx="50%" cy="40%">
          <stop offset="0%" :stop-color="bodyColor" stop-opacity="0.55" />
          <stop offset="100%" :stop-color="bodyColor" stop-opacity="0" />
        </radialGradient>
        <linearGradient :id="`body-${mood}`" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="var(--surface-strong)" />
          <stop offset="100%" :stop-color="bodyColor" />
        </linearGradient>
      </defs>

      <circle cx="60" cy="58" r="54" :fill="`url(#glow-${mood})`" />

      <!-- 天线 -->
      <line x1="60" y1="22" x2="60" y2="8" :stroke="bodyColor" stroke-width="3" stroke-linecap="round" />
      <circle class="antenna" cx="60" cy="7" r="6" :fill="bodyColor" />

      <!-- 头盔 -->
      <rect
        x="24"
        y="22"
        width="72"
        height="60"
        rx="26"
        :fill="`url(#body-${mood})`"
        stroke="rgba(10,16,48,0.35)"
        stroke-width="2"
      />
      <rect x="33" y="33" width="54" height="38" rx="18" fill="var(--cosmos-1)" />

      <!-- 眼睛 -->
      <g v-if="mood === 'happy' || mood === 'cheer'">
        <path d="M44 54 q7 -11 14 0" stroke="var(--success)" stroke-width="4" fill="none" stroke-linecap="round" />
        <path d="M64 54 q7 -11 14 0" stroke="var(--success)" stroke-width="4" fill="none" stroke-linecap="round" />
      </g>
      <g v-else-if="mood === 'sad'">
        <path d="M44 50 q7 9 14 0" stroke="var(--danger)" stroke-width="4" fill="none" stroke-linecap="round" />
        <path d="M64 50 q7 9 14 0" stroke="var(--danger)" stroke-width="4" fill="none" stroke-linecap="round" />
      </g>
      <g v-else-if="mood === 'think'">
        <circle cx="50" cy="52" r="5" fill="var(--accent)" />
        <circle cx="72" cy="50" r="5" fill="var(--accent)" />
      </g>
      <g v-else class="eyes">
        <circle cx="50" cy="52" r="6" fill="var(--brand)" />
        <circle cx="72" cy="52" r="6" fill="var(--brand)" />
        <circle cx="52" cy="50" r="2" fill="var(--surface-strong)" />
        <circle cx="74" cy="50" r="2" fill="var(--surface-strong)" />
      </g>

      <!-- 嘴 -->
      <path
        v-if="mood === 'sad'"
        d="M50 66 q10 -8 20 0"
        stroke="var(--danger)"
        stroke-width="3"
        fill="none"
        stroke-linecap="round"
      />
      <path
        v-else
        d="M50 64 q10 9 20 0"
        stroke="var(--brand)"
        stroke-width="3"
        fill="none"
        stroke-linecap="round"
      />

      <!-- 身体 -->
      <rect x="38" y="82" width="44" height="26" rx="13" :fill="bodyColor" opacity="0.9" />
      <circle cx="52" cy="95" r="3.5" fill="var(--cosmos-1)" opacity="0.55" />
      <circle cx="60" cy="95" r="3.5" fill="var(--cosmos-1)" opacity="0.55" />
      <circle cx="68" cy="95" r="3.5" fill="var(--cosmos-1)" opacity="0.55" />
    </svg>
  </div>
</template>

<style scoped>
.mascot {
  display: grid;
  place-items: center;
  animation: float 3.4s ease-in-out infinite;
}

.mood-cheer {
  animation: jump 0.7s ease-in-out infinite;
}

.mood-sad {
  animation: droop 2.4s ease-in-out infinite;
}

.antenna {
  animation: blink 1.6s ease-in-out infinite;
}

.eyes {
  animation: look 4s ease-in-out infinite;
}

@keyframes float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-8px);
  }
}

@keyframes jump {
  0%,
  100% {
    transform: translateY(0) rotate(-3deg);
  }
  50% {
    transform: translateY(-16px) rotate(4deg);
  }
}

@keyframes droop {
  0%,
  100% {
    transform: translateY(2px) rotate(-2deg);
  }
  50% {
    transform: translateY(6px) rotate(2deg);
  }
}

@keyframes blink {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.35;
  }
}

@keyframes look {
  0%,
  100% {
    transform: translateX(0);
  }
  30% {
    transform: translateX(3px);
  }
  60% {
    transform: translateX(-3px);
  }
}
</style>
