#!/usr/bin/env node
/**
 * Round 19 H2 smoke probe — 全库富 Play。
 *
 * 稳定断言（合入前后都跑）：
 *   - loadAllRichPlays / countRichPlays / listRichPlays / getCharPlay 可调用
 *   - 分片管线仍按单元懒加载（play-rich/uN.js ≥5，无整包静态 import）
 *   - 抽样字 getCharPlay 永不空
 *
 * 门槛断言（ROUND19_H2 可执行标记出现后才硬卡）：
 *   - countRichPlays() ≥ 1820
 *   - narration 去重 ≥ 1600
 *   - 字表每个字都有 hasRichPlay
 *
 * 未合入前默认 ○ PENDING 软跳过门槛，不把基线染红。
 * `--require-ready` 把 PENDING 升级为失败。
 */

import assert from 'node:assert/strict'
import { readdir, readFile, stat } from 'node:fs/promises'
import { relative, resolve, sep } from 'node:path'
import { pathToFileURL } from 'node:url'

const APP_ROOT = resolve(import.meta.dirname, '..')
const DATA_ROOT = resolve(APP_ROOT, 'src/data')
const PLAY_MODULE = resolve(DATA_ROOT, 'char-play.js')
const READY_MARKER = ['ROUND19', 'H2'].join('_')
const MIN_PLAYS = 1820
const MIN_NARRATIONS = 1600
const MIN_SHARDS = 5

const requireReady = process.argv.includes('--require-ready')
const sampleArg = process.argv.find((arg) => arg.startsWith('--sample='))
const sampleSize = sampleArg ? Number(sampleArg.slice('--sample='.length)) : 40

const stripComments = (source) =>
  source.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '')

async function walk(directory) {
  const entries = await readdir(directory, { withFileTypes: true })
  const nested = await Promise.all(
    entries.map((entry) => {
      const path = resolve(directory, entry.name)
      return entry.isDirectory() ? walk(path) : [path]
    }),
  )
  return nested.flat()
}

/** play-rich 分片：目录或文件名含 play-rich，排除整包 char-play-rich.js。 */
export async function findPlayRichShards() {
  const files = await walk(DATA_ROOT)
  return files.filter((file) => {
    if (!/\.(?:m?js)$/.test(file)) return false
    const name = relative(DATA_ROOT, file).split(sep).join('/')
    if (/(^|\/)char-play-rich\.js$/.test(name)) return false
    if (/(^|\/)index\.js$/.test(name) && /play-rich/.test(name)) return false
    return /play-rich/i.test(name)
  })
}

function hasExecutableMarker(source, exported) {
  return (
    Object.prototype.hasOwnProperty.call(exported, READY_MARKER) ||
    stripComments(source).includes(READY_MARKER)
  )
}

