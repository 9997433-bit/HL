<script setup>
import { computed, ref } from 'vue'
import { useProgressStore } from '@/stores/progress.js'
import { sound } from '@/utils/sound.js'

const TOTAL = 10
const progress = useProgressStore()
const beads = ref([])
const known = ref(6)
const round = ref(1)
const solved = ref(false)
const lastChecked = ref('')
const message = ref('移动弹珠，让左舱数量和任务卡一样。')
const earned = ref(0)

const leftBeads = computed(() => beads.value.filter((bead) => bead.side === 'left'))
const rightBeads = computed(() => beads.value.filter((bead) => bead.side === 'right'))
const leftCount = computed(() => leftBeads.value.length)
const rightCount = computed(() => rightBeads.value.length)
const equation = computed(() => `${leftCount.value} + ${rightCount.value} = ${TOTAL}`)
const targetEquation = computed(() => `${known.value} + ? = ${TOTAL}`)

function makeBeads(left = 5) {
  return Array.from({ length: TOTAL }, (_, index) => ({
    id: index + 1,
    side: index < left ? 'left' : 'right',
    color: index % 2 ? 'pink' : 'cyan',
  }))
}

function move(bead, side) {
  if (solved.value || bead.side === side) return
  bead.side = side
  lastChecked.value = ''
  message.value = `${leftCount.value} 和 ${rightCount.value} 合起来仍然是 10。`
  sound.click()
}

function moveOne(from, to) {
  const bead = beads.value.find((item) => item.side === from)
  if (bead) move(bead, to)
}

function distributionKey() {
  return beads.value.map((bead) => bead.side[0]).join('')
}

function check() {
  if (solved.value) return
  const signature = distributionKey()
  if (signature === lastChecked.value) {
    message.value = '先移动一颗弹珠，再检查一次。'
    return
  }
  lastChecked.value = signature
  const correct = leftCount.value === known.value
  progress.recordAnswer('counting', correct, {
    skill: 'compose-ten',
    stars: correct ? 2 : 0,
    xp: correct ? 16 : 2,
  })
  if (correct) {
    solved.value = true
    earned.value += 2
    message.value = `正确！${known.value} 和 ${TOTAL - known.value} 合成 10。`
    sound.correct()
  } else {
    const delta = known.value - leftCount.value
    message.value =
      delta > 0
        ? `还差 ${delta} 颗。请从右舱移 ${delta} 颗到左舱。`
        : `左舱多了 ${Math.abs(delta)} 颗，请移回右舱。`
    sound.wrong()
  }
}

function nextRound() {
  round.value += 1
  known.value = ((known.value + 3) % 9) + 1
  let start = ((known.value + 4) % 9) + 1
  if (start === known.value) start = known.value === 9 ? 2 : known.value + 1
  beads.value = makeBeads(start)
  solved.value = false
  lastChecked.value = ''
  message.value = '新任务：移动弹珠，让左舱数量和任务卡一样。'
  sound.click()
}

function reset() {
  beads.value = makeBeads(5)
  known.value = 6
  round.value = 1
  solved.value = false
  lastChecked.value = ''
  earned.value = 0
  message.value = '移动弹珠，让左舱数量和任务卡一样。'
}

reset()
</script>

