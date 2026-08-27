/**
 * Round 5B Play Layer 硬门槛（P1–P6，六项全过退出码 0，任一失败退出码 1）。
 *
 * 标准与探针约定：.agent_workspace/ROUND5B-ACCEPTANCE.md（§1 阈值、§2 探针约定）
 * 回填模板：.agent_workspace/acceptance-log-round5b.md
 *
 * 纯静态分析（fs + 正则），不 import 应用代码，无 node_modules 也能跑。
 * 支持 `--json`：输出机器可读汇总，便于编排器聚合。
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const asJson = process.argv.includes('--json')

const results = []
const record = (id, ok, detail) => results.push({ id, ok, detail })

const exists = (...rel) => rel.some((p) => fs.existsSync(path.join(root, p)))
const read = (rel) => {
  try {
    return fs.readFileSync(path.join(root, rel), 'utf8')
  } catch {
    return ''
  }
}
const count = (src, re) => (src.match(re) || []).length

/** 递归收集目录下的 .vue/.js 相对路径。 */
function walk(rel) {
  const out = []
  const abs = path.join(root, rel)
  if (!fs.existsSync(abs)) return out
  for (const ent of fs.readdirSync(abs, { withFileTypes: true })) {
    const child = `${rel}/${ent.name}`
    if (ent.isDirectory()) out.push(...walk(child))
    else if (/\.(vue|js)$/.test(ent.name)) out.push(child)
  }
  return out
}

