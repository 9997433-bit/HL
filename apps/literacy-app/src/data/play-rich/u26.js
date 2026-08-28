/**
 * 富互动 play 分片 u26 —— 这一单元的 18 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u26'

export const UNIT_RICH_PLAYS = [
  {
    char: '汤', unit: 'u26', theme: 'food',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '一勺一勺，把热汤喝干净。',
    props: { hero: '🍲', items: ['🥄', '🥄', '🥄'], goal: 3 },
    templateFallback: false
  },
  {
    char: '粥', unit: 'u26', theme: 'food',
    template: 'grow-tap', interaction: 'tap',
    narration: '米加水慢慢熬，熬成一碗粥。',
    props: { hero: '🥣', stages: ['🍚', '💧', '🥣'], goal: 3 },
    templateFallback: false
  },
  {
    char: '包', unit: 'u26', theme: 'food',
    template: 'count-tap', interaction: 'tap',
    narration: '蒸笼里的包子，数数有几个。',
    props: { hero: '🥟', items: ['🥟', '🥟', '🥟', '🥟'], goal: 4 },
    templateFallback: false
  },
  {
    char: '饼', unit: 'u26', theme: 'food',
    template: 'color-fill', interaction: 'tap',
    narration: '把小饼烙成金黄的颜色。',
    props: { hero: '🥞', color: 'gold', goal: 3 },
    templateFallback: false
  },
  {
    char: '油', unit: 'u26', theme: 'food',
    template: 'trace-path', interaction: 'drag',
    narration: '油从瓶口慢慢倒进锅里。',
    props: { hero: '🫗', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '盐', unit: 'u26', theme: 'food',
    template: 'count-tap', interaction: 'tap',
    narration: '撒一点盐，三下就够咸了。',
    props: { hero: '🧂', items: ['🧂', '🧂', '🧂'], goal: 3 },
    templateFallback: false
  },
  {
    char: '酸', unit: 'u26', theme: 'food',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '咬一口酸得眯眼，是哪一样。',
    props: { hero: '🍋', target: '🍋', decoys: ['🍬', '🍌', '🍞'], goal: 1 },
    templateFallback: false
  },
  {
    char: '辣', unit: 'u26', theme: 'feeling',
    template: 'grow-tap', interaction: 'tap',
    narration: '吃一口辣椒，脸越来越红。',
    props: { hero: '🌶️', stages: ['🙂', '😅', '🥵'], goal: 3 },
    templateFallback: false
  },
  {
    char: '咸', unit: 'u26', theme: 'food',
    template: 'sort-buckets', interaction: 'drag',
    narration: '咸的装一盘，甜的装一盘。',
    props: { hero: '🧂', items: [{ item: '🥨', bucket: '咸' }, { item: '🍟', bucket: '咸' }, { item: '🍰', bucket: '甜' }, { item: '🍭', bucket: '甜' }], buckets: [{ label: '咸', emoji: '🧂' }, { label: '甜', emoji: '🍬' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '熟', unit: 'u26', theme: 'food',
    template: 'morph-story', interaction: 'sequence',
    narration: '青果子晒着晒着，就熟透了。',
    props: { hero: '🍠', stages: ['🟢', '🟠', '熟'], goal: 3 },
    templateFallback: false
  },
  {
    char: '煮', unit: 'u26', theme: 'food',
    template: 'grow-tap', interaction: 'tap',
    narration: '水咕嘟咕嘟，把鸡蛋煮熟。',
    props: { hero: '🍳', stages: ['💧', '♨️', '🥚'], goal: 3 },
    templateFallback: false
  },
  {
    char: '炒', unit: 'u26', theme: 'food',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '拿起锅铲，来回翻炒几下。',
    props: { hero: '🍳', dir: 'right', goal: 4 },
    templateFallback: false
  },
  {
    char: '烧', unit: 'u26', theme: 'food',
    template: 'grow-tap', interaction: 'tap',
    narration: '灶下添柴，火越烧越旺。',
    props: { hero: '🔥', stages: ['🪵', '🔥', '🍲'], goal: 3 },
    templateFallback: false
  },
  {
    char: '味', unit: 'u26', theme: 'body',
    template: 'pair-match', interaction: 'drag',
    narration: '尝一尝，把味道和东西配好。',
    props: { hero: '👅', pairs: [{ a: '🍋', b: '😖' }, { a: '🍬', b: '😋' }, { a: '🌶️', b: '🥵' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '糕', unit: 'u26', theme: 'food',
    template: 'drag-parts', interaction: 'drag',
    narration: '一层一层叠起来，做个小蛋糕。',
    props: { hero: '🍰', parts: ['🟫', '🟨', '🍓'], goal: 3 },
    templateFallback: false
  },
  {
    char: '蜜', unit: 'u26', theme: 'food',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '小熊舔蜂蜜，一口一口舔光。',
    props: { hero: '🍯', items: ['🍯', '🍯', '🍯'], goal: 3 },
    templateFallback: false
  },
  {
    char: '饱', unit: 'u26', theme: 'feeling',
    template: 'grow-tap', interaction: 'tap',
    narration: '一口一口吃下去，肚子饱了。',
    props: { hero: '😋', stages: ['🍽️', '🍚', '😌'], goal: 3 },
    templateFallback: false
  },
  {
    char: '餐', unit: 'u26', theme: 'food',
    template: 'scene-poke', interaction: 'tap',
    narration: '摆好一餐饭，桌上都有什么。',
    props: { hero: '🍽️', items: ['🍚', '🥢', '🥣'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
