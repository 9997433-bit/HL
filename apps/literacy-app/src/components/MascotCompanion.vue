<script setup>
/**
 * 学伴「墨墨」。
 *
 * 用内联 SVG 而不是 emoji/图片：可以跟着主题变色、可以逐部件做动画，
 * 而且不增加任何素材体积。
 *
 * mood 控制表情，浏览器原生 Web Animations 负责三层动作：
 *   1) 常驻呼吸浮动；2) 随机眨眼；3) mood 切换时的一次性反应动作。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { sfx, speak } from '@/utils/audio.js'

const props = defineProps({
  mood: { type: String, default: 'idle' }, // idle | happy | think | sad | cheer | sleep
  /** 气泡里的话；空字符串表示不显示气泡 */
  say: { type: String, default: '' },
  size: { type: Number, default: 96 },
  /** 点击时是否朗读气泡内容；由外面接管换句时关掉，避免读的是上一句 */
  speakOnTap: { type: Boolean, default: true },
  /** 气泡在左还是右 */
  bubbleSide: { type: String, default: 'right' },
  /** 给孩子的点触提示，同时替换按钮的无障碍名称 */
  tapHint: { type: String, default: '' },
  /** 离线学伴对话的短选项：[{ id, label }] */
  quickReplies: { type: Array, default: () => [] }
})

const emit = defineEmits(['tap', 'reply'])

const root = ref(null)
const body = ref(null)
const eyeL = ref(null)
const eyeR = ref(null)
const bubble = ref(null)

let idleTween = null
let blinkTimer = null
const activeAnimations = new Set()

function animate(target, keyframes, options) {
  const animation = target?.animate?.(keyframes, options)
  if (!animation) return null
  activeAnimations.add(animation)
  animation.finished
    .catch(() => {})
    .finally(() => activeAnimations.delete(animation))
  return animation
}

function stopAnimations(target) {
  for (const animation of activeAnimations) {
    if (animation.effect?.target === target) animation.cancel()
  }
}

/** 各心情下的嘴形路径与眼睛缩放。 */
const FACES = {
  idle: { mouth: 'M 42 62 Q 50 69 58 62', eyeScale: 1, cheek: 0.5 },
  happy: { mouth: 'M 40 60 Q 50 73 60 60', eyeScale: 0.72, cheek: 0.9 },
  think: { mouth: 'M 44 65 L 56 63', eyeScale: 1.05, cheek: 0.35 },
  sad: { mouth: 'M 42 68 Q 50 60 58 68', eyeScale: 0.95, cheek: 0.3 },
  cheer: { mouth: 'M 38 58 Q 50 78 62 58', eyeScale: 0.6, cheek: 1 },
  sleep: { mouth: 'M 45 65 Q 50 69 55 65', eyeScale: 0.12, cheek: 0.4 }
}

const face = computed(() => FACES[props.mood] ?? FACES.idle)
const replies = computed(() =>
  props.quickReplies
    .map((reply, index) =>
      typeof reply === 'string'
        ? { id: reply, label: reply }
        : { id: String(reply?.id ?? index), label: String(reply?.label ?? '') }
    )
    .filter((reply) => reply.label.trim())
)

/**
 * 气泡本身是 role="status"，内容变了读屏会自己播报；
 * 所以给了点触提示时，按钮的名称就只讲「点它会发生什么」，不再重复台词。
 */
const buttonLabel = computed(() => {
  if (props.tapHint) return `学伴墨墨，${props.tapHint}`
  return props.say ? `学伴墨墨说：${props.say}` : '学伴墨墨'
})

function blink() {
  const targets = [eyeL.value, eyeR.value].filter(Boolean)
  if (targets.length && props.mood !== 'sleep') {
    for (const target of targets) {
      animate(
        target,
        [
          { transform: `scaleY(${face.value.eyeScale})` },
          { transform: 'scaleY(0.08)', offset: 0.42 },
          { transform: `scaleY(${face.value.eyeScale})` }
        ],
        { duration: 170, easing: 'ease-in-out' }
      )
    }
  }
  blinkTimer = window.setTimeout(blink, 2200 + Math.random() * 3200)
}

