<script setup>
/**
 * 字源演变小舞台。
 *
 * 一个字的来历分两帧演给孩子看：
 *
 *   第一帧「古人看到的样子」
 *     象形 / 指事字放一张小图（语料里的形状 DSL，见 utils/etymologySketch.js）；
 *     会意 / 形声字放几个零件（明 = 日 + 月）。
 *   第二帧「今天写的样子」
 *     直接用 hanzi-writer 的笔顺数据（makemeahanzi 一脉，和「写一写」同一份
 *     离线数据），按笔顺一笔一笔写出来。
 *
 * 中间那段「怎么从图变成字」交给 GSAP：小图边淡出边缩一点，字在同一个位置
 * 长出来，两帧叠在一处，孩子的视线不用跳。
 *
 * 笔画不是线条而是填好的轮廓，没法直接拿 stroke-dashoffset 画。这里的办法是
 * 给每一笔配一个 <mask>：mask 里放这一笔的中线（medians），把它加粗成一条
 * 白色的粗线，再动画它的 dashoffset——白线扫到哪里，那一笔就显出到哪里。
 * 这也是笔顺动画的通行做法，好处是笔画本身还是原来的轮廓，不会走形。
 *
 * 减少动态时（家长中心的开关，或系统的 prefers-reduced-motion）整套时间线
 * 都不建：两帧并排铺开，各自静止显示，配文照旧。看得到的信息一样多，
 * 只是不动——这一页的价值本来就在「图和字长得像」，不在动画本身。
 *
 * 这个组件连同 etymology.js 一起是按需加载的：单字页用 etymology-index.js
 * 里那串汉字判断要不要显示入口，孩子点了才 import() 进来。
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import gsap from 'gsap'
import { getEtymology, kindOf } from '@/data/etymology.js'
import { medianPath, sketchPaths } from '@/utils/etymologySketch.js'
import { loadCharData } from '@/utils/hanziData.js'
import { useSettingsStore } from '@/stores/settings.js'
import { sfx } from '@/utils/sfx.js'

const props = defineProps({
  char: { type: String, required: true },
  size: { type: Number, default: 220 },
  /** 数据一到就自动放一遍。列表里的小卡片用 false，详情里的大舞台用 true。 */
  autoplay: { type: Boolean, default: true }
})

const emit = defineEmits(['played'])

const settings = useSettingsStore()

/** mask 的 id 必须全局唯一：同一页可能同时挂着好几个舞台。 */
let seq = 0
const uid = `ety${(seq += 1)}-${Math.random().toString(36).slice(2, 7)}`

const sketchSvgRef = ref(null)
const partsRef = ref(null)
const glyphSvgRef = ref(null)

/** idle | loading | ready | failed */
const status = ref('idle')
/** look 看图 / write 写字 / done 演完了 */
const stage = ref('look')
const announce = ref('')

const strokes = ref([])
let timeline = null
let disposed = false

const entry = computed(() => getEtymology(props.char))
const kind = computed(() => kindOf(entry.value))
const sketch = computed(() => sketchPaths(entry.value?.sketch))
const parts = computed(() => entry.value?.parts ?? null)

/**
 * 家长中心的「减少动态」和系统的 prefers-reduced-motion 都算数。
 * 前者是这台设备上这个孩子的选择，后者是整机的无障碍设置，任意一个开着就不动。
 */
const reduced = computed(
  () =>
    settings.reduceMotion ||
    (typeof window !== 'undefined' &&
      !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches)
)

const maskId = (i) => `${uid}-m${i}`

const kindLabel = computed(() => (kind.value ? `${kind.value.name}字` : ''))

const lookCaption = computed(() =>
  parts.value ? '把零件拆开看' : '古人看到的样子（我们照着意思画的）'
)

/* ------------------------------------------------------------------ 数据 */

