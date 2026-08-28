<script setup>
/**
 * 技能图谱 —— 一张只读的地图，回答「这些技能谁挡着谁、孩子现在走到哪儿了」。
 *
 * 页面本身不出题也不写进度：掌握度来自 progress store，年龄档来自 settings store，
 * 节点状态与「推荐下一步」都由 data/skill-graph.js 的纯函数算出来。想练某个技能，
 * 从详情卡或推荐位跳去对应玩法，成绩仍旧记在那颗星球名下。
 *
 * 推荐同样是只读的：它不预约、不落盘，也不往 progress 里写任何东西，
 * 只是把同一份存档按当前年龄档重新排了个序。「去练」也只是一条链接：
 * 落到错题重练还是日冒险专项，由 data/skill-practice.js 现算（见那里的说明），
 * 点之前图谱不会因为算过这个落点而多写一个字节。
 */
import { computed, ref } from 'vue'
import { bandOf } from '@/data/age-band.js'
import {
  RECOMMEND_REASON_MAP,
  SKILL_STATUSES,
  STATUS_MAP,
  buildSkillGraph,
} from '@/data/skill-graph.js'
import { learnDemoRoute } from '@/data/learn-demo-index.js'
import { practiceEntry, wrongCountsBySkill } from '@/data/skill-practice.js'
import { buildWeekPlan, SESSION_MINUTES } from '@/data/week-plan.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { sound } from '@/utils/sound.js'

const progress = useProgressStore()
const settings = useSettingsStore()

const selectedId = ref(null)
const moduleFilter = ref('all')
/** 只看本档：把超前的技能压暗，但仍留在图上——家长要能看见后面还有什么。 */
const bandOnly = ref(false)
/** 一次停留是一组推荐 cohort；只在孩子点击开练时写入，不做浏览曝光打点。 */
const recoCohortId = `graph-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`

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

/** 技能 id → 它在推荐列表里排第几，图上给推荐位描一圈并标上序号。 */
const recoRank = computed(() =>
  Object.fromEntries(graph.value.reco.items.map((item, index) => [item.id, index + 1])),
)

