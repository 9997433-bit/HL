<script setup>
import { computed, onMounted, ref } from 'vue'
import gsap from 'gsap'
import { MODULES } from '@/data/modules'
import { ACHIEVEMENTS } from '@/data/achievements'
import { useProgressStore } from '@/stores/progress'
import { useFeedback } from '@/composables/useFeedback'
import MascotBot from '@/components/MascotBot.vue'

const progress = useProgressStore()
const { enter } = useFeedback()
const confirmReset = ref(false)

const unlockedIds = computed(() => new Set(progress.unlockedAchievements.map((a) => a.id)))
const unlockedCount = computed(() => unlockedIds.value.size)
const totalCount = ACHIEVEMENTS.length

const moduleRows = computed(() =>
  MODULES.map((m) => {
    const s = progress.moduleStat(m.id)
    return {
      ...m,
      ...s,
      rate: s.answered ? Math.round((s.correct / s.answered) * 100) : 0,
    }
  }),
)

const history = computed(() => progress.state.history.slice(0, 8))

const fmtDate = (ts) =>
  new Date(ts).toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })

const moduleName = (id) => MODULES.find((m) => m.id === id)?.name ?? id

function doReset() {
  progress.resetAll()
  confirmReset.value = false
}

onMounted(() => {
  enter('.ach-card', { stagger: 0.03 })
  gsap.fromTo(
    '.xp-fill',
    { width: '0%' },
    { width: `${Math.round(progress.levelProgress * 100)}%`, duration: 0.9, ease: 'power2.out' },
  )
})
</script>

<template>
  <main class="page stack">
    <section class="panel pilot">
      <MascotBot mood="happy" :size="96" />
      <div class="pilot-info">
        <input
          v-model="progress.state.pilotName"
          class="name-input"
          maxlength="12"
          aria-label="宇航员昵称"
        />
        <p class="dim">
          等级 {{ progress.state.level }} · 经验 {{ progress.state.xp }}/{{ progress.xpToNext }}
        </p>
        <div class="xp-bar"><div class="xp-fill" /></div>
        <div class="pilot-stats">
          <span class="chip">⭐ {{ progress.state.stars }} 星星</span>
          <span class="chip">📘 {{ progress.state.totalAnswered }} 题</span>
          <span class="chip">🎯 正确率 {{ progress.accuracy }}%</span>
          <span class="chip">🔥 最高 {{ progress.state.bestStreak }} 连击</span>
        </div>
      </div>
    </section>

    <section class="panel">
      <div class="row">
        <h3 class="panel-title">🏆 成就墙</h3>
        <span class="chip chip-on">{{ unlockedCount }} / {{ totalCount }}</span>
      </div>
      <div class="ach-grid">
        <div
          v-for="a in ACHIEVEMENTS"
          :key="a.id"
          class="ach-card"
          :class="{ locked: !unlockedIds.has(a.id) }"
        >
          <span class="ach-emoji">{{ unlockedIds.has(a.id) ? a.emoji : '🔒' }}</span>
          <strong class="ach-name">{{ a.name }}</strong>
          <span class="ach-desc dim">{{ a.desc }}</span>
        </div>
      </div>
    </section>

    <section class="panel">
      <h3 class="panel-title">📊 各星球学习情况</h3>
      <div class="mod-table">
        <div v-for="m in moduleRows" :key="m.id" class="mod-row">
          <span class="mod-emoji">{{ m.emoji }}</span>
          <div class="mod-name-col">
            <strong>{{ m.name }}</strong>
            <span class="dim tiny">{{ m.subtitle }}</span>
          </div>
          <div class="mod-bar">
            <div
              class="mod-bar-fill"
              :style="{ width: `${m.rate}%`, background: `linear-gradient(90deg, ${m.color}, ${m.accent})` }"
            />
          </div>
          <span class="mod-num">{{ m.correct }}/{{ m.answered }}</span>
          <span class="mod-num dim">{{ m.rate }}%</span>
        </div>
      </div>
    </section>

    <section class="panel">
      <h3 class="panel-title">🕘 最近练习</h3>
      <ul v-if="history.length" class="history">
        <li v-for="(h, i) in history" :key="i" class="hist-row">
          <span class="chip">{{ moduleName(h.moduleId) }}</span>
          <span class="muted">{{ h.correct }}/{{ h.total }} 正确</span>
          <span class="score" :class="{ good: h.score >= 80 }">{{ h.score }}%</span>
          <span class="spacer" />
          <span class="dim tiny">{{ fmtDate(h.at) }}</span>
        </li>
      </ul>
      <p v-else class="dim">还没有练习记录，去地图上选一个星球开始吧！</p>
    </section>

    <section class="panel settings">
      <h3 class="panel-title">⚙️ 设置</h3>
      <label class="switch-row">
        <input v-model="progress.state.settings.sound" type="checkbox" />
        <span>音效</span>
      </label>
      <div class="danger">
        <button v-if="!confirmReset" class="btn btn-ghost btn-sm" @click="confirmReset = true">
          🗑️ 清空全部进度
        </button>
        <template v-else>
          <span class="muted">确定要清空所有星星和成就吗？</span>
          <button class="btn btn-sm" style="border-color: var(--red); color: var(--red)" @click="doReset">
            确认清空
          </button>
          <button class="btn btn-ghost btn-sm" @click="confirmReset = false">取消</button>
        </template>
      </div>
    </section>
  </main>
