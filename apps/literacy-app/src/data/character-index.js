/**
 * Lightweight character catalogue for the application shell and progress
 * store. Keep rich teaching content in characters.js so home-page visitors do
 * not download definitions, examples and word lists before opening a lesson.
 */
export const UNITS = [
  { id: 'u1', name: '我和数字', emoji: '🔢', color: 'var(--seed-mango)', desc: '最先学会的十个字' },
  { id: 'u2', name: '大自然', emoji: '🌿', color: 'var(--seed-leaf)', desc: '日月山水，都在身边' },
  { id: 'u3', name: '身体和动物', emoji: '🐑', color: 'var(--seed-sky)', desc: '认识自己，认识小伙伴' },
  { id: 'u4', name: '会说话', emoji: '💬', color: 'var(--seed-grape)', desc: '把字连成句子' },
  { id: 'u5', name: '数字大家庭', emoji: '🔟', color: 'var(--seed-mint)', desc: '从四一直数到万' },
  { id: 'u6', name: '天气和大地', emoji: '🌦️', color: 'var(--seed-coral)', desc: '风雨云雪，脚下的土地' },
  { id: 'u7', name: '我的家人', emoji: '👨‍👩‍👧', color: 'var(--seed-mango)', desc: '一家人在一起' },
  { id: 'u8', name: '上学啦', emoji: '🎒', color: 'var(--seed-leaf)', desc: '学校里最常见的字' },
  { id: 'u9', name: '小动物', emoji: '🐟', color: 'var(--seed-sky)', desc: '水里游的，家里养的' },
  { id: 'u10', name: '五颜六色', emoji: '🎨', color: 'var(--seed-grape)', desc: '认识六种颜色' },
  { id: 'u11', name: '四季和时间', emoji: '🍂', color: 'var(--seed-mint)', desc: '春夏秋冬，早晚今明' },
  { id: 'u12', name: '出发去玩', emoji: '🚗', color: 'var(--seed-coral)', desc: '左右前后，出门啦' },
  { id: 'u13', name: '动起来', emoji: '🏃', color: 'var(--seed-mango)', desc: '走跑跳坐，身体的动作' },
  { id: 'u14', name: '家里的东西', emoji: '🛋️', color: 'var(--seed-leaf)', desc: '桌椅床灯，屋里都认得' },
  { id: 'u15', name: '好吃的', emoji: '🍚', color: 'var(--seed-sky)', desc: '米饭菜果，餐桌上的字' },
  { id: 'u16', name: '常用小词', emoji: '🔤', color: 'var(--seed-grape)', desc: '这那什么，说话离不开' }
]

export const UNIT_CHARACTER_IDS = Object.freeze({
  u1: '一二三上下人口大小我个们',
  u2: '日月山水火木田土天花海河林',
  u3: '手目耳心牛羊鸟中不好头牙兔',
  u4: '是有的看在来去会说也了很和',
  u5: '四五六七八九十百千万半双',
  u6: '风雨云雪地石草树星光冰沙',
  u7: '父母男女子你他她家爱哥姐妹国',
  u8: '学校老师生书字读写听问答本',
  u9: '鱼虫马猫狗鸡鸭猪象虎蛙熊',
  u10: '红黄蓝绿白黑色圆方长高',
  u11: '春夏秋冬早晚明今年时分刻岁',
  u12: '左右多少门车足前后里外边',
  u13: '走跑跳坐站吃喝拿唱笑哭打玩',
  u14: '桌椅床灯窗衣鞋帽碗杯伞房电',
  u15: '米饭菜果苹面蛋奶糖茶肉瓜',
  u16: '这那什么都要能想用做给把'
})

export const CHARACTER_INDEX = Object.freeze(
  UNITS.flatMap((unit) =>
    Array.from(UNIT_CHARACTER_IDS[unit.id], (char) => Object.freeze({ char, unit: unit.id }))
  )
)

export const CHARACTER_INDEX_MAP = new Map(CHARACTER_INDEX.map((item) => [item.char, item]))
export const TOTAL_CHARACTERS = CHARACTER_INDEX.length
