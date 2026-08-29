/**
 * 富互动 play 分片 u80 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u80'

export const UNIT_RICH_PLAYS = [
  {
    char: '玫', unit: 'u80', theme: 'color',
    template: 'grow-tap', interaction: 'tap',
    narration: '红玫瑰盛开，摘三朵。',
    props: { hero: '🌹', stages: ['📦', '🌹', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '规', unit: 'u80', theme: 'shape',
    template: 'drag-parts', interaction: 'drag',
    narration: '用圆规画一个圆。',
    props: { hero: '📐', parts: ['🧩', '🌱', '📐'], goal: 3 },
    templateFallback: false
  },
  {
    char: '抹', unit: 'u80', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '拿海绵抹掉黑板上的字。',
    props: { hero: '🧽', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '拢', unit: 'u80', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '双手合拢，捧住小鸟。',
    props: { hero: '🐦', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '拔', unit: 'u80', theme: 'nature',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '用力拔萝卜，拔出三根。',
    props: { hero: '🌱', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '坪', unit: 'u80', theme: 'nature',
    template: 'sound-tap', interaction: 'tap',
    narration: '草坪上野餐，点亮毯子。',
    props: { hero: '🌿', sound: '嗡嗡', goal: 3 },
    templateFallback: false
  },
  {
    char: '拣', unit: 'u80', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '把好豆子拣出来，放一边。',
    props: { hero: '🫘', target: '🫘', decoys: ['🪵', '❄️', '🎈'], goal: 1 },
    templateFallback: false
  },
  {
    char: '坦', unit: 'u80', theme: 'body',
    template: 'pair-match', interaction: 'drag',
    narration: '路又平又坦，一路滑过去。',
    props: { hero: '🛣️', pairs: [{ a: '🛣️', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '🛣️' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '担', unit: 'u80', theme: 'body',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '肩上担着货，走稳当。',
    props: { hero: '🎒', target: '🎒', decoys: ['🔥', '☀️', '🔑'], goal: 1 },
    templateFallback: false
  },
  {
    char: '押', unit: 'u80', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '押金先放这儿，拿回凭证。',
    props: { hero: '🖊️', items: [{ item: '🖊️', bucket: '左' }, { item: '📦', bucket: '左' }, { item: '❄️', bucket: '右' }, { item: '⭐', bucket: '右' }], buckets: [{ label: '左', emoji: '❄️' }, { label: '右', emoji: '⭐' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '抽', unit: 'u80', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '从书架抽出一本故事书。',
    props: { hero: '📚', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '拐', unit: 'u80', theme: 'shape',
    template: 'tap-reveal', interaction: 'tap',
    narration: '到路口拐弯，往左走。',
    props: { hero: '↩️', items: ['☀️', '🎁', '🔔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '者', unit: 'u80', theme: 'school',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '记者举话筒，采访一下。',
    props: { hero: '🙋', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '拆', unit: 'u80', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '把纸箱拆开，取出礼物。',
    props: { hero: '📦', items: [{ item: '📦', bucket: '左' }, { item: '🌱', bucket: '左' }, { item: '🎈', bucket: '右' }, { item: '📦', bucket: '右' }], buckets: [{ label: '左', emoji: '🎈' }, { label: '右', emoji: '📦' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '拎', unit: 'u80', theme: 'body',
    template: 'tap-reveal', interaction: 'tap',
    narration: '拎起购物袋，回家去。',
    props: { hero: '🛍️', items: ['🎁', '🧩', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '拥', unit: 'u80', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '张开双臂，拥一个大抱。',
    props: { hero: '🫂', target: '🫂', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '抵', unit: 'u80', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '举起盾抵挡住飞来的球。',
    props: { hero: '🛡️', stages: ['📦', '🛡️', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '拘', unit: 'u80', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '太拘束了，放松肩膀。',
    props: { hero: '😶', parts: ['🧩', '🌱', '😶'], goal: 3 },
    templateFallback: false
  },
  {
    char: '势', unit: 'u80', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '摆个姿势，拍一张照片。',
    props: { hero: '✍️', items: ['✍️', '✍️', '✍️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '垃', unit: 'u80', theme: 'object',
    template: 'scene-poke', interaction: 'tap',
    narration: '垃圾分类，扔进对的桶。',
    props: { hero: '🗑️', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
