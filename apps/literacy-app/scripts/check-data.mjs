/**
 * 内容自检，不需要浏览器。
 *
 * 最重要的一条是绘本的用字约束：分级绘本的价值就在于「只用孩子学过的字」，
 * 一旦有人加了一句超纲的话，孩子就会卡住。这条必须自动化守住。
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import {
  CHARACTER_MAP,
  TOTAL_CHARACTERS,
  UNITS,
  loadAllCharacters
} from '../src/data/characters.js'
import { BOOKS, charsInBook, verifyBookCoverage } from '../src/data/books.js'
import { BOOK_IDS, TOTAL_BOOKS } from '../src/data/book-index.js'
import { IDIOMS } from '../src/data/idioms.js'
import { TOTAL_IDIOMS } from '../src/data/idiom-index.js'
import { RADICALS, getRadical } from '../src/data/radicals.js'
import { ETYMOLOGY, ETYMOLOGY_KINDS } from '../src/data/etymology.js'
import { ETYMOLOGY_CHARS } from '../src/data/etymology-index.js'
import { DERIVED } from '../src/data/etymology-derived.js'
import { SIMILAR_MAP } from '../src/data/similar-chars.js'
import { POEMS, POEM_GLOSS, POEM_THEMES, charsInPoem, verifyPoemCoverage } from '../src/data/poems.js'
import { TOTAL_POEMS } from '../src/data/poem-index.js'
import { SONGS, SONG_THEMES, charsInSong, verifySongCoverage } from '../src/data/songs.js'
import { TOTAL_SONGS } from '../src/data/song-index.js'
import { TOTAL_UNIT_STORIES, hasUnitStory, unitStory } from '../src/data/unit-stories.js'
import { validateShape } from '../src/utils/etymologySketch.js'
import { STREAK_CHORDS, streakChord } from '../src/utils/audio.js'

const here = path.dirname(fileURLToPath(import.meta.url))
const baselineFile = path.resolve(here, '..', '..', '..', 'shared', 'data', 'common-hanzi.json')

const fails = []
const notes = []

const check = (ok, msg) => (ok ? notes.push(`✓ ${msg}`) : fails.push(`✗ ${msg}`))

/**
 * 字表分成「索引」和「按单元切开的详情包」两层，运行时按需加载。
 * 内容自检要看的是完整语料，所以这里把详情包全拉起来合并一遍——
 * 顺带也就验证了每个单元的详情包都存在、都能解析。
 */
const CHARACTERS = await loadAllCharacters()

/* ----------------------------------------------------------------- 字表 */
check(TOTAL_CHARACTERS >= 1800, `字表 ${TOTAL_CHARACTERS} 个字（要求 ≥ 1800）`)

const noDetail = CHARACTERS.filter((c) => !c.meaning || !c.words || !c.sentence)
check(
  noDetail.length === 0,
  `每个字都能在单元详情包里找到课文${noDetail.length ? `（缺：${noDetail.map((c) => c.char).join('')}）` : ''}`
)

const strayDetails = []
for (const unit of UNITS) {
  const pack = await import(`../src/data/chars/${unit.id}.js`).then((m) => m.default).catch(() => null)
  if (!pack) continue
  for (const char of Object.keys(pack)) {
    const light = CHARACTER_MAP.get(char)
    if (!light || light.unit !== unit.id) strayDetails.push(`${unit.id}:${char}`)
  }
}
check(
  strayDetails.length === 0,
  `详情包里没有索引之外的字${strayDetails.length ? `（${strayDetails.join('、')}）` : ''}`
)

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
check(baseline.length >= 1800, `共享字库基线 ${baseline.length} 个字（要求 ≥ 1800）`)

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
check(BOOKS.length >= 130, `绘本 ${BOOKS.length} 本（要求 ≥ 130）`)

const bookDupes = BOOKS.map((b) => b.id).filter((v, i, a) => a.indexOf(v) !== i)
check(bookDupes.length === 0, `绘本 id 无重复${bookDupes.length ? `（${bookDupes.join(',')}）` : ''}`)

