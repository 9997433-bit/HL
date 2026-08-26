<script setup>
/**
 * 家长中心 —— 对标识字 App 的 ParentView：
 * 口算门挡住孩子，进门后是技能雷达、错因统计、时长提醒和整档 JSON 备份。
 *
 * 这一页只读 store 里已有的数据，不自己再算一套统计口径：
 * 掌握度来自 curriculum 技能点，错因来自判题时打的 errorTags，
 * 时长来自 App 每 15 秒一次的在线采样。
 */
import { computed, ref } from 'vue'
import { MODULES } from '@/data/modules.js'
import { SKILLS } from '@/data/curriculum.js'
import { ERROR_TAGS, errorTagInfo } from '@/data/errorTags.js'
import { MASTERY_THRESHOLD } from '@/utils/mastery.js'
import { useProgressStore } from '@/stores/progress.js'
import { AGE_BANDS, useSettingsStore } from '@/stores/settings.js'
import { sound } from '@/utils/sound'
import OpenMojiAttribution from '@shared/components/OpenMojiAttribution.vue'

const progress = useProgressStore()
const settings = useSettingsStore()

/* ---------------- 口算门：一道两位数加法，挡住小朋友即可 ---------------- */

const unlocked = ref(false)
const answer = ref('')
const gateError = ref('')

function makeGateQuiz() {
  const a = 11 + Math.floor(Math.random() * 78)
  const b = 11 + Math.floor(Math.random() * 78)
  return { a, b, sum: a + b }
}

const quiz = ref(makeGateQuiz())

function submitGate() {
  if (Number(answer.value) === quiz.value.sum) {
    unlocked.value = true
    gateError.value = ''
    return
  }
  gateError.value = '答案不对，再算一次～'
  answer.value = ''
  quiz.value = makeGateQuiz()
}

/* ---------------- 时长提醒 ---------------- */

const week = computed(() => progress.last7Days)
const maxMinutes = computed(() => Math.max(5, ...week.value.map((d) => d.minutes)))

const limit = computed(() => settings.dailyLimitMinutes)

const usageRatio = computed(() =>
  limit.value > 0 ? Math.min(1, progress.todayMinutes / limit.value) : 0,
)

const usageState = computed(() => {
  if (limit.value <= 0) return { tone: 'off', text: '当前没有限制每日时长。' }
  const left = limit.value - progress.todayMinutes
  if (left <= 0) {
    return {
      tone: 'over',
      text: `今天已经用了 ${progress.todayMinutes} 分钟，超出建议时长 ${-left} 分钟，该休息了。`,
    }
  }
  if (left <= 5) {
    return { tone: 'near', text: `今天还剩 ${left} 分钟就到建议时长了。` }
  }
  return { tone: 'ok', text: `今天已用 ${progress.todayMinutes} 分钟，还剩 ${left} 分钟。` }
})

/* ---------------- 技能雷达 ---------------- */

const RADAR = { size: 240, center: 120, radius: 88 }

/** 玩法星球按 curriculum 模块 id 归位，雷达的每根轴对应一个星球。 */
const axes = computed(() =>
  MODULES.map((m) => {
    const skills = SKILLS.filter((s) => s.module === m.curriculumId)
    const total = skills.reduce((sum, s) => sum + (progress.mastery[s.id] ?? 0), 0)
    const value = skills.length ? total / skills.length : 0
    return {
      id: m.id,
      name: m.name,
      route: m.route,
      color: m.color,
      value,
      percent: Math.round(value * 100),
      practiced: skills.filter((s) => progress.mastery[s.id] !== undefined).length,
      mastered: skills.filter((s) => (progress.mastery[s.id] ?? 0) >= MASTERY_THRESHOLD).length,
      total: skills.length,
    }
  }),
)

/** 第 i 根轴上距离圆心 ratio 的点，从正上方开始顺时针排。 */
function radarPoint(index, ratio) {
  const angle = (Math.PI * 2 * index) / axes.value.length - Math.PI / 2
  return {
    x: RADAR.center + Math.cos(angle) * RADAR.radius * ratio,
    y: RADAR.center + Math.sin(angle) * RADAR.radius * ratio,
  }
}

