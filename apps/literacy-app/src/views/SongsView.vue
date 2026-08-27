<script setup>
/**
 * 儿歌小舞台。
 *
 * 和古诗长廊拆成「长廊 + 详情」两条路由不同，儿歌只有一条 `/songs/:id?`：
 * 每首歌四句，展开后一屏就放得下，多跳一次页面反而打断了「挑一首就唱」。
 * `:id` 只是为了能把某一首直接分享/收藏成链接。
 *
 * 唱的时候没有音频文件可放，人声和伴奏是分开合成的：
 * 旋律走 `playMelody()`（振荡器实时合成），范读走系统朗读。所以这里给了两个
 * 按钮而不是一个「播放」——它们本来就是两件事，孩子可以只听调子跟着哼，
 * 也可以只听一句一句的字音。没装中文语音的机器上第二个按钮会自己说明情况。
 *
 * ROUND9_H1 —— 儿歌 v2 的歌词-旋律同步动画。v1 只有「唱到的那个字亮一下」，
 * 试下来有三个说不清的地方，v2 各补一件事：
 *
 *   1. 点下去就开唱，孩子永远慢半句 → 三拍预备拍，数完再出声；
 *   2. 亮过就灭，看不出唱到哪儿了   → 唱过的字留一层浅底，配一条整首的进度条；
 *   3. 高亮只有「亮」，看不出旋律    → 字按音高抬起来，旁边一条音高带同步走。
 *
 * 第 3 条是这一版的重点：`pitchOfNote()` 把音名换算成 0–1 的相对高度，
 * 交给 CSS 变量 `--pitch` 决定字抬多高、音高带上的点落在哪一格。家长关了音效
 * 时旋律不响，这条看得见的旋律线照样在走——听不见也能跟着唱。
 *
 * 「减少动态」开着（或系统 prefers-reduced-motion）时只留颜色和进度，
 * 不做位移和跳动：动画是锦上添花，唱到哪个字这件事不能只靠动画表达。
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import MascotCompanion from '@/components/MascotCompanion.vue'
import VoiceNotice from '@/components/VoiceNotice.vue'
import { useMascotCoach } from '@/composables/useMascotCoach.js'
import { SONGS, SONG_THEMES, getSong, pitchOfNote, syllablesOfSongLine } from '@/data/songs.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { cancelSpeech, playMelody, sfx, speak, stopAllTones } from '@/utils/audio.js'

const props = defineProps({ id: { type: String, default: '' } })

const router = useRouter()
const progress = useProgressStore()
const settings = useSettingsStore()

const { line: coachLine, mood: coachMood, next: coachNext } = useMascotCoach('songs')

/** 预备拍。三拍是试出来的：两拍来不及反应，四拍孩子已经走神了。 */
const COUNT_IN_BEATS = 3

const theme = ref('all')
const openId = ref(props.id && getSong(props.id) ? props.id : '')
/** 正在唱到第几句、第几个字；-1 表示没在唱。 */
const activeLine = ref(-1)
const activeChar = ref(-1)
const mode = ref('') // '' | 'sing' | 'read'
const status = ref('')
/** 预备拍还剩几下；0 表示已经开唱（或根本没在唱）。 */
const countIn = ref(0)
/** 每唱一个字 +1。模板拿它当 `:key`，靠重建节点重放 CSS 动画，比手工加减类稳。 */
const beat = ref(0)
/** 进度条：已经唱了多少毫秒 / 这一首（含预备拍）一共多少毫秒。 */
const played = ref(0)
const totalMs = ref(0)

/** 所有待清理的定时器。换歌、离开页面、点「停一停」都要一次全清掉。 */
let timers = []
let raf = 0
let startedAt = 0

function clearTimers() {
  timers.forEach((t) => clearTimeout(t))
  timers = []
  if (raf) cancelAnimationFrame(raf)
  raf = 0
}

function later(fn, ms) {
  timers.push(setTimeout(fn, ms))
}

