/**
 * 富互动 play 脚本库 —— 「玩」这一步的手写剧本，覆盖前 20 个单元共 272 个字。
 *
 * 每条都是照着字义写的：雨接雨滴、火添柴、口张嘴发声、推往前推、拉往回拉。
 * 这一层的 templateFallback 一律为假；剩下的字由 char-play.js 按部首 / 主题
 * 模板自动补齐（那批 templateFallback 为真）。两层加起来才是全库 Play 覆盖。
 *
 * 舞台怎么用：
 *   template     具体演法，取值见下面的 PLAY_TEMPLATES
 *   interaction  交互类型（tap / drag / swipe / sequence）。某个模板的专属动效
 *                还没实现时按它退回通用演法，孩子照样玩得完——绝不能退成空白卡。
 *   narration    念给孩子听的一句，也是无障碍朗读的文案
 *   props.goal   要完成几次有效交互才算通关；reduce-motion 和「跳过这一步」
 *                不改变通关条件，只是不播动效
 *
 * 本文件由 scripts/gen-char-play-rich.mjs 从 scripts/data/char-play-seed.txt 生成，
 * 请勿手改；要改剧本改 seed，然后跑 npm run gen:play:rich。
 */

/** 模板名录：舞台照着 interaction 决定「怎么算玩完了」。 */
export const PLAY_TEMPLATES = {
  'morph-story': { interaction: 'sequence', desc: '象形分镜：从实物 emoji 一步步变成字形' },
  'tap-reveal': { interaction: 'tap', desc: '点一点，藏起来的东西一个个露出来' },
  'emoji-hunt': { interaction: 'tap', desc: '一堆干扰项里找出目标（找中后目标会换位置再出现）' },
  'count-tap': { interaction: 'tap', desc: '一个一个点着数，点满为止' },
  'pop-bubbles': { interaction: 'tap', desc: '戳掉 / 吃掉 / 喝掉，点一个少一个' },
  'grow-tap': { interaction: 'tap', desc: '点一下长一点，按 stages 逐级长大' },
  'sound-tap': { interaction: 'tap', desc: '点了会发声，跟着念拟声词' },
  'color-fill': { interaction: 'tap', desc: '点着把主角一块块涂上颜色' },
  'scene-poke': { interaction: 'tap', desc: '一幅小场景，挨个点亮里面的东西' },
  'drag-parts': { interaction: 'drag', desc: '把零件 / 部件拖到一起，拼成主角' },
  'rain-catch': { interaction: 'drag', desc: '东西往下掉，拖着工具去接' },
  'trace-path': { interaction: 'drag', desc: '按住主角顺着路线拖过去' },
  'pair-match': { interaction: 'drag', desc: '左右连线，配成一对' },
  'sort-buckets': { interaction: 'drag', desc: '把每样东西拖进它该去的筐' },
  'word-build': { interaction: 'drag', desc: '把两个字拖到一起，组成一个词' },
  'swipe-motion': { interaction: 'swipe', desc: '照着字义的方向划：推向前、拉回来、举往上' },
}

/** 主题分类，舞台拿它挑配色和音效。 */
export const PLAY_THEMES = ['number', 'nature', 'weather', 'animal', 'body', 'family', 'school', 'food', 'color', 'shape', 'time', 'place', 'action', 'object', 'word', 'feeling']

