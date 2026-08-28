/**
 * Round 15 · 一字一动画硬门槛（v1.0）。
 * 标准：.agent_workspace/ROUND15-ACCEPTANCE.md
 *
 * 固定输出 H1–H8。编排启动时（Play 未合入）预期 0/8 或仅文档存在时的部分结构绿。
 * `--json` 输出机读汇总。
 */

import fs from 'node:fs'
import path from 'node:path'
import { register } from 'node:module'
import { fileURLToPath } from 'node:url'
import { spawnSync } from 'node:child_process'

register('./alias-loader.mjs', import.meta.url)

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const asJson = process.argv.includes('--json')
const results = []
const fails = []
const notes = []
const EXPECTED = 8

const check = (id, ok, passMsg, failMsg = passMsg) => {
  const msg = ok ? passMsg : failMsg
  results.push({ id, status: ok ? 'pass' : 'fail', msg })
  ;(ok ? notes : fails).push(`${ok ? '✓' : '✗'} ${msg}`)
}
const read = (rel) => {
  try {
    return fs.readFileSync(path.join(root, rel), 'utf8')
  } catch {
    return ''
  }
}
const exists = (rel) => fs.existsSync(path.join(root, rel))
const stripComments = (src) =>
  src
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '')

const charDetail = stripComments(read('apps/literacy-app/src/views/CharDetailView.vue'))
const literacySmoke = stripComments(read('apps/literacy-app/scripts/smoke.mjs'))

