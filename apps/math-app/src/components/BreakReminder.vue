<script setup>
/**
 * 防沉迷提醒 —— 今天玩够家长设定的时长后弹出，遮住整页但不锁死：
 * 低龄孩子被硬掐断只会哭闹，这里给「再玩 5 分钟」和「先休息」两个出口，
 * 两个都会推迟 5 分钟再提醒，不至于每秒钟弹一次。
 */
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { sound } from '@/utils/sound'

const SNOOZE_MINUTES = 5

const router = useRouter()
const progress = useProgressStore()
const settings = useSettingsStore()

/** 下一次允许弹窗的「今日累计分钟」阈值，只在本次会话里有效。 */
const snoozeUntil = ref(0)

const due = computed(() => {
  const limit = settings.dailyLimitMinutes
  if (!settings.breakReminder || limit <= 0) return false
  return progress.todayMinutes >= Math.max(limit, snoozeUntil.value)
})

function snooze() {
  snoozeUntil.value = progress.todayMinutes + SNOOZE_MINUTES
}

function keepPlaying() {
  sound.click()
  snooze()
}

function rest() {
  sound.click()
  snooze()
  router.push('/')
}
</script>

<template>
  <div v-if="due" class="mask">
    <div class="card" role="dialog" aria-modal="true" aria-labelledby="break-title">
      <span class="emoji" aria-hidden="true">🌙</span>
      <h2 id="break-title" class="title">该让眼睛休息一下啦</h2>
      <p class="text">
        今天已经在星际里冒险 {{ progress.todayMinutes }} 分钟，
        超过家长设定的 {{ settings.dailyLimitMinutes }} 分钟。
        去远眺一会儿，或者把刚才的题在纸上再算一遍。
      </p>
      <div class="actions">
        <button class="btn btn-primary" type="button" @click="rest">🛌 先休息</button>
        <button class="btn btn-ghost" type="button" @click="keepPlaying">
          再玩 {{ SNOOZE_MINUTES }} 分钟
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
  padding: 20px;
  background: rgba(4, 7, 26, 0.82);
  backdrop-filter: blur(6px);
}

.card {
  width: min(420px, 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 28px 24px;
  text-align: center;
  border-radius: var(--radius-l);
  background: linear-gradient(160deg, #252e6c, #101540);
  border: 1px solid rgba(140, 158, 255, 0.4);
  box-shadow: var(--shadow-card);
}

.emoji {
  font-size: 46px;
  line-height: 1;
}

.title {
  font-size: 21px;
  font-weight: 900;
}

.text {
  font-size: 15px;
  line-height: 1.7;
  color: var(--ink-soft);
}

.actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: center;
}
</style>
