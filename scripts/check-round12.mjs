/**
 * Round 12 洪恩级体验全量落地硬门槛（v1.1 探针修订版）。
 * 标准：.agent_workspace/ROUND12-ACCEPTANCE.md（探针细则 §2，v1.1 修订记录见 §2 开头）
 *
 * 固定输出 8 个结果：H1–H8。基线（R11 闭合、R12 功能未合入）预期 1/8（仅 H8 绿）。
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

/* H1 ASR 模型落库：manifest files[] 落盘且 sha256 一致 + R12 落库 Go/No-Go 实体 + harness ROUND12_H1 + ROUND12_H1_SMOKE（§2.1）
   v1.0 漏洞：gonogo 回退 r11 文档（基线含 available/files[] 恒真）；filesOk||available 可只 flip available；
   marked 认 manifest.json 原文（note 写 ROUND12_H1 即过）。 */
{
  let filesOk = false
  let packBytes = 0
  try {
    const j = JSON.parse(read('apps/literacy-app/public/asr/manifest.json'))
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
  }
  const shipDoc = read('.agent_workspace/r12-followread-ship.md')
  const shipOk =
    shipDoc.length > 600 &&
    /落库|files\[\]|sha256|模型/i.test(shipDoc) &&
    /结论|判定|Go|No-Go|指标|阈值/.test(shipDoc) &&
    /\bROUND12_H1\b/.test(shipDoc)
  const evalScript = readStripped('apps/literacy-app/scripts/test-asr-eval-set.mjs')
  const harnessOk =
    /\bROUND12_H1\b/.test(evalScript) &&
    /assert|process\.exit/.test(evalScript) &&
    /跑分|eval|评测|score|wer|cer/i.test(evalScript)
  const smoke = /\bROUND12_H1_SMOKE\b/.test(literacySmoke)
  check(
    'H1',
    filesOk && shipOk && harnessOk && smoke,
    `H1 ASR 落库：files[] 落盘校验 ${packBytes}B + R12 落库 Go/No-Go + harness + ROUND12_H1_SMOKE`,
    `H1 ASR 未落库：files=${filesOk}，ship=${shipOk}，harness=${harnessOk}，smoke=${smoke} —— r12-literacy-asr-ship`
  )
}

/* H2 OCR 系统化：real ≥8 去重 + samples 授权 tier ≥8 + 真机 harness 带断言 + ROUND12_H2（§2.2）
   v1.0 漏洞：tier 词表在 JSON 注释里即过；harness >200 字符空壳即过；授权清单与 tier 结构化字段不查。 */
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
  let samples = 0
  let tierTagged = 0
  try {
    const j = JSON.parse(read('apps/literacy-app/scripts/fixtures/ocr/real-samples.json'))
    const list = Array.isArray(j.samples) ? j.samples : []
    samples = list.filter((s) => s && typeof s === 'object' && s.name && s.license).length
    tierTagged = list.filter((s) => {
      if (!s || typeof s !== 'object') return false
      const tier = s.tier && typeof s.tier === 'object' ? s.tier : s
      const light = tier.light ?? tier.lighting ?? tier.光照
      const angle = tier.angle ?? tier.角度
      const paper = tier.paper ?? tier.纸质 ?? tier.surface
      return light && angle && (paper || tier.paperType)
    }).length
  } catch {
    samples = 0
    tierTagged = 0
  }
  const matrixDoc = read('.agent_workspace/r12-ocr-matrix.md')
  const tierOk =
    tierTagged >= 8 ||
    (matrixDoc.length > 500 &&
      /光照|光线/i.test(matrixDoc) &&
      /角度/i.test(matrixDoc) &&
      /矩阵|tier|分格/i.test(matrixDoc))
  const harnessSrc = readStripped('apps/literacy-app/scripts/test-ocr-device.mjs')
  const harnessDoc = read('.agent_workspace/r12-ocr-device-harness.md')
  const harness =
    (harnessSrc.length > 200 &&
      /assert|process\.exit/.test(harnessSrc) &&
      /adb|WebView|真机|模拟器|emulator|device/i.test(harnessSrc)) ||
    (harnessDoc.length > 500 &&
      /adb|WebView|真机|模拟器|harness/i.test(harnessDoc) &&
      /assert|步骤|命令|复现/.test(harnessDoc))
  const marked = /\bROUND12_H2\b/.test(readStripped('apps/literacy-app/scripts/test-ocr-accuracy.mjs'))
  check(
    'H2',
    real >= 8 && samples >= 8 && tierOk && harness && marked,
    `H2 OCR 系统化 ${real} 张 + 授权 ${samples} 条 + tier ${tierTagged} + harness + ROUND12_H2`,
    `H2 OCR 未系统化：real=${real}/8，samples=${samples}/8，tier=${tierOk}（tagged=${tierTagged}），harness=${harness}，ROUND12_H2=${marked} —— r12-literacy-ocr-device`
  )
}

