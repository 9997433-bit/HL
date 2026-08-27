<script setup>
/**
 * 技能图谱 —— 一张只读的地图，回答「这些技能谁挡着谁、孩子现在走到哪儿了」。
 *
 * 页面本身不出题也不写进度：掌握度来自 progress store，年龄档来自 settings store，
 * 节点状态由 data/skill-graph.js 的纯函数算出来。想练某个技能，从详情卡跳去对应星球，
 * 成绩仍旧记在那颗星球名下。
 */
import { computed, ref } from 'vue'
import { bandOf } from '@/data/age-band.js'
import { buildSkillGraph, SKILL_STATUSES, STATUS_MAP } from '@/data/skill-graph.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { sound } from '@/utils/sound.js'

const progress = useProgressStore()
const settings = useSettingsStore()

const selectedId = ref(null)
const moduleFilter = ref('all')
/** 只看本档：把超前的技能压暗，但仍留在图上——家长要能看见后面还有什么。 */
const bandOnly = ref(false)

const band = computed(() => bandOf(settings.ageBand))

const graph = computed(() =>
  buildSkillGraph({ mastery: progress.state.mastery, ageBand: settings.ageBand }),
)

const size = computed(() => graph.value.size)
const nodeMap = computed(() => Object.fromEntries(graph.value.nodes.map((n) => [n.id, n])))

/** 被筛选条件压暗的节点仍然占位：坐标是算好的，抽掉一个连线就断了。 */
const faded = (node) =>
  (moduleFilter.value !== 'all' && node.module !== moduleFilter.value) ||
  (bandOnly.value && !node.inBand)

const nodes = computed(() =>
  graph.value.nodes.map((node) => ({
    ...node,
    faded: faded(node),
    selected: node.id === selectedId.value,
    statusLabel: STATUS_MAP[node.status].label,
  })),
)

const edges = computed(() =>
  graph.value.edges.map((edge) => ({
    ...edge,
    faded: faded(nodeMap.value[edge.from]) && faded(nodeMap.value[edge.to]),
    linked: edge.from === selectedId.value || edge.to === selectedId.value,
  })),
)

const stats = computed(() => graph.value.stats)

const summary = computed(() => [
  { key: 'mastered', label: '已掌握', value: `${stats.value.mastered}/${stats.value.total}` },
  { key: 'learning', label: '练习中', value: stats.value.learning },
  { key: 'ready', label: '可开练', value: stats.value.ready },
  { key: 'inband', label: `${band.value.name}覆盖`, value: `${stats.value.inBand.percent}%` },
])

/** 详情卡：选中节点的前置、后继与母题数，全部现算，不留第二份状态。 */
const detail = computed(() => {
  const node = nodeMap.value[selectedId.value]
  if (!node) return null
  return {
    ...node,
    statusLabel: STATUS_MAP[node.status].label,
    deps: node.deps.map((id) => nodeMap.value[id]).filter(Boolean),
    unlocks: graph.value.nodes.filter((n) => n.deps.includes(node.id)),
  }
})

const nextUp = computed(() => graph.value.next)

function select(node) {
  sound.click()
  selectedId.value = selectedId.value === node.id ? null : node.id
}

function pickModule(id) {
  if (moduleFilter.value === id) return
  sound.click()
  moduleFilter.value = id
}

function toggleBandOnly() {
  sound.click()
  bandOnly.value = !bandOnly.value
}
</script>

