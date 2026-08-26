<script setup>
import { computed } from 'vue'
import { useProgressStore } from '@/stores/progress.js'
import { SKILLS } from '@/data/curriculum.js'
import { sound } from '@/core/audio/sound.js'

const progress = useProgressStore()

const rows = computed(() =>
  SKILLS.map((s) => ({
    ...s,
    mastery: Math.round((progress.mastery[s.id] ?? 0) * 100)
  }))
)

function exportReport() {
  sound.tap()
  const blob = new Blob([progress.exportReport()], { type: 'application/json' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `math-report-${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(a.href)
}
</script>

<template>
  <div class="page">
    <router-link to="/" class="back-btn">← 返回星图</router-link>
    <h1 class="page-title">🏆 成就与进度</h1>

    <section class="panel summary">
      <p>⭐ 星星 <strong>{{ progress.stars }}</strong></p>
      <p>🔥 连续打卡 <strong>{{ progress.streak }}</strong> 天</p>
      <p>✅ 已掌握技能 <strong>{{ progress.masteredCount }}</strong> / {{ progress.totalSkills }}</p>
      <button class="export" @click="exportReport">导出 JSON 报告</button>
    </section>

    <section class="panel">
      <h2>技能掌握度</h2>
      <div v-for="r in rows" :key="r.id" class="row">
        <span>{{ r.name }}</span>
        <span class="bar"><span :style="{ width: `${r.mastery}%` }" /></span>
        <span>{{ r.mastery }}%</span>
      </div>
    </section>
  </div>
</template>

<style scoped>
.panel {
  background: var(--bg-card);
  border-radius: var(--radius-card);
  padding: 18px 20px;
  margin-bottom: 16px;
}
.summary p { margin: 8px 0; font-size: 18px; }
.export {
  margin-top: 12px;
  padding: 10px 16px;
  border-radius: 999px;
  cursor: pointer;
}
.row {
  display: grid;
  grid-template-columns: 1fr 2fr 48px;
  gap: 8px;
  align-items: center;
  margin: 8px 0;
  font-size: 14px;
}
.bar {
  height: 8px;
  background: #1a2744;
  border-radius: 999px;
  overflow: hidden;
}
.bar span {
  display: block;
  height: 100%;
  background: var(--star-gold);
}
</style>