const toPoints = (ratioOf) =>
  axes.value
    .map((axis, i) => {
      const p = radarPoint(i, ratioOf(axis))
      return `${p.x.toFixed(1)},${p.y.toFixed(1)}`
    })
    .join(' ')

const radarRings = computed(() => [0.25, 0.5, 0.75, 1].map((r) => toPoints(() => r)))
const radarShape = computed(() => toPoints((axis) => Math.max(0.03, axis.value)))
const radarSpokes = computed(() =>
  axes.value.map((axis, i) => ({ id: axis.id, ...radarPoint(i, 1) })),
)
const radarLabels = computed(() =>
  axes.value.map((axis, i) => {
    const p = radarPoint(i, 1.16)
    return {
      id: axis.id,
      name: axis.name,
      percent: axis.percent,
      x: p.x,
      y: p.y,
      anchor: p.x > RADAR.center + 6 ? 'start' : p.x < RADAR.center - 6 ? 'end' : 'middle',
    }
  }),
)

const radarSummary = computed(
  () => `技能雷达：${axes.value.map((a) => `${a.name} ${a.percent}%`).join('，')}`,
)

/** 练过但还没达标的技能点，家长照着这张单子安排复习。 */
const weakSkills = computed(() =>
  SKILLS.map((s) => ({ ...s, value: progress.mastery[s.id] }))
    .filter((s) => s.value !== undefined && s.value < MASTERY_THRESHOLD)
    .sort((a, b) => a.value - b.value)
    .slice(0, 8)
    .map((s) => ({
      ...s,
      percent: Math.round(s.value * 100),
      route: MODULES.find((m) => m.curriculumId === s.module)?.route ?? '/',
    })),
)

/* ---------------- 错因统计 ---------------- */

const errorRows = computed(() => {
  const entries = Object.entries(progress.errorTagCounts).filter(([, n]) => n > 0)
  const max = Math.max(1, ...entries.map(([, n]) => n))
  const sum = entries.reduce((total, [, n]) => total + n, 0)
  return entries
    .sort((a, b) => b[1] - a[1])
    .map(([id, count]) => ({
      id,
      count,
      ...errorTagInfo(id),
      width: Math.round((count / max) * 100),
      share: Math.round((count / sum) * 100),
    }))
})

const errorTotal = computed(() => errorRows.value.reduce((sum, row) => sum + row.count, 0))

/* ---------------- 数据管理 ---------------- */

const notice = ref('')
const importError = ref('')
const confirmReset = ref(false)

function flash(message) {
  notice.value = message
  setTimeout(() => {
    if (notice.value === message) notice.value = ''
  }, 4000)
}

