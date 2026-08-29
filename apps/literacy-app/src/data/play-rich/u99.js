/**
 * 富互动 play 分片 u99 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u99'

export const UNIT_RICH_PLAYS = [
  {
    char: '起', unit: 'u99', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '太阳升起，拉开窗帘。',
    props: { hero: '🌅', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '捎', unit: 'u99', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '捎一封信，顺路带上。',
    props: { hero: '📮', items: ['📮', '📮', '📮'], goal: 3 },
    templateFallback: false
  },
  {
    char: '捏', unit: 'u99', theme: 'body',
    template: 'tap-reveal', interaction: 'tap',
    narration: '捏一团泥，捏成小兔。',
    props: { hero: '🫰', items: ['🎁', '🧩', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '捉', unit: 'u99', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '捉住蝴蝶，轻轻放开。',
    props: { hero: '🦋', target: '🦋', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '捆', unit: 'u99', theme: 'number',
    template: 'grow-tap', interaction: 'tap',
    narration: '木头捆成一捆，扎紧。',
    props: { hero: '🪢', stages: ['📦', '🪢', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '捐', unit: 'u99', theme: 'school',
    template: 'drag-parts', interaction: 'drag',
    narration: '捐出旧书，放进爱心箱。',
    props: { hero: '🎁', parts: ['🧩', '🌱', '🎁'], goal: 3 },
    templateFallback: false
  },
  {
    char: '损', unit: 'u99', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '哪个杯子受损了？找裂痕。',
    props: { hero: '💔', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '袁', unit: 'u99', theme: 'place',
    template: 'scene-poke', interaction: 'tap',
    narration: '找到姓袁的卡片。',
    props: { hero: '👤', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '哲', unit: 'u99', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '想一条哲理，点亮灯泡。',
    props: { hero: '🤔', items: ['🤔', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '捡', unit: 'u99', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '把垃圾捡起来，扔进桶。',
    props: { hero: '🧹', sound: '嗡嗡', goal: 3 },
    templateFallback: false
  },
  {
    char: '挽', unit: 'u99', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '挽起袖子，准备干活。',
    props: { hero: '👕', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '捣', unit: 'u99', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '用杵捣年糕，捣软它。',
    props: { hero: '🥣', pairs: [{ a: '🥣', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '🥣' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '壶', unit: 'u99', theme: 'food',
    template: 'drag-parts', interaction: 'drag',
    narration: '茶壶倒水，倒满三杯。',
    props: { hero: '🫖', parts: ['🔥', '☀️', '🫖'], goal: 3 },
    templateFallback: false
  },
  {
    char: '捅', unit: 'u99', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '轻轻捅破纸窗，看外面。',
    props: { hero: '📌', items: ['📌', '❄️', '⭐'], goal: 3 },
    templateFallback: false
  },
  {
    char: '挨', unit: 'u99', theme: 'action',
    template: 'rain-catch', interaction: 'drag',
    narration: '挨着坐，肩并肩。',
    props: { hero: '🧍', items: ['🌙', '🎈', '🧩'], tool: '🧍', goal: 3 },
    templateFallback: false
  },
  {
    char: '耻', unit: 'u99', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '害羞低头，捂住脸。',
    props: { hero: '🙋', items: ['☀️', '🎁', '🔔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '恭', unit: 'u99', theme: 'feeling',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '恭恭敬敬鞠躬，问好。',
    props: { hero: '🙇', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '莽', unit: 'u99', theme: 'nature',
    template: 'count-tap', interaction: 'tap',
    narration: '草莽丛生，拨开找路。',
    props: { hero: '🌿', items: ['🌿', '🌿', '🌿', '🌿'], goal: 4 },
    templateFallback: false
  },
  {
    char: '莉', unit: 'u99', theme: 'nature',
    template: 'tap-reveal', interaction: 'tap',
    narration: '茉莉花开，闻闻清香。',
    props: { hero: '🌼', items: ['🎁', '🧩', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '莫', unit: 'u99', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '切莫乱跑，停在线内。',
    props: { hero: '🤫', target: '🤫', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
