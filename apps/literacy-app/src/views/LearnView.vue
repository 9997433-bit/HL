<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import gsap from 'gsap'
import CharCard from '@/components/CharCard.vue'
import ProgressRing from '@/components/ProgressRing.vue'
import { CHARACTERS, UNITS, charsOfUnit } from '@/data/characters.js'
import { unitCheer, unitStory, unitTeaser } from '@/data/unit-stories.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { sfx } from '@/utils/sfx.js'

const progress = useProgressStore()
const settings = useSettingsStore()

const FILTERS = [
  { id: 'all', label: '全部', emoji: '📚' },
  { id: 'new', label: '没学过', emoji: '✨' },
  { id: 'learning', label: '学过了', emoji: '🌱' },
  { id: 'mastered', label: '已掌握', emoji: '🏆' },
  { id: 'review', label: '要复习', emoji: '🔁' }
]

const filter = ref('all')

const reviewSet = computed(() => new Set(progress.reviewQueue.map((c) => c.char)))

function matches(char) {
  switch (filter.value) {
    case 'new':
      return !progress.isLearned(char)
    case 'learning':
      return progress.isLearned(char) && !progress.isMastered(char)
    case 'mastered':
      return progress.isMastered(char)
    case 'review':
      return reviewSet.value.has(char)
    default:
      return true
  }
}

const groups = computed(() =>
  UNITS.map((unit) => {
    const all = charsOfUnit(unit.id)
    return {
      unit,
      chars: all.filter((c) => matches(c.char)),
      total: all.length,
      stat: progress.unitProgress(unit.id),
      unlocked: progress.unlockedUnits[unit.id]
    }
  })
)

const visibleCount = computed(() => groups.value.reduce((n, g) => n + g.chars.length, 0))

/**
 * 一次只挂一个单元。
 * 字表已经过百，一屏铺开既滚不到底也拖慢低端平板；按单元翻页正好和课程节奏一致，
 * 同时把同时存在的卡片数压在十张左右。
 */
const pages = computed(() => groups.value.filter((g) => g.chars.length))

const pageIndex = ref(0)

const currentPage = computed(() => pages.value[Math.min(pageIndex.value, pages.value.length - 1)])

watch([filter, pages], () => {
  if (pageIndex.value > pages.value.length - 1) pageIndex.value = Math.max(0, pages.value.length - 1)
})

function turnPage(delta) {
  const next = pageIndex.value + delta
  if (next < 0 || next > pages.value.length - 1) return
  sfx.tap()
  pageIndex.value = next
}

function pickFilter(id) {
  sfx.tap()
  filter.value = id
  pageIndex.value = 0
}

/* ---------------------------------------------------------------- 单元地图
 *
 * 翻页器一次只让孩子看见一个单元，走了几站、还剩几站全靠脑补。
 * 地图把 58 个单元摊成一条路：已解锁的亮着并显示学到几成，没解锁的灰着，
 * 点哪一站就翻到哪一站。每一站配一句剧情，锁着的那句话负责勾人。
 */

const mapUnits = computed(() =>
  UNITS.map((unit, i) => {
    const unlocked = Boolean(progress.unlockedUnits[unit.id])
    const stat = progress.unitProgress(unit.id)
    return {
      unit,
      index: i,
      unlocked,
      stat,
      done: stat.ratio >= 1,
      story: unlocked ? unitStory(unit) : unitTeaser(unit)
    }
  })
)

const currentUnitId = computed(() => currentPage.value?.unit.id ?? null)

const currentStop = computed(
  () => mapUnits.value.find((s) => s.unit.id === currentUnitId.value) ?? mapUnits.value[0]
)

const trackEl = ref(null)

/** 把当前这一站滚进视野，孩子翻页后不用自己去地图上找光标。 */
function focusStop() {
  const node = trackEl.value?.querySelector('[data-current="true"]')
  node?.scrollIntoView({
    behavior: reduced.value ? 'auto' : 'smooth',
    block: 'nearest',
    inline: 'center'
  })
}

/**
 * 跳到某一站。锁着的单元照样能翻过去看——里面的生字卡本来就是锁着的，
 * 把整站也挡在门外只会让孩子以为地图坏了。
 */
async function goToUnit(unitId) {
  sfx.tap()
  if (!pages.value.some((p) => p.unit.id === unitId)) {
    // 当前筛选下这一站没有字（比如只看「要复习」），先回到全部再跳
    filter.value = 'all'
    await nextTick()
  }
  const idx = pages.value.findIndex((p) => p.unit.id === unitId)
  if (idx >= 0) pageIndex.value = idx
  await nextTick()
  focusStop()
}

watch(currentUnitId, () => nextTick(focusStop))

/* ------------------------------------------------------------ 解锁过场 */

