<script setup>
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import StarField from '@/components/StarField.vue'
import TopBar from '@/components/TopBar.vue'
import AchievementToast from '@/components/AchievementToast.vue'
import BreakReminder from '@/components/BreakReminder.vue'
import { SKILL_MAP } from '@/data/curriculum.js'
import { useSettingsStore } from '@/stores/settings.js'
import { useProgressStore } from '@/stores/progress.js'
import { sound } from '@/utils/sound'
import { motion } from '@/utils/motion'

/** 使用时长的采样间隔：15 秒够画分钟级曲线，又不会频繁写 localStorage。 */
const USAGE_TICK_MS = 15_000

const settings = useSettingsStore()
const progress = useProgressStore()
const route = useRoute()
const rootClass = computed(() => ({ 'eye-care': settings.eyeCare }))
const practiceFocus = computed(() => {
  const id = String(route.query.skill ?? route.query.focus ?? route.query.wrong ?? '')
  return SKILL_MAP[id] ?? null
})
const practiceAnchor = computed(() =>
  route.path === '/visual-demos' ? 'visual-practice' : 'practice-stage',
)

// 共享 design-tokens 以 <html data-theme> 选主题，立即恢复家长上次选择。
watch(
  () => settings.theme,
  (theme) => {
    document.documentElement.dataset.theme = theme
  },
  { immediate: true },
)

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
    <aside
      v-if="practiceFocus"
      :id="practiceAnchor"
      class="practice-focus"
      :data-practice-skill="practiceFocus.id"
      role="status"
    >
      <span aria-hidden="true">🎯</span>
      <span>
        已按推荐定位到专项：<strong>{{ practiceFocus.name }}</strong>
      </span>
      <RouterLink to="/skill-graph">返回技能图谱</RouterLink>
    </aside>
    <router-view v-slot="{ Component }">
      <transition name="page" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
    <footer class="release-footer">
      <span>MathQuest v1.0.0 · 学习记录保存在本机</span>
      <RouterLink to="/privacy">隐私政策</RouterLink>
    </footer>
  </div>
</template>

<style scoped>
.practice-focus {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  width: min(1080px, calc(100% - 2 * var(--gap-md)));
  margin: 0 auto var(--gap-sm);
  padding: var(--gap-sm) var(--gap-md);
  border: 1px solid color-mix(in srgb, var(--brand) 45%, transparent);
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--brand) 12%, var(--surface));
  font-size: var(--fs-sm);
}

.practice-focus > span:nth-child(2) {
  flex: 1;
}

.practice-focus a {
  color: var(--brand);
  font-weight: var(--fw-bold);
  text-decoration: underline;
  text-underline-offset: 3px;
}

.release-footer {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: var(--gap-sm);
  width: min(1080px, calc(100% - 2 * var(--gap-md)));
  margin: 0 auto var(--gap-xl);
  color: var(--text-soft);
  font-size: var(--fs-sm);
  text-align: center;
}

.release-footer a {
  display: inline-flex;
  align-items: center;
  min-height: var(--tap-min);
  padding-inline: var(--gap-md);
  border-radius: var(--radius-pill);
  color: var(--accent);
  font-weight: var(--fw-bold);
  text-decoration: underline;
  text-underline-offset: var(--gap-2xs);
}
</style>
