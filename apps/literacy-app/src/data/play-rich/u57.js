/**
 * 富互动 play 分片 u57 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u57'

export const UNIT_RICH_PLAYS = [
  {
    char: '欢', unit: 'u57', theme: 'feeling',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '欢呼一声，彩带全炸开。',
    props: { hero: '😄', items: ['🎊', '🎊', '🎊'], goal: 3 },
    templateFallback: false
  },
  {
    char: '乐', unit: 'u57', theme: 'feeling',
    template: 'sound-tap', interaction: 'tap',
    narration: '按一下就响，快乐的音符。',
    props: { hero: '🎉', sound: '啦啦', goal: 3 },
    templateFallback: false
  },
  {
    char: '悲', unit: 'u57', theme: 'feeling',
    template: 'morph-story', interaction: 'sequence',
    narration: '笑脸慢慢垮下来，好悲伤。',
    props: { hero: '😢', stages: ['🙂', '😔', '😢'], goal: 3 },
    templateFallback: false
  },
  {
    char: '愁', unit: 'u57', theme: 'feeling',
    template: 'grow-tap', interaction: 'tap',
    narration: '心事越堆越多，眉头皱起来。',
    props: { hero: '😟', stages: ['🙂', '😟', '😩'], goal: 3 },
    templateFallback: false
  },
  {
    char: '恼', unit: 'u57', theme: 'feeling',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '谁在生闷气？把苦恼的脸挑出来。',
    props: { hero: '😤', target: '😤', decoys: ['😀', '😴', '🥰'], goal: 1 },
    templateFallback: false
  },
  {
    char: '怒', unit: 'u57', theme: 'feeling',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '气得一拍桌子，怒气往上冲。',
    props: { hero: '😠', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '惊', unit: 'u57', theme: 'feeling',
    template: 'tap-reveal', interaction: 'tap',
    narration: '盒盖一开，吓一大惊。',
    props: { hero: '😲', items: ['🐍', '🎈', '🕷️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '恐', unit: 'u57', theme: 'feeling',
    template: 'sort-buckets', interaction: 'drag',
    narration: '不怕的搁一边，恐怖的搁一边。',
    props: { hero: '😨', items: [{ item: '🐣', bucket: '不怕' }, { item: '🌼', bucket: '不怕' }, { item: '👻', bucket: '害怕' }, { item: '🕷️', bucket: '害怕' }], buckets: [{ label: '不怕', emoji: '🙂' }, { label: '害怕', emoji: '😨' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '羞', unit: 'u57', theme: 'feeling',
    template: 'color-fill', interaction: 'tap',
    narration: '一害羞，脸蛋就红扑扑的。',
    props: { hero: '😊', color: '红', goal: 3 },
    templateFallback: false
  },
  {
    char: '傲', unit: 'u57', theme: 'feeling',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把头一抬，骄傲地挺起来。',
    props: { hero: '😌', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '柔', unit: 'u57', theme: 'body',
    template: 'trace-path', interaction: 'drag',
    narration: '软软的小熊，轻轻推着走。',
    props: { hero: '🧸', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '睛', unit: 'u57', theme: 'body',
    template: 'scene-poke', interaction: 'tap',
    narration: '睁着眼睛，看看周围有什么。',
    props: { hero: '👁️', items: ['🌈', '🐦', '🌻'], goal: 3 },
    templateFallback: false
  },
  {
    char: '睁', unit: 'u57', theme: 'body',
    template: 'grow-tap', interaction: 'tap',
    narration: '眼皮慢慢抬，眼睛睁开了。',
    props: { hero: '👀', stages: ['😴', '😑', '👀'], goal: 3 },
    templateFallback: false
  },
  {
    char: '眉', unit: 'u57', theme: 'body',
    template: 'drag-parts', interaction: 'drag',
    narration: '把两道眉毛贴到眼睛上边。',
    props: { hero: '😐', parts: ['〰️', '〰️'], goal: 2 },
    templateFallback: false
  },
  {
    char: '唇', unit: 'u57', theme: 'body',
    template: 'color-fill', interaction: 'tap',
    narration: '给小嘴唇涂上淡淡的粉。',
    props: { hero: '👄', color: '粉', goal: 3 },
    templateFallback: false
  },
  {
    char: '喉', unit: 'u57', theme: 'body',
    template: 'sound-tap', interaction: 'tap',
    narration: '摸摸喉咙，跟着哼一声。',
    props: { hero: '🗣️', sound: '嗯', goal: 3 },
    templateFallback: false
  },
  {
    char: '腰', unit: 'u57', theme: 'body',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '弯下腰去，捡起地上的球。',
    props: { hero: '🧍', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '掌', unit: 'u57', theme: 'body',
    template: 'count-tap', interaction: 'tap',
    narration: '拍拍手掌，一起拍五下。',
    props: { hero: '🖐️', items: ['👏', '👏', '👏', '👏', '👏'], goal: 5 },
    templateFallback: false
  },
  {
    char: '揉', unit: 'u57', theme: 'action',
    template: 'count-tap', interaction: 'tap',
    narration: '两只手揉一揉，揉三下面团。',
    props: { hero: '🤲', items: ['🥟', '🥟', '🥟'], goal: 3 },
    templateFallback: false
  },
  {
    char: '抖', unit: 'u57', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '冷得直发抖，被子抖一抖。',
    props: { hero: '🥶', dir: 'left', goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
