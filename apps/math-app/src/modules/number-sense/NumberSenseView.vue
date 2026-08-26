<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import gsap from 'gsap'
import MascotBot from '@/components/MascotBot.vue'
import SessionBar from '@/components/SessionBar.vue'
import RoundSummary from '@/components/RoundSummary.vue'
import { useProgressStore } from '@/stores/progress.js'
import { useFeedback } from '@/composables/useFeedback'
import { numericOptions, randInt, sample } from '@/utils/random'
import { sound } from '@/core/audio/sound.js'

const ROUND_SIZE = 8
const MODULE_ID = 'counting'

const router = useRouter()
const progress = useProgressStore()
const { correct: fxCorrect, wrong: fxWrong, burst, flyStar, pop, enter } = useFeedback()

const CARGO = [
  { icon: '💎', name: '能量水晶' },
  { icon: '🪨', name: '月岩样本' },
  { icon: '🍎', name: '太空苹果' },
  { icon: '🔋', name: '能量电池' },
  { icon: '🛸', name: '侦察飞碟' },
  { icon: '🌟', name: '星尘' },
  { icon: '🥚', name: '外星蛋' },
  { icon: '🍄', name: '星球蘑菇' },
]

/** 每题最大难度随轮次上升：先 1–10，后 1–20。 */
function makeQuestion(index) {
  const cargo = sample(CARGO)
  const ceiling = index < 3 ? 10 : 20
  const roll = Math.random()

  if (roll < 0.55) {
    const target = randInt(index < 3 ? 2 : 5, ceiling)
    const poolSize = Math.min(20, target + randInt(3, 6))
    return {
      type: 'drag',
      cargo,
      target,
      poolSize,
      prompt: `把 ${target} 个${cargo.name}装进货舱`,
      hint: `一个一个地数：1、2、3…… 数到 ${target} 就停下。`,
    }
  }

  if (roll < 0.8) {
    const target = randInt(3, ceiling)
    return {
      type: 'count',
      cargo,
      target,
      prompt: `雷达上有几个${cargo.name}？`,
      options: numericOptions(target, { count: 4, spread: 3, min: 1, max: 20 }),
      hint: '用手指点着一个一个数，别数漏也别数重复。',
    }
  }

  const step = Math.random() < 0.7 ? 1 : sample([2, 2, 5])
  const start = randInt(1, Math.max(1, ceiling - step * 4))
  const seq = [0, 1, 2, 3, 4].map((i) => start + i * step)
  const blank = randInt(1, 3)
  return {
    type: 'seq',
    cargo,
    target: seq[blank],
    seq,
    blank,
    prompt: step === 1 ? '这串数字少了哪一个？' : `每次加 ${step}，缺的是几？`,
    options: numericOptions(seq[blank], { count: 4, spread: Math.max(2, step + 1), min: 1, max: 40 }),
    hint: '看看相邻两个数差了多少，规律就出来了。',
  }
}

const questions = ref([])
const index = ref(0)
const marks = ref([])
const correctCount = ref(0)
const starsEarned = ref(0)
const showSummary = ref(false)
const locked = ref(false)
const showHint = ref(false)
const mood = ref('idle')
const message = ref('把货物拖进飞船的货舱吧！')
const chosen = ref(null)

const current = computed(() => questions.value[index.value] ?? null)

/* ---------------- 拖拽状态 ---------------- */

const pool = ref([]) // [{ id, inShip }]
const dragging = ref(null) // { id, x, y, from }
const ghostIcon = ref('')
const dropZone = ref(null)
const dropActive = ref(false)
const stageRef = ref(null)
const shipRef = ref(null)

const inShip = computed(() => pool.value.filter((p) => p.inShip))
const outside = computed(() => pool.value.filter((p) => !p.inShip))
const shipCount = computed(() => inShip.value.length)

function resetPool(q) {
  pool.value =
    q?.type === 'drag'
      ? Array.from({ length: q.poolSize }, (_, i) => ({ id: i, inShip: false }))
      : []
}

function pointerInDropZone(e) {
  const el = dropZone.value
  if (!el) return false
  const r = el.getBoundingClientRect()
  return e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom
}

