<script setup>
/**
 * 字迷宫。
 *
 * 玩法：迷宫里散着几个字，题目念一个字，走过去踩中它。踩错的字会消失，
 * 目标字永远留在原地——迷宫游戏最怕的是「走了半天发现这一关没法过」，
 * 所以判错只扣分不封路。
 *
 * 迷宫用递归回溯法现挖，天生是连通的完美迷宫，随机出多少局都保证走得通。
 *
 * 键盘是这款游戏的第一操作方式：迷宫区自己可聚焦，方向键 / WASD 直接走；
 * 触屏用下面那圈方向按钮，两条通道走的是同一个 move()。
 * 读屏用户看不到格子，所以每走一步都播报「你在第几行第几列 + 目标字在哪个方向」，
 * 这是把空间信息翻译成语言的唯一通道，不能省。
 */
import { computed, onBeforeUnmount, ref } from 'vue'
import StarBurst from '@/components/StarBurst.vue'
import CelebrationOverlay from '@/components/CelebrationOverlay.vue'
import VoiceNotice from '@/components/VoiceNotice.vue'
import { useCharPool } from '@/composables/useCharPool.js'
import { useProgressStore } from '@/stores/progress.js'
import { useSettingsStore } from '@/stores/settings.js'
import { isSpeechSupported, speak, stopSpeaking } from '@/utils/speech.js'
import { pick, sample, shuffle } from '@/utils/random.js'
import { sfx } from '@/utils/sfx.js'

/** 迷宫边长必须是奇数：偶数格挖不出「墙—路—墙」的规整通道。 */
const COLS = 9
const ROWS = 9
const ROUNDS = 5
/** 每一关摆几个字（1 个目标 + 若干干扰）。 */
const TILES = 4

const progress = useProgressStore()
const settings = useSettingsStore()
const { pool, usingFallback, drawPool } = useCharPool(TILES)

const speechOk = isSpeechSupported()

const burstRef = ref(null)
const stageRef = ref(null)

const phase = ref('intro') // intro | playing | done
const round = ref(0)
const score = ref(0)
const misses = ref(0)
const steps = ref(0)
const walls = ref([])
const player = ref({ x: 1, y: 1 })
const tiles = ref([])
const target = ref(null)
const celebrating = ref(false)
const announcement = ref('')

function announce(text) {
  // 同一句话写两次读屏不会再念，补个零宽空格逼它重播
  announcement.value = announcement.value === text ? `${text}\u200b` : text
}

/* ------------------------------------------------------------ 迷宫生成 */

/**
 * 递归回溯：从 (1,1) 出发，每次朝一个还没挖过的「隔一格」邻居打通，
 * 走不动就回退。结果是一张所有通路互相可达、且没有环的完美迷宫。
 */
function buildMaze() {
  const grid = Array.from({ length: ROWS }, () => Array(COLS).fill(true))
  const stack = [[1, 1]]
  grid[1][1] = false

  while (stack.length) {
    const [x, y] = stack[stack.length - 1]
    const next = shuffle([
      [2, 0],
      [-2, 0],
      [0, 2],
      [0, -2]
    ])
      .map(([dx, dy]) => [x + dx, y + dy])
      .find(([nx, ny]) => nx > 0 && ny > 0 && nx < COLS - 1 && ny < ROWS - 1 && grid[ny][nx])

    if (!next) {
      stack.pop()
      continue
    }
    const [nx, ny] = next
    grid[(y + ny) / 2][(x + nx) / 2] = false
    grid[ny][nx] = false
    stack.push([nx, ny])
  }
  return grid
}

const openCells = computed(() => {
  const out = []
  walls.value.forEach((row, y) =>
    row.forEach((isWall, x) => {
      if (!isWall) out.push({ x, y })
    })
  )
  return out
})

/* -------------------------------------------------------------- 出题 */

function placeTiles() {
  const { due, rest, all } = drawPool()
  const preferred = due.length && Math.random() < 0.6 ? due : all
  const chosen = pick(preferred) ?? all[0]
  target.value = chosen

  const distractors = sample(
    (rest.length >= TILES ? rest : all).filter((c) => c.char !== chosen.char),
    TILES - 1
  )

  // 字要摆得离孩子远一点，不然一步就踩到，迷宫就白挖了
  const far = openCells.value.filter(
    ({ x, y }) => Math.abs(x - player.value.x) + Math.abs(y - player.value.y) >= 4
  )
  const spots = sample(far.length >= TILES ? far : openCells.value, TILES)

  tiles.value = shuffle([chosen, ...distractors])
    .slice(0, spots.length)
    .map((c, i) => ({ ...c, x: spots[i].x, y: spots[i].y }))

  // 洗牌后目标字可能被 slice 掉，兜底把它塞回第一格
  if (!tiles.value.some((t) => t.char === chosen.char) && tiles.value.length) {
    tiles.value[0] = { ...chosen, x: tiles.value[0].x, y: tiles.value[0].y }
  }
}

