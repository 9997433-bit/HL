/**
 * Round 12 洪恩级体验全量落地硬门槛（v1.0）。
 * 标准：.agent_workspace/ROUND12-ACCEPTANCE.md（待 #3 验收子代理 v1.1 修订）
 *
 * 固定输出 8 个结果：H1–H8。基线（R11 闭合、R12 功能未合入）预期 1/8（仅 H8 绿）。
 * `--json` 输出机读汇总。
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

/* H1 ASR 模型落库：files[] 实体 或 available:true + Go/No-Go 更新 + ROUND12_H1 */
{
  let filesOk = false
  let available = false
  try {
    const j = JSON.parse(read('apps/literacy-app/public/asr/manifest.json'))
    available = j.available === true
    const files = Array.isArray(j.files) ? j.files : []
    filesOk = files.some(
      (f) =>
        f &&
        typeof f === 'object' &&
        typeof f.path === 'string' &&
        f.path.length > 0 &&
        typeof f.sha256 === 'string' &&
        /^[a-f0-9]{64}$/i.test(f.sha256) &&
        typeof f.bytes === 'number' &&
        f.bytes > 0
    )
  } catch {
    filesOk = false
    available = false
  }
  const gonogo = read('.agent_workspace/r12-followread-ship.md')
  const gonogoOk =
    gonogo.length > 600 ||
    (read('.agent_workspace/r11-followread-gonogo.md').length > 800 &&
      /\bROUND12_H1\b|模型落库|files\[\]|available/.test(
        read('.agent_workspace/r11-followread-gonogo.md')
      ))
  const marked =
    /\bROUND12_H1\b/.test(readStripped('apps/literacy-app/scripts/test-asr-eval-set.mjs')) ||
    /\bROUND12_H1_SMOKE\b/.test(literacySmoke) ||
    /\bROUND12_H1\b/.test(read('apps/literacy-app/public/asr/manifest.json'))
  check(
    'H1',
    (filesOk || available) && gonogoOk && marked,
    'H1 ASR 落库：files[] 或 available + Go/No-Go 更新 + ROUND12_H1',
    `H1 ASR 未落库：files=${filesOk}，available=${available}，gonogo=${gonogoOk}，marked=${marked} —— r12-literacy-asr-ship`
  )
}

/* H2 OCR 系统化：real ≥8 去重 + 矩阵 tier + 真机 harness + ROUND12_H2 */
{
  const dir = path.join(root, 'apps/literacy-app/scripts/fixtures/ocr')
  const PNG_MAGIC = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])
  const hashes = new Set()
  if (fs.existsSync(dir)) {
    for (const f of fs.readdirSync(dir)) {
      if (!/^real/i.test(f) || !f.endsWith('.png')) continue
      try {
        const buf = fs.readFileSync(path.join(dir, f))
        if (buf.length >= 4096 && buf.subarray(0, 8).equals(PNG_MAGIC))
          hashes.add(crypto.createHash('sha1').update(buf).digest('hex'))
      } catch {
        /* skip */
      }
    }
  }
  const real = hashes.size
  const matrixDoc = read('.agent_workspace/r12-ocr-matrix.md')
  const samplesJson = read('apps/literacy-app/scripts/fixtures/ocr/real-samples.json')
  const tierOk =
    (matrixDoc.length > 500 && /光照|角度|纸质|矩阵/i.test(matrixDoc)) ||
    (/light|angle|paper|tier/i.test(samplesJson) && /light|angle|paper|tier/i.test(samplesJson))
  const harness =
    readStripped('apps/literacy-app/scripts/test-ocr-device.mjs').length > 200 ||
    (read('.agent_workspace/r12-ocr-device-harness.md').length > 500 &&
      /真机|模拟器|adb|WebView|harness/i.test(read('.agent_workspace/r12-ocr-device-harness.md')))
  const marked = /\bROUND12_H2\b/.test(readStripped('apps/literacy-app/scripts/test-ocr-accuracy.mjs'))
  check(
    'H2',
    real >= 8 && tierOk && harness && marked,
    `H2 OCR 系统化 ${real} 张 + tier 矩阵 + 真机 harness + ROUND12_H2`,
    `H2 OCR 未系统化：real=${real}/8，tier=${tierOk}，harness=${harness}，ROUND12_H2=${marked} —— r12-literacy-ocr-device`
  )
}

