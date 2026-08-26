<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import gsap from 'gsap'
import MascotBot from '@/components/MascotBot.vue'
import SessionBar from '@/components/SessionBar.vue'
import RoundSummary from '@/components/RoundSummary.vue'
import ShapeGlyph from '@/components/ShapeGlyph.vue'
import { useProgressStore } from '@/stores/progress.js'
import { useFeedback } from '@/composables/useFeedback'
import { numericOptions, pick, randInt, sample, shuffle } from '@/utils/random'
import { sound } from '@/utils/sound'

const ROUND_SIZE = 10
const MODULE_ID = 'logic'

const router = useRouter()
const progress = useProgressStore()
const { correct: fxCorrect, wrong: fxWrong, burst, flyStar, enter } = useFeedback()

const EMOJI_SETS = [
  ['🔴', '🔵', '🟡'],
  ['🌟', '🌙', '☄️'],
  ['🚀', '🛸', '🛰️'],
  ['🐱', '🐶', '🐰'],
  ['🍎', '🍌', '🍇'],
]
const SHAPE_SET = ['triangle', 'square', 'circle', 'star', 'hexagon']
const PALETTE = ['#5ee7ff', '#9b8cff', '#ff7ac6', '#ffce4d', '#55e6a5']

/* ---------------- 题目生成 ---------------- */

/** 等差数列：2 4 6 _ 10 */
function arithmeticSeq() {
  const step = sample([1, 2, 2, 3, 5, 10])
  const start = randInt(1, 9)
  const seq = Array.from({ length: 5 }, (_, i) => start + i * step)
  return finishNumeric(seq, `每次加 ${step}`, `相邻两个数都相差 ${step}。`)
}

/** 递减数列：20 17 14 _ 8 */
function decreasingSeq() {
  const step = sample([1, 2, 3, 5])
  const start = randInt(step * 4 + 1, step * 4 + 20)
  const seq = Array.from({ length: 5 }, (_, i) => start - i * step)
  return finishNumeric(seq, `每次减 ${step}`, `数字一直在变小，每次少 ${step}。`)
}

/** 倍数数列：1 2 4 8 _ */
function doublingSeq() {
  const start = sample([1, 2, 3])
  const seq = Array.from({ length: 5 }, (_, i) => start * 2 ** i)
  return finishNumeric(seq, '每次翻一倍', '后一个数是前一个数的 2 倍。')
}

/** 差值递增：1 2 4 7 11 _ */
function growingGapSeq() {
  const start = randInt(1, 4)
  const seq = [start]
  for (let i = 1; i < 5; i++) seq.push(seq[i - 1] + i)
  return finishNumeric(seq, '每次多加 1', '相差的数一次比一次大 1：+1、+2、+3……')
}

/** 交替加减：3 8 5 10 7 _ */
function zigzagSeq() {
  const up = randInt(3, 6)
  const down = randInt(1, up - 1)
  const seq = [randInt(2, 8)]
  for (let i = 1; i < 6; i++) seq.push(seq[i - 1] + (i % 2 === 1 ? up : -down))
  return finishNumeric(seq, `一次加 ${up}，一次减 ${down}`, '注意数字是一上一下跳动的。')
}

function finishNumeric(seq, rule, hint) {
  const blank = randInt(1, seq.length - 1)
  const answer = seq[blank]
  return {
    type: 'number',
    prompt: '找出缺少的那个数字',
    rule,
    hint,
    seq,
    blank,
    answer,
    options: numericOptions(answer, { count: 4, spread: Math.max(2, Math.round(answer * 0.3) + 1), min: 0 }),
  }
}

/** 图形循环：ABAB / AABB / ABC */
function emojiCycle() {
  const set = sample(EMOJI_SETS)
  const patternKind = sample(['AB', 'AAB', 'ABC', 'AABB'])
  const [a, b, c] = shuffle(set)
  const unit = { AB: [a, b], AAB: [a, a, b], ABC: [a, b, c], AABB: [a, a, b, b] }[patternKind]
  const seq = Array.from({ length: 8 }, (_, i) => unit[i % unit.length])
  const blank = randInt(unit.length, 7)
  const answer = seq[blank]
  const options = shuffle([...new Set([answer, a, b, c].filter(Boolean))]).slice(0, Math.max(3, set.length))
  return {
    type: 'emoji',
    prompt: '按规律，问号处应该是什么？',
    rule: `重复出现的一组是 ${unit.join('')}`,
    hint: `每 ${unit.length} 个为一组不断重复。`,
    seq,
    blank,
    answer,
    options: shuffle(options),
  }
}

