<script setup>
import { useSettingsStore } from '@/stores/settings.js'
import { useProgressStore } from '@/stores/progress.js'

const emit = defineEmits(['close'])
const settings = useSettingsStore()
const progress = useProgressStore()
</script>

<template>
  <div class="mask" role="dialog" aria-modal="true" aria-labelledby="break-title">
    <div class="sheet card">
      <div class="sheet__emoji" aria-hidden="true">🌈</div>
      <h2 id="break-title" class="sheet__title">该休息一下啦！</h2>
      <p class="sheet__body">
        今天已经学习了
        <strong>{{ Math.round(progress.todayStats.seconds / 60) }}</strong>
        分钟，达到家长设定的 {{ settings.dailyLimitMinutes }} 分钟。<br />
        站起来走一走，看看远处的绿色，眼睛会更舒服哦。
      </p>
      <div class="sheet__actions">
        <button class="btn btn--primary btn--lg btn--block" type="button" @click="emit('close', 'stop')">
          好，我去休息 🙋
        </button>
        <button class="btn btn--ghost btn--block" type="button" @click="emit('close', 'continue')">
          再学一会儿
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mask {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: grid;
  place-items: center;
  padding: var(--gap-md);
  background: rgba(30, 22, 10, 0.44);
  backdrop-filter: blur(4px);
}

.sheet {
  width: min(420px, 100%);
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
  animation: pop-in var(--dur-mid) var(--ease-pop);
}

.sheet__emoji {
  font-size: 3.4rem;
  line-height: 1;
}

.sheet__title {
  font-size: 1.45rem;
  font-weight: 800;
  color: var(--text-strong);
}

.sheet__body {
  color: var(--text);
  line-height: 1.8;
}

.sheet__actions {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
}
</style>
