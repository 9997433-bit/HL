/**
 * 富互动 play 分片 u4 —— 这一单元的 13 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u4'

export const UNIT_RICH_PLAYS = [
  {
    char: '是', unit: 'u4', theme: 'word',
    template: 'sort-buckets', interaction: 'drag',
    narration: '说得对点是，说错了点不是。',
    props: { hero: '✅', items: [{ item: '鱼会游泳', bucket: '是' }, { item: '鸟会飞', bucket: '是' }, { item: '大象很小', bucket: '不是' }, { item: '火是凉的', bucket: '不是' }], buckets: [{ label: '是', emoji: '✅' }, { label: '不是', emoji: '❌' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '有', unit: 'u4', theme: 'word',
    template: 'tap-reveal', interaction: 'tap',
    narration: '口袋里有什么？点开看看你的宝贝。',
    props: { hero: '🎁', items: ['🍬', '🧸', '🔑'], goal: 3 },
    templateFallback: false
  },
  {
    char: '的', unit: 'u4', theme: 'word',
    template: 'pair-match', interaction: 'drag',
    narration: '这是谁的？把东西送回主人手里。',
    props: { hero: '🔗', pairs: [{ a: '🐶', b: '🦴' }, { a: '👶', b: '🍼' }, { a: '🐦', b: '🪹' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '看', unit: 'u4', theme: 'body',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '睁大眼睛看一看，找出躲起来的猫。',
    props: { hero: '👀', target: '🐱', decoys: ['🌳', '🌸', '🪨'], goal: 1 },
    templateFallback: false
  },
  {
    char: '在', unit: 'u4', theme: 'place',
    template: 'scene-poke', interaction: 'tap',
    narration: '小猫在哪里？在桌上、门口、家里。',
    props: { hero: '🐱', items: ['🪑', '🚪', '🏠'], goal: 3 },
    templateFallback: false
  },
  {
    char: '来', unit: 'u4', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '招招手，把小狗叫到身边来。',
    props: { hero: '🐶', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '去', unit: 'u4', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '挥挥手，送小车开到远远的地方去。',
    props: { hero: '🚗', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '会', unit: 'u4', theme: 'word',
    template: 'tap-reveal', interaction: 'tap',
    narration: '点点看谁会做这件事，会就亮起来。',
    props: { hero: '🌟', items: ['🐟', '🐦', '🐰'], goal: 3 },
    templateFallback: false
  },
  {
    char: '说', unit: 'u4', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '嘴巴一张一合，说出「你好」。',
    props: { hero: '🗣️', sound: '你好', goal: 3 },
    templateFallback: false
  },
  {
    char: '也', unit: 'u4', theme: 'word',
    template: 'pair-match', interaction: 'drag',
    narration: '他有的我也有，配成一样的一对。',
    props: { hero: '➕', pairs: [{ a: '🍎', b: '🍎' }, { a: '🎈', b: '🎈' }, { a: '🧸', b: '🧸' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '了', unit: 'u4', theme: 'word',
    template: 'count-tap', interaction: 'tap',
    narration: '做完一件点一下，做完了！',
    props: { hero: '🏁', items: ['✅', '✅', '✅'], goal: 3 },
    templateFallback: false
  },
  {
    char: '很', unit: 'u4', theme: 'word',
    template: 'grow-tap', interaction: 'tap',
    narration: '越点越开心，从开心变成很开心。',
    props: { hero: '‼️', stages: ['🙂', '😀', '😆'], goal: 3 },
    templateFallback: false
  },
  {
    char: '和', unit: 'u4', theme: 'word',
    template: 'pair-match', interaction: 'drag',
    narration: '你和我，把两个人拉到一起。',
    props: { hero: '🤝', pairs: [{ a: '🧒', b: '🧒' }, { a: '🐱', b: '🐶' }, { a: '🍎', b: '🍐' }], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
