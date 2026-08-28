<script setup>
/**
 * ROUND16_H4 学演示入口 —— 挂在玩法页上的那一个「🎞️ 看演示」。
 *
 * 卡在题面上的时候，孩子缺的往往不是再试一次，而是「这个知识点到底在讲什么」。
 * 传进来的技能点在注册表里有演示，就渲染按钮，点开就地弹出「实物 → 图形 → 算式」；
 * 没有演示就什么都不渲染——宁可没有入口，也不摆一个点了没反应的按钮。
 *
 * 弹层只盖在题面上，不接管这一轮：题序、连击、计时都由玩法页自己管，
 * 这里只把开合状态用 `update:open` 报出去，好让宿主在盖着的时候先别收键盘输入。
 *
 * 演示壳和注册表都按需加载：玩法路由块里只静态引 learn-demo-index 那份技能清单，
 * 不把全部旁白文案压进每个玩法的首包（预算见 scripts/check-route-budget.mjs）。
 */
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { SKILL_MAP } from '@/data/curriculum.js'
import { hasLearnDemo } from '@/data/learn-demo-index.js'
import { sound } from '@/utils/sound.js'

const props = defineProps({
  skill: { type: String, default: '' },
  label: { type: String, default: '🎞️ 看演示' },
})

const emit = defineEmits(['update:open'])

const LearnDemo = defineAsyncComponent(() => import('@/components/LearnDemo.vue'))

const demo = ref(null)
const open = ref(false)
const available = computed(() => hasLearnDemo(props.skill))
const skillName = computed(() => SKILL_MAP[props.skill]?.name ?? '')

async function show() {
  if (!available.value) return
  sound.click()
  const registry = await import('@/data/learn-demos.js')
  const found = registry.learnDemoOfSkill(props.skill)
  if (!found) return
  demo.value = found
  open.value = true
}

function hide() {
  if (!open.value) return
  open.value = false
  sound.click()
}

// 换题就收：上一题的知识点讲完了，不该盖在下一题上
watch(() => props.skill, () => (open.value = false))
watch(open, (value) => emit('update:open', value))

defineExpose({ hide, available })
</script>

<template>
  <button
    v-if="available"
    class="btn btn--ghost btn--sm"
    data-learn-demo-open
    :data-learn-demo-skill="skill"
    @click="show"
  >
    {{ label }}
  </button>

  <Teleport to="body">
    <div
      v-if="open && demo"
      class="demo-layer"
      role="dialog"
      aria-modal="true"
      aria-label="学演示"
      data-learn-demo-layer
      @keydown.esc="hide"
    >
      <div class="demo-layer-inner">
        <LearnDemo
          :key="demo.id"
          :demo="demo"
          :skill-name="skillName"
          dismiss-label="✕ 收起，继续练"
          @dismiss="hide"
        />
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.demo-layer {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  overflow: auto;
  padding: clamp(12px, 4vw, 40px);
  background: rgba(4, 6, 20, 0.78);
  backdrop-filter: blur(3px);
}

.demo-layer-inner {
  width: min(1080px, 100%);
}
</style>
