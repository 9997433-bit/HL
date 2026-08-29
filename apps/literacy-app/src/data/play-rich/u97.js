/**
 * 富互动 play 分片 u97 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u97'

export const UNIT_RICH_PLAYS = [
  {
    char: '觉', unit: 'u97', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '忽然觉悟，灯泡亮了。',
    props: { hero: '💡', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '宣', unit: 'u97', theme: 'place',
    template: 'grow-tap', interaction: 'tap',
    narration: '宣布好消息，敲三下鼓。',
    props: { hero: '📢', stages: ['🪨', '📢', '⭐'], goal: 3 },
    templateFallback: false
  },
  {
    char: '宫', unit: 'u97', theme: 'place',
    template: 'grow-tap', interaction: 'tap',
    narration: '走进宫殿，穿过大门。',
    props: { hero: '🏯', stages: ['🪵', '🏯', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '突', unit: 'u97', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '突然跳出来，吓一跳。',
    props: { hero: '⚡', pairs: [{ a: '⚡', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '⚡' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '穿', unit: 'u97', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '穿上外套，扣好扣子。',
    props: { hero: '👕', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '扁', unit: 'u97', theme: 'shape',
    template: 'color-fill', interaction: 'tap',
    narration: '皮球被压扁，打回气。',
    props: { hero: '🥞', color: 'green', goal: 3 },
    templateFallback: false
  },
  {
    char: '袄', unit: 'u97', theme: 'action',
    template: 'rain-catch', interaction: 'drag',
    narration: '穿上棉袄，暖和起来。',
    props: { hero: '🧥', items: ['🌙', '🎈', '🧩'], tool: '🧥', goal: 3 },
    templateFallback: false
  },
  {
    char: '祖', unit: 'u97', theme: 'number',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '祖国家园，点亮地图。',
    props: { hero: '🇨🇳', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '误', unit: 'u97', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '改掉错误，换成对勾。',
    props: { hero: '❌', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '诵', unit: 'u97', theme: 'school',
    template: 'grow-tap', interaction: 'tap',
    narration: '大声朗诵，读完一段。',
    props: { hero: '📖', stages: ['🎈', '📖', '🌱'], goal: 3 },
    templateFallback: false
  },
  {
    char: '退', unit: 'u97', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '往后退三步，让出空间。',
    props: { hero: '⬅️', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '昼', unit: 'u97', theme: 'time',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '白昼太阳高，点亮阳光。',
    props: { hero: '☀️', target: '☀️', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '屏', unit: 'u97', theme: 'weather',
    template: 'grow-tap', interaction: 'tap',
    narration: '滑动屏幕，翻到下一页。',
    props: { hero: '🖥️', stages: ['📦', '🖥️', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '费', unit: 'u97', theme: 'nature',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '花掉硬币，买一张票。',
    props: { hero: '💸', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '陡', unit: 'u97', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '陡坡好陡，小心爬上去。',
    props: { hero: '⛰️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '孩', unit: 'u97', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '小朋友们，手拉手排队。',
    props: { hero: '🧒', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '姥', unit: 'u97', theme: 'family',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '叫一声姥姥，送上拥抱。',
    props: { hero: '👵', items: ['👵', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '盈', unit: 'u97', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '月亮盈满，圆圆挂天上。',
    props: { hero: '🌕', sound: '呼呼', goal: 3 },
    templateFallback: false
  },
  {
    char: '绑', unit: 'u97', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '绳子绑紧礼物，打蝴蝶结。',
    props: { hero: '🪢', parts: ['🪵', '❄️', '🪢'], goal: 3 },
    templateFallback: false
  },
  {
    char: '绒', unit: 'u97', theme: 'object',
    template: 'pair-match', interaction: 'drag',
    narration: '摸摸绒毛，软软的。',
    props: { hero: '🐤', pairs: [{ a: '🐤', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '🐤' }], goal: 3 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
