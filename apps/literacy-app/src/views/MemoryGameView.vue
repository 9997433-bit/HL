<script setup>
/**
 * 配对记忆（翻翻卡）。
 *
 * 一对牌 = 一个汉字 + 它的拼音。翻开两张，配上了就留在桌面上，
 * 配错了盖回去。这样孩子每翻一次都在把「字形」和「读音」按在一起，
 * 比单纯的图形记忆多了一层识字价值。
 *
 * 每张牌都是真的 <button>：Tab 能走遍全场，回车 / 空格就是翻牌，
 * 不需要再造一套自定义按键。盖着的牌不把汉字写进 DOM——写进去读屏
 * 会直接把答案念出来，那这局就没得玩了。
 */
import { computed, onBeforeUnmount, ref } from 'vue'
import StarBurst from '@/components/StarBurst.vue'
import CelebrationOverlay from '@/components/CelebrationOverlay.vue'
import { useCharPool } from '@/composables/useCharPool.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { speak, stopSpeaking } from '@/utils/speech.js'
import { sample, shuffle } from '@/utils/random.js'
import { sfx } from '@/utils/sfx.js'

/** 难度只改「几对牌」，其余规则完全一样。 */
const LEVELS = [
  { id: 'easy', name: '简单', pairs: 4, emoji: '🐣' },
  { id: 'normal', name: '标准', pairs: 6, emoji: '🐤' },
  { id: 'hard', name: '挑战', pairs: 8, emoji: '🐔' }
]

/** 配错了盖回去之前留给孩子看一眼的时间。 */
const FLIP_BACK_MS = 900

const progress = useProgressStore()
const settings = useSettingsStore()

const burstRef = ref(null)

const levelId = ref('easy')
const level = computed(() => LEVELS.find((l) => l.id === levelId.value) ?? LEVELS[0])
const { pool, usingFallback, drawPool } = useCharPool(4)

const phase = ref('intro') // intro | playing | done
const cards = ref([])
const flipped = ref([]) // 当前翻开、还没判定的牌 index
const flips = ref(0)
const mistakes = ref(0)
const locked = ref(false)
const celebrating = ref(false)
const announcement = ref('')

let flipTimer = null

function announce(text) {
  announcement.value = announcement.value === text ? `${text}\u200b` : text
}

const matchedCount = computed(() => cards.value.filter((c) => c.state === 'matched').length / 2)
const cleared = computed(() => cards.value.length > 0 && matchedCount.value === level.value.pairs)

function chooseLevel(id) {
  sfx.tap()
  levelId.value = id
}

function deal() {
  const { due, rest, all } = drawPool()
  // 到期要复习的字优先上桌，不够再从其余的字里补
  const wanted = level.value.pairs
  const picked = [...sample(due, wanted), ...sample(rest, Math.max(0, wanted - due.length))]
  const chars = (picked.length >= wanted ? picked : sample(all, wanted)).slice(0, wanted)

  cards.value = shuffle(
    chars.flatMap((c, i) => [
      { id: `${c.char}-char-${i}`, pairId: c.char, face: 'char', char: c.char, pinyin: c.pinyin },
      { id: `${c.char}-pinyin-${i}`, pairId: c.char, face: 'pinyin', char: c.char, pinyin: c.pinyin }
    ])
  ).map((c) => ({ ...c, state: 'down' }))
}

function start() {
  sfx.tap()
  window.clearTimeout(flipTimer)
  celebrating.value = false
  phase.value = 'playing'
  flips.value = 0
  mistakes.value = 0
  flipped.value = []
  locked.value = false
  deal()
  announce(
    `配对记忆开始，一共 ${level.value.pairs} 对牌，${cards.value.length} 张。` +
      `翻开一个汉字和它的拼音就算配上。`
  )
}

function labelOf(card, index) {
  if (card.state === 'down') return `第 ${index + 1} 张牌，还盖着，按回车翻开`
  const face = card.face === 'char' ? `汉字「${card.char}」` : `拼音 ${card.pinyin}`
  return card.state === 'matched' ? `${face}，已经配对` : face
}