// 书架上一眼扫过去全是同名的书，孩子分不清读过哪本。
const bookTitleDupes = BOOKS.map((b) => b.title).filter((v, i, a) => a.indexOf(v) !== i)
check(
  bookTitleDupes.length === 0,
  `绘本书名无重复${bookTitleDupes.length ? `（${bookTitleDupes.join('、')}）` : ''}`
)

const levels = [...new Set(BOOKS.map((b) => b.level))].sort((a, b) => a - b)
check(levels.length >= 6, `绘本覆盖 ${levels.length} 个分级（要求 ≥ 6）：L${levels.join(' / L')}`)

// 分级只有在每一级都读得饱的时候才有意义，空档会让书架上出现断层。
const thinLevels = levels.filter((l) => BOOKS.filter((b) => b.level === l).length < 12)
check(
  thinLevels.length === 0,
  `每个分级至少 12 本书${thinLevels.length ? `（偏少：L${thinLevels.join('、L')}）` : ''}`
)

// 轻量索引是首页和 progress store 的唯一数据源，跟正文对不上就会显示错的分母。
check(
  TOTAL_BOOKS === BOOKS.length && BOOK_IDS.join(',') === BOOKS.map((b) => b.id).join(','),
  `绘本轻量索引与书目一致（book-index=${TOTAL_BOOKS}，书目=${BOOKS.length}）`
)

const coverage = verifyBookCoverage()
check(
  coverage.length === 0,
  coverage.length
    ? `绘本用字越界：${coverage.map((p) => `《${p.book}》→ ${p.missing.join('')}`).join('；')}`
    : '绘本正文只用了字表内的汉字'
)

const shortBooks = BOOKS.filter((b) => b.pages.length < 5)
check(
  shortBooks.length === 0,
  `每本绘本至少 5 页${shortBooks.length ? `（${shortBooks.map((b) => `《${b.title}》${b.pages.length} 页`).join('、')}）` : ''}`
)

const noPinyin = BOOKS.filter((b) => b.pages.some((p) => !p.p))
check(
  noPinyin.length === 0,
  `每页都配了拼音${noPinyin.length ? `（${noPinyin.map((b) => `《${b.title}》`).join('')}）` : ''}`
)

const badMeta = BOOKS.filter(
  (b) => !b.title || !b.pinyin || !b.summary || !b.cover || !b.levelName || b.palette?.length !== 2
)
check(
  badMeta.length === 0,
  `每本绘本都有书名/拼音/简介/封面/分级名和两色封面渐变${badMeta.length ? `（${badMeta.map((b) => b.id).join('、')}）` : ''}`
)

const noEmoji = BOOKS.filter((b) => b.pages.some((p) => !p.emoji || !p.text))
check(
  noEmoji.length === 0,
  `每页都有插图和正文${noEmoji.length ? `（${noEmoji.map((b) => `《${b.title}》`).join('')}）` : ''}`
)

// newChars 是「这本书的重点字」，会直接推给孩子去学，越界的话点开就是空详情页。
const strayNewChars = BOOKS.flatMap((b) =>
  (b.newChars ?? []).filter((c) => !CHARACTER_MAP.has(c)).map((c) => `${b.id}:${c}`)
)
check(
  strayNewChars.length === 0,
  `绘本的重点字都在字表里${strayNewChars.length ? `（${strayNewChars.join('、')}）` : ''}`
)

/* ----------------------------------------------------------------- 成语 */
check(IDIOMS.length >= 60, `成语 ${IDIOMS.length} 个（要求 ≥ 60）`)

const idiomWordDupes = IDIOMS.map((i) => i.word).filter((v, i, a) => a.indexOf(v) !== i)
check(
  idiomWordDupes.length === 0,
  `成语正文无重复${idiomWordDupes.length ? `（${idiomWordDupes.join('、')}）` : ''}`
)

// 逐字拆解卡是按成语正文一格一格摆的，两边对不上就会出现「拆解里没有这个字」。
const charDrift = IDIOMS.filter((i) => (i.chars ?? []).map((c) => c.c).join('') !== i.word)
check(
  charDrift.length === 0,
  `逐字拆解与成语正文逐字对应${charDrift.length ? `（${charDrift.map((i) => i.word).join('、')}）` : ''}`
)

