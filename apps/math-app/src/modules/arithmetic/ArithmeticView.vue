<script setup>
/**
 * 算术恒星 · 口算闯关。
 * 题目生成、数轴、错因归因留在这里；答题流程（选项/键盘/判题/星星/进度条）交给 QuizShell。
 */
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import QuizShell from '@/components/QuizShell.vue'
import { useProgressStore } from '@/stores/progress.js'
import { numericOptions, randInt, sample } from '@/utils/random'
import { sound } from '@/core/audio/sound.js'

const ROUND_SIZE = 10
const MODULE_ID = 'arithmetic'
const SPEED_BONUS_MS = 6000

const router = useRouter()
const progress = useProgressStore()

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
const inputMode = ref('choice')

const isHard = computed(() => level.value === 100)
const comboBest = ref(0)

/* ---------------------------------------------------------- 题目生成 */

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

/** 分级提示：一级是数数策略，二级直接给凑十/破十的拆分写法。 */
function hintsFor(q) {
  const out = []
  if (q.kind === 'add') {
    out.push(`从 ${q.a} 开始，往后数 ${q.b} 步。`)
    const toTen = 10 - (q.a % 10)
    if (q.b > toTen && toTen > 0) {
      out.push(`凑十法：${q.a} + ${toTen} = ${q.a + toTen}，再加剩下的 ${q.b - toTen}。`)
    }
  } else {
    out.push(`从 ${q.a} 开始，往前数 ${q.b} 步。`)
    const ones = q.a % 10
    if (q.b > ones && q.a > 10) {
      out.push(`破十法：先减 ${ones} 退到 ${q.a - ones}，再减剩下的 ${q.b - ones}。`)
    }
  }
  return out
}

/** 映射到 curriculum 技能点，让自适应掌握度引擎能收到反馈。 */
function skillOf(q) {
  if (level.value === 100) return 'add-within-100'
  if (level.value === 20) return q.kind === 'add' ? 'add-carry-20' : 'sub-borrow-20'
  return q.kind === 'add' ? 'add-within-10' : 'sub-within-10'
}

/**
 * 错因归类：个位相加过 10 却答错多半是忘进位，个位不够减则是忘退位；
 * 答出「另一种运算」的结果说明是把加减看反了。家长报告按这些标签统计薄弱点。
 */
function errorTagsOf(q, answered) {
  const tags = []
  const onesA = q.a % 10
  const onesB = q.b % 10
  if (q.kind === 'add' && answered === q.a - q.b) tags.push('wrong-op')
  if (q.kind === 'sub' && answered === q.a + q.b) tags.push('wrong-op')
  if (q.kind === 'add' && onesA + onesB >= 10) tags.push('carry')
  if (q.kind === 'sub' && onesA < onesB) tags.push('borrow')
  if (Math.abs(answered - q.answer) === 10) tags.push('off-by-ten')
  else if (Math.abs(answered - q.answer) === 1) tags.push('off-by-one')
  return [...new Set(tags)]
}

function buildQuestion() {
  const q = makeQuestion()
  const base = isHard.value ? 2 : 1
  return {
    ...q,
    id: `${q.a}${q.sign}${q.b}`,
    skill: skillOf(q),
    options: numericOptions(q.answer, {
      count: 4,
      spread: level.value === 100 ? 9 : 3,
      min: 0,
      max: level.value,
    }),
    hints: hintsFor(q),
    xp: isHard.value ? 18 : 10,
    tag: isHard.value ? 'arithmetic-hard' : undefined,
    // 连击越长，单题星星越多：3 连击 +1，5 连击 +2
    stars: ({ combo }) => base + (combo >= 5 ? 2 : combo >= 3 ? 1 : 0),
    errorTags: errorTagsOf,
  }
}

const questions = ref(Array.from({ length: ROUND_SIZE }, buildQuestion))
const currentIndex = ref(0)

function newRound() {
  comboBest.value = 0
  currentIndex.value = 0
  questions.value = Array.from({ length: ROUND_SIZE }, buildQuestion)
}

watch([level, op], newRound)

/* ------------------------------------------------------------ 数轴 */

const current = computed(() => questions.value[currentIndex.value] ?? null)

/** 20 以内才画数轴：再大格子就挤成一团，反而看不清跳跃过程。 */
const numberLine = computed(() => {
  const q = current.value
  if (!q || level.value > 20) return null
  const max = level.value
  return {
    max,
    ticks: Array.from({ length: max + 1 }, (_, i) => i),
    from: q.a,
    to: q.answer,
    left: Math.min(q.a, q.answer),
    width: Math.abs(q.answer - q.a),
  }
})

function onGraded({ correct }) {
  if (correct) comboBest.value = Math.max(comboBest.value, progress.combo)
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
</script>

<template>
  <main class="page">
    <QuizShell
      v-model:inputMode="inputMode"
      :module-id="MODULE_ID"
      :module-name="`算术恒星 · ${level} 以内`"
      :questions="questions"
      :speed-bonus-ms="SPEED_BONUS_MS"
      :perfect-bonus="4"
      :show-answer-slot="false"
      :hint-labels="['💡 提示', '💡 再提示（少 1⭐）']"
      :prompts="['算一算，答案是多少？', '看清符号再作答 🙂', '心里默算一遍，再选答案。']"
      @advance="currentIndex = $event"
      @graded="onGraded"
      @replay="newRound"
      @home="router.push('/')"
    >
      <template #controls>
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
      </template>

      <!-- 口算连击：连击越高星星加成越多，这里把加成明确画出来 -->
      <template #bar-extra>
        <span class="chip combo" :class="{ hot: progress.combo >= 3 }">
          🔥 连击 {{ progress.combo }}
          <em v-if="progress.combo >= 5">×3⭐</em>
          <em v-else-if="progress.combo >= 3">×2⭐</em>
        </span>
        <span v-if="comboBest >= 2" class="chip">🏅 本轮最佳 {{ comboBest }}</span>
      </template>

      <template #question="{ question, typed }">
        <div class="equation" :class="{ hard: isHard }">
          <span class="term">{{ question.a }}</span>
          <span class="sign">{{ question.sign }}</span>
          <span class="term">{{ question.b }}</span>
          <span class="sign">=</span>
          <span class="slot" :class="{ filled: typed !== '' }">
            {{ inputMode === 'keypad' ? typed || '?' : '?' }}
          </span>
        </div>
      </template>

      <template #beneath="{ question, hintLevel, locked }">
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
                start: t === question.a,
                end: (hintLevel > 0 || locked) && t === question.answer,
              }"
              :style="{ left: `${(t / numberLine.max) * 100}%` }"
            >
              <i class="nl-dot" />
              <em v-if="t % (numberLine.max > 10 ? 2 : 1) === 0" class="nl-label">{{ t }}</em>
            </span>
          </div>
        </div>
      </template>
    </QuizShell>
  </main>
</template>

<style scoped>
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

.combo em {
  font-style: normal;
  font-weight: 900;
  color: var(--gold);
}

.combo.hot {
  background: linear-gradient(135deg, rgba(255, 159, 69, 0.32), rgba(255, 107, 125, 0.32));
  border-color: rgba(255, 159, 69, 0.6);
  color: var(--ink);
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
</style>
