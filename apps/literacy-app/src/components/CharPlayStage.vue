<script setup>
/**
 * 「玩」这一步的舞台（ROUND15_H2）。
 *
 * 洪恩的做法是每个字先玩一分钟情境小游戏再开始学。我们照做，但玩法不是一字一
 * 美术，而是几个模板 + 一份可增长的脚本表（data/char-play.js）：舞台只认模板 id，
 * 拿到什么就渲染什么，所以 1820 个字里没人手写过的那些，进来照样有得玩。
 *
 * 五个模板：
 *   tap-reveal   点开盖子，看看和这个字有关的东西
 *   morph-story  图一帧帧变成字
 *   emoji-hunt   在一堆图里找出目标
 *   drag-parts   把对的偏旁送回字里
 *   rain-catch   落下来的东西接住对的（减少动态时改成静止网格，题目一样）
 *
 * 三条底线，和 EtymologyStage 一致：
 *  1. 永远有得玩：getCharPlay() 不返回 null，模板不认识就退回点一点。
 *  2. 永远能走完：右下角「跳过这一步」始终在，跳过也照样 emit complete，
 *     父级的五步流程不会因为一个小游戏卡住（WCAG §2.2.1 的思路）。
 *  3. 减少动态时不建任何时间线：下雨改成静止网格，变一变改成一按一帧，
 *     信息量不变，只是不动。
 *
 * 对外只有两件事：`complete`（玩完了，payload 里带 skipped）与 `skip`。
 */
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import gsap from 'gsap'
import OpenMojiIcon from '@shared/components/OpenMojiIcon.vue'
import { getCharPlay } from '@/data/char-play.js'
import { useFeedback } from '@/composables/useFeedback.js'
import { useSettingsStore } from '@/stores/settings.js'
import { sfx } from '@/utils/sfx.js'

const props = defineProps({
  char: { type: String, required: true },
  /** 父级已经取好了就直接传进来，省一次解析；不传就自己去 getCharPlay。 */
  play: { type: Object, default: null },
  /** 关掉之后「接一接」不自动下雨，等父级把这一步切到台前再开。 */
  autoStart: { type: Boolean, default: true }
})

const emit = defineEmits(['complete', 'skip', 'interact'])

// 单测 / 脚本里没有 pinia 也要能挂载，取不到设置就退回系统偏好
let settings = null
try {
  settings = useSettingsStore()
} catch {
  settings = null
}
const feedback = useFeedback()

const stageRef = ref(null)
const rainRef = ref(null)
const morphRef = ref(null)
const slotRef = ref(null)

const scene = computed(() => props.play ?? getCharPlay(props.char))
const bag = computed(() => scene.value?.props ?? {})
const template = computed(() => scene.value?.template ?? 'tap-reveal')

const reduced = computed(
  () =>
    settings?.reduceMotion === true ||
    (typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches === true)
)

/** playing | done */
const state = ref('playing')
const announce = ref('')
/** 这一关孩子真的动了几下手，父级可以拿它判断「玩过了」还是「跳过了」。 */
const interactions = ref(0)
let finished = false

/* --------------------------------------------------------------- 各模板状态 */

const opened = reactive(new Set())
const found = reactive(new Set())
const frame = ref(0)
const placed = ref(false)
const wrongOption = ref('')

let rainTweens = []
let morphTween = null

function killMotion() {
  for (const t of rainTweens) t.kill()
  rainTweens = []
  morphTween?.kill()
  morphTween = null
}

function reset() {
  killMotion()
  opened.clear()
  found.clear()
  frame.value = 0
  placed.value = false
  wrongOption.value = ''
  interactions.value = 0
  finished = false
  state.value = 'playing'
  announce.value = scene.value?.narration ?? ''
  if (props.autoStart && template.value === 'rain-catch' && !reduced.value) nextTick(startRain)
}

/* ------------------------------------------------------------------ 完成 */

function finish({ skipped = false } = {}) {
  if (finished) return
  finished = true
  killMotion()
  state.value = 'done'
  if (skipped) {
    announce.value = '这一关先跳过，我们去认一认这个字。'
  } else {
    announce.value = `玩好啦！这就是「${props.char}」。`
    feedback.celebrate(stageRef.value)
  }
  emit('complete', {
    char: props.char,
    template: template.value,
    templateFallback: scene.value?.templateFallback === true,
    interactions: interactions.value,
    skipped
  })
}

