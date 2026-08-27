<script setup>
/**
 * 跟读面板：范读 → 跟读 → 当场给一句评价。
 *
 * 三档能力（逐字评测 / 录音回放 / 自己听一听）由 useSpeechEval 判定，
 * 这里的职责是把每一档「能做到什么」明明白白摆在界面上——
 * 孩子读完之后看到的分数是怎么来的，不该靠猜。
 */
import { computed, ref, watch } from 'vue'
import { useSpeechEval } from '@/composables/useSpeechEval.js'
import { sfx } from '@/utils/audio.js'

const props = defineProps({
  /** 逐句：[{ text, pinyin }]，跟读按句推进。 */
  lines: { type: Array, required: true },
  title: { type: String, default: '' },
  /** 家长中心里关掉朗读时，范读按钮要跟着停。 */
  speechEnabled: { type: Boolean, default: true }
})

const emit = defineEmits(['scored'])

const {
  phase,
  mode,
  modeLabel,
  modeNote,
  result,
  error,
  level,
  recordingUrl,
  canRecognize,
  allowRecognition,
  playReference,
  start,
  stop,
  selfAssess,
  reset
} = useSpeechEval()

/** 0..n-1 是逐句，'all' 是整首连读。 */
const cursor = ref(0)
const whole = ref(false)

const current = computed(() => {
  if (whole.value) {
    return {
      label: '整首连读',
      text: props.lines.map((l) => l.text).join(''),
      pinyin: props.lines.map((l) => l.pinyin).join(' ')
    }
  }
  const line = props.lines[cursor.value] ?? props.lines[0]
  return { label: `第 ${cursor.value + 1} 句`, text: line?.text ?? '', pinyin: line?.pinyin ?? '' }
})

/** 每句读过一次就记一颗星，走到最后一句时提示可以整首连读了。 */
const done = ref(new Set())
const doneCount = computed(() => done.value.size)
const allLinesDone = computed(() => doneCount.value >= props.lines.length)

const say = ref('')

const charMarks = computed(() => result.value?.chars ?? [])

watch(
  () => [cursor.value, whole.value],
  () => {
    reset()
    say.value = ''
  }
)

async function onDemo() {
  sfx.tap()
  say.value = `范读${current.value.label}`
  const ok = await playReference(current.value.text)
  if (ok) say.value = `范读完了，轮到你读${current.value.label}`
}

async function onStart() {
  sfx.tap()
  const ok = await start(current.value.text)
  if (!ok) return
  say.value =
    mode.value === 'selfcheck'
      ? '大声读出来，读完点「我读完了」'
      : '正在听你读，读完点「我读完了」'
}

async function onStop() {
  sfx.tap()
  const scored = await stop()
  if (mode.value === 'selfcheck') {
    say.value = '读完啦，你觉得自己读得怎么样？'
    return
  }
  finish(scored)
}

function onSelfAssess(choice) {
  sfx.tap()
  finish(selfAssess(choice))
}

function finish(scored) {
  if (!scored) return
  if (!whole.value) done.value = new Set([...done.value, cursor.value])
  const grade = scored.grade?.label ?? ''
  say.value = scored.score === null ? `你评的是「${grade}」` : `得分 ${scored.score}，${grade}`
  if (scored.score !== null && scored.score >= 70) sfx.correct()
  emit('scored', {
    mode: scored.mode,
    score: scored.score,
    grade: scored.grade?.id ?? '',
    whole: whole.value,
    index: whole.value ? -1 : cursor.value
  })
}

function pick(index) {
  sfx.tap()
  whole.value = false
  cursor.value = index
}

function pickWhole() {
  sfx.tap()
  whole.value = true
}
</script>

