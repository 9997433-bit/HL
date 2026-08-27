<script setup>
/**
 * 单字学习页 = 一台五步状态机：认一认 → 写一写 → 听一听 → 考一考 → 领奖励。
 *
 * 为什么要做成状态机：孩子自己不会安排「先看再写再听再考」，
 * 把顺序固定下来，每一步做完自动接上下一步，一个字才算真的过了一遍。
 *
 * 三条规矩：
 *  1. 自动衔接不是自动跳走。每次自动前进都先在 `pendingNext` 里挂一秒多，
 *     期间屏幕上有「等一下」可以按停，读屏也会先播报下一步是什么（WCAG §2.2.1）。
 *  2. 任何一步都能用上面的步骤条手动跳。跳过去不等于做过：`done` 里只记
 *     真正做完的步骤，四步都做完了「领奖励」才会给这一轮记账、发徽章。
 *  3. 田字格、组词、例句、底部操作在所有阶段都在原地，状态机只换中间那块面板；
 *     这样孩子随时想写一笔、想听个词都不用先退出当前步骤。
 */
import {
  computed,
  defineAsyncComponent,
  nextTick,
  onBeforeUnmount,
  onMounted,
  reactive,
  ref,
  watch
} from 'vue'
import { useRouter } from 'vue-router'
import gsap from 'gsap'
import HanziStrokeBox from '@/components/HanziStrokeBox.vue'
import VoiceNotice from '@/components/VoiceNotice.vue'
import { CHARACTERS, getCharacter, getLoadedCharacter, loadCharacter } from '@/data/characters.js'
import { hasEtymology } from '@/data/etymology-index.js'
import { RADICAL_MAP, getRadical } from '@/data/radicals.js'
import { useFeedback } from '@/composables/useFeedback.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { speak } from '@/utils/speech.js'
import { sfx } from '@/utils/sfx.js'

const props = defineProps({ char: { type: String, required: true } })

/**
 * 字源演变按需加载：只有六十多个字有字源语料，而演变动画本身还要带上
 * GSAP 时间线和小图数据。有语料的字先显示一个入口按钮，孩子点了才 import()，
 * 没点过的字一个字节也不下载。
 */
const EtymologyStage = defineAsyncComponent(() => import('@/components/EtymologyStage.vue'))

const router = useRouter()
const progress = useProgressStore()
const settings = useSettingsStore()
/** 听一听 / 考一考的正反馈：音效、星星粒子、震动都从这里出。 */
const feedback = useFeedback()

const toast = ref('')

/* ------------------------------------------------------------ 五步状态机 */

const PHASES = [
  { id: 'intro', label: '认一认', emoji: '👀', hint: '看清字形，听听它怎么读' },
  { id: 'trace', label: '写一写', emoji: '✍️', hint: '在田字格里按笔顺写一遍' },
  { id: 'listen', label: '听一听', emoji: '👂', hint: '听读音，从三个字里挑出它' },
  { id: 'quiz', label: '考一考', emoji: '🧠', hint: '选出这个字的意思' },
  { id: 'reward', label: '领奖励', emoji: '🏆', hint: '看看这一趟的收获' }
]
const PHASE_IDS = PHASES.map((p) => p.id)
const phaseIndex = (id) => PHASE_IDS.indexOf(id)
const phaseAfter = (id) => PHASE_IDS[phaseIndex(id) + 1] ?? null
const phaseMeta = (id) => PHASES[phaseIndex(id)] ?? PHASES[0]

/** 各处自动衔接的等待时长（毫秒）。都留出了「等一下」能按停的余地。 */
const DELAY = {
  heard: 1600,
  introIdle: 18000,
  traced: 1400,
  skipped: 900,
  answered: 1400,
  revealed: 2000,
  traceStart: 1200
}

const phase = ref('intro')
/** 真正做完的步骤；手动跳过去不算数，「领奖励」凭它决定要不要记账。 */
const done = reactive({ intro: false, trace: false, listen: false, quiz: false })
/** 正在倒计时的自动衔接：{ id, label }。 */
const pendingNext = ref(null)
const stepAnnounce = ref('')

const railRef = ref(null)
const panelRef = ref(null)
const strokeBoxRef = ref(null)

let advanceTimer = null
let idleTimer = null
let traceTimer = null

const current = computed(() => phaseMeta(phase.value))
const flowReady = computed(() => done.intro && done.trace && done.listen && done.quiz)
const missingSteps = computed(() =>
  PHASES.filter((p) => p.id !== 'reward' && !done[p.id]).map((p) => p.label)
)

const decoded = computed(() => decodeURIComponent(props.char))

/**
 * 拼音、笔画这些随字表索引一起进主包，打开页面就能画；
 * 释义、组词、例句在单元详情包里，要等 import() 回来。
 * 先用索引把页面搭起来，课文到了再补上，避免为了一个字白等一个网络往返。
 */
