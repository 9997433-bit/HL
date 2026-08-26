<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import gsap from 'gsap'
import StarBurst from '@/components/StarBurst.vue'
import { CHARACTERS } from '@/data/characters.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { isSpeechSupported, speak, stopSpeaking } from '@/utils/speech.js'
import { sfx } from '@/utils/sfx.js'

const ROUNDS = 10
const OPTIONS = 4

const progress = useProgressStore()
const settings = useSettingsStore()

const burstRef = ref(null)
const boardRef = ref(null)

const phase = ref('intro') // intro | playing | done
const round = ref(0)
const score = ref(0)
const streak = ref(0)
const bestStreak = ref(0)
const target = ref(null)
const options = ref([])
const picked = ref(null)
const locked = ref(false)
const missedChars = ref([])

const speechOk = isSpeechSupported()

/** 出题池：优先用学过的字；不足 4 个时用课程最前面的字兜底。 */
const pool = computed(() => {
  const learned = CHARACTERS.filter((c) => progress.isLearned(c.char))
  return learned.length >= OPTIONS ? learned : CHARACTERS.slice(0, Math.max(OPTIONS, 8))
})

const usingFallbackPool = computed(
  () => CHARACTERS.filter((c) => progress.isLearned(c.char)).length < OPTIONS
)

function shuffle(list) {
  const a = [...list]
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[a[i], a[j]] = [a[j], a[i]]
  }
  return a
}

function nextRound() {
  picked.value = null
  locked.value = false

  const list = pool.value
  // 需要复习的字优先出现
  const review = progress.reviewQueue.filter((c) => list.some((x) => x.char === c.char))
  const preferred = review.length && Math.random() < 0.6 ? review : list
  const pick = preferred[Math.floor(Math.random() * preferred.length)]
  target.value = pick

  const distractors = shuffle(list.filter((c) => c.char !== pick.char)).slice(0, OPTIONS - 1)
  options.value = shuffle([pick, ...distractors])

  round.value += 1
  playPrompt()
  animateIn()
}

function animateIn() {
  if (settings.reduceMotion) return
  requestAnimationFrame(() => {
    const nodes = boardRef.value?.querySelectorAll('.opt')
    if (nodes?.length) {
      gsap.fromTo(
        nodes,
        { opacity: 0, y: 18, scale: 0.9 },
        { opacity: 1, y: 0, scale: 1, duration: 0.32, ease: 'back.out(1.7)', stagger: 0.05 }
      )
    }
  })
}

function playPrompt() {
  if (!target.value) return
  speak(target.value.char, { rate: settings.speechRate })
}

function replay() {
  sfx.tap()
  playPrompt()
}

function choose(opt) {
  if (locked.value || !target.value) return
  locked.value = true
  picked.value = opt.char

  const correct = opt.char === target.value.char
  if (correct) {
    score.value += 1
    streak.value += 1
    bestStreak.value = Math.max(bestStreak.value, streak.value)
    sfx.correct()
    burstRef.value?.burst()
  } else {
    streak.value = 0
    sfx.wrong()
    missedChars.value.push(target.value.char)
    shakeWrong(opt.char)
  }

  progress.recordAnswer(target.value.char, correct)
  progress.recordGameRound({ correct, streak: streak.value })

  setTimeout(() => {
    if (round.value >= ROUNDS) finish()
    else nextRound()
  }, correct ? 900 : 1600)
}

function shakeWrong(char) {
  if (settings.reduceMotion) return
  const el = boardRef.value?.querySelector(`[data-char="${char}"]`)
  if (el) gsap.fromTo(el, { x: -8 }, { x: 0, duration: 0.5, ease: 'elastic.out(1, 0.3)' })
}

function finish() {
  phase.value = 'done'
  if (score.value >= ROUNDS * 0.8) sfx.levelUp()
}

function start() {
  sfx.tap()
  phase.value = 'playing'
  round.value = 0
  score.value = 0
  streak.value = 0
  bestStreak.value = 0
  missedChars.value = []
  nextRound()
}

function optionState(opt) {
  if (!picked.value) return ''
  if (opt.char === target.value?.char) return 'is-right'
  if (opt.char === picked.value) return 'is-wrong'
  return 'is-dim'
}

const accuracy = computed(() => (round.value ? Math.round((score.value / ROUNDS) * 100) : 0))

const uniqueMissed = computed(() => [...new Set(missedChars.value)])

