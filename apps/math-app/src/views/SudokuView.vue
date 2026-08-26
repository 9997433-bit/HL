<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import gsap from 'gsap'
import RoundSummary from '@/components/RoundSummary.vue'
import MascotBot from '@/components/MascotBot.vue'
import { conflicts, generatePuzzle, N } from '@/utils/sudoku'
import { useFeedback } from '@/composables/useFeedback'
import { useProgressStore } from '@/stores/progress'
import { sfx } from '@/utils/sound'

const router = useRouter()
const progress = useProgressStore()
const { correct: fxCorrect, wrong: fxWrong, burst, flyStar, pop } = useFeedback()

const SYMBOLS = { number: ['1', '2', '3', '4'], emoji: ['🚀', '🪐', '⭐', '🛸'] }

const level = ref('easy')
const skin = ref('number')
const grid = ref([])
const given = ref([])
const solution = ref([])
const selected = ref(null)
const solved = ref(false)
const hintsUsed = ref(0)
const mistakes = ref(0)
const startedAt = ref(Date.now())
const elapsed = ref(0)
const boardEl = ref(null)
const cellRefs = ref([])
const lastStars = ref(0)

let timer = null

const badCells = computed(() => conflicts(grid.value))
const filledCount = computed(() => grid.value.filter((v) => v !== 0).length)
const complete = computed(() => filledCount.value === N * N && badCells.value.size === 0)
const symbols = computed(() => SYMBOLS[skin.value])

const timeLabel = computed(() => {
  const s = Math.floor(elapsed.value / 1000)
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
})

/** 已经在盘面上出现 4 次的数字可以从键盘上淡出。 */
const usedUp = computed(() => {
  const counts = {}
  for (const v of grid.value) if (v) counts[v] = (counts[v] ?? 0) + 1
  return counts
})

function newPuzzle() {
  const { puzzle, solution: sol, given: g } = generatePuzzle(level.value)
  grid.value = puzzle
  solution.value = sol
  given.value = g
  selected.value = null
  solved.value = false
  hintsUsed.value = 0
  mistakes.value = 0
  startedAt.value = Date.now()
  elapsed.value = 0
  nextTick(() => {
    gsap.fromTo(
      '.cell',
      { scale: 0.4, opacity: 0 },
      { scale: 1, opacity: 1, duration: 0.34, stagger: 0.03, ease: 'back.out(2)' },
    )
  })
}

function selectCell(i) {
  if (given.value[i] || solved.value) return
  selected.value = i
  sfx.tap()
  pop(cellRefs.value[i], { scale: 1.08 })
}

function place(v) {
  if (selected.value === null || solved.value) return
  const i = selected.value
  if (given.value[i]) return

  grid.value = grid.value.map((x, k) => (k === i ? (x === v ? 0 : v) : x))
  const el = cellRefs.value[i]

  if (grid.value[i] !== 0 && grid.value[i] !== solution.value[i]) {
    mistakes.value += 1
    fxWrong(el)
    progress.recordAnswer('sudoku', false)
  } else if (grid.value[i] !== 0) {
    sfx.tap()
    pop(el, { scale: 1.18 })
    progress.recordAnswer('sudoku', true, { stars: 0, xp: 4 })
  }
}

function erase() {
  if (selected.value === null || solved.value) return
  const i = selected.value
  if (given.value[i]) return
  grid.value = grid.value.map((x, k) => (k === i ? 0 : x))
  sfx.tap()
}

function hint() {
  if (solved.value) return
  const empties = grid.value
    .map((v, i) => (v === 0 || v !== solution.value[i] ? i : -1))
    .filter((i) => i >= 0 && !given.value[i])
  if (empties.length === 0) return
  const pick = empties[Math.floor(Math.random() * empties.length)]
  grid.value = grid.value.map((x, k) => (k === pick ? solution.value[k] : x))
  hintsUsed.value += 1
  selected.value = pick
  sfx.star()
  nextTick(() => pop(cellRefs.value[pick], { scale: 1.25 }))
}