check(
  TOTAL_IDIOMS === IDIOMS.length,
  `首页用的成语总数索引与语料一致（idiom-index=${TOTAL_IDIOMS}，语料=${IDIOMS.length}）`
)

const idiomDupes = IDIOMS.map((i) => i.id).filter((v, i, a) => a.indexOf(v) !== i)
check(idiomDupes.length === 0, `成语 id 无重复${idiomDupes.length ? `（${idiomDupes.join(',')}）` : ''}`)

/* ----------------------------------------------------------------- 古诗 */
check(POEMS.length >= 20, `古诗 ${POEMS.length} 首（要求 ≥ 20）`)

check(
  TOTAL_POEMS === POEMS.length,
  `首页用的古诗总数索引与语料一致（poem-index=${TOTAL_POEMS}，语料=${POEMS.length}）`
)

const poemDupes = POEMS.map((p) => p.id).filter((v, i, a) => a.indexOf(v) !== i)
check(poemDupes.length === 0, `古诗 id 无重复${poemDupes.length ? `（${poemDupes.join(',')}）` : ''}`)

const poemTitleDupes = POEMS.map((p) => p.title).filter((v, i, a) => a.indexOf(v) !== i)
check(
  poemTitleDupes.length === 0,
  `古诗标题无重复${poemTitleDupes.length ? `（${poemTitleDupes.join('、')}）` : ''}`
)

/**
 * 古诗的正文改不得，所以约束不是「只许用已学字」，而是
 * 「每个字要么已学，要么有注解」+「逐字拼音数量对得上」。
 * 后一条错了不会报错，只会让跟读页的拼音整体错位一格，最难靠肉眼发现。
 */
const poemCoverage = verifyPoemCoverage()
check(
  poemCoverage.length === 0,
  poemCoverage.length
    ? `古诗逐字校验不过：${poemCoverage
        .map(
          (p) =>
            `《${p.poem}》${p.unglossed.length ? `缺注解 ${p.unglossed.join('')}` : ''}${
              p.misaligned.length ? ` 拼音错位 ${p.misaligned.join('/')}` : ''
            }`
        )
        .join('；')}`
    : '古诗正文逐字都有拼音，生字都有注解'
)

const poemMeta = POEMS.filter(
  (p) =>
    !p.title ||
    !p.titlePinyin ||
    !p.author ||
    !p.dynasty ||
    !p.emoji ||
    !p.summary ||
    !p.tip ||
    p.palette?.length !== 2 ||
    !POEM_THEMES.some((t) => t.id === p.theme)
)
check(
  poemMeta.length === 0,
  `每首诗都有标题/拼音/作者/朝代/主题/简介/提示和两色渐变${poemMeta.length ? `（${poemMeta.map((p) => p.id).join('、')}）` : ''}`
)

const poemNoSense = POEMS.filter((p) => p.lines.some((l) => !l.text || !l.pinyin || !l.sense))
check(
  poemNoSense.length === 0,
  `每一句都有正文、拼音和白话${poemNoSense.length ? `（${poemNoSense.map((p) => `《${p.title}》`).join('')}）` : ''}`
)

// 长廊按主题分区，某个主题一首诗都没有的话，点进去就是空页面。
const emptyThemes = POEM_THEMES.filter((t) => !POEMS.some((p) => p.theme === t.id))
check(
  emptyThemes.length === 0,
  `每个主题分区都有诗${emptyThemes.length ? `（空：${emptyThemes.map((t) => t.name).join('、')}）` : ''}`
)

// 注解表留着用不到的条目不算错，但通常意味着诗被改过而注解忘了跟着删。
const strayGloss = Object.keys(POEM_GLOSS).filter(
  (ch) => !POEMS.some((p) => charsInPoem(p).includes(ch))
)
check(
  strayGloss.length === 0,
  `生字注解表里没有多余条目${strayGloss.length ? `（${strayGloss.join('')}）` : ''}`
)

