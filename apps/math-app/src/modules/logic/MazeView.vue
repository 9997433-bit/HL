<script setup>
/**
 * 逻辑迷宫 · Canvas 小游戏
 *
 * 一局三关：每关从左下角发射台出发，按 ①②③ 的顺序收齐能量块，
 * 舱门才会打开，然后才能飞到右上角的空间站。顺序这一层是「条件」，
 * 对应技能图谱里的 maze-condition（条件迷宫）——光会找路还不够，
 * 得先想清楚下一个该去哪儿。
 *
 * 迷宫生成、求解、提示都在 core/engine/maze.js 里，这里只负责画和接线。
 * 无障碍：画布本身可聚焦并接方向键，另有一组方向按钮供触屏与读屏用户使用，
 * 每走一步都会更新 aria-live 的状态行。
 *
 * 动效降级：prefers-reduced-motion（或家长关掉动效）时飞船不跑补间，
 * 直接落到目标格；能量块的呼吸光晕也一并关掉，画面完全静止。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import MascotBot from '@/components/MascotBot.vue'
import RoundSummary from '@/components/RoundSummary.vue'
import SessionBar from '@/components/SessionBar.vue'
import { useFeedback } from '@/composables/useFeedback'
import { useProgressStore } from '@/stores/progress.js'
import { AGE_BANDS, useSettingsStore } from '@/stores/settings.js'
import {
  buildMazeStage,
  canMove,
  cellIndex,
  DIRECTIONS,
  DIRECTION_MAP,
  hintDirection,
  MAZE_LEVELS,
  mazeLevelOf,
  nextObjective,
  rateRun,
  samePos,
  step,
} from '@/core/engine/maze.js'
import { sound } from '@/utils/sound'
import { uid } from '@/utils/random'

const MODULE_ID = 'maze'
const SKILL = 'maze-condition'
const STAGE_COUNT = 3
const WIDTH = 720
const PAD = 20
const MAX_BOARD_HEIGHT = 520

const router = useRouter()
const progress = useProgressStore()
const settings = useSettingsStore()
const { correct: fxCorrect, wrong: fxWrong, burst, celebrate, flyStar, prefersReducedMotion } =
  useFeedback()

const canvas = ref(null)
const band = ref(settings.ageBand)
const stage = ref(null)
const pos = ref({ x: 0, y: 0 })
const collected = ref(0)
const steps = ref(0)
const hints = ref(0)
const hintDir = ref('')
const stageIndex = ref(0)
const marks = ref([])
const clearedStages = ref(0)
const starsEarned = ref(0)
const stageDone = ref(false)
const showSummary = ref(false)
const mood = ref('idle')
const message = ref('')

let context = null
let raf = 0
/** 飞船的画面坐标（格为单位，可以是小数），追着逻辑坐标 pos 走。 */
let ship = { x: 0, y: 0 }

const level = computed(() => mazeLevelOf(band.value))
const maze = computed(() => stage.value?.maze ?? null)
const objective = computed(() => (stage.value ? nextObjective(stage.value, collected.value) : null))
const allCollected = computed(() => !!stage.value && collected.value >= stage.value.checkpoints.length)

const layout = computed(() => {
  const cols = maze.value?.cols ?? 1
  const rows = maze.value?.rows ?? 1
  const cell = Math.min((WIDTH - PAD * 2) / cols, (MAX_BOARD_HEIGHT - PAD * 2) / rows)
  return {
    cols,
    rows,
    cell,
    originX: (WIDTH - cols * cell) / 2,
    originY: PAD,
    height: Math.round(rows * cell + PAD * 2),
  }
})

const objectiveText = computed(() => {
  if (!objective.value) return ''
  return objective.value.kind === 'checkpoint'
    ? `去拿 ${objective.value.mark} 号能量块`
    : '能量收齐了，飞向空间站 🛰️'
})

const boardLabel = computed(() => {
  if (!stage.value) return '逻辑迷宫'
  return (
    `逻辑迷宫第 ${stageIndex.value + 1} 关，${layout.value.cols} 列 ${layout.value.rows} 行。` +
    `飞船在第 ${pos.value.y + 1} 行第 ${pos.value.x + 1} 列，` +
    `已收集 ${collected.value} / ${stage.value.checkpoints.length} 个能量块。${objectiveText.value}。` +
    '用方向键移动。'
  )
})