function onSolved() {
  solved.value = true
  clearInterval(timer)
  const stars = Math.max(1, 4 - hintsUsed.value - Math.floor(mistakes.value / 3))
  progress.bumpCounter('sudokuSolved')
  progress.addStars(stars)
  progress.finishSession('sudoku', {
    correct: N * N - given.value.filter(Boolean).length,
    total: N * N - given.value.filter(Boolean).length,
  })
  lastStars.value = stars
  fxCorrect(boardEl.value)
  burst(boardEl.value, { count: 30 })
  flyStar(boardEl.value)
}

watch(complete, (v) => {
  if (v && !solved.value) onSolved()
})

watch(level, newPuzzle)

function bindCell(el, i) {
  cellRefs.value[i] = el || null
}

function onKey(e) {
  if (/^[1-4]$/.test(e.key)) place(Number(e.key))
  else if (e.key === 'Backspace' || e.key === 'Delete') erase()
}

onMounted(() => {
  newPuzzle()
  timer = setInterval(() => {
    if (!solved.value) elapsed.value = Date.now() - startedAt.value
  }, 500)
  window.addEventListener('keydown', onKey)
})

onBeforeUnmount(() => {
  clearInterval(timer)
  window.removeEventListener('keydown', onKey)
})

const rowOf = (i) => Math.floor(i / N)
const colOf = (i) => i % N

function isPeer(i) {
  if (selected.value === null) return false
  const s = selected.value
  return (
    rowOf(i) === rowOf(s) ||
    colOf(i) === colOf(s) ||
    (Math.floor(rowOf(i) / 2) === Math.floor(rowOf(s) / 2) &&
      Math.floor(colOf(i) / 2) === Math.floor(colOf(s) / 2))
  )
}
</script>

<template>
  <main class="page stack">
    <section class="panel head-panel">
      <MascotBot :mood="solved ? 'cheer' : 'think'" :size="70" />
      <div class="head-text">
        <h2 class="prompt">每一行、每一列、每个小方格里，1–4 只能出现一次</h2>
        <p class="dim tip">⏱ {{ timeLabel }} · 已填 {{ filledCount }}/16 · 提示 {{ hintsUsed }} 次</p>
      </div>
      <div class="toggles">
        <div class="group">
          <button
            v-for="l in [
              { id: 'easy', label: '简单' },
              { id: 'normal', label: '普通' },
              { id: 'hard', label: '挑战' },
            ]"
            :key="l.id"
            class="chip"
            :class="{ 'chip-on': level === l.id }"
            @click="level = l.id"
          >
            {{ l.label }}
          </button>
        </div>
        <button class="chip" @click="skin = skin === 'number' ? 'emoji' : 'number'">
          {{ skin === 'number' ? '🔢 数字' : '🚀 图案' }}
        </button>
      </div>
    </section>

    <section class="board-wrap">
      <div ref="boardEl" class="board">
        <button
          v-for="(v, i) in grid"
          :key="i"
          :ref="(el) => bindCell(el, i)"
          class="cell"
          :class="{
            given: given[i],
            selected: selected === i,
            peer: isPeer(i) && selected !== i,
            bad: badCells.has(i),
            'edge-right': colOf(i) === 1,
            'edge-bottom': rowOf(i) === 1,
          }"
          @click="selectCell(i)"
        >
          <span v-if="v" class="val" :class="{ 'emoji-val': skin === 'emoji' }">
            {{ symbols[v - 1] }}
          </span>
        </button>
      </div>

      <div class="side">
        <div class="pad">
          <button
            v-for="(sym, k) in symbols"
            :key="sym"
            class="pad-key"
            :class="{ done: usedUp[k + 1] === 4 }"
            :disabled="selected === null || solved"
            @click="place(k + 1)"
          >
            {{ sym }}
          </button>
        </div>
        <div class="side-actions">
          <button class="btn btn-ghost btn-sm" :disabled="selected === null || solved" @click="erase">
            🧽 擦除
          </button>
          <button class="btn btn-warm btn-sm" :disabled="solved" @click="hint">💡 提示</button>
          <button class="btn btn-ghost btn-sm" @click="newPuzzle">🔄 换一题</button>
        </div>
        <p v-if="mistakes > 0" class="dim small">小错误 {{ mistakes }} 次，别灰心！</p>
      </div>
    </section>

    <RoundSummary
      v-if="solved"
      :correct="1"
      :total="1"
      :stars-earned="lastStars"
      module-name="数独空间站"
      @replay="newPuzzle"
      @home="router.push('/')"
    />
  </main>
