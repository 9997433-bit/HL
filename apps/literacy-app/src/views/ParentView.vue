<script setup>
/**
 * 家长中心：学习报告 + 使用设置 + 数据管理。
 *
 * 所有数字都来自本机 localStorage，页面上不做任何网络请求，
 * 「导出 / 导入」走的是文件下载与文件读取，方便换设备时手动搬家。
 */
import { computed, onMounted, ref } from 'vue'
import gsap from 'gsap'
import ProgressRing from '@/components/ProgressRing.vue'
import { UNITS } from '@/data/characters.js'
import { BOOKS } from '@/data/books.js'
import { IDIOMS } from '@/data/idioms.js'
import { RADICALS } from '@/data/radicals.js'
import { useProgressStore } from '@/stores/progress.js'
import { FONT_SCALES, THEMES, useSettingsStore } from '@/stores/settings.js'
import { sfx } from '@/utils/sfx.js'

const progress = useProgressStore()
const settings = useSettingsStore()

const chartRef = ref(null)
const fileRef = ref(null)
const notice = ref('')
const confirmingReset = ref(false)

const nameDraft = ref(settings.childName)

function flash(msg) {
  notice.value = msg
  setTimeout(() => {
    if (notice.value === msg) notice.value = ''
  }, 3000)
}

/* ------------------------------------------------------------------ 报告 */

const minutesToday = computed(() => Math.round(progress.todayStats.seconds / 60))

const summary = computed(() => [
  { emoji: '🈶', label: '认识的字', value: progress.learnedCount, unit: `/ ${progress.totalChars}` },
  { emoji: '🏆', label: '已掌握', value: progress.masteredCount, unit: '字' },
  { emoji: '⭐', label: '收集的星星', value: progress.stars, unit: '颗' },
  { emoji: '🔥', label: '连续学习', value: progress.streakDays, unit: '天' },
  { emoji: '⏱️', label: '今天用时', value: minutesToday.value, unit: '分钟' },
  { emoji: '🎧', label: '听音答对', value: progress.game.correct, unit: `/ ${progress.game.rounds || 0}` }
])

const days = computed(() => progress.recentDays)

/** 柱状图高度按当日分钟数归一化，至少留 4% 让「有来过」也看得见。 */
const maxMinutes = computed(() => Math.max(10, ...days.value.map((d) => d.minutes)))

function barHeight(d) {
  if (!d.minutes && !d.chars) return 0
  return Math.max(4, Math.round((d.minutes / maxMinutes.value) * 100))
}

const units = computed(() =>
  UNITS.map((u) => ({ ...u, stat: progress.unitProgress(u.id) }))
)

const contentStats = computed(() => [
  { emoji: '📖', label: '绘本读完', done: progress.booksFinished, total: BOOKS.length },
  { emoji: '🎭', label: '成语学过', done: progress.idiomsSeen, total: IDIOMS.length },
  { emoji: '🧩', label: '偏旁看过', done: progress.radicalsSeen, total: RADICALS.length }
])

const reviewChars = computed(() => progress.reviewQueue.slice(0, 12))

/* ------------------------------------------------------------------ 设置 */

function patch(key, value) {
  sfx.tap()
  settings.update({ [key]: value })
}

function saveName() {
  settings.update({ childName: nameDraft.value.trim().slice(0, 12) })
  flash('名字已保存 ✅')
}

/* -------------------------------------------------------------- 数据管理 */

