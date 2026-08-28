<script setup>
/**
 * 「玩」这一步的舞台（ROUND15_H2）。
 *
 * 洪恩每个字先玩一分钟情境小游戏再开始学。我们照做，但玩法不是一字一美术：
 * 剧本从三处来（人手写的富脚本、生成器补齐的全库条目、字表兜底合成），
 * data/char-play.js 把三套方言归一成六种互动，舞台只认这六种：
 *
 *   pick      从几个选项里点中对的（找一找 / 揭卡片 / 听音点）
 *   catch     一堆东西里点够次数（接字雨 / 数一数 / 戳泡泡）
 *   assemble  把零件送回位置（拼部件 / 补词语）
 *   watch     一帧一帧看完，点一下推进（图变字 / 跟着做）
 *   match     左边一个右边一个，配成一对（连一连 / 分一分）
 *   push      顺着一个方向推、拉、举（划一划 / 带一带）
 *
 * 三条底线：
 *  1. 永远有得玩：getCharPlay() 不返回 null，道具不齐由归一层补齐。
 *  2. 永远能走完：右下角「跳过这一步」始终在，跳过也照样 emit complete，
 *     父级的五步流程不会被一个小游戏卡住（WCAG §2.2.1 的思路）。
 *  3. 减少动态时不建任何时间线：会掉的东西改成静止网格，推一推改成直接就位，
 *     题目和通关条件一个字都不变。
 *
 * 对外只有两件事：`complete`（玩完了，payload 带 skipped）与 `skip`。
 */
import { computed, nextTick, onBeforeUnmount, reactive, ref, watch } from 'vue'
import gsap from 'gsap'
import OpenMojiIcon from '@shared/components/OpenMojiIcon.vue'
import { getCharPlay, getCharPlayAsync } from '@/data/char-play.js'
import { useFeedback } from '@/composables/useFeedback.js'
import { useSettingsStore } from '@/stores/settings.js'
import { speak } from '@/utils/speech.js'
import { sfx } from '@/utils/sfx.js'

const props = defineProps({
  char: { type: String, required: true },
  /** 父级已经取好了就直接传进来，省一次解析；不传就自己去 getCharPlay。 */
  play: { type: Object, default: null },
  /** 关掉之后会掉的道具不自动落，等父级把这一步切到台前再开。 */
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
const frameRef = ref(null)
const heroRef = ref(null)

/**
 * 手写剧本按单元分片，用到才下载（ROUND18_H3）。取剧本因此走异步口
 * getCharPlayAsync()，它会先把这个字的单元备好。
 *
 * 片在路上的那几十毫秒里舞台不空着：先用 getCharPlay() 同步那一份开演——
 * 那是自动补齐层出的关，一样玩得完，只是不是作者手写的那一版。片到了就换上。
 * 「玩」是五步的第一步，等一次网络就是一次白屏，所以宁可先演再换。
 */
const authored = ref(null)

const scene = computed(() => props.play ?? authored.value ?? getCharPlay(props.char))
const bag = computed(() => scene.value?.props ?? {})
const kind = computed(() => scene.value?.kind ?? 'catch')

const reduced = computed(
  () =>
    settings?.reduceMotion === true ||
    (typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches === true)
)

/** playing | done */
const state = ref('playing')
const announce = ref('')
/** 孩子真的动了几下手；父级可以拿它分辨「玩过了」和「跳过了」。 */
const interactions = ref(0)
let finished = false

/* --------------------------------------------------------------- 各式状态 */

/** 已经点中的道具 id（pick / catch / match 共用）。 */
const taken = reactive(new Set())
/** 点错过的那一个，用来闪一下红边。 */
const missed = ref('')
/** watch 走到第几帧。 */
const frame = ref(0)
/** assemble 每个格子里放进去的零件。 */
const filled = reactive(new Map())
/** match 左边选中的那一个。 */
const picked = ref('')
/** push 推了几下。 */
const pushes = ref(0)

let motionTweens = []

function killMotion() {
  for (const t of motionTweens) t.kill()
  motionTweens = []
}

function reset() {
  killMotion()
  taken.clear()
  opened.clear()
  filled.clear()
  missed.value = ''
  frame.value = 0
  picked.value = ''
  pushes.value = 0
  interactions.value = 0
  finished = false
  state.value = 'playing'
  announce.value = scene.value?.narration ?? ''
  if (props.autoStart && kind.value === 'catch' && bag.value.moving && !reduced.value) {
    nextTick(startFalling)
  }
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
    template: scene.value?.template ?? '',
    kind: kind.value,
    templateFallback: scene.value?.templateFallback === true,
    interactions: interactions.value,
    skipped
  })
}

