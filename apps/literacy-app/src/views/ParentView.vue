<script setup>
import { computed, ref } from 'vue'
import ProgressRing from '@/components/ProgressRing.vue'
import { FONT_SCALES, THEMES, useSettingsStore } from '@/stores/settings.js'
import { MASTERY_THRESHOLD, useProgressStore } from '@/stores/progress.js'
import { CHARACTERS, UNITS } from '@/data/characters.js'
import { BOOKS } from '@/data/books.js'
import { IDIOMS } from '@/data/idioms.js'
import { sfx } from '@/utils/sfx.js'

const progress = useProgressStore()
const settings = useSettingsStore()

/* ---------------- 家长验证：一道两位数加法，挡住小朋友即可 ---------------- */
const unlocked = ref(false)
const answer = ref('')
const gateError = ref('')
const quiz = ref(makeQuiz())

function makeQuiz() {
  const a = 11 + Math.floor(Math.random() * 78)
  const b = 11 + Math.floor(Math.random() * 78)
  return { a, b, sum: a + b }
}

function submitGate() {
  if (Number(answer.value) === quiz.value.sum) {
    unlocked.value = true
    gateError.value = ''
  } else {
    gateError.value = '答案不对，再算一次～'
    answer.value = ''
    quiz.value = makeQuiz()
  }
}

/* ---------------- 学习报告 ---------------- */
const week = computed(() => progress.last7Days)
const maxMinutes = computed(() =>
  Math.max(5, ...week.value.map((d) => Math.round(d.seconds / 60)))
)

const totalMinutes = computed(() =>
  Math.round(Object.values(progress.daily).reduce((n, d) => n + (d.seconds || 0), 0) / 60)
)

const unitRows = computed(() =>
  UNITS.map((u) => ({ ...u, ...progress.unitProgress(u.id) }))
)

/** 错得最多的字，给家长做针对性辅导用。 */
const weakChars = computed(() =>
  Object.entries(progress.chars)
    .map(([char, v]) => ({ char, ...v }))
    .filter((c) => (c.wrong || 0) > 0)
    .sort((a, b) => b.wrong - a.wrong || a.correct - b.correct)
    .slice(0, 12)
)

const accuracy = computed(() => {
  const c = Object.values(progress.chars).reduce((n, v) => n + (v.correct || 0), 0)
  const w = Object.values(progress.chars).reduce((n, v) => n + (v.wrong || 0), 0)
  return c + w ? Math.round((c / (c + w)) * 100) : 0
})

/* ---------------- 数据管理 ---------------- */
const importError = ref('')
const notice = ref('')

function flash(msg) {
  notice.value = msg
  setTimeout(() => {
    if (notice.value === msg) notice.value = ''
  }, 3000)
}

