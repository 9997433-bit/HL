<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import gsap from 'gsap'
import MascotBot from '@/components/MascotBot.vue'
import { ACHIEVEMENTS } from '@/data/achievements'
import { MODULES, MODULE_MAP } from '@/data/modules.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { useFeedback } from '@/composables/useFeedback'
import { sound } from '@/core/audio/sound.js'

const AVATARS = ['🧑‍🚀', '👩‍🚀', '🤖', '👽', '🐱', '🦊', '🐼', '🦖']

const router = useRouter()
const progress = useProgressStore()
const settings = useSettingsStore()
const { burst, pop, wrong } = useFeedback()

const filter = ref('all') // all | unlocked | locked
const editingName = ref(false)
const nameDraft = ref('')
const confirmReset = ref(false)
const gridRef = ref(null)

const unlockedIds = computed(() => progress.state.achievements)
const unlockedCount = computed(() => ACHIEVEMENTS.filter((a) => unlockedIds.value[a.id]).length)
const ratio = computed(() => Math.round((unlockedCount.value / ACHIEVEMENTS.length) * 100))

const cards = computed(() =>
  ACHIEVEMENTS.map((a) => ({
    ...a,
    unlocked: !!unlockedIds.value[a.id],
    at: unlockedIds.value[a.id] ?? null,
  })).filter((a) =>
    filter.value === 'unlocked' ? a.unlocked : filter.value === 'locked' ? !a.unlocked : true,
  ),
)

const moduleRows = computed(() =>
  MODULES.map((m) => {
    const s = progress.moduleStat(m.id)
    return {
      ...m,
      ...s,
      rate: s.answered ? Math.round((s.correct / s.answered) * 100) : 0,
      mastery: Math.round(progress.moduleProgress(m.id) * 100),
    }
  }),
)

const maxAnswered = computed(() => Math.max(1, ...moduleRows.value.map((r) => r.answered)))

/** 最近 12 次练习的得分曲线。 */
const spark = computed(() => {
  const list = [...progress.state.history].slice(0, 12).reverse()
  if (list.length < 2) return null
  const w = 260
  const h = 60
  const step = w / (list.length - 1)
  const points = list.map((h2, i) => `${(i * step).toFixed(1)},${(h - (h2.score / 100) * h).toFixed(1)}`)
  return {
    list,
    points: points.join(' '),
    area: `0,${h} ${points.join(' ')} ${w},${h}`,
    w,
    h,
    avg: Math.round(list.reduce((s, x) => s + x.score, 0) / list.length),
  }
})

const ringDash = computed(() => `${ratio.value * 2.51}, 251`)

