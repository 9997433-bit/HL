/**
 * 富互动 play 分片 u86 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u86'

export const UNIT_RICH_PLAYS = [
  {
    char: '炕', unit: 'u86', theme: 'shape',
    template: 'drag-parts', interaction: 'drag',
    narration: '北方火炕暖暖的，躺一躺。',
    props: { hero: '🛏️', parts: ['🔥', '☀️', '🛏️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '昏', unit: 'u86', theme: 'color',
    template: 'color-fill', interaction: 'tap',
    narration: '黄昏来了，天慢慢暗。',
    props: { hero: '🌆', color: 'blue', goal: 3 },
    templateFallback: false
  },
  {
    char: '狐', unit: 'u86', theme: 'animal',
    template: 'rain-catch', interaction: 'drag',
    narration: '狐狸尾巴尖，找出它来。',
    props: { hero: '🦊', items: ['🌙', '🎈', '🧩'], tool: '🦊', goal: 3 },
    templateFallback: false
  },
  {
    char: '饰', unit: 'u86', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '给蛋糕装饰上奶油花。',
    props: { hero: '🎀', parts: ['☀️', '🎁', '🎀'], goal: 3 },
    templateFallback: false
  },
  {
    char: '饲', unit: 'u86', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '给小鸡饲料，喂饱它们。',
    props: { hero: '🐔', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '享', unit: 'u86', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '切开蛋糕，一起享受。',
    props: { hero: '🍰', items: ['🍰', '🍰', '🍰', '🍰', '🍰'], goal: 5 },
    templateFallback: false
  },
  {
    char: '庞', unit: 'u86', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '庞然大物来了，好巨大。',
    props: { hero: '🐘', stages: ['🎁', '🐘', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '庙', unit: 'u86', theme: 'place',
    template: 'scene-poke', interaction: 'tap',
    narration: '走进小庙，敲一下钟。',
    props: { hero: '🛕', items: ['🔑', '🔔', '🪵'], goal: 3 },
    templateFallback: false
  },
  {
    char: '府', unit: 'u86', theme: 'shape',
    template: 'grow-tap', interaction: 'tap',
    narration: '政府大楼前，升升国旗。',
    props: { hero: '🏛️', stages: ['📦', '🏛️', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '剂', unit: 'u86', theme: 'object',
    template: 'pair-match', interaction: 'drag',
    narration: '药剂量一勺，喝下去。',
    props: { hero: '💊', pairs: [{ a: '💊', b: '🧩' }, { a: '🌱', b: '🔥' }, { a: '🧩', b: '💊' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '郊', unit: 'u86', theme: 'place',
    template: 'trace-path', interaction: 'drag',
    narration: '去郊外野餐，铺开毯子。',
    props: { hero: '🌳', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '废', unit: 'u86', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '废纸回收，扔进蓝桶。',
    props: { hero: '♻️', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '盲', unit: 'u86', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '闭上眼当盲人，摸索前进。',
    props: { hero: '🦯', items: ['🦯', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '闸', unit: 'u86', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '拉开水闸，水流出来。',
    props: { hero: '🚧', sound: '哗哗', goal: 3 },
    templateFallback: false
  },
  {
    char: '闹', unit: 'u86', theme: 'action',
    template: 'morph-story', interaction: 'sequence',
    narration: '闹钟闹起来，快关掉它。',
    props: { hero: '🎪', stages: ['🪵', '🎪', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '郑', unit: 'u86', theme: 'number',
    template: 'pair-match', interaction: 'drag',
    narration: '郑重地点头，答应下来。',
    props: { hero: '👤', pairs: [{ a: '👤', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '👤' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '券', unit: 'u86', theme: 'number',
    template: 'sort-buckets', interaction: 'drag',
    narration: '撕下一张券，换小礼品。',
    props: { hero: '🎫', items: [{ item: '🎫', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '单', unit: 'u86', theme: 'food',
    template: 'color-fill', interaction: 'tap',
    narration: '单人座位，只坐一个人。',
    props: { hero: '1️⃣', color: 'yellow', goal: 3 },
    templateFallback: false
  },
  {
    char: '炎', unit: 'u86', theme: 'weather',
    template: 'rain-catch', interaction: 'drag',
    narration: '太阳炎热，撑开遮阳伞。',
    props: { hero: '🔥', items: ['🌙', '🎈', '🧩'], tool: '🔥', goal: 3 },
    templateFallback: false
  },
  {
    char: '炉', unit: 'u86', theme: 'object',
    template: 'tap-reveal', interaction: 'tap',
    narration: '往炉子里添柴，火更旺。',
    props: { hero: '🔥', items: ['☀️', '🎁', '🔔'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
