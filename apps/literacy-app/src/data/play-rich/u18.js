/**
 * 富互动 play 分片 u18 —— 这一单元的 18 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u18'

export const UNIT_RICH_PLAYS = [
  {
    char: '脸', unit: 'u18', theme: 'body',
    template: 'scene-poke', interaction: 'tap',
    narration: '洗脸啦，点点脸上都有什么。',
    props: { hero: '😊', items: ['👁️', '👃', '👄'], goal: 3 },
    templateFallback: false
  },
  {
    char: '眼', unit: 'u18', theme: 'body',
    template: 'tap-reveal', interaction: 'tap',
    narration: '眨眨眼睛，睁开看看世界。',
    props: { hero: '👁️', items: ['👀', '👁️', '👁️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '鼻', unit: 'u18', theme: 'body',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '用鼻子闻一闻，哪个最香。',
    props: { hero: '👃', target: '🌸', decoys: ['🧦', '🗑️', '🐟'], goal: 1 },
    templateFallback: false
  },
  {
    char: '嘴', unit: 'u18', theme: 'body',
    template: 'sound-tap', interaction: 'tap',
    narration: '张开嘴巴，啊——',
    props: { hero: '👄', sound: '啊', goal: 3 },
    templateFallback: false
  },
  {
    char: '脚', unit: 'u18', theme: 'body',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '小脚丫左一步右一步往前走。',
    props: { hero: '🦶', dir: 'right', goal: 4 },
    templateFallback: false
  },
  {
    char: '腿', unit: 'u18', theme: 'body',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '抬起腿，跨过小水坑。',
    props: { hero: '🦵', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '背', unit: 'u18', theme: 'body',
    template: 'drag-parts', interaction: 'drag',
    narration: '把书包背到背上，出发上学。',
    props: { hero: '🎒', parts: ['🎒', '🧒'], goal: 2 },
    templateFallback: false
  },
  {
    char: '肚', unit: 'u18', theme: 'body',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '吃饱啦，肚子圆鼓鼓的。',
    props: { hero: '🫄', items: ['🍎', '🍞', '🍚'], goal: 3 },
    templateFallback: false
  },
  {
    char: '发', unit: 'u18', theme: 'body',
    template: 'trace-path', interaction: 'drag',
    narration: '梳一梳头发，梳得顺顺的。',
    props: { hero: '💇', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '指', unit: 'u18', theme: 'body',
    template: 'count-tap', interaction: 'tap',
    narration: '一根一根数手指，一共五根。',
    props: { hero: '👆', items: ['👆', '👆', '👆', '👆', '👆'], goal: 5 },
    templateFallback: false
  },
  {
    char: '肩', unit: 'u18', theme: 'body',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '耸耸肩，肩膀上下动一动。',
    props: { hero: '🙆', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '身', unit: 'u18', theme: 'body',
    template: 'scene-poke', interaction: 'tap',
    narration: '从头到脚，都是我的身体。',
    props: { hero: '🧍', items: ['🙂', '🫄', '🦶'], goal: 3 },
    templateFallback: false
  },
  {
    char: '体', unit: 'u18', theme: 'body',
    template: 'scene-poke', interaction: 'tap',
    narration: '做做运动，身体会更棒。',
    props: { hero: '💪', items: ['🏃', '🤸', '🏀'], goal: 3 },
    templateFallback: false
  },
  {
    char: '皮', unit: 'u18', theme: 'body',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '剥开外面的皮，才吃得到里面。',
    props: { hero: '🍌', items: ['🍌', '🍊', '🥔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '骨', unit: 'u18', theme: 'body',
    template: 'drag-parts', interaction: 'drag',
    narration: '把小骨头一根一根拼成骨架。',
    props: { hero: '🦴', parts: ['🦴', '🦴', '🦴'], goal: 3 },
    templateFallback: false
  },
  {
    char: '毛', unit: 'u18', theme: 'body',
    template: 'tap-reveal', interaction: 'tap',
    narration: '摸摸小动物身上软软的毛。',
    props: { hero: '🧶', items: ['🐑', '🐱', '🐰'], goal: 3 },
    templateFallback: false
  },
  {
    char: '血', unit: 'u18', theme: 'body',
    template: 'tap-reveal', interaction: 'tap',
    narration: '破了个小口子，贴上创可贴。',
    props: { hero: '🩸', items: ['🩹', '🩹'], goal: 2 },
    templateFallback: false
  },
  {
    char: '汗', unit: 'u18', theme: 'body',
    template: 'rain-catch', interaction: 'drag',
    narration: '跑得好热，汗珠掉下来，快擦掉。',
    props: { hero: '💦', items: ['💧', '💧', '💧'], tool: '🧻', goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
