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
import { AGE_BAND_MODULES, bandOf } from '@/data/age-band.js'
import { MODULES } from '@/data/modules.js'
import { SKILLS } from '@/data/curriculum.js'
import { ERROR_TAGS, errorTagInfo } from '@/data/errorTags.js'
import { buildWeekPlan, weekPlanAdoption } from '@/data/week-plan.js'
import { MASTERY_THRESHOLD } from '@/utils/mastery.js'
import { useProgressStore } from '@/stores/progress.js'
import { AGE_BANDS, THEMES, useSettingsStore } from '@/stores/settings.js'
import { useWeeklyReport } from '@/composables/useWeeklyReport.js'
import { sound } from '@/utils/sound'
import OpenMojiAttribution from '@shared/components/OpenMojiAttribution.vue'

const progress = useProgressStore()
const settings = useSettingsStore()

/* ---------------- 本周一句话 ----------------
 *
 * 下面的雷达和错因表能回答「练了多少、错在哪」，回答不了「所以这周该练什么」。
 * 周报就补这一句：一个弱项 + 最多三条能直接点过去的练习，本机现算，不联网。
 */
const weeklyReport = useWeeklyReport()

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

/* ---------------- 难度档 ---------------- */

/** 选中的档位在六个玩法里各自对应什么默认难度，改档后立刻跟着变。 */
const bandPreview = computed(() => {
  const band = bandOf(settings.ageBand)
  return AGE_BAND_MODULES.map((m) => ({ ...m, hint: band.hints[m.key] }))
})

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

/* ---------------- 推荐理由与采纳痕迹 ---------------- */

/**
 * 家长侧看的是同一份周计划（data/week-plan.js），只是问题不一样：
 * 孩子那边问「今天练什么」，家长这边问「凭什么推荐它、孩子到底练没练」。
 *
 * 两段都只读：计划是按当前存档现算的推演，痕迹是把存档里已有的记录
 * （掌握度、错题欠账、星球最近游玩时间）按计划里的技能点重排一遍。
 * 家长中心不替孩子预约功课，也不为了统计多记一笔数据。
 */
const weekPlan = computed(() =>
  buildWeekPlan({
    mastery: progress.state.mastery,
    ageBand: settings.ageBand,
    wrongBook: progress.state.wrongBook,
  }),
)

const adoption = computed(() =>
  weekPlanAdoption(weekPlan.value, {
    mastery: progress.state.mastery,
    wrongBook: progress.state.wrongBook,
    modules: progress.state.modules,
  }),
)

const recoMetrics = computed(() => progress.recommendationMetrics)
const recoTrend = computed(() => progress.recommendationTrend.slice(-8))
const recoMetricStatus = computed(
  () =>
    ({
      insufficient: '样本积累中',
      positive: '达到正向阈值',
      watch: '继续观察',
      negative: '低于预警线',
    })[recoMetrics.value.status] ?? '继续观察',
)

function signedLift(value) {
  return `${value > 0 ? '+' : ''}${value}pp`
}

function lastPlayedText(at) {
  if (!at) return '还没玩过'
  const days = Math.floor((Date.now() - at) / 864e5)
  if (days <= 0) return '今天玩过'
  return days === 1 ? '昨天玩过' : `${days} 天前玩过`
}

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

