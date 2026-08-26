<script setup>
/**
 * 首页「识字乐园地图」。
 *
 * 信息优先级：今天还差几个字 → 继续上次的进度 → 四个单元 → 其它玩法 → 复习。
 * 单元卡按顺序解锁：前一单元学到一半才开下一个，避免孩子一上来就跳到最难的。
 */
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { gsap } from 'gsap'

import { CHARACTERS, UNITS, charsOfUnit } from '@/data/characters.js'
import { BOOKS } from '@/data/books.js'
import { IDIOMS } from '@/data/idioms.js'
import { RADICALS } from '@/data/radicals.js'

import MascotCompanion from '@/components/MascotCompanion.vue'
import ProgressRing from '@/components/ProgressRing.vue'
import { useProgressStore } from '@/stores/progress.js'
import { sfx } from '@/utils/audio.js'

const progress = useProgressStore()
const router = useRouter()

const page = ref(null)

/** 单元解锁规则：第一个永远开着，之后要求上一个单元学过一半。 */
const units = computed(() =>
  UNITS.map((u, i) => {
    const stat = progress.unitProgress(u.id)
    const prev = i === 0 ? null : progress.unitProgress(UNITS[i - 1].id)
    const unlocked = i === 0 || (prev && prev.ratio >= 0.5)
    return { ...u, ...stat, unlocked, chars: charsOfUnit(u.id) }
  })
)

const greeting = computed(() => {
  const h = new Date().getHours()
  const name = progress.state.childName
  if (progress.dailyGoalReached) return `${name}，今天的目标完成啦，好厉害！`
  if (h < 6) return `${name}，天还没亮呢，早点休息哦。`
  if (h < 11) return `早上好，${name}！今天想认识哪个字？`
  if (h < 14) return `${name}，中午好，我们来学两个字吧！`
  if (h < 18) return `下午好，${name}！继续昨天的故事怎么样？`
  return `晚上好，${name}，读一本绘本再睡吧。`
})

const mascotMood = computed(() => {
  if (progress.dailyGoalReached) return 'cheer'
  if (progress.todayNewChars > 0) return 'happy'
  return 'idle'
})

const goalRatio = computed(() => {
  const goal = Math.max(1, progress.state.settings.dailyGoal)
  return Math.min(1, progress.todayNewChars / goal)
})

const activities = computed(() => [
  {
    to: '/listen',
    icon: '👂',
    title: '听音识字',
    desc: '听我读，你来找',
    tint: 'var(--seed-sky)',
    badge: progress.state.listen.bestStreak
      ? `最佳连对 ${progress.state.listen.bestStreak}`
      : '开始挑战'
  },
  {
    to: '/radicals',
    icon: '🧩',
    title: '偏旁部首',
    desc: '看懂字的小零件',
    tint: 'var(--seed-grape)',
    badge: `${progress.radicalsSeen} / ${RADICALS.length}`
  },
  {
    to: '/books',
    icon: '📚',
    title: '分级绘本',
    desc: '学过的字连成故事',
    tint: 'var(--seed-leaf)',
    badge: `${progress.booksFinished} / ${BOOKS.length} 本`
  },
  {
    to: '/idioms',
    icon: '🏮',
    title: '成语故事',
    desc: '四个字一个道理',
    tint: 'var(--seed-coral)',
    badge: `${progress.idiomsRead} / ${IDIOMS.length} 条`
  }
])

function go(path) {
  sfx.tap()
  router.push(path)
}

function continueLearning() {
  sfx.tap()
  router.push(`/learn/${encodeURIComponent(progress.nextChar.char)}`)
}

onMounted(() => {
  if (!page.value) return
  // 入场：卡片按顺序弹出，比整页淡入更有「翻开一本书」的感觉
  gsap.from(page.value.querySelectorAll('[data-anim]'), {
    y: 26,
    opacity: 0,
    duration: 0.5,
    stagger: 0.07,
    ease: 'back.out(1.4)',
    clearProps: 'all'
  })
})
</script>

