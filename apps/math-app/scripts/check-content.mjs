/**
 * 内容自检：不开浏览器，直接把题库和生成器跑上几千次，
 * 确认不会出现负数答案、NaN 文案、重复选项、无解或多解的数独。
 */
import {
  SCENE_SKINS,
  SEMANTIC_TEMPLATES,
  WORD_PROBLEMS,
  WORD_PROBLEM_TAGS,
  WORD_PROBLEM_TIERS,
  problemsOfTier,
} from '../src/data/wordProblems.js'
import {
  AGE_BANDS,
  AGE_BAND_MODULES,
  COUNTING_QUESTION_IDS,
  DEFAULT_AGE_BAND,
  GEOMETRY_QUESTION_IDS,
  LOGIC_PATTERN_IDS,
  bandOf,
} from '../src/data/age-band.js'
import { isKnownSkill, SKILLS, SKILL_MAP, skillsOfModule } from '../src/data/curriculum.js'
import {
  buildSkillGraph,
  GRAPH_SIZE,
  RECOMMEND_REASON_MAP,
  SKILL_EDGES,
  SKILL_LANES,
  SKILL_NODES,
  SKILL_NODE_MAP,
  recommend,
  recommendPath,
} from '../src/data/skill-graph.js'
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
  buildFocusDailyQuestion,
  buildFocusDailyQuestions,
  canDailyFocus,
  DAILY_FOCUS_SKILLS,
  DAILY_SIZE,
  DAILY_TEMPLATE_IDS,
  dailyFocusSeed,
} from '../src/data/daily.js'
import { practiceEntries, practiceEntry, wrongCountsBySkill } from '../src/data/skill-practice.js'
import {
  ADOPTION_STATE_MAP,
  buildWeekPlan,
  projectSession,
  shiftDateKey,
  WEEK_PLAN_DAYS,
  WEEK_PLAN_PER_DAY,
  weekPlanAdoption,
} from '../src/data/week-plan.js'
import { ERROR_TAGS } from '../src/data/errorTags.js'
import { CUES, noteToFreq, STREAK_CUES, streakCue } from '../src/utils/sound.js'
import { updateMastery, MASTERY_THRESHOLD } from '../src/utils/mastery.js'
import { LEARN_DEMOS, LEARN_DEMO_STAGES, objectTiles } from '../src/data/learn-demos.js'
import { hasLearnDemo, LEARN_DEMO_SKILLS, learnDemoRoute } from '../src/data/learn-demo-index.js'
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

