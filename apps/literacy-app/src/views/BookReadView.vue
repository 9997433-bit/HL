<script setup>
/**
 * 绘本阅读页。
 *
 * 两条并行的朗读线：
 *  1. 「读给我听」逐句朗读，读到哪句哪句高亮——设计规范 §9.6 要求语音与字幕互补，
 *     不识字的孩子靠高亮就能跟上读到哪儿了。
 *  2. 点任意一个字单独发音，并弹出拼音释义。
 * 两条线互斥：开始逐句朗读会清掉选中的字，点字会先停下逐句朗读，
 * 否则两段语音会抢 SpeechSynthesis 队列，听起来像卡带。
 *
 * 逐句朗读用一个自增的 token 做取消：翻页、点字、离开页面都让 token 失效，
 * 上一轮的 await 醒来发现 token 变了就自己退出，不会把高亮画到新的一页上。
 *
 * 插图交给 BookPageScene：写了 scene 的页摆成多元素场景，没写的仍是单 emoji。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import gsap from 'gsap'
import BookPageScene from '@/components/BookPageScene.vue'
import StarBurst from '@/components/StarBurst.vue'
import VoiceNotice from '@/components/VoiceNotice.vue'
import { charsInBook, getBook } from '@/data/books.js'
import { CHARACTER_MAP, getLoadedCharacter, loadCharacter } from '@/data/characters.js'
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
/** 被点开那个字的释义，跟着单元详情包异步到位。 */
const meaning = ref('')
watch(selected, (g) => {
  if (!g) meaning.value = ''
})
const stageRef = ref(null)
const burstRef = ref(null)

const page = computed(() => book.value?.pages[pageIndex.value] || null)
const total = computed(() => book.value?.pages.length || 0)
const isLast = computed(() => pageIndex.value >= total.value - 1)

const PUNCT = /[，。！？：、；「」《》…—\s]/
/** 断句点。对幼儿来说逗号也是一口气的边界，所以按小句而不是整句切。 */
const BREAK = /[，。！？、；：…]/

/**
 * 把正文切成小句，并记下每句在原文里的下标区间，
 * 好让高亮能精确落到属于这句的那几个字上。
 */
const sentences = computed(() => {
  const text = page.value?.text ?? ''
  const out = []
  let start = 0
  let i = 0
  while (i < text.length) {
    if (BREAK.test(text[i])) {
      let end = i + 1
      while (end < text.length && BREAK.test(text[end])) end++
      out.push({ start, end, text: text.slice(start, end) })
      start = end
      i = end
    } else {
      i++
    }
  }
  if (start < text.length) out.push({ start, end: text.length, text: text.slice(start) })
  return out.filter((s) => s.text.replace(PUNCT, '').trim().length > 0)
})

const glyphs = computed(() => {
  const list = sentences.value
  return (page.value?.text || '').split('').map((ch, i) => ({
    ch,
    i,
    isPunct: PUNCT.test(ch),
    known: CHARACTER_MAP.has(ch),
    sentence: list.findIndex((s) => i >= s.start && i < s.end)
  }))
})

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
  stopRead()
  selected.value = null
  pageIndex.value = target
  sfx.page()
  markRead()
  animatePage(delta)
  if (settings.speechOn) readAloud(false)
}

function finish() {
  stopRead()
  const { firstFinish } = progress.readPage(book.value.id, pageIndex.value, total.value)
  finished.value = true
  sfx.levelUp()
  burstRef.value?.burst()
  if (firstFinish) {
    // 读完整本额外奖励已在 store 里加过星，这里只做庆祝
  }
}

/* ------------------------------------------------------------ 逐句朗读 */

/** 正在朗读的小句下标，-1 表示没在读。 */
const readingIndex = ref(-1)
const reading = computed(() => readingIndex.value >= 0)

/** 每开一轮朗读就自增；旧的一轮醒来发现对不上就自己退出。 */
let readToken = 0

const wait = (ms) => new Promise((r) => setTimeout(r, ms))

/** 没有声音时高亮自己走的节奏：按字数估一个「念完这句」的时间。 */
const silentPace = (text) => Math.max(900, 420 * text.length)

function stopRead() {
  readToken += 1
  readingIndex.value = -1
  stopSpeaking()
}

async function playSentences(from = 0) {
  const token = ++readToken
  const list = sentences.value
  for (let i = from; i < list.length; i++) {
    if (token !== readToken) return
    readingIndex.value = i
    // 没装中文嗓音时 speak 会失败，这时高亮改成按字数估时自己往下走，
    // 孩子还能跟着看是读到哪一句了，家长照着念就行（VoiceNotice 已经解释了原因）。
    const spoken = await speak(list[i].text, { rate: settings.speechRate - 0.05 })
    if (token !== readToken) return
    if (!spoken) await wait(silentPace(list[i].text))
    if (token !== readToken) return
    await wait(240)
  }
  if (token === readToken) readingIndex.value = -1
}