function flip(index) {
  if (locked.value || phase.value !== 'playing') return
  const card = cards.value[index]
  if (!card || card.state !== 'down') return

  card.state = 'up'
  flips.value += 1
  flipped.value.push(index)
  sfx.tap()
  if (card.face === 'char') speak(card.char, { rate: settings.speechRate })
  announce(
    card.face === 'char'
      ? `翻开汉字「${card.char}」。`
      : `翻开拼音 ${card.pinyin}，它是哪个字的读音？`
  )

  if (flipped.value.length < 2) return

  const [a, b] = flipped.value.map((i) => cards.value[i])
  const same = a.pairId === b.pairId && a.face !== b.face
  if (same) settleMatch(a, b)
  else settleMiss(a, b)
}

function settleMatch(a, b) {
  a.state = 'matched'
  b.state = 'matched'
  flipped.value = []
  sfx.correct()
  burstRef.value?.burst()
  progress.recordAnswer(a.pairId, true)
  announce(`配上啦！「${a.char}」读作 ${a.pinyin}。已经配好 ${matchedCount.value} 对。`)
  if (cleared.value) window.setTimeout(finish, 600)
}

function settleMiss(a, b) {
  mistakes.value += 1
  locked.value = true
  sfx.wrong()
  progress.recordAnswer(a.pairId, false)
  announce(
    `「${a.face === 'char' ? a.char : a.pinyin}」和「${b.face === 'char' ? b.char : b.pinyin}」` +
      `不是一对，记住它们的位置，两张牌要盖回去了。`
  )
  flipTimer = window.setTimeout(() => {
    for (const card of [a, b]) if (card.state === 'up') card.state = 'down'
    flipped.value = []
    locked.value = false
  }, FLIP_BACK_MS)
}

function finish() {
  phase.value = 'done'
  announce(
    `全部配对完成！翻了 ${flips.value} 次，配错 ${mistakes.value} 次。`
  )
  celebrating.value = true
}

const earnedStars = computed(() => {
  if (mistakes.value === 0) return 3
  return mistakes.value <= level.value.pairs ? 2 : 1
})

onBeforeUnmount(() => {
  window.clearTimeout(flipTimer)
  stopSpeaking()
})
</script>

<template>
  <div class="page memory-game">
    <StarBurst ref="burstRef" />
    <p class="sr-only" role="status" aria-live="polite" aria-atomic="true">{{ announcement }}</p>

    <!-- 开始页 -->
    <section v-if="phase === 'intro'" class="card intro">
      <div class="intro__emoji" aria-hidden="true">🃏</div>
      <h2 class="intro__title">配对记忆</h2>
      <p class="intro__desc">
        每个字都有一张「汉字卡」和一张「拼音卡」。<br />
        翻开两张，配成一对就留在桌上，全部配完就赢啦 🎊
      </p>

      <fieldset class="levels">
        <legend class="levels__legend">今天玩几对？</legend>
        <div class="levels__row">
          <button
            v-for="l in LEVELS"
            :key="l.id"
            class="levelbtn"
            :class="{ 'is-on': l.id === levelId }"
            type="button"
            :aria-pressed="l.id === levelId"
            @click="chooseLevel(l.id)"
          >
            <span class="levelbtn__emoji" aria-hidden="true">{{ l.emoji }}</span>
            <span class="levelbtn__name">{{ l.name }}</span>
            <span class="levelbtn__desc">{{ l.pairs }} 对</span>
          </button>
        </div>
      </fieldset>

      <p v-if="usingFallback" class="warn">
        💡 还没学够 4 个字，这一局先用课程最前面的字来练习。
      </p>
      <p v-else class="muted">这一局从你学过的 {{ pool.length }} 个字里发牌。</p>

      <button class="btn btn--primary btn--lg btn--block" type="button" @click="start">
        开始翻牌 🚀
      </button>
    </section>

    <!-- 游戏中 -->
    <template v-else-if="phase === 'playing'">
      <section class="hud card card--flat">
        <div class="hud__row">
          <span class="pill">🎴 配好 {{ matchedCount }} / {{ level.pairs }}</span>
          <span class="pill pill--accent">🔄 翻了 {{ flips }} 次</span>
          <span v-if="mistakes" class="pill">🙈 配错 {{ mistakes }}</span>
        </div>
      </section>

      <section
        class="deck"
        :data-cleared="cleared"
        :style="{ '--deck-cols': level.pairs > 4 ? 4 : 2 }"
      >
        <button
          v-for="(card, i) in cards"
          :key="card.id"
          class="mcard"
          :class="`is-${card.state}`"
          type="button"
          :data-state="card.state"
          :data-face="card.state === 'down' ? undefined : card.face"
          :data-char="card.state === 'down' ? undefined : card.char"
          :disabled="card.state === 'matched'"
          :aria-label="labelOf(card, i)"
          @click="flip(i)"
        >
          <span v-if="card.state === 'down'" class="mcard__back" aria-hidden="true">❓</span>
          <span v-else-if="card.face === 'char'" class="mcard__char" aria-hidden="true">
            {{ card.char }}
          </span>
          <span v-else class="mcard__pinyin" aria-hidden="true">{{ card.pinyin }}</span>
        </button>
      </section>

      <p class="muted memory__tip">键盘：Tab 走到一张牌，回车或空格翻开它。</p>
    </template>

    <!-- 结算 -->
    <section v-else class="card intro">
      <div class="intro__emoji" aria-hidden="true">🎊</div>
      <h2 class="intro__title">全部配对完成！</h2>
      <p class="intro__desc">
        {{ level.pairs }} 对牌，翻了 <strong>{{ flips }}</strong> 次，配错 {{ mistakes }} 次。
      </p>
      <div class="intro__actions">
        <button class="btn btn--primary btn--lg" type="button" @click="start">再来一局 🔁</button>
        <RouterLink class="btn btn--ghost btn--lg" to="/games" @click="sfx.tap()">
          换个游戏 🎲
        </RouterLink>
      </div>
    </section>

    <CelebrationOverlay
      :open="celebrating"
      emoji="🃏"
      title="配对全清！"
      :subtitle="`${level.pairs} 对牌，翻了 ${flips} 次`"
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
  font-size: 1.6rem;
  font-weight: 800;
  color: var(--text-strong);
}

