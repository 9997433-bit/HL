/**
 * Round 9 深度打磨硬门槛（v1.1 探针修订版）。
 * 标准：.agent_workspace/ROUND9-ACCEPTANCE.md（探针细则见 §2，逐项与本文件对齐）
 *
 * 固定输出 8 个结果：H1–H8，结果数 ≠ 8 时门禁自身 FAIL。
 * 基线（Round 8 闭合、R9 功能未合入）预期 1/8（仅 H8 绿）。
 *
 * `--json` 输出机读汇总（passed/failed/results）供编排器聚合。
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
/** 剥 HTML / 块 / 整行 // 注释——探针信号必须写成代码（常量、断言名或行内尾注）。 */
const stripComments = (src) =>
  src
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '')
const readStripped = (rel) => stripComments(read(rel))

const literacySmoke = readStripped('apps/literacy-app/scripts/smoke.mjs')
const mathSmoke = readStripped('apps/math-app/scripts/smoke.mjs')

/* H1 儿歌 v2：合规条目 ≥ 10 + 歌词同步 v2 信号（剥注释）+ smoke 标记（§2.1） */
{
  let count = 0
  try {
    const mod = await import('../apps/literacy-app/src/data/songs.js')
    const list = mod.SONGS ?? mod.default ?? []
    const seen = new Set()
    count = Array.isArray(list)
      ? list.filter((s) => {
          if (!s || typeof s !== 'object' || !s.id || seen.has(s.id)) return false
          seen.add(s.id)
          return Boolean(s.title ?? s.name) && Boolean(s.lyrics ?? s.lines ?? s.audio ?? s.src)
        }).length
      : 0
  } catch {
    count = 0
  }
  const v2 = /ROUND9_H1|歌词同步|lyric[-_]?sync|songs?[-_]?v2/i.test(
    readStripped('apps/literacy-app/src/views/SongsView.vue') + literacySmoke
  )
  const smoke = /\bROUND9_H1_SMOKE\b/.test(literacySmoke)
  check(
    'H1',
    count >= 10 && v2 && smoke,
    `H1 儿歌 v2：${count} 首合规 + 歌词同步 v2 + smoke`,
    `H1 儿歌 v2 未闭环：${count}/10 首合规，v2=${v2 ? '有' : '缺失'}，smoke=${smoke ? '有' : '缺失'} —— r9-literacy-songs`
  )
}

/* H2 OCR 扩样：≥ 8 张有效 PNG（魔数 + ≥1KB）、≥ 2 张 handwriting 命名、脚本内 tier 信号 + ROUND9_H2（§2.2） */
{
  const dir = path.join(root, 'apps/literacy-app/scripts/fixtures/ocr')
  const PNG_MAGIC = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])
  const fixtures = fs.existsSync(dir)
    ? fs.readdirSync(dir).filter((f) => {
        if (!f.endsWith('.png')) return false
        try {
          const buf = fs.readFileSync(path.join(dir, f))
          return buf.length >= 1024 && buf.subarray(0, 8).equals(PNG_MAGIC)
        } catch {
          return false
        }
      })
    : []
  const handImgs = fixtures.filter((f) => /handwriting|hand|手写/i.test(f)).length
  const acc = readStripped('apps/literacy-app/scripts/test-ocr-accuracy.mjs')
  const tierWired = /handwriting|手写/i.test(acc)
  const marked = /\bROUND9_H2\b/.test(acc)
  check(
    'H2',
    fixtures.length >= 8 && handImgs >= 2 && tierWired && marked,
    `H2 OCR 扩样 ${fixtures.length} 张有效基准图（handwriting ${handImgs} 张）+ tier 已接进精度脚本`,
    `H2 OCR 扩样未闭环：有效 PNG=${fixtures.length}/8，handwriting 图=${handImgs}/2，脚本 tier=${tierWired}，ROUND9_H2=${marked} —— r9-literacy-ocr-expand`
  )
}

/* H3 图谱推荐：R9 专属推荐路径信号 + 视图展示 + smoke（nextSkills 是 R8 存量，不算数）（§2.3） */
{
  const dataDir = path.join(root, 'apps/math-app/src/data')
  const modDir = path.join(root, 'apps/math-app/src/modules/skill-graph')
  const pool = []
  if (fs.existsSync(dataDir))
    for (const f of fs.readdirSync(dataDir))
      if (/^skill.*\.js$/.test(f)) pool.push(`apps/math-app/src/data/${f}`)
  if (fs.existsSync(modDir))
    for (const f of fs.readdirSync(modDir)) pool.push(`apps/math-app/src/modules/skill-graph/${f}`)
  const src = pool.map(readStripped).join('\n')
  const reco = /推荐路径|recommend(ed)?Path|ROUND9_H3/i.test(src)
  const view = /推荐|recommend/i.test(readStripped('apps/math-app/src/modules/skill-graph/SkillGraphView.vue'))
  const smoke = /\bROUND9_H3_SMOKE\b/.test(literacySmoke) || /\bROUND9_H3_SMOKE\b/.test(mathSmoke)
  check(
    'H3',
    reco && view && exists('apps/math-app/src/modules/skill-graph/SkillGraphView.vue') && smoke,
    'H3 技能图谱推荐路径已接线（函数 + 视图展示 + smoke）',
    `H3 图谱推荐未闭环：路径函数=${reco}，视图展示=${view}，smoke=${smoke} —— r9-math-graph-reco`
  )
}

