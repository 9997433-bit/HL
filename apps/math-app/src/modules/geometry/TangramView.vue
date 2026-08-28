<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useProgressStore } from '@/stores/progress.js'
import { sound } from '@/utils/sound.js'

const WIDTH = 720
const HEIGHT = 470
const SNAP_DISTANCE = 34
const COLORS = ['#5ee7ff', '#9b8cff', '#ff7ac6', '#ffce4d', '#55e6a5', '#ff9f45', '#ff6b7d']

const SPECS = [
  {
    id: 'large-a',
    name: '大三角 1',
    points: [[-66, -55], [66, -55], [-66, 77]],
    start: [90, 392, 0],
    target: [322, 174, 0],
  },
  {
    id: 'large-b',
    name: '大三角 2',
    points: [[-66, -55], [66, -55], [-66, 77]],
    start: [190, 392, 180],
    target: [322, 174, 180],
  },
  {
    id: 'medium',
    name: '中三角',
    points: [[-48, -39], [48, -39], [-48, 57]],
    start: [290, 397, 0],
    target: [216, 174, 45],
  },
  {
    id: 'small-a',
    name: '小三角 1',
    points: [[-34, -28], [34, -28], [-34, 40]],
    start: [380, 398, 0],
    target: [238, 272, 0],
  },
  {
    id: 'small-b',
    name: '小三角 2',
    points: [[-34, -28], [34, -28], [-34, 40]],
    start: [465, 398, 180],
    target: [407, 272, 180],
  },
  {
    id: 'square',
    name: '正方形',
    points: [[-33, -33], [33, -33], [33, 33], [-33, 33]],
    start: [550, 397, 0],
    target: [322, 96, 45],
  },
  {
    id: 'parallelogram',
    name: '平行四边形',
    points: [[-50, -29], [25, -29], [50, 29], [-25, 29]],
    start: [645, 397, 0],
    target: [322, 310, 0],
  },
]

const canvas = ref(null)
const pieces = ref([])
const selectedId = ref('')
const dragging = ref(null)
const completed = ref(false)
const progress = useProgressStore()
const route = useRoute()
const practiceSkill = computed(() =>
  String(route.query.skill ?? '') === 'symmetry' ? 'symmetry' : 'tangram-basic',
)
let context = null

const solvedCount = computed(() => pieces.value.filter((piece) => piece.locked).length)
const selected = computed(() => pieces.value.find((piece) => piece.id === selectedId.value) ?? null)
const status = computed(() => {
  if (completed.value) return '火箭拼好啦！7 块七巧板全部归位。'
  if (!selected.value) return '先点选一块，再拖到虚线轮廓中。'
  if (selected.value.locked) return `${selected.value.name} 已经归位。`
  return `已选中${selected.value.name}：拖动，或用方向键移动；R 键旋转。`
})

function freshPieces() {
  return SPECS.map((spec, index) => ({
    ...spec,
    x: spec.start[0],
    y: spec.start[1],
    rotation: spec.start[2],
    flipped: false,
    locked: false,
    color: COLORS[index],
  }))
}

function toRadians(degrees) {
  return (degrees * Math.PI) / 180
}

function transformedPoints(piece, target = false) {
  const [x, y, rotation] = target ? piece.target : [piece.x, piece.y, piece.rotation]
  const angle = toRadians(rotation)
  const cos = Math.cos(angle)
  const sin = Math.sin(angle)
  const flip = target ? 1 : piece.flipped ? -1 : 1
  return piece.points.map(([px, py]) => {
    const fx = px * flip
    return [x + fx * cos - py * sin, y + fx * sin + py * cos]
  })
}

function polygonPath(ctx, points) {
  ctx.beginPath()
  ctx.moveTo(points[0][0], points[0][1])
  for (const [x, y] of points.slice(1)) ctx.lineTo(x, y)
  ctx.closePath()
}

