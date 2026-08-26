<script setup>
import { computed } from 'vue'
import { BOOKS, charsInBook } from '@/data/books.js'
import { useProgressStore } from '@/stores/progress.js'
import { sfx } from '@/utils/sfx.js'

const progress = useProgressStore()

const shelf = computed(() =>
  BOOKS.map((b) => {
    const chars = charsInBook(b)
    const known = chars.filter((c) => progress.isLearned(c)).length
    return {
      ...b,
      charCount: chars.length,
      knownCount: known,
      readiness: chars.length ? Math.round((known / chars.length) * 100) : 0,
      percent: progress.bookPercent(b.id, b.pages.length),
      finished: Boolean(progress.books[b.id]?.finished)
    }
  })
)
</script>

<template>
  <div class="page">
    <section class="card card--flat intro">
      <div class="intro__text">
        <h2 class="section-title">
          <span class="section-title__emoji" aria-hidden="true">📖</span>
          分级绘本
        </h2>
        <p class="muted">
          每一本绘本都只用课程里学过的字写成，孩子可以从头到尾自己读下来。
        </p>
      </div>
      <span class="pill">读完 {{ progress.booksFinished }} / {{ BOOKS.length }} 本</span>
    </section>

    <section class="shelf">
      <RouterLink
        v-for="b in shelf"
        :key="b.id"
        class="book"
        :to="`/books/${b.id}`"
        :style="{ '--c1': b.palette[0], '--c2': b.palette[1] }"
        @click="sfx.tap()"
      >
        <div class="book__cover">
          <span class="book__emoji" aria-hidden="true">{{ b.cover }}</span>
          <span class="book__level">L{{ b.level }}</span>
          <span v-if="b.finished" class="book__done" title="已读完">🏅</span>
        </div>
        <div class="book__body">
          <h3 class="book__title">{{ b.title }}</h3>
          <p class="book__pinyin muted">{{ b.pinyin }}</p>
          <p class="book__summary">{{ b.summary }}</p>
          <div class="book__tags">
            <span class="pill">{{ b.levelName }}</span>
            <span class="pill pill--accent">{{ b.pages.length }} 页 · {{ b.charCount }} 个字</span>
          </div>
          <div class="book__meter">
            <span class="book__bar">
              <span class="book__fill" :style="{ width: `${b.percent}%` }" />
            </span>
            <small>{{ b.percent ? `已读 ${b.percent}%` : '还没开始' }}</small>
          </div>
          <p class="book__ready muted">
            这本书用到的字，你已经学会
            <strong>{{ b.knownCount }} / {{ b.charCount }}</strong>
            个（{{ b.readiness }}%）
          </p>
        </div>
      </RouterLink>
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

.shelf {
  display: grid;
  gap: var(--gap-md);
}

.book {
  display: flex;
  gap: var(--gap-md);
  padding: var(--gap-md);
  border-radius: var(--radius-lg);
  background: var(--surface);
  border: 1px solid var(--surface-border);
  box-shadow: var(--shadow-md);
  transition: transform var(--dur-fast) var(--ease-pop), box-shadow var(--dur-fast) ease;
}

.book:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg);
}

.book:active {
  transform: scale(0.99);
}

.book__cover {
  position: relative;
  flex: none;
  display: grid;
  place-items: center;
  width: 110px;
  border-radius: var(--radius-md);
  background: linear-gradient(150deg, var(--c1) 0%, var(--c2) 100%);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

.book__cover::after {
  content: '';
  position: absolute;
  left: 9px;
  top: 0;
  bottom: 0;
  width: 3px;
  background: rgba(0, 0, 0, 0.08);
}

.book__emoji {
  font-size: 3rem;
  line-height: 1;
}

.book__level {
  position: absolute;
  top: 8px;
  right: 8px;
  padding: 2px 9px;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.85);
  color: var(--text-strong);
  font-size: 0.72rem;
  font-weight: 800;
}

.book__done {
  position: absolute;
  bottom: 8px;
  right: 8px;
  font-size: 1.3rem;
}

.book__body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.book__title {
  font-size: 1.2rem;
  font-weight: 800;
  color: var(--text-strong);
}

.book__pinyin {
  font-size: 0.76rem;
  letter-spacing: 0.04em;
}

.book__summary {
  font-size: 0.9rem;
  color: var(--text);
  line-height: 1.6;
}

.book__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 2px;
}

.book__meter {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.book__bar {
  flex: 1;
  height: 8px;
  border-radius: 4px;
  background: var(--stroke-hint);
  overflow: hidden;
}

.book__fill {
  display: block;
  height: 100%;
  border-radius: 4px;
  background: var(--accent);
  transition: width var(--dur-slow) var(--ease-pop);
}

.book__meter small {
  font-size: 0.74rem;
  color: var(--text-soft);
  white-space: nowrap;
}

.book__ready {
  font-size: 0.76rem;
}

@media (max-width: 520px) {
  .book {
    flex-direction: column;
  }
  .book__cover {
    width: 100%;
    height: 116px;
  }
}
</style>
