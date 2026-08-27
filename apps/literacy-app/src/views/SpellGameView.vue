<script setup>
/**
 * 拼音拼字。
 *
 * 屏幕上写着一个字，下面是被打乱的字母牌，孩子要按顺序把这个字的拼音拼出来。
 * 前面几款小游戏练的都是「看见字→认出它」，这一款反过来练「听见音→拼出它」：
 * 声母韵母得一个一个按顺序摆，拼错了牌就摆不进格子，孩子自己就发现拼错在哪。
 *
 * 字母牌里混了两张这个字用不上的字母，不然把牌全按一遍就拼完了。
 * 声调不进牌面（à 和 a 摆在一起孩子会以为是两个字母），
 * 但题面上的拼音仍然带调，读音这件事不能因为好实现就被抹掉。
 *
 * 每张牌都是真的 <button>：Tab 能走遍全场，回车摆牌；
 * 有实体键盘的话直接敲字母也行，两条通道走的是同一个 place()。
 */
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import CelebrationOverlay from '@/components/CelebrationOverlay.vue'
import VoiceNotice from '@/components/VoiceNotice.vue'
import { useCharPool } from '@/composables/useCharPool.js'
import { useFeedback } from '@/composables/useFeedback.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { isSpeechSupported, speak, stopSpeaking } from '@/utils/speech.js'
import { pinyinLetters } from '@/utils/pinyin.js'
import { pick, sample, shuffle } from '@/utils/random.js'

const ROUNDS = 6
/** 每关多发几张用不上的字母牌，防止「全按一遍」蒙混过关。 */
const EXTRA_KEYS = 2
/** 发干扰牌的字母表：都是拼音里真会出现的字母。 */
const ALPHABET = [...'abcdefghijklmnopqruwxyzü']

const progress = useProgressStore()
const settings = useSettingsStore()
const feedback = useFeedback()
const { pool, usingFallback, drawPool } = useCharPool(4)

const speechOk = isSpeechSupported()

const stageRef = ref(null)

const phase = ref('intro') // intro | playing | done
const round = ref(0)
const score = ref(0)
const misses = ref(0)
/** 连着拼对几个字；音高跟着它一级级往上走。 */
const streak = ref(0)
const target = ref(null)
const answer = ref([])
const keys = ref([])
const slots = ref([])
const answered = ref(false)
const celebrating = ref(false)
const announcement = ref('')

let nextTimer = null

function announce(text) {
  // 同一句话写两次读屏不会再念，补个零宽空格逼它重播
  announcement.value = announcement.value === text ? `${text}\u200b` : text
}

/* -------------------------------------------------------------- 出题 */

function deal() {
  const { due, all } = drawPool()
  const preferred = due.length && Math.random() < 0.6 ? due : all
  // 拼音拆不出字母的字（理论上没有，兜底而已）直接换一个
  const candidates = all.filter((c) => pinyinLetters(c.pinyin).length >= 2)
  const chosen =
    pick(preferred.filter((c) => pinyinLetters(c.pinyin).length >= 2)) ?? pick(candidates) ?? all[0]

  target.value = chosen
  answer.value = pinyinLetters(chosen.pinyin)

  const extras = sample(
    ALPHABET.filter((letter) => !answer.value.includes(letter)),
    EXTRA_KEYS
  )
  keys.value = shuffle([...answer.value, ...extras]).map((letter, i) => ({
    key: `${round.value}-${i}`,
    letter,
    used: false
  }))
  slots.value = []
  answered.value = false
}

function nextRound() {
  round.value += 1
  deal()
  announce(
    `第 ${round.value} 关，共 ${ROUNDS} 关。把「${target.value.char}」的拼音拼出来，` +
      `一共 ${answer.value.length} 个字母，按顺序点字母牌。`
  )
  playPrompt()
}

function playPrompt() {
  if (target.value) speak(target.value.char, { rate: settings.speechRate })
}

