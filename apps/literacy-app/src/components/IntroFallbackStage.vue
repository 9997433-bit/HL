<script setup>
/**
 * ROUND16_H2 · 「认一认」的回退舞台：没有字源的字也得有得看。
 *
 * 有字源语料的字在「认」这一步是 EtymologyStage 自动播演变动画；剩下的
 * 一千来个字原来只有一行释义加一个朗读按钮。同一步之内两种密度差得太远，
 * 孩子翻到冷门字就像走进空房间——这台舞台补的就是那间空房。
 *
 * 讲什么由 data/intro-fallback.js 定（三幕：部首 → 零件 → 组词情境），
 * 这里只管怎么演：
 *
 *   ① 部首  部首牌先弹出来，说清它管什么意思、一家子还有谁；
 *           说完让位，整个字在同一个位置一笔一笔写出来
 *   ② 零件  「部首 + ？= 这个字」摆成一道算式，问号牌翻个身
 *   ③ 组词  组词一张一张落下来，目标字在词里、在句子里都点亮
 *
 * 写字那一帧和 EtymologyStage 用同一套办法：笔画是填好的轮廓，画不了
 * dashoffset，就给每一笔配一个 mask，让 mask 里的白粗线扫过去。笔顺数据
 * 取不到（生僻字、离线包没裁进来）也不空台——那一帧退成一个大字。
 *
 * 减少动态：一条时间线都不建，三幕直接铺开各自静止显示，配文一字不少，
 * 并立刻 emit played，让父级的五步流程照常往下走。
 *
 * 对外只有一件事：`played`——三幕都看完了（自动演完，或者孩子自己点着看完）。
 */
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import gsap from 'gsap'
import { ROUND16_H2, buildIntroFallback } from '@/data/intro-fallback.js'
import { medianPath } from '@/utils/etymologySketch.js'
import { loadCharData } from '@/utils/hanziData.js'
import { useSettingsStore } from '@/stores/settings.js'
import { sfx } from '@/utils/sfx.js'

const props = defineProps({
  char: { type: String, required: true },
  /** 已经加载好的字条目：带释义 / 组词 / 例句，第三幕要用。 */
  item: { type: Object, default: null },
  size: { type: Number, default: 176 },
  /** 摆上台就自己讲一遍。列表里的小卡片可以关掉。 */
  autoplay: { type: Boolean, default: true }
})

const emit = defineEmits(['played'])

// 没有 pinia 的单测 / 脚本里也要能挂载，取不到设置就只看系统偏好
let settings = null
try {
  settings = useSettingsStore()
} catch {
  settings = null
}

/** mask 的 id 要全局唯一：一屏上可能同时站着好几台舞台。 */
let seq = 0
const uid = `ifs${(seq += 1)}-${Math.random().toString(36).slice(2, 7)}`
const maskId = (i) => `${uid}-m${i}`

const rootRef = ref(null)
const glyphSvgRef = ref(null)

const plan = computed(() => buildIntroFallback(props.char, props.item))
const scenes = computed(() => plan.value.scenes)
const sceneOf = (id) => scenes.value.find((s) => s.id === id) ?? null

/** 正在演的那一幕。 */
const scene = ref('radical')
/** 第一幕内部还有两拍：look 看部首牌 → write 写整个字。 */
const beat = ref('look')
/** 看过的幕；三幕都看过就算「认过了」。 */
const seen = reactive(new Set())
const announce = ref('')
const strokes = ref([])
/** idle | ready | failed —— 只说笔顺数据，取不到也不影响讲课。 */
const status = ref('idle')

let timeline = null
/** 时间线之外自己起的小动画（道具落地、写字），停的时候一起收。 */
let extras = []
let disposed = false
let told = false

const reduced = computed(
  () =>
    settings?.reduceMotion === true ||
    (typeof window !== 'undefined' &&
      window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches === true)
)

/* ------------------------------------------------------------------ 数据 */

async function loadStrokes() {
  strokes.value = []
  status.value = 'idle'
  const char = props.char
  const data = await loadCharData(char)
  if (disposed || props.char !== char) return
  if (!data?.strokes?.length) {
    status.value = 'failed'
    return
  }
  strokes.value = data.strokes.map((d, i) => ({
    d,
    median: medianPath(data.medians?.[i] ?? [])
  }))
  status.value = 'ready'
}

/* ------------------------------------------------------------------ 动画 */

