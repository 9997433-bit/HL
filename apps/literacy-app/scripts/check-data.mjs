/**
 * 内容自检，不需要浏览器。
 *
 * 最重要的一条是绘本的用字约束：分级绘本的价值就在于「只用孩子学过的字」，
 * 一旦有人加了一句超纲的话，孩子就会卡住。这条必须自动化守住。
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { CHARACTERS, CHARACTER_MAP, TOTAL_CHARACTERS, UNITS } from '../src/data/characters.js'
import { BOOKS, charsInBook, verifyBookCoverage } from '../src/data/books.js'
import { IDIOMS } from '../src/data/idioms.js'
import { RADICALS, getRadical } from '../src/data/radicals.js'

const here = path.dirname(fileURLToPath(import.meta.url))
const baselineFile = path.resolve(here, '..', '..', '..', 'shared', 'data', 'common-hanzi.json')

const fails = []
const notes = []

const check = (ok, msg) => (ok ? notes.push(`✓ ${msg}`) : fails.push(`✗ ${msg}`))

/* ----------------------------------------------------------------- 字表 */
check(TOTAL_CHARACTERS >= 200, `字表 ${TOTAL_CHARACTERS} 个字（要求 ≥ 200）`)

const dupes = CHARACTERS.map((c) => c.char).filter((c, i, a) => a.indexOf(c) !== i)
check(dupes.length === 0, `字表无重复${dupes.length ? `（重复：${dupes.join('')}）` : ''}`)

const badFields = CHARACTERS.filter(
  (c) => !c.pinyin || !c.meaning || !c.radical || !c.strokes || !c.words?.length || !c.sentence?.text
)
check(badFields.length === 0, `每个字都有拼音/释义/部首/笔画/组词/例句${badFields.length ? `（缺失：${badFields.map((c) => c.char).join('')}）` : ''}`)

const badUnit = CHARACTERS.filter((c) => !UNITS.some((u) => u.id === c.unit))
check(badUnit.length === 0, `每个字都归属到已定义的单元`)

const badRadical = CHARACTERS.filter((c) => !getRadical(c.radical))
check(badRadical.length === 0, `每个字的部首都能查到${badRadical.length ? `（${badRadical.map((c) => `${c.char}:${c.radical}`).join(', ')}）` : ''}`)

// 拼音色标按声调着色，缺声调会退化成灰色；emoji 是卡片上唯一的图形，两者都不能少。
const badTone = CHARACTERS.filter((c) => !(c.tone >= 1 && c.tone <= 5) || !c.emoji)
check(badTone.length === 0, `每个字都有 1–5 的声调和卡片图标${badTone.length ? `（${badTone.map((c) => c.char).join('')}）` : ''}`)

const badWords = CHARACTERS.filter(
  (c) => c.words.length < 2 || c.words.some((w) => !w.w || !w.p) || !c.sentence.p
)
check(badWords.length === 0, `每个字至少 2 个带拼音的组词，例句也有拼音${badWords.length ? `（${badWords.map((c) => c.char).join('')}）` : ''}`)

const thinUnits = UNITS.filter((u) => CHARACTERS.filter((c) => c.unit === u.id).length < 5)
check(thinUnits.length === 0, `每个单元至少 5 个字${thinUnits.length ? `（${thinUnits.map((u) => u.name).join('、')}）` : ''}`)

/* --------------------------------------------------------- 与共享基线对齐
 *
 * shared/data/common-hanzi.json 是 monorepo 里这套字库的事实基线，别的 App
 * 和验收脚本都读它。字表可以在基线之上加教学包装，但不能少字、更不能改拼音，
 * 否则两边一分叉，孩子在不同入口看到的读音就会打架。
 */
const baseline = JSON.parse(fs.readFileSync(baselineFile, 'utf8')).characters ?? []
check(baseline.length >= 200, `共享字库基线 ${baseline.length} 个字（要求 ≥ 200）`)

const missingFromTable = baseline.filter((b) => !CHARACTER_MAP.has(b.character))
check(
  missingFromTable.length === 0,
  `基线里的字都在字表里${missingFromTable.length ? `（缺：${missingFromTable.map((b) => b.character).join('')}）` : ''}`
)

const pinyinDrift = baseline.filter(
  (b) => CHARACTER_MAP.has(b.character) && CHARACTER_MAP.get(b.character).pinyin !== b.pinyin
)
check(
  pinyinDrift.length === 0,
  `字表拼音与基线一致${pinyinDrift.length ? `（${pinyinDrift.map((b) => `${b.character}:${b.pinyin}≠${CHARACTER_MAP.get(b.character).pinyin}`).join('、')}）` : ''}`
)

