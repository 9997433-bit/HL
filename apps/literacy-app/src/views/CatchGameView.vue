<script setup>
/**
 * 接字大冒险。
 *
 * 字从天上一格一格掉下来，孩子推着小篮子在四条轨道间左右挪，
 * 接住题目要的那个字、躲开别的字。前面几款小游戏都可以慢慢看、慢慢想，
 * 这一款练的是「一眼认出来」——字形已经认得了，才追得上掉下来的速度。
 *
 * 掉落用「整格」而不是像素：每一拍所有字往下挪一行，接没接到只看
 * 「到底那一拍篮子在不在这条轨道上」。这样规则孩子一看就懂，
 * 减少动效时把过渡关掉、节拍放慢，玩法一点没变，只是不再有滑动的残影。
 *
 * 键盘是第一操作方式：舞台自己可聚焦，方向键 / A D 换轨道；
 * 触屏用下面那两个大按钮。看不见画面的孩子靠播报也能玩：
 * 每次换轨道都会说清楚「这条轨道上方掉着什么字、还有几格到篮子」。
 */
import { computed, onBeforeUnmount, ref } from 'vue'
import CelebrationOverlay from '@/components/CelebrationOverlay.vue'
import VoiceNotice from '@/components/VoiceNotice.vue'
import { useCharPool } from '@/composables/useCharPool.js'
import { useFeedback } from '@/composables/useFeedback.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { isSpeechSupported, speak, stopSpeaking } from '@/utils/speech.js'
import { pick, sample } from '@/utils/random.js'

/** 四条轨道、五格高：一个字从冒头到落进篮子有五拍时间反应。 */
const LANES = 4
const ROWS = 5
/** 三波，每波接住 3 个目标字就换字。 */
const WAVES = 3
const PER_WAVE = 3
const LIVES = 3
/** 一拍多久：减少动效时放慢，让「看清楚」不再依赖手速。 */
const BEAT_MS = 780
const CALM_BEAT_MS = 1250
/** 场上同时最多几个字，再多就看不过来了。 */
const MAX_ITEMS = 4

const progress = useProgressStore()
const settings = useSettingsStore()
const feedback = useFeedback()
const { pool, usingFallback, drawPool } = useCharPool(4)

const speechOk = isSpeechSupported()

const stageRef = ref(null)

const phase = ref('intro') // intro | playing | done
const wave = ref(0)
const caught = ref(0)
const score = ref(0)
const misses = ref(0)
const lives = ref(LIVES)
/** 连着接对几个；音高跟着它一级级往上走。 */
const streak = ref(0)
const lane = ref(Math.floor(LANES / 2))
const items = ref([])
const target = ref(null)
const distractors = ref([])
const celebrating = ref(false)
const announcement = ref('')

let beatTimer = null
let seq = 0

function announce(text) {
  // 同一句话写两次读屏不会再念，补个零宽空格逼它重播
  announcement.value = announcement.value === text ? `${text}\u200b` : text
}

const quiet = computed(() => feedback.reducedMotion())
const beatMs = computed(() => (quiet.value ? CALM_BEAT_MS : BEAT_MS))

/* -------------------------------------------------------------- 出题 */

function newWave() {
  const { due, all } = drawPool()
  const preferred = due.length && Math.random() < 0.6 ? due : all
  const chosen = pick(preferred) ?? all[0]
  target.value = chosen
  distractors.value = sample(
    all.filter((c) => c.char !== chosen.char),
    6
  )
  items.value = []
  caught.value = 0
  wave.value += 1
  announce(
    `第 ${wave.value} 波，共 ${WAVES} 波。这一波要接住「${chosen.char}」，读作 ${chosen.pinyin}，` +
      `接住 ${PER_WAVE} 个就换字。别的字接到会掉一颗心。`
  )
  playPrompt()
}

function playPrompt() {
  if (target.value) speak(target.value.char, { rate: settings.speechRate })
}

function replay() {
  feedback.tap()
  playPrompt()
  announce(`这一波要接的是「${target.value?.char}」，读作 ${target.value?.pinyin}。${describeLane()}`)
}

/* -------------------------------------------------------------- 节拍 */

/** 这一拍要不要再放一个字下来：场上太挤就不放，目标字断档就必须放。 */
function spawn() {
  if (items.value.length >= MAX_ITEMS) return
  const topTaken = items.value.some((it) => it.row <= 0)
  if (topTaken) return

  const targetsOnField = items.value.filter((it) => it.isTarget).length
  const stillNeeded = PER_WAVE - caught.value
  const mustDrop = targetsOnField === 0 && stillNeeded > 0
  if (!mustDrop && Math.random() > 0.72) return

  const isTarget = mustDrop || Math.random() < 0.45
  const char = isTarget ? target.value : pick(distractors.value) ?? target.value
  const free = Array.from({ length: LANES }, (_, i) => i).filter(
    (l) => !items.value.some((it) => it.lane === l && it.row <= 1)
  )
  const dropLane = pick(free.length ? free : [Math.floor(Math.random() * LANES)])

  seq += 1
  items.value.push({
    id: `it-${seq}`,
    lane: dropLane,
    row: 0,
    char: char.char,
    pinyin: char.pinyin,
    isTarget: char.char === target.value?.char
  })
}

