#!/usr/bin/env node
/**
 * ROUND18_H2（承 ROUND17_H2）· 富 Play 生成管道的负例自测。
 *
 * 探针数的是「1240 条、旁白 1240 句不重样」。这两个数只要有一条路能绕过去，
 * 门槛就是假的：把同一句旁白复制 300 遍，条数照样够；把句号换成感叹号，
 * 一字不差的去重也照样放行——念给孩子听还是同一句。
 *
 * 所以拦截必须在**生成期**，而不是等探针事后数。这个脚本把 seed 改坏，
 * 逐条验证 gen-char-play-rich.mjs 真的拒绝落盘：
 *
 *   1. 一字不差的撞句     → 判错，且指名道姓说和谁撞了
 *   2. 只差标点语气的撞句 → 同样判错（narrationKey 归一后相等）
 *   3. 条数不到 1200      → 判错，不生成半成品
 *   4. 真 seed            → 通过，并且报出的条数 / 去重句数达线
 *   5. 本轮标记           → 生成器和生成物里都读得到 ROUND18_H2（剥注释仍在）
 *
 * 用法：node scripts/test-play-rich-guard.mjs
 */

import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const appDir = path.resolve(here, '..')
const genScript = path.join(here, 'gen-char-play-rich.mjs')
const seedFile = path.join(appDir, 'scripts', 'data', 'char-play-seed.txt')

const MIN_PLAYS = 1200
const MIN_NARRATIONS = 960
/** 本轮标记，生成器和生成物都得带着它，剥掉注释也还在。 */
const ROUND18_MARK = 'ROUND18_H2'

const failures = []
const fail = (msg) => failures.push(msg)

const seedLines = fs.readFileSync(seedFile, 'utf8').split('\n')
/** seed 里真正的脚本行（跳过注释和空行），下标是原文行号 - 1。 */
const rowIndexes = seedLines
  .map((line, i) => [line.trim(), i])
  .filter(([line]) => line && !line.startsWith('#') && line.split('|').length === 5)
  .map(([, i]) => i)

if (rowIndexes.length < MIN_PLAYS) {
  fail(`seed 只有 ${rowIndexes.length} 条脚本行，还没到 ${MIN_PLAYS} 条`)
}

const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'play-rich-guard-'))
const write = (name, lines) => {
  const file = path.join(tmpDir, name)
  fs.writeFileSync(file, lines.join('\n'))
  return file
}

/** 只校验不落盘地跑一遍生成器，把退出码和输出一起拿回来。 */
function runCheck(seedPath) {
  const proc = spawnSync(process.execPath, [genScript, '--check', `--seed=${seedPath}`], {
    cwd: appDir,
    encoding: 'utf8'
  })
  return { code: proc.status, out: `${proc.stdout ?? ''}${proc.stderr ?? ''}` }
}

const cols = (index) => seedLines[index].split('|')
const rebuild = (index, parts) => {
  const next = [...seedLines]
  next[index] = parts.join('|')
  return next
}

/* -------------------------------------------------- 1. 一字不差的撞句 */

{
  const [victim, donor] = [rowIndexes[rowIndexes.length - 1], rowIndexes[0]]
  const parts = cols(victim)
  parts[3] = cols(donor)[3]
  const { code, out } = runCheck(write('exact-twin.txt', rebuild(victim, parts)))
  if (code === 0) fail('一字不差的撞句居然生成成功了')
  if (!/一字不差/.test(out)) fail(`撞句报错没说清是撞句：${out.trim().split('\n')[0] ?? '(无输出)'}`)
}

/* ---------------------------------------- 2. 只差标点语气的「近似撞句」 */

{
  const [victim, donor] = [rowIndexes[rowIndexes.length - 2], rowIndexes[1]]
  const parts = cols(victim)
  // 念出来一模一样，只是标点和语气词不同：这一关必须也拦下
  parts[3] = `${cols(donor)[3].replace(/[。！？]$/, '')}！`
  const { code, out } = runCheck(write('near-twin.txt', rebuild(victim, parts)))
  if (code === 0) fail('只改标点语气的撞句被放行了')
  if (!/只差标点语气/.test(out)) {
    fail(`近似撞句报错没说清原因：${out.trim().split('\n')[0] ?? '(无输出)'}`)
  }
}