/** 家长中心的「减少动态」和系统的 prefers-reduced-motion，任意一个开着就不动。 */
const reduced = computed(
  () =>
    settings.reduceMotion ||
    (typeof window !== 'undefined' &&
      !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches)
)

const list = computed(() =>
  SONGS.map((s) => {
    const record = progress.state.songs?.[s.id]
    return { ...s, sung: Boolean(record?.sung), times: record?.times ?? 0 }
  })
)

const shown = computed(() =>
  theme.value === 'all' ? list.value : list.value.filter((s) => s.theme === theme.value)
)

const tabs = computed(() => [
  { id: 'all', name: '全部', emoji: '🎵', count: list.value.length },
  ...SONG_THEMES.map((t) => ({
    ...t,
    count: list.value.filter((s) => s.theme === t.id).length
  }))
])

const open = computed(() => (openId.value ? getSong(openId.value) : null))

/**
 * 展开的那首歌逐句逐字摊平，模板直接渲染，不在模板里算。
 * 每个字顺带带上音高（0–1），CSS 靠它决定这个字唱到时抬多高。
 */
const sheet = computed(() =>
  open.value
    ? open.value.lines.map((line, index) => ({
        index,
        cells: syllablesOfSongLine(line).map((cell) => ({
          ...cell,
          pitch: cell.punct ? 0 : pitchOfNote(cell.note)
        }))
      }))
    : []
)

/**
 * 当前这一句的音高带：一句歌词有几个字就有几个点，点的高低就是这个字的音高。
 * 没在唱的时候先显示第一句，孩子点开就知道这首歌是往上走还是往下走。
 */
const ribbon = computed(() => {
  const song = open.value
  if (!song) return []
  const line = song.lines[activeLine.value >= 0 ? activeLine.value : 0]
  if (!line) return []
  return line.notes.map((note) => ({ note, pitch: pitchOfNote(note) }))
})

/**
 * 唱到整首歌的百分之几。
 * 唱的时候按真实时间走（进度条得跟着旋律，不是跟着句数一格一格跳）；
 * 跟我读没有时间表——系统朗读多久说完谁也不知道——就退回按句计。
 */
const progressPct = computed(() => {
  const total = open.value?.lines.length ?? 0
  if (mode.value === 'read') return total ? Math.round(((activeLine.value + 1) / total) * 100) : 0
  if (!totalMs.value) return 0
  return Math.min(100, Math.round((played.value / totalMs.value) * 100))
})

/** 唱到第几句，给模板显示「第 2 / 4 句」。没在唱时是 0。 */
const atLine = computed(() => (activeLine.value >= 0 ? activeLine.value + 1 : 0))

/** 先推还没唱过的第一首，全唱过了就推第一首再来一遍。 */
const suggestion = computed(() => list.value.find((s) => !s.sung) ?? list.value[0] ?? null)

function stop({ quiet = false } = {}) {
  clearTimers()
  cancelSpeech()
  // 整首歌的音符是一次排进时间轴的，清定时器只停得住高亮，停不住声音。
  stopAllTones()
  mode.value = ''
  activeLine.value = -1
  activeChar.value = -1
  countIn.value = 0
  played.value = 0
  totalMs.value = 0
  if (!quiet) status.value = '停下来了，想唱了再点一次。'
}

function pick(id) {
  sfx.tap()
  stop({ quiet: true })
  openId.value = openId.value === id ? '' : id
  status.value = ''
  const target = openId.value ? `/songs/${openId.value}` : '/songs'
  if (router.currentRoute.value.path !== target) router.replace(target)
}

function pickTheme(id) {
  sfx.tap()
  theme.value = id
}

/** 进度条每帧推一次。rAF 而不是定时器：进度条要跟着屏幕刷新走才不抖。 */
function tickProgress() {
  if (mode.value !== 'sing' || !totalMs.value) return
  played.value = Math.min(totalMs.value, performance.now() - startedAt)
  if (played.value < totalMs.value) raf = requestAnimationFrame(tickProgress)
}

