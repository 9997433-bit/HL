/**
 * 富互动 play 分片 u32 —— 这一单元的 18 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u32'

export const UNIT_RICH_PLAYS = [
  {
    char: '练', unit: 'u32', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '一遍一遍地练，练满五遍。',
    props: { hero: '🏋️', items: ['⭐', '⭐', '⭐', '⭐', '⭐'], goal: 5 },
    templateFallback: false
  },
  {
    char: '习', unit: 'u32', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '每天练一点，本领越来越大。',
    props: { hero: '📖', stages: ['🌱', '💪', '🏆'], goal: 3 },
    templateFallback: false
  },
  {
    char: '记', unit: 'u32', theme: 'school',
    template: 'tap-reveal', interaction: 'tap',
    narration: '记在小本子上，就不容易忘。',
    props: { hero: '📓', items: ['✏️', '📌', '💡'], goal: 3 },
    templateFallback: false
  },
  {
    char: '忘', unit: 'u32', theme: 'school',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '想不起来了，像气球一个个飞走。',
    props: { hero: '💭', items: ['🎈', '🎈', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '认', unit: 'u32', theme: 'school',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '这个字你认得吗？把它认出来。',
    props: { hero: '👀', target: '字', decoys: ['木', '火', '山'], goal: 1 },
    templateFallback: false
  },
  {
    char: '识', unit: 'u32', theme: 'school',
    template: 'pair-match', interaction: 'drag',
    narration: '见过就认识，把字和图配起来。',
    props: { hero: '🔍', pairs: [{ a: '山', b: '⛰️' }, { a: '水', b: '💧' }, { a: '火', b: '🔥' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '懂', unit: 'u32', theme: 'feeling',
    template: 'grow-tap', interaction: 'tap',
    narration: '想一想，忽然一下就懂了。',
    props: { hero: '💡', stages: ['😕', '🤔', '💡'], goal: 3 },
    templateFallback: false
  },
  {
    char: '帮', unit: 'u32', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '搭把手，帮妈妈把篮子提回家。',
    props: { hero: '🧺', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '助', unit: 'u32', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '谁需要帮助？把人和帮手配好。',
    props: { hero: '🙌', pairs: [{ a: '🧓', b: '🤝' }, { a: '🧒', b: '📚' }, { a: '🐕', b: '🦴' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '试', unit: 'u32', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '试一试才知道，点开看结果。',
    props: { hero: '❔', items: ['✅', '✅', '❌'], goal: 3 },
    templateFallback: false
  },
  {
    char: '比', unit: 'u32', theme: 'shape',
    template: 'sort-buckets', interaction: 'drag',
    narration: '比一比，高的一边矮的一边。',
    props: { hero: '⚖️', items: [{ item: '🌳', bucket: '高' }, { item: '🏢', bucket: '高' }, { item: '🌱', bucket: '矮' }, { item: '🐜', bucket: '矮' }], buckets: [{ label: '高', emoji: '⬆️' }, { label: '矮', emoji: '⬇️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '赛', unit: 'u32', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '预备——跑！比赛开始啦。',
    props: { hero: '🏁', dir: 'right', goal: 5 },
    templateFallback: false
  },
  {
    char: '查', unit: 'u32', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '一页一页查一查，把它找出来。',
    props: { hero: '🔎', target: '🔍', decoys: ['📕', '📗', '📘'], goal: 1 },
    templateFallback: false
  },
  {
    char: '借', unit: 'u32', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把铅笔借给同桌用一下。',
    props: { hero: '✏️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '换', unit: 'u32', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '我的换你的，两样东西换一换。',
    props: { hero: '🔄', pairs: [{ a: '🍎', b: '🍐' }, { a: '🧸', b: '🪀' }, { a: '🎈', b: '🎁' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '修', unit: 'u32', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '车子坏了，拿工具把它修好。',
    props: { hero: '🔧', parts: ['🔧', '🔨', '🪛'], goal: 3 },
    templateFallback: false
  },
  {
    char: '种', unit: 'u32', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '挖个坑种下种子，浇水等它长。',
    props: { hero: '🌱', stages: ['🕳️', '🌰', '🌱'], goal: 3 },
    templateFallback: false
  },
  {
    char: '养', unit: 'u32', theme: 'animal',
    template: 'scene-poke', interaction: 'tap',
    narration: '养小狗要喂饭、遛弯、洗澡。',
    props: { hero: '🐕', items: ['🍖', '🦴', '🚿'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