<template>
  <div ref="page" class="page home">
    <!-- 今日概览 -->
    <section class="hero card" data-anim>
      <div class="hero__top">
        <MascotCompanion :mood="mascotMood" :say="greeting" :size="104" />
      </div>

      <div class="hero__stats">
        <ProgressRing
          :value="goalRatio"
          :size="86"
          :thickness="10"
          color="var(--brand)"
          :label="`${progress.todayNewChars}/${progress.state.settings.dailyGoal}`"
          sublabel="今日新字"
        />
        <div class="hero__numbers">
          <div class="hero__num">
            <strong>{{ progress.learnedCount }}</strong>
            <small>认识的字</small>
          </div>
          <div class="hero__num">
            <strong>{{ progress.masteredChars.length }}</strong>
            <small>已掌握</small>
          </div>
          <div class="hero__num">
            <strong>{{ progress.streakDays }}</strong>
            <small>连续天数</small>
          </div>
        </div>
      </div>

      <button class="btn btn--primary btn--lg btn--block" type="button" @click="continueLearning">
        <span aria-hidden="true">✏️</span>
        {{ progress.learnedCount === 0 ? '开始第一个字' : `继续学「${progress.nextChar.char}」` }}
      </button>
    </section>

    <!-- 单元地图 -->
    <section class="stack" data-anim>
      <h2 class="section-title">
        <span class="section-title__emoji">🗺️</span>
        识字地图
        <span class="pill">{{ progress.learnedCount }} / {{ CHARACTERS.length }} 字</span>
      </h2>

      <ul class="units">
        <li v-for="(u, i) in units" :key="u.id" class="units__row">
          <span class="units__line" :class="{ 'is-first': i === 0 }" aria-hidden="true"></span>

          <button
            class="unit"
            :class="{ 'is-locked': !u.unlocked, 'is-done': u.ratio === 1 }"
            type="button"
            :style="{ '--tint': u.color }"
            :disabled="!u.unlocked"
            @click="go(`/learn/${encodeURIComponent(u.chars[0].char)}`)"
          >
            <span class="unit__badge" aria-hidden="true">{{ u.unlocked ? u.emoji : '🔒' }}</span>

            <span class="unit__body">
              <strong class="unit__name">{{ u.name }}</strong>
              <small class="unit__desc">
                {{ u.unlocked ? u.desc : `先把「${units[i - 1].name}」学一半就解锁` }}
              </small>

              <span class="unit__bar" aria-hidden="true">
                <span class="unit__fill" :style="{ width: `${u.ratio * 100}%` }"></span>
              </span>

              <span class="unit__chars">
                <span
                  v-for="c in u.chars"
                  :key="c.char"
                  class="unit__char"
                  :data-level="progress.charStat(c.char).level"
                  >{{ c.char }}</span
                >
              </span>
            </span>

            <span class="unit__count">{{ u.learned }}/{{ u.total }}</span>
          </button>
        </li>
      </ul>
    </section>

    <!-- 其它玩法 -->
    <section class="stack" data-anim>
      <h2 class="section-title">
        <span class="section-title__emoji">🎠</span>
        再玩点别的
      </h2>

      <div class="acts">
        <button
          v-for="a in activities"
          :key="a.to"
          class="act"
          type="button"
          :style="{ '--tint': a.tint }"
          @click="go(a.to)"
        >
          <span class="act__icon" aria-hidden="true">{{ a.icon }}</span>
          <strong class="act__title">{{ a.title }}</strong>
          <small class="act__desc">{{ a.desc }}</small>
          <span class="act__badge">{{ a.badge }}</span>
        </button>
      </div>
    </section>

    <!-- 复习推荐 -->
    <section v-if="progress.reviewQueue.length" class="stack" data-anim>
      <h2 class="section-title">
        <span class="section-title__emoji">🔁</span>
        该复习啦
        <span class="pill pill--accent">{{ progress.reviewQueue.length }} 个字</span>
      </h2>
      <p class="muted">这些字学过但还没完全掌握，点一下再练一遍。</p>
      <div class="review">
        <button
          v-for="c in progress.reviewQueue"
          :key="c.char"
          class="review__chip"
          type="button"
          :data-level="progress.charStat(c.char).level"
          @click="go(`/learn/${encodeURIComponent(c.char)}`)"
        >
          <span class="review__char">{{ c.char }}</span>
          <small>{{ c.pinyin }}</small>
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.home {
  gap: var(--gap-xl);
}

/* ------------------------------------------------------------------ hero */

.hero {
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
}

.hero__top {
  display: flex;
  justify-content: center;
}

.hero__stats {
  display: flex;
  align-items: center;
  gap: var(--gap-lg);
  flex-wrap: wrap;
  justify-content: center;
}

.hero__numbers {
  display: flex;
  gap: var(--gap-lg);
  flex: 1;
  justify-content: space-around;
  min-width: 200px;
}

.hero__num {
  display: flex;
  flex-direction: column;
  align-items: center;
  line-height: 1.15;
}

.hero__num strong {
  font-size: 1.75rem;
  font-weight: 900;
  color: var(--brand-strong);
}

.hero__num small {
  color: var(--text-soft);
  font-size: 0.78rem;
}

/* ----------------------------------------------------------------- 单元 */

.units {
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
}

.units__row {
  position: relative;
  padding-left: 6px;
}

.units__line {
  position: absolute;
  left: 40px;
  top: -18px;
  height: 20px;
  width: 4px;
  border-radius: 2px;
  background: repeating-linear-gradient(
    to bottom,
    var(--stroke-hint) 0 6px,
    transparent 6px 11px
  );
}

