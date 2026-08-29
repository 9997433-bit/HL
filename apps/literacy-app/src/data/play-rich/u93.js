/**
 * 富互动 play 分片 u93 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u93'

export const UNIT_RICH_PLAYS = [
  {
    char: '趴', unit: 'u93', theme: 'body',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '趴在地毯上，往前爬。',
    props: { hero: '🐕', items: ['🐕', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '胃', unit: 'u93', theme: 'body',
    template: 'drag-parts', interaction: 'drag',
    narration: '胃里装食物，把饭吃完。',
    props: { hero: '🍚', parts: ['🪨', '🔥', '🍚'], goal: 3 },
    templateFallback: false
  },
  {
    char: '蚂', unit: 'u93', theme: 'animal',
    template: 'morph-story', interaction: 'sequence',
    narration: '小蚂蚁排队，跟着走。',
    props: { hero: '🐜', stages: ['🪵', '🐜', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '品', unit: 'u93', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '品尝三样点心，说说味道。',
    props: { hero: '🎁', pairs: [{ a: '🎁', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '🎁' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '咽', unit: 'u93', theme: 'weather',
    template: 'sort-buckets', interaction: 'drag',
    narration: '慢慢咽下去，别噎着。',
    props: { hero: '🗣️', items: [{ item: '🗣️', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '骂', unit: 'u93', theme: 'action',
    template: 'color-fill', interaction: 'tap',
    narration: '别骂人，换成温柔话。',
    props: { hero: '😠', color: 'blue', goal: 3 },
    templateFallback: false
  },
  {
    char: '哗', unit: 'u93', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '别喧哗，把声音按小。',
    props: { hero: '🤫', sound: '叮叮', goal: 3 },
    templateFallback: false
  },
  {
    char: '咱', unit: 'u93', theme: 'place',
    template: 'tap-reveal', interaction: 'tap',
    narration: '咱们一起走，手拉手。',
    props: { hero: '👫', items: ['☀️', '🎁', '🔔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '响', unit: 'u93', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '铃声响起，按掉闹钟。',
    props: { hero: '🔔', sound: '咔咔', goal: 3 },
    templateFallback: false
  },
  {
    char: '哈', unit: 'u93', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '哈哈大笑，笑出声来。',
    props: { hero: '😄', sound: '嗡嗡', goal: 3 },
    templateFallback: false
  },
  {
    char: '咬', unit: 'u93', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '咬一口苹果，嘎嘣脆。',
    props: { hero: '🦷', items: ['🎁', '🧩', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '咳', unit: 'u93', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '咳了一声，喝口水润润。',
    props: { hero: '🤧', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '咪', unit: 'u93', theme: 'animal',
    template: 'sound-tap', interaction: 'tap',
    narration: '猫咪咪咪叫，摸摸它。',
    props: { hero: '🐱', sound: '叮叮', goal: 3 },
    templateFallback: false
  },
  {
    char: '哪', unit: 'u93', theme: 'number',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪条路回家？选对的。',
    props: { hero: '❓', target: '❓', decoys: ['🧩', '🌱', '🔥'], goal: 1 },
    templateFallback: false
  },
  {
    char: '炭', unit: 'u93', theme: 'nature',
    template: 'trace-path', interaction: 'drag',
    narration: '往火里加木炭，烧得旺。',
    props: { hero: '🍠', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '贴', unit: 'u93', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '把邮票贴上信封。',
    props: { hero: '📮', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '钙', unit: 'u93', theme: 'number',
    template: 'sort-buckets', interaction: 'drag',
    narration: '喝牛奶补钙，骨头硬。',
    props: { hero: '🥛', items: [{ item: '🥛', bucket: '左' }, { item: '☀️', bucket: '左' }, { item: '🌱', bucket: '右' }, { item: '💧', bucket: '右' }], buckets: [{ label: '左', emoji: '🌱' }, { label: '右', emoji: '💧' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '钝', unit: 'u93', theme: 'time',
    template: 'sound-tap', interaction: 'tap',
    narration: '刀钝了，磨一磨锋利。',
    props: { hero: '🔪', sound: '哗哗', goal: 3 },
    templateFallback: false
  },
  {
    char: '钢', unit: 'u93', theme: 'school',
    template: 'morph-story', interaction: 'sequence',
    narration: '钢笔写出字，写三笔。',
    props: { hero: '🖋️', stages: ['🪵', '🖋️', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '钩', unit: 'u93', theme: 'animal',
    template: 'pair-match', interaction: 'drag',
    narration: '鱼钩甩出去，等鱼上钩。',
    props: { hero: '🪝', pairs: [{ a: '🪝', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '🪝' }], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