function download() {
  sfx.tap()
  const blob = new Blob([progress.exportJson()], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `识字进度-${new Date().toISOString().slice(0, 10)}.json`
  a.click()
  URL.revokeObjectURL(url)
  flash('进度已导出到下载文件夹 📦')
}

async function onFile(event) {
  const file = event.target.files?.[0]
  if (!file) return
  const text = await file.text()
  event.target.value = ''
  if (progress.importJson(text)) {
    sfx.levelUp()
    flash('进度导入成功 🎉')
  } else {
    sfx.wrong()
    flash('这个文件读不懂，请选择本应用导出的 JSON ❌')
  }
}

function askReset() {
  sfx.tap()
  confirmingReset.value = true
}

function doReset() {
  progress.resetAll()
  settings.reset()
  nameDraft.value = ''
  confirmingReset.value = false
  flash('已清空全部学习数据')
}

onMounted(() => {
  if (settings.reduceMotion) return
  const bars = chartRef.value?.querySelectorAll('.chart__fill')
  if (!bars?.length) return
  gsap.from(bars, {
    scaleY: 0,
    transformOrigin: 'bottom center',
    duration: 0.5,
    ease: 'back.out(1.5)',
    stagger: 0.03
  })
})
</script>

<template>
  <div class="page">
    <section class="card card--flat intro">
      <div class="intro__text">
        <h2 class="section-title">
          <span class="section-title__emoji" aria-hidden="true">👨‍👩‍👧</span>
          家长中心
        </h2>
        <p class="muted">
          这里是给大人看的。所有数据只存在这台设备的浏览器里，不会上传到任何服务器。
        </p>
      </div>
      <ProgressRing
        :value="progress.overallPercent / 100"
        :size="86"
        :thickness="9"
        sublabel="总进度"
      />
    </section>

    <p v-if="notice" class="notice">{{ notice }}</p>

    <!-- 关键指标 -->
    <section class="stack">
      <h3 class="section-title">
        <span class="section-title__emoji" aria-hidden="true">📊</span>
        学习概览
      </h3>
      <div class="cards">
        <div v-for="s in summary" :key="s.label" class="stat card">
          <span class="stat__emoji" aria-hidden="true">{{ s.emoji }}</span>
          <strong class="stat__value">{{ s.value }}</strong>
          <span class="stat__unit muted">{{ s.unit }}</span>
          <span class="stat__label">{{ s.label }}</span>
        </div>
      </div>
    </section>

    <!-- 近两周曲线 -->
    <section class="card stack">
      <h3 class="section-title">
        <span class="section-title__emoji" aria-hidden="true">📈</span>
        最近 14 天
      </h3>
      <div ref="chartRef" class="chart">
        <div v-for="d in days" :key="d.key" class="chart__col">
          <span class="chart__track">
            <span
              class="chart__fill"
              :class="{ 'is-empty': !barHeight(d) }"
              :style="{ height: `${barHeight(d)}%` }"
              :title="`${d.label}：${d.minutes} 分钟，${d.chars} 个新字`"
            />
          </span>
          <small class="chart__day">{{ d.label.slice(-2) }}</small>
        </div>
      </div>
      <p class="muted chart__foot">柱子高度代表当天的学习时长，鼠标停在上面能看到明细。</p>
    </section>

    <!-- 单元掌握度 -->
    <section class="card stack">
      <h3 class="section-title">
        <span class="section-title__emoji" aria-hidden="true">🗂️</span>
        各单元掌握度
      </h3>
      <ul class="units">
        <li v-for="u in units" :key="u.id" class="unit">
          <span class="unit__emoji" aria-hidden="true">{{ u.emoji }}</span>
          <span class="unit__body">
            <strong>{{ u.name }}</strong>
            <span class="unit__bar">
              <span class="unit__fill" :style="{ width: `${u.stat.percent}%`, background: u.color }" />
            </span>
          </span>
          <span class="pill">{{ u.stat.done }} / {{ u.stat.total }}</span>
        </li>
      </ul>

      <div class="content-stats">
        <span v-for="c in contentStats" :key="c.label" class="pill pill--accent">
          {{ c.emoji }} {{ c.label }} {{ c.done }} / {{ c.total }}
        </span>
      </div>
    </section>

    <!-- 复习建议 -->
    <section v-if="reviewChars.length" class="card stack">
      <h3 class="section-title">
        <span class="section-title__emoji" aria-hidden="true">🔁</span>
        建议今天复习
      </h3>
      <p class="muted">这些字学过但还不牢固，陪孩子再读一遍效果最好。</p>
      <div class="review">
        <RouterLink
          v-for="ch in reviewChars"
          :key="ch"
          class="review__chip"
          :to="`/learn/${encodeURIComponent(ch)}`"
          @click="sfx.tap()"
        >
          {{ ch }}
        </RouterLink>
      </div>
    </section>

    <!-- 设置 -->
    <section class="card stack">
      <h3 class="section-title">
        <span class="section-title__emoji" aria-hidden="true">⚙️</span>
        使用设置
      </h3>

      <div class="field">
        <label class="field__label" for="child-name">孩子的名字</label>
        <div class="field__row">
          <input
            id="child-name"
            v-model="nameDraft"
            class="input"
            type="text"
            maxlength="12"
            placeholder="小朋友"
            @blur="saveName"
          />
          <button class="btn btn--ghost" type="button" @click="saveName">保存</button>
        </div>
      </div>

      <div class="field">
        <span class="field__label">主题</span>
        <div class="options">
          <button
            v-for="t in THEMES"
            :key="t.id"
            class="option"
            :class="{ 'is-on': settings.theme === t.id }"
            type="button"
            @click="(sfx.tap(), settings.setTheme(t.id))"
          >
            <span class="option__emoji" aria-hidden="true">{{ t.emoji }}</span>
            <strong>{{ t.name }}</strong>
            <small class="muted">{{ t.desc }}</small>
          </button>
        </div>
      </div>

      <div class="field">
        <span class="field__label">字号</span>
        <div class="options options--inline">
          <button
            v-for="f in FONT_SCALES"
            :key="f.id"
            class="option option--sm"
            :class="{ 'is-on': settings.fontScale === f.id }"
            type="button"
            @click="patch('fontScale', f.id)"
          >
            {{ f.name }}
          </button>
        </div>
      </div>

      <div class="field">
        <label class="field__label" for="rate">
          朗读语速 <span class="muted">（{{ settings.speechRate.toFixed(2) }}×）</span>
        </label>
        <input
          id="rate"
          class="range"
          type="range"
          min="0.5"
          max="1.2"
          step="0.05"
          :value="settings.speechRate"
          @input="settings.update({ speechRate: Number($event.target.value) })"
        />
      </div>

      <div class="field">
        <label class="field__label" for="limit">
          每日建议时长
          <span class="muted">（{{ settings.dailyLimitMinutes ? `${settings.dailyLimitMinutes} 分钟` : '不限制' }}）</span>
        </label>
        <input
          id="limit"
          class="range"
          type="range"
          min="0"
          max="60"
          step="5"
          :value="settings.dailyLimitMinutes"
          @input="settings.update({ dailyLimitMinutes: Number($event.target.value) })"
        />
      </div>

      <ul class="switches">
        <li v-for="s in [
          { key: 'soundOn', label: '音效', desc: '答题与点击的提示音' },
          { key: 'speechOn', label: '朗读', desc: '用系统语音读出汉字和句子' },
          { key: 'showPinyin', label: '显示拼音', desc: '关掉可以练习脱离拼音认字' },
          { key: 'reduceMotion', label: '减少动画', desc: '孩子容易分心时可以关掉动效' },
          { key: 'breakReminder', label: '休息提醒', desc: '达到建议时长后弹出护眼提示' }
        ]" :key="s.key" class="switch">
          <span class="switch__text">
            <strong>{{ s.label }}</strong>
            <small class="muted">{{ s.desc }}</small>
          </span>
          <button
            class="toggle"
            :class="{ 'is-on': settings[s.key] }"
            type="button"
            role="switch"
            :aria-checked="settings[s.key]"
            :aria-label="s.label"
            @click="patch(s.key, !settings[s.key])"
          >
            <span class="toggle__knob" />
          </button>
        </li>
      </ul>
    </section>

    <!-- 数据管理 -->
    <section class="card stack">
      <h3 class="section-title">
        <span class="section-title__emoji" aria-hidden="true">💾</span>
        数据管理
      </h3>
      <p class="muted">
        换新设备时，先在旧设备导出 JSON，再到新设备导入，学习进度就搬过去了。
      </p>
      <div class="danger-row">
        <button class="btn btn--ghost" type="button" @click="download">📦 导出进度</button>
        <button class="btn btn--ghost" type="button" @click="(sfx.tap(), fileRef?.click())">
          📥 导入进度
        </button>
        <input ref="fileRef" class="sr-only" type="file" accept="application/json,.json" @change="onFile" />
        <button v-if="!confirmingReset" class="btn btn--ghost danger" type="button" @click="askReset">
          🗑️ 清空数据
        </button>
      </div>

      <div v-if="confirmingReset" class="confirm">
        <p><strong>确定要清空吗？</strong>所有已学的字、星星和绘本记录都会消失，且无法恢复。</p>
        <div class="danger-row">
          <button class="btn btn--ghost" type="button" @click="confirmingReset = false">再想想</button>
          <button class="btn danger-solid" type="button" @click="doReset">确定清空</button>
        </div>
      </div>
    </section>

    <p class="muted foot">
      快乐识字 · 开源项目，无广告、无订阅、无数据上传 🌱
    </p>
  </div>
