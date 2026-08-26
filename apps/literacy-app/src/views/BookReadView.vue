<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import gsap from 'gsap'
import StarBurst from '@/components/StarBurst.vue'
import { charsInBook, getBook } from '@/data/books.js'
import { CHARACTER_MAP } from '@/data/characters.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { speak, stopSpeaking } from '@/utils/speech.js'
import { sfx } from '@/utils/sfx.js'

const props = defineProps({ id: { type: String, required: true } })

const router = useRouter()
const progress = useProgressStore()
const settings = useSettingsStore()

const book = computed(() => getBook(props.id))
const pageIndex = ref(0)
const finished = ref(false)
const selected = ref(null)
const stageRef = ref(null)
const burstRef = ref(null)

const page = computed(() => book.value?.pages[pageIndex.value] || null)
const total = computed(() => book.value?.pages.length || 0)
const isLast = computed(() => pageIndex.value >= total.value - 1)

const PUNCT = /[，。！？：、；「」《》…—\s]/

const glyphs = computed(() =>
  (page.value?.text || '').split('').map((ch, i) => ({
    ch,
    i,
    isPunct: PUNCT.test(ch),
    known: CHARACTER_MAP.has(ch)
  }))
)

function markRead() {
  if (!book.value) return
  progress.readPage(book.value.id, pageIndex.value, total.value)
}

function animatePage(dir = 1) {
  if (settings.reduceMotion || !stageRef.value) return
  gsap.fromTo(
    stageRef.value,
    { opacity: 0, x: 34 * dir, rotateY: -4 * dir },
    { opacity: 1, x: 0, rotateY: 0, duration: 0.42, ease: 'power3.out' }
  )
}

function go(delta) {
  const target = pageIndex.value + delta
  if (target < 0) return
  if (target >= total.value) return finish()
  selected.value = null
  pageIndex.value = target
  sfx.page()
  markRead()
  animatePage(delta)
  if (settings.speechOn) readAloud(false)
}

function finish() {
  const { firstFinish } = progress.readPage(book.value.id, pageIndex.value, total.value)
  finished.value = true
  sfx.levelUp()
  burstRef.value?.burst()
  if (firstFinish) {
    // 读完整本额外奖励已在 store 里加过星，这里只做庆祝
  }
}

function readAloud(withTap = true) {
  if (withTap) sfx.tap()
  if (page.value) speak(page.value.text, { rate: settings.speechRate - 0.05 })
}

function tapChar(g) {
  if (g.isPunct) return
  sfx.tap()
  selected.value = selected.value?.i === g.i ? null : g
  speak(g.ch, { rate: settings.speechRate })
}

function restart() {
  sfx.tap()
  finished.value = false
  pageIndex.value = 0
  selected.value = null
  markRead()
}

const newCharsHere = computed(() => {
  if (!book.value) return []
  return charsInBook(book.value).filter((c) => !progress.isLearned(c))
})

onMounted(() => {
  if (!book.value) {
    router.replace('/books')
    return
  }
  markRead()
  animatePage(1)
})

watch(() => props.id, () => {
  pageIndex.value = 0
  finished.value = false
  selected.value = null
  if (book.value) markRead()
})

onBeforeUnmount(stopSpeaking)
</script>

<template>
  <div v-if="book" class="page reader">
    <StarBurst ref="burstRef" />

    <!-- 阅读中 -->
    <template v-if="!finished">
      <header class="rhead">
        <div class="rhead__meta">
          <h2 class="rhead__title">{{ book.title }}</h2>
          <p class="rhead__sub muted">{{ book.levelName }}</p>
        </div>
        <span class="pill">{{ pageIndex + 1 }} / {{ total }}</span>
      </header>

      <div class="dots" aria-hidden="true">
        <span
          v-for="n in total"
          :key="n"
          class="dots__dot"
          :class="{ 'is-on': n - 1 <= pageIndex }"
        />
      </div>

      <section ref="stageRef" class="spread card" :style="{ '--c1': book.palette[0], '--c2': book.palette[1] }">
        <div class="spread__art">
          <span class="spread__emoji" aria-hidden="true">{{ page.emoji }}</span>
        </div>

        <div class="spread__text">
          <p v-if="settings.showPinyin" class="spread__pinyin">{{ page.p }}</p>
          <p class="spread__line">
            <button
              v-for="g in glyphs"
              :key="g.i"
              class="glyph"
              :class="{
                'glyph--punct': g.isPunct,
                'glyph--unknown': !g.known && !g.isPunct,
                'is-picked': selected?.i === g.i
              }"
              type="button"
              :tabindex="g.isPunct ? -1 : 0"
              @click="tapChar(g)"
            >{{ g.ch }}</button>
          </p>

          <Transition name="fade-slide">
            <div v-if="selected" class="peek">
              <span class="peek__char">{{ selected.ch }}</span>
              <span class="peek__info">
                <strong v-if="selected.known">{{ CHARACTER_MAP.get(selected.ch).pinyin }}</strong>
                <small v-if="selected.known">{{ CHARACTER_MAP.get(selected.ch).meaning }}</small>
                <small v-else>这个字还没在课程里，先听听读音吧</small>
              </span>
              <RouterLink
                v-if="selected.known"
                class="btn btn--ghost peek__go"
                :to="`/learn/${encodeURIComponent(selected.ch)}`"
                @click="sfx.tap()"
              >
                去学 →
              </RouterLink>
            </div>
          </Transition>
        </div>
      </section>

      <div class="controls">
        <button class="btn btn--ghost btn--lg" type="button" :disabled="pageIndex === 0" @click="go(-1)">
          ← 上一页
        </button>
        <button class="btn btn--accent btn--lg" type="button" @click="readAloud()">🔊 读给我听</button>
        <button class="btn btn--primary btn--lg" type="button" @click="go(1)">
          {{ isLast ? '读完啦 🎉' : '下一页 →' }}
        </button>
      </div>
    </template>

    <!-- 读完 -->
    <section v-else class="done card">
      <div class="done__emoji" aria-hidden="true">🏅</div>
      <h2 class="done__title">《{{ book.title }}》读完啦！</h2>
      <p class="done__desc">
        一共 {{ total }} 页，全都是你学过的字。<br />
        真了不起，奖励 5 颗星 ⭐
      </p>

      <div v-if="newCharsHere.length" class="done__todo">
        <p class="muted">这本书里还有几个字没在字表里点开过：</p>
        <div class="done__chars">
          <RouterLink
            v-for="c in newCharsHere"
            :key="c"
            class="done__char"
            :to="`/learn/${encodeURIComponent(c)}`"
            @click="sfx.tap()"
          >{{ c }}</RouterLink>
        </div>
      </div>

      <div class="done__actions">
        <button class="btn btn--primary btn--lg" type="button" @click="restart">再读一遍 🔁</button>
        <RouterLink class="btn btn--ghost btn--lg" to="/books" @click="sfx.tap()">换一本 📚</RouterLink>
      </div>
    </section>
  </div>
