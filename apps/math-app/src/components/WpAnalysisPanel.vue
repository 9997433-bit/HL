<script setup>
/**
 * WpAnalysisPanel — 应用题剖析壳。
 *
 * 洪恩那类课把应用题讲成一段视频；我们做成孩子自己能点开、点到哪一步算哪一步的面板：
 *   图示理解 → 分步提示 → 变式入口
 *
 * 三条约束：
 *   1. 剖析是给卡住的孩子的台阶，不是所有人的必经流程——由玩法页按需挂载，
 *      面板自己只管「挂上来就是摊开的」，跳过按钮把收起的决定交回玩法页。
 *   2. 判题前最后一步的得数一律盖住。剖析不扣星，露答案就等于绕开提示的星星代价。
 *   3. 变式只换数字不换结构，看完还能顺手要一轮同类题接着练。
 */
import { computed, ref, watch } from 'vue'
import { buildAnalysis, ROUND16_H5, ROUND17_H4 } from '@/utils/wpAnalysis'
import { sound } from '@/utils/sound'

const props = defineProps({
  question: { type: Object, required: true },
  /** 判完题才允许显示最后一步的得数。 */
  reveal: { type: Boolean, default: false },
  /** 返回同结构新实例（母题的 make()）；不给就不显示变式入口。 */
  makeVariant: { type: Function, default: null },
})

const emit = defineEmits(['skip', 'practice'])

/** 已经摊开几步；一次只多给一步，孩子才有「自己往下想」的余地。 */
const shown = ref(1)
const variant = ref(null)

const analysis = computed(() => buildAnalysis(props.question))
const steps = computed(() => analysis.value.steps)
const visibleSteps = computed(() => steps.value.slice(0, shown.value))
const restCount = computed(() => Math.max(0, steps.value.length - shown.value))

const variantAnalysis = computed(() => (variant.value ? buildAnalysis(variant.value) : null))

function resultOf(step) {
  return step.asked && !props.reveal ? step.masked : step.display
}

function skip() {
  sound.click()
  emit('skip', props.question?.id ?? '')
}

function nextStep() {
  if (!restCount.value) return
  sound.click()
  shown.value += 1
}

function showAllSteps() {
  if (!restCount.value) return
  sound.click()
  shown.value = steps.value.length
}

function drawVariant() {
  if (!props.makeVariant) return
  sound.click()
  variant.value = props.makeVariant() ?? null
}

function practiceSame() {
  sound.click()
  emit('practice', props.question?.skill ?? '')
}

// 换题就把分步和变式收回起点：新题的第二步不该跟着上一道一起摊开
watch(
  () => props.question?.text,
  () => {
    shown.value = 1
    variant.value = null
  },
)

// 判完题再把剩下的步骤一次摊开，讲评时看到的是完整思路而不是半截
watch(
  () => props.reveal,
  (on) => {
    if (on) shown.value = steps.value.length
  },
)
</script>

