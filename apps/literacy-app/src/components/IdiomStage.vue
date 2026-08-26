<script setup>
/**
 * 成语小剧场舞台。
 * actors 用舞台百分比坐标定位，每次换幕由 GSAP 重新入场，
 * 关闭动画时直接落位（不做补间），保证内容仍然完整可见。
 */
import { onBeforeUnmount, ref, watch } from 'vue'
import gsap from 'gsap'
import { useSettingsStore } from '@/stores/settings.js'

const props = defineProps({
  scene: { type: Object, required: true },
  palette: { type: Array, default: () => ['#ffe9c7', '#d9f0ff'] },
  sceneIndex: { type: Number, default: 0 }
})

const settings = useSettingsStore()
const stage = ref(null)
let ctx = null

function replay() {
  if (!stage.value) return
  ctx?.revert()
  const nodes = stage.value.querySelectorAll('.actor')
  if (!nodes.length) return

  if (settings.reduceMotion) {
    gsap.set(nodes, { opacity: 1, scale: 1, y: 0 })
    return
  }

  ctx = gsap.context(() => {
    const tl = gsap.timeline()
    tl.fromTo(
      nodes,
      { opacity: 0, scale: 0.4, y: 30 },
      {
        opacity: 1,
        scale: 1,
        y: 0,
        duration: 0.5,
        ease: 'back.out(1.8)',
        stagger: 0.13
      }
    )
    nodes.forEach((el, i) => {
      tl.to(
        el,
        {
          y: '-=10',
          duration: 1.1 + i * 0.12,
          repeat: -1,
          yoyo: true,
          ease: 'sine.inOut'
        },
        0.6 + i * 0.1
      )
    })
  }, stage.value)
}

watch(() => props.sceneIndex, () => requestAnimationFrame(replay), { immediate: true })

onBeforeUnmount(() => ctx?.revert())

defineExpose({ replay })
</script>

<template>
  <div
    ref="stage"
    class="stage"
    :style="{ '--c1': palette[0], '--c2': palette[1] }"
    role="img"
    :aria-label="scene.text"
  >
    <span class="stage__ground" aria-hidden="true" />
    <span
      v-for="(a, i) in scene.actors"
      :key="`${sceneIndex}-${i}-${a.emoji}`"
      class="actor"
      :style="{
        left: `${a.x}%`,
        top: `${a.y}%`,
        fontSize: `${(a.scale || 1) * 2.6}rem`
      }"
      aria-hidden="true"
    >{{ a.emoji }}</span>
  </div>
</template>

<style scoped>
.stage {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 10;
  max-height: 320px;
  border-radius: var(--radius-lg);
  background: linear-gradient(165deg, var(--c1) 0%, var(--c2) 100%);
  overflow: hidden;
  box-shadow: inset 0 -18px 30px rgba(0, 0, 0, 0.06);
}

.stage__ground {
  position: absolute;
  left: -5%;
  right: -5%;
  bottom: -14%;
  height: 40%;
  border-radius: 50% 50% 0 0;
  background: rgba(255, 255, 255, 0.35);
}

.actor {
  position: absolute;
  transform: translate(-50%, -50%);
  line-height: 1;
  filter: drop-shadow(0 6px 10px rgba(0, 0, 0, 0.14));
  will-change: transform, opacity;
}
</style>