/**
 * 唱一遍：先数三拍预备，再逐句放旋律，跟着音符逐字高亮。
 *
 * 高亮不是靠给每个音挂回调，而是拿 `playMelody()` 返回的时间表排定时器——
 * 家长把音效关掉时旋律不响，时间表照样准，字还是会一个一个亮过去。
 *
 * 预备拍是 v2 加的：v1 点完按钮立刻出声，孩子反应过来时第一句已经过去了。
 * 现在这三拍只敲拍子不出旋律，数完再开唱，跟合唱团起拍是一个道理。
 */
function sing() {
  const song = open.value
  if (!song) return
  stop({ quiet: true })
  mode.value = 'sing'

  const beatMs = Math.round(60000 / song.bpm)
  const lead = COUNT_IN_BEATS * beatMs
  countIn.value = COUNT_IN_BEATS
  status.value = `预备…数完 ${COUNT_IN_BEATS} 拍，《${song.title}》就开始。`
  for (let i = 0; i < COUNT_IN_BEATS; i += 1) {
    later(() => {
      countIn.value = COUNT_IN_BEATS - i
      beat.value += 1
      sfx.tap()
    }, i * beatMs)
  }

  let at = lead
  song.lines.forEach((line, lineIndex) => {
    const lineStart = at
    const { offsets, duration } = playMelody(line.notes, { bpm: song.bpm, startAt: lineStart })
    later(() => {
      countIn.value = 0
      activeLine.value = lineIndex
      activeChar.value = 0
      if (lineIndex === 0) status.value = `开始唱《${song.title}》，看着亮起来的字跟着哼。`
    }, lineStart)
    offsets.forEach((offset, charIndex) => {
      later(() => {
        activeChar.value = charIndex
        beat.value += 1
      }, lineStart + offset)
    })
    // 句与句之间留半拍，孩子才来得及换气。
    at += duration + Math.round(beatMs / 2)
  })

  totalMs.value = at
  played.value = 0
  startedAt = performance.now()
  raf = requestAnimationFrame(tickProgress)

  later(() => {
    played.value = totalMs.value
    activeLine.value = -1
    activeChar.value = -1
    countIn.value = 0
    mode.value = ''
    const record = progress.markSongSung(song.id)
    status.value =
      record.times > 1
        ? `《${song.title}》又唱了一遍，一共唱过 ${record.times} 次。`
        : `《${song.title}》唱完啦，得到 2 颗星星。`
    sfx.celebrate()
  }, at)
}

/** 跟我读：一句一句念歌词，念完一句再念下一句。 */
function readAloud() {
  const song = open.value
  if (!song) return
  stop({ quiet: true })
  mode.value = 'read'
  status.value = `一句一句读《${song.title}》，你跟着读。`

  const next = (index) => {
    if (mode.value !== 'read') return
    if (index >= song.lines.length) {
      mode.value = ''
      activeLine.value = -1
      status.value = `《${song.title}》读完了，会唱了吗？`
      return
    }
    activeLine.value = index
    activeChar.value = -1
    speak(song.lines[index].text, { rate: settings.speechRate }).then((ok) => {
      if (mode.value !== 'read') return
      // 没有中文嗓音时 speak() 立刻返回 false，这里补一段停顿，
      // 否则四句会在一瞬间闪完，孩子只看见最后一句亮着。
      later(() => next(index + 1), ok ? 260 : 1200)
    })
  }
  next(0)
}

watch(
  () => props.id,
  (value) => {
    if (value && getSong(value)) openId.value = value
    else if (!value) openId.value = ''
  }
)

onBeforeUnmount(() => stop({ quiet: true }))
</script>