/* ============================================================
 * P1 每日冒险 3 件事（r5b-daily-adventure）
 * 约定：apps/literacy-app/src/stores/dailyQuest.js（或 composables/useDailyQuest.js）
 * 任务模板池 ≥3（TASK_SPECS / DAILY_TASKS，模板有 title 或 id），
 * 每日摆出 ≥3 件（DAILY_TASK_COUNT），有完成态（可勾选）；
 * HomeView 接线每日冒险入口；完成有庆祝。
 * ============================================================ */
{
  const storeRel = ['apps/literacy-app/src/stores/dailyQuest.js', 'apps/literacy-app/src/composables/useDailyQuest.js']
  const store = storeRel.map(read).join('\n')
  const home = read('apps/literacy-app/src/views/HomeView.vue')
  const cards = walk('apps/literacy-app/src/components')
    .filter((f) => /daily/i.test(path.basename(f)))
    .map(read)
    .join('\n')

  const hasStore = exists(...storeRel)
  const taskCount = Math.max(
    count(store, /\bid\s*:\s*['"][\w-]+['"]/g),
    count(store, /\btitle\s*:/g)
  )
  const perDay = Number((store.match(/DAILY_TASK_COUNT\s*=\s*(\d+)/) || [])[1] ?? taskCount)
  const hasTasks = /DAILY_TASKS|TASK_SPECS|useDailyQuest/i.test(store) && taskCount >= 3 && perDay >= 3
  const hasDone = /completed|done|checked|勾/i.test(store)
  const wired = /DailyAdventure|dailyQuest|useDailyQuest/i.test(home)
  const celebrates = /celebrat|庆祝|burst|StarBurst|彩带|confetti/i.test(cards + store)

  const ok = hasStore && hasTasks && hasDone && wired && celebrates
  const miss = [
    !hasStore && '任务库缺失（stores/dailyQuest.js）',
    hasStore && !hasTasks && `任务模板 ${taskCount}（需 ≥3 且每日摆出 ≥3 件）`,
    hasStore && !hasDone && '无完成态（completed）',
    !wired && 'HomeView 未接线',
    !celebrates && '完成无庆祝'
  ].filter(Boolean)
  record(
    'P1',
    ok,
    ok
      ? `每日冒险已接线（模板池 ${taskCount}，每日 ${perDay} 件，首页 + 庆祝齐备）`
      : `每日冒险未达标：${miss.join('；')} —— r5b-daily-adventure 交付`
  )
}

/* ============================================================
 * P2 吉祥物全程陪跑（r5b-mascot-companion）
 * 约定：识字 MascotCompanion / 数学 MascotBot 组件存在；
 * 路由级视图接线（非 App.vue 弹窗）：识字 views/*.vue ≥5 且数学 modules 视图 ≥5。
 * ============================================================ */
{
  const litComp = exists('apps/literacy-app/src/components/MascotCompanion.vue')
  const mathComp = exists('apps/math-app/src/components/MascotBot.vue')
  const litViews = walk('apps/literacy-app/src/views').filter((f) =>
    /MascotCompanion|useMascotCompanion/.test(read(f))
  )
  const mathViews = walk('apps/math-app/src/modules').filter(
    (f) => f.endsWith('.vue') && /MascotBot|useMascotCompanion/.test(read(f))
  )

  const ok = litComp && mathComp && litViews.length >= 5 && mathViews.length >= 5
  record(
    'P2',
    ok,
    ok
      ? `吉祥物陪跑：识字 ${litViews.length} 视图 + 数学 ${mathViews.length} 视图（各要求 ≥5）`
      : `吉祥物陪跑 识字 ${litViews.length}/5、数学 ${mathViews.length}/5${
          litComp && mathComp ? '' : '（组件缺失）'
        } —— r5b-mascot-companion 扩面`
  )
}

/* ============================================================
 * P3 统一 useFeedback（r5b-use-feedback）
 * 约定：shared/composables/useFeedback.js（或双 App 各一份 src/composables/useFeedback.js）；
 * 能力齐备：星星粒子 + 震动降级（vibrate）+ 音效钩子；
 * 三个面各接 ≥1 处：数学 QuizShell、识字小游戏视图、识字写字链路。
 * ============================================================ */
{
  const sharedPath = 'shared/composables/useFeedback.js'
  const litPath = 'apps/literacy-app/src/composables/useFeedback.js'
  const mathPath = 'apps/math-app/src/composables/useFeedback.js'
  const unified = exists(sharedPath) || (exists(litPath) && exists(mathPath))
  const src = [sharedPath, litPath, mathPath].map(read).join('\n')

  const hasParticle = /burst|[Ss]tar|粒子/.test(src)
  const hasVibrate = /vibrate/.test(src)
  const hasSfx = /sfx|sound/.test(src)

  const refs = (f) => /useFeedback/.test(read(f))
  const quizWired = refs('apps/math-app/src/components/QuizShell.vue')
  const gameWired = walk('apps/literacy-app/src/views').some((f) => /Game/.test(f) && refs(f))
  const writeWired =
    refs('apps/literacy-app/src/views/CharDetailView.vue') ||
    refs('apps/literacy-app/src/components/HanziStrokeBox.vue')

  const ok = unified && hasParticle && hasVibrate && hasSfx && quizWired && gameWired && writeWired
  const miss = [
    !unified && '统一 composable 缺失（shared/ 或双 App）',
    unified && !hasParticle && '缺星星粒子',
    unified && !hasVibrate && '缺震动降级（vibrate）',
    unified && !hasSfx && '缺音效钩子',
    !quizWired && 'Quiz 未接线',
    !gameWired && '识字小游戏未接线',
    !writeWired && '写字链路未接线'
  ].filter(Boolean)
  record(
    'P3',
    ok,
    ok
      ? '统一 useFeedback 已接线（粒子/震动/音效 + Quiz/游戏/写字三面）'
      : `useFeedback 未达标：${miss.join('；')} —— r5b-use-feedback 交付`
  )
}

/* ============================================================
 * P4 地图叙事解锁（r5b-map-narrative）
 * 约定（二选一，任一 App 达标即过）：
 * 识字 data/unitStories.js 导出 UNIT_STORIES（≥5 条，每条有 story 一句话剧情），
 *   LearnView 接线且带解锁过渡标记（unlock-anim/-reveal/-transition 或 unlockCelebrat*）；
 * 数学 data/planetStories.js 导出 PLANET_STORIES，同样要求接线 HomeView。
 * ============================================================ */
{
  const evalSide = (registryRel, exportName, viewRel) => {
    const registry = read(registryRel)
    const view = read(viewRel)
    const entries = count(registry, /\bstory\s*:/g)
    const hasRegistry = new RegExp(exportName).test(registry) && entries >= 5
    const wired = new RegExp(`${exportName}|${path.basename(registryRel, '.js')}`).test(view)
    const transition = /unlock[-_]?(anim|reveal|transition|fx)|unlockCelebrat/i.test(view + registry)
    return { entries, hasRegistry, wired, transition, ok: hasRegistry && wired && transition }
  }
  const lit = evalSide(
    'apps/literacy-app/src/data/unitStories.js',
    'UNIT_STORIES',
    'apps/literacy-app/src/views/LearnView.vue'
  )
  const math = evalSide(
    'apps/math-app/src/data/planetStories.js',
    'PLANET_STORIES',
    'apps/math-app/src/modules/home/HomeView.vue'
  )

  const ok = lit.ok || math.ok
  record(
    'P4',
    ok,
    ok
      ? `地图叙事已接线（识字 ${lit.entries} 条 / 数学 ${math.entries} 条剧情，含解锁过渡标记）`
      : `地图叙事未达标：剧情注册表 识字 ${lit.entries}、数学 ${math.entries} 条（需 ≥5 且视图接线 + 解锁过渡标记）—— r5b-map-narrative 交付`
  )
}

/* ============================================================
 * P5 游戏大厅街机化（r5b-games-arcade）
 * 约定：GamesView 有街机标记（arcade/街机）；data/games.js 每条 route
 * 都出现在 GamesView；每款游戏有一句话玩法（howToPlay/tagline 字段）。
 * ============================================================ */
{
  const gamesData = read('apps/literacy-app/src/data/games.js')
  const view = read('apps/literacy-app/src/views/GamesView.vue')
  const routes = [...gamesData.matchAll(/route\s*:\s*['"]([^'"]+)['"]/g)].map((m) => m[1])

  const arcade = /arcade|街机/i.test(view)
  const allRendered = routes.length > 0 && routes.every((r) => view.includes(r))
  const taglines = count(view + gamesData, /howToPlay\s*:|tagline\s*:/g)
  const hasTaglines = routes.length > 0 && taglines >= routes.length

  const ok = arcade && allRendered && hasTaglines
  const miss = [
    !arcade && '无街机风标记',
    !allRendered && `注册表 ${routes.length} 款未全部渲染进大厅`,
    !hasTaglines && `一句话玩法 ${taglines}/${routes.length}`
  ].filter(Boolean)
  record(
    'P5',
    ok,
    ok
      ? `街机大厅已接线（${routes.length} 台机器，每台有一句话玩法）`
      : `街机大厅未达标：${miss.join('；')} —— r5b-games-arcade 交付`
  )
}

/* ============================================================
 * P6 答对音效节奏（r5b-sfx-rhythm）
 * 约定：识字 utils/audio.js|sfx.js 与数学 utils/sound.js 提供 streak
 * 音高递进入口（sfx.streak/streakChord/streakCue）；两 App 各 ≥1 条
 * 答题链路（utils 之外）调用 sfx.streak(...)/streakCue(...)。
 * ============================================================ */
{
  const litSfx = read('apps/literacy-app/src/utils/sfx.js') + read('apps/literacy-app/src/utils/audio.js')
  const mathSfx = read('apps/math-app/src/utils/sound.js')
  const litHasCue = /streak/i.test(litSfx)
  const mathHasCue = /streakCue|streak\s*:/.test(mathSfx)

  const callRe = /sfx\.streak\s*\(|streakCue\s*\(/
  const wiredIn = (dir) =>
    walk(dir).filter((f) => !f.includes('/utils/') && callRe.test(read(f)))
  const litCalls = wiredIn('apps/literacy-app/src')
  const mathCalls = wiredIn('apps/math-app/src')

  const ok = litHasCue && mathHasCue && litCalls.length >= 1 && mathCalls.length >= 1
  const miss = [
    !litHasCue && '识字 sfx 无 streak 谱面',
    !mathHasCue && '数学 sound 无 streakCue',
    litHasCue && litCalls.length < 1 && '识字答题链路未调用',
    mathHasCue && mathCalls.length < 1 && '数学答题链路未调用'
  ].filter(Boolean)
  record(
    'P6',
    ok,
    ok
      ? `答对节奏已接线（识字 ${litCalls.length} 处 + 数学 ${mathCalls.length} 处调用）`
      : `答对节奏未达标：${miss.join('；')} —— r5b-sfx-rhythm 交付`
  )
}

/* ============================================================ */

const passed = results.filter((r) => r.ok)
const failed = results.filter((r) => !r.ok)

if (asJson) {
  console.log(
    JSON.stringify(
      {
        round: '5B',
        passed: passed.map((r) => r.id),
        failed: failed.map((r) => r.id),
        results
      },
      null,
      2
    )
  )
} else {
  for (const r of results) console.log(` ${r.ok ? '✓' : '✗'} ${r.id} ${r.detail}`)
  console.log(`\nRound 5B Play 门禁：${passed.length}/6 通过${failed.length ? `（失败：${failed.map((r) => r.id).join(' ')}）` : ''}`)
}
process.exit(failed.length ? 1 : 0)
