<script setup>
/**
 * 生活行星 · 应用题。
 * 这里只负责抽母题、实例化题面和画线段/实物图，
 * 答题流程（选项/键盘/判题/提示扣星/进度条/总结）复用 QuizShell。
 */
import { computed, defineAsyncComponent, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AgeBandBadge from '@/components/AgeBandBadge.vue'
import QuizShell from '@/components/QuizShell.vue'
import { useAgeBand } from '@/composables/useAgeBand'
import {
  WORD_PROBLEMS,
  WORD_PROBLEM_TIERS,
  problemsOfTier,
} from '@/data/wordProblems'
import { numericOptions, shuffle } from '@/utils/random'
import { sound } from '@/utils/sound'

const ROUND_SIZE = 8
const MODULE_ID = 'word'

/**
 * 剖析壳（ROUND16_H5）点开才下载：图示 + 分步 + 变式连算式解析器，
 * 加上 ROUND17_H4 那 50 条手写剖析文案，一共小 10 KiB gzip。
 * 多数题孩子读一遍就会做，没必要让每个人进星球时都背着它。
 */
const WpAnalysisPanel = defineAsyncComponent(() => import('@/components/WpAnalysisPanel.vue'))

/**
 * 变式用的抽题函数按母题 id 备好一份，别在渲染里现做：
 * 现做每渲染一次就是一个新函数，剖析面板会跟着白重绘。
 */
const VARIANT_MAKERS = new Map(WORD_PROBLEMS.map((tpl) => [tpl.id, () => tpl.make()]))

const router = useRouter()
const route = useRoute()

/** 家长中心选的年龄档决定进来时停在一步题、两步题还是进阶题。 */
const band = useAgeBand((next) => {
  // 档位没变就自己换一轮题，变了交给下面的 watch(tier)
  if (tier.value === next.defaults.word) newRound()
  else tier.value = next.defaults.word
})

const tier = ref(band.value.defaults.word)
const inputMode = ref('choice')

/** 剖析里点「换一轮同类题」选的技能，优先级高于进来时带的 ?skill=。 */
const pickedSkill = ref('')
const focusedSkill = computed(() => {
  const id = pickedSkill.value || String(route.query.skill ?? '')
  return WORD_PROBLEMS.some((problem) => problem.skill === id) ? id : ''
})
const bank = computed(() => {
  const tierPool = problemsOfTier(tier.value)
  if (!focusedSkill.value) return tierPool
  const focused = tierPool.filter((problem) => problem.skill === focusedSkill.value)
  return focused.length
    ? focused
    : WORD_PROBLEMS.filter((problem) => problem.skill === focusedSkill.value)
})

function buildQuestion(template) {
  const made = template.make()
  const base = template.steps >= 3 ? 4 : template.steps === 2 ? 3 : 2
  return {
    ...made,
    id: template.id,
    skill: template.skill,
    tag: template.tag,
    emoji: template.emoji,
    scene: template.scene,
    steps: template.steps,
    hints: [made.hint, `先列式：${made.equation}`].filter(Boolean),
    stars: base,
    xp: template.steps >= 3 ? 26 : template.steps === 2 ? 20 : 14,
    errorTags:
      template.steps >= 3 ? ['multi-step'] : template.steps === 2 ? ['two-step'] : ['one-step'],
    options: numericOptions(made.answer, {
      count: 4,
      spread: Math.max(3, Math.round(made.answer * 0.35) + 2),
      min: 0,
    }),
  }
}

/** 洗牌抽题：先把母题池打乱轮着用，池子空了再洗一次，避免一轮里反复撞同一道母题。 */
function drawRound() {
  const list = bank.value
  const out = []
  let pool = shuffle(list)
  while (out.length < ROUND_SIZE) {
    if (!pool.length) pool = shuffle(list)
    out.push(buildQuestion(pool.pop()))
  }
  return out
}

const questions = ref(drawRound())

function newRound() {
  questions.value = drawRound()
}

watch(tier, newRound)
watch(focusedSkill, newRound)

function setTier(id) {
  if (tier.value === id) return
  sound.click()
  tier.value = id
}

/** 剖析开着没有。开合状态跨题保留：连着几道都想看的孩子不用每题重点一次。 */
const analysisOpen = ref(false)
const analysisBtn = ref(null)

function openAnalysis() {
  sound.click()
  analysisOpen.value = true
}

/** 跳过时把焦点送回入口按钮，键盘用户不至于被扔回页首。 */
async function closeAnalysis() {
  analysisOpen.value = false
  await nextTick()
  analysisBtn.value?.focus()
}

/** 剖析看完想接着练同一类：换成这个技能的题，重抽一轮。 */
function practiceSkill(skill) {
  if (!skill) return
  if (focusedSkill.value === skill) newRound()
  else pickedSkill.value = skill
}

function clearFocus() {
  sound.click()
  if (pickedSkill.value) pickedSkill.value = ''
  else router.replace({ query: {} })
}
</script>

<template>
  <main class="page">
    <QuizShell
      v-model:inputMode="inputMode"
      :module-id="MODULE_ID"
      module-name="生活行星"
      :questions="questions"
      :perfect-bonus="5"
      :feedback-delay="2000"
      :max-digits="4"
      :hint-labels="['💡 给点提示', '🧮 看看算式（少 1⭐）']"
      :prompts="[
        '慢慢读题，把关键的数字圈出来。',
        '先想清楚问的是什么，再列算式。',
        '读两遍题目，不着急。',
      ]"
      @replay="newRound"
      @home="router.push('/')"
    >
      <template #controls>
        <div class="seg" role="group" aria-label="题目难度">
          <button
            v-for="t in WORD_PROBLEM_TIERS"
            :key="t.id"
            class="seg-btn"
            :class="{ on: tier === t.id }"
            @click="setTier(t.id)"
          >
            {{ t.label }}
          </button>
        </div>
        <AgeBandBadge module="word" />
        <span class="chip">📚 母题 {{ bank.length }} / {{ WORD_PROBLEMS.length }} 道</span>
        <button v-if="focusedSkill" class="btn btn--ghost btn--sm" @click="clearFocus">
          🎯 只练同类题 · 取消
        </button>
      </template>

      <template #question="{ question }">
        <article class="problem">
          <div class="problem-top">
            <span class="scene-emoji">{{ question.emoji }}</span>
            <div>
              <span class="chip scene">{{ question.scene }}</span>
              <span v-if="question.tag !== question.scene" class="chip">{{ question.tag }}</span>
              <span class="chip" :class="{ 'chip-on': question.steps >= 2 }">
                {{ question.steps >= 3 ? '进阶' : question.steps === 2 ? '两步' : '一步' }}
              </span>
            </div>
          </div>

          <p class="problem-text">{{ question.text }}</p>

          <!-- 可视化：把题目里的数量画出来（CPA 教学法的 Pictorial 一段） -->
          <div v-if="question.visual" class="visual">
            <div v-for="(g, gi) in question.visual.groups" :key="gi" class="vgroup">
              <span
                v-for="k in g"
                :key="k"
                class="vicon"
                :class="{
                  gone:
                    question.visual.strike !== undefined &&
                    gi === 0 &&
                    k > g - question.visual.strike,
                }"
              >
                {{ question.visual.icon }}
              </span>
              <em class="vcount">{{ g }}</em>
            </div>
          </div>
        </article>
      </template>

      <!-- 剖析壳（ROUND16_H5）：作答前/中随时能点开，看不看都不影响答题流程 -->
      <template #beneath="{ question, locked }">
        <button
          v-if="!analysisOpen"
          ref="analysisBtn"
          class="btn btn--ghost btn--sm analysis-open"
          aria-expanded="false"
          @click="openAnalysis"
        >
          🔍 剖析这道题（想不出来再点，可跳过）
        </button>
        <WpAnalysisPanel
          v-else-if="question"
          :question="question"
          :reveal="locked"
          :make-variant="VARIANT_MAKERS.get(question.id) ?? null"
          @skip="closeAnalysis"
          @practice="practiceSkill"
        />
      </template>

      <template #extra="{ question, locked }">
        <p v-if="locked" class="eq">{{ question.equation.replace('?', question.answer) }}</p>
      </template>
    </QuizShell>
  </main>
