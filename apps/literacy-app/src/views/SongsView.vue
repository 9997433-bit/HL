<script setup>
/**
 * 儿歌小舞台。
 *
 * 和古诗长廊拆成「长廊 + 详情」两条路由不同，儿歌只有一条 `/songs/:id?`：
 * 七首歌每首四句，展开后一屏就放得下，多跳一次页面反而打断了「挑一首就唱」。
 * `:id` 只是为了能把某一首直接分享/收藏成链接。
 *
 * 唱的时候没有音频文件可放，人声和伴奏是分开合成的：
 * 旋律走 `playMelody()`（振荡器实时合成），范读走系统朗读。所以这里给了两个
 * 按钮而不是一个「播放」——它们本来就是两件事，孩子可以只听调子跟着哼，
 * 也可以只听一句一句的字音。没装中文语音的机器上第二个按钮会自己说明情况。
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import MascotCompanion from '@/components/MascotCompanion.vue'
import VoiceNotice from '@/components/VoiceNotice.vue'
import { useMascotCoach } from '@/composables/useMascotCoach.js'
import { SONGS, SONG_THEMES, getSong, syllablesOfSongLine } from '@/data/songs.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { playMelody, sfx, speak, cancelSpeech } from '@/utils/audio.js'

const props = defineProps({ id: { type: String, default: '' } })

const router = useRouter()
const progress = useProgressStore()
const settings = useSettingsStore()

const { line: coachLine, mood: coachMood, next: coachNext } = useMascotCoach('songs')

const theme = ref('all')
const openId = ref(props.id && getSong(props.id) ? props.id : '')
/** 正在唱到第几句、第几个字；-1 表示没在唱。 */
const activeLine = ref(-1)
const activeChar = ref(-1)
const mode = ref('') // '' | 'sing' | 'read'
const status = ref('')

/** 所有待清理的定时器。换歌、离开页面、点「停一停」都要一次全清掉。 */
let timers = []

function clearTimers() {
  timers.forEach((t) => clearTimeout(t))
  timers = []
}

function later(fn, ms) {
  timers.push(setTimeout(fn, ms))
}

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

/** 展开的那首歌逐句逐字摊平，模板直接渲染，不在模板里算。 */
const sheet = computed(() =>
  open.value
    ? open.value.lines.map((line, index) => ({
        index,
        text: line.text,
        cells: syllablesOfSongLine(line)
      }))
    : []
)

/** 先推还没唱过的第一首，全唱过了就推第一首再来一遍。 */
const suggestion = computed(() => list.value.find((s) => !s.sung) ?? list.value[0] ?? null)

function stop({ quiet = false } = {}) {
  clearTimers()
  cancelSpeech()
  mode.value = ''
  activeLine.value = -1
  activeChar.value = -1
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

/**
 * 唱一遍：逐句放旋律，跟着音符逐字高亮。
 *
 * 高亮不是靠给每个音挂回调，而是拿 `playMelody()` 返回的时间表排定时器——
 * 家长把音效关掉时旋律不响，时间表照样准，字还是会一个一个亮过去。
 */
function sing() {
  const song = open.value
  if (!song) return
  stop({ quiet: true })
  mode.value = 'sing'
  status.value = `开始唱《${song.title}》，看着亮起来的字跟着哼。`

  let at = 0
  song.lines.forEach((line, lineIndex) => {
    const { offsets, duration } = playMelody(line.notes, { bpm: song.bpm })
    const lineStart = at
    later(() => {
      activeLine.value = lineIndex
      activeChar.value = 0
    }, lineStart)
    offsets.forEach((offset, charIndex) => {
      later(() => {
        activeChar.value = charIndex
      }, lineStart + offset)
    })
    // 句与句之间留半拍，孩子才来得及换气。
    at += duration + Math.round((60 / song.bpm) * 500)
  })

  later(() => {
    activeLine.value = -1
    activeChar.value = -1
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
          调子和字音是当场合成的，不用联网也能唱。
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

        <div v-if="openId === s.id" class="player">
          <p class="player__tip">💡 {{ s.tip }}</p>

          <ol class="lyrics">
            <li
              v-for="row in sheet"
              :key="row.index"
              class="lyrics__line"
              :class="{ 'is-on': activeLine === row.index }"
            >
              <span
                v-for="(cell, i) in row.cells"
                :key="i"
                class="cell"
                :class="{
                  'cell--punct': cell.punct,
                  'is-on': activeLine === row.index && !cell.punct && activeChar === cell.at
                }"
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

.cell {
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

.cell.is-on {
  background: var(--mango-400);
  transform: translateY(-2px) scale(1.12);
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
