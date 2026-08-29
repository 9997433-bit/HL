/**
 * 富互动 play 分片 u78 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u78'

export const UNIT_RICH_PLAYS = [
  {
    char: '穷', unit: 'u78', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '口袋空空，数一数还剩几。',
    props: { hero: '🌊', items: [{ item: '🌊', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '灾', unit: 'u78', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '洪水成灾，赶快搬到高处。',
    props: { hero: '🌊', stages: ['❄️', '🌊', '📦'], goal: 3 },
    templateFallback: false
  },
  {
    char: '证', unit: 'u78', theme: 'action',
    template: 'rain-catch', interaction: 'drag',
    narration: '出示证件，才能进大门。',
    props: { hero: '🪪', items: ['🌙', '🎈', '🧩'], tool: '🪪', goal: 3 },
    templateFallback: false
  },
  {
    char: '启', unit: 'u78', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '钥匙一转，开启宝箱。',
    props: { hero: '🔑', stages: ['☀️', '🔑', '🔔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '评', unit: 'u78', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '给作品评星，点满三颗。',
    props: { hero: '⭐', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '初', unit: 'u78', theme: 'time',
    template: 'grow-tap', interaction: 'tap',
    narration: '一开始，从最初那步走。',
    props: { hero: '🌱', stages: ['🎈', '🌱', '🌱'], goal: 3 },
    templateFallback: false
  },
  {
    char: '社', unit: 'u78', theme: 'place',
    template: 'grow-tap', interaction: 'tap',
    narration: '社区花园里，点亮花草。',
    props: { hero: '🏘️', stages: ['🎁', '🏘️', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '诉', unit: 'u78', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '把心里话诉说给朋友听。',
    props: { hero: '🗣️', target: '🗣️', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '罕', unit: 'u78', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '这颗宝石罕见，找出来。',
    props: { hero: '💎', stages: ['📦', '💎', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '译', unit: 'u78', theme: 'number',
    template: 'pair-match', interaction: 'drag',
    narration: '把外语译成中文，配对。',
    props: { hero: '🌐', pairs: [{ a: '🌐', b: '🧩' }, { a: '🌱', b: '🔥' }, { a: '🧩', b: '🌐' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '君', unit: 'u78', theme: 'family',
    template: 'trace-path', interaction: 'drag',
    narration: '小国君戴上王冠，坐上椅。',
    props: { hero: '👑', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '即', unit: 'u78', theme: 'animal',
    template: 'scene-poke', interaction: 'tap',
    narration: '立即行动，马上点三下。',
    props: { hero: '⏱️', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '屁', unit: 'u78', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '憋不住了，放个小屁。',
    props: { hero: '💨', items: ['💨', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '尿', unit: 'u78', theme: 'body',
    template: 'sound-tap', interaction: 'tap',
    narration: '想尿尿了，找到厕所门。',
    props: { hero: '🚽', sound: '呼呼', goal: 3 },
    templateFallback: false
  },
  {
    char: '迟', unit: 'u78', theme: 'time',
    template: 'morph-story', interaction: 'sequence',
    narration: '钟表走慢了，迟到了。',
    props: { hero: '🕗', stages: ['🪵', '🕗', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '局', unit: 'u78', theme: 'number',
    template: 'pair-match', interaction: 'drag',
    narration: '下完这一局棋，收好棋子。',
    props: { hero: '♟️', pairs: [{ a: '♟️', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '♟️' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '际', unit: 'u78', theme: 'shape',
    template: 'sort-buckets', interaction: 'drag',
    narration: '站在天际边，望向远方。',
    props: { hero: '🌅', items: [{ item: '🌅', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '阿', unit: 'u78', theme: 'school',
    template: 'color-fill', interaction: 'tap',
    narration: '叫一声阿姨，挥手问好。',
    props: { hero: '👵', color: 'blue', goal: 3 },
    templateFallback: false
  },
  {
    char: '陈', unit: 'u78', theme: 'number',
    template: 'rain-catch', interaction: 'drag',
    narration: '旧东西陈年了，擦一擦灰。',
    props: { hero: '🪑', items: ['🌙', '🎈', '🧩'], tool: '🪑', goal: 3 },
    templateFallback: false
  },
  {
    char: '阻', unit: 'u78', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '路障挡住了，把它挪开。',
    props: { hero: '🚧', items: ['☀️', '🎁', '🔔'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