function nextRound() {
  round.value += 1
  placeTiles()
  announce(
    `第 ${round.value} 关，共 ${ROUNDS} 关。找到「${target.value.char}」，读作 ${target.value.pinyin}。` +
      `${describePosition()}用方向键走过去踩住它。`
  )
  playPrompt()
}

function playPrompt() {
  if (target.value) speak(target.value.char, { rate: settings.speechRate })
}

function replay() {
  sfx.tap()
  playPrompt()
  announce(`再听一次：「${target.value?.char}」，${target.value?.pinyin}。${describePosition()}`)
}

/* -------------------------------------------------------------- 走位 */

const targetTile = computed(() =>
  tiles.value.find((t) => t.char === target.value?.char) ?? null
)

/** 把「目标在哪儿」翻译成一句话，读屏用户全靠它定位。 */
function describePosition() {
  const tile = targetTile.value
  if (!tile) return ''
  const dx = tile.x - player.value.x
  const dy = tile.y - player.value.y
  if (!dx && !dy) return '你正站在它上面。'
  const parts = []
  if (dy < 0) parts.push(`上边 ${-dy} 格`)
  if (dy > 0) parts.push(`下边 ${dy} 格`)
  if (dx < 0) parts.push(`左边 ${-dx} 格`)
  if (dx > 0) parts.push(`右边 ${dx} 格`)
  return `目标字在${parts.join('、')}。`
}

function move(dx, dy) {
  if (phase.value !== 'playing') return
  const nx = player.value.x + dx
  const ny = player.value.y + dy
  if (nx < 0 || ny < 0 || nx >= COLS || ny >= ROWS || walls.value[ny][nx]) {
    sfx.tap()
    announce(`那边是墙，走不过去。${describePosition()}`)
    return
  }

  player.value = { x: nx, y: ny }
  steps.value += 1

  const hit = tiles.value.find((t) => t.x === nx && t.y === ny)
  if (!hit) {
    announce(`第 ${player.value.y} 行第 ${player.value.x} 列。${describePosition()}`)
    return
  }
  if (hit.char === target.value?.char) collect(hit)
  else stumble(hit)
}

function collect(tile) {
  score.value += 1
  sfx.correct()
  burstRef.value?.burst()
  progress.recordAnswer(tile.char, true)
  announce(`踩中了！这就是「${tile.char}」，读作 ${tile.pinyin}。已经找到 ${score.value} 个字。`)
  tiles.value = []
  if (round.value >= ROUNDS) window.setTimeout(finish, 700)
  else window.setTimeout(nextRound, 700)
}

function stumble(tile) {
  misses.value += 1
  sfx.wrong()
  if (target.value) progress.recordAnswer(target.value.char, false)
  tiles.value = tiles.value.filter((t) => t !== tile)
  announce(
    `这个是「${tile.char}」，读作 ${tile.pinyin}，不是要找的字。` +
      `再找找「${target.value?.char}」。${describePosition()}`
  )
}

const KEYS = {
  ArrowUp: [0, -1],
  ArrowDown: [0, 1],
  ArrowLeft: [-1, 0],
  ArrowRight: [1, 0],
  w: [0, -1],
  s: [0, 1],
  a: [-1, 0],
  d: [1, 0]
}

function onKeydown(event) {
  const step = KEYS[event.key] ?? KEYS[event.key?.toLowerCase?.()]
  if (!step) return
  event.preventDefault()
  move(step[0], step[1])
}

/* -------------------------------------------------------------- 流程 */

function start() {
  sfx.tap()
  celebrating.value = false
  phase.value = 'playing'
  round.value = 0
  score.value = 0
  misses.value = 0
  steps.value = 0
  walls.value = buildMaze()
  player.value = { x: 1, y: 1 }
  nextRound()
  // 开局就把焦点放进迷宫，键盘用户不用先按一堆 Tab 才能走第一步
  window.setTimeout(() => stageRef.value?.focus(), 0)
}

function finish() {
  phase.value = 'done'
  announce(
    `迷宫走完了，找到 ${score.value} / ${ROUNDS} 个字，走了 ${steps.value} 步，踩错 ${misses.value} 次。`
  )
  if (score.value >= ROUNDS) celebrating.value = true
  else sfx.tap()
}

