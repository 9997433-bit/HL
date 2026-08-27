<script setup>
import { computed, ref } from 'vue'
import VisualMathDemo from '@/components/VisualMathDemo.vue'
import { VISUAL_DEMOS } from '@/data/visualDemos.js'
import { sound } from '@/utils/sound.js'

const selectedId = ref(VISUAL_DEMOS[0].id)
const selected = computed(
  () => VISUAL_DEMOS.find((demo) => demo.id === selectedId.value) ?? VISUAL_DEMOS[0],
)

function choose(id) {
  sound.click()
  selectedId.value = id
}
</script>

<template>
  <main class="page stack">
    <section class="intro card">
      <div>
        <p class="kicker">看得见的数学</p>
        <h2 class="page-title">数形演示中心</h2>
        <p class="muted">
          从熟悉的实物出发，先画成图形模型，再写成算式。每个演示都能跳过、重播或手动逐步播放。
        </p>
      </div>
      <span class="count-badge" data-visual-demo-count>{{ VISUAL_DEMOS.length }} 类演示</span>
    </section>

    <nav class="demo-picker card" aria-label="选择数形演示">
      <button
        v-for="demo in VISUAL_DEMOS"
        :key="demo.id"
        class="demo-tab"
        :class="{ on: selectedId === demo.id }"
        :aria-pressed="selectedId === demo.id"
        :data-demo-select="demo.id"
        @click="choose(demo.id)"
      >
        <span>{{ demo.object.emoji }}</span>
        <strong>{{ demo.title }}</strong>
        <small>{{ demo.equation }}</small>
      </button>
    </nav>

    <VisualMathDemo :key="selected.id" :demo="selected" />
  </main>
</template>

<style scoped>
.intro {
  display: flex;
  align-items: center;
  gap: 18px;
}

.intro > div {
  flex: 1;
}

.page-title {
  margin: 3px 0 6px;
}

.kicker {
  color: var(--brand);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 1.6px;
}

.count-badge {
  flex: none;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  color: var(--star);
  background: rgba(255, 206, 77, 0.12);
  border: 1px solid rgba(255, 206, 77, 0.34);
  font-weight: 900;
}

.demo-picker {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
  gap: 8px;
  padding: 12px;
}

.demo-tab {
  min-height: 104px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  border-radius: var(--radius-sm);
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.05);
  transition: transform 0.16s ease, border-color 0.16s ease, background 0.16s ease;
}

.demo-tab:hover,
.demo-tab.on {
  transform: translateY(-2px);
  border-color: rgba(94, 231, 255, 0.55);
  background: linear-gradient(145deg, rgba(94, 231, 255, 0.16), rgba(155, 140, 255, 0.14));
}

.demo-tab span {
  font-size: 24px;
}

.demo-tab strong {
  font-size: 13px;
}

.demo-tab small {
  color: var(--star);
  font-weight: 800;
}

@media (max-width: 560px) {
  .intro {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
