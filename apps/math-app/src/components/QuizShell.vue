<script setup>
/**
 * QuizShell — 通用答题壳。
 *
 * 把「一轮 N 题」的所有共性收在这里：题目切换、选项/键盘两种作答方式、
 * 键盘快捷键、判题与反馈动画、星星与连击、进度条、错因标签、轮次总结。
 * 各模块只负责生成题目和渲染题面（question 插槽），不再各写一遍这套流程。
 *
 * 题目协议（数组的每一项）：
 * {
 *   id, skill,                  // skill 用于上报掌握度，id 用于错题本去重
 *   answer: Number,             // 唯一正确答案
 *   options: Number[],          // 选择模式下的候选项
 *   unit: String,               // 单位，显示在选项与答案框里
 *   title | text | prompt,      // 错题本里这道题显示成什么，缺省用「第 n 题」兜底
 *   difficulty: *,              // 属于哪个难度档（配合 difficultySteps 做自适应）
 *   hint | hints: String[],     // 分级提示，用一级扣一颗星
 *   stars: Number | (ctx) => Number,  // 答对基础星数，默认 1；函数形式可按连击/秒答加成
 *   xp: Number,                 // 答对经验，默认 10
 *   tag: String,                // 透传给 progress.recordAnswer 的成就计数标记
 *   errorTags: String[] | (answered, question) => String[],
 * }
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import gsap from 'gsap'
import MascotBot from '@/components/MascotBot.vue'
import SessionBar from '@/components/SessionBar.vue'
import RoundSummary from '@/components/RoundSummary.vue'
import { useProgressStore, wrongBookKey } from '@/stores/progress.js'
import { useFeedback } from '@/composables/useFeedback'
import { errorTagInfo } from '@/data/errorTags.js'
import { createAdaptiveEngine } from '@/core/engine/adaptive.js'
import { sample } from '@/utils/random'
import { sound } from '@/utils/sound'

const props = defineProps({
  moduleId: { type: String, required: true },
  moduleName: { type: String, default: '本轮练习' },
  /** 本轮题目，长度即轮次题数；换数组等于换一轮。 */
  questions: { type: Array, required: true },
  inputMode: { type: String, default: 'choice' }, // choice | keypad
  allowModeToggle: { type: Boolean, default: true },
  /** 在这个毫秒数内答对额外奖励一颗星；0 表示不启用秒答奖励。 */
  speedBonusMs: { type: Number, default: 0 },
  maxDigits: { type: Number, default: 3 },
  /** 全对时额外奖励的星星。 */
  perfectBonus: { type: Number, default: 0 },
  /** 判完到进入下一题的停留时间。 */
  feedbackDelay: { type: Number, default: 1400 },
  /** 每用一级提示扣的星星。 */
  hintCost: { type: Number, default: 1 },
  hintLabels: { type: Array, default: () => ['💡 给点提示', '🧮 再给一点'] },
  /** 题间随机播报的鼓励语。 */
  prompts: { type: Array, default: () => ['算一算，答案是多少？'] },
  /** 键盘模式下是否渲染内置答案框（题面里已有填空位时关掉）。 */
  showAnswerSlot: { type: Boolean, default: true },
  /** 自适应调度：按掌握度 EMA 决定本轮剩下的题先出哪一道。 */
  adaptive: { type: Boolean, default: true },
  /** 难度档序列（由易到难）；给了才会按连对/连错发出升降档建议。 */
  difficultySteps: { type: Array, default: () => [] },
  /** 当前难度档，配合 difficultySteps 使用。 */
  difficulty: { type: [String, Number], default: null },
})

const emit = defineEmits([
  'update:inputMode',
  'graded',
  'finished',
  'replay',
  'home',
  'advance',
  'adapt',
])

const progress = useProgressStore()
const {
  correct: fxCorrect,
  wrong: fxWrong,
  celebrate: fxCelebrate,
  burst,
  flyStar,
  pop,
  enter
} = useFeedback()

const total = computed(() => props.questions.length)

const index = ref(0)
/** order[i] = 第 i 个出场的题在 props.questions 里的下标，自适应调度只改这个映射。 */
const order = ref([])
const marks = ref([])
const correctCount = ref(0)
const starsEarned = ref(0)
const fastAnswers = ref(0)
const showSummary = ref(false)
const locked = ref(false)
const chosen = ref(null)
const typed = ref('')
const hintLevel = ref(0)
const mood = ref('idle')
const message = ref(props.prompts[0] ?? '')
const lastResult = ref(null)
const questionStart = ref(Date.now())