function onSkip() {
  sfx.tap()
  emit('skip', { char: props.char, template: template.value })
  finish({ skipped: true })
}

function replay() {
  sfx.tap()
  reset()
}

function touched() {
  interactions.value += 1
  emit('interact', { char: props.char, template: template.value, count: interactions.value })
}

/* -------------------------------------------------------------- 点一点 */

const cards = computed(() => bag.value.items ?? [])

function openCard(item, event) {
  if (state.value === 'done' || opened.has(item.id)) return
  opened.add(item.id)
  touched()
  feedback.tap(event?.currentTarget)
  feedback.pop(event?.currentTarget)
  announce.value = `${item.label}。还剩 ${cards.value.length - opened.size} 个盖子。`
  if (opened.size >= cards.value.length) finish()
}

/* -------------------------------------------------------------- 变一变 */

const frames = computed(() => bag.value.frames ?? [])
const currentFrame = computed(() => frames.value[Math.min(frame.value, frames.value.length - 1)])

function stepFrame(event) {
  if (state.value === 'done') return
  const last = frames.value.length - 1
  if (frame.value >= last) {
    finish()
    return
  }
  frame.value += 1
  touched()
  feedback.tap(event?.currentTarget)
  announce.value = currentFrame.value?.caption ?? ''

  if (!reduced.value && morphRef.value) {
    morphTween?.kill()
    morphTween = gsap.fromTo(
      morphRef.value,
      { scale: 0.86, opacity: 0.2, rotate: -3 },
      { scale: 1, opacity: 1, rotate: 0, duration: 0.45, ease: 'back.out(1.7)' }
    )
  }
  if (frame.value >= last) window.setTimeout(() => finish(), reduced.value ? 200 : 700)
}

/* -------------------------------------------------------------- 找一找 */

const cells = computed(() => bag.value.cells ?? [])
const need = computed(() => Math.max(1, Number(bag.value.need) || 3))

function huntCell(cell, event) {
  if (state.value === 'done' || found.has(cell.id)) return
  touched()
  if (!cell.hit) {
    feedback.wrong(event?.currentTarget)
    announce.value = `这个不是 ${bag.value.target}，再找找看。`
    return
  }
  found.add(cell.id)
  feedback.correct(event?.currentTarget, { cueArg: found.size })
  const left = need.value - found.size
  announce.value = left > 0 ? `找到啦！还差 ${left} 个。` : '全找到啦！'
  if (found.size >= need.value) finish()
}

/* -------------------------------------------------------------- 拼一拼 */

const options = computed(() => bag.value.options ?? [])

function pickPart(option, event) {
  if (state.value === 'done' || placed.value) return
  touched()
  if (!option.correct) {
    wrongOption.value = option.id
    feedback.wrong(event?.currentTarget)
    announce.value = `「${option.glyph}」不是它的偏旁。${bag.value.hint ?? ''}`
    return
  }
  wrongOption.value = ''
  placed.value = true
  feedback.correct(event?.currentTarget, { cueArg: 2 })
  announce.value = `对啦！「${bag.value.whole}」带的是「${option.glyph}」${bag.value.answerName ?? ''}。`
  if (!reduced.value && slotRef.value) {
    gsap.fromTo(
      slotRef.value,
      { scale: 0.5, opacity: 0 },
      { scale: 1, opacity: 1, duration: 0.5, ease: 'back.out(2)' }
    )
  }
  window.setTimeout(() => finish(), reduced.value ? 200 : 600)
}

/* -------------------------------------------------------------- 接一接 */

const drops = computed(() => bag.value.drops ?? [])
/** 减少动态时用同一批道具铺成静止网格：题目一样，只是不掉下来。 */
const rainCells = computed(() => bag.value.staticCells ?? cells.value)

function startRain() {
  killMotion()
  const host = rainRef.value
  if (!host) return
  for (const el of host.querySelectorAll('.play__drop')) {
    const dur = (Number(el.dataset.duration) || 3000) / 1000
    const delay = (Number(el.dataset.delay) || 0) / 1000
    rainTweens.push(
      gsap.fromTo(
        el,
        { yPercent: -140, opacity: 1 },
        {
          yPercent: 620,
          duration: dur,
          delay,
          ease: 'none',
          repeat: -1,
          repeatDelay: 0.6
        }
      )
    )
  }
}

