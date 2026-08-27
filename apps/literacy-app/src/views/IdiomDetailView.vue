<script setup>
/**
 * 成语小剧场。
 *
 * 一条成语拆成四步：整体听读 → 逐字拆解 → 三格故事 → 情景小测。
 * 故事分格逐条揭示（而不是一次铺满），孩子的注意力更容易跟着走。
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import gsap from 'gsap'
import StarBurst from '@/components/StarBurst.vue'
import VoiceNotice from '@/components/VoiceNotice.vue'
import { IDIOMS, getIdiom } from '@/data/idioms.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { speak, stopSpeaking } from '@/utils/speech.js'
import { sfx } from '@/utils/sfx.js'

const props = defineProps({ id: { type: String, required: true } })

const router = useRouter()
const progress = useProgressStore()
const settings = useSettingsStore()

const burstRef = ref(null)
const storyRef = ref(null)

/** 已经揭示到第几格故事（0 表示一格都还没翻开）。 */
const revealed = ref(1)
const picked = ref(null)
const solved = ref(false)

/** 情景小测的对错只靠边框色和一行小字表达，读屏要单独说一遍。 */
const announcement = ref('')

const idiom = computed(() => getIdiom(props.id))

const index = computed(() => IDIOMS.findIndex((i) => i.id === props.id))
const prev = computed(() => (index.value > 0 ? IDIOMS[index.value - 1] : null))
const next = computed(() =>
  index.value >= 0 && index.value < IDIOMS.length - 1 ? IDIOMS[index.value + 1] : null
)

const record = computed(() => progress.idioms[props.id] || null)
const allRevealed = computed(() => !!idiom.value && revealed.value >= idiom.value.story.length)

/**
 * 头图只把成语自带的两个插画色交给 CSS，真正的配比由主题决定：
 * 明亮主题几乎原色，护眼主题掺一小半，夜间主题只留一点色相。
 * 这样换 data-theme 时头图跟着走，不会在夜间模式里糊上一块刺眼的浅黄。
 */
const heroTint = computed(() =>
  idiom.value ? { '--art-a': idiom.value.palette[0], '--art-b': idiom.value.palette[1] } : {}
)

function say(text, rate) {
  sfx.tap()
  speak(text, { rate: rate ?? settings.speechRate })
}

function readWhole() {
  if (!idiom.value) return
  say(`${idiom.value.word}。${idiom.value.meaning}`, settings.speechRate - 0.05)
}

function revealNext() {
  if (!idiom.value || allRevealed.value) return
  sfx.page()
  revealed.value += 1
  if (settings.speechOn) speak(idiom.value.story[revealed.value - 1].text, { rate: settings.speechRate })
  animateLastBeat()
}

function animateLastBeat() {
  if (settings.reduceMotion) return
  requestAnimationFrame(() => {
    const beats = storyRef.value?.querySelectorAll('.beat')
    const last = beats?.[beats.length - 1]
    if (!last) return
    gsap.fromTo(
      last,
      { opacity: 0, x: 26, scale: 0.96 },
      { opacity: 1, x: 0, scale: 1, duration: 0.4, ease: 'back.out(1.5)' }
    )
  })
}

function choose(i) {
  if (solved.value || !idiom.value) return
  picked.value = i
  const correct = i === idiom.value.quiz.answer
  progress.markIdiomQuiz(idiom.value.id, correct)
  if (correct) {
    solved.value = true
    sfx.correct()
    burstRef.value?.burst()
    announcement.value = `答对啦！${idiom.value.quiz.tip}`
  } else {
    sfx.wrong()
    announcement.value = `选的「${idiom.value.quiz.options[i]}」不对，再想想，换一个试试看。`
  }
}

function optionClass(i) {
  if (picked.value === null) return ''
  if (i === idiom.value.quiz.answer && solved.value) return 'is-right'
  if (i === picked.value && !solved.value) return 'is-wrong'
  return ''
}

function reset() {
  revealed.value = 1
  picked.value = null
  solved.value = false
  announcement.value = ''
  stopSpeaking()
}

function enter() {
  if (!idiom.value) {
    router.replace('/idioms')
    return
  }
  reset()
  progress.markIdiomSeen(idiom.value.id)
}

onMounted(enter)
watch(() => props.id, enter)
</script>