function onSkip() {
  sfx.tap()
  emit('skip', { char: props.char, template: scene.value?.template ?? '' })
  finish({ skipped: true })
}

function replay() {
  sfx.tap()
  reset()
}

function touched() {
  interactions.value += 1
  emit('interact', { char: props.char, kind: kind.value, count: interactions.value })
}

function wrong(target, text) {
  feedback.wrong(target)
  announce.value = text
}

/* ------------------------------------------------------ pick：点中对的那个 */

const options = computed(() => bag.value.options ?? [])
const need = computed(() => Math.max(1, Number(bag.value.need) || 1))
const opened = reactive(new Set())

function onPick(option, event) {
  if (state.value === 'done' || taken.has(option.id)) return
  touched()
  opened.add(option.id)
  if (!option.correct) {
    missed.value = option.id
    wrong(event?.currentTarget, `这个不是「${props.char}」，再看看别的。`)
    return
  }
  missed.value = ''
  taken.add(option.id)
  feedback.correct(event?.currentTarget, { cueArg: taken.size })
  const left = need.value - taken.size
  announce.value = left > 0 ? `对啦！还差 ${left} 个。` : '找到啦！'
  if (taken.size >= need.value) finish()
}

function sayIt() {
  sfx.tap()
  if (settings?.speechOn === false) return
  speak(bag.value.say || props.char, { rate: settings?.speechRate })
}

/* ---------------------------------------------------- catch：点够次数就过 */

const items = computed(() => bag.value.items ?? [])

function startFalling() {
  killMotion()
  const host = rainRef.value
  if (!host) return
  for (const el of host.querySelectorAll('.play__drop')) {
    const dur = (Number(el.dataset.duration) || 3000) / 1000
    const delay = (Number(el.dataset.delay) || 0) / 1000
    motionTweens.push(
      gsap.fromTo(
        el,
        { yPercent: -140, opacity: 1 },
        { yPercent: 620, duration: dur, delay, ease: 'none', repeat: -1, repeatDelay: 0.6 }
      )
    )
  }
}

function onCatch(item, event) {
  if (state.value === 'done' || taken.has(item.id)) return
  touched()
  opened.add(item.id)
  if (!item.hit) {
    missed.value = item.id
    wrong(event?.currentTarget, '这个不是要接的，看准了再点。')
    return
  }
  missed.value = ''
  taken.add(item.id)
  feedback.correct(event?.currentTarget, { cueArg: taken.size })
  const el = event?.currentTarget
  const tween = motionTweens.find((t) => t.targets()[0] === el)
  tween?.kill()
  if (el && !reduced.value) gsap.to(el, { scale: 1.6, opacity: 0, duration: 0.3, ease: 'power2.out' })
  if (bag.value.sound) announce.value = bag.value.sound
  const left = need.value - taken.size
  announce.value = left > 0 ? `接住啦！还差 ${left} 个。` : '都接住啦！'
  if (taken.size >= need.value) finish()
}

/* ------------------------------------------------- assemble：零件送回位置 */

const slots = computed(() => bag.value.slots ?? [])
const pieces = computed(() => bag.value.pieces ?? [])
const nextSlot = computed(() => slots.value.find((s) => !filled.has(s.id)) ?? null)

