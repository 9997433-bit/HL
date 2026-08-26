<script setup>
import { computed, onMounted, ref } from 'vue'
import gsap from 'gsap'
import ProgressRing from '@/components/ProgressRing.vue'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { BOOKS } from '@/data/books.js'
import { IDIOMS } from '@/data/idioms.js'
import { RADICALS } from '@/data/radicals.js'
import { sfx } from '@/utils/sfx.js'
import OpenMojiIcon from '@shared/components/OpenMojiIcon.vue'

const progress = useProgressStore()
const settings = useSettingsStore()

const mapRef = ref(null)

const nextChar = computed(() => progress.nextChar)

const stations = computed(() => [
  {
    to: '/learn',
    emoji: '🈶',
    title: '单字学习',
    desc: '看字形、听读音、写笔顺',
    color: 'var(--mango-400)',
    done: progress.learnedCount,
    total: progress.totalChars,
    unit: '字'
  },
  {
    to: '/game/listen',
    emoji: '🎧',
    title: '听音识字',
    desc: '听一听，选出正确的字',
    color: 'var(--mint-400)',
    done: progress.game.correct,
    total: null,
    unit: '次答对',
    locked: progress.learnedCount < 4,
    lockHint: '先学会 4 个字就能玩'
  },
  {
    to: '/radicals',
    emoji: '🧩',
    title: '偏旁部首',
    desc: '认识汉字的小零件',
    color: 'var(--sky-400)',
    done: progress.radicalsSeen,
    total: RADICALS.length,
    unit: '个'
  },
  {
    to: '/books',
    emoji: '📖',
    title: '分级绘本',
    desc: '只用学过的字，读完一整本',
    color: 'var(--leaf-400)',
    done: progress.booksFinished,
    total: BOOKS.length,
    unit: '本'
  },
  {
    to: '/idioms',
    emoji: '🎭',
    title: '成语启蒙',
    desc: '四格小剧场，看懂一个成语',
    color: 'var(--grape-400)',
    done: progress.idiomsSeen,
    total: IDIOMS.length,
    unit: '个'
  },
  {
    to: '/parent',
    emoji: '👨‍👩‍👧',
    title: '家长中心',
    desc: '学习报告与使用设置',
    color: 'var(--coral-400)',
    done: null,
    total: null
  }
])

onMounted(() => {
  if (settings.reduceMotion) return
  const nodes = mapRef.value?.querySelectorAll('.station')
  if (!nodes?.length) return
  gsap.from(nodes, {
    opacity: 0,
    y: 26,
    scale: 0.94,
    duration: 0.45,
    ease: 'back.out(1.6)',
    stagger: 0.07
  })
})
</script>

<template>
  <div class="page home">
    <!-- 顶部学习状态 -->
    <section class="hero card">
      <div class="hero__left">
        <p class="hero__eyebrow">今天的识字冒险</p>
        <h2 class="hero__title">
          已经认识
          <strong>{{ progress.learnedCount }}</strong>
          个字啦
        </h2>
        <div class="hero__chips">
          <span class="pill">🔥 连续 {{ progress.streakDays || 1 }} 天</span>
          <span class="pill pill--accent">🏆 掌握 {{ progress.masteredCount }} 字</span>
          <span v-if="progress.dueCount" class="pill">🔁 该复习 {{ progress.dueCount }} 字</span>
          <span class="pill">⏱️ 今天 {{ Math.round(progress.todayStats.seconds / 60) }} 分钟</span>
        </div>
        <RouterLink
          v-if="nextChar"
          class="btn btn--primary btn--lg hero__cta"
          :to="`/learn/${encodeURIComponent(nextChar.char)}`"
          @click="sfx.tap()"
        >
          继续学「{{ nextChar.char }}」 →
        </RouterLink>
      </div>
      <ProgressRing
        class="hero__ring"
        :value="progress.overallProgress"
        :size="106"
        :thickness="11"
        sublabel="总进度"
      />
    </section>

    <!-- 学习地图 -->
    <section class="stack">
      <h3 class="section-title">
        <OpenMojiIcon class="section-title__emoji" name="world-map" :size="22" />
        学习地图
      </h3>

      <div ref="mapRef" class="map">
        <span class="map__path" aria-hidden="true" />
        <RouterLink
          v-for="(s, i) in stations"
          :key="s.to"
          class="station"
          :class="[`station--${i % 2 === 0 ? 'left' : 'right'}`, { 'is-locked': s.locked }]"
          :to="s.locked ? '' : s.to"
          :style="{ '--station-color': s.color }"
          :aria-disabled="s.locked || undefined"
          @click="(e) => (s.locked ? e.preventDefault() : sfx.tap())"
        >
          <span class="station__dot" aria-hidden="true">
            <OpenMojiIcon class="station__emoji" :emoji="s.locked ? '🔒' : s.emoji" :size="34" />
            <span class="station__index">{{ i + 1 }}</span>
          </span>
          <span class="station__body">
            <strong class="station__title">{{ s.title }}</strong>
            <span class="station__desc">{{ s.locked ? s.lockHint : s.desc }}</span>
            <span v-if="s.done !== null" class="station__meter">
              <span v-if="s.total" class="station__bar">
                <span
                  class="station__fill"
                  :style="{ width: `${Math.min(100, Math.round((s.done / s.total) * 100))}%` }"
                />
              </span>
              <small>{{ s.done }}{{ s.total ? ` / ${s.total}` : '' }} {{ s.unit }}</small>
            </span>
          </span>
        </RouterLink>
      </div>
    </section>

    <p class="home__foot muted">
      开源项目 · 所有学习数据只保存在这台设备上 🌱
    </p>
  </div>
