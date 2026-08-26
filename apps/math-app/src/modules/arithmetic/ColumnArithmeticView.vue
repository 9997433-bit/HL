<script setup>
import { computed, ref } from 'vue'
import { ERROR_TAGS } from '@/data/errorTags.js'
import { useProgressStore, wrongBookKey } from '@/stores/progress.js'
import { sound } from '@/utils/sound.js'

const CASES = [
  {
    id: '28-plus-17',
    kind: 'carry',
    a: 28,
    b: 17,
    sign: '+',
    answer: 45,
    skill: 'add-within-100',
    tag: 'carry',
    stepPrompt: '个位 8 + 7 = 15，应该向十位进几？',
    stepAnswer: 1,
    stepChoices: [0, 1, 2],
    answerChoices: [35, 45, 55],
    explanation: '个位写 5，把满十得到的 1 写到十位上方；十位算 1 + 2 + 1 = 4。',
  },
  {
    id: '46-plus-38',
    kind: 'carry',
    a: 46,
    b: 38,
    sign: '+',
    answer: 84,
    skill: 'add-within-100',
    tag: 'carry',
    stepPrompt: '个位 6 + 8 = 14，应该向十位进几？',
    stepAnswer: 1,
    stepChoices: [0, 1, 2],
    answerChoices: [74, 84, 94],
    explanation: '个位写 4、向十位进 1；十位是 1 + 4 + 3 = 8。',
  },
  {
    id: '52-minus-28',
    kind: 'borrow',
    a: 52,
    b: 28,
    sign: '−',
    answer: 24,
    skill: 'sub-within-100',
    tag: 'borrow',
    stepPrompt: '个位 2 不够减 8，从十位借 1 能换成几个一？',
    stepAnswer: 10,
    stepChoices: [1, 10, 20],
    answerChoices: [24, 34, 44],
    explanation: '从 5 个十里借 1 个十，十位剩 4；个位变成 12，12 − 8 = 4，再算 4 − 2 = 2。',
  },
  {
    id: '71-minus-46',
    kind: 'borrow',
    a: 71,
    b: 46,
    sign: '−',
    answer: 25,
    skill: 'sub-within-100',
    tag: 'borrow',
    stepPrompt: '个位 1 不够减 6，从十位借 1 能换成几个一？',
    stepAnswer: 10,
    stepChoices: [1, 10, 20],
    answerChoices: [15, 25, 35],
    explanation: '从 7 个十里借 1 个十，十位剩 6；个位变成 11，11 − 6 = 5，再算 6 − 4 = 2。',
  },
]

const progress = useProgressStore()
const mode = ref('carry')
const caseIndex = ref({ carry: 0, borrow: 0 })
const step = ref(0)
const solved = ref(false)
const wrongChoice = ref(null)
const recordedMiss = ref(false)
const message = ref('先从个位算起，注意满十进 1、个位不够向十位借 1。')

const casesInMode = computed(() => CASES.filter((item) => item.kind === mode.value))
const current = computed(() => casesInMode.value[caseIndex.value[mode.value] % casesInMode.value.length])
const tagInfo = computed(() => ERROR_TAGS[current.value.tag])
const aDigits = computed(() => String(current.value.a).padStart(2, '0').split(''))
const bDigits = computed(() => String(current.value.b).padStart(2, '0').split(''))
const answerDigits = computed(() =>
  solved.value ? String(current.value.answer).padStart(2, '0').split('') : ['?', '?'],
)

function setMode(next) {
  if (mode.value === next) return
  mode.value = next
  resetQuestion()
  sound.click()
}

function recordMistake(value) {
  if (recordedMiss.value) return
  recordedMiss.value = true
  const q = current.value
  progress.recordAnswer('arithmetic', false, {
    skill: q.skill,
    errorTags: [q.tag, 'off-by-ten'],
  })
  progress.recordWrong({
    id: wrongBookKey('arithmetic', `column-${q.id}`),
    module: 'arithmetic',
    skill: q.skill,
    errorTag: q.tag,
    errorTags: [q.tag, 'off-by-ten'],
    title: `竖式 ${q.a} ${q.sign} ${q.b}`,
    answer: q.answer,
    options: q.answerChoices,
    hint: q.explanation,
    lastWrong: value,
  })
}

function chooseStep(value) {
  if (step.value !== 0 || solved.value) return
  wrongChoice.value = value
  if (value === current.value.stepAnswer) {
    step.value = 1
    wrongChoice.value = null
    message.value =
      mode.value === 'carry'
        ? '进位 1 已经写好。现在把十位也算完，选出竖式结果。'
        : '借来的 1 个十已经换成 10 个一。现在完成竖式。'
    sound.correct()
    return
  }
  recordMistake(value)
  message.value = `${tagInfo.value.label}：${tagInfo.value.tip}`
  sound.wrong()
}

