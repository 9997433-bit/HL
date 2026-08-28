<script setup>
/**
 * ROUND16_H4 学演示中心 —— 把注册表里的每个技能点摆成一张卡。
 *
 * 页面自己不放数据也不排顺序：条目、分组和三段内容全来自 data/learn-demos.js，
 * 播放/跳过/静态三态全在 components/LearnDemo.vue。这里只做三件事——
 * 按学科模块分组、解析深链（?demo= / ?skill=）、把选中的那条交给演示壳。
 */
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import LearnDemo from '@/components/LearnDemo.vue'
import { LEARN_DEMOS, ROUND17_H3 } from '@/data/learn-demos.js'
import { SKILL_MAP } from '@/data/curriculum.js'
import { MODULES } from '@/data/modules.js'
import { sound } from '@/utils/sound.js'

const route = useRoute()
const requested = String(route.query.demo ?? '')
const focused = String(route.query.skill ?? '')

// 深链优先级：指名道姓的 demo > 从技能图谱带过来的 skill > 表里第一条
const initial =
  LEARN_DEMOS.find((demo) => demo.id === requested) ??
  LEARN_DEMOS.find((demo) => demo.skill === focused) ??
  LEARN_DEMOS[0]

const selectedId = ref(initial.id)
const selected = computed(
  () => LEARN_DEMOS.find((demo) => demo.id === selectedId.value) ?? LEARN_DEMOS[0],
)
const selectedSkillName = computed(() => SKILL_MAP[selected.value.skill]?.name ?? '')

/** 学科模块 → 星球元数据；演示按星球分组，孩子才知道这一组该去哪儿练。 */
const PLANET_OF = Object.fromEntries(MODULES.map((m) => [m.curriculumId, m]))

const groups = computed(() => {
  const buckets = new Map()
  for (const demo of LEARN_DEMOS) {
    if (!buckets.has(demo.module)) buckets.set(demo.module, [])
    buckets.get(demo.module).push(demo)
  }
  return [...buckets].map(([moduleId, demos]) => ({
    id: moduleId,
    name: PLANET_OF[moduleId]?.name ?? moduleId,
    icon: PLANET_OF[moduleId]?.icon ?? '✨',
    route: PLANET_OF[moduleId]?.route ?? '/',
    demos,
  }))
})

function choose(id) {
  sound.click()
  selectedId.value = id
}
</script>

<template>
  <main class="page stack">
    <section class="intro card">
      <div>
        <p class="kicker">看得见的数学</p>
        <h2 class="page-title">学演示中心</h2>
        <p class="muted">
          每个技能点都有一段「实物 → 图形 → 算式」：先看熟悉的东西，再换成点和框，最后才写算式。
          能跳过、能重播，也能一步一步自己点。
        </p>
      </div>
      <span
        class="count-badge"
        data-visual-demo-count
        data-learn-demo-count
        :data-round17="ROUND17_H3"
      >
        {{ LEARN_DEMOS.length }} 个技能点
      </span>
    </section>

    <nav class="demo-picker card" aria-label="选择学演示">
      <section v-for="group in groups" :key="group.id" class="picker-group">
        <h3 class="group-head">
          <span aria-hidden="true">{{ group.icon }}</span>
          {{ group.name }}
          <small class="dim">{{ group.demos.length }} 个</small>
          <RouterLink class="group-link" :to="group.route">去练 →</RouterLink>
        </h3>
        <div class="group-grid">
          <button
            v-for="demo in group.demos"
            :key="demo.id"
            class="demo-tab"
            :class="{ on: selectedId === demo.id }"
            :aria-pressed="selectedId === demo.id"
            :data-demo-select="demo.id"
            :data-demo-select-skill="demo.skill"
            @click="choose(demo.id)"
          >
            <span>{{ demo.object.emoji }}</span>
            <strong>{{ demo.title }}</strong>
            <small>{{ demo.equation }}</small>
          </button>
        </div>
      </section>
    </nav>

    <LearnDemo :key="selected.id" :demo="selected" :skill-name="selectedSkillName" />
  </main>
</template>

<style scoped>
.intro {
  display: flex;
  align-items: center;
  gap: 18px;
}

.intro > div {
  flex: 1;
}

.page-title {
  margin: 3px 0 6px;
}

.kicker {
  color: var(--brand);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 1.6px;
}

.count-badge {
  flex: none;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  color: var(--star);
  background: rgba(255, 206, 77, 0.12);
  border: 1px solid rgba(255, 206, 77, 0.34);
  font-weight: 900;
  text-align: center;
}

.demo-picker {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 14px;
}

.group-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 15px;
}

.group-link {
  margin-left: auto;
  color: var(--brand);
  font-size: 13px;
  font-weight: 800;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.group-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
  gap: 8px;
}

.demo-tab {
  min-height: 104px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  border-radius: var(--radius-sm);
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.05);
  transition: transform 0.16s ease, border-color 0.16s ease, background 0.16s ease;
}

.demo-tab:hover,
.demo-tab.on {
  transform: translateY(-2px);
  border-color: rgba(94, 231, 255, 0.55);
  background: linear-gradient(145deg, rgba(94, 231, 255, 0.16), rgba(155, 140, 255, 0.14));
}

.demo-tab span {
  font-size: 24px;
}

.demo-tab strong {
  font-size: 13px;
}

.demo-tab small {
  color: var(--star);
  font-weight: 800;
}

@media (max-width: 560px) {
  .intro {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
