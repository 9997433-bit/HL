<script setup>
import { computed, watch } from 'vue'
import StarField from '@/components/StarField.vue'
import TopBar from '@/components/TopBar.vue'
import AchievementToast from '@/components/AchievementToast.vue'
import { useSettingsStore } from '@/stores/settings.js'
import { useProgressStore } from '@/stores/progress.js'
import { sound } from '@/utils/sound'

const settings = useSettingsStore()
const progress = useProgressStore()
const rootClass = computed(() => ({ 'eye-care': settings.eyeCare }))

// 音效开关以玩法层设置为准，护眼模式由设置 store 控制
watch(
  () => progress.state.settings.sound && settings.soundOn,
  (on) => sound.setEnabled(on),
  { immediate: true },
)
</script>

<template>
  <StarField />
  <div class="app-root" :class="rootClass">
    <TopBar />
    <AchievementToast />
    <router-view v-slot="{ Component }">
      <transition name="page" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </div>
</template>