<template>
  <div class="page">
    <section class="card card--flat intro">
      <div class="intro__text">
        <h2 class="section-title">
          <span class="section-title__emoji" aria-hidden="true">🎵</span>
          儿歌小舞台
        </h2>
        <p class="muted">
          {{ SONGS.length }} 首为这套字表新写的儿歌，歌词里的字都是学过的。
          调子和字音是当场合成的，不用联网也能唱；唱到哪个字哪个字亮，
          音越高字抬得越高。
        </p>
        <button
          v-if="suggestion"
          type="button"
          class="btn btn--primary intro__cta"
          @click="pick(suggestion.id)"
        >
          {{ suggestion.sung ? '再唱一遍' : '开始唱' }}《{{ suggestion.title }}》 →
        </button>
      </div>
      <span class="pill">唱过 {{ progress.songsSung }} / {{ SONGS.length }}</span>
    </section>

    <VoiceNotice fallback="没有朗读声也能唱：调子是现场合成的，照样响。" compact />

    <div class="tabs" role="group" aria-label="按主题挑儿歌">
      <button
        v-for="t in tabs"
        :key="t.id"
        type="button"
        class="tabs__btn"
        :class="{ 'is-on': theme === t.id }"
        :aria-pressed="theme === t.id"
        @click="pickTheme(t.id)"
      >
        <span aria-hidden="true">{{ t.emoji }}</span>
        {{ t.name }}
        <small>{{ t.count }}</small>
      </button>
    </div>

    <section class="shelf">
      <article
        v-for="s in shown"
        :key="s.id"
        class="song"
        :class="{ 'is-open': openId === s.id }"
        :style="{ '--c1': s.palette[0], '--c2': s.palette[1] }"
      >
        <button
          type="button"
          class="song__head"
          :aria-expanded="openId === s.id"
          @click="pick(s.id)"
        >
          <span class="song__emoji" aria-hidden="true">{{ s.emoji }}</span>
          <span class="song__meta">
            <strong class="song__title">{{ s.title }}</strong>
            <small class="song__pinyin">{{ s.titlePinyin }}</small>
            <small class="song__summary">{{ s.summary }}</small>
          </span>
          <span v-if="s.sung" class="song__badge" title="唱过了">✓ {{ s.times }}</span>
        </button>

        <div
          v-if="openId === s.id"
          class="player"
          :class="{ 'player--quiet': reduced, 'player--live': mode === 'sing' }"
          data-song-sync="v2"
        >
          <p class="player__tip">💡 {{ s.tip }}</p>

          <div class="track">
            <div
              class="track__bar"
              role="progressbar"
              :data-progress="progressPct"
              :aria-valuenow="progressPct"
              aria-valuemin="0"
              aria-valuemax="100"
              :aria-label="`《${s.title}》唱到哪儿了`"
            >
              <span class="track__fill" :style="{ width: `${progressPct}%` }" />
            </div>
            <small class="track__at">
              <span v-if="countIn" class="track__countin" aria-hidden="true">
                预备 {{ countIn }}
              </span>
              <span v-else-if="atLine">第 {{ atLine }} / {{ s.lines.length }} 句</span>
              <span v-else>{{ s.lines.length }} 句 · {{ s.bpm }} 拍</span>
            </small>
          </div>

          <!-- 音高带：一句歌词的旋律走向摊成一排点，唱到哪个字哪个点亮。 -->
          <div class="ribbon" aria-hidden="true">
            <span
              v-for="(dot, i) in ribbon"
              :key="i"
              class="ribbon__dot"
              :class="{
                'is-on': mode === 'sing' && activeChar === i,
                'is-done': mode === 'sing' && activeChar > i
              }"
              :style="{ '--pitch': dot.pitch }"
            />
            <span v-if="mode === 'sing' && !countIn" :key="beat" class="ribbon__beat">♪</span>
          </div>

          <ol class="lyrics">
            <li
              v-for="row in sheet"
              :key="row.index"
              class="lyrics__line"
              :class="{
                'is-on': activeLine === row.index,
                'is-done': activeLine > row.index
              }"
            >
              <span
                v-for="(cell, i) in row.cells"
                :key="i"
                class="cell"
                :class="{
                  'cell--punct': cell.punct,
                  'is-on': activeLine === row.index && !cell.punct && activeChar === cell.at,
                  'is-sung':
                    !cell.punct &&
                    (activeLine > row.index ||
                      (activeLine === row.index && activeChar > cell.at))
                }"
                :style="{ '--pitch': cell.pitch }"
              >
                <small v-if="settings.showPinyin && !cell.punct" class="cell__pinyin">
                  {{ cell.pinyin }}
                </small>
                <span class="cell__char">{{ cell.char }}</span>
              </span>
            </li>
          </ol>

          <div class="player__controls">
            <button
              type="button"
              class="btn btn--primary"
              :disabled="mode === 'sing'"
              @click="sing()"
            >
              🎼 {{ mode === 'sing' ? '正在唱…' : '唱一唱' }}
            </button>
            <button type="button" class="btn" :disabled="mode === 'read'" @click="readAloud()">
              🗣️ {{ mode === 'read' ? '正在读…' : '跟我读' }}
            </button>
            <button type="button" class="btn" :disabled="!mode" @click="stop()">⏹️ 停一停</button>
          </div>

          <p class="player__status" role="status" aria-live="polite">
            {{ status || `《${s.title}》一共 ${s.lines.length} 句，点「唱一唱」就开始。` }}
          </p>
        </div>
      </article>
    </section>

    <MascotCompanion
      class="mascot-dock"
      :mood="coachMood"
      :say="coachLine"
      :size="72"
      :speak-on-tap="false"
      tap-hint="点我，换一句悄悄话"
      @tap="coachNext"
    />
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
  gap: 8px;
  min-width: 0;
}