function exportData() {
  sound.click()
  const blob = new Blob([progress.exportJson()], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `星际数学冒险-进度-${new Date().toISOString().slice(0, 10)}.json`
  link.click()
  URL.revokeObjectURL(url)
  flash('进度已导出为 JSON 文件，可以拷到别的设备再导入。')
}

async function importData(event) {
  const file = event.target.files?.[0]
  if (!file) return
  importError.value = ''
  try {
    const result = progress.importJson(await file.text())
    flash(`已导入：${result.answered} 道题、${result.stars} 颗星、${result.skills} 个技能点。`)
  } catch (error) {
    importError.value = `导入失败：${error.message}`
  } finally {
    event.target.value = ''
  }
}

function resetAll() {
  progress.resetAll()
  confirmReset.value = false
  flash('学习记录已清空。')
}

function resetSettings() {
  settings.reset()
  flash('设置已恢复默认。')
}

function setLimit(value) {
  settings.set('dailyLimitMinutes', Number(value))
}
</script>

<template>
  <main class="page stack">
    <!-- 口算门 -->
    <section v-if="!unlocked" class="panel gate">
      <span class="gate-emoji" aria-hidden="true">🔐</span>
      <h2 class="gate-title">家长中心</h2>
      <p class="muted gate-desc">
        这里是学习报告和使用设置。为了不让小朋友自己改，先算一道两位数加法。
      </p>
      <form class="gate-form" @submit.prevent="submitGate">
        <label class="gate-q" for="parent-gate">{{ quiz.a }} + {{ quiz.b }} = ?</label>
        <input
          id="parent-gate"
          v-model="answer"
          class="gate-input"
          type="number"
          inputmode="numeric"
          autocomplete="off"
          placeholder="输入答案"
        />
        <button class="btn btn-primary btn-lg" type="submit">进入家长中心</button>
      </form>
      <p v-if="gateError" class="err" role="alert">{{ gateError }}</p>
      <RouterLink to="/" class="btn btn-ghost btn-sm">🗺️ 回到学习地图</RouterLink>
    </section>

    <template v-else>
      <p class="notice" role="status" aria-live="polite">{{ notice }}</p>

      <!-- 总览 -->
      <section class="panel">
        <h2 class="panel-title">👨‍👩‍👧 {{ progress.state.pilotName }} 的学习报告</h2>
        <div class="cards">
          <div class="cell">
            <strong>{{ progress.todayMinutes }}</strong><span class="muted">今日学习时长(分)</span>
          </div>
          <div class="cell">
            <strong>{{ progress.totalMinutes }}</strong><span class="muted">累计学习时长(分)</span>
          </div>
          <div class="cell">
            <strong>{{ progress.state.totalAnswered }}</strong><span class="muted">累计题数</span>
          </div>
          <div class="cell">
            <strong>{{ progress.accuracy }}%</strong><span class="muted">正确率</span>
          </div>
          <div class="cell">
            <strong>{{ progress.masteredCount }}/{{ progress.totalSkills }}</strong>
            <span class="muted">技能达标</span>
          </div>
          <div class="cell">
            <strong>{{ progress.state.dailyStreak }}</strong><span class="muted">连续天数</span>
          </div>
        </div>
      </section>

      <!-- 时长提醒 -->
      <section class="panel stack">
        <h3 class="panel-title">⏱️ 时长提醒</h3>

        <p class="usage" :class="`usage-${usageState.tone}`">{{ usageState.text }}</p>

        <div v-if="limit > 0" class="bar" aria-hidden="true">
          <span class="bar-fill" :style="{ width: `${usageRatio * 100}%` }" />
        </div>

        <div class="chart">
          <div v-for="day in week" :key="day.key" class="chart-col">
            <span class="chart-num muted">{{ day.minutes || '' }}</span>
            <span class="chart-track">
              <span
                class="chart-bar"
                :style="{ height: `${Math.max(3, (day.minutes / maxMinutes) * 100)}%` }"
              />
            </span>
            <span class="chart-label muted">{{ day.label }}</span>
            <span class="chart-sub">{{ day.answered ? `${day.answered}题` : '—' }}</span>
          </div>
        </div>
        <p class="muted note">柱子高度是每天的使用分钟数，下面是当天答题数。</p>

        <div class="field">
          <label class="field-label" for="daily-limit">
            每日建议时长：{{ limit > 0 ? `${limit} 分钟` : '不限制' }}
          </label>
          <input
            id="daily-limit"
            class="range"
            type="range"
            min="0"
            max="60"
            step="5"
            :value="limit"
            @input="setLimit($event.target.value)"
          />
        </div>

        <ul class="toggles">
          <li>
            <label>
              <input
                type="checkbox"
                :checked="settings.breakReminder"
                @change="settings.set('breakReminder', $event.target.checked)"
              />
              <span>
                <strong>到点提醒休息</strong>
                <small class="muted">达到建议时长后弹出护眼提示，可以顺延 5 分钟</small>
              </span>
            </label>
          </li>
          <li>
            <label>
              <input
                type="checkbox"
                :checked="settings.eyeCare"
                @change="settings.set('eyeCare', $event.target.checked)"
              />
              <span>
                <strong>护眼模式</strong>
                <small class="muted">降低饱和度与蓝光，晚上用更舒服</small>
              </span>
            </label>
          </li>
          <li>
            <label>
              <input
                type="checkbox"
                :checked="settings.soundOn"
                @change="settings.set('soundOn', $event.target.checked)"
              />
              <span>
                <strong>音效</strong>
                <small class="muted">答对答错的提示音</small>
              </span>
            </label>
          </li>
          <li>
            <label>
              <input
                type="checkbox"
                :checked="settings.animations"
                @change="settings.set('animations', $event.target.checked)"
              />
              <span>
                <strong>动效</strong>
                <small class="muted">星星飞舞与放大动画，对动画敏感的孩子建议关掉</small>
              </span>
            </label>
          </li>
        </ul>
      </section>

      <!-- 难度档 -->
      <section class="panel stack">
        <h3 class="panel-title">🎚️ 难度与年龄档</h3>
        <p class="muted note">
          年龄档决定孩子进入各个玩法时的默认难度，玩的过程中他自己也能切档。
        </p>
        <div class="bands" role="group" aria-label="年龄档">
          <button
            v-for="band in AGE_BANDS"
            :key="band.id"
            class="band"
            :class="{ on: settings.ageBand === band.id }"
            type="button"
            :aria-pressed="settings.ageBand === band.id"
            @click="settings.set('ageBand', band.id)"
          >
            <strong>{{ band.name }}</strong>
            <small class="muted">{{ band.desc }}</small>
          </button>
        </div>
      </section>

      <!-- 技能雷达 -->
      <section class="panel stack">
        <h3 class="panel-title">🕸️ 技能雷达</h3>
        <p class="muted note">
          每根轴是一颗星球，长度是该星球下 {{ progress.totalSkills }} 个技能点的平均掌握度，
          掌握度 ≥ {{ Math.round(MASTERY_THRESHOLD * 100) }}% 记为达标。
        </p>

        <div class="radar-wrap">
          <svg
            class="radar"
            :viewBox="`0 0 ${RADAR.size} ${RADAR.size}`"
            role="img"
            :aria-label="radarSummary"
          >
            <polygon
              v-for="(ring, i) in radarRings"
              :key="`ring-${i}`"
              :points="ring"
              class="radar-ring"
            />
            <line
              v-for="spoke in radarSpokes"
              :key="spoke.id"
              class="radar-spoke"
              :x1="RADAR.center"
              :y1="RADAR.center"
              :x2="spoke.x"
              :y2="spoke.y"
            />
            <polygon :points="radarShape" class="radar-shape" />
            <text
              v-for="label in radarLabels"
              :key="`label-${label.id}`"
              class="radar-text"
              :x="label.x"
              :y="label.y"
              :text-anchor="label.anchor"
            >
              {{ label.name }} {{ label.percent }}%
            </text>
          </svg>

          <ul class="axis-list">
            <li v-for="axis in axes" :key="axis.id" class="axis-row">
              <RouterLink :to="axis.route" class="axis-name">{{ axis.name }}</RouterLink>
              <span class="axis-bar" aria-hidden="true">
                <span
                  class="axis-fill"
                  :style="{ width: `${axis.percent}%`, background: axis.color }"
                />
              </span>
              <span class="axis-num">{{ axis.percent }}%</span>
              <span class="muted axis-sub">达标 {{ axis.mastered }}/{{ axis.total }}</span>
            </li>
          </ul>
        </div>

        <h4 class="sub-title">需要加强的技能点</h4>
        <p v-if="!weakSkills.length" class="muted">
          练过的技能点都已达标，可以去挑战新的星球了。
        </p>
        <ul v-else class="weak">
          <li v-for="skill in weakSkills" :key="skill.id">
            <RouterLink :to="skill.route" class="weak-item">
              <strong>{{ skill.name }}</strong>
              <span class="muted">{{ skill.level }} · 掌握度 {{ skill.percent }}%</span>
            </RouterLink>
          </li>
        </ul>
      </section>

      <!-- 错因统计 -->
      <section class="panel stack">
        <h3 class="panel-title">🔍 错因统计</h3>
        <p v-if="!errorRows.length" class="muted">
          还没有记录到错题。答错时系统会自动归类到 {{ Object.keys(ERROR_TAGS).length }} 种错因里，
          这里会告诉你孩子最常卡在哪一步。
        </p>
        <template v-else>
          <p class="muted note">共 {{ errorTotal }} 次错误，按出现次数排序，附上对应的讲解思路。</p>
          <ul class="errors">
            <li v-for="row in errorRows" :key="row.id" class="error-row">
              <div class="error-head">
                <strong>{{ row.label }}</strong>
                <span class="chip">{{ row.count }} 次 · {{ row.share }}%</span>
              </div>
              <span class="bar" aria-hidden="true">
                <span class="bar-fill warm" :style="{ width: `${row.width}%` }" />
              </span>
              <p class="muted error-tip">{{ row.tip }}</p>
            </li>
          </ul>
        </template>
      </section>

      <!-- 数据管理 -->
      <section class="panel stack">
        <h3 class="panel-title">💾 进度备份</h3>
        <p class="muted">
          学习数据只存在这台设备的浏览器里，不会上传服务器。换设备时先导出 JSON，再在新设备导入。
        </p>
        <div class="actions">
          <button class="btn btn-ghost" type="button" @click="exportData">⬇️ 导出进度</button>
          <label class="btn btn-ghost file-btn">
            ⬆️ 导入进度
            <input
              class="sr-only"
              type="file"
              accept="application/json,.json"
              @change="importData"
            />
          </label>
          <button class="btn btn-ghost" type="button" @click="resetSettings">
            ♻️ 恢复默认设置
          </button>
          <button
            v-if="!confirmReset"
            class="btn btn-ghost danger"
            type="button"
            @click="confirmReset = true"
          >
            🗑️ 清空学习记录
          </button>
          <template v-else>
            <button class="btn btn-ghost" type="button" @click="confirmReset = false">取消</button>
            <button class="btn danger" type="button" @click="resetAll">确认清空</button>
          </template>
        </div>
        <p v-if="importError" class="err" role="alert">{{ importError }}</p>
      </section>

      <section class="panel stack">
        <h3 class="panel-title">🌱 给家长的建议</h3>
        <ul class="tips">
          <li>每天 10–20 分钟，短而频繁比周末补一次长时间更有效。</li>
          <li>错因统计里排第一的那一类，先用纸笔陪着讲一遍，再回来练同类题。</li>
          <li>雷达上最短的那根轴不必急着补满，先把已经练过、还差一点的技能点做到达标。</li>
          <li>屏幕时间结束后，让孩子把刚才最难的一道题讲给你听，比多做十道更管用。</li>
        </ul>
        <RouterLink to="/progress" class="btn btn-ghost">🏆 查看孩子的成就墙</RouterLink>
      </section>

      <OpenMojiAttribution />
    </template>
  </main>
</template>

<style scoped>
/* ---- 口算门 ---- */

.gate {
  width: min(430px, 100%);
  margin: 24px auto 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  text-align: center;
}

.gate-emoji {
  font-size: 44px;
  line-height: 1;
}

.gate-title {
  font-size: 24px;
  font-weight: 900;
}

.gate-desc {
  font-size: 14px;
  line-height: 1.7;
}

.gate-form {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 4px;
}

.gate-q {
  font-size: 26px;
  font-weight: 900;
}

.gate-input {
  width: 100%;
  min-height: 52px;
  padding: 0 16px;
  border-radius: var(--radius-sm);
  border: 1px solid rgba(255, 255, 255, 0.24);
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-strong);
  font-family: inherit;
  font-size: 18px;
  text-align: center;
  outline: none;
}