function replay() {
  feedback.tap()
  playPrompt()
  announce(
    `再听一次：「${target.value?.char}」，读作 ${target.value?.pinyin}。` +
      `已经拼好 ${slots.value.length} / ${answer.value.length} 个字母。`
  )
}

/* -------------------------------------------------------------- 摆牌 */

const wanted = computed(() => answer.value[slots.value.length] ?? '')

function place(index, event) {
  if (answered.value || phase.value !== 'playing') return
  const card = keys.value[index]
  if (!card || card.used) return

  const anchor = event?.currentTarget ?? null

  if (card.letter !== wanted.value) {
    misses.value += 1
    streak.value = 0
    feedback.wrong(anchor)
    if (target.value) progress.recordAnswer(target.value.char, false)
    announce(
      `「${card.letter}」还不能摆在这里。` +
        `${slots.value.length ? `已经拼出 ${slots.value.join('')}，` : ''}再想想下一个字母是什么。`
    )
    return
  }

  card.used = true
  slots.value.push(card.letter)
  if (slots.value.length < answer.value.length) {
    feedback.tap(anchor)
    announce(`摆上「${card.letter}」，已经拼出 ${slots.value.join('')}。`)
    return
  }

  settle(anchor)
}

function settle(anchor) {
  answered.value = true
  score.value += 1
  streak.value += 1
  feedback.correct(anchor, { cueArg: streak.value })
  progress.recordAnswer(target.value.char, true)
  speak(target.value.char, { rate: settings.speechRate })
  announce(
    `拼对啦！「${target.value.char}」读作 ${target.value.pinyin}。已经拼对 ${score.value} 个字。`
  )
  nextTimer = window.setTimeout(() => {
    if (round.value >= ROUNDS) finish()
    else nextRound()
  }, 1200)
}

/** 摆错位置想反悔：把最后一张牌收回来。 */
function undo() {
  if (answered.value || !slots.value.length) return
  const letter = slots.value.pop()
  const card = [...keys.value].reverse().find((k) => k.used && k.letter === letter)
  if (card) card.used = false
  feedback.tap()
  announce(`收回「${letter}」，现在拼出 ${slots.value.join('') || '空'}。`)
}

/** 有实体键盘就直接敲字母；v 按拼音习惯当 ü 用。 */
function onKeydown(event) {
  if (phase.value !== 'playing' || answered.value) return
  if (event.metaKey || event.ctrlKey || event.altKey) return
  if (event.key === 'Backspace') {
    event.preventDefault()
    undo()
    return
  }
  const typed = event.key?.length === 1 ? event.key.toLowerCase() : ''
  if (!typed || !/[a-zü]/.test(typed)) return
  const letter = typed === 'v' ? 'ü' : typed
  const index = keys.value.findIndex((k) => !k.used && k.letter === letter)
  if (index < 0) return
  event.preventDefault()
  place(index, null)
}

/* -------------------------------------------------------------- 流程 */

function start() {
  feedback.tap()
  window.clearTimeout(nextTimer)
  celebrating.value = false
  phase.value = 'playing'
  round.value = 0
  score.value = 0
  misses.value = 0
  streak.value = 0
  nextRound()
  // 开局把焦点放进牌桌，敲键盘的人不用先按一串 Tab
  nextTick(() => stageRef.value?.focus())
}

function finish() {
  phase.value = 'done'
  announce(`这一局结束，拼对 ${score.value} / ${ROUNDS} 个字，摆错 ${misses.value} 次。`)
  if (score.value >= ROUNDS) celebrating.value = true
  else feedback.tap()
}

const earnedStars = computed(() => {
  if (misses.value === 0) return 3
  return misses.value <= 3 ? 2 : 1
})

const stageLabel = computed(
  () =>
    `拼音拼字。把「${target.value?.char ?? ''}」的拼音按顺序拼出来，` +
    `点字母牌或者直接敲键盘上的字母，退格键收回上一张。`
)

