<script setup>
/**
 * 小游戏大厅 —— 街机厅。
 *
 * 四台「机器」各练一种能力：听音辨形、空间寻字、字音配对、字形辨别。
 * 排成网格是为了让孩子一眼扫完再选，而不是从上往下读一列说明；
 * 每台机器只写一句话玩法，孩子自己读得完，家长也扫一眼就知道是练什么的。
 *
 * 霓虹边只是外观：颜色都走 --neon 这一个自定义属性，护眼主题下把辉光换成
 * 透明色（不是 none —— box-shadow 列表里不接受 none），只留边框。
 *
 * 所有小游戏都只出已学过的字，学的字越多，能玩的题目越多——
 * 招牌上那句话就是在讲这件事。
 */
import { computed } from 'vue'
import { useProgressStore } from '@/stores/progress.js'
import { sfx } from '@/utils/sfx.js'
import OpenMojiIcon from '@shared/components/OpenMojiIcon.vue'

const progress = useProgressStore()

/** 出题需要凑够的干扰项数量；不到就先去学字，机器出不了整题。 */
const MIN_CHARS = 4

const GAMES = [
  {
    to: '/listen',
    emoji: '🎧',
    slot: '01',
    name: '听音识字',
    trains: '听音辨形',
    howToPlay: '喇叭念一个字，你在四个字里点中它。',
    color: 'var(--mint-400)'
  },
  {
    to: '/games/maze',
    emoji: '🧭',
    slot: '02',
    name: '字迷宫',
    trains: '空间寻字',
    howToPlay: '按方向键走迷宫，踩到题目要找的那个字。',
    color: 'var(--sky-400)'
  },
  {
    to: '/games/memory',
    emoji: '🃏',
    slot: '03',
    name: '配对记忆',
    trains: '字音配对',
    howToPlay: '翻开两张牌，汉字和它的拼音对上就收走。',
    color: 'var(--grape-400)'
  },
  {
    to: '/games/spot',
    emoji: '🔍',
    slot: '04',
    name: '找不同',
    trains: '字形辨别',
    howToPlay: '一屏长得差不多的字里，点出唯一不一样的。',
    color: 'var(--mango-400)'
  }
]

const learned = computed(() => progress.learnedCount)
const ready = computed(() => learned.value >= MIN_CHARS)

const meters = computed(() => [
  { key: 'chars', label: '题库', value: `${learned.value} 字` },
  { key: 'stars', label: '星星', value: `${progress.stars}` },
  { key: 'streak', label: '最佳连对', value: `${progress.game.bestStreak}` }
])

const hostLine = computed(() =>
  ready.value
    ? `${learned.value} 个字都能出题，挑一台开玩吧！`
    : `再学 ${MIN_CHARS - learned.value} 个字，机器就有题出啦。`
)
</script>

<template>
  <div class="page arcade">
    <!-- 街机厅招牌 -->
    <section class="card card--strong arcade__sign">
      <span class="arcade__bulbs" aria-hidden="true"></span>
      <p class="arcade__eyebrow">识字街机厅</p>
      <h2 class="arcade__title">小游戏大厅</h2>
      <p class="arcade__desc">
        四台机器都只出<strong>你学过的字</strong>，现在能出题的有
        <strong>{{ learned }}</strong> 个字。多学几个字，街机厅就更热闹啦。
      </p>

      <ul class="arcade__meters">
        <li v-for="m in meters" :key="m.key" class="meter">
          <span class="meter__label">{{ m.label }}</span>
          <span class="meter__value">{{ m.value }}</span>
        </li>
      </ul>

      <p class="arcade__host">{{ hostLine }}</p>
    </section>

    <h3 class="arcade__pick">选一台机器</h3>

    <ul class="games-grid">
      <li v-for="g in GAMES" :key="g.to" class="games-grid__slot">
        <RouterLink
          class="machine card--tap"
          :to="g.to"
          :style="{ '--neon': g.color }"
          @click="sfx.tap()"
        >
          <span class="machine__top">
            <span class="machine__slot">{{ g.slot }} 号机</span>
            <span class="machine__tag">练{{ g.trains }}</span>
          </span>

          <span class="machine__screen">
            <OpenMojiIcon class="machine__icon" :emoji="g.emoji" :size="44" />
          </span>

          <strong class="machine__name">{{ g.name }}</strong>
          <span class="machine__how">{{ g.howToPlay }}</span>
          <span class="machine__cta">按我开玩 ▶</span>
        </RouterLink>
      </li>
    </ul>

    <p v-if="!ready" class="arcade__note card card--sunken">
      现在只认识 {{ learned }} 个字，机器还凑不齐一道题。先去
      <RouterLink class="arcade__link" to="/learn">学汉字</RouterLink>
      认几个字，再回来玩。
    </p>
  </div>
</template>

<style scoped>
.arcade {
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
}

/* ---------------------------------------------------------------- 招牌 */

.arcade__sign {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: var(--gap-xs);
  overflow: hidden;
  border: 2px solid color-mix(in srgb, var(--brand) 55%, transparent);
}

/* 走马灯灯带：只是装饰，减少动态时全局规则会把它按住 */
.arcade__bulbs {
  display: block;
  height: 8px;
  border-radius: var(--radius-pill);
  background: repeating-linear-gradient(
    90deg,
    var(--brand) 0 8px,
    color-mix(in srgb, var(--brand) 18%, transparent) 8px 22px
  );
  background-size: 44px 100%;
  animation: arcade-marquee 1.6s linear infinite;
}