.gate-input:focus {
  border-color: var(--brand);
}

.err {
  color: var(--danger);
  font-weight: 800;
  font-size: 14px;
}

/* ---- 通用 ---- */

.notice {
  align-self: center;
  padding: 9px 20px;
  border-radius: 999px;
  background: rgba(85, 230, 165, 0.18);
  border: 1px solid rgba(85, 230, 165, 0.5);
  color: var(--success);
  font-weight: 800;
  font-size: 14px;
}

.notice:empty {
  display: none;
}

.note {
  font-size: 13px;
  line-height: 1.7;
}

.sub-title {
  font-size: 15px;
  font-weight: 800;
}

.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(96px, 1fr));
  gap: 10px;
  margin-top: 14px;
}

.cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 12px 6px;
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.cell strong {
  font-size: 21px;
  font-weight: 900;
}

.cell span {
  font-size: 12px;
}

.bar {
  display: block;
  height: 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  overflow: hidden;
}

.bar-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--brand), var(--accent));
  transition: width 0.5s ease;
}

.bar-fill.warm {
  background: linear-gradient(90deg, var(--star), var(--neon-orange));
}

/* ---- 时长 ---- */

.usage {
  padding: 12px 16px;
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  font-size: 14px;
  font-weight: 700;
  line-height: 1.6;
}