function kill() {
  timeline?.kill()
  timeline = null
  for (const t of extras) t.kill()
  extras = []
}

const els = (selector) => [...(rootRef.value?.querySelectorAll(selector) ?? [])]
const revealEls = () => [...(glyphSvgRef.value?.querySelectorAll('.ifs__reveal') ?? [])]

/** 把所有元素摆成「演完了」的样子。静止模式和收尾都用它。 */
function settle() {
  gsap.set(els('.ifs__anim'), { clearProps: 'all' })
  gsap.set(revealEls(), { clearProps: 'all' })
}

function markSeen(id) {
  seen.add(id)
  if (told || seen.size < scenes.value.length) return
  told = true
  emit('played')
}

function goScene(id, { manual = false } = {}) {
  if (manual) {
    sfx.tap()
    kill()
    settle()
  }
  scene.value = id
  beat.value = id === 'radical' && !manual ? 'look' : 'done'
  const act = sceneOf(id)
  announce.value = act ? `${act.line}${act.note ? ` ${act.note}` : ''}` : ''
  markSeen(id)
}

/** 一幕里的道具挨个落下来。减少动态时这个函数根本不会被调到。 */
function popIn(selector) {
  const nodes = els(selector)
  if (!nodes.length) return
  extras.push(
    gsap.fromTo(
      nodes,
      { autoAlpha: 0, y: 16, scale: 0.9 },
      {
        autoAlpha: 1,
        y: 0,
        scale: 1,
        duration: 0.38,
        stagger: 0.08,
        ease: 'back.out(1.7)',
        clearProps: 'opacity,visibility,transform'
      }
    )
  )
}

/** 第一幕的收尾：整个字在部首让位之后一笔一笔写出来。 */
function writeGlyph() {
  beat.value = 'write'
  const reveals = revealEls()
  if (!reveals.length) {
    // 笔顺数据没到：退成一个大字弹出来，这一帧照样不空
    popIn('.ifs__plain')
    return
  }
  gsap.set(reveals, { strokeDashoffset: (i, el) => Number(el.dataset.len) })
  const write = gsap.timeline()
  for (const el of reveals) {
    const len = Number(el.dataset.len) || 1
    write.to(
      el,
      { strokeDashoffset: 0, duration: Math.min(0.62, 0.18 + len / 1100), ease: 'none' },
      '>-0.05'
    )
  }
  extras.push(write)
}

function play() {
  kill()
  told = false
  seen.clear()

  if (reduced.value) {
    // 三幕全铺开，静止显示。看得到的信息一个字不少，只是不动
    scene.value = 'radical'
    beat.value = 'done'
    settle()
    for (const act of scenes.value) seen.add(act.id)
    announce.value =
      scenes.value.map((act) => `${act.line}${act.note ? ` ${act.note}` : ''}`).join(' ') +
      '（已按「减少动态」设置关掉动画，三幕都直接摆出来了。）'
    told = true
    emit('played')
    return
  }

  scene.value = 'radical'
  beat.value = 'look'
  announce.value = sceneOf('radical')?.line ?? ''

  timeline = gsap.timeline()

  // ① 部首：部首牌 + 一家子先落地，看够两秒再让位给整个字
  timeline.call(() => {
    markSeen('radical')
    popIn('[data-act="radical"] .ifs__anim')
  })
  timeline.to({}, { duration: 2.2 })
  timeline.call(() => writeGlyph())
  timeline.to({}, { duration: 1.5 })

  // ② 零件：算式一张一张摆好，问号牌翻个身
  timeline.call(() => {
    goScene('parts')
    popIn('[data-act="parts"] .ifs__anim')
    const rest = els('[data-act="parts"] .ifs__piece--rest')
    if (rest.length) {
      extras.push(
        gsap.fromTo(
          rest,
          { rotateY: 0 },
          { rotateY: 360, duration: 0.9, delay: 0.5, ease: 'power2.inOut', clearProps: 'transform' }
        )
      )
    }
  })
  timeline.to({}, { duration: 3 })

  // ③ 组词：词卡落下来，目标字在词里、在句子里都点亮
  timeline.call(() => {
    goScene('word')
    popIn('[data-act="word"] .ifs__anim')
  })
  timeline.to({}, { duration: 2.6 })
}

function replay() {
  sfx.tap()
  play()
}