/** 家长中心的「减少动态」和系统的 prefers-reduced-motion，任意一个开着就不动。 */
const reduced = computed(
  () =>
    settings.reduceMotion ||
    (typeof window !== 'undefined' &&
      !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches)
)

/**
 * 新单元的门是在别处打开的：孩子在单字页写完最后一个字，上一单元刚好过 60%。
 * 等他回到字表，只会看到一把锁悄悄消失。这里把那一下补演出来——
 * 地图滚到新的一站，锁「啪」地弹开，剧情条落下来，由孩子自己按「进去看看」收场。
 */
const cheerUnit = ref(null)
const cheerRef = ref(null)
let cheerTl = null
let cheerCue = null

const cheerLine = computed(() => unitCheer(cheerUnit.value))

async function beginCheer() {
  const unit = progress.pendingUnitUnlock
  if (!unit || cheerUnit.value) return
  cheerUnit.value = unit
  await goToUnit(unit.id)
  await nextTick()
  playCheer()
}

function playCheer() {
  const banner = cheerRef.value
  if (!banner) return
  sfx.celebrate?.()
  if (reduced.value) return

  const node = trackEl.value?.querySelector(`[data-unit="${cheerUnit.value.id}"]`)
  cheerTl = gsap.timeline()
  cheerTl.fromTo(
    banner,
    { autoAlpha: 0, y: -14 },
    { autoAlpha: 1, y: 0, duration: 0.38, ease: 'power2.out' }
  )
  if (node) {
    cheerTl.fromTo(
      node,
      { filter: 'grayscale(1)', scale: 0.7 },
      {
        filter: 'grayscale(0)',
        scale: 1,
        duration: 0.6,
        ease: 'back.out(2.2)',
        overwrite: 'auto',
        clearProps: 'filter,transform'
      },
      '-=0.2'
    )
  }
  cheerTl.fromTo(
    banner.querySelectorAll('.cheer__row > *'),
    { autoAlpha: 0, y: 10 },
    { autoAlpha: 1, y: 0, duration: 0.3, stagger: 0.08, ease: 'power2.out' },
    '-=0.35'
  )
}

/** 收场：记账、清场，一次解锁了好几站就接着演下一站。 */
function closeCheer() {
  const unit = cheerUnit.value
  if (!unit) return
  sfx.tap()
  cheerTl?.kill()
  cheerTl = null
  progress.markUnitSeen(unit.id)
  cheerUnit.value = null
  nextTick(beginCheer)
}

watch(() => progress.pendingUnitUnlock?.id, () => beginCheer())

onMounted(() => {
  nextTick(focusStop)
  // 让页面先安静地铺开，过场再进来，免得和卡片入场挤在同一帧
  cheerCue = gsap.delayedCall(0.7, beginCheer)
})

onUnmounted(() => {
  cheerCue?.kill()
  cheerTl?.kill()
  cheerCue = null
  cheerTl = null
})

const randomChar = computed(() => {
  const unlocked = (c) => progress.unlockedUnits[c.unit]
  // 家长设了计划就先在计划单元里抽，抽不到再退回整份字表。
  const pool = progress.planChars.filter(unlocked)
  const fallback = CHARACTERS.filter(unlocked)
  const list = pool.length ? pool : fallback
  return list[Math.floor(Math.random() * list.length)] || CHARACTERS[0]
})

/** 家长面板里的学习计划，在这里只是一句提示，不拦着孩子往下翻。 */
const planNote = computed(() => {
  const parts = []
  if (!progress.isWholeCourse) {
    parts.push(`家长设了学习计划：这一阶段先学 ${progress.planUnitIds.length} 个单元、${progress.planProgress.total} 个字。`)
  }
  if (progress.dailyLimitReached) {
    parts.push(`今天的 ${progress.dailyNewLimit} 个新字已经学完啦，接着复习或者去读绘本吧。`)
  } else if (progress.newCharsLeft !== null) {
    parts.push(`今天还可以学 ${progress.newCharsLeft} 个新字。`)
  }
  return parts.join('')
})
</script>

