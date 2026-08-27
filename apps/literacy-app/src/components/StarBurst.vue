<script setup>
/** 答对 / 通关时的原生星星爆炸。挂在页面上，由父组件调用 burst()。 */
import { onBeforeUnmount, ref } from 'vue'

const props = defineProps({
  emojis: { type: Array, default: () => ['⭐', '🌟', '✨', '🎉', '🏅'] },
  count: { type: Number, default: 16 }
})

const layer = ref(null)
const particles = new Set()

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

  nodes.forEach((el, i) => {
    particles.add(el)
    const angle = (Math.PI * 2 * i) / nodes.length + Math.random() * 0.4
    const dist = 90 + Math.random() * 130
    const x = Math.cos(angle) * dist
    const y = Math.sin(angle) * dist - 40
    const fall = 140 + Math.random() * 80
    const scale = 0.8 + Math.random() * 0.8
    const rotate = (Math.random() - 0.5) * 360
    const animation = el.animate?.(
      [
        { opacity: 0, transform: 'translate(0, 0) scale(.2) rotate(0)' },
        {
          opacity: 1,
          transform: `translate(${x}px, ${y}px) scale(${scale}) rotate(${rotate}deg)`,
          offset: 0.42
        },
        {
          opacity: 0,
          transform: `translate(${x}px, ${y + fall}px) scale(${scale}) rotate(${rotate}deg)`
        }
      ],
      { duration: 1200 + Math.random() * 250, easing: 'ease-in', fill: 'forwards' }
    )
    const remove = () => {
      particles.delete(el)
      el.remove()
    }
    if (animation) animation.finished.then(remove).catch(remove)
    else window.setTimeout(remove, 1500)
  })
}

onBeforeUnmount(() => {
  for (const particle of particles) particle.remove()
  particles.clear()
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