@keyframes arcade-marquee {
  to {
    background-position: 44px 0;
  }
}

@media (prefers-reduced-motion: reduce) {
  .arcade__bulbs {
    animation: none;
  }
}

.arcade__eyebrow {
  font-size: var(--fs-sm);
  font-weight: var(--fw-heavy);
  letter-spacing: 0.24em;
  color: var(--text-soft);
}

.arcade__title {
  font-size: var(--fs-xl);
  font-weight: var(--fw-black);
  letter-spacing: 0.06em;
  color: var(--text-strong);
  text-shadow: 0 0 12px color-mix(in srgb, var(--brand) 45%, transparent);
}

.arcade__desc {
  line-height: var(--lh-loose);
  color: var(--text);
}

.arcade__meters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--gap-xs);
  list-style: none;
  padding: 0;
  margin: 0;
}

.meter {
  display: flex;
  align-items: baseline;
  gap: var(--gap-2xs);
  padding: 6px 12px;
  border-radius: var(--radius-pill);
  background: var(--surface-sunken);
  border: 1px solid color-mix(in srgb, var(--brand) 30%, transparent);
}

.meter__label {
  font-size: 0.74rem;
  font-weight: var(--fw-bold);
  color: var(--text);
}

.meter__value {
  font-family: var(--font-num);
  font-size: 0.95rem;
  font-weight: var(--fw-black);
  color: var(--text-strong);
}

.arcade__host {
  margin-top: var(--gap-2xs);
  padding: 8px 14px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  border-left: 4px solid var(--brand);
  font-weight: var(--fw-bold);
  line-height: var(--lh-base);
  color: var(--text-strong);
}

.arcade__pick {
  font-size: var(--fs-md);
  font-weight: var(--fw-heavy);
  color: var(--text-strong);
}

/* -------------------------------------------------------------- 机台网格 */

.games-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(148px, 1fr));
  gap: var(--gap-sm);
  list-style: none;
  padding: 0;
  margin: 0;
}

.games-grid__slot {
  display: flex;
}

.machine {
  --neon-glow: 0 0 18px color-mix(in srgb, var(--neon) 42%, transparent);

  display: flex;
  flex-direction: column;
  gap: var(--gap-2xs);
  width: 100%;
  min-height: var(--tap-min);
  padding: var(--gap-md);
  border: 2px solid color-mix(in srgb, var(--neon) 70%, transparent);
  border-radius: var(--radius-md);
  background: var(--surface);
  box-shadow:
    var(--shadow-md),
    var(--neon-glow),
    inset 0 0 14px color-mix(in srgb, var(--neon) 12%, transparent);
  color: var(--text);
}

/* card--tap 的 hover 会整条换掉 box-shadow，这里补回霓虹辉光 */
.machine:hover,
.machine:focus-visible {
  box-shadow:
    var(--shadow-lg),
    var(--neon-glow),
    inset 0 0 14px color-mix(in srgb, var(--neon) 18%, transparent);
}

/* 护眼主题禁辉光：box-shadow 列表里不能写 none，改成透明辉光 */
:root[data-theme='care'] .machine {
  --neon-glow: 0 0 0 transparent;
}

.machine__top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--gap-2xs);
}

.machine__slot {
  font-family: var(--font-num);
  font-size: 0.7rem;
  font-weight: var(--fw-heavy);
  letter-spacing: 0.08em;
  color: var(--text-soft);
}

.machine__tag {
  padding: 3px 8px;
  border-radius: var(--radius-pill);
  background: var(--surface-sunken);
  font-size: 0.68rem;
  font-weight: var(--fw-heavy);
  color: var(--text-strong);
}

/* 机台屏幕：霓虹底 + 扫描线，只放图标，不承载文字 */
.machine__screen {
  display: grid;
  place-items: center;
  height: 72px;
  margin: var(--gap-2xs) 0;
  border-radius: var(--radius-sm);
  border: 1px solid color-mix(in srgb, var(--neon) 45%, transparent);
  background:
    repeating-linear-gradient(
      180deg,
      color-mix(in srgb, var(--text-strong) 7%, transparent) 0 1px,
      transparent 1px 4px
    ),
    radial-gradient(72% 72% at 50% 32%, color-mix(in srgb, var(--neon) 30%, transparent), transparent 72%),
    var(--surface-sunken);
}

/* 没有对应 OpenMoji 素材时组件会退回 emoji 文本，字号要自己撑起来 */
.machine__icon {
  font-size: 40px;
  line-height: 1;
  filter: drop-shadow(0 2px 6px color-mix(in srgb, var(--neon) 55%, transparent));
}

.machine__name {
  font-size: 1.05rem;
  font-weight: var(--fw-heavy);
  color: var(--text-strong);
}

/* 一句话玩法：每台机器有且只有这一句，孩子自己读得完 */
.machine__how {
  font-size: 0.82rem;
  line-height: var(--lh-base);
  color: var(--text);
}

.machine__cta {
  margin-top: auto;
  padding-top: var(--gap-2xs);
  font-size: 0.8rem;
  font-weight: var(--fw-heavy);
  color: var(--text-strong);
}

.machine:hover .machine__cta {
  text-decoration: underline;
}

/* -------------------------------------------------------------- 出题门槛 */

.arcade__note {
  line-height: var(--lh-loose);
  color: var(--text);
}

.arcade__link {
  font-weight: var(--fw-heavy);
  color: var(--text-strong);
  text-decoration: underline;
}

@media (max-width: 360px) {
  .games-grid {
    grid-template-columns: 1fr;
  }
}
</style>