</template>

<style scoped>
.reader {
  position: relative;
}

.rhead {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
}

.rhead__meta {
  flex: 1;
  min-width: 0;
}

.rhead__title {
  font-size: 1.25rem;
  font-weight: 800;
  color: var(--text-strong);
}

.rhead__sub {
  font-size: 0.78rem;
}

.dots {
  display: flex;
  gap: 6px;
  justify-content: center;
}

.dots__dot {
  width: 26px;
  height: 6px;
  border-radius: 3px;
  background: var(--stroke-hint);
  transition: background var(--dur-mid) ease;
}

.dots__dot.is-on {
  background: var(--brand);
}

.spread {
  display: flex;
  flex-direction: column;
  gap: var(--gap-lg);
  padding: 0;
  overflow: hidden;
}

.spread__art {
  display: grid;
  place-items: center;
  min-height: 210px;
  background: linear-gradient(150deg, var(--c1) 0%, var(--c2) 100%);
}

.spread__emoji {
  font-size: clamp(4.5rem, 22vw, 7rem);
  line-height: 1;
  animation: float-y 4s ease-in-out infinite;
  filter: drop-shadow(0 8px 14px rgba(0, 0, 0, 0.12));
}

.spread__text {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 0 var(--gap-lg) var(--gap-lg);
}

.spread__pinyin {
  font-size: 0.88rem;
  color: var(--text-soft);
  letter-spacing: 0.04em;
  line-height: 1.7;
}

.spread__line {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
}

.glyph {
  font-size: clamp(1.7rem, 7vw, 2.4rem);
  line-height: 1.7;
  font-weight: 700;
  color: var(--text-strong);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
  padding: 0 1px;
  border-radius: 8px;
  transition: background var(--dur-fast) ease, color var(--dur-fast) ease,
    transform var(--dur-fast) var(--ease-pop);
}

.glyph:hover:not(.glyph--punct) {
  background: var(--brand-soft);
}

.glyph.is-picked {
  background: var(--brand);
  color: var(--text-invert);
  transform: translateY(-2px);
}

.glyph--punct {
  cursor: default;
  color: var(--text-soft);
}

.glyph--unknown {
  color: var(--text-soft);
  text-decoration: underline dotted;
  text-underline-offset: 6px;
}

.peek {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
}

.peek__char {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  flex: none;
  border-radius: var(--radius-sm);
  background: var(--surface-strong);
  font-size: 1.9rem;
  font-weight: 700;
  color: var(--text-strong);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', serif;
}

.peek__info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.peek__info strong {
  color: var(--brand-strong);
  font-size: 1rem;
}

.peek__info small {
  font-size: 0.78rem;
  color: var(--text-soft);
}

.peek__go {
  flex: none;
  min-height: 44px;
  padding: 0 16px;
  font-size: 0.9rem;
}

.controls {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: var(--gap-sm);
}

.done {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--gap-md);
  text-align: center;
}

.done__emoji {
  font-size: 4rem;
  line-height: 1;
  animation: float-y 3s ease-in-out infinite;
}

.done__title {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--text-strong);
}

.done__desc {
  line-height: 1.9;
}

.done__todo {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.done__chars {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.done__char {
  display: grid;
  place-items: center;
  width: 52px;
  height: 52px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--text-strong);
  box-shadow: var(--shadow-sm);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', serif;
}

.done__actions {
  display: flex;
  gap: var(--gap-sm);
  flex-wrap: wrap;
  justify-content: center;
}

@media (max-width: 560px) {
  .controls {
    grid-template-columns: 1fr 1fr;
  }
  .controls .btn:nth-child(2) {
    grid-column: 1 / -1;
    order: 3;
  }
}
</style>
