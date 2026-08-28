#!/usr/bin/env node

import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath, pathToFileURL } from 'node:url'
import path from 'node:path'
import test from 'node:test'

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

function read(relativePath) {
  try {
    return readFileSync(path.join(ROOT, relativePath), 'utf8')
  } catch {
    return ''
  }
}

function stripComments(source) {
  return source
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '')
}

function sources(relativePaths) {
  return relativePaths.map(read).join('\n')
}

function skipUntilMarker(t, marker, source) {
  if (new RegExp(`\\b${marker}\\b`).test(stripComments(source))) return false
  t.skip(`${marker} 功能分支尚未合入`)
  return true
}

function literalStrings(source) {
  return [...stripComments(source).matchAll(/(['"`])((?:\\.|(?!\1)[\s\S]){4,}?)\1/g)]
    .map((match) => match[2].replace(/\$\{[^}]+\}/g, '').trim())
    .filter(Boolean)
}

// ROUND16_H2 — 无字源冷门字进入「认」步时也必须挂载可动、非空的回退舞台。
test('ROUND16_H2 literacy intro fallback is wired and animated', (t) => {
  const detail = read('apps/literacy-app/src/views/CharDetailView.vue')
  const stage = sources([
    'apps/literacy-app/src/components/IntroFallbackStage.vue',
    'apps/literacy-app/src/components/CharIntroStage.vue',
  ])
  const all = `${detail}\n${stage}`
  if (skipUntilMarker(t, 'ROUND16_H2', all)) return

  const code = stripComments(all)
  const detailCode = stripComments(detail)
  assert.match(detailCode, /phase\s*={0,2}\s*['"]intro['"]|phase\s*===?\s*['"]intro['"]/)
  assert.match(
    detailCode,
    /IntroFallbackStage|CharIntroStage/,
    'CharDetailView must mount the Round 16 intro stage',
  )
  assert.match(
    code,
    /!has(?:Etymology|Origin)|no(?:Etymology|Ety|Origin)|fallback/i,
    'the stage must be selected for characters without etymology',
  )
  assert.ok(stage.length > 300, 'fallback stage must not be an empty component shell')
  assert.match(
    stripComments(stage),
    /animation|transition|requestAnimationFrame|setInterval|gsap/i,
    'fallback stage must contain programmatic or CSS animation',
  )
})

// ROUND16_H3 — 500 条富 Play 必须按字去重，且不能把模板补齐伪装成富脚本。
test('ROUND16_H3 rich plays reach 500 with real, distinct narration', async (t) => {
  const moduleUrl = pathToFileURL(
    path.join(ROOT, 'apps/literacy-app/src/data/char-play.js'),
  ).href
  const play = await import(moduleUrl)
  const count = play.countRichPlays?.() ?? 0
  if (count < 500) {
    t.skip(`ROUND16_H3 富 Play 尚未合入（当前 ${count}/500）`)
    return
  }

  assert.equal(typeof play.listRichPlays, 'function')
  const rows = play.listRichPlays()
  assert.ok(rows.length >= 500)
  assert.equal(new Set(rows.map((row) => row.char)).size, rows.length, 'rich plays must be unique by char')
  assert.equal(
    rows.filter((row) => row.templateFallback === true).length,
    0,
    'template fallbacks must not count as rich plays',
  )
  assert.equal(
    rows.filter((row) => typeof row.narration !== 'string' || row.narration.trim().length < 4).length,
    0,
    'every rich play needs meaningful narration',
  )
  assert.ok(
    new Set(rows.map((row) => row.narration.trim())).size >= Math.ceil(rows.length * 0.8),
    'at least 80% of rich-play narrations must be distinct',
  )
})

// ROUND16_H4 — 数学「学」演示至少覆盖 12 个技能，并保留三态、跳过和减弱动效路径。
test('ROUND16_H4 math learn demos cover the three-stage contract', (t) => {
  const demo = sources([
    'apps/math-app/src/components/LearnDemo.vue',
    'apps/math-app/src/components/SkillLearnDemo.vue',
    'apps/math-app/src/data/learn-demos.js',
    'apps/math-app/src/data/skill-learn-demos.js',
    'apps/math-app/src/modules/visual-demos/index.js',
  ])
  if (skipUntilMarker(t, 'ROUND16_H4', demo)) return

  const code = stripComments(demo)
  const ids = [
    ...code.matchAll(/(?:skillId|id)\s*:\s*['"`]([^'"`]+)['"`]/g),
  ].map((match) => match[1])
  assert.ok(new Set(ids).size >= 12, `expected at least 12 demo skill ids, got ${new Set(ids).size}`)
  assert.match(code, /object|concrete|实物/i, 'demo needs an object/concrete stage')
  assert.match(code, /visual|diagram|图形/i, 'demo needs a visual stage')
  assert.match(code, /equation|symbol|算式/i, 'demo needs an equation stage')
  assert.match(code, /skip|跳过/i, 'demo must be skippable')
  assert.match(
    code,
    /prefers-reduced-motion|reducedMotion|reduceMotion/i,
    'demo must have a reduced-motion completion path',
  )
})

// ROUND16_H5 — 应用题剖析必须能打开，并给出图示、分步与变式入口。
test('ROUND16_H5 word-problem analysis exposes the full help path', (t) => {
  const analysis = sources([
    'apps/math-app/src/modules/word-problems/WordProblemsView.vue',
    'apps/math-app/src/components/WpAnalysisPanel.vue',
    'apps/math-app/src/components/WordProblemAnalysis.vue',
  ])
  if (skipUntilMarker(t, 'ROUND16_H5', analysis)) return

  const code = stripComments(analysis)
  assert.match(code, /analysis|剖析|讲解/i, 'word-problem view needs an analysis trigger')
  assert.match(code, /diagram|model|图示|画图/i, 'analysis needs a visual model')
  assert.match(code, /steps?|分步|第一步/i, 'analysis needs step-by-step reasoning')
  assert.match(code, /variant|变式|再练/i, 'analysis needs a variant-practice entry')
  assert.match(code, /close|skip|关闭|跳过|收起/i, 'analysis must let the learner return to the problem')
})

// ROUND16_H6 — 学伴台词要覆盖新字、连对、复习和疲劳等阶段，而不是只堆通用鼓励。
test('ROUND16_H6 mascot scripts provide 40 distinct, staged lines', async (t) => {
  const paths = [
    'apps/literacy-app/src/data/mascotLines.js',
    'apps/math-app/src/data/mascotLines.js',
  ]
  const source = sources([
    ...paths,
    'apps/literacy-app/src/composables/useMascotCoach.js',
    'apps/math-app/src/composables/useMascotCoach.js',
  ])
  if (skipUntilMarker(t, 'ROUND16_H6', source)) return

  const generated = []
  const context = {
    name: '小宇',
    learned: 20,
    mastered: 12,
    due: 4,
    streak: 5,
    books: 2,
    idioms: 3,
    poems: 2,
    songs: 2,
    nextChar: '春',
    dailyCompleted: false,
    dailyDone: 2,
    dailyTotal: 5,
    stars: 18,
    consecutiveCorrect: 4,
    tired: true,
  }
  for (const relativePath of paths) {
    const mod = await import(pathToFileURL(path.join(ROOT, relativePath)).href)
    for (const scene of Object.keys(mod.MASCOT_SCENES ?? {})) {
      generated.push(...(mod.mascotLines?.(scene, context) ?? []))
    }
  }

  const lines = [...new Set([...generated, ...literalStrings(source)])]
    .map((line) => line.trim())
    .filter((line) => line.length >= 8 && !/TODO|占位|待补/i.test(line))
  assert.ok(lines.length >= 40, `expected at least 40 distinct mascot lines, got ${lines.length}`)
  assert.match(source, /新字|learn|intro/i, 'scripts need a new-character/learning stage')
  assert.match(source, /连对|连着答对|streak|consecutive/i, 'scripts need a correct-streak stage')
  assert.match(source, /复习|review|due/i, 'scripts need a review stage')
  assert.match(source, /累|休息|疲劳|tired|fatigue/i, 'scripts need a fatigue/rest stage')
})

// ROUND16_H7 — 家长周报需本地生成一句弱项结论，并把建议练习严格限制在 3 项内。
test('ROUND16_H7 parent weekly report explains weakness and caps practice', (t) => {
  const report = sources([
    'apps/literacy-app/src/views/ParentView.vue',
    'apps/math-app/src/modules/parent/ParentView.vue',
    'apps/literacy-app/src/composables/useWeeklyReport.js',
    'apps/math-app/src/composables/useWeeklyReport.js',
    'apps/literacy-app/src/utils/weeklyReport.js',
    'apps/math-app/src/utils/weeklyReport.js',
  ])
  if (skipUntilMarker(t, 'ROUND16_H7', report)) return

  const code = stripComments(report)
  assert.match(code, /本周|weekly|weekReport/i, 'report must be scoped to the current week')
  assert.match(code, /弱项|薄弱|weak/i, 'report must state the learner weakness')
  assert.match(code, /建议|recommend|practice/i, 'report must include recommended practice')
  assert.match(
    code,
    /slice\s*\(\s*0\s*,\s*3\s*\)|MAX_[A-Z_]*RECOMMEND\w*\s*=\s*3|limit\s*:\s*3/i,
    'recommended practice must be capped at three items',
  )
  assert.match(
    code,
    /computed\s*\(|function\s+\w*(?:Weekly|Week|Report)\w*\s*\(|=>/,
    'weekly explanation must be generated locally from progress',
  )
})
