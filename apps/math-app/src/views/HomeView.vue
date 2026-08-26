<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import gsap from 'gsap'
import { MODULES } from '@/data/modules.js'
import { useProgressStore } from '@/stores/progress.js'
import { useFeedback } from '@/composables/useFeedback'
import MascotBot from '@/components/MascotBot.vue'
import { sound } from '@/core/audio/sound.js'

const router = useRouter()
const progress = useProgressStore()
const { enter, wrong } = useFeedback()

const planetRefs = ref([])

const planets = computed(() =>
  MODULES.map((m) => {
    const stat = progress.moduleStat(m.id)
    return {
      ...m,
      stat,
      unlocked: progress.isModuleUnlocked(m.id),
      mastery: Math.round(progress.moduleProgress(m.id) * 100),
    }
  }),
)

const nextPlanet = computed(
  () =>
    planets.value.find((p) => p.unlocked && p.stat.answered === 0) ??
    planets.value.filter((p) => p.unlocked).at(-1) ??
    planets.value[0],
)

const pathD = computed(() => {
  const pts = MODULES.map((m) => m.node)
  let d = `M ${pts[0].x} ${pts[0].y}`
  for (let i = 1; i < pts.length; i++) {
    const mx = (pts[i - 1].x + pts[i].x) / 2
    d += ` C ${mx} ${pts[i - 1].y}, ${mx} ${pts[i].y}, ${pts[i].x} ${pts[i].y}`
  }
  return d
})

const totals = computed(() => [
  { label: '星星', value: progress.state.stars, icon: '⭐' },
  { label: '答题', value: progress.state.totalAnswered, icon: '📘' },
  { label: '正确率', value: `${progress.accuracy}%`, icon: '🎯' },
  {
    label: '成就',
    value: `${progress.unlockedAchievements.length}/${
      progress.unlockedAchievements.length + progress.lockedAchievements.length
    }`,
    icon: '🏆',
  },
])

function open(planet) {
  if (!planet.unlocked) {
    sound.wrong()
    wrong(
      planetRefs.value.find((r) => r?.dataset?.id === planet.id),
      { sound: false },
    )
    return
  }
  sound.click()
  router.push(planet.route)
}

onMounted(() => {
  enter('.stat-pill', { stagger: 0.05 })
  gsap.fromTo(
    planetRefs.value.filter(Boolean),
    { scale: 0, opacity: 0 },
    { scale: 1, opacity: 1, duration: 0.55, stagger: 0.09, ease: 'back.out(1.7)' },
  )
  gsap.fromTo('.orbit-path', { strokeDashoffset: 400 }, { strokeDashoffset: 0, duration: 2.2, ease: 'power2.out' })
})
</script>

<template>
  <main class="page stack">
    <section class="hero panel">
      <div class="hero-text">
        <p class="kicker">开源儿童数学启蒙</p>
        <h2 class="hero-title">星际数学冒险</h2>
        <p class="muted hero-sub">
          点亮六颗数学星球：从数数、加减法，到图形、规律、数独与生活应用题。
        </p>
        <div class="hero-actions">
          <button v-if="nextPlanet" class="btn btn-primary btn-lg" @click="open(nextPlanet)">
            🚀 继续冒险 · {{ nextPlanet.name }}
          </button>
          <RouterLink to="/progress" class="btn btn-ghost">🏆 我的成就</RouterLink>
        </div>
      </div>
      <MascotBot mood="idle" :size="128" class="hero-bot" />
    </section>

    <section class="stats-strip">
      <div v-for="t in totals" :key="t.label" class="stat-pill">
        <span class="stat-icon">{{ t.icon }}</span>
        <span class="stat-value">{{ t.value }}</span>
        <span class="stat-label dim">{{ t.label }}</span>
      </div>
    </section>

    <section class="map panel">
      <div class="map-head row">
        <h3 class="panel-title">🗺️ 学习地图</h3>
        <span class="chip">收集星星解锁新星球</span>
      </div>

      <div class="map-canvas">
        <svg class="orbit" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <path class="orbit-path" :d="pathD" />
        </svg>

        <button
          v-for="(p, i) in planets"
          :key="p.id"
          :ref="(el) => (planetRefs[i] = el)"
          :data-id="p.id"
          class="planet"
          :class="{ locked: !p.unlocked }"
          :style="{
            left: `${p.node.x}%`,
            top: `${p.node.y}%`,
            '--pc': p.color,
            '--pa': p.accent,
            animationDelay: `${i * 0.4}s`,
          }"
          :aria-label="`${p.name}${p.unlocked ? '' : '（未解锁）'}`"
          @click="open(p)"
        >
          <span class="planet-body">
            <span class="planet-emoji">{{ p.unlocked ? p.emoji : '🔒' }}</span>
            <span v-if="p.stat.answered > 0" class="planet-badge">{{ p.mastery }}%</span>
          </span>
          <span class="planet-label">
            <strong>{{ p.name }}</strong>
            <em v-if="!p.unlocked">需 {{ p.starsToUnlock }} ⭐</em>
            <em v-else>{{ p.subtitle }}</em>
          </span>
        </button>
      </div>
    </section>

    <section class="grid-cards">
      <button
        v-for="p in planets"
        :key="`card-${p.id}`"
        class="mod-card panel"
        :class="{ locked: !p.unlocked }"
        :style="{ '--pc': p.color, '--pa': p.accent }"
        @click="open(p)"
      >
        <div class="mod-top row">
          <span class="mod-emoji">{{ p.unlocked ? p.emoji : '🔒' }}</span>
          <div class="mod-titles">
            <strong class="mod-name">{{ p.name }}</strong>
            <span class="mod-sub dim">{{ p.subtitle }}</span>
          </div>
        </div>
        <p class="mod-blurb muted">{{ p.blurb }}</p>
        <div class="skills">
          <span v-for="s in p.skills" :key="s" class="chip">{{ s }}</span>
        </div>
        <div class="mod-progress">
          <div class="bar"><div class="fill" :style="{ width: `${p.mastery}%` }" /></div>
          <span class="dim small">
            {{ p.unlocked ? `已答对 ${p.stat.correct} 题 · 掌握度 ${p.mastery}%` : `累计 ${p.starsToUnlock} ⭐ 解锁` }}
          </span>
        </div>
      </button>
    </section>
  </main>
