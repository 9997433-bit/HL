/**
 * Round 14 洪恩体验对齐硬门槛（v1.1 探针修订版）。
 * 标准：.agent_workspace/ROUND14-ACCEPTANCE.md
 *
 * 固定输出 8 个结果：H1–H8。基线（R13 集成 7/8、R14 功能未合入）预期 1/8（仅 H8 绿）。
 * `--json` 输出机读汇总供编排器聚合。
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

const hasDeviceIdentity = (device) => {
  if (typeof device === 'string') return device.trim().length >= 3
  if (!device || typeof device !== 'object' || Array.isArray(device)) return false
  return ['model', 'name', 'deviceModel', 'product'].some(
    (key) => typeof device[key] === 'string' && device[key].trim().length >= 3
  )
}

const referencesR13AndroidSim = (value) =>
  /(?:\.agent_workspace\/)?evidence\/r13\/android-sim(?:\/|$)/i.test(
    String(value).replaceAll('\\', '/')
  )

const countScenePages = async () => {
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
  return scenePages
}

/* H1 ASR 体验放行：available:true + recorded≥300 + GO 文档 + 带设备身份的真机 RTF 证据 + ROUND14_H1 */
{
  let available = false
  let recordedClips = 0
  try {
    const manifest = JSON.parse(read('apps/literacy-app/public/asr/manifest.json'))
    available = manifest.available === true
  } catch {
    available = false
  }
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
  } catch {
    recordedClips = 0
  }

  const releaseDoc =
    read('.agent_workspace/r14-followread-release.md') ||
    read('.agent_workspace/r13-followread-release.md')
  const releaseOk =
    releaseDoc.length > 600 &&
    /\bROUND14_H1\b/.test(releaseDoc) &&
    /GO|go-no-go.*go|verdict.*go/i.test(releaseDoc) &&
    !/NO-GO|no-go|BLOCKED/i.test(releaseDoc.match(/操作结论|verdict|当前决策/i)?.[0] ?? releaseDoc.slice(0, 400))

  const deviceRtfPath = '.agent_workspace/evidence/r14/asr/device-rtf.json'
  let deviceRtfOk = false
  try {
    const rtf = JSON.parse(read(deviceRtfPath))
    deviceRtfOk =
      evidenceFileOk(deviceRtfPath, 100) &&
      rtf.onDevice === true &&
      rtf.simulated === false &&
      hasDeviceIdentity(rtf.device) &&
      typeof rtf.rtfP95 === 'number' &&
      Number.isFinite(rtf.rtfP95) &&
      rtf.rtfP95 >= 0 &&
      rtf.rtfP95 <= 0.5
  } catch {
    deviceRtfOk = false
  }

  const harnessOk =
    /\bROUND14_H1\b/.test(readStripped('apps/literacy-app/scripts/test-asr-eval-set.mjs')) &&
    /assert|process\.exit/.test(readStripped('apps/literacy-app/scripts/test-asr-eval-set.mjs'))
  const smoke = /\bROUND14_H1_SMOKE\b/.test(literacySmoke)

  check(
    'H1',
    available && recordedClips >= 300 && releaseOk && deviceRtfOk && harnessOk && smoke,
    `H1 ASR 体验放行：available + recorded≥300 + 真机 RTF + ROUND14_H1`,
    `H1 ASR 体验未放行：available=${available}，recorded=${recordedClips}/300，release=${releaseOk}，deviceRtf=${deviceRtfOk}，harness=${harnessOk}，smoke=${smoke} —— r14-literacy-asr-finalize`
  )
}