/* ----------------------------------------------------------------- 儿歌 */
check(SONGS.length >= 3, `儿歌 ${SONGS.length} 首（要求 ≥ 3）`)

check(
  TOTAL_SONGS === SONGS.length,
  `首页用的儿歌总数索引与语料一致（song-index=${TOTAL_SONGS}，语料=${SONGS.length}）`
)

const songDupes = SONGS.map((s) => s.id).filter((v, i, a) => a.indexOf(v) !== i)
check(songDupes.length === 0, `儿歌 id 无重复${songDupes.length ? `（${songDupes.join(',')}）` : ''}`)

/**
 * 儿歌是自己写的，所以按绘本的标准要求：一个没学过的字都不许出现。
 * 顺带校验逐字拼音与逐字音名的个数——错一个，跟唱高亮就会整句错位。
 */
const songCoverage = verifySongCoverage()
check(
  songCoverage.length === 0,
  songCoverage.length
    ? `儿歌逐字校验不过：${songCoverage
        .map(
          (s) =>
            `《${s.song}》${s.unknown.length ? `超纲字 ${s.unknown.join('')}` : ''}${
              s.misaligned.length ? ` ${s.misaligned.join('/')}` : ''
            }${s.badNotes.length ? ` 音名不认识 ${s.badNotes.join('/')}` : ''}`
        )
        .join('；')}`
    : '儿歌歌词只用学过的字，逐字拼音与曲谱都对得上'
)

const songMeta = SONGS.filter(
  (s) =>
    !s.title ||
    !s.titlePinyin ||
    !s.emoji ||
    !s.summary ||
    !s.tip ||
    !(s.bpm >= 60 && s.bpm <= 110) ||
    s.palette?.length !== 2 ||
    s.lines.length < 4 ||
    !SONG_THEMES.some((t) => t.id === s.theme)
)
check(
  songMeta.length === 0,
  `每首儿歌都有歌名/拼音/主题/简介/提示/两色渐变，速度在 60–110 且至少 4 句${songMeta.length ? `（${songMeta.map((s) => s.id).join('、')}）` : ''}`
)

const emptySongThemes = SONG_THEMES.filter((t) => !SONGS.some((s) => s.theme === t.id))
check(
  emptySongThemes.length === 0,
  `每个儿歌分区都有歌${emptySongThemes.length ? `（空：${emptySongThemes.map((t) => t.name).join('、')}）` : ''}`
)

/* ------------------------------------------------------------- 单元剧情 */
const storyless = UNITS.filter((u) => !hasUnitStory(u))
check(
  storyless.length === 0,
  `每个单元都有手写剧情，没有走兜底（${TOTAL_UNIT_STORIES} 条）${storyless.length ? `（缺：${storyless.map((u) => u.id).join('、')}）` : ''}`
)

const storyTexts = UNITS.map((u) => unitStory(u))
const storyDupes = storyTexts.filter((v, i, a) => a.indexOf(v) !== i)
check(
  storyDupes.length === 0,
  `单元剧情没有两站说同一句话${storyDupes.length ? `（${storyDupes[0]}）` : ''}`
)

// 地图上剧情只有一行的位置，太长会被截断，太短又交代不清这一站有什么。
const badStoryLength = UNITS.filter((u) => {
  const len = unitStory(u).length
  return len < 12 || len > 44
})
check(
  badStoryLength.length === 0,
  `单元剧情长度都在 12–44 字之间${badStoryLength.length ? `（${badStoryLength.map((u) => u.id).join('、')}）` : ''}`
)

/**
 * 剧情里用「」引起来的单字，必须真的收在这一站里。
 * u59 之后的单元名是虚构地名，剧情靠点名几个字来告诉孩子这一站会遇上谁——
 * 字表重排之后这些名字最容易变成谎话，而且没有任何报错。
 */