function onPiece(piece, event) {
  if (state.value === 'done' || !nextSlot.value) return
  touched()
  // 字形对得上哪个空格就落哪个（顺序随意，孩子不必从左往右）；
  // 对不上任何空格、自己又没标 correct，才算点错
  const slot =
    slots.value.find((s) => !filled.has(s.id) && s.glyph === piece.glyph) ??
    (piece.correct ? nextSlot.value : null)
  if (!slot) {
    missed.value = piece.id
    wrong(event?.currentTarget, `「${piece.glyph}」不是这里的零件。${bag.value.hint ?? ''}`)
    return
  }
  missed.value = ''
  filled.set(slot.id, piece.id)
  feedback.correct(event?.currentTarget, { cueArg: filled.size })
  if (!reduced.value) {
    const box = stageRef.value?.querySelector(`[data-slot="${slot.id}"]`)
    if (box) gsap.fromTo(box, { scale: 0.4, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.45, ease: 'back.out(2)' })
  }
  const left = slots.value.length - filled.size
  announce.value = left > 0 ? `放好一个，还差 ${left} 个。` : `拼好啦，这就是「${bag.value.whole ?? props.char}」。`
  if (left <= 0) window.setTimeout(() => finish(), reduced.value ? 200 : 600)
}

const pieceUsed = (piece) => [...filled.values()].includes(piece.id)

/* ------------------------------------------------------- watch：一帧一帧看 */

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
  if (!reduced.value && frameRef.value) {
    killMotion()
    motionTweens.push(
      gsap.fromTo(
        frameRef.value,
        { scale: 0.86, opacity: 0.2, rotate: -3 },
        { scale: 1, opacity: 1, rotate: 0, duration: 0.45, ease: 'back.out(1.7)' }
      )
    )
  }
  if (frame.value >= last) window.setTimeout(() => finish(), reduced.value ? 200 : 700)
}

/* ------------------------------------------------------- match：配成一对 */

const leftItems = computed(() => bag.value.left ?? [])
const rightItems = computed(() => bag.value.right ?? [])

function onLeft(item, event) {
  if (state.value === 'done' || taken.has(item.id)) return
  touched()
  picked.value = picked.value === item.id ? '' : item.id
  feedback.tap(event?.currentTarget)
  announce.value = picked.value ? '选好了，再点右边和它一对的。' : '取消了。'
}

function onRight(item, event) {
  if (state.value === 'done') return
  const chosen = leftItems.value.find((l) => l.id === picked.value)
  if (!chosen) {
    announce.value = '先点左边的一个。'
    return
  }
  touched()
  if (chosen.key !== item.key) {
    missed.value = item.id
    wrong(event?.currentTarget, '这两个不是一对，再试试。')
    return
  }
  missed.value = ''
  taken.add(chosen.id)
  picked.value = ''
  feedback.correct(event?.currentTarget, { cueArg: taken.size })
  const left = need.value - taken.size
  announce.value = left > 0 ? `配上啦！还差 ${left} 对。` : '全配上啦！'
  if (taken.size >= need.value) finish()
}

/* ---------------------------------------------------------- push：推一推 */

const AXIS = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] }

function onPush(event) {
  if (state.value === 'done') return
  touched()
  pushes.value += 1
  feedback.tap(event?.currentTarget)
  const [dx, dy] = AXIS[bag.value.dir] ?? AXIS.right
  const step = 26
  if (heroRef.value && !reduced.value) {
    gsap.to(heroRef.value, {
      x: dx * step * pushes.value,
      y: dy * step * pushes.value,
      duration: 0.4,
      ease: 'power2.out'
    })
  }
  const left = need.value - pushes.value
  announce.value = left > 0 ? `${bag.value.dirLabel}！还要 ${left} 下。` : '推到啦！'
  if (pushes.value >= need.value) finish()
}

/* ------------------------------------------------------------------ 进度 */

