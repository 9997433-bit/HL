/**
 * Round 13 真机通道与体验终局硬门槛（v1.0）。
 * 基线（R12 闭合、R13 功能未合入）预期 1/8（仅 H8 绿）。
 */

import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
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
const readStripped = (rel) => stripComments(read(rel))

const literacySmoke = readStripped('apps/literacy-app/scripts/smoke.mjs')
const mathSmoke = readStripped('apps/math-app/scripts/smoke.mjs')

/* H1 ASR 放行 */
{
  let available = false
  let filesOk = false
  try {
    const j = JSON.parse(read('apps/literacy-app/public/asr/manifest.json'))
    available = j.available === true
    filesOk = Array.isArray(j.files) && j.files.length >= 1
  } catch {
    /* fail-closed */
  }
  const freezeDoc = read('.agent_workspace/r13-asr-freeze-set.md')
  const freezeOk =
    freezeDoc.length > 800 &&
    /冻结集|freeze[\s_-]?set/i.test(freezeDoc) &&
    /≥?\s*50|条目|条数/.test(freezeDoc)
  const marked =
    /\bROUND13_H1\b/.test(readStripped('apps/literacy-app/scripts/test-asr-eval-set.mjs')) ||
    /\bROUND13_H1_SMOKE\b/.test(literacySmoke)
  check(
    'H1',
    (available || freezeOk) && filesOk && marked,
    'H1 ASR 放行：available 或冻结集≥50 + files 落库 + ROUND13_H1',
    `H1 ASR 未放行：available=${available}，freeze=${freezeOk}，files=${filesOk}，marked=${marked}`
  )
}

/* H2 OCR Android 模拟 */
{
  const sim = read('.agent_workspace/evidence/r13/android-sim/report.json')
  let simOk = false
  try {
    const j = JSON.parse(sim)
    simOk = j.simulated === true && j.ocr?.pass === true
  } catch {
    simOk = false
  }
  const reflux = read('.agent_workspace/r13-ocr-regression-loop.md')
  const refluxOk = reflux.length > 400 && /回流|regression|失败样本/i.test(reflux)
  const marked = /\bROUND13_H2\b/.test(readStripped('apps/literacy-app/scripts/test-ocr-device.mjs'))
  check(
    'H2',
    simOk && refluxOk && marked,
    'H2 OCR Android 模拟 + 失败回流 + ROUND13_H2',
    `H2 OCR Android 未闭环：sim=${simOk}，reflux=${refluxOk}，marked=${marked}`
  )
}

/* H3 绘本终局 ≥200 页 */
{
  let scenePages = 0
  try {
    const mod = await import('../apps/literacy-app/src/data/books.js')
    const books = mod.BOOKS ?? mod.default ?? []
    for (const b of Array.isArray(books) ? books : []) {
      for (const p of Array.isArray(b?.pages) ? b.pages : []) {
        const els = Array.isArray(p?.scene) ? p.scene : []
        if (els.filter((el) => el && typeof el === 'object').length >= 2) scenePages++
      }
    }
  } catch {
    scenePages = 0
  }
  const marked = /\bROUND13_H3\b/.test(
    readStripped('apps/literacy-app/src/data/books.js') + literacySmoke
  )
  check(
    'H3',
    scenePages >= 200 && marked,
    `H3 绘本终局 ${scenePages} 页 scene（≥200）+ ROUND13_H3`,
    `H3 绘本未终局：scenePages=${scenePages}/200，marked=${marked}`
  )
}

