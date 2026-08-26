/**
 * 成语启蒙语料。
 *
 * 每条成语都配一个「三段式」小故事（起因 / 经过 / 道理），
 * 这是给 5-8 岁孩子讲成语最容易听懂的结构。
 *
 * 字段：
 *   id        路由与进度记录用的稳定 id
 *   word      成语本体（四字）
 *   pinyin    整条拼音
 *   chars     逐字拆解，每字含拼音与「在这条成语里」的意思
 *   emoji     卡片图标
 *   palette   卡片渐变色（两个色值）
 *   meaning   一句话释义
 *   lesson    这条成语教我们什么
 *   story     故事三段
 *   quiz      情景选择题，answer 为 options 下标
 *
 * 注意：成语用字大多超出 characters.js 的 40 个字表，
 * 所以成语页只做「认读 + 听故事」，不要求书写掌握。
 */

export const IDIOMS = [
  {
    id: 'wybl',
    word: '亡羊补牢',
    pinyin: 'wáng yáng bǔ láo',
    emoji: '🐑',
    palette: ['#ffe6b3', '#ffd0d6'],
    meaning: '羊跑丢了才去修羊圈，现在动手还来得及。',
    lesson: '做错事不可怕，发现了马上改正，就不会错第二次。',
    chars: [
      { c: '亡', p: 'wáng', m: '丢了、不见了' },
      { c: '羊', p: 'yáng', m: '小羊' },
      { c: '补', p: 'bǔ', m: '修一修' },
      { c: '牢', p: 'láo', m: '关羊的圈' }
    ],
    story: [
      { emoji: '🕳️', text: '牧羊人的羊圈破了一个洞，夜里跑丢了一只羊。' },
      { emoji: '🙈', text: '邻居劝他快补上，他说「羊都丢了，补它做什么」，结果第二天又丢了一只。' },
      { emoji: '🔨', text: '他这才拿起木头把洞补好。从那以后，羊再也没有丢过。' }
    ],
    quiz: {
      q: '你把水杯打翻了，弄湿了桌子。这时候最好怎么做？',
      options: ['假装没看见走开', '马上擦干净，再把杯子放稳', '把杯子藏起来'],
      answer: 1,
      tip: '发现问题就动手补救，这就是「亡羊补牢」。'
    }
  },
  {
    id: 'szdt',
    word: '守株待兔',
    pinyin: 'shǒu zhū dài tù',
    emoji: '🐰',
    palette: ['#d9f6f3', '#e8e0ff'],
    meaning: '守着一棵树，等兔子自己撞上来。',
    lesson: '好运气不会天天有，想要收获还得自己动手。',
    chars: [
      { c: '守', p: 'shǒu', m: '守着不走' },
      { c: '株', p: 'zhū', m: '树桩子' },
      { c: '待', p: 'dài', m: '等待' },
      { c: '兔', p: 'tù', m: '兔子' }
    ],
    story: [
      { emoji: '🌳', text: '一个农夫在田里干活，忽然看见一只兔子撞到树桩上晕了过去。' },
      { emoji: '🍲', text: '他捡起兔子高高兴兴回家做了汤，心想：天天来这儿等就好啦！' },
      { emoji: '🌾', text: '从此他丢下锄头天天守在树桩边，兔子再没来，田里的苗全枯了。' }
    ],
    quiz: {
      q: '想让积木搭得又高又稳，应该怎么做？',
      options: ['坐着等它自己变高', '一块一块耐心往上搭', '许个愿就好了'],
      answer: 1,
      tip: '靠自己一步步做，比空等有用得多。'
    }
  },
  {
    id: 'hstz',
    word: '画蛇添足',
    pinyin: 'huà shé tiān zú',
    emoji: '🐍',
    palette: ['#dff5d8', '#fff1cf'],
    meaning: '给画好的蛇添上脚，反而画坏了。',
    lesson: '做得刚刚好就停下，多此一举反而办砸了事。',
    chars: [
      { c: '画', p: 'huà', m: '画画' },
      { c: '蛇', p: 'shé', m: '小蛇' },
      { c: '添', p: 'tiān', m: '多加上' },
      { c: '足', p: 'zú', m: '脚' }
    ],
    story: [
      { emoji: '🖌️', text: '几个人比赛画蛇，说好谁先画完谁就得到那壶酒。' },
      { emoji: '🦶', text: '有个人最先画好，看别人还没完，就得意地给蛇添了四只脚。' },
      { emoji: '🍶', text: '第二个人画完了，一把拿走酒说：蛇本来就没有脚，你画的不是蛇！' }
    ],
    quiz: {
      q: '一幅画已经很漂亮了，你最好——',
      options: ['再乱涂几笔显得热闹', '就这样收笔，保护好它', '全部涂黑重来'],
      answer: 1,
      tip: '恰到好处地停下来，也是一种本事。'
    }
  },
  {
    id: 'jdzw',
    word: '井底之蛙',
    pinyin: 'jǐng dǐ zhī wā',
    emoji: '🐸',
    palette: ['#c8ebff', '#d9f6f3'],
    meaning: '住在井底的青蛙，以为天空只有井口那么大。',
    lesson: '多出去看看世界，眼界才会越来越宽。',
    chars: [
      { c: '井', p: 'jǐng', m: '水井' },
      { c: '底', p: 'dǐ', m: '最下面' },
      { c: '之', p: 'zhī', m: '的' },
      { c: '蛙', p: 'wā', m: '青蛙' }
    ],
    story: [
      { emoji: '🕳️', text: '一只青蛙从小住在井里，它抬头一看，天空就是圆圆的一小块。' },
      { emoji: '🐢', text: '海龟路过，告诉它大海一眼望不到边，走上十天也走不完。' },
      { emoji: '🌊', text: '青蛙愣住了——原来自己看到的「整个天」，只是井口那么大。' }
    ],
    quiz: {
      q: '想知道世界有多大，最好的办法是——',
      options: ['一直待在房间里想象', '多读书、多出去看一看', '不用知道'],
      answer: 1,
      tip: '走出井口，天空就大起来了。'
    }
  },
  {
    id: 'bmzz',
    word: '拔苗助长',
    pinyin: 'bá miáo zhù zhǎng',
    emoji: '🌱',
    palette: ['#e6f5c9', '#ffe6b3'],
    meaning: '把禾苗往上拔，想帮它快点长高。',
    lesson: '什么事都有自己的节奏，太着急反而会坏事。',
    chars: [
      { c: '拔', p: 'bá', m: '往上拉' },
      { c: '苗', p: 'miáo', m: '小禾苗' },
      { c: '助', p: 'zhù', m: '帮忙' },
      { c: '长', p: 'zhǎng', m: '长高' }
    ],
    story: [
      { emoji: '😤', text: '有个农夫嫌田里的禾苗长得太慢，急得团团转。' },
      { emoji: '🤲', text: '他想出一个「好办法」：把每一棵苗都往上拔高一截。' },
      { emoji: '🥀', text: '忙了一整天，回家还很得意。第二天再看，禾苗全都枯死了。' }
    ],
    quiz: {
      q: '种下的小花今天还没开，你应该——',
      options: ['用手把花瓣掰开', '每天浇水，耐心等它开', '把它拔出来看看根'],
      answer: 1,
      tip: '给它时间，花自己会开。'
    }
  },
  {
    id: 'yedl',
    word: '掩耳盗铃',
    pinyin: 'yǎn ěr dào líng',
    emoji: '🔔',
    palette: ['#ffd9e8', '#e8e0ff'],
    meaning: '捂住自己的耳朵去偷铃铛，以为别人也听不见。',
    lesson: '骗得了自己，骗不了别人；做事要诚实。',
    chars: [
      { c: '掩', p: 'yǎn', m: '捂住' },
      { c: '耳', p: 'ěr', m: '耳朵' },
      { c: '盗', p: 'dào', m: '偷' },
      { c: '铃', p: 'líng', m: '铃铛' }
    ],
    story: [
      { emoji: '🔔', text: '有个人看上了别人家门上的大铃铛，想把它摘走。' },
      { emoji: '🙉', text: '他怕铃声被人听见，就先把自己的耳朵紧紧捂住，才伸手去摘。' },
      { emoji: '👮', text: '「当啷——」铃声传出老远，他自己听不见，别人可全听见了。' }
    ],
    quiz: {
      q: '不小心弄坏了同学的橡皮，怎么做才对？',
      options: ['塞进书包当没发生', '主动说对不起，想办法补上', '怪别人放得不好'],
      answer: 1,
      tip: '捂住耳朵不等于事情没发生，诚实才最勇敢。'
    }
  },
  {
    id: 'hjhw',
    word: '狐假虎威',
    pinyin: 'hú jiǎ hǔ wēi',
    emoji: '🦊',
    palette: ['#ffe0c2', '#ffd0d6'],
    meaning: '狐狸借着老虎的威风，把别的动物吓跑了。',
    lesson: '真正让人佩服的是自己的本事，不是借来的架势。',
    chars: [
      { c: '狐', p: 'hú', m: '狐狸' },
      { c: '假', p: 'jiǎ', m: '借用' },
      { c: '虎', p: 'hǔ', m: '老虎' },
      { c: '威', p: 'wēi', m: '威风' }
    ],
    story: [
      { emoji: '🐯', text: '老虎抓住了一只狐狸，正要吃掉它。' },
      { emoji: '🦊', text: '狐狸眼珠一转：我可是森林之王，不信你跟我走一趟！' },
      { emoji: '🏃', text: '动物们看见后面的老虎，吓得四散逃开。老虎却以为，大家怕的是狐狸。' }
    ],
    quiz: {
      q: '想让小伙伴佩服你，最好的办法是——',
      options: ['搬出厉害的人来吓唬他们', '把自己会的本领练得更好', '大声说话'],
      answer: 1,
      tip: '借来的威风会还回去，自己的本事才留得住。'
    }
  },
  {
    id: 'kzqj',
    word: '刻舟求剑',
    pinyin: 'kè zhōu qiú jiàn',
    emoji: '⛵',
    palette: ['#c8ebff', '#e6e6fa'],
    meaning: '剑掉进河里，却在船边刻个记号，等靠岸再去找。',
    lesson: '情况已经变了，办法也要跟着变。',
    chars: [
      { c: '刻', p: 'kè', m: '刻记号' },
      { c: '舟', p: 'zhōu', m: '小船' },
      { c: '求', p: 'qiú', m: '寻找' },
      { c: '剑', p: 'jiàn', m: '宝剑' }
    ],
    story: [
      { emoji: '🗡️', text: '一个人坐船过河，不小心把宝剑掉进了水里。' },
      { emoji: '🪚', text: '他不慌不忙，在船边掉剑的地方刻了一个记号。' },
      { emoji: '💦', text: '船靠了岸，他顺着记号跳下水去找——船早就走远啦，剑还在河中间呢。' }
    ],
    quiz: {
      q: '昨天走的那条小路今天在修，你应该——',
      options: ['还是硬走那条路', '换一条能走通的路', '干脆不去了'],
      answer: 1,
      tip: '路变了，走法也要变。'
    }
  }
]

export const IDIOM_MAP = new Map(IDIOMS.map((i) => [i.id, i]))

export function getIdiom(id) {
  return IDIOM_MAP.get(id) || null
}

/** 成语中出现的全部汉字（去重），供离线笔顺数据生成脚本使用。 */
export function idiomChars() {
  const set = new Set()
  for (const idiom of IDIOMS) {
    for (const ch of idiom.word) set.add(ch)
  }
  return [...set]
}

export const TOTAL_IDIOMS = IDIOMS.length