async function load() {
  strokes.value = []
  if (!entry.value) {
    status.value = 'failed'
    return
  }
  status.value = 'loading'
  const data = await loadCharData(props.char)
  if (disposed || props.char !== entry.value.c) return
  if (!data?.strokes?.length) {
    // 笔顺数据没拿到也别整块塌掉：第一帧还在，配文还在，只是写不出字
    status.value = 'failed'
    return
  }
  strokes.value = data.strokes.map((d, i) => ({ d, median: medianPath(data.medians?.[i] ?? []) }))
  status.value = 'ready'
  if (props.autoplay) requestAnimationFrame(() => play())
  else settle()
}

/* ------------------------------------------------------------------ 动画 */

function kill() {
  timeline?.kill()
  timeline = null
}

const sketchEls = () => [...(sketchSvgRef.value?.querySelectorAll('.ety__ink') ?? [])]
const partEls = () => [...(partsRef.value?.querySelectorAll('.ety__part, .ety__plus') ?? [])]
const revealEls = () => [...(glyphSvgRef.value?.querySelectorAll('.ety__reveal') ?? [])]

/** 把两帧都摆成「演完了」的样子：静止模式和动画收尾都用它。 */
function settle() {
  gsap.set([...sketchEls(), ...partEls()], { clearProps: 'all' })
  gsap.set(revealEls(), { clearProps: 'all' })
  stage.value = 'done'
}

function play() {
  if (status.value !== 'ready') return
  kill()

  if (reduced.value) {
    settle()
    announce.value =
      `「${props.char}」的来历：${entry.value.origin}${entry.value.evolve}` +
      '（已按「减少动态」设置关掉动画，两幅图都直接摆出来了。）'
    emit('played')
    return
  }

  stage.value = 'look'
  announce.value = `先看图：${entry.value.origin}`

  const ink = sketchEls()
  const chips = partEls()
  const reveals = revealEls()

  timeline = gsap.timeline({
    onComplete() {
      stage.value = 'done'
      announce.value = `${entry.value.evolve}这就是今天写的「${props.char}」。`
      emit('played')
    }
  })

  // 第一帧：小图一笔一笔画出来（实心的点改成弹一下，画不出线）
  for (const el of ink) {
    if (el.dataset.fill === '1') {
      timeline.fromTo(
        el,
        { opacity: 0, scale: 0.2, transformOrigin: 'center' },
        { opacity: 1, scale: 1, duration: 0.28, ease: 'back.out(2.4)' },
        '>-0.16'
      )
      continue
    }
    const len = el.getTotalLength?.() ?? 100
    timeline.fromTo(
      el,
      { strokeDasharray: len, strokeDashoffset: len, opacity: 1 },
      {
        strokeDashoffset: 0,
        duration: Math.min(0.7, 0.16 + len / 260),
        ease: 'power1.inOut'
      },
      '>-0.1'
    )
  }

  // 第一帧（零件版）：几个部件挨个落下来
  if (chips.length) {
    timeline.fromTo(
      chips,
      { opacity: 0, y: 18, scale: 0.86 },
      { opacity: 1, y: 0, scale: 1, duration: 0.36, stagger: 0.12, ease: 'back.out(1.7)' },
      0
    )
  }

  // 中间：图停一下再让位，孩子得有时间看清楚
  timeline.to({}, { duration: 0.7 })
  timeline.call(() => {
    stage.value = 'write'
    announce.value = `${entry.value.evolve}现在一笔一笔写出来。`
  })

  // 第二帧：mask 里的白线扫过去，笔画就跟着显出来
  if (reveals.length) {
    gsap.set(reveals, { strokeDashoffset: (i, el) => Number(el.dataset.len) })
    for (const el of reveals) {
      const len = Number(el.dataset.len) || 1
      timeline.to(
        el,
        { strokeDashoffset: 0, duration: Math.min(0.8, 0.2 + len / 900), ease: 'none' },
        '>-0.06'
      )
    }
  }
}

function replay() {
  sfx.tap()
  play()
}

/** 手动看某一帧：不想等动画的孩子（和读屏用户）可以直接切。 */
function goStage(id) {
  sfx.tap()
  kill()
  settle()
  stage.value = id
  announce.value =
    id === 'look' ? `${lookCaption.value}：${entry.value.origin}` : `今天写的「${props.char}」。`
}

