<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

const STARTUP_DELAY_MS = 3_000
const canvas = ref(null)
let raf = 0
let startupTimer = 0
let idleCallback = 0
let stars = []
let shooting = []
let ctx = null
let w = 0
let h = 0
let dpr = 1
let lastShootAt = 0
let paused = false
let started = false

function resize() {
  const el = canvas.value
  if (!el) return
  dpr = Math.min(window.devicePixelRatio || 1, 2)
  w = window.innerWidth
  h = window.innerHeight
  el.width = Math.floor(w * dpr)
  el.height = Math.floor(h * dpr)
  el.style.width = `${w}px`
  el.style.height = `${h}px`
  ctx = el.getContext('2d')
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  seed()
}

function seed() {
  const density = Math.round((w * h) / 9000)
  const count = Math.max(70, Math.min(240, density))
  const palette = ['#ffffff', '#cfe4ff', '#ffe9b0', '#b9d4ff', '#ffd7f2'] // token-ok: Canvas fillStyle cannot resolve CSS custom-property strings.
  stars = Array.from({ length: count }, () => ({
    x: Math.random() * w,
    y: Math.random() * h,
    r: Math.random() * 1.5 + 0.3,
    a: Math.random() * 0.6 + 0.25,
    tw: Math.random() * 0.02 + 0.004,
    dir: Math.random() > 0.5 ? 1 : -1,
    vy: Math.random() * 0.05 + 0.008,
    color: palette[Math.floor(Math.random() * palette.length)],
  }))
}

function spawnShootingStar() {
  const startX = Math.random() * w * 0.8
  shooting.push({
    x: startX,
    y: -20,
    vx: 2.6 + Math.random() * 2.2,
    vy: 1.8 + Math.random() * 1.4,
    life: 1,
  })
}

function draw(ts) {
  raf = requestAnimationFrame(draw)
  if (!ctx || paused) return

  ctx.clearRect(0, 0, w, h)

  for (const s of stars) {
    s.a += s.tw * s.dir
    if (s.a > 0.92) s.dir = -1
    if (s.a < 0.16) s.dir = 1
    s.y += s.vy
    if (s.y > h + 2) s.y = -2

    ctx.globalAlpha = s.a
    ctx.fillStyle = s.color
    ctx.beginPath()
    ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2)
    ctx.fill()

    if (s.r > 1.15) {
      ctx.globalAlpha = s.a * 0.35
      ctx.beginPath()
      ctx.arc(s.x, s.y, s.r * 3.2, 0, Math.PI * 2)
      ctx.fill()
    }
  }

  if (ts - lastShootAt > 5200 && Math.random() > 0.985) {
    lastShootAt = ts
    spawnShootingStar()
  }

  for (let i = shooting.length - 1; i >= 0; i--) {
    const m = shooting[i]
    m.x += m.vx
    m.y += m.vy
    m.life -= 0.008
    if (m.life <= 0 || m.x > w + 60 || m.y > h + 60) {
      shooting.splice(i, 1)
      continue
    }
    const grad = ctx.createLinearGradient(m.x, m.y, m.x - m.vx * 26, m.y - m.vy * 26)
    grad.addColorStop(0, `rgba(255,255,255,${m.life})`)
    grad.addColorStop(1, 'rgba(255,255,255,0)')
    ctx.globalAlpha = 1
    ctx.strokeStyle = grad
    ctx.lineWidth = 2
    ctx.lineCap = 'round'
    ctx.beginPath()
    ctx.moveTo(m.x, m.y)
    ctx.lineTo(m.x - m.vx * 26, m.y - m.vy * 26)
    ctx.stroke()
  }

  ctx.globalAlpha = 1
}

function onVisibility() {
  paused = document.hidden
}

function start() {
  if (started) return
  started = true
  resize()
  raf = requestAnimationFrame(draw)
}

function scheduleStart() {
  startupTimer = window.setTimeout(() => {
    startupTimer = 0
    if ('requestIdleCallback' in window) {
      idleCallback = window.requestIdleCallback(start, { timeout: 2_000 })
    } else {
      start()
    }
  }, STARTUP_DELAY_MS)
}

function onResize() {
  if (started) resize()
}

onMounted(() => {
  // 星空是纯装饰：首屏先保留轻量 CSS 星云，Canvas 在 load 后的空闲期再启动，
  // 避免逐帧绘制与首页 LCP / Vue hydration 争抢主线程。
  if (document.readyState === 'complete') scheduleStart()
  else window.addEventListener('load', scheduleStart, { once: true })
  window.addEventListener('resize', onResize)
  document.addEventListener('visibilitychange', onVisibility)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  clearTimeout(startupTimer)
  if (idleCallback && 'cancelIdleCallback' in window) window.cancelIdleCallback(idleCallback)
  window.removeEventListener('load', scheduleStart)
  window.removeEventListener('resize', onResize)
  document.removeEventListener('visibilitychange', onVisibility)
})
</script>

<template>
  <div class="starfield" aria-hidden="true">
    <canvas ref="canvas" />
    <div class="nebula nebula-a" />
    <div class="nebula nebula-b" />
    <div class="nebula nebula-c" />
  </div>
</template>

<style scoped>
.starfield {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
}

canvas {
  display: block;
}

.nebula {
  position: absolute;
  border-radius: 50%;
  filter: blur(70px);
  opacity: 0.4;
  animation: drift 26s ease-in-out infinite alternate;
}

.nebula-a {
  width: 46vw;
  height: 46vw;
  left: -12vw;
  top: -14vw;
  background: radial-gradient(circle, rgba(94, 231, 255, 0.45), transparent 68%);
}

.nebula-b {
  width: 40vw;
  height: 40vw;
  right: -10vw;
  top: 18vh;
  background: radial-gradient(circle, rgba(255, 122, 198, 0.4), transparent 68%);
  animation-delay: -9s;
}

.nebula-c {
  width: 52vw;
  height: 52vw;
  left: 26vw;
  bottom: -26vw;
  background: radial-gradient(circle, rgba(155, 140, 255, 0.42), transparent 70%);
  animation-delay: -16s;
}

@keyframes drift {
  from {
    transform: translate3d(0, 0, 0) scale(1);
  }
  to {
    transform: translate3d(3vw, 4vh, 0) scale(1.12);
  }
}
</style>
