<script setup>
/**
 * 朗读按钮。朗读期间图标做声波动画，读完自动复位。
 * 系统没有中文嗓音时按钮变灰并给出说明——静默失败会让孩子反复点。
 */
import { onBeforeUnmount, ref } from 'vue'
import { hasChineseVoice, speak, speechSupported } from '@/utils/audio.js'
import { useProgressStore } from '@/stores/progress.js'

const props = defineProps({
  text: { type: String, required: true },
  label: { type: String, default: '' },
  rate: { type: Number, default: 0.85 },
  variant: { type: String, default: 'primary' }, // primary | ghost | round
  size: { type: String, default: 'md' } // sm | md | lg
})

const emit = defineEmits(['spoken'])

const progress = useProgressStore()
const speaking = ref(false)

const available = speechSupported

async function onClick() {
  if (!props.text || speaking.value) return
  speaking.value = true
  const ok = await speak(props.text, { rate: props.rate })
  speaking.value = false
  emit('spoken', ok)
}

onBeforeUnmount(() => {
  speaking.value = false
})

const unavailableHint = () =>
  !available
    ? '当前浏览器不支持语音朗读'
    : !hasChineseVoice() && progress.state.settings.speech
      ? '系统里没有中文语音包，可在系统设置中添加'
      : ''
</script>

<template>
  <button
    class="speak"
    :class="[`speak--${variant}`, `speak--${size}`, { 'is-speaking': speaking }]"
    type="button"
    :disabled="!available || !progress.state.settings.speech"
    :title="unavailableHint() || `朗读「${text}」`"
    :aria-label="label || `朗读 ${text}`"
    @click="onClick"
  >
    <span class="speak__icon" aria-hidden="true">
      <span class="speak__wave"></span>
      <span class="speak__wave"></span>
      <span class="speak__wave"></span>
    </span>
    <span v-if="label" class="speak__label">{{ label }}</span>
  </button>
</template>

<style scoped>
.speak {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border-radius: var(--radius-pill);
  font-weight: 800;
  transition: transform var(--dur-fast) var(--ease-pop), filter var(--dur-fast) ease;
}

.speak:active:not(:disabled) {
  transform: scale(0.95);
}

.speak:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.speak--primary {
  background: linear-gradient(180deg, var(--brand) 0%, var(--brand-strong) 100%);
  color: var(--text-invert);
  box-shadow: var(--shadow-sm), var(--shadow-press);
}

.speak--ghost {
  background: var(--surface-strong);
  color: var(--text-strong);
  box-shadow: var(--shadow-sm);
}

.speak--round {
  background: var(--accent-soft);
  color: var(--text-strong);
  box-shadow: var(--shadow-sm);
}

.speak--sm {
  min-height: 42px;
  padding: 0 16px;
  font-size: 0.88rem;
}

.speak--md {
  min-height: var(--tap-min);
  padding: 0 24px;
  font-size: 1rem;
}

.speak--lg {
  min-height: 72px;
  padding: 0 34px;
  font-size: 1.2rem;
}

.speak--round.speak--md {
  width: var(--tap-min);
  padding: 0;
}

.speak--round.speak--lg {
  width: 72px;
  padding: 0;
}

/* 三根竖条构成的小喇叭波形 */
.speak__icon {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  height: 1.1em;
}

.speak__wave {
  display: block;
  width: 4px;
  border-radius: 2px;
  background: currentColor;
  height: 42%;
}

.speak__wave:nth-child(2) {
  height: 100%;
}

.speak__wave:nth-child(3) {
  height: 66%;
}

.speak.is-speaking .speak__wave {
  animation: speak-bounce 0.62s ease-in-out infinite alternate;
}

.speak.is-speaking .speak__wave:nth-child(2) {
  animation-delay: 0.13s;
}

.speak.is-speaking .speak__wave:nth-child(3) {
  animation-delay: 0.26s;
}

@keyframes speak-bounce {
  from {
    height: 30%;
  }
  to {
    height: 100%;
  }
}

.speak__label {
  line-height: 1;
}
</style>