/* ---------------- 画布 ---------------- */

const FALLBACK = { wall: '#5ee7ff', ok: '#55e6a5', star: '#ffce4d', hint: '#ff7ac6' }
let palette = { ...FALLBACK }

function readPalette() {
  if (typeof window === 'undefined') return
  const css = getComputedStyle(document.documentElement)
  const token = (name, fallback) => css.getPropertyValue(name).trim() || fallback
  palette = {
    wall: token('--neon-cyan', FALLBACK.wall),
    ok: token('--success', FALLBACK.ok),
    star: token('--star', FALLBACK.star),
    hint: token('--neon-pink', FALLBACK.hint),
  }
}

function centerOf(x, y) {
  const { cell, originX, originY } = layout.value
  return { cx: originX + (x + 0.5) * cell, cy: originY + (y + 0.5) * cell }
}

function drawWalls(ctx) {
  const { cols, rows, cell, originX, originY } = layout.value
  ctx.save()
  ctx.strokeStyle = palette.wall
  ctx.lineWidth = Math.max(3, cell * 0.09)
  ctx.lineCap = 'round'
  for (let y = 0; y < rows; y++) {
    for (let x = 0; x < cols; x++) {
      const open = maze.value.open[cellIndex(maze.value, x, y)]
      const left = originX + x * cell
      const top = originY + y * cell
      const segments = [
        [open & DIRECTION_MAP.up.bit, left, top, left + cell, top],
        [open & DIRECTION_MAP.right.bit, left + cell, top, left + cell, top + cell],
        [open & DIRECTION_MAP.down.bit, left, top + cell, left + cell, top + cell],
        [open & DIRECTION_MAP.left.bit, left, top, left, top + cell],
      ]
      for (const [passable, x1, y1, x2, y2] of segments) {
        if (passable) continue
        ctx.beginPath()
        ctx.moveTo(x1, y1)
        ctx.lineTo(x2, y2)
        ctx.stroke()
      }
    }
  }
  ctx.restore()
}

function drawMarker(ctx, x, y, text, { color, dim = false, glow = 0 }) {
  const { cell } = layout.value
  const { cx, cy } = centerOf(x, y)
  ctx.save()
  ctx.beginPath()
  ctx.arc(cx, cy, cell * (0.3 + glow * 0.04), 0, Math.PI * 2)
  ctx.fillStyle = dim ? 'rgba(255,255,255,0.08)' : color
  ctx.globalAlpha = dim ? 1 : 0.28
  ctx.fill()
  ctx.globalAlpha = 1
  ctx.lineWidth = 2
  ctx.strokeStyle = dim ? 'rgba(255,255,255,0.2)' : color
  ctx.stroke()
  ctx.fillStyle = dim ? 'rgba(226,233,255,0.45)' : color
  ctx.font = `800 ${Math.round(cell * 0.44)}px system-ui`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(text, cx, cy)
  ctx.restore()
}

function drawHint(ctx) {
  if (!hintDir.value) return
  const dir = DIRECTION_MAP[hintDir.value]
  const { cell } = layout.value
  const { cx, cy } = centerOf(pos.value.x, pos.value.y)
  ctx.save()
  ctx.fillStyle = palette.hint
  ctx.font = `900 ${Math.round(cell * 0.5)}px system-ui`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText(dir.arrow, cx + dir.dx * cell * 0.62, cy + dir.dy * cell * 0.62)
  ctx.restore()
}