const loaded = ref(getLoadedCharacter(decoded.value))
const item = computed(() => loaded.value ?? getCharacter(decoded.value))

watch(
  decoded,
  (char) => {
    loaded.value = getLoadedCharacter(char)
    loadCharacter(char).then((full) => {
      if (decoded.value === char) loaded.value = full
    })
  },
  { immediate: true }
)
const radical = computed(() => (item.value ? getRadical(item.value.radical) : null))

/** 有字源语料的字才显示「这个字的来历」，展开之后才真的把动画组件拉下来。 */
const hasOrigin = computed(() => hasEtymology(decoded.value))
const originOpen = ref(false)

function toggleOrigin() {
  sfx.tap()
  originOpen.value = !originOpen.value
}

/**
 * 只有 RADICALS 里的重点部首有讲解页。
 * 其余是 radicals.js 的兜底条目（横、大字头…），链过去只会落到第一个部首上，
 * 所以这类部首只展示不跳转。
 */
const radicalLink = computed(() =>
  radical.value && RADICAL_MAP.has(radical.value.id) ? `/radicals/${radical.value.id}` : null
)

const index = computed(() => CHARACTERS.findIndex((c) => c.char === decoded.value))
const prev = computed(() => (index.value > 0 ? CHARACTERS[index.value - 1] : null))
const next = computed(() =>
  index.value >= 0 && index.value < CHARACTERS.length - 1 ? CHARACTERS[index.value + 1] : null
)

const record = computed(() => progress.chars[decoded.value] || null)
const mastered = computed(() => progress.isMastered(decoded.value))

function say(text, rate) {
  sfx.tap()
  // 听读音也是一种学习行为，记下来才能算「认识了」
  if (item.value && text === item.value.char) progress.markHeard(text)
  speak(text, { rate: rate ?? settings.speechRate })
}

/* ------------------------------------------------------- 状态机：迁移 */

function clearTimers() {
  for (const t of [advanceTimer, idleTimer, traceTimer]) if (t) clearTimeout(t)
  advanceTimer = null
  idleTimer = null
  traceTimer = null
}

function cancelAdvance() {
  if (advanceTimer) clearTimeout(advanceTimer)
  advanceTimer = null
  pendingNext.value = null
}

/** 排一次自动衔接：先把「下一步是什么」摆出来，到点再真的走过去。 */
function scheduleAdvance(id, delay) {
  if (!id) return
  cancelAdvance()
  pendingNext.value = { id, label: phaseMeta(id).label }
  advanceTimer = window.setTimeout(() => {
    advanceTimer = null
    pendingNext.value = null
    goPhase(id)
  }, delay)
}

function holdOn() {
  sfx.tap()
  cancelAdvance()
  stepAnnounce.value = '好，先停在这一步，准备好了再点「下一步」。'
}

function goPhase(id, { manual = false } = {}) {
  if (!item.value || phaseIndex(id) < 0 || id === phase.value) return
  clearTimers()
  pendingNext.value = null
  phase.value = id
  const meta = phaseMeta(id)
  stepAnnounce.value = `第 ${phaseIndex(id) + 1} 步，共 ${PHASES.length} 步：${meta.label}。${meta.hint}`
  if (manual) sfx.tap()
  enterPhase(id, { manual })
}

/** 已经到过的最远一步，回头看不受限。 */
const reached = ref(0)

/** 手动点步骤条：只让往回看和往前一步，免得直接跳到领奖励白拿徽章。 */
const canJump = (id) => phaseIndex(id) <= Math.max(phaseIndex(phase.value) + 1, reached.value)

function onStepClick(id) {
  if (!canJump(id)) {
    stepAnnounce.value = `「${phaseMeta(id).label}」还没解锁，先把前面几步做完吧。`
    return
  }
  goPhase(id, { manual: true })
}

function nextStep() {
  const id = phaseAfter(phase.value)
  if (!id) return
  // 「认一认」看过听过就算过；写 / 听 / 考三步得真做完才记数，光按「下一步」不算
  if (phase.value === 'intro') done.intro = true
  goPhase(id, { manual: true })
}

function enterPhase(id, { manual } = {}) {
  reached.value = Math.max(reached.value, phaseIndex(id))
  if (id === 'intro') {
    // 干等着也别卡住：一直没有动作就自己往下走一步
    idleTimer = window.setTimeout(() => {
      done.intro = true
      scheduleAdvance('trace', 600)
    }, DELAY.introIdle)
  } else if (id === 'trace') {
    // 顺着流程走进来的，田字格自己进入描红；手动跳进来的让孩子自己按
    if (!manual) traceTimer = window.setTimeout(() => strokeBoxRef.value?.startQuiz(), DELAY.traceStart)
  } else if (id === 'listen') {
    buildListen()
    window.setTimeout(() => playListen(), 400)
  } else if (id === 'quiz') {
    buildQuiz()
  } else if (id === 'reward') {
    settleReward()
  }
}

