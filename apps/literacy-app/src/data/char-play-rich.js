/**
 * 手写的「玩」脚本（ROUND15_H2 的富脚本层）。
 *
 * 模板补齐能保证每个字都有得玩，但补出来的关卡只知道这个字属于哪个单元、
 * 带什么偏旁；「日」该看着太阳变成方框、「水」该接住落下来的水滴这种事，
 * 得人来写。这份表就是人写的那一层，条目越多，孩子遇到模板关的概率越低。
 *
 * 写一条的最小成本是三个字段：
 *
 *   { char: '日', template: 'morph-story', narration: '看：☀️ 慢慢变成了「日」。' }
 *
 * 道具（props）能不写就不写：char-play.js 会先按模板把整套道具生成好，
 * 这里写了哪一件就换哪一件，没写的照旧。所以补一条脚本永远不会把舞台写空。
 *
 * 模板 id 见 char-play.js 的 PLAY_TEMPLATES；写了舞台不认识的模板会被退回
 * 「点一点」，不会报错，但也就白写了。
 */

export const RICH_PLAYS = [
  /* ---------------------------------------------------------- u1 我和数字 */
  {
    char: '一',
    theme: 'number',
    template: 'morph-story',
    narration: '伸出一根手指，把它放平——就是「一」。',
    props: {
      frames: [
        { id: 'f0', emoji: '☝️', caption: '伸出一根手指' },
        { id: 'f1', emoji: '➖', caption: '把手指放平' },
        { id: 'f2', glyph: '一', caption: '这就是「一」' }
      ]
    }
  },
  {
    char: '二',
    theme: 'number',
    template: 'tap-reveal',
    narration: '点开盖子，数一数：一共有几样东西？两样，就写「二」。',
    props: {
      items: [
        { id: 'p0', emoji: '✌️', label: '两根手指', isChar: true },
        { id: 'p1', emoji: '👟', label: '两只鞋子' },
        { id: 'p2', emoji: '👀', label: '两只眼睛' }
      ],
      prompt: '点开 3 个盖子，每样都是两个'
    }
  },
  {
    char: '三',
    theme: 'number',
    template: 'emoji-hunt',
    narration: '找出 3 只小手，「三」就是三根横。',
    props: { need: 3 }
  },
  {
    char: '上',
    theme: 'number',
    template: 'tap-reveal',
    narration: '哪些东西在上面？点开看看，往上就写「上」。',
    props: {
      items: [
        { id: 'p0', emoji: '⬆️', label: '往上', isChar: true },
        { id: 'p1', emoji: '🪁', label: '风筝飞上天' },
        { id: 'p2', emoji: '🌞', label: '太阳挂在上面' }
      ],
      prompt: '点开 3 个盖子，都在上面'
    }
  },
  {
    char: '下',
    theme: 'number',
    template: 'tap-reveal',
    narration: '哪些东西在下面？点开看看，往下就写「下」。',
    props: {
      items: [
        { id: 'p0', emoji: '⬇️', label: '往下', isChar: true },
        { id: 'p1', emoji: '🍎', label: '苹果掉下来' },
        { id: 'p2', emoji: '🦶', label: '脚在最下面' }
      ],
      prompt: '点开 3 个盖子，都在下面'
    }
  },
  {
    char: '人',
    theme: 'family',
    template: 'morph-story',
    narration: '一个人站着，迈开两条腿走路——就是「人」。',
    props: {
      frames: [
        { id: 'f0', emoji: '🧍', caption: '有个人站在这儿' },
        { id: 'f1', emoji: '🚶', caption: '他迈开两条腿' },
        { id: 'f2', glyph: '人', caption: '两条腿，就是「人」' }
      ]
    }
  },
  {
    char: '口',
    theme: 'body',
    template: 'tap-reveal',
    narration: '嘴巴能做什么？点开三个盖子试试，「口」就是张开的嘴。',
    props: {
      items: [
        { id: 'p0', emoji: '👄', label: '张开的嘴', isChar: true },
        { id: 'p1', emoji: '🍚', label: '吃饭' },
        { id: 'p2', emoji: '🗣️', label: '说话' }
      ],
      prompt: '点开 3 个盖子'
    }
  },
  {
    char: '大',
    theme: 'body',
    template: 'morph-story',
    narration: '张开两只手，叉开两条腿，「大」就是一个人张得大大的。',
    props: {
      frames: [
        { id: 'f0', emoji: '🧍', caption: '一个人站着' },
        { id: 'f1', emoji: '🙆', caption: '他把手张开' },
        { id: 'f2', glyph: '大', caption: '张得大大的，就是「大」' }
      ]
    }
  },
  {
    char: '小',
    theme: 'animal',
    template: 'emoji-hunt',
    narration: '找出 3 只刚出壳的小鸡，小小的东西就写「小」。',
    props: { need: 3 }
  },

  /* ------------------------------------------------------------ u2 大自然 */
  {
    char: '日',
    theme: 'weather',
    template: 'morph-story',
    narration: '太阳圆圆的，古人把它画方了一点，中间点一横——就是「日」。',
    props: {
      frames: [
        { id: 'f0', emoji: '☀️', caption: '天上的太阳' },
        { id: 'f1', emoji: '🟠', caption: '把它画下来' },
        { id: 'f2', glyph: '日', caption: '方一点，就是「日」' }
      ]
    }
  },
  {
    char: '月',
    theme: 'weather',
    template: 'morph-story',
    narration: '月亮弯弯的，把弯月立起来，就是「月」。',
    props: {
      frames: [
        { id: 'f0', emoji: '🌙', caption: '弯弯的月亮' },
        { id: 'f1', emoji: '🌜', caption: '把它立起来' },
        { id: 'f2', glyph: '月', caption: '这就是「月」' }
      ]
    }
  },
  {
    char: '山',
    theme: 'nature',
    template: 'morph-story',
    narration: '三座山尖排在一起，就是「山」。',
    props: {
      frames: [
        { id: 'f0', emoji: '⛰️', caption: '远处的大山' },
        { id: 'f1', emoji: '🏔️', caption: '三个山尖' },
        { id: 'f2', glyph: '山', caption: '排一排，就是「山」' }
      ]
    }
  },
  {
    char: '水',
    theme: 'water',
    template: 'rain-catch',
    narration: '水滴落下来啦，接住 3 滴，「水」就跟你走。',
    props: { need: 3 }
  },
  {
    char: '火',
    theme: 'nature',
    template: 'tap-reveal',
    narration: '火能干什么？点开三个盖子看看，「火」是跳动的火苗。',
    props: {
      items: [
        { id: 'p0', emoji: '🔥', label: '跳动的火苗', isChar: true },
        { id: 'p1', emoji: '🍲', label: '煮汤' },
        { id: 'p2', emoji: '🕯️', label: '点亮蜡烛' }
      ],
      prompt: '点开 3 个盖子'
    }
  },
  {
    char: '土',
    theme: 'nature',
    template: 'tap-reveal',
    narration: '泥土里能长出什么？点开看看，「土」就是地面上一小堆泥。',
    props: {
      items: [
        { id: 'p0', emoji: '🟤', label: '一堆泥土', isChar: true },
        { id: 'p1', emoji: '🌱', label: '小苗钻出来' },
        { id: 'p2', emoji: '🥕', label: '土里的胡萝卜' }
      ],
      prompt: '点开 3 个盖子'
    }
  },
  {
    char: '天',
    theme: 'weather',
    template: 'rain-catch',
    narration: '天上飘下来好多云，接住 3 朵，就认识「天」。',
    props: { need: 3 }
  },
  {
    char: '云',
    theme: 'weather',
    template: 'emoji-hunt',
    narration: '找出 3 朵云，「云」在天上飘来飘去。',
    props: { need: 3 }
  },
  {
    char: '雨',
    theme: 'weather',
    template: 'rain-catch',
    narration: '下雨啦！接住 3 颗雨点，「雨」字里正好有四点。',
    props: { need: 3 }
  },
  {
    char: '风',
    theme: 'weather',
    template: 'emoji-hunt',
    narration: '风一吹，叶子就飞。找出 3 片被吹跑的叶子。',
    props: { need: 3 }
  },
  {
    char: '木',
    theme: 'nature',
    template: 'morph-story',
    narration: '一棵树有树干、有树枝、有树根，画下来就是「木」。',
    props: {
      frames: [
        { id: 'f0', emoji: '🌳', caption: '一棵大树' },
        { id: 'f1', emoji: '🌲', caption: '看它的树干和树枝' },
        { id: 'f2', glyph: '木', caption: '画下来，就是「木」' }
      ]
    }
  },
  {
    char: '石',
    theme: 'nature',
    template: 'emoji-hunt',
    narration: '山脚下滚下来好多石头，找出 3 块。',
    props: { need: 3 }
  },
  {
    char: '花',
    theme: 'nature',
    template: 'emoji-hunt',
    narration: '花园里开了好多花，找出 3 朵一样的。',
    props: { need: 3 }
  },

  /* -------------------------------------------------------- u3 身体和动物 */
  {
    char: '手',
    theme: 'body',
    template: 'tap-reveal',
    narration: '手能做的事可多啦，点开三个盖子看看。',
    props: {
      items: [
        { id: 'p0', emoji: '🖐️', label: '五根手指', isChar: true },
        { id: 'p1', emoji: '👏', label: '拍手' },
        { id: 'p2', emoji: '🤝', label: '握握手' }
      ],
      prompt: '点开 3 个盖子'
    }
  },
  {
    char: '目',
    theme: 'body',
    template: 'tap-reveal',
    narration: '「目」就是眼睛。点开盖子，看看眼睛能看到什么。',
    props: {
      items: [
        { id: 'p0', emoji: '👀', label: '一双眼睛', isChar: true },
        { id: 'p1', emoji: '🌈', label: '看见彩虹' },
        { id: 'p2', emoji: '📖', label: '看书' }
      ],
      prompt: '点开 3 个盖子'
    }
  },
  {
    char: '耳',
    theme: 'body',
    template: 'tap-reveal',
    narration: '耳朵能听见什么？点开三个盖子听听看。',
    props: {
      items: [
        { id: 'p0', emoji: '👂', label: '一只耳朵', isChar: true },
        { id: 'p1', emoji: '🎵', label: '听音乐' },
        { id: 'p2', emoji: '🐦', label: '听鸟叫' }
      ],
      prompt: '点开 3 个盖子'
    }
  },
  {
    char: '心',
    theme: 'feeling',
    template: 'tap-reveal',
    narration: '心里会有各种感觉，点开三个盖子看看。',
    props: {
      items: [
        { id: 'p0', emoji: '❤️', label: '心', isChar: true },
        { id: 'p1', emoji: '😊', label: '开心' },
        { id: 'p2', emoji: '🤗', label: '喜欢' }
      ],
      prompt: '点开 3 个盖子'
    }
  },
  {
    char: '鸟',
    theme: 'animal',
    template: 'emoji-hunt',
    narration: '树林里飞来好多小鸟，找出 3 只。',
    props: { need: 3 }
  },
  {
    char: '鱼',
    theme: 'water',
    template: 'rain-catch',
    narration: '小鱼从水里跳出来，接住 3 条就认识「鱼」。',
    props: { need: 3 }
  }
]

export default RICH_PLAYS