function beat() {
  if (phase.value !== 'playing') return

  // 先让场上的字各往下挪一格，再结算落到篮子那一行的字
  const landed = []
  const flying = []
  for (const it of items.value) {
    const moved = { ...it, row: it.row + 1 }
    if (moved.row >= ROWS) landed.push(moved)
    else flying.push(moved)
  }
  items.value = flying
  for (const it of landed) resolve(it)

  if (phase.value === 'playing') spawn()
}

function resolve(item) {
  const inBasket = item.lane === lane.value

  if (inBasket && item.isTarget) {
    caught.value += 1
    score.value += 1
    streak.value += 1
    feedback.correct(stageRef.value, { cueArg: streak.value })
    progress.recordAnswer(item.char, true)
    announce(`接住「${item.char}」啦！这一波已经接到 ${caught.value} / ${PER_WAVE} 个。`)
    if (caught.value >= PER_WAVE) {
      if (wave.value >= WAVES) finish(true)
      else newWave()
    }
    return
  }

  if (inBasket && !item.isTarget) {
    lose(`接到的是「${item.char}」，不是「${target.value?.char}」。`)
    progress.recordAnswer(target.value?.char ?? item.char, false)
    return
  }

  if (item.isTarget) {
    lose(`「${item.char}」从第 ${item.lane + 1} 条轨道漏掉了。`)
    progress.recordAnswer(item.char, false)
  }
}

function lose(reason) {
  misses.value += 1
  streak.value = 0
  lives.value -= 1
  feedback.wrong(stageRef.value)
  if (lives.value <= 0) {
    announce(`${reason}心用完了，这一局到这里。`)
    finish(false)
    return
  }
  announce(`${reason}还剩 ${lives.value} 颗心。${describeLane()}`)
}

function loop() {
  beat()
  if (phase.value !== 'playing') return
  beatTimer = window.setTimeout(loop, beatMs.value)
}

/* -------------------------------------------------------------- 走位 */

/** 把「这条轨道上方有什么」翻译成一句话，看不见画面全靠它。 */
function describeLane() {
  const here = items.value
    .filter((it) => it.lane === lane.value)
    .sort((a, b) => b.row - a.row)
  const head = here[0]
  if (!head) return `篮子在第 ${lane.value + 1} 条轨道，这条轨道上方是空的。`
  return (
    `篮子在第 ${lane.value + 1} 条轨道，上方 ${ROWS - head.row} 格掉着「${head.char}」，` +
    `${head.isTarget ? '就是要接的字。' : '不是要接的字。'}`
  )
}

function moveTo(next) {
  if (phase.value !== 'playing') return
  const clamped = Math.min(LANES - 1, Math.max(0, next))
  if (clamped === lane.value) {
    feedback.tap()
    announce(`已经在最${clamped === 0 ? '左' : '右'}边了。${describeLane()}`)
    return
  }
  lane.value = clamped
  feedback.tap()
  announce(describeLane())
}

const KEYS = {
  ArrowLeft: -1,
  ArrowRight: 1,
  a: -1,
  d: 1
}

function onKeydown(event) {
  const step = KEYS[event.key] ?? KEYS[event.key?.toLowerCase?.()]
  if (!step) return
  event.preventDefault()
  moveTo(lane.value + step)
}

/* -------------------------------------------------------------- 流程 */

function start() {
  feedback.tap()
  window.clearTimeout(beatTimer)
  celebrating.value = false
  phase.value = 'playing'
  wave.value = 0
  score.value = 0
  misses.value = 0
  streak.value = 0
  lives.value = LIVES
  lane.value = Math.floor(LANES / 2)
  newWave()
  // 开局就把焦点放进舞台，键盘用户不用先按一串 Tab 才能挪篮子
  window.setTimeout(() => stageRef.value?.focus(), 0)
  beatTimer = window.setTimeout(loop, beatMs.value)
}

function finish(cleared) {
  phase.value = 'done'
  window.clearTimeout(beatTimer)
  items.value = []
  announce(
    `这一局结束，接住 ${score.value} 个字，漏掉或接错 ${misses.value} 次，还剩 ${Math.max(0, lives.value)} 颗心。`
  )
  if (cleared) celebrating.value = true
  else feedback.tap()
}

