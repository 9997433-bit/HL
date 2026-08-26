/**
 * 识字语料库 —— 40 个一年级高频字，按「单元」分组。
 *
 * 每个字段的用途：
 *   char      汉字本体
 *   pinyin    带声调拼音
 *   tone      声调（1-4，5 表示轻声），用于拼音色彩标注
 *   meaning   儿童能懂的一句话释义
 *   radical   部首（与 radicals.js 的 id 对应）
 *   strokes   笔画数（用于田字格提示，笔顺动画由 hanzi-writer 运行时提供）
 *   emoji     卡片图标，替代插画资源
 *   words     组词，每条含拼音
 *   sentence  例句 + 拼音
 *
 * 绘本（books.js）中出现的所有汉字都必须在这里能查到，
 * `verifyBookCoverage()` 会在开发模式下校验这一点。
 */

export const UNITS = [
  { id: 'u1', name: '我和数字', emoji: '🔢', color: 'var(--seed-mango)', desc: '最先学会的十个字' },
  { id: 'u2', name: '大自然', emoji: '🌿', color: 'var(--seed-leaf)', desc: '日月山水，都在身边' },
  { id: 'u3', name: '身体和动物', emoji: '🐑', color: 'var(--seed-sky)', desc: '认识自己，认识小伙伴' },
  { id: 'u4', name: '会说话', emoji: '💬', color: 'var(--seed-grape)', desc: '把字连成句子' }
]

