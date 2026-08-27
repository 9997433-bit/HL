<script setup>
/**
 * 一首古诗的三件事：读一读、讲一讲、跟着读。
 *
 * 三件事拆成三个 Tab，而不是一路往下滚：孩子一次只做一件，
 * 家长也能直接把他带到「跟读」那一格。跟读面板自己会按设备能力降级。
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import FollowReadPanel from '@/components/FollowReadPanel.vue'
import MascotCompanion from '@/components/MascotCompanion.vue'
import { useMascotCoach } from '@/composables/useMascotCoach.js'
import { POEMS, getPoem, poemNewChars, syllablesOfLine } from '@/data/poems.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { speak } from '@/utils/audio.js'
import { sfx } from '@/utils/sfx.js'

const props = defineProps({
  id: { type: String, required: true },
  /** 直接从「跟读」入口进来时，一进页面就停在跟读那一格。 */
  startTab: { type: String, default: 'read' }
})

const router = useRouter()
const progress = useProgressStore()
const settings = useSettingsStore()

const { line: coachLine, mood: coachMood, next: coachNext } = useMascotCoach('poems')

const poem = computed(() => getPoem(props.id))
const tab = ref(props.startTab)
const readingIndex = ref(-1)
const peek = ref(null)
const say = ref('')

const TABS = [
  { id: 'read', name: '读一读', emoji: '📖' },
  { id: 'learn', name: '讲一讲', emoji: '💡' },
  { id: 'follow', name: '跟着读', emoji: '🎤' }
]

const newChars = computed(() => (poem.value ? poemNewChars(poem.value) : []))
const glossMap = computed(() => new Map(newChars.value.map((n) => [n.c, n])))

const rows = computed(() =>
  (poem.value?.lines ?? []).map((line, i) => ({
    index: i,
    sense: line.sense,
    text: line.text,
    pinyin: line.pinyin,
    cells: syllablesOfLine(line)
  }))
)

const record = computed(() => progress.state.poems?.[props.id] ?? null)

/** 找不到这首诗（改了 id、手打错了）就回长廊，别把孩子丢在空白页。 */
watch(
  poem,
  (value) => {
    if (!value) router.replace('/poems')
  },
  { immediate: true }
)

watch(
  () => props.startTab,
  (value) => {
    if (value) tab.value = value
  }
)

onMounted(() => {
  if (poem.value) progress.markPoemRead(poem.value.id)
})

function pickTab(id) {
  sfx.tap()
  tab.value = id
}

/** 逐句朗读：读到哪一句就高亮哪一句。 */
async function readAloud() {
  sfx.tap()
  const lines = poem.value?.lines ?? []
  for (let i = 0; i < lines.length; i += 1) {
    readingIndex.value = i
    say.value = `读第 ${i + 1} 句`
    // eslint-disable-next-line no-await-in-loop
    const ok = await speak(lines[i].text, { rate: Math.min(0.78, settings.speechRate) })
    if (!ok) break
  }
  readingIndex.value = -1
  say.value = '整首读完啦'
}

function tapGlyph(cell) {
  if (cell.punct) return
  sfx.tap()
  const gloss = glossMap.value.get(cell.char)
  peek.value = { char: cell.char, pinyin: cell.pinyin, meaning: gloss?.m ?? '' }
  speak(cell.char, { rate: 0.7 })
  say.value = `${cell.char}，读作 ${cell.pinyin}`
}

function onScored(payload) {
  if (!poem.value) return
  progress.recordFollowRead(poem.value.id, payload)
}
</script>

