<script setup>
/**
 * 单字学习页 —— 整个应用的核心。
 *
 * 一个字分三步走，对应顶部的三个标签：
 *   认一认  看图、听音、读组词和例句（掌握度 → 1）
 *   看笔顺  hanzi-writer 逐笔演示，可反复播放、可调速
 *   描一描  在田字格里按笔顺描红，全部写对才算过（掌握度 → 2）
 *
 * 页面地址里带字（/learn/花），方便家长直接把某个字的链接存起来。
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { gsap } from 'gsap'

import { CHARACTERS, getCharacter, unitById } from '@/data/characters.js'
import { getRadical } from '@/data/radicals.js'

import HanziWriter from '@/components/HanziWriter.vue'
import MascotCompanion from '@/components/MascotCompanion.vue'
import PinyinRuby from '@/components/PinyinRuby.vue'
import SpeakButton from '@/components/SpeakButton.vue'
import { useProgressStore } from '@/stores/progress.js'
import { MASTERY } from '@/stores/progress.js'
import { sfx, speak } from '@/utils/audio.js'

const route = useRoute()
const router = useRouter()
const progress = useProgressStore()

const TABS = [
  { id: 'meet', icon: '👀', label: '认一认' },
  { id: 'stroke', icon: '🖌️', label: '看笔顺' },
  { id: 'trace', icon: '✍️', label: '描一描' }
]

const tab = ref('meet')
const writerRef = ref(null)
const page = ref(null)
const heroChar = ref(null)

/** 描红结果：null 未完成 / {mistakes} 已完成 */
const traceResult = ref(null)
const traceMistakes = ref(0)

const char = computed(() => {
  const wanted = route.params.char ? decodeURIComponent(route.params.char) : ''
  return getCharacter(wanted) ?? CHARACTERS[0]
})

const index = computed(() => CHARACTERS.findIndex((c) => c.char === char.value.char))
const prevChar = computed(() => (index.value > 0 ? CHARACTERS[index.value - 1] : null))
const nextChar = computed(() =>
  index.value < CHARACTERS.length - 1 ? CHARACTERS[index.value + 1] : null
)

const unit = computed(() => unitById(char.value.unit))
const radical = computed(() => getRadical(char.value.radical))
const stat = computed(() => progress.charStat(char.value.char))
const mastery = computed(() => MASTERY[stat.value.level] ?? MASTERY[0])

/** 描红速度，孩子可以自己调慢。 */
const speed = ref(0.7)
const SPEEDS = [
  { v: 0.4, label: '慢' },
  { v: 0.7, label: '中' },
  { v: 1.2, label: '快' }
]

const mascotSay = computed(() => {
  if (tab.value === 'trace') {
    if (traceResult.value) {
      return traceMistakes.value === 0 ? '一笔都没错，太漂亮啦！' : '写完啦！再来一遍会更稳。'
    }
    return '跟着淡淡的影子，一笔一笔写下来。'
  }
  if (tab.value === 'stroke') return `「${char.value.char}」一共 ${char.value.strokes} 笔，看好顺序哦。`
  return char.value.meaning
})

const mascotMood = computed(() => {
  if (tab.value === 'trace' && traceResult.value) {
    return traceMistakes.value === 0 ? 'cheer' : 'happy'
  }
  if (tab.value === 'stroke') return 'think'
  return 'idle'
})

/* ------------------------------------------------------------------ 交互 */

function goto(c) {
  if (!c) return
  sfx.page()
  router.push(`/learn/${encodeURIComponent(c.char)}`)
}

function switchTab(id) {
  sfx.tap()
  tab.value = id
  traceResult.value = null
}

function readChar() {
  progress.markHeard(char.value.char)
  speak(char.value.char, { rate: 0.7 })
}

function replayStrokes() {
  sfx.tap()
  writerRef.value?.animate()
}

function restartTrace() {
  sfx.tap()
  traceResult.value = null
  writerRef.value?.startQuiz()
}

function hint() {
  sfx.tap()
  writerRef.value?.hintStroke()
}

function onTraceDone(summary) {
  traceMistakes.value = summary.totalMistakes
  traceResult.value = summary
  progress.markTraced(char.value.char)
  if (summary.totalMistakes === 0) progress.recordQuiz(char.value.char, true)
  speak(char.value.char, { rate: 0.7 })
}

/** 认一认这一步：打开就算「见过」，听过读音才升到「认识」。 */
function registerVisit() {
  progress.markSeen(char.value.char)
}

function bounceHero() {
  if (!heroChar.value) return
  gsap.fromTo(
    heroChar.value,
    { scale: 0.75, rotate: -6, opacity: 0 },
    { scale: 1, rotate: 0, opacity: 1, duration: 0.55, ease: 'back.out(2)' }
  )
}

