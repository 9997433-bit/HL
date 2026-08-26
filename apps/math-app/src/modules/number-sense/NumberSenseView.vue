<script setup>
import ModulePlaceholder from '@/components/ModulePlaceholder.vue'
</script>

<template>
  <ModulePlaceholder
    module-id="number-sense"
    icon="🔢"
    title="数字星球"
    subtitle="数与量启蒙 · L1-L2 · 全语音引导,不识字可玩"
    :gameplays="[
      '点数收集:Canvas 散点拖入篮子(拖拽判定)',
      '数字描红:Canvas 轨迹绘制与笔顺判定',
      '比大小:天平动画(GSAP 倾斜)',
      '序数与排队:第几个?',
      '10 的分与合:数字弹珠配对'
    ]"
  />
</template>