/* H3 绘本铺开：scene 页 ≥60 + ROUND12_H3 */
{
  let scenePages = 0
  try {
    const mod = await import('../apps/literacy-app/src/data/books.js')
    const books = mod.BOOKS ?? mod.default ?? []
    for (const b of Array.isArray(books) ? books : []) {
      for (const p of Array.isArray(b?.pages) ? b.pages : []) {
        const els = Array.isArray(p?.scene) ? p.scene : Array.isArray(p?.sceneElements) ? p.sceneElements : []
        if (els.filter((el) => el && typeof el === 'object').length >= 2) scenePages++
      }
    }
  } catch {
    scenePages = 0
  }
  const seedPool =
    readStripped('apps/literacy-app/src/data/books.js') +
    (exists('apps/literacy-app/src/data/books')
      ? fs
          .readdirSync(path.join(root, 'apps/literacy-app/src/data/books'))
          .map((f) => readStripped(`apps/literacy-app/src/data/books/${f}`))
          .join('\n')
      : '')
  const marked = /\bROUND12_H3\b/.test(seedPool + literacySmoke)
  check(
    'H3',
    scenePages >= 60 && marked,
    `H3 绘本场景铺开 ${scenePages} 页（≥60）+ ROUND12_H3`,
    `H3 绘本未铺开：scenePages=${scenePages}/60，ROUND12_H3=${marked} —— r12-literacy-books-rollout`
  )
}