.intro__text .muted {
  font-size: 0.88rem;
}

.intro__cta {
  align-self: flex-start;
  margin-top: 4px;
}

.tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tabs__btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  min-height: 44px;
  padding: 0 14px;
  border-radius: var(--radius-pill);
  border: 1px solid var(--surface-border);
  background: var(--surface);
  font-weight: 800;
  font-size: 0.85rem;
  color: var(--text-soft);
}

.tabs__btn.is-on {
  background: var(--brand-soft);
  color: var(--text-strong);
}

.tabs__btn small {
  opacity: 0.7;
}

.shelf {
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
}

.song {
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, var(--c1) 0%, var(--c2) 100%);
  box-shadow: var(--shadow-md);
  overflow: hidden;
}

.song__head {
  position: relative;
  display: flex;
  align-items: center;
  gap: var(--gap-md);
  width: 100%;
  min-height: 72px;
  padding: var(--gap-md);
  text-align: left;
  color: var(--text-strong);
  background: transparent;
}

.song__emoji {
  font-size: 2.1rem;
  line-height: 1;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.12));
}

.song__meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.song__title {
  font-size: 1.15rem;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.song__pinyin,
.song__summary {
  font-size: 0.75rem;
  color: rgba(61, 47, 31, 0.78);
}

.song__badge {
  margin-left: auto;
  padding: 3px 10px;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.82);
  font-size: 0.78rem;
  font-weight: 800;
}

.player {
  padding: 0 var(--gap-md) var(--gap-md);
  display: flex;
  flex-direction: column;
  gap: var(--gap-sm);
}

.player__tip {
  margin: 0;
  font-size: 0.82rem;
  color: rgba(61, 47, 31, 0.85);
}

/* ---------------------------------------- ROUND9_H1 歌词-旋律同步（儿歌 v2） */
.track {
  display: flex;
  align-items: center;
  gap: 10px;
}

.track__bar {
  flex: 1;
  height: 8px;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.66);
  overflow: hidden;
}

.track__fill {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--mango-400) 0%, var(--brand) 100%);
  /* 120ms 线性：比一帧长，抹掉 rAF 的抖动；比一拍短，不会看起来在追旋律。 */
  transition: width 120ms linear;
}

.track__at {
  min-width: 6.4em;
  text-align: right;
  font-size: 0.74rem;
  font-weight: 800;
  color: rgba(61, 47, 31, 0.8);
  font-variant-numeric: tabular-nums;
}

.track__countin {
  color: var(--brand-strong);
}

/*
 * 音高带。点的高低就是这个字的音高：`--pitch` 0 是最低音、1 是最高音，
 * 换算成 22px 的落差——够看出高低，又不至于把歌词挤下去。
 */
.ribbon {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  height: 32px;
  padding: 0 var(--gap-md);
}

