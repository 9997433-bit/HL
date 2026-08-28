/**
 * 生活行星应用题母题库。
 * 每个母题都是一个生成器：调用 make() 会随机出一道数值不同、结构相同的新题，
 * 因此几十个母题可以覆盖成千上万道不重复的练习。
 *
 * 母题分两层来源：
 *   1. CRAFTED —— 手写母题，题面各有各的说法（鸡兔同笼、相遇、植树、找零……），
 *      这类结构没法套模板，只能一道道写。
 *   2. SEMANTIC_TEMPLATES × SCENE_SKINS —— 语义模板负责数学结构（合并 / 剩余 /
 *      和倍 / 进一法……），场景皮肤只负责「在哪里、数的是什么」。两者做笛卡尔积，
 *      一个新语义或一张新皮肤就能整排地扩出母题，题面又不会读起来像同一道。
 *      所以扩容是「加一行语义 / 加一张皮肤」，而不是一道一道往下抄。
 *
 * steps 与 tier 是两件事，从 Round 18 起分开写（ROUND18_H4）：
 *   steps 是**字面上要算几步**，必须和 buildAnalysis() 从 equation 拆出的步数逐题对得上。
 *         对不上就说明剖析面板讲的步数和母题自己声称的不一样，孩子先信哪个都是错的。
 *   tier  是**难度档**，只有 'one' / 'two' / 'multi' 三挡，界面按它分难度、给星星、发 XP。
 *         不写就按 steps 推（1→one，2→two，>=3→multi）；和差倍、相遇这类
 *         「算式只有两步、但要先想明白怎么转换」的题型写明 tier: 'multi' 顶上去，
 *         反过来平均数算式上是三步、想法上仍是「先合起来再平分」两步，写 tier: 'two'。
 * 参数域都做过约束，保证答案是正整数，不会出现负数或小数。
 *
 * 随机数一律走 @/utils/random 的种子化 mulberry32 流：reseed(seed) 之后
 * 整个题库的产出逐字可复现，家长报告里的错题才回放得出来。
 */
import { randInt, sample } from '@/utils/random'

const NAMES = ['小星', '乐乐', '朵朵', '阿光', '妮妮', '小舟', '大熊', '果果']

const pair = () => {
  const a = sample(NAMES)
  let b = sample(NAMES)
  while (b === a) b = sample(NAMES)
  return [a, b]
}