</template>

<style scoped>
.hero {
  display: flex;
  align-items: center;
  gap: var(--gap-lg);
}

.hero__left {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.hero__eyebrow {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--text-soft);
  letter-spacing: 0.08em;
}

.hero__title {
  font-size: clamp(1.3rem, 5vw, 1.75rem);
  font-weight: 800;
  color: var(--text-strong);
  line-height: 1.3;
}

.hero__title strong {
  color: var(--brand-strong);
  font-size: 1.35em;
}

.hero__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.hero__cta {
  align-self: flex-start;
  margin-top: 6px;
}

.hero__ring {
  flex: none;
}

/* ---------------- 地图 ---------------- */
.map {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 4px 0;
}

.map__path {
  position: absolute;
  top: 30px;
  bottom: 30px;
  left: 50%;
  width: 6px;
  transform: translateX(-50%);
  border-radius: 3px;
  background-image: linear-gradient(
    to bottom,
    color-mix(in srgb, var(--brand) 55%, transparent) 0 14px,
    transparent 14px 26px
  );
  background-size: 6px 26px;
  opacity: 0.7;
}

.station {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: var(--gap-md);
  width: min(100%, 520px);
  padding: 14px 18px 14px 12px;
  border-radius: var(--radius-lg);
  background: var(--surface);
  border: 2px solid var(--surface-border);
  box-shadow: var(--shadow-md);
  backdrop-filter: blur(6px);
  transition: transform var(--dur-fast) var(--ease-pop), box-shadow var(--dur-fast) ease;
}

.station--left {
  align-self: flex-start;
}

.station--right {
  align-self: flex-end;
  flex-direction: row-reverse;
  text-align: right;
  padding: 14px 12px 14px 18px;
}

.station:hover {
  transform: translateY(-3px);
  box-shadow: var(--shadow-lg);
}

.station:active {
  transform: scale(0.985);
}

.station.is-locked {
  opacity: 0.6;
  filter: grayscale(0.5);
  cursor: not-allowed;
}

.station.is-locked:hover {
  transform: none;
}

.station__dot {
  position: relative;
  flex: none;
  display: grid;
  place-items: center;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: color-mix(in srgb, var(--station-color) 32%, var(--surface-strong));
  border: 3px solid color-mix(in srgb, var(--station-color) 70%, white 10%);
  box-shadow: var(--shadow-sm);
}

.station__emoji {
  font-size: 1.85rem;
  line-height: 1;
}

.station__index {
  position: absolute;
  right: -5px;
  bottom: -4px;
  min-width: 22px;
  height: 22px;
  padding: 0 5px;
  display: grid;
  place-items: center;
  border-radius: var(--radius-pill);
  background: var(--surface-strong);
  color: var(--text-strong);
  font-size: 0.72rem;
  font-weight: 800;
  box-shadow: var(--shadow-sm);
}

.station__body {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.station__title {
  font-size: 1.1rem;
  font-weight: 800;
  color: var(--text-strong);
}

.station__desc {
  font-size: 0.85rem;
  color: var(--text-soft);
}

.station__meter {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.station--right .station__meter {
  flex-direction: row-reverse;
}

.station__bar {
  flex: 1;
  min-width: 70px;
  height: 8px;
  border-radius: 4px;
  background: var(--stroke-hint);
  overflow: hidden;
}

.station__fill {
  display: block;
  height: 100%;
  border-radius: 4px;
  background: var(--station-color);
  transition: width var(--dur-slow) var(--ease-pop);
}

.station__meter small {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--text-soft);
  white-space: nowrap;
}

.home__foot {
  text-align: center;
  font-size: 0.8rem;
}

@media (max-width: 560px) {
  .hero {
    flex-direction: column-reverse;
    align-items: stretch;
    text-align: center;
  }
  .hero__ring {
    align-self: center;
  }
  .hero__chips {
    justify-content: center;
  }
  .hero__cta {
    align-self: stretch;
  }
  .station,
  .station--right {
    width: 100%;
    flex-direction: row;
    text-align: left;
    padding: 12px 14px 12px 10px;
  }
  .station--right .station__meter {
    flex-direction: row;
  }
  .map__path {
    left: 44px;
  }
}
</style>