function draw() {
  if (!context || !stage.value) return
  const { cell, height } = layout.value
  context.clearRect(0, 0, WIDTH, height)
  const bg = context.createLinearGradient(0, 0, WIDTH, height)
  bg.addColorStop(0, 'rgba(8,13,43,0.92)')
  bg.addColorStop(1, 'rgba(23,18,62,0.92)')
  context.fillStyle = bg
  context.fillRect(0, 0, WIDTH, height)

  drawWalls(context)

  const gate = allCollected.value
  drawMarker(context, stage.value.goal.x, stage.value.goal.y, gate ? '🛰️' : '🔒', {
    color: gate ? palette.ok : palette.star,
    dim: !gate,
  })
  drawMarker(context, stage.value.start.x, stage.value.start.y, '🏁', {
    color: palette.wall,
    dim: true,
  })
  stage.value.checkpoints.forEach((cp) => {
    const done = cp.order < collected.value
    const isNext = cp.order === collected.value
    drawMarker(context, cp.x, cp.y, done ? '✓' : cp.mark, {
      color: done ? palette.ok : palette.star,
      dim: done,
      glow: isNext ? 1 : 0,
    })
  })

  drawHint(context)

  const { originX, originY } = layout.value
  context.save()
  context.font = `${Math.round(cell * 0.56)}px system-ui`
  context.textAlign = 'center'
  context.textBaseline = 'middle'
  context.fillText(
    '🚀',
    originX + (ship.x + 0.5) * cell,
    originY + (ship.y + 0.5) * cell,
  )
  context.restore()
}

/** 飞船补间：动效关掉时直接落格，一帧都不跑。 */
function tick() {
  raf = 0
  const dx = pos.value.x - ship.x
  const dy = pos.value.y - ship.y
  if (Math.hypot(dx, dy) < 0.02) {
    ship = { x: pos.value.x, y: pos.value.y }
    draw()
    return
  }
  ship = { x: ship.x + dx * 0.3, y: ship.y + dy * 0.3 }
  draw()
  raf = requestAnimationFrame(tick)
}

function syncShip() {
  if (prefersReducedMotion()) {
    ship = { x: pos.value.x, y: pos.value.y }
    draw()
    return
  }
  if (!raf) raf = requestAnimationFrame(tick)
}

/* ---------------- 玩法 ---------------- */

function anchorEl() {
  return canvas.value
}

function collectAt(target) {
  const cp = stage.value.checkpoints.find((c) => samePos(c, target))
  if (!cp) return
  if (cp.order < collected.value) return

  // 路过后面编号的能量块是常事，不算错，只提醒它现在还拿不走
  if (cp.order > collected.value) {
    const wanted = stage.value.checkpoints[collected.value]
    message.value = `${cp.mark} 还不能拿，要先收 ${wanted.mark}。`
    mood.value = 'think'
    return
  }

  collected.value += 1
  starsEarned.value += 1
  progress.recordAnswer(MODULE_ID, true, { skill: SKILL, stars: 1, xp: 8 })
  fxCorrect(anchorEl(), { streak: progress.combo })
  burst(anchorEl(), { count: 14 })
  flyStar(anchorEl())
  mood.value = 'cheer'
  message.value = allCollected.value
    ? '能量收齐，舱门打开了，飞向空间站！'
    : `拿到 ${cp.mark}！接下来去 ${stage.value.checkpoints[collected.value].mark}。`
}

function reachGoal() {
  if (!allCollected.value) {
    message.value = `舱门还锁着，先去拿 ${objective.value.mark} 号能量块。`
    mood.value = 'think'
    fxWrong(anchorEl())
    return
  }
  const stars = rateRun(stage.value, { steps: steps.value, hints: hints.value })
  starsEarned.value += stars
  clearedStages.value += 1
  marks.value[stageIndex.value] = hints.value ? 'no' : 'ok'
  stageDone.value = true
  mood.value = 'cheer'
  progress.recordAnswer(MODULE_ID, true, { skill: SKILL, stars, xp: 18 })
  celebrate(anchorEl())
  message.value =
    `第 ${stageIndex.value + 1} 关通关！走了 ${steps.value} 步` +
    `（最短 ${stage.value.optimalSteps} 步），拿到 ${stars} 颗星。`
  if (stageIndex.value + 1 >= STAGE_COUNT) finishRound()
}

function move(dirId) {
  if (!stage.value || stageDone.value || showSummary.value) return
  if (!DIRECTION_MAP[dirId]) return

  if (!canMove(maze.value, pos.value, dirId)) {
    message.value = `${DIRECTION_MAP[dirId].name}边是墙，换个方向试试。`
    mood.value = 'think'
    fxWrong(anchorEl(), { sound: true })
    return
  }

  hintDir.value = ''
  pos.value = step(pos.value, dirId)
  steps.value += 1
  sound.click()
  syncShip()

  collectAt(pos.value)
  if (samePos(pos.value, stage.value.goal)) reachGoal()
}