/** 手写母题：题面结构独一份，套不进语义模板。 */
const CRAFTED = [
  {
    id: 'add-join',
    skill: 'wp-combine',
    tag: '合并',
    steps: 1,
    emoji: '🍎',
    scene: '果园',
    make() {
      const [a] = pair()
      const x = randInt(3, 12)
      const y = randInt(2, 10)
      return {
        text: `${a}上午摘了 ${x} 个苹果，下午又摘了 ${y} 个。${a}一共摘了多少个苹果？`,
        equation: `${x} + ${y} = ?`,
        answer: x + y,
        unit: '个',
        hint: '「一共」就是把两次的数量加起来。',
        visual: { icon: '🍎', groups: [x, y] },
      }
    },
  },
  {
    id: 'sub-left',
    skill: 'wp-remain',
    tag: '剩余',
    steps: 1,
    emoji: '🍪',
    scene: '厨房',
    make() {
      const total = randInt(8, 20)
      const eaten = randInt(2, total - 2)
      const [a] = pair()
      return {
        text: `盘子里原来有 ${total} 块饼干，${a}吃掉了 ${eaten} 块。盘子里还剩多少块？`,
        equation: `${total} − ${eaten} = ?`,
        answer: total - eaten,
        unit: '块',
        hint: '「还剩」要用减法：原来的减去吃掉的。',
        visual: { icon: '🍪', groups: [total], strike: eaten },
      }
    },
  },
  {
    id: 'compare-more',
    skill: 'wp-diff',
    tag: '比多少',
    steps: 1,
    emoji: '🐟',
    scene: '池塘',
    make() {
      const [a, b] = pair()
      const x = randInt(5, 18)
      const y = randInt(1, x - 1)
      return {
        text: `${a}钓到 ${x} 条鱼，${b}钓到 ${y} 条鱼。${a}比${b}多钓了几条鱼？`,
        equation: `${x} − ${y} = ?`,
        answer: x - y,
        unit: '条',
        hint: '「多几条」就是用多的减去少的。',
        visual: { icon: '🐟', groups: [x, y] },
      }
    },
  },
  {
    id: 'compare-total',
    skill: 'wp-combine',
    tag: '比多少',
    steps: 2,
    emoji: '🎈',
    scene: '游乐场',
    make() {
      const [a, b] = pair()
      const x = randInt(3, 12)
      const more = randInt(2, 8)
      return {
        text: `${a}有 ${x} 个气球，${b}比${a}多 ${more} 个。他们两人一共有多少个气球？`,
        equation: `${x} + (${x} + ${more}) = ?`,
        answer: x + (x + more),
        unit: '个',
        hint: `先算出${b}有多少个（${x} + ${more}），再把两人的加起来。`,
        visual: { icon: '🎈', groups: [x, x + more] },
      }
    },
  },
  {
    id: 'two-step-buy',
    skill: 'wp-remain',
    tag: '两步',
    steps: 2,
    emoji: '🛒',
    scene: '超市',
    make() {
      const start = randInt(15, 40)
      // 两次花销都从「还剩多少」里取上限，保证结果至少剩 1 元，不会算出负数
      const buy = randInt(3, Math.min(10, start - 5))
      const back = randInt(2, Math.min(8, start - buy - 1))
      return {
        text: `妈妈带了 ${start} 元去买菜，先花了 ${buy} 元买青菜，又花了 ${back} 元买鸡蛋。妈妈还剩多少元？`,
        equation: `${start} − ${buy} − ${back} = ?`,
        answer: start - buy - back,
        unit: '元',
        hint: '花了两次钱，就要减两次。',
      }
    },
  },
  {
    id: 'bus',
    skill: 'wp-remain',
    tag: '两步',
    steps: 2,
    emoji: '🚌',
    scene: '公交车',
    make() {
      const start = randInt(10, 30)
      const off = randInt(2, 8)
      const on = randInt(2, 9)
      return {
        text: `公交车上原来有 ${start} 人，到站时下去了 ${off} 人，又上来了 ${on} 人。现在车上有多少人？`,
        equation: `${start} − ${off} + ${on} = ?`,
        answer: start - off + on,
        unit: '人',
        hint: '下车是减，上车是加，按顺序一步一步算。',
      }
    },
  },
  {
    id: 'share',
    skill: 'wp-share',
    tag: '平均分',
    steps: 1,
    emoji: '🍬',
    scene: '分糖果',
    make() {
      const each = randInt(2, 6)
      const kids = randInt(2, 5)
      return {
        text: `有 ${each * kids} 颗糖，平均分给 ${kids} 个小朋友，每人能分到几颗？`,
        equation: `${each * kids} ÷ ${kids} = ?`,
        answer: each,
        unit: '颗',
        hint: `试试看：如果每人 ${each - 1} 颗够不够分完？平均分就是每人一样多。`,
        visual: { icon: '🍬', groups: Array.from({ length: kids }, () => each) },
      }
    },
  },
  {
    id: 'groups',
    skill: 'wp-times',
    tag: '几个几',
    steps: 1,
    emoji: '🥚',
    scene: '农场',
    make() {
      const boxes = randInt(2, 6)
      const per = randInt(2, 8)
      return {
        text: `一盒鸡蛋有 ${per} 个，${boxes} 盒一共有多少个鸡蛋？`,
        equation: `${per} × ${boxes} = ?`,
        answer: per * boxes,
        unit: '个',
        hint: `就是 ${boxes} 个 ${per} 相加：${Array.from({ length: boxes }, () => per).join(' + ')}。`,
        visual: { icon: '🥚', groups: Array.from({ length: boxes }, () => per) },
      }
    },
  },
  {
    id: 'time',
    skill: 'wp-combine',
    tag: '时间',
    steps: 1,
    emoji: '🕐',
    scene: '一天的安排',
    make() {
      const start = randInt(1, 8)
      const last = randInt(1, 4)
      return {
        text: `下午 ${start} 点开始上兴趣班，上了 ${last} 个小时。结束时是下午几点？`,
        equation: `${start} + ${last} = ?`,
        answer: start + last,
        unit: '点',
        hint: '在钟面上从开始时间往后数小时数。',
      }
    },
  },
  {
    id: 'money-change',
    skill: 'wp-two-step',
    tag: '找零',
    steps: 2,
    emoji: '💰',
    scene: '文具店',
    make() {
      const price = randInt(3, 9)
      const count = randInt(2, 5)
      const paid = price * count + randInt(1, 15)
      return {
        text: `一支铅笔 ${price} 元，买 ${count} 支要付多少钱？付了 ${paid} 元，应该找回多少元？（请回答找回的钱）`,
        equation: `${paid} − ${price} × ${count} = ?`,
        answer: paid - price * count,
        unit: '元',
        hint: `先算 ${count} 支铅笔一共 ${price * count} 元，再用付的钱减去它。`,
      }
    },
  },
  {
    id: 'length',
    skill: 'wp-remain',
    tag: '长度',
    steps: 1,
    emoji: '📏',
    scene: '手工课',
    make() {
      const total = randInt(20, 90)
      const cut = randInt(5, total - 5)
      return {
        text: `一根彩带长 ${total} 厘米，剪下 ${cut} 厘米做蝴蝶结。彩带还剩多少厘米？`,
        equation: `${total} − ${cut} = ?`,
        answer: total - cut,
        unit: '厘米',
        hint: '剪掉的部分要从总长里减掉。',
      }
    },
  },
  {
    id: 'ordinal',
    skill: 'wp-combine',
    tag: '排队',
    steps: 2,
    emoji: '🧍',
    scene: '排队',
    make() {
      const front = randInt(2, 9)
      const back = randInt(2, 9)
      return {
        text: `小星排队买冰淇淋，他前面有 ${front} 个人，后面有 ${back} 个人。这一队一共有多少人？`,
        equation: `${front} + 1 + ${back} = ?`,
        answer: front + 1 + back,
        unit: '人',
        hint: '别忘了把小星自己也算进去哦！',
      }
    },
  },
  {
    id: 'garden',
    skill: 'wp-times',
    tag: '两步',
    steps: 2,
    emoji: '🌻',
    scene: '花园',
    make() {
      const rows = randInt(2, 5)
      const per = randInt(3, 8)
      const wither = randInt(1, 6)
      return {
        text: `花园里种了 ${rows} 排向日葵，每排 ${per} 棵，后来枯萎了 ${wither} 棵。现在还有多少棵？`,
        equation: `${per} × ${rows} − ${wither} = ?`,
        answer: per * rows - wither,
        unit: '棵',
        hint: `先算一共种了 ${per * rows} 棵，再减掉枯萎的。`,
      }
    },
  },
  {
    id: 'books',
    skill: 'wp-remain',
    tag: '两步',
    steps: 2,
    emoji: '📚',
    scene: '图书角',
    make() {
      const [who] = pair()
      const total = randInt(20, 60)
      // 两天的页数都受剩余页数约束，保证「还剩多少页」是正数
      const day1 = randInt(3, Math.min(12, total - 6))
      const day2 = randInt(3, Math.min(12, total - day1 - 2))
      return {
        text: `一本故事书有 ${total} 页，${who}第一天看了 ${day1} 页，第二天看了 ${day2} 页。还剩多少页没看？`,
        equation: `${total} − ${day1} − ${day2} = ?`,
        answer: total - day1 - day2,
        unit: '页',
        hint: `两天一共看了 ${day1 + day2} 页，用总页数减掉它。`,
      }
    },
  },
  {
    id: 'stickers',
    skill: 'wp-diff',
    tag: '比多少',
    steps: 1,
    emoji: '✨',
    scene: '贴纸交换',
    make() {
      const [a, b] = pair()
      const x = randInt(6, 20)
      const less = randInt(2, 5)
      return {
        text: `${a}有 ${x} 张贴纸，${b}比${a}少 ${less} 张。${b}有多少张贴纸？`,
        equation: `${x} − ${less} = ?`,
        answer: x - less,
        unit: '张',
        hint: '「比…少」要用减法。',
        visual: { icon: '✨', groups: [x, x - less] },
      }
    },
  },
  {
    id: 'zoo',
    skill: 'wp-combine',
    tag: '合并',
    steps: 2,
    emoji: '🦒',
    scene: '动物园',
    make() {
      const a = randInt(3, 10)
      const b = randInt(3, 10)
      const c = randInt(2, 8)
      return {
        text: `动物园里有 ${a} 只长颈鹿、${b} 只斑马和 ${c} 只大象。这三种动物一共有多少只？`,
        equation: `${a} + ${b} + ${c} = ?`,
        answer: a + b + c,
        unit: '只',
        hint: '三个数依次相加，可以先算前两个。',
        visual: { icon: '🦒', groups: [a, b, c] },
      }
    },
  },

  /* ------------------------------------------------ 乘除专题 */

  {
    id: 'times-multiple',
    skill: 'wp-times',
    tag: '倍数',
    steps: 1,
    emoji: '🕊️',
    scene: '手工课',
    make() {
      const [a, b] = pair()
      const x = randInt(3, 12)
      const n = randInt(2, 5)
      return {
        text: `${a}折了 ${x} 只纸鹤，${b}折的是${a}的 ${n} 倍。${b}折了多少只纸鹤？`,
        equation: `${x} × ${n} = ?`,
        answer: x * n,
        unit: '只',
        hint: `「是…的 ${n} 倍」就是 ${n} 个 ${x} 加起来，也就是乘 ${n}。`,
        visual: { icon: '🕊️', groups: Array.from({ length: n }, () => x) },
      }
    },
  },
  {
    id: 'quotitive',
    skill: 'wp-share',
    tag: '包含除',
    steps: 1,
    emoji: '🥮',
    scene: '点心铺',
    make() {
      const per = randInt(2, 6)
      const boxes = randInt(2, 6)
      const total = per * boxes
      return {
        text: `有 ${total} 个月饼，每 ${per} 个装一盒，可以装满多少盒？`,
        equation: `${total} ÷ ${per} = ?`,
        answer: boxes,
        unit: '盒',
        hint: `看看 ${total} 里面一共有几个 ${per}。`,
        visual: { icon: '🥮', groups: Array.from({ length: boxes }, () => per) },
      }
    },
  },
  {
    id: 'div-remainder',
    skill: 'wp-two-step',
    tag: '有余数',
    steps: 2,
    emoji: '🍭',
    scene: '糖果屋',
    make() {
      const [who] = pair()
      const per = randInt(3, 6)
      const bags = randInt(2, 6)
      const rest = randInt(1, per - 1)
      const total = per * bags + rest
      return {
        text: `${who}有 ${total} 颗糖，每 ${per} 颗装一袋。装满若干袋后，还剩多少颗糖？`,
        equation: `${total} ÷ ${per} = ${bags} …… ?`,
        answer: rest,
        unit: '颗',
        hint: `先看能装满几袋，装不满一袋的那几颗就是剩下的。`,
      }
    },
  },
  {
    id: 'unit-price',
    skill: 'wp-times',
    tag: '归一',
    steps: 2,
    emoji: '📓',
    scene: '文具店',
    make() {
      const n1 = randInt(2, 5)
      const price = randInt(2, 9)
      const n2 = randInt(2, 8)
      return {
        text: `${n1} 本笔记本一共 ${n1 * price} 元。照这样计算，买 ${n2} 本要多少元？`,
        equation: `${n1 * price} ÷ ${n1} × ${n2} = ?`,
        answer: price * n2,
        unit: '元',
        hint: `先求出 1 本多少元，再乘 ${n2}。`,
      }
    },
  },
  {
    id: 'fraction-part',
    skill: 'wp-times',
    tag: '几分之几',
    steps: 2,
    emoji: '🍊',
    scene: '果篮',
    make() {
      const parts = randInt(2, 4)
      const each = randInt(2, 6)
      const take = randInt(1, parts - 1)
      return {
        text: `果篮里有 ${parts * each} 个橘子，平均分成 ${parts} 份，其中的 ${take} 份是多少个？`,
        equation: `${parts * each} ÷ ${parts} × ${take} = ?`,
        answer: each * take,
        unit: '个',
        hint: `先算 1 份有几个，再乘 ${take}。`,
        visual: { icon: '🍊', groups: Array.from({ length: parts }, () => each) },
      }
    },
  },
  {
    id: 'minibus',
    skill: 'wp-times',
    tag: '进一法',
    // 商 / 余数 / 再加一辆，剖析拆出来正好三步
    steps: 3,
    emoji: '🚐',
    scene: '春游',
    make() {
      const per = randInt(4, 8)
      const full = randInt(2, 6)
      const extra = randInt(1, per - 1)
      const total = per * full + extra
      return {
        text: `${total} 个小朋友去春游，每辆小车最多坐 ${per} 人。至少要几辆车才能都坐下？`,
        equation: `${total} ÷ ${per} = ${full} …… ${extra}，${full} + 1 = ?`,
        answer: full + 1,
        unit: '辆',
        hint: `坐不满的那 ${extra} 个小朋友也要上车，所以还得再加一辆。`,
      }
    },
  },

  /* ------------------------------------------------ 行程与工程 */

  {
    id: 'distance',
    skill: 'wp-times',
    tag: '行程',
    steps: 1,
    emoji: '🚂',
    scene: '小火车',
    make() {
      const speed = randInt(40, 90)
      const minutes = randInt(2, 8)
      return {
        text: `一辆小火车每分钟行 ${speed} 米，一共行了 ${minutes} 分钟。它行了多少米？`,
        equation: `${speed} × ${minutes} = ?`,
        answer: speed * minutes,
        unit: '米',
        hint: `每分钟 ${speed} 米，${minutes} 分钟就是 ${minutes} 个 ${speed} 米。`,
      }
    },
  },
  {
    id: 'meet',
    skill: 'wp-times',
    tag: '相遇',
    // 算式只有「求速度和」「求时间」两步，难得在想到要先合速度，所以难度仍挂进阶
    steps: 2,
    tier: 'multi',
    emoji: '🛣️',
    scene: '林荫道',
    make() {
      const [a, b] = pair()
      const sa = randInt(30, 70)
      const sb = randInt(30, 70)
      const minutes = randInt(2, 6)
      return {
        text: `${a}和${b}从相距 ${(sa + sb) * minutes} 米的两地同时出发，面对面走来。${a}每分钟走 ${sa} 米，${b}每分钟走 ${sb} 米。几分钟后两人相遇？`,
        equation: `${(sa + sb) * minutes} ÷ (${sa} + ${sb}) = ?`,
        answer: minutes,
        unit: '分钟',
        hint: `两人每分钟一共走近 ${sa + sb} 米，看看总路程里有几个 ${sa + sb}。`,
      }
    },
  },
  {
    id: 'work-days',
    skill: 'wp-times',
    tag: '工程',
    steps: 1,
    emoji: '🤖',
    scene: '机器人工厂',
    make() {
      const per = randInt(4, 9)
      const days = randInt(3, 8)
      return {
        text: `机器人每天能拼 ${per} 个模型，一共要拼 ${per * days} 个。需要拼多少天？`,
        equation: `${per * days} ÷ ${per} = ?`,
        answer: days,
        unit: '天',
        hint: `每天 ${per} 个，看看 ${per * days} 里面有几个 ${per}。`,
      }
    },
  },
  {
    id: 'planting',
    skill: 'wp-combine',
    tag: '植树',
    steps: 2,
    emoji: '🌳',
    scene: '林间小路',
    make() {
      const gap = sample([2, 3, 4, 5])
      const trees = randInt(4, 10)
      const length = gap * (trees - 1)
      return {
        text: `一条 ${length} 米长的小路，从头到尾每隔 ${gap} 米种一棵树，两端都要种。一共要种多少棵树？`,
        equation: `${length} ÷ ${gap} + 1 = ?`,
        answer: trees,
        unit: '棵',
        hint: `小路被分成了 ${trees - 1} 段，两端都种树的话，棵数要比段数多 1。`,
      }
    },
  },

  /* ------------------------------------------------ 和差倍与推理 */

  {
    id: 'sum-diff',
    skill: 'wp-diff',
    tag: '和差',
    // 「补齐再对半分」是两次计算，难在那一次假设，所以难度仍挂进阶
    steps: 2,
    tier: 'multi',
    emoji: '🃏',
    scene: '卡片收藏',
    make() {
      const [a, b] = pair()
      const small = randInt(2, 12)
      const diff = randInt(2, 8)
      const sum = small + small + diff
      return {
        text: `${a}和${b}一共有 ${sum} 张卡片，${a}比${b}多 ${diff} 张。${a}有多少张卡片？`,
        equation: `(${sum} + ${diff}) ÷ 2 = ?`,
        answer: small + diff,
        unit: '张',
        hint: `如果${b}也有那么多，总数就变成 ${sum + diff} 张，再平均分成两份。`,
      }
    },
  },
  {
    id: 'sum-times',
    skill: 'wp-times',
    tag: '和倍',
    // 「凑份数、求一份」是两次计算，难在把倍数看成份数，所以难度仍挂进阶
    steps: 2,
    tier: 'multi',
    emoji: '🐠',
    scene: '水族箱',
    make() {
      const [a, b] = pair()
      const small = randInt(2, 9)
      const n = randInt(2, 4)
      return {
        text: `${a}和${b}一共养了 ${small * (n + 1)} 条小鱼，${a}养的是${b}的 ${n} 倍。${b}养了多少条？`,
        equation: `${small * (n + 1)} ÷ (${n} + 1) = ?`,
        answer: small,
        unit: '条',
        hint: `把${b}的看成 1 份，${a}就是 ${n} 份，一共 ${n + 1} 份。`,
      }
    },
  },
  {
    id: 'chicken-rabbit',
    skill: 'wp-diff',
    tag: '鸡兔同笼',
    steps: 3,
    emoji: '🐰',
    scene: '农场笼子',
    make() {
      const chicken = randInt(2, 8)
      const rabbit = randInt(2, 8)
      const heads = chicken + rabbit
      const legs = chicken * 2 + rabbit * 4
      return {
        text: `笼子里有鸡和兔一共 ${heads} 只，数一数腿有 ${legs} 条。笼子里有多少只兔子？`,
        equation: `(${legs} − ${heads} × 2) ÷ 2 = ?`,
        answer: rabbit,
        unit: '只',
        hint: `假设全是鸡，就只有 ${heads * 2} 条腿；多出来的每 2 条腿，就是一只兔子。`,
      }
    },
  },
  {
    id: 'average',
    skill: 'wp-times',
    tag: '平均数',
    // 三天要两次加法再一次除法，算式上是三步；想法上仍是「先合起来再平分」两步
    steps: 3,
    tier: 'two',
    emoji: '📖',
    scene: '读书角',
    make() {
      const [who] = pair()
      const avg = randInt(3, 9)
      // d 至少 1，否则会出「三天分别读了 3、3、3 页」这种不用算的送分题
      const d = randInt(1, 2)
      return {
        text: `${who}三天分别读了 ${avg - d}、${avg}、${avg + d} 页书。平均每天读多少页？`,
        equation: `(${avg - d} + ${avg} + ${avg + d}) ÷ 3 = ?`,
        answer: avg,
        unit: '页',
        hint: `先把三天的页数加起来，再平均分成 3 天。`,
      }
    },
  },
  {
    id: 'age-later',
    skill: 'wp-combine',
    tag: '年龄',
    steps: 2,
    emoji: '👨‍👩‍👧',
    scene: '全家福',
    make() {
      const [who] = pair()
      const kid = randInt(6, 10)
      const gap = randInt(20, 30)
      const years = randInt(2, 6)
      return {
        text: `今年${who} ${kid} 岁，妈妈比${who}大 ${gap} 岁。${years} 年后妈妈多少岁？`,
        equation: `${kid} + ${gap} + ${years} = ?`,
        answer: kid + gap + years,
        unit: '岁',
        hint: `先算出妈妈今年 ${kid + gap} 岁，再加上 ${years} 年。`,
      }
    },
  },

  /* ------------------------------------------------ 图形与时间 */

  {
    id: 'perimeter',
    skill: 'wp-combine',
    tag: '周长',
    steps: 2,
    emoji: '🥬',
    scene: '菜地',
    make() {
      const long = randInt(3, 15)
      const wide = randInt(2, long)
      return {
        text: `一块长方形菜地长 ${long} 米、宽 ${wide} 米。绕着它走一圈是多少米？`,
        equation: `(${long} + ${wide}) × 2 = ?`,
        answer: (long + wide) * 2,
        unit: '米',
        hint: `一圈里有两条长和两条宽。`,
      }
    },
  },
  {
    id: 'area',
    skill: 'wp-times',
    tag: '面积',
    steps: 1,
    emoji: '🏷️',
    scene: '贴纸工坊',
    make() {
      const long = randInt(2, 12)
      const wide = randInt(2, 9)
      return {
        text: `一张长方形贴纸长 ${long} 厘米、宽 ${wide} 厘米。它的面积是多少平方厘米？`,
        equation: `${long} × ${wide} = ?`,
        answer: long * wide,
        unit: '平方厘米',
        hint: `面积就是每行 ${long} 个小方格，一共 ${wide} 行。`,
      }
    },
  },
  {
    id: 'duration',
    skill: 'wp-times',
    tag: '时间',
    steps: 2,
    emoji: '⏰',
    scene: '课程表',
    make() {
      const start = randInt(8, 11)
      const hours = randInt(1, 3)
      return {
        text: `围棋课 ${start} 时开始，${start + hours} 时结束。这节课一共上了多少分钟？`,
        equation: `(${start + hours} − ${start}) × 60 = ?`,
        answer: hours * 60,
        unit: '分钟',
        hint: `先算上了几个小时，1 小时是 60 分钟。`,
      }
    },
  },
]