function fmtDate(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

function tapCard(card, e) {
  sound.click()
  if (card.unlocked) {
    pop(e.currentTarget)
    burst(e.currentTarget, { count: 12 })
  } else {
    wrong(e.currentTarget, { sound: false })
  }
}

function setFilter(v) {
  if (filter.value === v) return
  sound.click()
  filter.value = v
  requestAnimationFrame(() =>
    gsap.fromTo(
      '.ach',
      { opacity: 0, scale: 0.85 },
      { opacity: 1, scale: 1, duration: 0.3, stagger: 0.03, ease: 'back.out(2)' },
    ),
  )
}

function startEditName() {
  nameDraft.value = progress.state.pilotName
  editingName.value = true
}

function saveName() {
  const v = nameDraft.value.trim().slice(0, 12)
  if (v) progress.state.pilotName = v
  editingName.value = false
  sound.star()
}

function chooseAvatar(a) {
  progress.state.avatar = a
  sound.click()
}

function toggleSound() {
  settings.toggle('soundOn')
  if (settings.soundOn) sound.correct()
}

function toggleEyeCare() {
  settings.toggle('eyeCare')
  sound.click()
}

function doReset() {
  progress.resetAll()
  confirmReset.value = false
  sound.wrong()
}

/** 家长可导出 JSON 学习报告，便于备份或换设备。 */
function exportReport() {
  sound.click()
  const blob = new Blob([progress.exportReport()], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `mathquest-report-${new Date().toISOString().slice(0, 10)}.json`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(() => {
  gsap.fromTo(
    '.ach',
    { opacity: 0, scale: 0.8, y: 14 },
    { opacity: 1, scale: 1, y: 0, duration: 0.38, stagger: 0.035, ease: 'back.out(2)' },
  )
  gsap.fromTo('.ring-fill', { strokeDasharray: '0, 251' }, { strokeDasharray: ringDash.value, duration: 1.1, ease: 'power2.out' })
})
</script>

<template>
  <main class="page stack">
    <!-- 档案卡 -->
    <section class="panel profile">
      <div class="avatar-block">
        <span class="avatar">{{ progress.state.avatar }}</span>
        <MascotBot :mood="unlockedCount > 0 ? 'happy' : 'idle'" :size="64" />
      </div>

      <div class="profile-main">
        <div class="name-row">
          <template v-if="editingName">
            <input
              v-model="nameDraft"
              class="name-input"
              maxlength="12"
              placeholder="输入昵称"
              @keyup.enter="saveName"
            />
            <button class="btn btn-primary btn-sm" @click="saveName">保存</button>
          </template>
          <template v-else>
            <h2 class="pilot">{{ progress.state.pilotName }}</h2>
            <button class="btn btn-ghost btn-sm" @click="startEditName">✏️ 改名</button>
          </template>
        </div>

        <div class="avatars">
          <button
            v-for="a in AVATARS"
            :key="a"
            class="av-pick"
            :class="{ on: progress.state.avatar === a }"
            @click="chooseAvatar(a)"
          >
            {{ a }}
          </button>
        </div>

        <div class="stat-grid">
          <div class="stat">
            <span class="v">Lv.{{ progress.state.level }}</span><span class="k dim">等级</span>
          </div>
          <div class="stat">
            <span class="v">{{ progress.state.stars }}</span><span class="k dim">星星</span>
          </div>
          <div class="stat">
            <span class="v">{{ progress.state.totalAnswered }}</span><span class="k dim">总题数</span>
          </div>
          <div class="stat">
            <span class="v">{{ progress.accuracy }}%</span><span class="k dim">正确率</span>
          </div>
          <div class="stat">
            <span class="v">{{ progress.state.bestStreak }}</span><span class="k dim">最佳连击</span>
          </div>
          <div class="stat">
            <span class="v">{{ progress.state.dailyStreak }}</span><span class="k dim">连续打卡</span>
          </div>
          <div class="stat">
            <span class="v">{{ progress.masteredCount }}/{{ progress.totalSkills }}</span
            ><span class="k dim">技能达标</span>
          </div>
          <div class="stat">
            <span class="v">{{ progress.state.counters.sudokuSolved }}</span
            ><span class="k dim">数独通关</span>
          </div>
        </div>

        <div class="xp">
          <div class="xp-bar">
            <span class="xp-fill" :style="{ width: `${progress.levelProgress * 100}%` }" />
          </div>
          <p class="dim tiny">
            距离 Lv.{{ progress.state.level + 1 }} 还需
            {{ progress.xpToNext - progress.state.xp }} 经验
          </p>
        </div>
      </div>

      <div class="ring-block">
        <svg viewBox="0 0 100 100" width="118" height="118" aria-hidden="true">
          <circle cx="50" cy="50" r="40" fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="8" />
          <circle
            class="ring-fill"
            cx="50"
            cy="50"
            r="40"
            fill="none"
            stroke="url(#achGrad)"
            stroke-width="8"
            stroke-linecap="round"
            :stroke-dasharray="ringDash"
            transform="rotate(-90 50 50)"
          />
          <defs>
            <linearGradient id="achGrad" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stop-color="#ffce4d" />
              <stop offset="100%" stop-color="#ff7ac6" />
            </linearGradient>
          </defs>
        </svg>
        <div class="ring-text">
          <strong>{{ unlockedCount }}</strong>
          <span class="dim">/ {{ ACHIEVEMENTS.length }}</span>
        </div>
      </div>
    </section>

    <!-- 成就墙 -->
    <section class="panel">
      <header class="wall-head">
        <h3 class="panel-title">🏆 成就墙</h3>
        <div class="spacer" />
        <div class="seg">
          <button class="seg-btn" :class="{ on: filter === 'all' }" @click="setFilter('all')">
            全部
          </button>
          <button
            class="seg-btn"
            :class="{ on: filter === 'unlocked' }"
            @click="setFilter('unlocked')"
          >
            已解锁 {{ unlockedCount }}
          </button>
          <button class="seg-btn" :class="{ on: filter === 'locked' }" @click="setFilter('locked')">
            未解锁 {{ ACHIEVEMENTS.length - unlockedCount }}
          </button>
        </div>
      </header>

      <div ref="gridRef" class="wall">
        <button
          v-for="a in cards"
          :key="a.id"
          class="ach"
          :class="{ locked: !a.unlocked }"
          @click="tapCard(a, $event)"
        >
          <span class="ach-emoji">{{ a.unlocked ? a.emoji : '🔒' }}</span>
          <span class="ach-name">{{ a.name }}</span>
          <span class="ach-desc dim">{{ a.desc }}</span>
          <span v-if="a.unlocked" class="ach-date">{{ fmtDate(a.at) }} 达成</span>
        </button>
      </div>

      <p v-if="!cards.length" class="muted empty">这个分类下还没有成就，继续加油！</p>
    </section>

    <!-- 各星球掌握度 -->
    <section class="panel">
      <h3 class="panel-title">🪐 星球掌握度</h3>
      <ul class="mod-list">
        <li v-for="m in moduleRows" :key="m.id" class="mod-row" :style="{ '--c': m.color }">
          <span class="mod-emoji">{{ m.icon }}</span>
          <div class="mod-body">
            <div class="mod-top">
              <strong>{{ m.name }}</strong>
              <span class="dim tiny">
                {{ m.answered }} 题 · 正确率 {{ m.rate }}% · 掌握度 {{ m.mastery }}%
              </span>
            </div>
            <div class="mod-bar">
              <span class="mod-fill" :style="{ width: `${(m.answered / maxAnswered) * 100}%` }" />
            </div>
          </div>
          <span class="chip">⭐ {{ m.stars }}</span>
          <RouterLink :to="m.route" class="btn btn-ghost btn-sm">练习</RouterLink>
        </li>
      </ul>
    </section>

    <!-- 最近表现 -->
    <section v-if="spark" class="panel">
      <h3 class="panel-title">📈 最近 {{ spark.list.length }} 轮表现</h3>
      <p class="dim tiny">平均得分 {{ spark.avg }}%</p>
      <svg class="spark" :viewBox="`0 0 ${spark.w} ${spark.h}`" preserveAspectRatio="none">
        <defs>
          <linearGradient id="sparkFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#5ee7ff" stop-opacity="0.5" />
            <stop offset="100%" stop-color="#5ee7ff" stop-opacity="0" />
          </linearGradient>
        </defs>
        <polygon :points="spark.area" fill="url(#sparkFill)" />
        <polyline
          :points="spark.points"
          fill="none"
          stroke="#5ee7ff"
          stroke-width="2"
          stroke-linejoin="round"
          vector-effect="non-scaling-stroke"
        />
      </svg>
      <ul class="history">
        <li v-for="(h, i) in spark.list.slice().reverse()" :key="i" class="hist-row">
          <span class="chip">{{ MODULE_MAP[h.moduleId]?.icon ?? '🎯' }}</span>
          <span>{{ MODULE_MAP[h.moduleId]?.name ?? h.moduleId }}</span>
          <div class="spacer" />
          <span class="dim">{{ h.correct }}/{{ h.total }}</span>
          <strong :class="{ good: h.score >= 80 }">{{ h.score }}%</strong>
        </li>
      </ul>
    </section>

    <!-- 设置 -->
    <section class="panel settings">
      <h3 class="panel-title">⚙️ 设置</h3>
      <div class="set-row">
        <span>音效</span>
        <div class="spacer" />
        <button class="toggle" :class="{ on: settings.soundOn }" @click="toggleSound">
          <span class="knob" />
        </button>
      </div>
      <div class="set-row">
        <span>护眼模式<em class="dim tiny note">降低饱和度，长时间使用更舒服</em></span>
        <div class="spacer" />
        <button class="toggle" :class="{ on: settings.eyeCare }" @click="toggleEyeCare">
          <span class="knob" />
        </button>
      </div>
      <div class="set-row">
        <span>导出学习报告<em class="dim tiny note">JSON 格式，可备份或给家长查看</em></span>
        <div class="spacer" />
        <button class="btn btn-ghost btn-sm" @click="exportReport">📤 导出</button>
      </div>
      <div class="set-row">
        <span>清空全部进度</span>
        <div class="spacer" />
        <button v-if="!confirmReset" class="btn btn-ghost btn-sm" @click="confirmReset = true">
          🗑️ 重置
        </button>
        <template v-else>
          <button class="btn btn-ghost btn-sm" @click="confirmReset = false">取消</button>
          <button class="btn btn-sm danger" @click="doReset">确认清空</button>
        </template>
      </div>
      <p class="dim tiny">进度保存在本机浏览器里，不会上传到任何服务器。</p>

      <button class="btn btn-primary" @click="router.push('/')">🗺️ 回到学习地图</button>
    </section>
  </main>
</template>

<style scoped>
.profile {
  display: flex;
  gap: 20px;
  align-items: center;
  flex-wrap: wrap;
}

.avatar-block {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: none;
}

.avatar {
  font-size: 46px;
  width: 74px;
  height: 74px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 30%, rgba(255, 255, 255, 0.32), rgba(94, 231, 255, 0.22));
  border: 2px solid rgba(255, 255, 255, 0.24);
}

.profile-main {
  flex: 1;
  min-width: 260px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.name-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.pilot {
  font-size: 24px;
  font-weight: 900;
}

.name-input {
  padding: 8px 14px;
  border-radius: 999px;
  font-family: inherit;
  font-size: 16px;
  font-weight: 700;
  color: var(--ink);
  background: rgba(255, 255, 255, 0.09);
  border: 1px solid rgba(255, 255, 255, 0.24);
  outline: none;
  max-width: 200px;
}

.avatars {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.av-pick {
  width: 36px;
  height: 36px;
  font-size: 20px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid transparent;
  transition: all 0.14s ease;
}

.av-pick:hover {
  transform: scale(1.14);
}

.av-pick.on {
  border-color: var(--gold);
  background: rgba(255, 206, 77, 0.2);
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(84px, 1fr));
  gap: 8px;
}

.stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 4px;
  border-radius: var(--radius-s);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.stat .v {
  font-size: 19px;
  font-weight: 900;
}

.stat .k {
  font-size: 11px;
}

.xp-bar {
  height: 9px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  overflow: hidden;
}

.xp-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--cyan), var(--violet));
  transition: width 0.6s ease;
}

