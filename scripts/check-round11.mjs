/**
 * Round 11 洪恩体验打磨硬门槛（v1.0 基线版）。
 * 标准：.agent_workspace/ROUND11-BRIEF.md（#3 升 v1.1）
 *
 * 基线（R10 闭合、R11 功能未合入）预期 1/8（仅 H8 绿）。
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
const readStripped = (rel) => stripComments(read(rel))

const literacySmoke = readStripped('apps/literacy-app/scripts/smoke.mjs')
const mathSmoke = readStripped('apps/math-app/scripts/smoke.mjs')

/* H1 跟读产品化：freezeChecklist + 评测/Go-No-Go + ROUND11_H1 */
{
  const manifest = read('apps/literacy-app/public/asr/manifest.json')
  let freezeOk = false
  try {
    const j = JSON.parse(manifest)
    freezeOk =
      Array.isArray(j.freezeChecklist) &&
      j.freezeChecklist.length >= 3 &&
      (j.sha256 || j.license || j.modelId)
  } catch {
    freezeOk = /freezeChecklist|sha256|Go.?No.?Go/i.test(manifest)
  }
  const doc =
    read('.agent_workspace/r11-followread-gonogo.md') +
    read('.agent_workspace/r11-asr-eval-set.md') +
    readStripped('apps/literacy-app/scripts/test-asr-eval-set.mjs')
  const harness = /ROUND11_H1|Go.?No.?Go|冻结集|eval.?set/i.test(doc)
  const smoke = /\bROUND11_H1(_SMOKE)?\b/.test(literacySmoke + doc)
  check(
    'H1',
    freezeOk && harness && smoke,
    'H1 跟读产品化：冻结清单 + 评测/Go-No-Go + ROUND11_H1',
    `H1 跟读未产品化：freeze=${freezeOk}，harness=${harness}，smoke=${smoke} —— r11-literacy-followread-prod`
  )
}

/* H2 OCR 矩阵：real 有效图 ≥5 + 失败话术 + ROUND11_H2 */
{
  const dir = path.join(root, 'apps/literacy-app/scripts/fixtures/ocr')
  const PNG_MAGIC = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a])
  const real = fs.existsSync(dir)
    ? fs.readdirSync(dir).filter((f) => {
        if (!/^real/i.test(f) || !f.endsWith('.png')) return false
        try {
          const buf = fs.readFileSync(path.join(dir, f))
          return buf.length >= 4096 && buf.subarray(0, 8).equals(PNG_MAGIC)
        } catch {
          return false
        }
      }).length
    : 0
  const ux =
    /失败|认不出|换一张|光线|ROUND11_H2/i.test(
      readStripped('apps/literacy-app/src/views/CameraOcrView.vue') +
        readStripped('apps/literacy-app/scripts/test-ocr-accuracy.mjs')
    )
  const marked = /\bROUND11_H2\b/.test(readStripped('apps/literacy-app/scripts/test-ocr-accuracy.mjs'))
  check(
    'H2',
    real >= 5 && ux && marked,
    `H2 OCR 实拍矩阵 ${real} 张 + 失败话术 + ROUND11_H2`,
    `H2 OCR 矩阵未闭环：real=${real}/5，ux=${ux}，ROUND11_H2=${marked} —— r11-literacy-ocr-matrix`
  )
}

/* H3 周计划：weekPlan/周计划 + 家长理由 + ROUND11_H3_SMOKE */
{
  const src =
    readStripped('apps/math-app/src/data/skill-graph.js') +
    readStripped('apps/math-app/src/data/skill-practice.js') +
    readStripped('apps/math-app/src/data/week-plan.js') +
    readStripped('apps/math-app/src/modules/skill-graph/SkillGraphView.vue') +
    readStripped('apps/math-app/src/modules/parent/ParentView.vue')
  const plan = /weekPlan|周计划|weeklyPlan|ROUND11_H3/i.test(src)
  const parent = /推荐理由|采纳|weekPlan|周计划/i.test(
    readStripped('apps/math-app/src/modules/parent/ParentView.vue')
  )
  const smoke = /\bROUND11_H3_SMOKE\b/.test(mathSmoke)
  check(
    'H3',
    plan && parent && smoke,
    'H3 推荐周计划 + 家长侧理由 + smoke',
    `H3 周计划未闭环：plan=${plan}，parent=${parent}，smoke=${smoke} —— r11-math-week-plan`
  )
}