/* ----------------------------------------------------------------- 绘本 */
check(BOOKS.length >= 5, `绘本 ${BOOKS.length} 本（要求 ≥ 5）`)

const bookDupes = BOOKS.map((b) => b.id).filter((v, i, a) => a.indexOf(v) !== i)
check(bookDupes.length === 0, `绘本 id 无重复${bookDupes.length ? `（${bookDupes.join(',')}）` : ''}`)

const levels = [...new Set(BOOKS.map((b) => b.level))]
check(levels.length >= 3, `绘本覆盖 ${levels.length} 个分级（要求 ≥ 3）`)

const coverage = verifyBookCoverage()
check(
  coverage.length === 0,
  coverage.length
    ? `绘本用字越界：${coverage.map((p) => `《${p.book}》→ ${p.missing.join('')}`).join('；')}`
    : '绘本正文只用了字表内的汉字'
)

for (const b of BOOKS) {
  check(b.pages.length >= 3, `《${b.title}》有 ${b.pages.length} 页`)
  const noPinyin = b.pages.filter((p) => !p.p)
  check(noPinyin.length === 0, `《${b.title}》每页都有拼音`)
}

/* ----------------------------------------------------------------- 成语 */
check(IDIOMS.length >= 20, `成语 ${IDIOMS.length} 个（要求 ≥ 20）`)

const idiomDupes = IDIOMS.map((i) => i.id).filter((v, i, a) => a.indexOf(v) !== i)
check(idiomDupes.length === 0, `成语 id 无重复${idiomDupes.length ? `（${idiomDupes.join(',')}）` : ''}`)

const idiomName = (i) => i.word ?? i.idiom ?? i.id
const idiomScenes = (i) => i.story ?? i.scenes ?? []

const badIdiom = IDIOMS.filter(
  (i) => !i.pinyin || !i.meaning || !i.lesson || idiomScenes(i).length < 2
)
check(
  badIdiom.length === 0,
  `每个成语都有拼音/释义/寓意和至少 2 段故事${badIdiom.length ? `（${badIdiom.map(idiomName).join('、')}）` : ''}`
)

const badChars = IDIOMS.filter((i) => (i.chars?.length ?? 0) !== 4)
check(badChars.length === 0, `每个成语都做了四字拆解${badChars.length ? `（${badChars.map(idiomName).join('、')}）` : ''}`)

const noQuiz = IDIOMS.filter((i) => !i.quiz)
check(noQuiz.length === 0, `每个成语都配了情景题${noQuiz.length ? `（${noQuiz.map(idiomName).join('、')}）` : ''}`)

const badQuiz = IDIOMS.filter((i) => {
  if (!i.quiz) return false
  const { options, answer } = i.quiz
  return !Array.isArray(options) || !(answer >= 0 && answer < options.length)
})
check(badQuiz.length === 0, `成语情景题的正确答案下标都在选项范围内${badQuiz.length ? `（${badQuiz.map(idiomName).join('、')}）` : ''}`)

/* ------------------------------------------------------------- 偏旁部首 */
check(RADICALS.length >= 8, `偏旁部首 ${RADICALS.length} 个`)

const badExample = RADICALS.flatMap((r) =>
  (r.chars ?? []).filter((c) => !CHARACTERS.some((x) => x.char === c)).map((c) => `${r.name}:${c}`)
)
check(badExample.length === 0, `部首的「学过的字」示例都在字表里${badExample.length ? `（${badExample.join(', ')}）` : ''}`)

/* ----------------------------------------------------------------- 输出 */
notes.forEach((n) => console.log(' ', n))
if (fails.length) {
  console.log('')
  fails.forEach((f) => console.log(' ', f))
}
console.log(`\n内容自检：${notes.length} 项通过，${fails.length} 项失败。`)

/* 附带一份统计，方便写验收报告 */
console.log(
  `\n统计：${TOTAL_CHARACTERS} 字 / ${UNITS.length} 单元 / ${RADICALS.length} 偏旁 / ` +
    `${BOOKS.length} 本绘本（共 ${BOOKS.reduce((n, b) => n + b.pages.length, 0)} 页，` +
    `${new Set(BOOKS.flatMap(charsInBook)).size} 个不重复用字） / ${IDIOMS.length} 个成语`
)

process.exit(fails.length ? 1 : 0)