/* ================================================== 语义模板 × 场景皮肤 */

/**
 * 场景皮肤：一张皮肤只回答「故事发生在哪里、数的是什么、动词怎么说」，
 * 不带任何数学结构，因此可以套在每一个语义模板上。
 *
 * verb  收集类动词，能接「上午…了 5 个」「比…多…了 3 个」
 * away  拿走类动词短语，能接数量：`小星${away} 3 个`
 * place 存放处所，能作主语：`${place}原来有 12 个…`
 * holder 容器量词，能作「装一${holder}」「3 ${holder}」
 */
export const SCENE_SKINS = [
  {
    id: 'shell',
    scene: '海边拾贝',
    emoji: '🐚',
    item: '贝壳',
    unit: '个',
    verb: '捡',
    away: '送给妹妹',
    place: '小桶里',
    holder: '桶',
  },
  {
    id: 'bakery',
    scene: '面包坊',
    emoji: '🥐',
    item: '可颂',
    unit: '个',
    verb: '烤',
    away: '卖掉',
    place: '面包篮里',
    holder: '袋',
  },
  {
    id: 'space',
    scene: '太空基地',
    emoji: '🚀',
    item: '星星贴',
    unit: '张',
    verb: '收集',
    away: '送给队友',
    place: '收纳格里',
    holder: '格',
  },
  {
    id: 'bug',
    scene: '昆虫屋',
    emoji: '🐞',
    item: '瓢虫',
    unit: '只',
    verb: '找到',
    away: '放回草地',
    place: '观察盒里',
    holder: '盒',
  },
  {
    id: 'bamboo',
    scene: '竹林',
    emoji: '🎋',
    item: '竹笋',
    unit: '根',
    verb: '挖',
    away: '分给熊猫',
    place: '竹篓里',
    holder: '篓',
  },
  {
    id: 'post',
    scene: '小小邮局',
    emoji: '✉️',
    item: '明信片',
    unit: '张',
    verb: '写',
    away: '寄走',
    place: '邮包里',
    holder: '包',
  },
  {
    id: 'market',
    scene: '农夫市集',
    emoji: '🍅',
    item: '番茄',
    unit: '个',
    verb: '摘',
    away: '送给邻居',
    place: '菜筐里',
    holder: '筐',
  },
  {
    id: 'reef',
    scene: '珊瑚礁',
    emoji: '🐠',
    item: '小丑鱼',
    unit: '条',
    verb: '捞',
    away: '放回海里',
    place: '观察缸里',
    holder: '缸',
  },
  {
    id: 'snow',
    scene: '雪地营地',
    emoji: '⛄',
    item: '雪球',
    unit: '个',
    verb: '滚',
    away: '送给伙伴',
    place: '雪屋里',
    holder: '筐',
  },
  {
    id: 'mine',
    scene: '水晶矿洞',
    emoji: '💎',
    item: '水晶',
    unit: '块',
    verb: '采',
    away: '送给矿工',
    place: '矿车里',
    holder: '车',
  },
]

