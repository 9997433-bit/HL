<script setup>
/**
 * 数独空间站 — 4×4 / 6×6 / 9×9 三档棋盘。
 * 三档共用 core/engine/sudoku.js 一套引擎：随机回溯生成完整盘 → 挖洞 →
 * 每挖一格用解计数器验证唯一解，所以任何档位的题目都保证有且只有一个答案。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import gsap from 'gsap'
import MascotBot from '@/components/MascotBot.vue'
import { useProgressStore } from '@/stores/progress.js'
import { useFeedback } from '@/composables/useFeedback'
import {
  candidatesOf,
  conflictsOf,
  generateSudoku,
  nextHint,
  specOf,
} from '@/core/engine/sudoku.js'
import { sound } from '@/utils/sound'

const MODULE_ID = 'sudoku'

/** 每档的挖洞数是实测出来的：9×9 挖到 52 洞时生成仍在 100ms 内，再多就明显卡顿。 */
const BOARDS = [
  {
    key: 4,
    label: '4×4',
    emoji: '🐣',
    desc: '2×2 宫，数字 1–4',
    holes: { easy: 7, normal: 9, hard: 11 },
    baseStars: 3,
  },
  {
    key: 6,
    label: '6×6',
    emoji: '🦊',
    desc: '3×2 宫，数字 1–6',
    holes: { easy: 16, normal: 20, hard: 24 },
    baseStars: 5,
  },
  {
    key: 9,
    label: '9×9',
    emoji: '🚀',
    desc: '3×3 宫，数字 1–9（标准数独）',
    holes: { easy: 38, normal: 46, hard: 52 },
    baseStars: 8,
  },
]

const DIFFICULTIES = [
  { id: 'easy', label: '简单', emoji: '🌱', bonus: 0 },
  { id: 'normal', label: '普通', emoji: '🔥', bonus: 1 },
  { id: 'hard', label: '挑战', emoji: '⚡', bonus: 3 },
]

const router = useRouter()
const progress = useProgressStore()
const { correct: fxCorrect, wrong: fxWrong, burst, flyStar, pop } = useFeedback()

const sizeKey = ref(4)
const difficulty = ref('easy')
const showNotes = ref(false)

const puzzle = ref([])
const solution = ref([])
const grid = ref([])
const selected = ref(null)
const mistakes = ref(0)
const hintsUsed = ref(0)
const solved = ref(false)
const seconds = ref(0)
const mood = ref('idle')
const message = ref('')
const boardRef = ref(null)
const solvedCount = ref(0)

let timer = null

const board = computed(() => BOARDS.find((b) => b.key === sizeKey.value) ?? BOARDS[0])
const tier = computed(() => DIFFICULTIES.find((d) => d.id === difficulty.value) ?? DIFFICULTIES[0])
const spec = computed(() => specOf(sizeKey.value))
const size = computed(() => spec.value.size)
const total = computed(() => size.value * size.value)
const skillId = computed(() => `sudoku-${sizeKey.value}`)

const givens = computed(() => puzzle.value.map((v) => v !== 0))
const filledCount = computed(() => grid.value.filter((v) => v !== 0).length)
const selectedValue = computed(() =>
  selected.value === null ? 0 : (grid.value[selected.value] ?? 0),
)

const intro = computed(
  () => `每一行、每一列、每一个 ${spec.value.boxW}×${spec.value.boxH} 宫里，1–${size.value} 都只能出现一次。`,
)

/** 冲突格集合，用于红色高亮。 */
const conflictSet = computed(() => {
  const set = new Set()
  grid.value.forEach((v, i) => {
    if (!v) return
    const bad = conflictsOf(grid.value, spec.value, i)
    if (bad.length) {
      set.add(i)
      bad.forEach((p) => set.add(p))
    }
  })
  return set
})

/** 候选数笔记：默认关闭，打开后在空格里列出这一格还能填哪些数。 */
const notes = computed(() => {
  if (!showNotes.value) return []
  return grid.value.map((v, i) => (v ? [] : candidatesOf(grid.value, spec.value, i)))
})

/** 某个数字是否已经在盘面上用满 size 次。 */
function usedUp(n) {
  return grid.value.filter((v) => v === n).length >= size.value
}

function peerOf(i) {
  if (selected.value === null) return false
  const { boxW, boxH } = spec.value
  const s = size.value
  const sr = Math.floor(selected.value / s)
  const sc = selected.value % s
  const r = Math.floor(i / s)
  const c = i % s
  return (
    sr === r ||
    sc === c ||
    (Math.floor(sr / boxH) === Math.floor(r / boxH) && Math.floor(sc / boxW) === Math.floor(c / boxW))
  )
}

