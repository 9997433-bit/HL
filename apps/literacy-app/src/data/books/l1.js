/**
 * 第 1 级扩展绘本 —— 由 scripts/gen-books.mjs 生成，请勿手改。
 * 正文改动请编辑 scripts/data/book-seed-*.mjs 后重新生成。
 */

export const LEVEL_1_BOOKS = [
  {
    id: 'bx1',
    title: '水里的朋友',
    pinyin: 'shuǐ lǐ de péng you',
    level: 1,
    levelName: '第 1 级 · 一页一个小动物',
    cover: '🐟',
    palette: ['#ffe6b3', '#c8ebff'],
    summary: '鱼、虾、蟹、龟、蛙，水里水边都是小伙伴。',
    newChars: ['鱼', '虾', '石', '头', '蟹', '龟', '慢', '岸'],
    pages: [
      { emoji: '🐟', text: '水里有鱼。', p: 'shuǐ lǐ yǒu yú.' },
      { emoji: '🦐', text: '水里有虾，虾很小。', p: 'shuǐ lǐ yǒu xiā, xiā hěn xiǎo.' },
      { emoji: '🦀', text: '石头下有蟹。', p: 'shí tou xià yǒu xiè.' },
      { emoji: '🐢', text: '水里还有龟，龟很慢。', p: 'shuǐ lǐ hái yǒu guī, guī hěn màn.' },
      { emoji: '🐸', text: '岸上有蛙，蛙会跳。', p: 'àn shàng yǒu wā, wā huì tiào.' },
      { emoji: '🌊', text: '水里的朋友真多！', p: 'shuǐ lǐ de péng you zhēn duō!' }
    ]
  },
  {
    id: 'bx2',
    title: '天上飞的',
    pinyin: 'tiān shàng fēi de',
    level: 1,
    levelName: '第 1 级 · 谁会飞',
    cover: '🐦',
    palette: ['#d9f6f3', '#ffe0e6'],
    summary: '鸟会飞，蝶会飞，蜂也会飞。蚁不会飞，蚁在地上走。',
    newChars: ['鸟', '会', '飞', '花', '蝶', '蜂', '蜜', '蚁'],
    pages: [
      { emoji: '🐦', text: '天上有鸟，鸟会飞。', p: 'tiān shàng yǒu niǎo, niǎo huì fēi.' },
      { emoji: '🦋', text: '花上有蝶，蝶也会飞。', p: 'huā shàng yǒu dié, dié yě huì fēi.' },
      { emoji: '🐝', text: '蜂在花上飞，蜂会做蜜。', p: 'fēng zài huā shàng fēi, fēng huì zuò mì.' },
      { emoji: '🐜', text: '蚁不会飞，蚁在地上走。', p: 'yǐ bù huì fēi, yǐ zài dì shàng zǒu.' },
      { emoji: '✈️', text: '天上有飞机，飞机很大。', p: 'tiān shàng yǒu fēi jī, fēi jī hěn dà.' },
      { emoji: '☁️', text: '我看天上，天上真高！', p: 'wǒ kàn tiān shàng, tiān shàng zhēn gāo!' }
    ]
  },
  {
    id: 'bx3',
    title: '山上山下的树',
    pinyin: 'shān shàng shān xià de shù',
    level: 1,
    levelName: '第 1 级 · 一页一种树',
    cover: '🌲',
    palette: ['#e8e0ff', '#fff1cf'],
    summary: '松高柳长，桃红梨黄，一页看一种树。',
    newChars: ['山', '松', '高', '柳', '枝', '长', '园', '桃'],
    pages: [
      { emoji: '🌲', text: '山上有松，松很高。', p: 'shān shàng yǒu sōng, sōng hěn gāo.' },
      { emoji: '🌳', text: '山下有柳，柳的枝很长。', p: 'shān xià yǒu liǔ, liǔ de zhī hěn cháng.' },
      { emoji: '🍑', text: '园里有桃，桃是红的。', p: 'yuán lǐ yǒu táo, táo shì hóng de.' },
      { emoji: '🌰', text: '树上有枣，枣也是红的。', p: 'shù shàng yǒu zǎo, zǎo yě shì hóng de.' },
      { emoji: '🍐', text: '那是梨树，梨是黄的。', p: 'nà shì lí shù, lí shì huáng de.' },
      { emoji: '🍃', text: '树多，叶也多。', p: 'shù duō, yè yě duō.' }
    ]
  },
  {
    id: 'bx4',
    title: '这是我的',
    pinyin: 'zhè shì wǒ de',
    level: 1,
    levelName: '第 1 级 · 从头认到脚',
    cover: '🧒',
    palette: ['#ffe0c2', '#e6f5c9'],
    summary: '眼耳鼻嘴手脚，指一指，说一说，都是我的。',
    newChars: ['眼', '耳', '鼻', '嘴', '手', '指', '脚', '会'],
    pages: [
      { emoji: '👀', text: '这是我的眼。', p: 'zhè shì wǒ de yǎn.' },
      { emoji: '👂', text: '这是我的耳。', p: 'zhè shì wǒ de ěr.' },
      { emoji: '👃', text: '这是我的鼻。', p: 'zhè shì wǒ de bí.' },
      { emoji: '👄', text: '这是我的嘴。', p: 'zhè shì wǒ de zuǐ.' },
      { emoji: '✋', text: '这是我的手，手上有指。', p: 'zhè shì wǒ de shǒu, shǒu shàng yǒu zhǐ.' },
      { emoji: '🦶', text: '这是我的脚，脚会走路。', p: 'zhè shì wǒ de jiǎo, jiǎo huì zǒu lù.' },
      { emoji: '🧒', text: '这都是我的身体。', p: 'zhè dōu shì wǒ de shēn tǐ.' }
    ]
  },
  {
    id: 'bx5',
    title: '桌上的饭菜',
    pinyin: 'zhuō shàng de fàn cài',
    level: 1,
    levelName: '第 1 级 · 一页一样吃的',
    cover: '🍚',
    palette: ['#c8ebff', '#e8e0ff'],
    summary: '米饭、菜、蛋、奶、汤，一桌子都摆好了。',
    newChars: ['桌', '米', '饭', '菜', '绿', '碗', '蛋', '杯'],
    pages: [
      { emoji: '🍚', text: '桌上有米饭。', p: 'zhuō shàng yǒu mǐ fàn.' },
      { emoji: '🥬', text: '桌上有菜，菜是绿的。', p: 'zhuō shàng yǒu cài, cài shì lǜ de.' },
      { emoji: '🥚', text: '碗里有一个蛋。', p: 'wǎn lǐ yǒu yī gè dàn.' },
      { emoji: '🥛', text: '杯里有奶，奶是白的。', p: 'bēi lǐ yǒu nǎi, nǎi shì bái de.' },
      { emoji: '🍲', text: '还有一碗汤，汤很热。', p: 'hái yǒu yī wǎn tāng, tāng hěn rè.' },
      { emoji: '😋', text: '这些我都爱吃！', p: 'zhè xiē wǒ dōu ài chī!' }
    ]
  },
  {
    id: 'bx6',
    title: '我的衣和鞋',
    pinyin: 'wǒ de yī hé xié',
    level: 1,
    levelName: '第 1 级 · 身上的字',
    cover: '👕',
    palette: ['#ffd6d6', '#d9f6f3'],
    summary: '衣、裤、袜、鞋、帽，一页一样，都是我的。',
    newChars: ['衣', '裤', '袜', '鞋', '帽', '这', '是', '我'],
    pages: [
      { emoji: '👕', text: '这是我的衣。', p: 'zhè shì wǒ de yī.' },
      { emoji: '👖', text: '这是我的裤。', p: 'zhè shì wǒ de kù.' },
      { emoji: '🧦', text: '这是我的袜。', p: 'zhè shì wǒ de wà.' },
      { emoji: '👟', text: '这是我的鞋。', p: 'zhè shì wǒ de xié.' },
      { emoji: '🧢', text: '这是我的帽。', p: 'zhè shì wǒ de mào.' },
      { emoji: '🎒', text: '衣裤鞋帽，都是我的。', p: 'yī kù xié mào, dōu shì wǒ de.' }
    ]
  },
  {
    id: 'bx7',
    title: '花园里',
    pinyin: 'huā yuán lǐ',
    level: 1,
    levelName: '第 1 级 · 花草和小虫',
    cover: '🌸',
    palette: ['#e6f5c9', '#ffe6b3'],
    summary: '红花在左，黄花在右，蜂和蝶都来了。',
    newChars: ['园', '花', '草', '高', '红', '左', '边', '黄'],
    pages: [
      { emoji: '🌸', text: '园里有花。', p: 'yuán lǐ yǒu huā.' },
      { emoji: '🌿', text: '园里有草，草不高。', p: 'yuán lǐ yǒu cǎo, cǎo bù gāo.' },
      { emoji: '🌹', text: '红花在左边，黄花在右边。', p: 'hóng huā zài zuǒ bian, huáng huā zài yòu bian.' },
      { emoji: '🍀', text: '草是绿的，叶也是绿的。', p: 'cǎo shì lǜ de, yè yě shì lǜ de.' },
      { emoji: '🐝', text: '蜂来了，蝶也来了。', p: 'fēng lái le, dié yě lái le.' },
      { emoji: '🌼', text: '我爱这个花园。', p: 'wǒ ài zhè gè huā yuán.' }
    ]
  },
  {
    id: 'bx8',
    title: '路上的车',
    pinyin: 'lù shàng de chē',
    level: 1,
    levelName: '第 1 级 · 会走的都在这里',
    cover: '🚗',
    palette: ['#fff1cf', '#ffd6d6'],
    summary: '大车小车、火车和船，路上真热闹。',
    newChars: ['路', '车', '慢', '快', '会', '骑', '铁', '火'],
    pages: [
      { emoji: '🚗', text: '路上有车。', p: 'lù shàng yǒu chē.' },
      { emoji: '🚌', text: '大车很慢，小车很快。', p: 'dà chē hěn màn, xiǎo chē hěn kuài.' },
      { emoji: '🚲', text: '我会骑车。', p: 'wǒ huì qí chē.' },
      { emoji: '🚂', text: '铁路上有火车，火车很长。', p: 'tiě lù shàng yǒu huǒ chē, huǒ chē hěn cháng.' },
      { emoji: '⛵', text: '河上有船，船不走路。', p: 'hé shàng yǒu chuán, chuán bù zǒu lù.' },
      { emoji: '🚦', text: '路上车多，我们要小心。', p: 'lù shàng chē duō, wǒ men yào xiǎo xīn.' }
    ]
  },
  {
    id: 'bx9',
    title: '屋里有什么',
    pinyin: 'wū lǐ yǒu shén me',
    level: 1,
    levelName: '第 1 级 · 家里的东西',
    cover: '🛋️',
    palette: ['#c8ebff', '#e6f5c9'],
    summary: '桌椅床灯窗门，一页认一样。',
    newChars: ['屋', '桌', '椅', '床', '毯', '灯', '亮', '窗'],
    pages: [
      { emoji: '🛋️', text: '屋里有桌，也有椅。', p: 'wū lǐ yǒu zhuō, yě yǒu yǐ.' },
      { emoji: '🛏️', text: '屋里有床，床上有毯。', p: 'wū lǐ yǒu chuáng, chuáng shàng yǒu tǎn.' },
      { emoji: '💡', text: '屋里有灯，灯很亮。', p: 'wū lǐ yǒu dēng, dēng hěn liàng.' },
      { emoji: '🪟', text: '屋里有窗，窗外有树。', p: 'wū lǐ yǒu chuāng, chuāng wài yǒu shù.' },
      { emoji: '🚪', text: '屋里有门，门开了。', p: 'wū lǐ yǒu mén, mén kāi le.' },
      { emoji: '🏠', text: '这就是我的家。', p: 'zhè jiù shì wǒ de jiā.' }
    ]
  },
  {
    id: 'bx10',
    title: '田里有什么',
    pinyin: 'tián lǐ yǒu shén me',
    level: 1,
    levelName: '第 1 级 · 看看庄稼',
    cover: '🌾',
    palette: ['#ffe0e6', '#fff1cf'],
    summary: '稻、麦、豆和牛，农人在田里忙。',
    newChars: ['田', '稻', '麦', '黄', '豆', '边', '牛', '吃'],
    pages: [
      { emoji: '🌾', text: '田里有稻。', p: 'tián lǐ yǒu dào.' },
      { emoji: '🌽', text: '田里有麦，麦是黄的。', p: 'tián lǐ yǒu mài, mài shì huáng de.' },
      { emoji: '🫘', text: '田里有豆，豆很小。', p: 'tián lǐ yǒu dòu, dòu hěn xiǎo.' },
      { emoji: '🐄', text: '田边有牛，牛在吃草。', p: 'tián biān yǒu niú, niú zài chī cǎo.' },
      { emoji: '👨‍🌾', text: '农人在田里忙。', p: 'nóng rén zài tián lǐ máng.' },
      { emoji: '🌞', text: '日光下，田很亮。', p: 'rì guāng xià, tián hěn liàng.' }
    ]
  },
  {
    id: 'bx11',
    title: '甜甜的果',
    pinyin: 'tián tián de guǒ',
    level: 1,
    levelName: '第 1 级 · 果子的色和味',
    cover: '🍎',
    palette: ['#d9f6f3', '#ffe0c2'],
    summary: '苹果红、梨黄、瓜大，一页尝一样。',
    newChars: ['苹', '果', '红', '甜', '梨', '黄', '葡', '萄'],
    pages: [
      { emoji: '🍎', text: '苹果是红的，很甜。', p: 'píng guǒ shì hóng de, hěn tián.' },
      { emoji: '🍐', text: '梨是黄的，也很甜。', p: 'lí shì huáng de, yě hěn tián.' },
      { emoji: '🍇', text: '葡萄小小的，一口一个。', p: 'pú táo xiǎo xiǎo de, yī kǒu yī gè.' },
      { emoji: '🍊', text: '橘是黄的，有点酸。', p: 'jú shì huáng de, yǒu diǎn suān.' },
      { emoji: '🍉', text: '瓜很大，瓜里是红的。', p: 'guā hěn dà, guā lǐ shì hóng de.' },
      { emoji: '😋', text: '果子真多，我都爱吃。', p: 'guǒ zǐ zhēn duō, wǒ dōu ài chī.' }
    ]
  },
  {
    id: 'bx12',
    title: '白天和夜里',
    pinyin: 'bái tiān hé yè lǐ',
    level: 1,
    levelName: '第 1 级 · 一天有两半',
    cover: '🌗',
    palette: ['#e8e0ff', '#c8ebff'],
    summary: '白天有日，夜里有月和星，灯一亮就该睡了。',
    newChars: ['白', '亮', '边', '玩', '夜', '星', '屋', '灯'],
    pages: [
      { emoji: '☀️', text: '白天，天上有日。', p: 'bái tiān, tiān shàng yǒu rì.' },
      { emoji: '🌤️', text: '白天很亮，我在外边玩。', p: 'bái tiān hěn liàng, wǒ zài wài bian wán.' },
      { emoji: '🌙', text: '夜里，天上有月。', p: 'yè lǐ, tiān shàng yǒu yuè.' },
      { emoji: '⭐', text: '夜里有星，星很多。', p: 'yè lǐ yǒu xīng, xīng hěn duō.' },
      { emoji: '💡', text: '夜里，屋里的灯亮了。', p: 'yè lǐ, wū lǐ de dēng liàng le.' },
      { emoji: '😴', text: '夜深了，我要睡了。', p: 'yè shēn le, wǒ yào shuì le.' }
    ]
  },
  {
    id: 'bx13',
    title: '上下左右',
    pinyin: 'shàng xià zuǒ yòu',
    level: 1,
    levelName: '第 1 级 · 说得清方向',
    cover: '🧭',
    palette: ['#ffe6b3', '#ffd6d6'],
    summary: '天上地下、左手右手、前门后窗，方向一次说清。',
    newChars: ['边', '地', '左', '手', '右', '门', '窗', '会'],
    pages: [
      { emoji: '⬆️', text: '天在上边。', p: 'tiān zài shàng bian.' },
      { emoji: '⬇️', text: '地在下边。', p: 'dì zài xià bian.' },
      { emoji: '⬅️', text: '我的左手在左边。', p: 'wǒ de zuǒ shǒu zài zuǒ bian.' },
      { emoji: '➡️', text: '我的右手在右边。', p: 'wǒ de yòu shǒu zài yòu bian.' },
      { emoji: '🚪', text: '前边有门，后边有窗。', p: 'qián bian yǒu mén, hòu bian yǒu chuāng.' },
      { emoji: '🧭', text: '上下左右，我都会说！', p: 'shàng xià zuǒ yòu, wǒ dōu huì shuō!' }
    ]
  },
  {
    id: 'bx14',
    title: '我会做什么',
    pinyin: 'wǒ huì zuò shén me',
    level: 1,
    levelName: '第 1 级 · 我会的可不少',
    cover: '🏃',
    palette: ['#e6f5c9', '#c8ebff'],
    summary: '走跑跳坐站，吃饭喝水唱歌，我会的真多。',
    newChars: ['会', '走', '跑', '跳', '高', '坐', '站', '吃'],
    pages: [
      { emoji: '🏃', text: '我会走，也会跑。', p: 'wǒ huì zǒu, yě huì pǎo.' },
      { emoji: '🤸', text: '我会跳，跳很高。', p: 'wǒ huì tiào, tiào hěn gāo.' },
      { emoji: '🪑', text: '我会坐，也会站。', p: 'wǒ huì zuò, yě huì zhàn.' },
      { emoji: '🍚', text: '我会吃饭，也会喝水。', p: 'wǒ huì chī fàn, yě huì hē shuǐ.' },
      { emoji: '🎤', text: '我会唱歌，也会笑。', p: 'wǒ huì chàng gē, yě huì xiào.' },
      { emoji: '😄', text: '我会的真多！', p: 'wǒ huì de zhēn duō!' }
    ]
  },
  {
    id: 'bx15',
    title: '十只小虫',
    pinyin: 'shí zhī xiǎo chóng',
    level: 1,
    levelName: '第 1 级 · 数着数着就数完了',
    cover: '🐛',
    palette: ['#ffd6d6', '#e8e0ff'],
    summary: '一只、二只、三只、四只，加在一同正好十只。',
    newChars: ['只', '虫', '叶', '蚁', '地', '蜂', '花', '蝶'],
    pages: [
      { emoji: '🐛', text: '一只小虫在叶上。', p: 'yī zhī xiǎo chóng zài yè shàng.' },
      { emoji: '🐜', text: '二只蚁在地上。', p: 'èr zhī yǐ zài dì shàng.' },
      { emoji: '🐝', text: '三只蜂在花上。', p: 'sān zhī fēng zài huā shàng.' },
      { emoji: '🦋', text: '四只蝶在风里。', p: 'sì zhī dié zài fēng lǐ.' },
      { emoji: '🔢', text: '我数一数：一，二，三，四。', p: 'wǒ shǔ yī shǔ: yī, èr, sān, sì.' },
      { emoji: '🌸', text: '一共十只小虫！', p: 'yī gòng shí zhī xiǎo chóng!' }
    ]
  },
  {
    id: 'bx16',
    title: '圆的和方的',
    pinyin: 'yuán de hé fāng de',
    level: 1,
    levelName: '第 1 级 · 看一看是什么形',
    cover: '⭕',
    palette: ['#fff1cf', '#d9f6f3'],
    summary: '日圆窗方、球圆箱方，一页比一对。',
    newChars: ['圆', '会', '窗', '方', '箱', '球', '打', '碗'],
    pages: [
      { emoji: '⭕', text: '日是圆的。', p: 'rì shì yuán de.' },
      { emoji: '🌕', text: '月也会是圆的。', p: 'yuè yě huì shì yuán de.' },
      { emoji: '🔲', text: '窗是方的。', p: 'chuāng shì fāng de.' },
      { emoji: '📦', text: '箱是方的。', p: 'xiāng shì fāng de.' },
      { emoji: '⚽', text: '球是圆的，我会打球。', p: 'qiú shì yuán de, wǒ huì dǎ qiú.' },
      { emoji: '🍽️', text: '碗是圆的，桌是方的。', p: 'wǎn shì yuán de, zhuō shì fāng de.' },
      { emoji: '👀', text: '圆的方的，我都认识。', p: 'yuán de fāng de, wǒ dōu rèn shi.' }
    ]
  },
  {
    id: 'bx17',
    title: '天冷天热',
    pinyin: 'tiān lěng tiān rè',
    level: 1,
    levelName: '第 1 级 · 冬天和夏天',
    cover: '🌡️',
    palette: ['#ffe0c2', '#c8ebff'],
    summary: '天冷了要帽和衣，天热了吃瓜喝水。',
    newChars: ['冬', '冷', '帽', '身', '厚', '衣', '夏', '热'],
    pages: [
      { emoji: '❄️', text: '冬天很冷。', p: 'dōng tiān hěn lěng.' },
      { emoji: '🧣', text: '天冷了，我要帽，也要一身厚衣。', p: 'tiān lěng le, wǒ yào mào, yě yào yī shēn hòu yī.' },
      { emoji: '☀️', text: '夏天很热。', p: 'xià tiān hěn rè.' },
      { emoji: '🍉', text: '天热了，我吃瓜，也喝水。', p: 'tiān rè le, wǒ chī guā, yě hē shuǐ.' },
      { emoji: '🔥', text: '火很热，我不去摸。', p: 'huǒ hěn rè, wǒ bù qù mō.' },
      { emoji: '🌡️', text: '冷和热，我都能说。', p: 'lěng hé rè, wǒ dōu néng shuō.' }
    ]
  },
  {
    id: 'bx18',
    title: '我家的猫和狗',
    pinyin: 'wǒ jiā de māo hé gǒu',
    level: 1,
    levelName: '第 1 级 · 两个小伙伴',
    cover: '🐱',
    palette: ['#c8ebff', '#ffe6b3'],
    summary: '猫爱吃鱼，狗爱吃肉，一个在椅上睡，一个在门口看家。',
    newChars: ['家', '只', '猫', '狗', '爱', '吃', '鱼', '肉'],
    pages: [
      { emoji: '🐱', text: '我家有一只猫。', p: 'wǒ jiā yǒu yī zhī māo.' },
      { emoji: '🐶', text: '我家有一只狗。', p: 'wǒ jiā yǒu yī zhī gǒu.' },
      { emoji: '🐟', text: '猫爱吃鱼。', p: 'māo ài chī yú.' },
      { emoji: '🍖', text: '狗爱吃肉。', p: 'gǒu ài chī ròu.' },
      { emoji: '😺', text: '猫在椅上睡。', p: 'māo zài yǐ shàng shuì.' },
      { emoji: '🐕', text: '狗在门口看家。', p: 'gǒu zài mén kǒu kàn jiā.' },
      { emoji: '❤️', text: '猫和狗都是我的伙伴。', p: 'māo hé gǒu dōu shì wǒ de huǒ bàn.' }
    ]
  },
  {
    id: 'bx19',
    title: '早上和晚上',
    pinyin: 'zǎo shang hé wǎn shang',
    level: 1,
    levelName: '第 1 级 · 一天的头和尾',
    cover: '🌅',
    palette: ['#ffe6b3', '#c8ebff'],
    summary: '早上吃饭上学，晚上读书睡觉，一天就这样过。',
    newChars: ['早', '吃', '饭', '学', '校', '晚', '山', '读'],
    pages: [
      { emoji: '🌅', text: '早上，日来了。', p: 'zǎo shang, rì lái le.' },
      { emoji: '🥣', text: '早上，我吃饭。', p: 'zǎo shang, wǒ chī fàn.' },
      { emoji: '🎒', text: '早上，我去学校。', p: 'zǎo shang, wǒ qù xué xiào.' },
      { emoji: '🌇', text: '晚上，日下山了。', p: 'wǎn shang, rì xià shān le.' },
      { emoji: '📖', text: '晚上，我读书。', p: 'wǎn shang, wǒ dú shū.' },
      { emoji: '🛏️', text: '晚上，我在床上睡。', p: 'wǎn shang, wǒ zài chuáng shàng shuì.' }
    ]
  },
  {
    id: 'bx20',
    title: '好听的声音',
    pinyin: 'hǎo tīng de shēng yīn',
    level: 1,
    levelName: '第 1 级 · 用耳听一听',
    cover: '🔔',
    palette: ['#d9f6f3', '#ffe0e6'],
    summary: '铃声、鸟声、雨声、歌声、鼓声，都用耳朵听。',
    newChars: ['铃', '声', '音', '鸟', '听', '雨', '窗', '妈'],
    pages: [
      { emoji: '🔔', text: '铃有声音。', p: 'líng yǒu shēng yīn.' },
      { emoji: '🐦', text: '鸟的声音很好听。', p: 'niǎo de shēng yīn hěn hǎo tīng.' },
      { emoji: '🌧️', text: '雨的声音在窗外。', p: 'yǔ de shēng yīn zài chuāng wài.' },
      { emoji: '🎵', text: '妈妈的歌很好听。', p: 'mā ma de gē hěn hǎo tīng.' },
      { emoji: '🥁', text: '鼓的声音很重。', p: 'gǔ de shēng yīn hěn zhòng.' },
      { emoji: '👂', text: '我用耳听，声音真多。', p: 'wǒ yòng ěr tīng, shēng yīn zhēn duō.' }
    ]
  }
]