/** 数量递增：▲ / ▲▲ / ▲▲▲ / ? */
function growingGroup() {
  const icon = sample(['⭐', '🔵', '🍎', '🚀'])
  const step = sample([1, 1, 2])
  const start = randInt(1, 2)
  const counts = Array.from({ length: 5 }, (_, i) => start + i * step)
  const blank = randInt(2, 4)
  const answer = counts[blank]
  return {
    type: 'group',
    prompt: '问号处应该有几个图案？',
    rule: `每次多 ${step} 个`,
    hint: `数一数每一组的个数：${counts.slice(0, blank).join('、')}……`,
    icon,
    counts,
    blank,
    answer,
    options: numericOptions(answer, { count: 4, spread: 2, min: 1, max: 14 }),
  }
}

/** 旋转规律：箭头每次转 90° */
function rotationPattern() {
  const stepDeg = sample([45, 90, 90, -90])
  const start = sample([0, 90, 180, 270])
  const angles = Array.from({ length: 5 }, (_, i) => start + i * stepDeg)
  const blank = randInt(2, 4)
  const answer = ((angles[blank] % 360) + 360) % 360
  const wrongAngles = new Set()
  while (wrongAngles.size < 3) {
    const cand = ((sample([0, 45, 90, 135, 180, 225, 270, 315]) % 360) + 360) % 360
    if (cand !== answer) wrongAngles.add(cand)
  }
  return {
    type: 'rotate',
    prompt: '箭头一直在转，问号处指向哪里？',
    rule: `每次转 ${Math.abs(stepDeg)} 度`,
    hint: stepDeg > 0 ? '它在顺时针转动。' : '它在逆时针转动。',
    angles: angles.map((a) => ((a % 360) + 360) % 360),
    blank,
    answer,
    options: shuffle([answer, ...wrongAngles]),
  }
}

/** 形状 + 颜色双规律 */
function shapeCycle() {
  const shapes = pick(SHAPE_SET, 3)
  const colors = pick(PALETTE, 2)
  const seq = Array.from({ length: 6 }, (_, i) => ({
    shape: shapes[i % shapes.length],
    color: colors[i % colors.length],
  }))
  const blank = randInt(3, 5)
  const answer = `${seq[blank].shape}|${seq[blank].color}`
  const wrong = new Set()
  while (wrong.size < 3) {
    const cand = `${sample(shapes)}|${sample(colors)}`
    if (cand !== answer) wrong.add(cand)
  }
  return {
    type: 'shape',
    prompt: '形状和颜色都有规律，问号是哪一个？',
    rule: '形状 3 个一循环，颜色 2 个一循环',
    hint: '先只看形状，再只看颜色，分开找规律。',
    seq,
    blank,
    answer,
    options: shuffle([answer, ...wrong]).map((k) => {
      const [shape, color] = k.split('|')
      return { key: k, shape, color }
    }),
  }
}

const MAKERS = [
  arithmeticSeq,
  decreasingSeq,
  doublingSeq,
  growingGapSeq,
  zigzagSeq,
  emojiCycle,
  emojiCycle,
  growingGroup,
  rotationPattern,
  shapeCycle,
]

/* ---------------- 流程 ---------------- */

const questions = ref([])
const index = ref(0)
const marks = ref([])
const correctCount = ref(0)
const starsEarned = ref(0)
const showSummary = ref(false)
const locked = ref(false)
const chosen = ref(null)
const showHint = ref(false)
const mood = ref('idle')
const message = ref('先看看前面几个，再猜问号里是什么。')

const current = computed(() => questions.value[index.value] ?? null)

/**
 * 循环型题目练的是「简单规律」，数列与数量递增练的是归纳推理，
 * 分开上报让掌握度更能反映真实薄弱环节。
 */
const SKILL_BY_TYPE = {
  emoji: 'pattern-abab',
  shape: 'pattern-abab',
  rotate: 'pattern-abab',
  number: 'deduction',
  group: 'deduction',
}

