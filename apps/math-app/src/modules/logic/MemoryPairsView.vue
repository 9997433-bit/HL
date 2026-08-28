<script setup>
/**
 * 配对记忆 · Canvas 小游戏
 *
 * 画布只负责画：牌背、翻牌、配对成功的高亮全在 canvas 上完成；
 * 交互与无障碍走盖在画布上的一层透明按钮，每张牌一个 <button>，
 * 带 aria-label 报出「第几张 / 翻没翻开 / 是什么」，键盘 Tab + 回车能整局玩完。
 *
 * 动效降级：prefers-reduced-motion（或家长关掉动效）时不跑 rAF 翻牌补间，
 * 直接切到正反面，配错后的回盖也缩短成一次静态延时。
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import LearnDemoLauncher from '@/components/LearnDemoLauncher.vue'
import MascotBot from '@/components/MascotBot.vue'
import RoundSummary from '@/components/RoundSummary.vue'
import SessionBar from '@/components/SessionBar.vue'
import { useFeedback } from '@/composables/useFeedback'
import { useProgressStore } from '@/stores/progress.js'
import { AGE_BANDS, useSettingsStore } from '@/stores/settings.js'
import {
  buildMemoryDeck,
  describeCard,
  isMatch,
  matchReason,
  memoryLevelOf,
  MEMORY_LEVELS,
  MEMORY_MODES,
} from '@/core/engine/memory-pairs.js'
import { sound } from '@/utils/sound'

const MODULE_ID = 'memory-pairs'
const SKILL = 'classify'
const WIDTH = 720
const PAD = 18
const GAP = 14
const MAX_BOARD_HEIGHT = 520
const PEEK_MS = 1500

const router = useRouter()
const progress = useProgressStore()
const settings = useSettingsStore()
const { correct: fxCorrect, wrong: fxWrong, burst, celebrate, flyStar, enter, prefersReducedMotion } =
  useFeedback()

const canvas = ref(null)
const deck = ref(buildMemoryDeck(memoryLevelOf(settings.ageBand)))
const flipped = ref([])
const matched = ref([])
const attempts = ref(0)
const marks = ref([])
const starsEarned = ref(0)
const locked = ref(false)
const peeking = ref(false)
const hintUsed = ref(false)
const showSummary = ref(false)
const mood = ref('idle')
const message = ref('')
const band = ref(settings.ageBand)

let context = null
let raf = 0
let flipTimer = 0
let peekTimer = 0
/** 每张牌的翻面进度 0（背面）→ 1（正面）。画布每帧读它，不进响应式。 */
let progressOf = []

const cards = computed(() => deck.value.cards)
const pairCount = computed(() => deck.value.pairs)
const modeInfo = computed(() => MEMORY_MODES[deck.value.mode])
const matchedPairs = computed(() => matched.value.length / 2)
const grid = computed(() => deck.value.grid)

const layout = computed(() => {
  const { cols, rows } = grid.value
  const cardW = (WIDTH - PAD * 2 - (cols - 1) * GAP) / cols
  const roomy = (MAX_BOARD_HEIGHT - PAD * 2 - (rows - 1) * GAP) / rows
  const cardH = Math.min(cardW * 1.24, roomy)
  return {
    cols,
    rows,
    cardW,
    cardH,
    height: Math.round(PAD * 2 + rows * cardH + (rows - 1) * GAP),
  }
})

const boxOf = (index) => {
  const { cols, cardW, cardH } = layout.value
  return {
    x: PAD + (index % cols) * (cardW + GAP),
    y: PAD + Math.floor(index / cols) * (cardH + GAP),
    w: cardW,
    h: cardH,
  }
}

const stateOf = (card) => {
  if (matched.value.includes(card.id)) return 'matched'
  if (peeking.value || flipped.value.includes(card.id)) return 'up'
  return 'down'
}

const labelOf = (card, index) =>
  describeCard(card, { index, total: cards.value.length, state: stateOf(card) })

const boardLabel = computed(
  () =>
    `配对记忆牌桌，${cards.value.length} 张卡片，已配对 ${matchedPairs.value} / ${pairCount.value} 对。` +
    modeInfo.value.rule,
)

/* ---------------- 画布 ---------------- */