function onPointerDown(e, item) {
  if (locked.value || current.value?.type !== 'drag') return
  e.preventDefault()
  ghostIcon.value = current.value.cargo.icon
  dragging.value = {
    id: item.id,
    x: e.clientX,
    y: e.clientY,
    startX: e.clientX,
    startY: e.clientY,
    moved: false,
    from: item.inShip ? 'ship' : 'pool',
  }
  window.addEventListener('pointermove', onPointerMove, { passive: false })
  window.addEventListener('pointerup', onPointerUp)
  window.addEventListener('pointercancel', onPointerUp)
}

function onPointerMove(e) {
  const d = dragging.value
  if (!d) return
  e.preventDefault()
  d.x = e.clientX
  d.y = e.clientY
  if (Math.abs(e.clientX - d.startX) > 5 || Math.abs(e.clientY - d.startY) > 5) d.moved = true
  dropActive.value = pointerInDropZone(e)
}

function onPointerUp(e) {
  const d = dragging.value
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  window.removeEventListener('pointercancel', onPointerUp)
  dragging.value = null
  dropActive.value = false
  if (!d) return
  pointerHandledAt = Date.now()

  const overShip = pointerInDropZone(e)
  const item = pool.value.find((p) => p.id === d.id)
  if (!item) return

  // 轻点（未移动）= 直接切换所在位置，方便触屏与低龄用户
  if (!d.moved) {
    setInShip(item, !item.inShip)
    return
  }
  if (d.from === 'pool' && overShip) setInShip(item, true)
  else if (d.from === 'ship' && !overShip) setInShip(item, false)
}

function setInShip(item, value) {
  if (item.inShip === value) return
  item.inShip = value
  sound.click()
  if (value) pop(shipRef.value, { scale: 1.03 })
}

/**
 * 键盘（Enter / 空格）激活按钮时浏览器只派发 click，不派发 pointer 事件，
 * 所以这里补一个兜底。指针操作后浏览器还会补发一个 click，用时间窗把它挡掉，
 * 否则一次点击会被计成两次。
 */
let pointerHandledAt = 0

function onCargoClick(item) {
  if (locked.value || current.value?.type !== 'drag') return
  if (Date.now() - pointerHandledAt < 400) return
  setInShip(item, !item.inShip)
}

/* ---------------- 判题 ---------------- */

/** 机器人的鼓励语。标题已经写了题目，这里不再重复念一遍。 */
function encourage() {
  return sample([
    '别着急，一个一个慢慢数。',
    '用手指点着数，不容易数漏哦。',
    '我在旁边给你加油 🤖',
    '数完再确认，稳一点更好。',
  ])
}


/** 映射到 curriculum 技能点，让自适应掌握度引擎能收到反馈。 */
function skillOf(q) {
  if (q.type === 'seq') return 'count-to-10'
  return q.target <= 5 ? 'count-to-5' : 'count-to-10'
}

function award(isRight, anchor) {
  marks.value[index.value] = isRight ? 'ok' : 'no'
  const skill = skillOf(current.value)
  if (isRight) {
    correctCount.value += 1
    const stars = current.value.target >= 11 ? 2 : 1
    starsEarned.value += stars
    progress.recordAnswer(MODULE_ID, true, { skill, stars, xp: 10 + current.value.target })
    fxCorrect(anchor)
    burst(anchor, { count: 18 })
    flyStar(anchor)
    mood.value = 'cheer'
    message.value = sample(['太棒了，数得真准！', '完全正确，继续保持！', '货舱装载完毕 ✅'])
  } else {
    progress.recordAnswer(MODULE_ID, false, { skill })
    fxWrong(anchor)
    mood.value = 'sad'
    message.value = `正确答案是 ${current.value.target}，我们再数一次好吗？`
  }
}

function submitDrag() {
  if (locked.value || !current.value) return
  locked.value = true
  award(shipCount.value === current.value.target, shipRef.value)
  setTimeout(next, 1500)
}

function chooseOption(value, e) {
  if (locked.value || !current.value) return
  locked.value = true
  chosen.value = value
  award(value === current.value.target, e.currentTarget)
  setTimeout(next, 1400)
}

function next() {
  chosen.value = null
  showHint.value = false
  locked.value = false
  mood.value = 'idle'
  if (index.value + 1 >= ROUND_SIZE) {
    finish()
    return
  }
  index.value += 1
  resetPool(current.value)
  message.value = encourage()
  animateIn()
}