<template>
  <div v-if="idiom" class="page idiom">
    <StarBurst ref="burstRef" />

    <!-- 成语本体 -->
    <section class="hero card" :style="heroTint">
      <span class="hero__emoji" aria-hidden="true">{{ idiom.emoji }}</span>
      <button class="hero__word" type="button" @click="readWhole">
        <span class="hero__pinyin">{{ idiom.pinyin }}</span>
        <span class="hero__text">{{ idiom.word }}</span>
        <span class="hero__hint">点一下，听老师读 🔊</span>
      </button>
      <p class="hero__meaning">{{ idiom.meaning }}</p>
      <div class="hero__pills">
        <span v-if="record?.quizRight" class="pill">🏅 答对过 {{ record.quizRight }} 次</span>
        <span v-else-if="record?.seen" class="pill">🌱 学过了</span>
      </div>
    </section>

    <VoiceNotice fallback="小剧场的字都写在屏幕上，家长可以照着读。" />

    <!-- 逐字拆解 -->
    <section class="card stack">
      <h3 class="section-title">
        <span class="section-title__emoji" aria-hidden="true">🔍</span>
        一个字一个字看
      </h3>
      <ul class="chars">
        <li v-for="c in idiom.chars" :key="c.c">
          <button class="charbox" type="button" @click="say(c.c)">
            <span class="charbox__pinyin">{{ c.p }}</span>
            <span class="charbox__glyph tianzige">{{ c.c }}</span>
            <span class="charbox__meaning">{{ c.m }}</span>
          </button>
        </li>
      </ul>
    </section>

    <!-- 三格故事 -->
    <section class="card stack">
      <h3 class="section-title">
        <span class="section-title__emoji" aria-hidden="true">🎬</span>
        小剧场
        <span class="section-title__count muted">{{ revealed }} / {{ idiom.story.length }}</span>
      </h3>

      <ol ref="storyRef" class="story">
        <li
          v-for="(s, i) in idiom.story.slice(0, revealed)"
          :key="i"
          class="beat"
        >
          <span class="beat__no" aria-hidden="true">{{ i + 1 }}</span>
          <span class="beat__emoji" aria-hidden="true">{{ s.emoji }}</span>
          <p class="beat__text">{{ s.text }}</p>
          <button class="beat__speak" type="button" :aria-label="`朗读第 ${i + 1} 段`" @click="say(s.text)">
            🔊
          </button>
        </li>
      </ol>

      <button v-if="!allRevealed" class="btn btn--primary btn--block" type="button" @click="revealNext">
        接下来发生了什么？ →
      </button>
      <p v-else class="lesson">
        <strong>💡 这个成语告诉我们：</strong>
        {{ idiom.lesson }}
      </p>
    </section>

    <!-- 情景小测 -->
    <section v-if="allRevealed && idiom.quiz" class="card stack">
      <h3 class="section-title">
        <span class="section-title__emoji" aria-hidden="true">🤔</span>
        想一想
      </h3>
      <p class="quiz__q">{{ idiom.quiz.q }}</p>
      <ul class="quiz__options">
        <li v-for="(opt, i) in idiom.quiz.options" :key="opt">
          <button
            class="choice"
            :class="optionClass(i)"
            type="button"
            :disabled="solved"
            @click="choose(i)"
          >
            <span class="choice__index" aria-hidden="true">{{ 'ABC'[i] }}</span>
            <span class="choice__text">{{ opt }}</span>
          </button>
        </li>
      </ul>
      <p class="sr-only" role="status" aria-live="polite" aria-atomic="true">{{ announcement }}</p>
      <p v-if="solved" class="quiz__tip" aria-hidden="true">🎉 答对啦！{{ idiom.quiz.tip }}</p>
      <p v-else-if="picked !== null" class="quiz__tip quiz__tip--miss" aria-hidden="true">
        再想想，换一个试试看～
      </p>
    </section>

    <!-- 翻页 -->
    <nav class="pager">
      <RouterLink
        class="btn btn--ghost"
        :class="{ 'is-disabled': !prev }"
        :to="prev ? `/idioms/${prev.id}` : ''"
        @click="(e) => (!prev ? e.preventDefault() : sfx.tap())"
      >
        ← {{ prev ? prev.word : '没有了' }}
      </RouterLink>
      <RouterLink class="btn btn--ghost" to="/idioms" @click="sfx.tap()">🏮 全部成语</RouterLink>
      <RouterLink
        class="btn btn--ghost"
        :class="{ 'is-disabled': !next }"
        :to="next ? `/idioms/${next.id}` : ''"
        @click="(e) => (!next ? e.preventDefault() : sfx.tap())"
      >
        {{ next ? next.word : '没有了' }} →
      </RouterLink>
    </nav>
  </div>
</template>

<style scoped>
.idiom {
  position: relative;
}

/* ---------------------------------------------------------------- 头图 */
.hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--gap-sm);
  text-align: center;
  border: 2px solid var(--surface-border);
  background-image: linear-gradient(
    135deg,
    color-mix(in srgb, var(--art-a, var(--brand)) var(--art-tint), var(--surface-strong)) 0%,
    color-mix(in srgb, var(--art-b, var(--accent)) var(--art-tint), var(--surface-strong)) 100%
  );
  transition: background-image var(--dur-mid) ease, border-color var(--dur-mid) ease;
}

.hero__emoji {
  font-size: 3.4rem;
  line-height: 1;
  filter: drop-shadow(0 3px 6px rgba(0, 0, 0, 0.15));
  animation: float-y 5s ease-in-out infinite;
}

.hero__word {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 6px 18px;
  border-radius: var(--radius-md);
  transition: transform var(--dur-fast) var(--ease-pop);
}

