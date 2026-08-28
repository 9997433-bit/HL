/**
 * 富互动 play 分片 u25 —— 这一单元的 18 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u25'

export const UNIT_RICH_PLAYS = [
  {
    char: '鹅', unit: 'u25', theme: 'animal',
    template: 'sound-tap', interaction: 'tap',
    narration: '大白鹅伸长脖子，嘎嘎叫。',
    props: { hero: '🦢', sound: '嘎', goal: 3 },
    templateFallback: false
  },
  {
    char: '蛇', unit: 'u25', theme: 'animal',
    template: 'trace-path', interaction: 'drag',
    narration: '小蛇扭来扭去，钻进草丛里。',
    props: { hero: '🐍', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '龟', unit: 'u25', theme: 'animal',
    template: 'trace-path', interaction: 'drag',
    narration: '乌龟背着壳，慢慢爬过沙地。',
    props: { hero: '🐢', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '虾', unit: 'u25', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '小虾一弹尾巴，往后蹦一下。',
    props: { hero: '🦐', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '蟹', unit: 'u25', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '螃蟹横着走，往旁边挪一挪。',
    props: { hero: '🦀', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '蜂', unit: 'u25', theme: 'animal',
    template: 'sound-tap', interaction: 'tap',
    narration: '小蜜蜂采花蜜，嗡嗡嗡。',
    props: { hero: '🐝', sound: '嗡', goal: 3 },
    templateFallback: false
  },
  {
    char: '蝶', unit: 'u25', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '蝴蝶扇扇翅膀，飞到花上去。',
    props: { hero: '🦋', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '猴', unit: 'u25', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '猴子抓住藤条，荡到对面去。',
    props: { hero: '🐒', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '狼', unit: 'u25', theme: 'animal',
    template: 'sound-tap', interaction: 'tap',
    narration: '月亮出来了，狼对着月亮嚎。',
    props: { hero: '🐺', sound: '嗷呜', goal: 3 },
    templateFallback: false
  },
  {
    char: '鹿', unit: 'u25', theme: 'animal',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '头上顶着角的是鹿，找出它。',
    props: { hero: '🦌', target: '🦌', decoys: ['🐎', '🐕', '🐄'], goal: 1 },
    templateFallback: false
  },
  {
    char: '鼠', unit: 'u25', theme: 'animal',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '小老鼠搬奶酪，一块一块搬走。',
    props: { hero: '🐭', items: ['🧀', '🧀', '🧀'], goal: 3 },
    templateFallback: false
  },
  {
    char: '燕', unit: 'u25', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '小燕子往南飞，翅膀一斜就走。',
    props: { hero: '🐦', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '蚁', unit: 'u25', theme: 'animal',
    template: 'count-tap', interaction: 'tap',
    narration: '一队蚂蚁搬粮食，数数几只。',
    props: { hero: '🐜', items: ['🐜', '🐜', '🐜', '🐜', '🐜'], goal: 5 },
    templateFallback: false
  },
  {
    char: '蚊', unit: 'u25', theme: 'animal',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '嗡——把讨厌的蚊子拍下来。',
    props: { hero: '🦟', items: ['🦟', '🦟', '🦟'], goal: 3 },
    templateFallback: false
  },
  {
    char: '尾', unit: 'u25', theme: 'animal',
    template: 'tap-reveal', interaction: 'tap',
    narration: '谁有尾巴？点点它们的小尾巴。',
    props: { hero: '🐕', items: ['🐈', '🐒', '🦎'], goal: 3 },
    templateFallback: false
  },
  {
    char: '角', unit: 'u25', theme: 'animal',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '谁的头上长着角？点出来。',
    props: { hero: '🦌', target: '🐂', decoys: ['🐖', '🐇', '🐓'], goal: 1 },
    templateFallback: false
  },
  {
    char: '羽', unit: 'u25', theme: 'animal',
    template: 'rain-catch', interaction: 'drag',
    narration: '鸟儿抖抖身子，接住飘下的羽毛。',
    props: { hero: '🐦', items: ['🪶', '🪶', '🪶'], tool: '🤲', goal: 3 },
    templateFallback: false
  },
  {
    char: '爪', unit: 'u25', theme: 'animal',
    template: 'drag-parts', interaction: 'drag',
    narration: '给小猫装上三只尖尖的爪。',
    props: { hero: '🐾', parts: ['🐾', '🐾', '🐾'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
