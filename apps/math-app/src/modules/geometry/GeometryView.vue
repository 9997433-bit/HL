<script setup>
import ModulePlaceholder from '@/components/ModulePlaceholder.vue'
</script>

<template>
  <ModulePlaceholder
    module-id="geometry"
    icon="🔷"
    title="图形星球"
    subtitle="几何空间 · L1-L5 · Canvas 矩阵变换与吸附判定"
    :gameplays="[
      '形状猎人:场景中找出指定图形',
      '七巧板拼图:旋转/翻转/吸附(Round 2 技术 spike)',
      '对称画师:镜像补全',
      '立体展开:正方体展开图判断(L4+)',
      '周长面积实验室:方格数格子'
    ]"
  />
</template>
