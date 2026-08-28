/**
 * 富互动 play 分片 u31 —— 这一单元的 18 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u31'

export const UNIT_RICH_PLAYS = [
  {
    char: '加', unit: 'u31', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '再加一个进来，一共有几个。',
    props: { hero: '➕', items: ['🍎', '🍎', '🍎', '🍎'], goal: 4 },
    templateFallback: false
  },
  {
    char: '减', unit: 'u31', theme: 'number',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '拿走一个就少一个，这叫减。',
    props: { hero: '➖', items: ['🍬', '🍬', '🍬', '🍬'], goal: 4 },
    templateFallback: false
  },
  {
    char: '等', unit: 'u31', theme: 'number',
    template: 'pair-match', interaction: 'drag',
    narration: '两边一样多才叫等，配一配。',
    props: { hero: '🟰', pairs: [{ a: '🍎', b: '🍐' }, { a: '⭐', b: '⭐' }, { a: '🍬', b: '🍭' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '倍', unit: 'u31', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '两个两个地数，二的二倍是四。',
    props: { hero: '✖️', items: ['🍒', '🍒', '🍒', '🍒'], goal: 4 },
    templateFallback: false
  },
  {
    char: '量', unit: 'u31', theme: 'object',
    template: 'trace-path', interaction: 'drag',
    narration: '拿尺子从头量到尾，看有多长。',
    props: { hero: '📏', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '算', unit: 'u31', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '拨一颗算珠算一下，拨满五颗。',
    props: { hero: '🧮', items: ['🔴', '🔴', '🔴', '🔴', '🔴'], goal: 5 },
    templateFallback: false
  },
  {
    char: '题', unit: 'u31', theme: 'school',
    template: 'tap-reveal', interaction: 'tap',
    narration: '翻开本子，今天要做几道题。',
    props: { hero: '📝', items: ['1️⃣', '2️⃣', '3️⃣'], goal: 3 },
    templateFallback: false
  },
  {
    char: '位', unit: 'u31', theme: 'place',
    template: 'sort-buckets', interaction: 'drag',
    narration: '每个人找到自己的位子坐好。',
    props: { hero: '🔢', items: [{ item: '🧒', bucket: '第一排' }, { item: '👧', bucket: '第一排' }, { item: '👦', bucket: '第二排' }, { item: '🧑', bucket: '第二排' }], buckets: [{ label: '第一排', emoji: '1️⃣' }, { label: '第二排', emoji: '2️⃣' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '元', unit: 'u31', theme: 'object',
    template: 'count-tap', interaction: 'tap',
    narration: '数数钱包里一共有几元。',
    props: { hero: '💴', items: ['🪙', '🪙', '🪙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '块', unit: 'u31', theme: 'number',
    template: 'drag-parts', interaction: 'drag',
    narration: '把三块积木摞成一座小塔。',
    props: { hero: '🧱', parts: ['🟥', '🟨', '🟦'], goal: 3 },
    templateFallback: false
  },
  {
    char: '层', unit: 'u31', theme: 'shape',
    template: 'grow-tap', interaction: 'tap',
    narration: '一层一层往上叠，叠成三层。',
    props: { hero: '🏢', stages: ['🟫', '🟨', '🎂'], goal: 3 },
    templateFallback: false
  },
  {
    char: '条', unit: 'u31', theme: 'shape',
    template: 'count-tap', interaction: 'tap',
    narration: '鱼缸里游着几条鱼？数数。',
    props: { hero: '🐠', items: ['🐠', '🐠', '🐠', '🐠'], goal: 4 },
    templateFallback: false
  },
  {
    char: '张', unit: 'u31', theme: 'object',
    template: 'count-tap', interaction: 'tap',
    narration: '一张一张发纸，发给四个人。',
    props: { hero: '📄', items: ['📄', '📄', '📄', '📄'], goal: 4 },
    templateFallback: false
  },
  {
    char: '片', unit: 'u31', theme: 'shape',
    template: 'rain-catch', interaction: 'drag',
    narration: '一片一片花瓣飘下来，接住它。',
    props: { hero: '🌸', items: ['🌸', '🌸', '🌸'], tool: '🧺', goal: 3 },
    templateFallback: false
  },
  {
    char: '支', unit: 'u31', theme: 'object',
    template: 'count-tap', interaction: 'tap',
    narration: '笔筒里的笔，一支一支数过来。',
    props: { hero: '✏️', items: ['✏️', '🖊️', '🖍️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '首', unit: 'u31', theme: 'word',
    template: 'sound-tap', interaction: 'tap',
    narration: '一首儿歌唱三遍，跟着哼。',
    props: { hero: '🎵', sound: '啦啦啦', goal: 3 },
    templateFallback: false
  },
  {
    char: '组', unit: 'u31', theme: 'number',
    template: 'sort-buckets', interaction: 'drag',
    narration: '分成两组，红的一组蓝的一组。',
    props: { hero: '👥', items: [{ item: '🍎', bucket: '红组' }, { item: '🍓', bucket: '红组' }, { item: '🫐', bucket: '蓝组' }, { item: '🐳', bucket: '蓝组' }], buckets: [{ label: '红组', emoji: '🔴' }, { label: '蓝组', emoji: '🔵' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '排', unit: 'u31', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '一个挨一个，排成整齐的一排。',
    props: { hero: '🧒', parts: ['🧒', '🧒', '🧒'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
