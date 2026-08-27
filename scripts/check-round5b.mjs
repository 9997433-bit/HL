/**
 * Round 5B Play Layer 硬门槛。
 * 标准：.agent_workspace/ROUND5B-ACCEPTANCE.md
 *
 * 这是源码契约门禁，不依赖构建产物。每个 P 项只记一次通过/失败，避免某一项
 * 拆成多个探针后把 “6 项硬门槛” 的分母冲大。Round 5B 功能分支合并前 FAIL
 * 是预期红灯；合并后必须 6/6。
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const fails = []
const notes = []

const check = (ok, msg) => (ok ? notes.push(`✓ ${msg}`) : fails.push(`✗ ${msg}`))
const read = (rel) => {
  try {
    return fs.readFileSync(path.join(root, rel), 'utf8')
  } catch {
    return ''
  }
}

const countMatches = (src, re) => (src.match(re) || []).length
const stripComments = (src) =>
  src
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '')

const walkSource = (rel) => {
  const start = path.join(root, rel)
  if (!fs.existsSync(start)) return []
  const files = []
  const walk = (dir) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name)
      if (entry.isDirectory()) walk(full)
      else if (/\.(?:js|mjs|ts|vue)$/.test(entry.name)) {
        files.push(path.relative(root, full).split(path.sep).join('/'))
      }
    }
  }
  walk(start)
  return files
}

const literacyFiles = walkSource('apps/literacy-app/src')
const mathFiles = walkSource('apps/math-app/src')
const source = (files) => stripComments(files.map(read).join('\n'))
const sourceRefs = (files, marker) =>
  files.filter((file) => file !== marker && stripComments(read(file)).includes('useFeedback'))

const routeViews = (app, routerFile) => {
  const router = stripComments(read(routerFile))
  const matches = [...router.matchAll(/import\(\s*['"]@\/([^'"]+\.vue)['"]\s*\)/g)]
  return [...new Set(matches.map((match) => `apps/${app}/src/${match[1]}`))]
}

/* P1 每日冒险 ≥3 任务 */
const homeFile = 'apps/literacy-app/src/views/HomeView.vue'
const home = stripComments(read(homeFile))
const dailyFiles = literacyFiles.filter(
  (file) => /(?:daily|quest|adventure)/i.test(path.basename(file)) && file !== homeFile
)
const dailySrc = source([homeFile, ...dailyFiles])
const taskCategories = [
  /学(?:习)?新字|new[-_ ]?char|learn[-_ ]?char/i,
  /复习|review/i,
  /绘本|成语|阅读|book|idiom|read/i,
  /小游戏|game/i
].filter((pattern) => pattern.test(dailySrc)).length
const declaredTasks = countMatches(
  source(dailyFiles),
  /\b(?:id|key|type)\s*:\s*['"`][\w-]+['"`]/g
)
const dailyTaskCount = Math.max(taskCategories, declaredTasks)
const dailyOnHome = /daily[-_ ]?quest|daily[-_ ]?adventure|今日(?:的)?(?:冒险|任务)/i.test(home)
const dailyInteractive =
  /type=["']checkbox|role=["']checkbox|aria-checked|toggle\w*(?:quest|task)|complete\w*(?:quest|task)|mark\w*complete/i.test(
    dailySrc
  )
const dailyCelebration =
  /confetti|celebrat|fireworks|burst|撒花|彩带|庆祝/i.test(dailySrc) &&
  /completed|complete|完成/i.test(dailySrc)
check(
  dailyOnHome && dailyTaskCount >= 3 && dailyInteractive && dailyCelebration,
  `P1 每日冒险：任务 ${dailyTaskCount}/3，首页=${dailyOnHome ? '已接线' : '未接线'}，` +
    `勾选=${dailyInteractive ? '有' : '无'}，完成庆祝=${dailyCelebration ? '有' : '无'}`
)

/* P2 吉祥物陪跑 ≥5 路由 */
const mascotRoutes = {
  literacy: routeViews('literacy-app', 'apps/literacy-app/src/router/index.js').filter((file) =>
    /<MascotCompanion\b/.test(stripComments(read(file)))
  ),
  math: routeViews('math-app', 'apps/math-app/src/router/index.js').filter((file) =>
    /<MascotBot\b/.test(stripComments(read(file)))
  )
}
const mascotRouteRefs = mascotRoutes.literacy.length + mascotRoutes.math.length
const mascotSources = {
  literacy: source([
    'apps/literacy-app/src/components/MascotCompanion.vue',
    ...mascotRoutes.literacy
  ]),
  math: source(['apps/math-app/src/components/MascotBot.vue', ...mascotRoutes.math])
}
const interactiveMascots = Object.values(mascotSources).every(
  (src) =>
    /@click|role=["']button|<button\b/i.test(src) &&
    /speak|speech|say|voice|encourag|语音|朗读|鼓励/i.test(src)
)
check(
  mascotRoutes.literacy.length > 0 &&
    mascotRoutes.math.length > 0 &&
    mascotRouteRefs >= 5 &&
    interactiveMascots,
  `P2 吉祥物陪跑：${mascotRouteRefs}/5 路由` +
    `（识字 ${mascotRoutes.literacy.length}，数学 ${mascotRoutes.math.length}），` +
    `点触语音/鼓励=${interactiveMascots ? '有' : '缺失'}`
)

/* P3 useFeedback */
const feedbackPaths = [
  'shared/composables/useFeedback.js',
  'apps/literacy-app/src/composables/useFeedback.js',
  'apps/math-app/src/composables/useFeedback.js'
]
const feedbackFiles = feedbackPaths.filter((file) => fs.existsSync(path.join(root, file)))
const hasSharedFeedback = feedbackFiles.includes('shared/composables/useFeedback.js')
const hasDualFeedback =
  feedbackFiles.includes('apps/literacy-app/src/composables/useFeedback.js') &&
  feedbackFiles.includes('apps/math-app/src/composables/useFeedback.js')
const literacyFeedbackRefs = sourceRefs(
  literacyFiles,
  'apps/literacy-app/src/composables/useFeedback.js'
)
const mathFeedbackRefs = sourceRefs(mathFiles, 'apps/math-app/src/composables/useFeedback.js')
const feedbackRefs = [...literacyFeedbackRefs, ...mathFeedbackRefs]
const feedbackDefinitions = source(feedbackFiles)
const feedbackCapabilities = {
  particles: /particle|burst|confetti|star|星星|粒子/i.test(feedbackDefinitions),
  haptics: /vibrat|haptic|navigator/i.test(feedbackDefinitions),
  sound: /\bsfx\b|\bsound\b|\baudio\b/i.test(feedbackDefinitions),
  reducedMotion: /reduceMotion|reducedMotion|prefers-reduced-motion/i.test(feedbackDefinitions)
}
const feedbackSurfaces = {
  quiz: feedbackRefs.some((file) => /Quiz|Question|modules\/.+View\.vue$/i.test(file)),
  game: feedbackRefs.some((file) => /(?:Game|Maze|Memory|Spot|Listen).*\.vue$/i.test(file)),
  writing: feedbackRefs.some((file) => /(?:CharDetail|Writ|Trace|Stroke).*\.vue$/i.test(file))
}
const allFeedbackCapabilities = Object.values(feedbackCapabilities).every(Boolean)
const allFeedbackSurfaces = Object.values(feedbackSurfaces).every(Boolean)
check(
  (hasSharedFeedback || hasDualFeedback) &&
    literacyFeedbackRefs.length > 0 &&
    mathFeedbackRefs.length > 0 &&
    feedbackRefs.length >= 3 &&
    allFeedbackCapabilities &&
    allFeedbackSurfaces,
  `P3 useFeedback：定义=${hasSharedFeedback ? 'shared' : hasDualFeedback ? '双 App' : '不完整'}，` +
    `引用=${feedbackRefs.length}（识字 ${literacyFeedbackRefs.length}/数学 ${mathFeedbackRefs.length}），` +
    `粒子/震动/音效/reduced-motion=${allFeedbackCapabilities ? '齐全' : '不全'}，` +
    `Quiz/游戏/写字=${allFeedbackSurfaces ? '齐全' : '不全'}`
)

/* P4 地图叙事 */
const mapCandidates = [
  {
    view: 'apps/literacy-app/src/views/LearnView.vue',
    files: literacyFiles.filter((file) => /(?:unit|map|story|chapter|narrative)/i.test(file))
  },
  {
    view: 'apps/math-app/src/modules/home/HomeView.vue',
    files: mathFiles.filter((file) => /(?:modules|map|story|chapter|narrative)/i.test(file))
  }
]
const mapNarrative = mapCandidates.find(({ view, files }) => {
  const viewSrc = stripComments(read(view))
  const allSrc = source([view, ...files])
  const locked = /unlock|locked|is-locked|未解锁|解锁/i.test(viewSrc)
  const greyed = /grayscale|gr[ae]y|灰显|is-locked|\.locked|opacity/i.test(viewSrc)
  const storyInView =
    /\b(?:story|narrative|chapter)\b|剧情|故事|章节/i.test(viewSrc) &&
    /\{\{[^}]*(?:story|narrative|chapter)[^}]*\}\}|剧情|故事|章节/i.test(viewSrc)
  const storyContent =
    countMatches(allSrc, /\b(?:story|narrative|chapter(?:Story)?)\s*:/gi) > 0 ||
    /剧情|故事|章节/.test(allSrc)
  const transition = /transition|animation|gsap|useFeedback|enter\(/i.test(viewSrc)
  const motionSafe =
    /reduceMotion|reducedMotion|prefers-reduced-motion|useFeedback/i.test(viewSrc)
  return locked && greyed && storyInView && storyContent && transition && motionSafe
})
check(
  Boolean(mapNarrative),
  mapNarrative
    ? `P4 地图叙事：${mapNarrative.view} 已接线锁定灰显、剧情、解锁过渡与动效降级`
    : 'P4 地图叙事：未找到同时具备锁定灰显、剧情文案、解锁过渡与 reduced-motion 的地图'
)

/* P5 街机大厅 */
const gamesFile = 'apps/literacy-app/src/views/GamesView.vue'
const gamesSrc = source([
  gamesFile,
  ...literacyFiles.filter((file) => /(?:games|arcade)/i.test(path.basename(file)))
])
const gamesView = stripComments(read(gamesFile))
const gameRoutes = new Set(
  [...gamesSrc.matchAll(/\b(?:to|route)\s*:\s*['"]((?:\/listen|\/games\/)[^'"]*)['"]/g)].map(
    (match) => match[1]
  )
)
const gameCount = Math.max(
  gameRoutes.size,
  countMatches(gamesSrc, /\bid\s*:\s*['"][\w-]+['"]/g)
)
const gameDescriptions = countMatches(gamesSrc, /\b(?:desc|howToPlay|tagline)\s*:/g)
const arcade = /arcade|街机|neon|霓虹|game-hall|pixel/i.test(gamesView)
const cardGrid =
  /display\s*:\s*grid|grid-template-(?:columns|rows)|class=["'][^"']*(?:grid|arcade)/i.test(
    gamesView
  )
const descriptionsRendered =
  /(?:g|game)\.(?:desc|howToPlay|tagline)|一句话玩法/i.test(gamesView)
check(
  arcade &&
    cardGrid &&
    gameCount > 0 &&
    gameDescriptions >= gameCount &&
    descriptionsRendered,
  `P5 街机大厅：街机视觉=${arcade ? '有' : '无'}，卡片网格=${cardGrid ? '有' : '无'}，` +
    `一句话玩法=${gameDescriptions}/${gameCount || '?'}`
)

/* P6 答对节奏 */
const rhythmState = (files, app) => {
  const audioFiles = files.filter((file) =>
    /(?:\/utils\/(?:audio|sfx|sound)|\/audio\/|\/composables\/useFeedback)\.(?:js|ts)$/i.test(
      file
    )
  )
  const answerFiles = files.filter((file) =>
    /(?:Quiz|Question|Game|CharDetail|NumberSense|Arithmetic|Geometry|Logic|Sudoku|WordProblems).*\.vue$/i.test(
      file
    )
  )
  const audioSrc = source(audioFiles)
  const answerSrc = source(answerFiles)
  const tonalProgression = [
    /(?:pitch|freq(?:uency)?|playbackRate)\s*[:=][^\n]*(?:streak|combo)/i,
    /(?:streak|combo)[^\n]*(?:pitch|freq(?:uency)?|playbackRate|semitone|transpose)/i,
    /(?:notes?|tones?|scale)\s*\[[^\]]*(?:streak|combo)/i,
    /(?:streak|combo)(?:Pitch|Tone|Level|Step)\b/i
  ].some((pattern) => pattern.test(audioSrc))
  const thresholdBeat =
    /if\s*\([^)]*(?:streak|combo)[^)]*(?:>=|>|%)[^)]*\)[\s\S]{0,180}(?:sfx|sound)\.(?:combo|celebrate|streak|correct)/i.test(
      answerSrc
    )
  const wired =
    /(?:sfx|sound)\.(?:correct|success|combo|streak|celebrate)\s*\([^)]*(?:streak|combo)/i.test(
      answerSrc
    ) ||
    /(?:fxCorrect|feedback|correct)\s*\([^)]*\{[^}]*(?:streak|combo)/i.test(answerSrc) ||
    thresholdBeat
  return {
    app,
    progressive: tonalProgression || thresholdBeat,
    wired,
    audioFiles: audioFiles.length
  }
}
const rhythm = [
  rhythmState(literacyFiles, '识字'),
  rhythmState(mathFiles, '数学')
]
check(
  rhythm.every((state) => state.progressive && state.wired),
  `P6 答对节奏：${rhythm
    .map(
      (state) =>
        `${state.app}[递进/节拍=${state.progressive ? '有' : '无'},答题接线=${state.wired ? '有' : '无'}]`
    )
    .join('，')}`
)

notes.forEach((n) => console.log(' ', n))
if (fails.length) {
  console.log('')
  fails.forEach((f) => console.log(' ', f))
}
console.log(`\nRound 5B Play 门禁：${notes.length} 项通过，${fails.length} 项失败。`)
if (fails.length) {
  console.log('说明：Round 5B 功能分支尚未全部合并时 FAIL 属预期红灯；集成后必须 6/6。')
}
process.exit(fails.length ? 1 : 0)