/* H3 绘本铺开：scene 页 ≥60 + 渲染不退化 + ROUND12_H3（§2.3）
   v1.0 漏洞：仅计数 scene 页，不查 BookPageScene 实体——数据堆页数、渲染零交付可蹭绿（R11 H4 同款）。 */
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
  const marked = /\bROUND12_H3\b/.test(seedPool + literacySmoke)
  check(
    'H3',
    scenePages >= 60 && rendered && marked,
    `H3 绘本场景铺开 ${scenePages} 页（≥60）+ 渲染接线 + ROUND12_H3`,
    `H3 绘本未铺开：scenePages=${scenePages}/60，rendered=${rendered}，ROUND12_H3=${marked} —— r12-literacy-books-rollout`
  )
}

/* H4 儿歌全库：13/13 去重音频 + 范唱试点实体 + ROUND12_H4（§2.4）
   v1.0 漏洞：vocalOk = doc>400 OR songs.js 词表——注释外一行 vocal 字样或短文即过；不要求落盘范唱资产。 */
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
  let vocalAsset = false
  const vocalDir = path.join(root, 'apps/literacy-app/public/audio/vocal-pilot')
  if (fs.existsSync(vocalDir)) {
    for (const f of fs.readdirSync(vocalDir)) {
      if (/\.(mp3|ogg|wav|m4a)$/i.test(f)) {
        try {
          if (fs.statSync(path.join(vocalDir, f)).size >= 10240) vocalAsset = true
        } catch {
          /* skip */
        }
      }
    }
  }
  const vocalDoc = read('.agent_workspace/r12-songs-vocal-pilot.md')
  const vocalOk =
    vocalAsset ||
    (vocalDoc.length > 500 &&
      /范唱|人声|vocal/i.test(vocalDoc) &&
      /piper|vits|录音|真人|试点/i.test(vocalDoc) &&
      /\bROUND12_H4\b/.test(vocalDoc))
  const marked = /\bROUND12_H4\b/.test(readStripped('apps/literacy-app/src/data/songs.js') + literacySmoke)
  check(
    'H4',
    songCount >= 13 && audioFiles.size >= 13 && vocalOk && marked,
    `H4 儿歌 13/13（音频 ${audioFiles.size}）+ 范唱试点 + ROUND12_H4`,
    `H4 儿歌未全库：songs=${songCount}/13，audio=${audioFiles.size}/13，vocal=${vocalOk}，ROUND12_H4=${marked} —— r12-literacy-songs-vocal`
  )
}