/* ---- H1 五步对齐 ---- */
{
  const hasPlay =
    /id:\s*['"]play['"]/.test(charDetail) ||
    /PHASES[\s\S]*玩/.test(charDetail)
  const hasSpeakOrQuiz =
    /id:\s*['"]speak['"]/.test(charDetail) ||
    /id:\s*['"]quiz['"]/.test(charDetail) ||
    /说/.test(charDetail)
  const fiveStepHint =
    /玩/.test(charDetail) &&
    /认/.test(charDetail) &&
    (/练/.test(charDetail) || /listen/.test(charDetail)) &&
    /写/.test(charDetail) &&
    hasSpeakOrQuiz
  check(
    'H1',
    hasPlay && fiveStepHint,
    'H1 CharDetailView 五步含玩→认→练→写→说',
    'H1 缺少玩步或五步未对齐洪恩玩认练写说'
  )
}

/* ---- H2 Play 引擎 + 全库 resolve ---- */
{
  const engineHit =
    exists('apps/literacy-app/src/components/CharPlayStage.vue') ||
    exists('apps/literacy-app/src/components/PlayStage.vue') ||
    /CharPlayStage|getCharPlay/.test(charDetail)
  let coverageOk = false
  let coverMsg = '未能加载 getCharPlay / CHARACTERS'
  try {
    const playModPaths = [
      'apps/literacy-app/src/data/char-play.js',
      'apps/literacy-app/src/data/charPlay.js',
      'apps/literacy-app/src/data/play-index.js',
      'apps/literacy-app/src/utils/charPlay.js'
    ]
    let getCharPlay = null
    for (const rel of playModPaths) {
      if (!exists(rel)) continue
      const mod = await import(path.join(root, rel))
      getCharPlay = mod.getCharPlay || mod.default?.getCharPlay
      if (getCharPlay) break
    }
    const charsMod = await import(path.join(root, 'apps/literacy-app/src/data/characters.js'))
    const list = charsMod.CHARACTERS || []
    if (typeof getCharPlay === 'function' && list.length >= 1800) {
      let miss = 0
      for (const c of list) {
        const p = getCharPlay(c.char)
        if (!p || !p.template) miss += 1
      }
      coverageOk = miss === 0
      coverMsg = coverageOk
        ? `H2 getCharPlay 全库 ${list.length}/${list.length} 有 template`
        : `H2 getCharPlay 空洞 ${miss}/${list.length}`
    } else {
      coverMsg = `H2 引擎未就绪（getCharPlay=${typeof getCharPlay}, chars=${list.length}）`
    }
  } catch (e) {
    coverMsg = `H2 加载失败：${e.message}`
  }
  check('H2', engineHit && coverageOk, coverMsg, coverMsg)
}

/* ---- H3 富脚本 ≥200 ---- */
{
  let rich = 0
  const seedPaths = [
    'apps/literacy-app/src/data/char-play-rich.js',
    'apps/literacy-app/src/data/char-play-catalog.js',
    'apps/literacy-app/scripts/data/char-play-seed.txt',
    'apps/literacy-app/scripts/data/char-play-rich.json'
  ]
  for (const rel of seedPaths) {
    const body = read(rel)
    if (!body) continue
    if (rel.endsWith('.txt')) {
      rich = Math.max(
        rich,
        body.split('\n').filter((l) => l.trim() && !l.trim().startsWith('#')).length
      )
    } else if (rel.endsWith('.json')) {
      try {
        const j = JSON.parse(body)
        rich = Math.max(rich, Array.isArray(j) ? j.length : Object.keys(j).length)
      } catch {
        /* ignore */
      }
    } else {
      const falses = body.match(/templateFallback\s*:\s*false/g)
      const entries = body.match(/char\s*:\s*['"]/g)
      if (falses) rich = Math.max(rich, falses.length)
      else if (entries) rich = Math.max(rich, entries.length)
    }
  }
  // Also count via runtime if available
  try {
    for (const rel of [
      'apps/literacy-app/src/data/char-play.js',
      'apps/literacy-app/src/data/charPlay.js'
    ]) {
      if (!exists(rel)) continue
      const mod = await import(path.join(root, rel))
      const list = mod.RICH_PLAY || mod.CHAR_PLAY_RICH || mod.richPlays
      if (Array.isArray(list)) rich = Math.max(rich, list.length)
      if (typeof mod.countRichPlays === 'function') {
        rich = Math.max(rich, mod.countRichPlays())
      }
    }
  } catch {
    /* ignore */
  }
  check(
    'H3',
    rich >= 200,
    `H3 富 play 脚本 ${rich} ≥ 200`,
    `H3 富 play 脚本 ${rich} < 200`
  )
}

/* ---- H4 认步字源默认播 ---- */
{
  const autoEty =
    (/phase\s*===\s*['"]intro['"]/.test(charDetail) || /认/.test(charDetail)) &&
    (/EtymologyStage/.test(charDetail) || /originOpen|autoOrigin|hasOrigin/.test(charDetail)) &&
    (/autoplay|originOpen\s*=\s*true|hasOrigin[\s\S]{0,200}EtymologyStage/.test(charDetail) ||
      /v-if="phase === 'intro'"[\s\S]*EtymologyStage/.test(charDetail) ||
      /认[\s\S]{0,800}EtymologyStage/.test(charDetail))
  // Stronger: intro phase mounts etymology without requiring click-first only
  const defaultShow =
    /hasOrigin[\s\S]{0,400}(v-if|v-show)[\s\S]{0,80}(phase|origin)/.test(charDetail) ||
    /phase === 'intro'[\s\S]{0,600}EtymologyStage/.test(charDetail) ||
    /phase === \"intro\"[\s\S]{0,600}EtymologyStage/.test(charDetail)
  check(
    'H4',
    Boolean(defaultShow || (autoEty && /ROUND15_H4|auto.*etymology|默认.*字源/i.test(charDetail))),
    'H4 认步默认挂载/播放字源舞台',
    'H4 认步仍把字源藏在可选按钮后'
  )
}

/* ---- H5 自动补齐管道 ---- */
{
  const gen =
    exists('apps/literacy-app/scripts/gen-char-play.mjs') ||
    exists('apps/literacy-app/scripts/gen-play.mjs')
  const marker =
    /ROUND15_H5|templateFallback|gen-char-play/.test(read('apps/literacy-app/scripts/gen-char-play.mjs')) ||
    /templateFallback/.test(read('apps/literacy-app/src/data/char-play.js')) ||
    /templateFallback/.test(read('apps/literacy-app/src/data/charPlay.js'))
  check(
    'H5',
    gen && marker,
    'H5 gen-char-play 自动补齐管道就位',
    'H5 缺少 gen-char-play 或 templateFallback 标记'
  )
}

/* ---- H6 写步引导 ---- */
{
  // 必须显式「进写步先示范再测验」编排；仅有手动「看老师写」按钮不算过线。
  const explicit =
    /ROUND15_H6/.test(charDetail) ||
    (/phase === ['"]trace['"]/.test(charDetail) &&
      /guideThenQuiz|demoBeforeQuiz|writeGuide|onEnterTrace|enterTrace/.test(charDetail)) ||
    (exists('apps/literacy-app/src/composables/useWriteGuide.js') &&
      /useWriteGuide/.test(charDetail))
  check(
    'H6',
    explicit,
    'H6 写步含引导示范再描红',
    'H6 写步未见引导示范编排'
  )
}

/* ---- H7 smoke ---- */
{
  const smokePlay =
    /ROUND15_H7/.test(literacySmoke) ||
    (/getCharPlay|CharPlayStage|char-play/.test(literacySmoke) &&
      /phase|玩|play/.test(literacySmoke))
  check(
    'H7',
    smokePlay,
    'H7 literacy smoke 覆盖 play/五步',
    'H7 smoke 未覆盖 play 流'
  )
}

/* ---- H8 往轮 ---- */
{
  const r13 = spawnSync('node', ['scripts/check-round13.mjs', '--json'], {
    cwd: root,
    encoding: 'utf8',
    timeout: 120000
  })
  let pass = 0
  try {
    const j = JSON.parse(r13.stdout || '{}')
    pass = j.passed ?? j.pass ?? 0
    if (j.results) pass = j.results.filter((r) => r.status === 'pass').length
  } catch {
    const m = (r13.stdout || '').match(/(\d+)\s*\/\s*8/)
    if (m) pass = Number(m[1])
  }
  check(
    'H8',
    pass >= 7,
    `H8 check:round13 ${pass}/8 ≥ 7`,
    `H8 check:round13 ${pass}/8 < 7（往轮退化或环境）`
  )
}

/* ---- report ---- */
const passed = results.filter((r) => r.status === 'pass').length
const summary = {
  round: 15,
  passed,
  total: EXPECTED,
  results
}

if (asJson) {
  console.log(JSON.stringify(summary, null, 2))
} else {
  console.log(`\nRound 15 check: ${passed}/${EXPECTED}\n`)
  for (const line of [...notes, ...fails]) console.log(line)
  if (passed < EXPECTED) process.exitCode = 1
}
