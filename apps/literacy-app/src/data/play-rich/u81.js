/**
 * 富互动 play 分片 u81 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u81'

export const UNIT_RICH_PLAYS = [
  {
    char: '拦', unit: 'u81', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '伸手拦住，别让球滚走。',
    props: { hero: '🚧', items: ['🚧', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '幸', unit: 'u81', theme: 'feeling',
    template: 'sound-tap', interaction: 'tap',
    narration: '幸运草找到了，摸一摸。',
    props: { hero: '🍀', sound: '呼呼', goal: 3 },
    templateFallback: false
  },
  {
    char: '拧', unit: 'u81', theme: 'number',
    template: 'morph-story', interaction: 'sequence',
    narration: '水龙头拧开，水流出来。',
    props: { hero: '🚰', stages: ['🪵', '🚰', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '招', unit: 'u81', theme: 'body',
    template: 'sound-tap', interaction: 'tap',
    narration: '招招手，请朋友过来。',
    props: { hero: '👋', sound: '嗡嗡', goal: 3 },
    templateFallback: false
  },
  {
    char: '披', unit: 'u81', theme: 'weather',
    template: 'sort-buckets', interaction: 'drag',
    narration: '披上斗篷，变成小超人。',
    props: { hero: '🧥', items: [{ item: '🧥', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '拨', unit: 'u81', theme: 'body',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '拨开草丛，看看藏着谁。',
    props: { hero: '🌿', target: '🌿', decoys: ['❄️', '⭐', '📦'], goal: 1 },
    templateFallback: false
  },
  {
    char: '抬', unit: 'u81', theme: 'number',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '两个人抬起大箱子。',
    props: { hero: '🙌', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '拇', unit: 'u81', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '竖起大拇指，夸夸他。',
    props: { hero: '👍', stages: ['☀️', '👍', '🔔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '其', unit: 'u81', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '其他几个也点亮，别漏。',
    props: { hero: '📗', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '茉', unit: 'u81', theme: 'nature',
    template: 'count-tap', interaction: 'tap',
    narration: '茉莉花香，闻一闻白花。',
    props: { hero: '🌼', items: ['🌼', '🌼', '🌼', '🌼', '🌼'], goal: 5 },
    templateFallback: false
  },
  {
    char: '茂', unit: 'u81', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '草木茂密，钻进小树林。',
    props: { hero: '🌳', stages: ['🎁', '🌳', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '英', unit: 'u81', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '戴上披风，当一回英雄。',
    props: { hero: '🦸', target: '🦸', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '苞', unit: 'u81', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '花苞鼓起来，快要开了。',
    props: { hero: '🌷', stages: ['📦', '🌷', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '范', unit: 'u81', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '照着模范字，描一描。',
    props: { hero: '🏅', parts: ['🧩', '🌱', '🏅'], goal: 3 },
    templateFallback: false
  },
  {
    char: '直', unit: 'u81', theme: 'shape',
    template: 'trace-path', interaction: 'drag',
    narration: '画一条直线，别弯了。',
    props: { hero: '📏', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '茁', unit: 'u81', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '小苗茁壮长，一天天高。',
    props: { hero: '🌱', stages: ['🎯', '🌱', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '茄', unit: 'u81', theme: 'food',
    template: 'color-fill', interaction: 'tap',
    narration: '紫茄子洗净，切成片。',
    props: { hero: '🍆', color: 'red', goal: 3 },
    templateFallback: false
  },
  {
    char: '茎', unit: 'u81', theme: 'nature',
    template: 'sound-tap', interaction: 'tap',
    narration: '花茎撑着花，轻轻扶正。',
    props: { hero: '🌿', sound: '哗哗', goal: 3 },
    templateFallback: false
  },
  {
    char: '苔', unit: 'u81', theme: 'nature',
    template: 'morph-story', interaction: 'sequence',
    narration: '石头上长青苔，摸摸绿绒。',
    props: { hero: '🟩', stages: ['🪵', '🟩', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '茅', unit: 'u81', theme: 'nature',
    template: 'pair-match', interaction: 'drag',
    narration: '茅草屋修好，点亮小窗。',
    props: { hero: '🛖', pairs: [{ a: '🛖', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '🛖' }], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