function finish() {
  progress.finishSession(MODULE_ID, {
    correct: correctCount.value,
    total: ROUND_SIZE,
    bonusStars: correctCount.value === ROUND_SIZE ? 3 : 0,
  })
  if (correctCount.value === ROUND_SIZE) starsEarned.value += 3
  showSummary.value = true
}

function startRound() {
  questions.value = Array.from({ length: ROUND_SIZE }, (_, i) => makeQuestion(i))
  index.value = 0
  marks.value = []
  correctCount.value = 0
  starsEarned.value = 0
  showSummary.value = false
  locked.value = false
  chosen.value = null
  mood.value = 'idle'
  progress.resetCombo()
  resetPool(current.value)
  message.value = encourage()
  animateIn()
}

function animateIn() {
  requestAnimationFrame(() => {
    gsap.fromTo(
      stageRef.value,
      { opacity: 0, y: 16 },
      { opacity: 1, y: 0, duration: 0.35, ease: 'power2.out' },
    )
    enter([...document.querySelectorAll('.options .opt')], { stagger: 0.05, y: 14 })
  })
}

/** 计数题里散落的货物位置，做成稳定的伪随机分布。 */
function scatterStyle(i, total) {
  const cols = Math.ceil(Math.sqrt(total * 1.6))
  const row = Math.floor(i / cols)
  const col = i % cols
  const jitterX = ((i * 37) % 11) - 5
  const jitterY = ((i * 53) % 11) - 5
  return {
    transform: `translate(${jitterX}px, ${jitterY}px) rotate(${((i * 29) % 21) - 10}deg)`,
    gridColumn: col + 1,
    gridRow: row + 1,
  }
}

onMounted(startRound)
onBeforeUnmount(() => {
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  window.removeEventListener('pointercancel', onPointerUp)
})
</script>