onMounted(() => {
  registerVisit()
  bounceHero()
  if (page.value) {
    gsap.from(page.value.querySelectorAll('[data-anim]'), {
      y: 20,
      opacity: 0,
      duration: 0.45,
      stagger: 0.06,
      ease: 'power2.out',
      clearProps: 'all'
    })
  }
})

watch(
  () => char.value.char,
  () => {
    registerVisit()
    traceResult.value = null
    tab.value = 'meet'
    bounceHero()
  }
)
</script>

<template>
  <div ref="page" class="page learn">
    <!-- 顶部：字 + 拼音 + 掌握度 -->
    <section class="head card" data-anim>
      <div class="head__main">
        <div ref="heroChar" class="head__glyph" :style="{ '--tint': unit?.color }">
          <span class="head__emoji" aria-hidden="true">{{ char.emoji }}</span>
          <span class="head__char">{{ char.char }}</span>
        </div>

        <div class="head__info">
          <p class="head__pinyin">{{ char.pinyin }}</p>
          <p class="head__meaning">{{ char.meaning }}</p>

          <div class="row">
            <span class="pill">{{ unit?.emoji }} {{ unit?.name }}</span>
            <span class="pill pill--accent">{{ char.strokes }} 笔</span>
            <span class="pill" :style="{ background: mastery.color, color: 'var(--text-strong)' }">
              {{ mastery.label }}
            </span>
          </div>

          <div class="row head__cta">
            <SpeakButton :text="char.char" label="读一读" size="md" @spoken="readChar" />
            <RouterLink
              v-if="radical"
              class="btn btn--ghost"
              :to="`/radicals/${radical.id}`"
              @click="sfx.tap()"
            >
              <span aria-hidden="true">🧩</span> 部首 {{ radical.glyph }}
            </RouterLink>
          </div>
        </div>
      </div>

      <!-- 上一个 / 下一个 -->
      <div class="head__nav">
        <button class="head__navbtn" type="button" :disabled="!prevChar" @click="goto(prevChar)">
          <span aria-hidden="true">←</span>
          <span>{{ prevChar?.char ?? '开头' }}</span>
        </button>
        <span class="head__pos">{{ index + 1 }} / {{ CHARACTERS.length }}</span>
        <button class="head__navbtn" type="button" :disabled="!nextChar" @click="goto(nextChar)">
          <span>{{ nextChar?.char ?? '结尾' }}</span>
          <span aria-hidden="true">→</span>
        </button>
      </div>
    </section>

    <!-- 三个步骤 -->
    <div class="tabs" role="tablist" data-anim>
      <button
        v-for="t in TABS"
        :key="t.id"
        class="tabs__btn"
        :class="{ 'is-active': tab === t.id }"
        type="button"
        role="tab"
        :aria-selected="tab === t.id"
        @click="switchTab(t.id)"
      >
        <span aria-hidden="true">{{ t.icon }}</span>
        {{ t.label }}
      </button>
    </div>

    <!-- ------------------------------------------------------- 认一认 -->
    <section v-if="tab === 'meet'" class="stack" data-anim>
      <div class="card stack">
        <h2 class="section-title">
          <span class="section-title__emoji">🧱</span>
          组词
        </h2>
        <div class="words">
          <button
            v-for="w in char.words"
            :key="w.w"
            class="word"
            type="button"
            @click="speak(w.w, { rate: 0.75 })"
          >
            <PinyinRuby :text="w.w" :pinyin="w.p" size="1.5rem" />
            <span class="word__play" aria-hidden="true">🔊</span>
          </button>
        </div>
      </div>

      <div class="card stack">
        <h2 class="section-title">
          <span class="section-title__emoji">💬</span>
          读一句
        </h2>
        <PinyinRuby
          :text="char.sentence.text"
          :pinyin="char.sentence.p"
          size="1.7rem"
          clickable
          @pick="(c) => getCharacter(c) && goto(getCharacter(c))"
        />
        <SpeakButton :text="char.sentence.text" label="听这句话" variant="ghost" size="md" />
        <p class="muted" style="font-size: 0.82rem">句子里认识的字可以点一下，直接跳过去学。</p>
      </div>

      <div class="card stack" v-if="radical && radical.meaning">
        <h2 class="section-title">
          <span class="section-title__emoji">🧩</span>
          它的偏旁
        </h2>
        <div class="radical-hint">
          <span class="radical-hint__glyph">{{ radical.glyph }}</span>
          <div>
            <strong>{{ radical.name }}</strong>
            <p class="muted">{{ radical.meaning }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- ------------------------------------------------------- 看笔顺 -->
    <section v-else-if="tab === 'stroke'" class="stack" data-anim>
      <div class="card writer-card">
        <HanziWriter
          ref="writerRef"
          :key="`stroke-${char.char}`"
          :char="char.char"
          :size="260"
          mode="animate"
          :speed="speed"
          :auto-start="true"
        />

        <div class="row writer-card__tools">
          <button class="btn btn--primary" type="button" @click="replayStrokes">
            <span aria-hidden="true">▶</span> 再看一遍
          </button>
          <button class="btn btn--ghost" type="button" @click="writerRef?.loopAnimation()">
            <span aria-hidden="true">🔁</span> 循环
          </button>
        </div>

        <div class="row speeds">
          <span class="muted">速度</span>
          <button
            v-for="s in SPEEDS"
            :key="s.v"
            class="speeds__btn"
            :class="{ 'is-active': speed === s.v }"
            type="button"
            @click="((speed = s.v), sfx.tap())"
          >
            {{ s.label }}
          </button>
        </div>
      </div>

      <div class="card stack">
        <h2 class="section-title">
          <span class="section-title__emoji">📏</span>
          写字小提示
        </h2>
        <ul class="tips">
          <li>先横后竖，先撇后捺。</li>
          <li>从上到下，从左到右。</li>
          <li>先外后内，最后封口。</li>
          <li>这个字有 <strong>{{ char.strokes }}</strong> 笔，数着写。</li>
        </ul>
      </div>
    </section>

    <!-- ------------------------------------------------------- 描一描 -->
    <section v-else class="stack" data-anim>
      <div class="card writer-card">
        <HanziWriter
          ref="writerRef"
          :key="`trace-${char.char}`"
          :char="char.char"
          :size="280"
          mode="quiz"
          :speed="speed"
          :auto-start="true"
          :hint-after-misses="2"
          @quiz-complete="onTraceDone"
        >
          <template #footer="{ strokesDone, mistakes }">
            <div class="trace__meter" aria-hidden="true">
              <span
                v-for="n in char.strokes"
                :key="n"
                class="trace__pip"
                :class="{ 'is-done': n <= strokesDone }"
              ></span>
            </div>
            <p class="muted trace__count">
              第 {{ Math.min(strokesDone + 1, char.strokes) }} 笔 / 共 {{ char.strokes }} 笔
              <template v-if="mistakes > 0"> · 写歪了 {{ mistakes }} 次</template>
            </p>
          </template>
        </HanziWriter>

        <div class="row writer-card__tools">
          <button class="btn btn--ghost" type="button" @click="hint">
            <span aria-hidden="true">💡</span> 教我这一笔
          </button>
          <button class="btn btn--ghost" type="button" @click="restartTrace">
            <span aria-hidden="true">↺</span> 重来
          </button>
        </div>
      </div>

      <Transition name="fade-slide">
        <div v-if="traceResult" class="card result">
          <span class="result__emoji" aria-hidden="true">
            {{ traceMistakes === 0 ? '🏆' : '👏' }}
          </span>
          <div class="stack" style="gap: 4px">
            <strong class="result__title">
              {{ traceMistakes === 0 ? '完美！一笔都没写错' : `写完啦，中途歪了 ${traceMistakes} 次` }}
            </strong>
            <small class="muted">「{{ char.char }}」现在是「{{ mastery.label }}」</small>
          </div>
          <div class="row">
            <button class="btn btn--ghost" type="button" @click="restartTrace">再写一遍</button>
            <button
              v-if="nextChar"
              class="btn btn--primary"
              type="button"
              @click="goto(nextChar)"
            >
              下一个字 →
            </button>
          </div>
        </div>
      </Transition>
    </section>

    <!-- 学伴常驻在底部，给当前步骤配一句话 -->
    <div class="learn__mascot" data-anim>
      <MascotCompanion :mood="mascotMood" :say="mascotSay" :size="76" />
    </div>
  </div>
</template>

<style scoped>
/* -------------------------------------------------------------- 顶部信息 */

.head {
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
}

.head__main {
  display: flex;
  gap: var(--gap-lg);
  align-items: flex-start;
  flex-wrap: wrap;
}

.head__glyph {
  position: relative;
  flex: none;
  display: grid;
  place-items: center;
  width: 132px;
  height: 132px;
  border-radius: var(--radius-lg);
  background: linear-gradient(160deg, color-mix(in srgb, var(--tint, var(--brand)) 26%, transparent), var(--surface-strong));
  border: 3px solid color-mix(in srgb, var(--tint, var(--brand)) 45%, transparent);
  box-shadow: var(--shadow-sm);
}

.head__char {
  font-size: 4.6rem;
  font-weight: 800;
  line-height: 1;
  color: var(--stroke-ink);
}

.head__emoji {
  position: absolute;
  top: -12px;
  right: -10px;
  font-size: 1.9rem;
  filter: drop-shadow(0 3px 5px rgba(0, 0, 0, 0.16));
  animation: float-y 3.4s ease-in-out infinite;
}

.head__info {
  flex: 1;
  min-width: 210px;
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
}

.head__pinyin {
  font-size: 1.8rem;
  font-weight: 800;
  color: var(--brand-strong);
  line-height: 1.15;
}

.head__meaning {
  color: var(--text);
  line-height: 1.55;
}

.head__cta {
  margin-top: 2px;
}

.head__nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--gap-sm);
  padding-top: var(--gap-sm);
  border-top: 2px dashed var(--stroke-hint);
}

