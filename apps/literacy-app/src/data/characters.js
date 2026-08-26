/**
 * 识字语料库 —— 106 个学前到一年级高频字，按「单元」分组。
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
  { id: 'u4', name: '会说话', emoji: '💬', color: 'var(--seed-grape)', desc: '把字连成句子' },
  { id: 'u5', name: '数字大家庭', emoji: '🔟', color: 'var(--seed-mint)', desc: '从四一直数到万' },
  { id: 'u6', name: '天气和大地', emoji: '🌦️', color: 'var(--seed-coral)', desc: '风雨云雪，脚下的土地' },
  { id: 'u7', name: '我的家人', emoji: '👨‍👩‍👧', color: 'var(--seed-mango)', desc: '一家人在一起' },
  { id: 'u8', name: '上学啦', emoji: '🎒', color: 'var(--seed-leaf)', desc: '学校里最常见的字' },
  { id: 'u9', name: '小动物', emoji: '🐟', color: 'var(--seed-sky)', desc: '水里游的，家里养的' },
  { id: 'u10', name: '五颜六色', emoji: '🎨', color: 'var(--seed-grape)', desc: '认识六种颜色' },
  { id: 'u11', name: '四季和时间', emoji: '🍂', color: 'var(--seed-mint)', desc: '春夏秋冬，早晚今明' },
  { id: 'u12', name: '出发去玩', emoji: '🚗', color: 'var(--seed-coral)', desc: '左右前后，出门啦' }
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
  },

  // ------------------------------ 单元五 ------------------------------
  {
    char: '四', pinyin: 'sì', tone: 4, unit: 'u5', radical: 'wei', strokes: 5, emoji: '4️⃣',
    meaning: '数字四，比三多一个。',
    words: [
      { w: '四个', p: 'sì gè' },
      { w: '四月', p: 'sì yuè' },
      { w: '四方', p: 'sì fāng' }
    ],
    sentence: { text: '田里有四只小鸟。', p: 'tián lǐ yǒu sì zhī xiǎo niǎo.' }
  },
  {
    char: '五', pinyin: 'wǔ', tone: 3, unit: 'u5', radical: 'erzi', strokes: 4, emoji: '5️⃣',
    meaning: '数字五，一只手正好五个手指。',
    words: [
      { w: '五个', p: 'wǔ gè' },
      { w: '五月', p: 'wǔ yuè' },
      { w: '五天', p: 'wǔ tiān' }
    ],
    sentence: { text: '一只小手有五个手指。', p: 'yī zhī xiǎo shǒu yǒu wǔ gè shǒu zhǐ.' }
  },
  {
    char: '六', pinyin: 'liù', tone: 4, unit: 'u5', radical: 'tou', strokes: 4, emoji: '6️⃣',
    meaning: '数字六，比五多一个。',
    words: [
      { w: '六个', p: 'liù gè' },
      { w: '六月', p: 'liù yuè' },
      { w: '六天', p: 'liù tiān' }
    ],
    sentence: { text: '六月的花很好看。', p: 'liù yuè de huā hěn hǎo kàn.' }
  },
  {
    char: '七', pinyin: 'qī', tone: 1, unit: 'u5', radical: 'yi', strokes: 2, emoji: '7️⃣',
    meaning: '数字七，一个星期有七天。',
    words: [
      { w: '七个', p: 'qī gè' },
      { w: '七月', p: 'qī yuè' },
      { w: '七天', p: 'qī tiān' }
    ],
    sentence: { text: '一个星期有七天。', p: 'yī gè xīng qī yǒu qī tiān.' }
  },
  {
    char: '八', pinyin: 'bā', tone: 1, unit: 'u5', radical: 'ba', strokes: 2, emoji: '8️⃣',
    meaning: '数字八，两撇往两边分开。',
    words: [
      { w: '八个', p: 'bā gè' },
      { w: '八月', p: 'bā yuè' },
      { w: '八天', p: 'bā tiān' }
    ],
    sentence: { text: '八月的天气很热。', p: 'bā yuè de tiān qì hěn rè.' }
  },
  {
    char: '九', pinyin: 'jiǔ', tone: 3, unit: 'u5', radical: 'pie', strokes: 2, emoji: '9️⃣',
    meaning: '数字九，比十少一个。',
    words: [
      { w: '九个', p: 'jiǔ gè' },
      { w: '九月', p: 'jiǔ yuè' },
      { w: '九天', p: 'jiǔ tiān' }
    ],
    sentence: { text: '九月我们去上学。', p: 'jiǔ yuè wǒ men qù shàng xué.' }
  },
  {
    char: '十', pinyin: 'shí', tone: 2, unit: 'u5', radical: 'shi', strokes: 2, emoji: '🔟',
    meaning: '数字十，一横加一竖。',
    words: [
      { w: '十个', p: 'shí gè' },
      { w: '十月', p: 'shí yuè' },
      { w: '十分', p: 'shí fēn' }
    ],
    sentence: { text: '十个手指数一数。', p: 'shí gè shǒu zhǐ shǔ yī shǔ.' }
  },
  {
    char: '百', pinyin: 'bǎi', tone: 3, unit: 'u5', radical: 'bai', strokes: 6, emoji: '💯',
    meaning: '十个十就是一百。',
    words: [
      { w: '一百', p: 'yī bǎi' },
      { w: '百年', p: 'bǎi nián' },
      { w: '百花', p: 'bǎi huā' }
    ],
    sentence: { text: '山上开了一百朵花。', p: 'shān shàng kāi le yī bǎi duǒ huā.' }
  },
  {
    char: '千', pinyin: 'qiān', tone: 1, unit: 'u5', radical: 'shi', strokes: 3, emoji: '🌌',
    meaning: '十个一百就是一千。',
    words: [
      { w: '一千', p: 'yī qiān' },
      { w: '千万', p: 'qiān wàn' },
      { w: '千里', p: 'qiān lǐ' }
    ],
    sentence: { text: '天上有一千颗小星星。', p: 'tiān shàng yǒu yī qiān kē xiǎo xīng xing.' }
  },
  {
    char: '万', pinyin: 'wàn', tone: 4, unit: 'u5', radical: 'yi', strokes: 3, emoji: '🎆',
    meaning: '十个一千就是一万，也表示很多很多。',
    words: [
      { w: '一万', p: 'yī wàn' },
      { w: '万一', p: 'wàn yī' },
      { w: '千万', p: 'qiān wàn' }
    ],
    sentence: { text: '水里有一万条小鱼。', p: 'shuǐ lǐ yǒu yī wàn tiáo xiǎo yú.' }
  },

  // ------------------------------ 单元六 ------------------------------
  {
    char: '风', pinyin: 'fēng', tone: 1, unit: 'u6', radical: 'feng', strokes: 4, emoji: '🌬️',
    meaning: '看不见的风，会把树叶吹得沙沙响。',
    words: [
      { w: '大风', p: 'dà fēng' },
      { w: '风车', p: 'fēng chē' },
      { w: '风雨', p: 'fēng yǔ' }
    ],
    sentence: { text: '大风把小树吹弯了。', p: 'dà fēng bǎ xiǎo shù chuī wān le.' }
  },
  {
    char: '雨', pinyin: 'yǔ', tone: 3, unit: 'u6', radical: 'yutou', strokes: 8, emoji: '🌧️',
    meaning: '从天上落下来的水，就是雨。',
    words: [
      { w: '下雨', p: 'xià yǔ' },
      { w: '大雨', p: 'dà yǔ' },
      { w: '雨水', p: 'yǔ shuǐ' }
    ],
    sentence: { text: '下雨了，我们回家。', p: 'xià yǔ le, wǒ men huí jiā.' }
  },
  {
    char: '云', pinyin: 'yún', tone: 2, unit: 'u6', radical: 'erzi', strokes: 4, emoji: '☁️',
    meaning: '天上白白的云，会慢慢地飘。',
    words: [
      { w: '白云', p: 'bái yún' },
      { w: '云朵', p: 'yún duǒ' },
      { w: '风云', p: 'fēng yún' }
    ],
    sentence: { text: '天上有白白的云。', p: 'tiān shàng yǒu bái bái de yún.' }
  },
  {
    char: '雪', pinyin: 'xuě', tone: 3, unit: 'u6', radical: 'yutou', strokes: 11, emoji: '❄️',
    meaning: '冬天飘下来的白雪，落在手上会化。',
    words: [
      { w: '下雪', p: 'xià xuě' },
      { w: '白雪', p: 'bái xuě' },
      { w: '雪人', p: 'xuě rén' }
    ],
    sentence: { text: '下雪了，我们堆雪人。', p: 'xià xuě le, wǒ men duī xuě rén.' }
  },
  {
    char: '地', pinyin: 'dì', tone: 4, unit: 'u6', radical: 'tu', strokes: 6, emoji: '🌍',
    meaning: '我们脚下的大地。',
    words: [
      { w: '大地', p: 'dà dì' },
      { w: '土地', p: 'tǔ dì' },
      { w: '地上', p: 'dì shàng' }
    ],
    sentence: { text: '小草从地里长出来。', p: 'xiǎo cǎo cóng dì lǐ zhǎng chū lái.' }
  },
  {
    char: '石', pinyin: 'shí', tone: 2, unit: 'u6', radical: 'shitou', strokes: 5, emoji: '🪨',
    meaning: '硬硬的石头，山上到处都是。',
    words: [
      { w: '石头', p: 'shí tou' },
      { w: '石山', p: 'shí shān' },
      { w: '山石', p: 'shān shí' }
    ],
    sentence: { text: '山上有一块大石头。', p: 'shān shàng yǒu yī kuài dà shí tou.' }
  },
  {
    char: '草', pinyin: 'cǎo', tone: 3, unit: 'u6', radical: 'cao', strokes: 9, emoji: '🌱',
    meaning: '绿绿的小草，长在土里。',
    words: [
      { w: '小草', p: 'xiǎo cǎo' },
      { w: '花草', p: 'huā cǎo' },
      { w: '草地', p: 'cǎo dì' }
    ],
    sentence: { text: '草地上有一只小羊。', p: 'cǎo dì shàng yǒu yī zhī xiǎo yáng.' }
  },
  {
    char: '树', pinyin: 'shù', tone: 4, unit: 'u6', radical: 'mu', strokes: 9, emoji: '🌳',
    meaning: '高高的树，木字旁说明它是树木。',
    words: [
      { w: '大树', p: 'dà shù' },
      { w: '树叶', p: 'shù yè' },
      { w: '树林', p: 'shù lín' }
    ],
    sentence: { text: '大树上有一只小鸟。', p: 'dà shù shàng yǒu yī zhī xiǎo niǎo.' }
  },

  // ------------------------------ 单元七 ------------------------------
  {
    char: '父', pinyin: 'fù', tone: 4, unit: 'u7', radical: 'fu', strokes: 4, emoji: '👨',
    meaning: '爸爸，也叫父亲。',
    words: [
      { w: '父母', p: 'fù mǔ' },
      { w: '父亲', p: 'fù qīn' },
      { w: '父女', p: 'fù nǚ' }
    ],
    sentence: { text: '我和父母去看花。', p: 'wǒ hé fù mǔ qù kàn huā.' }
  },
  {
    char: '母', pinyin: 'mǔ', tone: 3, unit: 'u7', radical: 'muqin', strokes: 5, emoji: '👩',
    meaning: '妈妈，也叫母亲。',
    words: [
      { w: '母亲', p: 'mǔ qīn' },
      { w: '父母', p: 'fù mǔ' },
      { w: '母羊', p: 'mǔ yáng' }
    ],
    sentence: { text: '我的母亲很爱我。', p: 'wǒ de mǔ qīn hěn ài wǒ.' }
  },
  {
    char: '男', pinyin: 'nán', tone: 2, unit: 'u7', radical: 'tian', strokes: 7, emoji: '👦',
    meaning: '男孩子。田里出力气的人就是男。',
    words: [
      { w: '男孩', p: 'nán hái' },
      { w: '男生', p: 'nán shēng' },
      { w: '男人', p: 'nán rén' }
    ],
    sentence: { text: '男生和女生一起玩。', p: 'nán shēng hé nǚ shēng yī qǐ wán.' }
  },
  {
    char: '女', pinyin: 'nǚ', tone: 3, unit: 'u7', radical: 'nv', strokes: 3, emoji: '👧',
    meaning: '女孩子。',
    words: [
      { w: '女生', p: 'nǚ shēng' },
      { w: '女儿', p: 'nǚ ér' },
      { w: '男女', p: 'nán nǚ' }
    ],
    sentence: { text: '女生在树下看书。', p: 'nǚ shēng zài shù xià kàn shū.' }
  },
  {
    char: '子', pinyin: 'zǐ', tone: 3, unit: 'u7', radical: 'zi', strokes: 3, emoji: '👶',
    meaning: '小孩子。',
    words: [
      { w: '孩子', p: 'hái zi' },
      { w: '儿子', p: 'ér zi' },
      { w: '子女', p: 'zǐ nǚ' }
    ],
    sentence: { text: '两个孩子在草地上跑。', p: 'liǎng gè hái zi zài cǎo dì shàng pǎo.' }
  },
  {
    char: '你', pinyin: 'nǐ', tone: 3, unit: 'u7', radical: 'ren', strokes: 7, emoji: '🫵',
    meaning: '说话时指着对方，就是你。',
    words: [
      { w: '你好', p: 'nǐ hǎo' },
      { w: '你们', p: 'nǐ men' },
      { w: '你的', p: 'nǐ de' }
    ],
    sentence: { text: '你好，我是小小的我。', p: 'nǐ hǎo, wǒ shì xiǎo xiǎo de wǒ.' }
  },
  {
    char: '他', pinyin: 'tā', tone: 1, unit: 'u7', radical: 'ren', strokes: 5, emoji: '🧑',
    meaning: '说的是另一个男生。',
    words: [
      { w: '他们', p: 'tā men' },
      { w: '他的', p: 'tā de' },
      { w: '他人', p: 'tā rén' }
    ],
    sentence: { text: '他会写自己的名字。', p: 'tā huì xiě zì jǐ de míng zi.' }
  },
  {
    char: '她', pinyin: 'tā', tone: 1, unit: 'u7', radical: 'nv', strokes: 6, emoji: '👩‍🦰',
    meaning: '说的是另一个女生，所以是女字旁。',
    words: [
      { w: '她们', p: 'tā men' },
      { w: '她的', p: 'tā de' },
      { w: '她说', p: 'tā shuō' }
    ],
    sentence: { text: '她说她也会读书。', p: 'tā shuō tā yě huì dú shū.' }
  },
  {
    char: '家', pinyin: 'jiā', tone: 1, unit: 'u7', radical: 'mian', strokes: 10, emoji: '🏠',
    meaning: '我们住的地方，宝盖头就是屋顶。',
    words: [
      { w: '我家', p: 'wǒ jiā' },
      { w: '家人', p: 'jiā rén' },
      { w: '回家', p: 'huí jiā' }
    ],
    sentence: { text: '我家有四口人。', p: 'wǒ jiā yǒu sì kǒu rén.' }
  },
  {
    char: '爱', pinyin: 'ài', tone: 4, unit: 'u7', radical: 'zhua', strokes: 10, emoji: '❤️',
    meaning: '很喜欢，心里暖暖的。',
    words: [
      { w: '爱心', p: 'ài xīn' },
      { w: '可爱', p: 'kě ài' },
      { w: '爱好', p: 'ài hào' }
    ],
    sentence: { text: '我爱我的家。', p: 'wǒ ài wǒ de jiā.' }
  },

  // ------------------------------ 单元八 ------------------------------
  {
    char: '学', pinyin: 'xué', tone: 2, unit: 'u8', radical: 'zi', strokes: 8, emoji: '📚',
    meaning: '学本领、学写字。',
    words: [
      { w: '学习', p: 'xué xí' },
      { w: '上学', p: 'shàng xué' },
      { w: '学会', p: 'xué huì' }
    ],
    sentence: { text: '我们上学去读书。', p: 'wǒ men shàng xué qù dú shū.' }
  },
  {
    char: '校', pinyin: 'xiào', tone: 4, unit: 'u8', radical: 'mu', strokes: 10, emoji: '🏫',
    meaning: '学校，大家一起学习的地方。',
    words: [
      { w: '学校', p: 'xué xiào' },
      { w: '校门', p: 'xiào mén' },
      { w: '校车', p: 'xiào chē' }
    ],
    sentence: { text: '学校门口有一棵大树。', p: 'xué xiào mén kǒu yǒu yī kē dà shù.' }
  },
  {
    char: '老', pinyin: 'lǎo', tone: 3, unit: 'u8', radical: 'lao', strokes: 6, emoji: '👴',
    meaning: '年纪大了，也用在「老师」里面。',
    words: [
      { w: '老师', p: 'lǎo shī' },
      { w: '老人', p: 'lǎo rén' },
      { w: '老家', p: 'lǎo jiā' }
    ],
    sentence: { text: '老师在教我们写字。', p: 'lǎo shī zài jiāo wǒ men xiě zì.' }
  },
  {
    char: '师', pinyin: 'shī', tone: 1, unit: 'u8', radical: 'jin', strokes: 6, emoji: '🧑‍🏫',
    meaning: '教我们本领的人。',
    words: [
      { w: '老师', p: 'lǎo shī' },
      { w: '师生', p: 'shī shēng' },
      { w: '师父', p: 'shī fu' }
    ],
    sentence: { text: '老师和学生都很开心。', p: 'lǎo shī hé xué shēng dōu hěn kāi xīn.' }
  },
  {
    char: '生', pinyin: 'shēng', tone: 1, unit: 'u8', radical: 'sheng', strokes: 5, emoji: '🌱',
    meaning: '出生、生长，也指学生。',
    words: [
      { w: '学生', p: 'xué shēng' },
      { w: '生日', p: 'shēng rì' },
      { w: '花生', p: 'huā shēng' }
    ],
    sentence: { text: '今天是我的生日。', p: 'jīn tiān shì wǒ de shēng rì.' }
  },
  {
    char: '书', pinyin: 'shū', tone: 1, unit: 'u8', radical: 'yizhe', strokes: 4, emoji: '📕',
    meaning: '一本一本的书，里面有很多字。',
    words: [
      { w: '看书', p: 'kàn shū' },
      { w: '读书', p: 'dú shū' },
      { w: '书本', p: 'shū běn' }
    ],
    sentence: { text: '我在家里看书。', p: 'wǒ zài jiā lǐ kàn shū.' }
  },
  {
    char: '字', pinyin: 'zì', tone: 4, unit: 'u8', radical: 'mian', strokes: 6, emoji: '🔤',
    meaning: '写下来的汉字。',
    words: [
      { w: '写字', p: 'xiě zì' },
      { w: '汉字', p: 'hàn zì' },
      { w: '生字', p: 'shēng zì' }
    ],
    sentence: { text: '我会写一百个字。', p: 'wǒ huì xiě yī bǎi gè zì.' }
  },
  {
    char: '读', pinyin: 'dú', tone: 2, unit: 'u8', radical: 'yan', strokes: 10, emoji: '📖',
    meaning: '把字念出声来。',
    words: [
      { w: '读书', p: 'dú shū' },
      { w: '朗读', p: 'lǎng dú' },
      { w: '读一读', p: 'dú yī dú' }
    ],
    sentence: { text: '老师读书给我们听。', p: 'lǎo shī dú shū gěi wǒ men tīng.' }
  },
  {
    char: '写', pinyin: 'xiě', tone: 3, unit: 'u8', radical: 'mibao', strokes: 5, emoji: '✍️',
    meaning: '用笔把字记下来。',
    words: [
      { w: '写字', p: 'xiě zì' },
      { w: '写好', p: 'xiě hǎo' },
      { w: '书写', p: 'shū xiě' }
    ],
    sentence: { text: '我用小手写字。', p: 'wǒ yòng xiǎo shǒu xiě zì.' }
  },
  {
    char: '听', pinyin: 'tīng', tone: 1, unit: 'u8', radical: 'kou', strokes: 7, emoji: '👂',
    meaning: '用耳朵听声音。',
    words: [
      { w: '听话', p: 'tīng huà' },
      { w: '好听', p: 'hǎo tīng' },
      { w: '听见', p: 'tīng jiàn' }
    ],
    sentence: { text: '我听见小鸟在唱歌。', p: 'wǒ tīng jiàn xiǎo niǎo zài chàng gē.' }
  },

  // ------------------------------ 单元九 ------------------------------
  {
    char: '鱼', pinyin: 'yú', tone: 2, unit: 'u9', radical: 'yu', strokes: 8, emoji: '🐟',
    meaning: '在水里游来游去的鱼。',
    words: [
      { w: '小鱼', p: 'xiǎo yú' },
      { w: '金鱼', p: 'jīn yú' },
      { w: '鱼儿', p: 'yú ér' }
    ],
    sentence: { text: '水里有很多小鱼。', p: 'shuǐ lǐ yǒu hěn duō xiǎo yú.' }
  },
  {
    char: '虫', pinyin: 'chóng', tone: 2, unit: 'u9', radical: 'chong', strokes: 6, emoji: '🐛',
    meaning: '小虫子，在草里慢慢爬。',
    words: [
      { w: '小虫', p: 'xiǎo chóng' },
      { w: '虫子', p: 'chóng zi' },
      { w: '毛毛虫', p: 'máo mao chóng' }
    ],
    sentence: { text: '草里有一只小虫。', p: 'cǎo lǐ yǒu yī zhī xiǎo chóng.' }
  },
  {
    char: '马', pinyin: 'mǎ', tone: 3, unit: 'u9', radical: 'ma', strokes: 3, emoji: '🐴',
    meaning: '跑得很快的马。',
    words: [
      { w: '小马', p: 'xiǎo mǎ' },
      { w: '马车', p: 'mǎ chē' },
      { w: '木马', p: 'mù mǎ' }
    ],
    sentence: { text: '小马在草地上跑。', p: 'xiǎo mǎ zài cǎo dì shàng pǎo.' }
  },
  {
    char: '猫', pinyin: 'māo', tone: 1, unit: 'u9', radical: 'quan', strokes: 11, emoji: '🐱',
    meaning: '喵喵叫的小猫。',
    words: [
      { w: '小猫', p: 'xiǎo māo' },
      { w: '花猫', p: 'huā māo' },
      { w: '猫咪', p: 'māo mī' }
    ],
    sentence: { text: '小猫在门口睡觉。', p: 'xiǎo māo zài mén kǒu shuì jiào.' }
  },
  {
    char: '狗', pinyin: 'gǒu', tone: 3, unit: 'u9', radical: 'quan', strokes: 8, emoji: '🐶',
    meaning: '汪汪叫的小狗。',
    words: [
      { w: '小狗', p: 'xiǎo gǒu' },
      { w: '大狗', p: 'dà gǒu' },
      { w: '狗窝', p: 'gǒu wō' }
    ],
    sentence: { text: '小狗和小猫是好朋友。', p: 'xiǎo gǒu hé xiǎo māo shì hǎo péng you.' }
  },

  // ------------------------------ 单元十 ------------------------------
  {
    char: '红', pinyin: 'hóng', tone: 2, unit: 'u10', radical: 'jiaosi', strokes: 6, emoji: '🔴',
    meaning: '像火一样的红色。',
    words: [
      { w: '红色', p: 'hóng sè' },
      { w: '红花', p: 'hóng huā' },
      { w: '火红', p: 'huǒ hóng' }
    ],
    sentence: { text: '树上有一朵红花。', p: 'shù shàng yǒu yī duǒ hóng huā.' }
  },
  {
    char: '黄', pinyin: 'huáng', tone: 2, unit: 'u10', radical: 'huang', strokes: 11, emoji: '🟡',
    meaning: '像太阳一样的黄色。',
    words: [
      { w: '黄色', p: 'huáng sè' },
      { w: '黄牛', p: 'huáng niú' },
      { w: '金黄', p: 'jīn huáng' }
    ],
    sentence: { text: '秋天树叶变黄了。', p: 'qiū tiān shù yè biàn huáng le.' }
  },
  {
    char: '蓝', pinyin: 'lán', tone: 2, unit: 'u10', radical: 'cao', strokes: 13, emoji: '🔵',
    meaning: '像天空一样的蓝色。',
    words: [
      { w: '蓝色', p: 'lán sè' },
      { w: '蓝天', p: 'lán tiān' },
      { w: '天蓝', p: 'tiān lán' }
    ],
    sentence: { text: '蓝天上有白云。', p: 'lán tiān shàng yǒu bái yún.' }
  },
  {
    char: '绿', pinyin: 'lǜ', tone: 4, unit: 'u10', radical: 'jiaosi', strokes: 11, emoji: '🟢',
    meaning: '像小草一样的绿色。',
    words: [
      { w: '绿色', p: 'lǜ sè' },
      { w: '绿草', p: 'lǜ cǎo' },
      { w: '绿叶', p: 'lǜ yè' }
    ],
    sentence: { text: '春天的草是绿的。', p: 'chūn tiān de cǎo shì lǜ de.' }
  },
  {
    char: '白', pinyin: 'bái', tone: 2, unit: 'u10', radical: 'bai', strokes: 5, emoji: '⚪',
    meaning: '像雪一样的白色。',
    words: [
      { w: '白色', p: 'bái sè' },
      { w: '白云', p: 'bái yún' },
      { w: '白天', p: 'bái tiān' }
    ],
    sentence: { text: '白白的云在天上。', p: 'bái bái de yún zài tiān shàng.' }
  },
  {
    char: '黑', pinyin: 'hēi', tone: 1, unit: 'u10', radical: 'hei', strokes: 12, emoji: '⚫',
    meaning: '晚上天黑黑的，什么也看不见。',
    words: [
      { w: '黑色', p: 'hēi sè' },
      { w: '黑马', p: 'hēi mǎ' },
      { w: '天黑', p: 'tiān hēi' }
    ],
    sentence: { text: '天黑了，小猫回家了。', p: 'tiān hēi le, xiǎo māo huí jiā le.' }
  },

  // ------------------------------ 单元十一 ------------------------------
  {
    char: '春', pinyin: 'chūn', tone: 1, unit: 'u11', radical: 'ri', strokes: 9, emoji: '🌷',
    meaning: '春天来了，花都开了。',
    words: [
      { w: '春天', p: 'chūn tiān' },
      { w: '春风', p: 'chūn fēng' },
      { w: '春雨', p: 'chūn yǔ' }
    ],
    sentence: { text: '春天来了，花都开了。', p: 'chūn tiān lái le, huā dōu kāi le.' }
  },
  {
    char: '夏', pinyin: 'xià', tone: 4, unit: 'u11', radical: 'zhiwen', strokes: 10, emoji: '🌞',
    meaning: '夏天很热，太阳很大。',
    words: [
      { w: '夏天', p: 'xià tiān' },
      { w: '夏日', p: 'xià rì' },
      { w: '夏夜', p: 'xià yè' }
    ],
    sentence: { text: '夏天的太阳很大。', p: 'xià tiān de tài yáng hěn dà.' }
  },
  {
    char: '秋', pinyin: 'qiū', tone: 1, unit: 'u11', radical: 'he', strokes: 9, emoji: '🍂',
    meaning: '秋天到了，树叶黄了。',
    words: [
      { w: '秋天', p: 'qiū tiān' },
      { w: '秋风', p: 'qiū fēng' },
      { w: '中秋', p: 'zhōng qiū' }
    ],
    sentence: { text: '秋风一吹，树叶落下来。', p: 'qiū fēng yī chuī, shù yè luò xià lái.' }
  },
  {
    char: '冬', pinyin: 'dōng', tone: 1, unit: 'u11', radical: 'zhiwen', strokes: 5, emoji: '⛄',
    meaning: '冬天很冷，还会下雪。',
    words: [
      { w: '冬天', p: 'dōng tiān' },
      { w: '冬日', p: 'dōng rì' },
      { w: '过冬', p: 'guò dōng' }
    ],
    sentence: { text: '冬天下雪了。', p: 'dōng tiān xià xuě le.' }
  },
  {
    char: '早', pinyin: 'zǎo', tone: 3, unit: 'u11', radical: 'ri', strokes: 6, emoji: '🌅',
    meaning: '早上，太阳刚刚出来。',
    words: [
      { w: '早上', p: 'zǎo shang' },
      { w: '早安', p: 'zǎo ān' },
      { w: '一早', p: 'yī zǎo' }
    ],
    sentence: { text: '早上我和母亲去上学。', p: 'zǎo shang wǒ hé mǔ qīn qù shàng xué.' }
  },
  {
    char: '晚', pinyin: 'wǎn', tone: 3, unit: 'u11', radical: 'ri', strokes: 11, emoji: '🌆',
    meaning: '晚上，天已经黑了。',
    words: [
      { w: '晚上', p: 'wǎn shang' },
      { w: '今晚', p: 'jīn wǎn' },
      { w: '晚安', p: 'wǎn ān' }
    ],
    sentence: { text: '晚上我们说晚安。', p: 'wǎn shang wǒ men shuō wǎn ān.' }
  },
  {
    char: '明', pinyin: 'míng', tone: 2, unit: 'u11', radical: 'ri', strokes: 8, emoji: '🌞',
    meaning: '日和月在一起，又亮又明。',
    words: [
      { w: '明天', p: 'míng tiān' },
      { w: '明白', p: 'míng bai' },
      { w: '明月', p: 'míng yuè' }
    ],
    sentence: { text: '明天我们去看小马。', p: 'míng tiān wǒ men qù kàn xiǎo mǎ.' }
  },
  {
    char: '今', pinyin: 'jīn', tone: 1, unit: 'u11', radical: 'renzitou', strokes: 4, emoji: '📅',
    meaning: '现在的这一天，就是今天。',
    words: [
      { w: '今天', p: 'jīn tiān' },
      { w: '今年', p: 'jīn nián' },
      { w: '今晚', p: 'jīn wǎn' }
    ],
    sentence: { text: '今天的天气很好。', p: 'jīn tiān de tiān qì hěn hǎo.' }
  },
  {
    char: '年', pinyin: 'nián', tone: 2, unit: 'u11', radical: 'pie', strokes: 6, emoji: '🎊',
    meaning: '一年有十二个月。',
    words: [
      { w: '今年', p: 'jīn nián' },
      { w: '新年', p: 'xīn nián' },
      { w: '过年', p: 'guò nián' }
    ],
    sentence: { text: '过年了，我们都很开心。', p: 'guò nián le, wǒ men dōu hěn kāi xīn.' }
  },
  {
    char: '时', pinyin: 'shí', tone: 2, unit: 'u11', radical: 'ri', strokes: 7, emoji: '⏰',
    meaning: '时间，钟表上走的就是它。',
    words: [
      { w: '时间', p: 'shí jiān' },
      { w: '小时', p: 'xiǎo shí' },
      { w: '时时', p: 'shí shí' }
    ],
    sentence: { text: '读书的时间到了。', p: 'dú shū de shí jiān dào le.' }
  },

  // ------------------------------ 单元十二 ------------------------------
  {
    char: '左', pinyin: 'zuǒ', tone: 3, unit: 'u12', radical: 'gong', strokes: 5, emoji: '👈',
    meaning: '左边，和右边正好相反。',
    words: [
      { w: '左手', p: 'zuǒ shǒu' },
      { w: '左边', p: 'zuǒ biān' },
      { w: '左右', p: 'zuǒ yòu' }
    ],
    sentence: { text: '我的左手拿着书。', p: 'wǒ de zuǒ shǒu ná zhe shū.' }
  },
  {
    char: '右', pinyin: 'yòu', tone: 4, unit: 'u12', radical: 'kou', strokes: 5, emoji: '👉',
    meaning: '右边，大多数人用右手写字。',
    words: [
      { w: '右手', p: 'yòu shǒu' },
      { w: '右边', p: 'yòu biān' },
      { w: '左右', p: 'zuǒ yòu' }
    ],
    sentence: { text: '我用右手写字。', p: 'wǒ yòng yòu shǒu xiě zì.' }
  },
  {
    char: '多', pinyin: 'duō', tone: 1, unit: 'u12', radical: 'xi', strokes: 6, emoji: '➕',
    meaning: '数量很多，两个夕叠在一起。',
    words: [
      { w: '很多', p: 'hěn duō' },
      { w: '多少', p: 'duō shao' },
      { w: '多了', p: 'duō le' }
    ],
    sentence: { text: '天上的星星很多。', p: 'tiān shàng de xīng xing hěn duō.' }
  },
  {
    char: '少', pinyin: 'shǎo', tone: 3, unit: 'u12', radical: 'xiao', strokes: 4, emoji: '➖',
    meaning: '数量不多，和「多」相反。',
    words: [
      { w: '很少', p: 'hěn shǎo' },
      { w: '多少', p: 'duō shao' },
      { w: '少了', p: 'shǎo le' }
    ],
    sentence: { text: '水里的小鱼很少。', p: 'shuǐ lǐ de xiǎo yú hěn shǎo.' }
  },
  {
    char: '门', pinyin: 'mén', tone: 2, unit: 'u12', radical: 'men', strokes: 3, emoji: '🚪',
    meaning: '进出都要走门。',
    words: [
      { w: '大门', p: 'dà mén' },
      { w: '开门', p: 'kāi mén' },
      { w: '门口', p: 'mén kǒu' }
    ],
    sentence: { text: '小狗在门口等我。', p: 'xiǎo gǒu zài mén kǒu děng wǒ.' }
  },
  {
    char: '车', pinyin: 'chē', tone: 1, unit: 'u12', radical: 'che', strokes: 4, emoji: '🚗',
    meaning: '车子，会在路上跑。',
    words: [
      { w: '火车', p: 'huǒ chē' },
      { w: '汽车', p: 'qì chē' },
      { w: '上车', p: 'shàng chē' }
    ],
    sentence: { text: '我们坐火车去看山。', p: 'wǒ men zuò huǒ chē qù kàn shān.' }
  },
  {
    char: '足', pinyin: 'zú', tone: 2, unit: 'u12', radical: 'zu', strokes: 7, emoji: '🦶',
    meaning: '脚，用来走路和跑步。',
    words: [
      { w: '足球', p: 'zú qiú' },
      { w: '手足', p: 'shǒu zú' },
      { w: '不足', p: 'bù zú' }
    ],
    sentence: { text: '我用足走路，用手写字。', p: 'wǒ yòng zú zǒu lù, yòng shǒu xiě zì.' }
  }
]

export const CHARACTER_MAP = new Map(CHARACTERS.map((c) => [c.char, c]))

/**
 * 查一个字。既接受 '人' 这样的字符串，也接受已经查出来的字条目本身，
 * 这样调用方不必先判断手里拿到的是 id 还是对象。
 */
export function getCharacter(char) {
  if (!char) return null
  const key = typeof char === 'string' ? char : char.char
  return CHARACTER_MAP.get(key) || null
}

export function charsOfUnit(unitId) {
  return CHARACTERS.filter((c) => c.unit === unitId)
}

export function unitById(unitId) {
  return UNITS.find((u) => u.id === unitId) || null
}

export const TOTAL_CHARACTERS = CHARACTERS.length