.ribbon__dot {
  --pitch: 0.5;
  width: 9px;
  height: 9px;
  flex: none;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.86);
  box-shadow: inset 0 0 0 1px rgba(61, 47, 31, 0.16);
  transform: translateY(calc((1 - var(--pitch)) * 22px));
  transition:
    background var(--dur-fast) ease,
    transform var(--dur-fast) var(--ease-pop);
}

.ribbon__dot.is-done {
  background: var(--brand-soft);
}

.ribbon__dot.is-on {
  background: var(--mango-400);
  transform: translateY(calc((1 - var(--pitch)) * 22px)) scale(1.6);
}

.ribbon__beat {
  margin-left: auto;
  font-size: 1.05rem;
  line-height: 1;
  color: var(--brand-strong);
  animation: song-beat 320ms var(--ease-pop) both;
}

@keyframes song-beat {
  0% {
    transform: scale(0.55) translateY(3px);
    opacity: 0.35;
  }
  45% {
    transform: scale(1.3) translateY(-3px);
    opacity: 1;
  }
  100% {
    transform: scale(1) translateY(0);
    opacity: 0.72;
  }
}

.lyrics {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 0;
  padding: var(--gap-md);
  list-style: none;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.72);
}

.lyrics__line {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  padding: 4px 6px;
  border-radius: var(--radius-sm);
  transition: background var(--dur-fast) ease;
}

.lyrics__line.is-on {
  background: var(--brand-soft);
}

/* 唱过的句子留一点痕迹：孩子抬头一看就知道还剩几句。 */
.lyrics__line.is-done {
  opacity: 0.72;
}

.cell {
  --pitch: 0.5;
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  min-width: 1.5em;
  border-radius: var(--radius-sm);
  transition: transform var(--dur-fast) var(--ease-pop), background var(--dur-fast) ease;
}

.cell--punct {
  min-width: 0.6em;
}

/* 这一句里已经唱过去的字：浅浅一层底，和「正在唱」的橙色区分得开。 */
.cell.is-sung {
  background: rgba(255, 255, 255, 0.82);
}

/*
 * 正在唱的那个字。抬起的高度跟着音高走（`--pitch` 0–1 换算成 2–12px），
 * 一句唱下来，字的起伏就是这句的旋律线——听不见也看得见。
 */
.cell.is-on {
  background: var(--mango-400);
  transform: translateY(calc(-2px - var(--pitch) * 10px)) scale(1.12);
}

.cell__pinyin {
  font-size: 0.62rem;
  line-height: 1.3;
  color: rgba(61, 47, 31, 0.7);
}

.cell__char {
  font-size: 1.35rem;
  font-weight: 700;
  line-height: 1.4;
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

.player__controls {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.player__status {
  margin: 0;
  min-height: 1.4em;
  font-size: 0.82rem;
  color: rgba(61, 47, 31, 0.85);
}

/*
 * 「减少动态」：位移和跳动全停，颜色、进度条、音高带的高低全留着。
 * 动画是锦上添花——唱到哪个字这件事不能只靠动画说清楚。
 */
.player--quiet .cell.is-on {
  transform: none;
}

.player--quiet .ribbon__dot,
.player--quiet .ribbon__dot.is-on {
  transform: translateY(calc((1 - var(--pitch)) * 22px));
}

.player--quiet .ribbon__beat {
  animation: none;
  opacity: 0.7;
}

.player--quiet .track__fill {
  transition: none;
}

@media (prefers-reduced-motion: reduce) {
  .cell.is-on {
    transform: none;
  }
  .ribbon__dot,
  .ribbon__dot.is-on {
    transform: translateY(calc((1 - var(--pitch)) * 22px));
  }
  .ribbon__beat {
    animation: none;
  }
  .track__fill {
    transition: none;
  }
}

@media (max-width: 560px) {
  .intro {
    flex-direction: column;
    align-items: stretch;
  }
  .intro .pill {
    align-self: flex-start;
  }
  .intro__cta {
    align-self: stretch;
  }
}
</style>