<template>
  <main class="page stack" data-skill="compose-ten">
    <section class="card hero">
      <div>
        <p class="kicker">分与合教具</p>
        <h2>十颗弹珠 · 两舱实验</h2>
        <p class="muted">点一颗弹珠就能把它移到另一边。数量虽然分法不同，合起来总是 10。</p>
      </div>
      <div class="round-chip">
        <strong>第 {{ round }} 关</strong>
        <span>已得 {{ earned }} ⭐</span>
      </div>
    </section>

    <section class="card mission">
      <span class="mission-icon">🎯</span>
      <div>
        <span class="dim">本关任务</span>
        <strong class="target-equation" :data-known="known">{{ targetEquation }}</strong>
        <p>左舱放 {{ known }} 颗，看看右舱应该有几颗。</p>
      </div>
    </section>

    <section class="card manipulative">
      <div class="ten-frame" aria-label="十格框">
        <span
          v-for="bead in beads"
          :key="`frame-${bead.id}`"
          class="frame-cell"
          :class="bead.side"
        >
          <i />
        </span>
      </div>

      <div class="split-board">
        <section class="bay left-bay" aria-label="左舱">
          <header>
            <strong>左舱</strong>
            <span class="bay-count" data-compose-left>{{ leftCount }}</span>
          </header>
          <div class="bead-box">
            <button
              v-for="bead in leftBeads"
              :key="bead.id"
              class="bead"
              :class="bead.color"
              :disabled="solved"
              data-bead-side="left"
              :aria-label="`把第 ${bead.id} 颗弹珠移到右舱`"
              @click="move(bead, 'right')"
            >
              {{ bead.id }}
            </button>
          </div>
          <button class="move-btn" :disabled="solved || !leftCount" @click="moveOne('left', 'right')">
            移一颗到右边 →
          </button>
        </section>

        <div class="plus" aria-hidden="true">+</div>

        <section class="bay right-bay" aria-label="右舱">
          <header>
            <strong>右舱</strong>
            <span class="bay-count" data-compose-right>{{ rightCount }}</span>
          </header>
          <div class="bead-box">
            <button
              v-for="bead in rightBeads"
              :key="bead.id"
              class="bead"
              :class="bead.color"
              :disabled="solved"
              data-bead-side="right"
              :aria-label="`把第 ${bead.id} 颗弹珠移到左舱`"
              @click="move(bead, 'left')"
            >
              {{ bead.id }}
            </button>
          </div>
          <button class="move-btn" :disabled="solved || !rightCount" @click="moveOne('right', 'left')">
            ← 移一颗到左边
          </button>
        </section>
      </div>

      <div class="equation" aria-live="polite">
        <span>{{ leftCount }}</span>
        <b>+</b>
        <span>{{ rightCount }}</span>
        <b>=</b>
        <span class="total">10</span>
      </div>

      <p class="message" :class="{ success: solved }" aria-live="polite">{{ message }}</p>

      <div class="actions">
        <button class="btn btn--ghost" @click="reset">重新开始</button>
        <button
          v-if="!solved"
          class="btn btn--primary btn--lg"
          data-compose-check
          @click="check"
        >
          检查 {{ equation }}
        </button>
        <button v-else class="btn btn--primary btn--lg" data-compose-next @click="nextRound">
          下一种分法 →
        </button>
      </div>
    </section>

    <section class="card fact">
      <strong>💡 10 的好朋友</strong>
      <div class="friend-pairs">
        <span v-for="n in 6" :key="n">{{ n - 1 }} + {{ 11 - n }}</span>
      </div>
    </section>
  </main>
</template>

<style scoped>
.hero {
  display: flex;
  align-items: center;
  gap: 18px;
}

.hero > div:first-child {
  flex: 1;
}

.hero h2 {
  margin: 3px 0 6px;
  font-size: clamp(24px, 5vw, 32px);
}

.kicker {
  color: var(--brand);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 1.5px;
}

.round-chip {
  flex: none;
  padding: 11px 15px;
  display: grid;
  justify-items: center;
  border-radius: var(--radius-md);
  background: rgba(255, 206, 77, 0.1);
  border: 1px solid rgba(255, 206, 77, 0.32);
}

.round-chip strong {
  color: var(--star);
}

.round-chip span {
  color: var(--text-soft);
  font-size: 12px;
}

.mission {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 14px;
  text-align: center;
}

.mission-icon {
  font-size: 38px;
}

.mission > div {
  display: grid;
  gap: 2px;
}

.target-equation {
  color: var(--star);
  font-size: 28px;
}