/* ------------------------------------------------- 状态机：认一认 / 写一写 */

function heard() {
  say(item.value.char)
  done.intro = true
  if (phase.value === 'intro') scheduleAdvance('trace', DELAY.heard)
}

/* --------------------------------------------------- 状态机：听一听 */

const shuffle = (list) => {
  const out = [...list]
  for (let i = out.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[out[i], out[j]] = [out[j], out[i]]
  }
  return out
}

/** 干扰项优先取同一单元的字：同主题的字长得更像，才有分辨的价值。 */
function distractors(count, exclude = () => false) {
  const pool = CHARACTERS.filter((c) => c.char !== decoded.value && !exclude(c))
  const near = pool.filter((c) => c.unit === item.value.unit)
  return shuffle(near.length >= count ? near : pool).slice(0, count)
}

const listenOptions = ref([])
const listenPick = ref('')
const listenTries = ref(0)
const listenRevealed = ref(false)

function buildListen() {
  listenOptions.value = shuffle([item.value, ...distractors(2)])
  listenPick.value = ''
  listenTries.value = 0
  listenRevealed.value = false
}

function playListen() {
  if (!item.value) return
  speak(item.value.char, { rate: settings.speechRate })
}

function onListenPick(option, event) {
  if (listenRevealed.value || done.listen) return
  const correct = option.char === decoded.value
  listenPick.value = option.char
  listenTries.value += 1
  progress.recordAnswer(decoded.value, correct)
  if (correct) {
    // 一次答对才算连对：听错过再选中的，音高不往上走
    feedback.correct(event?.currentTarget, { cueArg: listenTries.value === 1 ? 2 : 1 })
    listenRevealed.value = true
    done.listen = true
    stepAnnounce.value = `答对了，就是「${decoded.value}」。`
    scheduleAdvance('quiz', DELAY.answered)
    return
  }
  feedback.wrong(event?.currentTarget)
  if (listenTries.value >= 2) {
    listenRevealed.value = true
    done.listen = true
    stepAnnounce.value = `没关系，正确答案是「${decoded.value}」。`
    scheduleAdvance('quiz', DELAY.revealed)
  } else {
    stepAnnounce.value = '再听一次，选出刚才读的那个字。'
  }
}

/* --------------------------------------------------- 状态机：考一考 */

const quizOptions = ref([])
const quizPick = ref('')
const quizRevealed = ref(false)

function buildQuiz() {
  const others = distractors(2, (c) => c.meaning === item.value.meaning)
  quizOptions.value = shuffle([item.value, ...others])
  quizPick.value = ''
  quizRevealed.value = false
}

function onQuizPick(option, event) {
  if (quizRevealed.value) return
  const correct = option.char === decoded.value
  quizPick.value = option.char
  quizRevealed.value = true
  done.quiz = true
  progress.recordAnswer(decoded.value, correct)
  if (correct) {
    // 听一听也答对了的话，考一考的音再往上抬一档
    feedback.correct(event?.currentTarget, { cueArg: done.listen ? 3 : 1 })
    stepAnnounce.value = '意思也对上了！'
  } else {
    feedback.wrong(event?.currentTarget)
    stepAnnounce.value = `「${decoded.value}」的意思是：${item.value.meaning}`
  }
  scheduleAdvance('reward', correct ? DELAY.answered : DELAY.revealed)
}

/* --------------------------------------------------- 状态机：领奖励 */

const starsAtStart = ref(0)
const flowRounds = ref(0)
const rewardBadges = ref([])
let settled = false

function settleReward() {
  if (settled || !flowReady.value) return
  settled = true
  const { flows, badges } = progress.completeCharFlow(decoded.value)
  flowRounds.value = flows
  // 这一趟里解锁的徽章都在 recentBadges 里，靠它比只看返回值更稳
  rewardBadges.value = [...progress.recentBadges].slice(0, 3)
  if (!rewardBadges.value.length && badges.length) rewardBadges.value = badges.slice(0, 3)
  feedback.celebrate(panelRef.value)
}

const earnedStars = computed(() => Math.max(0, progress.stars - starsAtStart.value))

/** 重新走一遍：进度不清，只把这一轮的答题状态归零。 */
function restartFlow() {
  settled = false
  rewardBadges.value = []
  for (const key of Object.keys(done)) done[key] = false
  reached.value = 0
  starsAtStart.value = progress.stars
  progress.clearRecentBadges()
  goPhase('intro', { manual: true })
}

