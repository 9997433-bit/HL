<script setup>
/**
 * 全局庆祝层：把 progress store 里排队的庆祝事件接到可跳过的浮层上。
 *
 * 这里只负责「什么时候庆祝、庆祝什么」，动画节奏与跳过逻辑都在
 * CelebrationOverlay 里（设计规范 §6.2 / §6.3）。
 */
import { computed } from 'vue'
import CelebrationOverlay from '@/components/CelebrationOverlay.vue'
import { useProgressStore } from '@/stores/progress.js'

const progress = useProgressStore()

const event = computed(() => progress.pendingCelebration)

const reduceMotion = computed(() => progress.state.settings.motion === 'reduced')
</script>

<template>
  <CelebrationOverlay
    :key="event?.at"
    :open="!!event"
    :emoji="event?.emoji || '🎉'"
    :title="event?.title || '真棒！'"
    :subtitle="event?.subtitle || ''"
    :highlight="event?.char || ''"
    :stars="event?.stars || 0"
    :reduce-motion="reduceMotion"
    @done="progress.clearCelebration()"
  />
</template>
