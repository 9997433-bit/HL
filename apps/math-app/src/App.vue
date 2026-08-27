<script setup>
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import StarField from '@/components/StarField.vue'
import TopBar from '@/components/TopBar.vue'
import AchievementToast from '@/components/AchievementToast.vue'
import BreakReminder from '@/components/BreakReminder.vue'
import { useSettingsStore } from '@/stores/settings.js'
import { useProgressStore } from '@/stores/progress.js'
import { sound } from '@/utils/sound'
import { motion } from '@/utils/motion'

/** 使用时长的采样间隔：15 秒够画分钟级曲线，又不会频繁写 localStorage。 */
const USAGE_TICK_MS = 15_000

const settings = useSettingsStore()
const progress = useProgressStore()
const rootClass = computed(() => ({ 'eye-care': settings.eyeCare }))

// 音效开关以玩法层设置为准，护眼模式由设置 store 控制
watch(
  () => progress.state.settings.sound && settings.soundOn,
  (on) => sound.setEnabled(on),
  { immediate: true },
)

// 动效同理：家长中心关掉后，GSAP 反馈动画整体降级
watch(
  () => progress.state.settings.animations && settings.animations,
  (on) => motion.setEnabled(on),
  { immediate: true },
)

// 只统计页面真正在前台的时间：切到后台的挂机时长不该算进防沉迷额度
let usageTimer = null
onMounted(() => {
  usageTimer = setInterval(() => {
    if (document.visibilityState !== 'visible') return
    progress.recordUsage(USAGE_TICK_MS / 1000)
  }, USAGE_TICK_MS)
})
onBeforeUnmount(() => clearInterval(usageTimer))
</script>

<template>
  <StarField />
  <div class="app-root" :class="rootClass">
    <TopBar />
    <AchievementToast />
    <BreakReminder />
    <router-view v-slot="{ Component }">
      <transition name="page" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </div>
</template>
