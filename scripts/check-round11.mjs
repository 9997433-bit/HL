/**
 * Round 11 洪恩体验打磨硬门槛（v1.1 探针修订版）。
 * 标准：.agent_workspace/ROUND11-ACCEPTANCE.md（探针细则 §2，v1.1 修订记录见 §2 开头）
 *
 * 固定输出 8 个结果：H1–H8，结果数 ≠ 8 时门禁自身 FAIL。
 * 基线（R10 闭合、R11 功能未合入）预期 1/8（仅 H8 绿）。
 *
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

/* H1 跟读产品化：manifest 严格解析 + Go/No-Go 实体 + 评测集实体 + ROUND11_H1_SMOKE（§2.1）
   v1.0 漏洞：freezeOk 的 JSON 解析失败正则兜底（损坏 manifest 里出现 sha256 字样即真）；
   smoke 允许 doc 池命中（一份文档同时满足 harness+smoke）。均已废弃。 */
{
  let freezeOk = false
  try {
    const j = JSON.parse(read('apps/literacy-app/public/asr/manifest.json'))
    const items = Array.isArray(j.freezeChecklist)
      ? j.freezeChecklist.filter((it) => {
          if (typeof it === 'string') return it.trim().length >= 8
          if (it && typeof it === 'object') {
            const text = String(it.must || it.id || it.evidence || '')
            return text.trim().length >= 2
          }
          return false
        })
      : []
    freezeOk = items.length >= 3 && typeof j.modelId === 'string' && j.modelId.length > 0
  } catch {
    freezeOk = false
  }
  const gonogoDoc = read('.agent_workspace/r11-followread-gonogo.md')
  const gonogo =
    gonogoDoc.length > 800 &&
    /go[\s/_-]?no[\s/_-]?go/i.test(gonogoDoc) &&
    /结论|判定|指标|阈值/.test(gonogoDoc)
  const evalDoc = read('.agent_workspace/r11-asr-eval-set.md')
  const evalScript = readStripped('apps/literacy-app/scripts/test-asr-eval-set.mjs')
  const evalset =
    (evalDoc.length > 500 && /评测|eval[\s_-]?set|冻结集/i.test(evalDoc)) ||
    (/assert|process\.exit/.test(evalScript) && /评测|eval|冻结/i.test(evalScript))
  const smoke = /\bROUND11_H1_SMOKE\b/.test(literacySmoke)
  check(
    'H1',
    freezeOk && gonogo && evalset && smoke,
    'H1 跟读产品化：冻结清单 + Go/No-Go 实体 + 评测集实体 + ROUND11_H1_SMOKE',
    `H1 跟读未产品化：freeze=${freezeOk}，gonogo=${gonogo}，evalset=${evalset}，smoke=${smoke} —— r11-literacy-followread-prod`
  )
}

/* H2 OCR 矩阵：去重后有效 real PNG ≥5 + real-samples.json 授权条目 ≥5 + 视图失败话术（基线假词表）+ ROUND11_H2（§2.2）
   v1.0 漏洞：不去重（同图复制 5 份即过）；ux 词表含「换一张」在 CameraOcrView 基线恒真；
   real-samples.json 出处/授权清单完全不查（可与落盘图数脱节）。 */
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
        /* 不可读不算 */
      }
    }
  }
  const real = hashes.size
  let samples = 0
  try {
    const j = JSON.parse(read('apps/literacy-app/scripts/fixtures/ocr/real-samples.json'))
    samples = (Array.isArray(j.samples) ? j.samples : []).filter(
      (s) => s && typeof s === 'object' && s.name && s.license
    ).length
  } catch {
    samples = 0
  }
  const cam = readStripped('apps/literacy-app/src/views/CameraOcrView.vue')
  const ux = /失败|认不出|光线|太暗|模糊|重拍|\bROUND11_H2\b/.test(cam)
  const marked = /\bROUND11_H2\b/.test(readStripped('apps/literacy-app/scripts/test-ocr-accuracy.mjs'))
  check(
    'H2',
    real >= 5 && samples >= 5 && ux && marked,
    `H2 OCR 实拍矩阵 ${real} 张（去重）+ 授权清单 ${samples} 条 + 失败话术 + ROUND11_H2`,
    `H2 OCR 矩阵未闭环：real=${real}/5，samples=${samples}/5，ux=${ux}，ROUND11_H2=${marked} —— r11-literacy-ocr-matrix`
  )
}

