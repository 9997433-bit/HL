<script setup>
/**
 * 绘本页插图舞台（ROUND11_H4）。
 *
 * 一页一个大 emoji 只能说「这页跟鸟有关」，说不出「小鸟在雨里找不到家」。
 * 这里按 books.js 的场景 DSL 把一页摆成几件东西：各有位置、大小和一点轻微的动。
 *
 * 两件事是硬要求：
 *  1. 没写 scene 的页原样退回单 emoji——一百多本扩充绘本不必一次性全改；
 *  2. 「减少动态」或系统 prefers-reduced-motion 开着时一动不动，
 *     场景只负责好看，讲故事的仍然是正文和朗读高亮（规范 §3.4）。
 *
 * 画面靠 y 排前后：y 越大越靠近读者，所以按 y 排序渲染，后画的自然压在前面。
 */
import { computed } from 'vue'
import { SCENE_BACKDROPS } from '@/data/books.js'

const props = defineProps({
  /** 场景元素数组；空的话退回单 emoji。 */
  scene: { type: Array, default: () => [] },
  /** 背景预设 id。 */
  bg: { type: String, default: '' },
  /** 读屏念的一句话。 */
  alt: { type: String, default: '' },
  /** 绘本的两色渐变，没指定背景预设时用它。 */
  palette: { type: Array, default: () => [] },
  /** 兜底插图。 */
  emoji: { type: String, default: '' },
  /** 家长中心的「减少动态」。系统偏好由 CSS 媒体查询兜住。 */
  reduced: { type: Boolean, default: false }
})

/** 元素之间错开入场，一件件落进画面，比整幅一起闪出来温和。 */
const STAGGER_MS = 90

const items = computed(() =>
  props.scene
    .map((item, index) => ({
      key: `${index}-${item.e}`,
      e: item.e,
      x: item.x,
      y: item.y,
      s: item.s ?? 1,
      m: item.m ?? 'still',
      delay: index * STAGGER_MS
    }))
    .sort((a, b) => a.y - b.y)
)

const backdrop = computed(() => {
  const preset = SCENE_BACKDROPS.get(props.bg)
  if (preset) return preset
  const [from, to] = props.palette
  return [from ?? 'var(--surface-sunken)', to ?? 'var(--surface-strong)']
})
</script>

<template>
  <div
    class="scene"
    :class="{ 'is-still': reduced }"
    :data-scene="items.length ? 'dsl' : 'emoji'"
    :data-scene-items="items.length"
    :data-scene-bg="bg || 'palette'"
    :style="{ '--c1': backdrop[0], '--c2': backdrop[1] }"
    :role="items.length && alt ? 'img' : undefined"
    :aria-label="items.length && alt ? alt : undefined"
    :aria-hidden="items.length && alt ? undefined : 'true'"
  >
    <span
      v-for="item in items"
      :key="item.key"
      class="scene__slot"
      :style="{ left: `${item.x}%`, top: `${item.y}%` }"
      aria-hidden="true"
    >
      <span
        class="scene__item"
        :class="`scene__item--${item.m}`"
        :style="{ '--s': item.s, '--d': `${item.delay}ms` }"
      >{{ item.e }}</span>
    </span>
    <span v-if="!items.length" class="scene__solo" aria-hidden="true">{{ emoji }}</span>
  </div>
</template>

<style scoped>
.scene {
  position: relative;
  display: grid;
  place-items: center;
  min-height: 210px;
  overflow: hidden;
  background: linear-gradient(170deg, var(--c1) 0%, var(--c2) 100%);
}

/* 地面：一道柔和的横带，让底下那排东西看着是站着，不是飘着。 */
.scene[data-scene='dsl']::after {
  content: '';
  position: absolute;
  inset: auto -10% -14% -10%;
  height: 46%;
  border-radius: 50% 50% 0 0;
  background: rgba(255, 255, 255, 0.32);
  pointer-events: none;
}

.scene__slot {
  position: absolute;
  transform: translate(-50%, -50%);
  line-height: 1;
}

.scene__item {
  display: inline-block;
  font-size: calc(clamp(2rem, 9vw, 3.1rem) * var(--s, 1));
  line-height: 1;
  filter: drop-shadow(0 6px 10px rgba(0, 0, 0, 0.14));
  animation: scene-in 420ms var(--ease-pop) both var(--d, 0ms);
}

.scene__item--float {
  animation:
    scene-in 420ms var(--ease-pop) both var(--d, 0ms),
    scene-float 4.2s ease-in-out infinite calc(var(--d, 0ms) + 420ms);
}

.scene__item--sway {
  animation:
    scene-in 420ms var(--ease-pop) both var(--d, 0ms),
    scene-sway 5s ease-in-out infinite calc(var(--d, 0ms) + 420ms);
}

.scene__item--drift {
  animation:
    scene-in 420ms var(--ease-pop) both var(--d, 0ms),
    scene-drift 9s ease-in-out infinite calc(var(--d, 0ms) + 420ms);
}

.scene__solo {
  font-size: clamp(4.5rem, 22vw, 7rem);
  line-height: 1;
  animation: float-y 4s ease-in-out infinite;
  filter: drop-shadow(0 8px 14px rgba(0, 0, 0, 0.12));
}

@keyframes scene-in {
  from {
    opacity: 0;
    transform: scale(0.7);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes scene-float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-9px);
  }
}

@keyframes scene-sway {
  0%,
  100% {
    transform: rotate(-4deg);
  }
  50% {
    transform: rotate(4deg);
  }
}

@keyframes scene-drift {
  0%,
  100% {
    transform: translateX(-8px);
  }
  50% {
    transform: translateX(8px);
  }
}

/* 减少动态：入场和浮动一起停，画面照样是完整的多元素场景。 */
.scene.is-still .scene__item,
.scene.is-still .scene__solo {
  animation: none;
}

@media (prefers-reduced-motion: reduce) {
  .scene__item,
  .scene__solo {
    animation: none;
  }
}
</style>
