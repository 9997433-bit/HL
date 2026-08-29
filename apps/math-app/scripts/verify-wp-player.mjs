#!/usr/bin/env node
/**
 * Round 19 H4 smoke probe — 应用题剖析「讲解播放」时间轴。
 *
 * 稳定断言（合入前后都跑）：
 *   - WpAnalysisPanel 可解析、buildAnalysis 产出分步
 *   - 面板保留跳过 / 手动下一步入口
 *
 * 门槛断言（ROUND19_H4 可执行标记出现后才硬卡）：
 *   - 播放 / 暂停 / 进度（或等价 timeline 控制）
 *   - 自动推进步骤
 *   - reduced-motion 下降级为手动点步
 *
 * 未合入前 ○ PENDING。`--require-ready` 升级为失败。
 */

import assert from 'node:assert/strict'
import { existsSync } from 'node:fs'
import { readFile } from 'node:fs/promises'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { dirname, resolve } from 'node:path'
import './register-alias.mjs'

const APP_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const PANEL = resolve(APP_ROOT, 'src/components/WpAnalysisPanel.vue')
const READY_MARKER = ['ROUND19', 'H4'].join('_')
const requireReady = process.argv.includes('--require-ready')

const stripComments = (source) =>
  source
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '')

const PLAYER_FILES = [
  'src/components/WpAnalysisPanel.vue',
  'src/components/WpExplainPlayer.vue',
  'src/components/WpVideoPlayer.vue',
  'src/composables/useWpExplainPlayer.js',
  'src/composables/useWpPlayer.js',
  'src/utils/wpExplainPlayer.js',
  'src/utils/wpPlayer.js',
]

async function collectPlayerSource() {
  const chunks = []
  const found = []
  for (const relativePath of PLAYER_FILES) {
    const absolute = resolve(APP_ROOT, relativePath)
    if (!existsSync(absolute)) continue
    found.push(relativePath)
    chunks.push(await readFile(absolute, 'utf8'))
  }
  // 面板是硬依赖；其他是可选落点
  assert.ok(found.includes('src/components/WpAnalysisPanel.vue'), 'WpAnalysisPanel.vue missing')
  return { source: chunks.join('\n'), found }
}

function hasExecutableMarker(source, modules) {
  if (stripComments(source).includes(READY_MARKER)) return true
  return modules.some((module) => Object.prototype.hasOwnProperty.call(module, READY_MARKER))
}

export async function probeWpPlayer() {
  const { source, found } = await collectPlayerSource()
  const code = stripComments(source)

  const [problemData, analysisData] = await Promise.all([
    import('../src/data/wordProblems.js'),
    import('../src/utils/wpAnalysis.js'),
  ])
  const modules = [problemData, analysisData]
  for (const relativePath of found) {
    if (!/\.js$/.test(relativePath)) continue
    modules.push(await import(pathToFileURL(resolve(APP_ROOT, relativePath)).href))
  }
  const ready = hasExecutableMarker(source, modules)

  assert.ok(Array.isArray(problemData.WORD_PROBLEMS) && problemData.WORD_PROBLEMS.length > 0)
  assert.equal(typeof analysisData.buildAnalysis, 'function')

  const template = problemData.WORD_PROBLEMS[0]
  const analysis = analysisData.buildAnalysis({ ...template.make(), id: template.id })
  assert.ok(Array.isArray(analysis.steps) && analysis.steps.length >= 1, 'buildAnalysis produced no steps')

  // 稳定底线：跳过 + 手动推进（现有 nextStep / 下一步）
  assert.match(code, /skip|跳过/, 'analysis panel must stay skippable')
  assert.match(code, /nextStep|下一步|showAllSteps|继续/, 'analysis panel must keep a manual step path')

  const controls = {
    play: /播放|playExplain|startPlayback|togglePlay|\bplay\s*\(|state\s*===\s*['"`]playing['"`]|data-player-play/i.test(
      code,
    ),
    pause: /暂停|pauseExplain|togglePlay|\bpause\s*\(|state\s*===\s*['"`]paused['"`]|data-player-pause/i.test(
      code,
    ),
    progress:
      /进度|progress|currentStep|playbackProgress|seek|scrub|data-player-progress|aria-valuenow/i.test(
        code,
      ),
    autoAdvance:
      /自动|autoPlay|auto[- ]?advance|advanceStep|scheduleNext|setInterval|setTimeout|gsap\.timeline|requestAnimationFrame/i.test(
        code,
      ),
    reducedMotion:
      /prefers-reduced-motion|reduceMotion|reducedMotion|data-motion\s*=\s*['"`]reduced['"`]/i.test(code),
  }

  const controlHits = Object.entries(controls)
    .filter(([, ok]) => ok)
    .map(([id]) => id)

  const playerReady =
    ready &&
    controls.play &&
    controls.pause &&
    controls.progress &&
    controls.autoAdvance &&
    controls.reducedMotion

  if (!playerReady) {
    if (requireReady) {
      assert.ok(ready, `${READY_MARKER} marker is not available yet`)
      assert.ok(controls.play, `${READY_MARKER} missing play control`)
      assert.ok(controls.pause, `${READY_MARKER} missing pause control`)
      assert.ok(controls.progress, `${READY_MARKER} missing progress control`)
      assert.ok(controls.autoAdvance, `${READY_MARKER} missing auto-advance`)
      assert.ok(controls.reducedMotion, `${READY_MARKER} missing reduced-motion fallback`)
    }
    return {
      status: 'pending',
      ready,
      files: found,
      controls: controlHits,
      steps: analysis.steps.length,
      note:
        `marker=${ready}; player controls=${controlHits.join(',') || 'none'}; ` +
        'stable buildAnalysis / skip / manual-step assertions passed',
    }
  }

  return {
    status: 'passed',
    ready,
    files: found,
    controls: controlHits,
    steps: analysis.steps.length,
    note: '讲解播放器 exposes play/pause/progress/auto-advance with reduced-motion fallback',
  }
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) {
  const result = await probeWpPlayer()
  const symbol = result.status === 'passed' ? '✓' : '○'
  console.log(
    `${symbol} ${READY_MARKER} ${result.status.toUpperCase()}: ${result.note}; ` +
      `files=${result.files.length}, stepsSample=${result.steps}`,
  )
}