function exportData() {
  sfx.tap()
  const blob = new Blob([progress.exportJson()], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `识字进度-${new Date().toISOString().slice(0, 10)}.json`
  a.click()
  URL.revokeObjectURL(url)
  flash('进度已导出为 JSON 文件')
}

async function importData(event) {
  const file = event.target.files?.[0]
  if (!file) return
  importError.value = ''
  try {
    progress.importJson(await file.text())
    flash('进度已导入')
  } catch (err) {
    importError.value = `导入失败：${err.message}`
  } finally {
    event.target.value = ''
  }
}

function resetAll() {
  if (!window.confirm('确定要清空所有学习记录吗？此操作无法撤销。')) return
  progress.resetAll()
  flash('学习记录已清空')
}

function resetSettings() {
  settings.reset()
  flash('显示设置已恢复默认')
}
</script>

<template>
  <div class="page">
    <!-- 家长验证 -->
    <section v-if="!unlocked" class="gate card">
      <div class="gate__emoji" aria-hidden="true">🔐</div>
      <h2 class="gate__title">家长中心</h2>
      <p class="gate__desc muted">为了防止小朋友误改设置，请先回答一道算术题。</p>
      <form class="gate__form" @submit.prevent="submitGate">
        <label class="gate__q" for="gate-answer">
          {{ quiz.a }} + {{ quiz.b }} = ?
        </label>
        <input
          id="gate-answer"
          v-model="answer"
          class="gate__input"
          type="number"
          inputmode="numeric"
          autocomplete="off"
          placeholder="输入答案"
        />
        <button class="btn btn--primary btn--lg btn--block" type="submit">进入 →</button>
      </form>
      <p v-if="gateError" class="gate__err">{{ gateError }}</p>
    </section>

    <template v-else>
      <p v-if="notice" class="notice">{{ notice }}</p>

      <!-- 总览 -->
      <section class="card overview">
        <ProgressRing :percent="progress.overallPercent" :size="98" :stroke="10" label="识字进度" />
        <div class="overview__grid">
          <div><strong>{{ progress.learnedCount }}</strong><small>学过的字</small></div>
          <div><strong>{{ progress.masteredCount }}</strong><small>已掌握</small></div>
          <div><strong>{{ accuracy }}%</strong><small>作答正确率</small></div>
          <div><strong>{{ totalMinutes }}</strong><small>累计分钟</small></div>
          <div><strong>{{ progress.streakDays || 1 }}</strong><small>连续天数</small></div>
          <div><strong>{{ progress.stars }}</strong><small>获得星星</small></div>
        </div>
      </section>

      <!-- 近 7 天 -->
      <section class="card stack">
        <h3 class="section-title">
          <span class="section-title__emoji" aria-hidden="true">📊</span>
          最近 7 天
        </h3>
        <div class="chart">
          <div v-for="d in week" :key="d.key" class="chart__col">
            <span class="chart__value">{{ Math.round(d.seconds / 60) || '' }}</span>
            <span class="chart__track">
              <span
                class="chart__bar"
                :style="{ height: `${Math.max(3, (Math.round(d.seconds / 60) / maxMinutes) * 100)}%` }"
              />
            </span>
            <span class="chart__label">{{ d.label }}</span>
            <small class="chart__chars">{{ d.newChars ? `+${d.newChars}字` : '—' }}</small>
          </div>
        </div>
        <p class="muted chart__note">柱子高度是每天的学习分钟数，下面是当天新学的字数。</p>
      </section>

      <!-- 单元掌握情况 -->
      <section class="card stack">
        <h3 class="section-title">
          <span class="section-title__emoji" aria-hidden="true">📚</span>
          各单元进度
        </h3>
        <ul class="units">
          <li v-for="u in unitRows" :key="u.id" class="unitrow">
            <span class="unitrow__emoji" aria-hidden="true">{{ u.emoji }}</span>
            <span class="unitrow__name">{{ u.name }}</span>
            <span class="unitrow__bar">
              <span class="unitrow__fill" :style="{ width: `${u.percent}%`, background: u.color }" />
            </span>
            <span class="unitrow__num">{{ u.done }}/{{ u.total }}</span>
          </li>
        </ul>
        <div class="row">
          <span class="pill">📖 绘本 {{ progress.booksFinished }}/{{ BOOKS.length }}</span>
          <span class="pill">🎭 成语 {{ progress.idiomsSeen }}/{{ IDIOMS.length }}</span>
          <span class="pill">🎧 游戏 {{ progress.game.plays }} 题 · 正确率 {{ progress.gameAccuracy }}%</span>
        </div>
      </section>

      <!-- 需要加强 -->
      <section class="card stack">
        <h3 class="section-title">
          <span class="section-title__emoji" aria-hidden="true">🎯</span>
          建议加强的字
        </h3>
        <p v-if="!weakChars.length" class="muted">
          还没有出现答错的字。一个字答对 {{ MASTERY_THRESHOLD }} 次就算掌握。
        </p>
        <div v-else class="weak">
          <RouterLink
            v-for="c in weakChars"
            :key="c.char"
            class="weak__item"
            :to="`/learn/${encodeURIComponent(c.char)}`"
          >
            <span class="weak__char">{{ c.char }}</span>
            <small>对 {{ c.correct }} · 错 {{ c.wrong }}</small>
          </RouterLink>
        </div>
      </section>

      <!-- 使用设置 -->
      <section class="card stack">
        <h3 class="section-title">
          <span class="section-title__emoji" aria-hidden="true">⚙️</span>
          使用设置
        </h3>

        <div class="field">
          <label class="field__label" for="child-name">孩子的名字</label>
          <input
            id="child-name"
            class="field__input"
            type="text"
            maxlength="8"
            placeholder="例如：多多"
            :value="settings.childName"
            @input="settings.update({ childName: $event.target.value })"
          />
        </div>

        <div class="field">
          <span class="field__label">主题（护眼模式会降低蓝光与对比度）</span>
          <div class="opts">
            <button
              v-for="t in THEMES"
              :key="t.id"
              class="opt"
              :class="{ 'is-on': settings.theme === t.id }"
              type="button"
              @click="settings.setTheme(t.id)"
            >
              <span class="opt__emoji" aria-hidden="true">{{ t.emoji }}</span>
              <strong>{{ t.name }}</strong>
              <small>{{ t.desc }}</small>
            </button>
          </div>
        </div>

        <div class="field">
          <span class="field__label">字号</span>
          <div class="segmented">
            <button
              v-for="f in FONT_SCALES"
              :key="f.id"
              class="segmented__item"
              :class="{ 'is-on': settings.fontScale === f.id }"
              type="button"
              @click="settings.update({ fontScale: f.id })"
            >
              {{ f.name }}
            </button>
          </div>
        </div>

        <div class="field">
          <label class="field__label" for="rate">
            朗读语速：{{ settings.speechRate.toFixed(2) }} 倍
          </label>
          <input
            id="rate"
            class="field__range"
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
            每日建议时长：{{ settings.dailyLimitMinutes ? `${settings.dailyLimitMinutes} 分钟` : '不限制' }}
          </label>
          <input
            id="limit"
            class="field__range"
            type="range"
            min="0"
            max="60"
            step="5"
            :value="settings.dailyLimitMinutes"
            @input="settings.update({ dailyLimitMinutes: Number($event.target.value) })"
          />
        </div>

        <ul class="toggles">
          <li>
            <label>
              <input
                type="checkbox"
                :checked="settings.breakReminder"
                @change="settings.update({ breakReminder: $event.target.checked })"
              />
              <span><strong>到点提醒休息</strong><small>达到每日时长后弹出护眼提示</small></span>
            </label>
          </li>
          <li>
            <label>
              <input
                type="checkbox"
                :checked="settings.soundOn"
                @change="settings.update({ soundOn: $event.target.checked })"
              />
              <span><strong>音效</strong><small>答对答错的提示音</small></span>
            </label>
          </li>
          <li>
            <label>
              <input
                type="checkbox"
                :checked="settings.speechOn"
                @change="settings.update({ speechOn: $event.target.checked })"
              />
              <span><strong>自动朗读</strong><small>翻页和换幕时自动读出内容</small></span>
            </label>
          </li>
          <li>
            <label>
              <input
                type="checkbox"
                :checked="settings.showPinyin"
                @change="settings.update({ showPinyin: $event.target.checked })"
              />
              <span><strong>显示拼音</strong><small>关掉可以练习脱离拼音认字</small></span>
            </label>
          </li>
          <li>
            <label>
              <input
                type="checkbox"
                :checked="settings.reduceMotion"
                @change="settings.update({ reduceMotion: $event.target.checked })"
              />
              <span><strong>减少动画</strong><small>对动效敏感的孩子建议开启</small></span>
            </label>
          </li>
        </ul>
      </section>

      <!-- 数据 -->
      <section class="card stack">
        <h3 class="section-title">
          <span class="section-title__emoji" aria-hidden="true">💾</span>
          数据管理
        </h3>
        <p class="muted">
          学习数据只保存在这台设备的浏览器里（localStorage），不会上传到任何服务器。
          换设备时可以导出后再导入。
        </p>
        <div class="row">
          <button class="btn btn--ghost" type="button" @click="exportData">⬇️ 导出进度</button>
          <label class="btn btn--ghost">
            ⬆️ 导入进度
            <input class="sr-only" type="file" accept="application/json,.json" @change="importData" />
          </label>
          <button class="btn btn--ghost" type="button" @click="resetSettings">♻️ 恢复默认设置</button>
          <button class="btn btn--danger" type="button" @click="resetAll">🗑️ 清空学习记录</button>
        </div>
        <p v-if="importError" class="gate__err">{{ importError }}</p>
      </section>

      <section class="card stack">
        <h3 class="section-title">
          <span class="section-title__emoji" aria-hidden="true">🌱</span>
          给家长的小建议
        </h3>
        <ul class="tips">
          <li>每天 10–20 分钟即可，短而频繁比一次学很久更有效。</li>
          <li>先「看笔顺」再「我来写」，让孩子用手指跟着描，记忆更深。</li>
          <li>绘本只用学过的字，鼓励孩子自己读出声，读完请给一句具体的表扬。</li>
          <li>屏幕时间结束后，可以让孩子在纸上把当天的字再写一遍。</li>
        </ul>
      </section>
    </template>
  </div>
</template>

<style scoped>
.gate {
  width: min(420px, 100%);
  margin: var(--gap-xl) auto 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--gap-sm);
  text-align: center;
}

