/**
 * 富互动 play 分片 u94 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u94'

export const UNIT_RICH_PLAYS = [
  {
    char: '钮', unit: 'u94', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '按一下电钮，门开了。',
    props: { hero: '🔘', items: [{ item: '🔘', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '卸', unit: 'u94', theme: 'action',
    template: 'color-fill', interaction: 'tap',
    narration: '把货卸下车，搬进仓。',
    props: { hero: '📦', color: 'yellow', goal: 3 },
    templateFallback: false
  },
  {
    char: '氢', unit: 'u94', theme: 'number',
    template: 'rain-catch', interaction: 'drag',
    narration: '氢气球飞上天，抓住线。',
    props: { hero: '🎈', items: ['🌙', '🎈', '🧩'], tool: '🎈', goal: 3 },
    templateFallback: false
  },
  {
    char: '怎', unit: 'u94', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '怎么办？选一个办法。',
    props: { hero: '❓', items: ['☀️', '🎁', '🔔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '适', unit: 'u94', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '鞋子正合适，走两步。',
    props: { hero: '👟', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '竿', unit: 'u94', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '竹竿够高，够到苹果。',
    props: { hero: '🎣', stages: ['🎈', '🎣', '🌱'], goal: 3 },
    templateFallback: false
  },
  {
    char: '俩', unit: 'u94', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '我俩一组，击个掌。',
    props: { hero: '👬', items: ['👬', '👬', '👬', '👬'], goal: 4 },
    templateFallback: false
  },
  {
    char: '保', unit: 'u94', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '盾牌保护你，挡开石头。',
    props: { hero: '🛡️', target: '🛡️', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '促', unit: 'u94', theme: 'number',
    template: 'grow-tap', interaction: 'tap',
    narration: '催促一下，让他快点。',
    props: { hero: '⏩', stages: ['📦', '⏩', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '俐', unit: 'u94', theme: 'body',
    template: 'drag-parts', interaction: 'drag',
    narration: '口齿伶俐，说清三句话。',
    props: { hero: '🐒', parts: ['🧩', '🌱', '🐒'], goal: 3 },
    templateFallback: false
  },
  {
    char: '俗', unit: 'u94', theme: 'weather',
    template: 'trace-path', interaction: 'drag',
    narration: '过年风俗，贴上春联。',
    props: { hero: '🎎', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '皇', unit: 'u94', theme: 'family',
    template: 'scene-poke', interaction: 'tap',
    narration: '皇帝戴皇冠，坐上龙椅。',
    props: { hero: '👑', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '侯', unit: 'u94', theme: 'number',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '王侯进府，走过红毯。',
    props: { hero: '🏯', items: ['🏯', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '俊', unit: 'u94', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '骏马俊俏，梳理鬃毛。',
    props: { hero: '🐎', sound: '嗡嗡', goal: 3 },
    templateFallback: false
  },
  {
    char: '盾', unit: 'u94', theme: 'place',
    template: 'morph-story', interaction: 'sequence',
    narration: '举起盾牌，挡住攻击。',
    props: { hero: '🛡️', stages: ['🪵', '🛡️', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '须', unit: 'u94', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '必须先洗手，再吃饭。',
    props: { hero: '❗', pairs: [{ a: '❗', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '❗' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '叙', unit: 'u94', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '叙述故事，翻开三页。',
    props: { hero: '🗣️', items: [{ item: '🗣️', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '逃', unit: 'u94', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '小老鼠逃走，钻进洞。',
    props: { hero: '🐭', stages: ['❄️', '🐭', '📦'], goal: 3 },
    templateFallback: false
  },
  {
    char: '食', unit: 'u94', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '食物摆上桌，开动吧。',
    props: { hero: '🍚', items: ['🍚', '🌙', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '胜', unit: 'u94', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '赢得胜利，举起奖杯。',
    props: { hero: '🏆', items: ['☀️', '🎁', '🔔'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