function catchDrop(drop, event) {
  if (state.value === 'done' || found.has(drop.id)) return
  touched()
  if (!drop.hit) {
    feedback.wrong(event?.currentTarget)
    announce.value = `这个不是 ${bag.value.target}，看准了再接。`
    return
  }
  found.add(drop.id)
  feedback.correct(event?.currentTarget, { cueArg: found.size })
  const el = event?.currentTarget
  const tween = rainTweens.find((t) => t.targets()[0] === el)
  tween?.kill()
  if (el && !reduced.value) {
    gsap.to(el, { scale: 1.6, opacity: 0, duration: 0.32, ease: 'power2.out' })
  }
  const left = need.value - found.size
  announce.value = left > 0 ? `接住啦！还差 ${left} 个。` : '都接住啦！'
  if (found.size >= need.value) finish()
}

/* ------------------------------------------------------------------ 进度 */

const progressText = computed(() => {
  if (state.value === 'done') return '这一关玩好啦'
  if (template.value === 'tap-reveal') return `已点开 ${opened.size} / ${cards.value.length}`
  if (template.value === 'morph-story') return `第 ${frame.value + 1} 帧 / 共 ${frames.value.length} 帧`
  if (template.value === 'drag-parts') return placed.value ? '拼好啦' : '选一个偏旁'
  return `已找到 ${found.size} / ${need.value}`
})

watch(() => [props.char, template.value, reduced.value], reset, { immediate: true })

watch(
  () => props.autoStart,
  (on) => {
    if (on && template.value === 'rain-catch' && !reduced.value) nextTick(startRain)
  }
)

onBeforeUnmount(killMotion)

defineExpose({ finish, replay, skip: onSkip })
</script>