<template>
  <main class="page stack">
    <section class="panel bar-panel">
      <SessionBar
        :index="index"
        :total="ROUND_SIZE"
        :correct="correctCount"
        :streak="progress.combo"
        :marks="marks"
      />
    </section>

    <section v-if="current" ref="stageRef" class="panel stage">
      <header class="stage-head">
        <MascotBot :mood="mood" :size="76" />
        <div class="head-text">
          <h2 class="prompt">{{ current.prompt }}</h2>
          <p class="muted say">{{ message }}</p>
        </div>
        <button class="btn btn-ghost btn-sm hint-btn" @click="showHint = !showHint">
          💡 {{ showHint ? '收起' : '提示' }}
        </button>
      </header>

      <p v-if="showHint" class="hint">{{ current.hint }}</p>

      <!-- 拖拽装货 -->
      <template v-if="current.type === 'drag'">
        <div class="drag-area">
          <div class="pool" :aria-label="`${current.cargo.name}仓库`">
            <button
              v-for="item in outside"
              :key="item.id"
              class="opt cargo"
              :class="{ ghosted: dragging?.id === item.id }"
              :disabled="locked"
              :aria-label="`装入一个${current.cargo.name}`"
              @pointerdown="onPointerDown($event, item)"
              @click="onCargoClick(item)"
            >
              {{ current.cargo.icon }}
            </button>
            <p v-if="outside.length === 0" class="dim empty">仓库空啦</p>
          </div>

          <div
            ref="dropZone"
            class="ship-wrap"
            :class="{ active: dropActive }"
            aria-label="飞船货舱"
          >
            <div ref="shipRef" class="ship">
              <svg class="ship-svg" viewBox="0 0 240 120" aria-hidden="true">
                <defs>
                  <linearGradient id="hull" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#8ef0ff" />
                    <stop offset="100%" stop-color="#4a67d8" />
                  </linearGradient>
                </defs>
                <ellipse cx="120" cy="96" rx="104" ry="18" fill="rgba(94,231,255,0.16)" />
                <path
                  d="M22 78 Q120 20 218 78 Q120 108 22 78 Z"
                  fill="url(#hull)"
                  stroke="rgba(255,255,255,0.5)"
                  stroke-width="2"
                />
                <circle cx="120" cy="60" r="24" fill="rgba(13,18,54,0.75)" stroke="#bff3ff" stroke-width="2" />
                <circle cx="70" cy="76" r="6" fill="#ffce4d" />
                <circle cx="170" cy="76" r="6" fill="#ff7ac6" />
              </svg>
              <div class="hold">
                <button
                  v-for="item in inShip"
                  :key="item.id"
                  class="cargo in"
                  :disabled="locked"
                  :aria-label="`取出一个${current.cargo.name}`"
                  @pointerdown="onPointerDown($event, item)"
                  @click="onCargoClick(item)"
                >
                  {{ current.cargo.icon }}
                </button>
              </div>
              <div class="counter">
                <span class="counter-num">{{ shipCount }}</span>
                <span class="counter-goal dim">/ {{ current.target }}</span>
              </div>
            </div>
            <p class="drop-tip dim">把货物拖到这里（也可以直接点一下）</p>
          </div>
        </div>

        <div class="actions">
          <button class="btn btn-ghost btn-sm" :disabled="locked || !shipCount" @click="pool.forEach((p) => (p.inShip = false))">
            🧹 清空货舱
          </button>
          <button class="btn btn-primary btn-lg" :disabled="locked" @click="submitDrag">
            🚀 发射！
          </button>
        </div>
      </template>

      <!-- 数一数 -->
      <template v-else-if="current.type === 'count'">
        <div class="radar" :style="{ '--cols': Math.ceil(Math.sqrt(current.target * 1.6)) }">
          <span
            v-for="i in current.target"
            :key="i"
            class="blip"
            :style="scatterStyle(i - 1, current.target)"
          >
            {{ current.cargo.icon }}
          </span>
        </div>
        <div class="options">
          <button
            v-for="o in current.options"
            :key="o"
            class="opt"
            :class="{
              right: locked && o === current.target,
              bad: locked && chosen === o && o !== current.target,
            }"
            :disabled="locked"
            @click="chooseOption(o, $event)"
          >
            {{ o }}
          </button>
        </div>
      </template>

      <!-- 数序 -->
      <template v-else>
        <div class="sequence">
          <span
            v-for="(n, i) in current.seq"
            :key="i"
            class="seq-cell"
            :class="{ blank: i === current.blank }"
          >
            {{ i === current.blank ? '?' : n }}
          </span>
        </div>
        <div class="options">
          <button
            v-for="o in current.options"
            :key="o"
            class="opt"
            :class="{
              right: locked && o === current.target,
              bad: locked && chosen === o && o !== current.target,
            }"
            :disabled="locked"
            @click="chooseOption(o, $event)"
          >
            {{ o }}
          </button>
        </div>
      </template>
    </section>

    <Teleport to="body">
      <div
        v-if="dragging"
        class="ghost"
        :style="{ left: `${dragging.x}px`, top: `${dragging.y}px` }"
      >
        {{ ghostIcon }}
      </div>
    </Teleport>

    <RoundSummary
      v-if="showSummary"
      :correct="correctCount"
      :total="ROUND_SIZE"
      :stars-earned="starsEarned"
      module-name="数量星云"
      @replay="startRound"
      @home="router.push('/')"
    />
  </main>
</template>

<style scoped>
.bar-panel {
  padding: 14px 18px;
}

.stage {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stage-head {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.head-text {
  flex: 1;
  min-width: 200px;
}

.prompt {
  font-size: 22px;
  font-weight: 900;
}

.say {
  font-size: 14px;
  margin-top: 4px;
}

.hint-btn {
  flex: none;
}

.hint {
  padding: 10px 14px;
  border-radius: var(--radius-s);
  background: rgba(255, 206, 77, 0.12);
  border: 1px solid rgba(255, 206, 77, 0.4);
  color: var(--gold);
  font-size: 14px;
}

/* ---- 拖拽 ---- */

.drag-area {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.1fr);
  gap: 16px;
  align-items: stretch;
}

.pool {
  display: flex;
  flex-wrap: wrap;
  align-content: flex-start;
  gap: 8px;
  padding: 14px;
  min-height: 190px;
  border-radius: var(--radius-m);
  background: rgba(255, 255, 255, 0.04);
  border: 1px dashed rgba(255, 255, 255, 0.2);
}

.cargo {
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  font-size: 26px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.14);
  touch-action: none;
  transition: transform 0.12s ease, background 0.12s ease;
}

.cargo:hover:not(:disabled) {
  transform: translateY(-3px) scale(1.08);
  background: rgba(94, 231, 255, 0.2);
}

