<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import HanziStrokeBox from '@/components/HanziStrokeBox.vue'
import StarBurst from '@/components/StarBurst.vue'
import VoiceNotice from '@/components/VoiceNotice.vue'
import { CHARACTERS, getCharacter } from '@/data/characters.js'
import { RADICAL_MAP, getRadical } from '@/data/radicals.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { speak } from '@/utils/speech.js'
import { sfx } from '@/utils/sfx.js'

const props = defineProps({ char: { type: String, required: true } })

const router = useRouter()
const progress = useProgressStore()
const settings = useSettingsStore()

const burstRef = ref(null)
const toast = ref('')

const decoded = computed(() => decodeURIComponent(props.char))
const item = computed(() => getCharacter(decoded.value))
const radical = computed(() => (item.value ? getRadical(item.value.radical) : null))

/**
 * 只有 RADICALS 里的重点部首有讲解页。
 * 其余是 radicals.js 的兜底条目（横、大字头…），链过去只会落到第一个部首上，
 * 所以这类部首只展示不跳转。
 */
const radicalLink = computed(() =>
  radical.value && RADICAL_MAP.has(radical.value.id) ? `/radicals/${radical.value.id}` : null
)

const index = computed(() => CHARACTERS.findIndex((c) => c.char === decoded.value))
const prev = computed(() => (index.value > 0 ? CHARACTERS[index.value - 1] : null))
const next = computed(() =>
  index.value >= 0 && index.value < CHARACTERS.length - 1 ? CHARACTERS[index.value + 1] : null
)

const record = computed(() => progress.chars[decoded.value] || null)
const mastered = computed(() => progress.isMastered(decoded.value))

function say(text, rate) {
  sfx.tap()
  // 听读音也是一种学习行为，记下来才能算「认识了」
  if (item.value && text === item.value.char) progress.markHeard(text)
  speak(text, { rate: rate ?? settings.speechRate })
}

function flash(msg) {
  toast.value = msg
  setTimeout(() => {
    if (toast.value === msg) toast.value = ''
  }, 2600)
}

function markKnown() {
  const { justMastered } = progress.recordAnswer(decoded.value, true)
  sfx.correct()
  burstRef.value?.burst()
  flash(justMastered ? '太厉害了，这个字已经掌握啦！🏆' : '记住啦！+1 ⭐')
  if (justMastered) sfx.levelUp()
}

function onQuizSkip() {
  flash('跳过描红也没关系，随时可以回来写 ✍️')
}

function onQuizComplete({ mistakes }) {
  // 写完一遍才算「会写」，掌握度要靠它才能从「认识了」升到「会写了」。
  progress.markTraced(decoded.value)
  const { justMastered } = progress.recordAnswer(decoded.value, mistakes === 0)
  if (mistakes === 0) burstRef.value?.burst()
  if (justMastered) {
    sfx.levelUp()
    flash('这个字已经掌握啦！🏆')
  }
}

function track() {
  if (item.value) progress.visitChar(item.value.char)
}

onMounted(() => {
  if (!item.value) router.replace('/learn')
  else track()
})

watch(decoded, () => {
  if (!item.value) router.replace('/learn')
  else {
    track()
    toast.value = ''
  }
})
</script>

<template>
  <div v-if="item" class="page detail">
    <StarBurst ref="burstRef" />

    <!-- 主卡片：字形 + 笔顺 -->
    <section class="hero card">
      <div class="hero__info">
        <div class="hero__pinyin-row">
          <button class="hero__pinyin" type="button" @click="say(item.char)">
            <span class="hero__pinyin-text">{{ item.pinyin }}</span>
            <span class="hero__speaker" aria-hidden="true">🔊</span>
            <span class="sr-only">朗读 {{ item.char }}</span>
          </button>
          <span class="pill">{{ item.strokes }} 画</span>
          <span v-if="mastered" class="pill pill--accent">🏆 已掌握</span>
          <span v-else-if="record" class="pill pill--accent">🌱 学过 {{ record.views }} 次</span>
        </div>
        <p class="hero__meaning">{{ item.meaning }}</p>
        <RouterLink
          v-if="radicalLink"
          class="hero__radical"
          :to="radicalLink"
          @click="sfx.tap()"
        >
          <span class="hero__radical-glyph">{{ radical.glyph }}</span>
          <span>
            部首「{{ radical.name }}」
            <small class="muted">去看看 →</small>
          </span>
        </RouterLink>
        <div v-else-if="radical" class="hero__radical hero__radical--plain">
          <span class="hero__radical-glyph">{{ radical.glyph }}</span>
          <span>部首「{{ radical.name }}」</span>
        </div>
      </div>

      <HanziStrokeBox
        class="hero__writer"
        :char="item.char"
        :size="252"
        @quiz-complete="onQuizComplete"
        @quiz-skip="onQuizSkip"
      />
    </section>

    <!-- 播报区常驻，读屏才认得出后来写进去的提示；视觉气泡另走一份 -->
    <p class="sr-only" role="status" aria-live="polite" aria-atomic="true">{{ toast }}</p>
    <p v-if="toast" class="toast" aria-hidden="true">{{ toast }}</p>

    <VoiceNotice fallback="拼音就在字的上面，家长可以照着拼音读给孩子听。" />

    <!-- 组词 -->
    <section class="card stack">
      <h3 class="section-title">
        <span class="section-title__emoji" aria-hidden="true">🧺</span>
        跟它组个词
      </h3>
      <ul class="words">
        <li v-for="w in item.words" :key="w.w">
          <button class="word" type="button" @click="say(w.w)">
            <span class="word__pinyin">{{ w.p }}</span>
            <span class="word__text">{{ w.w }}</span>
            <span class="word__speaker" aria-hidden="true">🔊</span>
          </button>
        </li>
      </ul>
    </section>

    <!-- 例句 -->
    <section class="card stack">
      <h3 class="section-title">
        <span class="section-title__emoji" aria-hidden="true">💬</span>
        读一句话
      </h3>
      <button class="sentence" type="button" @click="say(item.sentence.text, settings.speechRate - 0.05)">
        <span v-if="settings.showPinyin" class="sentence__pinyin">{{ item.sentence.p }}</span>
        <span class="sentence__text">
          <span
            v-for="(ch, i) in item.sentence.text"
            :key="`${ch}-${i}`"
            class="sentence__char"
            :class="{ 'is-target': ch === item.char }"
          >{{ ch }}</span>
        </span>
        <span class="sentence__hint muted">点一下，听老师读 🔊</span>
      </button>
    </section>

    <!-- 底部操作 -->
    <section class="actions">
      <button class="btn btn--primary btn--lg btn--block" type="button" @click="markKnown">
        👍 我认识这个字啦
      </button>
      <div class="actions__nav">
        <RouterLink
          class="btn btn--ghost"
          :class="{ 'is-disabled': !prev }"
          :to="prev ? `/learn/${encodeURIComponent(prev.char)}` : ''"
          @click="(e) => (!prev ? e.preventDefault() : sfx.tap())"
        >
          ← {{ prev ? prev.char : '没有了' }}
        </RouterLink>
        <RouterLink class="btn btn--ghost" to="/learn" @click="sfx.tap()">📋 字表</RouterLink>
        <RouterLink
          class="btn btn--ghost"
          :class="{ 'is-disabled': !next }"
          :to="next ? `/learn/${encodeURIComponent(next.char)}` : ''"
          @click="(e) => (!next ? e.preventDefault() : sfx.tap())"
        >
          {{ next ? next.char : '没有了' }} →
        </RouterLink>
      </div>
    </section>
  </div>
