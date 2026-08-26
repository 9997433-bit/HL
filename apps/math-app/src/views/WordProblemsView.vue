<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import gsap from 'gsap'
import MascotBot from '@/components/MascotBot.vue'
import SessionBar from '@/components/SessionBar.vue'
import RoundSummary from '@/components/RoundSummary.vue'
import { useProgressStore } from '@/stores/progress'
import { useFeedback } from '@/composables/useFeedback'
import { WORD_PROBLEMS } from '@/data/wordProblems'
import { numericOptions, sample, shuffle } from '@/utils/random'
import { sfx } from '@/utils/sound'

const ROUND_SIZE = 8
const MODULE_ID = 'word'

const router = useRouter()
const progress = useProgressStore()
const { correct: fxCorrect, wrong: fxWrong, burst, flyStar, enter } = useFeedback()

const filter = ref('all') // all | one | two
const inputMode = ref('choice')

const questions = ref([])
const index = ref(0)
const marks = ref([])
const correctCount = ref(0)
const starsEarned = ref(0)
const showSummary = ref(false)
const locked = ref(false)
const chosen = ref(null)
const typed = ref('')
const hintLevel = ref(0) // 0 无 / 1 文字提示 / 2 显示算式
const mood = ref('idle')
const message = ref('慢慢读题，把关键的数字圈出来。')
const cardRef = ref(null)

const current = computed(() => questions.value[index.value] ?? null)

const bank = computed(() => {
  if (filter.value === 'one') return WORD_PROBLEMS.filter((p) => p.steps === 1)
  if (filter.value === 'two') return WORD_PROBLEMS.filter((p) => p.steps === 2)
  return WORD_PROBLEMS
})

function buildQuestion(template) {
  const made = template.make()
  return {
    ...made,
    id: template.id,
    tag: template.tag,
    emoji: template.emoji,
    scene: template.scene,
    steps: template.steps,
    options: numericOptions(made.answer, {
      count: 4,
      spread: Math.max(3, Math.round(made.answer * 0.35) + 2),
      min: 0,
    }),
  }
}

function drawTemplates() {
  const list = bank.value
  const out = []
  let pool = shuffle(list)
  while (out.length < ROUND_SIZE) {
    if (!pool.length) pool = shuffle(list)
    out.push(pool.pop())
  }
  return out
}

/* ---------- 判题 ---------- */

function grade(value, anchor) {
  const q = current.value
  const right = value === q.answer
  marks.value[index.value] = right ? 'ok' : 'no'
  chosen.value = value

  if (right) {
    const base = q.steps === 2 ? 3 : 2
    const stars = Math.max(1, base - hintLevel.value)
    correctCount.value += 1
    starsEarned.value += stars
    progress.recordAnswer(MODULE_ID, true, { stars, xp: q.steps === 2 ? 20 : 14 })
    fxCorrect(anchor)
    burst(anchor, { count: 20 })
    flyStar(anchor)
    mood.value = 'cheer'
    message.value = `${q.equation.replace('?', q.answer)} —— 解题成功！`
  } else {
    progress.recordAnswer(MODULE_ID, false)
    fxWrong(anchor)
    mood.value = 'sad'
    message.value = `正确算式是 ${q.equation.replace('?', q.answer)}，答案 ${q.answer} ${q.unit}。`
  }
  hintLevel.value = 2
}

function chooseOption(value, e) {
  if (locked.value) return
  locked.value = true
  grade(value, e.currentTarget)
  setTimeout(next, 2000)
}

function submitTyped() {
  if (locked.value || typed.value === '') return
  locked.value = true
  grade(Number(typed.value), cardRef.value)
  setTimeout(next, 2000)
}

function tapKey(k) {
  if (locked.value) return
  sfx.tap()
  if (k === 'del') {
    typed.value = typed.value.slice(0, -1)
    return
  }
  if (typed.value.length >= 4) return
  typed.value = `${typed.value}${k}`
}

function next() {
  chosen.value = null
  typed.value = ''
  hintLevel.value = 0
  locked.value = false
  mood.value = 'idle'
  if (index.value + 1 >= ROUND_SIZE) {
    finish()
    return
  }
  index.value += 1
  message.value = sample([
    '慢慢读题，把关键的数字圈出来。',
    '先想清楚问的是什么，再列算式。',
    '读两遍题目，不着急。',
  ])
  animateIn()
}