/**
 * 语义模板：只管数学结构与取值范围，题面里的名词动词全部从皮肤取。
 * make(skin) 的返回值和手写母题完全一致，下游不需要区分两种来源。
 */
export const SEMANTIC_TEMPLATES = [
  {
    id: 'join',
    skill: 'wp-combine',
    tag: '合并',
    steps: 1,
    make(s) {
      const [a] = pair()
      const x = randInt(3, 12)
      const y = randInt(2, 10)
      return {
        text: `${a}上午${s.verb}了 ${x} ${s.unit}${s.item}，下午又${s.verb}了 ${y} ${s.unit}。${a}一共${s.verb}了多少${s.unit}${s.item}？`,
        equation: `${x} + ${y} = ?`,
        answer: x + y,
        unit: s.unit,
        hint: '「一共」就是把两次的数量加起来。',
        visual: { icon: s.emoji, groups: [x, y] },
      }
    },
  },
  {
    id: 'remain',
    skill: 'wp-remain',
    tag: '剩余',
    steps: 1,
    make(s) {
      const [a] = pair()
      const total = randInt(8, 20)
      const gone = randInt(2, total - 2)
      return {
        text: `${s.place}原来有 ${total} ${s.unit}${s.item}，${a}${s.away} ${gone} ${s.unit}。${s.place}还剩多少${s.unit}？`,
        equation: `${total} − ${gone} = ?`,
        answer: total - gone,
        unit: s.unit,
        hint: '「还剩」要用减法：原来的减去拿走的。',
        visual: { icon: s.emoji, groups: [total], strike: gone },
      }
    },
  },
  {
    id: 'gap',
    skill: 'wp-diff',
    tag: '比多少',
    steps: 1,
    make(s) {
      const [a, b] = pair()
      const x = randInt(5, 18)
      const y = randInt(1, x - 1)
      return {
        text: `${a}${s.verb}了 ${x} ${s.unit}${s.item}，${b}${s.verb}了 ${y} ${s.unit}。${a}比${b}多${s.verb}了多少${s.unit}？`,
        equation: `${x} − ${y} = ?`,
        answer: x - y,
        unit: s.unit,
        hint: '「多多少」就是用多的减去少的。',
        visual: { icon: s.emoji, groups: [x, y] },
      }
    },
  },
  {
    id: 'fewer',
    skill: 'wp-diff',
    tag: '比多少',
    steps: 1,
    make(s) {
      const [a, b] = pair()
      const x = randInt(6, 20)
      const less = randInt(2, 5)
      return {
        text: `${a}${s.verb}了 ${x} ${s.unit}${s.item}，${b}比${a}少${s.verb}了 ${less} ${s.unit}。${b}${s.verb}了多少${s.unit}？`,
        equation: `${x} − ${less} = ?`,
        answer: x - less,
        unit: s.unit,
        hint: '「比…少」要用减法：从多的那份里减掉相差的。',
        visual: { icon: s.emoji, groups: [x, x - less] },
      }
    },
  },
  {
    id: 'times',
    skill: 'wp-times',
    tag: '倍数',
    steps: 1,
    make(s) {
      const [a, b] = pair()
      const x = randInt(3, 9)
      const n = randInt(2, 4)
      return {
        text: `${a}${s.verb}了 ${x} ${s.unit}${s.item}，${b}${s.verb}的是${a}的 ${n} 倍。${b}${s.verb}了多少${s.unit}？`,
        equation: `${x} × ${n} = ?`,
        answer: x * n,
        unit: s.unit,
        hint: `「是…的 ${n} 倍」就是 ${n} 个 ${x} 加起来，也就是乘 ${n}。`,
        visual: { icon: s.emoji, groups: Array.from({ length: n }, () => x) },
      }
    },
  },
  {
    id: 'pack',
    skill: 'wp-times',
    tag: '几个几',
    steps: 1,
    make(s) {
      const per = randInt(2, 6)
      const boxes = randInt(2, 5)
      return {
        text: `一${s.holder}${s.item}有 ${per} ${s.unit}，${boxes} ${s.holder}一共有多少${s.unit}${s.item}？`,
        equation: `${per} × ${boxes} = ?`,
        answer: per * boxes,
        unit: s.unit,
        hint: `就是 ${boxes} 个 ${per} 相加：${Array.from({ length: boxes }, () => per).join(' + ')}。`,
        visual: { icon: s.emoji, groups: Array.from({ length: boxes }, () => per) },
      }
    },
  },
  {
    id: 'share',
    skill: 'wp-share',
    tag: '平均分',
    steps: 1,
    make(s) {
      const each = randInt(2, 6)
      const kids = randInt(2, 5)
      return {
        text: `有 ${each * kids} ${s.unit}${s.item}，平均分给 ${kids} 个小朋友，每人能分到多少${s.unit}？`,
        equation: `${each * kids} ÷ ${kids} = ?`,
        answer: each,
        unit: s.unit,
        hint: '平均分就是每人一样多，看看每人拿几个才刚好分完。',
        visual: { icon: s.emoji, groups: Array.from({ length: kids }, () => each) },
      }
    },
  },
  {
    id: 'fit',
    skill: 'wp-share',
    tag: '包含除',
    steps: 1,
    make(s) {
      const per = randInt(2, 6)
      const boxes = randInt(2, 6)
      const total = per * boxes
      return {
        text: `有 ${total} ${s.unit}${s.item}，每 ${per} ${s.unit}装一${s.holder}，可以装满多少${s.holder}？`,
        equation: `${total} ÷ ${per} = ?`,
        answer: boxes,
        unit: s.holder,
        hint: `看看 ${total} 里面一共有几个 ${per}。`,
        visual: { icon: s.emoji, groups: Array.from({ length: boxes }, () => per) },
      }
    },
  },
  {
    id: 'both',
    skill: 'wp-combine',
    tag: '比多少',
    steps: 2,
    make(s) {
      const [a, b] = pair()
      const x = randInt(3, 12)
      const more = randInt(2, 8)
      return {
        text: `${a}${s.verb}了 ${x} ${s.unit}${s.item}，${b}比${a}多${s.verb}了 ${more} ${s.unit}。两人一共${s.verb}了多少${s.unit}？`,
        equation: `${x} + (${x} + ${more}) = ?`,
        answer: x + (x + more),
        unit: s.unit,
        hint: `先算出${b}${s.verb}了多少（${x} + ${more}），再把两人的加起来。`,
        visual: { icon: s.emoji, groups: [x, x + more] },
      }
    },
  },
  {
    id: 'flow',
    skill: 'wp-remain',
    tag: '一进一出',
    steps: 2,
    make(s) {
      const [a] = pair()
      const total = randInt(10, 30)
      const out = randInt(2, 8)
      const back = randInt(2, 9)
      return {
        text: `${s.place}原来有 ${total} ${s.unit}${s.item}，${a}${s.away} ${out} ${s.unit}，后来又${s.verb}了 ${back} ${s.unit}放进去。现在有多少${s.unit}？`,
        equation: `${total} − ${out} + ${back} = ?`,
        answer: total - out + back,
        unit: s.unit,
        hint: '拿走是减，放回是加，按顺序一步一步算。',
      }
    },
  },
  {
    id: 'twice-away',
    skill: 'wp-remain',
    tag: '两步',
    steps: 2,
    make(s) {
      const [a] = pair()
      const total = randInt(15, 40)
      // 两次都从「还剩多少」里取上限，保证至少剩 1 个，不会算出负数
      const first = randInt(3, Math.min(10, total - 5))
      const second = randInt(2, Math.min(8, total - first - 1))
      return {
        text: `${s.place}有 ${total} ${s.unit}${s.item}，${a}先${s.away} ${first} ${s.unit}，又${s.away} ${second} ${s.unit}。还剩多少${s.unit}？`,
        equation: `${total} − ${first} − ${second} = ?`,
        answer: total - first - second,
        unit: s.unit,
        hint: `两次一共拿走 ${first + second} ${s.unit}，用总数减掉它。`,
      }
    },
  },
  {
    id: 'pack-loss',
    skill: 'wp-two-step',
    tag: '两步',
    steps: 2,
    make(s) {
      const [a] = pair()
      const boxes = randInt(2, 5)
      const per = randInt(3, 8)
      const lost = randInt(1, Math.min(6, boxes * per - 1))
      return {
        text: `${a}把${s.item}装成 ${boxes} ${s.holder}，每${s.holder} ${per} ${s.unit}，路上弄丢了 ${lost} ${s.unit}。现在还有多少${s.unit}？`,
        equation: `${per} × ${boxes} − ${lost} = ?`,
        answer: per * boxes - lost,
        unit: s.unit,
        hint: `先算原来一共 ${per * boxes} ${s.unit}，再减掉丢掉的。`,
      }
    },
  },
  {
    id: 'sum-times',
    skill: 'wp-times',
    tag: '和倍',
    steps: 2,
    tier: 'multi',
    make(s) {
      const [a, b] = pair()
      const small = randInt(2, 9)
      const n = randInt(2, 4)
      return {
        text: `${a}和${b}一共${s.verb}了 ${small * (n + 1)} ${s.unit}${s.item}，${a}${s.verb}的是${b}的 ${n} 倍。${b}${s.verb}了多少${s.unit}？`,
        equation: `${small * (n + 1)} ÷ (${n} + 1) = ?`,
        answer: small,
        unit: s.unit,
        hint: `把${b}的看成 1 份，${a}就是 ${n} 份，一共 ${n + 1} 份。`,
      }
    },
  },
  {
    id: 'sum-gap',
    skill: 'wp-diff',
    tag: '和差',
    steps: 2,
    tier: 'multi',
    make(s) {
      const [a, b] = pair()
      const small = randInt(2, 12)
      const diff = randInt(2, 8)
      const sum = small + small + diff
      return {
        text: `${a}和${b}一共${s.verb}了 ${sum} ${s.unit}${s.item}，${a}比${b}多${s.verb}了 ${diff} ${s.unit}。${a}${s.verb}了多少${s.unit}？`,
        equation: `(${sum} + ${diff}) ÷ 2 = ?`,
        answer: small + diff,
        unit: s.unit,
        hint: `如果${b}也${s.verb}那么多，总数就变成 ${sum + diff} ${s.unit}，再平均分成两份。`,
      }
    },
  },
  {
    id: 'ceil-pack',
    skill: 'wp-share',
    tag: '进一法',
    steps: 3,
    make(s) {
      const per = randInt(4, 8)
      const full = randInt(2, 6)
      const extra = randInt(1, per - 1)
      const total = per * full + extra
      return {
        text: `有 ${total} ${s.unit}${s.item}，每${s.holder}最多装 ${per} ${s.unit}。至少要几${s.holder}才能全部装下？`,
        equation: `${total} ÷ ${per} = ${full} …… ${extra}，${full} + 1 = ?`,
        answer: full + 1,
        unit: s.holder,
        hint: `装不满的那 ${extra} ${s.unit}也要有地方放，所以还得再加一${s.holder}。`,
      }
    },
  },
  {
    id: 'left-over',
    skill: 'wp-share',
    tag: '有余数',
    steps: 2,
    make(s) {
      const per = randInt(3, 6)
      const packs = randInt(2, 6)
      const rest = randInt(1, per - 1)
      const total = per * packs + rest
      return {
        text: `有 ${total} ${s.unit}${s.item}，每 ${per} ${s.unit}装一${s.holder}。装满若干${s.holder}后，还剩多少${s.unit}？`,
        equation: `${total} ÷ ${per} = ${packs} …… ?`,
        answer: rest,
        unit: s.unit,
        hint: `先看能装满几${s.holder}，凑不满一${s.holder}的那几${s.unit}就是剩下的。`,
      }
    },
  },
  {
    id: 'unit-rate',
    skill: 'wp-times',
    tag: '归一',
    steps: 2,
    make(s) {
      const n1 = randInt(2, 5)
      const per = randInt(2, 9)
      let n2 = randInt(2, 8)
      // n2 撞上 n1 的话题目就白问了，往后挪一格（到顶就回到 2）
      if (n2 === n1) n2 = n1 === 8 ? 2 : n1 + 1
      return {
        text: `${n1} ${s.holder}${s.item}一共 ${n1 * per} ${s.unit}。照这样计算，${n2} ${s.holder}一共有多少${s.unit}？`,
        equation: `${n1 * per} ÷ ${n1} × ${n2} = ?`,
        answer: per * n2,
        unit: s.unit,
        hint: `先求出 1 ${s.holder}有多少${s.unit}，再乘 ${n2}。`,
      }
    },
  },
  {
    id: 'mean',
    skill: 'wp-times',
    tag: '平均数',
    steps: 3,
    tier: 'two',
    make(s) {
      const [a] = pair()
      // 三天取成「avg−d, avg, avg+d」，d 至少 1，免得三天一样多变成送分题
      const avg = randInt(4, 9)
      const d = randInt(1, 3)
      return {
        text: `${a}三天分别${s.verb}了 ${avg - d}、${avg}、${avg + d} ${s.unit}${s.item}。平均每天${s.verb}多少${s.unit}？`,
        equation: `(${avg - d} + ${avg} + ${avg + d}) ÷ 3 = ?`,
        answer: avg,
        unit: s.unit,
        hint: '先把三天的加起来，再平均分成 3 天。',
      }
    },
  },
]