.tiny {
  font-size: 12px;
}

.ring-block {
  position: relative;
  display: grid;
  place-items: center;
  flex: none;
}

.ring-text {
  position: absolute;
  display: flex;
  align-items: baseline;
  gap: 3px;
}

.ring-text strong {
  font-size: 30px;
  font-weight: 900;
}

/* ---- 成就墙 ---- */

.wall-head {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

.seg {
  display: flex;
  gap: 4px;
  padding: 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
}

.seg-btn {
  padding: 6px 13px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  color: var(--ink-soft);
  transition: all 0.16s ease;
  white-space: nowrap;
}

.seg-btn.on {
  background: linear-gradient(135deg, var(--gold), var(--pink));
  color: #2a0f1e;
}

.wall {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(148px, 1fr));
  gap: 12px;
}

.ach {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 16px 10px;
  text-align: center;
  border-radius: var(--radius-m);
  background: linear-gradient(160deg, rgba(255, 206, 77, 0.18), rgba(255, 122, 198, 0.12));
  border: 2px solid rgba(255, 206, 77, 0.42);
  transition: transform 0.16s ease, box-shadow 0.16s ease;
}

.ach:hover {
  transform: translateY(-4px);
  box-shadow: 0 14px 30px rgba(255, 206, 77, 0.2);
}

