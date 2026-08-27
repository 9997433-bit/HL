/**
 * 内容自检：不开浏览器，直接把题库和生成器跑上几千次，
 * 确认不会出现负数答案、NaN 文案、重复选项、无解或多解的数独。
 */
import {
  SCENE_SKINS,
  SEMANTIC_TEMPLATES,
  WORD_PROBLEMS,
  WORD_PROBLEM_TAGS,
  problemsOfTier,
} from '../src/data/wordProblems.js'
import { isKnownSkill, SKILL_MAP, skillsOfModule } from '../src/data/curriculum.js'
import {
  arithmeticSkill,
  countingSkill,
  geometrySkill,
  logicSkill,
  LOGIC_QUESTION_TYPES,
  sudokuSkill,
  SUDOKU_SIZES,
} from '../src/data/skill-mapping.js'
import {
  conflictsOf,
  countSolutions,
  generateSudoku,
  solve,
  specOf,
} from '../src/core/engine/sudoku.js'
import {
  buildMazeStage,
  canMove,
  DIRECTION_MAP,
  hintDirection,
  MAZE_LEVELS,
  nextObjective,
  rateRun,
  samePos,
  solveMaze,
  step,
} from '../src/core/engine/maze.js'
import {
  buildMemoryDeck,
  isMatch,
  MEMORY_LEVELS,
  matchReason,
  maxPairs,
} from '../src/core/engine/memory-pairs.js'
import {
  createRng,
  numericOptions,
  parseQuestionId,
  questionId,
  reseed,
} from '../src/utils/random.js'
import { COMPARE_SYMBOLS, compareQuestion, compareSymbol } from '../src/data/compare.js'
import {
  buildDailyQuestion,
  buildDailyQuestions,
  DAILY_SIZE,
  DAILY_TEMPLATE_IDS,
} from '../src/data/daily.js'
import { ERROR_TAGS } from '../src/data/errorTags.js'
import { CUES, noteToFreq, STREAK_CUES, streakCue } from '../src/utils/sound.js'
import { updateMastery, MASTERY_THRESHOLD } from '../src/utils/mastery.js'
import { VISUAL_DEMOS } from '../src/data/visualDemos.js'
import {
  createAdaptiveEngine,
  nextDifficulty,
  pickNextQuestion,
  skillWeight,
  weakestSkills,
} from '../src/core/engine/adaptive.js'

const MIN_TEMPLATES = 185
const MIN_SCENES = 40

let failures = 0
const fail = (msg) => {
  failures++
  console.log(`  ✗ ${msg}`)
}

console.log(`应用题母题 ${WORD_PROBLEMS.length} 个：`)
if (WORD_PROBLEMS.length < MIN_TEMPLATES) {
  fail(`母题只有 ${WORD_PROBLEMS.length} 个，少于要求的 ${MIN_TEMPLATES} 个`)
}

const ids = new Set()
const scenes = new Set()
const byStep = { 1: 0, 2: 0, 3: 0 }

