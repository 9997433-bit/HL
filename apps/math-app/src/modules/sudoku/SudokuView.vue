<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import gsap from 'gsap'
import MascotBot from '@/components/MascotBot.vue'
import { useProgressStore } from '@/stores/progress.js'
import { useFeedback } from '@/composables/useFeedback'
import { conflictsOf, generatePuzzle, nextHint } from '@/utils/sudoku4'
import { sound } from '@/core/audio/sound.js'

const MODULE_ID = 'sudoku'
const DIFFICULTIES = [
  { id: 'easy', label: '简单', clues: 9, emoji: '🌱', stars: 3 },
  { id: 'normal', label: '普通', clues: 7, emoji: '🔥', stars: 4 },
  { id: 'hard', label: '挑战', clues: 5, emoji: '🚀', stars: 6 },
]

const router = useRouter()
const progress = useProgressStore()
const { correct: fxCorrect, wrong: fxWrong, burst, flyStar, pop } = useFeedback()

const difficulty = ref('easy')
const puzzle = ref([])
const solution = ref([])
const grid = ref([])
const selected = ref(null)
const mistakes = ref(0)
const hintsUsed = ref(0)
const solved = ref(false)
const seconds = ref(0)
const mood = ref('idle')
const message = ref('每一行、每一列、每一个 2×2 宫里，1–4 都只能出现一次。')
const boardRef = ref(null)
const solvedCount = ref(0)

let timer = null

const config = computed(() => DIFFICULTIES.find((d) => d.id === difficulty.value) ?? DIFFICULTIES[0])
const givens = computed(() => puzzle.value.map((v) => v !== 0))
const filledCount = computed(() => grid.value.filter((v) => v !== 0).length)

/** 每个格子的冲突状态，用于红色高亮。 */
const conflictSet = computed(() => {
  const set = new Set()
  grid.value.forEach((v, i) => {
    if (!v) return
    if (conflictsOf(grid.value, i).length) {
      set.add(i)
      conflictsOf(grid.value, i).forEach((p) => set.add(p))
    }
  })
  return set
})

const selectedValue = computed(() =>
  selected.value === null ? 0 : grid.value[selected.value] ?? 0,
)