/* H3 周计划：数据/图谱侧 weekPlan 信号（池不含 ParentView）+ ParentView 自身理由/采纳信号 + ROUND11_H3_SMOKE（§2.3）
   v1.0 漏洞：plan 池混入 ParentView.vue——家长面板写一次「周计划」即同时点亮 plan+parent（跨文件拼接坍缩，R9/R10 同款）。 */
{
  const pool = []
  const dataDir = path.join(root, 'apps/math-app/src/data')
  const modDir = path.join(root, 'apps/math-app/src/modules/skill-graph')
  if (fs.existsSync(dataDir))
    for (const f of fs.readdirSync(dataDir))
      if (/^(skill|week|daily).*\.js$/i.test(f)) pool.push(`apps/math-app/src/data/${f}`)
  if (fs.existsSync(modDir))
    for (const f of fs.readdirSync(modDir)) pool.push(`apps/math-app/src/modules/skill-graph/${f}`)
  const src = pool.map(readStripped).join('\n')
  const plan = /weekPlan|weeklyPlan|周计划|\bROUND11_H3\b/i.test(src)
  const parent = /推荐理由|采纳|weekPlan|周计划/i.test(
    readStripped('apps/math-app/src/modules/parent/ParentView.vue')
  )
  const smoke = /\bROUND11_H3_SMOKE\b/.test(mathSmoke)
  check(
    'H3',
    plan && parent && smoke,
    'H3 推荐周计划（数据/图谱侧）+ 家长侧理由/采纳 + ROUND11_H3_SMOKE',
    `H3 周计划未闭环：plan=${plan}，parent=${parent}，smoke=${smoke} —— r11-math-week-plan`
  )
}