</template>

<style scoped>
.intro {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
}

.intro__text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.intro__text .muted {
  font-size: 0.88rem;
}

.notice {
  align-self: center;
  padding: 10px 22px;
  border-radius: var(--radius-pill);
  background: var(--success);
  color: #fff;
  font-weight: 800;
  box-shadow: var(--shadow-md);
  animation: pop-in var(--dur-mid) var(--ease-pop);
}

/* ---------------------------------------------------------- 概览卡片 */
.cards {
  display: grid;
  gap: var(--gap-sm);
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
}

.stat {
  display: grid;
  grid-template-columns: auto 1fr;
  grid-template-rows: auto auto;
  align-items: baseline;
  gap: 0 10px;
  padding: var(--gap-md);
}

.stat__emoji {
  grid-row: 1 / 3;
  align-self: center;
  font-size: 1.8rem;
  line-height: 1;
}

.stat__value {
  font-size: 1.6rem;
  font-weight: 800;
  color: var(--text-strong);
}

.stat__unit {
  font-size: 0.75rem;
  margin-left: -6px;
}

.stat__label {
  grid-column: 2;
  font-size: 0.82rem;
  color: var(--text-soft);
}

/* ---------------------------------------------------------- 柱状图 */
.chart {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 140px;
}

.chart__col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  height: 100%;
}