/** mood 变化时来一个短反应，让学伴显得在「回应」孩子。 */
function react(mood) {
  if (!body.value) return
  stopAnimations(body.value)

  if (mood === 'happy' || mood === 'cheer') {
    const rotate = mood === 'cheer'
    animate(
      body.value,
      [
        { transform: 'translateY(0) scale(1) rotate(0)' },
        {
          transform: `translateY(-14px) scale(.94, 1.08) rotate(${rotate ? '-8deg' : '0'})`,
          offset: 0.28
        },
        {
          transform: `translateY(0) scale(1.06, .94) rotate(${rotate ? '8deg' : '0'})`,
          offset: 0.53
        },
        { transform: 'translateY(0) scale(1) rotate(0)' }
      ],
      { duration: 640, easing: 'cubic-bezier(.34,1.56,.64,1)' }
    )
  } else if (mood === 'sad') {
    animate(
      body.value,
      [
        { transform: 'translateY(0) scaleY(1)' },
        { transform: 'translateY(6px) scaleY(.93)', offset: 0.33 },
        { transform: 'translateY(0) scaleY(1)' }
      ],
      { duration: 670, easing: 'ease-out' }
    )
  } else if (mood === 'think') {
    animate(
      body.value,
      [
        { transform: 'rotate(0)' },
        { transform: 'rotate(-6deg)', offset: 0.3 },
        { transform: 'rotate(4deg)', offset: 0.7 },
        { transform: 'rotate(0)' }
      ],
      { duration: 1000, easing: 'ease-in-out' }
    )
  }
}

function popBubble() {
  if (!bubble.value) return
  animate(
    bubble.value,
    [
      { opacity: 0, transform: 'translateY(8px) scale(.7)' },
      { opacity: 1, transform: 'translateY(0) scale(1)' }
    ],
    { duration: 400, easing: 'cubic-bezier(.34,1.56,.64,1)' }
  )
}

function onTap() {
  if (props.speakOnTap) {
    sfx.tap()
    if (props.say) speak(props.say)
  }
  react('happy')
  emit('tap')
}

function onReply(reply) {
  sfx.tap()
  react('happy')
  emit('reply', reply.id)
}

onMounted(() => {
  if (body.value) {
    idleTween = animate(
      body.value,
      [{ transform: 'translateY(0)' }, { transform: 'translateY(-6px)' }],
      {
        duration: 1800,
        easing: 'ease-in-out',
        iterations: Infinity,
        direction: 'alternate'
      }
    )
  }
  if (root.value) {
    animate(
      root.value,
      [
        { opacity: 0, transform: 'scale(.6)' },
        { opacity: 1, transform: 'scale(1)' }
      ],
      { duration: 600, easing: 'cubic-bezier(.34,1.56,.64,1)' }
    )
  }
  blink()
  if (props.say) popBubble()
})

onBeforeUnmount(() => {
  idleTween?.cancel()
  if (blinkTimer) clearTimeout(blinkTimer)
  for (const animation of activeAnimations) animation.cancel()
  activeAnimations.clear()
})

watch(() => props.mood, react)
watch(
  () => props.say,
  (v) => {
    if (v) popBubble()
  }
)
</script>