export const CHAR_PLAY_RICH = [
  // u1
  {
    char: '一', unit: 'u1', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '只点一个苹果就好，一就是最小的数。',
    props: { hero: '☝️', items: ['🍎'], goal: 1 },
    templateFallback: false
  },
  {
    char: '二', unit: 'u1', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '再添一只小鸭，两只排排站就是二。',
    props: { hero: '✌️', items: ['🦆', '🦆'], goal: 2 },
    templateFallback: false
  },
  {
    char: '三', unit: 'u1', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '点亮三颗星星，三横就是三。',
    props: { hero: '🤟', items: ['⭐', '⭐', '⭐'], goal: 3 },
    templateFallback: false
  },
  {
    char: '上', unit: 'u1', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '往上一推，气球飞到高高的天上。',
    props: { hero: '🎈', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '下', unit: 'u1', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '往下一拉，雨滴落到地面上。',
    props: { hero: '💧', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '人', unit: 'u1', theme: 'body',
    template: 'morph-story', interaction: 'sequence',
    narration: '小人迈开两条腿，就走成了人字。',
    props: { hero: '🧍', stages: ['🧍', '🚶', '人'], goal: 3 },
    templateFallback: false
  },
  {
    char: '口', unit: 'u1', theme: 'body',
    template: 'sound-tap', interaction: 'tap',
    narration: '点点小嘴巴，张开说「啊」。',
    props: { hero: '👄', sound: '啊', goal: 3 },
    templateFallback: false
  },
  {
    char: '大', unit: 'u1', theme: 'body',
    template: 'grow-tap', interaction: 'tap',
    narration: '张开双手越张越开，这就是大。',
    props: { hero: '🙆', stages: ['🙋', '🙆', '🐘'], goal: 3 },
    templateFallback: false
  },
  {
    char: '小', unit: 'u1', theme: 'nature',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '谁最小？把小小的那一个找出来。',
    props: { hero: '🐣', target: '🐣', decoys: ['🐔', '🐘', '🐄'], goal: 1 },
    templateFallback: false
  },
  {
    char: '我', unit: 'u1', theme: 'family',
    template: 'tap-reveal', interaction: 'tap',
    narration: '点点镜子里的小朋友，那就是我。',
    props: { hero: '🪞', items: ['🙋'], goal: 1 },
    templateFallback: false
  },
  {
    char: '个', unit: 'u1', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '一个一个放进筐里，数数几个。',
    props: { hero: '🧺', items: ['🍎', '🍎', '🍎'], goal: 3 },
    templateFallback: false
  },
  {
    char: '们', unit: 'u1', theme: 'family',
    template: 'tap-reveal', interaction: 'tap',
    narration: '一个人加上大家，就成了我们。',
    props: { hero: '👥', items: ['🧍', '🧍', '🧍'], goal: 3 },
    templateFallback: false
  },
  // u2
  {
    char: '日', unit: 'u2', theme: 'nature',
    template: 'morph-story', interaction: 'sequence',
    narration: '圆圆的太阳慢慢变方，就成了日。',
    props: { hero: '☀️', stages: ['☀️', '🌞', '日'], goal: 3 },
    templateFallback: false
  },
  {
    char: '月', unit: 'u2', theme: 'nature',
    template: 'morph-story', interaction: 'sequence',
    narration: '满月一点点变弯，弯成月字。',
    props: { hero: '🌙', stages: ['🌕', '🌙', '月'], goal: 3 },
    templateFallback: false
  },
  {
    char: '山', unit: 'u2', theme: 'nature',
    template: 'drag-parts', interaction: 'drag',
    narration: '把三个山尖尖立起来，就是山。',
    props: { hero: '⛰️', parts: ['⛰️', '⛰️', '⛰️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '水', unit: 'u2', theme: 'nature',
    template: 'trace-path', interaction: 'drag',
    narration: '带着小水滴顺着山坡流下来。',
    props: { hero: '💧', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '火', unit: 'u2', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '添一根柴，火苗就往上蹿一点。',
    props: { hero: '🔥', stages: ['🕯️', '🔥', '🌋'], goal: 3 },
    templateFallback: false
  },
  {
    char: '木', unit: 'u2', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '小树苗喝饱水，长成一棵大树。',
    props: { hero: '🌲', stages: ['🌱', '🌿', '🌲'], goal: 3 },
    templateFallback: false
  },
  {
    char: '田', unit: 'u2', theme: 'nature',
    template: 'scene-poke', interaction: 'tap',
    narration: '一格一格的田里，点点种了什么。',
    props: { hero: '🌾', items: ['🌾', '🌽', '🥬', '🍠'], goal: 4 },
    templateFallback: false
  },
  {
    char: '土', unit: 'u2', theme: 'nature',
    template: 'scene-poke', interaction: 'tap',
    narration: '挖挖泥土，看看土里藏着谁。',
    props: { hero: '🟫', items: ['🌱', '🐛', '🥔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '天', unit: 'u2', theme: 'nature',
    template: 'scene-poke', interaction: 'tap',
    narration: '抬头看天，天上都有些什么。',
    props: { hero: '🌤️', items: ['☁️', '🐦', '🌈', '✈️'], goal: 4 },
    templateFallback: false
  },
  {
    char: '花', unit: 'u2', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '浇浇水，花骨朵一点点开了。',
    props: { hero: '🌸', stages: ['🌱', '🌷', '🌸'], goal: 3 },
    templateFallback: false
  },
  {
    char: '海', unit: 'u2', theme: 'nature',
    template: 'scene-poke', interaction: 'tap',
    narration: '大海好宽，点点浪里的小伙伴。',
    props: { hero: '🌊', items: ['🐬', '🐠', '🐚', '⛵'], goal: 4 },
    templateFallback: false
  },
  {
    char: '河', unit: 'u2', theme: 'nature',
    template: 'trace-path', interaction: 'drag',
    narration: '带小船顺着弯弯的小河往前漂。',
    props: { hero: '⛵', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '林', unit: 'u2', theme: 'nature',
    template: 'drag-parts', interaction: 'drag',
    narration: '一个木是树，两个木并排就是林。',
    props: { hero: '🌳', parts: ['木', '木'], goal: 2 },
    templateFallback: false
  },
  // u3
  {
    char: '手', unit: 'u3', theme: 'body',
    template: 'tap-reveal', interaction: 'tap',
    narration: '数数小手，一根一根点手指。',
    props: { hero: '✋', items: ['👆', '👆', '👆', '👆', '👆'], goal: 5 },
    templateFallback: false
  },
  {
    char: '目', unit: 'u3', theme: 'body',
    template: 'morph-story', interaction: 'sequence',
    narration: '把眼睛竖起来，就变成目字。',
    props: { hero: '👁️', stages: ['👁️', '👀', '目'], goal: 3 },
    templateFallback: false
  },
  {
    char: '耳', unit: 'u3', theme: 'body',
    template: 'sound-tap', interaction: 'tap',
    narration: '捂住耳朵再放开，听听什么在响。',
    props: { hero: '👂', sound: '叮咚', goal: 3 },
    templateFallback: false
  },
  {
    char: '心', unit: 'u3', theme: 'body',
    template: 'sound-tap', interaction: 'tap',
    narration: '手放在胸口，心怦怦怦地跳。',
    props: { hero: '❤️', sound: '怦怦', goal: 3 },
    templateFallback: false
  },
  {
    char: '牛', unit: 'u3', theme: 'animal',
    template: 'sound-tap', interaction: 'tap',
    narration: '摸摸牛角，大牛哞地叫一声。',
    props: { hero: '🐄', sound: '哞', goal: 3 },
    templateFallback: false
  },
  {
    char: '羊', unit: 'u3', theme: 'animal',
    template: 'count-tap', interaction: 'tap',
    narration: '数数草地上的小羊，咩咩咩。',
    props: { hero: '🐑', items: ['🐑', '🐑', '🐑'], goal: 3 },
    templateFallback: false
  },
  {
    char: '鸟', unit: 'u3', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '轻轻往上一挥，小鸟飞起来了。',
    props: { hero: '🐦', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '中', unit: 'u3', theme: 'place',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '谁正好在正中间？点中它。',
    props: { hero: '🎯', target: '🎯', decoys: ['⬅️', '➡️', '⬆️'], goal: 1 },
    templateFallback: false
  },
  {
    char: '不', unit: 'u3', theme: 'word',
    template: 'sort-buckets', interaction: 'drag',
    narration: '摇摇头说不，分清能做和不能做。',
    props: { hero: '🙅', items: [{ item: '📚', bucket: '可以' }, { item: '🧸', bucket: '可以' }, { item: '🔥', bucket: '不可以' }, { item: '🔌', bucket: '不可以' }], buckets: [{ label: '可以', emoji: '👍' }, { label: '不可以', emoji: '🙅' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '好', unit: 'u3', theme: 'feeling',
    template: 'tap-reveal', interaction: 'tap',
    narration: '女和子放在一起，心里就觉得好。',
    props: { hero: '👍', items: ['👧', '👶'], goal: 2 },
    templateFallback: false
  },
  {
    char: '头', unit: 'u3', theme: 'body',
    template: 'scene-poke', interaction: 'tap',
    narration: '点点头上都有什么：头发眼睛嘴巴。',
    props: { hero: '🙂', items: ['💇', '👁️', '👄'], goal: 3 },
    templateFallback: false
  },
  {
    char: '牙', unit: 'u3', theme: 'body',
    template: 'tap-reveal', interaction: 'tap',
    narration: '张开嘴，把白牙齿一颗颗刷干净。',
    props: { hero: '🦷', items: ['🦷', '🦷', '🦷'], tool: '🪥', goal: 3 },
    templateFallback: false
  },
  {
    char: '兔', unit: 'u3', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '小兔子一蹦一蹦，往上跳三下。',
    props: { hero: '🐰', dir: 'up', goal: 3 },
    templateFallback: false
  },
  // u4
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
  // u5
  {
    char: '四', unit: 'u5', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '数四个草莓：一二三四。',
    props: { hero: '4️⃣', items: ['🍓', '🍓', '🍓', '🍓'], goal: 4 },
    templateFallback: false
  },
  {
    char: '五', unit: 'u5', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '张开一只手，正好五个手指。',
    props: { hero: '🖐️', items: ['👆', '👆', '👆', '👆', '👆'], goal: 5 },
    templateFallback: false
  },
  {
    char: '六', unit: 'u5', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '六颗糖，把小盒子装满。',
    props: { hero: '6️⃣', items: ['🍬', '🍬', '🍬', '🍬', '🍬', '🍬'], goal: 6 },
    templateFallback: false
  },
  {
    char: '七', unit: 'u5', theme: 'number',
    template: 'count-tap', interaction: 'tap',
    narration: '一个星期七天，点满七格。',
    props: { hero: '7️⃣', items: ['📅', '📅', '📅', '📅', '📅', '📅', '📅'], goal: 7 },
    templateFallback: false
  },
  {
    char: '八', unit: 'u5', theme: 'number',
    template: 'drag-parts', interaction: 'drag',
    narration: '两撇往两边一分，就写成八。',
    props: { hero: '8️⃣', parts: ['丿', '乀'], goal: 2 },
    templateFallback: false
  },
  {
    char: '九', unit: 'u5', theme: 'number',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '戳破九个泡泡，再一个就到十。',
    props: { hero: '9️⃣', items: ['🫧', '🫧', '🫧', '🫧', '🫧', '🫧', '🫧', '🫧', '🫧'], goal: 9 },
    templateFallback: false
  },
  {
    char: '十', unit: 'u5', theme: 'number',
    template: 'drag-parts', interaction: 'drag',
    narration: '一横加一竖，交叉就是十。',
    props: { hero: '🔟', parts: ['一', '丨'], goal: 2 },
    templateFallback: false
  },
  {
    char: '百', unit: 'u5', theme: 'number',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '十个十个数，一百好多好多。',
    props: { hero: '💯', items: ['🫧', '🫧', '🫧', '🫧', '🫧', '🫧', '🫧', '🫧', '🫧', '🫧'], goal: 10 },
    templateFallback: false
  },
  {
    char: '千', unit: 'u5', theme: 'number',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '一千颗星星撒满天，先点亮十颗。',
    props: { hero: '🌌', items: ['⭐', '⭐', '⭐', '⭐', '⭐', '⭐', '⭐', '⭐', '⭐', '⭐'], goal: 10 },
    templateFallback: false
  },
  {
    char: '万', unit: 'u5', theme: 'number',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '一万像烟花一样多，点开看看。',
    props: { hero: '🎆', items: ['🎆', '🎆', '🎆', '🎆', '🎆'], goal: 5 },
    templateFallback: false
  },
  {
    char: '半', unit: 'u5', theme: 'number',
    template: 'drag-parts', interaction: 'drag',
    narration: '把西瓜从中间切开，一人一半。',
    props: { hero: '🍉', parts: ['🍉', '🍉'], goal: 2 },
    templateFallback: false
  },
  {
    char: '双', unit: 'u5', theme: 'number',
    template: 'pair-match', interaction: 'drag',
    narration: '两只一样的才叫一双，配对试试。',
    props: { hero: '🙌', pairs: [{ a: '🧦', b: '🧦' }, { a: '👟', b: '👟' }, { a: '🧤', b: '🧤' }], goal: 3 },
    templateFallback: false
  },
  // u6
  {
    char: '风', unit: 'u6', theme: 'weather',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '呼——手指一划，风把树叶吹跑。',
    props: { hero: '🍃', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '雨', unit: 'u6', theme: 'weather',
    template: 'rain-catch', interaction: 'drag',
    narration: '下雨啦，撑起小伞接住雨滴。',
    props: { hero: '🌧️', items: ['💧', '💧', '💧', '💧'], tool: '☂️', goal: 4 },
    templateFallback: false
  },
  {
    char: '云', unit: 'u6', theme: 'weather',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '白云飘飘，推着它慢慢走。',
    props: { hero: '☁️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '雪', unit: 'u6', theme: 'weather',
    template: 'rain-catch', interaction: 'drag',
    narration: '雪花飘下来，用手心接住它。',
    props: { hero: '❄️', items: ['❄️', '❄️', '❄️'], tool: '🧤', goal: 3 },
    templateFallback: false
  },
  {
    char: '地', unit: 'u6', theme: 'nature',
    template: 'scene-poke', interaction: 'tap',
    narration: '脚下的大地上，都长着什么。',
    props: { hero: '🌍', items: ['🌱', '🌳', '🐛'], goal: 3 },
    templateFallback: false
  },
  {
    char: '石', unit: 'u6', theme: 'nature',
    template: 'drag-parts', interaction: 'drag',
    narration: '把小石头一块一块摞高。',
    props: { hero: '🪨', parts: ['🪨', '🪨', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '草', unit: 'u6', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '春天到，小草从土里钻出来。',
    props: { hero: '🌱', stages: ['🟫', '🌱', '🌿'], goal: 3 },
    templateFallback: false
  },
  {
    char: '树', unit: 'u6', theme: 'nature',
    template: 'grow-tap', interaction: 'tap',
    narration: '树苗长成大树，还结了果子。',
    props: { hero: '🌳', stages: ['🌱', '🌳', '🍎'], goal: 3 },
    templateFallback: false
  },
  {
    char: '星', unit: 'u6', theme: 'nature',
    template: 'tap-reveal', interaction: 'tap',
    narration: '夜里点一点，星星一闪一闪亮。',
    props: { hero: '⭐', items: ['⭐', '⭐', '⭐', '⭐', '⭐'], goal: 5 },
    templateFallback: false
  },
  {
    char: '光', unit: 'u6', theme: 'nature',
    template: 'tap-reveal', interaction: 'tap',
    narration: '打开灯，光照到哪里哪里亮。',
    props: { hero: '🔆', items: ['💡', '🕯️', '🔦'], goal: 3 },
    templateFallback: false
  },
  {
    char: '冰', unit: 'u6', theme: 'weather',
    template: 'morph-story', interaction: 'sequence',
    narration: '水冷得发抖，冻成硬硬的一块冰。',
    props: { hero: '🧊', stages: ['💧', '🧊', '❄️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '沙', unit: 'u6', theme: 'nature',
    template: 'scene-poke', interaction: 'tap',
    narration: '沙滩上的沙细细的，挖挖看。',
    props: { hero: '🏖️', items: ['🐚', '🦀', '🪣'], goal: 3 },
    templateFallback: false
  },
  // u7
  {
    char: '父', unit: 'u7', theme: 'family',
    template: 'tap-reveal', interaction: 'tap',
    narration: '点点看，爸爸都会做什么。',
    props: { hero: '👨', items: ['🧰', '🚗', '🍳'], goal: 3 },
    templateFallback: false
  },
  {
    char: '母', unit: 'u7', theme: 'family',
    template: 'tap-reveal', interaction: 'tap',
    narration: '妈妈抱抱我，心里暖暖的。',
    props: { hero: '👩', items: ['🤱', '❤️', '🍲'], goal: 3 },
    templateFallback: false
  },
  {
    char: '男', unit: 'u7', theme: 'family',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '田里出力的是男，找出男孩子。',
    props: { hero: '👦', target: '👦', decoys: ['👧', '👵', '🧒'], goal: 1 },
    templateFallback: false
  },
  {
    char: '女', unit: 'u7', theme: 'family',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '找出女孩子，她扎着小辫子。',
    props: { hero: '👧', target: '👧', decoys: ['👦', '🧔', '👴'], goal: 1 },
    templateFallback: false
  },
  {
    char: '子', unit: 'u7', theme: 'family',
    template: 'grow-tap', interaction: 'tap',
    narration: '小娃娃一点点长大，变成小朋友。',
    props: { hero: '👶', stages: ['👶', '🧒', '👦'], goal: 3 },
    templateFallback: false
  },
  {
    char: '你', unit: 'u7', theme: 'family',
    template: 'sound-tap', interaction: 'tap',
    narration: '指一指对面的小伙伴，说声你好。',
    props: { hero: '🫵', sound: '你好', goal: 3 },
    templateFallback: false
  },
  {
    char: '他', unit: 'u7', theme: 'family',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '他说的是那个男孩，把他找出来。',
    props: { hero: '🧑', target: '🧑', decoys: ['👩', '👧', '👵'], goal: 1 },
    templateFallback: false
  },
  {
    char: '她', unit: 'u7', theme: 'family',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '她是女字旁，说的是那个女孩。',
    props: { hero: '👩‍🦰', target: '👩‍🦰', decoys: ['🧑', '👦', '👴'], goal: 1 },
    templateFallback: false
  },
  {
    char: '家', unit: 'u7', theme: 'family',
    template: 'drag-parts', interaction: 'drag',
    narration: '宝盖头是屋顶，屋顶下面就是家。',
    props: { hero: '🏠', parts: ['🏠', '👨', '👩', '🧒'], goal: 4 },
    templateFallback: false
  },
  {
    char: '爱', unit: 'u7', theme: 'feeling',
    template: 'tap-reveal', interaction: 'tap',
    narration: '抱一抱，心里的爱冒出小红心。',
    props: { hero: '❤️', items: ['💗', '💖', '💞'], goal: 3 },
    templateFallback: false
  },
  {
    char: '哥', unit: 'u7', theme: 'family',
    template: 'sort-buckets', interaction: 'drag',
    narration: '哥哥比我大，把他放到大的那边。',
    props: { hero: '👦', items: [{ item: '👦', bucket: '大' }, { item: '🧔', bucket: '大' }, { item: '👶', bucket: '小' }, { item: '🧒', bucket: '小' }], buckets: [{ label: '大', emoji: '🔼' }, { label: '小', emoji: '🔽' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '姐', unit: 'u7', theme: 'family',
    template: 'tap-reveal', interaction: 'tap',
    narration: '姐姐牵着我的手，看她在做什么。',
    props: { hero: '👧', items: ['📚', '🎀', '🤝'], goal: 3 },
    templateFallback: false
  },
  {
    char: '妹', unit: 'u7', theme: 'family',
    template: 'grow-tap', interaction: 'tap',
    narration: '妹妹比我小，她还在慢慢长大。',
    props: { hero: '🧒', stages: ['👶', '🧒', '👧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '国', unit: 'u7', theme: 'place',
    template: 'drag-parts', interaction: 'drag',
    narration: '大方框里住着好多人，那是我们的国。',
    props: { hero: '🏯', parts: ['囗', '玉'], goal: 2 },
    templateFallback: false
  },
  // u8
  {
    char: '学', unit: 'u8', theme: 'school',
    template: 'grow-tap', interaction: 'tap',
    narration: '每学会一样本领，就点亮一颗星。',
    props: { hero: '📚', stages: ['📖', '✏️', '🌟'], goal: 3 },
    templateFallback: false
  },
  {
    char: '校', unit: 'u8', theme: 'school',
    template: 'scene-poke', interaction: 'tap',
    narration: '走进学校，点点里面都有什么。',
    props: { hero: '🏫', items: ['🚪', '🔔', '🏀'], goal: 3 },
    templateFallback: false
  },
  {
    char: '老', unit: 'u8', theme: 'school',
    template: 'sort-buckets', interaction: 'drag',
    narration: '谁年纪大？把老爷爷放到老这边。',
    props: { hero: '👴', items: [{ item: '👵', bucket: '老' }, { item: '🧓', bucket: '老' }, { item: '🧒', bucket: '小' }, { item: '👶', bucket: '小' }], buckets: [{ label: '老', emoji: '👴' }, { label: '小', emoji: '👶' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '师', unit: 'u8', theme: 'school',
    template: 'tap-reveal', interaction: 'tap',
    narration: '老师教我们本领，点点她手里的东西。',
    props: { hero: '🧑‍🏫', items: ['📕', '✏️', '🗺️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '生', unit: 'u8', theme: 'school',
    template: 'grow-tap', interaction: 'tap',
    narration: '一颗种子从土里生出来，越长越高。',
    props: { hero: '🌱', stages: ['🌰', '🌱', '🌿'], goal: 3 },
    templateFallback: false
  },
  {
    char: '书', unit: 'u8', theme: 'school',
    template: 'tap-reveal', interaction: 'tap',
    narration: '一页一页翻开书，看看里面画了什么。',
    props: { hero: '📕', items: ['📖', '🖼️', '🔤'], goal: 3 },
    templateFallback: false
  },
  {
    char: '字', unit: 'u8', theme: 'school',
    template: 'word-build', interaction: 'drag',
    narration: '一个个方块字，拼出「写字」。',
    props: { hero: '🔤', parts: ['写', '字'], word: '写字', goal: 2 },
    templateFallback: false
  },
  {
    char: '读', unit: 'u8', theme: 'school',
    template: 'sound-tap', interaction: 'tap',
    narration: '张开嘴，把书上的字大声读出来。',
    props: { hero: '📖', sound: '一二三', goal: 3 },
    templateFallback: false
  },
  {
    char: '写', unit: 'u8', theme: 'school',
    template: 'trace-path', interaction: 'drag',
    narration: '拿起笔，跟着线把字写下来。',
    props: { hero: '✍️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '听', unit: 'u8', theme: 'school',
    template: 'sound-tap', interaction: 'tap',
    narration: '竖起耳朵听一听，是什么在响。',
    props: { hero: '👂', sound: '叮咚', goal: 3 },
    templateFallback: false
  },
  {
    char: '问', unit: 'u8', theme: 'school',
    template: 'drag-parts', interaction: 'drag',
    narration: '门里放一个口，站在门口问一问。',
    props: { hero: '❓', parts: ['门', '口'], goal: 2 },
    templateFallback: false
  },
  {
    char: '答', unit: 'u8', theme: 'school',
    template: 'pair-match', interaction: 'drag',
    narration: '有问就有答，把问和答连起来。',
    props: { hero: '🗨️', pairs: [{ a: '🐶', b: '汪' }, { a: '🐱', b: '喵' }, { a: '🐄', b: '哞' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '本', unit: 'u8', theme: 'school',
    template: 'count-tap', interaction: 'tap',
    narration: '数一数，书架上有几本书。',
    props: { hero: '📔', items: ['📕', '📗', '📘'], goal: 3 },
    templateFallback: false
  },
  // u9
  {
    char: '鱼', unit: 'u9', theme: 'animal',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '水里游过好多东西，点住那条小鱼。',
    props: { hero: '🐟', target: '🐟', decoys: ['🐙', '🦀', '🐚'], goal: 3 },
    templateFallback: false
  },
  {
    char: '虫', unit: 'u9', theme: 'animal',
    template: 'trace-path', interaction: 'drag',
    narration: '小虫子扭一扭，慢慢爬过树叶。',
    props: { hero: '🐛', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '马', unit: 'u9', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '驾！小马嗒嗒嗒地往前跑。',
    props: { hero: '🐴', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '猫', unit: 'u9', theme: 'animal',
    template: 'sound-tap', interaction: 'tap',
    narration: '摸摸小猫，它喵地叫了一声。',
    props: { hero: '🐱', sound: '喵', goal: 3 },
    templateFallback: false
  },
  {
    char: '狗', unit: 'u9', theme: 'animal',
    template: 'sound-tap', interaction: 'tap',
    narration: '拍拍小狗的头，它汪汪叫。',
    props: { hero: '🐶', sound: '汪', goal: 3 },
    templateFallback: false
  },
  {
    char: '鸡', unit: 'u9', theme: 'animal',
    template: 'sound-tap', interaction: 'tap',
    narration: '小鸡叽叽叫，还会下蛋。',
    props: { hero: '🐔', sound: '叽', goal: 3 },
    templateFallback: false
  },
  {
    char: '鸭', unit: 'u9', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '扁嘴巴的小鸭，摇摇摆摆下水啦。',
    props: { hero: '🦆', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '猪', unit: 'u9', theme: 'animal',
    template: 'sound-tap', interaction: 'tap',
    narration: '胖小猪拱拱鼻子，哼哼哼。',
    props: { hero: '🐷', sound: '哼', goal: 3 },
    templateFallback: false
  },
  {
    char: '象', unit: 'u9', theme: 'animal',
    template: 'grow-tap', interaction: 'tap',
    narration: '大象的长鼻子，能卷起水喷出来。',
    props: { hero: '🐘', stages: ['🐘', '🚿', '🌊'], goal: 3 },
    templateFallback: false
  },
  {
    char: '虎', unit: 'u9', theme: 'animal',
    template: 'sound-tap', interaction: 'tap',
    narration: '老虎吼一声，森林都安静了。',
    props: { hero: '🐯', sound: '吼', goal: 3 },
    templateFallback: false
  },
  {
    char: '蛙', unit: 'u9', theme: 'animal',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '青蛙呱呱，一蹦跳到荷叶上。',
    props: { hero: '🐸', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '熊', unit: 'u9', theme: 'animal',
    template: 'scene-poke', interaction: 'tap',
    narration: '大熊要冬眠了，帮它准备好。',
    props: { hero: '🐻', items: ['🍯', '🛌', '🌲'], goal: 3 },
    templateFallback: false
  },
  // u10
  {
    char: '红', unit: 'u10', theme: 'color',
    template: 'color-fill', interaction: 'tap',
    narration: '把小苹果涂得红红的。',
    props: { hero: '🍎', color: 'red', goal: 3 },
    templateFallback: false
  },
  {
    char: '黄', unit: 'u10', theme: 'color',
    template: 'color-fill', interaction: 'tap',
    narration: '把小鸭子涂得黄黄的。',
    props: { hero: '🐤', color: 'yellow', goal: 3 },
    templateFallback: false
  },
  {
    char: '蓝', unit: 'u10', theme: 'color',
    template: 'color-fill', interaction: 'tap',
    narration: '把大海涂得蓝蓝的。',
    props: { hero: '🌊', color: 'blue', goal: 3 },
    templateFallback: false
  },
  {
    char: '绿', unit: 'u10', theme: 'color',
    template: 'color-fill', interaction: 'tap',
    narration: '把小草涂得绿绿的。',
    props: { hero: '🌿', color: 'green', goal: 3 },
    templateFallback: false
  },
  {
    char: '白', unit: 'u10', theme: 'color',
    template: 'color-fill', interaction: 'tap',
    narration: '把云朵涂得白白的。',
    props: { hero: '☁️', color: 'white', goal: 3 },
    templateFallback: false
  },
  {
    char: '黑', unit: 'u10', theme: 'color',
    template: 'tap-reveal', interaction: 'tap',
    narration: '天黑了，打开手电看看藏着谁。',
    props: { hero: '⚫', items: ['🦉', '🦇', '⭐'], tool: '🔦', goal: 3 },
    templateFallback: false
  },
  {
    char: '色', unit: 'u10', theme: 'color',
    template: 'sort-buckets', interaction: 'drag',
    narration: '把颜色分一分，红的一边蓝的一边。',
    props: { hero: '🎨', items: [{ item: '🍎', bucket: '红' }, { item: '🍓', bucket: '红' }, { item: '🌊', bucket: '蓝' }, { item: '🫐', bucket: '蓝' }], buckets: [{ label: '红', emoji: '🔴' }, { label: '蓝', emoji: '🔵' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '圆', unit: 'u10', theme: 'shape',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '找出圆圆的、一个角也没有的。',
    props: { hero: '⭕', target: '⭕', decoys: ['🔷', '🔺', '⬜'], goal: 3 },
    templateFallback: false
  },
  {
    char: '方', unit: 'u10', theme: 'shape',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '找出方方正正、四个角的。',
    props: { hero: '🔷', target: '⬜', decoys: ['⭕', '🔺', '💠'], goal: 3 },
    templateFallback: false
  },
  {
    char: '长', unit: 'u10', theme: 'shape',
    template: 'sort-buckets', interaction: 'drag',
    narration: '长的放这边，短的放那边。',
    props: { hero: '📏', items: [{ item: '🐍', bucket: '长' }, { item: '🚂', bucket: '长' }, { item: '🐛', bucket: '短' }, { item: '🚗', bucket: '短' }], buckets: [{ label: '长', emoji: '📏' }, { label: '短', emoji: '📎' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '高', unit: 'u10', theme: 'shape',
    template: 'sort-buckets', interaction: 'drag',
    narration: '高的往上摆，矮的往下摆。',
    props: { hero: '🗼', items: [{ item: '🦒', bucket: '高' }, { item: '🌲', bucket: '高' }, { item: '🐕', bucket: '矮' }, { item: '🌱', bucket: '矮' }], buckets: [{ label: '高', emoji: '🗼' }, { label: '矮', emoji: '🏠' }], goal: 4 },
    templateFallback: false
  },
  // u11
  {
    char: '春', unit: 'u11', theme: 'time',
    template: 'grow-tap', interaction: 'tap',
    narration: '春风一吹，花全都开了。',
    props: { hero: '🌷', stages: ['🌱', '🌷', '🌸'], goal: 3 },
    templateFallback: false
  },
  {
    char: '夏', unit: 'u11', theme: 'time',
    template: 'scene-poke', interaction: 'tap',
    narration: '夏天太阳好大，点点消暑的东西。',
    props: { hero: '🌞', items: ['🍉', '🏖️', '🍦'], goal: 3 },
    templateFallback: false
  },
  {
    char: '秋', unit: 'u11', theme: 'time',
    template: 'rain-catch', interaction: 'drag',
    narration: '秋风起，接住飘下来的黄叶子。',
    props: { hero: '🍂', items: ['🍁', '🍂', '🍁'], tool: '🧺', goal: 3 },
    templateFallback: false
  },
  {
    char: '冬', unit: 'u11', theme: 'time',
    template: 'scene-poke', interaction: 'tap',
    narration: '冬天冷冰冰，给雪人穿戴好。',
    props: { hero: '⛄', items: ['🧣', '🧤', '🎩'], goal: 3 },
    templateFallback: false
  },
  {
    char: '早', unit: 'u11', theme: 'time',
    template: 'morph-story', interaction: 'sequence',
    narration: '太阳从地平线上升起来，早上到了。',
    props: { hero: '🌅', stages: ['🌑', '🌅', '🌞'], goal: 3 },
    templateFallback: false
  },
  {
    char: '晚', unit: 'u11', theme: 'time',
    template: 'morph-story', interaction: 'sequence',
    narration: '太阳落下去月亮爬上来，天晚了。',
    props: { hero: '🌆', stages: ['🌇', '🌆', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '明', unit: 'u11', theme: 'time',
    template: 'drag-parts', interaction: 'drag',
    narration: '日和月放在一起，天亮堂堂。',
    props: { hero: '🌞', parts: ['日', '月'], goal: 2 },
    templateFallback: false
  },
  {
    char: '今', unit: 'u11', theme: 'time',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '一堆日子里，找出今天那一格。',
    props: { hero: '📅', target: '📅', decoys: ['🗓️', '🗓️', '🗓️'], goal: 1 },
    templateFallback: false
  },
  {
    char: '年', unit: 'u11', theme: 'time',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '新年到，点响四个小烟花。',
    props: { hero: '🎊', items: ['🎆', '🎆', '🎆', '🎆'], goal: 4 },
    templateFallback: false
  },
  {
    char: '时', unit: 'u11', theme: 'time',
    template: 'trace-path', interaction: 'drag',
    narration: '拨一拨时针，让钟走一圈。',
    props: { hero: '⏰', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '分', unit: 'u11', theme: 'time',
    template: 'drag-parts', interaction: 'drag',
    narration: '把一块饼干平平地分成两半。',
    props: { hero: '🍪', parts: ['🍪', '🍪'], goal: 2 },
    templateFallback: false
  },
  {
    char: '刻', unit: 'u11', theme: 'time',
    template: 'count-tap', interaction: 'tap',
    narration: '一刻是十五分，点四下就一小时。',
    props: { hero: '⏳', items: ['⏳', '⏳', '⏳', '⏳'], goal: 4 },
    templateFallback: false
  },
  {
    char: '岁', unit: 'u11', theme: 'time',
    template: 'count-tap', interaction: 'tap',
    narration: '过一个生日长一岁，点亮蜡烛数数。',
    props: { hero: '🎂', items: ['🕯️', '🕯️', '🕯️', '🕯️', '🕯️'], goal: 5 },
    templateFallback: false
  },
  // u12
  {
    char: '左', unit: 'u12', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '往左边挥挥手，左手举起来。',
    props: { hero: '👈', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '右', unit: 'u12', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '往右边挥挥手，右手举起来。',
    props: { hero: '👉', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '多', unit: 'u12', theme: 'number',
    template: 'sort-buckets', interaction: 'drag',
    narration: '哪一堆多？把多的挑出来。',
    props: { hero: '➕', items: [{ item: '🍎🍎🍎', bucket: '多' }, { item: '🍬🍬🍬', bucket: '多' }, { item: '🍎', bucket: '少' }, { item: '🍬', bucket: '少' }], buckets: [{ label: '多', emoji: '➕' }, { label: '少', emoji: '➖' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '少', unit: 'u12', theme: 'number',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '吃掉几个，果子就变少了。',
    props: { hero: '🍓', items: ['🍓', '🍓', '🍓'], goal: 3 },
    templateFallback: false
  },
  {
    char: '门', unit: 'u12', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '推开大门，吱呀一声请进。',
    props: { hero: '🚪', dir: 'right', goal: 2 },
    templateFallback: false
  },
  {
    char: '车', unit: 'u12', theme: 'object',
    template: 'trace-path', interaction: 'drag',
    narration: '开着小车沿着马路往前开。',
    props: { hero: '🚗', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '足', unit: 'u12', theme: 'body',
    template: 'count-tap', interaction: 'tap',
    narration: '数数小脚丫，一二，两只脚。',
    props: { hero: '🦶', items: ['🦶', '🦶'], goal: 2 },
    templateFallback: false
  },
  {
    char: '前', unit: 'u12', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '向前走三步，看看前面有什么。',
    props: { hero: '🚩', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '后', unit: 'u12', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '往后退一退，站到后面去。',
    props: { hero: '🔙', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '里', unit: 'u12', theme: 'place',
    template: 'sort-buckets', interaction: 'drag',
    narration: '把玩具放进盒子里面。',
    props: { hero: '📥', items: [{ item: '🧸', bucket: '里面' }, { item: '🧩', bucket: '里面' }, { item: '🍂', bucket: '外面' }, { item: '🪨', bucket: '外面' }], buckets: [{ label: '里面', emoji: '📥' }, { label: '外面', emoji: '📤' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '外', unit: 'u12', theme: 'place',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '推门走到外面，外面太阳真好。',
    props: { hero: '🌞', dir: 'right', goal: 2 },
    templateFallback: false
  },
  {
    char: '边', unit: 'u12', theme: 'place',
    template: 'sort-buckets', interaction: 'drag',
    narration: '左边右边，把东西摆到对的一边。',
    props: { hero: '🧭', items: [{ item: '🍎', bucket: '左边' }, { item: '🧸', bucket: '左边' }, { item: '🍐', bucket: '右边' }, { item: '🎈', bucket: '右边' }], buckets: [{ label: '左边', emoji: '👈' }, { label: '右边', emoji: '👉' }], goal: 4 },
    templateFallback: false
  },
  // u13
  {
    char: '走', unit: 'u13', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '一步一步慢慢走，走路要小心。',
    props: { hero: '🥾', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '跑', unit: 'u13', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '快跑！两只脚都离开地面了。',
    props: { hero: '💨', dir: 'right', goal: 5 },
    templateFallback: false
  },
  {
    char: '跳', unit: 'u13', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '用力一蹬，往上跳三下。',
    props: { hero: '🤸', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '坐', unit: 'u13', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '两个人坐在土地上，就是坐。',
    props: { hero: '🧎', parts: ['人', '人', '土'], goal: 3 },
    templateFallback: false
  },
  {
    char: '站', unit: 'u13', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '站直了，两只脚立在地上不动。',
    props: { hero: '🚏', dir: 'up', goal: 2 },
    templateFallback: false
  },
  {
    char: '吃', unit: 'u13', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '啊呜——把好吃的一口一口吃掉。',
    props: { hero: '😋', items: ['🍎', '🍌', '🍞'], goal: 3 },
    templateFallback: false
  },
  {
    char: '喝', unit: 'u13', theme: 'action',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '咕咚咕咚，把水喝光。',
    props: { hero: '🥤', items: ['💧', '💧', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '拿', unit: 'u13', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '伸出手，把东西握住拿起来。',
    props: { hero: '🤲', parts: ['🍎', '🧸'], goal: 2 },
    templateFallback: false
  },
  {
    char: '唱', unit: 'u13', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '张开嘴唱一首歌，啦啦啦。',
    props: { hero: '🎤', sound: '啦', goal: 3 },
    templateFallback: false
  },
  {
    char: '笑', unit: 'u13', theme: 'feeling',
    template: 'grow-tap', interaction: 'tap',
    narration: '嘴角越翘越高，笑得好开心。',
    props: { hero: '😄', stages: ['🙂', '😀', '😄'], goal: 3 },
    templateFallback: false
  },
  {
    char: '哭', unit: 'u13', theme: 'feeling',
    template: 'rain-catch', interaction: 'drag',
    narration: '眼泪掉下来了，用纸巾接住它。',
    props: { hero: '😢', items: ['💧', '💧'], tool: '🧻', goal: 2 },
    templateFallback: false
  },
  {
    char: '打', unit: 'u13', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '挥挥手，把小球打出去。',
    props: { hero: '🏓', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '玩', unit: 'u13', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '挑一样玩具，玩得开开心心。',
    props: { hero: '🧸', items: ['⚽', '🪀', '🧩'], goal: 3 },
    templateFallback: false
  },
  // u14
  {
    char: '桌', unit: 'u14', theme: 'object',
    template: 'scene-poke', interaction: 'tap',
    narration: '在桌子上摆好碗和杯子。',
    props: { hero: '🍽️', items: ['🥣', '🥛', '🥢'], goal: 3 },
    templateFallback: false
  },
  {
    char: '椅', unit: 'u14', theme: 'object',
    template: 'drag-parts', interaction: 'drag',
    narration: '装上靠背和椅子腿，坐上去。',
    props: { hero: '🪑', parts: ['🪑', '🦵', '🦵'], goal: 3 },
    templateFallback: false
  },
  {
    char: '床', unit: 'u14', theme: 'object',
    template: 'tap-reveal', interaction: 'tap',
    narration: '铺好被子，晚安，该睡觉了。',
    props: { hero: '🛏️', items: ['🛌', '🧸', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '灯', unit: 'u14', theme: 'object',
    template: 'tap-reveal', interaction: 'tap',
    narration: '按一下开关，灯就亮了。',
    props: { hero: '💡', items: ['💡', '🔦', '🕯️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '窗', unit: 'u14', theme: 'object',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '推开窗户，风吹进来啦。',
    props: { hero: '🪟', dir: 'right', goal: 2 },
    templateFallback: false
  },
  {
    char: '衣', unit: 'u14', theme: 'object',
    template: 'sort-buckets', interaction: 'drag',
    narration: '天冷穿厚衣，天热穿薄衣。',
    props: { hero: '👕', items: [{ item: '🧥', bucket: '冷' }, { item: '🧣', bucket: '冷' }, { item: '👕', bucket: '热' }, { item: '🩳', bucket: '热' }], buckets: [{ label: '冷', emoji: '❄️' }, { label: '热', emoji: '🌞' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '鞋', unit: 'u14', theme: 'object',
    template: 'pair-match', interaction: 'drag',
    narration: '把左脚右脚的鞋配成一双。',
    props: { hero: '👟', pairs: [{ a: '👟', b: '👟' }, { a: '🥾', b: '🥾' }, { a: '👢', b: '👢' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '帽', unit: 'u14', theme: 'object',
    template: 'tap-reveal', interaction: 'tap',
    narration: '挑一顶帽子戴在头上。',
    props: { hero: '🧢', items: ['🎩', '👒', '⛑️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '碗', unit: 'u14', theme: 'object',
    template: 'count-tap', interaction: 'tap',
    narration: '摆好三只碗，一人一只。',
    props: { hero: '🥣', items: ['🥣', '🥣', '🥣'], goal: 3 },
    templateFallback: false
  },
  {
    char: '杯', unit: 'u14', theme: 'object',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '把杯子里的水喝得光光的。',
    props: { hero: '🥛', items: ['💧', '💧', '💧'], goal: 3 },
    templateFallback: false
  },
  {
    char: '伞', unit: 'u14', theme: 'object',
    template: 'rain-catch', interaction: 'drag',
    narration: '下雨了，快撑开伞挡住雨点。',
    props: { hero: '☂️', items: ['💧', '💧', '💧'], tool: '☂️', goal: 3 },
    templateFallback: false
  },
  {
    char: '房', unit: 'u14', theme: 'object',
    template: 'drag-parts', interaction: 'drag',
    narration: '盖房子：先砌墙，再放屋顶。',
    props: { hero: '🏡', parts: ['🧱', '🧱', '🔺'], goal: 3 },
    templateFallback: false
  },
  {
    char: '电', unit: 'u14', theme: 'object',
    template: 'trace-path', interaction: 'drag',
    narration: '电顺着电线跑过来，灯就亮了。',
    props: { hero: '⚡', dir: 'right', goal: 3 },
    templateFallback: false
  },
  // u15
  {
    char: '米', unit: 'u15', theme: 'food',
    template: 'count-tap', interaction: 'tap',
    narration: '一粒一粒的白米，装进小碗里。',
    props: { hero: '🍙', items: ['🍚', '🍚', '🍚'], goal: 3 },
    templateFallback: false
  },
  {
    char: '饭', unit: 'u15', theme: 'food',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '米煮成饭啦，一口一口吃干净。',
    props: { hero: '🍚', items: ['🍚', '🍚', '🍚'], goal: 3 },
    templateFallback: false
  },
  {
    char: '菜', unit: 'u15', theme: 'food',
    template: 'sort-buckets', interaction: 'drag',
    narration: '把青菜放进菜篮，别放错了。',
    props: { hero: '🥬', items: [{ item: '🥦', bucket: '是菜' }, { item: '🥕', bucket: '是菜' }, { item: '🍭', bucket: '不是菜' }, { item: '🍫', bucket: '不是菜' }], buckets: [{ label: '是菜', emoji: '🥬' }, { label: '不是菜', emoji: '🍬' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '果', unit: 'u15', theme: 'food',
    template: 'grow-tap', interaction: 'tap',
    narration: '花谢了，树上结出果子。',
    props: { hero: '🍇', stages: ['🌸', '🍏', '🍎'], goal: 3 },
    templateFallback: false
  },
  {
    char: '苹', unit: 'u15', theme: 'food',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '一堆水果里，找出红苹果。',
    props: { hero: '🍎', target: '🍎', decoys: ['🍌', '🍇', '🍐'], goal: 3 },
    templateFallback: false
  },
  {
    char: '面', unit: 'u15', theme: 'food',
    template: 'trace-path', interaction: 'drag',
    narration: '长长的面条，夹起来吸溜一口。',
    props: { hero: '🍜', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '蛋', unit: 'u15', theme: 'food',
    template: 'tap-reveal', interaction: 'tap',
    narration: '敲一敲蛋壳，看看里面是谁。',
    props: { hero: '🥚', items: ['🥚', '🥚', '🐣'], goal: 3 },
    templateFallback: false
  },
  {
    char: '奶', unit: 'u15', theme: 'food',
    template: 'pop-bubbles', interaction: 'tap',
    narration: '咕嘟咕嘟，把牛奶喝完。',
    props: { hero: '🍼', items: ['🥛', '🥛'], goal: 2 },
    templateFallback: false
  },
  {
    char: '糖', unit: 'u15', theme: 'food',
    template: 'count-tap', interaction: 'tap',
    narration: '数数糖果，不过一天只能吃一颗。',
    props: { hero: '🍬', items: ['🍬', '🍭', '🍫'], goal: 3 },
    templateFallback: false
  },
  {
    char: '茶', unit: 'u15', theme: 'food',
    template: 'grow-tap', interaction: 'tap',
    narration: '茶叶放进水里，泡出香香的茶。',
    props: { hero: '🍵', stages: ['🍃', '🫖', '🍵'], goal: 3 },
    templateFallback: false
  },
  {
    char: '肉', unit: 'u15', theme: 'food',
    template: 'sort-buckets', interaction: 'drag',
    narration: '哪些是肉？把肉放进盘子。',
    props: { hero: '🍖', items: [{ item: '🍗', bucket: '是肉' }, { item: '🥩', bucket: '是肉' }, { item: '🥕', bucket: '不是肉' }, { item: '🥦', bucket: '不是肉' }], buckets: [{ label: '是肉', emoji: '🍖' }, { label: '不是肉', emoji: '🥬' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '瓜', unit: 'u15', theme: 'food',
    template: 'drag-parts', interaction: 'drag',
    narration: '大西瓜切开，一块一块分着吃。',
    props: { hero: '🍉', parts: ['🍉', '🍉', '🍉'], goal: 3 },
    templateFallback: false
  },
  // u16
  {
    char: '这', unit: 'u16', theme: 'word',
    template: 'tap-reveal', interaction: 'tap',
    narration: '指着近处说这个，就在手边。',
    props: { hero: '👇', items: ['🧸', '🍎', '🖍️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '那', unit: 'u16', theme: 'word',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '远远的那个才是那，点远处的。',
    props: { hero: '👆', target: '🏔️', decoys: ['🧸', '🍎', '🪑'], goal: 1 },
    templateFallback: false
  },
  {
    char: '什', unit: 'u16', theme: 'word',
    template: 'tap-reveal', interaction: 'tap',
    narration: '盒子里是什么？打开问一问。',
    props: { hero: '❔', items: ['🎁', '🎁', '🎁'], goal: 3 },
    templateFallback: false
  },
  {
    char: '么', unit: 'u16', theme: 'word',
    template: 'pair-match', interaction: 'drag',
    narration: '什么、怎么、这么，把两个字配好。',
    props: { hero: '🔎', pairs: [{ a: '什', b: '么' }, { a: '怎', b: '么' }, { a: '这', b: '么' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '都', unit: 'u16', theme: 'word',
    template: 'count-tap', interaction: 'tap',
    narration: '一个都不少，全点到才算都。',
    props: { hero: '🧑‍🤝‍🧑', items: ['🧒', '🧒', '🧒', '🧒'], goal: 4 },
    templateFallback: false
  },
  {
    char: '要', unit: 'u16', theme: 'feeling',
    template: 'sort-buckets', interaction: 'drag',
    narration: '想要的放这边，不要的放那边。',
    props: { hero: '🙏', items: [{ item: '🍎', bucket: '要' }, { item: '🧸', bucket: '要' }, { item: '🗑️', bucket: '不要' }, { item: '🦟', bucket: '不要' }], buckets: [{ label: '要', emoji: '🙏' }, { label: '不要', emoji: '🙅' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '能', unit: 'u16', theme: 'feeling',
    template: 'tap-reveal', interaction: 'tap',
    narration: '试一试就知道，我能行。',
    props: { hero: '💪', items: ['🏃', '🎨', '🎵'], goal: 3 },
    templateFallback: false
  },
  {
    char: '想', unit: 'u16', theme: 'feeling',
    template: 'tap-reveal', interaction: 'tap',
    narration: '闭上眼想一想，脑袋里冒出什么。',
    props: { hero: '💭', items: ['🍦', '🏖️', '🎁'], goal: 3 },
    templateFallback: false
  },
  {
    char: '用', unit: 'u16', theme: 'action',
    template: 'pair-match', interaction: 'drag',
    narration: '每样东西都有用处，配一配。',
    props: { hero: '🛠️', pairs: [{ a: '✏️', b: '📄' }, { a: '🥄', b: '🍚' }, { a: '🔑', b: '🚪' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '做', unit: 'u16', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '动手做一做：做饭、做手工。',
    props: { hero: '🧑‍🔧', items: ['🍳', '✂️', '🔨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '给', unit: 'u16', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把礼物送到小伙伴手里。',
    props: { hero: '🎁', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '把', unit: 'u16', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '把扫帚拿过来，抓住把手。',
    props: { hero: '🧹', parts: ['🧹', '✋'], goal: 2 },
    templateFallback: false
  },
  // u17
  {
    char: '笔', unit: 'u17', theme: 'school',
    template: 'trace-path', interaction: 'drag',
    narration: '拿起铅笔，跟着线画一道。',
    props: { hero: '✏️', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '纸', unit: 'u17', theme: 'school',
    template: 'tap-reveal', interaction: 'tap',
    narration: '白白的一张纸，在上面画点什么。',
    props: { hero: '📄', items: ['🖍️', '✏️', '🖌️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '画', unit: 'u17', theme: 'school',
    template: 'color-fill', interaction: 'tap',
    narration: '画一幅画，给它涂上颜色。',
    props: { hero: '🎨', color: 'rainbow', goal: 3 },
    templateFallback: false
  },
  {
    char: '课', unit: 'u17', theme: 'school',
    template: 'scene-poke', interaction: 'tap',
    narration: '上课啦，点点课上要用的东西。',
    props: { hero: '📚', items: ['📕', '✏️', '🔔'], goal: 3 },
    templateFallback: false
  },
  {
    char: '班', unit: 'u17', theme: 'school',
    template: 'count-tap', interaction: 'tap',
    narration: '数数我们班有几个小朋友。',
    props: { hero: '🏫', items: ['🧒', '🧒', '🧒', '🧒'], goal: 4 },
    templateFallback: false
  },
  {
    char: '同', unit: 'u17', theme: 'school',
    template: 'pair-match', interaction: 'drag',
    narration: '一样的才是同，找出相同的。',
    props: { hero: '🤝', pairs: [{ a: '🍎', b: '🍎' }, { a: '📕', b: '📕' }, { a: '⚽', b: '⚽' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '朋', unit: 'u17', theme: 'school',
    template: 'drag-parts', interaction: 'drag',
    narration: '两个月字并排站，就是朋友的朋。',
    props: { hero: '🧑‍🤝‍🧑', parts: ['月', '月'], goal: 2 },
    templateFallback: false
  },
  {
    char: '友', unit: 'u17', theme: 'feeling',
    template: 'pair-match', interaction: 'drag',
    narration: '手拉着手，就成了好朋友。',
    props: { hero: '💞', pairs: [{ a: '🧒', b: '🧒' }, { a: '🐱', b: '🐶' }, { a: '👦', b: '👧' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '教', unit: 'u17', theme: 'school',
    template: 'sound-tap', interaction: 'tap',
    narration: '老师教一句，我们跟着念一句。',
    props: { hero: '👩‍🏫', sound: '跟我读', goal: 3 },
    templateFallback: false
  },
  {
    char: '室', unit: 'u17', theme: 'school',
    template: 'scene-poke', interaction: 'tap',
    narration: '教室里都有什么？点点看。',
    props: { hero: '🚪', items: ['🪑', '🖼️', '🪟'], goal: 3 },
    templateFallback: false
  },
  {
    char: '队', unit: 'u17', theme: 'school',
    template: 'drag-parts', interaction: 'drag',
    narration: '一个跟着一个，排成一条队。',
    props: { hero: '🚶', parts: ['🧒', '🧒', '🧒'], goal: 3 },
    templateFallback: false
  },
  {
    char: '讲', unit: 'u17', theme: 'school',
    template: 'sound-tap', interaction: 'tap',
    narration: '站上讲台，大声讲给大家听。',
    props: { hero: '🗣️', sound: '大家好', goal: 3 },
    templateFallback: false
  },
  {
    char: '台', unit: 'u17', theme: 'school',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把小凳子摞高，就成了小台子。',
    props: { hero: '🎤', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '板', unit: 'u17', theme: 'school',
    template: 'color-fill', interaction: 'tap',
    narration: '在黑板上写写画画，再擦干净。',
    props: { hero: '🪵', color: 'black', goal: 3 },
    templateFallback: false
  },
  {
    char: '图', unit: 'u17', theme: 'school',
    template: 'scene-poke', interaction: 'tap',
    narration: '摊开地图，点点上面画了什么。',
    props: { hero: '🗺️', items: ['⛰️', '🏞️', '🏠'], goal: 3 },
    templateFallback: false
  },
  {
    char: '数', unit: 'u17', theme: 'school',
    template: 'count-tap', interaction: 'tap',
    narration: '数一数，一共有几个。',
    props: { hero: '🔢', items: ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣'], goal: 5 },
    templateFallback: false
  },
  {
    char: '语', unit: 'u17', theme: 'school',
    template: 'sound-tap', interaction: 'tap',
    narration: '说一句话，说出来的就是语。',
    props: { hero: '💬', sound: '你好呀', goal: 3 },
    templateFallback: false
  },
  {
    char: '文', unit: 'u17', theme: 'school',
    template: 'word-build', interaction: 'drag',
    narration: '把字连起来，就成了一篇文。',
    props: { hero: '📝', parts: ['语', '文'], word: '语文', goal: 2 },
    templateFallback: false
  },
  // u18
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
  // u19
  {
    char: '爸', unit: 'u19', theme: 'family',
    template: 'tap-reveal', interaction: 'tap',
    narration: '爸爸举高高，点点他在做什么。',
    props: { hero: '👨', items: ['🤾', '🍳', '🚗'], goal: 3 },
    templateFallback: false
  },
  {
    char: '妈', unit: 'u19', theme: 'family',
    template: 'tap-reveal', interaction: 'tap',
    narration: '妈妈抱一抱，暖暖的。',
    props: { hero: '👩', items: ['🤱', '🍲', '❤️'], goal: 3 },
    templateFallback: false
  },
  {
    char: '弟', unit: 'u19', theme: 'family',
    template: 'sort-buckets', interaction: 'drag',
    narration: '弟弟比我小，放到小的那边。',
    props: { hero: '👦', items: [{ item: '🧔', bucket: '大' }, { item: '👨', bucket: '大' }, { item: '👦', bucket: '小' }, { item: '👶', bucket: '小' }], buckets: [{ label: '大', emoji: '🔼' }, { label: '小', emoji: '🔽' }], goal: 4 },
    templateFallback: false
  },
  {
    char: '爷', unit: 'u19', theme: 'family',
    template: 'pair-match', interaction: 'drag',
    narration: '爷爷是爸爸的爸爸，连一连。',
    props: { hero: '👴', pairs: [{ a: '👴', b: '👨' }, { a: '👵', b: '👩' }], goal: 2 },
    templateFallback: false
  },
  {
    char: '叔', unit: 'u19', theme: 'family',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '叔叔是爸爸的弟弟，找出叔叔。',
    props: { hero: '🧔', target: '🧔', decoys: ['👴', '👦', '👶'], goal: 1 },
    templateFallback: false
  },
  {
    char: '姑', unit: 'u19', theme: 'family',
    template: 'pair-match', interaction: 'drag',
    narration: '姑姑是爸爸的姐妹，配一配。',
    props: { hero: '👩‍🦰', pairs: [{ a: '👨', b: '👩‍🦰' }, { a: '👩', b: '🧑‍🦱' }], goal: 2 },
    templateFallback: false
  },
  {
    char: '姨', unit: 'u19', theme: 'family',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '阿姨是妈妈的姐妹，点出阿姨。',
    props: { hero: '🧑‍🦱', target: '🧑‍🦱', decoys: ['👴', '👦', '🧒'], goal: 1 },
    templateFallback: false
  },
  {
    char: '亲', unit: 'u19', theme: 'feeling',
    template: 'tap-reveal', interaction: 'tap',
    narration: '亲一亲抱一抱，最亲的人在身边。',
    props: { hero: '🤗', items: ['❤️', '💞', '💗'], goal: 3 },
    templateFallback: false
  },
  {
    char: '客', unit: 'u19', theme: 'family',
    template: 'scene-poke', interaction: 'tap',
    narration: '客人来啦，请他喝茶、坐下。',
    props: { hero: '🛎️', items: ['🍵', '🪑', '🍪'], goal: 3 },
    templateFallback: false
  },
  {
    char: '伴', unit: 'u19', theme: 'family',
    template: 'pair-match', interaction: 'drag',
    narration: '好伙伴要两个人，配成一对。',
    props: { hero: '👯', pairs: [{ a: '🧒', b: '🧒' }, { a: '👦', b: '👧' }, { a: '👯', b: '👯' }], goal: 3 },
    templateFallback: false
  },
  {
    char: '伙', unit: 'u19', theme: 'family',
    template: 'count-tap', interaction: 'tap',
    narration: '一群小伙伴，数数一共几个。',
    props: { hero: '🧑‍🤝‍🧑', items: ['🧒', '🧒', '🧒', '🧒'], goal: 4 },
    templateFallback: false
  },
  {
    char: '邻', unit: 'u19', theme: 'family',
    template: 'scene-poke', interaction: 'tap',
    narration: '隔壁邻居家，去打个招呼。',
    props: { hero: '🏘️', items: ['🚪', '🔔', '👋'], goal: 3 },
    templateFallback: false
  },
  {
    char: '众', unit: 'u19', theme: 'family',
    template: 'count-tap', interaction: 'tap',
    narration: '三个人叠在一起，人多就是众。',
    props: { hero: '👥', items: ['🧍', '🧍', '🧍'], goal: 3 },
    templateFallback: false
  },
  {
    char: '婆', unit: 'u19', theme: 'family',
    template: 'pair-match', interaction: 'drag',
    narration: '外婆是妈妈的妈妈，连一连。',
    props: { hero: '👵', pairs: [{ a: '👵', b: '👩' }, { a: '👴', b: '👨' }], goal: 2 },
    templateFallback: false
  },
  {
    char: '孙', unit: 'u19', theme: 'family',
    template: 'grow-tap', interaction: 'tap',
    narration: '小孙子一点点长大。',
    props: { hero: '🧒', stages: ['👶', '🧒', '👦'], goal: 3 },
    templateFallback: false
  },
  {
    char: '娃', unit: 'u19', theme: 'family',
    template: 'tap-reveal', interaction: 'tap',
    narration: '小娃娃睡着了，轻轻拍一拍。',
    props: { hero: '👶', items: ['🍼', '🧸', '🌙'], goal: 3 },
    templateFallback: false
  },
  {
    char: '姓', unit: 'u19', theme: 'word',
    template: 'word-build', interaction: 'drag',
    narration: '每个人都有姓，姓在名字前面。',
    props: { hero: '🏷️', parts: ['姓', '名'], word: '姓名', goal: 2 },
    templateFallback: false
  },
  {
    char: '名', unit: 'u19', theme: 'word',
    template: 'word-build', interaction: 'drag',
    narration: '写下自己的名字，念一念。',
    props: { hero: '📛', parts: ['名', '字'], word: '名字', goal: 2 },
    templateFallback: false
  },
  // u20
  {
    char: '拉', unit: 'u20', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '使劲往自己这边拉。',
    props: { hero: '🤝', dir: 'left', goal: 3 },
    templateFallback: false
  },
  {
    char: '推', unit: 'u20', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '双手往前推，小车动起来。',
    props: { hero: '🛒', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '提', unit: 'u20', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '用手拎起水桶，往上提。',
    props: { hero: '🧺', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '抱', unit: 'u20', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '张开两只手，把小熊抱住。',
    props: { hero: '🤱', parts: ['🧸', '✋', '✋'], goal: 3 },
    templateFallback: false
  },
  {
    char: '洗', unit: 'u20', theme: 'action',
    template: 'scene-poke', interaction: 'tap',
    narration: '打开水龙头，把小手洗干净。',
    props: { hero: '🧼', items: ['🚿', '🧴', '🤲'], goal: 3 },
    templateFallback: false
  },
  {
    char: '扫', unit: 'u20', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '拿起扫把，把地上的土扫走。',
    props: { hero: '🧹', dir: 'right', goal: 4 },
    templateFallback: false
  },
  {
    char: '拍', unit: 'u20', theme: 'action',
    template: 'sound-tap', interaction: 'tap',
    narration: '拍拍手，啪啪啪。',
    props: { hero: '👏', sound: '啪', goal: 3 },
    templateFallback: false
  },
  {
    char: '摸', unit: 'u20', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '闭上眼摸一摸，猜猜是什么。',
    props: { hero: '🖐️', items: ['🧸', '🐱', '🪨'], goal: 3 },
    templateFallback: false
  },
  {
    char: '找', unit: 'u20', theme: 'action',
    template: 'emoji-hunt', interaction: 'tap',
    narration: '钥匙不见了，快把它找出来。',
    props: { hero: '🔍', target: '🔑', decoys: ['🧦', '📕', '🧸'], goal: 1 },
    templateFallback: false
  },
  {
    char: '抓', unit: 'u20', theme: 'action',
    template: 'tap-reveal', interaction: 'tap',
    narration: '一把抓住气球，别让它飞走。',
    props: { hero: '🫳', items: ['🎈', '🎈', '🎈'], goal: 3 },
    templateFallback: false
  },
  {
    char: '放', unit: 'u20', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '轻轻把东西放下来。',
    props: { hero: '🫴', dir: 'down', goal: 3 },
    templateFallback: false
  },
  {
    char: '开', unit: 'u20', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把门打开，请进。',
    props: { hero: '🔓', dir: 'right', goal: 2 },
    templateFallback: false
  },
  {
    char: '关', unit: 'u20', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '出门记得把门关上。',
    props: { hero: '🔒', dir: 'left', goal: 2 },
    templateFallback: false
  },
  {
    char: '送', unit: 'u20', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把礼物送给好朋友。',
    props: { hero: '🎁', dir: 'right', goal: 3 },
    templateFallback: false
  },
  {
    char: '收', unit: 'u20', theme: 'action',
    template: 'drag-parts', interaction: 'drag',
    narration: '玩具玩完了，一件件收回箱子。',
    props: { hero: '📦', parts: ['🧸', '🪀', '🧩'], goal: 3 },
    templateFallback: false
  },
  {
    char: '挂', unit: 'u20', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '把画往上挂到墙上。',
    props: { hero: '🖼️', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '举', unit: 'u20', theme: 'action',
    template: 'swipe-motion', interaction: 'swipe',
    narration: '会回答的小朋友，把手高高举起。',
    props: { hero: '🙋', dir: 'up', goal: 3 },
    templateFallback: false
  },
  {
    char: '摆', unit: 'u20', theme: 'action',
    template: 'sort-buckets', interaction: 'drag',
    narration: '把碗筷一样一样摆整齐。',
    props: { hero: '🪑', items: [{ item: '🥣', bucket: '桌上' }, { item: '🥢', bucket: '桌上' }, { item: '🫖', bucket: '柜里' }, { item: '🍶', bucket: '柜里' }], buckets: [{ label: '桌上', emoji: '🍽️' }, { label: '柜里', emoji: '🗄️' }], goal: 4 },
    templateFallback: false
  },
]

/** 字 → 富脚本。 */
export const RICH_PLAY_BY_CHAR = new Map(CHAR_PLAY_RICH.map((p) => [p.char, p]))

/** 这个字有没有手写剧本；没有就交给 char-play.js 的模板补齐。 */
export function getRichPlay(char) {
  return RICH_PLAY_BY_CHAR.get(char) ?? null
}

/** 手写剧本条数（Round 15 H3 数的就是它）。 */
export function countRichPlays() {
  return CHAR_PLAY_RICH.length
}

/** 手写覆盖到的单元。 */
export const RICH_PLAY_UNITS = ['u1', 'u2', 'u3', 'u4', 'u5', 'u6', 'u7', 'u8', 'u9', 'u10', 'u11', 'u12', 'u13', 'u14', 'u15', 'u16', 'u17', 'u18', 'u19', 'u20']
