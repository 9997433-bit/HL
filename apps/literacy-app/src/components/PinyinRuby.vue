<script setup>
/**
 * 拼音注音文本。
 *
 * 用原生 <ruby> 而不是自己摆两行 <span>：屏幕阅读器和复制粘贴都更友好，
 * 关闭注音时（家长面板可切换）直接不渲染 <rt>，版面不会跳动太多。
 *
 * 传 `pinyin` 时按空格切分，逐字对齐；不传则整段只显示汉字。
 */
import { computed } from 'vue'
import { useProgressStore } from '@/stores/progress.js'

const props = defineProps({
  text: { type: String, required: true },
  /** 空格分隔的音节，数量应与 text 中的汉字数一致 */
  pinyin: { type: String, default: '' },
  size: { type: String, default: '1.5rem' },
  /** 强制显示注音，忽略全局设置 */
  forcePinyin: { type: Boolean, default: false },
  /** 点某个字时抛出该字 */
  clickable: { type: Boolean, default: false }
})

const emit = defineEmits(['pick'])

const progress = useProgressStore()

const showPinyin = computed(() => props.forcePinyin || progress.state.settings.showPinyin)

const PUNCT = /[，。！？：、；「」《》…—,.!?;:'"]/

/**
 * 把正文和音节配对。标点不占音节，所以要一边走一边错位对齐。
 */
const tokens = computed(() => {
  const syllables = props.pinyin.trim() ? props.pinyin.trim().split(/\s+/) : []
  let si = 0
  return [...props.text].map((ch) => {
    if (PUNCT.test(ch) || ch === ' ') return { ch, p: '', punct: true }
    const p = syllables[si] ?? ''
    si += 1
    return { ch, p, punct: false }
  })
})

/** 声调 → 颜色，跟很多识字教材的四声配色习惯一致。 */
const TONE_COLOR = {
  1: 'var(--seed-coral)',
  2: 'var(--seed-mango)',
  3: 'var(--seed-leaf)',
  4: 'var(--seed-sky)',
  5: 'var(--text-soft)'
}

const TONE_MARKS = [
  { re: /[āēīōūǖ]/, tone: 1 },
  { re: /[áéíóúǘ]/, tone: 2 },
  { re: /[ǎěǐǒǔǚ]/, tone: 3 },
  { re: /[àèìòùǜ]/, tone: 4 }
]

function toneOf(syllable) {
  if (!syllable) return 5
  for (const { re, tone } of TONE_MARKS) if (re.test(syllable)) return tone
  return 5
}

function onPick(token) {
  if (props.clickable && !token.punct) emit('pick', token.ch)
}
</script>

<template>
  <p class="ruby-line" :style="{ fontSize: size }">
    <template v-for="(t, i) in tokens" :key="`${t.ch}-${i}`">
      <span v-if="t.punct" class="ruby-line__punct">{{ t.ch }}</span>
      <ruby
        v-else
        class="ruby-line__item"
        :class="{ 'is-clickable': clickable }"
        :style="{ '--tone-color': TONE_COLOR[toneOf(t.p)] }"
        :tabindex="clickable ? 0 : undefined"
        :role="clickable ? 'button' : undefined"
        @click="onPick(t)"
        @keydown.enter.prevent="onPick(t)"
        @keydown.space.prevent="onPick(t)"
      >
        {{ t.ch }}
        <rt v-if="showPinyin && t.p">{{ t.p }}</rt>
      </ruby>
    </template>
  </p>
</template>

<style scoped>
.ruby-line {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 2px 1px;
  line-height: 1.75;
  color: var(--text-strong);
  font-weight: 600;
}

.ruby-line__item {
  ruby-align: center;
  border-radius: 8px;
  padding: 0 2px;
  transition: background var(--dur-fast) ease, transform var(--dur-fast) var(--ease-pop);
}

.ruby-line__item.is-clickable {
  cursor: pointer;
}

.ruby-line__item.is-clickable:hover,
.ruby-line__item.is-clickable:focus-visible {
  background: var(--brand-soft);
  transform: translateY(-2px);
}

.ruby-line__item rt {
  font-size: 0.44em;
  font-weight: 700;
  color: var(--tone-color, var(--text-soft));
  letter-spacing: 0.01em;
  /* ruby 默认贴得太近，孩子看不清 */
  transform: translateY(-1px);
}

.ruby-line__punct {
  align-self: flex-end;
  color: var(--text-soft);
}
</style>