function askHint() {
  if (!stage.value || stageDone.value) return
  const dir = hintDirection(stage.value, pos.value, collected.value)
  if (!dir) return
  hints.value += 1
  hintDir.value = dir
  sound.click()
  message.value = `提示：先往${DIRECTION_MAP[dir].name}走（少 1⭐）。`
  draw()
}

function loadStage(index = stageIndex.value) {
  const config = level.value
  const built = buildMazeStage({ ...config, seed: `maze-${uid()}-${index}` })
  if (!built) return
  stage.value = built
  pos.value = { ...built.start }
  ship = { x: built.start.x, y: built.start.y }
  collected.value = 0
  steps.value = 0
  hints.value = 0
  hintDir.value = ''
  stageDone.value = false
  mood.value = 'idle'
  message.value = `第 ${index + 1} 关：按 ${built.checkpoints
    .map((c) => c.mark)
    .join('→')} 的顺序收集能量块，再飞到空间站。`
  nextTick(() => {
    draw()
    canvas.value?.focus?.()
  })
}

function nextStage() {
  stageIndex.value += 1
  loadStage(stageIndex.value)
}

function finishRound() {
  progress.finishSession(MODULE_ID, {
    correct: clearedStages.value,
    total: STAGE_COUNT,
    bonusStars: clearedStages.value === STAGE_COUNT ? 2 : 0,
  })
  if (clearedStages.value === STAGE_COUNT) starsEarned.value += 2
  showSummary.value = true
}

function startRound() {
  stageIndex.value = 0
  clearedStages.value = 0
  starsEarned.value = 0
  marks.value = []
  showSummary.value = false
  progress.resetCombo()
  loadStage(0)
}

function chooseBand(id) {
  band.value = id
  startRound()
}

const KEY_MAP = {
  ArrowUp: 'up',
  ArrowRight: 'right',
  ArrowDown: 'down',
  ArrowLeft: 'left',
  w: 'up',
  d: 'right',
  s: 'down',
  a: 'left',
  W: 'up',
  D: 'right',
  S: 'down',
  A: 'left',
}

function onKeydown(event) {
  const dir = KEY_MAP[event.key]
  if (!dir) return
  event.preventDefault()
  move(dir)
}

watch(
  () => layout.value.height,
  () => nextTick(draw),
)

onMounted(() => {
  readPalette()
  context = canvas.value?.getContext('2d') ?? null
  startRound()
})

onBeforeUnmount(() => {
  if (raf) cancelAnimationFrame(raf)
  context = null
})
</script>

