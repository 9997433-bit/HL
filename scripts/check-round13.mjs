/**
 * Round 13 真机通道与体验终局硬门槛（v1.1 探针修订版）。
 * 标准：.agent_workspace/ROUND13-ACCEPTANCE.md（探针细则 §2，v1.1 修订记录见 §2 开头）
 *
 * 固定输出 8 个结果：H1–H8。基线（R12 闭合、R13 功能未合入）预期 1/8（仅 H8 绿）。
 * `--json` 输出机读汇总（passed/failed/results）供编排器聚合。
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
/** 剥 HTML / 块 / 整行 // 注释——探针信号必须写成代码（常量、断言名或行内尾注）。 */
const stripComments = (src) =>
  src
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '')
const readStripped = (rel) => stripComments(read(rel))

const literacySmoke = readStripped('apps/literacy-app/scripts/smoke.mjs')
const mathSmoke = readStripped('apps/math-app/scripts/smoke.mjs')

const sha256File = (absPath) => {
  try {
    return crypto.createHash('sha256').update(fs.readFileSync(absPath)).digest('hex')
  } catch {
    return ''
  }
}

const evidenceFileOk = (rel, minBytes = 200) => {
  try {
    return fs.statSync(path.join(root, rel)).size >= minBytes
  } catch {
    return false
  }
}

