<script setup>
import { onMounted, ref } from 'vue'
import gsap from 'gsap'
import ModuleCard from '@/components/ModuleCard.vue'
import { MODULES } from '@/data/curriculum.js'
import { useProgressStore } from '@/stores/progress.js'
import { sound } from '@/core/audio/sound.js'

const progress = useProgressStore()
const grid = ref(null)

onMounted(() => {
  gsap.from(grid.value.children, {
    y: 30,
    opacity: 0,
    duration: 0.5,
    stagger: 0.08,
    ease: 'back.out(1.6)'
  })
})
</script>

<template>
  <div class="page home">
    <header class="hero">
      <h1 class="page-title">🦊 数学星球大冒险</h1>
      <p class="page-subtitle">和麦麦船长一起,探索 7 颗数学星球!</p>
      <div class="stats">
        <span class="stat">⭐ {{ progress.stars }}</span>
        <span class="stat">🔥 连续 {{ progress.streak }} 天</span>
        <span class="stat">🏆 {{ progress.masteredCount }}/{{ progress.totalSkills }} 技能</span>
      </div>
    </header>

    <div ref="grid" class="planet-grid">
      <ModuleCard
        v-for="m in MODULES"
        :key="m.id"
        :module="m"
        :progress="progress.moduleProgress(m.id)"
        @click="sound.click()"
      />
    </div>
  </div>
</template>

<style scoped>
.hero {
  text-align: center;
  padding: 24px 0 8px;
}
.stats {
  display: flex;
  justify-content: center;
  gap: 16px;
  margin: 12px 0 24px;
}
.stat {
  background: var(--bg-card);
  border-radius: 999px;
  padding: 6px 14px;
  font-size: 14px;
}
.planet-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}
</style>
