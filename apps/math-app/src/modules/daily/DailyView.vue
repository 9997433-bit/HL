<script setup>
/**
 * 今日冒险 —— 每天 5 道题，覆盖点数 / 加法 / 比大小 / 减法 / 数序。
 *
 * 题目由日期决定（见 data/daily.js），刷新页面不会换题；
 * 完成情况写在 progress.dailyQuest 上，首页的 CTA 直接读它。
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import QuizShell from '@/components/QuizShell.vue'
import { useProgressStore } from '@/stores/progress.js'
import { COMPARE_NAME } from '@/data/compare.js'
import { buildDailyQuestions, DAILY_PERFECT_BONUS, dailyDateKey } from '@/data/daily.js'

const MODULE_ID = 'daily'

const router = useRouter()
const progress = useProgressStore()

const dateKey = dailyDateKey()
const questions = ref(buildDailyQuestions(dateKey))
const inputMode = ref('choice')
const finished = ref(false)

const quest = computed(() => progress.dailyQuest)
const dateLabel = computed(() => dateKey.replaceAll('-', ' / '))

onMounted(() => progress.startDailyQuest())

function onGraded({ correct }) {
  if (!finished.value) progress.recordDailyStep(correct)
}

function onFinished({ correct }) {
  finished.value = true
  progress.finishDailyQuest({ correct })
}
</script>

<template>
  <main class="page">
    <QuizShell
      v-model:inputMode="inputMode"
      :module-id="MODULE_ID"
      module-name="今日冒险"
      :questions="questions"
      :allow-mode-toggle="false"
      :perfect-bonus="DAILY_PERFECT_BONUS"
      :hint-labels="['💡 提示', '💡 再提示（少 1⭐）']"
      :prompts="[
        '今天的 5 道题，慢慢来 🙂',
        '做完就能点亮今天的打卡。',
        '每天 5 题，坚持比做得快更重要。',
      ]"
      @graded="onGraded"
      @finished="onFinished"
      @home="router.push('/')"
      @replay="router.push('/')"
    >
      <template #controls>
        <span class="chip">🗓️ {{ dateLabel }}</span>
        <span class="chip">📋 今日 {{ quest.done }}/{{ quest.total }}</span>
        <span v-if="quest.streak > 0" class="chip">🔥 连续 {{ quest.streak }} 天</span>
        <span v-if="quest.completed" class="chip done">✅ 今天已完成</span>
      </template>

      <template #head-extra="{ question }">
        <span class="chip label">{{ question.label }}</span>
      </template>

      <template #question="{ question }">
        <!-- 数一数 -->
        <div v-if="question.type === 'count'" class="daily-count">
          <p class="daily-prompt">{{ question.prompt }}</p>
          <div class="dot-field">
            <span v-for="i in question.answer" :key="i" class="dot">{{ question.cargo.icon }}</span>
          </div>
        </div>

        <!-- 加减法 -->
        <div v-else-if="question.type === 'equation'" class="equation">
          <span class="term">{{ question.a }}</span>
          <span class="sign">{{ question.sign }}</span>
          <span class="term">{{ question.b }}</span>
          <span class="sign">=</span>
          <span class="slot">?</span>
        </div>

        <!-- 比大小 -->
        <div v-else-if="question.type === 'compare'" class="compare">
          <span class="cmp-num">{{ question.left }}</span>
          <span class="cmp-slot">?</span>
          <span class="cmp-num">{{ question.right }}</span>
        </div>

        <!-- 数序 -->
        <div v-else class="sequence">
          <span
            v-for="(n, i) in question.seq"
            :key="i"
            class="seq-cell"
            :class="{ blank: i === question.blank }"
          >
            {{ i === question.blank ? '?' : n }}
          </span>
        </div>

        <p v-if="question.type !== 'count'" class="daily-sub muted">{{ question.prompt }}</p>
      </template>

      <template #extra="{ question }">
        <p v-if="question.type === 'compare'" class="dim tiny">
          选项含义：{{ question.options.map((o) => `${o} ${COMPARE_NAME[o]}`).join('，') }}
        </p>
      </template>
    </QuizShell>
  </main>
</template>

<style scoped>
.chip.done {
  color: var(--green);
  border-color: color-mix(in srgb, var(--green) 55%, transparent);
}

.chip.label {
  flex: none;
}

.daily-prompt {
  font-size: 20px;
  font-weight: 900;
  text-align: center;
  margin-bottom: 10px;
}

.daily-sub {
  text-align: center;
  font-size: 14px;
  margin-top: 8px;
}

.dot-field {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  border-radius: var(--radius-m);
  background:
    repeating-radial-gradient(circle at 50% 50%, rgba(94, 231, 255, 0.08) 0 1px, transparent 1px 34px),
    rgba(6, 9, 30, 0.5);
  border: 1px solid rgba(94, 231, 255, 0.2);
}

.dot {
  font-size: 30px;
  line-height: 1;
}

.equation,
.compare {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  flex-wrap: wrap;
  font-weight: 900;
}

.term,
.cmp-num {
  font-size: clamp(34px, 8vw, 52px);
  color: var(--cyan);
  text-shadow: 0 0 20px rgba(94, 231, 255, 0.4);
}

.sign {
  font-size: clamp(26px, 6vw, 40px);
  color: var(--ink-soft);
}

.slot,
.cmp-slot {
  min-width: 66px;
  height: 66px;
  display: grid;
  place-items: center;
  font-size: 34px;
  color: var(--gold);
  border-radius: var(--radius-s);
  border: 2px dashed var(--gold);
  background: rgba(255, 206, 77, 0.1);
}

.sequence {
  display: flex;
  gap: 10px;
  justify-content: center;
  flex-wrap: wrap;
}

.seq-cell {
  width: 62px;
  height: 62px;
  display: grid;
  place-items: center;
  font-size: 26px;
  font-weight: 900;
  border-radius: var(--radius-s);
  background: rgba(255, 255, 255, 0.07);
  border: 1px solid rgba(255, 255, 255, 0.14);
}

.seq-cell.blank {
  color: var(--gold);
  border: 2px dashed var(--gold);
  background: rgba(255, 206, 77, 0.1);
}

.tiny {
  font-size: 12px;
  text-align: center;
}
</style>
