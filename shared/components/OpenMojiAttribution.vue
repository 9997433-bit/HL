<script setup>
import { OPENMOJI_ATTRIBUTION } from '@shared/utils/openmoji.js'
</script>

<template>
  <p class="openmoji-attribution muted">
    {{ OPENMOJI_ATTRIBUTION }}
    <a href="https://creativecommons.org/licenses/by-sa/4.0/" target="_blank" rel="noopener noreferrer"
      >CC BY-SA 4.0</a
    >
  </p>
</template>

<style scoped>
.openmoji-attribution {
  margin: 0;
  font-size: 0.72rem;
  line-height: 1.45;
  opacity: 0.75;
}

.openmoji-attribution a {
  color: inherit;
}
</style>
