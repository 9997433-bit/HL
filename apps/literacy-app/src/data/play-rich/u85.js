/**
 * 富互动 play 分片 u85 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u85'

export const UNIT_RICH_PLAYS = [
  {
    char: '依', unit: 'u85', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '小羊依着妈妈，靠一靠。',
    props: { hero: '🐑', items: ['🐑', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '迫', unit: 'u85', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '时间紧迫，赶快点三下。',
    props: { hero: '⏰', sound: '嗡嗡', goal: 3 },
    templateFallback: false
  },
  {
    char: '质', unit: 'u85', theme: 'action',
    template: 'morph-story', interaction: 'sequence',
    narration: '比比质量，哪颗宝石好。',
    props: { hero: '💎', stages: ['🪵', '💎', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '欣', unit: 'u85', theme: 'feeling',
    template: 'pair-match', interaction: 'drag',
    narration: '心里欣喜，跳起小舞蹈。',
    props: { hero: '😊', pairs: [{ a: '😊', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '😊' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '征', unit: 'u85', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '扛起旗长征，一步步走。',
    props: { hero: '🚩', items: [{ item: '🚩', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '往', unit: 'u85', theme: 'action',
    template: 'color-fill', interaction: 'tap',
    narration: '往前走，别往后看。',
    props: { hero: '➡️', color: 'pink', goal: 3 },
    templateFallback: false
  },
  {
    char: '彼', unit: 'u85', theme: 'shape',
    template: 'pair-match', interaction: 'drag',
    narration: '彼岸有花，划船过去。',
    props: { hero: '↔️', pairs: [{ a: '↔️', b: '🌙' }, { a: '🎈', b: '🧩' }, { a: '🌙', b: '↔️' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '径', unit: 'u85', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '沿着小径，走到花园。',
    props: { hero: '🚶', items: ['☀️', '🎁', '🔔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '命', unit: 'u85', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '生命之火，点亮三盏灯。',
    props: { hero: '❤️', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '受', unit: 'u85', theme: 'feeling',
    template: 'count-tap', interaction: 'tap',
    narration: '双手接受礼物，说谢谢。',
    props: { hero: '🎁', items: ['🎁', '🎁', '🎁', '🎁'], goal: 4 },
    templateFallback: false
  },
  {
    char: '贪', unit: 'u85', theme: 'body',
    template: 'tap-reveal', interaction: 'tap',
    narration: '别贪心，只拿一块糖。',
    props: { hero: '🍭', items: ['🎁', '🧩', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '念', unit: 'u85', theme: 'school',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '打开书本，念出三行字。',
    props: { hero: '📖', target: '📖', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '贫', unit: 'u85', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '口袋贫空，找找硬币。',
    props: { hero: '🪫', stages: ['📦', '🪫', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '肤', unit: 'u85', theme: 'body',
    template: 'drag-parts', interaction: 'drag',
    narration: '涂点润肤霜，保护皮肤。',
    props: { hero: '🧴', parts: ['🧩', '🌱', '🧴'], goal: 3 },
    templateFallback: false
  },
  {
    char: '肺', unit: 'u85', theme: 'body',
    template: 'trace-path', interaction: 'drag',
    narration: '深深吸气，肺部鼓起来。',
    props: { hero: '🫁', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '肢', unit: 'u85', theme: 'body',
    template: 'scene-poke', interaction: 'tap',
    narration: '活动四肢，伸伸胳膊腿。',
    props: { hero: '🦵', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '肿', unit: 'u85', theme: 'color',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '蚊子叮肿了，贴上创可贴。',
    props: { hero: '🤕', items: ['🤕', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '胀', unit: 'u85', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '气球胀大了，别吹太满。',
    props: { hero: '🎈', stages: ['🪨', '🎈', '⭐'], goal: 3 },
    templateFallback: false
  },
  {
    char: '股', unit: 'u85', theme: 'number',
    template: 'grow-tap', interaction: 'tap',
    narration: '一股清风吹来，接住它。',
    props: { hero: '💨', stages: ['🪵', '💨', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '肥', unit: 'u85', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '给花施肥，让它长胖。',
    props: { hero: '🌱', pairs: [{ a: '🌱', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '🌱' }], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