</template>

<style scoped>
.head-panel {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.head-text {
  flex: 1;
  min-width: 220px;
}

.prompt {
  font-size: clamp(16px, 2.8vw, 21px);
  font-weight: 900;
}

.tip {
  font-size: 12px;
  margin-top: 4px;
}

.toggles {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
}

.group {
  display: flex;
  gap: 6px;
}

.toggles .chip {
  cursor: pointer;
}

.board-wrap {
  display: flex;
  gap: 24px;
  align-items: flex-start;
  justify-content: center;
  flex-wrap: wrap;
}

.board {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px;
  padding: 12px;
  border-radius: var(--radius-l);
  background: linear-gradient(160deg, rgba(37, 46, 108, 0.92), rgba(16, 21, 60, 0.92));
  border: 1px solid rgba(140, 158, 255, 0.24);
  box-shadow: var(--shadow-card);
  width: min(92vw, 380px);
}

.cell {
  aspect-ratio: 1;
  display: grid;
  place-items: center;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.05);
  border: 2px solid rgba(255, 255, 255, 0.08);
  font-size: clamp(24px, 7vw, 38px);
  font-weight: 900;
  transition: all 0.16s ease;
}

.cell.edge-right {
  margin-right: 6px;
}

.cell.edge-bottom {
  margin-bottom: 6px;
}

.cell.given {
  background: rgba(155, 140, 255, 0.22);
  border-color: rgba(155, 140, 255, 0.4);
  color: var(--ink);
  cursor: default;
}

.cell:not(.given) .val {
  color: var(--cyan);
}

.cell.peer {
  background: rgba(255, 255, 255, 0.09);
}

.cell.selected {
  border-color: var(--gold);
  background: rgba(255, 206, 77, 0.18);
  box-shadow: 0 0 18px rgba(255, 206, 77, 0.35);
}

.cell.bad {
  border-color: var(--red);
  background: rgba(255, 107, 125, 0.2);
}

.cell.bad .val {
  color: var(--red);
}

.emoji-val {
  font-size: 0.82em;
}

.side {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
}

.pad {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
}

.pad-key {
  width: 78px;
  height: 78px;
  border-radius: 20px;
  font-size: 32px;
  font-weight: 900;
  background: linear-gradient(140deg, rgba(94, 231, 255, 0.24), rgba(155, 140, 255, 0.2));
  border: 2px solid rgba(94, 231, 255, 0.4);
  transition: transform 0.12s ease;
}

.pad-key:hover:not(:disabled) {
  transform: translateY(-3px);
}

.pad-key.done {
  opacity: 0.35;
}

.side-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.small {
  font-size: 12px;
}

@media (max-width: 700px) {
  .board-wrap {
    flex-direction: column;
    align-items: center;
  }

  .side {
    width: min(92vw, 380px);
  }

  .pad {
    grid-template-columns: repeat(4, 1fr);
    width: 100%;
  }

  .pad-key {
    width: 100%;
    height: 62px;
  }

  .side-actions {
    flex-direction: row;
  }
}
</style>