/* H1 ASR 放行：files[] 落盘校验 +（available 放行腿 或 冻结集≥50 实体腿）+ harness + ROUND13_H1_SMOKE（§2.1）
   v1.0 漏洞：available||freeze 短路；freeze 只认 md 词表不认 JSON 实体数；files 只数 length≥1；
   marked 认 harness OR smoke，文档可跨填。 */
{
  let filesOk = false
  let packBytes = 0
  let available = false
  try {
    const j = JSON.parse(read('apps/literacy-app/public/asr/manifest.json'))
    available = j.available === true
    const files = Array.isArray(j.files) ? j.files : []
    let verified = 0
    for (const f of files) {
      if (
        !f ||
        typeof f !== 'object' ||
        typeof f.path !== 'string' ||
        !f.path ||
        typeof f.sha256 !== 'string' ||
        !/^[a-f0-9]{64}$/i.test(f.sha256) ||
        typeof f.bytes !== 'number' ||
        f.bytes <= 0
      )
        continue
      const abs = path.join(root, 'apps/literacy-app/public', f.path.replace(/^\//, ''))
      try {
        const st = fs.statSync(abs)
        if (st.size >= f.bytes && sha256File(abs).toLowerCase() === f.sha256.toLowerCase()) {
          verified++
          packBytes += st.size
        }
      } catch {
        /* 落盘缺失或哈希不符 */
      }
    }
    filesOk = verified >= 1 && packBytes <= 60 * 1024 * 1024
  } catch {
    filesOk = false
    available = false
  }

  let recordedClips = 0
  let skeletonClips = 0
  try {
    const evalSet = JSON.parse(read('apps/literacy-app/scripts/data/asr-eval-set.json'))
    const clips = Array.isArray(evalSet.clips) ? evalSet.clips : []
    recordedClips = clips.filter(
      (c) =>
        c &&
        typeof c === 'object' &&
        c.status === 'recorded' &&
        (c.audio || c.audioPath || c.wav)
    ).length
    skeletonClips = clips.filter((c) => c && typeof c === 'object' && c.id && c.spoken).length
  } catch {
    recordedClips = 0
    skeletonClips = 0
  }

  const freezeDoc = read('.agent_workspace/r13-asr-freeze-set.md')
  const freezeDocOk =
    freezeDoc.length > 800 &&
    /冻结集|freeze[\s_-]?set/i.test(freezeDoc) &&
    /\bROUND13_H1\b/.test(freezeDoc) &&
    (/RTF|真机|Android|基准/i.test(freezeDoc) || /实录|recorded/i.test(freezeDoc))
  const freezeLeg = (recordedClips >= 50 || skeletonClips >= 50) && freezeDocOk

  const releaseDoc = read('.agent_workspace/r13-followread-release.md')
  const releaseLeg =
    available &&
    releaseDoc.length > 600 &&
    /Go|No-Go|PASS|放行|available/i.test(releaseDoc) &&
    /RTF|Android|真机|性能/i.test(releaseDoc) &&
    /\bROUND13_H1\b/.test(releaseDoc)

  const evalScript = readStripped('apps/literacy-app/scripts/test-asr-eval-set.mjs')
  const harnessOk =
    /\bROUND13_H1\b/.test(evalScript) &&
    /assert|process\.exit/.test(evalScript) &&
    /跑分|eval|评测|RTF|wer|cer/i.test(evalScript)
  const smoke = /\bROUND13_H1_SMOKE\b/.test(literacySmoke)

  check(
    'H1',
    filesOk && (releaseLeg || freezeLeg) && harnessOk && smoke,
    `H1 ASR 放行：files[] 落盘 ${packBytes}B + 放行/冻结集腿 + harness + ROUND13_H1_SMOKE`,
    `H1 ASR 未放行：files=${filesOk}，release=${releaseLeg}，freeze=${freezeLeg}（recorded=${recordedClips}，skeleton=${skeletonClips}），harness=${harnessOk}，smoke=${smoke} —— r13-literacy-asr-release`
  )
}

/* H2 OCR Android 模拟 + 失败回流（§2.2）
   v1.0 漏洞：手搓 report.json 即过；回流 doc 词表即过；harness 只查 ROUND13_H2 无 assert/Android 信号。 */
{
  const evDir = '.agent_workspace/evidence/r13/android-sim'
  const reportRaw = read(`${evDir}/report.json`)
  let simOk = false
  try {
    const j = JSON.parse(reportRaw)
    const steps = Array.isArray(j.steps) ? j.steps : []
    const stepPass = (name) => steps.some((s) => s?.step === name && s.pass === true)
    simOk =
      j.simulated === true &&
      j.ocr?.pass === true &&
      stepPass('ocr-device-a') &&
      evidenceFileOk(`${evDir}/ocr-device-a.log`, 200)
  } catch {
    simOk = false
  }
  const reflux = read('.agent_workspace/r13-ocr-regression-loop.md')
  const refluxOk =
    reflux.length > 600 &&
    /回流|regression|失败样本|tier/i.test(reflux) &&
    /采集|标注|复现|闭环|harness/i.test(reflux) &&
    /\bROUND13_H2\b/.test(reflux)
  const harnessSrc = readStripped('apps/literacy-app/scripts/test-ocr-device.mjs')
  const marked =
    /\bROUND13_H2\b/.test(harnessSrc) &&
    /assert|process\.exit/.test(harnessSrc) &&
    /android|WebView|adb|模拟|emulator|device/i.test(harnessSrc)
  check(
    'H2',
    simOk && refluxOk && marked,
    'H2 OCR Android 模拟 + 失败回流设计 + harness ROUND13_H2',
    `H2 OCR Android 未闭环：sim=${simOk}，reflux=${refluxOk}，harness=${marked} —— r13-literacy-ocr-android`
  )
}

/* H3 绘本终局 ≥200 页 scene + 渲染不退化（§2.3）
   v1.0 漏洞：只数 scene 页，不查 BookPageScene 渲染腿（R12 H3 同款复发）。 */
{
  let scenePages = 0
  try {
    const mod = await import('../apps/literacy-app/src/data/books.js')
    const books = mod.BOOKS ?? mod.default ?? []
    for (const b of Array.isArray(books) ? books : []) {
      for (const p of Array.isArray(b?.pages) ? b.pages : []) {
        const els = Array.isArray(p?.scene)
          ? p.scene
          : Array.isArray(p?.sceneElements)
            ? p.sceneElements
            : []
        if (els.filter((el) => el && typeof el === 'object').length >= 2) scenePages++
      }
    }
  } catch {
    scenePages = 0
  }
  const comp = readStripped('apps/literacy-app/src/components/BookPageScene.vue')
  const view = readStripped('apps/literacy-app/src/views/BookReadView.vue')
  const rendered = comp.length > 300 || /scene/i.test(view)
  const seedPool =
    readStripped('apps/literacy-app/src/data/books.js') +
    (exists('apps/literacy-app/src/data/books')
      ? fs
          .readdirSync(path.join(root, 'apps/literacy-app/src/data/books'))
          .map((f) => readStripped(`apps/literacy-app/src/data/books/${f}`))
          .join('\n')
      : '')
  const marked = /\bROUND13_H3\b/.test(seedPool + literacySmoke)
  check(
    'H3',
    scenePages >= 200 && rendered && marked,
    `H3 绘本终局 ${scenePages} 页 scene（≥200）+ 渲染接线 + ROUND13_H3`,
    `H3 绘本未终局：scenePages=${scenePages}/200，rendered=${rendered}，ROUND13_H3=${marked} —— r13-literacy-books-final`
  )
}

/* H4 范唱批次 ≥3 首人声 + R12 13/13 不退化（§2.4）
   v1.0 漏洞：vocal 路径含 vocal 字样即过，不要求批次/人声质量；不查 R12 全库音频腿。 */
{
  const audioFiles = new Set()
  const vocalFiles = new Set()
  let songCount = 0
  try {
    const mod = await import('../apps/literacy-app/src/data/songs.js')
    const list = mod.SONGS ?? mod.default ?? []
    const seen = new Set()
    for (const s of Array.isArray(list) ? list : []) {
      if (!s || typeof s !== 'object' || !s.id || seen.has(s.id)) continue
      seen.add(s.id)
      if (!(s.title ?? s.name)) continue
      songCount++
      const ref = String(s.audio || s.src || s.melodyUrl || '')
      if (!/:\/\/|\.\./.test(ref)) {
        const m = ref.match(/^[^?#]+\.(mp3|ogg|wav|m4a)$/i)
        if (m) {
          const rel = m[0].replace(/^\//, '')
          try {
            if (fs.statSync(path.join(root, 'apps/literacy-app/public', rel)).size >= 10240)
              audioFiles.add(rel)
          } catch {
            /* missing */
          }
        }
      }
      const vRef = String(s.vocal || s.vocalAudio || '')
      if (!/:\/\/|\.\./.test(vRef) && /vocal/i.test(vRef)) {
        const vm = vRef.match(/^[^?#]+\.(mp3|ogg|wav|m4a)$/i)
        if (vm) {
          const rel = vm[0].replace(/^\//, '')
          try {
            if (fs.statSync(path.join(root, 'apps/literacy-app/public', rel)).size >= 10240)
              vocalFiles.add(rel)
          } catch {
            /* missing */
          }
        }
      }
    }
  } catch {
    songCount = 0
  }

  const vocalDir = path.join(root, 'apps/literacy-app/public/audio/vocal-batch')
  if (fs.existsSync(vocalDir)) {
    for (const f of fs.readdirSync(vocalDir)) {
      if (/\.(mp3|ogg|wav|m4a)$/i.test(f)) {
        try {
          if (fs.statSync(path.join(vocalDir, f)).size >= 10240)
            vocalFiles.add(`audio/vocal-batch/${f}`)
        } catch {
          /* skip */
        }
      }
    }
  }

  const batchDoc = read('.agent_workspace/r13-songs-vocal-batch.md')
  const batchMetaOk =
    batchDoc.length > 500 &&
    /范唱|人声|vocal/i.test(batchDoc) &&
    /真人|录音|piper|高质量|批次/i.test(batchDoc) &&
    /\bROUND13_H4\b/.test(batchDoc)
  const marked = /\bROUND13_H4\b/.test(readStripped('apps/literacy-app/src/data/songs.js') + literacySmoke)
  const vocalOk = vocalFiles.size >= 3 && batchMetaOk

  check(
    'H4',
    songCount >= 13 && audioFiles.size >= 13 && vocalOk && marked,
    `H4 范唱批次 ${vocalFiles.size} 首（≥3）+ 13/13 音频 + ROUND13_H4`,
    `H4 范唱未批次：songs=${songCount}/13，audio=${audioFiles.size}/13，vocal=${vocalFiles.size}/3，batch=${batchMetaOk}，ROUND13_H4=${marked} —— r13-literacy-vocal-batch`
  )
}

/* H5 lift 准实验口径 + ROUND13_H5_SMOKE（§2.5）
   v1.0 漏洞：exp 池拼接 progress.js——store 写 lift 字段即点亮 exp；smoke 单信号。 */
{
  const exp = read('.agent_workspace/r13-reco-lift-experiment.md')
  const expOk =
    exp.length > 600 &&
    /对照|准实验|A\/B|lift|因果|实验组/i.test(exp) &&
    /%|百分点|baseline|对照组|趋势|报表/.test(exp) &&
    /\bROUND13_H5\b/.test(exp)
  const smoke = /\bROUND13_H5_SMOKE\b/.test(mathSmoke)
  check(
    'H5',
    expOk && smoke,
    'H5 lift 准实验口径 + ROUND13_H5_SMOKE',
    `H5 lift 未闭环：exp=${expOk}，smoke=${smoke} —— r13-math-lift-experiment`
  )
}

/* H6 Android 模拟 harness 首条证据（§2.6）
   v1.0 漏洞：手搓 report.json 即过；harness 长度+注释块 ROUND13_H6 即过；不要求证据日志/APK 落盘/签核文档。 */
{
  const evDir = '.agent_workspace/evidence/r13/android-sim'
  const reportRaw = read(`${evDir}/report.json`)
  let simOk = false
  try {
    const j = JSON.parse(reportRaw)
    const steps = Array.isArray(j.steps) ? j.steps : []
    const stepPass = (name) => steps.some((s) => s?.step === name && s.pass === true)
    const mandatory = [
      'build:all',
      'sync:android',
      'check:android',
      'gradle:literacy',
      'gradle:math',
    ]
    const stepsOk = mandatory.every(stepPass)
    const lit = j.literacy ?? {}
    const mat = j.math ?? {}
    const litApkRel = 'apps/literacy-app/android/app/build/outputs/apk/debug/app-debug.apk'
    const matApkRel = 'apps/math-app/android/app/build/outputs/apk/debug/app-debug.apk'
    const litApkOk =
      lit.apkSha256 &&
      exists(litApkRel) &&
      sha256File(path.join(root, litApkRel)).toLowerCase() === String(lit.apkSha256).toLowerCase()
    const matApkOk =
      mat.apkSha256 &&
      exists(matApkRel) &&
      sha256File(path.join(root, matApkRel)).toLowerCase() === String(mat.apkSha256).toLowerCase()
    const logsOk =
      evidenceFileOk(`${evDir}/smoke-literacy.log`, 500) &&
      evidenceFileOk(`${evDir}/smoke-math.log`, 200) &&
      evidenceFileOk(`${evDir}/gradle-literacy.log`, 200) &&
      evidenceFileOk(`${evDir}/gradle-math.log`, 200)
    simOk =
      j.simulated === true &&
      stepsOk &&
      lit.smokePass === true &&
      mat.smokePass === true &&
      lit.smokeProblems === 0 &&
      mat.smokeProblems === 0 &&
      lit.smokeRoutes >= 100 &&
      mat.smokeRoutes >= 15 &&
      litApkOk &&
      matApkOk &&
      logsOk
  } catch {
    simOk = false
  }

  const recordDoc = read('.agent_workspace/r13-android-sim-record.md')
  const recordOk =
    recordDoc.length > 800 &&
    /simulated|模拟|不等价真机/i.test(recordDoc) &&
    /evidence\/r13\/android-sim|android-sim/.test(recordDoc) &&
    /\bROUND13_H6\b/.test(recordDoc)

  const harness = readStripped('scripts/android-sim.mjs')
  const harnessOk =
    harness.length > 500 &&
    /\bROUND13_H6\b/.test(harness) &&
    /process\.exit|spawnSync/.test(harness) &&
    /simulated\s*:\s*true|'simulated'\s*,\s*true/.test(harness)

  check(
    'H6',
    simOk && recordOk && harnessOk,
    'H6 Android 模拟：双 APK 落盘 + 证据日志 + 签核文档 + ROUND13_H6 harness',
    `H6 Android 模拟未闭环：sim=${simOk}，record=${recordOk}，harness=${harnessOk} —— r13-android-sim-harness`
  )
}

/* H7 商店真实提交/内测（§2.7）
   v1.0 漏洞：ROUND13_H7 OR 日期/SHA/版本——缺字面标记或缺日期仍可过。 */
{
  const submit = read('.agent_workspace/r13-store-submission-record.md')
  const conclusionBlocked = /操作结论：\*\*BLOCKED|当前决策：\*\*NO-GO\/BLOCKED/i.test(submit)
  const receiptSection = submit.match(/## 6\.[\s\S]*/)?.[0] ?? ''
  const filledReceipt =
    receiptSection.length > 200 &&
    /20[0-9]{2}-[0-9]{2}-[0-9]{2}/.test(receiptSection) &&
    !/\[待填\]/.test(receiptSection)
  const submitOk =
    submit.length > 600 &&
    /提交|内测|Play Console|TestFlight|track|轨道/i.test(submit) &&
    /\bROUND13_H7\b/.test(submit) &&
    /日期|date/i.test(submit) &&
    /SHA|sha256|commit/i.test(submit) &&
    /版本|version|build/i.test(submit) &&
    !conclusionBlocked &&
    (filledReceipt || /\b状态：\s*(SUBMITTED|VERIFIED)\b/i.test(submit))
  check(
    'H7',
    submitOk,
    'H7 商店真实提交/内测记录 + ROUND13_H7',
    `H7 商店实提未闭环：submit=${submitOk} —— r13-store-submit`
  )
}

/* H8 R12 不退化（§2.8） */
{
  const r12 = spawnSync(process.execPath, ['scripts/check-round12.mjs'], {
    cwd: root,
    encoding: 'utf8',
  })
  const ok = r12.status === 0 && /8\/8/.test(r12.stdout + r12.stderr)
  check('H8', ok, 'H8 Round 12 门禁 8/8 无退化', `H8 Round 12 退化 exit=${r12.status}`)
}

if (results.length !== EXPECTED) {
  const msg = `门禁自身结果数异常：${results.length}/${EXPECTED}，请修复 check-round13.mjs`
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