/**
 * 年龄档 L1–L5：六个玩法的默认难度必须填齐，每个值都得是对应玩法真认得的档位，
 * 而且档位越高不能反而越简单——否则家长把档往上调，孩子做的题却变容易了。
 */
{
  const SUDOKU_DIFFICULTIES = ['easy', 'normal', 'hard'] // SudokuView 的 DIFFICULTIES
  const ARITHMETIC_LEVELS = [10, 20, 100] // ArithmeticView 的 LEVELS
  const ARITHMETIC_OPS = ['add', 'sub', 'mix']
  const GEOMETRY_SCOPES = ['2d', '3d', 'all']
  const PLANE_ONLY = ['sides', 'odd'] // GeometryView 在立体范围下会去掉这两种
  const tierIds = WORD_PROBLEM_TIERS.map((t) => t.id)
  const moduleKeys = AGE_BAND_MODULES.map((m) => m.key)

  if (AGE_BANDS.length !== 5) fail(`年龄档应有 L1–L5 共 5 档，实际 ${AGE_BANDS.length} 档`)
  if (!AGE_BANDS.some((b) => b.id === DEFAULT_AGE_BAND)) fail(`默认档位 ${DEFAULT_AGE_BAND} 不在表里`)
  if (bandOf('不存在的档位').id !== DEFAULT_AGE_BAND) fail('bandOf 遇到未知档位没有回落到默认档')

  for (const band of AGE_BANDS) {
    const d = band.defaults
    const at = `年龄档 ${band.id}`
    if (!band.name || !band.desc) fail(`${at} 缺少名称或说明`)
    for (const key of moduleKeys) {
      if (!band.hints?.[key]) fail(`${at} 缺少「${key}」的难度说明`)
    }

    const { ceilings, dragCap, steps, mix } = d.counting
    if (!(ceilings?.length === 2 && ceilings[0] >= 3 && ceilings[1] >= ceilings[0])) {
      fail(`${at} 数量星云的数值上限不合理：${JSON.stringify(ceilings)}`)
    }
    if (!(dragCap >= 5)) fail(`${at} 装货题上限 ${dragCap} 太小，凑不出题`)
    if (!steps?.length || steps.some((s) => !Number.isInteger(s) || s < 1)) {
      fail(`${at} 数序题的公差不合法：${JSON.stringify(steps)}`)
    }
    const mixKeys = Object.keys(mix)
    if (mixKeys.some((k) => !COUNTING_QUESTION_IDS.includes(k))) {
      fail(`${at} 题型权重里有未知题型：${mixKeys.join('、')}`)
    }
    for (const id of COUNTING_QUESTION_IDS) {
      if (!(mix[id] > 0)) fail(`${at} 没给题型「${id}」权重，这一档永远抽不到它`)
    }

    if (!GEOMETRY_SCOPES.includes(d.geometry.scope)) fail(`${at} 图形范围不合法：${d.geometry.scope}`)
    if (!d.geometry.makers.length) fail(`${at} 形状卫星一种题型都没开`)
    for (const id of d.geometry.makers) {
      if (!GEOMETRY_QUESTION_IDS.includes(id)) fail(`${at} 形状卫星有未知题型：${id}`)
    }
    if (d.geometry.scope === '3d' && d.geometry.makers.every((id) => PLANE_ONLY.includes(id))) {
      fail(`${at} 立体范围下所有题型都会被过滤掉，出不了题`)
    }

    if (!d.logic.length) fail(`${at} 规律环带一种题型都没开`)
    for (const id of d.logic) {
      if (!LOGIC_PATTERN_IDS.includes(id)) fail(`${at} 规律环带有未知题型：${id}`)
    }

    if (!ARITHMETIC_LEVELS.includes(d.arithmetic.level)) {
      fail(`${at} 口算档位 ${d.arithmetic.level} 不在 ${ARITHMETIC_LEVELS.join('/')} 里`)
    }
    if (!ARITHMETIC_OPS.includes(d.arithmetic.op)) fail(`${at} 口算运算类型不合法：${d.arithmetic.op}`)
    if (!tierIds.includes(d.word)) fail(`${at} 应用题难度档「${d.word}」不存在`)
    if (!problemsOfTier(d.word).length) fail(`${at} 应用题难度档「${d.word}」一道母题都没有`)
    if (!SUDOKU_SIZES.includes(d.sudoku.size)) fail(`${at} 数独棋盘 ${d.sudoku.size} 不存在`)
    if (!SUDOKU_DIFFICULTIES.includes(d.sudoku.difficulty)) {
      fail(`${at} 数独挖洞档「${d.sudoku.difficulty}」不存在`)
    }
  }

  for (let i = 1; i < AGE_BANDS.length; i++) {
    const prev = AGE_BANDS[i - 1]
    const cur = AGE_BANDS[i]
    const worse = (key, get) => {
      if (get(cur) < get(prev)) fail(`${cur.id} 的${key}反而低于 ${prev.id}`)
    }
    worse('数量上限', (b) => b.defaults.counting.ceilings[1])
    worse('口算档位', (b) => b.defaults.arithmetic.level)
    worse('数独棋盘', (b) => b.defaults.sudoku.size)
  }

  console.log(
    `年龄档 ${AGE_BANDS.map((b) => b.id).join('/')}：` +
      `各驱动 ${moduleKeys.length} 个玩法的默认难度，档位越高越难`,
  )
}