function resetFlow() {
  clearTimers()
  originOpen.value = false
  settled = false
  rewardBadges.value = []
  flowRounds.value = 0
  listenOptions.value = []
  quizOptions.value = []
  for (const key of Object.keys(done)) done[key] = false
  reached.value = 0
  phase.value = 'intro'
  pendingNext.value = null
  stepAnnounce.value = ''
  starsAtStart.value = progress.stars
  progress.clearRecentBadges()
  enterPhase('intro', { manual: true })
}

/* ------------------------------------------------------------ 动效 */

/** 换步骤时面板整块弹进来，步骤条上的当前点跟着跳一下。 */
async function playPhaseTransition() {
  await nextTick()
  if (settings.reduceMotion) return
  const panel = panelRef.value
  if (panel) {
    gsap.fromTo(
      panel,
      { autoAlpha: 0, y: 22, scale: 0.97 },
      {
        autoAlpha: 1,
        y: 0,
        scale: 1,
        duration: 0.42,
        ease: 'back.out(1.5)',
        clearProps: 'opacity,visibility,transform'
      }
    )
    const items = panel.querySelectorAll('.opt, .reward__item')
    if (items.length) {
      gsap.from(items, {
        autoAlpha: 0,
        y: 14,
        duration: 0.34,
        stagger: 0.06,
        delay: 0.1,
        ease: 'back.out(1.6)',
        clearProps: 'opacity,visibility,transform'
      })
    }
  }
  const dot = railRef.value?.querySelector('.rail__step.is-current .rail__dot')
  if (dot) {
    gsap.fromTo(
      dot,
      { scale: 0.55 },
      { scale: 1, duration: 0.5, ease: 'back.out(2.6)', clearProps: 'transform' }
    )
  }
}

watch(phase, playPhaseTransition)

function flash(msg) {
  toast.value = msg
  setTimeout(() => {
    if (toast.value === msg) toast.value = ''
  }, 2600)
}

function markKnown(event) {
  const { justMastered } = progress.recordAnswer(decoded.value, true)
  const anchor = event?.currentTarget ?? panelRef.value
  if (justMastered) feedback.celebrate(anchor)
  else feedback.correct(anchor)
  flash(justMastered ? '太厉害了，这个字已经掌握啦！🏆' : '记住啦！+1 ⭐')
}

function onQuizSkip() {
  flash('跳过描红也没关系，随时可以回来写 ✍️')
  // 跳过不算「写一写」做完了，但流程别停在这儿干等着
  if (phase.value === 'trace') scheduleAdvance('listen', DELAY.skipped)
}

function onQuizComplete({ mistakes }) {
  // 写完一遍才算「会写」，掌握度要靠它才能从「认识了」升到「会写了」。
  progress.markTraced(decoded.value)
  const { justMastered } = progress.recordAnswer(decoded.value, mistakes === 0)
  if (justMastered) {
    feedback.celebrate(strokeBoxRef.value)
    flash('这个字已经掌握啦！🏆')
  } else if (mistakes === 0) {
    feedback.burst(strokeBoxRef.value)
  }
  done.intro = true
  done.trace = true
  // 在哪一步写完的都算数：孩子常常在「认一认」时就自己动手写了
  if (phase.value === 'intro' || phase.value === 'trace') {
    scheduleAdvance('listen', DELAY.traced)
  }
}

function onStrokeDemo({ strokeNum }) {
  flash(`第 ${strokeNum + 1} 笔有点难，先看老师写一遍 ✍️`)
}

function track() {
  if (item.value) progress.visitChar(item.value.char)
}

onMounted(() => {
  if (!item.value) {
    router.replace('/learn')
    return
  }
  resetFlow()
  track()
  playPhaseTransition()
})

watch(decoded, () => {
  if (!item.value) router.replace('/learn')
  else {
    toast.value = ''
    resetFlow()
    track()
  }
})

onBeforeUnmount(clearTimers)
</script>