export const CHARACTERS = [
  // ------------------------------ 单元一 ------------------------------
  {
    char: '一', pinyin: 'yī', tone: 1, unit: 'u1', radical: 'yi', strokes: 1, emoji: '☝️',
    meaning: '最小的数字，一个。',
    words: [
      { w: '一个', p: 'yī gè' },
      { w: '第一', p: 'dì yī' },
      { w: '一天', p: 'yī tiān' }
    ],
    sentence: { text: '我有一口大水。', p: 'wǒ yǒu yī kǒu dà shuǐ.' }
  },
  {
    char: '二', pinyin: 'èr', tone: 4, unit: 'u1', radical: 'yi', strokes: 2, emoji: '✌️',
    meaning: '两个，比一多一点。',
    words: [
      { w: '二月', p: 'èr yuè' },
      { w: '第二', p: 'dì èr' },
      { w: '二手', p: 'èr shǒu' }
    ],
    sentence: { text: '二月有小花。', p: 'èr yuè yǒu xiǎo huā.' }
  },
  {
    char: '三', pinyin: 'sān', tone: 1, unit: 'u1', radical: 'yi', strokes: 3, emoji: '🤟',
    meaning: '三个，三条横线。',
    words: [
      { w: '三天', p: 'sān tiān' },
      { w: '三月', p: 'sān yuè' },
      { w: '三口', p: 'sān kǒu' }
    ],
    sentence: { text: '我家有三口人。', p: 'wǒ jiā yǒu sān kǒu rén.' }
  },
  {
    char: '上', pinyin: 'shàng', tone: 4, unit: 'u1', radical: 'yi', strokes: 3, emoji: '⬆️',
    meaning: '高高的地方，往高处走。',
    words: [
      { w: '上山', p: 'shàng shān' },
      { w: '天上', p: 'tiān shàng' },
      { w: '上来', p: 'shàng lái' }
    ],
    sentence: { text: '小羊上山去。', p: 'xiǎo yáng shàng shān qù.' }
  },
  {
    char: '下', pinyin: 'xià', tone: 4, unit: 'u1', radical: 'yi', strokes: 3, emoji: '⬇️',
    meaning: '低低的地方，往低处走。',
    words: [
      { w: '下来', p: 'xià lái' },
      { w: '山下', p: 'shān xià' },
      { w: '下手', p: 'xià shǒu' }
    ],
    sentence: { text: '山下有水。', p: 'shān xià yǒu shuǐ.' }
  },
  {
    char: '人', pinyin: 'rén', tone: 2, unit: 'u1', radical: 'ren', strokes: 2, emoji: '🧍',
    meaning: '像一个人张开两条腿走路。',
    words: [
      { w: '大人', p: 'dà rén' },
      { w: '人口', p: 'rén kǒu' },
      { w: '好人', p: 'hǎo rén' }
    ],
    sentence: { text: '大人在山下。', p: 'dà rén zài shān xià.' }
  },
  {
    char: '口', pinyin: 'kǒu', tone: 3, unit: 'u1', radical: 'kou', strokes: 3, emoji: '👄',
    meaning: '嘴巴，画出来就是一个方框。',
    words: [
      { w: '口水', p: 'kǒu shuǐ' },
      { w: '人口', p: 'rén kǒu' },
      { w: '口花花', p: 'kǒu huā huā' }
    ],
    sentence: { text: '我的口会说。', p: 'wǒ de kǒu huì shuō.' }
  },
  {
    char: '大', pinyin: 'dà', tone: 4, unit: 'u1', radical: 'da', strokes: 3, emoji: '🙆',
    meaning: '一个人张开手，好大好大。',
    words: [
      { w: '大山', p: 'dà shān' },
      { w: '大水', p: 'dà shuǐ' },
      { w: '大人', p: 'dà rén' }
    ],
    sentence: { text: '大山上有大花。', p: 'dà shān shàng yǒu dà huā.' }
  },
  {
    char: '小', pinyin: 'xiǎo', tone: 3, unit: 'u1', radical: 'xiao', strokes: 3, emoji: '🐣',
    meaning: '很小很小，比大要少。',
    words: [
      { w: '小花', p: 'xiǎo huā' },
      { w: '小羊', p: 'xiǎo yáng' },
      { w: '小心', p: 'xiǎo xīn' }
    ],
    sentence: { text: '小牛看小羊。', p: 'xiǎo niú kàn xiǎo yáng.' }
  },
  {
    char: '我', pinyin: 'wǒ', tone: 3, unit: 'u1', radical: 'ge', strokes: 7, emoji: '🙋',
    meaning: '说话的这个人，就是我自己。',
    words: [
      { w: '我们', p: 'wǒ men' },
      { w: '我的', p: 'wǒ de' },
      { w: '自我', p: 'zì wǒ' }
    ],
    sentence: { text: '我是小小的我。', p: 'wǒ shì xiǎo xiǎo de wǒ.' }
  },

  // ------------------------------ 单元二 ------------------------------
  {
    char: '日', pinyin: 'rì', tone: 4, unit: 'u2', radical: 'ri', strokes: 4, emoji: '☀️',
    meaning: '太阳，也表示一天。',
    words: [
      { w: '日子', p: 'rì zi' },
      { w: '生日', p: 'shēng rì' },
      { w: '日月', p: 'rì yuè' }
    ],
    sentence: { text: '天上有日。', p: 'tiān shàng yǒu rì.' }
  },
  {
    char: '月', pinyin: 'yuè', tone: 4, unit: 'u2', radical: 'yue', strokes: 4, emoji: '🌙',
    meaning: '月亮，弯弯的挂在天上。',
    words: [
      { w: '月亮', p: 'yuè liàng' },
      { w: '三月', p: 'sān yuè' },
      { w: '月牙', p: 'yuè yá' }
    ],
    sentence: { text: '我看天上的月。', p: 'wǒ kàn tiān shàng de yuè.' }
  },
  {
    char: '山', pinyin: 'shān', tone: 1, unit: 'u2', radical: 'shan', strokes: 3, emoji: '⛰️',
    meaning: '三个山尖尖，就是一座山。',
    words: [
      { w: '大山', p: 'dà shān' },
      { w: '上山', p: 'shàng shān' },
      { w: '山水', p: 'shān shuǐ' }
    ],
    sentence: { text: '山上有小花。', p: 'shān shàng yǒu xiǎo huā.' }
  },
  {
    char: '水', pinyin: 'shuǐ', tone: 3, unit: 'u2', radical: 'shui', strokes: 4, emoji: '💧',
    meaning: '会流动的水，河里海里都有。',
    words: [
      { w: '水果', p: 'shuǐ guǒ' },
      { w: '口水', p: 'kǒu shuǐ' },
      { w: '山水', p: 'shān shuǐ' }
    ],
    sentence: { text: '水上有花。', p: 'shuǐ shàng yǒu huā.' }
  },
  {
    char: '火', pinyin: 'huǒ', tone: 3, unit: 'u2', radical: 'huo', strokes: 4, emoji: '🔥',
    meaning: '红红的火苗，很烫，要小心。',
    words: [
      { w: '火车', p: 'huǒ chē' },
      { w: '大火', p: 'dà huǒ' },
      { w: '火山', p: 'huǒ shān' }
    ],
    sentence: { text: '大火不好，小心火。', p: 'dà huǒ bù hǎo, xiǎo xīn huǒ.' }
  },
  {
    char: '木', pinyin: 'mù', tone: 4, unit: 'u2', radical: 'mu', strokes: 4, emoji: '🌲',
    meaning: '树，也表示木头。',
    words: [
      { w: '木头', p: 'mù tou' },
      { w: '大木', p: 'dà mù' },
      { w: '木马', p: 'mù mǎ' }
    ],
    sentence: { text: '土上有木。', p: 'tǔ shàng yǒu mù.' }
  },
  {
    char: '田', pinyin: 'tián', tone: 2, unit: 'u2', radical: 'tian', strokes: 5, emoji: '🌾',
    meaning: '一块一块的田地，种庄稼的地方。',
    words: [
      { w: '田地', p: 'tián dì' },
      { w: '水田', p: 'shuǐ tián' },
      { w: '田中', p: 'tián zhōng' }
    ],
    sentence: { text: '田中有水。', p: 'tián zhōng yǒu shuǐ.' }
  },
  {
    char: '土', pinyin: 'tǔ', tone: 3, unit: 'u2', radical: 'tu', strokes: 3, emoji: '🟫',
    meaning: '泥土，花和树都长在土里。',
    words: [
      { w: '土地', p: 'tǔ dì' },
      { w: '水土', p: 'shuǐ tǔ' },
      { w: '土花', p: 'tǔ huā' }
    ],
    sentence: { text: '田里有土，土上有花。', p: 'tián lǐ yǒu tǔ, tǔ shàng yǒu huā.' }
  },
  {
    char: '天', pinyin: 'tiān', tone: 1, unit: 'u2', radical: 'da', strokes: 4, emoji: '🌤️',
    meaning: '头顶上的天空，也表示一天。',
    words: [
      { w: '天上', p: 'tiān shàng' },
      { w: '天天', p: 'tiān tiān' },
      { w: '三天', p: 'sān tiān' }
    ],
    sentence: { text: '天上有日和月。', p: 'tiān shàng yǒu rì hé yuè.' }
  },
  {
    char: '花', pinyin: 'huā', tone: 1, unit: 'u2', radical: 'cao', strokes: 7, emoji: '🌸',
    meaning: '香香的花朵，草字头表示它是植物。',
    words: [
      { w: '花朵', p: 'huā duǒ' },
      { w: '小花', p: 'xiǎo huā' },
      { w: '花草', p: 'huā cǎo' }
    ],
    sentence: { text: '小花在水上。', p: 'xiǎo huā zài shuǐ shàng.' }
  },

  // ------------------------------ 单元三 ------------------------------
  {
    char: '手', pinyin: 'shǒu', tone: 3, unit: 'u3', radical: 'shou', strokes: 4, emoji: '✋',
    meaning: '两只手，可以拿东西、可以写字。',
    words: [
      { w: '小手', p: 'xiǎo shǒu' },
      { w: '手心', p: 'shǒu xīn' },
      { w: '手工', p: 'shǒu gōng' }
    ],
    sentence: { text: '我有手，我会看。', p: 'wǒ yǒu shǒu, wǒ huì kàn.' }
  },
  {
    char: '目', pinyin: 'mù', tone: 4, unit: 'u3', radical: 'mubu', strokes: 5, emoji: '👁️',
    meaning: '眼睛，把眼睛竖起来写就是目。',
    words: [
      { w: '目光', p: 'mù guāng' },
      { w: '耳目', p: 'ěr mù' },
      { w: '目中', p: 'mù zhōng' }
    ],
    sentence: { text: '我的目会看天。', p: 'wǒ de mù huì kàn tiān.' }
  },
  {
    char: '耳', pinyin: 'ěr', tone: 3, unit: 'u3', radical: 'er', strokes: 6, emoji: '👂',
    meaning: '耳朵，用来听声音。',
    words: [
      { w: '耳朵', p: 'ěr duo' },
      { w: '木耳', p: 'mù ěr' },
      { w: '耳目', p: 'ěr mù' }
    ],
    sentence: { text: '小牛的耳大大的。', p: 'xiǎo niú de ěr dà dà de.' }
  },
  {
    char: '心', pinyin: 'xīn', tone: 1, unit: 'u3', radical: 'xin', strokes: 4, emoji: '❤️',
    meaning: '心脏，也表示心里想的事。',
    words: [
      { w: '小心', p: 'xiǎo xīn' },
      { w: '好心', p: 'hǎo xīn' },
      { w: '心口', p: 'xīn kǒu' }
    ],
    sentence: { text: '我的心是好心。', p: 'wǒ de xīn shì hǎo xīn.' }
  },
  {
    char: '牛', pinyin: 'niú', tone: 2, unit: 'u3', radical: 'niu', strokes: 4, emoji: '🐄',
    meaning: '牛，头上有两只角。',
    words: [
      { w: '小牛', p: 'xiǎo niú' },
      { w: '牛羊', p: 'niú yáng' },
      { w: '水牛', p: 'shuǐ niú' }
    ],
    sentence: { text: '小牛在田中。', p: 'xiǎo niú zài tián zhōng.' }
  },
  {
    char: '羊', pinyin: 'yáng', tone: 2, unit: 'u3', radical: 'yang', strokes: 6, emoji: '🐑',
    meaning: '羊，白白的毛，会咩咩叫。',
    words: [
      { w: '小羊', p: 'xiǎo yáng' },
      { w: '山羊', p: 'shān yáng' },
      { w: '牛羊', p: 'niú yáng' }
    ],
    sentence: { text: '小羊上山看花。', p: 'xiǎo yáng shàng shān kàn huā.' }
  },
  {
    char: '鸟', pinyin: 'niǎo', tone: 3, unit: 'u3', radical: 'niao', strokes: 5, emoji: '🐦',
    meaning: '小鸟，会在天上飞。',
    words: [
      { w: '小鸟', p: 'xiǎo niǎo' },
      { w: '鸟儿', p: 'niǎo ér' },
      { w: '花鸟', p: 'huā niǎo' }
    ],
    sentence: { text: '小鸟在天上。', p: 'xiǎo niǎo zài tiān shàng.' }
  },
  {
    char: '中', pinyin: 'zhōng', tone: 1, unit: 'u3', radical: 'shu', strokes: 4, emoji: '🎯',
    meaning: '中间，一竖穿过方框正中。',
    words: [
      { w: '中间', p: 'zhōng jiān' },
      { w: '中心', p: 'zhōng xīn' },
      { w: '田中', p: 'tián zhōng' }
    ],
    sentence: { text: '我在田中看鸟。', p: 'wǒ zài tián zhōng kàn niǎo.' }
  },
  {
    char: '不', pinyin: 'bù', tone: 4, unit: 'u3', radical: 'yi', strokes: 4, emoji: '🙅',
    meaning: '表示否定，就是「没有」「不要」。',
    words: [
      { w: '不好', p: 'bù hǎo' },
      { w: '不是', p: 'bù shì' },
      { w: '不大', p: 'bù dà' }
    ],
    sentence: { text: '我不是大人。', p: 'wǒ bù shì dà rén.' }
  },
  {
    char: '好', pinyin: 'hǎo', tone: 3, unit: 'u3', radical: 'nv', strokes: 6, emoji: '👍',
    meaning: '很棒、很喜欢。女和子在一起就是好。',
    words: [
      { w: '好人', p: 'hǎo rén' },
      { w: '你好', p: 'nǐ hǎo' },
      { w: '好心', p: 'hǎo xīn' }
    ],
    sentence: { text: '小牛说：好，好！', p: 'xiǎo niú shuō: hǎo, hǎo!' }
  },

  // ------------------------------ 单元四 ------------------------------
  {
    char: '是', pinyin: 'shì', tone: 4, unit: 'u4', radical: 'ri', strokes: 9, emoji: '✅',
    meaning: '表示「就是」，把两样东西连起来。',
    words: [
      { w: '不是', p: 'bù shì' },
      { w: '是的', p: 'shì de' },
      { w: '真是', p: 'zhēn shì' }
    ],
    sentence: { text: '手是我的。', p: 'shǒu shì wǒ de.' }
  },
  {
    char: '有', pinyin: 'yǒu', tone: 3, unit: 'u4', radical: 'yue', strokes: 6, emoji: '🎁',
    meaning: '拥有，存在。',
    words: [
      { w: '有的', p: 'yǒu de' },
      { w: '有人', p: 'yǒu rén' },
      { w: '有心', p: 'yǒu xīn' }
    ],
    sentence: { text: '山上有小花。', p: 'shān shàng yǒu xiǎo huā.' }
  },
  {
    char: '的', pinyin: 'de', tone: 5, unit: 'u4', radical: 'bai', strokes: 8, emoji: '🔗',
    meaning: '最常用的字，表示「谁的」。',
    words: [
      { w: '我的', p: 'wǒ de' },
      { w: '好的', p: 'hǎo de' },
      { w: '大大的', p: 'dà dà de' }
    ],
    sentence: { text: '这是我的小手。', p: 'zhè shì wǒ de xiǎo shǒu.' }
  },
  {
    char: '看', pinyin: 'kàn', tone: 4, unit: 'u4', radical: 'mubu', strokes: 9, emoji: '👀',
    meaning: '手放在眼睛上，远远地望。',
    words: [
      { w: '看看', p: 'kàn kàn' },
      { w: '好看', p: 'hǎo kàn' },
      { w: '看花', p: 'kàn huā' }
    ],
    sentence: { text: '我看小鸟。', p: 'wǒ kàn xiǎo niǎo.' }
  },
  {
    char: '在', pinyin: 'zài', tone: 4, unit: 'u4', radical: 'tu', strokes: 6, emoji: '📍',
    meaning: '说明东西在哪个地方。',
    words: [
      { w: '在上', p: 'zài shàng' },
      { w: '在家', p: 'zài jiā' },
      { w: '在下', p: 'zài xià' }
    ],
    sentence: { text: '小羊在山下。', p: 'xiǎo yáng zài shān xià.' }
  },
  {
    char: '来', pinyin: 'lái', tone: 2, unit: 'u4', radical: 'mu', strokes: 7, emoji: '🏃',
    meaning: '从别的地方到这里来。',
    words: [
      { w: '来了', p: 'lái le' },
      { w: '上来', p: 'shàng lái' },
      { w: '来人', p: 'lái rén' }
    ],
    sentence: { text: '小牛来了。', p: 'xiǎo niú lái le.' }
  },
  {
    char: '去', pinyin: 'qù', tone: 4, unit: 'u4', radical: 'tu', strokes: 5, emoji: '🚶',
    meaning: '离开这里，到别的地方。',
    words: [
      { w: '去看', p: 'qù kàn' },
      { w: '上去', p: 'shàng qù' },
      { w: '去年', p: 'qù nián' }
    ],
    sentence: { text: '我去看小鸟。', p: 'wǒ qù kàn xiǎo niǎo.' }
  },
  {
    char: '会', pinyin: 'huì', tone: 4, unit: 'u4', radical: 'ren', strokes: 6, emoji: '🌟',
    meaning: '学会了、能做到。',
    words: [
      { w: '会说', p: 'huì shuō' },
      { w: '学会', p: 'xué huì' },
      { w: '不会', p: 'bù huì' }
    ],
    sentence: { text: '我会上山。', p: 'wǒ huì shàng shān.' }
  },
  {
    char: '说', pinyin: 'shuō', tone: 1, unit: 'u4', radical: 'yan', strokes: 9, emoji: '🗣️',
    meaning: '用嘴巴讲话，言字旁跟说话有关。',
    words: [
      { w: '说话', p: 'shuō huà' },
      { w: '会说', p: 'huì shuō' },
      { w: '说好', p: 'shuō hǎo' }
    ],
    sentence: { text: '小羊说：我也会。', p: 'xiǎo yáng shuō: wǒ yě huì.' }
  },
  {
    char: '也', pinyin: 'yě', tone: 3, unit: 'u4', radical: 'yi', strokes: 3, emoji: '➕',
    meaning: '表示「一样、同样」。',
    words: [
      { w: '也是', p: 'yě shì' },
      { w: '也会', p: 'yě huì' },
      { w: '也好', p: 'yě hǎo' }
    ],
    sentence: { text: '小羊也会上山。', p: 'xiǎo yáng yě huì shàng shān.' }
  }
]

export const CHARACTER_MAP = new Map(CHARACTERS.map((c) => [c.char, c]))

export function getCharacter(char) {
  return CHARACTER_MAP.get(char) || null
}

export function charsOfUnit(unitId) {
  return CHARACTERS.filter((c) => c.unit === unitId)
}

export function unitById(unitId) {
  return UNITS.find((u) => u.id === unitId) || null
}

export const TOTAL_CHARACTERS = CHARACTERS.length
