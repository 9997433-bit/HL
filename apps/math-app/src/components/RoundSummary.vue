<script setup>
import { computed, onMounted, ref } from 'vue'
import gsap from 'gsap'
import MascotBot from '@/components/MascotBot.vue'
import { useFeedback } from '@/composables/useFeedback'

const props = defineProps({
  correct: { type: Number, required: true },
  total: { type: Number, required: true },
  starsEarned: { type: Number, default: 0 },
  moduleName: { type: String, default: '本轮练习' },
})

const emit = defineEmits(['replay', 'home'])

const card = ref(null)
const { burst } = useFeedback()

const score = computed(() => (props.total ? Math.round((props.correct / props.total) * 100) : 0))
const medals = computed(() => (score.value >= 100 ? 3 : score.value >= 80 ? 2 : score.value >= 60 ? 1 : 0))
const mood = computed(() => (score.value >= 80 ? 'cheer' : score.value >= 50 ? 'happy' : 'think'))
const remark = computed(() => {
  if (score.value >= 100) return '完美！整个星系都在为你鼓掌 🎊'
  if (score.value >= 80) return '太棒了！你是优秀的小宇航员 ✨'
  if (score.value >= 60) return '不错哦，再练一轮会更稳 💪'
  return '没关系，慢慢来，我们一起再飞一次 🛸'
})

onMounted(() => {
  gsap.fromTo(
    card.value,
    { scale: 0.86, opacity: 0, y: 22 },
    { scale: 1, opacity: 1, y: 0, duration: 0.5, ease: 'back.out(1.6)' },
  )
  gsap.fromTo(
    '.medal',
    { scale: 0, rotate: -140 },
    { scale: 1, rotate: 0, duration: 0.5, stagger: 0.14, delay: 0.3, ease: 'back.out(3)' },
  )
  if (score.value >= 60) setTimeout(() => burst(card.value, { count: 22 }), 420)
})
</script>

<template>
  <div class="overlay">
    <div ref="card" class="summary card">
      <MascotBot :mood="mood" :size="110" />
      <h2 class="head">{{ moduleName }}完成！</h2>

      <div class="medals">
        <span v-for="i in 3" :key="i" class="medal" :class="{ dim: i > medals }">⭐</span>
      </div>

      <div class="stats">
        <div class="stat">
          <span class="value">{{ correct }}/{{ total }}</span>
          <span class="label dim">答对</span>
        </div>
        <div class="stat">
          <span class="value">{{ score }}%</span>
          <span class="label dim">正确率</span>
        </div>
        <div class="stat">
          <span class="value">+{{ starsEarned }}</span>
          <span class="label dim">获得星星</span>
        </div>
      </div>

      <p class="remark muted">{{ remark }}</p>

      <div class="actions">
        <button class="btn btn--primary btn--lg" @click="emit('replay')">🔄 再来一轮</button>
        <button class="btn btn--ghost" @click="emit('home')">🗺️ 回到地图</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 120;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(5, 8, 26, 0.74);
  backdrop-filter: blur(8px);
}

.summary {
  width: min(96vw, 460px);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  text-align: center;
}

.head {
  font-size: 26px;
  font-weight: 900;
}

.medals {
  display: flex;
  gap: 10px;
  font-size: 40px;
}

.medal.dim {
  filter: grayscale(1);
  opacity: 0.3;
}

.stats {
  display: flex;
  gap: 10px;
  width: 100%;
}

.stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 12px 6px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.value {
  font-size: 22px;
  font-weight: 900;
}

.label {
  font-size: 12px;
}

.remark {
  font-size: 15px;
}

.actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: center;
}
</style>