.gate__emoji {
  font-size: 3rem;
  line-height: 1;
}

.gate__title {
  font-size: 1.4rem;
  font-weight: 800;
  color: var(--text-strong);
}

.gate__desc {
  font-size: 0.88rem;
}

.gate__form {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
  margin-top: var(--gap-sm);
}

.gate__q {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--text-strong);
}

.gate__input,
.field__input {
  width: 100%;
  min-height: 52px;
  padding: 0 16px;
  border-radius: var(--radius-md);
  border: 2px solid var(--surface-border);
  background: var(--surface-strong);
  font-size: 1.05rem;
  text-align: center;
}

.field__input {
  text-align: left;
}

.gate__err {
  color: var(--danger);
  font-weight: 700;
  font-size: 0.9rem;
}

.notice {
  align-self: center;
  padding: 9px 20px;
  border-radius: var(--radius-pill);
  background: var(--success);
  color: #fff;
  font-weight: 700;
  box-shadow: var(--shadow-sm);
}

.overview {
  display: flex;
  align-items: center;
  gap: var(--gap-lg);
  flex-wrap: wrap;
}

.overview__grid {
  flex: 1;
  min-width: 220px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--gap-sm);
}

.overview__grid div {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 6px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
}

.overview__grid strong {
  font-size: 1.35rem;
  color: var(--text-strong);
  line-height: 1.2;
}