<template>
  <main class="page stack" data-skill-graph>
    <section class="intro card">
      <div>
        <p class="kicker">看得见的学习路线</p>
        <h2 class="page-title">技能图谱</h2>
        <p class="muted">
          {{ stats.total }} 个技能点按依赖关系连成一张图：左边的练熟了，右边的才真正学得动。
          这里只展示进度，练习仍然回各颗星球里做。
        </p>
      </div>
      <div class="intro-side">
        <span class="chip graph-band" data-graph-band>
          🎚️ 年龄档 {{ band.id }} · {{ band.name }}
        </span>
        <span class="dim small">档位在家长中心设置，本页只读</span>
      </div>
    </section>

    <section class="summary-row" aria-label="技能掌握概览">
      <div v-for="item in summary" :key="item.key" class="summary card" :data-graph-stat="item.key">
        <strong>{{ item.value }}</strong>
        <span class="dim small">{{ item.label }}</span>
      </div>
    </section>

    <section class="controls card">
      <div class="filter-row" role="group" aria-label="按星球筛选">
        <button
          class="chip filter"
          :class="{ 'chip-on': moduleFilter === 'all' }"
          data-module-filter="all"
          :aria-pressed="moduleFilter === 'all'"
          @click="pickModule('all')"
        >
          全部星球
        </button>
        <button
          v-for="lane in graph.lanes"
          :key="lane.module"
          class="chip filter"
          :class="{ 'chip-on': moduleFilter === lane.module }"
          :data-module-filter="lane.module"
          :aria-pressed="moduleFilter === lane.module"
          @click="pickModule(lane.module)"
        >
          {{ lane.emoji }} {{ lane.name }}
          <em class="dim">{{ lane.mastered }}/{{ lane.total }}</em>
        </button>
      </div>
      <div class="legend-row">
        <button
          class="chip filter"
          :class="{ 'chip-on': bandOnly }"
          data-band-filter
          :aria-pressed="bandOnly"
          @click="toggleBandOnly"
        >
          {{ bandOnly ? '☑' : '☐' }} 只看 {{ band.id }} 该会的
        </button>
        <span class="spacer" />
        <span v-for="s in SKILL_STATUSES" :key="s.id" class="legend" :data-legend="s.id">
          <i :style="{ background: s.color }" aria-hidden="true" />
          {{ s.label }}
        </span>
      </div>
    </section>

    <section class="canvas-wrap card" aria-label="技能依赖图">
      <div class="canvas" :style="{ width: `${size.width}px`, height: `${size.height}px` }">
        <div
          v-for="lane in graph.lanes"
          :key="lane.module"
          class="lane"
          :data-skill-lane="lane.module"
          :style="{
            top: `${lane.top}px`,
            height: `${lane.height}px`,
            width: `${size.width}px`,
            '--lane-color': lane.color,
          }"
        >
          <span class="lane-tag">{{ lane.emoji }} {{ lane.name }} · {{ lane.percent }}%</span>
        </div>

        <svg
          class="edges"
          :viewBox="`0 0 ${size.width} ${size.height}`"
          :width="size.width"
          :height="size.height"
          aria-hidden="true"
        >
          <path
            v-for="edge in edges"
            :key="edge.id"
            class="edge"
            :class="{ open: edge.open, faded: edge.faded, linked: edge.linked }"
            :data-skill-edge="edge.id"
            :d="edge.path"
          />
        </svg>

        <button
          v-for="node in nodes"
          :key="node.id"
          class="node"
          :class="[node.status, { faded: node.faded, focus: node.focus, on: node.selected }]"
          :data-skill-node="node.id"
          :data-skill-status="node.status"
          :data-in-band="node.inBand ? '1' : '0'"
          :aria-pressed="node.selected"
          :aria-label="`${node.name}，${node.moduleName}，${node.level} 档，${node.statusLabel}，掌握度 ${node.percent}%`"
          :style="{
            left: `${node.x}px`,
            top: `${node.y}px`,
            width: `${node.w}px`,
            height: `${node.h}px`,
            '--node-color': node.color,
          }"
          @click="select(node)"
        >
          <span class="node-top">
            <span class="node-emoji" aria-hidden="true">{{ node.emoji }}</span>
            <strong class="node-name">{{ node.name }}</strong>
            <span class="node-level">{{ node.level }}</span>
          </span>
          <span class="node-bar" aria-hidden="true">
            <i :style="{ width: `${node.percent}%` }" />
          </span>
        </button>
      </div>
    </section>

    <section v-if="detail" class="detail card" data-skill-detail>
      <div class="detail-head row">
        <span class="detail-emoji" aria-hidden="true">{{ detail.emoji }}</span>
        <div>
          <h3 class="panel-title">{{ detail.name }}</h3>
          <p class="dim small">
            {{ detail.moduleName }} · {{ detail.level }} 档 · {{ detail.statusLabel }} ·
            掌握度 {{ detail.percent }}%
          </p>
        </div>
        <span class="spacer" />
        <RouterLink class="btn btn--primary btn--sm" :to="detail.route">
          去 {{ detail.moduleName }} 练 →
        </RouterLink>
      </div>
      <dl class="detail-grid">
        <div>
          <dt class="dim small">前置技能</dt>
          <dd>
            <span v-if="!detail.deps.length" class="dim">没有前置，随时可以开练</span>
            <span
              v-for="dep in detail.deps"
              :key="dep.id"
              class="chip tiny"
              :class="dep.status"
              :data-skill-dep="dep.id"
            >
              {{ dep.name }} {{ dep.percent }}%
            </span>
          </dd>
        </div>
        <div>
          <dt class="dim small">练熟后解锁</dt>
          <dd>
            <span v-if="!detail.unlocks.length" class="dim">这是这条线的终点</span>
            <span
              v-for="next in detail.unlocks"
              :key="next.id"
              class="chip tiny"
              :data-skill-unlock="next.id"
            >
              {{ next.name }}
            </span>
          </dd>
        </div>
        <div v-if="detail.wordProblems">
          <dt class="dim small">生活行星母题</dt>
          <dd><span class="chip tiny">{{ detail.wordProblems }} 道母题在练这一点</span></dd>
        </div>
      </dl>
    </section>

    <section class="next card" aria-labelledby="next-title">
      <h3 id="next-title" class="panel-title">接下来练什么</h3>
      <p class="muted small">按「练过没过线 → 前置已通的新技能」排，本档的排在超前的前面。</p>
      <ul class="next-list">
        <li v-for="node in nextUp" :key="node.id" class="next-row" :data-next-skill="node.id">
          <span class="node-emoji" aria-hidden="true">{{ node.emoji }}</span>
          <div class="next-titles">
            <strong>{{ node.name }}</strong>
            <span class="dim small">
              {{ node.moduleName }} · {{ node.level }} 档 ·
              {{ node.status === 'learning' ? `已练到 ${node.percent}%` : '前置已通，可以开练' }}
            </span>
          </div>
          <RouterLink class="btn btn--ghost btn--sm" :to="node.route">去练 →</RouterLink>
        </li>
        <li v-if="!nextUp.length" class="dim">整张图都练完了，去成就墙看看战绩吧。</li>
      </ul>
    </section>

    <div class="foot-links">
      <RouterLink to="/" class="btn btn--ghost btn--sm">🗺️ 回到学习地图</RouterLink>
      <RouterLink to="/progress" class="btn btn--ghost btn--sm">🏆 成就墙</RouterLink>
    </div>
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