.manipulative {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.ten-frame {
  width: min(100%, 540px);
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  border: 3px solid rgba(220, 230, 255, 0.55);
  border-radius: 12px;
  overflow: hidden;
}

.frame-cell {
  min-height: 54px;
  display: grid;
  place-items: center;
  border: 1px solid rgba(220, 230, 255, 0.22);
  background: rgba(255, 255, 255, 0.035);
}

.frame-cell i {
  width: 31px;
  height: 31px;
  border-radius: 50%;
}

.frame-cell.left i {
  background: var(--brand);
  box-shadow: 0 0 14px rgba(94, 231, 255, 0.48);
}

.frame-cell.right i {
  background: var(--neon-pink);
  box-shadow: 0 0 14px rgba(255, 122, 198, 0.48);
}

.split-board {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 14px;
}

.bay {
  min-height: 220px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  border-radius: var(--radius-md);
  border: 2px dashed rgba(255, 255, 255, 0.2);
}

.left-bay {
  background: rgba(94, 231, 255, 0.08);
  border-color: rgba(94, 231, 255, 0.36);
}

.right-bay {
  background: rgba(255, 122, 198, 0.08);
  border-color: rgba(255, 122, 198, 0.36);
}

.bay header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.bay-count {
  width: 42px;
  height: 42px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  font-size: 23px;
  font-weight: 900;
}

.bead-box {
  flex: 1;
  display: flex;
  align-content: flex-start;
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px;
}

.bead {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  color: #071225;
  font-size: 13px;
  font-weight: 900;
  box-shadow: inset -5px -6px 10px rgba(0, 0, 0, 0.2), 0 7px 14px rgba(0, 0, 0, 0.28);
  transition: transform 0.15s ease;
}

.bead:hover:not(:disabled) {
  transform: translateY(-4px) scale(1.06);
}

.bead.cyan {
  background: radial-gradient(circle at 32% 28%, #d7fbff, var(--brand) 45%, #3999b2);
}

.bead.pink {
  background: radial-gradient(circle at 32% 28%, #ffe1f2, var(--neon-pink) 45%, #b44f88);
}

.move-btn {
  padding: 7px;
  border-radius: 999px;
  color: var(--text);
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.06);
  font-size: 12px;
  font-weight: 800;
}

.plus {
  color: var(--star);
  font-size: 38px;
  font-weight: 900;
}

.equation {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.equation span {
  min-width: 60px;
  padding: 8px 14px;
  text-align: center;
  border-radius: var(--radius-sm);
  color: var(--brand);
  background: rgba(94, 231, 255, 0.1);
  border: 2px solid rgba(94, 231, 255, 0.35);
  font-size: 34px;
  font-weight: 900;
}

.equation .total {
  color: var(--star);
  border-color: rgba(255, 206, 77, 0.42);
  background: rgba(255, 206, 77, 0.1);
}

.equation b {
  font-size: 28px;
}

.message {
  min-height: 45px;
  padding: 11px 14px;
  border-radius: var(--radius-sm);
  text-align: center;
  color: var(--text);
  background: rgba(155, 140, 255, 0.1);
  border: 1px solid rgba(155, 140, 255, 0.3);
  font-weight: 800;
}

.message.success {
  color: var(--success);
  background: rgba(85, 230, 165, 0.1);
  border-color: rgba(85, 230, 165, 0.35);
}

.actions {
  display: flex;
  justify-content: center;
  gap: 10px;
  flex-wrap: wrap;
}

.fact {
  display: flex;
  align-items: center;
  gap: 14px;
}

.friend-pairs {
  display: flex;
  gap: 7px;
  flex-wrap: wrap;
}

.friend-pairs span {
  padding: 5px 9px;
  border-radius: 999px;
  color: var(--text);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  font-size: 12px;
  font-weight: 800;
}

@media (max-width: 660px) {
  .split-board {
    grid-template-columns: 1fr;
  }

  .plus {
    justify-self: center;
  }

  .bay {
    min-height: 180px;
  }

  .fact,
  .hero {
    align-items: flex-start;
  }
}
</style>