/* H2 OCR 体验：App≥40/41 非空逐例矩阵 + 真机 B 段 + 队列无逾期 + ROUND14_H2 */
{
  let appRecall = 0
  let appTotal = 0
  let ocrSectionOk = false
  try {
    const matrix = JSON.parse(
      read('.agent_workspace/evidence/r14/ocr/app-webview-matrix.json')
    )
    const section = matrix.ocrSection ?? matrix['ocr-section']
    const rows = Array.isArray(matrix.samples)
      ? matrix.samples
      : Array.isArray(section)
        ? section
        : Array.isArray(section?.cases)
          ? section.cases
          : Array.isArray(section?.rows)
            ? section.rows
            : Array.isArray(section?.results)
              ? section.results
              : []
    const validRows = rows.filter((row) => row && typeof row === 'object')
    const declaredPass = Number(matrix.passCount ?? section?.passCount)
    const declaredTotal = Number(matrix.total ?? section?.total)
    appTotal = declaredTotal >= 41 ? declaredTotal : validRows.length
    appRecall = Number.isFinite(declaredPass)
      ? declaredPass
      : validRows.filter(
          (row) =>
            row.pass === true ||
            String(row.status ?? row.result ?? '').toLowerCase() === 'pass'
        ).length

    ocrSectionOk =
      appTotal >= 41 &&
      appRecall >= 40 &&
      validRows.length >= 41 &&
      Number.isFinite(declaredPass) &&
      Number.isFinite(declaredTotal) &&
      declaredPass === appRecall &&
      declaredTotal === appTotal &&
      matrix.simulated === true
  } catch {
    appRecall = 0
    appTotal = 0
    ocrSectionOk = false
  }

  let deviceBOk = false
  try {
    const b = JSON.parse(read('.agent_workspace/evidence/r14/android/ocr-device-b.json'))
    deviceBOk = b.pass === true && b.onDevice === true && b.simulated !== true
  } catch {
    deviceBOk = false
  }

  let queueOk = false
  try {
    const q = JSON.parse(read('apps/literacy-app/scripts/fixtures/ocr/regressions/queue.json'))
    const items = Array.isArray(q.items) ? q.items : []
    const overdue = items.filter(
      (i) => i && (i.status === 'new' || i.status === 'triaged') && i.dueRound && i.dueRound <= 14
    )
    queueOk = items.length >= 1 && overdue.length === 0
  } catch {
    queueOk = false
  }

  const reflux =
    read('.agent_workspace/r14-ocr-experience-loop.md') ||
    read('.agent_workspace/r13-ocr-regression-loop.md')
  const refluxOk =
    reflux.length > 600 &&
    /\bROUND14_H2\b/.test(reflux) &&
    /采集|标注|复现|闭环/i.test(reflux)

  const harnessSrc = readStripped('apps/literacy-app/scripts/test-ocr-device.mjs')
  const harnessOk =
    /\bROUND14_H2\b/.test(harnessSrc) &&
    /assert|process\.exit/.test(harnessSrc) &&
    /android|WebView|device|真机/i.test(harnessSrc)

  check(
    'H2',
    ocrSectionOk && deviceBOk && queueOk && refluxOk && harnessOk,
    `H2 OCR 体验闭环：App ${appRecall}/${appTotal} + 真机 B 段 + 队列 + ROUND14_H2`,
    `H2 OCR 体验未闭环：app=${appRecall}/${appTotal}，ocrSection=${ocrSectionOk}，deviceB=${deviceBOk}，queue=${queueOk}，reflux=${refluxOk}，harness=${harnessOk} —— r14-literacy-ocr-device-b`
  )
}

/* H3 绘本密度 ≥400 scene + 渲染 + ROUND14_H3 */
{
  const scenePages = await countScenePages()
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
  const marked = /\bROUND14_H3\b/.test(seedPool + literacySmoke)
  check(
    'H3',
    scenePages >= 400 && rendered && marked,
    `H3 绘本密度 ${scenePages} 页 scene（≥400）+ 渲染 + ROUND14_H3`,
    `H3 绘本未达标：scenePages=${scenePages}/400，rendered=${rendered}，ROUND14_H3=${marked} —— r14-literacy-books-batch2`
  )
}

