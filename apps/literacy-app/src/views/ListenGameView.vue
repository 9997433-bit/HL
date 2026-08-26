<script setup>
/**
 * 听音识字。
 *
 * 玩法内核只有一条：听一个字的读音，从四个里挑出来。
 * 内核之外套了三层「皮」——安静的卡片、钓鱼池、打地鼠草地——
 * 换皮只改场景与动画，出题、判分、复习队列全都共用同一套逻辑，
 * 所以加一层皮不需要碰任何计分代码（见 SKINS 表）。
 *
 * 三层皮的动画都走 GSAP，并且统一挂在 boardRef 的 gsap.context 上，
 * 换关时整块 revert，不会有上一关的补间漏到下一关。
 * 家长把动效设成「减弱」时，所有循环动画都不启动，只留状态色变化。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import gsap from 'gsap'
import StarBurst from '@/components/StarBurst.vue'
import CelebrationOverlay from '@/components/CelebrationOverlay.vue'
import VoiceNotice from '@/components/VoiceNotice.vue'
import { CHARACTERS } from '@/data/characters.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { isSpeechSupported, speak, stopSpeaking } from '@/utils/speech.js'
import { sfx } from '@/utils/sfx.js'

const ROUNDS = 10
const OPTIONS = 4

/**
 * 换皮表。每张皮只描述「长什么样、怎么动、怎么说话」，
 * 判分和出题完全不看这里，所以以后加新皮只需要往这个数组里加一项。
 */
const SKINS = [
  {
    id: 'card',
    name: '安静卡片',
    emoji: '🃏',
    desc: '没有多余动画，专心听字',
    sceneEmoji: '📚',
    sceneHint: '听到了哪个字？点一点下面的卡片',
    listenLabel: '再听一次',
    rightHint: '答对啦！',
    wrongHint: '再听一遍，慢慢来'
  },
  {
    id: 'fish',
    name: '钓鱼池',
    emoji: '🎣',
    desc: '四条小鱼游过来，钓走念对的那条',
    sceneEmoji: '🎣',
    sceneHint: '听清楚了就去钓那条鱼',
    listenLabel: '再听一次鱼儿说话',
    rightHint: '钓上来啦！',
    wrongHint: '这条不是，鱼儿游走了'
  },
  {
    id: 'mole',
    name: '地鼠草地',
    emoji: '🔨',
    desc: '地鼠探出头，敲中念对的那只',
    sceneEmoji: '🌱',
    sceneHint: '哪只地鼠在念这个字？敲它',
    listenLabel: '再听一次地鼠说话',
    rightHint: '敲中啦！',
    wrongHint: '敲空了，它缩回去了'
  }
]

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
const celebrating = ref(false)

/**
 * 读屏播报。
 *
 * 屏幕上的反馈是「颜色 + 一句短提示 + 动画」，这三样读屏用户一样都拿不到，
 * 所以每一步都在这里写一句完整的话：第几关、答对没有、正确答案是哪个字。
 * 短提示（feedback）留在视觉层，播报走这条独立的 sr-only 通道，避免同一句
 * 话被读两遍。
 */
const announcement = ref('')

function announce(text) {
  // 同一句话再写一次不会触发播报，加个零宽空格让读屏把重复的提示也念出来
  announcement.value = announcement.value === text ? `${text}\u200b` : text
}

const speechOk = isSpeechSupported()

const skinId = computed(() => SKINS.some((s) => s.id === settings.listenSkin) ? settings.listenSkin : 'fish')
const skin = computed(() => SKINS.find((s) => s.id === skinId.value) ?? SKINS[0])

function chooseSkin(id) {
  sfx.tap()
  settings.update({ listenSkin: id })
}

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
  announce(`第 ${round.value} 关，共 ${ROUNDS} 关。${skin.value.sceneHint}，${OPTIONS} 个字里选一个。`)
  playPrompt()
  animateIn()
}

/* -------------------------------------------------------------- 场景动画 */

let boardCtx = null

function killBoardAnimations() {
  boardCtx?.revert()
  boardCtx = null
}