const cleared = computed(() => score.value >= WAVES * PER_WAVE)

const earnedStars = computed(() => {
  if (misses.value === 0) return 3
  return misses.value <= 2 ? 2 : 1
})

const stageLabel = computed(
  () =>
    `接字大冒险。用左右方向键或 A D 把篮子挪到字掉下来的那条轨道上，` +
    `现在要接「${target.value?.char ?? ''}」。${describeLane()}`
)

/** 一维摊平的格子，纯装饰：给轨道画出参考线。 */
const trackCells = computed(() =>
  Array.from({ length: LANES * ROWS }, (_, i) => ({ lane: i % LANES, row: Math.floor(i / LANES) }))
)

onBeforeUnmount(() => {
  window.clearTimeout(beatTimer)
  stopSpeaking()
})
</script>

<template>
  <div class="page catch-game">
    <p class="sr-only" role="status" aria-live="polite" aria-atomic="true">{{ announcement }}</p>

    <!-- 开始页 -->
    <section v-if="phase === 'intro'" class="card intro">
      <div class="intro__emoji" aria-hidden="true">🧺</div>
      <h2 class="intro__title">接字大冒险</h2>
      <p class="intro__desc">
        字会从天上掉下来，把篮子挪到要接的那个字下面。<br />
        接错或漏掉都会掉一颗心，一共 {{ WAVES }} 波、{{ LIVES }} 颗心。
      </p>

      <VoiceNotice fallback="要接的字会大大地写在轨道上方，可以请家长读给你听。" />

      <p v-if="usingFallback" class="warn">💡 还没学够 4 个字，这一局先用课程最前面的字来练习。</p>
      <p v-else class="muted">这一局从你学过的 {{ pool.length }} 个字里出题。</p>

      <p class="muted catch__calm" :data-quiet="quiet">
        {{
          quiet
            ? '已经按你的「减少动效」设置放慢了节奏，字会一格一格地挪下来。'
            : '想慢一点玩，可以在家长中心打开「减少动效」。'
        }}
      </p>

      <button class="btn btn--primary btn--lg btn--block" type="button" @click="start">
        开始接字 🚀
      </button>
    </section>

    <!-- 游戏中 -->
    <template v-else-if="phase === 'playing'">
      <section class="hud card card--flat">
        <div class="hud__row">
          <span class="pill">第 {{ wave }} / {{ WAVES }} 波</span>
          <span class="pill pill--accent">⭐ {{ score }}</span>
          <span class="pill">❤️ {{ lives }}</span>
          <span v-if="misses" class="pill">💦 失手 {{ misses }}</span>
        </div>
      </section>

      <section class="quest card">
        <p class="quest__label">这一波要接的字</p>
        <p class="quest__char">{{ target?.char }}</p>
        <p class="quest__pinyin">{{ target?.pinyin }}</p>
        <button v-if="speechOk" class="btn btn--ghost btn--sm" type="button" @click="replay">
          🔊 再听一次
        </button>
      </section>

      <div
        ref="stageRef"
        class="catch"
        :class="{ 'catch--quiet': quiet }"
        role="group"
        tabindex="0"
        :aria-label="stageLabel"
        :data-lane="lane"
        :data-wave="wave"
        @keydown="onKeydown"
      >
        <div
          class="catch__field"
          :style="{ '--lanes': LANES, '--rows': ROWS, '--beat': `${beatMs}ms` }"
          aria-hidden="true"
        >
          <span
            v-for="cell in trackCells"
            :key="`c-${cell.lane}-${cell.row}`"
            class="catch__cell"
            :style="{ '--lane': cell.lane, '--row': cell.row }"
          ></span>

          <span
            v-for="item in items"
            :key="item.id"
            class="catch__item"
            :class="{ 'is-target': item.isTarget }"
            :style="{ '--lane': item.lane, '--row': item.row }"
            :data-char="item.char"
            :data-lane="item.lane"
            :data-row="item.row"
            :data-target="item.isTarget"
          >
            {{ item.char }}
          </span>

          <span class="catch__basket" :style="{ '--lane': lane }" data-basket="true">🧺</span>
        </div>
      </div>

      <div class="catch__pad">
        <button class="btn btn--ghost btn--lg" type="button" @click="moveTo(lane - 1)">
          ⬅️ 左
        </button>
        <button class="btn btn--ghost btn--lg" type="button" @click="moveTo(lane + 1)">
          右 ➡️
        </button>
      </div>

      <p class="muted catch__tip">键盘：左右方向键或 A D 换一条轨道。</p>
    </template>

    <!-- 结算 -->
    <section v-else class="card intro">
      <div class="intro__emoji" aria-hidden="true">{{ cleared ? '🏆' : '💪' }}</div>
      <h2 class="intro__title">{{ cleared ? '全部接住啦！' : '再来一次会更稳' }}</h2>
      <p class="intro__desc">
        这一局接住 <strong>{{ score }}</strong> 个字，失手 {{ misses }} 次。
      </p>
      <div class="intro__actions">
        <button class="btn btn--primary btn--lg" type="button" @click="start">再接一局 🔁</button>
        <RouterLink class="btn btn--ghost btn--lg" to="/games" @click="feedback.tap()">
          换个游戏 🎲
        </RouterLink>
      </div>
    </section>

    <CelebrationOverlay
      :open="celebrating"
      emoji="🧺"
      title="接字大冒险通关！"
      :subtitle="`接住 ${score} 个字`"
      :stars="earnedStars"
      :reduce-motion="settings.reduceMotion"
      @done="celebrating = false"
    />
  </div>
