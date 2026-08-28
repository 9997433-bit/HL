#!/usr/bin/env node

import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { register } from 'node:module'
import test from 'node:test'
import { fileURLToPath, pathToFileURL } from 'node:url'

register('./alias-loader.mjs', import.meta.url)

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

function absolute(relativePath) {
  return path.join(ROOT, relativePath)
}

function read(relativePath) {
  try {
    return fs.readFileSync(absolute(relativePath), 'utf8')
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

function sourceFiles(relativeDirectory) {
  const directory = absolute(relativeDirectory)
  if (!fs.existsSync(directory)) return []
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const relativePath = path.join(relativeDirectory, entry.name)
    if (entry.isDirectory()) return sourceFiles(relativePath)
    return /\.(?:js|mjs|ts|tsx|vue)$/.test(entry.name) ? [relativePath] : []
  })
}

async function importFromRoot(relativePath) {
  return import(pathToFileURL(absolute(relativePath)).href)
}

function skipPending(t, marker, reason) {
  t.skip(`${marker} 尚未合入：${reason}`)
}

test('H2 rich-play registry keeps 900 real, meaningfully narrated plays', async (t) => {
  const play = await importFromRoot('apps/literacy-app/src/data/char-play.js')
  assert.equal(typeof play.countRichPlays, 'function', 'missing countRichPlays()')
  assert.equal(typeof play.listRichPlays, 'function', 'missing listRichPlays()')

  const marker =
    play.RICH_PLAY_PROBE === 'ROUND17_H2' ||
    /\bROUND17_H2\b/.test(stripComments(read('apps/literacy-app/src/data/char-play.js')))
  if (!marker) return skipPending(t, 'ROUND17_H2', '先保留富 Play 公共接口')

  const rows = play.listRichPlays()
  assert.ok(Array.isArray(rows), 'listRichPlays() must return an array')
  assert.equal(play.countRichPlays(), rows.length, 'count and registry length disagree')
  assert.ok(rows.length >= 900, `expected at least 900 rich plays, got ${rows.length}`)
  assert.equal(new Set(rows.map((row) => row.char)).size, rows.length, 'rich plays must be unique by char')
  assert.equal(
    rows.filter((row) => row?.templateFallback === true).length,
    0,
    'template fallbacks must not count as rich plays',
  )

  const narrations = rows.map((row) => String(row?.narration ?? '').trim())
  assert.equal(narrations.filter((line) => line.length < 4).length, 0, 'every rich play needs narration')
  const distinct = new Set(narrations).size
  assert.ok(distinct >= 720, `expected at least 720 distinct narrations, got ${distinct}`)
  assert.ok(
    distinct >= Math.ceil(rows.length * 0.8),
    `narration uniqueness ${distinct}/${rows.length} is below 80%`,
  )

  if (typeof play.richPlayCoverage === 'function') {
    assert.deepEqual(play.richPlayCoverage(), {
      probe: 'ROUND17_H2',
      plays: rows.length,
      narrations: distinct,
    })
  }
})