const stageRef = ref(null)
const promptRef = ref(null)

const current = computed(() => props.questions[order.value[index.value] ?? index.value] ?? null)
const hints = computed(() => {
  const q = current.value
  if (!q) return []
  if (Array.isArray(q.hints)) return q.hints
  return q.hint ? [q.hint] : []
})
const canHint = computed(() => !locked.value && hintLevel.value < hints.value.length)
const percent = computed(() => (total.value ? Math.round((index.value / total.value) * 100) : 0))

/** 传给各插槽的上下文，题面组件靠它拿到当前题与作答状态。 */
const slotCtx = computed(() => ({
  question: current.value,
  index: index.value,
  total: total.value,
  locked: locked.value,
  chosen: chosen.value,
  typed: typed.value,
  hintLevel: hintLevel.value,
  result: lastResult.value,
}))

const shownTags = computed(() =>
  (lastResult.value?.correct === false ? lastResult.value.errorTags : []).map((id) => ({
    id,
    ...errorTagInfo(id),
  })),
)

/* ----------------------------------------------------- 自适应 / 错题本 */

const keyOf = (q) => wrongBookKey(props.moduleId, q?.id ?? `${q?.skill ?? 'q'}-${q?.answer}`)

/** 错题本列表里显示的题面；各玩法字段名不统一，这里统一兜底，绝不写出 undefined。 */
function titleOf(q, position) {
  for (const candidate of [q?.title, q?.text, q?.prompt, q?.equation]) {
    if (typeof candidate === 'string' && candidate.trim()) return candidate.trim()
  }
  return `${props.moduleName} · 第 ${position + 1} 题`
}

/** 这个玩法当前还欠着几道错题，答题时一直挂在进度条下面提醒。 */
const wrongOwed = computed(() => progress.wrongOfModule(props.moduleId).length)

let engine = createAdaptiveEngine({})

function makeEngine() {
  engine = createAdaptiveEngine({
    mastery: progress.state.mastery,
    wrongBook: progress.state.wrongBook,
    steps: props.difficultySteps,
    difficulty: props.difficulty,
    wrongKeyOf: keyOf,
  })
}

/**
 * 把「下一道」换成引擎挑中的那道：只在剩下的题里做一次交换，
 * 每道题仍然恰好出一次，进度条与本轮题数都不受影响。
 */
function planNext() {
  const at = index.value + 1
  if (!props.adaptive || at >= order.value.length) return
  const tail = order.value.slice(at)
  const picked = engine.pickNextQuestion(tail.map((i) => props.questions[i]))
  if (!picked || picked.index === 0) return
  const swapped = [...order.value]
  const target = at + picked.index
  ;[swapped[at], swapped[target]] = [swapped[target], swapped[at]]
  order.value = swapped
}

/* ---------------------------------------------------------------- 判题 */

function tagsFor(q, answered) {
  const raw = typeof q.errorTags === 'function' ? q.errorTags(answered, q) : q.errorTags
  return Array.isArray(raw) ? raw.filter(Boolean) : []
}