<template>
  <div v-if="item" class="page detail" :data-phase="phase">
    <!-- 五步进度条：既是导航，也是「现在在第几步」的说明 -->
    <nav ref="railRef" class="rail card" aria-label="单字学习五步">
      <ol class="rail__list">
        <li v-for="(p, i) in PHASES" :key="p.id" class="rail__item">
          <button
            class="rail__step"
            :class="{
              'is-current': phase === p.id,
              'is-done': done[p.id],
              'is-locked': !canJump(p.id)
            }"
            type="button"
            :data-step="p.id"
            :aria-current="phase === p.id ? 'step' : undefined"
            :aria-disabled="canJump(p.id) ? undefined : 'true'"
            :aria-label="`第 ${i + 1} 步 ${p.label}${done[p.id] ? '，已完成' : ''}`"
            @click="onStepClick(p.id)"
          >
            <span class="rail__dot" aria-hidden="true">{{ done[p.id] ? '✓' : p.emoji }}</span>
            <span class="rail__label">{{ p.label }}</span>
          </button>
        </li>
      </ol>
      <p class="sr-only" role="status" aria-live="polite" aria-atomic="true">{{ stepAnnounce }}</p>
    </nav>

    <!-- 主卡片：字形 + 笔顺 -->
    <section class="hero card">
      <div class="hero__info">
        <div class="hero__pinyin-row">
          <button class="hero__pinyin" type="button" @click="say(item.char)">
            <span class="hero__pinyin-text">{{ item.pinyin }}</span>
            <span class="hero__speaker" aria-hidden="true">🔊</span>
            <span class="sr-only">朗读 {{ item.char }}</span>
          </button>
          <span class="pill">{{ item.strokes }} 画</span>
          <span v-if="mastered" class="pill pill--accent">🏆 已掌握</span>
          <span v-else-if="record" class="pill pill--accent">🌱 学过 {{ record.views }} 次</span>
        </div>
        <p class="hero__meaning">{{ item.meaning ?? '正在把这个字的故事翻出来…' }}</p>
        <RouterLink
          v-if="radicalLink"
          class="hero__radical"
          :to="radicalLink"
          @click="sfx.tap()"
        >
          <span class="hero__radical-glyph">{{ radical.glyph }}</span>
          <span>
            部首「{{ radical.name }}」
            <small class="muted">去看看 →</small>
          </span>
        </RouterLink>
        <div v-else-if="radical" class="hero__radical hero__radical--plain">
          <span class="hero__radical-glyph">{{ radical.glyph }}</span>
          <span>部首「{{ radical.name }}」</span>
        </div>
      </div>

      <HanziStrokeBox
        ref="strokeBoxRef"
        class="hero__writer"
        :char="item.char"
        :size="252"
        @quiz-complete="onQuizComplete"
        @quiz-skip="onQuizSkip"
        @stroke-demo="onStrokeDemo"
      />
    </section>

    <!-- 当前这一步 -->
    <section ref="panelRef" class="card stack panel" :data-panel="phase">
      <h3 class="section-title">
        <span class="section-title__emoji" aria-hidden="true">{{ current.emoji }}</span>
        第 {{ phaseIndex(phase) + 1 }} 步 · {{ current.label }}
      </h3>
      <p class="panel__hint muted">{{ current.hint }}</p>

      <!-- 认一认 -->
      <template v-if="phase === 'intro'">
        <div class="intro">
          <button class="btn btn--primary btn--lg intro__say" type="button" @click="heard">
            🔊 听「{{ item.char }}」怎么读
          </button>
          <p class="intro__meaning">{{ item.meaning }}</p>
          <p class="intro__strokes muted">{{ item.strokes }} 画 · 部首「{{ radical ? radical.name : item.radical }}」</p>
        </div>
      </template>

      <!-- 写一写 -->
      <template v-else-if="phase === 'trace'">
        <div class="trace">
          <p class="trace__tip">先点「看笔顺」记住顺序，再在田字格里写一遍。</p>
          <div class="trace__acts">
            <button class="btn btn--ghost" type="button" @click="strokeBoxRef?.play()">
              ▶️ 再看一遍笔顺
            </button>
            <button class="btn btn--accent" type="button" @click="strokeBoxRef?.startQuiz()">
              ✍️ 开始描红
            </button>
          </div>
          <p class="muted trace__note">
            写不动也没关系：按空格键或点「写下一笔」，我来帮忙；同一笔连错 3 次，我会自动示范。
          </p>
        </div>
      </template>

      <!-- 听一听 -->
      <template v-else-if="phase === 'listen'">
        <div class="ask">
          <button class="btn btn--primary ask__play" type="button" @click="playListen">
            🔊 再听一次
          </button>
          <p class="ask__q">刚才读的是哪个字？</p>
          <div class="opts">
            <button
              v-for="o in listenOptions"
              :key="o.char"
              class="opt opt--char"
              :class="{
                'is-right': listenRevealed && o.char === item.char,
                'is-wrong': listenPick === o.char && o.char !== item.char
              }"
              type="button"
              :data-char="o.char"
              :disabled="listenRevealed"
              @click="onListenPick(o, $event)"
            >
              {{ o.char }}
            </button>
          </div>
          <p v-if="listenRevealed" class="ask__feedback">
            {{ listenPick === item.char ? '答对啦！就是这个字 🎉' : `正确答案是「${item.char}」` }}
          </p>
        </div>
      </template>

      <!-- 考一考 -->
      <template v-else-if="phase === 'quiz'">
        <div class="ask">
          <p class="ask__q">「{{ item.char }}」是什么意思？</p>
          <div class="opts opts--text">
            <button
              v-for="o in quizOptions"
              :key="o.char"
              class="opt opt--text"
              :class="{
                'is-right': quizRevealed && o.char === item.char,
                'is-wrong': quizPick === o.char && o.char !== item.char
              }"
              type="button"
              :data-char="o.char"
              :disabled="quizRevealed"
              @click="onQuizPick(o, $event)"
            >
              {{ o.meaning }}
            </button>
          </div>
          <p v-if="quizRevealed" class="ask__feedback">
            {{ quizPick === item.char ? '意思也对上了，真棒！' : `「${item.char}」的意思是：${item.meaning}` }}
          </p>
        </div>
      </template>

      <!-- 领奖励 -->
      <template v-else>
        <div class="reward">
          <p v-if="!flowReady" class="reward__todo">
            还差 {{ missingSteps.join('、') }} 没做完，做完这一趟才算完整走了一遍哦。
          </p>
          <template v-else>
            <div class="reward__stats">
              <span class="reward__item pill pill--accent">⭐ 这一趟 +{{ earnedStars }} 星</span>
              <span class="reward__item pill">🧭 「{{ item.char }}」完整学过 {{ flowRounds }} 遍</span>
              <span class="reward__item pill">{{ mastered ? '🏆 已掌握' : '🌱 继续加油' }}</span>
            </div>
            <div v-if="rewardBadges.length" class="reward__badges">
              <p class="reward__badges-title">🎖️ 新徽章到手！</p>
              <div class="badgerow">
                <span v-for="b in rewardBadges" :key="b.id" class="badgechip reward__item">
                  <span class="badgechip__emoji" aria-hidden="true">{{ b.emoji }}</span>
                  <span>
                    <strong>{{ b.name }}</strong>
                    <small class="muted">{{ b.desc }}</small>
                  </span>
                </span>
              </div>
            </div>
            <p v-else class="muted reward__item">
              继续学下去，成就墙上的徽章会一枚枚亮起来。
            </p>
          </template>
          <div class="reward__acts">
            <button class="btn btn--ghost" type="button" @click="restartFlow">🔁 再走一遍</button>
            <RouterLink
              v-if="next"
              class="btn btn--primary"
              :to="`/learn/${encodeURIComponent(next.char)}`"
              @click="sfx.tap()"
            >
              下一个字「{{ next.char }}」 →
            </RouterLink>
          </div>
        </div>
      </template>

      <!-- 自动衔接：先说清楚要去哪，再给一个按停的机会 -->
      <div v-if="pendingNext" class="autonext">
        <span class="autonext__text">马上进入「{{ pendingNext.label }}」…</span>
        <button class="btn btn--ghost btn--sm" type="button" @click="holdOn">✋ 等一下</button>
      </div>
      <button
        v-else-if="phase !== 'reward'"
        class="btn btn--ghost panel__next"
        type="button"
        @click="nextStep"
      >
        下一步：{{ phaseMeta(phaseAfter(phase)).label }} →
      </button>
    </section>

    <!-- 播报区常驻，读屏才认得出后来写进去的提示；视觉气泡另走一份 -->
    <p class="sr-only" role="status" aria-live="polite" aria-atomic="true">{{ toast }}</p>
    <p v-if="toast" class="toast" aria-hidden="true">{{ toast }}</p>

    <VoiceNotice fallback="拼音就在字的上面，家长可以照着拼音读给孩子听。" />

    <!-- 这个字的来历：有字源语料的字才出现，展开才加载演变动画 -->
    <section v-if="hasOrigin" class="card stack origin">
      <h3 class="section-title">
        <span class="section-title__emoji" aria-hidden="true">🏺</span>
        这个字的来历
        <RouterLink
          class="origin__more"
          :to="`/etymology/${encodeURIComponent(item.char)}`"
          @click="sfx.tap()"
        >
          去字源馆 →
        </RouterLink>
      </h3>
      <button
        class="btn btn--accent btn--block"
        type="button"
        :aria-expanded="originOpen"
        aria-controls="char-origin-panel"
        @click="toggleOrigin"
      >
        {{ originOpen ? '收起来' : `🏺 看看「${item.char}」当初是怎么来的` }}
      </button>
      <div id="char-origin-panel" class="origin__panel">
        <EtymologyStage v-if="originOpen" :char="item.char" :size="176" />
      </div>
    </section>

    <!-- 组词 -->
    <section v-if="item.words" class="card stack">
      <h3 class="section-title">
        <span class="section-title__emoji" aria-hidden="true">🧺</span>
        跟它组个词
      </h3>
      <ul class="words">
        <li v-for="w in item.words" :key="w.w">
          <button class="word" type="button" @click="say(w.w)">
            <span class="word__pinyin">{{ w.p }}</span>
            <span class="word__text">{{ w.w }}</span>
            <span class="word__speaker" aria-hidden="true">🔊</span>
          </button>
        </li>
      </ul>
    </section>

    <!-- 例句 -->
    <section v-if="item.sentence" class="card stack">
      <h3 class="section-title">
        <span class="section-title__emoji" aria-hidden="true">💬</span>
        读一句话
      </h3>
      <button class="sentence" type="button" @click="say(item.sentence.text, settings.speechRate - 0.05)">
        <span v-if="settings.showPinyin" class="sentence__pinyin">{{ item.sentence.p }}</span>
        <span class="sentence__text">
          <span
            v-for="(ch, i) in item.sentence.text"
            :key="`${ch}-${i}`"
            class="sentence__char"
            :class="{ 'is-target': ch === item.char }"
          >{{ ch }}</span>
        </span>
        <span class="sentence__hint muted">点一下，听老师读 🔊</span>
      </button>
    </section>

    <!-- 底部操作 -->
    <section class="actions">
      <button class="btn btn--primary btn--lg btn--block" type="button" @click="markKnown($event)">
        👍 我认识这个字啦
      </button>
      <div class="actions__nav">
        <RouterLink
          class="btn btn--ghost"
          :class="{ 'is-disabled': !prev }"
          :to="prev ? `/learn/${encodeURIComponent(prev.char)}` : ''"
          @click="(e) => (!prev ? e.preventDefault() : sfx.tap())"
        >
          ← {{ prev ? prev.char : '没有了' }}
        </RouterLink>
        <RouterLink class="btn btn--ghost" to="/learn" @click="sfx.tap()">📋 字表</RouterLink>
        <RouterLink
          class="btn btn--ghost"
          :class="{ 'is-disabled': !next }"
          :to="next ? `/learn/${encodeURIComponent(next.char)}` : ''"
          @click="(e) => (!next ? e.preventDefault() : sfx.tap())"
        >
          {{ next ? next.char : '没有了' }} →
        </RouterLink>
      </div>
    </section>
  </div>