const earnedStars = computed(() => {
  if (misses.value === 0) return 3
  return misses.value <= 2 ? 2 : 1
})

const stageLabel = computed(
  () =>
    `字迷宫。用方向键或 W A S D 走一步，也可以点下面的方向按钮。` +
    `现在要找「${target.value?.char ?? ''}」。${describePosition()}`
)

/** 模板里按 [y][x] 取太啰嗦，先摊平成一维。 */
const cells = computed(() => {
  const out = []
  for (let y = 0; y < ROWS; y += 1) {
    for (let x = 0; x < COLS; x += 1) {
      const tile = tiles.value.find((t) => t.x === x && t.y === y)
      out.push({
        x,
        y,
        wall: Boolean(walls.value[y]?.[x]),
        char: tile?.char ?? '',
        isPlayer: player.value.x === x && player.value.y === y
      })
    }
  }
  return out
})

onBeforeUnmount(stopSpeaking)
</script>

<template>
  <div class="page maze-game">
    <StarBurst ref="burstRef" />
    <p class="sr-only" role="status" aria-live="polite" aria-atomic="true">{{ announcement }}</p>

    <!-- 开始页 -->
    <section v-if="phase === 'intro'" class="card intro">
      <div class="intro__emoji" aria-hidden="true">🧭</div>
      <h2 class="intro__title">字迷宫</h2>
      <p class="intro__desc">
        听清楚要找哪个字，用方向键在迷宫里走过去踩住它。<br />
        一共 {{ ROUNDS }} 关，全部找到就通关 🏁
      </p>

      <VoiceNotice fallback="要找的字会大大地写在迷宫上方，可以请家长读给你听。" />

      <p v-if="usingFallback" class="warn">
        💡 还没学够 {{ TILES }} 个字，这一局先用课程最前面的字来练习。
      </p>
      <p v-else class="muted">这一局从你学过的 {{ pool.length }} 个字里出题。</p>

      <button class="btn btn--primary btn--lg btn--block" type="button" @click="start">
        进迷宫 🚀
      </button>
    </section>

    <!-- 游戏中 -->
    <template v-else-if="phase === 'playing'">
      <section class="hud card card--flat">
        <div class="hud__row">
          <span class="pill">第 {{ round }} / {{ ROUNDS }} 关</span>
          <span class="pill pill--accent">⭐ {{ score }}</span>
          <span class="pill">👣 {{ steps }} 步</span>
        </div>
      </section>

      <section class="quest card">
        <p class="quest__label">要找的字</p>
        <p class="quest__char">{{ target?.char }}</p>
        <p class="quest__pinyin">{{ target?.pinyin }}</p>
        <button class="btn btn--ghost btn--sm" type="button" @click="replay">🔊 再听一次</button>
      </section>

      <div
        ref="stageRef"
        class="maze__stage"
        role="group"
        tabindex="0"
        :aria-label="stageLabel"
        @keydown="onKeydown"
      >
        <div
          class="maze"
          :class="{ 'maze--quiet': settings.reduceMotion }"
          :data-cols="COLS"
          :data-rows="ROWS"
          :style="{ '--maze-cols': COLS }"
          aria-hidden="true"
        >
          <div
            v-for="cell in cells"
            :key="`${cell.x}-${cell.y}`"
            class="maze__cell"
            :class="{ 'is-wall': cell.wall, 'is-player': cell.isPlayer }"
            :data-x="cell.x"
            :data-y="cell.y"
            :data-wall="cell.wall"
            :data-char="cell.char || undefined"
            :data-player="cell.isPlayer || undefined"
          >
            <span v-if="cell.isPlayer" class="maze__hero">🐣</span>
            <span v-else-if="cell.char" class="maze__tile">{{ cell.char }}</span>
          </div>
        </div>
      </div>

      <div class="dpad">
        <button class="dpad__btn dpad__btn--up" type="button" @click="move(0, -1)">
          <span aria-hidden="true">⬆️</span><span class="dpad__text">上</span>
        </button>
        <button class="dpad__btn dpad__btn--left" type="button" @click="move(-1, 0)">
          <span aria-hidden="true">⬅️</span><span class="dpad__text">左</span>
        </button>
        <button class="dpad__btn dpad__btn--right" type="button" @click="move(1, 0)">
          <span aria-hidden="true">➡️</span><span class="dpad__text">右</span>
        </button>
        <button class="dpad__btn dpad__btn--down" type="button" @click="move(0, 1)">
          <span aria-hidden="true">⬇️</span><span class="dpad__text">下</span>
        </button>
      </div>

      <p class="muted maze__tip">键盘：方向键或 W A S D 走一步。</p>
    </template>

    <!-- 结算 -->
    <section v-else class="card intro">
      <div class="intro__emoji" aria-hidden="true">{{ score >= ROUNDS ? '🏆' : '💪' }}</div>
      <h2 class="intro__title">{{ score >= ROUNDS ? '全部找到啦！' : '再走一次会更快' }}</h2>
      <p class="intro__desc">
        这一局找到 <strong>{{ score }}</strong> / {{ ROUNDS }} 个字，走了 {{ steps }} 步，
        踩错 {{ misses }} 次。
      </p>
      <div class="intro__actions">
        <button class="btn btn--primary btn--lg" type="button" @click="start">再走一局 🔁</button>
        <RouterLink class="btn btn--ghost btn--lg" to="/games" @click="sfx.tap()">
          换个游戏 🎲
        </RouterLink>
      </div>
    </section>

    <CelebrationOverlay
      :open="celebrating"
      emoji="🧭"
      title="字迷宫通关！"
      :subtitle="`找到 ${score} / ${ROUNDS} 个字`"
      :stars="earnedStars"
      :reduce-motion="settings.reduceMotion"
      @done="celebrating = false"
    />
  </div>
