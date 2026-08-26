<script setup>
import ModulePlaceholder from '@/components/ModulePlaceholder.vue'
</script>

<template>
  <ModulePlaceholder
    module-id="logic"
    icon="🧩"
    title="逻辑星球"
    subtitle="逻辑推理 · L1-L4 · 模式文法生成无限题"
    :gameplays="[
      '图案序列:ABAB/AABB/递增模式续接',
      '分类大师:颜色/形状/功能多维分类',
      '迷宫寻宝:条件迷宫(只走偶数格)',
      '真假侦探:简单命题推理(L4+)'
    ]"
  />
</template>
