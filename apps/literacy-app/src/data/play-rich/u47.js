/**
 * 富互动 play 分片 u47 —— 这一单元的 20 条手写剧本（ROUND18_H3）。
 *
 * 玩到这一单元的字时由 char-play.js 的 ensurePlayUnit() 动态 import 进来，
 * 不在任何同步 import 链上：别的模块要用请走 char-play.js 的异步口，
 * 直接静态 import 本文件等于把拆包白拆了（check:bundle 与 check:round18 都会拦）。
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 这一片是哪个单元。 */
export const UNIT = 'u47'

export const UNIT_RICH_PLAYS = [
  {
    char: '兽', unit: 'u47', theme: 'animal',
    template: 'sort-buckets', interaction: 'drag',
    narration: '四条腿的进林子，会飞的上天。',
    props: { hero: '🦁', items: [{ item: '🐅', bucket: '林子' }, { item: '🐻', bucket: '林子' }, { item: '🕊️', bucket: '天上' }, { item: '🦅', bucket: '天上' }], buckets: [{ label: '林子', emoji: '🌲' }, { label: '天上', emoji: '☁️' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '禽', unit: 'u47', theme: 'animal',
    template: 'count-tap', interaction: 'tap',
    narration: '院子里的家禽，数满四只。',
    props: { hero: '🐔', items: ['🐔', '🦆', '🦢', '🦃'], goal: 4 },
    templateFallback: false
  },
  {
    char: '鸽', unit: 'u47', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '松开手，鸽子往上飞走了。',
    props: { hero: '🕊️', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '雀', unit: 'u47', theme: 'animal',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '小麻雀啄米，一粒粒啄光。',
    props: { hero: '🐦', items: ['🌾', '🌾', '🌾'], goal: 3 },
    templateFallback: false
  },
  {
    char: '鹰', unit: 'u47', theme: 'animal',
    template: 'trace-path', interaction: 'drag',
    narration: '老鹰盯住猎物，俯冲下去。',
    props: { hero: '🦅', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '鸦', unit: 'u47', theme: 'animal',
    template: 'sound-tap', interaction: 'tap',
    narration: '乌鸦停在枝头，哇哇地叫。',
    props: { hero: '🐦‍⬛', sound: '哇哇', goal: 3 },
    templateFallback: false
  },
  {
    char: '鹤', unit: 'u47', theme: 'animal',
    template: 'grow-tap', interaction: 'tap',
    narration: '小鹤长大，脖子腿都变长。',
    props: { hero: '🕊️', stages: ['🐣', '🦢', '🕊️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '狮', unit: 'u47', theme: 'animal',
    template: 'sound-tap', interaction: 'tap',
    narration: '狮子张开大嘴，吼一声。',
    props: { hero: '🦁', sound: '吼吼', goal: 3 },
    templateFallback: false
  },
  {
    char: '豹', unit: 'u47', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '花豹跑起来，一溜烟往前。',
    props: { hero: '🐆', dir: 'right', goal: 4 },
    templateFallback: false
  },
  {
    char: '猿', unit: 'u47', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '猿猴抓住藤条，荡过去。',
    props: { hero: '🦍', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '鲸', unit: 'u47', theme: 'animal',
    template: 'grow-tap', interaction: 'tap',
    narration: '鲸鱼喷出水柱，越喷越高。',
    props: { hero: '🐋', stages: ['🐋', '💦', '⛲'], goal: 3 },
    templateFallback: false
  },
  {
    char: '鲨', unit: 'u47', theme: 'animal',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '海里哪个是鲨鱼？找尖鳍的。',
    props: { hero: '🦈', target: '🦈', decoys: ['🐟', '🐠', '🐙'], goal: 1 },
    templateFallback: false
  },
  {
    char: '蚕', unit: 'u47', theme: 'animal',
    template: 'morph-story', interaction: 'sequence',
    narration: '蚕宝宝吐丝结茧，变成蛾。',
    props: { hero: '🐛', stages: ['🐛', '🕸️', '🦋'], goal: 3 },
    templateFallback: false
  },
  {
    char: '蜘', unit: 'u47', theme: 'animal',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '叶子底下蹲着蜘蛛，找出来。',
    props: { hero: '🕷️', target: '🕷️', decoys: ['🍃', '🐞', '🪨'], goal: 1 },
    templateFallback: false
  },
  {
    char: '蛛', unit: 'u47', theme: 'animal',
    template: 'trace-path', interaction: 'drag',
    narration: '蛛丝一圈圈绕，织成一张网。',
    props: { hero: '🕸️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '蝉', unit: 'u47', theme: 'animal',
    template: 'sound-tap', interaction: 'tap',
    narration: '夏天的蝉在树上，知了知了。',
    props: { hero: '🎶', sound: '知了', goal: 3 },
    templateFallback: false
  },
  {
    char: '蜻', unit: 'u47', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '蜻蜓点了下水，又飞起来。',
    props: { hero: '🪰', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '蜓', unit: 'u47', theme: 'animal',
    template: 'count-tap', interaction: 'tap',
    narration: '荷叶上停了几只蜻蜓？数数。',
    props: { hero: '🪰', items: ['🪰', '🪰', '🪰'], goal: 3 },
    templateFallback: false
  },
  {
    char: '躲', unit: 'u47', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '它躲在哪儿？翻开找一找。',
    props: { hero: '🙈', items: ['🌳', '🪨', '🚪'], goal: 3 },
    templateFallback: false
  },
  {
    char: '藏', unit: 'u47', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '宝贝藏在哪个箱子里？',
    props: { hero: '🗝️', target: '🗝️', decoys: ['📦', '🧳', '🗃️'], goal: 1 },
    templateFallback: false
  },
]

export default UNIT_RICH_PLAYS