</template>

<style scoped>
.detail {
  position: relative;
}

/* ---------------- 五步进度条 ---------------- */
.rail {
  padding: 12px;
}

.rail__list {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 6px;
  list-style: none;
  margin: 0;
  padding: 0;
}

.rail__step {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  padding: 8px 4px;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-soft);
  font-weight: 700;
  transition: background var(--dur-fast) ease, color var(--dur-fast) ease;
}

.rail__dot {
  display: grid;
  place-items: center;
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: var(--surface-sunken);
  border: 2px solid var(--stroke-hint);
  font-size: 1.15rem;
  line-height: 1;
}

.rail__label {
  font-size: 0.78rem;
  white-space: nowrap;
}

.rail__step.is-done {
  color: var(--success);
}

.rail__step.is-done .rail__dot {
  background: color-mix(in srgb, var(--success) 22%, var(--surface));
  border-color: var(--success);
  color: var(--success);
}

.rail__step.is-current {
  background: var(--accent-soft);
  color: var(--text-strong);
}

.rail__step.is-current .rail__dot {
  background: var(--surface-strong);
  border-color: var(--brand);
  box-shadow: var(--shadow-sm);
}

.rail__step.is-locked {
  opacity: 0.45;
}

/* ---------------- 当前步骤面板 ---------------- */
.panel__hint {
  font-size: 0.85rem;
  margin-top: -4px;
}

