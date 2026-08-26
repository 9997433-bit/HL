<script setup>
defineProps({
  index: { type: Number, required: true }, // 已完成题数
  total: { type: Number, required: true },
  correct: { type: Number, default: 0 },
  streak: { type: Number, default: 0 },
  marks: { type: Array, default: () => [] }, // 'ok' | 'no' | undefined
})
</script>

<template>
  <div class="session-bar">
    <div class="dots" :aria-label="`进度 ${index} / ${total}`">
      <span
        v-for="i in total"
        :key="i"
        class="dot"
        :class="{
          ok: marks[i - 1] === 'ok',
          no: marks[i - 1] === 'no',
          now: i - 1 === index && marks[i - 1] === undefined,
        }"
      />
    </div>
    <div class="spacer" />
    <span class="chip">第 {{ Math.min(index + 1, total) }} / {{ total }} 题</span>
    <span class="chip chip-on">✅ {{ correct }}</span>
    <span v-if="streak >= 2" class="chip streak">🔥 {{ streak }} 连击</span>
  </div>
</template>

<style scoped>
.session-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.dots {
  display: flex;
  gap: 6px;
}

.dot {
  width: 13px;
  height: 13px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.2);
  transition: all 0.25s ease;
}

.dot.ok {
  background: var(--green);
  border-color: var(--green);
  box-shadow: 0 0 10px rgba(85, 230, 165, 0.6);
}

.dot.no {
  background: var(--red);
  border-color: var(--red);
}

.dot.now {
  background: var(--gold);
  border-color: var(--gold);
  transform: scale(1.28);
  box-shadow: 0 0 12px rgba(255, 206, 77, 0.7);
}

.streak {
  background: linear-gradient(135deg, rgba(255, 159, 69, 0.32), rgba(255, 107, 125, 0.32));
  border-color: rgba(255, 159, 69, 0.6);
  color: var(--ink);
}
</style>
