<script setup>
/**
 * 诗词长廊。详情在 PoemDetailView，这里只负责按主题挑诗和显示进度。
 *
 * 卡片上写「生字 N」而不是「难度 N 星」：对孩子来说，一首诗难不难，
 * 就取决于里面有几个字还没在字表里学过——这个数字是算出来的，
 * 字表长大之后它会自己变小。
 */
import { computed, onMounted, ref } from 'vue'
import gsap from 'gsap'
import MascotCompanion from '@/components/MascotCompanion.vue'
import { useMascotCoach } from '@/composables/useMascotCoach.js'
import { POEMS, POEM_THEMES, poemKnownRatio, poemNewChars } from '@/data/poems.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { sfx } from '@/utils/sfx.js'

const progress = useProgressStore()
const settings = useSettingsStore()

const { line: coachLine, mood: coachMood, next: coachNext } = useMascotCoach('poems')

const galleryRef = ref(null)
const theme = ref('all')

const list = computed(() =>
  POEMS.map((p) => {
    const record = progress.state.poems?.[p.id]
    return {
      ...p,
      newCount: poemNewChars(p).length,
      knownPercent: Math.round(poemKnownRatio(p) * 100),
      read: Boolean(record?.read),
      bestScore: record?.bestScore ?? null,
      reads: record?.reads ?? 0
    }
  })
)

const shown = computed(() =>
  theme.value === 'all' ? list.value : list.value.filter((p) => p.theme === theme.value)
)

const tabs = computed(() => [
  { id: 'all', name: '全部', emoji: '📜', count: list.value.length },
  ...POEM_THEMES.map((t) => ({
    ...t,
    count: list.value.filter((p) => p.theme === t.id).length
  }))
])

/** 先推没读过的里面生字最少的那一首，别一上来就丢《江雪》给他。 */
const suggestion = computed(() => {
  const unread = list.value.filter((p) => !p.read)
  const pool = unread.length ? unread : list.value
  return [...pool].sort((a, b) => a.newCount - b.newCount)[0] ?? null
})

function pickTheme(id) {
  sfx.tap()
  theme.value = id
}

onMounted(() => {
  if (settings.reduceMotion) return
  const cards = galleryRef.value?.querySelectorAll('.poem')
  if (!cards?.length) return
  gsap.from(cards, {
    opacity: 0,
    y: 24,
    scale: 0.93,
    duration: 0.4,
    ease: 'back.out(1.6)',
    stagger: 0.04
  })
})
</script>

<template>
  <div class="page">
    <section class="card card--flat intro">
      <div class="intro__text">
        <h2 class="section-title">
          <span class="section-title__emoji" aria-hidden="true">📜</span>
          古诗长廊
        </h2>
        <p class="muted">
          {{ POEMS.length }} 首最常背的古诗，每首都有逐字拼音、白话意思和跟读评测。
          没学过的字会当场教。
        </p>
        <RouterLink
          v-if="suggestion"
          class="btn btn--primary intro__cta"
          :to="`/poems/${suggestion.id}`"
          @click="sfx.tap()"
        >
          {{ suggestion.read ? '再读一遍' : '开始读' }}《{{ suggestion.title }}》 →
        </RouterLink>
      </div>
      <span class="pill">读过 {{ progress.poemsRead }} / {{ POEMS.length }}</span>
    </section>

    <div class="tabs" role="group" aria-label="按主题挑诗">
      <button
        v-for="t in tabs"
        :key="t.id"
        type="button"
        class="tabs__btn"
        :class="{ 'is-on': theme === t.id }"
        :aria-pressed="theme === t.id"
        @click="pickTheme(t.id)"
      >
        <span aria-hidden="true">{{ t.emoji }}</span>
        {{ t.name }}
        <small>{{ t.count }}</small>
      </button>
    </div>

    <section ref="galleryRef" class="gallery">
      <RouterLink
        v-for="p in shown"
        :key="p.id"
        class="poem"
        :to="`/poems/${p.id}`"
        :style="{ '--c1': p.palette[0], '--c2': p.palette[1] }"
        @click="sfx.tap()"
      >
        <span class="poem__emoji" aria-hidden="true">{{ p.emoji }}</span>
        <strong class="poem__title">{{ p.title }}</strong>
        <span class="poem__pinyin">{{ p.titlePinyin }}</span>
        <span class="poem__by">{{ p.dynasty }} · {{ p.author }}</span>
        <span class="poem__summary">{{ p.summary }}</span>
        <span class="poem__meta">
          <small>已学 {{ p.knownPercent }}%</small>
          <small>生字 {{ p.newCount }}</small>
        </span>
        <span v-if="p.bestScore !== null" class="poem__badge" title="跟读最好成绩">
          🎤 {{ p.bestScore }}
        </span>
        <span v-else-if="p.read" class="poem__badge" title="读过了">✓</span>
      </RouterLink>
    </section>

    <MascotCompanion
      class="mascot-dock"
      :mood="coachMood"
      :say="coachLine"
      :size="72"
      :speak-on-tap="false"
      tap-hint="点我，换一句悄悄话"
      @tap="coachNext"
    />
  </div>
</template>

<style scoped>
.intro {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
}

.intro__text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.intro__text .muted {
  font-size: 0.88rem;
}

.intro__cta {
  align-self: flex-start;
  margin-top: 4px;
}

.tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tabs__btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 44px;
  padding: 0 14px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--surface-border);
  background: var(--surface);
  font-weight: 800;
  font-size: 0.85rem;
  color: var(--text-soft);
}

.tabs__btn.is-on {
  background: var(--brand-soft);
  color: var(--text-strong);
}

/**
 * 数量角标不调透明度：--text-soft 再压 0.7 之后，在选中态的浅色底上
 * 对比度只剩 4.05:1，过不了 WCAG AA。让它直接继承按钮的文字色。
 */
.tabs__btn small {
  color: inherit;
}

.gallery {
  display: grid;
  gap: var(--gap-md);
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
}

.poem {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: var(--gap-lg) var(--gap-md);
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, var(--c1) 0%, var(--c2) 100%);
  box-shadow: var(--shadow-md);
  text-align: center;
  color: var(--text-strong);
  transition: transform var(--dur-fast) var(--ease-pop), box-shadow var(--dur-fast) ease;
}

.poem:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-lg);
}

.poem:active {
  transform: translateY(0) scale(0.97);
}

.poem__emoji {
  font-size: 2.2rem;
  line-height: 1;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.12));
}

.poem__title {
  font-size: 1.3rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

.poem__pinyin {
  font-size: 0.72rem;
  letter-spacing: 0.05em;
  color: rgba(61, 47, 31, 0.7);
}

.poem__by {
  font-size: 0.75rem;
  font-weight: 700;
  color: rgba(61, 47, 31, 0.8);
}

.poem__summary {
  margin-top: 4px;
  font-size: 0.8rem;
  line-height: 1.6;
  color: rgba(61, 47, 31, 0.85);
}

.poem__meta {
  display: flex;
  gap: 8px;
  margin-top: 6px;
  font-size: 0.72rem;
  color: rgba(61, 47, 31, 0.72);
}

.poem__badge {
  position: absolute;
  top: 10px;
  right: 12px;
  display: grid;
  place-items: center;
  min-width: 26px;
  height: 26px;
  padding: 0 8px;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.8);
  font-size: 0.8rem;
  font-weight: 800;
}

@media (max-width: 560px) {
  .intro {
    flex-direction: column;
    align-items: stretch;
  }
  .intro .pill {
    align-self: flex-start;
  }
  .intro__cta {
    align-self: stretch;
  }
}
</style>