</template>

<style scoped>
.intro {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--gap-md);
  text-align: center;
}

.intro__emoji {
  font-size: 3.4rem;
  line-height: 1;
}

.intro__title {
  font-size: var(--fs-xl);
  font-weight: var(--fw-black);
  color: var(--text-strong);
}

.intro__desc {
  line-height: var(--lh-loose);
  color: var(--text);
}

.intro__actions {
  display: flex;
  gap: var(--gap-sm);
  flex-wrap: wrap;
  justify-content: center;
}

.warn {
  width: 100%;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  background: var(--brand-soft);
  color: var(--text-strong);
  font-size: var(--fs-sm);
  line-height: var(--lh-loose);
}

.catch__calm {
  font-size: 0.82rem;
  line-height: var(--lh-base);
}

.hud__row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* ------------------------------------------------------------ 题面 */

.quest {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--gap-2xs);
  text-align: center;
}

.quest__label {
  font-size: var(--fs-sm);
  font-weight: var(--fw-bold);
  color: var(--text-soft);
}

.quest__char {
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
  font-size: clamp(2.6rem, 18vw, 3.8rem);
  font-weight: var(--fw-heavy);
  line-height: 1.1;
  color: var(--text-strong);
}

.quest__pinyin {
  font-size: var(--fs-md);
  font-weight: var(--fw-bold);
  color: var(--text);
}

/* ------------------------------------------------------------ 轨道 */

.catch {
  border-radius: var(--radius-md);
  outline-offset: 4px;
}

.catch__field {
  position: relative;
  /* 五格轨道 + 底下一格放篮子 */
  aspect-ratio: 4 / 5;
  border-radius: var(--radius-md);
  border: 2px solid color-mix(in srgb, var(--brand) 32%, transparent);
  background:
    repeating-linear-gradient(
      90deg,
      color-mix(in srgb, var(--text-soft) 16%, transparent) 0 1px,
      transparent 1px calc(100% / var(--lanes))
    ),
    var(--surface-sunken);
  overflow: hidden;
}

.catch__cell,
.catch__item,
.catch__basket {
  position: absolute;
  display: grid;
  place-items: center;
  width: calc(100% / var(--lanes));
  height: calc(100% / (var(--rows) + 1));
  left: calc(var(--lane) * 100% / var(--lanes));
}

.catch__cell {
  top: calc(var(--row) * 100% / (var(--rows) + 1));
  border-bottom: 1px dashed color-mix(in srgb, var(--text-soft) 14%, transparent);
}

.catch__item {
  top: calc(var(--row) * 100% / (var(--rows) + 1));
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
  font-size: clamp(1.5rem, 7vw, 2rem);
  font-weight: var(--fw-heavy);
  color: var(--text-strong);
  transition: top var(--beat) linear;
}

/* 目标字和别的字看得出区别，但不靠颜色单打独斗：还多一圈托底 */
.catch__item.is-target {
  border-radius: var(--radius-pill);
  background: color-mix(in srgb, var(--mint-400) 28%, transparent);
  box-shadow: inset 0 0 0 2px color-mix(in srgb, var(--success) 55%, transparent);
}

.catch__basket {
  top: calc(var(--rows) * 100% / (var(--rows) + 1));
  font-size: clamp(1.8rem, 9vw, 2.4rem);
  transition: left var(--dur-fast) var(--ease-pop);
}

/* 减少动效：不再滑动，字与篮子直接出现在下一格 */
.catch--quiet .catch__item,
.catch--quiet .catch__basket {
  transition: none;
}

.catch__pad {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--gap-sm);
}

.catch__tip {
  text-align: center;
  font-size: 0.8rem;
}

@media (prefers-reduced-motion: reduce) {
  .catch__item,
  .catch__basket {
    transition: none;
  }
}
</style>