/* ROUND16_H4 学演示注册表：每条挂一个技能点，完整走完「实物 → 图形 → 算式」三段。 */
{
  const MIN_LEARN_DEMOS = 12
  const demoIds = new Set()
  const demoSkills = new Set()
  if (LEARN_DEMOS.length < MIN_LEARN_DEMOS) {
    fail(`学演示只有 ${LEARN_DEMOS.length} 条，少于要求的 ${MIN_LEARN_DEMOS} 个技能点`)
  }
  for (const demo of LEARN_DEMOS) {
    if (!demo.id || demoIds.has(demo.id)) fail(`学演示 id 缺失或重复：${demo.id}`)
    demoIds.add(demo.id)
    if (!demo.object?.label || !demo.object?.emoji) fail(`学演示 ${demo.id} 缺少实物段`)
    if (!demo.visual?.label || !demo.visual?.groups?.length) fail(`学演示 ${demo.id} 缺少图形段`)
    if (!demo.equation) fail(`学演示 ${demo.id} 缺少算式段`)
    // 三句旁白一段一句：跳过与 reduced-motion 静态三态都靠它对齐面板
    if (demo.narration?.length !== LEARN_DEMO_STAGES.length) {
      fail(`学演示 ${demo.id} 应有 ${LEARN_DEMO_STAGES.length} 段旁白`)
    }
    if (demo.skill !== demo.skillId) fail(`学演示 ${demo.id} 的 skill 与 skillId 不一致`)
    if (!isKnownSkill(demo.skill)) fail(`学演示 ${demo.id} 技能点「${demo.skill}」不在图谱里`)
    // 一个技能点最多一条演示：练习入口按技能取，重复了就说不清弹哪条
    if (demoSkills.has(demo.skill)) fail(`技能点「${demo.skill}」挂了不止一条学演示`)
    demoSkills.add(demo.skill)
    if (!SKILL_MAP[demo.skill] || SKILL_MAP[demo.skill].module !== demo.module) {
      fail(`学演示 ${demo.id} 的模块「${demo.module}」和技能点所属模块对不上`)
    }
    const tiles = objectTiles(demo.object)
    if (!tiles.length || tiles.some((tile) => !tile.items.length)) {
      fail(`学演示 ${demo.id} 的实物段渲染不出任何实物`)
    }
  }

  // 练习壳只静态引 learn-demo-index（见那里的说明），两边漏改一边就会给出死入口
  const listed = new Set(LEARN_DEMO_SKILLS)
  if (LEARN_DEMO_SKILLS.length !== listed.size) fail('learn-demo-index 的技能清单里有重复项')
  for (const skill of demoSkills) {
    if (!listed.has(skill)) fail(`learn-demo-index 少登记了技能点「${skill}」`)
  }
  for (const skill of listed) {
    if (!demoSkills.has(skill)) fail(`learn-demo-index 多登记了技能点「${skill}」`)
    if (!hasLearnDemo(skill)) fail(`hasLearnDemo 认不出已登记的技能点「${skill}」`)
    if (learnDemoRoute(skill)?.query?.skill !== skill) fail(`「${skill}」的演示深链没带上技能点`)
  }
  if (learnDemoRoute('not-a-skill') !== null) fail('没有演示的技能点不该给出深链')

  const byModule = {}
  for (const demo of LEARN_DEMOS) byModule[demo.module] = (byModule[demo.module] ?? 0) + 1
  console.log(
    `学演示 ${LEARN_DEMOS.length} 个技能点：实物 / 图形 / 算式 / 三段旁白齐全（` +
      `${Object.entries(byModule)
        .map(([m, n]) => `${m} ${n}`)
        .join('、')}）`,
  )
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

/**
 * 技能图谱：节点、连线、布局与判读。
 *
 * 图谱页是只读视图，一旦布局算错（节点重叠、连线倒着画）或状态判错（前置没通
 * 却显示可开练），家长看到的就是一张会撒谎的地图，而这在浏览器里很难一眼看出来，
 * 所以在这里把几何和判读都验死。
 */
{
  const nodeIds = new Set(SKILL_NODES.map((n) => n.id))
  if (nodeIds.size !== SKILL_NODES.length) fail('技能图谱存在重复节点')
  for (const skill of SKILLS) {
    if (!nodeIds.has(skill.id)) fail(`技能点「${skill.id}」没有出现在图谱上`)
  }
  for (const node of SKILL_NODES) {
    if (!SKILL_MAP[node.id]) fail(`图谱节点「${node.id}」不在 curriculum 里`)
    if (!node.name || !node.level) fail(`图谱节点「${node.id}」缺少名称或等级`)
    if (node.x < 0 || node.y < 0) fail(`图谱节点「${node.id}」坐标为负：${node.x},${node.y}`)
    if (node.x + node.w > GRAPH_SIZE.width || node.y + node.h > GRAPH_SIZE.height) {
      fail(`图谱节点「${node.id}」溢出画布 ${GRAPH_SIZE.width}×${GRAPH_SIZE.height}`)
    }
  }

  // 依赖必须严格从左往右：前置节点的右边缘不能越过后继节点的左边缘
  const edgeIds = new Set()
  for (const edge of SKILL_EDGES) {
    if (edgeIds.has(edge.id)) fail(`图谱连线重复：${edge.id}`)
    edgeIds.add(edge.id)
    const from = SKILL_NODE_MAP[edge.from]
    const to = SKILL_NODE_MAP[edge.to]
    if (!from || !to) {
      fail(`图谱连线 ${edge.id} 指向了不存在的节点`)
      continue
    }
    if (from.depth >= to.depth) {
      fail(`图谱连线 ${edge.id} 从深度 ${from.depth} 连到 ${to.depth}，会画成倒着的箭头`)
    }
    if (!/^M [\d.]+ [\d.]+ C /.test(edge.path)) fail(`图谱连线 ${edge.id} 的路径不合法`)
  }
  const depCount = SKILLS.reduce((sum, s) => sum + (s.deps?.length ?? 0), 0)
  if (SKILL_EDGES.length !== depCount) {
    fail(`图谱连线 ${SKILL_EDGES.length} 条，curriculum 里有 ${depCount} 条依赖`)
  }

  // 同一模块泳道内不许重叠：重叠就意味着两个节点画在同一个格子上
  for (const lane of SKILL_LANES) {
    const boxes = SKILL_NODES.filter((n) => n.module === lane.module)
    for (const node of boxes) {
      if (node.y < lane.top || node.y + node.h > lane.top + lane.height) {
        fail(`节点「${node.id}」跑出了「${lane.name}」泳道`)
      }
    }
    for (let i = 0; i < boxes.length; i++) {
      for (let j = i + 1; j < boxes.length; j++) {
        const a = boxes[i]
        const b = boxes[j]
        if (a.x === b.x && a.y === b.y) fail(`节点「${a.id}」与「${b.id}」画在同一个位置`)
      }
    }
  }
  const laneSkills = SKILL_LANES.flatMap((l) => l.skills)
  if (laneSkills.length !== SKILLS.length) {
    fail(`泳道只收了 ${laneSkills.length} 个技能，curriculum 有 ${SKILLS.length} 个`)
  }

  // 判读：空存档下只有无前置的技能可开练，其余一律待解锁
  const empty = buildSkillGraph({ mastery: {}, ageBand: 'L1' })
  for (const node of empty.nodes) {
    const want = node.deps.length ? 'locked' : 'ready'
    if (node.status !== want) fail(`空存档下「${node.id}」应为 ${want}，实际 ${node.status}`)
  }
  if (empty.stats.mastered !== 0) fail('空存档却算出了已掌握的技能')
  if (empty.nodes.some((n) => n.percent !== 0)) fail('空存档却算出了非零掌握度')

  // 达标一个前置，只应让它的直接后继变成「可开练」，不该越级放行
  const seeded = buildSkillGraph({
    mastery: { 'count-to-5': MASTERY_THRESHOLD, 'add-within-10': 0.4 },
    ageBand: 'L2',
  })
  const statusById = Object.fromEntries(seeded.nodes.map((n) => [n.id, n.status]))
  if (statusById['count-to-5'] !== 'mastered') fail('达标的技能没有判成已掌握')
  if (statusById['count-to-10'] !== 'ready') fail('前置达标后的技能没有变成可开练')
  if (statusById['count-to-20'] !== 'locked') fail('隔了一层前置的技能被越级放行')
  if (statusById['add-within-10'] !== 'learning') fail('练过没过线的技能没有判成练习中')
  if (!seeded.edges.find((e) => e.id === 'count-to-5->count-to-10')?.open) {
    fail('前置达标后连线没有变成已打通')
  }

  // 年龄档只影响「在不在本档」的标注，不改状态：图谱是只读的
  const bands = AGE_BANDS.map((band) => buildSkillGraph({ mastery: {}, ageBand: band.id }))
  for (const graph of bands) {
    if (graph.nodes.some((n, i) => n.status !== empty.nodes[i].status)) {
      fail(`档位 ${graph.band} 改变了技能状态，年龄档不该影响判读`)
    }
  }
  const inBandCounts = bands.map((g) => g.nodes.filter((n) => n.inBand).length)
  for (let i = 1; i < inBandCounts.length; i++) {
    if (inBandCounts[i] < inBandCounts[i - 1]) {
      fail(`档位越高本档技能反而更少：${inBandCounts[i - 1]} → ${inBandCounts[i]}`)
    }
  }
  if (inBandCounts.at(-1) !== SKILL_NODES.length) fail('最高档没有覆盖全部技能点')
  if (buildSkillGraph({ ageBand: '不存在的档位' }).band !== DEFAULT_AGE_BAND) {
    fail('未知档位没有回落到默认档')
  }

  // 建议列表：只推可以立刻练的，练过没过线的排在全新技能前面
  const advice = seeded.next
  if (!advice.length) fail('技能图谱没给出任何「接下来练什么」的建议')
  if (advice.some((n) => n.status === 'locked' || n.status === 'mastered')) {
    fail('建议列表里混进了待解锁或已掌握的技能')
  }
  if (advice[0]?.id !== 'add-within-10') {
    fail(`建议第一条应是练过没过线的 add-within-10，实际 ${advice[0]?.id}`)
  }

  /**
   * 推荐路径：图谱要回答的不只是「现在能练什么」，还有「照着练下去能拿下什么」。
   * 推荐只许由掌握度和年龄档两个输入决定，且一个字节都不许写回存档——
   * 这里连传进去的 mastery 对象有没有被顺手改过都要验，免得推荐变成隐形的进度写入。
   */
  const RECO_SEED = { 'count-to-5': 0.95, 'count-to-10': 0.9, 'add-within-10': 0.4 }
  const frozen = JSON.stringify(RECO_SEED)
  const views = Object.fromEntries(
    AGE_BANDS.map((band) => [band.id, recommend({ mastery: RECO_SEED, ageBand: band.id })]),
  )
  if (JSON.stringify(RECO_SEED) !== frozen) fail('recommend 改写了传进去的掌握度存档')

  for (const [bandId, view] of Object.entries(views)) {
    if (!view.items.length) fail(`${bandId} 档没有推荐出任何可练的技能`)
    if (view.items.length > 4) fail(`${bandId} 档一口气推了 ${view.items.length} 条`)
    for (const item of view.items) {
      if (item.status !== 'learning' && item.status !== 'ready') {
        fail(`${bandId} 档推荐了 ${item.status} 的「${item.id}」`)
      }
      if (!RECOMMEND_REASON_MAP[item.reason]) fail(`「${item.id}」的推荐理由 ${item.reason} 不认识`)
      if (!item.why) fail(`「${item.id}」没有给出推荐理由文案`)
    }
    const scores = view.items.map((item) => item.score)
    if (scores.some((s, i) => i && s > scores[i - 1])) {
      fail(`${bandId} 档的推荐没有按分数从高到低排：${scores.join(',')}`)
    }
    // 超前技能不许插到本档技能前面
    const lastInBand = view.items.reduce((last, item, i) => (item.reason === 'ahead' ? last : i), -1)
    const firstAhead = view.items.findIndex((item) => item.reason === 'ahead')
    if (firstAhead >= 0 && firstAhead < lastInBand) {
      fail(`${bandId} 档把超前技能「${view.items[firstAhead].id}」排在了本档技能前面`)
    }

    // 路线：终点是目标，途中不含已掌握的技能，且每一步的前置都在它之前补齐
    if (!view.goal) fail(`${bandId} 档没有给出本档目标`)
    if (view.path.at(-1)?.id !== view.goal?.id) {
      fail(`${bandId} 档路线终点「${view.path.at(-1)?.id}」与目标「${view.goal?.id}」对不上`)
    }
    const walked = new Set(
      Object.entries(RECO_SEED)
        .filter(([, v]) => v >= MASTERY_THRESHOLD)
        .map(([id]) => id),
    )
    for (const step of view.path) {
      if (walked.has(step.id)) fail(`${bandId} 档路线里混进了已掌握的「${step.id}」`)
      for (const dep of SKILL_MAP[step.id].deps ?? []) {
        if (!walked.has(dep)) fail(`${bandId} 档路线上「${step.id}」排在了前置「${dep}」前面`)
      }
      walked.add(step.id)
    }
  }

  // 年龄档只换排法：同一份存档换档位，推荐会变，状态一个都不许变
  if (views.L1.items[0].id !== 'add-within-10' || views.L1.items[0].reason !== 'finish') {
    fail(`练过没过线的技能没有排在推荐第一位，实际 ${views.L1.items[0].id}`)
  }
  const reasonOf = (bandId, id) => views[bandId].items.find((i) => i.id === id)?.reason
  if (reasonOf('L1', 'shape-2d') !== 'focus' || reasonOf('L4', 'shape-2d') !== 'base') {
    fail(
      `L1 该把 shape-2d 判成本档主推、L4 该判成补基础，实际 ${reasonOf('L1', 'shape-2d')}/${reasonOf('L4', 'shape-2d')}`,
    )
  }
  if (views.L1.goal.id === views.L4.goal.id) fail('L1 与 L4 的本档目标不该是同一个技能')
  const bandStatuses = Object.values(views).map((view) =>
    recommendPath(view.goal.id, RECO_SEED)
      .map((n) => n.id)
      .join(','),
  )
  if (new Set(bandStatuses).size < 2) fail('各档位的推荐路线完全一样，年龄档没有参与推荐')

  // 全部练熟后不该再有推荐，也不该硬凑一个目标出来
  const finished = recommend({
    mastery: Object.fromEntries(SKILLS.map((s) => [s.id, 1])),
    ageBand: 'L5',
  })
  if (finished.items.length || finished.goal || finished.path.length) {
    fail('技能全部掌握后推荐位没有清空')
  }

  console.log(
    `技能图谱推荐：首推 ${views.L2.items[0].name}（${views.L2.items[0].reasonLabel}），` +
      `L1–L5 目标 ${AGE_BANDS.map(
        (b) => `${b.id}→${views[b.id].goal.name} ${views[b.id].path.length} 步`,
      ).join('，')}`,
  )

  console.log(
    `技能图谱：${SKILL_NODES.length} 节点 / ${SKILL_EDGES.length} 连线 / ${SKILL_LANES.length} 条泳道，` +
      `画布 ${GRAPH_SIZE.width}×${GRAPH_SIZE.height}，L1–L5 本档覆盖 ${inBandCounts.join('→')}`,
  )
}

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

/**
 * 专项冒险：图谱推荐「先补这一点」，点下去开出来的 5 道题就必须真的练在这一点上。
 * 一道题落到哪个技能由 skill-mapping 裁决，所以这里逐题验它的裁决结果——
 * 取值窗口只要有一处没夹住，孩子练的就是另一个技能，而掌握度还会记到推荐的那个上。
 */
{
  const DAYS = 120
  const start = Date.UTC(2026, 0, 1)
  let checked = 0

  if (DAILY_FOCUS_SKILLS.length < 8) {
    fail(`每日冒险只能专练 ${DAILY_FOCUS_SKILLS.length} 个技能点，覆盖面太窄`)
  }
  for (const skill of DAILY_FOCUS_SKILLS) {
    if (!isKnownSkill(skill)) fail(`专项冒险声称能练图谱外的技能点「${skill}」`)
  }
  if (canDailyFocus('sudoku-9')) fail('数独技能不该被当成每日冒险能出的题')
  if (buildFocusDailyQuestions({ skill: 'sudoku-9' }).length) {
    fail('出不了题的技能应返回空题组，而不是硬凑')
  }
  if (buildFocusDailyQuestion(0, { skill: '不存在的技能' }) !== null) {
    fail('认不出的技能点应返回 null')
  }

  for (const skill of DAILY_FOCUS_SKILLS) {
    for (let d = 0; d < DAYS; d++) {
      const dateKey = new Date(start + d * 864e5).toISOString().slice(0, 10)
      const first = buildFocusDailyQuestions({ skill, dateKey })
      const second = buildFocusDailyQuestions({ skill, dateKey })

      if (first.length !== DAILY_SIZE) {
        fail(`${skill} ${dateKey} 的专项冒险有 ${first.length} 题，应为 ${DAILY_SIZE}`)
      }
      if (JSON.stringify(first) !== JSON.stringify(second)) {
        fail(`${skill} ${dateKey} 的专项冒险两次生成不一致，刷新就换题`)
      }

      first.forEach((q, slot) => {
        const seed = dailyFocusSeed(skill, dateKey, slot)
        if (q.seed !== seed) fail(`${q.id} 的种子应为 ${seed}，实际 ${q.seed}`)
        if (q.id !== `${q.templateId}:${seed}`) fail(`${q.id} 的 id 没有带上种子`)
        if (q.focusSkill !== skill) fail(`${q.id} 没有标出它属于哪次专项`)
        if (q.skill !== skill) fail(`${skill} 的专项题 ${q.id} 却记到了「${q.skill}」`)
        if (!q.options.includes(q.answer)) fail(`${q.id} 选项里没有正确答案 ${q.answer}`)
        if (new Set(q.options).size !== q.options.length) fail(`${q.id} 选项有重复`)
        if (typeof q.answer === 'number' && (!Number.isInteger(q.answer) || q.answer < 0)) {
          fail(`${q.id} 的答案不是自然数：${q.answer}`)
        }
        if (/NaN|undefined/.test(q.prompt)) fail(`${q.id} 题干渲染异常：${q.prompt}`)
        if (!q.hints?.length || q.hints.some((h) => /NaN|undefined|-\d/.test(h))) {
          fail(`${q.id} 的提示文案异常：${q.hints?.join(' / ')}`)
        }
        checked++
      })

      if (new Set(first.map((q) => q.id)).size !== first.length) {
        fail(`${skill} ${dateKey} 的专项冒险出现重复题目 id`)
      }
    }
  }

  // 换一天要换题，换技能更要换题；否则「专项」只是换了个标题
  const sameDay = (skill) =>
    buildFocusDailyQuestions({ skill, dateKey: '2026-05-04' })
      .map((q) => q.prompt)
      .join('|')
  if (sameDay('add-carry-20') === sameDay('add-within-10')) {
    fail('同一天里两个技能的专项冒险出了同一套题')
  }
  if (
    sameDay('add-carry-20') ===
    buildFocusDailyQuestions({ skill: 'add-carry-20', dateKey: '2026-05-05' })
      .map((q) => q.prompt)
      .join('|')
  ) {
    fail('相邻两天的专项冒险题目完全相同')
  }
  // 专项冒险和当天的常规冒险各走各的种子，不该互相顶掉
  const regular = new Set(buildDailyQuestions('2026-05-04').map((q) => q.id))
  if (buildFocusDailyQuestions({ skill: 'add-carry-20', dateKey: '2026-05-04' }).some((q) => regular.has(q.id))) {
    fail('专项冒险的题目 id 撞上了当天常规冒险的题')
  }

  console.log(
    `专项冒险 ${DAILY_FOCUS_SKILLS.length} 个技能 × ${DAYS} 天共 ${checked} 道：` +
      `逐题落回本技能、同日可复现、与常规冒险互不覆盖`,
  )
}

/**
 * 推荐 → 开练入口：推荐排完序之后，「去练」得落到真能练这一点的地方。
 * 落点只由推荐项和错题本快照决定，且和推荐一样是只读的。
 */
{
  const RECO_SEED = { 'count-to-5': 0.95, 'count-to-10': 0.9, 'add-within-10': 0.4 }
  const view = recommend({ mastery: RECO_SEED, ageBand: 'L2' })

  const clean = practiceEntries(view.items, { wrongBook: {} })
  if (clean.length !== view.items.length) fail('有推荐项算不出开练入口')
  for (const [index, entry] of clean.entries()) {
    const item = view.items[index]
    if (entry.skill !== item.id) fail(`第 ${index + 1} 条入口指向了别的技能「${entry.skill}」`)
    if (!entry.label || !entry.hint) fail(`「${entry.skill}」的入口没有文案`)
    if (!entry.to?.path) fail(`「${entry.skill}」的入口没有落点路由`)
    const want = canDailyFocus(item.id) ? 'daily' : 'planet'
    if (entry.kind !== want) fail(`空错题本下「${item.id}」的落点应是 ${want}，实际 ${entry.kind}`)
    if (entry.kind === 'daily' && entry.to.query?.focus !== item.id) {
      fail(`「${item.id}」的日冒险入口没有带上技能：${JSON.stringify(entry.to.query)}`)
    }
    if (entry.kind === 'planet' && entry.to.path !== item.route) {
      fail(`「${item.id}」的星球入口指向 ${entry.to.path}，应为 ${item.route}`)
    }
  }

  // 欠着错题就先还账：同一条推荐的落点从日冒险换成错题重练
  const owed = {
    'arithmetic:7+3': { skill: 'add-within-10', attempts: 2 },
    'arithmetic:8+2': { skill: 'add-within-10', attempts: 1 },
    'daily:no-skill': { attempts: 1 },
  }
  const counts = wrongCountsBySkill(owed)
  if (counts['add-within-10'] !== 2) fail(`错题欠账应按技能算出 2 道，实际 ${counts['add-within-10']}`)
  if (Object.keys(counts).length !== 1) fail('没有技能点的错题不该被算进任何技能的欠账')

  const owedEntry = practiceEntry(
    view.items.find((item) => item.id === 'add-within-10'),
    { wrongBook: owed },
  )
  if (owedEntry.kind !== 'wrongBook') fail(`欠着错题时落点应是错题本，实际 ${owedEntry.kind}`)
  if (owedEntry.to.query?.wrong !== 'add-within-10') fail('错题重练入口没有带上技能点')
  if (owedEntry.wrongCount !== 2) fail(`错题重练入口应显示 2 道，实际 ${owedEntry.wrongCount}`)
  if (owedEntry.planet.route !== '/arithmetic') fail('错题落点丢了它自己的星球入口')

  if (JSON.stringify(RECO_SEED) !== JSON.stringify({ 'count-to-5': 0.95, 'count-to-10': 0.9, 'add-within-10': 0.4 })) {
    fail('算开练入口时改写了掌握度存档')
  }
  if (practiceEntry(null) !== null) fail('没有技能点的推荐项不该算出入口')

  const kinds = clean.map((entry) => entry.kind)
  console.log(
    `开练入口：L2 首条「${view.items[0].name}」落到 ${clean[0].kind}（${clean[0].label}），` +
      `欠账时改走错题本 ${owedEntry.wrongCount} 道，本档落点 ${kinds.join(' / ')}`,
  )
}

/**
 * 周计划：推荐排的是「此刻练什么」，周计划排的是「这一周怎么练」。
 * 它必须是**滚动**的——照着练下去，过了线的技能要从后面几天里退场，
 * 新解锁的补进来；而且推演全程只在副本上跑，一个字节都不许写回存档。
 */
{
  const PLAN_SEED = { 'count-to-5': 0.95, 'count-to-10': 0.9, 'add-within-10': 0.4 }
  const PLAN_BOOK = {
    'arithmetic:7+3': { skill: 'add-within-10', answer: 10, attempts: 2 },
    'arithmetic:8+2': { skill: 'add-within-10', answer: 10, attempts: 1 },
  }
  const frozenSeed = JSON.stringify(PLAN_SEED)
  const frozenBook = JSON.stringify(PLAN_BOOK)
  const START = '2026-05-04'

  const plan = buildWeekPlan({
    mastery: PLAN_SEED,
    ageBand: 'L2',
    wrongBook: PLAN_BOOK,
    startDate: START,
  })
  if (JSON.stringify(PLAN_SEED) !== frozenSeed) fail('周计划改写了传进去的掌握度存档')
  if (JSON.stringify(PLAN_BOOK) !== frozenBook) fail('周计划改写了传进去的错题本')

  // 一天一格，日期连着排，头两天说人话
  if (plan.days.length !== WEEK_PLAN_DAYS) fail(`周计划排了 ${plan.days.length} 天`)
  plan.days.forEach((day, index) => {
    if (day.dateKey !== shiftDateKey(START, index)) {
      fail(`第 ${index + 1} 天的日期 ${day.dateKey} 不接在 ${START} 后面`)
    }
    if (day.skills.length > WEEK_PLAN_PER_DAY) {
      fail(`第 ${index + 1} 天排了 ${day.skills.length} 个技能，一天最多 ${WEEK_PLAN_PER_DAY} 个`)
    }
    if (!day.label) fail(`第 ${index + 1} 天没有日历称呼`)
  })
  if (plan.days[0].label !== '今天' || plan.days[1].label !== '明天') {
    fail(`头两天该叫「今天/明天」，实际 ${plan.days[0].label}/${plan.days[1].label}`)
  }
  if (!plan.days[0].today || plan.days[1].today) fail('周计划没有标出哪一天是今天')

  // 每一场功课都得说得出理由、给得出落点，推演值只许往上走
  for (const day of plan.days) {
    for (const skill of day.skills) {
      if (!RECOMMEND_REASON_MAP[skill.reason]) {
        fail(`第 ${day.day} 天「${skill.id}」的理由 ${skill.reason} 不认识`)
      }
      if (!skill.why || !skill.reasonHint) fail(`第 ${day.day} 天「${skill.id}」没有理由文案`)
      if (!skill.entry?.to?.path) fail(`第 ${day.day} 天「${skill.id}」没有开练入口`)
      if (skill.mastery >= MASTERY_THRESHOLD) {
        fail(`第 ${day.day} 天还在排已过线的「${skill.id}」`)
      }
      if (!(skill.projected > skill.mastery)) {
        fail(`「${skill.id}」练一场的推演值 ${skill.projected} 没有涨`)
      }
      if (skill.projected !== projectSession(skill.mastery)) {
        fail(`「${skill.id}」的推演没走 projectSession`)
      }
    }
  }

  // 滚动：过了线就退场，后面的日子必须让给别的技能
  const seenAfterPass = plan.skills.filter(
    (row) => row.passOnDay && row.days.some((day) => day > row.passOnDay),
  )
  if (seenAfterPass.length) {
    fail(`「${seenAfterPass[0].id}」预计第 ${seenAfterPass[0].passOnDay} 天过线，后面还排着`)
  }
  if (plan.skills.length <= WEEK_PLAN_PER_DAY) {
    fail(`一周只排了 ${plan.skills.length} 个技能，等于把今天的推荐抄了 ${WEEK_PLAN_DAYS} 遍`)
  }
  const dayOneIds = plan.days[0].skills.map((s) => s.id).join(',')
  if (plan.days.at(-1).skills.map((s) => s.id).join(',') === dayOneIds) {
    fail('第一天和最后一天排的是同一批技能，计划没有滚动')
  }

  // 欠着错题的先还账：它排在第一天头一场，落点也走错题重练
  if (plan.days[0].skills[0].id !== 'add-within-10') {
    fail(`欠着 2 道错题的技能没有排在第一场，实际 ${plan.days[0].skills[0].id}`)
  }
  if (plan.days[0].skills[0].entry.kind !== 'wrongBook') {
    fail(`第一场的落点应是错题重练，实际 ${plan.days[0].skills[0].entry.kind}`)
  }
  // 账当天还清，后面几天不该再按欠账排
  if (plan.days.slice(1).some((day) => day.skills.some((s) => s.entry.kind === 'wrongBook'))) {
    fail('周计划把同一笔错题欠账重复算到了后面几天')
  }

  // 同样的输入排出同样的计划；换个档位就该换一份
  const again = buildWeekPlan({
    mastery: PLAN_SEED,
    ageBand: 'L2',
    wrongBook: PLAN_BOOK,
    startDate: START,
  })
  if (JSON.stringify(again) !== JSON.stringify(plan)) fail('同样的输入排出了两份不同的周计划')
  const planOf = (band) =>
    buildWeekPlan({ mastery: PLAN_SEED, ageBand: band, startDate: START })
      .days.flatMap((day) => day.skills.map((s) => s.id))
      .join(',')
  if (planOf('L1') === planOf('L4')) fail('L1 与 L4 排出的周计划一模一样，年龄档没有参与排期')

  // 全部练熟之后不该硬凑功课，七天全是自由练
  const done = buildWeekPlan({
    mastery: Object.fromEntries(SKILLS.map((s) => [s.id, 1])),
    ageBand: 'L5',
    startDate: START,
  })
  if (done.stats.sessions !== 0 || done.stats.restDays !== WEEK_PLAN_DAYS) {
    fail(`技能全部过线后仍排了 ${done.stats.sessions} 场功课`)
  }
  if (done.days.some((day) => !day.note)) fail('空出来的日子没有给家长一句交代')

  /* 采纳痕迹：只读统计，只认存档里已经有的记录，不新记任何东西 */
  const adoption = weekPlanAdoption(plan, {
    mastery: PLAN_SEED,
    wrongBook: PLAN_BOOK,
    modules: { arithmetic: { lastPlayed: 1_700_000_000_000 } },
  })
  if (JSON.stringify(PLAN_SEED) !== frozenSeed) fail('采纳统计改写了掌握度存档')
  if (adoption.total !== plan.skills.length) fail('采纳统计漏掉了计划里的技能')
  if (adoption.passed + adoption.owed + adoption.practiced + adoption.untouched !== adoption.total) {
    fail('采纳统计的四种痕迹加不齐总数')
  }
  for (const row of adoption.rows) {
    if (!ADOPTION_STATE_MAP[row.state]) fail(`「${row.id}」的痕迹 ${row.state} 不认识`)
    if (!row.trace) fail(`「${row.id}」没有给出痕迹说明`)
    if (!row.reasonLabel || !row.why) fail(`「${row.id}」在家长页丢了推荐理由`)
    if (!row.days.length) fail(`「${row.id}」没有标出排在周几`)
  }
  const owedRow = adoption.rows.find((row) => row.id === 'add-within-10')
  if (owedRow.state !== 'owed' || owedRow.wrongCount !== 2) {
    fail(`欠着 2 道错题的技能痕迹是 ${owedRow.state}/${owedRow.wrongCount}`)
  }
  if (owedRow.lastPlayedAt !== 1_700_000_000_000) fail('采纳痕迹没有读到星球的最近游玩时间')
  if (adoption.rows.some((row) => row.id !== 'add-within-10' && row.state !== 'untouched')) {
    fail('存档里没练过的技能被算成了练过')
  }
  // 掌握度到了线，痕迹就该翻成「已过线」；这是统计口径唯一的输入
  const passedAll = weekPlanAdoption(plan, {
    mastery: Object.fromEntries(plan.skills.map((s) => [s.id, 1])),
  })
  if (passedAll.passed !== plan.skills.length || passedAll.touchedPercent !== 100) {
    fail(`全部过线后采纳统计只认出 ${passedAll.passed}/${plan.skills.length} 个`)
  }
  if (weekPlanAdoption(null).total !== 0) fail('没有计划时采纳统计该是空的')

  console.log(
    `周计划：${plan.stats.days} 天 ${plan.stats.sessions} 场 ${plan.stats.skills} 个技能` +
      `（约 ${plan.stats.minutes} 分钟，预计 ${plan.stats.passing} 个过线），` +
      `首场「${plan.days[0].skills[0].name}」落到 ${plan.days[0].skills[0].entry.kind}；` +
      `采纳痕迹 ${adoption.touched}/${adoption.total} 有记录`,
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