const strayStoryChars = []
for (const unit of UNITS) {
  const pack = await import(`../src/data/chars/${unit.id}.js`).then((m) => m.default).catch(() => null)
  if (!pack) continue
  const quoted = [...unitStory(unit).matchAll(/「(.)」/g)].map((m) => m[1])
  const stray = quoted.filter((ch) => !pack[ch])
  if (stray.length) strayStoryChars.push(`${unit.id}:${stray.join('')}`)
}
check(
  strayStoryChars.length === 0,
  `单元剧情点名的字都收在本单元里${strayStoryChars.length ? `（${strayStoryChars.join('、')}）` : ''}`
)

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

/* ----------------------------------------------------------------- 字源
 *
 * 字源动画的第二帧直接用离线笔顺数据画，所以字源语料只能收字表里的字——
 * 收了字表外的字，那一帧就会在断网时开天窗。
 */
check(ETYMOLOGY.length >= 200, `字源演变 ${ETYMOLOGY.length} 个字（要求 ≥ 200）`)

const etyDupes = ETYMOLOGY.map((e) => e.c).filter((v, i, a) => a.indexOf(v) !== i)
check(etyDupes.length === 0, `字源语料无重复字${etyDupes.length ? `（${etyDupes.join('')}）` : ''}`)

const etyStray = ETYMOLOGY.filter((e) => !CHARACTER_MAP.has(e.c))
check(
  etyStray.length === 0,
  `字源语料里的字都在字表里${etyStray.length ? `（${etyStray.map((e) => e.c).join('')}）` : ''}`
)

const etyKinds = new Set(ETYMOLOGY_KINDS.map((k) => k.id))
const etyBadKind = ETYMOLOGY.filter((e) => !etyKinds.has(e.kind))
check(
  etyBadKind.length === 0,
  `每个字都归到了象形/指事/会意/形声${etyBadKind.length ? `（${etyBadKind.map((e) => e.c).join('')}）` : ''}`
)

const etyNoText = ETYMOLOGY.filter((e) => !e.origin || !e.evolve)
check(
  etyNoText.length === 0,
  `每个字都写了「本来是什么」和「怎么变的」${etyNoText.length ? `（${etyNoText.map((e) => e.c).join('')}）` : ''}`
)

// 第一帧要么是小图要么是零件，两样都没有的话舞台上会是一块空白
const etyNoFrame = ETYMOLOGY.filter((e) => !e.sketch?.length && !(e.parts?.length >= 2))
check(
  etyNoFrame.length === 0,
  `每个字都有小图或至少两个零件${etyNoFrame.length ? `（${etyNoFrame.map((e) => e.c).join('')}）` : ''}`
)

const etyBadShape = []
for (const e of ETYMOLOGY) {
  for (const shape of e.sketch ?? []) {
    const problem = validateShape(shape)
    if (problem) etyBadShape.push(`${e.c}:${problem}`)
  }
}
check(
  etyBadShape.length === 0,
  `每张字源小图都画得出来${etyBadShape.length ? `（${etyBadShape.join('；')}）` : ''}`
)

check(
  ETYMOLOGY_CHARS === ETYMOLOGY.map((e) => e.c).join(''),
  '单字页用的字源索引与语料逐字对齐'
)

/**
 * 派生条目的零件是「形旁 + 声旁」，两个字形都会原样显示给孩子看。
 * 形旁串了（比如种子里的字换了单元、部首跟着变了）不会报错，
 * 只会让讲解和字形对不上号，所以这里逐条核一遍形旁。
 */
const partDrift = DERIVED.filter((e) => {
  if (e.kind !== 'xing') return false
  const glyph = getRadical(CHARACTER_MAP.get(e.c)?.radical)?.glyph
  return e.parts?.[0]?.g !== glyph
})
check(
  partDrift.length === 0,
  `派生字源的形旁与字表部首一致${partDrift.length ? `（${partDrift.map((e) => e.c).join('')}，重跑 npm run gen:etymology）` : ''}`
)

// 讲解里引用的读音必须和字表拼音一致，不然孩子照着念就是错的
const pinyinOff = DERIVED.filter(
  (e) => e.kind === 'xing' && !e.evolve.includes(CHARACTER_MAP.get(e.c)?.pinyin ?? '\u0000')
)
check(
  pinyinOff.length === 0,
  `派生字源写的读音与字表一致${pinyinOff.length ? `（${pinyinOff.map((e) => e.c).join('')}）` : ''}`
)

