<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { MODULE_MAP, MODULES } from '@/data/modules.js'
import { TOPICS } from '@/data/topics.js'
import { useProgressStore } from '@/stores/progress.js'
import { useMascotCoach } from '@/composables/useMascotCoach.js'
import MascotBot from '@/components/MascotBot.vue'
import { sound } from '@/utils/sound'
import { reducedMotion as prefersReducedMotion } from '@/utils/motion'
import { createFeedback } from '@shared/composables/useFeedback.js'
import OpenMojiIcon from '@shared/components/OpenMojiIcon.vue'

const router = useRouter()
const progress = useProgressStore()
const feedback = createFeedback({
  reducedMotion: prefersReducedMotion,
  particles: {
    glyphs: ['★', '✦', '✧', '✩'],
    colors: ['#ffce4d', '#5ee7ff', '#ff7ac6', '#55e6a5'],
    count: 14,
    size: [8, 18],
    spread: 130,
  },
})
const { burst, wrong } = feedback

/** 小算在首页常驻：气泡里挂着一句和今天进度有关的话，点它换下一句并读出来。 */
const { line: coachLine, mood: coachMood, next: coachNext } = useMascotCoach('home')

const planetRefs = ref([])
const chapterRefs = ref([])

const planets = computed(() =>
  MODULES.map((m) => {
    const stat = progress.moduleStat(m.id)
    const unlocked = progress.isModuleUnlocked(m.id)
    return {
      ...m,
      stat,
      unlocked,
      // 锁着的星球讲「为什么现在去不了」，解锁的讲「到了那儿干什么」
      line: unlocked ? m.story : m.lockedStory,
      // 「还差几颗星」当场算：文案只负责说做什么能攒到，数字由存档说了算
      starsShort: Math.max(0, m.starsToUnlock - progress.state.stars),
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

/** 航线上第一颗还锁着的星球：地图顶上那句「下一章怎么开」说的就是它。 */
const nextLocked = computed(() => planets.value.find((p) => !p.unlocked) ?? null)

/** 专题挑战：比较 / 速算 / 生活应用，三条不占星球位的专线。 */
const topics = TOPICS

function openTopic(topic) {
  sound.click()
  router.push(topic.route)
}

/** 今日冒险：每天 5 题的打卡任务，进度直接读 store。 */
const daily = computed(() => progress.dailyQuest)

const dailyLabel = computed(() => {
  const d = daily.value
  if (d.completed) return `✅ 今日冒险已完成 · 连续 ${d.streak} 天`
  if (d.done > 0) return `🗓️ 继续今日冒险 · ${d.done}/${d.total}`
  return `🗓️ 今日冒险 · ${d.total} 题`
})

function openDaily() {
  sound.click()
  router.push('/daily')
}

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

/* ------------------------------------------------------------ 解锁过场 */

/**
 * 星球从「锁着」变成「能去」是这张地图上最值得庆祝的一刻，
 * 可它多半发生在别的页面——答对最后一题的瞬间——孩子回到地图时
 * 只会看到一颗默默变亮的球。这里把那一刻补演一遍：星球先亮相，
 * 再讲一句剧情，由孩子自己按「出发」收场。不设自动消失，
 * 免得他正好低头看键盘就错过了。
 *
 * 演过的星球记进存档（markPlanetSeen），刷新不会重播。
 */
const scene = ref(null)
const sceneRef = ref(null)
const sceneOrbRef = ref(null)
const sceneBodyRef = ref(null)
const activeAnimations = new Set()

function animate(target, keyframes, options) {
  if (!target?.animate || prefersReducedMotion()) return null
  const animation = target.animate(keyframes, options)
  activeAnimations.add(animation)
  animation.finished
    .catch(() => {})
    .finally(() => activeAnimations.delete(animation))
  return animation
}

function clearAnimations() {
  for (const animation of activeAnimations) animation.cancel()
  activeAnimations.clear()
}

function beginScene() {
  const id = progress.pendingPlanetUnlock
  if (!id || scene.value) return
  const mod = MODULE_MAP[id]
  if (!mod) {
    progress.markPlanetSeen(id)
    return
  }
  scene.value = mod
  nextTick(playScene)
}

function playScene() {
  const root = sceneRef.value
  if (!root) return
  const planetEl = planetRefs.value.find((el) => el?.dataset?.id === scene.value.id)
  sound.combo()
  // 不动版：剧情条照样完整呈现，只是一次到位，不做位移与缩放
  if (prefersReducedMotion()) return

  animate(
    root,
    [
      { opacity: 0, transform: 'translateY(-18px)' },
      { opacity: 1, transform: 'translateY(0)' },
    ],
    { duration: 400, easing: 'ease-out', fill: 'backwards' },
  )
  animate(
    sceneOrbRef.value,
    [
      { filter: 'grayscale(1)', transform: 'scale(0) rotate(-140deg)' },
      { filter: 'grayscale(0)', transform: 'scale(1) rotate(0)' },
    ],
    {
      delay: 250,
      duration: 700,
      easing: 'cubic-bezier(.34,1.56,.64,1)',
      fill: 'backwards',
    },
  )
  ;[...(sceneBodyRef.value?.children ?? [])].forEach((child, index) => {
    animate(
      child,
      [
        { opacity: 0, transform: 'translateY(12px)' },
        { opacity: 1, transform: 'translateY(0)' },
      ],
      {
        delay: 600 + index * 90,
        duration: 340,
        easing: 'ease-out',
        fill: 'backwards',
      },
    )
  })
  window.setTimeout(() => {
    if (scene.value) burst(sceneOrbRef.value, { count: 18 })
  }, 760)

  // 章节轨上对应的那一格也一起亮起来：新开的是「第几章」要看得见
  const chapterEl = chapterRefs.value.find((el) => el?.dataset?.chapter === scene.value.id)
  if (chapterEl) {
    animate(
      chapterEl,
      [
        { filter: 'grayscale(1)', transform: 'scale(.9)' },
        { filter: 'grayscale(0)', transform: 'scale(1)' },
      ],
      { delay: 650, duration: 500, easing: 'cubic-bezier(.34,1.56,.64,1)' },
    )
  }

  // 地图上那颗球同步褪灰，孩子的视线自然从剧情条落回航线
  if (planetEl) {
    animate(
      planetEl,
      [
        { filter: 'grayscale(1)', transform: 'translate(-50%, -50%) scale(.82)' },
        { filter: 'grayscale(0)', transform: 'translate(-50%, -50%) scale(1)' },
      ],
      { delay: 600, duration: 600, easing: 'cubic-bezier(.34,1.56,.64,1)' },
    )
  }
}

/** 收场：记账、清场，若一次解锁了好几颗就接着演下一颗。 */
function closeScene(go = false) {
  const mod = scene.value
  if (!mod) return
  clearAnimations()
  sound.click()
  progress.markPlanetSeen(mod.id)
  scene.value = null
  if (go) router.push(mod.route)
  else nextTick(beginScene)
}

watch(() => progress.pendingPlanetUnlock, beginScene)

/** 让星球入场动画先跑完，过场才不会和它抢同一颗球的 transform。 */
let sceneCue = null

onMounted(() => {
  document.querySelectorAll('.stat-pill').forEach((element, index) => {
    animate(
      element,
      [
        { opacity: 0, transform: 'translateY(18px)' },
        { opacity: 1, transform: 'translateY(0)' },
      ],
      { delay: index * 50, duration: 420, easing: 'ease-out', fill: 'backwards' },
    )
  })
  planetRefs.value.filter(Boolean).forEach((element, index) => {
    animate(
      element,
      [
        { opacity: 0, transform: 'translate(-50%, -50%) scale(0)' },
        { opacity: 1, transform: 'translate(-50%, -50%) scale(1)' },
      ],
      {
        delay: index * 90,
        duration: 550,
        easing: 'cubic-bezier(.34,1.56,.64,1)',
        fill: 'backwards',
      },
    )
  })
  animate(
    document.querySelector('.orbit-path'),
    [{ strokeDashoffset: 400 }, { strokeDashoffset: 0 }],
    { duration: 2200, easing: 'ease-out' },
  )
  sceneCue = window.setTimeout(beginScene, 1100)
})

onUnmounted(() => {
  if (sceneCue) clearTimeout(sceneCue)
  clearAnimations()
  feedback.dispose()
  sceneCue = null
})
</script>

<template>
  <main class="page stack">
    <section class="hero card">
      <div class="hero-text">
        <p class="kicker">开源儿童数学启蒙</p>
        <h2 class="hero-title">星际数学冒险</h2>
        <p class="muted hero-sub">
          点亮六颗数学星球：从数数、加减法，到图形、规律、数独与生活应用题。
        </p>
        <div class="hero-actions">
          <button
            class="btn btn--primary btn--lg daily-cta"
            :class="{ done: daily.completed }"
            data-daily-cta
            @click="openDaily"
          >
            {{ dailyLabel }}
          </button>
          <button v-if="nextPlanet" class="btn btn--ghost btn--lg" @click="open(nextPlanet)">
            🚀 继续冒险 · {{ nextPlanet.name }}
          </button>
          <RouterLink to="/compare" class="btn btn--ghost">⚖️ 比大小擂台</RouterLink>
          <RouterLink to="/progress" class="btn btn--ghost">🏆 我的成就</RouterLink>
          <RouterLink to="/parent" class="btn btn--ghost">👨‍👩‍👧 家长中心</RouterLink>
        </div>
        <div class="daily-track" v-if="!daily.completed">
          <span
            v-for="i in daily.total"
            :key="i"
            class="daily-pip"
            :class="{ on: i <= daily.done }"
            aria-hidden="true"
          />
          <span class="dim small">今天已完成 {{ daily.done }} / {{ daily.total }} 题</span>
        </div>
      </div>
      <div class="hero-bot">
        <MascotBot
          :mood="coachMood"
          :size="128"
          interactive
          tap-label="点我，小算给你说句鼓励的话"
          @tap="coachNext"
        />
        <p class="bot-say" role="status">{{ coachLine }}</p>
      </div>
    </section>

    <section class="tool-deck" aria-labelledby="tool-deck-title">
      <div class="tool-deck-head">
        <div>
          <h3 id="tool-deck-title" class="panel-title">动手学数学</h3>
          <p class="muted">演示、拼摆和逐位计算，把抽象知识变成看得见的操作。</p>
        </div>
        <span class="chip">Round 5 新教具</span>
      </div>
      <div class="tool-grid">
        <RouterLink class="tool-card card demo" to="/visual-demos">
          <span class="tool-icon">🎞️</span>
          <strong>数形演示</strong>
          <small>实物 → 图形 → 算式</small>
        </RouterLink>
        <RouterLink class="tool-card card compose" to="/compose-ten">
          <span class="tool-icon">🔵</span>
          <strong>10 的分与合</strong>
          <small>移动十颗弹珠</small>
        </RouterLink>
        <RouterLink class="tool-card card tangram" to="/tangram">
          <span class="tool-icon">🧩</span>
          <strong>七巧板</strong>
          <small>Canvas 火箭拼图</small>
        </RouterLink>
        <RouterLink class="tool-card card column" to="/column-arithmetic">
          <span class="tool-icon">🧮</span>
          <strong>竖式工坊</strong>
          <small>进位 / 借位错因专练</small>
        </RouterLink>
        <RouterLink class="tool-card card memory" to="/memory-pairs">
          <span class="tool-icon">🃏</span>
          <strong>配对记忆</strong>
          <small>Canvas 记忆矩阵</small>
        </RouterLink>
        <RouterLink class="tool-card card maze" to="/maze">
          <span class="tool-icon">🌀</span>
          <strong>逻辑迷宫</strong>
          <small>按顺序收能量块</small>
        </RouterLink>
      </div>
    </section>

    <section class="tool-deck topic-deck" aria-labelledby="topic-deck-title">
      <div class="tool-deck-head">
        <div>
          <h3 id="topic-deck-title" class="panel-title">专题挑战</h3>
          <p class="muted">想专门补哪一块就点哪一条，成绩照样记进对应的星球。</p>
        </div>
        <span class="chip">比较 · 速算 · 生活</span>
      </div>
      <div class="topic-grid">
        <button
          v-for="t in topics"
          :key="t.id"
          class="topic-card card"
          :data-topic="t.id"
          :data-route="t.route"
          @click="openTopic(t)"
        >
          <div class="topic-top row">
            <span class="topic-icon"><OpenMojiIcon :emoji="t.emoji" :size="30" /></span>
            <div class="topic-titles">
              <strong>{{ t.name }}</strong>
              <span class="dim small">{{ t.tagline }}</span>
            </div>
          </div>
          <p class="topic-blurb muted">{{ t.blurb }}</p>
          <div class="skills">
            <span v-for="s in t.skills" :key="s" class="chip">{{ s }}</span>
          </div>
        </button>
      </div>
    </section>

    <section
      v-if="scene"
      ref="sceneRef"
      class="unlock-scene card"
      :style="{ '--pc': scene.color, '--pa': scene.accent }"
      role="status"
      aria-live="polite"
    >
      <span ref="sceneOrbRef" class="unlock-orb" aria-hidden="true">
        <OpenMojiIcon :emoji="scene.emoji" :size="44" />
      </span>
      <div ref="sceneBodyRef" class="unlock-body">
        <p class="unlock-kicker">{{ scene.chapterName }} 解锁</p>
        <strong class="unlock-name">{{ scene.name }}</strong>
        <p class="unlock-line">{{ scene.unlockLine }}</p>
        <p class="unlock-story muted">{{ scene.story }}</p>
        <p class="unlock-goal dim small">🎯 {{ scene.goal }}</p>
      </div>
      <div class="unlock-actions">
        <button class="btn btn--primary" @click="closeScene(true)">🚀 立刻出发</button>
        <button class="btn btn--ghost" @click="closeScene(false)">待会儿再去</button>
      </div>
    </section>

    <section class="stats-strip">
      <div v-for="t in totals" :key="t.label" class="stat-pill">
        <span class="stat-icon"><OpenMojiIcon :emoji="t.icon" :size="22" /></span>
        <span class="stat-value">{{ t.value }}</span>
        <span class="stat-label dim">{{ t.label }}</span>
      </div>
    </section>

    <section class="map card">
      <div class="map-head row">
        <h3 class="panel-title"><OpenMojiIcon name="world-map" :size="20" /> 学习地图</h3>
        <span class="chip">收集星星解锁新星球</span>
      </div>
      <p v-if="nextPlanet" class="map-chapter">
        <span class="chapter-tag">{{ nextPlanet.chapterName }}</span>
        <span class="dim small">🎯 {{ nextPlanet.goal }}</span>
      </p>
      <p v-if="nextPlanet" class="map-story muted">
        <span aria-hidden="true">🛸</span>
        {{ nextPlanet.line }}
      </p>
      <p v-if="nextLocked" class="map-unlock">
        <span aria-hidden="true">🔒</span>
        下一章「{{ nextLocked.chapterName }}」还差 {{ nextLocked.starsShort }} ⭐ ——
        {{ nextLocked.unlockHint }}
      </p>

      <!-- 章节轨：六章一字排开，走到哪儿、下一章还差多少，一眼看完 -->
      <ol class="chapter-rail" aria-label="章节进度">
        <li
          v-for="(p, i) in planets"
          :key="`ch-${p.id}`"
          :ref="(el) => (chapterRefs[i] = el)"
          :data-chapter="p.id"
          class="chapter-step"
          :class="{ locked: !p.unlocked, current: p.id === nextPlanet?.id }"
          :style="{ '--pc': p.color }"
        >
          <span class="chapter-no">{{ p.chapterNo }}</span>
          <span class="chapter-name">{{ p.chapterName.split(' · ')[1] ?? p.name }}</span>
          <span v-if="!p.unlocked" class="chapter-need dim">还差 {{ p.starsShort }} ⭐</span>
          <span v-else class="chapter-need dim">{{ p.mastery }}%</span>
        </li>
      </ol>

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
          :class="{
            locked: !p.unlocked,
            'is-next': p.id === nextPlanet?.id,
            'is-unlocking': p.id === scene?.id,
          }"
          :style="{
            left: `${p.node.x}%`,
            top: `${p.node.y}%`,
            '--pc': p.color,
            '--pa': p.accent,
            animationDelay: `${i * 0.4}s`,
          }"
          :aria-label="`${p.chapterName}：${p.name}${
            p.unlocked ? '' : `（未解锁，还差 ${p.starsShort} 颗星。${p.unlockHint}）`
          }${p.id === nextPlanet?.id ? '（推荐下一站）' : ''}：${p.line}`"
          @click="open(p)"
        >
          <span class="planet-body">
            <OpenMojiIcon class="planet-emoji" :emoji="p.unlocked ? p.emoji : '🔒'" :size="36" />
            <span v-if="p.stat.answered > 0" class="planet-badge">{{ p.mastery }}%</span>
          </span>
          <span class="planet-label">
            <i class="planet-chapter">第 {{ p.chapterNo }} 章</i>
            <strong>{{ p.name }}</strong>
            <em v-if="!p.unlocked">还差 {{ p.starsShort }} ⭐</em>
            <em v-else>{{ p.subtitle }}</em>
          </span>
        </button>
      </div>
    </section>

    <section class="grid-cards">
      <button
        v-for="p in planets"
        :key="`card-${p.id}`"
        class="mod-card card"
        :class="{ locked: !p.unlocked, 'is-next': p.id === nextPlanet?.id }"
        :style="{ '--pc': p.color, '--pa': p.accent }"
        @click="open(p)"
      >
        <div class="mod-top row">
          <span class="mod-emoji"><OpenMojiIcon :emoji="p.unlocked ? p.emoji : '🔒'" :size="32" /></span>
          <div class="mod-titles">
            <span class="mod-chapter">{{ p.chapterName }}</span>
            <strong class="mod-name">{{ p.name }}</strong>
            <span class="mod-sub dim">{{ p.subtitle }}</span>
          </div>
          <span v-if="p.id === nextPlanet?.id" class="chip next-chip">推荐下一站</span>
        </div>
        <p class="mod-story">
          <span aria-hidden="true">{{ p.unlocked ? '✨' : '🔒' }}</span>
          {{ p.line }}
        </p>
        <p v-if="!p.unlocked" class="mod-hint">
          解锁条件：还差 {{ p.starsShort }} ⭐ —— {{ p.unlockHint }}
        </p>
        <p v-else class="mod-goal dim small">🎯 {{ p.goal }}</p>
        <p v-if="p.unlocked" class="mod-blurb muted">{{ p.blurb }}</p>
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
  color: var(--brand);
}

.hero-title {
  font-size: clamp(28px, 5vw, 44px);
  font-weight: 900;
  line-height: 1.1;
  background: linear-gradient(120deg, var(--text-strong), var(--brand) 40%, var(--neon-pink));
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
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  width: min(200px, 100%);
}

.bot-say {
  padding: 8px 14px;
  border-radius: var(--radius-md);
  background: var(--surface-sunken);
  border: 1px solid var(--surface-border);
  font-size: 13px;
  font-weight: 700;
  line-height: 1.5;
  text-align: center;
  color: var(--text-strong);
}

.daily-cta.done {
  filter: saturate(0.85);
}

.daily-track {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
}

.daily-pip {
  width: 26px;
  height: 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.16);
}

.daily-pip.on {
  background: linear-gradient(90deg, var(--cyan), var(--violet));
  border-color: transparent;
}

.daily-track .small {
  margin-left: 6px;
}

.tool-deck {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tool-deck-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.tool-deck-head p {
  margin-top: 3px;
  font-size: 13px;
}

.tool-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

.tool-card {
  min-height: 132px;
  padding: 15px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 4px;
  border-color: color-mix(in srgb, var(--tool-color) 42%, transparent);
  background:
    radial-gradient(circle at 100% 0%, color-mix(in srgb, var(--tool-color) 22%, transparent), transparent 56%),
    linear-gradient(160deg, var(--surface), color-mix(in srgb, var(--cosmos-1) 92%, transparent));
  transition: transform 0.16s ease, border-color 0.16s ease;
}

.tool-card:hover {
  transform: translateY(-4px);
  border-color: var(--tool-color);
}

.tool-card.demo {
  --tool-color: var(--brand);
}

.tool-card.compose {
  --tool-color: var(--neon-violet);
}

.tool-card.tangram {
  --tool-color: var(--neon-pink);
}

.tool-card.column {
  --tool-color: var(--star);
}

.tool-card.memory {
  --tool-color: var(--neon-cyan);
}

.tool-card.maze {
  --tool-color: var(--success);
}

.tool-icon {
  font-size: 29px;
}

.tool-card strong {
  font-size: 15px;
}

.tool-card small {
  color: var(--text-soft);
}

.topic-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.topic-card {
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px;
  border-color: color-mix(in srgb, var(--brand) 30%, transparent);
  background:
    radial-gradient(90% 130% at 100% 0%, color-mix(in srgb, var(--neon-violet) 16%, transparent), transparent 58%),
    linear-gradient(160deg, var(--surface), color-mix(in srgb, var(--cosmos-1) 92%, transparent));
  transition: transform 0.16s ease, border-color 0.16s ease;
}

.topic-card:hover {
  transform: translateY(-4px);
  border-color: var(--brand);
}

.topic-top {
  gap: 10px;
}

.topic-icon {
  width: 44px;
  height: 44px;
  flex: none;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: linear-gradient(140deg, color-mix(in srgb, var(--brand) 28%, transparent), transparent);
  border: 1px solid color-mix(in srgb, var(--brand) 40%, transparent);
}

.topic-titles {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.topic-titles strong {
  font-size: 16px;
}

.topic-blurb {
  font-size: 13px;
  line-height: 1.5;
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
  border-radius: var(--radius-md);
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

.unlock-scene {
  display: flex;
  align-items: center;
  gap: 16px;
  border-color: color-mix(in srgb, var(--pc) 55%, transparent);
  background:
    radial-gradient(90% 160% at 0% 50%, color-mix(in srgb, var(--pc) 26%, transparent), transparent 62%),
    linear-gradient(140deg, var(--surface), color-mix(in srgb, var(--cosmos-1) 92%, transparent));
}

.unlock-orb {
  flex: none;
  width: 78px;
  height: 78px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: linear-gradient(140deg, var(--pc), var(--pa));
  box-shadow: 0 0 0 6px color-mix(in srgb, var(--pc) 26%, transparent);
}

.unlock-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.unlock-kicker {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 2px;
  color: var(--pc);
}

.unlock-name {
  font-size: 20px;
  font-weight: 900;
}

.unlock-line {
  font-size: 14px;
  line-height: 1.5;
}

.unlock-story {
  font-size: 13px;
}

.unlock-actions {
  flex: none;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.map-head {
  margin-bottom: 8px;
}

.map-head .chip {
  margin-left: auto;
}

.map-chapter {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}

.chapter-tag {
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 1px;
  color: var(--text-invert);
  background: linear-gradient(135deg, var(--brand), var(--neon-violet));
}

.map-story {
  margin-bottom: 10px;
  font-size: 13px;
}

.map-unlock {
  margin: -4px 0 10px;
  font-size: 13px;
  line-height: 1.5;
  color: var(--text-soft);
}

/* ---- 章节轨 ---- */

.chapter-rail {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 6px;
  margin-bottom: 12px;
  list-style: none;
}

.chapter-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 8px 4px;
  border-radius: var(--radius-sm);
  border: 1px solid color-mix(in srgb, var(--pc) 34%, transparent);
  background: color-mix(in srgb, var(--pc) 10%, transparent);
  text-align: center;
}

.chapter-step.locked {
  border-color: var(--surface-border);
  background: var(--surface-sunken);
  filter: grayscale(1);
}

.chapter-step.current {
  border-color: var(--pc);
  box-shadow: 0 0 0 1px color-mix(in srgb, var(--pc) 40%, transparent);
}

.chapter-no {
  font-size: 15px;
  font-weight: 900;
  color: var(--pc);
}

.chapter-step.locked .chapter-no {
  color: var(--text-soft);
}

.chapter-name {
  font-size: 12px;
  font-weight: 800;
  line-height: 1.25;
}

.chapter-need {
  font-size: 11px;
}

.map-canvas {
  position: relative;
  height: 340px;
  border-radius: var(--radius-md);
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
  background: radial-gradient(
      circle at 32% 28%,
      color-mix(in srgb, var(--surface-strong) 20%, transparent),
      transparent 55%
    ),
    linear-gradient(140deg, var(--pc), var(--pa));
  box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.08), 0 12px 28px rgba(0, 0, 0, 0.45);
  transition: transform 0.18s ease;
}

.planet:hover .planet-body {
  transform: scale(1.1);
}

/* 未解锁 = 整颗球退成灰调：一眼看得出「这儿还没开」，但轮廓仍留在航线上 */
.planet.locked .planet-body {
  background: linear-gradient(140deg, var(--surface-strong), var(--surface-sunken));
  filter: grayscale(1) brightness(0.85);
}

.planet.locked .planet-label strong {
  color: var(--text-soft);
}

/* 正在演过场的那颗球先跳出灰调，和剧情条对上号 */
.planet.is-unlocking .planet-body {
  filter: none;
  box-shadow:
    0 0 0 8px color-mix(in srgb, var(--pc) 42%, transparent),
    0 0 34px 10px color-mix(in srgb, var(--pc) 40%, transparent);
}

/* 推荐下一站的星球「呼吸」：只动光晕，不动 transform，免得和 bob 打架 */
.planet.is-next .planet-body {
  animation: breathe 2.8s ease-in-out infinite;
}

.planet.is-next .planet-label strong {
  color: var(--pc);
}

@keyframes breathe {
  0%,
  100% {
    box-shadow:
      0 0 0 4px rgba(255, 255, 255, 0.08),
      0 12px 28px rgba(0, 0, 0, 0.45);
  }
  50% {
    box-shadow:
      0 0 0 9px color-mix(in srgb, var(--pc) 40%, transparent),
      0 0 32px 8px color-mix(in srgb, var(--pc) 45%, transparent),
      0 12px 28px rgba(0, 0, 0, 0.45);
  }
}

.planet-badge {
  position: absolute;
  right: -8px;
  bottom: -4px;
  font-size: 11px;
  font-weight: 900;
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--cosmos-1);
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

.planet-chapter {
  font-style: normal;
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 1px;
  color: var(--pc);
}

.planet.locked .planet-chapter {
  color: var(--text-soft);
}

.planet-label strong {
  font-size: 13px;
}

.planet-label em {
  font-style: normal;
  font-size: 11px;
  color: var(--text-soft);
}

.mod-card {
  text-align: left;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 18px;
  transition: transform 0.16s ease, border-color 0.16s ease;
  border-radius: var(--radius-md);
}

.mod-card:hover {
  transform: translateY(-4px);
  border-color: color-mix(in srgb, var(--pc) 60%, transparent);
}

.mod-card.locked {
  filter: grayscale(0.9);
  border-style: dashed;
}

.mod-story {
  font-size: 13.5px;
  line-height: 1.5;
  color: var(--text-strong);
}

.mod-card.locked .mod-story {
  color: var(--text-soft);
  font-style: italic;
}

/* 解锁条件写成一句可执行的话，而不是只挂一个「需 N ⭐」的价签 */
.mod-hint {
  font-size: 12.5px;
  line-height: 1.5;
  padding: 7px 10px;
  border-radius: var(--radius-sm);
  color: var(--text);
  background: var(--surface-sunken);
  border: 1px dashed color-mix(in srgb, var(--pc) 45%, transparent);
}

.mod-goal {
  font-size: 12.5px;
  line-height: 1.5;
}

.mod-card.is-next {
  border-color: color-mix(in srgb, var(--pc) 55%, transparent);
  animation: card-breathe 2.8s ease-in-out infinite;
}

@keyframes card-breathe {
  0%,
  100% {
    box-shadow: 0 0 0 0 color-mix(in srgb, var(--pc) 0%, transparent);
  }
  50% {
    box-shadow: 0 0 26px 2px color-mix(in srgb, var(--pc) 32%, transparent);
  }
}

.next-chip {
  margin-left: auto;
  flex: none;
  color: var(--pc);
  border-color: color-mix(in srgb, var(--pc) 55%, transparent);
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

.mod-chapter {
  font-size: 11px;
  font-weight: 900;
  letter-spacing: 1px;
  color: var(--pc);
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

/* 关掉动效时呼吸灯退化为常亮描边：推荐位不能因为不动就消失 */
@media (prefers-reduced-motion: reduce) {
  .planet.is-next .planet-body {
    box-shadow:
      0 0 0 6px color-mix(in srgb, var(--pc) 40%, transparent),
      0 12px 28px rgba(0, 0, 0, 0.45);
  }

  .mod-card.is-next {
    box-shadow: 0 0 18px 1px color-mix(in srgb, var(--pc) 28%, transparent);
  }
}

@media (max-width: 720px) {
  .unlock-scene {
    flex-wrap: wrap;
  }

  .unlock-actions {
    flex-direction: row;
    width: 100%;
  }

  .unlock-actions .btn {
    flex: 1;
  }
}

@media (max-width: 860px) {
  .hero {
    flex-direction: column;
    text-align: center;
  }

  .hero-actions {
    justify-content: center;
  }

  .daily-track {
    justify-content: center;
    flex-wrap: wrap;
  }

  .map-canvas {
    height: 300px;
  }

  .planet-body {
    width: 54px;
    height: 54px;
    font-size: 24px;
  }

  .tool-grid,
  .topic-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .chapter-rail {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (max-width: 560px) {
  .stats-strip,
  .topic-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .map {
    display: none;
  }

  .tool-deck-head {
    align-items: flex-start;
  }
}
</style>