const progressText = computed(() => {
  if (state.value === 'done') return '这一关玩好啦'
  if (kind.value === 'watch') return `第 ${frame.value + 1} 帧 / 共 ${frames.value.length} 帧`
  if (kind.value === 'assemble') return `已放好 ${filled.size} / ${slots.value.length}`
  if (kind.value === 'push') return `已${bag.value.dirLabel ?? '推'} ${pushes.value} / ${need.value} 下`
  return `已完成 ${taken.size} / ${need.value}`
})

/**
 * 换字就去取这个字的手写剧本。两道防护：
 *   竞态 —— 回来时字已经翻走了就丢弃结果，别把上一个字的关摆到这一个字上；
 *   打断 —— 孩子已经动过手 / 已经玩完就这一次不换了，等下一个字再说。
 */
watch(
  () => props.char,
  (char) => {
    authored.value = null
    if (props.play) return
    getCharPlayAsync(char).then((play) => {
      if (props.char !== char || state.value === 'done' || interactions.value > 0) return
      authored.value = play
    })
  },
  { immediate: true }
)

// 关卡换了（换字、手写剧本到货、减少动态开关）就从头摆一遍
watch(() => [props.char, scene.value, reduced.value], reset, { immediate: true })

watch(
  () => props.autoStart,
  (on) => {
    if (on && kind.value === 'catch' && bag.value.moving && !reduced.value) nextTick(startFalling)
  }
)

onBeforeUnmount(killMotion)

defineExpose({ finish, replay, skip: onSkip })
</script>