.panel__next {
  align-self: flex-end;
}

.intro,
.trace,
.ask,
.reward {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
  align-items: flex-start;
}

.intro__say {
  align-self: stretch;
}

.intro__meaning {
  font-size: 1.02rem;
  line-height: 1.8;
}

.intro__strokes,
.trace__note {
  font-size: 0.8rem;
}

.trace__tip,
.ask__q {
  font-size: 1.05rem;
  font-weight: 800;
  color: var(--text-strong);
}

.trace__acts,
.reward__acts {
  display: flex;
  flex-wrap: wrap;
  gap: var(--gap-sm);
}

.ask {
  align-self: stretch;
}

.opts {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--gap-sm);
  width: 100%;
}

.opts--text {
  grid-template-columns: 1fr;
}

.opt {
  padding: 14px 12px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  border: 3px solid transparent;
  color: var(--text-strong);
  font-weight: 700;
  transition: transform var(--dur-fast) var(--ease-pop), border-color var(--dur-fast) ease;
}

.opt:hover:not(:disabled) {
  border-color: color-mix(in srgb, var(--brand) 45%, transparent);
}

.opt:active:not(:disabled) {
  transform: scale(0.97);
}

.opt--char {
  font-size: clamp(2rem, 9vw, 2.6rem);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
  line-height: 1.2;
}

.opt--text {
  text-align: left;
  font-size: 0.95rem;
  font-weight: 600;
  line-height: 1.6;
}

.opt.is-right {
  border-color: var(--success);
  background: color-mix(in srgb, var(--success) 18%, var(--surface-sunken));
}

.opt.is-wrong {
  border-color: var(--danger);
  background: color-mix(in srgb, var(--danger) 14%, var(--surface-sunken));
}

.opt:disabled {
  opacity: 1;
}

.ask__feedback {
  font-weight: 800;
  color: var(--success);
}

