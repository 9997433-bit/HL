/**
 * 富互动 play 分片 u87 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u87'

export const UNIT_RICH_PLAYS = [
  {
    char: '沫', unit: 'u87', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '肥皂沫冒起来，戳破泡泡。',
    props: { hero: '🫧', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '法', unit: 'u87', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '想个办法，解开谜题。',
    props: { hero: '⚖️', items: ['⚖️', '⚖️', '⚖️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '沾', unit: 'u87', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '笔尖沾墨水，写一个字。',
    props: { hero: '🖌️', items: ['🎁', '🧩', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '泪', unit: 'u87', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '擦掉眼泪，换上笑脸。',
    props: { hero: '😢', target: '😢', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '泊', unit: 'u87', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '小船停泊在岸边，系好绳。',
    props: { hero: '⛵', stages: ['📦', '⛵', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '泡', unit: 'u87', theme: 'food',
    template: 'drag-parts', interaction: 'drag',
    narration: '泡泡飞起来，戳破三个。',
    props: { hero: '🫧', parts: ['🧩', '🌱', '🫧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '注', unit: 'u87', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '往杯子里注水，倒满。',
    props: { hero: '👀', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '泣', unit: 'u87', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '小声哭泣，递一张纸巾。',
    props: { hero: '😭', sound: '呼呼', goal: 3 },
    templateFallback: false
  },
  {
    char: '沸', unit: 'u87', theme: 'weather',
    template: 'grow-tap', interaction: 'tap',
    narration: '水沸腾了，冒出热气。',
    props: { hero: '♨️', stages: ['🌱', '♨️', '☀️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '沼', unit: 'u87', theme: 'nature',
    template: 'sound-tap', interaction: 'tap',
    narration: '沼泽里有青蛙，找出来。',
    props: { hero: '🐸', sound: '嗡嗡', goal: 3 },
    templateFallback: false
  },
  {
    char: '泽', unit: 'u87', theme: 'shape',
    template: 'morph-story', interaction: 'sequence',
    narration: '水面有光泽，闪一闪。',
    props: { hero: '✨', stages: ['🪵', '✨', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '性', unit: 'u87', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '每种动物性格不同，配对。',
    props: { hero: '🎭', pairs: [{ a: '🎭', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '🎭' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '怜', unit: 'u87', theme: 'body',
    template: 'sort-buckets', interaction: 'drag',
    narration: '可怜小猫，给它温暖。',
    props: { hero: '🥺', items: [{ item: '🥺', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '宝', unit: 'u87', theme: 'action',
    template: 'color-fill', interaction: 'tap',
    narration: '打开宝箱，取出宝石。',
    props: { hero: '💎', color: 'red', goal: 3 },
    templateFallback: false
  },
  {
    char: '宗', unit: 'u87', theme: 'action',
    template: 'rain-catch', interaction: 'drag',
    narration: '找到祖宗画像，点亮它。',
    props: { hero: '🎯', items: ['🌙', '🎈', '🧩'], tool: '🎯', goal: 3 },
    templateFallback: false
  },
  {
    char: '定', unit: 'u87', theme: 'number',
    template: 'tap-reveal', interaction: 'tap',
    narration: '钉住图钉，位置定好了。',
    props: { hero: '📌', items: ['☀️', '🎁', '🔔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '宠', unit: 'u87', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '摸摸宠物，它摇尾巴。',
    props: { hero: '🐹', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '审', unit: 'u87', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '仔细审题，再选答案。',
    props: { hero: '🔍', items: ['🔍', '🔍', '🔍', '🔍'], goal: 4 },
    templateFallback: false
  },
  {
    char: '官', unit: 'u87', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '五官找一找：眼耳口鼻。',
    props: { hero: '👀', items: ['🎁', '🧩', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '宛', unit: 'u87', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '云朵宛如小羊，找相似的。',
    props: { hero: '🪞', target: '🪞', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