function grade(value, anchor) {
  const q = current.value
  const right = value === q.answer
  marks.value[index.value] = right ? 'ok' : 'no'
  chosen.value = value
  const skill = SKILL_BY_TYPE[q.type] ?? 'pattern-abab'

  if (right) {
    const stars = showHint.value ? 1 : 2
    correctCount.value += 1
    starsEarned.value += stars
    progress.recordAnswer(MODULE_ID, true, { skill, stars, xp: 14 })
    fxCorrect(anchor)
    burst(anchor, { count: 18 })
    flyStar(anchor)
    mood.value = 'cheer'
    message.value = `规律是「${q.rule}」，你破译成功了！`
  } else {
    progress.recordAnswer(MODULE_ID, false, { skill })
    fxWrong(anchor)
    mood.value = 'sad'
    message.value = `规律是「${q.rule}」，再看一遍就明白啦。`
  }
}

function answer(value, e) {
  if (locked.value) return
  locked.value = true
  grade(value, e.currentTarget)
  setTimeout(next, 1700)
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
  message.value = '先看看前面几个，再猜问号里是什么。'
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
  questions.value = shuffle(MAKERS)
    .concat(shuffle(MAKERS))
    .slice(0, ROUND_SIZE)
    .map((make) => make())
  index.value = 0
  marks.value = []
  correctCount.value = 0
  starsEarned.value = 0
  showSummary.value = false
  locked.value = false
  chosen.value = null
  showHint.value = false
  mood.value = 'idle'
  message.value = '先看看前面几个，再猜问号里是什么。'
  progress.resetCombo()
  animateIn()
}

function animateIn() {
  requestAnimationFrame(() => {
    gsap.fromTo(
      '.cell',
      { opacity: 0, x: -18 },
      { opacity: 1, x: 0, duration: 0.3, stagger: 0.06, ease: 'power2.out' },
    )
    enter([...document.querySelectorAll('.opt')], { stagger: 0.05, y: 14, delay: 0.15 })
  })
}

function toggleHint() {
  sound.click()
  showHint.value = !showHint.value
}

onMounted(startRound)
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

    <section v-if="current" class="panel stage">
      <header class="stage-head">
        <MascotBot :mood="mood" :size="72" />
        <div class="head-text">
          <h2 class="prompt">{{ current.prompt }}</h2>
          <p class="muted say">{{ message }}</p>
        </div>
        <button class="btn btn-ghost btn-sm" @click="toggleHint">
          💡 {{ showHint ? '收起提示' : '提示（少 1⭐）' }}
        </button>
      </header>

      <p v-if="showHint" class="hint">{{ current.hint }}</p>

      <!-- 序列展示 -->
      <div class="belt">
        <!-- 数字序列 -->
        <template v-if="current.type === 'number'">
          <span
            v-for="(n, i) in current.seq"
            :key="i"
            class="cell"
            :class="{ blank: i === current.blank }"
          >
            {{ i === current.blank ? '?' : n }}
          </span>
        </template>

        <!-- 图案循环 -->
        <template v-else-if="current.type === 'emoji'">
          <span
            v-for="(e, i) in current.seq"
            :key="i"
            class="cell"
            :class="{ blank: i === current.blank }"
          >
            {{ i === current.blank ? '?' : e }}
          </span>
        </template>

        <!-- 数量递增 -->
        <template v-else-if="current.type === 'group'">
          <span
            v-for="(c, i) in current.counts"
            :key="i"
            class="cell group-cell"
            :class="{ blank: i === current.blank }"
          >
            <template v-if="i === current.blank">?</template>
            <template v-else>
              <i v-for="k in c" :key="k" class="dot-icon">{{ current.icon }}</i>
            </template>
          </span>
        </template>

        <!-- 旋转 -->
        <template v-else-if="current.type === 'rotate'">
          <span
            v-for="(a, i) in current.angles"
            :key="i"
            class="cell"
            :class="{ blank: i === current.blank }"
          >
            <template v-if="i === current.blank">?</template>
            <svg v-else viewBox="0 0 40 40" width="34" height="34" :style="{ transform: `rotate(${a}deg)` }">
              <path
                d="M20 5 L31 30 L20 24 L9 30 Z"
                fill="#ffce4d"
                stroke="rgba(255,255,255,0.6)"
                stroke-width="1.6"
                stroke-linejoin="round"
              />
            </svg>
          </span>
        </template>

        <!-- 形状 + 颜色 -->
        <template v-else>
          <span
            v-for="(s, i) in current.seq"
            :key="i"
            class="cell"
            :class="{ blank: i === current.blank }"
          >
            <template v-if="i === current.blank">?</template>
            <ShapeGlyph v-else :shape="s.shape" :size="40" :color="s.color" />
          </span>
        </template>
      </div>

      <p class="rule-tag chip" :class="{ 'chip-on': locked }">
        {{ locked ? `🔍 规律：${current.rule}` : '🔍 规律待破译' }}
      </p>

      <!-- 选项 -->
      <div class="options">
        <!-- 旋转题：选项也用箭头 -->
        <template v-if="current.type === 'rotate'">
          <button
            v-for="a in current.options"
            :key="a"
            class="opt"
            :class="{
              right: locked && a === current.answer,
              bad: locked && chosen === a && a !== current.answer,
            }"
            :disabled="locked"
            @click="answer(a, $event)"
          >
            <svg viewBox="0 0 40 40" width="42" height="42" :style="{ transform: `rotate(${a}deg)` }">
              <path
                d="M20 5 L31 30 L20 24 L9 30 Z"
                fill="#ffce4d"
                stroke="rgba(255,255,255,0.6)"
                stroke-width="1.6"
                stroke-linejoin="round"
              />
            </svg>
          </button>
        </template>

        <!-- 形状题 -->
        <template v-else-if="current.type === 'shape'">
          <button
            v-for="o in current.options"
            :key="o.key"
            class="opt"
            :class="{
              right: locked && o.key === current.answer,
              bad: locked && chosen === o.key && o.key !== current.answer,
            }"
            :disabled="locked"
            @click="answer(o.key, $event)"
          >
            <ShapeGlyph :shape="o.shape" :size="52" :color="o.color" />
          </button>
        </template>

        <!-- 数字 / 图案 -->
        <template v-else>
          <button
            v-for="o in current.options"
            :key="o"
            class="opt"
            :class="{
              right: locked && o === current.answer,
              bad: locked && chosen === o && o !== current.answer,
            }"
            :disabled="locked"
            @click="answer(o, $event)"
          >
            <template v-if="current.type === 'group'">
              <i v-for="k in o" :key="k" class="dot-icon sm">{{ current.icon }}</i>
            </template>
            <template v-else>{{ o }}</template>
          </button>
        </template>
      </div>
    </section>

    <RoundSummary
      v-if="showSummary"
      :correct="correctCount"
      :total="ROUND_SIZE"
      :stars-earned="starsEarned"
      module-name="规律环带"
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
  font-size: 21px;
  font-weight: 900;
}

