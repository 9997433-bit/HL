<script setup>
/**
 * 找不同。
 *
 * 一屏格子里铺着同一个字，只有一个是别的字——而且那个字长得很像
 * （同一个部首，或者笔画数只差一两笔）。孩子要做的是「看清楚字形」，
 * 这正是低年级最容易混的一关：日和目、人和入、大和太。
 *
 * 干扰字从**已学字**里挑，挑不出形近的才退回随便一个别的字，
 * 所以永远不会冒出没教过的生字。
 *
 * 每个格子都是 <button>：Tab 遍历、回车作答，键盘用户不用任何额外手势。
 */
import { computed, onBeforeUnmount, ref } from 'vue'
import StarBurst from '@/components/StarBurst.vue'
import CelebrationOverlay from '@/components/CelebrationOverlay.vue'
import { useCharPool } from '@/composables/useCharPool.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { speak, stopSpeaking } from '@/utils/speech.js'
import { pick, shuffle } from '@/utils/random.js'
import { sfx } from '@/utils/sfx.js'

const ROUNDS = 6
const CELLS = 12

const progress = useProgressStore()
const settings = useSettingsStore()
const { pool, usingFallback, drawPool } = useCharPool(2)

const burstRef = ref(null)

const phase = ref('intro') // intro | playing | done
const round = ref(0)
const score = ref(0)
const misses = ref(0)
const cells = ref([])
const base = ref(null)
const odd = ref(null)
const answered = ref(false)
const ruledOut = ref([])
const celebrating = ref(false)
const announcement = ref('')

let nextTimer = null

function announce(text) {
  announcement.value = announcement.value === text ? `${text}\u200b` : text
}

/**
 * 形近判定：同部首优先，其次笔画数相差不超过 1。
 * 这两条规则挑出来的字，恰好覆盖了低年级最常见的混淆对。
 */
function lookalikesOf(target, list) {
  const others = list.filter((c) => c.char !== target.char)
  const sameRadical = others.filter((c) => c.radical === target.radical)
  const closeStrokes = others.filter((c) => Math.abs(c.strokes - target.strokes) <= 1)
  const near = [...new Set([...sameRadical, ...closeStrokes])]
  return near.length ? near : others
}

function nextRound() {
  const { due, all } = drawPool()
  if (all.length < 2) return
  const preferred = due.length && Math.random() < 0.6 ? due : all
  const target = pick(preferred) ?? all[0]
  const other = pick(lookalikesOf(target, all)) ?? all.find((c) => c.char !== target.char)

  base.value = target
  odd.value = other
  answered.value = false
  ruledOut.value = []

  const oddIndex = Math.floor(Math.random() * CELLS)
  cells.value = shuffle(
    Array.from({ length: CELLS }, (_, i) => (i === oddIndex ? other : target))
  ).map((c, i) => ({ key: `${round.value}-${i}`, char: c.char, pinyin: c.pinyin }))

  round.value += 1
  announce(
    `第 ${round.value} 关，共 ${ROUNDS} 关。${CELLS} 个格子里只有一个字跟别的不一样，把它找出来。`
  )
}

function choose(cell, index) {
  if (answered.value || phase.value !== 'playing') return
  const correct = cell.char === odd.value?.char

  if (correct) {
    answered.value = true
    score.value += 1
    sfx.correct()
    burstRef.value?.burst()
    progress.recordAnswer(cell.char, true)
    speak(cell.char, { rate: settings.speechRate })
    announce(
      `答对了！不一样的是「${cell.char}」，读作 ${cell.pinyin}；` +
        `其余都是「${base.value.char}」。已经答对 ${score.value} 关。`
    )
    nextTimer = window.setTimeout(() => {
      if (round.value >= ROUNDS) finish()
      else nextRound()
    }, 1100)
    return
  }

  misses.value += 1
  sfx.wrong()
  if (!ruledOut.value.includes(index)) ruledOut.value.push(index)
  if (odd.value) progress.recordAnswer(odd.value.char, false)
  announce(`「${cell.char}」和大多数格子一样，不是它。再仔细看看字的形状。`)
}

function start() {
  sfx.tap()
  window.clearTimeout(nextTimer)
  celebrating.value = false
  phase.value = 'playing'
  round.value = 0
  score.value = 0
  misses.value = 0
  nextRound()
}

function finish() {
  phase.value = 'done'
  announce(`这一局结束，答对 ${score.value} / ${ROUNDS} 关，看错 ${misses.value} 次。`)
  if (score.value >= ROUNDS) celebrating.value = true
  else sfx.tap()
}