onBeforeUnmount(() => {
  window.clearTimeout(nextTimer)
  stopSpeaking()
})
</script>

<template>
  <div class="page spell-game">
    <p class="sr-only" role="status" aria-live="polite" aria-atomic="true">{{ announcement }}</p>

    <!-- 开始页 -->
    <section v-if="phase === 'intro'" class="card intro">
      <div class="intro__emoji" aria-hidden="true">🔤</div>
      <h2 class="intro__title">拼音拼字</h2>
      <p class="intro__desc">
        屏幕上写着一个字，下面的字母牌被打乱了。<br />
        按顺序点字母，把它的拼音拼出来，一共 {{ ROUNDS }} 关。
      </p>

      <VoiceNotice fallback="每个字的拼音会写在字的下面，可以请家长读给你听。" />

      <p v-if="usingFallback" class="warn">💡 还没学够 4 个字，这一局先用课程最前面的字来练习。</p>
      <p v-else class="muted">这一局从你学过的 {{ pool.length }} 个字里出题。</p>

      <button class="btn btn--primary btn--lg btn--block" type="button" @click="start">
        开始拼 🚀
      </button>
    </section>

    <!-- 游戏中 -->
    <template v-else-if="phase === 'playing'">
      <section class="hud card card--flat">
        <div class="hud__row">
          <span class="pill">第 {{ round }} / {{ ROUNDS }} 关</span>
          <span class="pill pill--accent">⭐ {{ score }}</span>
          <span v-if="misses" class="pill">✋ 摆错 {{ misses }}</span>
        </div>
      </section>

      <section class="quest card">
        <p class="quest__label">拼出这个字的拼音</p>
        <p class="quest__char">{{ target?.char }}</p>
        <p class="quest__pinyin">{{ target?.pinyin }}</p>
        <button v-if="speechOk" class="btn btn--ghost btn--sm" type="button" @click="replay">
          🔊 再听一次
        </button>
      </section>

      <div
        ref="stageRef"
        class="spell"
        :class="{ 'spell--quiet': settings.reduceMotion }"
        role="group"
        tabindex="0"
        :aria-label="stageLabel"
        :data-answered="answered"
        @keydown="onKeydown"
      >
        <ol class="spell__slots" :data-filled="slots.length" :data-size="answer.length">
          <li
            v-for="(letter, i) in answer"
            :key="`slot-${i}`"
            class="spell__slot"
            :class="{ 'is-filled': i < slots.length, 'is-next': i === slots.length && !answered }"
            :data-letter="slots[i] ?? ''"
          >
            <span v-if="i < slots.length">{{ slots[i] }}</span>
            <span v-else class="spell__blank" aria-hidden="true">_</span>
          </li>
        </ol>

        <p class="sr-only">
          已经拼出 {{ slots.join('') || '还没有字母' }}，还差 {{ answer.length - slots.length }} 个字母。
        </p>

        <ul class="spell__keys">
          <li v-for="(card, i) in keys" :key="card.key">
            <button
              class="spell__key"
              :class="{ 'is-used': card.used }"
              type="button"
              :data-letter="card.letter"
              :disabled="card.used || answered"
              :aria-label="`字母 ${card.letter}`"
              @click="place(i, $event)"
            >
              <span aria-hidden="true">{{ card.letter }}</span>
            </button>
          </li>
        </ul>
      </div>

      <div class="spell__acts">
        <button
          class="btn btn--ghost btn--sm"
          type="button"
          :disabled="!slots.length || answered"
          @click="undo"
        >
          ↩️ 收回一张
        </button>
      </div>

      <p class="muted spell__tip">键盘：Tab 选牌、回车摆牌，也可以直接敲字母，退格收回。</p>
    </template>

    <!-- 结算 -->
    <section v-else class="card intro">
      <div class="intro__emoji" aria-hidden="true">{{ score >= ROUNDS ? '🏆' : '💪' }}</div>
      <h2 class="intro__title">{{ score >= ROUNDS ? '全部拼对啦！' : '再拼一次更熟练' }}</h2>
      <p class="intro__desc">
        这一局拼对 <strong>{{ score }}</strong> / {{ ROUNDS }} 个字，摆错 {{ misses }} 次。
      </p>
      <div class="intro__actions">
        <button class="btn btn--primary btn--lg" type="button" @click="start">再拼一局 🔁</button>
        <RouterLink class="btn btn--ghost btn--lg" to="/games" @click="feedback.tap()">
          换个游戏 🎲
        </RouterLink>
      </div>
    </section>

    <CelebrationOverlay
      :open="celebrating"
      emoji="🔤"
      title="全部拼对！"
      :subtitle="`拼对 ${score} / ${ROUNDS} 个字`"
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
  font-size: clamp(3rem, 22vw, 4.4rem);
  font-weight: var(--fw-heavy);
  line-height: 1.1;
  color: var(--text-strong);
}