/** 语义模板 × 场景皮肤：每个组合都是一个独立母题，id 为 `语义-皮肤`。 */
const SKINNED = SEMANTIC_TEMPLATES.flatMap((semantic) =>
  SCENE_SKINS.map((skin) => ({
    id: `${semantic.id}-${skin.id}`,
    skill: semantic.skill,
    tag: semantic.tag,
    steps: semantic.steps,
    // 皮肤只换名词，难度档跟着语义走
    tier: semantic.tier,
    emoji: skin.emoji,
    scene: skin.scene,
    make: () => semantic.make(skin),
  })),
)

export const WORD_PROBLEMS = [...CRAFTED, ...SKINNED]

/** 母题总数。Round 6 内容门禁（scripts/check-round6.mjs H6）直接读这个值。 */
export const WORD_PROBLEM_COUNT = WORD_PROBLEMS.length

/**
 * 一道母题落在哪个难度档：写明了就听它的，没写就按字面步数推。
 * 界面上的「一步 / 两步 / 进阶」标签、星星数、XP、错因标签全走这里，
 * 所以校正 steps 不会顺手把某一档的题量抽空。
 */
export function tierOf(problem) {
  const declared = problem?.tier
  if (declared === 'one' || declared === 'two' || declared === 'multi') return declared
  const steps = problem?.steps ?? 1
  return steps >= 3 ? 'multi' : steps === 2 ? 'two' : 'one'
}

/** 难度档：一步 / 两步 / 进阶。 */
export const WORD_PROBLEM_TIERS = [
  { id: 'all', label: '🌍 全部', match: () => true },
  { id: 'one', label: '1️⃣ 一步题', match: (p) => tierOf(p) === 'one' },
  { id: 'two', label: '2️⃣ 两步题', match: (p) => tierOf(p) === 'two' },
  { id: 'multi', label: '🧠 进阶题', match: (p) => tierOf(p) === 'multi' },
]

export function problemsOfTier(tierId) {
  const tier = WORD_PROBLEM_TIERS.find((t) => t.id === tierId) ?? WORD_PROBLEM_TIERS[0]
  return WORD_PROBLEMS.filter(tier.match)
}

/** 母题覆盖的语义类别，用于内容自检与家长报告。 */
export const WORD_PROBLEM_TAGS = [...new Set(WORD_PROBLEMS.map((p) => p.tag))]