for (const tpl of WORD_PROBLEMS) {
  if (ids.has(tpl.id)) fail(`母题 id 重复：${tpl.id}`)
  ids.add(tpl.id)
  scenes.add(tpl.scene)
  byStep[Math.min(3, tpl.steps ?? 1)] += 1
  if (typeof tpl.make !== 'function') {
    fail(`${tpl.id} 没有 make() 生成器`)
    continue
  }
  for (let i = 0; i < 2000; i++) {
    let q
    try {
      q = tpl.make()
    } catch (err) {
      fail(`${tpl.id} 第 ${i} 次生成抛错：${err.message}`)
      break
    }
    if (!Number.isInteger(q.answer)) fail(`${tpl.id} 答案不是整数：${q.answer}`)
    if (q.answer < 0) fail(`${tpl.id} 出现负数答案：${q.answer}`)
    if (/NaN|undefined|\{/.test(q.text)) fail(`${tpl.id} 题干渲染异常：${q.text}`)
    if (/NaN|undefined/.test(q.equation)) fail(`${tpl.id} 算式渲染异常：${q.equation}`)
    if (!q.equation || !q.unit) fail(`${tpl.id} 缺少算式或单位`)
    if (!q.hint) fail(`${tpl.id} 缺少提示文案`)
  }
}
if (scenes.size < MIN_SCENES) fail(`只有 ${scenes.size} 种场景，少于要求的 ${MIN_SCENES} 种`)
if (WORD_PROBLEM_TAGS.some((t) => !t)) fail('存在没有语义标签的母题')
console.log(
  `  ${WORD_PROBLEM_TAGS.length} 类语义标签 / ${scenes.size} 种场景，` +
    `一步 ${byStep[1]} · 两步 ${byStep[2]} · 进阶 ${byStep[3]}，每个母题各生成 2000 道`,
)

for (const tierId of ['one', 'two', 'multi']) {
  if (problemsOfTier(tierId).length === 0) fail(`难度档「${tierId}」一道母题都没有`)
}

/* 数形演示注册表：每类必须完整走完「实物 → 图形 → 算式」三段。 */
{
  const demoIds = new Set()
  if (VISUAL_DEMOS.length < 7) fail(`数形演示只有 ${VISUAL_DEMOS.length} 类，少于要求的 7 类`)
  for (const demo of VISUAL_DEMOS) {
    if (!demo.id || demoIds.has(demo.id)) fail(`数形演示 id 缺失或重复：${demo.id}`)
    demoIds.add(demo.id)
    if (!demo.object?.label || !demo.object?.emoji) fail(`数形演示 ${demo.id} 缺少实物段`)
    if (!demo.visual?.label || !demo.visual?.groups?.length) fail(`数形演示 ${demo.id} 缺少图形段`)
    if (!demo.equation) fail(`数形演示 ${demo.id} 缺少算式段`)
    if (demo.narration?.length !== 3) fail(`数形演示 ${demo.id} 应有 3 段旁白`)
    if (!isKnownSkill(demo.skill)) fail(`数形演示 ${demo.id} 技能点「${demo.skill}」不在图谱里`)
  }
  console.log(`数形演示 ${VISUAL_DEMOS.length} 类：实物 / 图形 / 算式 / 三段旁白齐全`)
}

/* 语义模板 × 场景皮肤：笛卡尔积必须完整铺满，否则等于悄悄少了一批母题 */
{
  const skinned = new Set(WORD_PROBLEMS.map((t) => t.id))
  let missing = 0
  for (const semantic of SEMANTIC_TEMPLATES) {
    for (const skin of SCENE_SKINS) {
      if (!skinned.has(`${semantic.id}-${skin.id}`)) {
        missing++
        fail(`语义「${semantic.id}」缺少皮肤「${skin.id}」的组合`)
      }
    }
  }
  const crossed = SEMANTIC_TEMPLATES.length * SCENE_SKINS.length - missing
  console.log(
    `  语义模板 ${SEMANTIC_TEMPLATES.length} × 场景皮肤 ${SCENE_SKINS.length} = ${crossed} 个组合母题，` +
      `另有 ${WORD_PROBLEMS.length - crossed} 个手写母题`,
  )
}

/* 种子化 PRNG：同一个 seed 下整个题库逐字复现，换 seed 才换题 */
{
  const snapshot = (seed) => {
    reseed(seed)
    return JSON.stringify(WORD_PROBLEMS.map((tpl) => tpl.make()))
  }
  if (snapshot('wp-2026') !== snapshot('wp-2026')) {
    fail('同一 seed 下应用题母题两次生成结果不一致')
  }
  if (snapshot('wp-2026') === snapshot('wp-2027')) {
    fail('换了 seed 应用题母题却生成出完全相同的题面')
  }
  console.log(`  种子化 PRNG：reseed 后 ${WORD_PROBLEMS.length} 道题逐字复现，换 seed 即换题`)
}

/* 技能点映射 */
const produced = new Set()
for (const tpl of WORD_PROBLEMS) {
  produced.add(tpl.skill)
  const skill = SKILL_MAP[tpl.skill]
  if (!skill) fail(`母题 ${tpl.id} 的技能点「${tpl.skill}」不在图谱里`)
  else if (skill.module !== 'word-problems') {
    fail(`母题 ${tpl.id} 记到了 ${skill.module} 的技能点「${tpl.skill}」`)
  }
}
for (const type of ['drag', 'count', 'seq']) {
  for (let target = 1; target <= 20; target++) produced.add(countingSkill({ type, target }))
}
for (const target of COMPARE_SYMBOLS) {
  for (let max = 1; max <= 20; max++) produced.add(countingSkill({ type: 'compare', target, max }))
}
for (const level of [10, 20, 100]) {
  for (const kind of ['add', 'sub']) produced.add(arithmeticSkill({ level, kind }))
}
for (const dim of ['2d', '3d']) produced.add(geometrySkill({ dim }))
for (const type of [...LOGIC_QUESTION_TYPES, 'unknown-type']) produced.add(logicSkill(type))
for (const size of SUDOKU_SIZES) produced.add(sudokuSkill(size))
for (const id of produced) {
  if (!isKnownSkill(id)) fail(`映射产出的技能点「${id}」不在图谱里`)
}
for (const skill of skillsOfModule('word-problems')) {
  const covered = WORD_PROBLEMS.filter((t) => t.skill === skill.id).length
  if (!covered) fail(`技能点「${skill.id}」(${skill.name}) 没有任何母题能练到`)
}
console.log(
  `技能点映射：产出 ${produced.size} 个 id 全部在图谱里，应用题 ${
    skillsOfModule('word-problems').length
  } 个技能点均有母题覆盖`,
)

/* 数独三档 */
for (const [sizeKey, holes, rounds] of [
  [4, 11, 200],
  [6, 24, 60],
  [9, 52, 12],
]) {
  const spec = specOf(sizeKey)
  let unique = 0
  let clean = 0
  let clueMin = Infinity
  let worstMs = 0
  for (let i = 0; i < rounds; i++) {
    const t0 = performance.now()
    const { puzzle, solution } = generateSudoku(sizeKey, holes)
    worstMs = Math.max(worstMs, performance.now() - t0)
    const s = solve(puzzle, spec)
    if (s && s.join() === solution.join()) unique += 1
    else fail(`${sizeKey}×${sizeKey} 第 ${i} 局回填出的解和答案不一致`)
    if (countSolutions(puzzle, spec, 2) !== 1) fail(`${sizeKey}×${sizeKey} 第 ${i} 局解不唯一`)
    if (puzzle.every((v, idx) => !v || conflictsOf(puzzle, spec, idx).length === 0)) clean += 1
    else fail(`${sizeKey}×${sizeKey} 第 ${i} 局题面自带冲突`)
    clueMin = Math.min(clueMin, puzzle.filter(Boolean).length)
  }
  console.log(
    `数独 ${sizeKey}×${sizeKey} ${rounds} 局：唯一解 ${unique}，题面无冲突 ${clean}，` +
      `最少给定数 ${clueMin}，最慢生成 ${worstMs.toFixed(1)}ms`,
  )
  if (worstMs > 1000) fail(`${sizeKey}×${sizeKey} 生成最慢 ${worstMs.toFixed(0)}ms，会卡住界面`)
}

let optOk = 0
const TRIES = 5000
for (let i = 0; i < TRIES; i++) {
  const ans = Math.floor(Math.random() * 100)
  const opts = numericOptions(ans, { count: 4, spread: 5, min: 0, max: 100 })
  if (
    opts.length === 4 &&
    new Set(opts).size === 4 &&
    opts.includes(ans) &&
    opts.every((n) => Number.isInteger(n) && n >= 0 && n <= 100)
  ) {
    optOk++
  }
}
if (optOk !== TRIES) fail(`numericOptions ${TRIES - optOk} 次不合规`)
console.log(`选项生成器 ${TRIES} 次：合规 ${optOk}`)

/* ---------------------------------------------------------------- 可复现 */

/* 随机流本身：同种子逐位一致，异种子不同流 */
{
  const a = Array.from({ length: 64 }, createRng('seed-a'))
  const b = Array.from({ length: 64 }, createRng('seed-a'))
  const c = Array.from({ length: 64 }, createRng('seed-b'))
  if (a.join() !== b.join()) fail('同一个 seed 的两条随机流结果不一致')
  if (a.join() === c.join()) fail('不同 seed 的随机流结果完全相同')
  if (a.some((n) => !(n >= 0 && n < 1))) fail('mulberry32 产出越界，应落在 [0,1)')
  const die = createRng(7)
  const rolls = Array.from({ length: 600 }, () => die.int(1, 6))
  if (rolls.some((n) => n < 1 || n > 6 || !Number.isInteger(n))) fail('rng.int 越界')
  if (new Set(rolls).size !== 6) fail(`rng.int(1,6) 只掷出了 ${new Set(rolls).size} 种点数`)
}

/* 题目 id：`${templateId}:${seed}`，拆回来还得是原样 */
if (questionId('daily-add', '2026-01-01#1') !== 'daily-add:2026-01-01#1') {
  fail('questionId 的拼接格式不是 `${templateId}:${seed}`')
}
{
  const parsed = parseQuestionId(questionId('daily-add', '2026-01-01#1'))
  if (parsed.templateId !== 'daily-add' || parsed.seed !== '2026-01-01#1') {
    fail(`parseQuestionId 拆不回原值：${JSON.stringify(parsed)}`)
  }
}

/* 比大小：符号判定与题目复现 */
{
  let compareOk = 0
  for (let i = 0; i < 3000; i++) {
    const seed = `compare-${i}`
    const q = compareQuestion(seed, { ceiling: 20 })
    const again = compareQuestion(seed, { ceiling: 20 })
    if (q.id !== `compare:${seed}`) fail(`比大小题 id 不对：${q.id}`)
    if (JSON.stringify(q) !== JSON.stringify(again)) fail(`比大小题 ${seed} 两次生成不一致`)
    if (q.target !== compareSymbol(q.left, q.right)) {
      fail(`比大小题判错：${q.left} ${q.target} ${q.right}`)
    }
    if (q.options.join() !== COMPARE_SYMBOLS.join()) fail('比大小题的选项不是 < = > 三个符号')
    if (q.left < 1 || q.left > 20 || q.right < 1 || q.right > 20) {
      fail(`比大小题数值越界：${q.left} / ${q.right}`)
    }
    if (!isKnownSkill(q.skill)) fail(`比大小题记到了图谱外的技能点「${q.skill}」`)
    compareOk++
  }
  const symbols = new Set(
    Array.from({ length: 400 }, (_, i) => compareQuestion(`spread-${i}`).target),
  )
  if (symbols.size !== 3) fail(`比大小题只出现了 ${[...symbols].join('')}，三种符号没出全`)
  console.log(`比大小题 ${compareOk} 道：判定正确、可按 seed 复现，> < = 三种符号齐全`)
}

/* 每日冒险：同一天永远是同一套题，题目 id 里带着可复现的 seed */
{
  const DAYS = 400
  const start = Date.UTC(2026, 0, 1)
  let checked = 0
  for (let d = 0; d < DAYS; d++) {
    const dateKey = new Date(start + d * 864e5).toISOString().slice(0, 10)
    const first = buildDailyQuestions(dateKey)
    const second = buildDailyQuestions(dateKey)

    if (first.length !== DAILY_SIZE) fail(`${dateKey} 的每日冒险有 ${first.length} 题，应为 ${DAILY_SIZE}`)
    if (JSON.stringify(first) !== JSON.stringify(second)) {
      fail(`${dateKey} 的每日冒险两次生成不一致，同一天换了题`)
    }

    first.forEach((q, slot) => {
      const seed = `${dateKey}#${slot}`
      if (q.id !== `${DAILY_TEMPLATE_IDS[slot]}:${seed}`) {
        fail(`${dateKey} 第 ${slot} 题 id 应为 ${DAILY_TEMPLATE_IDS[slot]}:${seed}，实际 ${q.id}`)
      }
      // 只凭题目 id 里的 seed 就要能把这道题原样重建出来
      const rebuilt = buildDailyQuestion(slot, parseQuestionId(q.id).seed.split('#')[0])
      if (JSON.stringify(rebuilt) !== JSON.stringify(q)) fail(`${q.id} 无法凭 id 复现`)

      if (q.answer === undefined || q.answer === null) fail(`${q.id} 没有答案`)
      if (!Array.isArray(q.options) || q.options.length < 3) fail(`${q.id} 选项不足`)
      if (new Set(q.options).size !== q.options.length) fail(`${q.id} 选项有重复`)
      if (!q.options.includes(q.answer)) fail(`${q.id} 选项里没有正确答案 ${q.answer}`)
      if (typeof q.answer === 'number' && (!Number.isInteger(q.answer) || q.answer < 0)) {
        fail(`${q.id} 的答案不是自然数：${q.answer}`)
      }
      if (/NaN|undefined/.test(q.prompt)) fail(`${q.id} 题干渲染异常：${q.prompt}`)
      if (!q.hints?.length || q.hints.some((h) => /NaN|undefined|-\d/.test(h))) {
        fail(`${q.id} 的提示文案异常：${q.hints?.join(' / ')}`)
      }
      if (!isKnownSkill(q.skill)) fail(`${q.id} 记到了图谱外的技能点「${q.skill}」`)
      checked++
    })

    const ids = new Set(first.map((q) => q.id))
    if (ids.size !== first.length) fail(`${dateKey} 的每日冒险出现重复题目 id`)
  }

  // 换一天必须换题，否则「每日」就没有意义
  const monday = buildDailyQuestions('2026-03-02').map((q) => q.prompt).join('|')
  const tuesday = buildDailyQuestions('2026-03-03').map((q) => q.prompt).join('|')
  if (monday === tuesday) fail('相邻两天的每日冒险题目完全相同')
  console.log(
    `每日冒险 ${DAYS} 天共 ${checked} 道：同日可复现、跨日不重样，` +
      `题型顺序 ${DAILY_TEMPLATE_IDS.join(' → ')}`,
  )
}

/* 条件迷宫：每一档都要能生成、能走通，而且只跟着提示走就一定能通关 */
{
  if (!isKnownSkill('maze-condition')) fail('逻辑迷宫记的技能点 maze-condition 不在图谱里')
  let stages = 0
  let walked = 0
  for (const [bandId, config] of Object.entries(MAZE_LEVELS)) {
    for (let i = 0; i < 40; i++) {
      const seed = `${bandId}-${i}`
      const stage = buildMazeStage({ ...config, seed })
      if (!stage) {
        fail(`${bandId} 第 ${i} 座迷宫编排失败`)
        continue
      }
      stages++

      const again = buildMazeStage({ ...config, seed })
      if (JSON.stringify(stage) !== JSON.stringify(again)) {
        fail(`${bandId} 第 ${i} 座迷宫同种子两次生成不一致`)
      }
      if (stage.checkpoints.length !== config.checkpoints) {
        fail(`${bandId} 第 ${i} 座迷宫只放下 ${stage.checkpoints.length} 个能量块`)
      }
      const marks = new Set(stage.checkpoints.map((c) => `${c.x},${c.y}`))
      if (marks.size !== stage.checkpoints.length) fail(`${bandId} 第 ${i} 座迷宫能量块重叠`)
      if (marks.has(`${stage.start.x},${stage.start.y}`)) fail(`${bandId} 能量块压在发射台上`)
      if (marks.has(`${stage.goal.x},${stage.goal.y}`)) fail(`${bandId} 能量块压在空间站上`)
      if (!(stage.optimalSteps > 0)) fail(`${bandId} 第 ${i} 座迷宫最短步数为 ${stage.optimalSteps}`)

      // 完美迷宫：任意一格都必须能从起点走到
      const unreachable = []
      for (let y = 0; y < config.rows; y++) {
        for (let x = 0; x < config.cols; x++) {
          if (!solveMaze(stage.maze, stage.start, { x, y })) unreachable.push(`${x},${y}`)
        }
      }
      if (unreachable.length) fail(`${bandId} 第 ${i} 座迷宫有 ${unreachable.length} 格走不到`)

      // 只跟着提示走：必须按顺序收齐能量块，并在最短步数内到达终点
      let at = { ...stage.start }
      let collected = 0
      let steps = 0
      const cap = stage.optimalSteps + 4
      while (steps < cap && !(collected === stage.checkpoints.length && samePos(at, stage.goal))) {
        const dir = hintDirection(stage, at, collected)
        if (!dir) {
          fail(`${bandId} 第 ${i} 座迷宫在 ${at.x},${at.y} 给不出提示`)
          break
        }
        if (!canMove(stage.maze, at, dir)) {
          fail(`${bandId} 第 ${i} 座迷宫的提示指向墙：${DIRECTION_MAP[dir].name}`)
          break
        }
        at = step(at, dir)
        steps++
        const target = nextObjective(stage, collected)
        if (target.kind === 'checkpoint' && samePos(at, target)) collected++
      }
      if (collected !== stage.checkpoints.length || !samePos(at, stage.goal)) {
        fail(`${bandId} 第 ${i} 座迷宫跟着提示走 ${steps} 步也没通关`)
      } else if (steps !== stage.optimalSteps) {
        fail(`${bandId} 第 ${i} 座迷宫提示路线 ${steps} 步，最短是 ${stage.optimalSteps} 步`)
      }
      walked += steps

      if (rateRun(stage, { steps: stage.optimalSteps, hints: 0 }) !== 3) {
        fail(`${bandId} 走出最短路线却没给满星`)
      }
      if (rateRun(stage, { steps: stage.optimalSteps * 3, hints: 4 }) !== 1) {
        fail(`${bandId} 绕远又狂用提示还不止 1 星`)
      }
    }
  }
  console.log(
    `条件迷宫 ${stages} 座（5 档 × 40）：每格可达、能量块按序可收，` +
      `跟提示共走 ${walked} 步全部按最短路线通关`,
  )
}

/* 配对记忆：牌堆必须两两成对，同类档的每一对都得真的同类 */
{
  if (!isKnownSkill('classify')) fail('配对记忆记的技能点 classify 不在图谱里')
  let decks = 0
  for (const [bandId, config] of Object.entries(MEMORY_LEVELS)) {
    if (config.pairs > maxPairs(config.mode)) {
      fail(`${bandId} 要 ${config.pairs} 对，${config.mode} 档最多只有 ${maxPairs(config.mode)} 对`)
    }
    for (let i = 0; i < 200; i++) {
      const seed = `${bandId}-${i}`
      const deck = buildMemoryDeck({ ...config, seed })
      decks++

      if (JSON.stringify(deck) !== JSON.stringify(buildMemoryDeck({ ...config, seed }))) {
        fail(`${bandId} 第 ${i} 副牌同种子两次生成不一致`)
      }
      if (deck.cards.length !== config.pairs * 2) {
        fail(`${bandId} 第 ${i} 副牌有 ${deck.cards.length} 张，应为 ${config.pairs * 2} 张`)
      }
      if (new Set(deck.cards.map((c) => c.id)).size !== deck.cards.length) {
        fail(`${bandId} 第 ${i} 副牌出现重复卡片 id`)
      }
      if (deck.grid.cols * deck.grid.rows < deck.cards.length) {
        fail(`${bandId} 第 ${i} 副牌的网格摆不下 ${deck.cards.length} 张卡`)
      }

      const byPair = new Map()
      for (const card of deck.cards) {
        if (!card.glyph || !card.label || !card.groupName) fail(`${bandId} 第 ${i} 副牌有残缺卡片`)
        byPair.set(card.pairId, [...(byPair.get(card.pairId) ?? []), card])
      }
      if (byPair.size !== config.pairs) fail(`${bandId} 第 ${i} 副牌凑出 ${byPair.size} 对`)
      for (const [pairId, faces] of byPair) {
        if (faces.length !== 2) fail(`${bandId} 第 ${i} 副牌的 ${pairId} 有 ${faces.length} 张`)
        const [a, b] = faces
        if (!isMatch(a, b)) fail(`${bandId} 第 ${i} 副牌的 ${pairId} 自己配不上`)
        if (a.group !== b.group) fail(`${bandId} 第 ${i} 副牌的 ${pairId} 跨类了`)
        if (config.mode === 'category' && a.glyph === b.glyph) {
          fail(`${bandId} 同类档的 ${pairId} 是两张一样的牌`)
        }
        if (config.mode === 'same' && a.glyph !== b.glyph) {
          fail(`${bandId} 同图档的 ${pairId} 是两张不同的牌`)
        }
        if (/NaN|undefined/.test(matchReason(a, b, deck.mode))) {
          fail(`${bandId} 第 ${i} 副牌的配对讲解渲染异常`)
        }
      }

      // 不同对的牌不能被判成一对，否则随便点两张都能配上
      const first = deck.cards[0]
      const stranger = deck.cards.find((c) => c.pairId !== first.pairId)
      if (isMatch(first, stranger)) fail(`${bandId} 第 ${i} 副牌把不同对的牌判成了一对`)
      if (isMatch(first, first)) fail('同一张牌不该跟自己配成一对')
    }
  }
  console.log(`配对记忆 ${decks} 副牌（5 档 × 200）：两两成对、同类档确为同类、可按种子复现`)
}

for (const [id, info] of Object.entries(ERROR_TAGS)) {
  if (!info.label || !info.tip) fail(`错因标签 ${id} 缺少文案`)
}
console.log(`错因标签 ${Object.keys(ERROR_TAGS).length} 条`)

if (Math.abs(noteToFreq('A4') - 440) > 1e-9) fail(`A4 应为 440Hz，实际 ${noteToFreq('A4')}`)
if (Math.abs(noteToFreq('C5') - 523.2511) > 1e-3) fail(`C5 频率不对：${noteToFreq('C5')}`)
if (!(noteToFreq('Eb4') < noteToFreq('E4'))) fail('Eb4 应低于 E4')
if (noteToFreq('H4') !== null) fail('非法音名应返回 null')
let noteCount = 0
for (const [name, cue] of Object.entries(CUES)) {
  if (!cue.notes.length) fail(`音效 ${name} 没有音符`)
  for (const note of cue.notes) {
    noteCount++
    if (noteToFreq(note) === null) fail(`音效 ${name} 里的音名无法解析：${note}`)
  }
}
console.log(`音效谱面 ${Object.keys(CUES).length} 段共 ${noteCount} 个音：音名全部可解析`)

const streakEndings = STREAK_CUES.map((cue) => noteToFreq(cue.notes[cue.notes.length - 1]))
if (streakEndings.some((freq, index) => index > 0 && freq <= streakEndings[index - 1])) {
  fail('连对音效的收尾音没有逐级升高')
}
if (streakCue(0) !== STREAK_CUES[0] || streakCue(999) !== STREAK_CUES[STREAK_CUES.length - 1]) {
  fail('连对音效没有在安全音域内封顶')
}
console.log(`连对音效 ${STREAK_CUES.length} 档：音高递进并在最高档封顶`)

/* 自适应引擎：用固定种子跑，结论必须每次都一样 */

/** mulberry32：小、快、可复现，够做分布回归。 */
function seeded(seed) {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = Math.imul(a ^ (a >>> 15), 1 | a)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const weightAt = (m) => skillWeight('add-within-10', { mastery: { 'add-within-10': m } })
const masteryLadder = [0, 0.2, 0.4, 0.6, 0.79]
const ladderWeights = masteryLadder.map(weightAt)
for (let i = 1; i < ladderWeights.length; i++) {
  if (ladderWeights[i] >= ladderWeights[i - 1]) {
    fail(`掌握度 ${masteryLadder[i]} 的权重没有低于 ${masteryLadder[i - 1]}`)
  }
}
// 达标之后只留固定的复习权重，不再随掌握度继续掉
if (weightAt(MASTERY_THRESHOLD) !== weightAt(1)) fail('达标区间的复习权重应当是常数')
if (!(weightAt(MASTERY_THRESHOLD) < ladderWeights.at(-1))) fail('已达标技能权重没有低于弱项')
const freshWeight = skillWeight('add-within-10', { mastery: {} })
if (!(freshWeight < ladderWeights[0] && freshWeight > weightAt(1))) {
  fail(`新技能权重 ${freshWeight} 应落在「全不会」和「已达标」之间`)
}

const owedWeight = skillWeight('add-within-10', {
  mastery: { 'add-within-10': 0.5 },
  wrongBook: { 'arithmetic:7+5': { skill: 'add-within-10', attempts: 3 } },
})
const plainWeight = skillWeight('add-within-10', { mastery: { 'add-within-10': 0.5 } })
if (!(owedWeight > plainWeight)) fail('错题本欠账没有抬高技能权重')
const cooledWeight = skillWeight('add-within-10', {
  mastery: { 'add-within-10': 0.5 },
  recent: ['add-within-10'],
})
if (!(cooledWeight < plainWeight)) fail('刚出过的技能没有降权')

// 弱项 vs 已达标：4000 次加权抽样里弱项必须占压倒多数
const pool = [
  { id: 'weak', skill: 'sub-borrow-20' },
  { id: 'strong', skill: 'add-within-10' },
]
const distMastery = { 'sub-borrow-20': 0.15, 'add-within-10': 0.95 }
const rng = seeded(20260426)
const hits = { weak: 0, strong: 0 }
for (let i = 0; i < 4000; i++) {
  const picked = pickNextQuestion(pool, { mastery: distMastery, rng })
  hits[picked.question.id] += 1
}
if (hits.weak < hits.strong * 5) {
  fail(`弱项只抽到 ${hits.weak} 次，达标技能 ${hits.strong} 次，弱项加权不明显`)
}

// 同样掌握度下，进过错题本的那道题要被优先重练
const bookPool = [
  { id: '7+5', skill: 'add-carry-20' },
  { id: '6+4', skill: 'add-carry-20' },
]
const bookRng = seeded(777)
const bookHits = { '7+5': 0, '6+4': 0 }
for (let i = 0; i < 4000; i++) {
  const picked = pickNextQuestion(bookPool, {
    mastery: { 'add-carry-20': 0.5 },
    wrongBook: { '7+5': { skill: 'add-carry-20', attempts: 3 } },
    wrongKeyOf: (q) => q.id,
    rng: bookRng,
  })
  bookHits[picked.question.id] += 1
}
if (bookHits['7+5'] <= bookHits['6+4'] * 1.5) {
  fail(`错题 ${bookHits['7+5']} 次 vs 新题 ${bookHits['6+4']} 次，错题本加成太弱`)
}

// 空池子返回 null，非空池子永远给得出一道题
if (pickNextQuestion([], {}) !== null) fail('空候选池应返回 null')
if (!pickNextQuestion([{ id: 'x' }], { rng: () => 0.999 })) fail('非空候选池不该挑不出题')

// 难度档：连对升、连错降，两头夹住
const steps = [10, 20, 100]
if (nextDifficulty(10, { streak: 3 }, { steps }) !== 20) fail('连对 3 题没有升档')
if (nextDifficulty(10, { streak: 2 }, { steps }) !== 10) fail('连对 2 题就升档了')
if (nextDifficulty(20, { missStreak: 2 }, { steps }) !== 10) fail('连错 2 题没有降档')
if (nextDifficulty(100, { streak: 9 }, { steps }) !== 100) fail('最高档还能继续升')
if (nextDifficulty(10, { missStreak: 9 }, { steps }) !== 10) fail('最低档还能继续降')
if (nextDifficulty(10, { streak: 9 }, { steps: [] }) !== 10) fail('没有档位序列时不该换档')

// 引擎：掌握度按 EMA 推进，升降档后 streak 归零
const engine = createAdaptiveEngine({ steps, mastery: {}, rng: seeded(1) })
let expected
for (let i = 0; i < 3; i++) expected = updateMastery(expected, true)
const up = [true, true, true].map((ok) => engine.record('add-within-10', ok)).at(-1)
if (!up.changed || up.difficulty !== 20 || up.direction !== 'up') {
  fail(`连对 3 题后应升到 20 档，实际 ${up.difficulty}（changed=${up.changed}）`)
}
if (up.streak !== 0) fail(`升档后连对数应清零，实际 ${up.streak}`)
if (engine.state.mastery['add-within-10'] !== expected) {
  fail(`引擎掌握度 ${engine.state.mastery['add-within-10']} 与 updateMastery 推进结果 ${expected} 不一致`)
}
const down = [false, false].map((ok) => engine.record('add-within-10', ok)).at(-1)
if (!down.changed || down.difficulty !== 10 || down.direction !== 'down') {
  fail(`连错 2 题后应降回 10 档，实际 ${down.difficulty}`)
}

// 同一种子跑两遍必须一模一样，否则回归测试没有意义
const replay = (seed) => {
  const e = createAdaptiveEngine({ steps, mastery: distMastery, rng: seeded(seed) })
  return Array.from({ length: 50 }, () => e.pickNextQuestion(pool).question.id).join('')
}
if (replay(42) !== replay(42)) fail('同一随机种子两次调度结果不一致')

const advice = weakestSkills(
  [{ id: 'add-within-10' }, { id: 'sub-borrow-20' }, { id: 'mul-table' }],
  {
    mastery: { 'add-within-10': 0.9, 'sub-borrow-20': 0.2, 'mul-table': 0.6 },
  },
  2,
)
if (advice.length !== 2) fail(`建议列表应有 2 条，实际 ${advice.length}`)
if (advice[0]?.id !== 'sub-borrow-20') fail(`最该补的应是最弱的技能，实际 ${advice[0]?.id}`)
if (advice.some((s) => s.mastery >= MASTERY_THRESHOLD)) fail('已达标技能不该出现在补练建议里')

console.log(
  `自适应引擎：弱项抽中 ${hits.weak}/4000（达标 ${hits.strong}），` +
    `错题优先 ${bookHits['7+5']}:${bookHits['6+4']}，升降档与 EMA 推进一致`,
)

console.log(failures ? `\n${failures} 项不通过。` : '\n全部通过。')
process.exit(failures ? 1 : 0)