function grade(value, anchor) {
  const q = current.value
  if (!q) return
  const right = value === q.answer
  const elapsed = Date.now() - questionStart.value
  marks.value[index.value] = right ? 'ok' : 'no'
  chosen.value = value

  if (right) {
    const fast = props.speedBonusMs > 0 && elapsed < props.speedBonusMs
    if (fast) fastAnswers.value += 1
    // combo 传入的是「算上这一题」的连击数，recordAnswer 之后 store 里才会自增
    const ctx = { combo: progress.combo + 1, fast, elapsed, hintLevel: hintLevel.value }
    const base = typeof q.stars === 'function' ? q.stars(ctx) : (q.stars ?? 1)
    const stars = Math.max(1, base + (fast ? 1 : 0) - hintLevel.value * props.hintCost)
    correctCount.value += 1
    starsEarned.value += stars
    progress.recordAnswer(props.moduleId, true, {
      skill: q.skill,
      stars,
      xp: q.xp ?? 10,
      tag: q.tag,
    })
    // 这道题原本欠在错题本里：答对就把它放出去，比多给一颗星更有成就感
    const redeemed = progress.clearWrong(keyOf(q))
    // recordAnswer 已把本题计入 combo，音效因此能随连续答对逐级升高。
    fxCorrect(anchor, { streak: progress.combo })
    burst(anchor, { count: 16 + Math.min(10, progress.combo * 2) })
    flyStar(anchor)
    mood.value = 'cheer'
    message.value = redeemed
      ? `错题拿下！这道题从错题本里飞走啦 📕✨ +${stars} ⭐`
      : fast
        ? `又快又准！+${stars} ⭐`
        : progress.combo >= 3
          ? `${progress.combo} 连击，火力全开 🔥 +${stars} ⭐`
          : sample(['答对啦！', '算得很好 👏', '完全正确 ✅'])
    lastResult.value = {
      correct: true,
      value,
      answer: q.answer,
      stars,
      elapsed,
      errorTags: [],
      redeemed,
    }
  } else {
    const errorTags = tagsFor(q, value)
    progress.recordAnswer(props.moduleId, false, { skill: q.skill, errorTags })
    progress.recordWrong({
      id: keyOf(q),
      module: props.moduleId,
      skill: q.skill,
      errorTag: errorTags[0],
      errorTags,
      title: titleOf(q, index.value),
      answer: q.answer,
      options: Array.isArray(q.options) ? q.options : [],
      unit: q.unit ?? '',
      hint: hints.value[0] ?? '',
      lastWrong: value,
    })
    fxWrong(anchor)
    mood.value = 'sad'
    message.value = `正确答案是 ${q.answer}${q.unit ?? ''}，已记进错题本 📕`
    lastResult.value = {
      correct: false,
      value,
      answer: q.answer,
      stars: 0,
      elapsed,
      errorTags,
      redeemed: false,
    }
  }

  // 掌握度 EMA 与连对/连错都交给引擎，升降档只发建议，换不换档由父组件决定
  const adapt = engine.record(q.skill, right)
  if (adapt.changed) emit('adapt', adapt)
  planNext()

  // 用完提示就把剩下的提示全部摊开，讲评时孩子能看到完整思路
  hintLevel.value = hints.value.length
  emit('graded', { question: q, ...lastResult.value })
}

function submit(value, anchor) {
  if (locked.value || current.value == null) return
  locked.value = true
  grade(value, anchor)
  setTimeout(next, props.feedbackDelay)
}

function chooseOption(value, e) {
  submit(value, e.currentTarget)
}

function submitTyped() {
  if (typed.value === '') return
  submit(Number(typed.value), promptRef.value ?? stageRef.value)
}

function tapKey(k) {
  if (locked.value) return
  sound.click()
  if (k === 'del') {
    typed.value = typed.value.slice(0, -1)
    return
  }
  if (typed.value.length >= props.maxDigits) return
  typed.value = `${typed.value}${k}`
}

/* ------------------------------------------------------------ 轮次流转 */

function next() {
  chosen.value = null
  typed.value = ''
  hintLevel.value = 0
  locked.value = false
  lastResult.value = null
  mood.value = 'idle'
  if (index.value + 1 >= total.value) {
    finish()
    return
  }
  index.value += 1
  message.value = sample(props.prompts)
  questionStart.value = Date.now()
  // 自适应换过顺序，父组件要的是「现在这道题在题库里的下标」
  emit('advance', order.value[index.value] ?? index.value)
  animateIn()
}

function finish() {
  const perfect = total.value > 0 && correctCount.value === total.value
  const bonus = perfect ? props.perfectBonus : 0
  progress.finishSession(props.moduleId, {
    correct: correctCount.value,
    total: total.value,
    bonusStars: bonus,
  })
  starsEarned.value += bonus
  showSummary.value = true
  // 全对才放大庆祝：音效 + 加倍粒子 + 一串震动，都走共用反馈的降级规则
  if (perfect) fxCelebrate(stageRef.value)
  emit('finished', { correct: correctCount.value, total: total.value, stars: starsEarned.value })
}

function restart() {
  index.value = 0
  order.value = props.questions.map((_, i) => i)
  makeEngine()
  marks.value = []
  correctCount.value = 0
  starsEarned.value = 0
  fastAnswers.value = 0
  showSummary.value = false
  locked.value = false
  chosen.value = null
  typed.value = ''
  hintLevel.value = 0
  lastResult.value = null
  mood.value = 'idle'
  message.value = props.prompts[0] ?? ''
  questionStart.value = Date.now()
  progress.resetCombo()
  emit('advance', order.value[0] ?? 0)
  animateIn()
}