</template>

<style scoped>
.detail {
  position: relative;
}

.hero {
  display: flex;
  gap: var(--gap-lg);
  align-items: center;
}

.hero__info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
  min-width: 0;
}

.hero__pinyin-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.hero__pinyin {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 18px;
  border-radius: var(--radius-pill);
  background: linear-gradient(180deg, var(--brand) 0%, var(--brand-strong) 100%);
  color: var(--text-invert);
  box-shadow: var(--shadow-sm);
  transition: transform var(--dur-fast) var(--ease-pop);
}

.hero__pinyin:active {
  transform: scale(0.94);
}

.hero__pinyin-text {
  font-size: 1.35rem;
  font-weight: 800;
  letter-spacing: 0.05em;
}

.hero__speaker {
  font-size: 1.1rem;
}

.hero__meaning {
  font-size: 1.05rem;
  line-height: 1.8;
  color: var(--text);
}

.hero__radical {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  align-self: flex-start;
  padding: 8px 16px 8px 8px;
  border-radius: var(--radius-pill);
  background: var(--accent-soft);
  font-weight: 700;
  color: var(--text-strong);
}

/* 没有讲解页的兜底部首：同样的信息，但不做成可点的样子 */
.hero__radical--plain {
  background: var(--surface-sunken);
  color: var(--text);
}

.hero__radical-glyph {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--surface-strong);
  font-size: 1.3rem;
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', serif;
}

.hero__radical small {
  font-size: 0.75rem;
  margin-left: 4px;
}

.hero__writer {
  flex: none;
}

.toast {
  align-self: center;
  padding: 10px 22px;
  border-radius: var(--radius-pill);
  background: var(--success);
  color: #fff;
  font-weight: 800;
  box-shadow: var(--shadow-md);
  animation: pop-in var(--dur-mid) var(--ease-pop);
}

.words {
  display: grid;
  gap: var(--gap-sm);
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
}

.word {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1px;
  position: relative;
  padding: 12px 40px 12px 16px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  border: 2px solid transparent;
  text-align: left;
  transition: transform var(--dur-fast) var(--ease-pop), border-color var(--dur-fast) ease;
}

.word:hover {
  border-color: color-mix(in srgb, var(--brand) 45%, transparent);
}

.word:active {
  transform: scale(0.97);
}

.word__pinyin {
  font-size: 0.78rem;
  color: var(--text-soft);
}

.word__text {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--text-strong);
}

.word__speaker {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 1.1rem;
  opacity: 0.65;
}

.sentence {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
  padding: var(--gap-md);
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  text-align: left;
  transition: transform var(--dur-fast) var(--ease-pop);
}

.sentence:active {
  transform: scale(0.99);
}

.sentence__pinyin {
  font-size: 0.85rem;
  color: var(--text-soft);
  letter-spacing: 0.04em;
}

.sentence__text {
  font-size: clamp(1.4rem, 5.5vw, 1.9rem);
  font-weight: 700;
  color: var(--text-strong);
  line-height: 1.7;
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

.sentence__char.is-target {
  color: var(--brand-strong);
  border-bottom: 3px solid var(--brand);
  border-radius: 2px;
}

.sentence__hint {
  font-size: 0.78rem;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
}

.actions__nav {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: var(--gap-sm);
}

.actions__nav .btn.is-disabled {
  opacity: 0.4;
  pointer-events: none;
}

@media (max-width: 720px) {
  .hero {
    flex-direction: column-reverse;
    align-items: stretch;
  }
  .hero__writer {
    align-self: center;
  }
}
</style>
