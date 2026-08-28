/**
 * 富互动 play 分片 u46 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u46'

export const UNIT_RICH_PLAYS = [
  {
    char: '荒', unit: 'u46', theme: 'nature',
    template: 'morph-story', interaction: 'sequence',
    narration: '草都枯了，地变得荒荒的。',
    props: { hero: '🏜️', stages: ['🌳', '🌾', '🏜️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '漠', unit: 'u46', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '骆驼在沙漠里，一步步往前。',
    props: { hero: '🐪', dir: 'right', goal: 4 },
    templateFallback: false
  },
  {
    char: '湾', unit: 'u46', theme: 'nature',
    template: 'trace-path', interaction: 'drag',
    narration: '海水拐个弯，围出一个湾。',
    props: { hero: '🌊', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '滩', unit: 'u46', theme: 'place',
    template: 'scene-poke', interaction: 'tap',
    narration: '沙滩上捡到了什么？点一点。',
    props: { hero: '🏝️', items: ['🐚', '⭐', '🦀'], goal: 3 },
    templateFallback: false
  },
  {
    char: '尘', unit: 'u46', theme: 'nature',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '灰尘飘啊飘，一粒粒吹掉。',
    props: { hero: '🌫️', items: ['🌫️', '🌫️', '🌫️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '灰', unit: 'u46', theme: 'color',
    template: 'color-fill', interaction: 'tap',
    narration: '把小石头涂成灰灰的颜色。',
    props: { hero: '🪨', color: 'gray', goal: 3 },
    templateFallback: false
  },
  {
    char: '烟', unit: 'u46', theme: 'weather',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '烟囱里的烟，直直往上飘。',
    props: { hero: '💨', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '焰', unit: 'u46', theme: 'weather',
    template: 'grow-tap', interaction: 'tap',
    narration: '添把柴，火焰蹿得老高。',
    props: { hero: '🔥', stages: ['🕯️', '🔥', '🌋'], goal: 3 },
    templateFallback: false
  },
  {
    char: '深', unit: 'u46', theme: 'shape',
    template: 'grow-tap', interaction: 'tap',
    narration: '水一层比一层深，别再走了。',
    props: { hero: '🕳️', stages: ['🥣', '🛁', '🕳️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '浅', unit: 'u46', theme: 'shape',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪个水最浅？挑出最矮的。',
    props: { hero: '🥣', target: '🥣', decoys: ['🛁', '🌊', '🕳️'], goal: 1 },
    templateFallback: false
  },
  {
    char: '宽', unit: 'u46', theme: 'shape',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把路往两边拉，越拉越宽。',
    props: { hero: '↔️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '窄', unit: 'u46', theme: 'place',
    template: 'trace-path', interaction: 'drag',
    narration: '小路很窄，侧着身子过去。',
    props: { hero: '🚧', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '厚', unit: 'u46', theme: 'object',
    template: 'drag-parts', interaction: 'drag',
    narration: '一本压一本，摞得厚厚的。',
    props: { hero: '📚', parts: ['📕', '📗', '📘'], goal: 3 },
    templateFallback: false
  },
  {
    char: '薄', unit: 'u46', theme: 'object',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '薄薄一张纸，一吹就飞。',
    props: { hero: '📄', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '硬', unit: 'u46', theme: 'object',
    template: 'sort-buckets', interaction: 'drag',
    narration: '硬的敲得响，软的按得下。',
    props: { hero: '🪨', items: [{ item: '🥥', bucket: '硬' }, { item: '🧱', bucket: '硬' }, { item: '🍞', bucket: '软' }, { item: '☁️', bucket: '软' }], buckets: [{ label: '硬', emoji: '🪨' }, { label: '软', emoji: '🧸' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '软', unit: 'u46', theme: 'object',
    template: 'color-fill', interaction: 'tap',
    narration: '软软的小熊，涂上暖黄色。',
    props: { hero: '🧸', color: 'gold', goal: 3 },
    templateFallback: false
  },
  {
    char: '强', unit: 'u46', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '每天练一练，胳膊越来越强。',
    props: { hero: '💪', stages: ['🦴', '💪', '🏋️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '弱', unit: 'u46', theme: 'nature',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '小苗还弱，风一吹就倒。',
    props: { hero: '🍃', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '新', unit: 'u46', theme: 'object',
    template: 'morph-story', interaction: 'sequence',
    narration: '旧本子换成新本子，真干净。',
    props: { hero: '🆕', stages: ['🗞️', '📄', '📘'], goal: 3 },
    templateFallback: false
  },
  {
    char: '旧', unit: 'u46', theme: 'object',
    template: 'color-fill', interaction: 'tap',
    narration: '旧报纸放久了，变成黄黄的。',
    props: { hero: '🗞️', color: 'khaki', goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
