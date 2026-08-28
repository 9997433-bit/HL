/**
 * 富互动 play 分片 u70 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u70'

export const UNIT_RICH_PLAYS = [
  {
    char: '宅', unit: 'u70', theme: 'place',
    template: 'scene-poke', interaction: 'tap',
    narration: '回到自家宅子，点点屋里头。',
    props: { hero: '🏠', items: ['🛋️', '🛏️', '🪴'], goal: 3 },
    templateFallback: false
  },
  {
    char: '安', unit: 'u70', theme: 'feeling',
    template: 'grow-tap', interaction: 'tap',
    narration: '小鸽子落下来，心里安安的。',
    props: { hero: '🕊️', stages: ['🌪️', '🕊️', '😌'], goal: 3 },
    templateFallback: false
  },
  {
    char: '许', unit: 'u70', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '说声可以，许你打开这几样。',
    props: { hero: '✅', items: ['🎁', '🍬', '📦'], goal: 3 },
    templateFallback: false
  },
  {
    char: '讽', unit: 'u70', theme: 'feeling',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪张脸在做怪相？挑出面具。',
    props: { hero: '🎭', target: '🎭', decoys: ['🙂', '😐', '😑'], goal: 1 },
    templateFallback: false
  },
  {
    char: '设', unit: 'u70', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '设计一座房子，把零件摆好。',
    props: { hero: '🏗️', parts: ['🧱', '🚪', '🪟'], goal: 3 },
    templateFallback: false
  },
  {
    char: '访', unit: 'u70', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '带着礼物去访问朋友家。',
    props: { hero: '🎁', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '诀', unit: 'u70', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '口诀藏在盒子里，念出来。',
    props: { hero: '🔑', items: ['1️⃣', '2️⃣', '3️⃣'], goal: 3 },
    templateFallback: false
  },
  {
    char: '寻', unit: 'u70', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '拿放大镜寻一寻，找出瓢虫。',
    props: { hero: '🔎', target: '🐞', decoys: ['🍃', '🌿', '🪨'], goal: 1 },
    templateFallback: false
  },
  {
    char: '迅', unit: 'u70', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '嗖一下，迅速跑到那边去。',
    props: { hero: '⚡', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '尽', unit: 'u70', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '一个个吃尽，盘子空空的。',
    props: { hero: '🔚', items: ['🍡', '🍡', '🍡'], goal: 3 },
    templateFallback: false
  },
  {
    char: '异', unit: 'u70', theme: 'feeling',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪一个和别的不一样？',
    props: { hero: '❓', target: '🟣', decoys: ['🔵', '🟦', '🔷'], goal: 1 },
    templateFallback: false
  },
  {
    char: '阵', unit: 'u70', theme: 'weather',
    template: 'count-tap', interaction: 'tap',
    narration: '一阵一阵刮风，刮了三阵。',
    props: { hero: '🌬️', items: ['🌬️', '🌬️', '🌬️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '如', unit: 'u70', theme: 'action',
    template: 'morph-story', interaction: 'sequence',
    narration: '镜子里的样子，和我如出一辙。',
    props: { hero: '🪞', stages: ['🧒', '🪞', '🧒'], goal: 3 },
    templateFallback: false
  },
  {
    char: '妇', unit: 'u70', theme: 'family',
    template: 'tap-reveal', interaction: 'tap',
    narration: '阿姨在忙什么？点开看一看。',
    props: { hero: '👩', items: ['🧺', '🍲', '🧹'], goal: 3 },
    templateFallback: false
  },
  {
    char: '驮', unit: 'u70', theme: 'animal',
    template: 'drag-parts', interaction: 'drag',
    narration: '骆驼背上驮着货，装好它。',
    props: { hero: '🐫', parts: ['📦', '🐫'], goal: 2 },
    templateFallback: false
  },
  {
    char: '纤', unit: 'u70', theme: 'object',
    template: 'count-tap', interaction: 'tap',
    narration: '细纤纤的线一根根，数三根。',
    props: { hero: '🧵', items: ['🧵', '🧵', '🧵'], goal: 3 },
    templateFallback: false
  },
  {
    char: '驯', unit: 'u70', theme: 'animal',
    template: 'count-tap', interaction: 'tap',
    narration: '小马被驯服了，拍它三下。',
    props: { hero: '🐎', items: ['🐎', '🐎', '🐎'], goal: 3 },
    templateFallback: false
  },
  {
    char: '约', unit: 'u70', theme: 'time',
    template: 'pair-match', interaction: 'drag',
    narration: '约好了时间，把日子配起来。',
    props: { hero: '📅', pairs: [{ a: '📅', b: '🎂' }, { a: '⏰', b: '🏫' }, { a: '🌙', b: '🛏️' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '级', unit: 'u70', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '一级一级往上爬楼梯。',
    props: { hero: '🪜', stages: ['🪜', '🧗', '🏔️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '驰', unit: 'u70', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '骏马撒开腿，飞驰起来。',
    props: { hero: '🐴', dir: 'right', goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