function drawGrid(ctx) {
  ctx.save()
  ctx.strokeStyle = 'rgba(148,168,255,0.08)'
  ctx.lineWidth = 1
  for (let x = 0; x <= WIDTH; x += 30) {
    ctx.beginPath()
    ctx.moveTo(x, 0)
    ctx.lineTo(x, HEIGHT)
    ctx.stroke()
  }
  for (let y = 0; y <= HEIGHT; y += 30) {
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(WIDTH, y)
    ctx.stroke()
  }
  ctx.restore()
}

function draw() {
  if (!context) return
  context.clearRect(0, 0, WIDTH, HEIGHT)
  const background = context.createLinearGradient(0, 0, WIDTH, HEIGHT)
  background.addColorStop(0, '#080d2b')
  background.addColorStop(1, '#17123e')
  context.fillStyle = background
  context.fillRect(0, 0, WIDTH, HEIGHT)
  drawGrid(context)

  context.save()
  context.font = '800 15px system-ui'
  context.fillStyle = 'rgba(220,230,255,0.75)'
  context.fillText('虚线火箭拼图区', 245, 34)
  context.fillText('七巧板零件区', 24, 350)
  context.restore()

  for (const piece of pieces.value) {
    polygonPath(context, transformedPoints(piece, true))
    context.fillStyle = 'rgba(255,255,255,0.035)'
    context.fill()
    context.setLineDash([8, 6])
    context.strokeStyle = piece.locked ? 'rgba(85,230,165,0.35)' : 'rgba(220,230,255,0.38)'
    context.lineWidth = 2
    context.stroke()
    context.setLineDash([])
  }

  for (const piece of pieces.value) {
    const points = transformedPoints(piece)
    polygonPath(context, points)
    context.fillStyle = piece.color
    context.globalAlpha = piece.locked ? 0.9 : 1
    context.fill()
    context.globalAlpha = 1
    context.strokeStyle = piece.id === selectedId.value ? '#ffffff' : 'rgba(6,9,30,0.72)'
    context.lineWidth = piece.id === selectedId.value ? 4 : 2
    context.stroke()
    if (piece.locked) {
      context.save()
      context.fillStyle = '#071225'
      context.font = '900 18px system-ui'
      context.textAlign = 'center'
      context.textBaseline = 'middle'
      context.fillText('✓', piece.x, piece.y)
      context.restore()
    }
  }
}

function boardPoint(event) {
  const rect = canvas.value.getBoundingClientRect()
  return {
    x: ((event.clientX - rect.left) / rect.width) * WIDTH,
    y: ((event.clientY - rect.top) / rect.height) * HEIGHT,
  }
}

function pointInPolygon(point, polygon) {
  let inside = false
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const [xi, yi] = polygon[i]
    const [xj, yj] = polygon[j]
    const crosses =
      yi > point.y !== yj > point.y &&
      point.x < ((xj - xi) * (point.y - yi)) / (yj - yi || Number.EPSILON) + xi
    if (crosses) inside = !inside
  }
  return inside
}

function onPointerDown(event) {
  const point = boardPoint(event)
  const hit = [...pieces.value]
    .reverse()
    .find((piece) => !piece.locked && pointInPolygon(point, transformedPoints(piece)))
  if (!hit) return
  selectedId.value = hit.id
  dragging.value = { id: hit.id, dx: point.x - hit.x, dy: point.y - hit.y }
  canvas.value.setPointerCapture?.(event.pointerId)
  sound.click()
}

function onPointerMove(event) {
  if (!dragging.value) return
  const piece = pieces.value.find((item) => item.id === dragging.value.id)
  if (!piece || piece.locked) return
  const point = boardPoint(event)
  piece.x = Math.max(35, Math.min(WIDTH - 35, point.x - dragging.value.dx))
  piece.y = Math.max(35, Math.min(HEIGHT - 35, point.y - dragging.value.dy))
}

function angleDistance(a, b) {
  const delta = ((a - b + 180) % 360) - 180
  return Math.abs(delta)
}