.hero__word:active {
  transform: scale(0.97);
}

.hero__pinyin {
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text);
  letter-spacing: 0.12em;
}

.hero__text {
  font-size: clamp(2.2rem, 11vw, 3.2rem);
  font-weight: 800;
  line-height: 1.2;
  letter-spacing: 0.14em;
  color: var(--text-strong);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

.hero__hint {
  font-size: 0.75rem;
  color: var(--text-soft);
}

.hero__meaning {
  max-width: 34ch;
  font-size: 1rem;
  line-height: 1.75;
  color: var(--text-strong);
}

.hero__pills {
  display: flex;
  gap: 8px;
}

.hero .pill {
  background: color-mix(in srgb, var(--surface-strong) 76%, transparent);
  color: var(--text-strong);
}

/* ------------------------------------------------------------ 逐字拆解 */
.section-title__count {
  margin-left: auto;
  font-size: 0.85rem;
  font-weight: 700;
}

.chars {
  display: grid;
  gap: var(--gap-sm);
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
}

.charbox {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 12px 8px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  border: 2px solid transparent;
  transition: transform var(--dur-fast) var(--ease-pop), border-color var(--dur-fast) ease;
}

.charbox:hover {
  border-color: color-mix(in srgb, var(--brand) 45%, transparent);
}

.charbox:active {
  transform: scale(0.96);
}

.charbox__pinyin {
  font-size: 0.78rem;
  color: var(--text-soft);
}

.charbox__glyph {
  display: grid;
  place-items: center;
  width: 66px;
  height: 66px;
  font-size: 2.2rem;
  line-height: 1;
  color: var(--text-strong);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', serif;
}

.charbox__meaning {
  font-size: 0.78rem;
  color: var(--text-soft);
  text-align: center;
}

/* -------------------------------------------------------------- 小剧场 */
.story {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
  counter-reset: beat;
}

.beat {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: var(--gap-sm);
  padding: var(--gap-md) 46px var(--gap-md) var(--gap-md);
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
}

.beat__no {
  flex: none;
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: var(--brand);
  color: var(--text-invert);
  font-size: 0.8rem;
  font-weight: 800;
}

.beat__emoji {
  flex: none;
  font-size: 1.7rem;
  line-height: 1.2;
}

.beat__text {
  flex: 1;
  font-size: 1rem;
  line-height: 1.8;
  color: var(--text);
}

.beat__speak {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  width: 34px;
  height: 34px;
  border-radius: 50%;
  font-size: 1rem;
  opacity: 0.7;
  transition: opacity var(--dur-fast) ease, transform var(--dur-fast) var(--ease-pop);
}

.beat__speak:hover {
  opacity: 1;
}

.beat__speak:active {
  transform: translateY(-50%) scale(0.9);
}

.lesson {
  padding: var(--gap-md);
  border-radius: var(--radius-md);
  background: var(--accent-soft);
  font-size: 0.98rem;
  line-height: 1.8;
  color: var(--text-strong);
}

/* ---------------------------------------------------------------- 小测 */
.quiz__q {
  font-size: 1.05rem;
  line-height: 1.75;
  color: var(--text-strong);
  font-weight: 700;
}

.quiz__options {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
}

.choice {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  min-height: var(--tap-min);
  padding: 12px 18px;
  border-radius: var(--radius-md);
  background: var(--surface-strong);
  border: 2px solid var(--surface-border);
  text-align: left;
  font-size: 1rem;
  transition: transform var(--dur-fast) var(--ease-pop), border-color var(--dur-fast) ease,
    background var(--dur-fast) ease;
}

.choice:not(:disabled):hover {
  border-color: color-mix(in srgb, var(--brand) 50%, transparent);
}

.choice:not(:disabled):active {
  transform: scale(0.98);
}

.choice__index {
  flex: none;
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--brand-soft);
  font-weight: 800;
  font-size: 0.85rem;
  color: var(--text-strong);
}

.choice.is-right {
  background: color-mix(in srgb, var(--success) 18%, var(--surface-strong));
  border-color: var(--success);
}

.choice.is-right .choice__index {
  background: var(--success);
  color: var(--text-invert);
}

.choice.is-wrong {
  background: color-mix(in srgb, var(--danger) 14%, var(--surface-strong));
  border-color: var(--danger);
  animation: wiggle 0.28s ease-in-out 2;
}

.quiz__tip {
  padding: 10px 16px;
  border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--success) 16%, transparent);
  font-weight: 700;
  color: var(--text-strong);
}

.quiz__tip--miss {
  background: color-mix(in srgb, var(--danger) 12%, transparent);
}

/* ---------------------------------------------------------------- 翻页 */
.pager {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: var(--gap-sm);
}

.pager .btn.is-disabled {
  opacity: 0.4;
  pointer-events: none;
}

@media (max-width: 480px) {
  .pager {
    grid-template-columns: 1fr;
  }
}
</style>
