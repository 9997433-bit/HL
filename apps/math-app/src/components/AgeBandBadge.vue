<script setup>
/** 玩法页上的年龄档提示：告诉家长这一页的起步难度是从哪儿来的。 */
import { computed } from 'vue'
import { bandSummary } from '@/data/age-band.js'
import { useAgeBand } from '@/composables/useAgeBand'

const props = defineProps({
  /** age-band.js 里 AGE_BAND_MODULES 的 key */
  module: { type: String, required: true },
})

const band = useAgeBand()
const hint = computed(() => band.value.hints[props.module] ?? band.value.desc)
const title = computed(() => `年龄档在家长中心设置。${bandSummary(band.value.id)}`)
</script>

<template>
  <span class="chip band-badge" :title="title">
    🎚️ {{ band.name }} · 默认 {{ hint }}
  </span>
</template>

<style scoped>
.band-badge {
  border-color: rgba(155, 140, 255, 0.42);
  background: rgba(155, 140, 255, 0.12);
}
</style>