function start() {
  kill()
  told = false
  seen.clear()
  loadStrokes()
  if (props.autoplay) play()
  else {
    scene.value = 'radical'
    beat.value = 'done'
    announce.value = sceneOf('radical')?.line ?? ''
  }
}

onMounted(start)
watch(() => props.char, start)

// 「减少动态」当场改了也算数：正在演的就停下，改成铺开
watch(reduced, () => {
  if (props.autoplay) play()
})

onBeforeUnmount(() => {
  disposed = true
  kill()
})

defineExpose({ play, goScene })
</script>

<template>
  <div
    ref="rootRef"
    class="ifs"
    :class="{ 'ifs--static': reduced }"
    :data-round16="ROUND16_H2"
    :data-char="char"
    :data-scene="reduced ? 'static' : scene"
    :data-beat="beat"
    :data-strokes="status"
    :style="{ '--ifs-size': `min(${size}px, 46vw)` }"
  >
    <div class="ifs__acts-stack">
      <!-- ① 部首：先认零件，再看整个字写出来 -->
      <section
        v-if="sceneOf('radical')"
        class="ifs__act"
        data-act="radical"
        :aria-hidden="!reduced && scene !== 'radical' ? 'true' : undefined"
      >
        <p class="ifs__title">
          <span aria-hidden="true">{{ sceneOf('radical').emoji }}</span>
          {{ sceneOf('radical').title }}
        </p>
        <div class="ifs__frames">
          <figure class="ifs__frame ifs__frame--look">
            <div class="ifs__slot ifs__anim">
              <span class="ifs__radical-glyph">{{ sceneOf('radical').glyph }}</span>
            </div>
            <figcaption class="ifs__cap">{{ sceneOf('radical').name }}</figcaption>
          </figure>

          <span class="ifs__arrow" aria-hidden="true">→</span>

          <figure class="ifs__frame ifs__frame--write">
            <div class="ifs__slot">
              <svg
                v-if="status === 'ready'"
                ref="glyphSvgRef"
                class="ifs__glyph"
                viewBox="0 0 1024 1024"
                role="img"
                :aria-label="`「${char}」，共 ${strokes.length} 笔`"
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
                      class="ifs__reveal"
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
                    class="ifs__stroke"
                    :d="s.d"
                    :mask="reduced ? undefined : `url(#${maskId(i)})`"
                  />
                </g>
              </svg>
              <p v-else class="ifs__plain ifs__anim" :aria-label="char">{{ char }}</p>
            </div>
            <figcaption class="ifs__cap">
              整个字「{{ char }}」 · {{ sceneOf('radical').strokes }} 画
            </figcaption>
          </figure>
        </div>
        <p class="ifs__line">{{ sceneOf('radical').line }}</p>
        <p class="ifs__line ifs__line--soft">{{ sceneOf('radical').note }}</p>
        <p v-if="sceneOf('radical').family.length" class="ifs__family ifs__anim">
          <span class="muted">{{ sceneOf('radical').familyLabel }}</span>
          <span
            v-for="f in sceneOf('radical').family"
            :key="f"
            class="ifs__chip ifs__anim"
          >{{ f }}</span>
        </p>
      </section>

      <!-- ② 零件：认识的那一半 + 留着不瞎猜的那一半 -->
      <section
        v-if="sceneOf('parts')"
        class="ifs__act"
        data-act="parts"
        :aria-hidden="!reduced && scene !== 'parts' ? 'true' : undefined"
      >
        <p class="ifs__title">
          <span aria-hidden="true">🧩</span>
          {{ sceneOf('parts').title }}
        </p>
        <div v-if="sceneOf('parts').mode === 'split'" class="ifs__equation">
          <template v-for="(p, i) in sceneOf('parts').pieces" :key="p.key">
            <span v-if="i" class="ifs__plus" aria-hidden="true">+</span>
            <span
              class="ifs__piece ifs__anim"
              :class="{
                'ifs__piece--known': p.known,
                'ifs__piece--rest': !p.known
              }"
            >
              <span class="ifs__piece-glyph">{{ p.glyph }}</span>
              <span class="ifs__piece-label">{{ p.label }}</span>
            </span>
          </template>
          <span class="ifs__plus" aria-hidden="true">=</span>
          <span class="ifs__piece ifs__piece--whole ifs__anim">
            <span class="ifs__piece-glyph">{{ char }}</span>
            <span class="ifs__piece-label">{{ sceneOf('parts').strokes }} 画</span>
          </span>
        </div>
        <div v-else class="ifs__equation">
          <span class="ifs__piece ifs__piece--whole ifs__anim">
            <span class="ifs__piece-glyph">{{ char }}</span>
            <span class="ifs__piece-label">{{ sceneOf('parts').strokes }} 画</span>
          </span>
          <template v-if="sceneOf('parts').family.length">
            <span class="ifs__plus" aria-hidden="true">→</span>
            <span
              v-for="f in sceneOf('parts').family.slice(0, 4)"
              :key="f"
              class="ifs__piece ifs__piece--known ifs__anim"
            >
              <span class="ifs__piece-glyph">{{ f }}</span>
              <span class="ifs__piece-label">里也有它</span>
            </span>
          </template>
        </div>
        <p class="ifs__line">{{ sceneOf('parts').line }}</p>
        <p class="ifs__line ifs__line--soft">{{ sceneOf('parts').note }}</p>
      </section>

      <!-- ③ 组词情境：这个字在词里、在句子里 -->
      <section
        v-if="sceneOf('word')"
        class="ifs__act"
        data-act="word"
        :aria-hidden="!reduced && scene !== 'word' ? 'true' : undefined"
      >
        <p class="ifs__title">
          <span aria-hidden="true">{{ sceneOf('word').emoji }}</span>
          {{ sceneOf('word').title }}
        </p>
        <div v-if="sceneOf('word').words.length" class="ifs__words">
          <span v-for="w in sceneOf('word').words" :key="w.w" class="ifs__word ifs__anim">
            <span class="ifs__word-pinyin">{{ w.p }}</span>
            <span class="ifs__word-text">
              <span
                v-for="(ch, i) in w.w"
                :key="`${ch}-${i}`"
                class="ifs__word-char"
                :class="{ 'is-target': ch === char }"
              >{{ ch }}</span>
            </span>
          </span>
        </div>
        <p v-else class="ifs__plain-word ifs__anim">
          <span class="ifs__word-text">{{ char }}</span>
          <span class="muted">{{ sceneOf('word').pinyin }}</span>
        </p>
        <p v-if="sceneOf('word').sentence" class="ifs__sentence ifs__anim">
          <span
            v-for="(ch, i) in sceneOf('word').sentence.text"
            :key="`s-${ch}-${i}`"
            class="ifs__word-char"
            :class="{ 'is-target': ch === char }"
          >{{ ch }}</span>
        </p>
        <p class="ifs__line">{{ sceneOf('word').line }}</p>
        <p class="ifs__line ifs__line--soft">{{ sceneOf('word').note }}</p>
      </section>
    </div>

    <!-- 想自己看哪一幕就看哪一幕：不等动画，读屏用户也用得上 -->
    <div class="ifs__nav">
      <button
        v-if="!reduced"
        class="btn btn--primary btn--sm"
        type="button"
        @click="replay"
      >
        ▶️ 再讲一遍
      </button>
      <button
        v-for="(act, i) in scenes"
        :key="act.id"
        class="btn btn--ghost btn--sm"
        type="button"
        :aria-pressed="!reduced && scene === act.id ? 'true' : 'false'"
        @click="goScene(act.id, { manual: true })"
      >
        {{ ['①', '②', '③'][i] ?? '·' }} {{ act.title }}
      </button>
    </div>

    <p class="sr-only" role="status" aria-live="polite" aria-atomic="true">{{ announce }}</p>
  </div>