.intro-side {
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 6px;
  text-align: right;
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

.graph-band {
  border-color: rgba(155, 140, 255, 0.42);
  background: rgba(155, 140, 255, 0.12);
}

.summary-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
}

.summary {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 14px 10px;
}

.summary strong {
  font-size: 22px;
  color: var(--star);
}

.controls {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.filter-row,
.legend-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.filter em {
  font-style: normal;
  font-size: 12px;
}

.legend {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 12px;
  color: var(--text-soft);
}

.legend i {
  width: 10px;
  height: 10px;
  border-radius: 3px;
}

/* ---------- 图 ---------- */

.canvas-wrap {
  overflow: auto;
  padding: 10px;
}

.canvas {
  position: relative;
}

.lane {
  position: absolute;
  left: 0;
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--lane-color) 7%, transparent);
  border: 1px dashed color-mix(in srgb, var(--lane-color) 26%, transparent);
}

.lane-tag {
  position: absolute;
  top: 4px;
  right: 8px;
  font-size: 11px;
  font-weight: 800;
  color: color-mix(in srgb, var(--lane-color) 78%, white);
  opacity: 0.85;
}

.edges {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.edge {
  fill: none;
  stroke: rgba(255, 255, 255, 0.16);
  stroke-width: 2;
  stroke-dasharray: 5 5;
}

.edge.open {
  stroke: rgba(85, 230, 165, 0.55);
  stroke-dasharray: none;
}

.edge.linked {
  stroke: var(--brand);
  stroke-width: 3;
  stroke-dasharray: none;
}

.edge.faded {
  opacity: 0.18;
}

.node {
  position: absolute;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
  padding: 8px 10px;
  text-align: left;
  border-radius: var(--radius-sm);
  border: 1px solid color-mix(in srgb, var(--node-color) 34%, transparent);
  background: linear-gradient(
    150deg,
    color-mix(in srgb, var(--node-color) 16%, var(--surface)),
    var(--surface)
  );
  transition: transform 0.16s ease, box-shadow 0.16s ease, opacity 0.16s ease;
}

.node:hover,
.node.on {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px color-mix(in srgb, var(--node-color) 30%, transparent);
  border-color: color-mix(in srgb, var(--node-color) 72%, transparent);
}

.node.locked {
  opacity: 0.62;
  border-style: dashed;
}

.node.mastered {
  border-color: rgba(85, 230, 165, 0.6);
}

.node.focus::after {
  content: '';
  position: absolute;
  inset: -4px;
  border-radius: calc(var(--radius-sm) + 4px);
  border: 1px solid rgba(155, 140, 255, 0.5);
  pointer-events: none;
}

.node.faded {
  opacity: 0.2;
}

.node-top {
  display: flex;
  align-items: center;
  gap: 6px;
}

.node-emoji {
  font-size: 16px;
}

.node-name {
  flex: 1;
  font-size: 13px;
  line-height: 1.2;
}

.node-level {
  font-size: 10px;
  font-weight: 900;
  color: var(--text-soft);
}

.node-bar {
  display: block;
  height: 5px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  overflow: hidden;
}

.node-bar i {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: var(--node-color);
}

/* ---------- 详情与建议 ---------- */

.detail-emoji {
  font-size: 28px;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.detail-grid dd {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 5px;
}

.chip.tiny {
  padding: 3px 10px;
  font-size: 12px;
}

.chip.tiny.mastered {
  border-color: rgba(85, 230, 165, 0.5);
  color: #55e6a5;
}

.next-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 10px;
}

.next-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.05);
}

.next-titles {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.foot-links {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

@media (max-width: 640px) {
  .intro {
    flex-direction: column;
    align-items: flex-start;
  }

  .intro-side {
    align-items: flex-start;
    text-align: left;
  }
}
</style>