.ach.locked {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.1);
  filter: grayscale(0.9);
  opacity: 0.65;
}

.ach-emoji {
  font-size: 38px;
  filter: drop-shadow(0 4px 10px rgba(0, 0, 0, 0.4));
}

.ach-name {
  font-size: 15px;
  font-weight: 900;
}

.ach-desc {
  font-size: 11px;
  line-height: 1.4;
}

.ach-date {
  font-size: 10px;
  font-weight: 800;
  color: var(--gold);
}

.empty {
  text-align: center;
  padding: 20px;
}

/* ---- 模块 ---- */

.mod-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.mod-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-s);
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.mod-emoji {
  font-size: 26px;
  flex: none;
}

.mod-body {
  flex: 1;
  min-width: 0;
}

.mod-top {
  display: flex;
  align-items: baseline;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 5px;
}

.mod-bar {
  height: 7px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  overflow: hidden;
}

.mod-fill {
  display: block;
  height: 100%;
  border-radius: 999px;
  background: var(--c);
  transition: width 0.6s ease;
}

/* ---- 曲线 ---- */

.spark {
  width: 100%;
  height: 76px;
  margin: 12px 0;
}

.history {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.hist-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: var(--radius-s);
  background: rgba(255, 255, 255, 0.04);
  font-size: 13px;
}

.hist-row strong.good {
  color: var(--green);
}

/* ---- 设置 ---- */

.settings {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: stretch;
}

.set-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 15px;
  font-weight: 700;
}

.note {
  display: block;
  font-style: normal;
  font-weight: 600;
  margin-top: 2px;
}

.toggle {
  width: 52px;
  height: 30px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.2);
  position: relative;
  transition: background 0.2s ease;
}

.toggle.on {
  background: linear-gradient(135deg, var(--green), var(--cyan));
}

.knob {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #fff;
  transition: transform 0.2s ease;
}

.toggle.on .knob {
  transform: translateX(22px);
}

.danger {
  background: rgba(255, 107, 125, 0.22);
  border-color: var(--red);
  color: #ffd3d9;
}

@media (max-width: 560px) {
  .ring-block {
    order: -1;
  }
}
</style>
