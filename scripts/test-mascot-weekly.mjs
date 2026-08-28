/**
 * Round 16 · 学伴人格（H6）与家长周报（H7）的行为回归。
 *
 * 这两样东西都只是「把存档翻译成人话」，没有网络、没有 DOM，
 * 所以整套逻辑都住在纯模块里，这里直接在 Node 下跑：
 *
 *   H6 每个阶段在对应状态下必须被选中，且台词条数够（识字 ≥40 条）；
 *   H7 每条弱项规则都要能命中，建议练习恒定在 1–3 条且每条都有落点。
 *
 * 台词与建议的措辞会一直改，所以断言只压结构与边界，不压具体句子。
 */

import assert from 'node:assert/strict'
import { register } from 'node:module'

register('./alias-loader.mjs', import.meta.url)

const litMascot = await import(
  new URL('../apps/literacy-app/src/data/mascotLines.js', import.meta.url)
)
const mathMascot = await import(
  new URL('../apps/math-app/src/data/mascotLines.js', import.meta.url)
)
const litReport = await import(
  new URL('../apps/literacy-app/src/utils/weeklyReport.js', import.meta.url)
)
const mathReport = await import(
  new URL('../apps/math-app/src/utils/weeklyReport.js', import.meta.url)
)

const failures = []
const check = (name, fn) => {
  try {
    fn()
    console.log(`  ✓ ${name}`)
  } catch (err) {
    failures.push(`${name}: ${err.message}`)
    console.log(`  ✗ ${name}: ${err.message}`)
  }
}

/* ------------------------------------------------------------------ H6 */

console.log('\nH6 学伴人格剧本')

const LIT_STAGE_MIN = 40

check(`识字阶段台词 ≥ ${LIT_STAGE_MIN} 条`, () => {
  const n = litMascot.countMascotStageLines()
  assert.ok(n >= LIT_STAGE_MIN, `只有 ${n} 条`)
})

check('数学阶段台词非空', () => {
  assert.ok(mathMascot.countMascotStageLines() > 0)
})

check('两个 App 的剧本版本标记一致', () => {
  assert.equal(litMascot.ROUND16_H6_STAGE_SCRIPT, 'ROUND16_H6')
  assert.equal(mathMascot.ROUND16_H6_STAGE_SCRIPT, 'ROUND16_H6')
})

check('每个阶段在任何上下文下都至少有一句话', () => {
  for (const mod of [litMascot, mathMascot]) {
    for (const stage of mod.MASCOT_STAGES) {
      assert.ok(stage.lines({}).length > 0, `${stage.id} 在空上下文下没有台词`)
      assert.ok(mod.mascotStageLines(stage.id, {}).length > 0, `${stage.id} 点名取不到台词`)
    }
  }
})

check('台词里不夹 emoji（要交给 SpeechSynthesis 念）', () => {
  const emoji = /\p{Extended_Pictographic}/u
  for (const mod of [litMascot, mathMascot]) {
    for (const stage of mod.MASCOT_STAGES) {
      for (const line of stage.lines({ combo: 5, due: 3, daysAway: 4, wrongCount: 5 })) {
        assert.ok(!emoji.test(line), `${stage.id}「${line}」里有表情符号`)
      }
    }
  }
})

check('识字阶段判定按优先级命中', () => {
  const cases = [
    [{ daysAway: 5 }, 'comeback'],
    [{ restDue: true }, 'fatigue'],
    [{ sessionMinutes: 20 }, 'fatigue'],
    [{ justMastered: true }, 'mastered'],
    [{ combo: 4 }, 'combo'],
    [{ recentWrong: 1 }, 'encourage'],
    [{ due: 2 }, 'review'],
    [{ dailyLimitReached: true }, 'finish'],
    [{ nextChar: '人' }, 'newChar'],
    [{}, 'idle']
  ]
  for (const [ctx, expected] of cases) {
    assert.equal(litMascot.pickMascotStage(ctx).id, expected, JSON.stringify(ctx))
  }
})

check('数学阶段判定按优先级命中', () => {
  const cases = [
    [{ daysAway: 4 }, 'comeback'],
    [{ todayMinutes: 25 }, 'fatigue'],
    [{ combo: 3 }, 'combo'],
    [{ wrongCount: 3 }, 'wrongBook'],
    [{ recentWrong: 1 }, 'encourage'],
    [{ dailyCompleted: false }, 'daily'],
    [{ dailyCompleted: true }, 'finish']
  ]
  for (const [ctx, expected] of cases) {
    assert.equal(mathMascot.pickMascotStage(ctx).id, expected, JSON.stringify(ctx))
  }
})

check('mascotLines 把阶段台词排在场景台词前面', () => {
  const lines = litMascot.mascotLines('home', { due: 3 })
  const stage = litMascot.mascotStageLines('review', { due: 3 })
  assert.deepEqual(lines.slice(0, stage.length), stage)
  assert.ok(lines.length > stage.length, '场景常驻语丢了')
})

check('场景名写错也不会没话说', () => {
  assert.ok(litMascot.mascotLines('不存在的页面', {}).length > 0)
  assert.ok(mathMascot.mascotLines('不存在的页面', {}).length > 0)
})