watch(() => props.char, load, { immediate: true })
watch(reduced, () => {
  if (status.value === 'ready') play()
})

onBeforeUnmount(() => {
  disposed = true
  kill()
})

defineExpose({ play, goStage })
</script>

<template>
  <div
    v-if="entry"
    class="ety"
    :class="{ 'ety--static': reduced }"
    :data-stage="reduced ? 'static' : stage"
    :data-char="char"
    :data-kind="entry.kind"
    :data-ready="status === 'ready' ? 'true' : 'false'"
  >
    <div class="ety__frames" :style="{ '--ety-size': `${size}px` }">
      <!-- 第一帧：古人看到的样子 / 拆开的零件 -->
      <figure class="ety__frame ety__frame--look">
        <div class="ety__slot">
          <svg
            v-if="entry.sketch"
            ref="sketchSvgRef"
            class="ety__sketch"
            viewBox="0 0 100 100"
            role="img"
            :aria-label="`「${char}」的字源示意图：${entry.origin}`"
          >
            <path
              v-for="p in sketch"
              :key="p.key"
              class="ety__ink"
              :class="{ 'is-fill': p.fill }"
              :data-fill="p.fill ? '1' : '0'"
              :d="p.d"
            />
          </svg>

          <div
            v-else
            ref="partsRef"
            class="ety__parts"
            role="img"
            :aria-label="`「${char}」由 ${parts.map((p) => p.g).join('、')} 组成：${entry.origin}`"
          >
            <template v-for="(p, i) in parts" :key="`${p.g}-${i}`">
              <span v-if="i" class="ety__plus" aria-hidden="true">+</span>
              <span class="ety__part">
                <span class="ety__part-glyph">{{ p.g }}</span>
                <span class="ety__part-note">{{ p.m }}</span>
              </span>
            </template>
          </div>
        </div>
        <figcaption class="ety__cap">{{ lookCaption }}</figcaption>
      </figure>

      <span class="ety__arrow" aria-hidden="true">→</span>

      <!-- 第二帧：今天写的样子 -->
      <figure class="ety__frame ety__frame--write">
        <div class="ety__slot">
          <svg
            v-if="status === 'ready'"
            ref="glyphSvgRef"
            class="ety__glyph"
            viewBox="0 0 1024 1024"
            role="img"
            :aria-label="`今天写的「${char}」，共 ${strokes.length} 笔`"
          >
            <defs>
              <mask
                v-for="(s, i) in strokes"
                :id="maskId(i)"
                :key="`m${i}`"
                maskUnits="userSpaceOnUse"
                x="-256"
                y="-256"
                width="1536"
                height="1536"
              >
                <path
                  class="ety__reveal"
                  :d="s.median.d"
                  :data-len="Math.round(s.median.length)"
                  :style="{ strokeDasharray: Math.round(s.median.length) }"
                />
              </mask>
            </defs>
            <g transform="scale(1, -1) translate(0, -900)">
              <path
                v-for="(s, i) in strokes"
                :key="`s${i}`"
                class="ety__stroke"
                :d="s.d"
                :mask="reduced ? undefined : `url(#${maskId(i)})`"
              />
            </g>
          </svg>
          <p v-else class="ety__plain" :aria-label="`今天写的「${char}」`">{{ char }}</p>
        </div>
        <figcaption class="ety__cap">今天写的「{{ char }}」</figcaption>
      </figure>
    </div>

    <!-- 配文：动画能说的，文字也要说一遍 -->
    <div class="ety__text">
      <p class="ety__kind">
        <span aria-hidden="true">{{ kind?.emoji }}</span>
        <strong>{{ kindLabel }}</strong>
        <span class="muted">{{ kind?.desc }}</span>
      </p>
      <p class="ety__line">{{ entry.origin }}</p>
      <p class="ety__line ety__line--soft">{{ entry.evolve }}</p>
    </div>

    <div class="ety__acts">
      <button
        v-if="!reduced"
        class="btn btn--primary btn--sm"
        type="button"
        :disabled="status !== 'ready'"
        @click="replay"
      >
        ▶️ 再演一遍
      </button>
      <button class="btn btn--ghost btn--sm" type="button" @click="goStage('look')">
        🖼️ 只看图
      </button>
      <button
        class="btn btn--ghost btn--sm"
        type="button"
        :disabled="status !== 'ready'"
        @click="goStage('write')"
      >
        🖌️ 只看字
      </button>
    </div>

    <p class="sr-only" role="status" aria-live="polite" aria-atomic="true">{{ announce }}</p>
  </div>