const FALLBACK = { back: '#5ee7ff', ok: '#55e6a5', star: '#ffce4d' }

let palette = { ...FALLBACK }

/** 画布读不到 CSS 变量，挂载时把主题色抄一份进来，换主题也就跟着换。 */
function readPalette() {
  if (typeof window === 'undefined') return
  const css = getComputedStyle(document.documentElement)
  const token = (name, fallback) => css.getPropertyValue(name).trim() || fallback
  palette = {
    back: token('--neon-cyan', FALLBACK.back),
    ok: token('--success', FALLBACK.ok),
    star: token('--star', FALLBACK.star),
  }
}

function roundRect(ctx, x, y, w, h, r) {
  const radius = Math.min(r, w / 2, h / 2)
  ctx.beginPath()
  ctx.moveTo(x + radius, y)
  ctx.arcTo(x + w, y, x + w, y + h, radius)
  ctx.arcTo(x + w, y + h, x, y + h, radius)
  ctx.arcTo(x, y + h, x, y, radius)
  ctx.arcTo(x, y, x + w, y, radius)
  ctx.closePath()
}

function drawBack(ctx, box) {
  const gradient = ctx.createLinearGradient(box.x, box.y, box.x + box.w, box.y + box.h)
  gradient.addColorStop(0, 'rgba(94,231,255,0.34)')
  gradient.addColorStop(1, 'rgba(155,140,255,0.34)')
  roundRect(ctx, box.x, box.y, box.w, box.h, 16)
  ctx.fillStyle = gradient
  ctx.fill()
  ctx.strokeStyle = palette.back
  ctx.lineWidth = 2
  ctx.stroke()
  ctx.save()
  ctx.fillStyle = 'rgba(255,255,255,0.72)'
  ctx.font = `700 ${Math.round(box.h * 0.3)}px system-ui`
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillText('?', box.x + box.w / 2, box.y + box.h / 2)
  ctx.restore()
}

function drawFront(ctx, box, card, done) {
  roundRect(ctx, box.x, box.y, box.w, box.h, 16)
  ctx.fillStyle = done ? 'rgba(85,230,165,0.22)' : 'rgba(255,255,255,0.1)'
  ctx.fill()
  ctx.strokeStyle = done ? palette.ok : 'rgba(255,255,255,0.5)'
  ctx.lineWidth = done ? 3 : 2
  ctx.stroke()

  ctx.save()
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.font = `${Math.round(box.h * 0.42)}px system-ui`
  ctx.fillText(card.glyph, box.x + box.w / 2, box.y + box.h * 0.44)
  ctx.font = `700 ${Math.max(12, Math.round(box.h * 0.15))}px system-ui`
  ctx.fillStyle = done ? palette.ok : 'rgba(226,233,255,0.9)'
  ctx.fillText(card.label, box.x + box.w / 2, box.y + box.h * 0.8)
  if (done) {
    ctx.font = `700 ${Math.max(11, Math.round(box.h * 0.13))}px system-ui`
    ctx.fillStyle = palette.star
    ctx.fillText('✓', box.x + box.w - 16, box.y + 16)
  }
  ctx.restore()
}

function draw() {
  if (!context) return
  const { height } = layout.value
  context.clearRect(0, 0, WIDTH, height)
  const bg = context.createLinearGradient(0, 0, WIDTH, height)
  bg.addColorStop(0, 'rgba(8,13,43,0.9)')
  bg.addColorStop(1, 'rgba(23,18,62,0.9)')
  context.fillStyle = bg
  context.fillRect(0, 0, WIDTH, height)

  cards.value.forEach((card, index) => {
    const box = boxOf(index)
    const p = progressOf[index] ?? 0
    const squeeze = Math.abs(Math.cos(Math.PI * p))
    const w = Math.max(2, box.w * squeeze)
    const scaled = { x: box.x + (box.w - w) / 2, y: box.y, w, h: box.h }
    if (p < 0.5) drawBack(context, scaled)
    else drawFront(context, scaled, card, matched.value.includes(card.id))
  })
}