/* H4 绘本场景：数据探针（≥1 页 scene 数组含 ≥2 个对象元素）+ 渲染侧接线 + ROUND11_H4（§2.4）
   v1.0 漏洞：/scene|scenes|.../ 纯正则——数据里塞个 `const scene = null` 即过，多元素本体零校验。 */
{
  let sceneUnits = 0
  try {
    const mod = await import('../apps/literacy-app/src/data/books.js')
    const books = mod.BOOKS ?? mod.default ?? []
    for (const b of Array.isArray(books) ? books : []) {
      for (const p of Array.isArray(b?.pages) ? b.pages : []) {
        const els = Array.isArray(p?.scene) ? p.scene : Array.isArray(p?.sceneElements) ? p.sceneElements : []
        if (els.filter((el) => el && typeof el === 'object').length >= 2) sceneUnits++
      }
    }
  } catch {
    sceneUnits = 0
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
  const marked = /\bROUND11_H4\b/.test(seedPool + comp + view + literacySmoke)
  check(
    'H4',
    sceneUnits >= 1 && rendered && marked,
    `H4 绘本多元素场景 ${sceneUnits} 页（scene ≥2 元素）+ 渲染接线 + ROUND11_H4`,
    `H4 绘本场景未闭环：sceneUnits=${sceneUnits}/1，rendered=${rendered}，ROUND11_H4=${marked} —— r11-literacy-book-scene`
  )
}

/* H5 儿歌过半：合规条目（R9 口径）+ 引用锚定音频扩展名 + public 资产存在 ≥10KB + 去重 ≥8 + ROUND11_H5（§2.5）
   v1.0 漏洞（R10 H5 v1.1 已堵过、v1.0 全数回退）：不过滤条目（重复 id 算多首）、不去重（8 条引用同一文件算 8）、
   扩展名正则不锚定（fake.mp3.txt 也算）、候选路径回退允许 CDN URL 蹭本地文件。 */
{
  const audioFiles = new Set()
  try {
    const mod = await import('../apps/literacy-app/src/data/songs.js')
    const list = mod.SONGS ?? mod.default ?? []
    const seen = new Set()
    for (const s of Array.isArray(list) ? list : []) {
      if (!s || typeof s !== 'object' || !s.id || seen.has(s.id)) continue
      seen.add(s.id)
      if (!(s.title ?? s.name)) continue
      const ref = String(s.audio || s.src || s.melodyUrl || '')
      if (/:\/\/|\.\./.test(ref)) continue
      const m = ref.match(/^[^?#]+\.(mp3|ogg|wav|m4a)$/i)
      if (!m) continue
      const rel = m[0].replace(/^\//, '')
      try {
        if (fs.statSync(path.join(root, 'apps/literacy-app/public', rel)).size >= 10240)
          audioFiles.add(rel)
      } catch {
        /* 资产不存在不算 */
      }
    }
  } catch {
    /* 数据模块不可读即 0 */
  }
  const marked = /\bROUND11_H5\b/.test(
    readStripped('apps/literacy-app/src/data/songs.js') + literacySmoke
  )
  check(
    'H5',
    audioFiles.size >= 8 && marked,
    `H5 儿歌真实旋律 ${audioFiles.size} 首（public 资产存在且 ≥10KB，去重）+ ROUND11_H5`,
    `H5 儿歌扩样未闭环：audio=${audioFiles.size}/8，ROUND11_H5=${marked} —— r11-literacy-songs-expand`
  )
}

/* H6 预算/趋势：evidence/r11 有效证据 ≥1（JSON 可解析 >200B / md >200B）+ 预算实体（脚本带断言 或 文档带路由×预算表）（§2.6）
   v1.0 漏洞：任意空 .json/.md 占位算证据；budget 三选一里两个是裸 exists（touch 即过，R10 H4 同款）。 */
{
  let evidence = 0
  const evDir = '.agent_workspace/evidence/r11'
  if (exists(evDir)) {
    for (const f of fs.readdirSync(path.join(root, evDir))) {
      const raw = read(`${evDir}/${f}`)
      if (f.endsWith('.json')) {
        try {
          if (raw.length > 200) {
            JSON.parse(raw)
            evidence++
          }
        } catch {
          /* 无效 JSON 不算 */
        }
      } else if (f.endsWith('.md') && raw.length > 200) evidence++
    }
  }
  const budgetScript =
    readStripped('apps/math-app/scripts/check-route-budget.mjs') +
    readStripped('scripts/check-route-budget.mjs')
  const scriptOk =
    /route|路由/i.test(budgetScript) &&
    /budget|预算/i.test(budgetScript) &&
    /process\.exit|assert/.test(budgetScript)
  const budgetDoc = read('.agent_workspace/r11-perf-budget.md')
  const docOk =
    budgetDoc.length > 800 && /路由|route/i.test(budgetDoc) && /预算|budget|阈值/i.test(budgetDoc)
  const budget = scriptOk || docOk
  check(
    'H6',
    evidence >= 1 && budget,
    `H6 evidence/r11 有效证据 ${evidence} 份 + 路由预算实体（script=${scriptOk}/doc=${docOk}）`,
    `H6 预算趋势未闭环：evidence=${evidence}/1，budget=${budget}（script=${scriptOk}，doc=${docOk}） —— r11-perf-budget-trend`
  )
}

/* H7 TTS/分发：评估文档实体（>1500 + 候选方案 + 结论） 或 商店清单实体 + 反馈回路实体（§2.7）
   v1.0 漏洞：tts 的 OR 让 20 字节「ROUND11_H7」占位文件即过；store 侧 RELEASE-CHECKLIST 的
   商店字样基线恒真 + FEEDBACK-LOOP 裸 exists——touch 一个空文件整个 H7 变绿。 */
{
  const ttsDoc = read('.agent_workspace/r11-tts-evaluation.md')
  const tts =
    ttsDoc.length > 1500 &&
    /piper|vits|espeak|sherpa|分批录音|录音/i.test(ttsDoc) &&
    /结论|建议|选型|对比/.test(ttsDoc)
  const storeChecklist = read('.agent_workspace/r11-store-checklist.md')
  const storeDoc =
    (storeChecklist.length > 500 && /商店|Play|App Store|上架/i.test(storeChecklist)) ||
    /\bROUND11_H7\b/.test(read('.agent_workspace/RELEASE-CHECKLIST.md'))
  const feedback = read('.agent_workspace/FEEDBACK-LOOP.md')
  const feedbackOk =
    feedback.length > 500 && /反馈|feedback/i.test(feedback) && /渠道|回路|处理|流程/.test(feedback)
  const store = storeDoc && feedbackOk
  check(
    'H7',
    tts || store,
    `H7 离线 TTS 评估（${tts}）或 商店清单 + 反馈回路（${store}）已交付实体`,
    `H7 TTS/分发未闭环：tts=${tts}，store=${store}（storeDoc=${storeDoc}，feedback=${feedbackOk}） —— r11-tts-store-feedback`
  )
}

/* H8 R10 不退化（§2.8） */
{
  const r10 = spawnSync(process.execPath, ['scripts/check-round10.mjs'], {
    cwd: root,
    encoding: 'utf8',
  })
  const ok = r10.status === 0 && /8\/8/.test(r10.stdout + r10.stderr)
  check('H8', ok, 'H8 Round 10 门禁 8/8 无退化', `H8 Round 10 退化 exit=${r10.status}`)
}

if (results.length !== EXPECTED) {
  const msg = `门禁自身结果数异常：${results.length}/${EXPECTED}，请修复 check-round11.mjs`
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
  console.log(`\nRound 11 体验门禁：${notes.length}/${EXPECTED} 项通过，${fails.length} 项失败。`)
  if (fails.length) console.log('说明：R11 功能分支未全部合并时 FAIL 属预期红灯；集成后必须 8/8。')
}

process.exit(fails.length ? 1 : 0)