function trySnap(piece) {
  if (!piece || piece.locked) return false
  const [tx, ty, rotation] = piece.target
  const distance = Math.hypot(piece.x - tx, piece.y - ty)
  if (distance > SNAP_DISTANCE || angleDistance(piece.rotation, rotation) > 23 || piece.flipped) {
    return false
  }
  piece.x = tx
  piece.y = ty
  piece.rotation = rotation
  piece.locked = true
  sound.correct()
  checkComplete()
  return true
}

function onPointerUp(event) {
  const piece = pieces.value.find((item) => item.id === dragging.value?.id)
  dragging.value = null
  canvas.value.releasePointerCapture?.(event.pointerId)
  trySnap(piece)
}

function selectPiece(id) {
  selectedId.value = id
  sound.click()
}

function rotateSelected(direction) {
  const piece = selected.value
  if (!piece || piece.locked) return
  piece.rotation = (piece.rotation + direction * 45 + 360) % 360
  sound.click()
  trySnap(piece)
}

function flipSelected() {
  const piece = selected.value
  if (!piece || piece.locked) return
  piece.flipped = !piece.flipped
  sound.click()
}

function nudge(dx, dy) {
  const piece = selected.value
  if (!piece || piece.locked) return
  piece.x = Math.max(35, Math.min(WIDTH - 35, piece.x + dx))
  piece.y = Math.max(35, Math.min(HEIGHT - 35, piece.y + dy))
  trySnap(piece)
}

function hintSnap() {
  const piece = selected.value
  if (!piece || piece.locked) return
  const [x, y, rotation] = piece.target
  piece.x = x
  piece.y = y
  piece.rotation = rotation
  piece.flipped = false
  piece.locked = true
  sound.correct()
  checkComplete()
}

function checkComplete() {
  if (completed.value || pieces.value.some((piece) => !piece.locked)) return
  completed.value = true
  progress.recordAnswer('geometry', true, { skill: practiceSkill.value, stars: 3, xp: 24 })
  progress.finishSession('geometry', { correct: 1, total: 1 })
}

function reset() {
  pieces.value = freshPieces()
  selectedId.value = pieces.value[0].id
  dragging.value = null
  completed.value = false
  sound.click()
  nextTick(draw)
}

function onKeydown(event) {
  const actions = {
    ArrowLeft: () => nudge(-8, 0),
    ArrowRight: () => nudge(8, 0),
    ArrowUp: () => nudge(0, -8),
    ArrowDown: () => nudge(0, 8),
    r: () => rotateSelected(1),
    R: () => rotateSelected(1),
    Enter: () => trySnap(selected.value),
  }
  const action = actions[event.key]
  if (!action) return
  event.preventDefault()
  action()
}

watch([pieces, selectedId], draw, { deep: true })

onMounted(() => {
  pieces.value = freshPieces()
  selectedId.value = pieces.value[0].id
  context = canvas.value.getContext('2d')
  draw()
})

onBeforeUnmount(() => {
  context = null
})
</script>

