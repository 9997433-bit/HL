<script setup>
/**
 * 今日冒险 —— 每天 5 道题，覆盖点数 / 加法 / 比大小 / 减法 / 数序。
 *
 * 题目由日期决定（见 data/daily.js），刷新页面不会换题；
 * 完成情况写在 progress.dailyQuest 上，首页的 CTA 直接读它。
 *
 * 还有一种进法：技能图谱的推荐位带着 `?focus=<技能点>` 跳进来，这时出的是
 * 只练那一个技能的**专项冒险**，题目同样由「日期 + 技能」定死，刷新不换题。
 * 专项冒险不算今天的打卡——打卡认的是那份覆盖五类题的常规冒险，
 * 拿一份自己挑难度的专项题去顶，连续天数就不再是同一回事了。
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import MascotBot from '@/components/MascotBot.vue'
import QuizShell from '@/components/QuizShell.vue'
import { useMascotCoach } from '@/composables/useMascotCoach.js'
import { useProgressStore } from '@/stores/progress.js'
import { COMPARE_NAME } from '@/data/compare.js'
import {
  buildDailyQuestions,
  buildFocusDailyQuestions,
  canDailyFocus,
  DAILY_PERFECT_BONUS,
  dailyDateKey,
} from '@/data/daily.js'
import { SKILL_MAP } from '@/data/curriculum.js'

const MODULE_ID = 'daily'

const route = useRoute()
const router = useRouter()
const progress = useProgressStore()

const dateKey = dailyDateKey()
/** 认不出的技能点当没传：宁可回到常规冒险，也不要给孩子一页空题。 */
const focusSkill = computed(() => {
  const id = String(route.query.focus ?? '')
  return canDailyFocus(id) ? id : ''
})
const focusName = computed(() => SKILL_MAP[focusSkill.value]?.name ?? '')

const buildQuestions = () =>
  focusSkill.value
    ? buildFocusDailyQuestions({ skill: focusSkill.value, dateKey })
    : buildDailyQuestions(dateKey)

const inputMode = ref('choice')
const finished = ref(false)
const questions = ref(buildQuestions())

// 从一条推荐直接换到另一条时路由不重建组件，题目得跟着 focus 换
watch(focusSkill, () => {
  finished.value = false
  questions.value = buildQuestions()
})

/**
 * 小算在答题时也陪着：答题壳里那只机器人换成可点触的陪跑形态，
 * 点一下换一句鼓励语、读出来，并写进它自己的台词行。
 */
const quiz = ref(null)
const { mood: coachMood, next: coachNext } = useMascotCoach('daily')

function cheerMe() {
  quiz.value?.announce(coachNext())
}

const quest = computed(() => progress.dailyQuest)
const dateLabel = computed(() => dateKey.replaceAll('-', ' / '))

onMounted(() => progress.startDailyQuest())

function onGraded({ correct }) {
  if (focusSkill.value || finished.value) return
  progress.recordDailyStep(correct)
}

function onFinished({ correct }) {
  finished.value = true
  // 专项冒险的星星与掌握度照记（QuizShell 负责），但不动今天的打卡
  if (focusSkill.value) return
  progress.finishDailyQuest({ correct })
}
</script>

<template>
  <main class="page">
    <QuizShell
      ref="quiz"
      v-model:inputMode="inputMode"
      :module-id="MODULE_ID"
      :module-name="focusSkill ? `${focusName}专项` : '今日冒险'"
      :questions="questions"
      :allow-mode-toggle="false"
      :perfect-bonus="DAILY_PERFECT_BONUS"
      :hint-labels="['💡 提示', '💡 再提示（少 1⭐）']"
      :prompts="
        focusSkill
          ? [
              `这一轮只练${focusName}，慢慢来 🙂`,
              '专攻一个点，比东练一题西练一题见效快。',
              '做完再回图谱看看，这一点亮了几分。',
            ]
          : ['今天的 5 道题，慢慢来 🙂', '做完就能点亮今天的打卡。', '每天 5 题，坚持比做得快更重要。']
      "
      @graded="onGraded"
      @finished="onFinished"
      @home="router.push('/')"
      @replay="router.push(focusSkill ? '/skill-graph' : '/')"
    >
      <template #mascot="{ mood }">
        <MascotBot
          :mood="coachMood === 'cheer' ? 'cheer' : mood"
          :size="72"
          interactive
          tap-label="点我，小算给你说句鼓励的话"
          @tap="cheerMe"
        />
      </template>

      <template #controls>
        <span class="chip">🗓️ {{ dateLabel }}</span>
        <template v-if="focusSkill">
          <span class="chip focus" :data-daily-focus="focusSkill">
            🎯 {{ focusName }} 专项 {{ questions.length }} 题
          </span>
          <span class="chip dim-chip">专项练习不占今天的打卡</span>
          <RouterLink class="btn btn--ghost btn--sm" to="/skill-graph">🧭 回技能图谱</RouterLink>
        </template>
        <template v-else>
          <span class="chip">📋 今日 {{ quest.done }}/{{ quest.total }}</span>
          <span v-if="quest.streak > 0" class="chip">🔥 连续 {{ quest.streak }} 天</span>
          <span v-if="quest.completed" class="chip done">✅ 今天已完成</span>
        </template>
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

.chip.focus {
  color: var(--cyan);
  border-color: color-mix(in srgb, var(--cyan) 55%, transparent);
}

.chip.dim-chip {
  color: var(--ink-soft);
  font-size: 12px;
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
