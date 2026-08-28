/**
 * 富互动 play 分片 u24 —— 这一单元的 18 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u24'

export const UNIT_RICH_PLAYS = [
  {
    char: '叶', unit: 'u24', theme: 'nature',
    template: 'count-tap', interaction: 'tap',
    narration: '数数树枝上挂着几片叶子。',
    props: { hero: '🍃', items: ['🍃', '🍃', '🍃', '🍃'], goal: 4 },
    templateFallback: false
  },
  {
    char: '根', unit: 'u24', theme: 'nature',
    template: 'trace-path', interaction: 'drag',
    narration: '顺着树根，一直画到土里去。',
    props: { hero: '🌳', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '苗', unit: 'u24', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '小苗喝饱水，冒出两片嫩叶子。',
    props: { hero: '🌾', stages: ['🌰', '🌱', '🌿'], goal: 3 },
    templateFallback: false
  },
  {
    char: '竹', unit: 'u24', theme: 'nature',
    template: 'drag-parts', interaction: 'drag',
    narration: '一节一节接起来，长成一根竹。',
    props: { hero: '🎋', parts: ['🎋', '🎋', '🎋'], goal: 3 },
    templateFallback: false
  },
  {
    char: '松', unit: 'u24', theme: 'nature',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪棵是松树？找出尖尖的那棵。',
    props: { hero: '🌲', target: '🌲', decoys: ['🌳', '🌴', '🌵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '桃', unit: 'u24', theme: 'food',
    template: 'grow-tap', interaction: 'tap',
    narration: '桃花谢了，枝头结出大桃子。',
    props: { hero: '🍑', stages: ['🌸', '🟢', '🍑'], goal: 3 },
    templateFallback: false
  },
  {
    char: '梨', unit: 'u24', theme: 'food',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '咬一口又一口，把甜梨吃完。',
    props: { hero: '🍐', items: ['🍐', '🍐', '🍐'], goal: 3 },
    templateFallback: false
  },
  {
    char: '麦', unit: 'u24', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '麦子熟了，一片地金灿灿。',
    props: { hero: '🌾', stages: ['🌱', '🌿', '🌾'], goal: 3 },
    templateFallback: false
  },
  {
    char: '谷', unit: 'u24', theme: 'food',
    template: 'count-tap', interaction: 'tap',
    narration: '一粒一粒的谷子，收进谷仓。',
    props: { hero: '🌾', items: ['🌾', '🌾', '🌾', '🌾'], goal: 4 },
    templateFallback: false
  },
  {
    char: '豆', unit: 'u24', theme: 'food',
    template: 'count-tap', interaction: 'tap',
    narration: '剥开豆荚，数数里面几颗豆。',
    props: { hero: '🫘', items: ['🫘', '🫘', '🫘', '🫘'], goal: 4 },
    templateFallback: false
  },
  {
    char: '芽', unit: 'u24', theme: 'nature',
    template: 'morph-story', interaction: 'sequence',
    narration: '种子裂开一条缝，钻出小芽。',
    props: { hero: '🌱', stages: ['🌰', '🌱', '芽'], goal: 3 },
    templateFallback: false
  },
  {
    char: '荷', unit: 'u24', theme: 'nature',
    template: 'scene-poke', interaction: 'tap',
    narration: '荷叶圆圆铺满池，上面有谁。',
    props: { hero: '🪷', items: ['🐸', '🦆', '🐞'], goal: 3 },
    templateFallback: false
  },
  {
    char: '枝', unit: 'u24', theme: 'nature',
    template: 'drag-parts', interaction: 'drag',
    narration: '给大树装上枝丫，好挂果子。',
    props: { hero: '🌳', parts: ['🌳', '🌿', '🌿'], goal: 3 },
    templateFallback: false
  },
  {
    char: '森', unit: 'u24', theme: 'nature',
    template: 'drag-parts', interaction: 'drag',
    narration: '三个木挤在一起，就是森。',
    props: { hero: '🌲', parts: ['木', '木', '木'], goal: 3 },
    templateFallback: false
  },
  {
    char: '柳', unit: 'u24', theme: 'nature',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '柳条长长的，风一吹就摆。',
    props: { hero: '🌿', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '杏', unit: 'u24', theme: 'food',
    template: 'color-fill', interaction: 'tap',
    narration: '把杏子涂成黄澄澄的样子。',
    props: { hero: '🍑', color: 'yellow', goal: 3 },
    templateFallback: false
  },
  {
    char: '枣', unit: 'u24', theme: 'food',
    template: 'rain-catch', interaction: 'drag',
    narration: '摇一摇枣树，拿篮子接住红枣。',
    props: { hero: '🌳', items: ['🔴', '🔴', '🔴'], tool: '🧺', goal: 3 },
    templateFallback: false
  },
  {
    char: '青', unit: 'u24', theme: 'color',
    template: 'color-fill', interaction: 'tap',
    narration: '把竹子涂得青青的，很好看。',
    props: { hero: '🎋', color: 'green', goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
