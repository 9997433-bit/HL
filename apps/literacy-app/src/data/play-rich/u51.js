/**
 * 富互动 play 分片 u51 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u51'

export const UNIT_RICH_PLAYS = [
  {
    char: '琴', unit: 'u51', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '按下琴键，一个一个弹五下。',
    props: { hero: '🎹', items: ['🎹', '🎹', '🎹', '🎹', '🎹'], goal: 5 },
    templateFallback: false
  },
  {
    char: '鼓', unit: 'u51', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '敲起小鼓，咚咚咚。',
    props: { hero: '🥁', sound: '咚咚', goal: 3 },
    templateFallback: false
  },
  {
    char: '笛', unit: 'u51', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '笛子吹起来，呜呜地响。',
    props: { hero: '🎶', sound: '呜呜', goal: 3 },
    templateFallback: false
  },
  {
    char: '箫', unit: 'u51', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '竖着的箫，气从上往下走。',
    props: { hero: '🎵', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '弦', unit: 'u51', theme: 'object',
    template: 'trace-path', interaction: 'drag',
    narration: '手指拨一下弦，颤个不停。',
    props: { hero: '🎻', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '调', unit: 'u51', theme: 'word',
    template: 'sort-buckets', interaction: 'drag',
    narration: '高的声音在上，低的在下。',
    props: { hero: '🎼', items: [{ item: '🐦', bucket: '高' }, { item: '🔔', bucket: '高' }, { item: '🐻', bucket: '低' }, { item: '🥁', bucket: '低' }], buckets: [{ label: '高', emoji: '⬆️' }, { label: '低', emoji: '⬇️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '律', unit: 'u51', theme: 'number',
    template: 'pair-match', interaction: 'drag',
    narration: '一快一慢，节律配成对。',
    props: { hero: '📊', pairs: [{ a: '🐇', b: '⚡' }, { a: '🐢', b: '🐌' }, { a: '🥁', b: '🎵' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '谱', unit: 'u51', theme: 'object',
    template: 'scene-poke', interaction: 'tap',
    narration: '乐谱上的音符，挨个点亮。',
    props: { hero: '🎼', items: ['🎵', '🎶', '🎼'], goal: 3 },
    templateFallback: false
  },
  {
    char: '弹', unit: 'u51', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '手指弹三下，声音跳出来。',
    props: { hero: '🎹', items: ['👆', '👆', '👆'], goal: 3 },
    templateFallback: false
  },
  {
    char: '奏', unit: 'u51', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '每种乐器配上它的声音。',
    props: { hero: '🎺', pairs: [{ a: '🎺', b: '📢' }, { a: '🥁', b: '🔊' }, { a: '🎻', b: '🎵' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '彩', unit: 'u51', theme: 'color',
    template: 'morph-story', interaction: 'sequence',
    narration: '白光穿过水珠，变出七彩。',
    props: { hero: '🌈', stages: ['⬜', '💧', '🌈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '描', unit: 'u51', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '照着虚线描一遍，别出格。',
    props: { hero: '✏️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '涂', unit: 'u51', theme: 'color',
    template: 'color-fill', interaction: 'tap',
    narration: '拿蜡笔把小房子涂满黄色。',
    props: { hero: '🖍️', color: 'yellow', goal: 3 },
    templateFallback: false
  },
  {
    char: '塑', unit: 'u51', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '捏几团泥，塑成一个小人。',
    props: { hero: '🗿', parts: ['🟤', '🟤', '🟤'], goal: 3 },
    templateFallback: false
  },
  {
    char: '雕', unit: 'u51', theme: 'action',
    template: 'morph-story', interaction: 'sequence',
    narration: '一刀刀刻下去，石头成了像。',
    props: { hero: '🗿', stages: ['🪨', '🔨', '🗿'], goal: 3 },
    templateFallback: false
  },
  {
    char: '展', unit: 'u51', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '画展上挂着画，一幅幅看。',
    props: { hero: '🖼️', items: ['🖼️', '🎨', '🖌️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '镜', unit: 'u51', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '镜子里的和外面的，配一对。',
    props: { hero: '🪞', pairs: [{ a: '🙂', b: '🙂' }, { a: '✋', b: '✋' }, { a: '🐱', b: '🐱' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '剪', unit: 'u51', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '咔嚓一下，把纸剪开。',
    props: { hero: '✂️', dir: 'down', goal: 4 },
    templateFallback: false
  },
  {
    char: '影', unit: 'u51', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '谁的影子？把人和影配上。',
    props: { hero: '👥', pairs: [{ a: '🐘', b: '👥' }, { a: '🌳', b: '👥' }, { a: '🧒', b: '👥' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '痕', unit: 'u51', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '地上留下一道痕，找出来。',
    props: { hero: '🔍', target: '👣', decoys: ['🍃', '🪨', '🌿'], goal: 1 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