/** 入场 + 待机循环。每张皮的「活着」的感觉都靠这一段。 */
function animateIn() {
  killBoardAnimations()
  if (settings.reduceMotion) return

  requestAnimationFrame(() => {
    const host = boardRef.value
    if (!host) return
    boardCtx = gsap.context(() => {
      const nodes = gsap.utils.toArray('.opt', host)
      if (!nodes.length) return

      if (skinId.value === 'fish') {
        // 小鱼从池子两侧游进来，然后原地上下浮（幅度压在 10px 内）
        gsap.fromTo(
          nodes,
          { opacity: 0, x: (i) => (i % 2 ? 56 : -56), scale: 0.86 },
          { opacity: 1, x: 0, scale: 1, duration: 0.5, ease: 'power2.out', stagger: 0.07 }
        )
        nodes.forEach((node, i) => {
          gsap.to(node, {
            y: i % 2 ? -8 : 8,
            rotate: i % 2 ? -2 : 2,
            duration: 1.8 + i * 0.22,
            delay: 0.5 + i * 0.08,
            ease: 'sine.inOut',
            yoyo: true,
            repeat: -1
          })
        })
      } else if (skinId.value === 'mole') {
        // 地鼠从洞里依次探头，探完轻轻晃两下
        gsap.fromTo(
          nodes,
          { opacity: 0, y: 76, scale: 0.8 },
          {
            opacity: 1,
            y: 0,
            scale: 1,
            duration: 0.46,
            ease: 'back.out(1.7)',
            stagger: 0.07,
            onComplete: () => {
              nodes.forEach((node, i) => {
                gsap.to(node, {
                  y: -6,
                  duration: 1.3 + i * 0.18,
                  ease: 'sine.inOut',
                  yoyo: true,
                  repeat: -1
                })
              })
            }
          }
        )
      } else {
        gsap.fromTo(
          nodes,
          { opacity: 0, y: 18, scale: 0.9 },
          { opacity: 1, y: 0, scale: 1, duration: 0.32, ease: 'back.out(1.7)', stagger: 0.05 }
        )
      }
    }, host)
  })
}

function nodeFor(char) {
  return boardRef.value?.querySelector(`[data-char="${char}"]`) ?? null
}

/** 答对：钓鱼往上提竿，地鼠被敲扁再弹起，卡片就单纯弹一下。 */
function animateRight(char) {
  if (settings.reduceMotion) return
  const el = nodeFor(char)
  if (!el) return
  gsap.killTweensOf(el)
  if (skinId.value === 'fish') {
    gsap.to(el, { y: -120, rotate: -14, scale: 1.06, duration: 0.62, ease: 'back.in(1.2)' })
  } else if (skinId.value === 'mole') {
    gsap
      .timeline()
      .to(el, { scaleY: 0.72, scaleX: 1.16, duration: 0.1, ease: 'power2.out' })
      .to(el, { scaleY: 1, scaleX: 1, y: -18, duration: 0.42, ease: 'elastic.out(1, 0.4)' })
      .to(el, { rotate: 360, duration: 0.5, ease: 'power2.out' }, '<')
  } else {
    gsap.to(el, { y: -14, scale: 1.06, duration: 0.34, ease: 'back.out(2)' })
  }
}

/** 答错：温和的「跑掉 / 缩回去」，不用红叉也不用刺耳音（设计规范 §2.3）。 */
function animateWrong(char) {
  if (settings.reduceMotion) return
  const el = nodeFor(char)
  if (!el) return
  gsap.killTweensOf(el)
  if (skinId.value === 'fish') {
    gsap.to(el, { x: 46, rotate: 10, opacity: 0.35, duration: 0.5, ease: 'power2.in' })
  } else if (skinId.value === 'mole') {
    gsap.to(el, { y: 78, opacity: 0.3, duration: 0.4, ease: 'power2.in' })
  } else {
    gsap.fromTo(el, { x: -8 }, { x: 0, duration: 0.5, ease: 'elastic.out(1, 0.3)' })
  }
}

/* ------------------------------------------------------------------ 流程 */

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
    animateRight(opt.char)
    announce(
      `答对了，是「${opt.char}」，读作 ${opt.pinyin}。` +
        `已经答对 ${score.value} 题，共 ${ROUNDS} 关。`
    )
  } else {
    streak.value = 0
    sfx.wrong()
    missedChars.value.push(target.value.char)
    animateWrong(opt.char)
    announce(
      `选的是「${opt.char}」，${opt.pinyin}；正确答案是「${target.value.char}」，` +
        `读作 ${target.value.pinyin}。${skin.value.wrongHint}。`
    )
  }

  progress.recordAnswer(target.value.char, correct)
  progress.recordGameRound({ correct, streak: streak.value })

  setTimeout(() => {
    if (round.value >= ROUNDS) finish()
    else nextRound()
  }, correct ? 900 : 1600)
}

function finish() {
  killBoardAnimations()
  phase.value = 'done'
  announce(
    `这一局结束，答对 ${score.value} / ${ROUNDS} 题，正确率 ${accuracy.value}%，` +
      `拿到 ${earnedStars.value} 颗星，最高连对 ${bestStreak.value} 次。`
  )
  if (score.value >= ROUNDS * 0.6) celebrating.value = true
  else sfx.tap()
}