<template>
  <div v-if="poem" class="page poem-detail" :data-tab="tab">
    <section
      class="hero card"
      :style="{ '--c1': poem.palette[0], '--c2': poem.palette[1] }"
    >
      <span class="hero__emoji" aria-hidden="true">{{ poem.emoji }}</span>
      <div class="hero__text">
        <p class="hero__pinyin">{{ poem.titlePinyin }}</p>
        <h2 class="hero__title">{{ poem.title }}</h2>
        <p class="hero__by">{{ poem.dynasty }} · {{ poem.author }}</p>
        <p class="hero__summary">{{ poem.summary }}</p>
      </div>
      <span v-if="record?.bestScore != null" class="pill hero__best">
        🎤 最好 {{ record.bestScore }} 分
      </span>
    </section>

    <div class="tabs" role="tablist" aria-label="这首诗怎么学">
      <button
        v-for="t in TABS"
        :key="t.id"
        type="button"
        role="tab"
        class="tabs__btn"
        :class="{ 'is-on': tab === t.id }"
        :aria-selected="tab === t.id"
        @click="pickTab(t.id)"
      >
        <span aria-hidden="true">{{ t.emoji }}</span>
        {{ t.name }}
      </button>
    </div>

    <!-- 读一读 -->
    <section v-if="tab === 'read'" class="card stack">
      <div class="acts">
        <button type="button" class="btn btn--primary" @click="readAloud">🔊 读给我听</button>
        <RouterLink class="btn" :to="`/follow-read/${poem.id}`" @click="sfx.tap()">
          🎤 我要跟读
        </RouterLink>
      </div>

      <div class="verse">
        <p
          v-for="row in rows"
          :key="row.index"
          class="verse__line"
          :class="{ 'is-reading': readingIndex === row.index }"
        >
          <span
            v-for="(cell, i) in row.cells"
            :key="i"
            class="glyph"
            :class="{ 'glyph--punct': cell.punct, 'glyph--new': glossMap.has(cell.char) }"
            :role="cell.punct ? undefined : 'button'"
            :tabindex="cell.punct ? undefined : 0"
            @click="tapGlyph(cell)"
            @keydown.enter.prevent="tapGlyph(cell)"
            @keydown.space.prevent="tapGlyph(cell)"
          >
            <small v-if="settings.showPinyin" class="glyph__p">{{ cell.pinyin }}</small>
            <span class="glyph__c">{{ cell.char }}</span>
          </span>
        </p>
      </div>

      <div v-if="peek" class="peek">
        <strong class="peek__char">{{ peek.char }}</strong>
        <span class="peek__p">{{ peek.pinyin }}</span>
        <span v-if="peek.meaning" class="peek__m">{{ peek.meaning }}</span>
      </div>
    </section>

    <!-- 讲一讲 -->
    <section v-else-if="tab === 'learn'" class="card stack">
      <h3 class="section-title">
        <span class="section-title__emoji" aria-hidden="true">💡</span>
        一句一句讲
      </h3>
      <ol class="senses">
        <li v-for="row in rows" :key="row.index" class="sense">
          <p class="sense__text">{{ row.text }}</p>
          <p class="sense__say muted">{{ row.sense }}</p>
        </li>
      </ol>

      <h3 class="section-title">
        <span class="section-title__emoji" aria-hidden="true">🆕</span>
        这首诗里的生字（{{ newChars.length }} 个）
      </h3>
      <p v-if="!newChars.length" class="muted">这首诗里的字你都学过啦，直接读就行。</p>
      <ul v-else class="news">
        <li v-for="n in newChars" :key="n.c" class="news__item">
          <strong class="news__char">{{ n.c }}</strong>
          <span class="news__p">{{ n.p }}</span>
          <span class="news__m">{{ n.m }}</span>
        </li>
      </ul>

      <p class="tipbox">{{ poem.tip }}</p>
    </section>

    <!-- 跟着读 -->
    <FollowReadPanel
      v-else
      :lines="poem.lines"
      :title="poem.title"
      :speech-enabled="settings.speechOn"
      @scored="onScored"
    />

    <nav class="jump">
      <RouterLink class="btn" to="/poems" @click="sfx.tap()">← 回长廊</RouterLink>
      <RouterLink
        v-for="p in POEMS.filter((x) => x.id !== poem.id).slice(0, 2)"
        :key="p.id"
        class="btn"
        :to="`/poems/${p.id}`"
        @click="sfx.tap()"
      >
        《{{ p.title }}》
      </RouterLink>
    </nav>

    <p class="sr-only" aria-live="polite">{{ say }}</p>

    <MascotCompanion
      class="mascot-dock"
      :mood="coachMood"
      :say="coachLine"
      :size="70"
      :speak-on-tap="false"
      tap-hint="点我，换一句悄悄话"
      @tap="coachNext"
    />
  </div>