/** 翻牌补间：只在还有牌没到位时占着 rAF，动效关掉时一步到位。 */
function tick() {
  raf = 0
  let moving = false
  cards.value.forEach((card, index) => {
    const target = stateOf(card) === 'down' ? 0 : 1
    const current = progressOf[index] ?? 0
    const delta = target - current
    if (Math.abs(delta) < 0.02) {
      progressOf[index] = target
      return
    }
    progressOf[index] = current + Math.sign(delta) * 0.12
    moving = true
  })
  draw()
  if (moving) raf = requestAnimationFrame(tick)
}

function sync() {
  if (prefersReducedMotion()) {
    progressOf = cards.value.map((card) => (stateOf(card) === 'down' ? 0 : 1))
    draw()
    return
  }
  if (!raf) raf = requestAnimationFrame(tick)
}

/* ---------------- 玩法 ---------------- */

function cardById(id) {
  return cards.value.find((card) => card.id === id) ?? null
}

function resolve(anchor) {
  const [a, b] = flipped.value.map(cardById)
  attempts.value += 1
  message.value = matchReason(a, b, deck.value.mode)

  if (isMatch(a, b)) {
    const stars = hintUsed.value ? 1 : 2
    matched.value.push(a.id, b.id)
    flipped.value = []
    marks.value[matchedPairs.value - 1] = 'ok'
    starsEarned.value += stars
    mood.value = 'cheer'
    progress.recordAnswer(MODULE_ID, true, { skill: SKILL, stars, xp: 12 })
    fxCorrect(anchor, { streak: progress.combo })
    burst(anchor, { count: 16 })
    flyStar(anchor)
    sync()
    if (matchedPairs.value === pairCount.value) finish(anchor)
    return
  }

  mood.value = 'sad'
  locked.value = true
  progress.recordAnswer(MODULE_ID, false, { skill: SKILL })
  fxWrong(anchor)
  sync()
  flipTimer = window.setTimeout(
    () => {
      flipped.value = []
      locked.value = false
      mood.value = 'idle'
      message.value = '记住它们在哪儿，再试一次。'
      sync()
    },
    prefersReducedMotion() ? 700 : 1100,
  )
}

function onCardClick(index, event) {
  const card = cards.value[index]
  if (!card || locked.value || peeking.value || showSummary.value) return
  if (matched.value.includes(card.id) || flipped.value.includes(card.id)) return

  sound.click()
  flipped.value = [...flipped.value, card.id]
  mood.value = 'think'
  sync()
  if (flipped.value.length < 2) {
    message.value = '再翻一张，看看能不能配上。'
    return
  }
  resolve(event.currentTarget)
}

function finish(anchor) {
  const perfect = attempts.value === pairCount.value
  if (perfect) starsEarned.value += 3
  progress.finishSession(MODULE_ID, {
    correct: pairCount.value,
    total: Math.max(attempts.value, pairCount.value),
    bonusStars: perfect ? 3 : 0,
  })
  celebrate(anchor ?? canvas.value)
  message.value = perfect
    ? `${attempts.value} 次全中，一张都没记错！`
    : `全部配对完成，一共翻了 ${attempts.value} 次。`
  showSummary.value = true
}

/** 全场偷看一眼：救急用，看过之后这一局每对只记 1 颗星。 */
function peek() {
  if (peeking.value || locked.value || showSummary.value) return
  sound.click()
  hintUsed.value = true
  peeking.value = true
  message.value = '记住它们的位置！'
  sync()
  peekTimer = window.setTimeout(() => {
    peeking.value = false
    sync()
  }, PEEK_MS)
}

function startRound(level = memoryLevelOf(band.value)) {
  window.clearTimeout(flipTimer)
  window.clearTimeout(peekTimer)
  deck.value = buildMemoryDeck(level)
  flipped.value = []
  matched.value = []
  marks.value = []
  attempts.value = 0
  starsEarned.value = 0
  locked.value = false
  peeking.value = false
  hintUsed.value = false
  showSummary.value = false
  mood.value = 'idle'
  message.value = modeInfo.value.rule
  progressOf = cards.value.map(() => 0)
  progress.resetCombo()
  nextTick(() => {
    draw()
    sync()
    enter([...document.querySelectorAll('.mem-chip')], { stagger: 0.05, y: 12 })
  })
}