function chooseAnswer(value) {
  if (step.value !== 1 || solved.value) return
  wrongChoice.value = value
  if (value !== current.value.answer) {
    recordMistake(value)
    message.value = `再检查一次每一位。${current.value.explanation}`
    sound.wrong()
    return
  }
  solved.value = true
  wrongChoice.value = null
  progress.recordAnswer('arithmetic', true, {
    skill: current.value.skill,
    stars: 2,
    xp: 18,
  })
  progress.clearWrong(wrongBookKey('arithmetic', `column-${current.value.id}`))
  message.value = `算对了！${current.value.explanation}`
  sound.correct()
}

function resetQuestion() {
  step.value = 0
  solved.value = false
  wrongChoice.value = null
  recordedMiss.value = false
  message.value = '先从个位算起，注意满十进 1、个位不够向十位借 1。'
}

function nextQuestion() {
  caseIndex.value[mode.value] = (caseIndex.value[mode.value] + 1) % casesInMode.value.length
  resetQuestion()
  sound.click()
}
</script>

<template>
  <main class="page stack">
    <section class="card hero">
      <div>
        <p class="kicker">逐位计算专题</p>
        <h2>竖式工坊</h2>
        <p class="muted">从个位开始，一步解决进位或借位，再完成两位数加减法。</p>
      </div>
      <span class="error-badge">错因专练：{{ tagInfo.label }}</span>
    </section>

    <section class="card mode-card">
      <div class="seg" role="group" aria-label="竖式专题">
        <button
          class="seg-btn"
          :class="{ on: mode === 'carry' }"
          data-column-mode="carry"
          @click="setMode('carry')"
        >
          ⬆️ 进位加法
        </button>
        <button
          class="seg-btn"
          :class="{ on: mode === 'borrow' }"
          data-column-mode="borrow"
          @click="setMode('borrow')"
        >
          ⬇️ 借位减法
        </button>
      </div>
      <p class="dim">{{ tagInfo.tip }}</p>
    </section>

    <section class="card workshop">
      <div class="column-wrap">
        <div class="place-labels" aria-hidden="true">
          <span>十位</span>
          <span>个位</span>
        </div>
        <div
          class="column-math"
          :class="{ carry: mode === 'carry', borrow: mode === 'borrow' }"
          :aria-label="`${current.a} ${current.sign} ${current.b} 的竖式`"
        >
          <div class="carry-row">
            <span v-if="mode === 'borrow' && step > 0" class="borrow-mark">
              {{ Number(aDigits[0]) - 1 }}
            </span>
            <span v-else-if="mode === 'carry' && step > 0" class="carry-mark">1</span>
            <span />
          </div>
          <div class="number-row">
            <span>{{ aDigits[0] }}</span>
            <span :class="{ borrowed: mode === 'borrow' && step > 0 }">
              {{ mode === 'borrow' && step > 0 ? Number(aDigits[1]) + 10 : aDigits[1] }}
            </span>
          </div>
          <div class="number-row operand">
            <b>{{ current.sign }}</b>
            <span>{{ bDigits[0] }}</span>
            <span>{{ bDigits[1] }}</span>
          </div>
          <div class="rule" />
          <div class="number-row answer-row">
            <span>{{ answerDigits[0] }}</span>
            <span>{{ answerDigits[1] }}</span>
          </div>
        </div>
      </div>

      <div class="step-panel">
        <span class="step-chip">第 {{ step + 1 }} 步 / 2</span>
        <h3 v-if="step === 0">{{ current.stepPrompt }}</h3>
        <h3 v-else>完整竖式 {{ current.a }} {{ current.sign }} {{ current.b }} 等于多少？</h3>

        <div v-if="step === 0" class="options">
          <button
            v-for="choice in current.stepChoices"
            :key="choice"
            class="column-option"
            :class="{ wrong: wrongChoice === choice && choice !== current.stepAnswer }"
            :data-correct="choice === current.stepAnswer"
            data-column-step-option
            @click="chooseStep(choice)"
          >
            {{ choice }}
          </button>
        </div>
        <div v-else class="options">
          <button
            v-for="choice in current.answerChoices"
            :key="choice"
            class="column-option"
            :class="{
              wrong: wrongChoice === choice && choice !== current.answer,
              right: solved && choice === current.answer,
            }"
            :disabled="solved"
            :data-correct="choice === current.answer"
            data-column-answer-option
            @click="chooseAnswer(choice)"
          >
            {{ choice }}
          </button>
        </div>

        <p class="message" :class="{ success: solved }" aria-live="polite">{{ message }}</p>

        <button v-if="solved" class="btn btn--primary" data-column-next @click="nextQuestion">
          下一道{{ mode === 'carry' ? '进位' : '借位' }}题 →
        </button>
      </div>
    </section>

    <section class="cause-grid">
      <article class="card cause-card">
        <span>⬆️</span>
        <div>
          <h3>为什么要进位？</h3>
          <p>个位满 10 就打包成 1 个十，个位只留下不足 10 的部分。</p>
        </div>
      </article>
      <article class="card cause-card">
        <span>⬇️</span>
        <div>
          <h3>为什么能借位？</h3>
          <p>从十位借来的 1 表示 1 个十，到了个位要换成 10 个一。</p>
        </div>
      </article>
    </section>
  </main>