<template>
  <section
    ref="stageRef"
    class="play"
    :class="{ 'play--static': reduced, 'play--done': state === 'done' }"
    :style="{ '--play-accent': scene.accent }"
    :data-char="char"
    :data-template="template"
    :data-state="state"
    :data-fallback="scene.templateFallback ? 'true' : 'false'"
    :aria-label="`「${char}」的玩一玩：${scene.templateLabel}`"
  >
    <header class="play__head">
      <p class="play__badge">
        <span aria-hidden="true">{{ scene.themeEmoji }}</span>
        <strong>{{ scene.templateLabel }}</strong>
        <span class="muted">{{ scene.themeLabel }}</span>
      </p>
      <p class="play__narration">{{ scene.narration }}</p>
    </header>

    <!-- 点一点：盖子下面藏着和这个字有关的东西 -->
    <ul v-if="template === 'tap-reveal'" class="play__cards">
      <li v-for="item in cards" :key="item.id">
        <button
          type="button"
          class="play__card"
          :class="{ 'is-open': opened.has(item.id) }"
          :aria-pressed="opened.has(item.id)"
          :aria-label="opened.has(item.id) ? item.label : '还没打开的盖子'"
          @click="openCard(item, $event)"
        >
          <span v-if="!opened.has(item.id)" class="play__cover" aria-hidden="true">?</span>
          <template v-else>
            <OpenMojiIcon class="play__icon" :emoji="item.emoji" :size="46" />
            <span v-if="item.isChar" class="play__glyph play__glyph--sm">{{ char }}</span>
            <span class="play__label">{{ item.label }}</span>
          </template>
        </button>
      </li>
    </ul>

    <!-- 变一变：图一帧帧变成字 -->
    <div v-else-if="template === 'morph-story'" class="play__morph">
      <div ref="morphRef" class="play__morph-slot">
        <OpenMojiIcon
          v-if="currentFrame?.emoji"
          class="play__icon play__icon--big"
          :emoji="currentFrame.emoji"
          :size="96"
          :label="currentFrame.caption"
        />
        <span v-if="currentFrame?.glyph" class="play__glyph">{{ currentFrame.glyph }}</span>
      </div>
      <p class="play__caption">{{ currentFrame?.caption }}</p>
      <button type="button" class="btn btn--primary" @click="stepFrame($event)">
        {{ frame >= frames.length - 1 ? '玩好啦' : (bag.button ?? '变！') }}
      </button>
    </div>

    <!-- 找一找 / 接一接（静止版）：在一堆图里挑出对的 -->
    <div
      v-else-if="template === 'emoji-hunt' || (template === 'rain-catch' && reduced)"
      class="play__grid"
    >
      <button
        v-for="cell in template === 'emoji-hunt' ? cells : rainCells"
        :key="cell.id"
        type="button"
        class="play__cell"
        :class="{ 'is-found': found.has(cell.id) }"
        :disabled="found.has(cell.id)"
        :aria-label="cell.label"
        @click="huntCell(cell, $event)"
      >
        <OpenMojiIcon class="play__icon" :emoji="cell.emoji" :size="38" />
      </button>
    </div>

    <!-- 拼一拼：把对的偏旁送回字里 -->
    <div v-else-if="template === 'drag-parts'" class="play__assemble">
      <div class="play__whole">
        <span ref="slotRef" class="play__slot" :class="{ 'is-filled': placed }">
          {{ placed ? bag.answer : '？' }}
        </span>
        <span class="play__glyph">{{ bag.whole }}</span>
      </div>
      <p class="play__caption">{{ placed ? bag.hint : '哪个偏旁是它的？' }}</p>
      <ul class="play__parts">
        <li v-for="option in options" :key="option.id">
          <button
            type="button"
            class="play__part"
            :class="{ 'is-wrong': wrongOption === option.id, 'is-right': placed && option.correct }"
            :disabled="placed"
            :aria-label="`${option.glyph} ${option.name}`"
            @click="pickPart(option, $event)"
          >
            <span class="play__part-glyph">{{ option.glyph }}</span>
            <span class="play__label">{{ option.name }}</span>
          </button>
        </li>
      </ul>
    </div>

    <!-- 接一接：落下来的东西，接住对的 -->
    <div v-else ref="rainRef" class="play__rain">
      <button
        v-for="drop in drops"
        :key="drop.id"
        type="button"
        class="play__drop"
        :class="{ 'is-caught': found.has(drop.id) }"
        :style="{ left: `${drop.x}%` }"
        :data-delay="drop.delay"
        :data-duration="drop.duration"
        :disabled="found.has(drop.id)"
        :aria-label="drop.label"
        @click="catchDrop(drop, $event)"
      >
        <OpenMojiIcon class="play__icon" :emoji="drop.emoji" :size="40" />
      </button>
      <p class="play__ground">接住 {{ bag.target }}</p>
    </div>

    <footer class="play__foot">
      <p class="play__progress">{{ progressText }}</p>
      <div class="play__acts">
        <button v-if="state === 'done'" type="button" class="btn btn--ghost btn--sm" @click="replay">
          🔁 再玩一次
        </button>
        <button v-else type="button" class="btn btn--ghost btn--sm" @click="onSkip">
          ⏭️ 跳过这一步
        </button>
      </div>
    </footer>

    <p class="sr-only" role="status" aria-live="polite" aria-atomic="true">{{ announce }}</p>
  </section>
</template>

<style scoped>
.play {
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
  width: 100%;
  padding: var(--card-pad);
  border-radius: var(--radius-lg);
  background: var(--surface);
  border: 2px solid var(--surface-border);
  border-top: 6px solid var(--play-accent, var(--brand));
}

.play__head {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.play__badge {
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-size: var(--fs-sm);
}

.play__badge strong {
  color: var(--text-strong);
}

.play__narration {
  font-size: var(--fs-md);
  line-height: var(--lh-loose);
  color: var(--text);
}

/* ------------------------------------------------------------ 点一点 */

.play__cards {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--gap-sm);
  list-style: none;
  margin: 0;
  padding: 0;
}

.play__card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  width: 88px;
  min-height: var(--tap-hero, 96px);
  padding: var(--gap-xs);
  border-radius: var(--radius-md);
  border: 2px dashed var(--stroke-hint);
  background: var(--surface-sunken);
  cursor: pointer;
}

.play__card.is-open {
  border-style: solid;
  border-color: var(--play-accent, var(--brand));
  background: var(--surface);
}

.play__cover {
  font-size: var(--fs-xl);
  font-weight: var(--fw-black);
  color: var(--text-soft);
}

/* ------------------------------------------------------------ 变一变 */

.play__morph {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--gap-sm);
}

.play__morph-slot {
  position: relative;
  display: grid;
  place-items: center;
  gap: var(--gap-xs);
  min-height: 132px;
  padding: var(--gap-sm);
}