</template>

<style scoped>
.hero {
  display: flex;
  align-items: center;
  gap: 20px;
  background:
    radial-gradient(120% 140% at 100% 0%, rgba(255, 122, 198, 0.22), transparent 55%),
    linear-gradient(160deg, rgba(37, 46, 108, 0.92), rgba(16, 21, 60, 0.92));
}

.hero-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.kicker {
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 2px;
  color: var(--cyan);
}

.hero-title {
  font-size: clamp(28px, 5vw, 44px);
  font-weight: 900;
  line-height: 1.1;
  background: linear-gradient(120deg, #ffffff, var(--cyan) 40%, var(--pink));
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}

.hero-sub {
  font-size: 15px;
  max-width: 46ch;
}

.hero-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 8px;
}

.hero-bot {
  flex: none;
}

.stats-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.stat-pill {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 12px 8px;
  border-radius: var(--radius-m);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.stat-icon {
  font-size: 20px;
}

.stat-value {
  font-size: 20px;
  font-weight: 900;
}

.stat-label {
  font-size: 12px;
}

.map-head {
  margin-bottom: 8px;
}

.map-head .chip {
  margin-left: auto;
}

.map-canvas {
  position: relative;
  height: 340px;
  border-radius: var(--radius-m);
  background:
    radial-gradient(60% 80% at 20% 80%, rgba(94, 231, 255, 0.14), transparent 60%),
    radial-gradient(60% 80% at 80% 20%, rgba(255, 122, 198, 0.14), transparent 60%),
    rgba(8, 12, 38, 0.5);
  border: 1px solid rgba(140, 158, 255, 0.16);
}

.orbit {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.orbit-path {
  fill: none;
  stroke: rgba(148, 168, 255, 0.55);
  stroke-width: 0.5;
  stroke-dasharray: 2 2.4;
  vector-effect: non-scaling-stroke;
}

.planet {
  position: absolute;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  animation: bob 4.6s ease-in-out infinite;
}

@keyframes bob {
  0%,
  100% {
    transform: translate(-50%, -50%);
  }
  50% {
    transform: translate(-50%, calc(-50% - 9px));
  }
}

.planet-body {
  position: relative;
  width: 68px;
  height: 68px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  font-size: 30px;
  background: radial-gradient(circle at 32% 28%, #ffffff33, transparent 55%),
    linear-gradient(140deg, var(--pc), var(--pa));
  box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.08), 0 12px 28px rgba(0, 0, 0, 0.45);
  transition: transform 0.18s ease;
}

.planet:hover .planet-body {
  transform: scale(1.1);
}

.planet.locked .planet-body {
  background: linear-gradient(140deg, #3a4272, #262c52);
  filter: saturate(0.4);
}

.planet-badge {
  position: absolute;
  right: -8px;
  bottom: -4px;
  font-size: 11px;
  font-weight: 900;
  padding: 2px 7px;
  border-radius: 999px;
  background: #0b1030;
  border: 1px solid var(--pc);
  color: var(--pc);
}

.planet-label {
  display: flex;
  flex-direction: column;
  align-items: center;
  line-height: 1.25;
  text-align: center;
  white-space: nowrap;
}

.planet-label strong {
  font-size: 13px;
}

.planet-label em {
  font-style: normal;
  font-size: 11px;
  color: var(--ink-dim);
}

.mod-card {
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 18px;
  transition: transform 0.16s ease, border-color 0.16s ease;
  border-radius: var(--radius-m);
}

.mod-card:hover {
  transform: translateY(-4px);
  border-color: color-mix(in srgb, var(--pc) 60%, transparent);
}

.mod-card.locked {
  opacity: 0.55;
}

.mod-emoji {
  width: 46px;
  height: 46px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  font-size: 24px;
  background: linear-gradient(140deg, color-mix(in srgb, var(--pc) 30%, transparent), transparent);
  border: 1px solid color-mix(in srgb, var(--pc) 45%, transparent);
  flex: none;
}

.mod-titles {
  display: flex;
  flex-direction: column;
}

.mod-name {
  font-size: 17px;
  font-weight: 900;
}

.mod-sub {
  font-size: 12px;
}

.mod-blurb {
  font-size: 14px;
  line-height: 1.5;
}

.skills {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.mod-progress {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.bar {
  height: 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  overflow: hidden;
}

.fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--pc), var(--pa));
  transition: width 0.6s ease;
}

.small {
  font-size: 12px;
}

@media (max-width: 860px) {
  .hero {
    flex-direction: column;
    text-align: center;
  }

  .hero-actions {
    justify-content: center;
  }

  .map-canvas {
    height: 300px;
  }

  .planet-body {
    width: 54px;
    height: 54px;
    font-size: 24px;
  }
}

@media (max-width: 560px) {
  .stats-strip {
    grid-template-columns: repeat(2, 1fr);
  }

  .map {
    display: none;
  }
}
</style>
