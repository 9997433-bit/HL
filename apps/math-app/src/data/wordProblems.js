/**
 * 生活行星应用题母题库。
 * 每个母题都是一个生成器：调用 make() 会随机出一道数值不同、结构相同的新题，
 * 因此 16 个母题可以覆盖上百道不重复的练习。
 */
import { randInt, sample } from '@/utils/random'

const NAMES = ['小星', '乐乐', '朵朵', '阿光', '妮妮', '小舟', '大熊', '果果']

const pair = () => {
  const a = sample(NAMES)
  let b = sample(NAMES)
  while (b === a) b = sample(NAMES)
  return [a, b]
}

export const WORD_PROBLEMS = [
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
    skill: 'wp-times',
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
    skill: 'wp-times',
    tag: '钱',
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
]

export const WORD_PROBLEM_COUNT = WORD_PROBLEMS.length
