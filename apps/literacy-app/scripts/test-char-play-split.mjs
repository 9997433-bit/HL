#!/usr/bin/env node
/**
 * Round 18 H3 smoke probe.
 *
 * The baseline still keeps the rich play bank in one synchronous module. Until
 * the split implementation lands, this script exercises the stable getCharPlay
 * contract and reports the split checks as pending. Once the implementation
 * exports the Round 18 marker, the same probe also rejects a synchronous rich
 * import and imports every discovered shard.
 */

import assert from 'node:assert/strict'
import { readdir, readFile } from 'node:fs/promises'
import { relative, resolve, sep } from 'node:path'
import { pathToFileURL } from 'node:url'

const APP_ROOT = resolve(import.meta.dirname, '..')
const DATA_ROOT = resolve(APP_ROOT, 'src/data')
const PLAY_MODULE = resolve(DATA_ROOT, 'char-play.js')
const READY_MARKER = ['ROUND18', 'H3'].join('_')
const requireReady = process.argv.includes('--require-ready')

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

/**
 * Discover source modules that look like rich-play shards. The unsplit
 * char-play-rich.js bank itself is deliberately excluded.
 */
export async function findCharPlayShards() {
  const files = await walk(DATA_ROOT)
  return files.filter((file) => {
    if (!/\.(?:m?js)$/.test(file)) return false
    const name = relative(DATA_ROOT, file).split(sep).join('/')
    if (name === 'char-play-rich.js') return false
    return /(?:char-play-rich|char-play-shard|play-rich-shard)/i.test(name)
  })
}

/**
 * Exercise getCharPlay without assuming whether the split implementation keeps
 * it synchronous or makes it awaitable.
 */
export async function probeGetCharPlay(playModule, chars = ['日', '水', '龘', '']) {
  const getCharPlay = playModule.getCharPlay ?? playModule.default?.getCharPlay
  assert.equal(typeof getCharPlay, 'function', 'char-play module must export getCharPlay')

  const plays = []
  for (const char of chars) {
    const play = await getCharPlay(char)
    assert.ok(play && typeof play === 'object', `getCharPlay(${JSON.stringify(char)}) returned no play`)
    assert.equal(typeof play.template, 'string', `getCharPlay(${JSON.stringify(char)}) has no template`)
    assert.ok(play.template.trim(), `getCharPlay(${JSON.stringify(char)}) has an empty template`)
    assert.equal(typeof play.kind, 'string', `getCharPlay(${JSON.stringify(char)}) has no renderer kind`)
    assert.ok(play.props && typeof play.props === 'object', `getCharPlay(${JSON.stringify(char)}) has no props`)
    plays.push(play)
  }
  return plays
}

export async function probeCharPlaySplit() {
  const source = await readFile(PLAY_MODULE, 'utf8')
  const executableSource = stripComments(source)
  const playModule = await import(pathToFileURL(PLAY_MODULE))
  const shards = await findCharPlayShards()
  const exported = { ...(playModule.default ?? {}), ...playModule }
  const ready =
    Object.prototype.hasOwnProperty.call(exported, READY_MARKER) ||
    executableSource.includes(READY_MARKER)

  const syncRichImport =
    /(?:^|\n)\s*import\s+(?!\s*\()(?:(?!\n).)*?['"][^'"]*char-play-rich\.js['"]/.test(source)

  const plays = await probeGetCharPlay(playModule)

  if (!ready) {
    if (requireReady) {
      assert.fail(`${READY_MARKER} is not available yet`)
    }
    return {
      status: 'pending',
      ready,
      syncRichImport,
      shards: shards.length,
      plays: plays.length,
      note: 'split marker is not available; stable getCharPlay assertions passed',
    }
  }

  assert.equal(syncRichImport, false, 'char-play.js still synchronously imports char-play-rich.js')
  assert.ok(shards.length >= 2, `expected at least two rich-play shard modules, found ${shards.length}`)

  for (const shard of shards) {
    await assert.doesNotReject(
      import(pathToFileURL(shard)),
      `rich-play shard failed to load: ${relative(APP_ROOT, shard)}`,
    )
  }

  return {
    status: 'passed',
    ready,
    syncRichImport,
    shards: shards.length,
    plays: plays.length,
    note: `${shards.length} shard modules and getCharPlay loaded without throwing`,
  }
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) {
  const result = await probeCharPlaySplit()
  const symbol = result.status === 'passed' ? '✓' : '○'
  console.log(
    `${symbol} ${READY_MARKER} ${result.status.toUpperCase()}: ${result.note}; ` +
      `sync-rich-import=${result.syncRichImport}, shards=${result.shards}`,
  )
}