/* H4 绘本场景：多元素场景样板 + ROUND11_H4 */
{
  const books =
    readStripped('apps/literacy-app/src/data/books.js') +
    readStripped('apps/literacy-app/src/components/BookPageScene.vue') +
    readStripped('apps/literacy-app/src/views/BookReadView.vue')
  const scene = /scene|scenes|多元素|ROUND11_H4|BookPageScene/i.test(books)
  const marked = /\bROUND11_H4\b/.test(books + literacySmoke)
  check(
    'H4',
    scene && marked,
    'H4 绘本页场景组合样板 + ROUND11_H4',
    `H4 绘本场景未闭环：scene=${scene}，ROUND11_H4=${marked} —— r11-literacy-book-scene`
  )
}

/* H5 儿歌过半：真实音频 ≥8 */
{
  let withAudio = 0
  try {
    const mod = await import('../apps/literacy-app/src/data/songs.js')
    const list = mod.SONGS ?? mod.default ?? []
    if (Array.isArray(list)) {
      withAudio = list.filter((s) => {
        const ref = String(s?.audio || s?.src || s?.melodyUrl || '')
        if (!/\.(mp3|ogg|wav|m4a)/i.test(ref)) return false
        const rel = ref.replace(/^\//, '')
        const candidates = [
          path.join(root, 'apps/literacy-app/public', rel),
          path.join(root, 'apps/literacy-app/public', ref.replace(/^.*audio\//, 'audio/')),
        ]
        return candidates.some((p) => {
          try {
            return fs.statSync(p).size >= 10240
          } catch {
            return false
          }
        })
      }).length
    }
  } catch {
    withAudio = 0
  }
  const marked = /\bROUND11_H5\b/.test(
    readStripped('apps/literacy-app/src/data/songs.js') + literacySmoke
  )
  check(
    'H5',
    withAudio >= 8 && marked,
    `H5 儿歌真实旋律 ${withAudio} 首（≥8）+ ROUND11_H5`,
    `H5 儿歌扩样未闭环：audio=${withAudio}/8，ROUND11_H5=${marked} —— r11-literacy-songs-expand`
  )
}

/* H6 预算/趋势：evidence/r11 + 路由预算或趋势 */
{
  let evidence = 0
  if (exists('.agent_workspace/evidence/r11')) {
    for (const f of fs.readdirSync(path.join(root, '.agent_workspace/evidence/r11'))) {
      if (/\.(json|md)$/i.test(f)) evidence++
    }
  }
  const budget =
    exists('apps/math-app/scripts/check-route-budget.mjs') ||
    exists('.agent_workspace/r11-perf-budget.md') ||
    /ROUND11_H6|route.?budget|趋势/i.test(
      read('.agent_workspace/r11-perf-budget.md') + readStripped('scripts/lighthouse-ci.mjs')
    )
  check(
    'H6',
    evidence >= 1 && budget,
    `H6 evidence/r11 ${evidence} 份 + 路由预算/趋势`,
    `H6 预算趋势未闭环：evidence=${evidence}/1，budget=${budget} —— r11-perf-budget-trend`
  )
}

/* H7 TTS/分发：评估文档或商店清单+反馈回路 */
{
  const tts =
    read('.agent_workspace/r11-tts-evaluation.md').length > 1500 ||
    /\bROUND11_H7\b/.test(read('.agent_workspace/r11-tts-evaluation.md'))
  const store =
    /商店|Play|App Store|分发/.test(read('.agent_workspace/RELEASE-CHECKLIST.md')) &&
    (exists('.agent_workspace/FEEDBACK-LOOP.md') ||
      exists('.agent_workspace/r11-store-checklist.md'))
  check(
    'H7',
    tts || store,
    'H7 离线 TTS 评估或商店/反馈骨架已交付',
    `H7 TTS/分发未闭环：tts=${tts}，store=${store} —— r11-tts-store-feedback`
  )
}

/* H8 R10 不退化 */
{
  const r10 = spawnSync(process.execPath, ['scripts/check-round10.mjs'], {
    cwd: root,
    encoding: 'utf8',
  })
  const ok = r10.status === 0 && /8\/8/.test(r10.stdout + r10.stderr)
  check('H8', ok, 'H8 Round 10 门禁 8/8 无退化', `H8 Round 10 退化 exit=${r10.status}`)
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
  console.log(`\nRound 11 体验门禁：${notes.length}/${EXPECTED} 项通过，${fails.length} 项失败。`)
  console.log('说明：R11 功能分支未全部合并时 FAIL 属预期红灯；集成后必须 8/8。')
}

process.exit(fails.length ? 1 : 0)
