<script setup>
import { computed, ref, watch } from 'vue'
import CharCard from '@/components/CharCard.vue'
import ProgressRing from '@/components/ProgressRing.vue'
import { CHARACTERS, UNITS, charsOfUnit } from '@/data/characters.js'
import { useProgressStore } from '@/stores/progress.js'
import { sfx } from '@/utils/sfx.js'

const progress = useProgressStore()

const FILTERS = [
  { id: 'all', label: '全部', emoji: '📚' },
  { id: 'new', label: '没学过', emoji: '✨' },
  { id: 'learning', label: '学过了', emoji: '🌱' },
  { id: 'mastered', label: '已掌握', emoji: '🏆' },
  { id: 'review', label: '要复习', emoji: '🔁' }
]

const filter = ref('all')

const reviewSet = computed(() => new Set(progress.reviewQueue.map((c) => c.char)))

function matches(char) {
  switch (filter.value) {
    case 'new':
      return !progress.isLearned(char)
    case 'learning':
      return progress.isLearned(char) && !progress.isMastered(char)
    case 'mastered':
      return progress.isMastered(char)
    case 'review':
      return reviewSet.value.has(char)
    default:
      return true
  }
}

const groups = computed(() =>
  UNITS.map((unit) => {
    const all = charsOfUnit(unit.id)
    return {
      unit,
      chars: all.filter((c) => matches(c.char)),
      total: all.length,
      stat: progress.unitProgress(unit.id),
      unlocked: progress.unlockedUnits[unit.id]
    }
  })
)

const visibleCount = computed(() => groups.value.reduce((n, g) => n + g.chars.length, 0))

/**
 * 一次只挂一个单元。
 * 字表已经过百，一屏铺开既滚不到底也拖慢低端平板；按单元翻页正好和课程节奏一致，
 * 同时把同时存在的卡片数压在十张左右。
 */
const pages = computed(() => groups.value.filter((g) => g.chars.length))

const pageIndex = ref(0)

const currentPage = computed(() => pages.value[Math.min(pageIndex.value, pages.value.length - 1)])

watch([filter, pages], () => {
  if (pageIndex.value > pages.value.length - 1) pageIndex.value = Math.max(0, pages.value.length - 1)
})

function turnPage(delta) {
  const next = pageIndex.value + delta
  if (next < 0 || next > pages.value.length - 1) return
  sfx.tap()
  pageIndex.value = next
}

function pickFilter(id) {
  sfx.tap()
  filter.value = id
  pageIndex.value = 0
}

const randomChar = computed(() => {
  const unlocked = (c) => progress.unlockedUnits[c.unit]
  // 家长设了计划就先在计划单元里抽，抽不到再退回整份字表。
  const pool = progress.planChars.filter(unlocked)
  const fallback = CHARACTERS.filter(unlocked)
  const list = pool.length ? pool : fallback
  return list[Math.floor(Math.random() * list.length)] || CHARACTERS[0]
})

/** 家长面板里的学习计划，在这里只是一句提示，不拦着孩子往下翻。 */
const planNote = computed(() => {
  const parts = []
  if (!progress.isWholeCourse) {
    parts.push(`家长设了学习计划：这一阶段先学 ${progress.planUnitIds.length} 个单元、${progress.planProgress.total} 个字。`)
  }
  if (progress.dailyLimitReached) {
    parts.push(`今天的 ${progress.dailyNewLimit} 个新字已经学完啦，接着复习或者去读绘本吧。`)
  } else if (progress.newCharsLeft !== null) {
    parts.push(`今天还可以学 ${progress.newCharsLeft} 个新字。`)
  }
  return parts.join('')
})
</script>

