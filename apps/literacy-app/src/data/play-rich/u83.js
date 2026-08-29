/**
 * 富互动 play 分片 u83 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u83'

export const UNIT_RICH_PLAYS = [
  {
    char: '咕', unit: 'u83', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '肚子咕咕叫，该吃饭了。',
    props: { hero: '🍽️', sound: '咚咚', goal: 3 },
    templateFallback: false
  },
  {
    char: '昌', unit: 'u83', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '小城昌盛了，灯火通明。',
    props: { hero: '🌞', stages: ['🎈', '🌞', '🌱'], goal: 3 },
    templateFallback: false
  },
  {
    char: '呵', unit: 'u83', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '呵一口气，镜面起雾。',
    props: { hero: '🤗', sound: '叮叮', goal: 3 },
    templateFallback: false
  },
  {
    char: '畅', unit: 'u83', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '书读得流畅，一页页翻。',
    props: { hero: '📖', target: '📖', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '易', unit: 'u83', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '这道题很容易，点对勾。',
    props: { hero: '👌', pairs: [{ a: '👌', b: '📦' }, { a: '🎯', b: '💧' }, { a: '📦', b: '👌' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '咧', unit: 'u83', theme: 'number',
    template: 'grow-tap', interaction: 'tap',
    narration: '咧开嘴笑，露出小白牙。',
    props: { hero: '😁', stages: ['🧩', '😁', '🔥'], goal: 3 },
    templateFallback: false
  },
  {
    char: '昂', unit: 'u83', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '昂起头，挺胸往前走。',
    props: { hero: '🦢', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '典', unit: 'u83', theme: 'school',
    template: 'scene-poke', interaction: 'tap',
    narration: '翻开字典，查这个字。',
    props: { hero: '📖', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '固', unit: 'u83', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '螺丝拧牢固，不会晃。',
    props: { hero: '🧱', items: ['🧱', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '忠', unit: 'u83', theme: 'body',
    template: 'sound-tap', interaction: 'tap',
    narration: '小狗忠诚，一直跟着你。',
    props: { hero: '🐕', sound: '呼呼', goal: 3 },
    templateFallback: false
  },
  {
    char: '咐', unit: 'u83', theme: 'action',
    template: 'morph-story', interaction: 'sequence',
    narration: '妈妈吩咐三件事，记牢。',
    props: { hero: '🗣️', stages: ['🪵', '🗣️', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '呼', unit: 'u83', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '深深呼一口气，再吸气。',
    props: { hero: '💨', pairs: [{ a: '💨', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '💨' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '鸣', unit: 'u83', theme: 'animal',
    template: 'sound-tap', interaction: 'tap',
    narration: '小鸟鸣叫，跟着学三声。',
    props: { hero: '🐦', sound: '咚咚', goal: 3 },
    templateFallback: false
  },
  {
    char: '咏', unit: 'u83', theme: 'school',
    template: 'sound-tap', interaction: 'tap',
    narration: '歌咏会上，唱出旋律。',
    props: { hero: '🎵', sound: '哗哗', goal: 3 },
    templateFallback: false
  },
  {
    char: '呢', unit: 'u83', theme: 'school',
    template: 'rain-catch', interaction: 'drag',
    narration: '好呢——点点头答应。',
    props: { hero: '❓', items: ['🌙', '🎈', '🧩'], tool: '❓', goal: 3 },
    templateFallback: false
  },
  {
    char: '咖', unit: 'u83', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '冲一杯咖啡，闻闻香气。',
    props: { hero: '☕', items: ['☀️', '🎁', '🔔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '帖', unit: 'u83', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把画帖平，服服帖帖。',
    props: { hero: '📄', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '帜', unit: 'u83', theme: 'object',
    template: 'count-tap', interaction: 'tap',
    narration: '举起旗帜，迎风飘扬。',
    props: { hero: '🚩', items: ['🚩', '🚩', '🚩', '🚩', '🚩'], goal: 5 },
    templateFallback: false
  },
  {
    char: '帕', unit: 'u83', theme: 'body',
    template: 'tap-reveal', interaction: 'tap',
    narration: '用手帕擦擦汗。',
    props: { hero: '🧻', items: ['🎁', '🧩', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '凯', unit: 'u83', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '打胜仗凯旋，戴上花环。',
    props: { hero: '🏆', target: '🏆', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
