<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import gsap from 'gsap'
import MascotBot from '@/components/MascotBot.vue'
import SessionBar from '@/components/SessionBar.vue'
import RoundSummary from '@/components/RoundSummary.vue'
import { useProgressStore } from '@/stores/progress.js'
import { useFeedback } from '@/composables/useFeedback'
import { numericOptions, randInt, sample } from '@/utils/random'
import { sound } from '@/utils/sound'

const ROUND_SIZE = 10
const MODULE_ID = 'arithmetic'
const SPEED_BONUS_MS = 6000

const router = useRouter()
const progress = useProgressStore()
const { correct: fxCorrect, wrong: fxWrong, burst, flyStar, pop, enter } = useFeedback()

const LEVELS = [
  { id: 10, label: '10 以内', emoji: '🌱', desc: '入门：一位数加减' },
  { id: 20, label: '20 以内', emoji: '🔥', desc: '进阶：进位与退位' },
  { id: 100, label: '100 以内', emoji: '🚀', desc: '挑战：两位数加减' },
]
const OPS = [
  { id: 'add', label: '加法 +' },
  { id: 'sub', label: '减法 −' },
  { id: 'mix', label: '混合 ±' },
]

const level = ref(10)
const op = ref('mix')
const inputMode = ref('choice') // choice | keypad

const questions = ref([])
const index = ref(0)
const marks = ref([])
const correctCount = ref(0)
const starsEarned = ref(0)
const showSummary = ref(false)
const locked = ref(false)
const chosen = ref(null)
const typed = ref('')
const mood = ref('idle')
const message = ref('算一算，答案是多少？')
const showHint = ref(false)
const questionStart = ref(0)
const fastAnswers = ref(0)

const stageRef = ref(null)
const equationRef = ref(null)

const current = computed(() => questions.value[index.value] ?? null)
const isHard = computed(() => level.value === 100)

function makeQuestion() {
  const max = level.value
  const kind = op.value === 'mix' ? sample(['add', 'sub']) : op.value

  if (kind === 'add') {
    let a
    let b
    if (max === 100) {
      a = randInt(10, 89)
      b = randInt(2, 100 - a)
    } else {
      a = randInt(1, max - 1)
      b = randInt(1, max - a)
    }
    return { a, b, kind, sign: '+', answer: a + b }
  }

  let a
  let b
  if (max === 100) {
    a = randInt(20, 99)
    b = randInt(2, a - 1)
  } else {
    a = randInt(2, max)
    b = randInt(1, a)
  }
  return { a, b, kind, sign: '−', answer: a - b }
}

function buildQuestion() {
  const q = makeQuestion()
  q.options = numericOptions(q.answer, {
    count: 4,
    spread: level.value === 100 ? 9 : 3,
    min: 0,
    max: level.value,
  })
  q.hint =
    q.kind === 'add'
      ? `从 ${q.a} 开始，往后数 ${q.b} 步。`
      : `从 ${q.a} 开始，往前数 ${q.b} 步。`
  return q
}

/* ---------- 数轴辅助 ---------- */

const numberLine = computed(() => {
  const q = current.value
  if (!q || level.value > 20) return null
  const max = level.value
  const from = q.a
  const to = q.answer
  return {
    max,
    ticks: Array.from({ length: max + 1 }, (_, i) => i),
    from,
    to,
    left: Math.min(from, to),
    width: Math.abs(to - from),
  }
})

/* ---------- 判题 ---------- */

/** 映射到 curriculum 技能点，让自适应掌握度引擎能收到反馈。 */
function skillOf(q) {
  if (level.value === 100) return 'add-within-100'
  if (level.value === 20) return q.kind === 'add' ? 'add-carry-20' : 'sub-borrow-20'
  return q.kind === 'add' ? 'add-within-10' : 'sub-within-10'
}

/**
 * 错因归类：个位相加过 10 却答错多半是忘进位，个位不够减则是忘退位。
 * 家长报告里按这些标签统计薄弱点。
 */
function errorTagsOf(q, answered) {
  const tags = []
  const onesA = q.a % 10
  const onesB = q.b % 10
  if (q.kind === 'add' && onesA + onesB >= 10) tags.push('carry')
  if (q.kind === 'sub' && onesA < onesB) tags.push('borrow')
  if (Math.abs(answered - q.answer) === 10) tags.push('off-by-ten')
  else if (Math.abs(answered - q.answer) === 1) tags.push('off-by-one')
  return tags
}