/* H5 推荐度量：度量实体 + skill-practice 侧 34 节点覆盖 + ROUND12_H5_SMOKE（§2.5）
   v1.0 漏洞：metrics 池拼接 progress+parent+skillPractice——家长面板写 adoptionRate 即点亮 metrics；
   coverageOk 允许 metricsDoc 含「34」而无 skill-practice 改代码。 */
{
  const metricsDoc = read('.agent_workspace/r12-reco-metrics.md')
  const progress = readStripped('apps/math-app/src/stores/progress.js')
  const skillPractice = readStripped('apps/math-app/src/data/skill-practice.js')
  const metricsOk =
    (metricsDoc.length > 600 &&
      /lift|掌握度|采纳率|对照|度量/i.test(metricsDoc) &&
      /%|百分点|baseline|对照组|\d+\.\d+/.test(metricsDoc)) ||
    (/recoLift|recommendLift|adoptionRate|推荐效果/i.test(progress) &&
      /%|lift|采纳|掌握/.test(progress))
  const coverageOk =
    /\bROUND12_H5\b/.test(skillPractice) ||
    (/dailyFocus|allSkills|skillIds|planetNodes/i.test(skillPractice) &&
      (/34|全节点|全图谱|allSkills/i.test(skillPractice) ||
        (() => {
          try {
            const modPath = path.join(root, 'apps/math-app/src/data/skills.js')
            const src = read(modPath)
            const m = src.match(/export\s+const\s+SKILLS\s*=\s*\[/)
            if (!m) return false
            const ids = [...src.matchAll(/id:\s*['"]([^'"]+)['"]/g)].map((x) => x[1])
            return new Set(ids).size >= 34
          } catch {
            return false
          }
        })()))
  const smoke = /\bROUND12_H5_SMOKE\b/.test(mathSmoke)
  check(
    'H5',
    metricsOk && coverageOk && smoke,
    'H5 推荐度量 + 开练 34 节点覆盖 + ROUND12_H5_SMOKE',
    `H5 推荐度量未闭环：metrics=${metricsOk}，coverage=${coverageOk}，smoke=${smoke} —— r12-math-reco-metrics`
  )
}

/* H6 mobile LH + 真机通道：evidence/r12 ≥2 有效 mobile LH（P≥95）+ 定案文档（§2.6）
   v1.0 漏洞：JSON >500B 且 filename/formFactor 含 mobile 即过——空壳 LH 占位可蹭绿；无 P 分阈值。 */
{
  let mobileLh = 0
  const evDir = '.agent_workspace/evidence/r12'
  if (exists(evDir)) {
    for (const f of fs.readdirSync(path.join(root, evDir))) {
      if (!f.endsWith('.json')) continue
      const raw = read(`${evDir}/${f}`)
      try {
        const j = JSON.parse(raw)
        const mobile = j.formFactor === 'mobile' || /mobile/i.test(f)
        const perf = j.categories?.performance?.score
        if (raw.length > 500 && mobile && typeof perf === 'number' && perf >= 0.95) mobileLh++
      } catch {
        /* skip */
      }
    }
  }
  const deviceDoc = read('.agent_workspace/r12-android-device-decision.md')
  const deviceOk =
    deviceDoc.length > 800 &&
    /三选一|定案|云真机|Android QA|发布决策/i.test(deviceDoc) &&
    /evidence\/r12|真机|设备/i.test(deviceDoc) &&
    /\bROUND12_H6\b/.test(deviceDoc)
  check(
    'H6',
    mobileLh >= 2 && deviceOk,
    `H6 evidence/r12 mobile LH ${mobileLh} 份（P≥95）+ 真机通道定案文档`,
    `H6 真机/LH 未闭环：mobileLh=${mobileLh}/2，device=${deviceOk} —— r12-perf-device-lh`
  )
}

/* H7 TTS 试点 或 发布演练：试点资产/接线 或 （提交演练 + R12 反馈运行说明）（§2.7）
   v1.0 漏洞：三腿 AND（与简报 OR 不符）；FEEDBACK-LOOP R11 骨架 >800 字即点亮 feedbackRun；
   exists('tts-pilot') 空目录 / offlineTts.js >300 骨架即过。 */
{
  let ttsAsset = false
  const ttsDir = path.join(root, 'apps/literacy-app/public/audio/tts-pilot')
  if (fs.existsSync(ttsDir)) {
    for (const f of fs.readdirSync(ttsDir)) {
      if (/\.(mp3|ogg|wav|m4a|onnx|json)$/i.test(f)) {
        try {
          if (fs.statSync(path.join(ttsDir, f)).size >= 10240) ttsAsset = true
        } catch {
          /* skip */
        }
      }
    }
  }
  const ttsDoc = read('.agent_workspace/r12-tts-pilot.md')
  const ttsWire = readStripped('apps/literacy-app/src/utils/offlineTts.js')
  const ttsLeg =
    ttsAsset ||
    (ttsDoc.length > 600 &&
      /试点|pilot|古诗|朗读|TTS/i.test(ttsDoc) &&
      /piper|vits|espeak|sherpa|离线/i.test(ttsDoc) &&
      /\bROUND12_H7\b/.test(ttsDoc)) ||
    (ttsWire.length > 300 &&
      /piper|vits|synthesize|speak|离线/i.test(ttsWire) &&
      /\bROUND12_H7\b/.test(ttsWire))
  const releaseDrill = read('.agent_workspace/r12-store-submission-drill.md')
  const releaseOk =
    releaseDrill.length > 600 &&
    /提交|演练|Play|App Store|checklist/i.test(releaseDrill) &&
    /\bROUND12_H7\b/.test(releaseDrill) &&
    /日期|SHA|版本/.test(releaseDrill)
  const feedback = read('.agent_workspace/FEEDBACK-LOOP.md')
  const feedbackRun =
    feedback.length > 800 &&
    /运行|处理|SLA|issue|工单/i.test(feedback) &&
    /\bROUND12_H7\b|R12 反馈运行/.test(feedback)
  check(
    'H7',
    ttsLeg || (releaseOk && feedbackRun),
    `H7 TTS 试点（${ttsLeg}）或 商店提交演练 + R12 反馈运行（${releaseOk && feedbackRun}）`,
    `H7 TTS/发布未闭环：tts=${ttsLeg}，release=${releaseOk}，feedbackRun=${feedbackRun} —— r12-tts-release-drill`
  )
}

/* H8 R11 不退化（§2.8） */
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