function animateIn() {
  requestAnimationFrame(() => {
    if (promptRef.value) {
      gsap.fromTo(
        promptRef.value,
        { opacity: 0, scale: 0.94 },
        { opacity: 1, scale: 1, duration: 0.3, ease: 'back.out(1.8)', clearProps: 'transform' },
      )
    }
    enter([...(stageRef.value?.querySelectorAll('.opt') ?? [])], { stagger: 0.05, y: 14 })
  })
}

function moreHint() {
  if (!canHint.value) return
  sound.click()
  hintLevel.value += 1
}

function toggleMode() {
  sound.click()
  emit('update:inputMode', props.inputMode === 'choice' ? 'keypad' : 'choice')
  typed.value = ''
  pop(stageRef.value, { scale: 1.01 })
}

/* -------------------------------------------------------------- 键盘 */

function onKeydown(e) {
  if (showSummary.value || locked.value) return
  if (props.inputMode === 'keypad') {
    if (/^[0-9]$/.test(e.key)) tapKey(e.key)
    else if (e.key === 'Backspace') tapKey('del')
    else if (e.key === 'Enter') submitTyped()
    else return
    e.preventDefault()
    return
  }
  // 选择模式下 1..9 直接选第 n 个选项，键盘用户不用 Tab 一路走过去
  const opts = current.value?.options ?? []
  const n = Number(e.key)
  if (Number.isInteger(n) && n >= 1 && n <= opts.length) {
    const el = stageRef.value?.querySelectorAll('.opt')[n - 1]
    submit(opts[n - 1], el)
    e.preventDefault()
  }
}

// 父组件换一批题（改难度、再来一轮）就重置整个轮次
watch(() => props.questions, restart)

onMounted(() => {
  restart()
  window.addEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

/** 让父组件把一句话写进吉祥物的台词行（下一次判题会覆盖它）。 */
function announce(text) {
  if (typeof text === 'string' && text.trim()) message.value = text
}

defineExpose({ restart, announce, index, current, locked, typed })
</script>

<template>
  <div class="quiz-shell stack">
    <section v-if="$slots.controls || allowModeToggle" class="card quiz-controls">
      <slot name="controls" />
      <div class="spacer" />
      <button v-if="allowModeToggle" class="btn btn--ghost btn--sm" @click="toggleMode">
        {{ inputMode === 'choice' ? '⌨️ 改为输入' : '🔢 改为选择' }}
      </button>
    </section>

    <section class="card quiz-bar">
      <SessionBar
        :index="index"
        :total="total"
        :correct="correctCount"
        :streak="progress.combo"
        :marks="marks"
      />
      <div
        class="progress-track"
        role="progressbar"
        :aria-valuenow="percent"
        aria-valuemin="0"
        aria-valuemax="100"
        :aria-label="`本轮进度 ${percent}%`"
      >
        <span class="progress-fill" :style="{ width: `${percent}%` }" />
      </div>
      <div class="bar-foot">
        <span class="chip">⭐ 本轮 {{ starsEarned }}</span>
        <span v-if="fastAnswers" class="chip">⚡ 秒答 {{ fastAnswers }}</span>
        <span v-if="wrongOwed" class="chip owed" :title="'答对同一道题就能把它移出错题本'">
          📕 错题本 {{ wrongOwed }}
        </span>
        <slot name="bar-extra" v-bind="slotCtx" />
      </div>
    </section>

    <section v-if="current" ref="stageRef" class="card quiz-stage">
      <header class="stage-head">
        <!--
          默认是那只只会做表情的机器人；玩法页想让它变成能点触的陪跑伙伴，
          就用 mascot 插槽换一只 interactive 的进来，再用 announce() 把它说的话
          写进下面这行台词里。
        -->
        <slot name="mascot" :mood="mood" :message="message">
          <MascotBot :mood="mood" :size="72" />
        </slot>
        <p class="muted say" role="status">{{ message }}</p>
        <div class="spacer" />
        <slot name="head-extra" v-bind="slotCtx" />
        <button
          v-if="hints.length"
          class="btn btn--ghost btn--sm"
          :disabled="!canHint"
          @click="moreHint"
        >
          {{ hintLabels[Math.min(hintLevel, hintLabels.length - 1)] }}
        </button>
      </header>

      <div ref="promptRef" class="quiz-prompt">
        <slot name="question" v-bind="slotCtx" />
      </div>

      <slot name="beneath" v-bind="slotCtx" />

      <p v-for="(h, i) in hints.slice(0, hintLevel)" :key="i" class="quiz-hint">💡 {{ h }}</p>

      <!-- 错因归因：答错时告诉孩子「错在哪一类」，而不只是「错了」 -->
      <div v-if="shownTags.length" class="why">
        <span class="why-head">错因</span>
        <span v-for="t in shownTags" :key="t.id" class="why-chip" :title="t.tip">{{ t.label }}</span>
        <p v-if="shownTags[0].tip" class="why-tip">{{ shownTags[0].tip }}</p>
      </div>

      <slot name="extra" v-bind="slotCtx" />

      <div v-if="inputMode === 'choice'" class="options">
        <button
          v-for="(o, i) in current.options"
          :key="o"
          class="opt"
          :class="{
            right: locked && o === current.answer,
            bad: locked && chosen === o && o !== current.answer,
          }"
          :disabled="locked"
          :aria-keyshortcuts="String(i + 1)"
          @click="chooseOption(o, $event)"
        >
          {{ o }}<small v-if="current.unit">{{ current.unit }}</small>
        </button>
      </div>

      <div v-else class="keypad-wrap">
        <div v-if="showAnswerSlot" class="answer-slot" :class="{ filled: typed !== '' }">
          {{ typed || '?' }}<small v-if="current.unit">{{ current.unit }}</small>
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
        <p class="dim tiny">也可以用键盘数字键输入，回车提交</p>
      </div>
    </section>

    <RoundSummary
      v-if="showSummary"
      :correct="correctCount"
      :total="total"
      :stars-earned="starsEarned"
      :module-name="moduleName"
      @replay="emit('replay')"
      @home="emit('home')"
    />
  </div>
</template>

<style scoped>
.quiz-controls {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  align-items: center;
  padding: 14px 18px;
}

.quiz-bar {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 18px;
}

.progress-track {
  height: 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  overflow: hidden;
}

.progress-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--brand), var(--accent), var(--star));
  transition: width 0.35s ease;
}

