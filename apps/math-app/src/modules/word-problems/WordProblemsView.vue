<script setup>
/**
 * 生活行星 · 应用题。
 * 这里只负责抽母题、实例化题面和画线段/实物图，
 * 答题流程（选项/键盘/判题/提示扣星/进度条/总结）复用 QuizShell。
 */
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import QuizShell from '@/components/QuizShell.vue'
import {
  WORD_PROBLEMS,
  WORD_PROBLEM_TIERS,
  problemsOfTier,
} from '@/data/wordProblems'
import { numericOptions, shuffle } from '@/utils/random'
import { sound } from '@/core/audio/sound.js'

const ROUND_SIZE = 8
const MODULE_ID = 'word'

const router = useRouter()

const tier = ref('all')
const inputMode = ref('choice')

const bank = computed(() => problemsOfTier(tier.value))

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

function setTier(id) {
  if (tier.value === id) return
  sound.click()
  tier.value = id
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
        <span class="chip">📚 母题 {{ bank.length }} / {{ WORD_PROBLEMS.length }} 道</span>
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
  color: var(--ink-soft);
  transition: all 0.16s ease;
  white-space: nowrap;
}

.seg-btn.on {
  background: linear-gradient(135deg, var(--orange), var(--gold));
  color: #3a2400;
  box-shadow: 0 6px 16px rgba(255, 159, 69, 0.32);
}

.problem {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 20px;
  border-radius: var(--radius-m);
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
  border-radius: var(--radius-s);
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
  color: var(--gold);
}

.eq {
  align-self: flex-start;
  padding: 8px 18px;
  border-radius: var(--radius-s);
  background: rgba(94, 231, 255, 0.12);
  border: 1px solid rgba(94, 231, 255, 0.4);
  font-size: 22px;
  font-weight: 900;
  color: var(--cyan);
}
</style>