test('H3 learn-demo registry covers 27 skills with three-stage and escape paths', async (t) => {
  const demos = await importFromRoot('apps/math-app/src/data/learn-demos.js')
  assert.ok(Array.isArray(demos.LEARN_DEMOS), 'missing LEARN_DEMOS registry')
  if (demos.ROUND17_H3 !== 'learn-demo-registry-27') {
    return skipPending(t, 'ROUND17_H3', `当前公共注册表为 ${demos.LEARN_DEMOS.length} 条`)
  }

  const rows = demos.LEARN_DEMOS
  assert.ok(rows.length >= 27, `expected at least 27 demos, got ${rows.length}`)
  assert.equal(new Set(rows.map((row) => row.id)).size, rows.length, 'demo ids must be unique')
  assert.equal(new Set(rows.map((row) => row.skillId)).size, rows.length, 'demo skill ids must be unique')
  assert.deepEqual(
    demos.LEARN_DEMO_STAGES.map((stage) => stage.id),
    ['object', 'visual', 'equation'],
  )

  for (const row of rows) {
    assert.ok(row.object && typeof row.object === 'object', `${row.id} is missing object stage`)
    assert.ok(row.visual && typeof row.visual === 'object', `${row.id} is missing visual stage`)
    assert.ok(String(row.equation ?? '').trim(), `${row.id} is missing equation stage`)
    assert.equal(row.narration?.length, 3, `${row.id} must have one narration per stage`)
    assert.equal(demos.learnDemoOfSkill(row.skillId)?.id, row.id, `${row.id} is not addressable by skill`)
  }

  const index = await importFromRoot('apps/math-app/src/data/learn-demo-index.js')
  assert.deepEqual(
    [...index.LEARN_DEMO_SKILLS].sort(),
    rows.map((row) => row.skillId).sort(),
    'lazy index and demo registry must stay in sync',
  )

  const component = stripComments(read('apps/math-app/src/components/LearnDemo.vue'))
  assert.match(component, /data-demo-skip|function\s+skip\s*\(/, 'demo needs a skip path')
  assert.match(
    component,
    /prefers-reduced-motion|reducedMotion/i,
    'demo needs a reduced-motion completion path',
  )
})

test('H4 handcrafted explanations cover 20 templates and reach the analysis panel', async (t) => {
  const relativePath = 'apps/math-app/src/data/word-problem-explains.js'
  if (!fs.existsSync(absolute(relativePath))) {
    return skipPending(t, 'ROUND17_H4', '等待手写剖析数据接口')
  }

  const explains = await importFromRoot(relativePath)
  assert.equal(explains.ROUND17_H4, 'handwritten-explain-chain')
  assert.ok(Array.isArray(explains.WORD_PROBLEM_EXPLAINS), 'missing WORD_PROBLEM_EXPLAINS')
  assert.equal(explains.EXPLAIN_COUNT, explains.WORD_PROBLEM_EXPLAINS.length)
  assert.ok(explains.EXPLAIN_COUNT >= 20, `expected at least 20 explanations, got ${explains.EXPLAIN_COUNT}`)
  assert.equal(
    new Set(explains.WORD_PROBLEM_EXPLAINS.map((row) => row.id)).size,
    explains.EXPLAIN_COUNT,
    'explanation ids must be unique',
  )

  for (const row of explains.WORD_PROBLEM_EXPLAINS) {
    assert.ok(String(row.headline ?? '').trim().length >= 12, `${row.id} needs a meaningful headline`)
    assert.ok(row.steps?.length > 0, `${row.id} needs handwritten steps`)
    row.steps.forEach((write, index) => {
      assert.equal(typeof write, 'function', `${row.id} step ${index + 1} must be executable`)
      const line = String(
        write({
          a: 12,
          b: 3,
          value: 4,
          quotient: 4,
          remainder: 0,
          op: '÷',
          index,
          all: [],
          question: { unit: '个' },
        }) ?? '',
      ).trim()
      assert.ok(line.length >= 8, `${row.id} step ${index + 1} is empty or too short`)
      assert.doesNotMatch(line, /TODO|undefined|NaN|待补|占位/i)
    })
  }

  const problems = await importFromRoot('apps/math-app/src/data/wordProblems.js')
  const template = problems.WORD_PROBLEMS.find((problem) => explains.explainOf(problem.id))
  assert.ok(template, 'no real word-problem id resolves to a handcrafted explanation')
  const covered = { ...template.make(), id: template.id }
  const analysisModule = await importFromRoot('apps/math-app/src/utils/wpAnalysis.js')
  const analysis = analysisModule.buildAnalysis(covered)
  assert.equal(analysis.handwritten, true, `${covered.id} did not use its handcrafted chain`)
  assert.ok(analysis.steps.length > 0 && analysis.steps.every((step) => step.hand === true))

  const panel = stripComments(read('apps/math-app/src/components/WpAnalysisPanel.vue'))
  assert.match(panel, /ROUND17_H4/, 'analysis panel does not expose the Round 17 chain')
  assert.match(panel, /emit\s*\(\s*['"]skip['"]|跳过/, 'analysis panel must be skippable')
  const timeDriven = /requestAnimationFrame|setTimeout|setInterval/.test(panel)
  assert.ok(
    !timeDriven || /prefers-reduced-motion|reducedMotion/i.test(panel),
    'time-driven analysis must provide a reduced-motion completion path',
  )
})

test('H5 mascot stage lines are wired into the single-character and quiz paths', (t) => {
  const appFiles = [
    ...sourceFiles('apps/literacy-app/src'),
    ...sourceFiles('apps/math-app/src'),
  ]
  const markedFiles = appFiles.filter((relativePath) =>
    /\bROUND17_H5\b/.test(stripComments(read(relativePath))),
  )
  if (!markedFiles.length) return skipPending(t, 'ROUND17_H5', '等待关键路径接线标记')

  const charDetail = stripComments(read('apps/literacy-app/src/views/CharDetailView.vue'))
  const quizShell = stripComments(read('apps/math-app/src/components/QuizShell.vue'))
  const markedSource = markedFiles.map(read).map(stripComments).join('\n')
  const mascotApi = /useMascotCoach|mascotStageLines|pickMascotStage/

  assert.match(markedSource, mascotApi, 'ROUND17_H5 marker is not attached to a mascot-stage API')
  assert.match(charDetail, /mascot|学伴|coach/i, 'single-character path does not mount the mascot coach')
  assert.match(
    `${quizShell}\n${markedSource}`,
    /recentWrong|wrongCount|mistake|incorrect/i,
    'quiz feedback does not pass a wrong-answer signal',
  )
  assert.ok(
    mascotApi.test(charDetail) || mascotApi.test(quizShell),
    'neither CharDetailView nor QuizShell calls the staged mascot API',
  )
})

test('H6 walkthrough manifest references four real critical-path captures', (t) => {
  const relativePath = '.agent_workspace/evidence/r17/walkthrough.md'
  const document = read(relativePath)
  if (!document) return skipPending(t, 'ROUND17_H6', '等待走查清单与截图/录屏')

  const references = [
    ...document.matchAll(
      /(?:\.agent_workspace\/)?evidence\/r17\/[^\s)"'<>]+\.(?:png|jpe?g|webp|gif|mp4)/gi,
    ),
  ].map((match) => match[0].replace(/[?#].*$/, ''))
  const unique = [...new Set(references)]
  assert.ok(unique.length >= 4, `expected at least 4 capture references, got ${unique.length}`)

  for (const reference of unique) {
    const relativeAsset = reference.startsWith('.agent_workspace/')
      ? reference
      : path.join('.agent_workspace', reference)
    assert.ok(fs.existsSync(absolute(relativeAsset)), `walkthrough asset does not exist: ${reference}`)
    assert.ok(fs.statSync(absolute(relativeAsset)).size > 8, `walkthrough asset is empty: ${reference}`)
  }

  assert.match(document, /认步|认字|富\s*Play|H2/i, 'walkthrough misses the literacy rich-play path')
  assert.match(document, /学演示|三态|H3/i, 'walkthrough misses the learn-demo path')
  assert.match(document, /剖析|应用题|H4/i, 'walkthrough misses the explanation path')
  assert.match(document, /周报|家长|H5/i, 'walkthrough misses the parent-report path')
  assert.doesNotMatch(document, /TODO|待补截图|占位路径/i)
})

test('H7 Android evidence records a reproducible simulation or an honest block', (t) => {
  const evidenceDirectory = absolute('.agent_workspace/evidence/r17')
  const candidates = fs.existsSync(evidenceDirectory)
    ? fs
        .readdirSync(evidenceDirectory)
        .filter((name) => /(?:android|device).*\.(?:md|txt|json)$/i.test(name))
    : []
  if (!candidates.length) return skipPending(t, 'ROUND17_H7', '等待 android:sim 报告或 BLOCKED 台账')

  const report = candidates
    .map((name) => read(path.join('.agent_workspace/evidence/r17', name)))
    .join('\n')
  assert.ok(report.length > 200, 'Android evidence is too short to be reproducible')
  assert.match(
    report,
    /npm\s+(?:run\s+android:sim|run\s+sync:android|--prefix\s+\S+\s+run\s+\S+)|scripts\/android-sim\.mjs/,
    'Android evidence must include a reproduction command',
  )

  if (/\bBLOCKED\b/.test(report)) {
    assert.match(report, /原因|阻断|设备|ADB|SDK|环境|权限|密钥/i, 'BLOCKED entry needs a concrete reason')
    assert.match(report, /复现|重跑|命令|执行|run/i, 'BLOCKED entry needs recovery/reproduction steps')
    return
  }

  assert.match(report, /android:sim|模拟/i, 'successful evidence must identify the simulation run')
  assert.match(report, /literacy|识字/i, 'successful evidence must cover the literacy APK')
  assert.match(report, /math|数学/i, 'successful evidence must cover the math APK')
  assert.ok(
    (report.match(/[^\s"'`]+\.apk/gi) ?? []).length >= 2 || /双\s*APK/i.test(report),
    'successful evidence must account for both APKs',
  )
  assert.doesNotMatch(report, /TODO|待补|占位/i)
})