<template>
  <section
    ref="stageRef"
    class="play char-play-stage"
    :class="{ 'play--static': reduced, 'play--done': state === 'done' }"
    :style="{ '--play-accent': scene.accent }"
    data-char-play
    :data-char="char"
    :data-play-template="scene.template"
    :data-template="scene.template"
    :data-kind="kind"
    :data-state="state"
    :data-fallback="scene.templateFallback ? 'true' : 'false'"
    :aria-label="`「${char}」的玩一玩：${scene.templateLabel}`"
  >
    <header class="play__head">
      <p class="play__badge">
        <span aria-hidden="true">{{ scene.themeEmoji }}</span>
        <strong>{{ scene.templateLabel }}</strong>
        <span v-if="scene.themeLabel" class="muted">{{ scene.themeLabel }}</span>
      </p>
      <p class="play__narration">{{ scene.narration }}</p>
      <p v-if="scene.prompt" class="play__caption">{{ scene.prompt }}</p>
    </header>

    <!-- pick：从几个里点中对的 -->
    <div v-if="kind === 'pick'" class="play__pick">
      <p v-if="bag.sceneLabel" class="play__scene">
        <span aria-hidden="true">{{ bag.scene }}</span> {{ bag.sceneLabel }}
      </p>
      <button v-if="bag.say" type="button" class="btn btn--ghost btn--sm" @click="sayIt">
        🔊 再听一遍{{ bag.pinyin ? `（${bag.pinyin}）` : '' }}
      </button>
      <ul class="play__cards">
        <li v-for="option in options" :key="option.id">
          <button
            type="button"
            class="play__card"
            :class="{
              'is-open': !bag.cover || opened.has(option.id),
              'is-right': taken.has(option.id),
              'is-wrong': missed === option.id
            }"
            :disabled="taken.has(option.id)"
            :aria-label="bag.cover && !opened.has(option.id) ? '盖着的卡片' : option.label"
            @click="onPick(option, $event)"
          >
            <span v-if="bag.cover && !opened.has(option.id)" class="play__cover" aria-hidden="true">
              {{ bag.cover }}
            </span>
            <template v-else>
              <OpenMojiIcon v-if="option.emoji" class="play__icon" :emoji="option.emoji" :size="46" />
              <span v-if="option.glyph" class="play__glyph play__glyph--sm">{{ option.glyph }}</span>
              <span v-if="taken.has(option.id) && option.reveal" class="play__label">{{ option.reveal }}</span>
            </template>
          </button>
        </li>
      </ul>
    </div>

    <!-- catch：会掉的、要数的，点够次数就过 -->
    <div
      v-else-if="kind === 'catch' && bag.moving && !reduced"
      ref="rainRef"
      class="play__rain"
    >
      <button
        v-for="item in items"
        :key="item.id"
        type="button"
        class="play__drop"
        :class="{ 'is-caught': taken.has(item.id) }"
        :style="{ left: `${item.x}%` }"
        :data-delay="item.delay"
        :data-duration="item.duration"
        :disabled="taken.has(item.id)"
        :aria-label="item.label"
        @click="onCatch(item, $event)"
      >
        <OpenMojiIcon v-if="item.emoji" class="play__icon" :emoji="item.emoji" :size="40" />
        <span v-else class="play__glyph play__glyph--sm">{{ item.glyph }}</span>
      </button>
      <p class="play__ground">
        <span v-if="bag.tool" aria-hidden="true">{{ bag.tool }}</span>
        接住「{{ bag.target }}」
      </p>
    </div>

    <div v-else-if="kind === 'catch'" class="play__grid">
      <button
        v-for="item in items"
        :key="item.id"
        type="button"
        class="play__cell"
        :class="{ 'is-found': taken.has(item.id), 'is-wrong': missed === item.id }"
        :disabled="taken.has(item.id)"
        :aria-label="bag.cover && !opened.has(item.id) ? '盖着的卡片' : item.label"
        @click="onCatch(item, $event)"
      >
        <span v-if="bag.cover && !opened.has(item.id)" class="play__cover" aria-hidden="true">
          {{ bag.cover }}
        </span>
        <template v-else>
          <OpenMojiIcon v-if="item.emoji" class="play__icon" :emoji="item.emoji" :size="38" />
          <span v-else class="play__glyph play__glyph--sm">{{ item.glyph }}</span>
        </template>
      </button>
    </div>

    <!-- assemble：零件送回位置 -->
    <div v-else-if="kind === 'assemble'" class="play__assemble">
      <div v-if="bag.mode === 'word'" class="play__word">
        <span
          v-for="(ch, i) in bag.chars"
          :key="`w${i}`"
          class="play__glyph"
          :class="{ 'play__slot': i === bag.blank }"
          :data-slot="i === bag.blank ? slots[0]?.id : undefined"
        >
          {{ i === bag.blank ? (filled.size ? ch : '？') : ch }}
        </span>
      </div>
      <div v-else class="play__whole">
        <span
          v-for="slot in slots"
          :key="slot.id"
          class="play__slot"
          :class="{ 'is-filled': filled.has(slot.id) }"
          :data-slot="slot.id"
        >
          {{ filled.has(slot.id) ? slot.glyph : '？' }}
        </span>
        <span class="play__arrow" aria-hidden="true">→</span>
        <span class="play__glyph">{{ bag.whole }}</span>
      </div>
      <p class="play__caption">{{ bag.hint }}</p>
      <ul class="play__parts">
        <li v-for="piece in pieces" :key="piece.id">
          <button
            type="button"
            class="play__part"
            :class="{ 'is-wrong': missed === piece.id, 'is-right': pieceUsed(piece) }"
            :disabled="pieceUsed(piece) || state === 'done'"
            :aria-label="`${piece.glyph}${piece.label ? ' ' + piece.label : ''}`"
            @click="onPiece(piece, $event)"
          >
            <span class="play__part-glyph">{{ piece.glyph }}</span>
            <span v-if="piece.label" class="play__label">{{ piece.label }}</span>
          </button>
        </li>
      </ul>
    </div>

    <!-- watch：一帧一帧看完 -->
    <div v-else-if="kind === 'watch'" class="play__morph">
      <div ref="frameRef" class="play__morph-slot">
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

    <!-- match：左边一个右边一个 -->
    <div v-else-if="kind === 'match'" class="play__match">
      <ul class="play__column">
        <li v-for="item in leftItems" :key="item.id">
          <button
            type="button"
            class="play__cell"
            :class="{ 'is-found': taken.has(item.id), 'is-picked': picked === item.id }"
            :disabled="taken.has(item.id)"
            :aria-pressed="picked === item.id"
            :aria-label="item.label || '左边的一个'"
            @click="onLeft(item, $event)"
          >
            <OpenMojiIcon v-if="item.emoji" class="play__icon" :emoji="item.emoji" :size="38" />
            <span v-else class="play__glyph play__glyph--sm">{{ item.glyph }}</span>
          </button>
        </li>
      </ul>
      <ul class="play__column">
        <li v-for="item in rightItems" :key="item.id">
          <button
            type="button"
            class="play__cell"
            :class="{ 'is-wrong': missed === item.id }"
            :aria-label="item.label || '右边的一个'"
            @click="onRight(item, $event)"
          >
            <OpenMojiIcon v-if="item.emoji" class="play__icon" :emoji="item.emoji" :size="38" />
            <span v-else class="play__glyph play__glyph--sm">{{ item.glyph }}</span>
            <span v-if="item.label" class="play__label">{{ item.label }}</span>
          </button>
        </li>
      </ul>
    </div>

    <!-- push：顺着一个方向推 -->
    <div v-else class="play__push">
      <div class="play__track">
        <span ref="heroRef" class="play__hero">
          <OpenMojiIcon class="play__icon play__icon--big" :emoji="bag.hero" :size="72" />
        </span>
      </div>
      <button type="button" class="btn btn--primary" @click="onPush($event)">
        {{ bag.dirLabel }}推一下
      </button>
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