function grade(value, anchor) {
  const q = current.value
  const right = value === q.answer
  marks.value[index.value] = right ? 'ok' : 'no'
  const skill = skillOf(q)

  if (right) {
    const elapsed = Date.now() - questionStart.value
    const fast = elapsed < SPEED_BONUS_MS
    if (fast) fastAnswers.value += 1
    const stars = (isHard.value ? 2 : 1) + (fast ? 1 : 0)
    correctCount.value += 1
    starsEarned.value += stars
    progress.recordAnswer(MODULE_ID, true, {
      skill,
      stars,
      xp: isHard.value ? 18 : 10,
      tag: isHard.value ? 'arithmetic-hard' : undefined,
    })
    fxCorrect(anchor)
    burst(anchor, { count: isHard.value ? 22 : 16 })
    flyStar(anchor)
    mood.value = 'cheer'
    message.value = fast
      ? `又快又准！+${stars} ⭐`
      : sample(['答对啦！', '算得很好 👏', '完全正确 ✅'])
  } else {
    progress.recordAnswer(MODULE_ID, false, { skill, errorTags: errorTagsOf(q, value) })
    fxWrong(anchor)
    mood.value = 'sad'
    message.value = `${q.a} ${q.sign} ${q.b} = ${q.answer}，记住这一题哦。`
  }
  return right
}

function chooseOption(value, e) {
  if (locked.value) return
  locked.value = true
  chosen.value = value
  grade(value, e.currentTarget)
  setTimeout(next, 1400)
}

function submitTyped() {
  if (locked.value || typed.value === '') return
  locked.value = true
  const value = Number(typed.value)
  chosen.value = value
  grade(value, equationRef.value)
  setTimeout(next, 1400)
}

function tapKey(k) {
  if (locked.value) return
  sound.click()
  if (k === 'del') {
    typed.value = typed.value.slice(0, -1)
    return
  }
  if (typed.value.length >= 3) return
  typed.value = `${typed.value}${k}`
}

function next() {
  chosen.value = null
  typed.value = ''
  showHint.value = false
  locked.value = false
  mood.value = 'idle'
  if (index.value + 1 >= ROUND_SIZE) {
    finish()
    return
  }
  index.value += 1
  message.value = '算一算，答案是多少？'
  questionStart.value = Date.now()
  animateIn()
}

function finish() {
  const perfect = correctCount.value === ROUND_SIZE
  progress.finishSession(MODULE_ID, {
    correct: correctCount.value,
    total: ROUND_SIZE,
    bonusStars: perfect ? 4 : 0,
  })
  if (perfect) starsEarned.value += 4
  showSummary.value = true
}

function startRound() {
  questions.value = Array.from({ length: ROUND_SIZE }, buildQuestion)
  index.value = 0
  marks.value = []
  correctCount.value = 0
  starsEarned.value = 0
  fastAnswers.value = 0
  showSummary.value = false
  locked.value = false
  chosen.value = null
  typed.value = ''
  mood.value = 'idle'
  message.value = '算一算，答案是多少？'
  questionStart.value = Date.now()
  progress.resetCombo()
  animateIn()
}

function animateIn() {
  requestAnimationFrame(() => {
    if (equationRef.value) {
      gsap.fromTo(
        equationRef.value,
        { opacity: 0, scale: 0.9 },
        { opacity: 1, scale: 1, duration: 0.32, ease: 'back.out(2)' },
      )
    }
    enter([...document.querySelectorAll('.opt')], { stagger: 0.05, y: 14 })
  })
}

function setLevel(id) {
  if (level.value === id) return
  sound.click()
  level.value = id
}

function setOp(id) {
  if (op.value === id) return
  sound.click()
  op.value = id
}

function toggleMode() {
  sound.click()
  inputMode.value = inputMode.value === 'choice' ? 'keypad' : 'choice'
  pop(stageRef.value, { scale: 1.01 })
}

watch([level, op], startRound)