/* ------------------------------------------------------------------ H7 */

console.log('\nH7 家长可解释周报')

const week = (day) => Array.from({ length: 7 }, (_, i) => ({ key: `2026-08-2${2 + i}`, ...day }))

/** 一份「练得挺勤、没有短板」的底子，各用例只在它上面改一处。 */
const litBusy = {
  days: week({ seconds: 900, newChars: 2 }),
  learnedCount: 20,
  masteredCount: 20,
  averageRetention: 0.9,
  booksFinished: 3,
  poemsRead: 2,
  accuracy: 92,
  chars: { 人: { level: 3, traced: 2, correct: 5 } }
}

const mathBusy = {
  days: week({ minutes: 9, answered: 10, correct: 9 }),
  modules: [
    { id: 'arithmetic', name: '算术恒星', route: '/arithmetic', answered: 20 },
    { id: 'geometry', name: '形状卫星', route: '/geometry', answered: 5 }
  ]
}

const litCases = [
  ['absent', {}],
  ['thin', { days: [{ key: '2026-08-28', seconds: 600, newChars: 2 }] }],
  [
    'backlog',
    {
      ...litBusy,
      dueCount: 7,
      memoryCards: Array.from({ length: 7 }, (_, i) => ({
        char: `字${i}`,
        retention: 0.3,
        isDue: true
      }))
    }
  ],
  ['errors', { ...litBusy, chars: { 人: { level: 2, traced: 1, wrong: 3, correct: 1 } } }],
  ['fading', { ...litBusy, averageRetention: 0.45, memoryCards: [{ char: '人', retention: 0.2 }] }],
  [
    'writing',
    {
      ...litBusy,
      masteredCount: 1,
      chars: { 人: { level: 1, traced: 0 }, 大: { level: 1, traced: 0 }, 小: { level: 1, traced: 0 } }
    }
  ],
  ['output', { ...litBusy, booksFinished: 0, poemsRead: 0 }],
  ['steady', litBusy]
]

const mathCases = [
  ['absent', {}],
  ['thin', { days: [{ key: '2026-08-28', minutes: 8, answered: 6, correct: 5 }] }],
  ['wrongbook', { ...mathBusy, wrongCount: 5 }],
  ['errorTag', { ...mathBusy, errorTagCounts: { carry: 4 } }],
  ['accuracy', { days: week({ minutes: 9, answered: 10, correct: 4 }) }],
  [
    'weakSkill',
    { ...mathBusy, skills: [{ id: 'a', name: '进位加', mastery: 0.3, route: '/arithmetic' }] }
  ],
  [
    'narrow',
    {
      ...mathBusy,
      modules: [
        { id: 'arithmetic', name: '算术恒星', route: '/arithmetic', answered: 20 },
        { id: 'geometry', name: '形状卫星', route: '/geometry', answered: 0 }
      ]
    }
  ],
  ['steady', mathBusy]
]

for (const [app, build, cases] of [
  ['识字', litReport.buildWeeklyReport, litCases],
  ['数学', mathReport.buildWeeklyReport, mathCases]
]) {
  check(`${app}周报覆盖全部 ${cases.length} 条弱项规则`, () => {
    const seen = new Set()
    for (const [expected, input] of cases) {
      const report = build(input)
      assert.equal(report.weakness.id, expected, `期望 ${expected}，得到 ${report.weakness.id}`)
      seen.add(report.weakness.id)
    }
    assert.equal(seen.size, cases.length)
  })

  check(`${app}周报的建议练习恒在 1–3 条且都有落点`, () => {
    for (const [, input] of cases) {
      const report = build(input)
      assert.ok(report.drills.length >= 1, '一条建议都没有')
      assert.ok(report.drills.length <= 3, `给了 ${report.drills.length} 条，超过 3 条`)
      for (const drill of report.drills) {
        assert.ok(drill.title, '建议缺标题')
        assert.ok(drill.why, `建议「${drill.title}」没说为什么`)
        assert.ok(String(drill.to).startsWith('/'), `建议「${drill.title}」没有可点的落点`)
      }
      const ids = report.drills.map((d) => d.id)
      assert.equal(new Set(ids).size, ids.length, `建议 id 重复：${ids.join(', ')}`)
    }
  })

  check(`${app}周报一句话不为空、带版本标记`, () => {
    for (const [, input] of cases) {
      const report = build(input)
      assert.equal(report.script, 'ROUND16_H7')
      assert.ok(report.headline.length >= 10, `一句话太短：${report.headline}`)
      assert.ok(report.range, '缺少统计区间')
    }
  })

  check(`${app}周报在空输入下也能出一份完整报告`, () => {
    const report = build()
    assert.ok(report.headline)
    assert.ok(report.drills.length >= 1)
    assert.equal(report.week.activeDays, 0)
  })
}

console.log(
  `\n识字阶段台词 ${litMascot.countMascotStageLines()} 条 · ` +
    `数学阶段台词 ${mathMascot.countMascotStageLines()} 条`
)

if (failures.length) {
  console.error(`\n✗ ${failures.length} 项未通过`)
  for (const f of failures) console.error(`  - ${f}`)
  process.exit(1)
}
console.log('\n✓ 学伴人格与家长周报全部通过')