// 每一类都得有几个字，不然「原来这一类字都长这样」的规律看不出来
const thinKinds = ETYMOLOGY_KINDS.filter((k) => ETYMOLOGY.filter((e) => e.kind === k.id).length < 5)
check(
  thinKinds.length === 0,
  `象形/指事/会意/形声每类至少 5 个字${thinKinds.length ? `（${thinKinds.map((k) => k.name).join('、')}）` : ''}`
)

/* ----------------------------------------------------------------- 形近字
 *
 * 形近字库是生成物（scripts/gen-similar-chars.mjs），字表一改它就会走散：
 * 库里留着已经删掉的字，选择题就会渲染出点不开的选项。
 * 这里只验「有没有走散」和「覆盖够不够」，相似度本身由生成器负责。
 */
const similarCoverage = CHARACTERS.filter((c) => SIMILAR_MAP.has(c.char)).length
check(
  similarCoverage >= CHARACTERS.length * 0.95,
  `形近字库覆盖 ${similarCoverage} / ${CHARACTERS.length} 个字（要求 ≥ 95%）`
)

const similarStray = []
for (const [char, packed] of SIMILAR_MAP) {
  if (!CHARACTER_MAP.has(char)) similarStray.push(char)
  for (const other of packed) {
    if (!CHARACTER_MAP.has(other)) similarStray.push(`${char}→${other}`)
    if (other === char) similarStray.push(`${char}→自己`)
  }
}
check(
  similarStray.length === 0,
  `形近字库里的字都在字表里${similarStray.length ? `（${similarStray.slice(0, 12).join('、')}${similarStray.length > 12 ? '…' : ''}，重跑 npm run gen:similar）` : ''}`
)

// 三选一 / 四选一各要 2–3 个干扰项，少于 3 个的字出题就会退回「随便找个字」。
const similarThin = [...SIMILAR_MAP].filter(([, packed]) => packed.length < 3).map(([c]) => c)
check(
  similarThin.length <= CHARACTERS.length * 0.05,
  `形近字不足 3 个的字只有 ${similarThin.length} 个（上限 ${Math.floor(CHARACTERS.length * 0.05)}）`
)

/* ------------------------------------------------------------- 偏旁部首 */
check(RADICALS.length >= 8, `偏旁部首 ${RADICALS.length} 个`)

const badExample = RADICALS.flatMap((r) =>
  (r.chars ?? []).filter((c) => !CHARACTERS.some((x) => x.char === c)).map((c) => `${r.name}:${c}`)
)
check(badExample.length === 0, `部首的「学过的字」示例都在字表里${badExample.length ? `（${badExample.join(', ')}）` : ''}`)

/* ------------------------------------------------------------- 答对音效 */
const streakEndings = STREAK_CHORDS.map((chord) => chord[chord.length - 1])
check(
  streakEndings.every((freq, index) => index === 0 || freq > streakEndings[index - 1]),
  `连对音效 ${STREAK_CHORDS.length} 档收尾音逐级升高`
)
check(
  streakChord(0) === STREAK_CHORDS[0] &&
    streakChord(Number.NaN) === STREAK_CHORDS[0] &&
    streakChord(999) === STREAK_CHORDS[STREAK_CHORDS.length - 1],
  '连对音效把异常值与长连击限制在安全音域'
)

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
    `${new Set(BOOKS.flatMap(charsInBook)).size} 个不重复用字） / ${IDIOMS.length} 个成语 / ` +
    `${ETYMOLOGY.length} 个字有字源演变 / ${SONGS.length} 首儿歌（共 ` +
    `${SONGS.reduce((n, s) => n + s.lines.length, 0)} 句，` +
    `${new Set(SONGS.flatMap(charsInSong)).size} 个不重复用字） / ` +
    `${TOTAL_UNIT_STORIES} 条单元剧情`
)

process.exit(fails.length ? 1 : 0)
