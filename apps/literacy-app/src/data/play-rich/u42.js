/**
 * 富互动 play 分片 u42 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u42'

export const UNIT_RICH_PLAYS = [
  {
    char: '买', unit: 'u42', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '挑三样放进篮子，买回家。',
    props: { hero: '🛍️', items: ['🍎', '🥛', '🍞'], goal: 3 },
    templateFallback: false
  },
  {
    char: '卖', unit: 'u42', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把货递出去，东西就卖掉了。',
    props: { hero: '🏷️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '价', unit: 'u42', theme: 'object',
    template: 'pair-match', interaction: 'drag',
    narration: '每样东西标个价，连一连。',
    props: { hero: '💲', pairs: [{ a: '🍎', b: '1️⃣' }, { a: '🍞', b: '2️⃣' }, { a: '🎂', b: '3️⃣' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '钱', unit: 'u42', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '数数钱包里有几个硬币。',
    props: { hero: '💰', items: ['🪙', '🪙', '🪙', '🪙'], goal: 4 },
    templateFallback: false
  },
  {
    char: '币', unit: 'u42', theme: 'object',
    template: 'sort-buckets', interaction: 'drag',
    narration: '纸币放钱包，硬币投存钱罐。',
    props: { hero: '🪙', items: [{ item: '💵', bucket: '钱包' }, { item: '💶', bucket: '钱包' }, { item: '🪙', bucket: '罐子' }, { item: '🔘', bucket: '罐子' }], buckets: [{ label: '钱包', emoji: '👛' }, { label: '罐子', emoji: '🏦' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '贵', unit: 'u42', theme: 'object',
    template: 'sort-buckets', interaction: 'drag',
    narration: '贵的摆左边，便宜的摆右边。',
    props: { hero: '💎', items: [{ item: '💍', bucket: '贵' }, { item: '⌚', bucket: '贵' }, { item: '🍬', bucket: '便宜' }, { item: '✏️', bucket: '便宜' }], buckets: [{ label: '贵', emoji: '💎' }, { label: '便宜', emoji: '🪙' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '便', unit: 'u42', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '走这条近路，回家更方便。',
    props: { hero: '🚶', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '宜', unit: 'u42', theme: 'object',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪样最便宜？挑出小价钱的。',
    props: { hero: '🏷️', target: '🍬', decoys: ['💎', '⌚', '📱'], goal: 1 },
    templateFallback: false
  },
  {
    char: '存', unit: 'u42', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '一枚一枚存进罐子，存五枚。',
    props: { hero: '🏦', items: ['🪙', '🪙', '🪙', '🪙', '🪙'], goal: 5 },
    templateFallback: false
  },
  {
    char: '取', unit: 'u42', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '从罐子里取出钱，往外拿。',
    props: { hero: '🤲', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '零', unit: 'u42', theme: 'number',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '三块都吃光，盘子里剩零个。',
    props: { hero: '0️⃣', items: ['🍪', '🍪', '🍪'], goal: 3 },
    templateFallback: false
  },
  {
    char: '购', unit: 'u42', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '购物车里放了啥？点点看。',
    props: { hero: '🛒', items: ['🥕', '🍚', '🧴'], goal: 3 },
    templateFallback: false
  },
  {
    char: '售', unit: 'u42', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '售货窗口一开，一样样端出来。',
    props: { hero: '🧾', items: ['🍦', '🥤', '🌭'], goal: 3 },
    templateFallback: false
  },
  {
    char: '贸', unit: 'u42', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '你的换我的，两边贸一贸。',
    props: { hero: '🤝', pairs: [{ a: '🍎', b: '🍌' }, { a: '🐟', b: '🥕' }, { a: '🧶', b: '🪵' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '商', unit: 'u42', theme: 'place',
    template: 'scene-poke', interaction: 'tap',
    narration: '小商店里有什么？挨个点亮。',
    props: { hero: '🏪', items: ['🍙', '🥤', '🍫'], goal: 3 },
    templateFallback: false
  },
  {
    char: '余', unit: 'u42', theme: 'number',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '分完还剩两个，这就叫余。',
    props: { hero: '🍡', items: ['🍡', '🍡'], goal: 2 },
    templateFallback: false
  },
  {
    char: '除', unit: 'u42', theme: 'number',
    template: 'sort-buckets', interaction: 'drag',
    narration: '四块饼分两盘，一盘放两块。',
    props: { hero: '➗', items: [{ item: '🍪', bucket: '左盘' }, { item: '🍪', bucket: '左盘' }, { item: '🍪', bucket: '右盘' }, { item: '🍪', bucket: '右盘' }], buckets: [{ label: '左盘', emoji: '🟠' }, { label: '右盘', emoji: '🔵' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '均', unit: 'u42', theme: 'number',
    template: 'sort-buckets', interaction: 'drag',
    narration: '两个小朋友分糖，要分得均。',
    props: { hero: '⚖️', items: [{ item: '🍬', bucket: '你的' }, { item: '🍬', bucket: '你的' }, { item: '🍭', bucket: '我的' }, { item: '🍭', bucket: '我的' }], buckets: [{ label: '你的', emoji: '🧒' }, { label: '我的', emoji: '🧑' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '斤', unit: 'u42', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '一斤一斤称过去，称满三斤。',
    props: { hero: '⚖️', items: ['⚖️', '⚖️', '⚖️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '吨', unit: 'u42', theme: 'object',
    template: 'grow-tap', interaction: 'tap',
    narration: '一袋、一车、一吨，越来越重。',
    props: { hero: '🚛', stages: ['🎒', '🚚', '🏔️'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