<template>
  <div class="page">
    <section class="intro card card--flat">
      <div class="intro__text">
        <h2 class="section-title">
          <span class="section-title__emoji" aria-hidden="true">🈶</span>
          单字学习
        </h2>
        <p class="muted">
          共 {{ progress.totalChars }} 个常用字，分成 {{ UNITS.length }} 个单元。
          学完一个单元的 60%，下一个单元就会解锁。
        </p>
        <p v-if="planNote" class="muted intro__plan">📅 {{ planNote }}</p>
      </div>
      <ProgressRing
        :value="progress.overallProgress"
        :size="82"
        :thickness="9"
        sublabel="已认识"
      />
    </section>

    <div class="toolbar" role="group" aria-label="筛选汉字">
      <button
        v-for="f in FILTERS"
        :key="f.id"
        class="chip"
        :class="{ 'is-on': filter === f.id }"
        type="button"
        :aria-pressed="filter === f.id"
        @click="pickFilter(f.id)"
      >
        <span aria-hidden="true">{{ f.emoji }}</span> {{ f.label }}
      </button>
      <RouterLink
        class="chip chip--action"
        :to="`/learn/${encodeURIComponent(randomChar.char)}`"
        @click="sfx.tap()"
      >
        🎲 随机一个字
      </RouterLink>
    </div>

    <section
      v-if="cheerUnit"
      ref="cheerRef"
      class="cheer card"
      :style="{ '--uc': cheerUnit.color }"
      role="status"
      aria-live="polite"
    >
      <div class="cheer__row">
        <span class="cheer__emoji" aria-hidden="true">{{ cheerUnit.emoji }}</span>
        <div class="cheer__text">
          <strong class="cheer__title">新单元解锁</strong>
          <p class="cheer__line">{{ cheerLine }}</p>
        </div>
        <button class="btn btn--primary cheer__go" type="button" @click="closeCheer">
          进去看看
        </button>
      </div>
    </section>

    <section class="unitmap card card--flat" aria-labelledby="unitmap-title">
      <header class="unitmap__head">
        <h3 id="unitmap-title" class="unitmap__title">
          <span aria-hidden="true">🗺️</span> 单元地图
        </h3>
        <span class="pill unitmap__count">
          已开 {{ mapUnits.filter((s) => s.unlocked).length }} / {{ mapUnits.length }} 站
        </span>
      </header>
      <ol ref="trackEl" class="unitmap__track" role="list">
        <li v-for="stop in mapUnits" :key="stop.unit.id" class="unitmap__stop">
          <button
            class="stop"
            type="button"
            :class="{ 'is-locked': !stop.unlocked, 'is-current': stop.unit.id === currentUnitId }"
            :style="{ '--uc': stop.unit.color }"
            :data-unit="stop.unit.id"
            :data-current="stop.unit.id === currentUnitId"
            :aria-current="stop.unit.id === currentUnitId ? 'true' : undefined"
            :aria-label="`第 ${stop.index + 1} 站 ${stop.unit.name}${
              stop.unlocked ? `，已学 ${stop.stat.percent}%` : '，还没解锁'
            }。${stop.story}`"
            @click="goToUnit(stop.unit.id)"
          >
            <span class="stop__badge" aria-hidden="true">
              {{ stop.unlocked ? stop.unit.emoji : '🔒' }}
            </span>
            <span class="stop__name">{{ stop.unit.name }}</span>
            <span class="stop__bar" aria-hidden="true">
              <span class="stop__fill" :style="{ width: `${stop.stat.percent}%` }" />
            </span>
          </button>
        </li>
      </ol>
      <p v-if="currentStop" class="unitmap__story" :class="{ 'is-locked': !currentStop.unlocked }">
        <span aria-hidden="true">{{ currentStop.unlocked ? '📖' : '🔒' }}</span>
        {{ currentStop.story }}
      </p>
    </section>

    <p v-if="!visibleCount" class="empty card">
      <span class="empty__emoji" aria-hidden="true">🐣</span>
      这个分类下还没有字，换一个筛选看看吧！
    </p>

    <section v-if="currentPage" :key="currentPage.unit.id" class="unit stack">
      <header class="unit__head">
        <span class="unit__emoji" aria-hidden="true">
          {{ currentPage.unlocked ? currentPage.unit.emoji : '🔒' }}
        </span>
        <div class="unit__meta">
          <h3 class="unit__name">{{ currentPage.unit.name }}</h3>
          <p class="unit__desc muted">
            {{ currentPage.unlocked ? currentPage.unit.desc : '学完上一个单元的 60% 后解锁' }}
          </p>
        </div>
        <span class="unit__count pill">{{ currentPage.stat.done }} / {{ currentPage.total }}</span>
      </header>
      <div class="grid-auto grid-chars">
        <!--
          单元锁只拦「还没学过的字」。孩子从复习队列或搜索里学过的字如果
          因为所在单元没解锁而变成不可点，等于把到期要复习的字锁在门外。
        -->
        <CharCard
          v-for="c in currentPage.chars"
          :key="c.char"
          :item="c"
          :locked="!currentPage.unlocked && !progress.isLearned(c.char)"
        />
      </div>

      <nav class="pager" aria-label="按单元翻页">
        <button
          class="btn btn--ghost"
          type="button"
          :disabled="pageIndex === 0"
          @click="turnPage(-1)"
        >
          ← 上一页
        </button>
        <span class="pager__at">第 {{ pageIndex + 1 }} / {{ pages.length }} 单元</span>
        <button
          class="btn btn--ghost"
          type="button"
          :disabled="pageIndex >= pages.length - 1"
          @click="turnPage(1)"
        >
          下一页 →
        </button>
      </nav>
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

.intro__plan {
  font-weight: 700;
  color: var(--text-strong);
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip {
  min-height: 44px;
  padding: 0 16px;
  border-radius: var(--radius-pill);
  background: var(--surface);
  border: 2px solid var(--surface-border);
  color: var(--text);
  font-weight: 700;
  font-size: 0.9rem;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  box-shadow: var(--shadow-sm);
  transition: transform var(--dur-fast) var(--ease-pop), background var(--dur-fast) ease;
}

.chip:active {
  transform: scale(0.95);
}

.chip.is-on {
  background: linear-gradient(180deg, var(--brand) 0%, var(--brand-strong) 100%);
  color: var(--text-invert);
  border-color: transparent;
}

.chip--action {
  margin-left: auto;
  background: var(--accent-soft);
}

.grid-chars {
  grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
}

/* -------------------------------------------------------------- 单元地图 */

.unitmap {
  display: flex;
  flex-direction: column;
  gap: var(--gap-xs);
}

.unitmap__head {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
}

.unitmap__title {
  flex: 1;
  font-size: 0.95rem;
  font-weight: 800;
  color: var(--text-strong);
}

.unitmap__count {
  flex: none;
  font-size: 0.78rem;
}

.unitmap__track {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding: 4px 2px 10px;
  scroll-snap-type: x proximity;
  scrollbar-width: thin;
}

.unitmap__stop {
  flex: none;
  scroll-snap-align: center;
}

.stop {
  width: 96px;
  min-height: 92px;
  padding: 8px 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  border-radius: var(--radius-sm);
  border: 2px solid var(--surface-border);
  background: var(--surface);
  box-shadow: var(--shadow-sm);
  transition: transform var(--dur-fast) var(--ease-pop), border-color var(--dur-fast) ease;
}

.stop:active {
  transform: scale(0.95);
}

.stop__badge {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-pill);
  background: color-mix(in srgb, var(--uc) 26%, transparent);
  font-size: 1.15rem;
  line-height: 1;
}

.stop__name {
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--text-strong);
  text-align: center;
  line-height: 1.25;
}

.stop__bar {
  width: 100%;
  height: 5px;
  border-radius: var(--radius-pill);
  background: var(--surface-sunken);
  overflow: hidden;
}

.stop__fill {
  display: block;
  height: 100%;
  border-radius: var(--radius-pill);
  background: var(--uc);
  transition: width var(--dur-slow) var(--ease-smooth);
}

/* 没解锁的站点整块褪成灰调，一眼能看出这条路还没走到 */
.stop.is-locked {
  filter: grayscale(0.85);
  opacity: 0.62;
}

.stop.is-locked .stop__name {
  color: var(--text-soft);
}

.stop.is-current {
  border-color: var(--brand);
  box-shadow: var(--shadow-md);
}

.unitmap__story {
  font-size: 0.84rem;
  line-height: 1.55;
  color: var(--text-strong);
}

.unitmap__story.is-locked {
  color: var(--text-soft);
  font-style: italic;
}

/* ------------------------------------------------------------ 解锁过场 */

.cheer {
  border: 2px solid color-mix(in srgb, var(--uc) 60%, transparent);
  background: linear-gradient(140deg, color-mix(in srgb, var(--uc) 18%, transparent), var(--surface));
}

.cheer__row {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
}

.cheer__emoji {
  flex: none;
  width: 54px;
  height: 54px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-pill);
  background: color-mix(in srgb, var(--uc) 32%, transparent);
  font-size: 1.7rem;
}

.cheer__text {
  flex: 1;
  min-width: 0;
}

.cheer__title {
  display: block;
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 2px;
  color: var(--brand-strong);
}

.cheer__line {
  font-size: 0.92rem;
  line-height: 1.5;
  color: var(--text-strong);
}

.cheer__go {
  flex: none;
}

@media (max-width: 520px) {
  .cheer__row {
    flex-wrap: wrap;
  }

  .cheer__go {
    width: 100%;
  }
}

.unit__head {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
}

.unit__emoji {
  font-size: 1.7rem;
  line-height: 1;
}

.unit__meta {
  flex: 1;
  min-width: 0;
}

.unit__name {
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--text-strong);
}

.unit__desc {
  font-size: 0.8rem;
}

.unit__count {
  flex: none;
}

.pager {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--gap-sm);
}

.pager__at {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--text-soft);
}

.pager .btn[disabled] {
  opacity: 0.4;
}

.empty {
  display: flex;
  align-items: center;
  gap: var(--gap-sm);
  justify-content: center;
  color: var(--text-soft);
}

.empty__emoji {
  font-size: 1.6rem;
}
</style>