function onKeydown(e) {
  if (showSummary.value || inputMode.value !== 'keypad') return
  if (/^[0-9]$/.test(e.key)) tapKey(e.key)
  else if (e.key === 'Backspace') tapKey('del')
  else if (e.key === 'Enter') submitTyped()
}

onMounted(() => {
  startRound()
  window.addEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <main class="page stack">
    <section class="panel controls">
      <div class="seg" role="group" aria-label="难度">
        <button
          v-for="l in LEVELS"
          :key="l.id"
          class="seg-btn"
          :class="{ on: level === l.id }"
          :title="l.desc"
          @click="setLevel(l.id)"
        >
          {{ l.emoji }} {{ l.label }}
        </button>
      </div>
      <div class="seg" role="group" aria-label="运算类型">
        <button
          v-for="o in OPS"
          :key="o.id"
          class="seg-btn"
          :class="{ on: op === o.id }"
          @click="setOp(o.id)"
        >
          {{ o.label }}
        </button>
      </div>
      <button class="btn btn-ghost btn-sm" @click="toggleMode">
        {{ inputMode === 'choice' ? '⌨️ 改为输入' : '🔢 改为选择' }}
      </button>
    </section>

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
        <MascotBot :mood="mood" :size="72" />
        <p class="muted say">{{ message }}</p>
        <div class="spacer" />
        <span v-if="fastAnswers" class="chip">⚡ 秒答 {{ fastAnswers }}</span>
        <button class="btn btn-ghost btn-sm" @click="showHint = !showHint">💡 提示</button>
      </header>

      <div ref="equationRef" class="equation" :class="{ hard: isHard }">
        <span class="term">{{ current.a }}</span>
        <span class="sign">{{ current.sign }}</span>
        <span class="term">{{ current.b }}</span>
        <span class="sign">=</span>
        <span class="slot" :class="{ filled: typed !== '' }">
          {{ inputMode === 'keypad' ? typed || '?' : '?' }}
        </span>
      </div>

      <p v-if="showHint" class="hint">{{ current.hint }}</p>

      <!-- 数轴（10 / 20 以内） -->
      <div v-if="numberLine" class="numline" aria-hidden="true">
        <div class="nl-track">
          <span
            class="nl-span"
            :style="{
              left: `${(numberLine.left / numberLine.max) * 100}%`,
              width: `${(numberLine.width / numberLine.max) * 100}%`,
            }"
          />
          <span
            v-for="t in numberLine.ticks"
            :key="t"
            class="nl-tick"
            :class="{
              start: t === current.a,
              end: showHint && t === current.answer,
            }"
            :style="{ left: `${(t / numberLine.max) * 100}%` }"
          >
            <i class="nl-dot" />
            <em v-if="t % (numberLine.max > 10 ? 2 : 1) === 0" class="nl-label">{{ t }}</em>
          </span>
        </div>
      </div>

      <!-- 选择题 -->
      <div v-if="inputMode === 'choice'" class="options">
        <button
          v-for="o in current.options"
          :key="o"
          class="opt"
          :class="{
            right: locked && o === current.answer,
            bad: locked && chosen === o && o !== current.answer,
          }"
          :disabled="locked"
          @click="chooseOption(o, $event)"
        >
          {{ o }}
        </button>
      </div>

      <!-- 数字键盘 -->
      <div v-else class="keypad-wrap">
        <div class="keypad">
          <button
            v-for="k in ['1', '2', '3', '4', '5', '6', '7', '8', '9', 'del', '0', 'ok']"
            :key="k"
            class="key"
            :class="{ wide: k === 'ok', del: k === 'del' }"
            :disabled="locked || (k === 'ok' && typed === '')"
            @click="k === 'ok' ? submitTyped() : tapKey(k)"
          >
            {{ k === 'del' ? '⌫' : k === 'ok' ? '确定' : k }}
          </button>
        </div>
        <p class="dim tiny">也可以用键盘数字键输入，回车提交</p>
      </div>
    </section>

    <RoundSummary
      v-if="showSummary"
      :correct="correctCount"
      :total="ROUND_SIZE"
      :stars-earned="starsEarned"
      :module-name="`算术恒星 · ${level} 以内`"
      @replay="startRound"
      @home="router.push('/')"
    />
  </main>
</template>

