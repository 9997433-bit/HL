/**
 * 富互动 play 分片 u82 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u82'

export const UNIT_RICH_PLAYS = [
  {
    char: '枚', unit: 'u82', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '数一数，有几枚硬币。',
    props: { hero: '🪙', items: ['🪙', '🪙', '🪙', '🪙'], goal: 4 },
    templateFallback: false
  },
  {
    char: '枫', unit: 'u82', theme: 'nature',
    template: 'color-fill', interaction: 'tap',
    narration: '枫叶变红了，捡起三片。',
    props: { hero: '🍁', color: 'violet', goal: 3 },
    templateFallback: false
  },
  {
    char: '构', unit: 'u82', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '积木构起来，搭成高塔。',
    props: { hero: '🏗️', parts: ['🌙', '🎈', '🏗️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '杭', unit: 'u82', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '小船驶向杭州，漂过桥。',
    props: { hero: '🏞️', items: ['☀️', '🎁', '🔔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '杰', unit: 'u82', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '杰出小明星，戴上奖章。',
    props: { hero: '🌟', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '枕', unit: 'u82', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '枕头摆好，准备睡觉。',
    props: { hero: '🛏️', items: ['🛏️', '🛏️', '🛏️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '矿', unit: 'u82', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '挖出矿石，放进矿车。',
    props: { hero: '⛏️', items: ['🎁', '🧩', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '奔', unit: 'u82', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '撒开腿奔跑，冲向终点。',
    props: { hero: '🐎', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '奋', unit: 'u82', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '握紧拳头，奋力跳起来。',
    props: { hero: '✊', stages: ['📦', '✊', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '态', unit: 'u82', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '换个态度，笑脸对大家。',
    props: { hero: '🎭', parts: ['🧩', '🌱', '🎭'], goal: 3 },
    templateFallback: false
  },
  {
    char: '欧', unit: 'u82', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '在地图上找到欧洲。',
    props: { hero: '🌍', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '妻', unit: 'u82', theme: 'family',
    template: 'scene-poke', interaction: 'tap',
    narration: '新娘和新郎，妻子牵手。',
    props: { hero: '👩', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '轰', unit: 'u82', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '雷声轰轰响，捂住耳朵。',
    props: { hero: '💥', sound: '咔咔', goal: 3 },
    templateFallback: false
  },
  {
    char: '肯', unit: 'u82', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '点头说肯，愿意帮忙。',
    props: { hero: '👍', sound: '嗡嗡', goal: 3 },
    templateFallback: false
  },
  {
    char: '肾', unit: 'u82', theme: 'body',
    template: 'morph-story', interaction: 'sequence',
    narration: '找到肾脏卡片，贴正确。',
    props: { hero: '🫘', stages: ['🪵', '🫘', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '贤', unit: 'u82', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '贤惠姐姐，把家收拾好。',
    props: { hero: '📚', pairs: [{ a: '📚', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '📚' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '尚', unit: 'u82', theme: 'weather',
    template: 'sort-buckets', interaction: 'drag',
    narration: '时尚帽子戴上，转一圈。',
    props: { hero: '⏳', items: [{ item: '⏳', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '旺', unit: 'u82', theme: 'body',
    template: 'grow-tap', interaction: 'tap',
    narration: '炉火很旺，越烧越亮。',
    props: { hero: '🔥', stages: ['❄️', '🔥', '📦'], goal: 3 },
    templateFallback: false
  },
  {
    char: '昆', unit: 'u82', theme: 'animal',
    template: 'rain-catch', interaction: 'drag',
    narration: '找一找哪只是昆虫。',
    props: { hero: '🦋', items: ['🌙', '🎈', '🧩'], tool: '🦋', goal: 3 },
    templateFallback: false
  },
  {
    char: '哎', unit: 'u82', theme: 'word',
    template: 'sound-tap', interaction: 'tap',
    narration: '哎一声，打招呼问好。',
    props: { hero: '😮', sound: '嗡嗡', goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