/* ------------------------------------------------- 3. 条数不到 1200 */

{
  const keep = new Set(rowIndexes.slice(0, MIN_PLAYS - 1))
  const thin = seedLines.filter((line, i) => keep.has(i) || !rowIndexes.includes(i))
  const { code, out } = runCheck(write('too-thin.txt', thin))
  if (code === 0) fail(`只剩 ${MIN_PLAYS - 1} 条也算过线`)
  if (!/没到 ROUND17_H2 的线/.test(out)) {
    fail(`条数不足的报错没说清门槛：${out.trim().split('\n')[0] ?? '(无输出)'}`)
  }
}

/* -------------------------------------------------- 4. 真 seed 必须过 */

{
  const { code, out } = runCheck(seedFile)
  if (code !== 0) fail(`真 seed 没过校验：${out}`)
  const m = out.match(/(\d+)\s*条，覆盖\s*(\d+)\s*个单元、\d+\s*个模板，旁白\s*(\d+)\s*句不重样/)
  if (!m) {
    fail(`看不懂生成器的汇报：${out.trim()}`)
  } else {
    const [, plays, units, narrations] = m.map(Number)
    if (plays < MIN_PLAYS) fail(`富脚本 ${plays} 条，不到 ${MIN_PLAYS}`)
    if (narrations < MIN_NARRATIONS) fail(`旁白去重 ${narrations} 句，不到 ${MIN_NARRATIONS}`)
    if (narrations !== plays) fail(`${plays} 条脚本却只有 ${narrations} 句旁白，有撞句漏网`)
    console.log(`真 seed：${plays} 条 / ${units} 个单元 / 旁白 ${narrations} 句不重样`)
  }
}

/* ------------------------------------- 5. 生成物和运行时口径对得上 */

{
  const runtime = await import('../src/data/char-play.js')
  const coverage = runtime.richPlayCoverage()
  if (coverage.probe !== 'ROUND17_H2') fail(`运行时标记是 ${coverage.probe}，不是 ROUND17_H2`)
  if (coverage.plays < MIN_PLAYS) fail(`运行时富脚本 ${coverage.plays} 条，不到 ${MIN_PLAYS}`)
  if (coverage.narrations < MIN_NARRATIONS) {
    fail(`运行时旁白去重 ${coverage.narrations} 句，不到 ${MIN_NARRATIONS}`)
  }
  const rows = runtime.listRichPlays()
  const templated = rows.filter((row) => row.templateFallback !== false)
  if (templated.length) fail(`${templated.length} 条富脚本被标成了模板补齐`)
  console.log(
    `运行时：${coverage.probe} · ${coverage.plays} 条 / 旁白 ${coverage.narrations} 句不重样`
  )
}

/* ------------------------------- 6. 本轮标记在生成器和生成物里都读得到 */

{
  // 剥掉注释再找：写在文档块里的标记不算数，探针要的是可执行的那一份
  const stripComments = (text) =>
    text.replace(/\/\*[\s\S]*?\*\//g, ' ').replace(/(^|[^:])\/\/.*$/gm, '$1')
  const genSource = stripComments(fs.readFileSync(genScript, 'utf8'))
  if (!genSource.includes(ROUND18_MARK)) fail(`生成器里找不到可执行的 ${ROUND18_MARK}`)
  const built = stripComments(fs.readFileSync(path.join(appDir, 'src', 'data', 'char-play-rich.js'), 'utf8'))
  if (!built.includes(ROUND18_MARK)) fail(`生成物里找不到可执行的 ${ROUND18_MARK}`)
}

fs.rmSync(tmpDir, { recursive: true, force: true })

if (failures.length) {
  console.error(`\n✗ ${failures.length} 处不合格：`)
  for (const line of failures) console.error(`  - ${line}`)
  process.exit(1)
}

console.log('✓ 撞句与条数不足都在生成期被拦下，真 seed 达线')
