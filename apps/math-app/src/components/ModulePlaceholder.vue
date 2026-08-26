<script setup>
/**
 * Round 1 模块占位壳:展示模块信息、已规划玩法与技能点。
 * Round 2 各模块用真实玩法视图替换本组件。
 */
import { skillsOfModule } from '@/data/curriculum.js'

const props = defineProps({
  moduleId: { type: String, required: true },
  icon: { type: String, required: true },
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  gameplays: { type: Array, default: () => [] }
})

const skills = skillsOfModule(props.moduleId)
</script>

<template>
  <div class="page">
    <router-link to="/" class="back-btn">← 返回星图</router-link>
    <h1 class="page-title">{{ icon }} {{ title }}</h1>
    <p class="page-subtitle">{{ subtitle }}</p>

    <section class="panel">
      <h2>已规划玩法(Round 2 实现)</h2>
      <ul>
        <li v-for="g in gameplays" :key="g">{{ g }}</li>
      </ul>
    </section>

    <section v-if="skills.length" class="panel">
      <h2>技能点({{ skills.length }})</h2>
      <div class="chips">
        <span v-for="s in skills" :key="s.id" class="chip">{{ s.level }} · {{ s.name }}</span>
      </div>
    </section>

    <slot />
  </div>
</template>

<style scoped>
.panel {
  background: var(--bg-card);
  border-radius: var(--radius-card);
  padding: 18px 20px;
  margin-bottom: 16px;
}
h2 {
  font-size: 16px;
  margin-bottom: 10px;
  color: var(--star-gold);
}
ul {
  padding-left: 20px;
  line-height: 1.9;
  font-size: 15px;
}
.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.chip {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 999px;
  padding: 5px 12px;
  font-size: 13px;
}
</style>
