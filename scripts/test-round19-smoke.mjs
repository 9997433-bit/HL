#!/usr/bin/env node
/**
 * Round 19 smoke / 单测入口。
 *
 * 覆盖：
 *   H2 全库富 Play（≥1820 / narration ≥1600，分片管线不破）
 *   H3 CharPlayStage 精美度（≥3 类升级 + reduced-motion）
 *   H4 剖析讲解播放器（播/暂停/进度/自动推进 + reduced-motion 手动降级）
 *
 * 功能分支未合入前对应用例 `t.skip`（PENDING 软跳过），稳定契约仍硬断言。
 * 也可直接跑各 workspace 探针：
 *   npm run test:play:full --workspace=apps/literacy-app
 *   npm run test:play:polish --workspace=apps/literacy-app
 *   npm run verify:wp-player --workspace=apps/math-app
 */

import assert from 'node:assert/strict'
import { register } from 'node:module'
import test from 'node:test'
import { pathToFileURL } from 'node:url'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

register('./alias-loader.mjs', import.meta.url)

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')

async function importProbe(relativePath) {
  return import(pathToFileURL(path.join(ROOT, relativePath)).href)
}

test('H2 full-library rich play keeps shard pipeline and thresholds', async (t) => {
  const { probePlayFull } = await importProbe('apps/literacy-app/scripts/test-play-full.mjs')
  const result = await probePlayFull()
  assert.ok(result.shards >= 5, `expected play-rich shards, got ${result.shards}`)
  assert.ok(result.sample >= 1, 'expected getCharPlay sample coverage')
  if (result.status === 'pending') {
    t.skip(`ROUND19_H2 PENDING: ${result.note}`)
    return
  }
  assert.equal(result.status, 'passed')
  assert.ok(result.plays >= 1820, `rich plays ${result.plays} < 1820`)
  assert.ok(result.narrations >= 1600, `narrations ${result.narrations} < 1600`)
})

test('H3 CharPlayStage polish exposes three upgrades with reduced motion', async (t) => {
  const { probePlayPolish } = await importProbe('apps/literacy-app/scripts/test-play-polish.mjs')
  const result = await probePlayPolish()
  if (result.status === 'pending') {
    t.skip(`ROUND19_H3 PENDING: ${result.note}`)
    return
  }
  assert.equal(result.status, 'passed')
  assert.ok(result.upgrades.length >= 3, `expected ≥3 upgrades, got ${result.upgrades.length}`)
})

test('H4 word-problem explain player supports play/pause/progress', async (t) => {
  const { probeWpPlayer } = await importProbe('apps/math-app/scripts/verify-wp-player.mjs')
  const result = await probeWpPlayer()
  assert.ok(result.steps >= 1, 'buildAnalysis must still produce steps')
  if (result.status === 'pending') {
    t.skip(`ROUND19_H4 PENDING: ${result.note}`)
    return
  }
  assert.equal(result.status, 'passed')
  for (const key of ['play', 'pause', 'progress', 'autoAdvance', 'reducedMotion']) {
    assert.ok(result.controls.includes(key), `missing player control ${key}`)
  }
})