<template>
  <section class="fr card" :data-mode="mode" :data-phase="phase">
    <header class="fr__head">
      <h3 class="section-title">
        <span class="section-title__emoji" aria-hidden="true">🎤</span>
        跟着读一读
      </h3>
      <span class="pill">{{ modeLabel }}</span>
    </header>

    <p class="fr__mode muted">{{ modeNote }}</p>

    <label v-if="canRecognize" class="fr__opt">
      <input v-model="allowRecognition" type="checkbox" />
      <span>打开逐字评测（会用浏览器的语音识别，可能联网）</span>
    </label>

    <!-- 选读哪一句 -->
    <div class="fr__picker" role="group" aria-label="选择要跟读的句子">
      <button
        v-for="(line, i) in lines"
        :key="i"
        type="button"
        class="fr__chip"
        :class="{ 'is-on': !whole && cursor === i, 'is-done': done.has(i) }"
        @click="pick(i)"
      >
        {{ i + 1 }}
      </button>
      <button
        type="button"
        class="fr__chip fr__chip--whole"
        :class="{ 'is-on': whole }"
        :disabled="!allLinesDone"
        :title="allLinesDone ? '整首连读' : '每一句都读过一遍就能连读整首'"
        @click="pickWhole"
      >
        整首
      </button>
    </div>

    <!-- 要读的内容 -->
    <div class="fr__stage">
      <p class="fr__label muted">{{ current.label }}</p>
      <p class="fr__pinyin">{{ current.pinyin }}</p>
      <p class="fr__text">
        <template v-if="charMarks.length">
          <span
            v-for="(m, i) in charMarks"
            :key="i"
            class="fr__glyph"
            :data-status="m.status"
          >{{ m.char }}</span>
        </template>
        <template v-else>{{ current.text }}</template>
      </p>
    </div>

    <!-- 录音时的音量条：孩子看得见自己的声音，比一句「请说话」有用得多 -->
    <div v-if="phase === 'recording' && mode !== 'selfcheck'" class="fr__meter" aria-hidden="true">
      <span class="fr__meter-fill" :style="{ width: `${Math.round(level * 100)}%` }" />
    </div>

    <div class="fr__acts">
      <button
        type="button"
        class="btn fr__demo"
        :disabled="!speechEnabled || phase === 'recording'"
        @click="onDemo"
      >
        🔊 听我读一遍
      </button>
      <button
        v-if="phase !== 'recording'"
        type="button"
        class="btn btn--primary fr__go"
        @click="onStart"
      >
        🎤 我来读
      </button>
      <button v-else type="button" class="btn btn--primary fr__stop" @click="onStop">
        ✅ 我读完了
      </button>
    </div>

    <p v-if="error" class="fr__err">{{ error }}</p>

    <!-- 自评档：没有麦克风就不假装打分，让孩子自己说读得怎么样 -->
    <div v-if="mode === 'selfcheck' && phase === 'result' && !result" class="fr__self">
      <p class="muted">读得怎么样？自己选一个：</p>
      <div class="fr__self-row">
        <button type="button" class="btn fr__self-btn" @click="onSelfAssess('fluent')">
          🌟 很流利
        </button>
        <button type="button" class="btn fr__self-btn" @click="onSelfAssess('okay')">
          ✨ 有点卡
        </button>
        <button type="button" class="btn fr__self-btn" @click="onSelfAssess('again')">
          🔁 还要再来
        </button>
      </div>
    </div>

    <!-- 结果 -->
    <div v-if="result" class="fr__result" :data-score="result.score ?? ''" :data-grade="result.grade?.id">
      <div class="fr__score">
        <span class="fr__score-emoji" aria-hidden="true">{{ result.grade?.emoji }}</span>
        <strong v-if="result.score !== null" class="fr__score-num">{{ result.score }}</strong>
        <span class="fr__score-label">{{ result.grade?.label }}</span>
      </div>
      <p class="fr__tip">{{ result.grade?.tip }}</p>
      <p v-if="result.note" class="muted fr__note">{{ result.note }}</p>
      <p v-if="result.heard" class="muted fr__heard">听到的是：{{ result.heard }}</p>
      <div v-if="recordingUrl" class="fr__playback">
        <p class="muted">听听自己刚才读的：</p>
        <audio class="fr__audio" :src="recordingUrl" controls preload="none" />
      </div>
    </div>

    <p class="fr__foot muted">已经读过 {{ doneCount }} / {{ lines.length }} 句</p>
    <p class="sr-only" aria-live="polite">{{ say }}</p>
  </section>
</template>

<style scoped>
.fr {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
}

.fr__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--gap-sm);
}

.fr__mode {
  font-size: 0.85rem;
}

.fr__opt {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8rem;
  color: var(--text-soft);
}

.fr__picker {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.fr__chip {
  min-width: 44px;
  min-height: 44px;
  padding: 0 12px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--surface-border);
  background: var(--surface);
  font-weight: 800;
  color: var(--text-soft);
}

.fr__chip.is-done {
  border-color: var(--mint-400);
  color: var(--text-strong);
}

.fr__chip.is-on {
  background: var(--brand-soft);
  color: var(--text-strong);
}

.fr__chip:disabled {
  opacity: 0.45;
}

.fr__chip--whole {
  min-width: 64px;
}

.fr__stage {
  padding: var(--gap-md);
  border-radius: var(--radius-lg);
  background: var(--brand-soft);
  text-align: center;
}

.fr__label {
  font-size: 0.78rem;
}

.fr__pinyin {
  font-size: 0.82rem;
  letter-spacing: 0.05em;
  color: var(--text-soft);
}

.fr__text {
  margin-top: 6px;
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  line-height: 1.7;
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

.fr__glyph[data-status='hit'] {
  color: var(--mint-400);
}

.fr__glyph[data-status='miss'] {
  color: var(--coral-400);
  text-decoration: underline wavy;
  text-underline-offset: 6px;
}

.fr__meter {
  height: 10px;
  border-radius: var(--radius-pill);
  background: var(--surface-border);
  overflow: hidden;
}

.fr__meter-fill {
  display: block;
  height: 100%;
  border-radius: var(--radius-pill);
  background: var(--mint-400);
  transition: width 80ms linear;
}

.fr__acts,
.fr__self-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--gap-sm);
}

.fr__err {
  font-size: 0.82rem;
  color: var(--coral-400);
}

.fr__self {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.fr__result {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: var(--gap-md);
  border-radius: var(--radius-lg);
  background: var(--surface);
  border: 1px solid var(--surface-border);
}

.fr__score {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.fr__score-emoji {
  font-size: 1.6rem;
}

.fr__score-num {
  font-size: 1.8rem;
  font-weight: 800;
}

.fr__score-label {
  font-weight: 800;
}

.fr__note,
.fr__heard,
.fr__tip {
  font-size: 0.84rem;
  line-height: 1.6;
}

.fr__audio {
  width: 100%;
  margin-top: 4px;
}

.fr__foot {
  font-size: 0.78rem;
}
</style>