.play__morph-slot .play__icon--big + .play__glyph {
  /* 中间那帧图和字叠在一处，孩子的视线不用来回跳 */
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  opacity: 0.92;
}

/* ------------------------------------------------------------ 找一找 */

.play__grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--gap-xs);
}

.play__cell {
  display: grid;
  place-items: center;
  min-height: var(--tap-comfy, 56px);
  padding: var(--gap-2xs);
  border-radius: var(--radius-sm);
  border: 2px solid var(--surface-border);
  background: var(--surface-sunken);
  cursor: pointer;
}

.play__cell.is-found {
  border-color: var(--success);
  background: var(--surface);
  opacity: 0.55;
}

/* ------------------------------------------------------------ 拼一拼 */

.play__assemble {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--gap-sm);
}

.play__whole {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
}

.play__slot {
  display: grid;
  place-items: center;
  width: 64px;
  height: 64px;
  border-radius: var(--radius-md);
  border: 2px dashed var(--stroke-hint);
  background: var(--surface-sunken);
  font-family: var(--font-hanzi);
  font-size: var(--fs-xl);
  color: var(--text-soft);
}

.play__slot.is-filled {
  border-style: solid;
  border-color: var(--success);
  color: var(--text-strong);
}

.play__parts {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--gap-sm);
  list-style: none;
  margin: 0;
  padding: 0;
}

.play__part {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  min-width: var(--tap-min, 44px);
  min-height: var(--tap-comfy, 56px);
  padding: var(--gap-2xs) var(--gap-xs);
  border-radius: var(--radius-md);
  border: 2px solid var(--surface-border);
  background: var(--surface-sunken);
  cursor: pointer;
}

.play__part-glyph {
  font-family: var(--font-hanzi);
  font-size: var(--fs-lg);
  color: var(--text-strong);
}

.play__part.is-right {
  border-color: var(--success);
}

.play__part.is-wrong {
  border-color: var(--danger);
}

/* ------------------------------------------------------------ 接一接 */

.play__rain {
  position: relative;
  overflow: hidden;
  min-height: 240px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  border: 2px solid var(--surface-border);
}

.play__drop {
  position: absolute;
  top: 0;
  display: grid;
  place-items: center;
  min-width: var(--tap-min, 44px);
  min-height: var(--tap-min, 44px);
  padding: 0;
  border: 0;
  background: none;
  cursor: pointer;
}

.play__drop.is-caught {
  opacity: 0;
  pointer-events: none;
}

.play__ground {
  position: absolute;
  inset-inline: 0;
  bottom: 0;
  padding: var(--gap-2xs);
  text-align: center;
  font-size: var(--fs-sm);
  color: var(--text-soft);
  background: var(--surface);
  border-top: 2px dashed var(--stroke-hint);
}

/* ------------------------------------------------------------ 公共 */

/*
 * OpenMoji 只随包带了三十多个界面图标，字表里的卡片图标多数还没有对应 SVG，
 * OpenMojiIcon 这时会退回系统 emoji 文本——那条分支不吃 size 属性，
 * 字号得由这里给，否则落物和卡片会缩成一行小字。
 */
.play__icon {
  font-size: 34px;
  line-height: 1;
}

.play__icon--big {
  font-size: 84px;
}

.play__glyph {
  font-family: var(--font-hanzi);
  font-size: var(--fs-display);
  line-height: 1;
  color: var(--text-strong);
}

.play__glyph--sm {
  font-size: var(--fs-lg);
}

.play__label {
  font-size: var(--fs-xs);
  line-height: var(--lh-base);
  text-align: center;
  color: var(--text-soft);
}

.play__caption {
  font-size: var(--fs-sm);
  color: var(--text-soft);
  text-align: center;
}

.play__foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--gap-sm);
}

.play__progress {
  font-size: var(--fs-sm);
  color: var(--text-soft);
}

.play__acts {
  display: flex;
  gap: var(--gap-sm);
}

.play--done .play__narration::after {
  content: ' 🎉';
}

/* 减少动态：不建时间线，落物那一关直接换成静止网格（模板层已备好道具） */
.play--static .play__cell,
.play--static .play__card,
.play--static .play__part {
  transition: none;
}

@media (max-width: 420px) {
  .play__grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .play__card {
    width: 76px;
  }
}
</style>
