/**
 * 富互动 play 分片 u61 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u61'

export const UNIT_RICH_PLAYS = [
  {
    char: '仁', unit: 'u61', theme: 'feeling',
    template: 'pair-match', interaction: 'drag',
    narration: '待人有爱心，把心配成对。',
    props: { hero: '❤️', pairs: [{ a: '❤️', b: '❤️' }, { a: '💛', b: '💛' }, { a: '💙', b: '💙' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '仅', unit: 'u61', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '仅仅一个就够了，只点一下。',
    props: { hero: '1️⃣', items: ['🍬'], goal: 1 },
    templateFallback: false
  },
  {
    char: '反', unit: 'u61', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '翻过来，看看反面是什么。',
    props: { hero: '🔄', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '介', unit: 'u61', theme: 'family',
    template: 'tap-reveal', interaction: 'tap',
    narration: '我来介绍新朋友，一个个揭。',
    props: { hero: '🙋', items: ['🐶', '🐱', '🐰'], goal: 3 },
    templateFallback: false
  },
  {
    char: '乏', unit: 'u61', theme: 'feeling',
    template: 'morph-story', interaction: 'sequence',
    narration: '玩累了，人一下子没了力气。',
    props: { hero: '😪', stages: ['🏃', '🚶', '😪'], goal: 3 },
    templateFallback: false
  },
  {
    char: '氏', unit: 'u61', theme: 'family',
    template: 'drag-parts', interaction: 'drag',
    narration: '一家人姓一个姓，凑成一家。',
    props: { hero: '👪', parts: ['👨', '👩', '👧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '勿', unit: 'u61', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '这里勿动，找出禁止的牌子。',
    props: { hero: '🚫', target: '🚫', decoys: ['✅', '➡️', '🔵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '欠', unit: 'u61', theme: 'body',
    template: 'grow-tap', interaction: 'tap',
    narration: '困了打个哈欠，嘴越张越大。',
    props: { hero: '🥱', stages: ['🙂', '😯', '🥱'], goal: 3 },
    templateFallback: false
  },
  {
    char: '丹', unit: 'u61', theme: 'color',
    template: 'color-fill', interaction: 'tap',
    narration: '丹就是红，把花瓣涂红透。',
    props: { hero: '🌺', color: '丹红', goal: 3 },
    templateFallback: false
  },
  {
    char: '匀', unit: 'u61', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '分得匀匀的：你两个我两个。',
    props: { hero: '⚖️', items: [{ item: '🍬', bucket: '你的' }, { item: '🍭', bucket: '你的' }, { item: '🍫', bucket: '我的' }, { item: '🍪', bucket: '我的' }], buckets: [{ label: '你的', emoji: '🙋' }, { label: '我的', emoji: '🙆' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '乌', unit: 'u61', theme: 'animal',
    template: 'color-fill', interaction: 'tap',
    narration: '乌鸦黑黑的，涂成墨黑色。',
    props: { hero: '🐦‍⬛', color: '黑', goal: 3 },
    templateFallback: false
  },
  {
    char: '勾', unit: 'u61', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '笔尖往下一勾，画个小钩。',
    props: { hero: '✔️', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '凤', unit: 'u61', theme: 'animal',
    template: 'grow-tap', interaction: 'tap',
    narration: '凤凰抖抖尾巴，越来越美。',
    props: { hero: '🦚', stages: ['🐣', '🦜', '🦚'], goal: 3 },
    templateFallback: false
  },
  {
    char: '计', unit: 'u61', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '拨着算珠计一计，拨四下。',
    props: { hero: '🧮', items: ['🧮', '🧮', '🧮', '🧮'], goal: 4 },
    templateFallback: false
  },
  {
    char: '订', unit: 'u61', theme: 'school',
    template: 'drag-parts', interaction: 'drag',
    narration: '把纸订在一起，别上曲别针。',
    props: { hero: '📝', parts: ['📄', '📎'], goal: 2 },
    templateFallback: false
  },
  {
    char: '户', unit: 'u61', theme: 'place',
    template: 'tap-reveal', interaction: 'tap',
    narration: '一户一户问一声，看看谁在。',
    props: { hero: '🚪', items: ['👵', '🐕', '👶'], goal: 3 },
    templateFallback: false
  },
  {
    char: '引', unit: 'u61', theme: 'action',
    template: 'rain-catch', interaction: 'drag',
    narration: '磁石引着铁片，一片片吸住。',
    props: { hero: '🧲', items: ['📎', '🔩', '🔗'], tool: '🧲', goal: 3 },
    templateFallback: false
  },
  {
    char: '丑', unit: 'u61', theme: 'feeling',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '哪个小丑的鼻子最红？找出来。',
    props: { hero: '🤡', target: '🤡', decoys: ['😀', '😺', '🐷'], goal: 1 },
    templateFallback: false
  },
  {
    char: '巴', unit: 'u61', theme: 'body',
    template: 'sound-tap', interaction: 'tap',
    narration: '张开嘴巴，跟我念一声巴。',
    props: { hero: '👄', sound: '巴', goal: 3 },
    templateFallback: false
  },
  {
    char: '孔', unit: 'u61', theme: 'shape',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '一个个小孔，挨着戳穿它。',
    props: { hero: '🕳️', items: ['⚫', '⚫', '⚫'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
