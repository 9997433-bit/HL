<script setup>
/**
 * 偏旁部首页：左右滑动的部首条 + 当前部首详情。
 *
 * 当前部首由地址栏决定（/radicals/shui），不是组件内部状态——
 * 单字页的「去看看部首」就是靠这个链接跳过来的，
 * 内部 ref 会让那条链接永远停在第一个部首上。
 */
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { RADICALS } from '@/data/radicals.js'
import { CHARACTER_MAP } from '@/data/characters.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { speak } from '@/utils/speech.js'
import { sfx } from '@/utils/sfx.js'

const progress = useProgressStore()
const settings = useSettingsStore()
const route = useRoute()
const router = useRouter()

const pickerEl = ref(null)

/** 地址里的 id 认不出来时退回第一个，不要让页面空掉。 */
const active = computed(
  () => RADICALS.find((r) => r.id === route.params.id) || RADICALS[0]
)

const openId = computed(() => active.value.id)

function select(r) {
  if (r.id === openId.value) return
  sfx.tap()
  router.push(`/radicals/${r.id}`)
}

/** 从别的页面直接跳进来时，把选中的部首滚到可视区内。 */
function revealActive() {
  const el = pickerEl.value?.querySelector('.is-on')
  el?.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' })
}

watch(
  openId,
  (id) => {
    progress.viewRadical(id)
    nextTick(revealActive)
  },
  { immediate: true }
)

function say(text) {
  sfx.tap()
  speak(text, { rate: settings.speechRate })
}

/** 示例字里，语料库中已收录的才可以点进去学。 */
function isLearnable(char) {
  return CHARACTER_MAP.has(char)
}
</script>

<template>
  <div class="page">
    <section class="card card--flat intro">
      <div class="intro__text">
        <h2 class="section-title">
          <span class="section-title__emoji" aria-hidden="true">🧩</span>
          偏旁部首
        </h2>
        <p class="muted">
          汉字是由「小零件」拼起来的。认识了偏旁，看到没学过的字也能猜出它的意思。
        </p>
      </div>
      <span class="pill">已看过 {{ progress.radicalsSeen }} / {{ RADICALS.length }}</span>
    </section>

    <!-- 部首选择条 -->
    <section ref="pickerEl" class="picker" role="tablist" aria-label="选择偏旁">
      <button
        v-for="r in RADICALS"
        :key="r.id"
        class="picker__item"
        :class="{ 'is-on': r.id === openId }"
        type="button"
        role="tab"
        :aria-selected="r.id === openId"
        @click="select(r)"
      >
        <span class="picker__glyph">{{ r.glyph }}</span>
        <span class="picker__name">{{ r.name }}</span>
      </button>
    </section>

    <!-- 详情 -->
    <section :key="active.id" class="detail card">
      <div class="detail__head">
        <div class="detail__glyph tianzige">
          <span>{{ active.glyph }}</span>
        </div>
        <div class="detail__meta">
          <button class="detail__name" type="button" @click="say(active.name)">
            {{ active.name }} <span aria-hidden="true">🔊</span>
          </button>
          <p class="detail__pinyin muted">{{ active.pinyin }}</p>
          <p class="detail__from">
            <span class="pill">由「{{ active.from }}」变来</span>
            <span class="pill pill--accent">{{ active.strokes }} 画</span>
          </p>
        </div>
        <span class="detail__emoji" aria-hidden="true">{{ active.emoji }}</span>
      </div>

      <p class="detail__meaning">{{ active.meaning }}</p>
      <p class="detail__hint">💡 {{ active.hint }}</p>

      <div class="detail__block">
        <h3 class="detail__label">课本里学过的字</h3>
        <div class="chars">
          <RouterLink
            v-for="c in active.chars"
            :key="c"
            class="chars__item"
            :class="{ 'is-done': progress.isLearned(c) }"
            :to="`/learn/${encodeURIComponent(c)}`"
            @click="sfx.tap()"
          >
            <span class="chars__char">{{ c }}</span>
            <small v-if="isLearnable(c)">{{ CHARACTER_MAP.get(c).pinyin }}</small>
          </RouterLink>
        </div>
      </div>

      <div class="detail__block">
        <h3 class="detail__label">还有这些字也带它</h3>
        <div class="chars chars--ghost">
          <button
            v-for="c in active.more"
            :key="c"
            class="chars__item chars__item--ghost"
            type="button"
            @click="say(c)"
          >
            <span class="chars__char">{{ c }}</span>
          </button>
        </div>
        <p class="muted detail__note">这些字以后会学到，现在先认个脸熟～</p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.intro {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
}

.intro__text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.intro__text .muted {
  font-size: 0.88rem;
}

.picker {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding: 4px 2px 10px;
  scrollbar-width: thin;
}

.picker__item {
  flex: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  width: 78px;
  padding: 10px 6px;
  border-radius: var(--radius-md);
  background: var(--surface-strong);
  border: 2px solid transparent;
  box-shadow: var(--shadow-sm);
  transition: transform var(--dur-fast) var(--ease-pop), border-color var(--dur-fast) ease;
}

.picker__item:active {
  transform: scale(0.94);
}

.picker__item.is-on {
  border-color: var(--brand);
  background: var(--brand-soft);
}

.picker__glyph {
  font-size: 1.9rem;
  line-height: 1.1;
  font-weight: 700;
  color: var(--text-strong);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', serif;
}

.picker__name {
  font-size: 0.7rem;
  color: var(--text-soft);
  white-space: nowrap;
}

.detail {
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
  animation: pop-in var(--dur-mid) var(--ease-pop);
}

.detail__head {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
}

.detail__glyph {
  flex: none;
  display: grid;
  place-items: center;
  width: 108px;
  height: 108px;
}

.detail__glyph span {
  position: relative;
  z-index: 1;
  font-size: 4rem;
  line-height: 1;
  font-weight: 700;
  color: var(--brand-strong);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', serif;
}

.detail__meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail__name {
  align-self: flex-start;
  font-size: 1.4rem;
  font-weight: 800;
  color: var(--text-strong);
}

.detail__pinyin {
  font-size: 0.85rem;
}

.detail__from {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-top: 4px;
}

.detail__emoji {
  font-size: 2.4rem;
  align-self: flex-start;
}

.detail__meaning {
  font-size: 1.05rem;
  line-height: 1.8;
  color: var(--text);
}

.detail__hint {
  padding: 12px 16px;
  border-radius: var(--radius-md);
  background: var(--accent-soft);
  color: var(--text-strong);
  font-size: 0.92rem;
  line-height: 1.7;
}

.detail__block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail__label {
  font-size: 0.92rem;
  font-weight: 800;
  color: var(--text-strong);
}

.detail__note {
  font-size: 0.76rem;
}

.chars {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.chars__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0;
  width: 68px;
  height: 68px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  border: 2px solid transparent;
  box-shadow: var(--shadow-sm);
  transition: transform var(--dur-fast) var(--ease-pop);
}

.chars__item:active {
  transform: scale(0.94);
}

.chars__item.is-done {
  border-color: var(--accent);
}

.chars__item--ghost {
  opacity: 0.75;
  border-style: dashed;
  border-color: var(--stroke-hint);
  background: transparent;
  box-shadow: none;
}

.chars__char {
  font-size: 1.8rem;
  line-height: 1.1;
  font-weight: 700;
  color: var(--text-strong);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', serif;
}

.chars__item small {
  font-size: 0.65rem;
  color: var(--text-soft);
}

@media (max-width: 520px) {
  .detail__glyph {
    width: 84px;
    height: 84px;
  }
  .detail__glyph span {
    font-size: 3rem;
  }
}
</style>