.overview__grid small {
  font-size: 0.7rem;
  color: var(--text-soft);
}

/* 图表 */
.chart {
  display: flex;
  gap: 6px;
  align-items: flex-end;
  height: 168px;
}

.chart__col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  height: 100%;
}

.chart__value {
  font-size: 0.72rem;
  font-weight: 800;
  color: var(--text-soft);
  min-height: 1em;
}

.chart__track {
  flex: 1;
  width: 100%;
  max-width: 34px;
  display: flex;
  align-items: flex-end;
  border-radius: 8px;
  background: var(--surface-sunken);
  overflow: hidden;
}

.chart__bar {
  width: 100%;
  border-radius: 8px;
  background: linear-gradient(180deg, var(--brand) 0%, var(--brand-strong) 100%);
  transition: height var(--dur-slow) var(--ease-pop);
}

.chart__label {
  font-size: 0.7rem;
  color: var(--text-soft);
}

.chart__chars {
  font-size: 0.64rem;
  color: var(--accent);
  font-weight: 700;
}

.chart__note {
  font-size: 0.76rem;
}

/* 单元 */
.units {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.unitrow {
  display: flex;
  align-items: center;
  gap: 10px;
}

.unitrow__emoji {
  font-size: 1.2rem;
}

.unitrow__name {
  width: 92px;
  font-weight: 700;
  font-size: 0.9rem;
  color: var(--text-strong);
}

.unitrow__bar {
  flex: 1;
  height: 10px;
  border-radius: 5px;
  background: var(--stroke-hint);
  overflow: hidden;
}

.unitrow__fill {
  display: block;
  height: 100%;
  border-radius: 5px;
  transition: width var(--dur-slow) var(--ease-pop);
}

.unitrow__num {
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--text-soft);
  min-width: 44px;
  text-align: right;
}

/* 需加强 */
.weak {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.weak__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px 10px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  min-width: 72px;
}

.weak__char {
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--text-strong);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', serif;
}

.weak__item small {
  font-size: 0.66rem;
  color: var(--text-soft);
}

/* 设置项 */
.field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field__label {
  font-size: 0.9rem;
  font-weight: 700;
  color: var(--text-strong);
}

.field__range {
  width: 100%;
  accent-color: var(--brand);
  height: 34px;
}

.opts {
  display: grid;
  gap: 8px;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
}

.opt {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1px;
  padding: 12px 14px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  border: 2px solid transparent;
  text-align: left;
  transition: border-color var(--dur-fast) ease, transform var(--dur-fast) var(--ease-pop);
}

.opt:active {
  transform: scale(0.97);
}

.opt.is-on {
  border-color: var(--brand);
  background: var(--brand-soft);
}

.opt__emoji {
  font-size: 1.3rem;
}

.opt strong {
  color: var(--text-strong);
}

.opt small {
  font-size: 0.72rem;
  color: var(--text-soft);
}

.segmented {
  display: flex;
  gap: 6px;
  padding: 5px;
  border-radius: var(--radius-pill);
  background: var(--surface-sunken);
}

.segmented__item {
  flex: 1;
  min-height: 44px;
  border-radius: var(--radius-pill);
  font-weight: 700;
  color: var(--text);
  transition: background var(--dur-fast) ease, color var(--dur-fast) ease;
}

.segmented__item.is-on {
  background: var(--brand);
  color: var(--text-invert);
}

.toggles {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.toggles label {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  cursor: pointer;
}

.toggles input {
  width: 24px;
  height: 24px;
  accent-color: var(--brand);
  flex: none;
}

.toggles span {
  display: flex;
  flex-direction: column;
}

.toggles strong {
  color: var(--text-strong);
  font-size: 0.95rem;
}

.toggles small {
  font-size: 0.75rem;
  color: var(--text-soft);
}

.btn--danger {
  background: var(--danger);
  color: #fff;
}

.tips {
  display: flex;
  flex-direction: column;
  gap: 8px;
  color: var(--text);
  font-size: 0.92rem;
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

@media (max-width: 520px) {
  .overview__grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