<template>
  <div class="page">
    <section class="intro card card--flat">
      <div class="intro__text">
        <h2 class="section-title">
          <span class="section-title__emoji" aria-hidden="true">🈶</span>
          单字学习
        </h2>
        <p class="muted">
          共 {{ progress.totalChars }} 个常用字，分成 {{ UNITS.length }} 个单元。
          学完一个单元的 60%，下一个单元就会解锁。
        </p>
        <p v-if="planNote" class="muted intro__plan">📅 {{ planNote }}</p>
      </div>
      <ProgressRing
        :value="progress.overallProgress"
        :size="82"
        :thickness="9"
        sublabel="已认识"
      />
    </section>

    <div class="toolbar" role="group" aria-label="筛选汉字">
      <button
        v-for="f in FILTERS"
        :key="f.id"
        class="chip"
        :class="{ 'is-on': filter === f.id }"
        type="button"
        :aria-pressed="filter === f.id"
        @click="pickFilter(f.id)"
      >
        <span aria-hidden="true">{{ f.emoji }}</span> {{ f.label }}
      </button>
      <RouterLink
        class="chip chip--action"
        :to="`/learn/${encodeURIComponent(randomChar.char)}`"
        @click="sfx.tap()"
      >
        🎲 随机一个字
      </RouterLink>
    </div>

    <p v-if="!visibleCount" class="empty card">
      <span class="empty__emoji" aria-hidden="true">🐣</span>
      这个分类下还没有字，换一个筛选看看吧！
    </p>

    <section v-if="currentPage" :key="currentPage.unit.id" class="unit stack">
      <header class="unit__head">
        <span class="unit__emoji" aria-hidden="true">
          {{ currentPage.unlocked ? currentPage.unit.emoji : '🔒' }}
        </span>
        <div class="unit__meta">
          <h3 class="unit__name">{{ currentPage.unit.name }}</h3>
          <p class="unit__desc muted">
            {{ currentPage.unlocked ? currentPage.unit.desc : '学完上一个单元的 60% 后解锁' }}
          </p>
        </div>
        <span class="unit__count pill">{{ currentPage.stat.done }} / {{ currentPage.total }}</span>
      </header>
      <div class="grid-auto grid-chars">
        <!--
          单元锁只拦「还没学过的字」。孩子从复习队列或搜索里学过的字如果
          因为所在单元没解锁而变成不可点，等于把到期要复习的字锁在门外。
        -->
        <CharCard
          v-for="c in currentPage.chars"
          :key="c.char"
          :item="c"
          :locked="!currentPage.unlocked && !progress.isLearned(c.char)"
        />
      </div>

      <nav class="pager" aria-label="按单元翻页">
        <button
          class="btn btn--ghost"
          type="button"
          :disabled="pageIndex === 0"
          @click="turnPage(-1)"
        >
          ← 上一页
        </button>
        <span class="pager__at">第 {{ pageIndex + 1 }} / {{ pages.length }} 单元</span>
        <button
          class="btn btn--ghost"
          type="button"
          :disabled="pageIndex >= pages.length - 1"
          @click="turnPage(1)"
        >
          下一页 →
        </button>
      </nav>
    </section>
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
  gap: 6px;
}

.intro__text .muted {
  font-size: 0.88rem;
}

.intro__plan {
  font-weight: 700;
  color: var(--text-strong);
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  min-height: 44px;
  padding: 0 16px;
  border-radius: var(--radius-pill);
  background: var(--surface);
  border: 2px solid var(--surface-border);
  color: var(--text);
  font-weight: 700;
  font-size: 0.9rem;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  box-shadow: var(--shadow-sm);
  transition: transform var(--dur-fast) var(--ease-pop), background var(--dur-fast) ease;
}

.chip:active {
  transform: scale(0.95);
}

.chip.is-on {
  background: linear-gradient(180deg, var(--brand) 0%, var(--brand-strong) 100%);
  color: var(--text-invert);
  border-color: transparent;
}

.chip--action {
  margin-left: auto;
  background: var(--accent-soft);
}

.grid-chars {
  grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
}

.unit__head {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
}

.unit__emoji {
  font-size: 1.7rem;
  line-height: 1;
}

.unit__meta {
  flex: 1;
  min-width: 0;
}

.unit__name {
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--text-strong);
}

.unit__desc {
  font-size: 0.8rem;
}

.unit__count {
  flex: none;
}

.pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--gap-sm);
}

.pager__at {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--text-soft);
}

.pager .btn[disabled] {
  opacity: 0.4;
}

.empty {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  justify-content: center;
  color: var(--text-soft);
}

.empty__emoji {
  font-size: 1.6rem;
}
</style>