</template>

<style scoped>
.pilot {
  display: flex;
  align-items: center;
  gap: 20px;
}

.pilot-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.name-input {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.16);
  border-radius: 14px;
  padding: 8px 14px;
  font-size: 22px;
  font-weight: 900;
  font-family: inherit;
  color: var(--ink);
  max-width: 260px;
}

.name-input:focus {
  outline: 2px solid var(--cyan);
}

.xp-bar {
  height: 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  overflow: hidden;
}

.xp-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--cyan), var(--violet));
  border-radius: 999px;
}

.pilot-stats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.ach-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
  margin-top: 14px;
}

.ach-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  text-align: center;
  padding: 14px 10px;
  border-radius: var(--radius-m);
  background: linear-gradient(150deg, rgba(255, 206, 77, 0.16), rgba(255, 122, 198, 0.12));
  border: 1px solid rgba(255, 206, 77, 0.35);
}

.ach-card.locked {
  background: rgba(255, 255, 255, 0.04);
  border-color: rgba(255, 255, 255, 0.1);
  filter: grayscale(0.7);
  opacity: 0.65;
}

.ach-emoji {
  font-size: 32px;
}

.ach-name {
  font-size: 15px;
}

.ach-desc {
  font-size: 12px;
  line-height: 1.4;
}

.mod-table {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.mod-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.mod-emoji {
  font-size: 24px;
  width: 34px;
  text-align: center;
  flex: none;
}

.mod-name-col {
  display: flex;
  flex-direction: column;
  width: 140px;
  flex: none;
}

.tiny {
  font-size: 11px;
}

.mod-bar {
  flex: 1;
  height: 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  overflow: hidden;
  min-width: 60px;
}

.mod-bar-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.6s ease;
}

.mod-num {
  width: 56px;
  text-align: right;
  font-weight: 800;
  font-size: 14px;
  flex: none;
}

.history {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}

.hist-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
  font-size: 14px;
  flex-wrap: wrap;
}

.score {
  font-weight: 900;
  color: var(--gold);
}

.score.good {
  color: var(--green);
}

.settings {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.switch-row {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  cursor: pointer;
}

.switch-row input {
  width: 20px;
  height: 20px;
  accent-color: var(--cyan);
}

.danger {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

@media (max-width: 640px) {
  .pilot {
    flex-direction: column;
    text-align: center;
  }

  .mod-name-col {
    width: 96px;
  }
}
</style>
