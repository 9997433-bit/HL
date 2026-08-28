/**
 * 富互动 play 分片 u15 —— 这一单元的 12 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u15'

export const UNIT_RICH_PLAYS = [
  {
    char: '米', unit: 'u15', theme: 'food',
    template: 'count-tap', interaction: 'tap',
    narration: '一粒一粒的白米，装进小碗里。',
    props: { hero: '🍙', items: ['🍚', '🍚', '🍚'], goal: 3 },
    templateFallback: false
  },
  {
    char: '饭', unit: 'u15', theme: 'food',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '米煮成饭啦，一口一口吃干净。',
    props: { hero: '🍚', items: ['🍚', '🍚', '🍚'], goal: 3 },
    templateFallback: false
  },
  {
    char: '菜', unit: 'u15', theme: 'food',
    template: 'sort-buckets', interaction: 'drag',
    narration: '把青菜放进菜篮，别放错了。',
    props: { hero: '🥬', items: [{ item: '🥦', bucket: '是菜' }, { item: '🥕', bucket: '是菜' }, { item: '🍭', bucket: '不是菜' }, { item: '🍫', bucket: '不是菜' }], buckets: [{ label: '是菜', emoji: '🥬' }, { label: '不是菜', emoji: '🍬' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '果', unit: 'u15', theme: 'food',
    template: 'grow-tap', interaction: 'tap',
    narration: '花谢了，树上结出果子。',
    props: { hero: '🍇', stages: ['🌸', '🍏', '🍎'], goal: 3 },
    templateFallback: false
  },
  {
    char: '苹', unit: 'u15', theme: 'food',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '一堆水果里，找出红苹果。',
    props: { hero: '🍎', target: '🍎', decoys: ['🍌', '🍇', '🍐'], goal: 3 },
    templateFallback: false
  },
  {
    char: '面', unit: 'u15', theme: 'food',
    template: 'trace-path', interaction: 'drag',
    narration: '长长的面条，夹起来吸溜一口。',
    props: { hero: '🍜', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '蛋', unit: 'u15', theme: 'food',
    template: 'tap-reveal', interaction: 'tap',
    narration: '敲一敲蛋壳，看看里面是谁。',
    props: { hero: '🥚', items: ['🥚', '🥚', '🐣'], goal: 3 },
    templateFallback: false
  },
  {
    char: '奶', unit: 'u15', theme: 'food',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '咕嘟咕嘟，把牛奶喝完。',
    props: { hero: '🍼', items: ['🥛', '🥛'], goal: 2 },
    templateFallback: false
  },
  {
    char: '糖', unit: 'u15', theme: 'food',
    template: 'count-tap', interaction: 'tap',
    narration: '数数糖果，不过一天只能吃一颗。',
    props: { hero: '🍬', items: ['🍬', '🍭', '🍫'], goal: 3 },
    templateFallback: false
  },
  {
    char: '茶', unit: 'u15', theme: 'food',
    template: 'grow-tap', interaction: 'tap',
    narration: '茶叶放进水里，泡出香香的茶。',
    props: { hero: '🍵', stages: ['🍃', '🫖', '🍵'], goal: 3 },
    templateFallback: false
  },
  {
    char: '肉', unit: 'u15', theme: 'food',
    template: 'sort-buckets', interaction: 'drag',
    narration: '哪些是肉？把肉放进盘子。',
    props: { hero: '🍖', items: [{ item: '🍗', bucket: '是肉' }, { item: '🥩', bucket: '是肉' }, { item: '🥕', bucket: '不是肉' }, { item: '🥦', bucket: '不是肉' }], buckets: [{ label: '是肉', emoji: '🍖' }, { label: '不是肉', emoji: '🥬' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '瓜', unit: 'u15', theme: 'food',
    template: 'drag-parts', interaction: 'drag',
    narration: '大西瓜切开，一块一块分着吃。',
    props: { hero: '🍉', parts: ['🍉', '🍉', '🍉'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