</template>

<style scoped>
.hero {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--gap-md);
  background: linear-gradient(135deg, var(--c1) 0%, var(--c2) 100%);
}

.hero__emoji {
  font-size: 2.8rem;
  line-height: 1;
}

.hero__text {
  flex: 1;
  min-width: 0;
}

.hero__pinyin {
  font-size: 0.78rem;
  letter-spacing: 0.06em;
  color: rgba(61, 47, 31, 0.7);
}

.hero__title {
  font-size: 1.6rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
  color: var(--text-strong);
}

.hero__by {
  font-size: 0.85rem;
  font-weight: 700;
  color: rgba(61, 47, 31, 0.82);
}

.hero__summary {
  margin-top: 4px;
  font-size: 0.85rem;
  line-height: 1.6;
  color: rgba(61, 47, 31, 0.85);
}

.hero__best {
  position: absolute;
  top: 10px;
  right: 12px;
}

.tabs {
  display: flex;
  gap: 6px;
}

.tabs__btn {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  min-height: 48px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--surface-border);
  background: var(--surface);
  font-weight: 800;
  color: var(--text-soft);
}

.tabs__btn.is-on {
  background: var(--brand-soft);
  color: var(--text-strong);
}

.acts,
.jump {
  display: flex;
  flex-wrap: wrap;
  gap: var(--gap-sm);
}

.verse {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: var(--gap-md) var(--gap-sm);
  border-radius: var(--radius-lg);
  background: var(--brand-soft);
}

.verse__line {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 2px;
  padding: 6px 4px;
  border-radius: var(--radius-md);
  transition: background var(--dur-fast) ease;
}

.verse__line.is-reading {
  background: rgba(255, 255, 255, 0.6);
}

.glyph {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  min-width: 34px;
  padding: 2px 1px;
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.glyph--punct {
  min-width: 16px;
  cursor: default;
}

.glyph__p {
  font-size: 0.62rem;
  line-height: 1.2;
  color: var(--text-soft);
}

.glyph__c {
  font-size: 1.5rem;
  line-height: 1.4;
  font-weight: 700;
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

.glyph--new .glyph__c {
  color: var(--coral-400);
}

.glyph:not(.glyph--punct):hover,
.glyph:focus-visible {
  background: rgba(255, 255, 255, 0.75);
}

.peek {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: var(--gap-sm) var(--gap-md);
  border-radius: var(--radius-lg);
  border: 1px solid var(--surface-border);
}

.peek__char {
  font-size: 1.6rem;
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

.peek__p {
  font-weight: 700;
  color: var(--text-soft);
}

.peek__m {
  font-size: 0.85rem;
  color: var(--text-soft);
}

.senses {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
  padding-left: 0;
  list-style: none;
}

.sense {
  padding: var(--gap-sm) var(--gap-md);
  border-radius: var(--radius-md);
  background: var(--brand-soft);
}

.sense__text {
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

.sense__say {
  margin-top: 2px;
  font-size: 0.85rem;
  line-height: 1.6;
}

.news {
  display: grid;
  gap: 6px;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  padding-left: 0;
  list-style: none;
}

.news__item {
  display: flex;
  align-items: baseline;
  gap: 7px;
  padding: 8px 10px;
  border-radius: var(--radius-md);
  border: 1px solid var(--surface-border);
}

.news__char {
  font-size: 1.3rem;
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

.news__p {
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--text-soft);
}

.news__m {
  font-size: 0.78rem;
  line-height: 1.5;
  color: var(--text-soft);
}

.tipbox {
  padding: var(--gap-sm) var(--gap-md);
  border-radius: var(--radius-md);
  background: var(--brand-soft);
  font-size: 0.88rem;
  line-height: 1.7;
}
</style>