/* ---------------- 领奖励 ---------------- */
.reward {
  align-self: stretch;
}

.reward__stats,
.badgerow {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.reward__badges {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.reward__badges-title {
  font-weight: 800;
  color: var(--text-strong);
}

.reward__todo {
  font-weight: 700;
  color: var(--text-soft);
}

.badgechip {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 8px 16px 8px 8px;
  border-radius: var(--radius-pill);
  background: var(--accent-soft);
}

.badgechip strong {
  display: block;
  color: var(--text-strong);
  font-size: 0.95rem;
}

.badgechip small {
  font-size: 0.75rem;
}

.badgechip__emoji {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: var(--surface-strong);
  font-size: 1.2rem;
}

/* ---------------- 自动衔接 ---------------- */
.autonext {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--gap-sm);
  flex-wrap: wrap;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  border: 2px dashed color-mix(in srgb, var(--brand) 45%, transparent);
}

.autonext__text {
  font-weight: 700;
  color: var(--text-strong);
}

.hero {
  display: flex;
  gap: var(--gap-lg);
  align-items: center;
}

.hero__info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
  min-width: 0;
}

.hero__pinyin-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.hero__pinyin {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 18px;
  border-radius: var(--radius-pill);
  background: linear-gradient(180deg, var(--brand) 0%, var(--brand-strong) 100%);
  color: var(--text-invert);
  box-shadow: var(--shadow-sm);
  transition: transform var(--dur-fast) var(--ease-pop);
}

.hero__pinyin:active {
  transform: scale(0.94);
}

.hero__pinyin-text {
  font-size: 1.35rem;
  font-weight: 800;
  letter-spacing: 0.05em;
}

.hero__speaker {
  font-size: 1.1rem;
}

.hero__meaning {
  font-size: 1.05rem;
  line-height: 1.8;
  color: var(--text);
}

.hero__radical {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  align-self: flex-start;
  padding: 8px 16px 8px 8px;
  border-radius: var(--radius-pill);
  background: var(--accent-soft);
  font-weight: 700;
  color: var(--text-strong);
}

/* 没有讲解页的兜底部首：同样的信息，但不做成可点的样子 */
.hero__radical--plain {
  background: var(--surface-sunken);
  color: var(--text);
}

.hero__radical-glyph {
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--surface-strong);
  font-size: 1.3rem;
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', serif;
}

.hero__radical small {
  font-size: 0.75rem;
  margin-left: 4px;
}

.hero__writer {
  flex: none;
}

.toast {
  align-self: center;
  padding: 10px 22px;
  border-radius: var(--radius-pill);
  background: var(--success);
  color: var(--text-invert);
  font-weight: 800;
  box-shadow: var(--shadow-md);
  animation: pop-in var(--dur-mid) var(--ease-pop);
}

.origin__more {
  margin-left: auto;
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--text-soft);
}

.origin__panel:empty {
  display: none;
}

.words {
  display: grid;
  gap: var(--gap-sm);
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
}

.word {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 1px;
  position: relative;
  padding: 12px 40px 12px 16px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  border: 2px solid transparent;
  text-align: left;
  transition: transform var(--dur-fast) var(--ease-pop), border-color var(--dur-fast) ease;
}

.word:hover {
  border-color: color-mix(in srgb, var(--brand) 45%, transparent);
}

.word:active {
  transform: scale(0.97);
}

.word__pinyin {
  font-size: 0.78rem;
  color: var(--text-soft);
}

.word__text {
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--text-strong);
}

.word__speaker {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 1.1rem;
  opacity: 0.65;
}

.sentence {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
  padding: var(--gap-md);
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  text-align: left;
  transition: transform var(--dur-fast) var(--ease-pop);
}

.sentence:active {
  transform: scale(0.99);
}

.sentence__pinyin {
  font-size: 0.85rem;
  color: var(--text-soft);
  letter-spacing: 0.04em;
}

.sentence__text {
  font-size: clamp(1.4rem, 5.5vw, 1.9rem);
  font-weight: 700;
  color: var(--text-strong);
  line-height: 1.7;
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

.sentence__char.is-target {
  color: var(--brand-strong);
  border-bottom: 3px solid var(--brand);
  border-radius: 2px;
}

.sentence__hint {
  font-size: 0.78rem;
}

.actions {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
}

.actions__nav {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: var(--gap-sm);
}

.actions__nav .btn.is-disabled {
  opacity: 0.4;
  pointer-events: none;
}

@media (max-width: 720px) {
  .hero {
    flex-direction: column-reverse;
    align-items: stretch;
  }
  .hero__writer {
    align-self: center;
  }
}

@media (max-width: 420px) {
  .rail__dot {
    width: 36px;
    height: 36px;
    font-size: 1rem;
  }
  .rail__label {
    font-size: 0.7rem;
  }
}
</style>
