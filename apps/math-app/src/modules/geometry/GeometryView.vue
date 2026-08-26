<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import gsap from 'gsap'
import MascotBot from '@/components/MascotBot.vue'
import SessionBar from '@/components/SessionBar.vue'
import RoundSummary from '@/components/RoundSummary.vue'
import ShapeGlyph from '@/components/ShapeGlyph.vue'
import { useProgressStore } from '@/stores/progress.js'
import { useFeedback } from '@/composables/useFeedback'
import { REAL_OBJECTS, SHAPES, SHAPES_2D, SHAPES_3D } from '@/data/shapes'
import { geometrySkill } from '@/data/skill-mapping.js'
import { numericOptions, pick, sample, shuffle } from '@/utils/random'
import { sound } from '@/utils/sound'

const ROUND_SIZE = 10
const MODULE_ID = 'geometry'
const PALETTE = ['#5ee7ff', '#9b8cff', '#ff7ac6', '#ffce4d', '#55e6a5', '#ff9f45']

const router = useRouter()
const progress = useProgressStore()
const { correct: fxCorrect, wrong: fxWrong, burst, flyStar, enter } = useFeedback()

const scope = ref('2d') // 2d | 3d | all
const pool = computed(() =>
  scope.value === '2d' ? SHAPES_2D : scope.value === '3d' ? SHAPES_3D : SHAPES,
)

const questions = ref([])
const index = ref(0)
const marks = ref([])
const correctCount = ref(0)
const starsEarned = ref(0)
const showSummary = ref(false)
const locked = ref(false)
const chosen = ref(null)
const mood = ref('idle')
const message = ref('在陨石群里找出正确的图形吧！')
const showFact = ref(false)
const stageRef = ref(null)

const current = computed(() => questions.value[index.value] ?? null)

/** 题型 1：给名字，从 4 个陨石里点出对应图形。 */
function makeFindByName(list) {
  const [target, ...rest] = pick(list, 4)
  const choices = shuffle([target, ...rest]).map((s, i) => ({
    ...s,
    color: PALETTE[i % PALETTE.length],
  }))
  return {
    type: 'find',
    prompt: `哪一个是「${target.name}」？`,
    answer: target.id,
    target,
    choices,
    fact: target.fact,
  }
}

/** 题型 2：给图形，从 4 个名字里选。 */
function makeNameIt(list) {
  const [target, ...rest] = pick(list, 4)
  return {
    type: 'name',
    prompt: '这个图形叫什么名字？',
    answer: target.name,
    target,
    color: sample(PALETTE),
    choices: shuffle([target, ...rest]).map((s) => s.name),
    fact: target.fact,
  }
}

/** 题型 3：数一数这个图形有几条边。 */
function makeCountSides(list) {
  const candidates = list.filter((s) => s.dim === '2d' && s.sides >= 3)
  const target = sample(candidates.length ? candidates : SHAPES_2D.filter((s) => s.sides >= 3))
  return {
    type: 'sides',
    prompt: `「${target.name}」有几条边？`,
    answer: target.sides,
    target,
    color: sample(PALETTE),
    choices: numericOptions(target.sides, { count: 4, spread: 3, min: 1, max: 12 }),
    fact: target.fact,
  }
}

/** 题型 4：生活中的物体是什么形状。 */
function makeRealObject(list) {
  const ids = new Set(list.map((s) => s.id))
  const usable = REAL_OBJECTS.filter((o) => ids.has(o.shape))
  if (usable.length < 1) return makeNameIt(list)
  const obj = sample(usable)
  const target = SHAPES.find((s) => s.id === obj.shape)
  const distractors = pick(
    list.filter((s) => s.id !== target.id),
    3,
  )
  return {
    type: 'real',
    prompt: `${obj.emoji} ${obj.label}是什么形状？`,
    answer: target.id,
    target,
    obj,
    choices: shuffle([target, ...distractors]).map((s, i) => ({
      ...s,
      color: PALETTE[i % PALETTE.length],
    })),
    fact: target.fact,
  }
}

/** 题型 5：找出「不一样」的那一个（另外三个同类）。 */
function makeOddOne(list) {
  const family = list.filter((s) => s.dim === list[0].dim)
  const base = family.length >= 4 ? family : SHAPES
  const group = pick(
    base.filter((s) => s.sides === 4),
    3,
  )
  if (group.length < 3) return makeFindByName(list)
  const odd = sample(base.filter((s) => s.sides !== 4))
  const choices = shuffle([...group, odd]).map((s, i) => ({
    ...s,
    color: PALETTE[i % PALETTE.length],
  }))
  return {
    type: 'odd',
    prompt: '哪一个不是四条边的图形？',
    answer: odd.id,
    target: odd,
    choices,
    fact: `${odd.name}：${odd.fact}`,
  }
}