function setTheme(theme) {
  settings.set('theme', theme)
  sound.click()
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

      <!-- 本周弱项一句话 + 建议练习 -->
      <section
        class="panel stack weekly"
        data-weekly-report
        :data-weakness="weeklyReport.weakness.id"
      >
        <h3 class="panel-title">🗞️ 本周一句话（{{ weeklyReport.range }}）</h3>
        <p class="weekly-headline" data-weekly-headline>{{ weeklyReport.headline }}</p>
        <p class="muted note">
          这周来了 {{ weeklyReport.week.activeDays }} 天 ·
          共 {{ weeklyReport.week.minutes }} 分钟 ·
          做了 {{ weeklyReport.week.answered }} 道题 ·
          弱项判定：{{ weeklyReport.weakness.label }}
        </p>

        <h4 class="sub-title">这周建议练这 {{ weeklyReport.drills.length }} 件事</h4>
        <ol class="weekly-drills">
          <li v-for="drill in weeklyReport.drills" :key="drill.id" class="weekly-drill">
            <RouterLink class="weekly-go" :to="drill.to">
              <strong>{{ drill.title }}</strong>
              <small class="muted">{{ drill.why }}</small>
              <span class="chip">
                {{ drill.minutes > 0 ? `约 ${drill.minutes} 分钟` : '只是一个约定' }}
              </span>
            </RouterLink>
          </li>
        </ol>
        <p class="muted note">
          这段话是按本机存档现算的：没有联网，也没有拿别的孩子做对比。
          不认同判断就直接看下面的雷达和错因表，那才是原始记录。
        </p>
      </section>

      <!-- 共享主题 -->
      <section class="panel stack">
        <h3 class="panel-title">🎨 显示主题</h3>
        <p class="muted note">主题由双 App 共用的 design tokens 驱动，选择会保存在本机。</p>
        <div class="themes" role="group" aria-label="显示主题">
          <button
            v-for="theme in THEMES"
            :key="theme.id"
            class="theme-option"
            :class="{ on: settings.theme === theme.id }"
            type="button"
            :aria-pressed="settings.theme === theme.id"
            @click="setTheme(theme.id)"
          >
            <span class="theme-emoji" aria-hidden="true">{{ theme.emoji }}</span>
            <span>
              <strong>{{ theme.name }}</strong>
              <small class="muted">{{ theme.desc }}</small>
            </span>
          </button>
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

        <ul class="band-preview" aria-label="当前年龄档在各玩法里的默认难度">
          <li v-for="m in bandPreview" :key="m.key">
            <span class="muted">{{ m.name }}</span>
            <strong>{{ m.hint }}</strong>
          </li>
        </ul>
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

      <!-- 推荐理由与采纳痕迹 -->
      <section class="panel stack" data-parent-reco>
        <h3 class="panel-title">📅 推荐理由与采纳痕迹</h3>
        <p class="muted note">
          技能图谱按孩子当前的掌握度排出这一周的练习计划：{{ weekPlan.stats.days }} 天
          {{ weekPlan.stats.sessions }} 场，涉及 {{ weekPlan.stats.skills }} 个技能点。
          下面先说「凭什么推荐它们」，再说这些技能点在存档里留下了什么痕迹。
        </p>

        <div
          class="reco-metric-grid"
          data-reco-metrics
          :data-adoption-rate="recoMetrics.adoptionRate"
          :data-reco-lift="recoMetrics.recoLift"
          :data-reco-status="recoMetrics.status"
        >
          <div class="cell">
            <strong>{{ recoMetrics.adoptionRate }}%</strong>
            <span class="muted">推荐采纳率</span>
          </div>
          <div class="cell">
            <strong>{{ recoMetrics.recoLift > 0 ? '+' : '' }}{{ recoMetrics.recoLift }}pp</strong>
            <span class="muted">推荐相对提升</span>
          </div>
          <div class="cell">
            <strong>{{ recoMetricStatus }}</strong>
            <span class="muted">
              {{ recoMetrics.adoptions }} 次采纳 / {{ recoMetrics.controls }} 个对照
            </span>
          </div>
        </div>
        <p class="muted note" data-reco-metric-definition>
          准实验 lift = 被采纳技能的掌握度变化 − 同批未采纳技能的变化；至少
          {{ recoMetrics.thresholds.minAdoptions }} 次采纳和
          {{ recoMetrics.thresholds.minControls }} 个对照后才判读。它受孩子自选择与对照串线影响，
          只表示关联，不能当作个人因果证明；该字段会随“导出进度”写入 recommendationEffect。
        </p>

        <div
          v-if="recoTrend.length"
          class="reco-trend"
          data-reco-trend
          :data-trend-points="recoTrend.length"
        >
          <h4 class="sub-title">近 {{ recoTrend.length }} 个记录日的采纳 / lift 趋势</h4>
          <ol class="reco-trend-list">
            <li
              v-for="point in recoTrend"
              :key="point.date"
              class="reco-trend-point"
              data-reco-trend-point
              :data-reco-trend-date="point.date"
              :data-reco-trend-adoption-rate="point.adoptionRate"
              :data-reco-trend-lift="point.recoLift"
            >
              <time :datetime="point.date">{{ point.date.slice(5) }}</time>
              <strong>采纳 {{ point.adoptionRate }}%</strong>
              <strong :class="{ negative: point.recoLift < 0 }">
                lift {{ signedLift(point.recoLift) }}
              </strong>
              <span class="muted">{{ point.adoptions }} 采纳 / {{ point.controls }} 对照</span>
            </li>
          </ol>
          <p class="muted note">
            每个自然日冻结一条读数，同日练习覆盖当天点；趋势随导出写入
            recommendationTrend，历史日期不会被今天的掌握度改写。
          </p>
        </div>

        <template v-if="adoption.total">
          <h4 class="sub-title">凭什么推荐这些</h4>
          <ul class="reasons">
            <li
              v-for="reason in adoption.byReason"
              :key="reason.id"
              class="reason-row"
              :data-reco-reason-row="reason.id"
            >
              <div class="row-head">
                <strong>{{ reason.label }}</strong>
                <span class="chip">{{ reason.count }} 个技能 · {{ reason.sessions }} 场</span>
              </div>
              <p class="muted row-tip">{{ reason.hint }}</p>
              <p class="muted row-tip">{{ reason.skills.join('、') }}</p>
            </li>
          </ul>

          <h4 class="sub-title">采纳痕迹</h4>
          <p class="muted note" data-adoption-summary>
            计划里的 {{ adoption.total }} 个技能点，{{ adoption.touched }} 个在存档里查得到记录
            （{{ adoption.touchedPercent }}%）：已过线 {{ adoption.passed }}、练过
            {{ adoption.practiced }}、欠着错题 {{ adoption.owed }}、还没开练
            {{ adoption.untouched }}。
          </p>
          <p class="muted note">
            这是周计划痕迹，不是推荐点击、更不是因果：这里只能看出计划里的技能点动没动过——
            可能是照着练的，也可能是孩子自己逛到那颗星球上去了。
          </p>
          <ul class="adoption">
            <li
              v-for="row in adoption.rows"
              :key="row.id"
              class="adoption-row"
              :data-adoption-row="row.id"
              :data-adoption-state="row.state"
            >
              <div class="row-head">
                <strong>{{ row.emoji }} {{ row.name }}</strong>
                <span class="chip" :class="row.state">{{ row.stateLabel }}</span>
              </div>
              <p class="muted row-tip">
                第 {{ row.days.join('、') }} 天安排 · {{ row.reasonLabel }}：{{ row.why }}
              </p>
              <p class="muted row-tip">
                {{ row.trace }} · {{ row.moduleName }}{{ lastPlayedText(row.lastPlayedAt) }}
              </p>
            </li>
          </ul>
        </template>
        <p v-else class="muted">
          图上该练的技能点都过线了，这周没有需要安排的新功课，复习和自由练都行。
        </p>

        <RouterLink to="/skill-graph" class="btn btn-ghost">🕸️ 看看完整周计划</RouterLink>
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
        <RouterLink to="/skill-graph" class="btn btn-ghost">🕸️ 打开技能图谱</RouterLink>
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

/* ---- 本周一句话 ---- */

.weekly-headline {
  padding: 12px 16px;
  border-radius: var(--radius-sm);
  background: rgba(94, 231, 255, 0.12);
  border-left: 4px solid var(--brand);
  font-size: 15px;
  font-weight: 700;
  line-height: 1.8;
}

.weekly-drills {
  display: flex;
  flex-direction: column;
  gap: 8px;
  counter-reset: drill;
}

.weekly-drill {
  counter-increment: drill;
}

.weekly-go {
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-areas: 'no title' 'no why' 'no time';
  gap: 2px 12px;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.weekly-go::before {
  grid-area: no;
  align-self: center;
  content: counter(drill);
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--brand);
  color: #05213a;
  font-weight: 900;
}

.weekly-go strong {
  grid-area: title;
  font-size: 15px;
}

.weekly-go small {
  grid-area: why;
  font-size: 12px;
  line-height: 1.6;
}

.weekly-go .chip {
  grid-area: time;
  justify-self: start;
  margin-top: 4px;
  font-size: 11px;
}

.weekly-go:hover,
.weekly-go:focus-visible {
  border-color: var(--brand);
}

.themes {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 8px;
}

.theme-option {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: var(--tap-min);
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  background: var(--surface-sunken);
  border: 2px solid transparent;
  text-align: left;
}

.theme-option.on {
  border-color: var(--brand);
  background: var(--brand-soft);
}

.theme-option > span:last-child {
  display: flex;
  flex-direction: column;
}

.theme-option small {
  font-size: 12px;
}

.theme-emoji {
  font-size: 24px;
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

.band-preview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 6px 14px;
  list-style: none;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  background: rgba(94, 231, 255, 0.07);
  border: 1px solid rgba(94, 231, 255, 0.22);
}

.band-preview li {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 13px;
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

/* ---- 推荐理由与采纳痕迹 ---- */

.reasons,
.adoption {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.reco-metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 8px;
}

.reco-trend {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.reco-trend-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 8px;
}

.reco-trend-point {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid rgba(96, 214, 255, 0.24);
  background: rgba(96, 214, 255, 0.07);
}

.reco-trend-point time,
.reco-trend-point span {
  font-size: 12px;
}

.reco-trend-point strong {
  font-size: 14px;
  color: #55e6a5;
}

.reco-trend-point strong.negative {
  color: #ff8f8f;
}

.reason-row,
.adoption-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
}

.row-head {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.row-head strong {
  font-size: 15px;
}

.row-tip {
  font-size: 13px;
  line-height: 1.6;
}

.chip.passed {
  border-color: rgba(85, 230, 165, 0.5);
  color: #55e6a5;
}

.chip.owed {
  border-color: rgba(255, 120, 120, 0.5);
  color: #ff8f8f;
}

.chip.practiced {
  border-color: rgba(255, 206, 77, 0.5);
  color: #ffce4d;
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
