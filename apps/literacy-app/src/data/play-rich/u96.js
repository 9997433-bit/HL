/**
 * 富互动 play 分片 u96 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u96'

export const UNIT_RICH_PLAYS = [
  {
    char: '姿', unit: 'u96', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '摆个舞蹈姿势，定格。',
    props: { hero: '💃', stages: ['📦', '💃', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '帝', unit: 'u96', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '皇帝出巡，走过长廊。',
    props: { hero: '👑', parts: ['🧩', '🌱', '👑'], goal: 3 },
    templateFallback: false
  },
  {
    char: '施', unit: 'u96', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '工地施工，吊起砖块。',
    props: { hero: '🏗️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '闻', unit: 'u96', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '用鼻子闻一闻，是花香。',
    props: { hero: '👃', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '阁', unit: 'u96', theme: 'number',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '爬上阁楼，打开小窗。',
    props: { hero: '🏯', items: ['🏯', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '美', unit: 'u96', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '画出美丽的花，涂上色。',
    props: { hero: '🌸', sound: '哗哗', goal: 3 },
    templateFallback: false
  },
  {
    char: '类', unit: 'u96', theme: 'number',
    template: 'morph-story', interaction: 'sequence',
    narration: '按种类分，同类放一起。',
    props: { hero: '🗂️', stages: ['🪵', '🗂️', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '籽', unit: 'u96', theme: 'food',
    template: 'pair-match', interaction: 'drag',
    narration: '把籽撒进土里，等发芽。',
    props: { hero: '🌻', pairs: [{ a: '🌻', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '🌻' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '炼', unit: 'u96', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '炉火炼铁，越炼越亮。',
    props: { hero: '🔥', items: [{ item: '🔥', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '烂', unit: 'u96', theme: 'action',
    template: 'color-fill', interaction: 'tap',
    narration: '烂苹果扔掉，留好的。',
    props: { hero: '🍎', color: 'violet', goal: 3 },
    templateFallback: false
  },
  {
    char: '剃', unit: 'u96', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '理发剃平，梳子梳齐。',
    props: { hero: '✂️', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '洼', unit: 'u96', theme: 'shape',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '水洼里有倒影，看一看。',
    props: { hero: '🕳️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '活', unit: 'u96', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '小鱼活蹦乱跳，喂饲料。',
    props: { hero: '🌱', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '派', unit: 'u96', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '派送快递，送到门口。',
    props: { hero: '📨', pairs: [{ a: '📨', b: '🎈' }, { a: '📦', b: '🌱' }, { a: '🎈', b: '📨' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '济', unit: 'u96', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '救济物资，分给大家。',
    props: { hero: '🤝', items: ['🎁', '🧩', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '浓', unit: 'u96', theme: 'weather',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '雾气很浓，拨开看路。',
    props: { hero: '🌫️', target: '🌫️', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '津', unit: 'u96', theme: 'body',
    template: 'grow-tap', interaction: 'tap',
    narration: '吃得津津有味，再咬一口。',
    props: { hero: '😋', stages: ['📦', '😋', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '恒', unit: 'u96', theme: 'body',
    template: 'grow-tap', interaction: 'tap',
    narration: '恒心坚持，每天练三下。',
    props: { hero: '♾️', stages: ['🧩', '♾️', '🔥'], goal: 3 },
    templateFallback: false
  },
  {
    char: '恰', unit: 'u96', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '恰好合适，不大不小。',
    props: { hero: '👌', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '恨', unit: 'u96', theme: 'feeling',
    template: 'scene-poke', interaction: 'tap',
    narration: '把悔恨揉掉，重新开始。',
    props: { hero: '😔', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