.say {
  font-size: 14px;
  margin-top: 4px;
}

.hint {
  padding: 10px 14px;
  border-radius: var(--radius-s);
  background: rgba(85, 230, 165, 0.1);
  border: 1px solid rgba(85, 230, 165, 0.36);
  color: var(--green);
  font-size: 14px;
}

.belt {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  padding: 20px 12px;
  border-radius: var(--radius-m);
  background:
    linear-gradient(90deg, rgba(85, 230, 165, 0.08), rgba(94, 231, 255, 0.08)),
    rgba(6, 9, 30, 0.42);
  border: 1px solid rgba(85, 230, 165, 0.2);
}

.cell {
  min-width: 62px;
  height: 62px;
  padding: 4px;
  display: grid;
  place-items: center;
  font-size: 26px;
  font-weight: 900;
  border-radius: var(--radius-s);
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.14);
}

.group-cell {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  align-items: center;
  justify-content: center;
  padding: 6px;
  max-width: 96px;
}

.dot-icon {
  font-size: 15px;
  font-style: normal;
  line-height: 1;
}

.dot-icon.sm {
  font-size: 17px;
}

.cell.blank {
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

.rule-tag {
  align-self: center;
}

.options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: 12px;
}

.opt {
  min-height: 78px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 3px;
  padding: 14px 10px;
  font-size: 28px;
  font-weight: 900;
  border-radius: var(--radius-m);
  background: linear-gradient(160deg, rgba(85, 230, 165, 0.15), rgba(94, 231, 255, 0.15));
  border: 2px solid rgba(85, 230, 165, 0.4);
  transition: transform 0.14s ease, box-shadow 0.14s ease;
}

.opt:hover:not(:disabled) {
  transform: translateY(-3px);
  box-shadow: 0 10px 24px rgba(85, 230, 165, 0.24);
}

.opt.right {
  background: rgba(85, 230, 165, 0.3);
  border-color: var(--green);
}

.opt.bad {
  background: rgba(255, 107, 125, 0.26);
  border-color: var(--red);
}

@media (max-width: 560px) {
  .cell {
    min-width: 48px;
    height: 48px;
    font-size: 20px;
  }

  .prompt {
    font-size: 18px;
  }
}
</style>