.intro__desc {
  line-height: 1.9;
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
  font-size: 0.85rem;
  line-height: 1.7;
}

.levels {
  width: 100%;
  border: none;
  padding: 0;
  margin: 0;
}

.levels__legend {
  padding: 0 0 6px;
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--text-soft);
}

.levels__row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--gap-sm);
}

.levelbtn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  min-height: var(--tap-min);
  padding: 10px 6px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  border: 3px solid transparent;
}

.levelbtn.is-on {
  border-color: var(--brand);
  background: var(--brand-soft);
}

.levelbtn__emoji {
  font-size: 1.5rem;
  line-height: 1.2;
}

.levelbtn__name {
  font-size: 0.85rem;
  font-weight: 800;
  color: var(--text-strong);
}

.levelbtn__desc {
  font-size: 0.7rem;
  color: var(--text-soft);
}

.hud__row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

/* ------------------------------------------------------------------ 牌桌 */

.deck {
  display: grid;
  grid-template-columns: repeat(var(--deck-cols), 1fr);
  gap: var(--gap-sm);
}

.mcard {
  display: grid;
  place-items: center;
  aspect-ratio: 1 / 1.2;
  min-height: var(--tap-min);
  border-radius: var(--radius-lg);
  background: var(--surface-strong);
  border: 3px solid transparent;
  box-shadow: var(--shadow-md);
  transition: transform var(--dur-fast) var(--ease-pop), background var(--dur-fast) ease,
    border-color var(--dur-fast) ease;
}

.mcard:active:not(:disabled) {
  transform: scale(0.95);
}

.mcard.is-down {
  background: linear-gradient(
    160deg,
    color-mix(in srgb, var(--sky-400) 34%, var(--surface-strong)) 0%,
    color-mix(in srgb, var(--grape-400) 26%, var(--surface-strong)) 100%
  );
}

.mcard.is-up {
  border-color: var(--brand);
  background: var(--brand-soft);
}

.mcard.is-matched {
  border-color: var(--success);
  background: color-mix(in srgb, var(--success) 16%, var(--surface-strong));
  opacity: 1;
}

.mcard__back {
  font-size: 1.8rem;
  line-height: 1;
}

.mcard__char {
  font-size: clamp(1.8rem, 9vw, 2.8rem);
  line-height: 1;
  font-weight: 700;
  color: var(--text-strong);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

.mcard__pinyin {
  padding: 0 4px;
  font-size: clamp(0.85rem, 4vw, 1.15rem);
  font-weight: 700;
  color: var(--text-strong);
  word-break: break-word;
}

.memory__tip {
  text-align: center;
  font-size: 0.8rem;
}
</style>