.bar-foot {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.owed {
  background: rgba(255, 122, 198, 0.18);
  border-color: rgba(255, 122, 198, 0.5);
}

.quiz-stage {
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
  flex: 1;
  min-width: 180px;
}

.quiz-hint {
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  background: rgba(255, 206, 77, 0.12);
  border: 1px solid rgba(255, 206, 77, 0.4);
  color: var(--star);
  font-size: 14px;
}

.why {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  background: rgba(255, 107, 125, 0.12);
  border: 1px solid rgba(255, 107, 125, 0.42);
}

.why-head {
  font-size: 13px;
  font-weight: 900;
  color: var(--danger);
}

.why-chip {
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 800;
  background: rgba(255, 107, 125, 0.22);
  border: 1px solid rgba(255, 107, 125, 0.5);
  color: var(--text-strong);
}

.why-tip {
  flex-basis: 100%;
  font-size: 13px;
  color: var(--text);
}

.options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
}

.opt {
  padding: 22px 10px;
  font-size: 30px;
  font-weight: 900;
  border-radius: var(--radius-md);
  background: linear-gradient(160deg, rgba(255, 206, 77, 0.16), rgba(255, 159, 69, 0.14));
  border: 2px solid rgba(255, 206, 77, 0.42);
  transition: transform 0.14s ease, box-shadow 0.14s ease;
}

.opt small {
  font-size: 14px;
  color: var(--text);
  margin-left: 2px;
}

.opt:hover:not(:disabled) {
  transform: translateY(-3px);
  box-shadow: 0 10px 24px rgba(255, 159, 69, 0.26);
}

.opt.right {
  background: rgba(85, 230, 165, 0.28);
  border-color: var(--success);
}

.opt.bad {
  background: rgba(255, 107, 125, 0.26);
  border-color: var(--danger);
}

.keypad-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.answer-slot {
  min-width: 160px;
  padding: 10px 20px;
  text-align: center;
  font-size: 34px;
  font-weight: 900;
  color: var(--brand);
  border-radius: var(--radius-sm);
  border: 3px dashed rgba(94, 231, 255, 0.55);
}

.answer-slot.filled {
  border-style: solid;
  background: rgba(94, 231, 255, 0.12);
}

.answer-slot small {
  font-size: 16px;
  color: var(--text);
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
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.16);
  transition: transform 0.12s ease, background 0.12s ease;
}

.key:hover:not(:disabled) {
  transform: translateY(-2px);
  background: rgba(255, 255, 255, 0.16);
}

.key.del {
  color: var(--neon-orange);
}

.key.wide {
  font-size: 18px;
  background: linear-gradient(135deg, var(--brand), var(--accent));
  color: var(--text-invert);
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