/* H4 儿歌全库：13/13 音频 + 范唱试点 + ROUND12_H4 */
{
  const audioFiles = new Set()
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
      if (/:\/\/|\.\./.test(ref)) continue
      const m = ref.match(/^[^?#]+\.(mp3|ogg|wav|m4a)$/i)
      if (!m) continue
      const rel = m[0].replace(/^\//, '')
      try {
        if (fs.statSync(path.join(root, 'apps/literacy-app/public', rel)).size >= 10240)
          audioFiles.add(rel)
      } catch {
        /* missing */
      }
    }
  } catch {
    songCount = 0
  }
  const vocalDoc = read('.agent_workspace/r12-songs-vocal-pilot.md')
  const vocalOk =
    vocalDoc.length > 400 ||
    /\bvocal\b|范唱|人声|piper|vits/i.test(readStripped('apps/literacy-app/src/data/songs.js'))
  const marked = /\bROUND12_H4\b/.test(readStripped('apps/literacy-app/src/data/songs.js') + literacySmoke)
  check(
    'H4',
    songCount >= 13 && audioFiles.size >= 13 && vocalOk && marked,
    `H4 儿歌 13/13（音频 ${audioFiles.size}）+ 范唱试点 + ROUND12_H4`,
    `H4 儿歌未全库：songs=${songCount}/13，audio=${audioFiles.size}/13，vocal=${vocalOk}，ROUND12_H4=${marked} —— r12-literacy-songs-vocal`
  )
}

/* H5 推荐度量：效果度量实体 + 开练覆盖扩展 + ROUND12_H5_SMOKE */
{
  const metricsDoc = read('.agent_workspace/r12-reco-metrics.md')
  const progress = readStripped('apps/math-app/src/stores/progress.js')
  const parent = readStripped('apps/math-app/src/modules/parent/ParentView.vue')
  const skillPractice = readStripped('apps/math-app/src/data/skill-practice.js')
  const metricsOk =
    (metricsDoc.length > 600 && /lift|掌握度|采纳率|对照|度量/i.test(metricsDoc)) ||
    (/recoLift|recommendLift|adoptionRate|推荐效果/i.test(progress + parent + skillPractice))
  const coverageOk =
    /\bROUND12_H5\b|dailyFocus.*34|全图谱|allSkills/i.test(skillPractice + mathSmoke) ||
    (metricsDoc.length > 600 && /34|全节点|planet/i.test(metricsDoc))
  const smoke = /\bROUND12_H5_SMOKE\b/.test(mathSmoke)
  check(
    'H5',
    metricsOk && coverageOk && smoke,
    'H5 推荐度量 + 开练覆盖扩展 + ROUND12_H5_SMOKE',
    `H5 推荐度量未闭环：metrics=${metricsOk}，coverage=${coverageOk}，smoke=${smoke} —— r12-math-reco-metrics`
  )
}

/* H6 mobile LH + 真机通道：evidence/r12 ≥2 mobile JSON + 定案文档 */
{
  let mobileLh = 0
  const evDir = '.agent_workspace/evidence/r12'
  if (exists(evDir)) {
    for (const f of fs.readdirSync(path.join(root, evDir))) {
      if (!f.endsWith('.json')) continue
      const raw = read(`${evDir}/${f}`)
      try {
        const j = JSON.parse(raw)
        if (raw.length > 500 && (j.formFactor === 'mobile' || /mobile/i.test(f))) mobileLh++
      } catch {
        /* skip */
      }
    }
  }
  const deviceDoc = read('.agent_workspace/r12-android-device-decision.md')
  const deviceOk =
    deviceDoc.length > 800 &&
    /三选一|定案|云真机|Android QA|发布决策/i.test(deviceDoc) &&
    /evidence\/r12|真机/i.test(deviceDoc)
  check(
    'H6',
    mobileLh >= 2 && deviceOk,
    `H6 evidence/r12 mobile LH ${mobileLh} 份 + 真机通道定案文档`,
    `H6 真机/LH 未闭环：mobileLh=${mobileLh}/2，device=${deviceOk} —— r12-perf-device-lh`
  )
}

/* H7 TTS 试点 / 发布演练：试点资产或接线 + 提交演练 + 反馈运行 */
{
  const ttsPilot =
    exists('apps/literacy-app/public/audio/tts-pilot') ||
    readStripped('apps/literacy-app/src/utils/offlineTts.js').length > 300 ||
    (read('.agent_workspace/r12-tts-pilot.md').length > 600 &&
      /试点|pilot|piper|vits|古诗|朗读/i.test(read('.agent_workspace/r12-tts-pilot.md')))
  const releaseDrill = read('.agent_workspace/r12-store-submission-drill.md')
  const releaseOk =
    releaseDrill.length > 600 &&
    /提交|演练|Play|App Store|checklist/i.test(releaseDrill) &&
    /\bROUND12_H7\b|日期|SHA|版本/.test(releaseDrill)
  const feedback = read('.agent_workspace/FEEDBACK-LOOP.md')
  const feedbackRun =
    feedback.length > 800 &&
    /运行|处理|SLA|issue|工单/i.test(feedback)
  check(
    'H7',
    ttsPilot && releaseOk && feedbackRun,
    `H7 TTS 试点（${ttsPilot}）+ 商店提交演练 + 反馈回路运行说明`,
    `H7 TTS/发布未闭环：tts=${ttsPilot}，release=${releaseOk}，feedbackRun=${feedbackRun} —— r12-tts-release-drill`
  )
}

/* H8 R11 不退化 */
{
  const r11 = spawnSync(process.execPath, ['scripts/check-round11.mjs'], {
    cwd: root,
    encoding: 'utf8',
  })
  const ok = r11.status === 0 && /8\/8/.test(r11.stdout + r11.stderr)
  check('H8', ok, 'H8 Round 11 门禁 8/8 无退化', `H8 Round 11 退化 exit=${r11.status}`)
}

if (results.length !== EXPECTED) {
  const msg = `门禁自身结果数异常：${results.length}/${EXPECTED}，请修复 check-round12.mjs`
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
  console.log(`\nRound 12 全量落地门禁：${notes.length}/${EXPECTED} 项通过，${fails.length} 项失败。`)
  if (fails.length) console.log('说明：R12 功能分支未全部合并时 FAIL 属预期红灯；集成后必须 8/8。')
}

process.exit(fails.length ? 1 : 0)