<template>
  <main class="page stack">
    <section class="card hero">
      <div class="hero-text">
        <p class="kicker">Canvas 逻辑小游戏</p>
        <h2>逻辑迷宫 · 能量补给线</h2>
        <p class="muted">
          从发射台出发，按编号顺序收齐能量块，空间站的舱门才会打开。方向键或下面的方向盘都能开船。
        </p>
      </div>
      <div class="hero-stats">
        <span class="chip" data-maze-steps>👣 {{ steps }} 步</span>
        <span class="chip" data-maze-collected>
          ⚡ {{ collected }} / {{ stage?.checkpoints.length ?? 0 }}
        </span>
        <span class="chip chip-on" data-maze-objective>{{ objectiveText }}</span>
      </div>
    </section>

    <section class="card bar-panel">
      <SessionBar
        :index="clearedStages"
        :total="STAGE_COUNT"
        :correct="clearedStages"
        :streak="progress.combo"
        :marks="marks"
      />
    </section>

    <section class="card stage-card">
      <header class="stage-head">
        <MascotBot :mood="mood" :size="64" />
        <p class="say" data-maze-status aria-live="polite">{{ message }}</p>
        <button class="btn btn--ghost btn--sm" data-maze-hint :disabled="stageDone" @click="askHint">
          💡 指个方向（少 1⭐）
        </button>
      </header>

      <div class="board" :style="{ aspectRatio: `${WIDTH} / ${layout.height}` }">
        <canvas
          ref="canvas"
          class="maze-canvas"
          :width="WIDTH"
          :height="layout.height"
          :data-maze-size="`${layout.cols}x${layout.rows}`"
          :data-maze-pos="`${pos.x},${pos.y}`"
          tabindex="0"
          role="application"
          :aria-label="boardLabel"
          @keydown="onKeydown"
        />
      </div>

      <div class="pad" role="group" aria-label="方向盘">
        <button
          v-for="dir in DIRECTIONS"
          :key="dir.id"
          class="btn btn--ghost pad-btn"
          :class="`pad-${dir.id}`"
          :data-maze-move="dir.id"
          :disabled="stageDone"
          :aria-label="`向${dir.name}走`"
          @click="move(dir.id)"
        >
          {{ dir.arrow }}
        </button>
        <span class="pad-hub" aria-hidden="true">🚀</span>
      </div>

      <div v-if="stageDone && !showSummary" class="cleared" role="status">
        <strong>🎉 第 {{ stageIndex + 1 }} 关完成</strong>
        <button class="btn btn--primary" data-maze-next @click="nextStage">下一关 →</button>
      </div>
    </section>

    <section class="card level-panel">
      <div class="seg" role="group" aria-label="难度档">
        <button
          v-for="option in AGE_BANDS"
          :key="option.id"
          class="seg-btn"
          :class="{ on: band === option.id }"
          :aria-pressed="band === option.id"
          :data-maze-band="option.id"
          @click="chooseBand(option.id)"
        >
          {{ option.id }} · {{ MAZE_LEVELS[option.id].cols }}×{{ MAZE_LEVELS[option.id].rows }}
        </button>
      </div>
      <div class="level-actions">
        <button class="btn btn--ghost" @click="startRound">🔄 换一座迷宫</button>
        <button class="btn btn--ghost" @click="router.push('/memory-pairs')">🃏 去玩配对记忆</button>
      </div>
    </section>

    <RoundSummary
      v-if="showSummary"
      :correct="clearedStages"
      :total="STAGE_COUNT"
      :stars-earned="starsEarned"
      module-name="逻辑迷宫"
      @replay="startRound"
      @home="router.push('/')"
    />
  </main>
</template>

<style scoped>
.hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.hero-text {
  flex: 1;
  min-width: 260px;
}

.kicker {
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--neon-cyan);
  font-weight: 800;
}

.hero-stats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.bar-panel {
  padding: 14px 18px;
}

.stage-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.stage-head {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.say {
  flex: 1;
  min-width: 200px;
  font-size: 15px;
  font-weight: 700;
}

.board {
  width: 100%;
}

.maze-canvas {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: var(--radius-md);
  border: 1px solid rgba(94, 231, 255, 0.22);
}

.maze-canvas:focus-visible {
  outline: 3px solid var(--star);
  outline-offset: 2px;
}

.pad {
  align-self: center;
  display: grid;
  grid-template-columns: repeat(3, 62px);
  grid-template-rows: repeat(3, 56px);
  gap: 6px;
  place-items: stretch;
}

.pad-btn {
  min-height: 0;
  font-size: 22px;
  padding: 0;
}

.pad-up {
  grid-area: 1 / 2;
}

.pad-left {
  grid-area: 2 / 1;
}

.pad-right {
  grid-area: 2 / 3;
}

.pad-down {
  grid-area: 3 / 2;
}

.pad-hub {
  grid-area: 2 / 2;
  display: grid;
  place-items: center;
  font-size: 24px;
}

.cleared {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  flex-wrap: wrap;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  background: rgba(85, 230, 165, 0.12);
  border: 1px solid rgba(85, 230, 165, 0.4);
}

.level-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.seg {
  display: flex;
  gap: 4px;
  padding: 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  flex-wrap: wrap;
}

.seg-btn {
  padding: 7px 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 800;
  color: var(--text);
  white-space: nowrap;
  transition: all 0.16s ease;
}

.seg-btn.on {
  background: linear-gradient(135deg, var(--accent), var(--neon-pink));
  color: var(--text-invert);
  box-shadow: 0 6px 16px rgba(155, 140, 255, 0.34);
}

.level-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