function buildQuestion(i) {
  const list = pool.value
  const makers = [makeFindByName, makeNameIt, makeCountSides, makeRealObject, makeOddOne]
  const weights = scope.value === '3d' ? [0, 1, 3] : [0, 1, 2, 3, 4]
  const idx = i < 2 ? weights[i % weights.length] : sample(weights)
  return makers[idx](list)
}

/* ---------- 判题 ---------- */

function grade(value, anchor) {
  const q = current.value
  const right = value === q.answer
  marks.value[index.value] = right ? 'ok' : 'no'
  chosen.value = value
  // 映射到 curriculum 技能点，让自适应掌握度引擎能收到反馈
  const skill = geometrySkill(q.target)

  if (right) {
    const stars = q.target.dim === '3d' ? 2 : 1
    correctCount.value += 1
    starsEarned.value += stars
    progress.recordAnswer(MODULE_ID, true, { skill, stars, xp: 12 })
    fxCorrect(anchor)
    burst(anchor, { count: 18 })
    flyStar(anchor)
    mood.value = 'cheer'
    message.value = sample(['找到啦！', '眼力真好 👀', '完全正确 ✅'])
  } else {
    progress.recordAnswer(MODULE_ID, false, { skill })
    fxWrong(anchor)
    mood.value = 'sad'
    message.value = `这是「${q.target.name}」。${q.fact}`
  }
  showFact.value = true
}

function answer(value, e) {
  if (locked.value) return
  locked.value = true
  grade(value, e.currentTarget)
  setTimeout(next, 1600)
}

function next() {
  chosen.value = null
  showFact.value = false
  locked.value = false
  mood.value = 'idle'
  if (index.value + 1 >= ROUND_SIZE) {
    finish()
    return
  }
  index.value += 1
  message.value = '看清楚每一个陨石的形状～'
  animateIn()
}

function finish() {
  const perfect = correctCount.value === ROUND_SIZE
  progress.finishSession(MODULE_ID, {
    correct: correctCount.value,
    total: ROUND_SIZE,
    bonusStars: perfect ? 3 : 0,
  })
  if (perfect) starsEarned.value += 3
  showSummary.value = true
}

function startRound() {
  questions.value = Array.from({ length: ROUND_SIZE }, (_, i) => buildQuestion(i))
  index.value = 0
  marks.value = []
  correctCount.value = 0
  starsEarned.value = 0
  showSummary.value = false
  locked.value = false
  chosen.value = null
  showFact.value = false
  mood.value = 'idle'
  message.value = '在陨石群里找出正确的图形吧！'
  progress.resetCombo()
  animateIn()
}

function animateIn() {
  requestAnimationFrame(() => {
    gsap.fromTo(
      '.rock',
      { opacity: 0, scale: 0.7, rotate: -20 },
      { opacity: 1, scale: 1, rotate: 0, duration: 0.42, stagger: 0.07, ease: 'back.out(2)' },
    )
    enter([...document.querySelectorAll('.word-opt')], { stagger: 0.05, y: 14 })
    if (stageRef.value) {
      gsap.fromTo(
        '.hero-shape',
        { scale: 0.75, opacity: 0 },
        { scale: 1, opacity: 1, duration: 0.4, ease: 'back.out(2)' },
      )
    }
  })
}

function setScope(v) {
  if (scope.value === v) return
  sound.click()
  scope.value = v
}

watch(scope, startRound)
onMounted(startRound)
</script>