</template>

<style scoped>
.ety {
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
  width: 100%;
}

.ety__frames {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--gap-sm);
}

.ety__frame {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  margin: 0;
}

.ety__slot {
  position: relative;
  display: grid;
  place-items: center;
  width: var(--ety-size);
  height: var(--ety-size);
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  border: 2px dashed var(--stroke-hint);
}

.ety__frame--write .ety__slot {
  border-style: solid;
  border-color: var(--surface-border);
}

.ety__sketch,
.ety__glyph {
  width: 86%;
  height: 86%;
  overflow: visible;
}

.ety__ink {
  fill: none;
  stroke: var(--brand-strong);
  stroke-width: 3.4;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.ety__ink.is-fill {
  fill: var(--brand-strong);
  stroke: none;
}

.ety__stroke {
  fill: var(--stroke-ink);
}

.ety__reveal {
  fill: none;
  stroke: #fff; /* token-ok: mask 里的白色是「显出来」的开关，不是界面颜色 */
  stroke-width: 260;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.ety__parts {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 4px;
  padding: 6px;
}

.ety__part {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  max-width: 78px;
}

.ety__part-glyph {
  font-size: clamp(1.8rem, 8vw, 2.5rem);
  line-height: 1.1;
  color: var(--text-strong);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

.ety__part-note {
  font-size: 0.66rem;
  line-height: 1.4;
  text-align: center;
  color: var(--text-soft);
}

.ety__plus {
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--text-soft);
}

.ety__plain {
  font-size: calc(var(--ety-size) * 0.55);
  line-height: 1;
  color: var(--text-strong);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

.ety__cap {
  max-width: var(--ety-size);
  font-size: 0.72rem;
  line-height: 1.5;
  text-align: center;
  color: var(--text-soft);
}

.ety__arrow {
  font-size: 1.5rem;
  color: var(--text-soft);
}

/*
 * 动画模式下两帧是叠在一处的：图淡出、字长出来，视线不用来回跳。
 * 静止模式（下面的 .ety--static）才把它们并排铺开。
 */
.ety:not(.ety--static) .ety__frames {
  position: relative;
  display: grid;
  place-items: center;
  min-height: calc(var(--ety-size) + 26px);
}

.ety:not(.ety--static) .ety__frame {
  grid-area: 1 / 1;
  transition: opacity var(--dur-mid) ease, transform var(--dur-mid) var(--ease-pop);
}

.ety:not(.ety--static) .ety__arrow {
  display: none;
}

.ety[data-stage='look'] .ety__frame--write {
  opacity: 0;
  transform: scale(0.9);
  pointer-events: none;
}

.ety[data-stage='write'] .ety__frame--look,
.ety[data-stage='done'] .ety__frame--look {
  opacity: 0;
  transform: scale(1.08);
  pointer-events: none;
}

.ety__text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ety__kind {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 0.85rem;
}

.ety__kind strong {
  color: var(--text-strong);
}

.ety__kind .muted {
  font-size: 0.78rem;
}

.ety__line {
  font-size: 0.95rem;
  line-height: 1.75;
  color: var(--text);
}

.ety__line--soft {
  color: var(--text-soft);
}

.ety__acts {
  display: flex;
  flex-wrap: wrap;
  gap: var(--gap-sm);
}

/* -------------------------------------------------------------- 减少动态 */
.ety--static .ety__frames {
  flex-wrap: wrap;
}

@media (max-width: 420px) {
  .ety__frames {
    --ety-size: min(200px, 62vw);
  }
}
</style>