.chart__track {
  flex: 1;
  width: 100%;
  display: flex;
  align-items: flex-end;
  border-radius: var(--radius-sm);
  background: var(--surface-sunken);
  overflow: hidden;
}

.chart__fill {
  width: 100%;
  border-radius: var(--radius-sm);
  background: linear-gradient(180deg, var(--brand) 0%, var(--brand-strong) 100%);
}

.chart__fill.is-empty {
  background: transparent;
}

.chart__day {
  font-size: 0.65rem;
  color: var(--text-soft);
  white-space: nowrap;
}

.chart__foot {
  font-size: 0.78rem;
}

/* ---------------------------------------------------------- 单元 */
.units {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
}

.unit {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
}

.unit__emoji {
  font-size: 1.4rem;
  line-height: 1;
}

.unit__body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.unit__body strong {
  font-size: 0.92rem;
  color: var(--text-strong);
}

.unit__bar {
  height: 9px;
  border-radius: 5px;
  background: var(--stroke-hint);
  overflow: hidden;
}

.unit__fill {
  display: block;
  height: 100%;
  border-radius: 5px;
  transition: width var(--dur-slow) var(--ease-pop);
}

.content-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

/* ---------------------------------------------------------- 复习 */
.review {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.review__chip {
  display: grid;
  place-items: center;
  width: 54px;
  height: 54px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  border: 2px solid var(--surface-border);
  font-size: 1.5rem;
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', serif;
  color: var(--text-strong);
  transition: transform var(--dur-fast) var(--ease-pop);
}

.review__chip:active {
  transform: scale(0.94);
}

/* ---------------------------------------------------------- 设置 */
.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field__label {
  font-weight: 700;
  color: var(--text-strong);
  font-size: 0.92rem;
}

.field__row {
  display: flex;
  gap: var(--gap-sm);
}

.input {
  flex: 1;
  min-height: var(--tap-min);
  padding: 0 18px;
  border-radius: var(--radius-pill);
  background: var(--surface-sunken);
  border: 2px solid var(--surface-border);
}

.range {
  width: 100%;
  accent-color: var(--brand);
  height: 32px;
}

.options {
  display: grid;
  gap: var(--gap-sm);
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
}

.options--inline {
  grid-template-columns: repeat(auto-fit, minmax(70px, 1fr));
}

.option {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 12px 16px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  border: 2px solid transparent;
  text-align: left;
  transition: transform var(--dur-fast) var(--ease-pop), border-color var(--dur-fast) ease;
}

.option--sm {
  align-items: center;
  padding: 12px 10px;
  font-weight: 700;
}

.option:active {
  transform: scale(0.97);
}

.option.is-on {
  border-color: var(--brand);
  background: var(--brand-soft);
}

.option__emoji {
  font-size: 1.3rem;
  line-height: 1;
}

.option small {
  font-size: 0.75rem;
}

.switches {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.switch {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
  padding: 10px 0;
  border-bottom: 1px solid var(--surface-border);
}

.switch:last-child {
  border-bottom: none;
}

.switch__text {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.switch__text small {
  font-size: 0.76rem;
}

.toggle {
  flex: none;
  width: 58px;
  height: 34px;
  padding: 3px;
  border-radius: var(--radius-pill);
  background: var(--stroke-hint);
  transition: background var(--dur-fast) ease;
}

.toggle.is-on {
  background: var(--success);
}

.toggle__knob {
  display: block;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #fff;
  box-shadow: var(--shadow-sm);
  transition: transform var(--dur-fast) var(--ease-pop);
}

.toggle.is-on .toggle__knob {
  transform: translateX(24px);
}

/* ---------------------------------------------------------- 危险区 */
.danger-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--gap-sm);
}

.danger {
  color: var(--danger);
  border-color: color-mix(in srgb, var(--danger) 40%, transparent);
}

.danger-solid {
  background: var(--danger);
  color: #fff;
}

.confirm {
  padding: var(--gap-md);
  border-radius: var(--radius-md);
  background: color-mix(in srgb, var(--danger) 12%, transparent);
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
  font-size: 0.9rem;
}

.foot {
  text-align: center;
  font-size: 0.8rem;
}

@media (max-width: 560px) {
  .intro {
    flex-direction: column-reverse;
    align-items: stretch;
    text-align: center;
  }
  .intro .ring {
    align-self: center;
  }
}
</style>
