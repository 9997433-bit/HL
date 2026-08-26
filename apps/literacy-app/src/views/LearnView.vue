<script setup>
import { computed, ref } from 'vue'
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

const reviewSet = computed(() => new Set(progress.reviewQueue))

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

function pickFilter(id) {
  sfx.tap()
  filter.value = id
}

const randomChar = computed(() => {
  const pool = CHARACTERS.filter((c) => progress.unlockedUnits[c.unit])
  return pool[Math.floor(Math.random() * pool.length)] || CHARACTERS[0]
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
      </div>
      <ProgressRing :percent="progress.overallPercent" :size="82" :stroke="9" label="已认识" />
    </section>

    <div class="toolbar" role="tablist" aria-label="筛选汉字">
      <button
        v-for="f in FILTERS"
        :key="f.id"
        class="chip"
        :class="{ 'is-on': filter === f.id }"
        type="button"
        role="tab"
        :aria-selected="filter === f.id"
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

    <section v-for="g in groups" v-show="g.chars.length" :key="g.unit.id" class="unit stack">
      <header class="unit__head">
        <span class="unit__emoji" aria-hidden="true">{{ g.unlocked ? g.unit.emoji : '🔒' }}</span>
        <div class="unit__meta">
          <h3 class="unit__name">{{ g.unit.name }}</h3>
          <p class="unit__desc muted">
            {{ g.unlocked ? g.unit.desc : '学完上一个单元的 60% 后解锁' }}
          </p>
        </div>
        <span class="unit__count pill">{{ g.stat.done }} / {{ g.total }}</span>
      </header>
      <div class="grid-auto grid-chars">
        <CharCard v-for="c in g.chars" :key="c.char" :item="c" :locked="!g.unlocked" />
      </div>
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
