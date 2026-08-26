<script setup>
/**
 * 朗读不可用时的友好提示。
 *
 * 之前这里是「静默失败」：系统没装中文嗓音时点小喇叭什么都不会发生，
 * 家长只会以为应用坏了。现在分两种情况说人话——
 * 浏览器不支持朗读，和支持但系统里没有中文嗓音——
 * 并且都给出「不用朗读也能继续玩」的替代路径。
 *
 * 儿童侧只看到一句温和的话（设计规范 §10），
 * 装嗓音的技术步骤收在 <details> 里给家长看。
 */
import { computed, ref } from 'vue'
import { useVoiceStatus } from '@/composables/useVoiceStatus.js'
import { sfx } from '@/utils/audio.js'

const props = defineProps({
  /** 这一页少了朗读会缺什么，用来补一句「可以让家长读给你听」之类的替代方案。 */
  fallback: { type: String, default: '' },
  /** 紧凑版：只留一行字，用在已经很挤的页面里。 */
  compact: { type: Boolean, default: false }
})

const { status } = useVoiceStatus()

const visible = computed(() => status.value === 'missing' || status.value === 'unsupported')

const headline = computed(() =>
  status.value === 'unsupported'
    ? '这个浏览器不会朗读，先看字也一样能学'
    : '这台设备上还没有中文的朗读声音'
)

const detailOpen = ref(false)

function toggleDetail(event) {
  detailOpen.value = event.target.open
  sfx.tap()
}
</script>

<template>
  <p v-if="visible" class="vnotice" :class="{ 'vnotice--compact': compact }" role="status" aria-live="polite">
    <span class="vnotice__emoji" aria-hidden="true">🔇</span>
    <span class="vnotice__body">
      <strong class="vnotice__headline">{{ headline }}</strong>
      <span v-if="fallback && !compact" class="vnotice__fallback">{{ fallback }}</span>

      <details v-if="!compact" class="vnotice__detail" @toggle="toggleDetail">
        <summary class="vnotice__summary">家长看这里：怎么装中文嗓音</summary>
        <span class="vnotice__steps">
          Windows：设置 → 时间和语言 → 语音 → 添加语音 → 中文（简体，中国）。<br />
          macOS / iOS：设置 → 辅助功能 → 朗读内容 → 声音 → 中文。<br />
          Android：设置 → 系统 → 语言和输入法 → 文字转语音 → 安装语音数据。<br />
          装好后回到这里刷新一下，小喇叭就会说话了。
        </span>
      </details>
    </span>
  </p>
</template>

<style scoped>
.vnotice {
  display: flex;
  align-items: flex-start;
  gap: var(--gap-sm);
  width: 100%;
  padding: 12px 14px;
  border-radius: var(--radius-md);
  background: var(--brand-soft);
  border: 2px solid color-mix(in srgb, var(--brand) 32%, transparent);
  color: var(--text);
  font-size: 0.88rem;
  line-height: 1.75;
  text-align: left;
}

.vnotice__emoji {
  flex: none;
  font-size: 1.3rem;
  line-height: 1.4;
}

.vnotice__body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.vnotice__headline {
  color: var(--text-strong);
  font-weight: 700;
}

.vnotice__fallback {
  color: var(--text-soft);
}

.vnotice__detail {
  margin-top: 2px;
}

.vnotice__summary {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  color: var(--brand-strong);
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
}

.vnotice__steps {
  display: block;
  padding-top: 6px;
  color: var(--text-soft);
  font-size: 0.8rem;
  line-height: 1.9;
}

.vnotice--compact {
  padding: 8px 12px;
  font-size: 0.82rem;
}
</style>