.head__navbtn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 44px;
  padding: 0 16px;
  border-radius: var(--radius-pill);
  background: var(--surface-sunken);
  font-weight: 700;
  color: var(--text-strong);
  transition: transform var(--dur-fast) var(--ease-pop);
}

.head__navbtn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.head__navbtn:not(:disabled):active {
  transform: scale(0.95);
}

.head__pos {
  color: var(--text-soft);
  font-size: 0.85rem;
  font-weight: 700;
  white-space: nowrap;
}

/* ------------------------------------------------------------------ tabs */

.tabs {
  display: flex;
  gap: 4px;
  padding: 5px;
  background: var(--surface);
  border: 1px solid var(--surface-border);
  border-radius: var(--radius-pill);
  box-shadow: var(--shadow-sm);
}

.tabs__btn {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 50px;
  border-radius: var(--radius-pill);
  font-weight: 800;
  color: var(--text-soft);
  transition: background var(--dur-fast) ease, color var(--dur-fast) ease,
    transform var(--dur-fast) var(--ease-pop);
}

.tabs__btn.is-active {
  background: linear-gradient(180deg, var(--brand) 0%, var(--brand-strong) 100%);
  color: var(--text-invert);
  box-shadow: var(--shadow-sm);
}

.tabs__btn:active {
  transform: scale(0.97);
}