<template>
  <section
    class="panel"
    role="region"
    aria-label="应用题剖析"
    :data-analysis="ROUND16_H5"
    :data-explain="analysis.handwritten ? ROUND17_H4 : ''"
  >
    <header class="panel-head">
      <span class="chip chip-on">🔍 剖析</span>
      <!-- 手写剖析链讲的是「这道题为什么先算它」，值得让孩子知道这段是老师写的 -->
      <span v-if="analysis.handwritten" class="chip chip-hand">✍️ 老师讲法</span>
      <p class="dim">看懂「为什么这样列式」，再回去作答。</p>
      <div class="spacer" />
      <button class="btn btn--ghost btn--sm" @click="skip">跳过 ✕</button>
    </header>

    <!-- 一 · 图示理解：先把数量画成长短，再说要求的是哪一段 -->
    <section class="block">
      <h3 class="block-title">① 图示理解</h3>
      <div v-if="analysis.knowns.length" class="knowns">
        <span class="chip">已知</span>
        <span v-for="k in analysis.knowns" :key="k.label" class="chip num">{{ k.label }}</span>
      </div>
      <p v-if="analysis.ask" class="ask">❓ {{ analysis.ask }}</p>
      <div class="bars" role="img" :aria-label="`图示：${analysis.diagram.caption}`">
        <div v-for="(bar, i) in analysis.diagram.bars" :key="i" class="bar-row">
          <span class="bar-label">{{ analysis.diagram.icon || '▮' }} {{ bar.value }}</span>
          <span class="bar-track">
            <span class="bar-fill" :style="{ width: `${bar.percent}%` }">
              <span
                v-if="bar.strikePercent"
                class="bar-gone"
                :style="{ width: `${bar.strikePercent}%` }"
              />
            </span>
          </span>
        </div>
        <div class="bar-row">
          <span class="bar-label ask-label">? 要求的</span>
          <span class="bar-track"><span class="bar-fill unknown" /></span>
        </div>
      </div>
      <p class="dim caption">{{ analysis.diagram.caption }}</p>
    </section>

    <!-- 二 · 分步提示：一次只放一步，最后一步的得数判题前盖住 -->
    <section class="block">
      <h3 class="block-title">② 分步提示</h3>
      <p v-if="analysis.why" class="why">💬 {{ analysis.why }}</p>
      <ol v-if="steps.length" class="steps">
        <li v-for="(step, i) in visibleSteps" :key="i" class="step">
          <span class="step-expr">{{ step.expr }} = {{ resultOf(step) }}</span>
          <span class="step-why">{{ step.why }}</span>
        </li>
      </ol>
      <p v-else class="fallback">整道题的算式：{{ analysis.equation }}</p>
      <div v-if="restCount" class="step-actions">
        <button class="btn btn--ghost btn--sm" @click="nextStep">
          再看一步（还剩 {{ restCount }} 步）
        </button>
        <button class="btn btn--ghost btn--sm" @click="showAllSteps">全部摊开</button>
      </div>
      <p v-else-if="steps.length && !reveal" class="dim caption">
        最后一步的得数先盖着 —— 算出来再回去选答案。
      </p>
    </section>

    <!-- 三 · 变式入口：同结构换数字，看完可以直接要一轮同类题 -->
    <section v-if="makeVariant" class="block">
      <h3 class="block-title">③ 变式</h3>
      <div class="variant-actions">
        <button class="btn btn--ghost btn--sm" @click="drawVariant">
          {{ variant ? '再换一道变式' : '看一道同结构的变式' }}
        </button>
        <button class="btn btn--ghost btn--sm" @click="practiceSame">换一轮同类题练</button>
      </div>
      <div v-if="variant && variantAnalysis" class="variant">
        <p class="variant-text">{{ variant.text }}</p>
        <!-- 变式是讲给卡住的孩子看的范例，所以它的每一步都摊开，不盖得数 -->
        <ol v-if="variantAnalysis.steps.length" class="steps">
          <li v-for="(step, i) in variantAnalysis.steps" :key="i" class="step">
            <span class="step-expr">{{ step.expr }} = {{ step.display }}</span>
          </li>
        </ol>
        <p class="variant-eq">
          {{ variantAnalysis.equation.replace('?', String(variant.answer)) }}
        </p>
        <p class="dim caption">结构和上面这道一模一样，只换了数字和说法。</p>
      </div>
    </section>
  </section>
</template>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px 18px;
  border-radius: var(--radius-md);
  background:
    radial-gradient(90% 120% at 100% 0%, rgba(94, 231, 255, 0.12), transparent 62%),
    rgba(6, 9, 30, 0.42);
  border: 1px solid rgba(94, 231, 255, 0.32);
}

.panel-head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.spacer {
  flex: 1;
}

.block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.block-title {
  font-size: 14px;
  font-weight: 900;
  letter-spacing: 0.5px;
  color: var(--brand);
}

.knowns {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}

.num {
  background: rgba(255, 206, 77, 0.16);
  border-color: rgba(255, 206, 77, 0.45);
  font-weight: 900;
}

.chip-hand {
  background: rgba(85, 230, 165, 0.14);
  border-color: rgba(85, 230, 165, 0.42);
  color: var(--success);
  font-weight: 800;
}

.ask {
  font-size: 15px;
  font-weight: 800;
  line-height: 1.7;
}

.bars {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.bar-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.bar-label {
  min-width: 76px;
  font-size: 13px;
  font-weight: 800;
}

.ask-label {
  color: var(--star);
}

.bar-track {
  flex: 1;
  height: 16px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.07);
  overflow: hidden;
}

.bar-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--brand), var(--accent));
  transition: width 0.3s ease;
}

.bar-gone {
  display: block;
  height: 100%;
  margin-left: auto;
  border-radius: 999px;
  background: repeating-linear-gradient(
    45deg,
    rgba(6, 9, 30, 0.65),
    rgba(6, 9, 30, 0.65) 5px,
    rgba(255, 255, 255, 0.12) 5px,
    rgba(255, 255, 255, 0.12) 10px
  );
}

.bar-fill.unknown {
  width: 46%;
  background: transparent;
  border: 2px dashed rgba(255, 206, 77, 0.6);
}

.caption {
  font-size: 12px;
}

.why {
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  background: rgba(255, 206, 77, 0.1);
  border: 1px solid rgba(255, 206, 77, 0.32);
  font-size: 14px;
}

.steps {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 0;
  padding-left: 20px;
}

.step {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.step-expr {
  font-size: 19px;
  font-weight: 900;
  color: var(--brand);
}

.step-why {
  font-size: 13px;
  color: var(--text);
}

.fallback {
  font-size: 18px;
  font-weight: 900;
  color: var(--brand);
}

.step-actions,
.variant-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.variant {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.05);
  border: 1px dashed rgba(255, 255, 255, 0.2);
}

.variant-text {
  font-size: 15px;
  line-height: 1.7;
}

.variant-eq {
  align-self: flex-start;
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  background: rgba(85, 230, 165, 0.14);
  border: 1px solid rgba(85, 230, 165, 0.42);
  font-size: 18px;
  font-weight: 900;
  color: var(--success);
}
</style>