/** 「读给我听」是一个开关：正在读就停下，没在读就从头读。 */
function readAloud(withTap = true) {
  if (withTap) sfx.tap()
  if (reading.value) {
    stopRead()
    return
  }
  selected.value = null
  if (sentences.value.length) playSentences(0)
}

/** 点某一句：从这句开始往下读，方便孩子回头听没听清的那句。 */
function readFrom(index) {
  sfx.tap()
  selected.value = null
  stopRead()
  playSentences(index)
}

function tapChar(g) {
  if (g.isPunct) return
  sfx.tap()
  stopRead()
  selected.value = selected.value?.i === g.i ? null : g
  if (!selected.value) return
  speak(g.ch, { rate: settings.speechRate })
  // 释义在单元详情包里，点到哪个字才去取哪一包。
  if (g.known) {
    loadCharacter(g.ch).then((full) => {
      if (selected.value?.i === g.i) meaning.value = full?.meaning ?? ''
    })
    meaning.value = getLoadedCharacter(g.ch)?.meaning ?? ''
  }
}

function restart() {
  sfx.tap()
  stopRead()
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
  stopRead()
  pageIndex.value = 0
  finished.value = false
  selected.value = null
  if (book.value) markRead()
})

onBeforeUnmount(stopRead)
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

      <section ref="stageRef" class="spread card">
        <!-- 整幅换掉：翻页时重挂一次，元素才会重新一件件落进画面 -->
        <BookPageScene
          :key="`${book.id}-${pageIndex}`"
          :scene="page.scene"
          :bg="page.sceneBg"
          :alt="page.sceneAlt"
          :palette="book.palette"
          :emoji="page.emoji"
          :reduced="settings.reduceMotion"
        />

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
                'is-picked': selected?.i === g.i,
                'is-reading': g.sentence === readingIndex
              }"
              type="button"
              :tabindex="g.isPunct ? -1 : 0"
              :aria-label="g.isPunct ? undefined : `读一读「${g.ch}」`"
              @click="tapChar(g)"
            >{{ g.ch }}</button>
          </p>

          <p class="readbar" role="status" aria-live="polite">
            <span v-if="reading" class="readbar__now">
              🎧 正在读第 {{ readingIndex + 1 }} / {{ sentences.length }} 句
            </span>
            <span v-else class="readbar__idle muted">
              点一个字听发音，点「读给我听」整页读一遍
            </span>
          </p>

          <ul v-if="sentences.length > 1" class="lines">
            <li v-for="(s, i) in sentences" :key="i">
              <button
                class="lines__btn"
                :class="{ 'is-reading': i === readingIndex }"
                type="button"
                :aria-label="`从第 ${i + 1} 句读起`"
                @click="readFrom(i)"
              >
                <span class="lines__no" aria-hidden="true">{{ i + 1 }}</span>
                <span class="lines__text">{{ s.text }}</span>
                <span class="lines__icon" aria-hidden="true">🔊</span>
              </button>
            </li>
          </ul>

          <VoiceNotice fallback="没有声音也能读：点字会高亮，家长可以照着读给孩子听。" />

          <Transition name="fade-slide">
            <div v-if="selected" class="peek">
              <span class="peek__char">{{ selected.ch }}</span>
              <span class="peek__info">
                <strong v-if="selected.known">{{ CHARACTER_MAP.get(selected.ch).pinyin }}</strong>
                <small v-if="selected.known">{{ meaning }}</small>
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
        <button
          class="btn btn--accent btn--lg"
          type="button"
          :aria-pressed="reading"
          @click="readAloud()"
        >
          {{ reading ? '⏸ 停一下' : '🔊 读给我听' }}
        </button>
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

/* 朗读高亮：底色 + 下划线双通道，色彩不做唯一信息通道（规范 §3.4） */
.glyph.is-reading {
  background: var(--accent-soft);
  box-shadow: inset 0 -4px 0 var(--accent);
}

.glyph.is-reading.is-picked {
  background: var(--brand);
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

.readbar {
  min-height: 1.5em;
  font-size: 0.82rem;
  line-height: 1.6;
}

.readbar__now {
  color: var(--accent);
  font-weight: 700;
}

.lines {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.lines__btn {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  min-height: 44px;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  background: var(--surface-sunken);
  border: 2px solid transparent;
  text-align: left;
  transition: border-color var(--dur-fast) ease, background var(--dur-fast) ease;
}

.lines__btn:hover {
  border-color: color-mix(in srgb, var(--accent) 45%, transparent);
}

.lines__btn.is-reading {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.lines__no {
  flex: none;
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--surface-strong);
  color: var(--text-soft);
  font-size: 0.72rem;
  font-weight: 800;
}

.lines__btn.is-reading .lines__no {
  background: var(--accent);
  color: var(--text-invert);
}

.lines__text {
  flex: 1;
  min-width: 0;
  font-size: 0.92rem;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.lines__icon {
  flex: none;
  opacity: 0.6;
  font-size: 0.9rem;
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