function chooseBand(id) {
  band.value = id
  startRound(memoryLevelOf(id))
}

watch([matched, flipped, peeking], sync, { deep: true })
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
  window.clearTimeout(flipTimer)
  window.clearTimeout(peekTimer)
  context = null
})
</script>

<template>
  <main class="page stack">
    <section class="card hero">
      <div class="hero-text">
        <p class="kicker">Canvas 逻辑小游戏</p>
        <h2>配对记忆 · 记忆矩阵</h2>
        <p class="muted">{{ modeInfo.rule }}翻开两张卡片，配上了就把它们留在桌面上。</p>
      </div>
      <div class="hero-stats">
        <span class="chip mem-chip" data-memory-matched>
          🧠 {{ matchedPairs }} / {{ pairCount }} 对
        </span>
        <span class="chip mem-chip" data-memory-attempts>🔁 翻了 {{ attempts }} 次</span>
        <span class="chip mem-chip chip-on">{{ modeInfo.name }}</span>
      </div>
    </section>

    <section class="card bar-panel">
      <SessionBar
        :index="matchedPairs"
        :total="pairCount"
        :correct="matchedPairs"
        :streak="progress.combo"
        :marks="marks"
      />
    </section>

    <section class="card stage">
      <header class="stage-head">
        <MascotBot :mood="mood" :size="64" />
        <p class="say" aria-live="polite">{{ message }}</p>
        <LearnDemoLauncher :skill="SKILL" />
        <button class="btn btn--ghost btn--sm" data-memory-peek :disabled="peeking" @click="peek">
          👀 偷看一眼（少 1⭐）
        </button>
      </header>

      <div class="board" :style="{ aspectRatio: `${WIDTH} / ${layout.height}` }">
        <canvas
          ref="canvas"
          class="board-canvas"
          :width="WIDTH"
          :height="layout.height"
          role="img"
          :data-memory-cards="cards.length"
          :aria-label="boardLabel"
        />
        <button
          v-for="(card, index) in cards"
          :key="card.id"
          class="card-hit"
          :class="{ up: stateOf(card) !== 'down', done: stateOf(card) === 'matched' }"
          :data-card-index="index"
          :data-card-pair="card.pairId"
          :data-card-state="stateOf(card)"
          :aria-disabled="stateOf(card) === 'matched'"
          :aria-label="labelOf(card, index)"
          :style="{
            left: `${(boxOf(index).x / WIDTH) * 100}%`,
            top: `${(boxOf(index).y / layout.height) * 100}%`,
            width: `${(boxOf(index).w / WIDTH) * 100}%`,
            height: `${(boxOf(index).h / layout.height) * 100}%`,
          }"
          @click="onCardClick(index, $event)"
        />
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
          :data-memory-band="option.id"
          @click="chooseBand(option.id)"
        >
          {{ option.id }} · {{ MEMORY_LEVELS[option.id].pairs }} 对
        </button>
      </div>
      <div class="level-actions">
        <button class="btn btn--ghost" @click="startRound()">🔄 换一副牌</button>
        <button class="btn btn--ghost" @click="router.push('/maze')">🌀 去玩逻辑迷宫</button>
      </div>
    </section>

    <RoundSummary
      v-if="showSummary"
      :correct="pairCount"
      :total="Math.max(attempts, pairCount)"
      :stars-earned="starsEarned"
      module-name="配对记忆"
      @replay="startRound()"
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
  min-width: 240px;
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

.stage {
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
  position: relative;
  width: 100%;
}

.board-canvas {
  display: block;
  width: 100%;
  height: 100%;
  border-radius: var(--radius-md);
  border: 1px solid rgba(94, 231, 255, 0.22);
}

.card-hit {
  position: absolute;
  padding: 0;
  background: transparent;
  border: 2px solid transparent;
  border-radius: 16px;
  cursor: pointer;
}

.card-hit:hover:not([aria-disabled='true']) {
  border-color: rgba(255, 255, 255, 0.45);
}

.card-hit:focus-visible {
  outline: 3px solid var(--star);
  outline-offset: 2px;
}

.card-hit.done {
  cursor: default;
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

@media (max-width: 560px) {
  .say {
    font-size: 14px;
  }
}
</style>