const nodes = computed(() =>
  graph.value.nodes.map((node) => ({
    ...node,
    faded: faded(node),
    selected: node.id === selectedId.value,
    statusLabel: STATUS_MAP[node.status].label,
    recoRank: recoRank.value[node.id] ?? 0,
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

/** 推荐下一步：掌握度决定「能练什么、补到哪儿了」，年龄档决定「先练哪个」。 */
const reco = computed(() => graph.value.reco)

/** 错题欠账按技能点归拢一次，推荐位的落点和详情卡都读它。 */
const wrongCounts = computed(() => wrongCountsBySkill(progress.state.wrongBook))
const detailEntry = computed(() =>
  detail.value ? practiceEntry(detail.value, { wrongCounts: wrongCounts.value }) : null,
)

/**
 * ROUND16_H4：开练之前先看一眼「这个技能长什么样」。
 * 只有注册表里真有这条演示才给链接，没有就不摆一个死按钮出来。
 */
const detailDemo = computed(() => (detail.value ? learnDemoRoute(detail.value.id) : null))

const recoItems = computed(() =>
  reco.value.items.map((item) => ({
    ...item,
    hint: RECOMMEND_REASON_MAP[item.reason].hint,
    entry: practiceEntry(item, { wrongCounts: wrongCounts.value }),
  })),
)

/**
 * 周计划：把上面这份推荐往后滚一周（见 data/week-plan.js）。
 * 和推荐一样只读——里面的掌握度是「照着练大概会到哪儿」的推演值，
 * 页面上必须标成预计，不能让家长把它当成孩子已经拿到的成绩。
 */
const weekPlan = computed(() =>
  buildWeekPlan({
    mastery: progress.state.mastery,
    ageBand: settings.ageBand,
    wrongBook: progress.state.wrongBook,
  }),
)

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

function adoptRecommendation(item) {
  progress.recordRecommendationAdoption({
    cohortId: recoCohortId,
    skill: item.id,
    offeredSkills: recoItems.value.map((row) => row.id),
    source: 'next-step',
  })
}

function adoptWeekSkill(skill) {
  const today = weekPlan.value.days.find((day) => day.today)
  progress.recordRecommendationAdoption({
    cohortId: `${recoCohortId}-week`,
    skill: skill.id,
    offeredSkills: today?.skills.map((row) => row.id) ?? [skill.id],
    source: 'week-plan',
  })
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
          :class="[
            node.status,
            { faded: node.faded, focus: node.focus, on: node.selected, reco: node.recoRank },
          ]"
          :data-skill-node="node.id"
          :data-skill-status="node.status"
          :data-in-band="node.inBand ? '1' : '0'"
          :data-reco-rank="node.recoRank || null"
          :aria-pressed="node.selected"
          :aria-label="`${node.name}，${node.moduleName}，${node.level} 档，${node.statusLabel}，掌握度 ${node.percent}%${
            node.recoRank ? `，推荐第 ${node.recoRank} 步` : ''
          }`"
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
          <span v-if="node.recoRank" class="node-reco" aria-hidden="true">{{ node.recoRank }}</span>
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
        <RouterLink
          v-if="detailDemo"
          class="btn btn--ghost btn--sm"
          :to="detailDemo"
          :data-learn-demo-link="detail.id"
        >
          🎞️ 先看演示
        </RouterLink>
        <RouterLink class="btn btn--ghost btn--sm" :to="detail.route">
          去 {{ detail.moduleName }} 练 →
        </RouterLink>
        <RouterLink
          v-if="detailEntry"
          class="btn btn--primary btn--sm"
          :to="detailEntry.to"
          :data-skill-practice-entry="detail.id"
          :data-skill-practice-kind="detailEntry.kind"
        >
          练此专项 →
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

    <section class="next card" aria-labelledby="next-title" data-skill-reco>
      <div class="next-head row">
        <h3 id="next-title" class="panel-title">推荐下一步</h3>
        <span class="spacer" />
        <span class="chip tiny dim" data-reco-readonly>只读建议 · 不写进度</span>
      </div>
      <p class="muted small">
        按「掌握度 × {{ band.id }} 年龄档」现算：先补练过没过线的，再补本档欠着的底子，
        超前的排最后。换个档位再看，就是另一份建议。
      </p>
      <p class="muted small">
        「去练」直接落到能练这一点的地方：还欠着错题就去错题本重做，
        每日冒险出得了这类题就开一份当天固定的专项冒险，都不行才回星球。
      </p>
      <ul class="next-list">
        <li
          v-for="(item, index) in recoItems"
          :key="item.id"
          class="next-row"
          :data-next-skill="item.id"
          :data-reco-item="item.id"
          :data-reco-reason="item.reason"
          :data-reco-rank="index + 1"
        >
          <span class="reco-no" aria-hidden="true">{{ index + 1 }}</span>
          <span class="node-emoji" aria-hidden="true">{{ item.emoji }}</span>
          <div class="next-titles">
            <strong>
              {{ item.name }}
              <em class="reason" :class="item.reason" :title="item.hint">{{ item.reasonLabel }}</em>
            </strong>
            <span class="dim small">
              {{ item.moduleName }} · {{ item.level }} 档 · {{ item.why }}
            </span>
            <span class="dim small" :data-reco-entry-hint="item.entry.kind">
              {{ item.entry.hint }}
            </span>
          </div>
          <div class="next-actions">
            <RouterLink
              class="btn btn--primary btn--sm"
              :to="item.entry.to"
              :data-reco-entry="item.entry.kind"
              :data-reco-entry-skill="item.id"
              @click="adoptRecommendation(item)"
            >
              {{ item.entry.label }} →
            </RouterLink>
            <RouterLink
              v-if="item.entry.kind !== 'planet'"
              class="btn btn--ghost btn--sm"
              :to="item.route"
              :data-reco-planet="item.id"
            >
              去{{ item.moduleName }}
            </RouterLink>
          </div>
        </li>
        <li v-if="!recoItems.length" class="dim">整张图都练完了，去成就墙看看战绩吧。</li>
      </ul>

      <div v-if="reco.goal" class="reco-path" data-reco-path>
        <p class="path-head">
          <span class="dim small">本档目标</span>
          <strong :data-reco-goal="reco.goal.id">{{ reco.goal.emoji }} {{ reco.goal.name }}</strong>
          <span class="dim small">还差 {{ reco.path.length }} 步</span>
        </p>
        <ol class="path-list">
          <li
            v-for="step in reco.path"
            :key="step.id"
            class="path-step"
            :class="step.status"
            :data-reco-step="step.id"
            :data-reco-step-index="step.step"
          >
            <span class="step-no" aria-hidden="true">{{ step.step }}</span>
            <span class="step-name">{{ step.name }}</span>
            <span class="dim small">{{ step.percent }}%</span>
          </li>
        </ol>
      </div>
    </section>

    <section class="week card" aria-labelledby="week-title" data-week-plan>
      <div class="next-head row">
        <h3 id="week-title" class="panel-title">这一周怎么练</h3>
        <span class="spacer" />
        <span class="chip tiny dim" data-week-readonly>推演计划 · 不写进度</span>
      </div>
      <p class="muted small">
        把上面的推荐往后滚 {{ weekPlan.stats.days }} 天：假设每天照着练一场
        （{{ SESSION_MINUTES }} 分钟上下、五道题），练到过线的技能就从后面几天里退场，
        被它挡着的新技能补上来。所以这不是把今天的建议抄七遍。
      </p>
      <p class="muted small" data-week-projected-note>
        百分比里「预计」的那一半是推演出来的，不是成绩：孩子练没练、练成什么样，
        仍旧只看玩法页记下的那份进度。这一页照旧一个字节都不写。
      </p>

      <div class="week-reasons">
        <span
          v-for="reason in weekPlan.stats.byReason"
          :key="reason.id"
          class="chip tiny"
          :data-week-reason-chip="reason.id"
          :title="reason.hint"
        >
          {{ reason.label }} {{ reason.count }} 个
        </span>
      </div>

      <ol class="week-list">
        <li
          v-for="day in weekPlan.days"
          :key="day.dateKey"
          class="week-day"
          :class="{ today: day.today, rest: day.rest }"
          :data-week-day="day.day"
          :data-week-date="day.dateKey"
          :data-week-rest="day.rest ? '1' : '0'"
        >
          <div class="day-head">
            <strong>{{ day.label }}</strong>
            <span class="dim small">{{ day.weekday }} · {{ day.dateKey }}</span>
            <span class="spacer" />
            <span v-if="!day.rest" class="dim small">约 {{ day.minutes }} 分钟</span>
          </div>

          <p v-if="day.rest" class="dim small">{{ day.note }}</p>

          <div
            v-for="skill in day.skills"
            :key="skill.id"
            class="week-skill"
            :data-week-skill="skill.id"
            :data-week-reason="skill.reason"
          >
            <span class="node-emoji" aria-hidden="true">{{ skill.emoji }}</span>
            <div class="week-titles">
              <strong>
                {{ skill.name }}
                <em class="reason" :class="skill.reason" :title="skill.reasonHint">
                  {{ skill.reasonLabel }}
                </em>
              </strong>
              <span class="dim small">{{ skill.moduleName }} · {{ skill.why }}</span>
              <span class="dim small" :data-week-projected="skill.projectedPercent">
                {{ skill.percent }}% → 预计 {{ skill.projectedPercent }}%
                <em v-if="skill.willPass" class="pass" data-week-pass>预计这天过线</em>
              </span>
            </div>
            <RouterLink
              v-if="day.today"
              class="btn btn--primary btn--sm"
              :to="skill.entry.to"
              :data-week-entry="skill.entry.kind"
              :data-week-entry-skill="skill.id"
              @click="adoptWeekSkill(skill)"
            >
              {{ skill.entry.label }} →
            </RouterLink>
            <span v-else class="dim small week-later">到那天去{{ skill.moduleName }}练</span>
          </div>
        </li>
      </ol>

      <p class="muted small" data-week-summary>
        整周 {{ weekPlan.stats.sessions }} 场 · {{ weekPlan.stats.skills }} 个技能 ·
        约 {{ weekPlan.stats.minutes }} 分钟，照着练预计有
        {{ weekPlan.stats.passing }} 个能过线。家长中心能看到这份计划的推荐理由和采纳痕迹。
      </p>
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

.node.reco {
  border-color: rgba(94, 231, 255, 0.75);
  box-shadow: 0 0 0 1px rgba(94, 231, 255, 0.28);
}

.node-reco {
  position: absolute;
  top: -7px;
  left: -7px;
  width: 18px;
  height: 18px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: var(--brand);
  color: #071021;
  font-size: 11px;
  font-weight: 900;
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

.next-head {
  display: flex;
  align-items: center;
  gap: 10px;
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
  flex-wrap: wrap;
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

.next-actions {
  flex: none;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  justify-content: flex-end;
}

.reco-no {
  flex: none;
  width: 20px;
  height: 20px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: rgba(94, 231, 255, 0.16);
  color: var(--brand);
  font-size: 12px;
  font-weight: 900;
}

.reason {
  margin-left: 6px;
  padding: 1px 7px;
  border-radius: 999px;
  font-style: normal;
  font-size: 11px;
  font-weight: 800;
  border: 1px solid currentcolor;
  color: var(--text-soft);
}

.reason.finish {
  color: #ffce4d;
}

.reason.base {
  color: #55e6a5;
}

.reason.focus {
  color: #5ee7ff;
}

.reason.ahead {
  color: #9b8cff;
}

.reco-path {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed rgba(255, 255, 255, 0.12);
}

.path-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px;
}

.path-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
  padding: 0;
  list-style: none;
}

.path-step {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  font-size: 12px;
}

.path-step.learning {
  border-color: rgba(255, 206, 77, 0.5);
}

.path-step.ready {
  border-color: rgba(94, 231, 255, 0.5);
}

.step-no {
  width: 16px;
  height: 16px;
  display: grid;
  place-items: center;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  font-size: 10px;
  font-weight: 900;
}

/* ---------- 周计划 ---------- */

.week-reasons {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.week-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
  padding: 0;
  list-style: none;
}

.week-day {
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.04);
}

.week-day.today {
  border-color: rgba(94, 231, 255, 0.45);
}

.week-day.rest {
  border-style: dashed;
}

.day-head {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px;
}

.week-skill {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed rgba(255, 255, 255, 0.1);
}

.week-titles {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.week-later {
  flex: none;
}

.pass {
  margin-left: 6px;
  font-style: normal;
  font-weight: 800;
  color: #55e6a5;
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