onMounted(() => {
  if (!speechOk) return
})

onBeforeUnmount(stopSpeaking)
</script>

<template>
  <div class="page game">
    <StarBurst ref="burstRef" />

    <!-- 开始页 -->
    <section v-if="phase === 'intro'" class="card intro">
      <div class="intro__emoji" aria-hidden="true">🎧</div>
      <h2 class="intro__title">听音识字</h2>
      <p class="intro__desc">
        小耳朵听一听，然后在四个字里找出听到的那一个。<br />
        一共 {{ ROUNDS }} 关，答对一个得 1 颗星 ⭐
      </p>

      <p v-if="!speechOk" class="warn">
        ⚠️ 这个浏览器不支持语音朗读。游戏仍可进行，题目汉字会显示在提示区，可以由家长读给孩子听。
      </p>
      <p v-else-if="usingFallbackPool" class="warn warn--soft">
        💡 还没学够 4 个字，这一局先用课程最前面的字来练习。
      </p>

      <div class="intro__stats">
        <div><strong>{{ progress.game.plays }}</strong><small>玩过的题</small></div>
        <div><strong>{{ progress.gameAccuracy }}%</strong><small>正确率</small></div>
        <div><strong>{{ progress.game.bestStreak }}</strong><small>最高连对</small></div>
      </div>

      <button class="btn btn--primary btn--lg btn--block" type="button" @click="start">
        开始游戏 🚀
      </button>
    </section>

    <!-- 游戏中 -->
    <template v-else-if="phase === 'playing'">
      <section class="hud card card--flat">
        <div class="hud__bar">
          <span class="hud__fill" :style="{ width: `${(round / ROUNDS) * 100}%` }" />
        </div>
        <div class="hud__row">
          <span class="pill">第 {{ round }} / {{ ROUNDS }} 关</span>
          <span class="pill pill--accent">⭐ {{ score }}</span>
          <span v-if="streak >= 2" class="pill hud__streak">🔥 连对 {{ streak }}</span>
        </div>
      </section>

      <section class="speaker card">
        <button class="speaker__btn" type="button" @click="replay">
          <span class="speaker__icon" aria-hidden="true">🔊</span>
          <span class="speaker__label">再听一次</span>
          <span class="speaker__wave" aria-hidden="true" />
        </button>
        <p v-if="!speechOk" class="speaker__fallback">
          请家长读：<strong>{{ target?.char }}</strong>（{{ target?.pinyin }}）
        </p>
        <p v-else class="muted speaker__tip">听到了哪个字？点一点下面的卡片</p>
      </section>

      <section ref="boardRef" class="board">
        <button
          v-for="opt in options"
          :key="opt.char"
          class="opt"
          :class="optionState(opt)"
          :data-char="opt.char"
          type="button"
          :disabled="locked"
          @click="choose(opt)"
        >
          <span class="opt__char">{{ opt.char }}</span>
          <span v-if="picked" class="opt__pinyin">{{ opt.pinyin }}</span>
        </button>
      </section>
    </template>

    <!-- 结算 -->
    <section v-else class="card intro">
      <div class="intro__emoji" aria-hidden="true">
        {{ accuracy >= 80 ? '🏆' : accuracy >= 50 ? '🎉' : '💪' }}
      </div>
      <h2 class="intro__title">
        {{ accuracy >= 80 ? '太棒了！' : accuracy >= 50 ? '做得不错！' : '再练一练就更好啦' }}
      </h2>
      <p class="intro__desc">
        这一局答对 <strong>{{ score }}</strong> / {{ ROUNDS }} 题，最高连对 {{ bestStreak }} 次。
      </p>

      <div v-if="uniqueMissed.length" class="missed">
        <p class="missed__title">这几个字再看看：</p>
        <div class="missed__list">
          <RouterLink
            v-for="c in uniqueMissed"
            :key="c"
            class="missed__item"
            :to="`/learn/${encodeURIComponent(c)}`"
            @click="sfx.tap()"
          >{{ c }}</RouterLink>
        </div>
      </div>

      <div class="intro__actions">
        <button class="btn btn--primary btn--lg" type="button" @click="start">再来一局 🔁</button>
        <RouterLink class="btn btn--ghost btn--lg" to="/" @click="sfx.tap()">回地图 🗺️</RouterLink>
      </div>
    </section>
  </div>
</template>