/** 某个数字是否已经在盘面上用满 4 次。 */
function usedUp(n) {
  return grid.value.filter((v) => v === n).length >= 4
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
  const { puzzle: p, solution: s } = generatePuzzle(config.value.clues)
  puzzle.value = p
  solution.value = s
  grid.value = [...p]
  selected.value = null
  mistakes.value = 0
  hintsUsed.value = 0
  solved.value = false
  mood.value = 'idle'
  message.value = '每一行、每一列、每一个 2×2 宫里，1–4 都只能出现一次。'
  startTimer()
  requestAnimationFrame(() => {
    gsap.fromTo(
      '.cell',
      { opacity: 0, scale: 0.6 },
      { opacity: 1, scale: 1, duration: 0.3, stagger: 0.02, ease: 'back.out(2)' },
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
  if (solved.value || selected.value === null) return
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
    progress.recordAnswer(MODULE_ID, false, { skill: 'sudoku-4' })
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

  const base = config.value.stars
  const penalty = Math.min(base - 1, hintsUsed.value + Math.floor(mistakes.value / 2))
  const stars = Math.max(1, base - penalty)

  progress.recordAnswer(MODULE_ID, true, { skill: 'sudoku-4', stars, xp: 20 + base * 4 })
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
    '.cell',
    { scale: 1 },
    { scale: 1.12, duration: 0.22, yoyo: true, repeat: 1, stagger: { each: 0.03, from: 'center' } },
  )
}

function restart() {
  sound.click()
  grid.value = [...puzzle.value]
  selected.value = null
  solved.value = false
  message.value = '清空重来，慢慢想 🙂'
}

function setDifficulty(id) {
  if (difficulty.value === id) return
  sound.click()
  difficulty.value = id
}

function onKeydown(e) {
  if (/^[1-4]$/.test(e.key)) place(Number(e.key))
  else if (e.key === 'Backspace' || e.key === 'Delete' || e.key === '0') erase()
  else if (selected.value !== null) {
    const r = Math.floor(selected.value / 4)
    const c = selected.value % 4
    if (e.key === 'ArrowUp' && r > 0) selected.value -= 4
    else if (e.key === 'ArrowDown' && r < 3) selected.value += 4
    else if (e.key === 'ArrowLeft' && c > 0) selected.value -= 1
    else if (e.key === 'ArrowRight' && c < 3) selected.value += 1
  }
}

watch(difficulty, newGame)

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
    <section class="panel controls">
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
      <span class="chip">🔢 {{ filledCount }}/16</span>
    </section>

    <section class="panel stage">
      <header class="stage-head">
        <MascotBot :mood="mood" :size="72" />
        <p class="muted say">{{ message }}</p>
      </header>

      <div class="board-wrap">
        <div ref="boardRef" class="board" role="grid" aria-label="4×4 数独">
          <button
            v-for="(v, i) in grid"
            :key="i"
            class="cell"
            :class="{
              given: givens[i],
              sel: selected === i,
              peer:
                selected !== null &&
                (Math.floor(selected / 4) === Math.floor(i / 4) ||
                  selected % 4 === i % 4 ||
                  (Math.floor(Math.floor(selected / 4) / 2) === Math.floor(Math.floor(i / 4) / 2) &&
                    Math.floor((selected % 4) / 2) === Math.floor((i % 4) / 2))),
              same: v !== 0 && v === selectedValue,
              bad: conflictSet.has(i),
              'edge-right': i % 4 === 1,
              'edge-bottom': Math.floor(i / 4) === 1,
            }"
            :aria-label="`第${Math.floor(i / 4) + 1}行第${(i % 4) + 1}列 ${v || '空'}`"
            @click="selectCell(i)"
          >
            {{ v || '' }}
          </button>
        </div>
      </div>

      <div class="pad">
        <button
          v-for="n in 4"
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
        <button class="btn btn-ghost btn-sm" :disabled="solved" @click="useHint">
          💡 提示（-1⭐）
        </button>
        <button class="btn btn-ghost btn-sm" :disabled="solved" @click="restart">🔄 重来这局</button>
        <button class="btn btn-primary" @click="newGame">
          {{ solved ? '🧩 下一局' : '🎲 换一局' }}
        </button>
        <button class="btn btn-ghost btn-sm" @click="router.push('/')">🗺️ 回到地图</button>
      </div>

      <p v-if="solvedCount" class="dim tiny">本次进入空间站已完成 {{ solvedCount }} 局</p>
    </section>

    <section class="panel rules">
      <h3 class="panel-title">🧠 玩法说明</h3>
      <ul class="rule-list muted">
        <li>棋盘是 4×4，被粗线分成 4 个 2×2 的「宫」。</li>
        <li>每一行、每一列、每一个宫里，数字 1、2、3、4 都只能出现一次。</li>
        <li>点一个空格，再点下面的数字就能填入；再点一次同样的数字可以取消。</li>
        <li>也可以用键盘 1–4 填数、方向键移动、退格键擦除。</li>
        <li>填错会有提示，但不会强制清除，可以自己发现并改正。</li>
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
  color: var(--ink-soft);
  transition: all 0.16s ease;
}

.seg-btn.on {
  background: linear-gradient(135deg, var(--violet), var(--pink));
  color: #12082a;
  box-shadow: 0 6px 16px rgba(155, 140, 255, 0.34);
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
  border-radius: var(--radius-m);
  background:
    radial-gradient(70% 70% at 50% 0%, rgba(155, 140, 255, 0.18), transparent 70%),
    rgba(6, 9, 30, 0.5);
  border: 1px solid rgba(155, 140, 255, 0.3);
}

.board {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 4px;
  width: min(84vw, 340px);
}

.cell {
  aspect-ratio: 1;
  display: grid;
  place-items: center;
  font-size: clamp(24px, 8vw, 36px);
  font-weight: 900;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.07);
  border: 2px solid rgba(255, 255, 255, 0.1);
  color: var(--cyan);
  transition: all 0.14s ease;
}

.cell.given {
  background: rgba(255, 255, 255, 0.14);
  color: var(--ink);
  cursor: default;
}

.cell.peer {
  background: rgba(155, 140, 255, 0.12);
}

.cell.same {
  box-shadow: inset 0 0 0 2px rgba(255, 206, 77, 0.6);
}

.cell.sel {
  border-color: var(--gold);
  background: rgba(255, 206, 77, 0.18);
  box-shadow: 0 0 20px rgba(255, 206, 77, 0.45);
}

.cell.bad {
  color: var(--red);
  border-color: var(--red);
  background: rgba(255, 107, 125, 0.16);
}

/* 2×2 宫的分隔线 */
.cell.edge-right {
  margin-right: 5px;
}

.cell.edge-bottom {
  margin-bottom: 5px;
}

.pad {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: center;
}

.numkey {
  width: 62px;
  height: 62px;
  font-size: 28px;
  font-weight: 900;
  border-radius: var(--radius-s);
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
  color: var(--violet);
  font-weight: 900;
}
</style>