</template>

<style scoped>
.ifs {
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
  width: 100%;
}

/* 动画模式下三幕叠在一处，切幕不跳版；静止模式（下面）才竖着铺开 */
.ifs__acts-stack {
  display: grid;
  gap: var(--gap-md);
}

.ifs:not(.ifs--static) .ifs__act {
  grid-area: 1 / 1;
  transition: opacity var(--dur-mid) ease, transform var(--dur-mid) var(--ease-pop);
}

.ifs:not(.ifs--static) .ifs__act[aria-hidden='true'] {
  opacity: 0;
  transform: scale(0.96);
  pointer-events: none;
}

.ifs__act {
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
  align-items: center;
  text-align: center;
}

.ifs__title {
  align-self: flex-start;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
  font-weight: 800;
  color: var(--text-strong);
}

/* ---------------- ① 部首 ---------------- */
.ifs__frames {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--gap-sm);
}

.ifs__frame {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  margin: 0;
}

.ifs__slot {
  position: relative;
  display: grid;
  place-items: center;
  width: var(--ifs-size);
  height: var(--ifs-size);
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  border: 2px dashed var(--stroke-hint);
}

.ifs__frame--write .ifs__slot {
  border-style: solid;
  border-color: var(--surface-border);
}

.ifs__radical-glyph,
.ifs__plain {
  font-size: calc(var(--ifs-size) * 0.55);
  line-height: 1;
  color: var(--text-strong);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

.ifs__radical-glyph {
  color: var(--brand-strong);
}

.ifs__glyph {
  width: 86%;
  height: 86%;
  overflow: visible;
}

.ifs__stroke {
  fill: var(--stroke-ink);
}

.ifs__reveal {
  fill: none;
  stroke: #fff; /* token-ok: mask 里的白色是「显出来」的开关，不是界面颜色 */
  stroke-width: 260;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.ifs__cap {
  max-width: var(--ifs-size);
  font-size: 0.72rem;
  line-height: 1.5;
  color: var(--text-soft);
}

.ifs__arrow {
  font-size: 1.5rem;
  color: var(--text-soft);
}

/* 第一幕内部两拍：部首牌说完话，才把位置让给整个字 */
.ifs:not(.ifs--static) .ifs__frames {
  position: relative;
  display: grid;
  place-items: center;
  min-height: calc(var(--ifs-size) + 26px);
}

.ifs:not(.ifs--static) .ifs__frame {
  grid-area: 1 / 1;
  transition: opacity var(--dur-mid) ease, transform var(--dur-mid) var(--ease-pop);
}

.ifs:not(.ifs--static) .ifs__arrow {
  display: none;
}

.ifs[data-beat='look'] .ifs__frame--write {
  opacity: 0;
  transform: scale(0.9);
  pointer-events: none;
}

.ifs[data-beat='write'] .ifs__frame--look,
.ifs[data-beat='done'] .ifs__frame--look {
  opacity: 0;
  transform: scale(1.08);
  pointer-events: none;
}

/* 静止模式：两帧并排，谁也不藏 */
.ifs--static .ifs__frames {
  flex-wrap: wrap;
}

.ifs__family {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 0.85rem;
}

.ifs__chip {
  display: inline-grid;
  place-items: center;
  min-width: 40px;
  padding: 4px 10px;
  border-radius: var(--radius-pill);
  background: var(--accent-soft);
  color: var(--text-strong);
  font-size: 1.3rem;
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

/* ---------------- ② 零件 ---------------- */
.ifs__equation {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
  gap: var(--gap-sm);
}

.ifs__piece {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  min-width: 72px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  border: 2px solid transparent;
}

.ifs__piece--known {
  border-color: color-mix(in srgb, var(--brand) 45%, transparent);
}

.ifs__piece--rest {
  border-style: dashed;
  border-color: var(--stroke-hint);
}

.ifs__piece--whole {
  background: var(--accent-soft);
}

.ifs__piece-glyph {
  font-size: clamp(1.8rem, 8vw, 2.4rem);
  line-height: 1.1;
  color: var(--text-strong);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

.ifs__piece-label {
  font-size: 0.68rem;
  line-height: 1.4;
  color: var(--text-soft);
}

.ifs__plus {
  font-size: 1.2rem;
  font-weight: 800;
  color: var(--text-soft);
}

/* ---------------- ③ 组词 ---------------- */
.ifs__words {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: var(--gap-sm);
}

.ifs__word,
.ifs__plain-word {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 8px 14px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
}

.ifs__word-pinyin {
  font-size: 0.72rem;
  color: var(--text-soft);
}

.ifs__word-text {
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--text-strong);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

.ifs__sentence {
  font-size: 1.05rem;
  line-height: 1.8;
  color: var(--text);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

.ifs__word-char.is-target {
  color: var(--brand-strong);
  border-bottom: 3px solid var(--brand);
  border-radius: 2px;
}

/* ---------------- 配文与操作 ---------------- */
.ifs__line {
  font-size: 0.95rem;
  line-height: 1.75;
  color: var(--text);
}

.ifs__line--soft {
  font-size: 0.85rem;
  color: var(--text-soft);
}

.ifs__nav {
  display: flex;
  flex-wrap: wrap;
  gap: var(--gap-sm);
}
</style>
