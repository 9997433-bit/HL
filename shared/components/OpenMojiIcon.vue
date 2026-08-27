<script setup>
import { computed } from 'vue'
import { openMojiUrl, resolveIcon } from '@shared/utils/openmoji.js'

const props = defineProps({
  /** shared/assets/openmoji 文件名，不含 .svg */
  name: { type: String, default: '' },
  /** 若未给 name，则按 emoji → 文件名映射表解析 */
  emoji: { type: String, default: '' },
  size: { type: [Number, String], default: 24 },
  label: { type: String, default: '' },
})

const iconName = computed(() => resolveIcon(props))
const src = computed(() => openMojiUrl(iconName.value))
const px = computed(() => (typeof props.size === 'number' ? `${props.size}px` : props.size))
</script>

<template>
  <img
    v-if="src"
    class="openmoji-icon"
    :src="src"
    :width="size"
    :height="size"
    :style="{ width: px, height: px }"
    :alt="label"
    :aria-hidden="label ? undefined : true"
    draggable="false"
    decoding="async"
  />
  <span v-else-if="emoji" class="openmoji-icon__fallback" aria-hidden="true">{{ emoji }}</span>
</template>

<style scoped>
.openmoji-icon {
  display: inline-block;
  vertical-align: middle;
  object-fit: contain;
  flex-shrink: 0;
  user-select: none;
  -webkit-user-drag: none;
}

.openmoji-icon__fallback {
  display: inline-block;
  line-height: 1;
}
</style>