<style scoped>
.controls {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
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
  white-space: nowrap;
}

.seg-btn.on {
  background: linear-gradient(135deg, var(--gold), var(--orange));
  color: #3a2400;
  box-shadow: 0 6px 16px rgba(255, 159, 69, 0.32);
}

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
  gap: 12px;
  flex-wrap: wrap;
}

.say {
  font-size: 15px;
}

.equation {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 26px 12px;
  border-radius: var(--radius-m);
  background:
    radial-gradient(70% 120% at 50% 0%, rgba(255, 206, 77, 0.16), transparent 70%),
    rgba(6, 9, 30, 0.45);
  border: 1px solid rgba(255, 206, 77, 0.26);
  flex-wrap: wrap;
}

.equation.hard {
  border-color: rgba(255, 122, 198, 0.4);
}

.term,
.sign {
  font-size: clamp(34px, 9vw, 62px);
  font-weight: 900;
  line-height: 1;
}

.sign {
  color: var(--gold);
}

.slot {
  min-width: 92px;
  padding: 6px 16px;
  font-size: clamp(34px, 9vw, 62px);
  font-weight: 900;
  line-height: 1;
  text-align: center;
  border-radius: var(--radius-s);
  border: 3px dashed rgba(94, 231, 255, 0.6);
  color: var(--cyan);
}

.slot.filled {
  border-style: solid;
  background: rgba(94, 231, 255, 0.12);
}

.hint {
  padding: 10px 14px;
  border-radius: var(--radius-s);
  background: rgba(255, 206, 77, 0.12);
  border: 1px solid rgba(255, 206, 77, 0.4);
  color: var(--gold);
  font-size: 14px;
  text-align: center;
}

/* ---- 数轴 ---- */

.numline {
  padding: 26px 22px 12px;
}

.nl-track {
  position: relative;
  height: 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.16);
}

.nl-span {
  position: absolute;
  top: 0;
  height: 4px;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--cyan), var(--violet));
  opacity: 0.5;
}

.nl-tick {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  display: grid;
  justify-items: center;
}

.nl-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.35);
}

.nl-tick.start .nl-dot {
  width: 14px;
  height: 14px;
  background: var(--gold);
  box-shadow: 0 0 12px rgba(255, 206, 77, 0.8);
}

.nl-tick.end .nl-dot {
  width: 14px;
  height: 14px;
  background: var(--green);
  box-shadow: 0 0 12px rgba(85, 230, 165, 0.8);
}

.nl-label {
  position: absolute;
  top: 12px;
  font-size: 11px;
  font-style: normal;
  color: var(--ink-dim);
}

/* ---- 选项 / 键盘 ---- */

.options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
}

.opt {
  padding: 22px 10px;
  font-size: 30px;
  font-weight: 900;
  border-radius: var(--radius-m);
  background: linear-gradient(160deg, rgba(255, 206, 77, 0.16), rgba(255, 159, 69, 0.14));
  border: 2px solid rgba(255, 206, 77, 0.42);
  transition: transform 0.14s ease, box-shadow 0.14s ease;
}

.opt:hover:not(:disabled) {
  transform: translateY(-3px);
  box-shadow: 0 10px 24px rgba(255, 159, 69, 0.26);
}

.opt.right {
  background: rgba(85, 230, 165, 0.28);
  border-color: var(--green);
}

.opt.bad {
  background: rgba(255, 107, 125, 0.26);
  border-color: var(--red);
}

.keypad-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.keypad {
  display: grid;
  grid-template-columns: repeat(3, 84px);
  gap: 10px;
}

.key {
  height: 60px;
  font-size: 26px;
  font-weight: 900;
  border-radius: var(--radius-s);
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.16);
  transition: transform 0.12s ease, background 0.12s ease;
}

.key:hover:not(:disabled) {
  transform: translateY(-2px);
  background: rgba(255, 255, 255, 0.16);
}

.key.del {
  color: var(--orange);
}

.key.wide {
  font-size: 18px;
  background: linear-gradient(135deg, var(--cyan), var(--violet));
  color: #08122b;
  border-color: transparent;
}

.tiny {
  font-size: 12px;
}

@media (max-width: 560px) {
  .keypad {
    grid-template-columns: repeat(3, 72px);
  }
}
</style>