<template>
  <main class="page stack">
    <section class="card controls">
      <div class="seg" role="group" aria-label="图形范围">
        <button class="seg-btn" :class="{ on: scope === '2d' }" @click="setScope('2d')">
          ▲ 平面图形
        </button>
        <button class="seg-btn" :class="{ on: scope === '3d' }" @click="setScope('3d')">
          🧊 立体图形
        </button>
        <button class="seg-btn" :class="{ on: scope === 'all' }" @click="setScope('all')">
          ✨ 全部混合
        </button>
      </div>
      <div class="spacer" />
      <span class="chip">共 {{ pool.length }} 种图形</span>
    </section>

    <section class="card bar-panel">
      <SessionBar
        :index="index"
        :total="ROUND_SIZE"
        :correct="correctCount"
        :streak="progress.combo"
        :marks="marks"
      />
    </section>

    <section v-if="current" ref="stageRef" class="card stage">
      <header class="stage-head">
        <MascotBot :mood="mood" :size="72" />
        <div class="head-text">
          <h2 class="prompt">{{ current.prompt }}</h2>
          <p class="muted say">{{ message }}</p>
        </div>
      </header>

      <!-- 需要展示单个大图形的题型 -->
      <div
        v-if="current.type === 'name' || current.type === 'sides'"
        class="hero-shape"
      >
        <ShapeGlyph
          :shape="current.target.id"
          :size="170"
          :color="current.color"
          :label="current.target.name"
        />
      </div>

      <!-- 选图形（陨石群） -->
      <div
        v-if="current.type === 'find' || current.type === 'real' || current.type === 'odd'"
        class="rocks"
      >
        <button
          v-for="c in current.choices"
          :key="c.id"
          class="opt rock"
          :class="{
            right: locked && c.id === current.answer,
            bad: locked && chosen === c.id && c.id !== current.answer,
          }"
          :disabled="locked"
          :aria-label="c.name"
          @click="answer(c.id, $event)"
        >
          <ShapeGlyph :shape="c.id" :size="96" :color="c.color" :label="c.name" />
          <span v-if="locked" class="rock-name">{{ c.name }}</span>
        </button>
      </div>

      <!-- 选名字 / 选边数 -->
      <div v-else class="word-options">
        <button
          v-for="c in current.choices"
          :key="c"
          class="opt word-opt"
          :class="{
            right: locked && c === current.answer,
            bad: locked && chosen === c && c !== current.answer,
          }"
          :disabled="locked"
          @click="answer(c, $event)"
        >
          {{ c }}{{ current.type === 'sides' ? ' 条' : '' }}
        </button>
      </div>

      <p v-if="showFact" class="fact">💡 {{ current.fact }}</p>
    </section>

    <RoundSummary
      v-if="showSummary"
      :correct="correctCount"
      :total="ROUND_SIZE"
      :stars-earned="starsEarned"
      module-name="形状卫星"
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
  background: linear-gradient(135deg, var(--pink), var(--violet));
  color: #1a0a22;
  box-shadow: 0 6px 16px rgba(255, 122, 198, 0.32);
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

.hero-shape {
  display: grid;
  place-items: center;
  padding: 12px;
  border-radius: var(--radius-m);
  background:
    radial-gradient(60% 80% at 50% 40%, rgba(155, 140, 255, 0.16), transparent 70%),
    rgba(6, 9, 30, 0.4);
  border: 1px solid rgba(155, 140, 255, 0.24);
}

.rocks {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 14px;
}

.rock {
  display: grid;
  place-items: center;
  gap: 6px;
  padding: 16px 8px;
  border-radius: var(--radius-m);
  background:
    radial-gradient(70% 70% at 30% 25%, rgba(255, 255, 255, 0.1), transparent 70%),
    rgba(255, 255, 255, 0.05);
  border: 2px solid rgba(255, 255, 255, 0.12);
  transition: transform 0.16s ease, box-shadow 0.16s ease, border-color 0.16s ease;
}

.rock:hover:not(:disabled) {
  transform: translateY(-5px) rotate(-2deg);
  border-color: rgba(94, 231, 255, 0.55);
  box-shadow: 0 14px 30px rgba(94, 231, 255, 0.2);
}

.rock.right {
  border-color: var(--green);
  background: rgba(85, 230, 165, 0.16);
}

.rock.bad {
  border-color: var(--red);
  background: rgba(255, 107, 125, 0.16);
}

.rock-name {
  font-size: 13px;
  font-weight: 800;
  color: var(--ink-soft);
}

.word-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
}

.word-opt {
  padding: 18px 12px;
  font-size: 20px;
  font-weight: 900;
  border-radius: var(--radius-m);
  background: linear-gradient(160deg, rgba(255, 122, 198, 0.16), rgba(155, 140, 255, 0.16));
  border: 2px solid rgba(255, 122, 198, 0.4);
  transition: transform 0.14s ease, box-shadow 0.14s ease;
}

.word-opt:hover:not(:disabled) {
  transform: translateY(-3px);
  box-shadow: 0 10px 24px rgba(255, 122, 198, 0.24);
}

.word-opt.right {
  background: rgba(85, 230, 165, 0.28);
  border-color: var(--green);
}

.word-opt.bad {
  background: rgba(255, 107, 125, 0.26);
  border-color: var(--red);
}

.fact {
  padding: 12px 16px;
  border-radius: var(--radius-s);
  background: rgba(94, 231, 255, 0.1);
  border: 1px solid rgba(94, 231, 255, 0.32);
  color: var(--ink-soft);
  font-size: 14px;
}

@media (max-width: 560px) {
  .prompt {
    font-size: 18px;
  }
}
</style>
