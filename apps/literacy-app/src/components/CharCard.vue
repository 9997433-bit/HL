<script setup>
import { computed } from 'vue'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import OpenMojiIcon from '@shared/components/OpenMojiIcon.vue'

const props = defineProps({
  item: { type: Object, required: true },
  locked: { type: Boolean, default: false }
})

const progress = useProgressStore()
const settings = useSettingsStore()

const state = computed(() => {
  if (props.locked) return 'locked'
  if (progress.isMastered(props.item.char)) return 'mastered'
  if (progress.isLearned(props.item.char)) return 'learned'
  return 'new'
})

const badge = computed(
  () =>
    ({
      locked: { icon: 'locked', text: '未解锁' },
      mastered: { icon: 'trophy', text: '已掌握' },
      learned: { icon: 'seedling', text: '学过了' },
      new: { icon: 'sparkles', text: '新字' }
    })[state.value]
)
</script>

<template>
  <component
    :is="locked ? 'div' : 'RouterLink'"
    :to="locked ? undefined : `/learn/${encodeURIComponent(item.char)}`"
    class="cc"
    :class="`cc--${state}`"
    :aria-disabled="locked || undefined"
  >
    <span class="cc__badge" :title="badge.text">
      <OpenMojiIcon :name="badge.icon" :size="16" />
    </span>
    <span class="cc__char">{{ item.char }}</span>
    <span v-if="settings.showPinyin" class="cc__pinyin">{{ item.pinyin }}</span>
    <OpenMojiIcon class="cc__emoji" :emoji="item.emoji" :size="18" />
    <span class="sr-only">{{ item.char }}，{{ item.pinyin }}，{{ badge.text }}</span>
  </component>
</template>

<style scoped>
.cc {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  aspect-ratio: 1 / 1.06;
  padding: 10px 8px;
  border-radius: var(--radius-md);
  background: var(--surface-strong);
  border: 2px solid transparent;
  box-shadow: var(--shadow-sm);
  transition: transform var(--dur-fast) var(--ease-pop), box-shadow var(--dur-fast) ease,
    border-color var(--dur-fast) ease;
}

.cc:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
}

.cc:active {
  transform: translateY(0) scale(0.96);
}

.cc__char {
  font-size: clamp(2rem, 8vw, 2.6rem);
  line-height: 1.05;
  font-weight: 700;
  color: var(--text-strong);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

.cc__pinyin {
  font-size: 0.78rem;
  color: var(--text-soft);
  letter-spacing: 0.03em;
}

.cc__emoji {
  position: absolute;
  left: 7px;
  bottom: 5px;
  font-size: 0.9rem;
  opacity: 0.75;
}

.cc__badge {
  position: absolute;
  top: 6px;
  right: 7px;
  font-size: 0.85rem;
  line-height: 1;
}

.cc--new {
  border-color: color-mix(in srgb, var(--brand) 35%, transparent);
}

.cc--learned {
  background: linear-gradient(180deg, var(--surface-strong) 55%, var(--accent-soft) 100%);
  border-color: color-mix(in srgb, var(--accent) 45%, transparent);
}

.cc--mastered {
  background: linear-gradient(180deg, var(--surface-strong) 45%, var(--brand-soft) 100%);
  border-color: var(--star);
  box-shadow: var(--shadow-md);
}

.cc--locked {
  opacity: 0.45;
  filter: grayscale(0.6);
  cursor: not-allowed;
  box-shadow: none;
}

.cc--locked:hover {
  transform: none;
}
</style>
