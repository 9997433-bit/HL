/**
 * ROUND16_H4 「学演示」注册表 —— 每个技能点一段「实物 → 图形 → 算式」。
 *
 * 这份表回答的是「开练之前，这个知识点长什么样」。三段是硬契约：
 *
 *   object   实物段：孩子在生活里见过的东西，看得见、数得清；
 *   visual   图形段：把实物换成同构的点/框，数量关系还在，具体的物没了；
 *   equation 算式段：把图形关系压成一行符号。
 *
 * narration 必须正好三句，一段一句，跳过时也要能单独读懂。
 * 播放、跳过、重播、reduced-motion 静态三态全在 components/LearnDemo.vue 里，
 * 新增概念只在这里登记数据，不要再造第二套计时器。
 *
 * 技能点 id 取自 data/curriculum.js；覆盖清单见
 * .agent_workspace/evidence/r16/learn-demo-registry.md。
 */

/** 探针可执行标记（注释里的 ROUND16_H4 不算数）。 */
export const ROUND16_H4 = 'learn-demo-registry'

/** 图形段的框型：不给就是裸点组。 */
export const VISUAL_FRAMES = {
  ten: '十格框',
  fraction: '整体等分',
  mirror: '对称轴',
}

const RAW_DEMOS = [
  /* ───────────────────────────── 数与量启蒙 ───────────────────────────── */
  {
    id: 'count-to-5',
    skillId: 'count-to-5',
    module: 'number-sense',
    title: '数到最后那个数',
    subtitle: '一个一个数，最后念到的数就是总数',
    object: { emoji: '🐤', count: 4, label: '池塘里 4 只小鸭' },
    visual: { groups: [4], label: '4 个圆点' },
    equation: '4',
    narration: [
      '池塘里游来 4 只小鸭，我们一只一只数。',
      '一只小鸭换一个圆点，只剩下「有几个」。',
      '数到最后念的是 4，就写成数字 4。',
    ],
  },
  {
    id: 'counting',
    skillId: 'count-to-10',
    module: 'number-sense',
    title: '点数变数字',
    subtitle: '一个一个数，把实物抽象成数量',
    object: { emoji: '🍎', count: 5, label: '5 个苹果' },
    visual: { groups: [5], label: '5 个圆点' },
    equation: '5',
    narration: ['先看见 5 个苹果。', '每个苹果对应一个圆点。', '5 个圆点可以写成数字 5。'],
  },
  {
    id: 'teen-ten-frame',
    skillId: 'count-to-20',
    module: 'number-sense',
    title: '十几就是十和几',
    subtitle: '先装满一个十，剩下的单独放',
    object: {
      emoji: '🍬',
      count: 13,
      label: '13 颗糖：装满一盒，外加 3 颗',
      tiles: [
        { count: 10, caption: '装满一盒' },
        { count: 3, caption: '散着 3 颗' },
      ],
    },
    visual: { groups: [10, 3], frame: 'ten', groupLabels: ['10', '3'], label: '一框满十，另放 3 个' },
    equation: '10 + 3 = 13',
    narration: [
      '13 颗糖先装盒，一盒正好十颗。',
      '一个格子框正好摆满十个点，旁边另放 3 个。',
      '十和三合起来读作十三：10 + 3 = 13。',
    ],
  },
  {
    id: 'number-order',
    skillId: 'number-order',
    module: 'number-sense',
    title: '相邻数是一级台阶',
    subtitle: '前一个少 1，后一个多 1',
    object: {
      emoji: '🧱',
      count: 18,
      label: '三摞积木：5 块、6 块、7 块',
      tiles: [
        { count: 5, caption: '5 块' },
        { count: 6, caption: '6 块' },
        { count: 7, caption: '7 块' },
      ],
    },
    visual: {
      groups: [5, 6, 7],
      groupLabels: ['5', '6', '7'],
      highlightGroup: 1,
      label: '一列比一列多一个点',
    },
    equation: '5 < 6 < 7',
    narration: [
      '三摞积木，一摞比一摞高一块。',
      '排成三列点，右边永远比左边多一个。',
      '所以 6 的前一个是 5、后一个是 7：5 < 6 < 7。',
    ],
  },
  {
    id: 'comparison',
    skillId: 'compare-to-10',
    module: 'number-sense',
    title: '一一对应比大小',
    subtitle: '配对后看哪边还有剩余',
    object: { emoji: '🍪', groups: [5, 3], count: 8, label: '5 块和 3 块饼干' },
    visual: { groups: [5, 3], label: '上下配对，5 这一边多 2 个' },
    equation: '5 > 3',
    narration: ['左边 5 块，右边 3 块。', '一一配对后，左边还多 2 块。', '所以 5 大于 3，写作 5 > 3。'],
  },
  {
    id: 'compare-teen',
    skillId: 'compare-to-20',
    module: 'number-sense',
    title: '十几比大小先看十',
    subtitle: '十位一样，就比个位',
    object: {
      emoji: '🐚',
      count: 27,
      label: '12 个和 15 个贝壳',
      tiles: [
        { count: 12, caption: '我捡了 12 个' },
        { count: 15, caption: '他捡了 15 个' },
      ],
    },
    visual: {
      groups: [12, 15],
      frame: 'ten',
      groupLabels: ['12 个', '15 个'],
      label: '每行 5 个摆齐，右边多出 3 个',
    },
    equation: '12 < 15',
    narration: [
      '一边 12 个贝壳，一边 15 个，堆着看不出谁多。',
      '每行 5 个摆齐：前两行都正好是十，第三行一边 2 个、一边 5 个。',
      '十位一样就比个位：12 小于 15，写作 12 < 15。',
    ],
  },
  {
    id: 'compose-ten',
    skillId: 'compose-ten',
    module: 'number-sense',
    title: '10 的分与合',
    subtitle: '同一个整体可以分成两部分',
    object: { emoji: '🔵', groups: [6, 4], count: 10, label: '10 颗弹珠分两舱' },
    visual: { groups: [6, 4], label: '十格框里 6 格和 4 格' },
    equation: '6 + 4 = 10',
    narration: ['一共有 10 颗弹珠。', '把它们分成 6 颗和 4 颗。', '6 和 4 合成 10：6 + 4 = 10。'],
  },

  /* ─────────────────────────────── 加减乘除 ─────────────────────────────── */
  {
    id: 'addition',
    skillId: 'add-within-10',
    module: 'arithmetic',
    title: '合起来是加法',
    subtitle: '两群实物合成一个整体',
    object: { emoji: '🚀', groups: [3, 2], count: 5, label: '3 艘和 2 艘飞船' },
    visual: { groups: [3, 2], label: '两组圆点合在一起' },
    equation: '3 + 2 = 5',
    narration: ['先有 3 艘飞船，又来了 2 艘。', '画成 3 个点和 2 个点。', '合起来用加法：3 + 2 = 5。'],
  },
  {
    id: 'subtraction',
    skillId: 'sub-within-10',
    module: 'arithmetic',
    title: '拿走就是减法',
    subtitle: '从整体里去掉一部分',
    object: { emoji: '⭐', count: 6, removed: 2, label: '6 颗星拿走 2 颗' },
    visual: { groups: [4, 2], crossedGroup: 1, label: '划掉最后 2 个圆点' },
    equation: '6 − 2 = 4',
    narration: ['这里原来有 6 颗星。', '拿走的 2 颗用斜线划掉。', '还剩 4 颗：6 − 2 = 4。'],
  },
  {
    id: 'make-ten-add',
    skillId: 'add-carry-20',
    module: 'arithmetic',
    title: '凑十法：先把十装满',
    subtitle: '借几个凑满十，再加剩下的',
    object: {
      emoji: '🧃',
      count: 14,
      label: '9 盒果汁又来 5 盒',
      tiles: [
        { count: 9, caption: '原有 9 盒' },
        { count: 5, caption: '又来 5 盒' },
      ],
    },
    visual: {
      groups: [10, 4],
      frame: 'ten',
      groupLabels: ['9 借 1 凑满十', '5 借走 1 剩 4'],
      label: '左边格子先填满十，右边还剩 4 个',
    },
    equation: '9 + 5 = 14',
    narration: [
      '左边 9 盒，右边 5 盒，9 离十只差 1 盒。',
      '从右边借 1 盒把左边填满十格，右边还剩 4 盒。',
      '满十再加 4：9 + 5 = 14。',
    ],
  },
  {
    id: 'break-ten-sub',
    skillId: 'sub-borrow-20',
    module: 'arithmetic',
    title: '破十法：从十里拿',
    subtitle: '个位不够减，就拆开那个十',
    object: { emoji: '🍞', count: 13, removed: 5, label: '13 个面包吃掉 5 个' },
    visual: {
      groups: [5, 5, 3],
      crossedGroup: 0,
      groupLabels: ['从十里划掉 5', '十里剩 5', '个位的 3'],
      label: '把 13 拆成 10 和 3，只从 10 里拿',
    },
    equation: '13 − 5 = 8',
    narration: [
      '一共 13 个面包要拿走 5 个，可个位只有 3，不够减。',
      '把 13 拆成 10 和 3，先从 10 里划掉 5，十里还剩 5。',
      '剩下的 5 再加上个位的 3：13 − 5 = 8。',
    ],
  },
  {
    id: 'add-tens-ones',
    skillId: 'add-within-100',
    module: 'arithmetic',
    title: '两位数相加：捆和捆加',
    subtitle: '整十跟整十加，个位跟个位加',
    object: {
      emoji: '🧱',
      count: 55,
      label: '3 捆小棒，再加 2 捆零 5 根',
      tiles: [
        { count: 3, caption: '3 捆＝30' },
        { count: 2, caption: '2 捆＝20' },
        { emoji: '🔸', count: 5, caption: '5 根' },
      ],
    },
    visual: {
      groups: [5, 5],
      groupLabels: ['3 个十 + 2 个十', '再添 5 个一'],
      label: '先合整十，再补个位',
    },
    equation: '30 + 25 = 55',
    narration: [
      '一捆小棒是十根：这边 3 捆，那边 2 捆零 5 根。',
      '先把捆和捆合起来，一共 5 捆，也就是 5 个十。',
      '5 个十再添 5 个一：30 + 25 = 55。',
    ],
  },
  {
    id: 'sub-tens-ones',
    skillId: 'sub-within-100',
    module: 'arithmetic',
    title: '两位数相减：先减整十',
    subtitle: '减的是整十，散着的一根都不用动',
    object: {
      emoji: '🧱',
      count: 46,
      label: '46 根小棒：4 捆零 6 根',
      tiles: [
        { count: 4, caption: '4 捆＝40' },
        { emoji: '🔸', count: 6, caption: '6 根' },
      ],
    },
    visual: {
      groups: [2, 2, 6],
      crossedGroup: 0,
      groupLabels: ['拿走 2 捆', '还剩 2 捆', '个位 6 不动'],
      label: '只从捆里拿，散着的一根没少',
    },
    equation: '46 − 20 = 26',
    narration: [
      '46 根小棒摆成 4 捆零 6 根。',
      '减 20 就是拿走 2 捆，散着的 6 根一根没动。',
      '还剩 2 捆零 6 根：46 − 20 = 26。',
    ],
  },
  {
    id: 'multiplication',
    skillId: 'mul-table',
    module: 'arithmetic',
    title: '几个几是乘法',
    subtitle: '相同数量的组可以简写',
    object: { emoji: '🌼', groups: [3, 3], count: 6, label: '2 盆花，每盆 3 朵' },
    visual: { groups: [3, 3], label: '2 组，每组 3 个圆点' },
    equation: '2 × 3 = 6',
    narration: ['有 2 盆花，每盆都是 3 朵。', '画成同样多的 2 组圆点。', '2 个 3 可以写成 2 × 3 = 6。'],
  },
  {
    id: 'division',
    skillId: 'div-basic',
    module: 'arithmetic',
    title: '平均分是除法',
    subtitle: '把整体分成同样多的几份',
    object: { emoji: '🍓', groups: [2, 2, 2], count: 6, label: '6 颗草莓平均放 3 盘' },
    visual: { groups: [2, 2, 2], label: '3 个圈，每圈 2 个圆点' },
    equation: '6 ÷ 3 = 2',
    narration: ['把 6 颗草莓平均放进 3 个盘子。', '每个圈里都画 2 个点。', '每盘 2 颗：6 ÷ 3 = 2。'],
  },

  /* ─────────────────────────────── 几何空间 ─────────────────────────────── */
  {
    id: 'fraction',
    skillId: 'shape-2d',
    module: 'geometry',
    title: '一半是二分之一',
    subtitle: '把一个整体平均分',
    object: { emoji: '🍕', count: 1, label: '一张完整的披萨' },
    visual: { groups: [1, 1], frame: 'fraction', label: '平均分成 2 份，取其中 1 份' },
    equation: '1 ÷ 2 = ½',
    narration: ['先看一张完整的披萨。', '把整体平均切成相同的 2 份。', '其中 1 份叫二分之一，写作 ½。'],
  },
  {
    id: 'symmetry-fold',
    skillId: 'symmetry',
    module: 'geometry',
    title: '对折重合是对称',
    subtitle: '沿着一条线折过去，两边刚好盖住',
    object: { emoji: '🦋', count: 1, label: '一只蝴蝶，沿身体中线对折' },
    visual: {
      groups: [3, 3],
      frame: 'mirror',
      groupLabels: ['左翼 3 个点', '右翼 3 个点'],
      label: '对称轴两边点数一样多',
    },
    equation: '3 = 3',
    narration: [
      '蝴蝶沿着身体中间那条线对折。',
      '左右两半各画 3 个点，折过去正好重合。',
      '两边一样多，这条线就是对称轴：3 = 3。',
    ],
  },

  /* ─────────────────────────────── 逻辑推理 ─────────────────────────────── */
  {
    id: 'pattern-abab',
    skillId: 'pattern-abab',
    module: 'logic',
    title: '循环规律：找那一小节',
    subtitle: '重复的那一小节就是规律',
    object: {
      emoji: '🔴',
      count: 6,
      label: '红蓝红蓝……串成的珠子',
      sequence: ['🔴', '🔵', '🔴', '🔵', '🔴', '🔵'],
    },
    visual: {
      groups: [2, 2, 2],
      groupLabels: ['第 1 节', '第 2 节', '第 3 节'],
      label: '每 2 颗一节，反复 3 次',
    },
    equation: '2 × 3 = 6',
    narration: [
      '串珠是红、蓝、红、蓝这样排下去的。',
      '把重复的那一小节圈出来：每 2 颗算一节。',
      '3 节一共 6 颗：2 × 3 = 6，下一颗一定是红色。',
    ],
  },
  {
    id: 'pattern-number',
    skillId: 'pattern-number',
    module: 'logic',
    title: '数列规律：看差多少',
    subtitle: '相邻两项差一样，就按这个差往下写',
    object: {
      emoji: '🪙',
      count: 12,
      label: '三堆金币：2 枚、4 枚、6 枚',
      tiles: [
        { count: 2, caption: '2 枚' },
        { count: 4, caption: '4 枚' },
        { count: 6, caption: '6 枚' },
      ],
    },
    visual: {
      groups: [2, 4, 6],
      groupLabels: ['+2', '+2', '再 +2 ?'],
      highlightGroup: 2,
      label: '每堆都比前一堆多 2 个点',
    },
    equation: '6 + 2 = 8',
    narration: [
      '三堆金币分别是 2 枚、4 枚、6 枚。',
      '画成点就看清了：每堆都比前一堆多 2 个。',
      '差都是 2，下一项就是 6 + 2 = 8。',
    ],
  },

  /* ─────────────────────────────── 生活应用题 ─────────────────────────────── */
  {
    id: 'wp-combine',
    skillId: 'wp-combine',
    module: 'word-problems',
    title: '合并问题：两部分找总数',
    subtitle: '问「一共」，就把两部分并起来',
    object: {
      emoji: '🐟',
      count: 7,
      label: '鱼缸里 4 条，又放进 3 条',
      tiles: [
        { count: 4, caption: '原来 4 条' },
        { count: 3, caption: '又放 3 条' },
      ],
    },
    visual: { groups: [4, 3], groupLabels: ['部分', '部分'], label: '两部分并成一个整体' },
    equation: '4 + 3 = 7',
    narration: [
      '题目说：鱼缸里有 4 条鱼，又放进 3 条。',
      '两部分各画一组点，问的是把它们并起来有多少。',
      '求总数用加法：4 + 3 = 7 条。',
    ],
  },
  {
    id: 'wp-remain',
    skillId: 'wp-remain',
    module: 'word-problems',
    title: '剩余问题：整体去掉一部分',
    subtitle: '问「还剩」，就从总数里拿走',
    object: { emoji: '🎈', count: 8, removed: 3, label: '8 个气球飞走 3 个' },
    visual: { groups: [5, 3], crossedGroup: 1, groupLabels: ['还剩', '飞走'], label: '从整体里划掉飞走的那部分' },
    equation: '8 − 3 = 5',
    narration: [
      '题目说：手里有 8 个气球，飞走了 3 个。',
      '整体画成 8 个点，飞走的 3 个划掉。',
      '问「还剩」用减法：8 − 3 = 5 个。',
    ],
  },
]

