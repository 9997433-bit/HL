/**
 * 富互动 play 分片 u9 —— 这一单元的 12 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u9'

export const UNIT_RICH_PLAYS = [
  {
    char: '鱼', unit: 'u9', theme: 'animal',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '水里游过好多东西，点住那条小鱼。',
    props: { hero: '🐟', target: '🐟', decoys: ['🐙', '🦀', '🐚'], goal: 3 },
    templateFallback: false
  },
  {
    char: '虫', unit: 'u9', theme: 'animal',
    template: 'trace-path', interaction: 'drag',
    narration: '小虫子扭一扭，慢慢爬过树叶。',
    props: { hero: '🐛', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '马', unit: 'u9', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '驾！小马嗒嗒嗒地往前跑。',
    props: { hero: '🐴', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '猫', unit: 'u9', theme: 'animal',
    template: 'sound-tap', interaction: 'tap',
    narration: '摸摸小猫，它喵地叫了一声。',
    props: { hero: '🐱', sound: '喵', goal: 3 },
    templateFallback: false
  },
  {
    char: '狗', unit: 'u9', theme: 'animal',
    template: 'sound-tap', interaction: 'tap',
    narration: '拍拍小狗的头，它汪汪叫。',
    props: { hero: '🐶', sound: '汪', goal: 3 },
    templateFallback: false
  },
  {
    char: '鸡', unit: 'u9', theme: 'animal',
    template: 'sound-tap', interaction: 'tap',
    narration: '小鸡叽叽叫，还会下蛋。',
    props: { hero: '🐔', sound: '叽', goal: 3 },
    templateFallback: false
  },
  {
    char: '鸭', unit: 'u9', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '扁嘴巴的小鸭，摇摇摆摆下水啦。',
    props: { hero: '🦆', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '猪', unit: 'u9', theme: 'animal',
    template: 'sound-tap', interaction: 'tap',
    narration: '胖小猪拱拱鼻子，哼哼哼。',
    props: { hero: '🐷', sound: '哼', goal: 3 },
    templateFallback: false
  },
  {
    char: '象', unit: 'u9', theme: 'animal',
    template: 'grow-tap', interaction: 'tap',
    narration: '大象的长鼻子，能卷起水喷出来。',
    props: { hero: '🐘', stages: ['🐘', '🚿', '🌊'], goal: 3 },
    templateFallback: false
  },
  {
    char: '虎', unit: 'u9', theme: 'animal',
    template: 'sound-tap', interaction: 'tap',
    narration: '老虎吼一声，森林都安静了。',
    props: { hero: '🐯', sound: '吼', goal: 3 },
    templateFallback: false
  },
  {
    char: '蛙', unit: 'u9', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '青蛙呱呱，一蹦跳到荷叶上。',
    props: { hero: '🐸', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '熊', unit: 'u9', theme: 'animal',
    template: 'scene-poke', interaction: 'tap',
    narration: '大熊要冬眠了，帮它准备好。',
    props: { hero: '🐻', items: ['🍯', '🛌', '🌲'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