.usage-near {
  background: rgba(255, 206, 77, 0.14);
  border-color: rgba(255, 206, 77, 0.5);
}

.usage-over {
  background: rgba(255, 107, 125, 0.16);
  border-color: rgba(255, 107, 125, 0.55);
}

.chart {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  height: 156px;
}

.chart-col {
  flex: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
}

.chart-num {
  font-size: 12px;
  font-weight: 800;
  min-height: 1em;
}

.chart-track {
  flex: 1;
  width: 100%;
  max-width: 34px;
  display: flex;
  align-items: flex-end;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.chart-bar {
  width: 100%;
  border-radius: 8px;
  background: linear-gradient(180deg, var(--brand), var(--accent));
  transition: height 0.5s ease;
}

.chart-label {
  font-size: 12px;
}

.chart-sub {
  font-size: 11px;
  font-weight: 800;
  color: var(--star);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field-label {
  font-size: 14px;
  font-weight: 800;
}

.range {
  width: 100%;
  height: 34px;
  accent-color: var(--brand);
}

.toggles {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.toggles label {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  cursor: pointer;
}

.toggles input {
  width: 22px;
  height: 22px;
  flex: none;
  accent-color: var(--brand);
}

.toggles span {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.toggles strong {
  font-size: 15px;
}

.toggles small {
  font-size: 12px;
  line-height: 1.5;
}

/* ---- 年龄档 ---- */

.bands {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
  gap: 8px;
}

.band {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 12px 14px;
  text-align: left;
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  transition: border-color 0.14s ease, background 0.14s ease;
}

.band.on {
  border-color: var(--brand);
  background: rgba(94, 231, 255, 0.14);
}

.band strong {
  font-size: 15px;
}

.band small {
  font-size: 12px;
}

/* ---- 雷达 ---- */

.radar-wrap {
  display: flex;
  gap: 18px;
  align-items: center;
  flex-wrap: wrap;
}

.radar {
  width: 260px;
  max-width: 100%;
  flex: none;
}

.radar-ring {
  fill: none;
  stroke: rgba(255, 255, 255, 0.14);
  stroke-width: 1;
}

.radar-spoke {
  stroke: rgba(255, 255, 255, 0.14);
  stroke-width: 1;
}

.radar-shape {
  fill: rgba(94, 231, 255, 0.28);
  stroke: var(--brand);
  stroke-width: 2;
  stroke-linejoin: round;
}

.radar-text {
  fill: var(--text-strong);
  font-size: 10px;
  font-weight: 700;
}

.axis-list {
  flex: 1;
  min-width: 240px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.axis-row {
  display: grid;
  grid-template-columns: 84px 1fr 42px;
  align-items: center;
  gap: 8px;
}

.axis-name {
  font-size: 13px;
  font-weight: 800;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.axis-bar {
  height: 9px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  overflow: hidden;
}

.axis-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  transition: width 0.5s ease;
}

.axis-num {
  font-size: 13px;
  font-weight: 900;
  text-align: right;
}

.axis-sub {
  grid-column: 2 / -1;
  font-size: 11px;
  margin-top: -4px;
}

.weak {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.weak-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.weak-item strong {
  font-size: 14px;
}

.weak-item span {
  font-size: 12px;
}

/* ---- 错因 ---- */

.errors {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.error-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.error-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.error-head strong {
  font-size: 15px;
}

.error-tip {
  font-size: 13px;
  line-height: 1.6;
}

/* ---- 数据 ---- */

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.file-btn {
  cursor: pointer;
}

.danger {
  border-color: rgba(255, 107, 125, 0.6);
  color: var(--danger);
}

.tips {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 14px;
  line-height: 1.7;
}

.tips li {
  padding-left: 22px;
  position: relative;
}

.tips li::before {
  content: '🌟';
  position: absolute;
  left: 0;
  top: 0;
}

@media (max-width: 560px) {
  .axis-row {
    grid-template-columns: 76px 1fr 40px;
  }
}
</style>