function finish() {
  const perfect = correctCount.value === ROUND_SIZE
  progress.finishSession(MODULE_ID, {
    correct: correctCount.value,
    total: ROUND_SIZE,
    bonusStars: perfect ? 5 : 0,
  })
  if (perfect) starsEarned.value += 5
  showSummary.value = true
}

function startRound() {
  questions.value = drawTemplates().map(buildQuestion)
  index.value = 0
  marks.value = []
  correctCount.value = 0
  starsEarned.value = 0
  showSummary.value = false
  locked.value = false
  chosen.value = null
  typed.value = ''
  hintLevel.value = 0
  mood.value = 'idle'
  message.value = '慢慢读题，把关键的数字圈出来。'
  progress.resetStreak()
  animateIn()
}

function animateIn() {
  requestAnimationFrame(() => {
    if (cardRef.value) {
      gsap.fromTo(
        cardRef.value,
        { opacity: 0, y: 20 },
        { opacity: 1, y: 0, duration: 0.38, ease: 'power2.out' },
      )
    }
    enter([...document.querySelectorAll('.opt')], { stagger: 0.06, y: 14, delay: 0.12 })
  })
}

function moreHint() {
  sfx.tap()
  if (hintLevel.value < 2) hintLevel.value += 1
}

function setFilter(v) {
  if (filter.value === v) return
  sfx.tap()
  filter.value = v
  startRound()
}

function toggleMode() {
  sfx.tap()
  inputMode.value = inputMode.value === 'choice' ? 'keypad' : 'choice'
}

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
      <div class="seg" role="group" aria-label="题目类型">
        <button class="seg-btn" :class="{ on: filter === 'all' }" @click="setFilter('all')">
          🌍 全部
        </button>
        <button class="seg-btn" :class="{ on: filter === 'one' }" @click="setFilter('one')">
          1️⃣ 一步题
        </button>
        <button class="seg-btn" :class="{ on: filter === 'two' }" @click="setFilter('two')">
          2️⃣ 两步题
        </button>
      </div>
      <div class="spacer" />
      <span class="chip">📚 母题 {{ bank.length }} 道</span>
      <button class="btn btn-ghost btn-sm" @click="toggleMode">
        {{ inputMode === 'choice' ? '⌨️ 改为输入' : '🔢 改为选择' }}
      </button>
    </section>

    <section class="panel bar-panel">
      <SessionBar
        :index="index"
        :total="ROUND_SIZE"
        :correct="correctCount"
        :streak="progress.streak"
        :marks="marks"
      />
    </section>

    <section v-if="current" class="panel stage">
      <header class="stage-head">
        <MascotBot :mood="mood" :size="72" />
        <p class="muted say">{{ message }}</p>
      </header>

      <article ref="cardRef" class="problem">
        <div class="problem-top">
          <span class="scene-emoji">{{ current.emoji }}</span>
          <div>
            <span class="chip scene">{{ current.scene }}</span>
            <span class="chip">{{ current.tag }}</span>
            <span class="chip" :class="{ 'chip-on': current.steps === 2 }">
              {{ current.steps === 2 ? '两步' : '一步' }}
            </span>
          </div>
        </div>

        <p class="problem-text">{{ current.text }}</p>

        <!-- 可视化：把题目里的数量画出来 -->
        <div v-if="current.visual" class="visual">
          <div v-for="(g, gi) in current.visual.groups" :key="gi" class="vgroup">
            <span
              v-for="k in g"
              :key="k"
              class="vicon"
              :class="{
                gone:
                  current.visual.strike !== undefined &&
                  gi === 0 &&
                  k > g - current.visual.strike,
              }"
            >
              {{ current.visual.icon }}
            </span>
            <em class="vcount">{{ g }}</em>
          </div>
        </div>

        <p v-if="hintLevel >= 1" class="hint">💡 {{ current.hint }}</p>
        <p v-if="hintLevel >= 2" class="eq">
          {{ locked ? current.equation.replace('?', current.answer) : current.equation }}
        </p>

        <button v-if="hintLevel < 2 && !locked" class="btn btn-ghost btn-sm hint-btn" @click="moreHint">
          {{ hintLevel === 0 ? '💡 给点提示' : '🧮 看看算式（少 1⭐）' }}
        </button>
      </article>

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
          {{ o }} <small>{{ current.unit }}</small>
        </button>
      </div>

      <!-- 输入模式 -->
      <div v-else class="keypad-wrap">
        <div class="answer-slot" :class="{ filled: typed !== '' }">
          {{ typed || '?' }} <small>{{ current.unit }}</small>
        </div>
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
      </div>
    </section>

    <RoundSummary
      v-if="showSummary"
      :correct="correctCount"
      :total="ROUND_SIZE"
      :stars-earned="starsEarned"
      module-name="生活行星"
      @replay="startRound"
      @home="router.push('/')"
    />
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
  white-space: nowrap;
}