.quest__pinyin {
  font-size: var(--fs-md);
  font-weight: var(--fw-bold);
  color: var(--text);
}

/* ------------------------------------------------------------ 牌桌 */

.spell {
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
  padding: var(--gap-sm);
  border-radius: var(--radius-md);
  outline-offset: 4px;
}

.spell__slots {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--gap-xs);
  list-style: none;
  padding: 0;
  margin: 0;
}

.spell__slot {
  display: grid;
  place-items: center;
  min-width: 46px;
  min-height: 56px;
  padding: 0 6px;
  border-radius: var(--radius-sm);
  border: 2px dashed color-mix(in srgb, var(--text-soft) 55%, transparent);
  background: var(--surface-sunken);
  font-family: var(--font-num);
  font-size: 1.7rem;
  font-weight: var(--fw-black);
  color: var(--text-strong);
  transition: border-color var(--dur-fast) ease, background var(--dur-fast) ease;
}

.spell__slot.is-filled {
  border-style: solid;
  border-color: var(--success);
  background: color-mix(in srgb, var(--success) 16%, var(--surface-strong));
}

/* 下一个该填的格子亮起来，孩子知道笔尖在哪 */
.spell__slot.is-next {
  border-color: var(--brand);
  background: var(--brand-soft);
}

.spell__blank {
  color: var(--text-soft);
}

.spell__keys {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--gap-sm);
  list-style: none;
  padding: 0;
  margin: 0;
}

.spell__key {
  display: grid;
  place-items: center;
  min-width: var(--tap-min);
  min-height: var(--tap-min);
  padding: 8px 14px;
  border-radius: var(--radius-md);
  border: 2px solid color-mix(in srgb, var(--brand) 35%, transparent);
  background: var(--surface-strong);
  box-shadow: var(--shadow-sm);
  font-family: var(--font-num);
  font-size: 1.5rem;
  font-weight: var(--fw-black);
  color: var(--text-strong);
  transition: transform var(--dur-fast) var(--ease-pop), opacity var(--dur-fast) ease;
}

.spell__key:active:not(:disabled) {
  transform: scale(0.94);
}

.spell__key.is-used {
  opacity: 0.35;
}

/* 家长面板关掉动效：牌不再缩放，只留颜色变化 */
.spell--quiet .spell__key,
.spell--quiet .spell__slot {
  transition: none;
}

.spell--quiet .spell__key:active:not(:disabled) {
  transform: none;
}

.spell__acts {
  display: flex;
  justify-content: center;
}

.spell__tip {
  text-align: center;
  font-size: 0.8rem;
}

@media (prefers-reduced-motion: reduce) {
  .spell__key,
  .spell__slot {
    transition: none;
  }

  .spell__key:active:not(:disabled) {
    transform: none;
  }
}
</style>