const earnedStars = computed(() => {
  if (misses.value === 0) return 3
  return misses.value <= 3 ? 2 : 1
})

onBeforeUnmount(() => {
  window.clearTimeout(nextTimer)
  stopSpeaking()
})
</script>

<template>
  <div class="page spot-game">
    <StarBurst ref="burstRef" />
    <p class="sr-only" role="status" aria-live="polite" aria-atomic="true">{{ announcement }}</p>

    <!-- 开始页 -->
    <section v-if="phase === 'intro'" class="card intro">
      <div class="intro__emoji" aria-hidden="true">🔍</div>
      <h2 class="intro__title">找不同</h2>
      <p class="intro__desc">
        {{ CELLS }} 个格子里藏着一个「不一样」的字，<br />
        它跟其他字长得很像，看仔细再点它。一共 {{ ROUNDS }} 关。
      </p>

      <p v-if="usingFallback" class="warn">
        💡 还没学够 2 个字，这一局先用课程最前面的字来练习。
      </p>
      <p v-else class="muted">这一局从你学过的 {{ pool.length }} 个字里出题。</p>

      <button class="btn btn--primary btn--lg btn--block" type="button" @click="start">
        开始找 🚀
      </button>
    </section>

    <!-- 游戏中 -->
    <template v-else-if="phase === 'playing'">
      <section class="hud card card--flat">
        <div class="hud__row">
          <span class="pill">第 {{ round }} / {{ ROUNDS }} 关</span>
          <span class="pill pill--accent">⭐ {{ score }}</span>
          <span v-if="misses" class="pill">👀 看错 {{ misses }}</span>
        </div>
      </section>

      <p class="spot__quest">哪个字跟别的不一样？</p>

      <section class="spot" :data-answered="answered">
        <button
          v-for="(cell, i) in cells"
          :key="cell.key"
          class="spot__cell"
          :class="{
            'is-right': answered && cell.char === odd?.char,
            'is-out': ruledOut.includes(i)
          }"
          type="button"
          :data-char="cell.char"
          :disabled="answered"
          :aria-label="`第 ${i + 1} 个格子，${cell.char}`"
          @click="choose(cell, i)"
        >
          <span aria-hidden="true">{{ cell.char }}</span>
        </button>
      </section>

      <p class="muted spot__tip">键盘：Tab 走到一个格子，回车或空格选它。</p>
    </template>

    <!-- 结算 -->
    <section v-else class="card intro">
      <div class="intro__emoji" aria-hidden="true">{{ score >= ROUNDS ? '🏆' : '💪' }}</div>
      <h2 class="intro__title">{{ score >= ROUNDS ? '全部找对啦！' : '眼睛再尖一点' }}</h2>
      <p class="intro__desc">
        这一局答对 <strong>{{ score }}</strong> / {{ ROUNDS }} 关，看错 {{ misses }} 次。
      </p>
      <div class="intro__actions">
        <button class="btn btn--primary btn--lg" type="button" @click="start">再找一局 🔁</button>
        <RouterLink class="btn btn--ghost btn--lg" to="/games" @click="sfx.tap()">
          换个游戏 🎲
        </RouterLink>
      </div>
    </section>

    <CelebrationOverlay
      :open="celebrating"
      emoji="🔍"
      title="全部找对！"
      :subtitle="`答对 ${score} / ${ROUNDS} 关`"
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

.hud__row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.spot__quest {
  text-align: center;
  font-weight: 800;
  color: var(--text-strong);
}

.spot {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--gap-sm);
}

.spot__cell {
  display: grid;
  place-items: center;
  aspect-ratio: 1;
  min-height: var(--tap-min);
  border-radius: var(--radius-md);
  background: var(--surface-strong);
  border: 3px solid transparent;
  box-shadow: var(--shadow-sm);
  font-size: clamp(1.6rem, 8vw, 2.2rem);
  font-weight: 700;
  color: var(--text-strong);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
  transition: transform var(--dur-fast) var(--ease-pop), border-color var(--dur-fast) ease,
    background var(--dur-fast) ease;
}

.spot__cell:active:not(:disabled) {
  transform: scale(0.94);
}

.spot__cell.is-out {
  opacity: 0.45;
}

.spot__cell.is-right {
  border-color: var(--success);
  background: color-mix(in srgb, var(--success) 18%, var(--surface-strong));
}

.spot__tip {
  text-align: center;
  font-size: 0.8rem;
}

@media (max-width: 340px) {
  .spot {
    grid-template-columns: repeat(3, 1fr);
  }
}
</style>
