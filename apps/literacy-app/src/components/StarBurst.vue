<script setup>
/** 答对 / 通关时的 GSAP 星星爆炸。挂在页面上，由父组件调用 burst()。 */
import { onBeforeUnmount, ref } from 'vue'
import gsap from 'gsap'

const props = defineProps({
  emojis: { type: Array, default: () => ['⭐', '🌟', '✨', '🎉', '🏅'] },
  count: { type: Number, default: 16 }
})

const layer = ref(null)
let ctx = null

function burst(origin) {
  const host = layer.value
  if (!host) return
  const rect = host.getBoundingClientRect()
  const cx = origin?.x ?? rect.width / 2
  const cy = origin?.y ?? rect.height / 2

  const nodes = []
  for (let i = 0; i < props.count; i++) {
    const el = document.createElement('span')
    el.className = 'sb__particle'
    el.textContent = props.emojis[i % props.emojis.length]
    el.style.left = `${cx}px`
    el.style.top = `${cy}px`
    host.appendChild(el)
    nodes.push(el)
  }

  ctx = gsap.context(() => {
    nodes.forEach((el, i) => {
      const angle = (Math.PI * 2 * i) / nodes.length + Math.random() * 0.4
      const dist = 90 + Math.random() * 130
      gsap.fromTo(
        el,
        { x: 0, y: 0, scale: 0.2, opacity: 0, rotation: 0 },
        {
          x: Math.cos(angle) * dist,
          y: Math.sin(angle) * dist - 40,
          scale: 0.8 + Math.random() * 0.8,
          opacity: 1,
          rotation: (Math.random() - 0.5) * 360,
          duration: 0.5 + Math.random() * 0.25,
          ease: 'power2.out'
        }
      )
      gsap.to(el, {
        y: `+=${140 + Math.random() * 80}`,
        opacity: 0,
        duration: 0.8,
        delay: 0.4,
        ease: 'power1.in',
        onComplete: () => el.remove()
      })
    })
  }, host)
}

onBeforeUnmount(() => {
  ctx?.revert()
})

defineExpose({ burst })
</script>

<template>
  <div ref="layer" class="sb" aria-hidden="true" />
</template>

<style>
.sb {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: visible;
  z-index: 40;
}

.sb__particle {
  position: absolute;
  font-size: 1.5rem;
  line-height: 1;
  will-change: transform, opacity;
  pointer-events: none;
}
</style>