function start() {
  sfx.tap()
  announce('游戏开始。')
  celebrating.value = false
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

/** 结算的星数：按正确率给 1-3 颗，庆祝浮层用它做星排。 */
const earnedStars = computed(() => {
  if (accuracy.value >= 90) return 3
  if (accuracy.value >= 70) return 2
  return 1
})

const feedback = computed(() => {
  if (!picked.value) return ''
  return picked.value === target.value?.char ? skin.value.rightHint : skin.value.wrongHint
})

// 玩到一半换皮时，把待机动画按新皮重建一次
watch(skinId, () => {
  if (phase.value === 'playing') animateIn()
})

onMounted(() => {
  if (!speechOk) return
})

onBeforeUnmount(() => {
  killBoardAnimations()
  stopSpeaking()
})
</script>

<template>
  <div class="page game">
    <StarBurst ref="burstRef" />

    <p class="sr-only" role="status" aria-live="polite" aria-atomic="true">{{ announcement }}</p>

    <!-- 开始页 -->
    <section v-if="phase === 'intro'" class="card intro">
      <div class="intro__emoji" aria-hidden="true">🎧</div>
      <h2 class="intro__title">听音识字</h2>
      <p class="intro__desc">
        小耳朵听一听，然后在四个字里找出听到的那一个。<br />
        一共 {{ ROUNDS }} 关，答对一个得 1 颗星 ⭐
      </p>

      <fieldset class="skins">
        <legend class="skins__legend">今天在哪儿玩？</legend>
        <div class="skins__row">
          <button
            v-for="s in SKINS"
            :key="s.id"
            class="skinbtn"
            :class="{ 'is-on': s.id === skinId }"
            type="button"
            :aria-pressed="s.id === skinId"
            @click="chooseSkin(s.id)"
          >
            <span class="skinbtn__emoji" aria-hidden="true">{{ s.emoji }}</span>
            <span class="skinbtn__name">{{ s.name }}</span>
            <span class="skinbtn__desc">{{ s.desc }}</span>
          </button>
        </div>
      </fieldset>

      <VoiceNotice fallback="题目的字会显示在提示区，可以请家长读给你听。" />

      <p v-if="usingFallbackPool" class="warn warn--soft">
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
          <span class="pill hud__skin">{{ skin.emoji }} {{ skin.name }}</span>
        </div>
      </section>

      <section class="speaker card">
        <button class="speaker__btn" type="button" @click="replay">
          <span class="speaker__icon" aria-hidden="true">🔊</span>
          <span class="speaker__label">{{ skin.listenLabel }}</span>
          <span class="speaker__wave" aria-hidden="true" />
        </button>
        <p v-if="!speechOk" class="speaker__fallback">
          请家长读：<strong>{{ target?.char }}</strong>（{{ target?.pinyin }}）
        </p>
        <p v-else class="muted speaker__tip">{{ skin.sceneHint }}</p>
        <VoiceNotice v-if="speechOk" compact />
      </section>

      <section
        ref="boardRef"
        class="board"
        :class="`board--${skinId}`"
        :data-skin="skinId"
      >
        <span class="board__scene" aria-hidden="true">{{ skin.sceneEmoji }}</span>
        <button
          v-for="opt in options"
          :key="opt.char"
          class="opt"
          :class="[optionState(opt), `opt--${skinId}`]"
          :data-char="opt.char"
          type="button"
          :disabled="locked"
          :aria-label="`选 ${opt.char}`"
          @click="choose(opt)"
        >
          <span class="opt__char">{{ opt.char }}</span>
          <span v-if="picked" class="opt__pinyin">{{ opt.pinyin }}</span>
          <span class="opt__deco" aria-hidden="true" />
        </button>
      </section>

      <!-- 视觉短提示；完整播报交给上面的 sr-only 区域，避免读屏念两遍 -->
      <p class="feedback" aria-hidden="true">{{ feedback }}</p>
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

    <CelebrationOverlay
      :open="celebrating"
      :emoji="skin.emoji"
      :title="`${skin.name}闯关成功！`"
      :subtitle="`答对 ${score} / ${ROUNDS} 题`"
      :stars="earnedStars"
      :reduce-motion="settings.reduceMotion"
      @done="celebrating = false"
    />
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

/* ------------------------------------------------------------------ 换皮 */

.skins {
  width: 100%;
  border: none;
  padding: 0;
  margin: 0;
}

.skins__legend {
  padding: 0 0 6px;
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--text-soft);
}

.skins__row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--gap-sm);
}

.skinbtn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  min-height: var(--tap-min);
  padding: 10px 6px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  border: 3px solid transparent;
  transition: transform var(--dur-fast) var(--ease-pop), border-color var(--dur-fast) ease,
    background var(--dur-fast) ease;
}

.skinbtn:active {
  transform: scale(0.96);
}

.skinbtn.is-on {
  border-color: var(--brand);
  background: var(--brand-soft);
}

.skinbtn__emoji {
  font-size: 1.6rem;
  line-height: 1.2;
}

