<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { IDIOMS } from '@/data/idioms.js'
import { useProgressStore } from '@/stores/progress.js'
import { sfx } from '@/utils/sfx.js'

const route = useRoute()
const router = useRouter()
const progress = useProgressStore()

const active = computed(() => IDIOMS.find((i) => i.id === route.params.id) ?? null)

const list = computed(() =>
  IDIOMS.map((i) => ({
    ...i,
    seen: Boolean(progress.idioms[i.id]?.read)
  }))
)

function open(id) {
  sfx.tap()
  progress.markIdiomRead(id)
  router.push(`/idioms/${id}`)
}

function back() {
  sfx.tap()
  router.push('/idioms')
}

function pickQuiz(idx, idiom) {
  if (idx === idiom.quiz.answer) {
    sfx.success()
    progress.recordIdiomQuiz(idiom.id, true)
  } else {
    sfx.wrong()
  }
}
</script>

<template>
  <div class="page">
    <template v-if="!active">
      <section class="card card--flat intro">
        <h2 class="section-title"><span aria-hidden="true">🏮</span> 成语启蒙</h2>
        <p class="muted">听三段小故事，看懂一个成语。</p>
        <span class="pill">已读 {{ progress.idiomsSeen }} / {{ IDIOMS.length }}</span>
      </section>
      <div class="grid">
        <button
          v-for="i in list"
          :key="i.id"
          class="card idiom-card"
          :style="{ background: `linear-gradient(135deg, ${i.palette[0]}, ${i.palette[1]})` }"
          @click="open(i.id)"
        >
          <span class="emoji">{{ i.emoji }}</span>
          <strong>{{ i.word }}</strong>
          <small>{{ i.pinyin }}</small>
          <span v-if="i.seen" class="badge">✓</span>
        </button>
      </div>
    </template>

    <template v-else>
      <button class="back" @click="back">← 返回列表</button>
      <article class="card detail">
        <header>
          <span class="big">{{ active.emoji }}</span>
          <h1>{{ active.word }}</h1>
          <p class="muted">{{ active.pinyin }}</p>
        </header>
        <p class="meaning">{{ active.meaning }}</p>
        <section class="story">
          <h3>小故事</h3>
          <div v-for="(s, n) in active.story" :key="n" class="beat">
            <span>{{ s.emoji }}</span>
            <p>{{ s.text }}</p>
          </div>
        </section>
        <section v-if="active.quiz" class="quiz">
          <h3>想一想</h3>
          <p>{{ active.quiz.q }}</p>
          <button
            v-for="(opt, idx) in active.quiz.options"
            :key="opt"
            class="choice"
            @click="pickQuiz(idx, active)"
          >
            {{ opt }}
          </button>
          <p class="tip muted">{{ active.quiz.tip }}</p>
        </section>
      </article>
    </template>
  </div>
</template>

<style scoped>
.intro { margin-bottom: 16px; }
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}
.idiom-card {
  position: relative;
  border: none;
  cursor: pointer;
  padding: 16px;
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: #333;
}
.emoji { font-size: 32px; }
.badge {
  position: absolute;
  top: 8px;
  right: 8px;
  background: #fff8;
  border-radius: 999px;
  padding: 2px 8px;
}
.back {
  margin-bottom: 12px;
  background: none;
  border: none;
  color: var(--ink-muted);
  cursor: pointer;
}
.detail { padding: 20px; }
.big { font-size: 48px; }
.story .beat {
  display: flex;
  gap: 10px;
  margin: 10px 0;
  align-items: flex-start;
}
.quiz .choice {
  display: block;
  width: 100%;
  margin: 8px 0;
  padding: 12px;
  border-radius: 12px;
  border: 2px solid var(--stroke-soft);
  background: #fff;
  cursor: pointer;
}
</style>