const timeText = computed(() => {
  const m = Math.floor(seconds.value / 60)
  const s = seconds.value % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

function startTimer() {
  stopTimer()
  seconds.value = 0
  timer = setInterval(() => {
    if (!solved.value) seconds.value += 1
  }, 1000)
}

function stopTimer() {
  if (timer) clearInterval(timer)
  timer = null
}

function newGame() {
  const { puzzle: p, solution: s } = generateSudoku(sizeKey.value, board.value.holes[difficulty.value])
  puzzle.value = p
  solution.value = s
  grid.value = [...p]
  selected.value = null
  mistakes.value = 0
  hintsUsed.value = 0
  solved.value = false
  mood.value = 'idle'
  message.value = intro.value
  startTimer()
  requestAnimationFrame(() => {
    gsap.fromTo(
      boardRef.value?.querySelectorAll('.cell') ?? [],
      { opacity: 0, scale: 0.6 },
      {
        opacity: 1,
        scale: 1,
        duration: 0.3,
        stagger: Math.min(0.02, 1.2 / total.value),
        ease: 'back.out(2)',
      },
    )
  })
}

function selectCell(i) {
  if (solved.value || givens.value[i]) {
    if (givens.value[i]) selected.value = i
    return
  }
  sound.click()
  selected.value = i
}

function place(n) {
  if (solved.value || selected.value === null || n > size.value) return
  const i = selected.value
  if (givens.value[i]) return

  if (grid.value[i] === n) {
    grid.value[i] = 0
    sound.click()
    return
  }

  grid.value[i] = n
  const cellEl = boardRef.value?.querySelectorAll('.cell')[i]

  if (solution.value[i] !== n) {
    mistakes.value += 1
    progress.recordAnswer(MODULE_ID, false, { skill: skillId.value, errorTags: ['wrong-op'] })
    fxWrong(cellEl)
    mood.value = 'sad'
    message.value = '这个数字在这一行、列或宫里重复啦，再想想～'
    return
  }

  sound.star()
  pop(cellEl)
  mood.value = 'happy'
  message.value = '填对了，继续！'
  checkSolved(cellEl)
}

function erase() {
  if (solved.value || selected.value === null) return
  const i = selected.value
  if (givens.value[i]) return
  sound.click()
  grid.value[i] = 0
}

function useHint() {
  if (solved.value) return
  const hint = nextHint(grid.value, solution.value)
  if (!hint) return
  hintsUsed.value += 1
  grid.value[hint.index] = hint.value
  selected.value = hint.index
  sound.combo()
  const cellEl = boardRef.value?.querySelectorAll('.cell')[hint.index]
  pop(cellEl, { scale: 1.25 })
  message.value = `机器人帮你填了一个 ${hint.value}（已用提示 ${hintsUsed.value} 次）`
  checkSolved(cellEl)
}

function checkSolved(anchor) {
  if (grid.value.some((v, i) => v !== solution.value[i])) return
  solved.value = true
  stopTimer()
  solvedCount.value += 1
  mood.value = 'cheer'

  const base = board.value.baseStars + tier.value.bonus
  const penalty = Math.min(base - 1, hintsUsed.value + Math.floor(mistakes.value / 2))
  const stars = Math.max(1, base - penalty)

  progress.recordAnswer(MODULE_ID, true, { skill: skillId.value, stars, xp: 20 + base * 4 })
  progress.bumpCounter('sudokuSolved')
  progress.finishSession(MODULE_ID, {
    correct: 1,
    total: 1,
    bonusStars: mistakes.value === 0 && hintsUsed.value === 0 ? 2 : 0,
  })

  fxCorrect(boardRef.value)
  burst(boardRef.value, { count: 30 })
  flyStar(anchor ?? boardRef.value)
  message.value =
    mistakes.value === 0 && hintsUsed.value === 0
      ? `完美通关！用时 ${timeText.value}，一次都没错 🎉`
      : `解开啦！用时 ${timeText.value}，错了 ${mistakes.value} 次。`
  gsap.fromTo(
    boardRef.value?.querySelectorAll('.cell') ?? [],
    { scale: 1 },
    {
      scale: 1.12,
      duration: 0.22,
      yoyo: true,
      repeat: 1,
      stagger: { each: Math.min(0.03, 1.5 / total.value), from: 'center' },
    },
  )
}

function restart() {
  sound.click()
  grid.value = [...puzzle.value]
  selected.value = null
  solved.value = false
  message.value = '清空重来，慢慢想 🙂'
}

function setSize(key) {
  if (sizeKey.value === key) return
  sound.click()
  sizeKey.value = key
}

function setDifficulty(id) {
  if (difficulty.value === id) return
  sound.click()
  difficulty.value = id
}

function toggleNotes() {
  sound.click()
  showNotes.value = !showNotes.value
}

function onKeydown(e) {
  const n = Number(e.key)
  if (Number.isInteger(n) && n >= 1 && n <= size.value) place(n)
  else if (e.key === 'Backspace' || e.key === 'Delete' || e.key === '0') erase()
  else if (selected.value !== null) {
    const s = size.value
    const r = Math.floor(selected.value / s)
    const c = selected.value % s
    if (e.key === 'ArrowUp' && r > 0) selected.value -= s
    else if (e.key === 'ArrowDown' && r < s - 1) selected.value += s
    else if (e.key === 'ArrowLeft' && c > 0) selected.value -= 1
    else if (e.key === 'ArrowRight' && c < s - 1) selected.value += 1
  }
}

watch([sizeKey, difficulty], newGame)

onMounted(() => {
  newGame()
  window.addEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => {
  stopTimer()
  window.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <main class="page stack">
    <section class="card controls">
      <div class="seg" role="group" aria-label="棋盘档位">
        <button
          v-for="b in BOARDS"
          :key="b.key"
          class="seg-btn"
          :class="{ on: sizeKey === b.key }"
          :title="b.desc"
          @click="setSize(b.key)"
        >
          {{ b.emoji }} {{ b.label }}
        </button>
      </div>
      <div class="seg" role="group" aria-label="难度">
        <button
          v-for="d in DIFFICULTIES"
          :key="d.id"
          class="seg-btn"
          :class="{ on: difficulty === d.id }"
          @click="setDifficulty(d.id)"
        >
          {{ d.emoji }} {{ d.label }}
        </button>
      </div>
      <div class="spacer" />
      <span class="chip">⏱️ {{ timeText }}</span>
      <span class="chip">❌ {{ mistakes }}</span>
      <span class="chip">🔢 {{ filledCount }}/{{ total }}</span>
    </section>

    <section class="card stage">
      <header class="stage-head">
        <MascotBot :mood="mood" :size="72" />
        <p class="muted say">{{ message }}</p>
      </header>

      <div class="board-wrap">
        <div
          ref="boardRef"
          class="board"
          :class="`s${sizeKey}`"
          role="group"
          :aria-label="`${size}×${size} 数独`"
          :style="{ gridTemplateColumns: `repeat(${size}, 1fr)` }"
        >
          <button
            v-for="(v, i) in grid"
            :key="i"
            class="cell"
            :class="{
              given: givens[i],
              sel: selected === i,
              peer: peerOf(i),
              same: v !== 0 && v === selectedValue,
              bad: conflictSet.has(i),
              'edge-right': (i % size) % spec.boxW === spec.boxW - 1 && i % size !== size - 1,
              'edge-bottom':
                Math.floor(i / size) % spec.boxH === spec.boxH - 1 &&
                Math.floor(i / size) !== size - 1,
            }"
            :aria-label="`第${Math.floor(i / size) + 1}行第${(i % size) + 1}列 ${v || '空'}`"
            @click="selectCell(i)"
          >
            <template v-if="v">{{ v }}</template>
            <span v-else-if="notes[i]?.length" class="notes">
              <i v-for="n in notes[i]" :key="n">{{ n }}</i>
            </span>
          </button>
        </div>
      </div>

      <div class="pad">
        <button
          v-for="n in size"
          :key="n"
          class="numkey"
          :class="{ done: usedUp(n) }"
          :disabled="solved || selected === null || givens[selected]"
          @click="place(n)"
        >
          {{ n }}
        </button>
        <button
          class="numkey erase"
          :disabled="solved || selected === null || givens[selected]"
          @click="erase"
        >
          ⌫
        </button>
      </div>

      <div class="actions">
        <button class="btn btn--ghost btn--sm" :disabled="solved" @click="useHint">
          💡 提示（-1⭐）
        </button>
        <button class="btn btn--ghost btn--sm" :class="{ 'btn-on': showNotes }" @click="toggleNotes">
          {{ showNotes ? '✏️ 关闭候选数' : '✏️ 候选数笔记' }}
        </button>
        <button class="btn btn--ghost btn--sm" :disabled="solved" @click="restart">🔄 重来这局</button>
        <button class="btn btn--primary" @click="newGame">
          {{ solved ? '🧩 下一局' : '🎲 换一局' }}
        </button>
        <button class="btn btn--ghost btn--sm" @click="router.push('/')">🗺️ 回到地图</button>
      </div>

      <p v-if="solvedCount" class="dim tiny">本次进入空间站已完成 {{ solvedCount }} 局</p>
    </section>

    <section class="card rules">
      <h3 class="panel-title">🧠 玩法说明</h3>
      <ul class="rule-list muted">
        <li>当前是 {{ board.label }} 棋盘：{{ board.desc }}。</li>
        <li>每一行、每一列、每一个宫里，数字都只能出现一次。</li>
        <li>点一个空格，再点下面的数字就能填入；再点一次同样的数字可以取消。</li>
        <li>也可以用键盘 1–{{ size }} 填数、方向键移动、退格键擦除。</li>
        <li>卡住时打开「候选数笔记」，空格里会列出这一格还能填哪些数。</li>
        <li>每道题都通过唯一解校验，一定能凭推理填出来，不需要猜。</li>
      </ul>
    </section>
  </main>
</template>

<style scoped>
.controls {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  padding: 14px 18px;
}

.seg {
  display: flex;
  gap: 4px;
  padding: 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.seg-btn {
  padding: 7px 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 800;
  color: var(--text);
  transition: all 0.16s ease;
  white-space: nowrap;
}

.seg-btn.on {
  background: linear-gradient(135deg, var(--accent), var(--neon-pink));
  color: var(--text-invert);
  box-shadow: 0 6px 16px rgba(155, 140, 255, 0.34);
}

.btn-on {
  background: rgba(155, 140, 255, 0.28);
  border-color: rgba(155, 140, 255, 0.6);
}

.stage {
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-items: center;
}

.stage-head {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  align-self: stretch;
}

.say {
  font-size: 14px;
  flex: 1;
  min-width: 200px;
}

.board-wrap {
  padding: 12px;
  border-radius: var(--radius-md);
  background:
    radial-gradient(70% 70% at 50% 0%, rgba(155, 140, 255, 0.18), transparent 70%),
    rgba(6, 9, 30, 0.5);
  border: 1px solid rgba(155, 140, 255, 0.3);
}

.board {
  display: grid;
  gap: 3px;
  width: min(88vw, 340px);
}

.board.s6 {
  width: min(90vw, 420px);
}

.board.s9 {
  width: min(92vw, 520px);
  gap: 2px;
}

.cell {
  aspect-ratio: 1;
  display: grid;
  place-items: center;
  font-size: clamp(22px, 7vw, 34px);
  font-weight: 900;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.07);
  border: 2px solid rgba(255, 255, 255, 0.1);
  color: var(--brand);
  transition: background 0.14s ease, border-color 0.14s ease, box-shadow 0.14s ease;
}

.board.s6 .cell {
  font-size: clamp(18px, 5vw, 28px);
  border-radius: 8px;
}

.board.s9 .cell {
  font-size: clamp(13px, 3.4vw, 24px);
  border-radius: 6px;
  border-width: 1px;
}

.cell.given {
  background: rgba(255, 255, 255, 0.14);
  color: var(--text-strong);
  cursor: default;
}

.cell.peer {
  background: rgba(155, 140, 255, 0.12);
}

.cell.same {
  box-shadow: inset 0 0 0 2px rgba(255, 206, 77, 0.6);
}

.cell.sel {
  border-color: var(--star);
  background: rgba(255, 206, 77, 0.18);
  box-shadow: 0 0 20px rgba(255, 206, 77, 0.45);
}

.cell.bad {
  color: var(--danger);
  border-color: var(--danger);
  background: rgba(255, 107, 125, 0.16);
}

/* 宫的分隔线 */
.cell.edge-right {
  margin-right: 5px;
}

.cell.edge-bottom {
  margin-bottom: 5px;
}

.notes {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 1px 3px;
  padding: 2px;
  line-height: 1;
}

.notes i {
  font-size: clamp(8px, 1.6vw, 11px);
  font-style: normal;
  font-weight: 700;
  color: var(--text-soft);
}

.pad {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
}

.numkey {
  width: 56px;
  height: 56px;
  font-size: 26px;
  font-weight: 900;
  border-radius: var(--radius-sm);
  background: linear-gradient(160deg, rgba(155, 140, 255, 0.24), rgba(94, 231, 255, 0.18));
  border: 2px solid rgba(155, 140, 255, 0.45);
  transition: transform 0.12s ease, box-shadow 0.12s ease;
}

.numkey:hover:not(:disabled) {
  transform: translateY(-3px);
  box-shadow: 0 10px 22px rgba(155, 140, 255, 0.3);
}

.numkey.done {
  opacity: 0.45;
}

.numkey.erase {
  font-size: 22px;
  background: rgba(255, 255, 255, 0.07);
  border-color: rgba(255, 255, 255, 0.18);
}

.actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: center;
}

.tiny {
  font-size: 12px;
}

.rules {
  align-self: stretch;
}

.rule-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 10px;
  font-size: 14px;
  line-height: 1.5;
}

.rule-list li::before {
  content: '· ';
  color: var(--accent);
  font-weight: 900;
}

@media (max-width: 560px) {
  .numkey {
    width: 48px;
    height: 48px;
    font-size: 22px;
  }
}
</style>