</template>

<style scoped>
.seg {
  display: flex;
  gap: 4px;
  padding: 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  flex-wrap: wrap;
}

.seg-btn {
  padding: 7px 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 800;
  color: var(--text);
  transition: all 0.16s ease;
  white-space: nowrap;
}

.seg-btn.on {
  background: linear-gradient(135deg, var(--neon-orange), var(--star));
  color: var(--text-invert);
  box-shadow: 0 6px 16px rgba(255, 159, 69, 0.32);
}

.problem {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 20px;
  border-radius: var(--radius-md);
  background:
    radial-gradient(80% 100% at 0% 0%, rgba(255, 159, 69, 0.14), transparent 60%),
    rgba(6, 9, 30, 0.45);
  border: 1px solid rgba(255, 159, 69, 0.28);
}

.problem-top {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.problem-top .chip {
  margin-right: 6px;
}

.scene-emoji {
  font-size: 38px;
}

.scene {
  background: rgba(255, 159, 69, 0.2);
  border-color: rgba(255, 159, 69, 0.5);
}

.problem-text {
  font-size: clamp(17px, 4.2vw, 21px);
  font-weight: 700;
  line-height: 1.75;
  letter-spacing: 0.3px;
}

.visual {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}

.vgroup {
  display: flex;
  align-items: center;
  gap: 3px;
  flex-wrap: wrap;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.05);
  border: 1px dashed rgba(255, 255, 255, 0.18);
  max-width: 100%;
}

.vicon {
  font-size: 19px;
  line-height: 1;
}

.vicon.gone {
  opacity: 0.28;
  filter: grayscale(1);
  text-decoration: line-through;
}

.vcount {
  margin-left: 6px;
  font-style: normal;
  font-weight: 900;
  color: var(--star);
}

.analysis-open {
  align-self: flex-start;
}

.eq {
  align-self: flex-start;
  padding: 8px 18px;
  border-radius: var(--radius-sm);
  background: rgba(94, 231, 255, 0.12);
  border: 1px solid rgba(94, 231, 255, 0.4);
  font-size: 22px;
  font-weight: 900;
  color: var(--brand);
}
</style>
