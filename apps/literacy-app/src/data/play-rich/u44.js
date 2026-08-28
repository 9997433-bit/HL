/**
 * 富互动 play 分片 u44 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u44'

export const UNIT_RICH_PLAYS = [
  {
    char: '龙', unit: 'u44', theme: 'animal',
    template: 'grow-tap', interaction: 'tap',
    narration: '龙的身子一节一节长起来。',
    props: { hero: '🐉', stages: ['🐍', '🐉', '☁️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '舟', unit: 'u44', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '划起龙舟，一齐往前冲。',
    props: { hero: '🛶', dir: 'right', goal: 4 },
    templateFallback: false
  },
  {
    char: '粽', unit: 'u44', theme: 'food',
    template: 'drag-parts', interaction: 'drag',
    narration: '粽叶包住米，扎上一根线。',
    props: { hero: '🍙', parts: ['🍃', '🍚', '🧵'], goal: 3 },
    templateFallback: false
  },
  {
    char: '团', unit: 'u44', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '一家人团在一起，两两牵手。',
    props: { hero: '🧶', pairs: [{ a: '👦', b: '👧' }, { a: '👨', b: '👩' }, { a: '👴', b: '👵' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '拜', unit: 'u44', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '双手作揖，往下拜一拜。',
    props: { hero: '🙇', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '贺', unit: 'u44', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '拉响三个礼炮，恭贺新年。',
    props: { hero: '🎉', items: ['🎉', '🎊', '🎇'], goal: 3 },
    templateFallback: false
  },
  {
    char: '祝', unit: 'u44', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '吹灭蜡烛，祝你生日快乐。',
    props: { hero: '🎂', items: ['🕯️', '🕯️', '🕯️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '福', unit: 'u44', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把福字倒过来贴，福到了。',
    props: { hero: '🧧', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '喜', unit: 'u44', theme: 'feeling',
    template: 'morph-story', interaction: 'sequence',
    narration: '嘴角往上翘，喜得笑出声。',
    props: { hero: '😄', stages: ['😐', '🙂', '😄'], goal: 3 },
    templateFallback: false
  },
  {
    char: '庆', unit: 'u44', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '放烟花庆祝，一朵朵点开。',
    props: { hero: '🎆', items: ['🎆', '🎇', '✨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '礼', unit: 'u44', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '拆开礼物，看看里面是啥。',
    props: { hero: '🎁', items: ['🧸', '🚗', '📕'], goal: 3 },
    templateFallback: false
  },
  {
    char: '貌', unit: 'u44', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '有礼貌的是哪个？找出笑脸。',
    props: { hero: '🙋', target: '🙋', decoys: ['😠', '😝', '😴'], goal: 1 },
    templateFallback: false
  },
  {
    char: '谢', unit: 'u44', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '收下礼物要说：谢谢你。',
    props: { hero: '🙏', sound: '谢谢', goal: 3 },
    templateFallback: false
  },
  {
    char: '请', unit: 'u44', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '想要就先说：请给我。',
    props: { hero: '🤲', sound: '请您', goal: 3 },
    templateFallback: false
  },
  {
    char: '敬', unit: 'u44', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '抬起小手，敬个礼。',
    props: { hero: '🫡', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '孝', unit: 'u44', theme: 'family',
    template: 'scene-poke', interaction: 'tap',
    narration: '给爷爷奶奶做点事，这叫孝。',
    props: { hero: '👴', items: ['🍵', '🪑', '👐'], goal: 3 },
    templateFallback: false
  },
  {
    char: '诚', unit: 'u44', theme: 'feeling',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '说实话的那张脸，找出来。',
    props: { hero: '💯', target: '💯', decoys: ['🤥', '😶', '🙄'], goal: 1 },
    templateFallback: false
  },
  {
    char: '实', unit: 'u44', theme: 'feeling',
    template: 'grow-tap', interaction: 'tap',
    narration: '一句实话，心里踏踏实实。',
    props: { hero: '🧱', stages: ['❓', '💬', '🧱'], goal: 3 },
    templateFallback: false
  },
  {
    char: '勇', unit: 'u44', theme: 'feeling',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '挺起胸膛往前走，真勇敢。',
    props: { hero: '🦁', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '敢', unit: 'u44', theme: 'feeling',
    template: 'count-tap', interaction: 'tap',
    narration: '举手回答三次，越举越敢。',
    props: { hero: '✊', items: ['✊', '✊', '✊'], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
