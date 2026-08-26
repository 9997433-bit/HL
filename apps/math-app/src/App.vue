<script setup>
import { computed } from 'vue'
import { useSettingsStore } from '@/stores/settings.js'

const settings = useSettingsStore()
const rootClass = computed(() => ({ 'eye-care': settings.eyeCare }))
</script>

<template>
  <div class="app-root" :class="rootClass">
    <router-view v-slot="{ Component }">
      <transition name="page" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </div>
</template>

<style>
.page-enter-active,
.page-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.page-enter-from {
  opacity: 0;
  transform: translateY(12px);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-12px);
}
</style>