.skinbtn__name {
  font-size: 0.85rem;
  font-weight: 800;
  color: var(--text-strong);
}

.skinbtn__desc {
  font-size: 0.68rem;
  line-height: 1.5;
  color: var(--text-soft);
}

/* -------------------------------------------------------------------- HUD */

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

.hud__skin {
  margin-left: auto;
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
  background: linear-gradient(
    180deg,
    var(--accent) 0%,
    color-mix(in srgb, var(--accent) 65%, var(--text-strong) 12%) 100%
  );
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

.feedback {
  min-height: 1.6em;
  text-align: center;
  font-weight: 700;
  color: var(--text-soft);
}

/* ----------------------------------------------------------------- 答题区 */

.board {
  position: relative;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--gap-md);
  padding: var(--gap-md);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.board__scene {
  position: absolute;
  right: 12px;
  top: 10px;
  font-size: 1.6rem;
  line-height: 1;
  opacity: 0.55;
  pointer-events: none;
}

.opt {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  aspect-ratio: 1 / 0.86;
  min-height: var(--tap-min);
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
  position: relative;
  z-index: 2;
  font-size: clamp(3rem, 15vw, 4.6rem);
  line-height: 1;
  font-weight: 700;
  color: var(--text-strong);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

.opt__pinyin {
  position: relative;
  z-index: 2;
  font-size: 0.9rem;
  color: var(--text-soft);
}

.opt__deco {
  position: absolute;
  pointer-events: none;
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

/* ---- 皮肤：安静卡片（默认样式已经够了，只补一点场景底色） ---- */

.board--card {
  background: color-mix(in srgb, var(--surface-sunken) 60%, transparent);
}

/* ---- 皮肤：钓鱼池 ---- */

.board--fish {
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--sky-400) 26%, var(--surface-sunken)) 0%,
    color-mix(in srgb, var(--mint-400) 34%, var(--surface-sunken)) 100%
  );
  box-shadow: inset 0 8px 20px color-mix(in srgb, var(--sky-400) 24%, transparent);
}

.opt--fish {
  /* 鱼身：左圆右尖的胶囊，尾巴用 ::after 补一个三角 */
  border-radius: 62% 38% 42% 58% / 54% 50% 50% 46%;
  background: linear-gradient(
    150deg,
    color-mix(in srgb, var(--mango-400) 70%, var(--surface-strong)) 0%,
    color-mix(in srgb, var(--coral-400) 55%, var(--surface-strong)) 100%
  );
  border-color: color-mix(in srgb, var(--surface-strong) 70%, transparent);
}

.opt--fish .opt__deco {
  right: -10px;
  top: 50%;
  width: 26px;
  height: 34px;
  transform: translateY(-50%);
  background: inherit;
  clip-path: polygon(100% 0, 100% 100%, 0 50%);
  opacity: 0.9;
}

/* 鱼眼 */
.opt--fish::before {
  content: '';
  position: absolute;
  left: 18%;
  top: 24%;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--text-strong);
  opacity: 0.75;
}

.opt--fish.is-right {
  background: linear-gradient(
    150deg,
    color-mix(in srgb, var(--success) 45%, var(--surface-strong)) 0%,
    color-mix(in srgb, var(--success) 20%, var(--surface-strong)) 100%
  );
}

/* ---- 皮肤：地鼠草地 ---- */

.board--mole {
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--leaf-400) 22%, var(--surface-sunken)) 0%,
    color-mix(in srgb, var(--leaf-400) 40%, var(--surface-sunken)) 100%
  );
  row-gap: var(--gap-lg);
}

.opt--mole {
  border-radius: 50% 50% 42% 42%;
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--mango-400) 58%, var(--surface-strong)) 0%,
    color-mix(in srgb, var(--coral-400) 34%, var(--surface-strong)) 100%
  );
  border-color: color-mix(in srgb, var(--surface-strong) 60%, transparent);
}

/* 洞口：压在地鼠脚下的一道深色椭圆 */
.opt--mole .opt__deco {
  left: 8%;
  right: 8%;
  bottom: -12px;
  height: 22px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--stroke-ink) 42%, transparent);
  z-index: 1;
}

/* 两只耳朵 */
.opt--mole::before,
.opt--mole::after {
  content: '';
  position: absolute;
  top: 4px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: inherit;
}

.opt--mole::before {
  left: 14%;
}

.opt--mole::after {
  right: 14%;
}

.opt--mole.is-right {
  background: linear-gradient(
    180deg,
    color-mix(in srgb, var(--success) 42%, var(--surface-strong)) 0%,
    color-mix(in srgb, var(--success) 18%, var(--surface-strong)) 100%
  );
}

/* ------------------------------------------------------------------ 结算 */

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

@media (max-width: 380px) {
  .skins__row {
    grid-template-columns: 1fr;
  }
}
</style>
