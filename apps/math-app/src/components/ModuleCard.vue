<script setup>
import { computed } from 'vue'

const props = defineProps({
  module: { type: Object, required: true },
  progress: { type: Number, default: 0 }
})

const pct = computed(() => Math.round(props.progress * 100))
</script>

<template>
  <router-link :to="`/${module.id}`" class="module-card" :style="{ '--accent': module.color }">
    <span class="icon">{{ module.icon }}</span>
    <div class="info">
      <h3>{{ module.name }}</h3>
      <p>{{ module.subtitle }}</p>
      <div class="bar"><div class="fill" :style="{ width: pct + '%' }" /></div>
    </div>
  </router-link>
</template>

<style scoped>
.module-card {
  display: flex;
  align-items: center;
  gap: 14px;
  background: var(--bg-card);
  border: 2px solid transparent;
  border-radius: var(--radius-card);
  padding: 18px;
  text-decoration: none;
  color: inherit;
  transition: transform 0.15s ease, border-color 0.15s ease;
}
.module-card:hover {
  transform: translateY(-3px) scale(1.02);
  border-color: var(--accent);
}
.icon {
  font-size: 40px;
  filter: drop-shadow(0 2px 6px rgba(0, 0, 0, 0.35));
}
.info {
  flex: 1;
}
h3 {
  font-size: 18px;
}
p {
  font-size: 13px;
  color: var(--text-dim);
  margin: 2px 0 8px;
}
.bar {
  height: 6px;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.12);
  overflow: hidden;
}
.fill {
  height: 100%;
  border-radius: 3px;
  background: var(--accent);
  transition: width 0.4s ease;
}
</style>