export async function probePlayFull() {
  const source = await readFile(PLAY_MODULE, 'utf8')
  const playModule = await import(pathToFileURL(PLAY_MODULE))
  const exported = { ...(playModule.default ?? {}), ...playModule }
  const ready = hasExecutableMarker(source, exported)

  assert.equal(typeof exported.loadAllRichPlays, 'function', 'missing loadAllRichPlays()')
  assert.equal(typeof exported.countRichPlays, 'function', 'missing countRichPlays()')
  assert.equal(typeof exported.listRichPlays, 'function', 'missing listRichPlays()')
  assert.equal(typeof exported.getCharPlay, 'function', 'missing getCharPlay()')

  const syncRichImport =
    /(?:^|\n)\s*import\s+(?!\s*\()(?:(?!\n).)*?['"][^'"]*char-play-rich\.js['"]/.test(source)
  assert.equal(syncRichImport, false, 'char-play.js must not synchronously import the rich bank')

  const shards = await findPlayRichShards()
  assert.ok(
    shards.length >= MIN_SHARDS,
    `expected ≥${MIN_SHARDS} play-rich shards, found ${shards.length}`,
  )
  let shardBytes = 0
  for (const shard of shards) {
    shardBytes += (await stat(shard)).size
    await assert.doesNotReject(
      import(pathToFileURL(shard)),
      `play-rich shard failed to load: ${relative(APP_ROOT, shard)}`,
    )
  }

  await exported.loadAllRichPlays()
  const plays = Number(await exported.countRichPlays()) || 0
  const rows = await exported.listRichPlays()
  assert.ok(Array.isArray(rows), 'listRichPlays() must return an array')
  assert.equal(plays, rows.length, 'countRichPlays and listRichPlays length disagree')

  const { CHAR_INDEX } = await import(pathToFileURL(resolve(DATA_ROOT, 'char-index.js')))
  assert.ok(Array.isArray(CHAR_INDEX) && CHAR_INDEX.length >= 1800, 'char index looks truncated')

  const step = Math.max(1, Math.ceil(CHAR_INDEX.length / Math.max(1, sampleSize)))
  const sample = CHAR_INDEX.filter((_, index) => index % step === 0).slice(0, sampleSize)
  for (const entry of sample) {
    const play = await exported.getCharPlay(entry.char)
    assert.ok(play && typeof play === 'object', `getCharPlay(${entry.char}) returned empty`)
    assert.ok(String(play.template ?? '').trim(), `getCharPlay(${entry.char}) has no template`)
    assert.ok(String(play.kind ?? '').trim(), `getCharPlay(${entry.char}) has no kind`)
    assert.ok(play.props && typeof play.props === 'object', `getCharPlay(${entry.char}) has no props`)
  }

  const narrations = new Set()
  for (const row of rows) {
    if (!row || row.templateFallback === true) continue
    const line = typeof row.narration === 'string' ? row.narration.trim() : ''
    if (line) narrations.add(line)
  }

  const stable = {
    plays,
    narrations: narrations.size,
    shards: shards.length,
    shardKiB: Math.round(shardBytes / 1024),
    sample: sample.length,
  }

  if (!ready || plays < MIN_PLAYS || narrations.size < MIN_NARRATIONS) {
    if (requireReady) {
      assert.ok(ready, `${READY_MARKER} marker is not available yet`)
      assert.ok(plays >= MIN_PLAYS, `rich plays ${plays} < ${MIN_PLAYS}`)
      assert.ok(narrations.size >= MIN_NARRATIONS, `narrations ${narrations.size} < ${MIN_NARRATIONS}`)
    }
    return {
      status: 'pending',
      ready,
      ...stable,
      note:
        `marker=${ready}; rich=${plays}/${MIN_PLAYS}, narrations=${narrations.size}/${MIN_NARRATIONS}; ` +
        'stable loader / shard / getCharPlay assertions passed',
    }
  }

  assert.equal(
    rows.filter((row) => row?.templateFallback === true).length,
    0,
    'template fallbacks must not count as rich plays',
  )
  assert.equal(new Set(rows.map((row) => row.char)).size, rows.length, 'rich plays must be unique by char')
  assert.equal(
    rows.filter((row) => typeof row.narration !== 'string' || row.narration.trim().length < 4).length,
    0,
    'every rich play needs meaningful narration',
  )

  if (typeof exported.hasRichPlay === 'function') {
    const missing = CHAR_INDEX.filter((entry) => !exported.hasRichPlay(entry.char)).map((e) => e.char)
    assert.equal(missing.length, 0, `chars still without rich play: ${missing.slice(0, 12).join(',')}`)
  }

  return {
    status: 'passed',
    ready,
    ...stable,
    note: `full-library rich play ${plays} with ${narrations.size} distinct narrations`,
  }
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) {
  const result = await probePlayFull()
  const symbol = result.status === 'passed' ? '✓' : '○'
  console.log(
    `${symbol} ${READY_MARKER} ${result.status.toUpperCase()}: ${result.note}; ` +
      `shards=${result.shards} (${result.shardKiB} KiB), sample=${result.sample}`,
  )
}