.cargo.ghosted {
  opacity: 0.25;
}

.cargo.in {
  width: 34px;
  height: 34px;
  font-size: 20px;
  background: rgba(94, 231, 255, 0.16);
}

.empty {
  font-size: 13px;
  margin: auto;
}

.ship-wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  border-radius: var(--radius-m);
  border: 2px dashed rgba(94, 231, 255, 0.35);
  background: rgba(94, 231, 255, 0.05);
  transition: all 0.18s ease;
}

.ship-wrap.active {
  border-color: var(--green);
  background: rgba(85, 230, 165, 0.14);
  box-shadow: 0 0 28px rgba(85, 230, 165, 0.3);
}

.ship {
  position: relative;
  flex: 1;
  border-radius: var(--radius-m);
  padding: 6px;
}

.ship-svg {
  width: 100%;
  height: auto;
  display: block;
  opacity: 0.85;
}

.hold {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: center;
  min-height: 46px;
  padding: 8px;
}

.counter {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 6px;
}

.counter-num {
  font-size: 32px;
  font-weight: 900;
  color: var(--cyan);
  text-shadow: 0 0 18px rgba(94, 231, 255, 0.6);
}

.counter-goal {
  font-size: 18px;
  font-weight: 800;
}

.drop-tip {
  font-size: 12px;
  text-align: center;
}

.actions {
  display: flex;
  gap: 10px;
  justify-content: center;
  flex-wrap: wrap;
}

.ghost {
  position: fixed;
  z-index: 9999;
  transform: translate(-50%, -50%) scale(1.35);
  font-size: 30px;
  pointer-events: none;
  filter: drop-shadow(0 6px 12px rgba(0, 0, 0, 0.5));
}

/* ---- 数一数 ---- */

.radar {
  display: grid;
  grid-template-columns: repeat(var(--cols, 5), 1fr);
  gap: 6px;
  justify-items: center;
  padding: 20px;
  border-radius: var(--radius-m);
  background:
    repeating-radial-gradient(circle at 50% 50%, rgba(94, 231, 255, 0.08) 0 1px, transparent 1px 34px),
    rgba(6, 9, 30, 0.5);
  border: 1px solid rgba(94, 231, 255, 0.2);
  min-height: 170px;
  align-content: center;
}

.blip {
  font-size: 30px;
  animation: blip-in 0.4s ease-out both;
}

@keyframes blip-in {
  from {
    opacity: 0;
    transform: scale(0.4);
  }
}

/* ---- 数序 ---- */

.sequence {
  display: flex;
  gap: 10px;
  justify-content: center;
  flex-wrap: wrap;
  padding: 18px 0;
}

.seq-cell {
  width: 62px;
  height: 62px;
  display: grid;
  place-items: center;
  font-size: 26px;
  font-weight: 900;
  border-radius: var(--radius-s);
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.14);
}

.seq-cell.blank {
  color: var(--gold);
  border: 2px dashed var(--gold);
  background: rgba(255, 206, 77, 0.1);
  animation: pulse 1.4s ease-in-out infinite;
}

@keyframes pulse {
  0%,
  100% {
    box-shadow: 0 0 0 rgba(255, 206, 77, 0);
  }
  50% {
    box-shadow: 0 0 22px rgba(255, 206, 77, 0.55);
  }
}

/* ---- 选项 ---- */

.options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: 12px;
}

.options .opt {
  padding: 20px 10px;
  font-size: 28px;
  font-weight: 900;
  border-radius: var(--radius-m);
  background: linear-gradient(160deg, rgba(94, 231, 255, 0.16), rgba(155, 140, 255, 0.16));
  border: 2px solid rgba(155, 140, 255, 0.4);
  transition: transform 0.14s ease, box-shadow 0.14s ease;
}

.options .opt:hover:not(:disabled) {
  transform: translateY(-3px);
  box-shadow: 0 10px 24px rgba(94, 231, 255, 0.24);
}

.options .opt.right {
  background: rgba(85, 230, 165, 0.28);
  border-color: var(--green);
}

.options .opt.bad {
  background: rgba(255, 107, 125, 0.26);
  border-color: var(--red);
}

@media (max-width: 720px) {
  .drag-area {
    grid-template-columns: 1fr;
  }

  .prompt {
    font-size: 18px;
  }
}
</style>