/**
 * 对外的演示条目。
 *
 * `skill` 是 `skillId` 的别名：图谱、错题本、掌握度一路都叫 skill，
 * 演示这边多一个 skillId 只是为了在注册表里一眼看出这行挂在哪个技能点上。
 */
export const LEARN_DEMOS = RAW_DEMOS.map((demo) => ({ ...demo, skill: demo.skillId }))

export const LEARN_DEMO_MAP = Object.fromEntries(LEARN_DEMOS.map((demo) => [demo.id, demo]))

const BY_SKILL = Object.fromEntries(LEARN_DEMOS.map((demo) => [demo.skill, demo]))

export const learnDemoById = (id) => LEARN_DEMO_MAP[id] ?? null

export const learnDemoOfSkill = (skill) => BY_SKILL[skill] ?? null

/** 三段固定不变：演示壳按它渲染进度条，验收按它数覆盖。 */
export const LEARN_DEMO_STAGES = [
  { id: 'object', label: '实物', icon: '🧺', tag: '①' },
  { id: 'visual', label: '图形', icon: '●', tag: '②' },
  { id: 'equation', label: '算式', icon: '=', tag: '③' },
]

/**
 * 实物段的统一渲染形态。
 *
 * 三种写法（tiles / sequence / groups+count）在这里收敛成同一个结构，
 * 演示壳只认 `{ items, caption, crossedFrom }`，不必知道数据是怎么写的。
 */
export function objectTiles(object = {}) {
  const fallback = object.emoji ?? '⬤'
  if (Array.isArray(object.tiles)) {
    return object.tiles.map((tile) => ({
      items: Array.from({ length: tile.count ?? 0 }, () => tile.emoji ?? fallback),
      caption: tile.caption ?? '',
      crossedFrom: tile.crossedFrom ?? Number.POSITIVE_INFINITY,
    }))
  }
  if (Array.isArray(object.sequence)) {
    return [{ items: [...object.sequence], caption: '', crossedFrom: Number.POSITIVE_INFINITY }]
  }
  const groups = object.groups ?? [object.count ?? 1]
  const total = groups.reduce((sum, n) => sum + n, 0)
  const keep = total - (object.removed ?? 0)
  let passed = 0
  return groups.map((count) => {
    const tile = {
      items: Array.from({ length: count }, () => fallback),
      caption: '',
      crossedFrom: Math.max(0, keep - passed),
    }
    passed += count
    return tile
  })
}

export default LEARN_DEMOS