/* ------------------------------------------------------------ pick */

.play__pick {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--gap-sm);
}

.play__scene {
  font-size: var(--fs-sm);
  color: var(--text-soft);
}

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
  border-color: var(--surface-border);
  background: var(--surface);
}

.play__card.is-right {
  border-color: var(--success);
}

.play__card.is-wrong,
.play__cell.is-wrong,
.play__part.is-wrong {
  border-color: var(--danger);
}

.play__cover {
  font-size: var(--fs-xl);
  line-height: 1;
}

/* ------------------------------------------------------------ catch / match */

/*
 * 道具少到一两件时（「揭一揭」只盖着一张牌），四等分网格会把那一张顶到左上角，
 * 看着像没加载完。改成居中换行，一张也好、九张也好都摆在中间。
 */
.play__grid {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--gap-xs);
}

.play__grid .play__cell {
  flex: 0 0 auto;
  width: 72px;
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

.play__cell.is-picked {
  border-color: var(--play-accent, var(--brand));
  box-shadow: var(--shadow-sm);
}

.play__match {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--gap-md);
}

.play__column {
  display: flex;
  flex-direction: column;
  gap: var(--gap-xs);
  list-style: none;
  margin: 0;
  padding: 0;
}

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
  /* left 是落点的中线，往左收半个身位才不会贴着右边缘掉下来 */
  margin-left: calc(var(--tap-min, 44px) / -2);
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

/* ------------------------------------------------------------ assemble */

.play__assemble {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--gap-sm);
}

.play__whole,
.play__word {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
}

.play__slot {
  display: grid;
  place-items: center;
  min-width: 64px;
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

.play__arrow {
  font-size: var(--fs-lg);
  color: var(--text-soft);
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
  /* 零件多半是部件或 emoji，比正文再大一号才够小手看清、够大点得中 */
  font-size: var(--fs-xl);
  line-height: 1.2;
  color: var(--text-strong);
}

.play__part.is-right {
  border-color: var(--success);
  opacity: 0.6;
}

/* ------------------------------------------------------------ watch */

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
  /* 图和字叠在一处，孩子的视线不用来回跳 */
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  opacity: 0.92;
}

/* ------------------------------------------------------------ push */

.play__push {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--gap-sm);
}

.play__track {
  display: grid;
  place-items: center;
  width: 100%;
  min-height: 132px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  border: 2px dashed var(--stroke-hint);
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

.play--static .play__cell,
.play--static .play__card,
.play--static .play__part {
  transition: none;
}

@media (max-width: 420px) {
  .play__grid .play__cell {
    width: 64px;
  }

  .play__card {
    width: 76px;
  }
}
</style>
