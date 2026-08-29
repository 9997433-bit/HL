/**
 * 富互动 play 分片 u98 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u98'

export const UNIT_RICH_PLAYS = [
  {
    char: '结', unit: 'u98', theme: 'food',
    template: 'sort-buckets', interaction: 'drag',
    narration: '鞋带打个结，不会散。',
    props: { hero: '🎀', items: [{ item: '🎀', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '绕', unit: 'u98', theme: 'action',
    template: 'color-fill', interaction: 'tap',
    narration: '绕着树转三圈，回来。',
    props: { hero: '🔄', color: 'orange', goal: 3 },
    templateFallback: false
  },
  {
    char: '骄', unit: 'u98', theme: 'feeling',
    template: 'rain-catch', interaction: 'drag',
    narration: '别骄傲，谦虚点点头。',
    props: { hero: '😤', items: ['🌙', '🎈', '🧩'], tool: '😤', goal: 3 },
    templateFallback: false
  },
  {
    char: '绘', unit: 'u98', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '画笔描绘出彩虹。',
    props: { hero: '🎨', items: ['☀️', '🎁', '🔔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '骆', unit: 'u98', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '骆驼队走过，跟着脚印。',
    props: { hero: '🐫', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '络', unit: 'u98', theme: 'number',
    template: 'drag-parts', interaction: 'drag',
    narration: '网线络成网，连上结点。',
    props: { hero: '🍃', parts: ['🎈', '📦', '🍃'], goal: 3 },
    templateFallback: false
  },
  {
    char: '绝', unit: 'u98', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '绳子绝断了，接回去。',
    props: { hero: '🚫', items: ['🎁', '🧩', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '统', unit: 'u98', theme: 'number',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '统一穿红衣，排成一队。',
    props: { hero: '🧧', target: '🧧', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '耗', unit: 'u98', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '电能耗光了，充充电。',
    props: { hero: '⏳', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '耙', unit: 'u98', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '用耙子耙地，弄松泥土。',
    props: { hero: '🌾', parts: ['🧩', '🌱', '🌾'], goal: 3 },
    templateFallback: false
  },
  {
    char: '艳', unit: 'u98', theme: 'color',
    template: 'color-fill', interaction: 'tap',
    narration: '花色鲜艳，涂上大红。',
    props: { hero: '🌺', color: 'orange', goal: 3 },
    templateFallback: false
  },
  {
    char: '泰', unit: 'u98', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '登上泰山，插上一面旗。',
    props: { hero: '⛰️', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '秦', unit: 'u98', theme: 'number',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '秦朝兵马俑，点亮盔甲。',
    props: { hero: '🏯', items: ['🏯', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '珠', unit: 'u98', theme: 'shape',
    template: 'sound-tap', interaction: 'tap',
    narration: '珍珠滚进贝壳，捡回来。',
    props: { hero: '📿', sound: '哗哗', goal: 3 },
    templateFallback: false
  },
  {
    char: '素', unit: 'u98', theme: 'food',
    template: 'color-fill', interaction: 'tap',
    narration: '素菜盘子，别放肉进去。',
    props: { hero: '🥗', color: 'violet', goal: 3 },
    templateFallback: false
  },
  {
    char: '顽', unit: 'u98', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '顽皮猴子，抓它的尾巴。',
    props: { hero: '🐒', pairs: [{ a: '🐒', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '🐒' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '捞', unit: 'u98', theme: 'animal',
    template: 'sort-buckets', interaction: 'drag',
    narration: '从水里捞起皮球。',
    props: { hero: '🎣', items: [{ item: '🎣', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '栽', unit: 'u98', theme: 'nature',
    template: 'color-fill', interaction: 'tap',
    narration: '把树苗栽进土坑。',
    props: { hero: '🌳', color: 'khaki', goal: 3 },
    templateFallback: false
  },
  {
    char: '捕', unit: 'u98', theme: 'animal',
    template: 'rain-catch', interaction: 'drag',
    narration: '撒网捕捉小鱼，收网。',
    props: { hero: '🕸️', items: ['🌙', '🎈', '🧩'], tool: '🕸️', goal: 3 },
    templateFallback: false
  },
  {
    char: '振', unit: 'u98', theme: 'school',
    template: 'tap-reveal', interaction: 'tap',
    narration: '翅膀振动，小鸟飞起。',
    props: { hero: '🕊️', items: ['☀️', '🎁', '🔔'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