.units__line.is-first {
  display: none;
}

.unit {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: var(--gap-md);
  width: 100%;
  padding: var(--gap-md);
  text-align: left;

  background: var(--surface);
  border: 2px solid var(--surface-border);
  border-left: 6px solid var(--tint);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  transition: transform var(--dur-fast) var(--ease-pop), box-shadow var(--dur-fast) ease;
}

.unit:not(:disabled):hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-md);
}

.unit:not(:disabled):active {
  transform: translateY(0) scale(0.99);
}

.unit.is-locked {
  opacity: 0.62;
  cursor: not-allowed;
  border-left-color: var(--stroke-hint);
}

.unit.is-done {
  background: linear-gradient(120deg, var(--brand-soft), var(--surface));
}

.unit__badge {
  display: grid;
  place-items: center;
  flex: none;
  width: 58px;
  height: 58px;
  border-radius: 50%;
  background: var(--surface-strong);
  box-shadow: var(--shadow-sm);
  font-size: 1.7rem;
}

.unit__body {
  display: flex;
  flex-direction: column;
  gap: 5px;
  flex: 1;
  min-width: 0;
}

.unit__name {
  font-size: 1.12rem;
  font-weight: 800;
  color: var(--text-strong);
}

.unit__desc {
  color: var(--text-soft);
  font-size: 0.82rem;
  line-height: 1.4;
}

.unit__bar {
  display: block;
  height: 8px;
  border-radius: 4px;
  background: var(--stroke-hint);
  overflow: hidden;
}

.unit__fill {
  display: block;
  height: 100%;
  border-radius: 4px;
  background: var(--tint);
  transition: width var(--dur-slow) var(--ease-pop);
}

.unit__chars {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 2px;
}

.unit__char {
  display: grid;
  place-items: center;
  width: 26px;
  height: 26px;
  border-radius: 7px;
  font-size: 0.92rem;
  font-weight: 700;
  background: var(--surface-sunken);
  color: var(--text-soft);
}

.unit__char[data-level='1'] {
  background: color-mix(in srgb, var(--seed-sky) 32%, transparent);
  color: var(--text-strong);
}
.unit__char[data-level='2'] {
  background: color-mix(in srgb, var(--seed-mint) 40%, transparent);
  color: var(--text-strong);
}
.unit__char[data-level='3'] {
  background: var(--seed-mango);
  color: #3d2f1f;
}

.unit__count {
  flex: none;
  align-self: center;
  font-weight: 900;
  color: var(--text-strong);
  font-size: 0.95rem;
}

/* --------------------------------------------------------------- 其它玩法 */

.acts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(158px, 1fr));
  gap: var(--gap-md);
}

.act {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: var(--gap-md);
  text-align: left;

  background: var(--surface);
  border: 2px solid var(--surface-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  transition: transform var(--dur-fast) var(--ease-pop), box-shadow var(--dur-fast) ease;
  overflow: hidden;
  position: relative;
}

.act::after {
  content: '';
  position: absolute;
  right: -28px;
  top: -28px;
  width: 84px;
  height: 84px;
  border-radius: 50%;
  background: var(--tint);
  opacity: 0.16;
}

.act:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-md);
}

.act:active {
  transform: translateY(0) scale(0.98);
}

.act__icon {
  font-size: 2rem;
  line-height: 1.2;
}

.act__title {
  font-size: 1.05rem;
  font-weight: 800;
  color: var(--text-strong);
}

.act__desc {
  color: var(--text-soft);
  font-size: 0.8rem;
}

.act__badge {
  margin-top: 8px;
  align-self: flex-start;
  padding: 3px 12px;
  border-radius: var(--radius-pill);
  background: var(--surface-sunken);
  font-size: 0.74rem;
  font-weight: 700;
  color: var(--text);
}

/* ----------------------------------------------------------------- 复习 */

.review {
  display: flex;
  flex-wrap: wrap;
  gap: var(--gap-sm);
}

.review__chip {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0;
  min-width: 62px;
  padding: 8px 10px;
  border-radius: var(--radius-md);
  background: var(--surface-strong);
  box-shadow: var(--shadow-sm);
  border-bottom: 4px solid var(--seed-sky);
  transition: transform var(--dur-fast) var(--ease-pop);
}

.review__chip[data-level='2'] {
  border-bottom-color: var(--seed-mint);
}

.review__chip:active {
  transform: translateY(2px);
}

.review__char {
  font-size: 1.6rem;
  font-weight: 800;
  color: var(--text-strong);
  line-height: 1.15;
}

.review__chip small {
  color: var(--text-soft);
  font-size: 0.7rem;
}

@media (max-width: 520px) {
  .hero__numbers {
    gap: var(--gap-md);
  }
  .hero__num strong {
    font-size: 1.45rem;
  }
}
</style>