.seg-btn.on {
  background: linear-gradient(135deg, var(--orange), var(--gold));
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
  gap: 14px;
  flex-wrap: wrap;
}

.say {
  font-size: 14px;
  flex: 1;
  min-width: 200px;
}

.problem {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 20px;
  border-radius: var(--radius-m);
  background:
    radial-gradient(80% 100% at 0% 0%, rgba(255, 159, 69, 0.14), transparent 60%),
    rgba(6, 9, 30, 0.45);
  border: 1px solid rgba(255, 159, 69, 0.28);
}

.problem-top {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.problem-top .chip {
  margin-right: 6px;
}

.scene-emoji {
  font-size: 38px;
}

.scene {
  background: rgba(255, 159, 69, 0.2);
  border-color: rgba(255, 159, 69, 0.5);
}

.problem-text {
  font-size: clamp(17px, 4.2vw, 21px);
  font-weight: 700;
  line-height: 1.75;
  letter-spacing: 0.3px;
}

.visual {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}

.vgroup {
  display: flex;
  align-items: center;
  gap: 3px;
  flex-wrap: wrap;
  padding: 8px 12px;
  border-radius: var(--radius-s);
  background: rgba(255, 255, 255, 0.05);
  border: 1px dashed rgba(255, 255, 255, 0.18);
  max-width: 100%;
}

.vicon {
  font-size: 19px;
  line-height: 1;
}

.vicon.gone {
  opacity: 0.28;
  filter: grayscale(1);
  text-decoration: line-through;
}

.vcount {
  margin-left: 6px;
  font-style: normal;
  font-weight: 900;
  color: var(--gold);
}

.hint {
  padding: 10px 14px;
  border-radius: var(--radius-s);
  background: rgba(255, 206, 77, 0.12);
  border: 1px solid rgba(255, 206, 77, 0.4);
  color: var(--gold);
  font-size: 14px;
}

.eq {
  align-self: flex-start;
  padding: 8px 18px;
  border-radius: var(--radius-s);
  background: rgba(94, 231, 255, 0.12);
  border: 1px solid rgba(94, 231, 255, 0.4);
  font-size: 22px;
  font-weight: 900;
  color: var(--cyan);
}

.hint-btn {
  align-self: flex-start;
}

.options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 12px;
}

.opt {
  padding: 20px 10px;
  font-size: 26px;
  font-weight: 900;
  border-radius: var(--radius-m);
  background: linear-gradient(160deg, rgba(255, 159, 69, 0.16), rgba(255, 206, 77, 0.14));
  border: 2px solid rgba(255, 159, 69, 0.42);
  transition: transform 0.14s ease, box-shadow 0.14s ease;
}

.opt small {
  font-size: 14px;
  color: var(--ink-soft);
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
  gap: 12px;
}

.answer-slot {
  min-width: 160px;
  padding: 10px 20px;
  text-align: center;
  font-size: 34px;
  font-weight: 900;
  color: var(--cyan);
  border-radius: var(--radius-s);
  border: 3px dashed rgba(94, 231, 255, 0.55);
}

.answer-slot.filled {
  border-style: solid;
  background: rgba(94, 231, 255, 0.12);
}

.answer-slot small {
  font-size: 16px;
  color: var(--ink-soft);
}

.keypad {
  display: grid;
  grid-template-columns: repeat(3, 84px);
  gap: 10px;
}

.key {
  height: 58px;
  font-size: 24px;
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
  font-size: 17px;
  background: linear-gradient(135deg, var(--gold), var(--orange));
  color: #3a2400;
  border-color: transparent;
}

@media (max-width: 560px) {
  .keypad {
    grid-template-columns: repeat(3, 72px);
  }
}
</style>
