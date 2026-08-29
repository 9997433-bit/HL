/**
 * 富互动 play 分片 u79 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u79'

export const UNIT_RICH_PLAYS = [
  {
    char: '附', unit: 'u79', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把贴纸附加在本子上。',
    props: { hero: '📎', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '坠', unit: 'u79', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '落叶往下坠，接到篮子里。',
    props: { hero: '🍂', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '妙', unit: 'u79', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '这个办法真妙，亮三颗星。',
    props: { hero: '✨', items: ['🎁', '🧩', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '妨', unit: 'u79', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '别妨碍别人走路，让一让。',
    props: { hero: '🚧', target: '🚧', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '努', unit: 'u79', theme: 'action',
    template: 'grow-tap', interaction: 'tap',
    narration: '努足劲，把箱子抬起来。',
    props: { hero: '💪', stages: ['📦', '💪', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '忍', unit: 'u79', theme: 'feeling',
    template: 'drag-parts', interaction: 'drag',
    narration: '忍住不哭，深吸一口气。',
    props: { hero: '😣', parts: ['🧩', '🌱', '😣'], goal: 3 },
    templateFallback: false
  },
  {
    char: '劲', unit: 'u79', theme: 'action',
    template: 'trace-path', interaction: 'drag',
    narration: '使出全身劲，推开大门。',
    props: { hero: '🏋️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '纯', unit: 'u79', theme: 'number',
    template: 'scene-poke', interaction: 'tap',
    narration: '牛奶纯纯的，倒满一杯。',
    props: { hero: '🥛', items: ['🎯', '🪵', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '纱', unit: 'u79', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '拉开窗纱，阳光照进来。',
    props: { hero: '🪟', items: ['🪟', '🌱', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '纳', unit: 'u79', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把信接纳进邮箱。',
    props: { hero: '📥', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '纵', unit: 'u79', theme: 'shape',
    template: 'grow-tap', interaction: 'tap',
    narration: '顺着纵向，从上画到下。',
    props: { hero: '↕️', stages: ['🪵', '↕️', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '纷', unit: 'u79', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '花瓣纷纷落下，接住三片。',
    props: { hero: '🍂', pairs: [{ a: '🍂', b: '💧' }, { a: '🌙', b: '🎁' }, { a: '💧', b: '🍂' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '纹', unit: 'u79', theme: 'nature',
    template: 'sort-buckets', interaction: 'drag',
    narration: '指纹按上去，留下印记。',
    props: { hero: '🌀', items: [{ item: '🌀', bucket: '左' }, { item: '🔑', bucket: '左' }, { item: '🔥', bucket: '右' }, { item: '☀️', bucket: '右' }], buckets: [{ label: '左', emoji: '🔥' }, { label: '右', emoji: '☀️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '纺', unit: 'u79', theme: 'nature',
    template: 'color-fill', interaction: 'tap',
    narration: '棉花纺成线，一卷卷绕。',
    props: { hero: '🧶', color: 'yellow', goal: 3 },
    templateFallback: false
  },
  {
    char: '驴', unit: 'u79', theme: 'animal',
    template: 'grow-tap', interaction: 'tap',
    narration: '小毛驴驮货，走稳一点。',
    props: { hero: '🫏', stages: ['🌙', '🫏', '🧩'], goal: 3 },
    templateFallback: false
  },
  {
    char: '纽', unit: 'u79', theme: 'shape',
    template: 'tap-reveal', interaction: 'tap',
    narration: '扣上纽扣，衣服穿整齐。',
    props: { hero: '🔘', items: ['☀️', '🎁', '🔔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '奉', unit: 'u79', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '双手奉上礼物，鞠躬。',
    props: { hero: '🎁', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '环', unit: 'u79', theme: 'nature',
    template: 'count-tap', interaction: 'tap',
    narration: '花环戴在头上，转一圈。',
    props: { hero: '💍', items: ['💍', '💍', '💍'], goal: 3 },
    templateFallback: false
  },
  {
    char: '武', unit: 'u79', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '打一套武术，出三招。',
    props: { hero: '🥋', items: ['🎁', '🧩', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '责', unit: 'u79', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '完成责任清单，勾掉三项。',
    props: { hero: '📋', target: '📋', decoys: ['🔑', '🔔', '🪵'], goal: 1 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
