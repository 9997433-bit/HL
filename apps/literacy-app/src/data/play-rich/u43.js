/**
 * 富互动 play 分片 u43 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u43'

export const UNIT_RICH_PLAYS = [
  {
    char: '信', unit: 'u43', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '写好的信折起来，放进信封。',
    props: { hero: '✉️', parts: ['📄', '✉️'], goal: 2 },
    templateFallback: false
  },
  {
    char: '封', unit: 'u43', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把封口往下一压，封好了。',
    props: { hero: '📩', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '寄', unit: 'u43', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '走到邮筒边，把信寄出去。',
    props: { hero: '📮', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '递', unit: 'u43', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '快递送到家，包裹配上门牌。',
    props: { hero: '📦', pairs: [{ a: '📦', b: '🏠' }, { a: '📮', b: '🏢' }, { a: '🚚', b: '🏪' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '址', unit: 'u43', theme: 'place',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '按地址找门牌，是哪一家？',
    props: { hero: '📍', target: '🏠', decoys: ['🌳', '🚗', '🐕'], goal: 1 },
    templateFallback: false
  },
  {
    char: '号', unit: 'u43', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '一号二号三号，数着门牌走。',
    props: { hero: '🔢', items: ['1️⃣', '2️⃣', '3️⃣'], goal: 3 },
    templateFallback: false
  },
  {
    char: '码', unit: 'u43', theme: 'number',
    template: 'tap-reveal', interaction: 'tap',
    narration: '密码有几个数字？点开看看。',
    props: { hero: '🔢', items: ['4️⃣', '5️⃣', '6️⃣'], goal: 3 },
    templateFallback: false
  },
  {
    char: '话', unit: 'u43', theme: 'word',
    template: 'sound-tap', interaction: 'tap',
    narration: '拿起电话说句话：喂喂喂。',
    props: { hero: '☎️', sound: '喂喂', goal: 3 },
    templateFallback: false
  },
  {
    char: '讯', unit: 'u43', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '讯号一格格往上冒，通了。',
    props: { hero: '📡', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '报', unit: 'u43', theme: 'object',
    template: 'scene-poke', interaction: 'tap',
    narration: '报纸上有啥新鲜事？点开读。',
    props: { hero: '📰', items: ['⚽', '🌦️', '🎬'], goal: 3 },
    templateFallback: false
  },
  {
    char: '刊', unit: 'u43', theme: 'object',
    template: 'count-tap', interaction: 'tap',
    narration: '一期一期的画刊，翻满四本。',
    props: { hero: '📖', items: ['📖', '📖', '📖', '📖'], goal: 4 },
    templateFallback: false
  },
  {
    char: '传', unit: 'u43', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '一个传一个，把话传下去。',
    props: { hero: '🔁', pairs: [{ a: '🧒', b: '🧒' }, { a: '🗣️', b: '👂' }, { a: '📨', b: '📬' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '联', unit: 'u43', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '把两节车厢联在一起。',
    props: { hero: '🔗', parts: ['🚃', '🚃'], goal: 2 },
    templateFallback: false
  },
  {
    char: '次', unit: 'u43', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '再来一次，一共跳三次。',
    props: { hero: '🔢', items: ['🦘', '🦘', '🦘'], goal: 3 },
    templateFallback: false
  },
  {
    char: '铁', unit: 'u43', theme: 'object',
    template: 'trace-path', interaction: 'drag',
    narration: '铁轨一直往前铺，跟着走。',
    props: { hero: '🛤️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '隧', unit: 'u43', theme: 'place',
    template: 'morph-story', interaction: 'sequence',
    narration: '山里挖开一条道，成了隧道。',
    props: { hero: '🚇', stages: ['⛰️', '🕳️', '🚇'], goal: 3 },
    templateFallback: false
  },
  {
    char: '主', unit: 'u43', theme: 'family',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '谁是这家的主人？找出来。',
    props: { hero: '👑', target: '👑', decoys: ['🐕', '🪑', '🌼'], goal: 1 },
    templateFallback: false
  },
  {
    char: '员', unit: 'u43', theme: 'school',
    template: 'count-tap', interaction: 'tap',
    narration: '队里有几个队员？数一数。',
    props: { hero: '🧑', items: ['🧑', '🧑', '🧑', '🧑'], goal: 4 },
    templateFallback: false
  },
  {
    char: '部', unit: 'u43', theme: 'shape',
    template: 'drag-parts', interaction: 'drag',
    narration: '把三个部件拼到一起。',
    props: { hero: '🧩', parts: ['🧩', '🧩', '🧩'], goal: 3 },
    templateFallback: false
  },
  {
    char: '导', unit: 'u43', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '导游在前面带路，跟上他。',
    props: { hero: '🧭', dir: 'right', goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