/* ------------------------------------------------------------------ 组词 */

.words {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: var(--gap-sm);
}

.word {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 30px 10px 14px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  border: 2px solid transparent;
  transition: border-color var(--dur-fast) ease, transform var(--dur-fast) var(--ease-pop);
}

.word:hover {
  border-color: var(--brand);
}

.word:active {
  transform: scale(0.97);
}

.word__play {
  position: absolute;
  right: 9px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 0.9rem;
  opacity: 0.55;
}

.radical-hint {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
}

.radical-hint__glyph {
  display: grid;
  place-items: center;
  flex: none;
  width: 64px;
  height: 64px;
  border-radius: var(--radius-md);
  background: var(--accent-soft);
  font-size: 2.2rem;
  font-weight: 700;
  color: var(--text-strong);
}

.radical-hint strong {
  color: var(--text-strong);
}

/* ----------------------------------------------------------------- 写字 */

.writer-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--gap-md);
}

.writer-card__tools {
  justify-content: center;
}

.speeds {
  justify-content: center;
}

.speeds__btn {
  min-width: 48px;
  min-height: 40px;
  padding: 0 14px;
  border-radius: var(--radius-pill);
  background: var(--surface-sunken);
  font-weight: 700;
  color: var(--text-soft);
}

.speeds__btn.is-active {
  background: var(--accent-soft);
  color: var(--text-strong);
  box-shadow: inset 0 0 0 2px var(--accent);
}

.tips {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: var(--text);
}

.tips li {
  position: relative;
  padding-left: 22px;
}

.tips li::before {
  content: '✔';
  position: absolute;
  left: 0;
  color: var(--success);
  font-weight: 800;
}

/* 描红进度小圆点 */
.trace__meter {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 5px;
  margin-top: 4px;
}

.trace__pip {
  width: 11px;
  height: 11px;
  border-radius: 50%;
  background: var(--stroke-hint);
  transition: background var(--dur-fast) ease, transform var(--dur-fast) var(--ease-pop);
}

.trace__pip.is-done {
  background: var(--accent);
  transform: scale(1.2);
}

.trace__count {
  font-size: 0.85rem;
  text-align: center;
}

.result {
  display: flex;
  align-items: center;
  gap: var(--gap-md);
  flex-wrap: wrap;
  border: 3px solid var(--success);
}

.result__emoji {
  font-size: 2.6rem;
  line-height: 1;
}

.result__title {
  color: var(--text-strong);
  font-size: 1.05rem;
}

.learn__mascot {
  display: flex;
  justify-content: center;
}

@media (max-width: 520px) {
  .head__glyph {
    width: 108px;
    height: 108px;
  }
  .head__char {
    font-size: 3.8rem;
  }
  .tabs__btn {
    font-size: 0.9rem;
    gap: 3px;
  }
}
</style>