<style scoped>
.game {
  position: relative;
}

.intro {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--gap-md);
  text-align: center;
}

.intro__emoji {
  font-size: 3.6rem;
  line-height: 1;
  animation: float-y 3.2s ease-in-out infinite;
}

.intro__title {
  font-size: 1.6rem;
  font-weight: 800;
  color: var(--text-strong);
}

.intro__desc {
  line-height: 1.9;
  color: var(--text);
}

.intro__stats {
  display: flex;
  gap: var(--gap-md);
  width: 100%;
  justify-content: center;
}

.intro__stats div {
  flex: 1;
  max-width: 130px;
  display: flex;
  flex-direction: column;
  padding: 10px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
}

.intro__stats strong {
  font-size: 1.3rem;
  color: var(--text-strong);
}

.intro__stats small {
  font-size: 0.72rem;
  color: var(--text-soft);
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
  background: color-mix(in srgb, var(--danger) 14%, transparent);
  color: var(--text-strong);
  font-size: 0.85rem;
  line-height: 1.7;
}

.warn--soft {
  background: var(--brand-soft);
}

.hud {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: var(--gap-md);
}

.hud__bar {
  height: 12px;
  border-radius: 6px;
  background: var(--stroke-hint);
  overflow: hidden;
}

.hud__fill {
  display: block;
  height: 100%;
  border-radius: 6px;
  background: linear-gradient(90deg, var(--brand) 0%, var(--accent) 100%);
  transition: width var(--dur-mid) var(--ease-pop);
}

.hud__row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.hud__streak {
  background: color-mix(in srgb, var(--danger) 20%, transparent);
}

.speaker {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  text-align: center;
}

.speaker__btn {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 18px 34px;
  border-radius: var(--radius-xl);
  background: linear-gradient(180deg, var(--accent) 0%, color-mix(in srgb, var(--accent) 65%, #000 12%) 100%);
  color: var(--text-invert);
  box-shadow: var(--shadow-md);
  transition: transform var(--dur-fast) var(--ease-pop);
}

.speaker__btn:active {
  transform: scale(0.95);
}

.speaker__icon {
  font-size: 2.6rem;
  line-height: 1;
}

.speaker__label {
  font-weight: 800;
  letter-spacing: 0.05em;
}

.speaker__wave {
  position: absolute;
  inset: -6px;
  border-radius: inherit;
  border: 3px solid color-mix(in srgb, var(--accent) 60%, transparent);
  animation: pulse-ring 2s ease-out infinite;
  pointer-events: none;
}

@keyframes pulse-ring {
  0% {
    transform: scale(0.96);
    opacity: 0.8;
  }
  100% {
    transform: scale(1.12);
    opacity: 0;
  }
}

.speaker__tip {
  font-size: 0.85rem;
}

.speaker__fallback {
  font-size: 0.95rem;
}

.speaker__fallback strong {
  font-size: 1.6rem;
  color: var(--brand-strong);
}

.board {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--gap-md);
}

.opt {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  aspect-ratio: 1 / 0.86;
  border-radius: var(--radius-lg);
  background: var(--surface-strong);
  border: 3px solid transparent;
  box-shadow: var(--shadow-md);
  transition: transform var(--dur-fast) var(--ease-pop), border-color var(--dur-fast) ease,
    background var(--dur-fast) ease, opacity var(--dur-fast) ease;
}

.opt:active:not(:disabled) {
  transform: scale(0.95);
}

.opt__char {
  font-size: clamp(3rem, 15vw, 4.6rem);
  line-height: 1;
  font-weight: 700;
  color: var(--text-strong);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

.opt__pinyin {
  font-size: 0.9rem;
  color: var(--text-soft);
}

.opt.is-right {
  border-color: var(--success);
  background: color-mix(in srgb, var(--success) 16%, var(--surface-strong));
}

.opt.is-wrong {
  border-color: var(--danger);
  background: color-mix(in srgb, var(--danger) 14%, var(--surface-strong));
}

.opt.is-dim {
  opacity: 0.45;
}

.missed {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
}

.missed__title {
  font-size: 0.85rem;
  color: var(--text-soft);
}

.missed__list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.missed__item {
  display: grid;
  place-items: center;
  width: 54px;
  height: 54px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  font-size: 1.7rem;
  font-weight: 700;
  color: var(--text-strong);
  box-shadow: var(--shadow-sm);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', serif;
}
</style>