<template>
  <main class="page stack">
    <section class="card hero">
      <div>
        <p class="kicker">Canvas 几何实验室</p>
        <h2>七巧板 · 火箭任务</h2>
        <p class="muted">拖动 7 块拼板到虚线轮廓；靠近正确位置与角度时会自动吸附。</p>
      </div>
      <div class="progress-chip">
        <strong data-tangram-solved>{{ solvedCount }} / 7</strong>
        <span>已归位</span>
      </div>
    </section>

    <section class="card board-card">
      <canvas
        ref="canvas"
        class="tangram-canvas"
        :width="WIDTH"
        :height="HEIGHT"
        data-piece-count="7"
        tabindex="0"
        role="application"
        aria-label="七巧板画布。点选并拖动拼板；方向键移动，R 键旋转。"
        @pointerdown="onPointerDown"
        @pointermove="onPointerMove"
        @pointerup="onPointerUp"
        @pointercancel="onPointerUp"
        @keydown="onKeydown"
      />
      <p class="status" aria-live="polite">{{ status }}</p>
    </section>

    <section class="card controls">
      <div class="piece-picker" role="group" aria-label="选择拼板">
        <button
          v-for="piece in pieces"
          :key="piece.id"
          class="piece-btn"
          :class="{ on: selectedId === piece.id, done: piece.locked }"
          :style="{ '--piece-color': piece.color }"
          :aria-pressed="selectedId === piece.id"
          :data-piece-select="piece.id"
          @click="selectPiece(piece.id)"
        >
          <span class="swatch" />
          {{ piece.name }} <span v-if="piece.locked">✓</span>
        </button>
      </div>

      <div class="tool-row">
        <button class="btn btn--ghost" :disabled="!selected || selected.locked" @click="rotateSelected(-1)">
          ↶ 左转 45°
        </button>
        <button
          class="btn btn--ghost"
          data-tangram-rotate
          :disabled="!selected || selected.locked"
          @click="rotateSelected(1)"
        >
          ↷ 右转 45°
        </button>
        <button class="btn btn--ghost" :disabled="!selected || selected.locked" @click="flipSelected">
          ⇋ 翻面
        </button>
        <button class="btn btn--primary" :disabled="!selected || selected.locked" @click="hintSnap">
          💡 提示归位
        </button>
        <button class="btn btn--ghost" @click="reset">重新拼</button>
      </div>
    </section>

    <section v-if="completed" class="card success" role="status">
      <span>🚀</span>
      <div>
        <h3>火箭拼装成功！</h3>
        <p>你已经用完 2 个大三角、1 个中三角、2 个小三角、1 个正方形和 1 个平行四边形。</p>
      </div>
    </section>
  </main>
</template>

<style scoped>
.hero {
  display: flex;
  align-items: center;
  gap: 18px;
}

.hero > div:first-child {
  flex: 1;
}

.hero h2 {
  margin: 3px 0 6px;
  font-size: clamp(24px, 5vw, 32px);
}

.kicker {
  color: var(--brand);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 1.5px;
}

.progress-chip {
  flex: none;
  min-width: 92px;
  padding: 12px;
  display: grid;
  justify-items: center;
  border-radius: var(--radius-md);
  background: rgba(85, 230, 165, 0.1);
  border: 1px solid rgba(85, 230, 165, 0.35);
}

.progress-chip strong {
  color: var(--success);
  font-size: 25px;
}

.progress-chip span {
  color: var(--text-soft);
  font-size: 12px;
}

.board-card {
  padding: 12px;
}

.tangram-canvas {
  width: 100%;
  height: auto;
  display: block;
  border-radius: var(--radius-md);
  border: 1px solid rgba(94, 231, 255, 0.28);
  touch-action: none;
  cursor: grab;
}

.tangram-canvas:active {
  cursor: grabbing;
}

.tangram-canvas:focus-visible {
  outline: 3px solid var(--brand);
  outline-offset: 3px;
}

.status {
  min-height: 24px;
  padding: 9px 8px 0;
  color: var(--text);
  text-align: center;
  font-size: 13px;
  font-weight: 700;
}

.controls {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.piece-picker {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(125px, 1fr));
  gap: 7px;
}

.piece-btn {
  padding: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border-radius: var(--radius-sm);
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.05);
  color: var(--text);
  font-size: 12px;
  font-weight: 800;
}

.piece-btn.on {
  border-color: var(--piece-color);
  box-shadow: 0 0 16px color-mix(in srgb, var(--piece-color) 30%, transparent);
}

.piece-btn.done {
  color: var(--success);
}

.swatch {
  width: 13px;
  height: 13px;
  border-radius: 3px;
  background: var(--piece-color);
}

.tool-row {
  display: flex;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}

.success {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  border-color: rgba(85, 230, 165, 0.42);
  background: linear-gradient(145deg, rgba(85, 230, 165, 0.17), rgba(94, 231, 255, 0.12));
}

.success > span {
  font-size: 48px;
}

.success h3 {
  color: var(--success);
  margin-bottom: 4px;
}

@media (max-width: 560px) {
  .hero {
    align-items: flex-start;
  }

  .tangram-canvas {
    min-height: 310px;
    object-fit: fill;
  }
}
</style>
