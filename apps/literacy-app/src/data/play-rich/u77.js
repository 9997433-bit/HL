/**
 * 富互动 play 分片 u77 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u77'

export const UNIT_RICH_PLAYS = [
  {
    char: '库', unit: 'u77', theme: 'place',
    template: 'scene-poke', interaction: 'tap',
    narration: '打开仓库，取出三件货。',
    props: { hero: '🏚️', items: ['🌱', '💧', '☀️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '应', unit: 'u77', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '这道题应该选哪个？点它。',
    props: { hero: '✅', sound: '哗哗', goal: 3 },
    templateFallback: false
  },
  {
    char: '序', unit: 'u77', theme: 'action',
    template: 'morph-story', interaction: 'sequence',
    narration: '按顺序排队，一二三走。',
    props: { hero: '🔢', stages: ['🪵', '🔢', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '辛', unit: 'u77', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '辣椒真辛苦，辣得冒汗。',
    props: { hero: '🌶️', pairs: [{ a: '🌶️', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '🌶️' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '弃', unit: 'u77', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把废纸弃进垃圾桶。',
    props: { hero: '🚮', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '闲', unit: 'u77', theme: 'action',
    template: 'color-fill', interaction: 'tap',
    narration: '空闲时光，躺着歇一歇。',
    props: { hero: '🛋️', color: 'khaki', goal: 3 },
    templateFallback: false
  },
  {
    char: '闷', unit: 'u77', theme: 'body',
    template: 'rain-catch', interaction: 'drag',
    narration: '心里闷闷的，开窗透气。',
    props: { hero: '😔', items: ['🌙', '🎈', '🧩'], tool: '😔', goal: 3 },
    templateFallback: false
  },
  {
    char: '兑', unit: 'u77', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '把代币兑换成小贴纸。',
    props: { hero: '💱', pairs: [{ a: '💱', b: '☀️' }, { a: '🎁', b: '🔔' }, { a: '☀️', b: '💱' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '灶', unit: 'u77', theme: 'food',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '灶台点火，开始做饭。',
    props: { hero: '🍳', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '灿', unit: 'u77', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '烟花灿烂，点亮夜空。',
    props: { hero: '✨', items: ['✨', '✨', '✨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '汪', unit: 'u77', theme: 'animal',
    template: 'sound-tap', interaction: 'tap',
    narration: '小狗汪汪叫，跟着学三声。',
    props: { hero: '🐕', sound: '咔咔', goal: 3 },
    templateFallback: false
  },
  {
    char: '沐', unit: 'u77', theme: 'weather',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '洗个热水澡，沐个舒服浴。',
    props: { hero: '🚿', target: '🚿', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '汰', unit: 'u77', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '淘汰坏苹果，留下好的。',
    props: { hero: '🧹', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '沃', unit: 'u77', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '沃土里浇水，种子发芽。',
    props: { hero: '🌱', parts: ['🧩', '🌱', '🌱'], goal: 3 },
    templateFallback: false
  },
  {
    char: '泛', unit: 'u77', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '小船泛在湖上，轻轻漂。',
    props: { hero: '⛵', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '沧', unit: 'u77', theme: 'weather',
    template: 'color-fill', interaction: 'tap',
    narration: '沧海无边，浪花一层层。',
    props: { hero: '🌊', color: 'red', goal: 3 },
    templateFallback: false
  },
  {
    char: '沉', unit: 'u77', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '石头沉下水底，一直往下。',
    props: { hero: '⚓', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '怀', unit: 'u77', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '抱在怀里，轻轻摇一摇。',
    props: { hero: '🫂', sound: '嗡嗡', goal: 3 },
    templateFallback: false
  },
  {
    char: '忧', unit: 'u77', theme: 'feeling',
    template: 'morph-story', interaction: 'sequence',
    narration: '赶走忧愁，换成笑脸。',
    props: { hero: '😟', stages: ['🪵', '😟', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '牢', unit: 'u77', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '绳子绑牢，不会松开。',
    props: { hero: '🔒', pairs: [{ a: '🔒', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '🔒' }], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