</template>

<style scoped>
.intro {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--gap-md);
  text-align: center;
}

.intro__emoji {
  font-size: 3.4rem;
  line-height: 1;
}

.intro__title {
  font-size: 1.6rem;
  font-weight: 800;
  color: var(--text-strong);
}

.intro__desc {
  line-height: 1.9;
  color: var(--text);
}

.intro__actions {
  display: flex;
  gap: var(--gap-sm);
  flex-wrap: wrap;
  justify-content: center;
}

.warn {
  width: 100%;
  padding: 10px 14px;
  border-radius: var(--radius-md);
  background: var(--brand-soft);
  color: var(--text-strong);
  font-size: 0.85rem;
  line-height: 1.7;
}

.hud__row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.quest {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  text-align: center;
}

.quest__label {
  font-size: 0.8rem;
  color: var(--text-soft);
}

.quest__char {
  font-size: 3rem;
  line-height: 1.1;
  font-weight: 700;
  color: var(--text-strong);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

.quest__pinyin {
  color: var(--text-soft);
}

/* ------------------------------------------------------------------ 迷宫 */

.maze__stage {
  border-radius: var(--radius-lg);
  padding: 6px;
}

.maze__stage:focus-visible {
  outline: 3px solid var(--brand);
  outline-offset: 2px;
}

.maze {
  display: grid;
  grid-template-columns: repeat(var(--maze-cols), 1fr);
  gap: 2px;
  padding: var(--gap-sm);
  border-radius: var(--radius-lg);
  background: var(--surface-sunken);
}

.maze__cell {
  position: relative;
  display: grid;
  place-items: center;
  aspect-ratio: 1;
  border-radius: 6px;
  background: var(--surface-strong);
}

.maze__cell.is-wall {
  background: color-mix(in srgb, var(--stroke-ink) 55%, var(--surface-sunken));
}

.maze__cell.is-player {
  background: var(--brand-soft);
}

.maze__hero {
  font-size: clamp(0.9rem, 4.4vw, 1.5rem);
  line-height: 1;
  transition: transform var(--dur-fast) var(--ease-pop);
}

.maze--quiet .maze__hero {
  transition: none;
}

.maze__tile {
  font-size: clamp(0.85rem, 4vw, 1.4rem);
  line-height: 1;
  font-weight: 700;
  color: var(--text-strong);
  font-family: 'Kaiti SC', 'STKaiti', 'KaiTi', 'PingFang SC', serif;
}

.maze__tip {
  text-align: center;
  font-size: 0.8rem;
}

/* --------------------------------------------------------------- 方向键 */

.dpad {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-template-areas:
    '. up .'
    'left . right'
    '. down .';
  gap: var(--gap-sm);
  max-width: 260px;
  margin: 0 auto;
}

.dpad__btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  min-height: var(--tap-min);
  border-radius: var(--radius-md);
  background: var(--surface-strong);
  color: var(--text-strong);
  box-shadow: var(--shadow-sm);
  font-size: 1.3rem;
}

.dpad__btn:active {
  transform: scale(0.94);
}

.dpad__text {
  font-size: 0.72rem;
  font-weight: 800;
}

.dpad__btn--up {
  grid-area: up;
}

.dpad__btn--down {
  grid-area: down;
}

.dpad__btn--left {
  grid-area: left;
}

.dpad__btn--right {
  grid-area: right;
}
</style>
