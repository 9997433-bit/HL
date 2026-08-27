/**
 * Round 5B Play Layer 硬门槛。
 * 标准：.agent_workspace/ROUND5B-ACCEPTANCE.md
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const fails = []
const notes = []

const check = (ok, msg) => (ok ? notes.push(`✓ ${msg}`) : fails.push(`✗ ${msg}`))
const exists = (...rel) => rel.some((p) => fs.existsSync(path.join(root, p)))
const read = (rel) => {
  try {
    return fs.readFileSync(path.join(root, rel), 'utf8')
  } catch {
    return ''
  }
}

const countMatches = (src, re) => (src.match(re) || []).length

/* P1 每日冒险 ≥3 任务 */
const home = read('apps/literacy-app/src/views/HomeView.vue')
const dailyStore = read('apps/literacy-app/src/stores/dailyQuest.js')
const dailyComposable = read('apps/literacy-app/src/composables/useDailyQuest.js')
const dailySrc = home + dailyStore + dailyComposable
const dailyHits =
  countMatches(dailySrc, /dailyQuest|daily-quest|今日冒险|todayQuest|DAILY_TASKS/i) +
  (dailySrc.includes('tasks') && dailySrc.includes('completed') ? 1 : 0)
check(
  dailyHits >= 2 && (dailySrc.includes('3') || countMatches(dailySrc, /tasks\s*[:=]\s*\[/g) >= 1),
  dailyHits >= 2
    ? 'P1 每日冒险 3 任务已接线'
    : 'P1 每日冒险未接线 —— 由 r5b-daily-adventure 交付（首页 ≥3 项可勾选任务）'
)

/* P2 吉祥物陪跑 ≥5 路由 */
const mascotFiles = [
  'apps/literacy-app/src/components/MascotCompanion.vue',
  'apps/math-app/src/components/MascotBot.vue'
]
const literacyRoutes = read('apps/literacy-app/src/router/index.js')
const mathRoutes = read('apps/math-app/src/router/index.js')
let mascotRouteRefs = 0
for (const f of [
  'apps/literacy-app/src/views/HomeView.vue',
  'apps/literacy-app/src/views/LearnView.vue',
  'apps/literacy-app/src/views/GamesView.vue',
  'apps/literacy-app/src/views/BooksView.vue',
  'apps/literacy-app/src/views/IdiomsView.vue',
  'apps/math-app/src/modules/home/HomeView.vue',
  'apps/math-app/src/modules/daily/DailyView.vue'
]) {
  const s = read(f)
  if (/MascotCompanion|MascotBot/.test(s)) mascotRouteRefs++
}
check(
  exists(...mascotFiles) && mascotRouteRefs >= 5,
  mascotRouteRefs >= 5
    ? `P2 吉祥物陪跑 ${mascotRouteRefs} 处视图接线（要求 ≥ 5）`
    : `P2 吉祥物陪跑 ${mascotRouteRefs}/5 —— 由 r5b-mascot-companion 扩面`
)

/* P3 useFeedback */
const feedbackPaths = [
  'shared/composables/useFeedback.js',
  'apps/literacy-app/src/composables/useFeedback.js',
  'apps/math-app/src/composables/useFeedback.js'
]
const feedbackFile = feedbackPaths.find((p) => exists(p))
let feedbackRefs = 0
if (feedbackFile) {
  const name = path.basename(feedbackFile, '.js')
  for (const f of [
    'apps/literacy-app/src',
    'apps/math-app/src'
  ]) {
    const walk = (dir) => {
      if (!fs.existsSync(path.join(root, dir))) return
      for (const ent of fs.readdirSync(path.join(root, dir), { withFileTypes: true })) {
        const rel = `${dir}/${ent.name}`
        if (ent.isDirectory()) walk(rel)
        else if (/\.(vue|js)$/.test(ent.name)) {
          const s = read(rel)
          if (s.includes(name) || s.includes('useFeedback')) feedbackRefs++
        }
      }
    }
    walk(f)
  }
}
check(
  feedbackFile && feedbackRefs >= 3,
  feedbackFile
    ? `P3 useFeedback 已接线（${feedbackRefs} 处引用）`
    : 'P3 useFeedback 未创建 —— 由 r5b-use-feedback 交付'
)

/* P4 地图叙事 */
const learn = read('apps/literacy-app/src/views/LearnView.vue')
const mathHome = read('apps/math-app/src/modules/home/HomeView.vue')
const narrative =
  /unlock|locked|剧情|故事|章节|chapterStory|planetStory/i.test(learn + mathHome)
check(
  narrative,
  narrative ? 'P4 地图叙事解锁已接线' : 'P4 地图叙事未接线 —— 由 r5b-map-narrative 交付'
)

/* P5 街机大厅 */
const games = read('apps/literacy-app/src/views/GamesView.vue')
const arcade = /arcade|街机|neon|game-hall|games-grid/i.test(games)
check(
  arcade,
  arcade ? 'P5 游戏大厅街机化已接线' : 'P5 游戏大厅未街机化 —— 由 r5b-games-arcade 交付'
)

/* P6 答对节奏 */
const literacySfx = read('apps/literacy-app/src/utils/sfx.js')
const mathSfx = read('apps/math-app/src/utils/sfx.js') + read('apps/math-app/src/audio/sfx.js')
const rhythm =
  /streak|combo|pitch|音高|连对/i.test(literacySfx + mathSfx + read('apps/literacy-app/src/composables/useFeedback.js') + read('apps/math-app/src/composables/useFeedback.js'))
check(
  rhythm,
  rhythm ? 'P6 答对音效节奏已接线' : 'P6 答对节奏未接线 —— 由 r5b-sfx-rhythm 交付'
)

notes.forEach((n) => console.log(' ', n))
if (fails.length) {
  console.log('')
  fails.forEach((f) => console.log(' ', f))
}
console.log(`\nRound 5B Play 门禁：${notes.length} 项通过，${fails.length} 项失败。`)
process.exit(fails.length ? 1 : 0)