/* H4 范唱批次 ≥3 */
{
  const vocalFiles = new Set()
  try {
    const mod = await import('../apps/literacy-app/src/data/songs.js')
    for (const s of mod.SONGS ?? []) {
      const v = String(s?.vocal || s?.vocalAudio || '')
      if (/vocal/i.test(v) && /\.(mp3|ogg|wav|m4a)$/i.test(v)) {
        const rel = v.replace(/^\//, '')
        try {
          if (fs.statSync(path.join(root, 'apps/literacy-app/public', rel)).size >= 8192)
            vocalFiles.add(rel)
        } catch {
          /* missing */
        }
      }
    }
  } catch {
    /* empty */
  }
  const marked = /\bROUND13_H4\b/.test(readStripped('apps/literacy-app/src/data/songs.js') + literacySmoke)
  check(
    'H4',
    vocalFiles.size >= 3 && marked,
    `H4 范唱批次 ${vocalFiles.size} 首（≥3）+ ROUND13_H4`,
    `H4 范唱未批次：vocal=${vocalFiles.size}/3，marked=${marked}`
  )
}

/* H5 lift 准实验 */
{
  const exp = read('.agent_workspace/r13-reco-lift-experiment.md')
  const expOk =
    exp.length > 600 &&
    /对照|准实验|A\/B|lift|因果/i.test(exp) &&
    /ROUND13_H5|adoptionRate|recoLift/i.test(exp + readStripped('apps/math-app/src/stores/progress.js'))
  const smoke = /\bROUND13_H5_SMOKE\b/.test(mathSmoke)
  check(
    'H5',
    expOk && smoke,
    'H5 lift 准实验口径 + ROUND13_H5_SMOKE',
    `H5 lift 未闭环：exp=${expOk}，smoke=${smoke}`
  )
}

/* H6 Android 模拟 harness */
{
  const report = read('.agent_workspace/evidence/r13/android-sim/report.json')
  let simOk = false
  try {
    const j = JSON.parse(report)
    simOk =
      j.simulated === true &&
      j.literacy?.apkSha256 &&
      j.math?.apkSha256 &&
      j.literacy?.smokeRoutes >= 100 &&
      j.math?.smokeRoutes >= 15
  } catch {
    simOk = false
  }
  const harness = readStripped('scripts/android-sim.mjs')
  const harnessOk = harness.length > 500 && /\bROUND13_H6\b/.test(harness)
  check(
    'H6',
    simOk && harnessOk,
    'H6 Android 模拟：双 APK + android-sim 报告 + ROUND13_H6',
    `H6 Android 模拟未闭环：sim=${simOk}，harness=${harnessOk}`
  )
}

/* H7 商店实提 */
{
  const submit = read('.agent_workspace/r13-store-submission-record.md')
  const submitOk =
    submit.length > 600 &&
    /提交|内测|Play Console|TestFlight|track|轨道/i.test(submit) &&
    /\bROUND13_H7\b|日期|SHA|版本/.test(submit)
  check(
    'H7',
    submitOk,
    'H7 商店真实提交/内测记录 + ROUND13_H7',
    `H7 商店实提未闭环：submit=${submitOk}`
  )
}

/* H8 R12 不退化 */
{
  const r12 = spawnSync(process.execPath, ['scripts/check-round12.mjs'], {
    cwd: root,
    encoding: 'utf8',
  })
  const ok = r12.status === 0 && /8\/8/.test(r12.stdout + r12.stderr)
  check('H8', ok, 'H8 Round 12 门禁 8/8 无退化', `H8 Round 12 退化 exit=${r12.status}`)
}

if (results.length !== EXPECTED) {
  const msg = `门禁自身结果数异常：${results.length}/${EXPECTED}`
  results.push({ id: 'meta', status: 'fail', msg })
  fails.push(`✗ ${msg}`)
}

if (asJson) {
  console.log(JSON.stringify({ passed: notes.length, failed: fails.length, results }, null, 2))
} else {
  notes.forEach((n) => console.log(' ', n))
  if (fails.length) {
    console.log('')
    fails.forEach((f) => console.log(' ', f))
  }
  console.log(`\nRound 13 终局门禁：${notes.length}/${EXPECTED} 项通过，${fails.length} 项失败。`)
  if (fails.length) console.log('说明：R13 功能分支未全部合并时 FAIL 属预期红灯；集成后必须 8/8。')
}

process.exit(fails.length ? 1 : 0)