/* H4 范唱全库 13/13 真人 + ROUND14_H4 */
{
  const humanVocals = new Set()
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
      const vRef = String(s.vocal || s.vocalAudio || '')
      const isHuman = s.humanStudio === true || /humanStudio\s*:\s*true/.test(JSON.stringify(s))
      if (isHuman && !/:\/\/|\.\./.test(vRef)) {
        const vm = vRef.match(/^[^?#]+\.(mp3|ogg|wav|m4a)$/i)
        if (vm) {
          const rel = vm[0].replace(/^\//, '')
          try {
            if (fs.statSync(path.join(root, 'apps/literacy-app/public', rel)).size >= 10240)
              humanVocals.add(rel)
          } catch {
            /* missing */
          }
        }
      }
    }
  } catch {
    songCount = 0
  }

  const batchDoc = read('.agent_workspace/r14-songs-vocal-full.md')
  const docOk =
    batchDoc.length > 500 &&
    /\bROUND14_H4\b/.test(batchDoc) &&
    /13\s*\/\s*13|全库|humanStudio|真人/i.test(batchDoc)

  check(
    'H4',
    songCount >= 13 && humanVocals.size >= 13 && docOk,
    `H4 范唱全库 ${humanVocals.size}/13 真人 + ROUND14_H4`,
    `H4 范唱未全库：songs=${songCount}，humanVocal=${humanVocals.size}/13，doc=${docOk} —— r14-literacy-vocal-full`
  )
}

/* H5 L1 朗读批次 + ROUND14_H5 */
{
  const doc = read('.agent_workspace/r14-tts-l1-batch.md')
  const docOk =
    doc.length > 500 &&
    /\bROUND14_H5\b/.test(doc) &&
    /L1|单元|字卡|朗读|TTS|真人/i.test(doc)

  let assetCount = 0
  const assetDir = path.join(root, 'apps/literacy-app/public/audio/tts-l1')
  if (fs.existsSync(assetDir)) {
    for (const f of fs.readdirSync(assetDir)) {
      if (/\.(mp3|ogg|wav|opus|m4a)$/i.test(f)) {
        try {
          if (fs.statSync(path.join(assetDir, f)).size >= 4096) assetCount++
        } catch {
          /* skip */
        }
      }
    }
  }

  const smoke = /\bROUND14_H5_SMOKE\b/.test(literacySmoke)
  check(
    'H5',
    docOk && assetCount >= 20 && smoke,
    `H5 L1 朗读批次：${assetCount} 资产 + 文档 + ROUND14_H5_SMOKE`,
    `H5 L1 朗读未闭环：assets=${assetCount}/20，doc=${docOk}，smoke=${smoke} —— r14-literacy-tts-l1`
  )
}

/* H6 真机签核：evidence/r14/android 非 simulated + GO 定案 + ROUND14_H6 */
{
  const signoffPath = '.agent_workspace/evidence/r14/android/device-signoff.json'
  const signoffRaw = read(signoffPath)
  let signoffOk = false
  try {
    const j = JSON.parse(signoffRaw)
    signoffOk =
      j.pass === true &&
      j.onDevice === true &&
      j.simulated === false &&
      Array.isArray(j.devices) &&
      j.devices.length >= 2 &&
      !referencesR13AndroidSim(signoffRaw)
  } catch {
    signoffOk = false
  }

  const decision =
    read('.agent_workspace/r14-android-device-decision.md') ||
    read('.agent_workspace/r12-android-device-decision.md')
  const decisionOk =
    decision.length > 600 &&
    /\bROUND14_H6\b/.test(decision) &&
    /\bGO\b|发布签核.*GO|verdict.*go/i.test(decision) &&
    !/NO-GO|BLOCKED/i.test(decision.match(/操作结论|verdict|当前决策|发布签核/i)?.[0] ?? '')

  const recordDoc = read('.agent_workspace/r14-android-device-record.md')
  const recordOk =
    recordDoc.length > 800 &&
    /真机|onDevice|不等价模拟/i.test(recordDoc) &&
    /evidence\/r14\/android/.test(recordDoc) &&
    /\bROUND14_H6\b/.test(recordDoc)
  const noR13SimPath =
    !referencesR13AndroidSim(decision) && !referencesR13AndroidSim(recordDoc)

  check(
    'H6',
    signoffOk &&
      decisionOk &&
      recordOk &&
      noR13SimPath &&
      evidenceFileOk(signoffPath, 100),
    'H6 真机签核：device-signoff + GO 定案 + 签核文档 + ROUND14_H6',
    `H6 真机未签核：signoff=${signoffOk}，decision=${decisionOk}，record=${recordOk}，noR13SimPath=${noR13SimPath} —— r14-android-device-matrix`
  )
}

/* H7 商店内测实提 + ROUND14_H7 */
{
  const submit = read('.agent_workspace/r14-store-submission-record.md')
  const conclusionBlocked = /操作结论：\*\*BLOCKED|当前决策：\*\*NO-GO\/BLOCKED/i.test(submit)
  const receiptSection = submit.match(/## 6\.[\s\S]*/)?.[0] ?? ''
  const filledReceipt =
    receiptSection.length > 200 &&
    /20[0-9]{2}-[0-9]{2}-[0-9]{2}/.test(receiptSection) &&
    !/\[待填\]/.test(receiptSection)
  const submitOk =
    submit.length > 600 &&
    /内测|Play Console|TestFlight|track|轨道/i.test(submit) &&
    /\bROUND14_H7\b/.test(submit) &&
    /日期|date/i.test(submit) &&
    /SHA|sha256|commit/i.test(submit) &&
    /版本|version|build/i.test(submit) &&
    !conclusionBlocked &&
    (filledReceipt || /\b状态：\s*(SUBMITTED|VERIFIED)\b/i.test(submit))
  check(
    'H7',
    submitOk,
    'H7 商店内测实提 + ROUND14_H7',
    `H7 商店内测未闭环：submit=${submitOk} —— r14-store-internal-test`
  )
}

/* H8 R13+R12 不退化 */
{
  const r12 = spawnSync(process.execPath, ['scripts/check-round12.mjs'], {
    cwd: root,
    encoding: 'utf8',
  })
  const r13 = spawnSync(process.execPath, ['scripts/check-round13.mjs'], {
    cwd: root,
    encoding: 'utf8',
  })
  const r12Ok = r12.status === 0 && /8\/8/.test(r12.stdout + r12.stderr)
  const r13Pass = (r13.stdout + r13.stderr).match(/✓/g)?.length ?? 0
  const r13Ok = r13Pass >= 7
  check(
    'H8',
    r12Ok && r13Ok,
    `H8 往轮不退化：round12 8/8 + round13 ${r13Pass}/8`,
    `H8 退化：round12=${r12Ok}，round13Pass=${r13Pass}/8`
  )
}

if (results.length !== EXPECTED) {
  const msg = `门禁自身结果数异常：${results.length}/${EXPECTED}，请修复 check-round14.mjs`
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
  console.log(`\nRound 14 体验门禁：${notes.length}/${EXPECTED} 项通过，${fails.length} 项失败。`)
  if (fails.length)
    console.log('说明：R14 功能分支未全部合并时 FAIL 属预期红灯；体验 flip 目标 7/8 或 8/8。')
}

process.exit(fails.length ? 1 : 0)