</template>

<style scoped>
.hero {
  display: flex;
  align-items: center;
  gap: 18px;
}

.hero > div {
  flex: 1;
}

.hero h2 {
  margin: 3px 0 6px;
  font-size: clamp(24px, 5vw, 32px);
}

.kicker {
  color: var(--brand);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 1.5px;
}

.error-badge {
  flex: none;
  padding: 10px 14px;
  border-radius: 999px;
  color: var(--star);
  background: rgba(255, 206, 77, 0.1);
  border: 1px solid rgba(255, 206, 77, 0.35);
  font-size: 13px;
  font-weight: 900;
}

.mode-card {
  display: flex;
  align-items: center;
  gap: 14px;
}

.seg {
  display: flex;
  gap: 5px;
  padding: 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.seg-btn {
  padding: 9px 15px;
  border-radius: 999px;
  color: var(--text);
  font-size: 13px;
  font-weight: 900;
}

.seg-btn.on {
  color: var(--text-invert);
  background: linear-gradient(135deg, var(--star), var(--neon-orange));
}

.workshop {
  display: grid;
  grid-template-columns: minmax(250px, 0.8fr) minmax(300px, 1.2fr);
  gap: 22px;
  align-items: stretch;
}

.column-wrap {
  padding: 20px;
  display: flex;
  justify-content: center;
  gap: 10px;
  border-radius: var(--radius-md);
  background:
    repeating-linear-gradient(0deg, transparent 0 39px, rgba(94, 231, 255, 0.07) 40px),
    repeating-linear-gradient(90deg, transparent 0 39px, rgba(94, 231, 255, 0.07) 40px),
    rgba(6, 9, 30, 0.45);
  border: 1px solid rgba(94, 231, 255, 0.22);
}

.place-labels {
  padding-top: 6px;
  display: grid;
  grid-template-columns: repeat(2, 58px);
  align-content: start;
  color: var(--text-soft);
  font-size: 12px;
  text-align: center;
  position: absolute;
}

.column-math {
  width: 180px;
  margin-top: 28px;
  display: grid;
  gap: 2px;
}

.carry-row,
.number-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  min-height: 59px;
  align-items: center;
  text-align: center;
}

.carry-row {
  min-height: 34px;
  color: var(--neon-pink);
  font-size: 20px;
  font-weight: 900;
}

.number-row {
  position: relative;
  font-size: 48px;
  font-weight: 900;
  line-height: 1;
}

.number-row.operand {
  grid-template-columns: 28px repeat(2, 1fr);
}

.number-row.operand b {
  color: var(--star);
  font-size: 34px;
}

.borrowed {
  color: var(--brand);
  font-size: 36px;
}

.rule {
  height: 4px;
  border-radius: 999px;
  background: var(--text-strong);
}

.answer-row {
  color: var(--success);
}

.step-panel {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 16px;
}

.step-panel h3 {
  font-size: 20px;
  line-height: 1.45;
}

.step-chip {
  align-self: flex-start;
  padding: 5px 10px;
  border-radius: 999px;
  color: var(--brand);
  background: rgba(94, 231, 255, 0.1);
  border: 1px solid rgba(94, 231, 255, 0.3);
  font-size: 12px;
  font-weight: 900;
}

.options {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.column-option {
  min-height: 65px;
  border-radius: var(--radius-md);
  color: var(--text-strong);
  background: linear-gradient(150deg, rgba(94, 231, 255, 0.14), rgba(155, 140, 255, 0.14));
  border: 2px solid rgba(155, 140, 255, 0.35);
  font-size: 27px;
  font-weight: 900;
  transition: transform 0.14s ease, border-color 0.14s ease;
}

.column-option:hover:not(:disabled) {
  transform: translateY(-3px);
  border-color: var(--brand);
}

.column-option.wrong {
  border-color: var(--danger);
  background: rgba(255, 107, 125, 0.18);
}

.column-option.right {
  border-color: var(--success);
  background: rgba(85, 230, 165, 0.18);
}

.message {
  min-height: 66px;
  padding: 11px 14px;
  border-radius: var(--radius-sm);
  color: var(--text);
  background: rgba(255, 206, 77, 0.08);
  border: 1px solid rgba(255, 206, 77, 0.25);
  line-height: 1.45;
  font-weight: 700;
}

.message.success {
  color: var(--success);
  border-color: rgba(85, 230, 165, 0.35);
  background: rgba(85, 230, 165, 0.08);
}

.cause-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}

.cause-card {
  display: flex;
  align-items: center;
  gap: 13px;
}

.cause-card > span {
  font-size: 34px;
}

.cause-card h3 {
  margin-bottom: 4px;
  font-size: 16px;
}

.cause-card p {
  color: var(--text);
  font-size: 13px;
  line-height: 1.45;
}

@media (max-width: 720px) {
  .mode-card,
  .hero {
    align-items: flex-start;
    flex-direction: column;
  }

  .workshop {
    grid-template-columns: 1fr;
  }

  .cause-grid {
    grid-template-columns: 1fr;
  }
}
</style>