/* H4 跟读 ASR 路线：评估文档（长度 + 关键词）或 PoC 接线（剥注释）（§2.4） */
{
  const doc = read('.agent_workspace/r9-followread-asr-evaluation.md')
  const docOk = doc.length > 800 && /ASR|音素|phoneme/i.test(doc) && /离线|offline|评估|evaluat/i.test(doc)
  const src =
    readStripped('apps/literacy-app/src/composables/useSpeechEval.js') +
    readStripped('apps/literacy-app/src/utils/speechEval.js')
  const pocOk = /phonemeMarks|similarityV2|ROUND9_H4/i.test(src)
  check(
    'H4',
    docOk || pocOk,
    `H4 跟读 ASR/音素路线已交付（doc=${docOk}，poc=${pocOk}）`,
    `H4 跟读路线未闭环：doc=${docOk}（${doc.length} 字符），poc=${pocOk} —— r9-literacy-followread-asr`
  )
}

/* H5 绘本投稿文档：≥ 1500 字符 + 投稿 + schema/字段 + fenced 示例（§2.5） */
{
  const doc = read('.agent_workspace/BOOK-COMMUNITY-SUBMISSION.md')
  const ok =
    doc.length > 1500 && /投稿/.test(doc) && /schema|字段|JSON/i.test(doc) && /```/.test(doc)
  check(
    'H5',
    ok,
    'H5 绘本社区投稿格式文档已交付（含 schema 与示例）',
    `H5 绘本投稿文档未闭环：长度=${doc.length}/1500，投稿=${/投稿/.test(doc)}，schema=${/schema|字段|JSON/i.test(doc)}，示例=${/```/.test(doc)} —— r9-content-quality`
  )
}

/* H6 LH CI 锁：脚本存在且含 lighthouse + 版本锁 + 阈值断言；evidence/r9 ≥ 2 份可解析 JSON（§2.6） */
{
  const ci = readStripped('scripts/lighthouse-ci.mjs')
  const ciOk =
    exists('scripts/lighthouse-ci.mjs') &&
    /lighthouse/i.test(ci) &&
    /version|版本/i.test(ci) &&
    /process\.exit|assert/.test(ci) &&
    /95|MIN_LH|threshold|阈值/i.test(ci)
  let jsonCount = 0
  if (exists('.agent_workspace/evidence/r9')) {
    const walk = (d) => {
      for (const f of fs.readdirSync(d, { withFileTypes: true })) {
        const p = path.join(d, f.name)
        if (f.isDirectory()) walk(p)
        else if (f.name.endsWith('.json')) {
          try {
            const raw = fs.readFileSync(p, 'utf8')
            if (raw.length > 200) {
              JSON.parse(raw)
              jsonCount++
            }
          } catch {
            /* 无效 JSON 不算 */
          }
        }
      }
    }
    walk(path.join(root, '.agent_workspace/evidence/r9'))
  }
  check(
    'H6',
    ciOk && jsonCount >= 2,
    `H6 Lighthouse CI 锁（版本锁 + 阈值断言）+ evidence/r9 ${jsonCount} 份 JSON`,
    `H6 Perf CI 未闭环：ci=${ciOk}，有效 json=${jsonCount}/2 —— r9-perf-ci-device`
  )
}

/* H7 发布清单：报告 Round 9 + evidence/r9 索引 + 零 ⏳/❌；RELEASE-CHECKLIST 三重信号（§2.7） */
{
  const report = read('.agent_workspace/GLOBAL-SUMMARY-REPORT.md')
  const reportOk =
    /Round\s*9/i.test(report) &&
    report.includes('evidence/r9') &&
    !/⏳|❌|待 R8/.test(report)
  const rel = read('.agent_workspace/RELEASE-CHECKLIST.md')
  const relOk =
    rel.length > 800 && /LICENSE/i.test(rel) && /发布|release/i.test(rel) && /证据|evidence|回滚/i.test(rel)
  check(
    'H7',
    reportOk && relOk,
    'H7 Round 9 报告 + RELEASE-CHECKLIST',
    `H7 发布清单未终验：报告=${reportOk}（Round9=${/Round\s*9/i.test(report)}，evidence/r9=${report.includes('evidence/r9')}，占位=${/⏳|❌|待 R8/.test(report) ? '有残留' : '无'}），清单=${relOk}（${rel.length} 字符） —— r9-global-release`
  )
}

/* H8 R8 不退化（§2.8） */
{
  const r8 = spawnSync(process.execPath, ['scripts/check-round8.mjs'], { cwd: root, encoding: 'utf8' })
  const ok = r8.status === 0 && /8\/8/.test(r8.stdout + r8.stderr)
  check('H8', ok, 'H8 Round 8 门禁 8/8 无退化', `H8 Round 8 退化 exit=${r8.status}`)
}

if (results.length !== EXPECTED) {
  const msg = `门禁自身结果数异常：${results.length}/${EXPECTED}，请修复 check-round9.mjs`
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
  console.log(`\nRound 9 深度门禁：${notes.length}/${EXPECTED} 项通过，${fails.length} 项失败。`)
  if (fails.length) console.log('说明：R9 功能分支未全部合并时 FAIL 属预期红灯；集成后必须 8/8。')
}
process.exit(fails.length ? 1 : 0)