<template>
  <div ref="root" class="mascot" :class="`mascot--${bubbleSide}`">
    <button
      class="mascot__btn"
      type="button"
      :style="{ width: `${size}px`, height: `${size}px` }"
      :aria-label="buttonLabel"
      @click="onTap"
    >
      <svg ref="body" viewBox="0 0 100 100" class="mascot__svg" aria-hidden="true">
        <defs>
          <linearGradient :id="`mascotBody-${size}`" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="var(--mango-400)" />
            <stop offset="100%" stop-color="var(--coral-400)" />
          </linearGradient>
        </defs>

        <!-- 耳朵 -->
        <ellipse cx="26" cy="24" rx="11" ry="14" :fill="`url(#mascotBody-${size})`" transform="rotate(-18 26 24)" />
        <ellipse cx="74" cy="24" rx="11" ry="14" :fill="`url(#mascotBody-${size})`" transform="rotate(18 74 24)" />
        <ellipse cx="26" cy="25" rx="5" ry="7" fill="var(--surface-strong)" opacity="0.55" transform="rotate(-18 26 25)" />
        <ellipse cx="74" cy="25" rx="5" ry="7" fill="var(--surface-strong)" opacity="0.55" transform="rotate(18 74 25)" />

        <!-- 身体 -->
        <ellipse cx="50" cy="55" rx="36" ry="34" :fill="`url(#mascotBody-${size})`" />
        <ellipse cx="50" cy="62" rx="24" ry="22" fill="var(--surface-strong)" opacity="0.9" />

        <!-- 腮红 -->
        <ellipse cx="28" cy="60" rx="6" ry="4" fill="var(--coral-400)" :opacity="face.cheek" />
        <ellipse cx="72" cy="60" rx="6" ry="4" fill="var(--coral-400)" :opacity="face.cheek" />

        <!-- 眼睛 -->
        <g ref="eyeL" :style="{ transform: `scaleY(${face.eyeScale})`, transformOrigin: '38px 48px' }">
          <ellipse cx="38" cy="48" rx="5" ry="6.5" fill="var(--stroke-ink)" />
          <circle cx="40" cy="45.5" r="1.9" fill="var(--surface-strong)" />
        </g>
        <g ref="eyeR" :style="{ transform: `scaleY(${face.eyeScale})`, transformOrigin: '62px 48px' }">
          <ellipse cx="62" cy="48" rx="5" ry="6.5" fill="var(--stroke-ink)" />
          <circle cx="64" cy="45.5" r="1.9" fill="var(--surface-strong)" />
        </g>

        <!-- 嘴 -->
        <path
          :d="face.mouth"
          fill="none"
          stroke="var(--stroke-ink)"
          stroke-width="2.6"
          stroke-linecap="round"
        />

        <!-- 头顶小笔（墨墨是一支会写字的小精灵） -->
        <rect x="47" y="4" width="6" height="14" rx="3" fill="var(--mint-400)" />
        <path d="M 47 16 L 53 16 L 50 21 Z" fill="var(--stroke-ink)" />

        <!-- 睡着时的 Z -->
        <text v-if="mood === 'sleep'" x="80" y="26" font-size="14" fill="var(--text-soft)">z</text>
      </svg>
    </button>

    <div v-if="say || replies.length" ref="bubble" class="mascot__bubble">
      <p v-if="say" role="status" aria-live="polite">{{ say }}</p>
      <small v-if="tapHint" class="mascot__hint">{{ tapHint }}</small>
      <div v-if="replies.length" class="mascot__quick" role="group" aria-label="学伴对话选项">
        <button
          v-for="reply in replies"
          :key="reply.id"
          type="button"
          class="mascot__quick-btn"
          @click="onReply(reply)"
        >
          {{ reply.label }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.mascot {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
}

.mascot--left {
  flex-direction: row-reverse;
}

.mascot__btn {
  flex: none;
  padding: 0;
  border-radius: 50%;
  transition: transform var(--dur-fast) var(--ease-pop);
}

.mascot__btn:active {
  transform: scale(0.93);
}

.mascot__svg {
  width: 100%;
  height: 100%;
  overflow: visible;
  filter: drop-shadow(0 6px 12px rgba(90, 70, 40, 0.18));
}

.mascot__bubble {
  position: relative;
  max-width: 240px;
  padding: 10px 16px;
  background: var(--surface-strong);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  font-size: 0.92rem;
  font-weight: 600;
  color: var(--text-strong);
  line-height: 1.45;
}

.mascot__bubble::before {
  content: '';
  position: absolute;
  top: 50%;
  width: 0;
  height: 0;
  border: 8px solid transparent;
}

.mascot--right .mascot__bubble::before {
  left: -15px;
  margin-top: -8px;
  border-right-color: var(--surface-strong);
}

.mascot--left .mascot__bubble::before {
  right: -15px;
  margin-top: -8px;
  border-left-color: var(--surface-strong);
}

.mascot__bubble p {
  margin: 0;
}

.mascot__hint {
  display: block;
  margin-top: 4px;
  font-size: 0.74rem;
  font-weight: 700;
  color: var(--text-soft);
}

.mascot__quick {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.mascot__quick-btn {
  min-height: 44px;
  padding: 6px 10px;
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-pill);
  background: var(--brand-soft);
  color: var(--text-strong);
  font: inherit;
  font-size: 0.78rem;
  font-weight: 800;
}

.mascot__quick-btn:focus-visible {
  outline: 3px solid var(--focus-ring);
  outline-offset: 2px;
}

@media (max-width: 480px) {
  .mascot__bubble {
    max-width: 190px;
    font-size: 0.85rem;
  }
}
</style>
