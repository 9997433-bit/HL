/**
 * 最早的 30 本分级绘本，逐句手写、手工注音，是整套绘本的语感基准。
 *
 * 后面批量生成的扩展绘本（books/l1.js … books/l6.js）在结构上照抄这里：
 * 同样的分级、页、逐句朗读字段。所以这一份不参与生成，改动请直接编辑本文件。
 */

export const CORE_BOOKS = [
  {
    id: 'b1',
    title: '我看大自然',
    pinyin: 'wǒ kàn dà zì rán',
    level: 1,
    levelName: '第 1 级 · 十个字就能读',
    cover: '🌄',
    palette: ['#ffe6b3', '#c8ebff'],
    summary: '天上有什么？山下有什么？跟着小主人公看一看。',
    newChars: ['天', '日', '月', '山', '水', '田', '土', '木', '花'],
    pages: [
      { emoji: '🌅', text: '天上有日，天上有月。', p: 'tiān shàng yǒu rì, tiān shàng yǒu yuè.' },
      { emoji: '⛰️', text: '山下有水，水上有花。', p: 'shān xià yǒu shuǐ, shuǐ shàng yǒu huā.' },
      { emoji: '🌾', text: '田中有土，土上有木。', p: 'tián zhōng yǒu tǔ, tǔ shàng yǒu mù.' },
      { emoji: '🙋', text: '我在山下，我看天上的月。', p: 'wǒ zài shān xià, wǒ kàn tiān shàng de yuè.' },
      { emoji: '🌸', text: '大山，小花，我也会看！', p: 'dà shān, xiǎo huā, wǒ yě huì kàn!' }
    ]
  },
  {
    id: 'b6',
    title: '一二三，数一数',
    pinyin: 'yī èr sān, shǔ yī shǔ',
    level: 1,
    levelName: '第 1 级 · 从一数到十',
    cover: '🔢',
    palette: ['#ffe6b3', '#e8e0ff'],
    summary: '一到十先念一遍，再去数天上的鸟、水里的鱼、山上的花。',
    newChars: ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十'],
    pages: [
      { emoji: '🖐️', text: '一，二，三，四，五。', p: 'yī, èr, sān, sì, wǔ.' },
      { emoji: '✋', text: '六，七，八，九，十。', p: 'liù, qī, bā, jiǔ, shí.' },
      { emoji: '🐦', text: '天上有三只小鸟。', p: 'tiān shàng yǒu sān zhī xiǎo niǎo.' },
      { emoji: '🐟', text: '水里有五条小鱼。', p: 'shuǐ lǐ yǒu wǔ tiáo xiǎo yú.' },
      { emoji: '🌸', text: '山上有花。我数一数，一共十！', p: 'shān shàng yǒu huā. wǒ shǔ yī shǔ, yī gòng shí!' },
      { emoji: '🙋', text: '我会数数，一到十我都会！', p: 'wǒ huì shǔ shù, yī dào shí wǒ dōu huì!' }
    ]
  },
  {
    id: 'b7',
    title: '大大小小',
    pinyin: 'dà dà xiǎo xiǎo',
    level: 1,
    levelName: '第 1 级 · 反过来的字',
    cover: '🐘',
    palette: ['#d9f6f3', '#ffe0c2'],
    summary: '大和小、多和少、远和近，一页看一对。',
    newChars: ['大', '小', '多', '少', '长', '高', '远', '近'],
    pages: [
      { emoji: '🐘', text: '大象大，小马小。', p: 'dà xiàng dà, xiǎo mǎ xiǎo.' },
      { emoji: '🌳', text: '大树高，小草不高。', p: 'dà shù gāo, xiǎo cǎo bù gāo.' },
      { emoji: '🐟', text: '水里的鱼很多，天上的云很少。', p: 'shuǐ lǐ de yú hěn duō, tiān shàng de yún hěn shǎo.' },
      { emoji: '🏔️', text: '山很远，家很近。', p: 'shān hěn yuǎn, jiā hěn jìn.' },
      { emoji: '🐍', text: '小蛇长，小虫不长。', p: 'xiǎo shé cháng, xiǎo chóng bù cháng.' },
      { emoji: '🙋', text: '我不大也不小，我天天在长高！', p: 'wǒ bù dà yě bù xiǎo, wǒ tiān tiān zài zhǎng gāo!' }
    ]
  },
  {
    id: 'b8',
    title: '我的一家人',
    pinyin: 'wǒ de yī jiā rén',
    level: 1,
    levelName: '第 1 级 · 家里有谁',
    cover: '👨‍👩‍👧‍👦',
    palette: ['#ffe0e6', '#fff1cf'],
    summary: '爸爸妈妈爷爷姑姑，一页一个人，读完就认识一家人。',
    newChars: ['爸', '妈', '爷', '姑', '弟', '妹', '亲', '家'],
    pages: [
      { emoji: '👨', text: '这是我爸爸。', p: 'zhè shì wǒ bà ba.' },
      { emoji: '👩', text: '这是我妈妈。', p: 'zhè shì wǒ mā ma.' },
      { emoji: '👴', text: '这是爷爷，那是姑姑。', p: 'zhè shì yé ye, nà shì gū gu.' },
      { emoji: '👶', text: '我有弟弟，也有妹妹。', p: 'wǒ yǒu dì di, yě yǒu mèi mei.' },
      { emoji: '🏡', text: '我们一家人都在家里。', p: 'wǒ men yī jiā rén dōu zài jiā lǐ.' },
      { emoji: '❤️', text: '我爱我家，我家的人都爱我。', p: 'wǒ ài wǒ jiā, wǒ jiā de rén dōu ài wǒ.' }
    ]
  },
  {
    id: 'b9',
    title: '我看到的色',
    pinyin: 'wǒ kàn dào de sè',
    level: 1,
    levelName: '第 1 级 · 一页一个色',
    cover: '🌈',
    palette: ['#ffd6d6', '#c8ebff'],
    summary: '红的苹果、蓝的海、白的云，读一遍就认全了色的字。',
    newChars: ['红', '黄', '蓝', '绿', '白', '黑', '色', '亮'],
    pages: [
      { emoji: '🍎', text: '苹果是红的。', p: 'píng guǒ shì hóng de.' },
      { emoji: '🌞', text: '日是黄的，月也是黄的。', p: 'rì shì huáng de, yuè yě shì huáng de.' },
      { emoji: '🌊', text: '海是蓝的，天也是蓝的。', p: 'hǎi shì lán de, tiān yě shì lán de.' },
      { emoji: '🌿', text: '草是绿的，叶也是绿的。', p: 'cǎo shì lǜ de, yè yě shì lǜ de.' },
      { emoji: '☁️', text: '云是白的，夜是黑的。', p: 'yún shì bái de, yè shì hēi de.' },
      { emoji: '🌈', text: '雨后天上有光，光里的色又多又亮！', p: 'yǔ hòu tiān shàng yǒu guāng, guāng lǐ de sè yòu duō yòu liàng!' }
    ]
  },
  {
    id: 'b2',
    title: '小牛和小羊',
    pinyin: 'xiǎo niú hé xiǎo yáng',
    level: 2,
    levelName: '第 2 级 · 有对话的小故事',
    cover: '🐄',
    palette: ['#d9f6f3', '#ffe0e6'],
    summary: '小牛想上山，小羊说「我也会」。它们在山上看到了什么？',
    newChars: ['牛', '羊', '说', '会', '也', '去', '来'],
    pages: [
      { emoji: '🐄', text: '山上有小牛，山下有小羊。', p: 'shān shàng yǒu xiǎo niú, shān xià yǒu xiǎo yáng.' },
      { emoji: '🗣️', text: '小牛说：我会上山。', p: 'xiǎo niú shuō: wǒ huì shàng shān.' },
      { emoji: '🐑', text: '小羊说：我也会，我也来！', p: 'xiǎo yáng shuō: wǒ yě huì, wǒ yě lái!' },
      { emoji: '🌼', text: '小牛小羊上山去，山上有花，花下有水。', p: 'xiǎo niú xiǎo yáng shàng shān qù, shān shàng yǒu huā, huā xià yǒu shuǐ.' },
      { emoji: '👀', text: '小牛看小羊，小羊看小牛。', p: 'xiǎo niú kàn xiǎo yáng, xiǎo yáng kàn xiǎo niú.' },
      { emoji: '🎉', text: '天上有日。小牛小羊说：好，好！', p: 'tiān shàng yǒu rì. xiǎo niú xiǎo yáng shuō: hǎo, hǎo!' }
    ]
  },
  {
    id: 'b3',
    title: '我的小手和小口',
    pinyin: 'wǒ de xiǎo shǒu hé xiǎo kǒu',
    level: 2,
    levelName: '第 2 级 · 认识自己',
    cover: '✋',
    palette: ['#e8e0ff', '#fff1cf'],
    summary: '手会做什么？口会做什么？我是一个小小的我。',
    newChars: ['手', '口', '目', '耳', '心', '是', '的', '不'],
    pages: [
      { emoji: '✋', text: '我有手，我有口。', p: 'wǒ yǒu shǒu, wǒ yǒu kǒu.' },
      { emoji: '🫰', text: '手是我的，口也是我的。', p: 'shǒu shì wǒ de, kǒu yě shì wǒ de.' },
      { emoji: '👂', text: '我的耳，我的目，我的心。', p: 'wǒ de ěr, wǒ de mù, wǒ de xīn.' },
      { emoji: '👀', text: '我会看，我也会说。', p: 'wǒ huì kàn, wǒ yě huì shuō.' },
      { emoji: '🧒', text: '我不是大人，我是小小的我！', p: 'wǒ bù shì dà rén, wǒ shì xiǎo xiǎo de wǒ!' }
    ]
  },
  {
    id: 'b10',
    title: '小鸟回家',
    pinyin: 'xiǎo niǎo huí jiā',
    level: 2,
    levelName: '第 2 级 · 有人来帮忙',
    cover: '🐦',
    palette: ['#c8ebff', '#e6f5c9'],
    summary: '风来了雨来了，小鸟找不到家。小松鼠说：别急，我帮你。',
    newChars: ['鸟', '飞', '找', '急', '帮', '回', '风', '雨'],
    pages: [
      { emoji: '🐦', text: '小鸟在天上飞，飞了很远。', p: 'xiǎo niǎo zài tiān shàng fēi, fēi le hěn yuǎn.' },
      { emoji: '🌧️', text: '风来了，雨也来了。', p: 'fēng lái le, yǔ yě lái le.' },
      { emoji: '😰', text: '小鸟找不到家，很急。', p: 'xiǎo niǎo zhǎo bù dào jiā, hěn jí.' },
      { emoji: '🐿️', text: '小松鼠说：别急，我帮你找。', p: 'xiǎo sōng shǔ shuō: bié jí, wǒ bāng nǐ zhǎo.' },
      { emoji: '🌳', text: '小松鼠和小鸟走到一个大树下。', p: 'xiǎo sōng shǔ hé xiǎo niǎo zǒu dào yī gè dà shù xià.' },
      { emoji: '🏠', text: '小鸟说：这就是我的家！', p: 'xiǎo niǎo shuō: zhè jiù shì wǒ de jiā!' },
      { emoji: '🎉', text: '雨停了，小鸟和小松鼠都笑了。', p: 'yǔ tíng le, xiǎo niǎo hé xiǎo sōng shǔ dōu xiào le.' }
    ]
  },
  {
    id: 'b11',
    title: '下雨天',
    pinyin: 'xià yǔ tiān',
    level: 2,
    levelName: '第 2 级 · 从家里到外边',
    cover: '☔',
    palette: ['#c8ebff', '#e8e0ff'],
    summary: '云黑了，雷来了。妈妈给我一把伞，我走到外边去。',
    newChars: ['雨', '伞', '云', '雷', '湿', '外', '屋', '换'],
    pages: [
      { emoji: '☁️', text: '天上的云黑了。', p: 'tiān shàng de yún hēi le.' },
      { emoji: '⚡', text: '雷来了，雨也来了。', p: 'léi lái le, yǔ yě lái le.' },
      { emoji: '☔', text: '妈妈给我一把伞。', p: 'mā ma gěi wǒ yī bǎ sǎn.' },
      { emoji: '🚶', text: '我拿伞走到外边。', p: 'wǒ ná sǎn zǒu dào wài biān.' },
      { emoji: '💧', text: '雨打在伞上，我的鞋湿了。', p: 'yǔ dǎ zài sǎn shàng, wǒ de xié shī le.' },
      { emoji: '🏠', text: '回到屋里，妈妈让我换鞋。', p: 'huí dào wū lǐ, mā ma ràng wǒ huàn xié.' },
      { emoji: '🌈', text: '雨停了，天上又有光了。', p: 'yǔ tíng le, tiān shàng yòu yǒu guāng le.' }
    ]
  },
  {
    id: 'b12',
    title: '我能做好多',
    pinyin: 'wǒ néng zuò hǎo duō',
    level: 2,
    levelName: '第 2 级 · 我会做的小事',
    cover: '🧒',
    palette: ['#e6f5c9', '#fff1cf'],
    summary: '洗脸、扫地、摆碗、挂衣，一天下来，我能做的真不少。',
    newChars: ['洗', '扫', '收', '摆', '挂', '干', '净', '忙'],
    pages: [
      { emoji: '🧼', text: '早上，我会洗脸。', p: 'zǎo shang, wǒ huì xǐ liǎn.' },
      { emoji: '🖐️', text: '我会洗手，我的手很干净。', p: 'wǒ huì xǐ shǒu, wǒ de shǒu hěn gān jìng.' },
      { emoji: '🧹', text: '我会扫地，地上很干净。', p: 'wǒ huì sǎo dì, dì shàng hěn gān jìng.' },
      { emoji: '🍽️', text: '我会摆碗，也会收碗。', p: 'wǒ huì bǎi wǎn, yě huì shōu wǎn.' },
      { emoji: '👕', text: '我会拿衣，也会挂衣。', p: 'wǒ huì ná yī, yě huì guà yī.' },
      { emoji: '👏', text: '妈妈说：你真能帮忙！', p: 'mā ma shuō: nǐ zhēn néng bāng máng!' },
      { emoji: '😄', text: '我说：我会做的还有好多！', p: 'wǒ shuō: wǒ huì zuò de hái yǒu hǎo duō!' }
    ]
  },
  {
    id: 'b4',
    title: '我家的一天',
    pinyin: 'wǒ jiā de yī tiān',
    level: 3,
    levelName: '第 3 级 · 一家人的日子',
    cover: '🏡',
    palette: ['#ffe0c2', '#e6f5c9'],
    summary: '从早饭到晚上开灯，跟着我看看家里的一天。',
    newChars: ['坐', '桌', '吃', '饭', '哥', '姐', '杯', '茶', '房', '灯'],
    pages: [
      { emoji: '🍚', text: '早上，我坐在桌前吃饭。', p: 'zǎo shang, wǒ zuò zài zhuō qián chī fàn.' },
      { emoji: '👨‍👩‍👧', text: '父母也来了，我们一家人都在。', p: 'fù mǔ yě lái le, wǒ men yī jiā rén dōu zài.' },
      { emoji: '🥬', text: '桌上有米饭、菜和一个蛋。', p: 'zhuō shàng yǒu mǐ fàn, cài hé yī gè dàn.' },
      { emoji: '🍎', text: '哥哥要一杯茶，姐姐想吃苹果。', p: 'gē ge yào yī bēi chá, jiě jie xiǎng chī píng guǒ.' },
      { emoji: '📖', text: '吃了饭，我们去房里读书。', p: 'chī le fàn, wǒ men qù fáng lǐ dú shū.' },
      { emoji: '💡', text: '晚上，灯是黄的，我们都笑了。', p: 'wǎn shang, dēng shì huáng de, wǒ men dōu xiào le.' }
    ]
  },
  {
    id: 'b5',
    title: '小鸡问什么',
    pinyin: 'xiǎo jī wèn shén me',
    level: 3,
    levelName: '第 3 级 · 爱问的小动物',
    cover: '🐔',
    palette: ['#fff1cf', '#d9f6f3'],
    summary: '小鸡什么都想问。问一问，就多知道一点。',
    newChars: ['鸡', '鸭', '猪', '问', '这', '那', '什', '么', '都', '能'],
    pages: [
      { emoji: '🐔', text: '小鸡问：这是什么？', p: 'xiǎo jī wèn: zhè shì shén me?' },
      { emoji: '🐄', text: '老牛说：这是一个大瓜。', p: 'lǎo niú shuō: zhè shì yī gè dà guā.' },
      { emoji: '🦆', text: '小鸭问：那是什么？', p: 'xiǎo yā wèn: nà shì shén me?' },
      { emoji: '🥚', text: '小猪说：那是一个白色的蛋。', p: 'xiǎo zhū shuō: nà shì yī gè bái sè de dàn.' },
      { emoji: '😄', text: '小鸡和小鸭都笑了：我们什么都想问！', p: 'xiǎo jī hé xiǎo yā dōu xiào le: wǒ men shén me dōu xiǎng wèn!' },
      { emoji: '🌟', text: '老牛说：多问一问，我们都能学好。', p: 'lǎo niú shuō: duō wèn yī wèn, wǒ men dōu néng xué hǎo.' }
    ]
  },
  {
    id: 'b13',
    title: '上学的头一天',
    pinyin: 'shàng xué de tóu yī tiān',
    level: 3,
    levelName: '第 3 级 · 学校里的一天',
    cover: '🎒',
    palette: ['#ffe0c2', '#c8ebff'],
    summary: '妈妈送我到学校门口，教室里都是不认识的同学。放学时我说：学校真好。',
    newChars: ['学', '校', '师', '班', '同', '室', '认', '识'],
    pages: [
      { emoji: '🎒', text: '今天，我头一天上学。', p: 'jīn tiān, wǒ tóu yī tiān shàng xué.' },
      { emoji: '🏫', text: '妈妈送我到学校门口。', p: 'mā ma sòng wǒ dào xué xiào mén kǒu.' },
      { emoji: '👩‍🏫', text: '老师在教室门前迎我。', p: 'lǎo shī zài jiào shì mén qián yíng wǒ.' },
      { emoji: '🧒', text: '教室里有好多同学，我都不认识。', p: 'jiào shì lǐ yǒu hǎo duō tóng xué, wǒ dōu bù rèn shi.' },
      { emoji: '🙋', text: '一个女同学问我的名字。我说：我的名字是小明。', p: 'yī gè nǚ tóng xué wèn wǒ de míng zi. wǒ shuō: wǒ de míng zi shì xiǎo míng.' },
      { emoji: '📖', text: '老师教我们读书，也教我们写字。', p: 'lǎo shī jiào wǒ men dú shū, yě jiào wǒ men xiě zì.' },
      { emoji: '😄', text: '放学了，我对妈妈说：学校真好！', p: 'fàng xué le, wǒ duì mā ma shuō: xué xiào zhēn hǎo!' }
    ]
  },
  {
    id: 'b14',
    title: '春夏秋冬',
    pinyin: 'chūn xià qiū dōng',
    level: 3,
    levelName: '第 3 级 · 一年走一回',
    cover: '🍁',
    palette: ['#e6f5c9', '#ffd6d6'],
    summary: '花开、水凉、叶黄、下雪，一年四时，一页一时。',
    newChars: ['春', '夏', '秋', '冬', '雪', '热', '冷', '熟'],
    pages: [
      { emoji: '🌸', text: '春天到了，花开了，草绿了。', p: 'chūn tiān dào le, huā kāi le, cǎo lǜ le.' },
      { emoji: '🐝', text: '小蜂在花上飞，小蝶也来了。', p: 'xiǎo fēng zài huā shàng fēi, xiǎo dié yě lái le.' },
      { emoji: '☀️', text: '夏天很热，我们去河里玩水。', p: 'xià tiān hěn rè, wǒ men qù hé lǐ wán shuǐ.' },
      { emoji: '🍉', text: '夏天的瓜又大又甜。', p: 'xià tiān de guā yòu dà yòu tián.' },
      { emoji: '🍂', text: '秋天来了，树叶黄了。', p: 'qiū tiān lái le, shù yè huáng le.' },
      { emoji: '🍐', text: '秋天的梨和枣都熟了。', p: 'qiū tiān de lí hé zǎo dōu shú le.' },
      { emoji: '❄️', text: '冬天很冷，天上下雪，地上白了。', p: 'dōng tiān hěn lěng, tiān shàng xià xuě, dì shàng bái le.' },
      { emoji: '🧣', text: '春夏秋冬，我都爱。', p: 'chūn xià qiū dōng, wǒ dōu ài.' }
    ]
  },
  {
    id: 'b15',
    title: '小猫学画画',
    pinyin: 'xiǎo māo xué huà huà',
    level: 3,
    levelName: '第 3 级 · 多试几回就会了',
    cover: '🐱',
    palette: ['#ffe0e6', '#e8e0ff'],
    summary: '头一张画得不好，小猫哭了。妈妈说：刚学都不会，多试几张就会了。',
    newChars: ['画', '笔', '纸', '试', '再', '刚', '张', '支'],
    pages: [
      { emoji: '🐱', text: '小猫想学画画。', p: 'xiǎo māo xiǎng xué huà huà.' },
      { emoji: '🖌️', text: '妈妈给他一支笔，一张纸。', p: 'mā ma gěi tā yī zhī bǐ, yī zhāng zhǐ.' },
      { emoji: '🐟', text: '小猫画了一条鱼，鱼的头太大了。', p: 'xiǎo māo huà le yī tiáo yú, yú de tóu tài dà le.' },
      { emoji: '😿', text: '小猫哭了：我不会画。', p: 'xiǎo māo kū le: wǒ bù huì huà.' },
      { emoji: '🐈', text: '妈妈说：别急，再画一张。', p: 'mā ma shuō: bié jí, zài huà yī zhāng.' },
      { emoji: '🎨', text: '小猫又画了一张，这条鱼真好看。', p: 'xiǎo māo yòu huà le yī zhāng, zhè tiáo yú zhēn hǎo kàn.' },
      { emoji: '🖼️', text: '小猫把画挂在屋里。', p: 'xiǎo māo bǎ huà guà zài wū lǐ.' },
      { emoji: '😸', text: '妈妈说：刚学都不会，多试几张就会了。', p: 'mā ma shuō: gāng xué dōu bù huì, duō shì jǐ zhāng jiù huì le.' }
    ]
  },
  {
    id: 'b16',
    title: '小猴种的桃树',
    pinyin: 'xiǎo hóu zhòng de táo shù',
    level: 4,
    levelName: '第 4 级 · 等一等才有的果',
    cover: '🐒',
    palette: ['#ffd6d6', '#e6f5c9'],
    summary: '小猴把桃子里的核放进土里，一年又一年地拿水来。等到秋天，树上真的有桃了。',
    newChars: ['猴', '桃', '种', '苗', '满', '收', '送', '等'],
    pages: [
      { emoji: '🐒', text: '小猴在山上找到一个桃。', p: 'xiǎo hóu zài shān shàng zhǎo dào yī gè táo.' },
      { emoji: '🌰', text: '桃很甜。小猴把桃里的子放到土里。', p: 'táo hěn tián. xiǎo hóu bǎ táo lǐ de zǐ fàng dào tǔ lǐ.' },
      { emoji: '💧', text: '每天早上，小猴用碗拿水来。', p: 'měi tiān zǎo shang, xiǎo hóu yòng wǎn ná shuǐ lái.' },
      { emoji: '🌱', text: '过了几天，土里长了一个小苗。', p: 'guò le jǐ tiān, tǔ lǐ zhǎng le yī gè xiǎo miáo.' },
      { emoji: '🌳', text: '过了一年，又过了一年，小苗长高了，长大了。', p: 'guò le yī nián, yòu guò le yī nián, xiǎo miáo zhǎng gāo le, zhǎng dà le.' },
      { emoji: '🌸', text: '春天，树上开满了花。', p: 'chūn tiān, shù shàng kāi mǎn le huā.' },
      { emoji: '🍑', text: '秋天，树上有好多桃。', p: 'qiū tiān, shù shàng yǒu hǎo duō táo.' },
      { emoji: '🐵', text: '小猴收了桃，送给山下的朋友。', p: 'xiǎo hóu shōu le táo, sòng gěi shān xià de péng you.' },
      { emoji: '😄', text: '朋友问：这是什么？小猴说：这是我种的桃。', p: 'péng you wèn: zhè shì shén me? xiǎo hóu shuō: zhè shì wǒ zhòng de táo.' }
    ]
  },
  {
    id: 'b17',
    title: '这不是我的伞',
    pinyin: 'zhè bù shì wǒ de sǎn',
    level: 4,
    levelName: '第 4 级 · 拿了别人的东西',
    cover: '🌂',
    palette: ['#e8e0ff', '#c8ebff'],
    summary: '小明的伞不见了，他拿走门口的黄伞。小红说：这是我的。小明的脸红了。',
    newChars: ['伞', '借', '还', '别', '对', '路', '脸', '把'],
    pages: [
      { emoji: '🌂', text: '雨天，小明找不到他的伞。', p: 'yǔ tiān, xiǎo míng zhǎo bù dào tā de sǎn.' },
      { emoji: '🔍', text: '他在教室里找，在桌下找，都没有。', p: 'tā zài jiào shì lǐ zhǎo, zài zhuō xià zhǎo, dōu méi yǒu.' },
      { emoji: '💛', text: '门口有一把黄伞。小明拿了黄伞就走。', p: 'mén kǒu yǒu yī bǎ huáng sǎn. xiǎo míng ná le huáng sǎn jiù zǒu.' },
      { emoji: '😮', text: '走到路上，小红说：这是我的伞，不是你的。', p: 'zǒu dào lù shàng, xiǎo hóng shuō: zhè shì wǒ de sǎn, bù shì nǐ de.' },
      { emoji: '😳', text: '小明的脸红了。他把伞还给小红。', p: 'xiǎo míng de liǎn hóng le. tā bǎ sǎn huán gěi xiǎo hóng.' },
      { emoji: '☂️', text: '小红说：别急，我的伞大，我们同用一把。', p: 'xiǎo hóng shuō: bié jí, wǒ de sǎn dà, wǒ men tóng yòng yī bǎ.' },
      { emoji: '🚶', text: '他们同走一条路，回到家。', p: 'tā men tóng zǒu yī tiáo lù, huí dào jiā.' },
      { emoji: '🛏️', text: '过了一天，小明在他的床下找到了他的伞。', p: 'guò le yī tiān, xiǎo míng zài tā de chuáng xià zhǎo dào le tā de sǎn.' },
      { emoji: '😄', text: '小明把伞借给小红，说：今天用我的！', p: 'xiǎo míng bǎ sǎn jiè gěi xiǎo hóng, shuō: jīn tiān yòng wǒ de!' }
    ]
  },
  {
    id: 'b18',
    title: '河上的小船',
    pinyin: 'hé shàng de xiǎo chuán',
    level: 4,
    levelName: '第 4 级 · 从早走到晚',
    cover: '⛵',
    palette: ['#c8ebff', '#d9f6f3'],
    summary: '爷爷的小船在河上走了一天，看过鱼、看过鸟，也看过一个小岛。',
    newChars: ['船', '岸', '流', '波', '岛', '停', '过', '向'],
    pages: [
      { emoji: '⛵', text: '河上有一只小船。', p: 'hé shàng yǒu yī zhī xiǎo chuán.' },
      { emoji: '👴', text: '爷爷在船上，我也在船上。', p: 'yé ye zài chuán shàng, wǒ yě zài chuán shàng.' },
      { emoji: '🌊', text: '水在流，船向前走。', p: 'shuǐ zài liú, chuán xiàng qián zǒu.' },
      { emoji: '🐟', text: '水里有鱼，鱼从船下过。', p: 'shuǐ lǐ yǒu yú, yú cóng chuán xià guò.' },
      { emoji: '🐦', text: '天上有鸟，鸟在船上边飞。', p: 'tiān shàng yǒu niǎo, niǎo zài chuán shàng bian fēi.' },
      { emoji: '🏝️', text: '前边有一个小岛，岛上有树，树上有花。', p: 'qián bian yǒu yī gè xiǎo dǎo, dǎo shàng yǒu shù, shù shàng yǒu huā.' },
      { emoji: '🌅', text: '天晚了，日从山后下去。', p: 'tiān wǎn le, rì cóng shān hòu xià qù.' },
      { emoji: '⚓', text: '爷爷把船停在岸边。', p: 'yé ye bǎ chuán tíng zài àn biān.' },
      { emoji: '🏠', text: '我们回家了。我说：明天还来！', p: 'wǒ men huí jiā le. wǒ shuō: míng tiān hái lái!' }
    ]
  },
  {
    id: 'b19',
    title: '小蚁的一片饼',
    pinyin: 'xiǎo yǐ de yī piàn bǐng',
    level: 4,
    levelName: '第 4 级 · 一只不行，大家来',
    cover: '🐜',
    palette: ['#ffe0c2', '#fff1cf'],
    summary: '一片饼太重，一只小蚁拉不走。他回家找来伙伴，众蚁共用力，饼就走了。',
    newChars: ['蚁', '饼', '拉', '推', '众', '力', '重', '共'],
    pages: [
      { emoji: '🐜', text: '一只小蚁在路上找到一片饼。', p: 'yī zhī xiǎo yǐ zài lù shàng zhǎo dào yī piàn bǐng.' },
      { emoji: '😮', text: '饼很大，也很重。', p: 'bǐng hěn dà, yě hěn zhòng.' },
      { emoji: '💪', text: '小蚁用力拉，饼不走。', p: 'xiǎo yǐ yòng lì lā, bǐng bù zǒu.' },
      { emoji: '😓', text: '小蚁用力推，饼还是不走。', p: 'xiǎo yǐ yòng lì tuī, bǐng hái shì bù zǒu.' },
      { emoji: '🏠', text: '小蚁回家，找来他的伙伴。', p: 'xiǎo yǐ huí jiā, zhǎo lái tā de huǒ bàn.' },
      { emoji: '🐜', text: '一只，二只，三只……好多小蚁都来了。', p: 'yī zhī, èr zhī, sān zhī…… hǎo duō xiǎo yǐ dōu lái le.' },
      { emoji: '🙌', text: '众蚁共用力，饼就走了！', p: 'zhòng yǐ gòng yòng lì, bǐng jiù zǒu le!' },
      { emoji: '📦', text: '他们把饼拉回家。', p: 'tā men bǎ bǐng lā huí jiā.' },
      { emoji: '😄', text: '小蚁说：一只力小，众蚁力大！', p: 'xiǎo yǐ shuō: yī zhī lì xiǎo, zhòng yǐ lì dà!' }
    ]
  },
  {
    id: 'b20',
    title: '小狗病了',
    pinyin: 'xiǎo gǒu bìng le',
    level: 4,
    levelName: '第 4 级 · 去一回医院',
    cover: '🐕',
    palette: ['#ffd6d6', '#d9f6f3'],
    summary: '小狗吃了太多糖，肚子很痛。我们开车去医院，医生说：休三天，别吃糖。',
    newChars: ['病', '医', '院', '痛', '怕', '休', '抱', '糖'],
    pages: [
      { emoji: '🐕', text: '小狗不吃饭，也不玩球。', p: 'xiǎo gǒu bù chī fàn, yě bù wán qiú.' },
      { emoji: '😟', text: '他的肚子很痛。', p: 'tā de dù zi hěn tòng.' },
      { emoji: '🏥', text: '妈妈说：我们去医院。', p: 'mā ma shuō: wǒ men qù yī yuàn.' },
      { emoji: '🚗', text: '爸爸开车，我抱小狗坐在后边。', p: 'bà ba kāi chē, wǒ bào xiǎo gǒu zuò zài hòu bian.' },
      { emoji: '👨‍⚕️', text: '医生问：他吃了什么？', p: 'yī shēng wèn: tā chī le shén me?' },
      { emoji: '🍬', text: '我说：他吃了太多糖。', p: 'wǒ shuō: tā chī le tài duō táng.' },
      { emoji: '😰', text: '小狗很怕，我拉他的爪。', p: 'xiǎo gǒu hěn pà, wǒ lā tā de zhuǎ.' },
      { emoji: '🛏️', text: '医生说：休三天，别吃糖。', p: 'yī shēng shuō: xiū sān tiān, bié chī táng.' },
      { emoji: '🐶', text: '三天后，小狗好了。他又打球，又跑又跳。', p: 'sān tiān hòu, xiǎo gǒu hǎo le. tā yòu dǎ qiú, yòu pǎo yòu tiào.' },
      { emoji: '😄', text: '我对小狗说：以后别吃太多糖！', p: 'wǒ duì xiǎo gǒu shuō: yǐ hòu bié chī tài duō táng!' }
    ]
  },
  {
    id: 'b21',
    title: '森林里的歌会',
    pinyin: 'sēn lín lǐ de gē huì',
    level: 5,
    levelName: '第 5 级 · 好多角色的故事',
    cover: '🎶',
    palette: ['#e6f5c9', '#c8ebff'],
    summary: '小鸟唱得高，小蛙唱得重，小鹿不会唱歌但会跳舞。森林里的歌会，人人都有一样能做的。',
    newChars: ['森', '林', '声', '音', '歌', '曲', '舞', '熊'],
    pages: [
      { emoji: '🌲', text: '森林里有好多树，树上有好多鸟。', p: 'sēn lín lǐ yǒu hǎo duō shù, shù shàng yǒu hǎo duō niǎo.' },
      { emoji: '🎶', text: '今天，森林里有一个歌会。', p: 'jīn tiān, sēn lín lǐ yǒu yī gè gē huì.' },
      { emoji: '🐦', text: '小鸟头一个唱。他的声音又高又亮。', p: 'xiǎo niǎo tóu yī gè chàng. tā de shēng yīn yòu gāo yòu liàng.' },
      { emoji: '🐸', text: '小蛙也来唱。他的声音很重，很有力。', p: 'xiǎo wā yě lái chàng. tā de shēng yīn hěn zhòng, hěn yǒu lì.' },
      { emoji: '🦆', text: '小鸭唱了一曲，大家都笑了。', p: 'xiǎo yā chàng le yī qǔ, dà jiā dōu xiào le.' },
      { emoji: '🦌', text: '小鹿不会唱歌，但他会跳舞。', p: 'xiǎo lù bù huì chàng gē, dàn tā huì tiào wǔ.' },
      { emoji: '🐝', text: '小蜂在花上飞，他的声音也很好听。', p: 'xiǎo fēng zài huā shàng fēi, tā de shēng yīn yě hěn hǎo tīng.' },
      { emoji: '🌙', text: '月光下，森林里都是歌和舞。', p: 'yuè guāng xià, sēn lín lǐ dōu shì gē hé wǔ.' },
      { emoji: '🐻', text: '老熊说：我们每年都要开一个歌会！', p: 'lǎo xióng shuō: wǒ men měi nián dōu yào kāi yī gè gē huì!' }
    ]
  },
  {
    id: 'b22',
    title: '小鹿的生日',
    pinyin: 'xiǎo lù de shēng rì',
    level: 5,
    levelName: '第 5 级 · 朋友送来的心意',
    cover: '🦌',
    palette: ['#ffe0e6', '#fff1cf'],
    summary: '小猴送桃，小蜂送蜜，小松鼠送果。糕上摆六个红果，一个果就是一岁。',
    newChars: ['客', '糕', '蜜', '甜', '岁', '香', '同'],
    pages: [
      { emoji: '🦌', text: '今天是小鹿的生日。', p: 'jīn tiān shì xiǎo lù de shēng rì.' },
      { emoji: '🏠', text: '小鹿的家里来了好多客人。', p: 'xiǎo lù de jiā lǐ lái le hǎo duō kè rén.' },
      { emoji: '🐒', text: '小猴送来一个大桃。', p: 'xiǎo hóu sòng lái yī gè dà táo.' },
      { emoji: '🐝', text: '小蜂送来一碗蜜，又香又甜。', p: 'xiǎo fēng sòng lái yī wǎn mì, yòu xiāng yòu tián.' },
      { emoji: '🐿️', text: '小松鼠送来几个果。', p: 'xiǎo sōng shǔ sòng lái jǐ gè guǒ.' },
      { emoji: '🎂', text: '妈妈做了一个大糕。', p: 'mā ma zuò le yī gè dà gāo.' },
      { emoji: '🍒', text: '糕上摆了六个红果，一个果就是一岁。', p: 'gāo shàng bǎi le liù gè hóng guǒ, yī gè guǒ jiù shì yī suì.' },
      { emoji: '🎶', text: '大家一同唱歌，一同跳舞。', p: 'dà jiā yī tóng chàng gē, yī tóng tiào wǔ.' },
      { emoji: '😄', text: '小鹿说：有朋友的生日最好！', p: 'xiǎo lù shuō: yǒu péng you de shēng rì zuì hǎo!' }
    ]
  },
  {
    id: 'b23',
    title: '城里和乡下',
    pinyin: 'chéng lǐ hé xiāng xià',
    level: 5,
    levelName: '第 5 级 · 走远一点看看',
    cover: '🏙️',
    palette: ['#e8e0ff', '#e6f5c9'],
    summary: '小明的家在城里，爷爷的家在乡下。车走得越远，楼房越少，田越多。',
    newChars: ['城', '乡', '村', '街', '市', '楼', '农', '静'],
    pages: [
      { emoji: '🏙️', text: '小明的家在城里。', p: 'xiǎo míng de jiā zài chéng lǐ.' },
      { emoji: '🏡', text: '爷爷的家在乡下的一个小村。', p: 'yé ye de jiā zài xiāng xià de yī gè xiǎo cūn.' },
      { emoji: '🚗', text: '今天，爸爸开车送小明去乡下。', p: 'jīn tiān, bà ba kāi chē sòng xiǎo míng qù xiāng xià.' },
      { emoji: '🛣️', text: '车走了很远。路边的楼房少了，田多了。', p: 'chē zǒu le hěn yuǎn. lù biān de lóu fáng shǎo le, tián duō le.' },
      { emoji: '🐄', text: '田里有牛，田边有水。农人在田里忙。', p: 'tián lǐ yǒu niú, tián biān yǒu shuǐ. nóng rén zài tián lǐ máng.' },
      { emoji: '👴', text: '爷爷在门口迎他们。', p: 'yé ye zài mén kǒu yíng tā men.' },
      { emoji: '🍎', text: '爷爷的园里有果树，树上的苹果红了。', p: 'yé ye de yuán lǐ yǒu guǒ shù, shù shàng de píng guǒ hóng le.' },
      { emoji: '🌙', text: '夜里很静，天上的星又多又亮。', p: 'yè lǐ hěn jìng, tiān shàng de xīng yòu duō yòu liàng.' },
      { emoji: '😄', text: '小明说：城里有街有市，乡下有田有星，都好！', p: 'xiǎo míng shuō: chéng lǐ yǒu jiē yǒu shì, xiāng xià yǒu tián yǒu xīng, dōu hǎo!' }
    ]
  },
  {
    id: 'b24',
    title: '到海上去',
    pinyin: 'dào hǎi shàng qù',
    level: 5,
    levelName: '第 5 级 · 海里有什么',
    cover: '🌊',
    palette: ['#c8ebff', '#ffe6b3'],
    summary: '夏天，一只借来的小船带我们到海上：白色的虾、旁边走的蟹、很慢的龟，还有一个小岛。',
    newChars: ['洋', '浪', '虾', '蟹', '龟', '旁', '慢', '转'],
    pages: [
      { emoji: '🌊', text: '夏天，我们到海边玩。', p: 'xià tiān, wǒ men dào hǎi biān wán.' },
      { emoji: '⛵', text: '爸爸借了一只船，我们到海上去。', p: 'bà ba jiè le yī zhī chuán, wǒ men dào hǎi shàng qù.' },
      { emoji: '💙', text: '海很大，水是蓝的，波和浪都很高。', p: 'hǎi hěn dà, shuǐ shì lán de, bō hé làng dōu hěn gāo.' },
      { emoji: '🦐', text: '水里有虾，虾的身体是白的。', p: 'shuǐ lǐ yǒu xiā, xiā de shēn tǐ shì bái de.' },
      { emoji: '🦀', text: '石头下有蟹，蟹走路向旁边走。', p: 'shí tou xià yǒu xiè, xiè zǒu lù xiàng páng biān zǒu.' },
      { emoji: '🐢', text: '海里还有龟，龟很慢，但他从不停。', p: 'hǎi lǐ hái yǒu guī, guī hěn màn, dàn tā cóng bù tíng.' },
      { emoji: '🏝️', text: '前边有一个小岛，岛上有几只鸟。', p: 'qián bian yǒu yī gè xiǎo dǎo, dǎo shàng yǒu jǐ zhī niǎo.' },
      { emoji: '🐟', text: '我们在岛边看鱼，鱼在水里转来转去。', p: 'wǒ men zài dǎo biān kàn yú, yú zài shuǐ lǐ zhuàn lái zhuàn qù.' },
      { emoji: '🌅', text: '天晚了，我们的船回岸。', p: 'tiān wǎn le, wǒ men de chuán huí àn.' },
      { emoji: '😄', text: '我说：海洋真大，我还要来！', p: 'wǒ shuō: hǎi yáng zhēn dà, wǒ hái yào lái!' }
    ]
  },
  {
    id: 'b25',
    title: '小鼠学算题',
    pinyin: 'xiǎo shǔ xué suàn tí',
    level: 5,
    levelName: '第 5 级 · 一天练一点',
    cover: '🐭',
    palette: ['#fff1cf', '#e8e0ff'],
    summary: '小鼠一开头连数都不会数。老师用果子教他加和减，一年后，他算题最快。',
    newChars: ['算', '题', '加', '减', '练', '习', '快', '位'],
    pages: [
      { emoji: '🐭', text: '小鼠不会数数。', p: 'xiǎo shǔ bù huì shǔ shù.' },
      { emoji: '🏫', text: '老师教他：一，二，三，四，五。', p: 'lǎo shī jiào tā: yī, èr, sān, sì, wǔ.' },
      { emoji: '🌰', text: '老师给他三个果，问：这是几个？', p: 'lǎo shī gěi tā sān gè guǒ, wèn: zhè shì jǐ gè?' },
      { emoji: '🐁', text: '小鼠数了数，说：三个！', p: 'xiǎo shǔ shǔ le shǔ, shuō: sān gè!' },
      { emoji: '➕', text: '老师又给他二个果，说：三加二是五。', p: 'lǎo shī yòu gěi tā èr gè guǒ, shuō: sān jiā èr shì wǔ.' },
      { emoji: '➖', text: '小鼠吃了一个。老师说：五减一是四。', p: 'xiǎo shǔ chī le yī gè. lǎo shī shuō: wǔ jiǎn yī shì sì.' },
      { emoji: '🎉', text: '小鼠笑了：我会算题了！', p: 'xiǎo shǔ xiào le: wǒ huì suàn tí le!' },
      { emoji: '📖', text: '从那天以后，小鼠每天都练习算题。', p: 'cóng nà tiān yǐ hòu, xiǎo shǔ měi tiān dōu liàn xí suàn tí.' },
      { emoji: '🏅', text: '过了一年，班上算题最快的就是小鼠。', p: 'guò le yī nián, bān shàng suàn tí zuì kuài de jiù shì xiǎo shǔ.' }
    ]
  },
  {
    id: 'b26',
    title: '月和小星',
    pinyin: 'yuè hé xiǎo xīng',
    level: 6,
    levelName: '第 6 级 · 一段长长的对话',
    cover: '🌙',
    palette: ['#e8e0ff', '#c8ebff'],
    summary: '小星问月：你为什么这么亮？月说：我的光是日给我的。那小星的光呢？窗前的小娃有答案。',
    newChars: ['星', '光', '夜', '暖', '窗', '娃', '眼', '空'],
    pages: [
      { emoji: '🌙', text: '夜里，天上有一个月。', p: 'yè lǐ, tiān shàng yǒu yī gè yuè.' },
      { emoji: '⭐', text: '月的旁边有好多小星。', p: 'yuè de páng biān yǒu hǎo duō xiǎo xīng.' },
      { emoji: '🌟', text: '一个小星问月：你为什么这么亮？', p: 'yī gè xiǎo xīng wèn yuè: nǐ wèi shén me zhè me liàng?' },
      { emoji: '🌕', text: '月说：我不亮。我的光是日给我的。', p: 'yuè shuō: wǒ bù liàng. wǒ de guāng shì rì gěi wǒ de.' },
      { emoji: '✨', text: '小星说：我的光也不大，我太远了。', p: 'xiǎo xīng shuō: wǒ de guāng yě bù dà, wǒ tài yuǎn le.' },
      { emoji: '🌌', text: '月说：远也好。你在空上，山下的人都能看到你。', p: 'yuè shuō: yuǎn yě hǎo. nǐ zài kōng shàng, shān xià de rén dōu néng kàn dào nǐ.' },
      { emoji: '🧒', text: '这时，一个小娃在窗前看天。', p: 'zhè shí, yī gè xiǎo wá zài chuāng qián kàn tiān.' },
      { emoji: '👀', text: '他对妈妈说：我看到了一个星，最亮的那个！', p: 'tā duì mā ma shuō: wǒ kàn dào le yī gè xīng, zuì liàng de nà gè!' },
      { emoji: '💗', text: '小星听了，心里很暖。', p: 'xiǎo xīng tīng le, xīn lǐ hěn nuǎn.' },
      { emoji: '🌠', text: '月说：你看，你的光已到了他的眼里。', p: 'yuè shuō: nǐ kàn, nǐ de guāng yǐ dào le tā de yǎn lǐ.' }
    ]
  },
  {
    id: 'b27',
    title: '我们班的图书角',
    pinyin: 'wǒ men bān de tú shū jiǎo',
    level: 6,
    levelName: '第 6 级 · 大家的东西大家管',
    cover: '📚',
    palette: ['#ffe0c2', '#d9f6f3'],
    summary: '班上有一百本书，借书要写名字。有一本书没有还回来，老师说：还回来就好。',
    newChars: ['图', '角', '借', '记', '忘', '排', '讲', '百'],
    pages: [
      { emoji: '📚', text: '我们班有一个图书角。', p: 'wǒ men bān yǒu yī gè tú shū jiǎo.' },
      { emoji: '🧑‍🏫', text: '老师说：这些书是大家的。', p: 'lǎo shī shuō: zhè xiē shū shì dà jiā de.' },
      { emoji: '📖', text: '图书角里共有一百本书。', p: 'tú shū jiǎo lǐ gòng yǒu yī bǎi běn shū.' },
      { emoji: '✍️', text: '借书的人要写下名字和日子。', p: 'jiè shū de rén yào xiě xià míng zi hé rì zi.' },
      { emoji: '🧒', text: '小明借了一本画书，三天后还回来。', p: 'xiǎo míng jiè le yī běn huà shū, sān tiān hòu huán huí lái.' },
      { emoji: '👧', text: '小红借了一本讲花草的书。', p: 'xiǎo hóng jiè le yī běn jiǎng huā cǎo de shū.' },
      { emoji: '😟', text: '有一天，一本书没有还回来。', p: 'yǒu yī tiān, yī běn shū méi yǒu huán huí lái.' },
      { emoji: '🔍', text: '老师说：别急，我们找一找。', p: 'lǎo shī shuō: bié jí, wǒ men zhǎo yī zhǎo.' },
      { emoji: '🎒', text: '一个同学打开书包，那本书就在里边。他的脸红了。', p: 'yī gè tóng xué dǎ kāi shū bāo, nà běn shū jiù zài lǐ bian. tā de liǎn hóng le.' },
      { emoji: '😄', text: '老师说：还回来就好。以后别忘了记名字。', p: 'lǎo shī shuō: huán huí lái jiù hǎo. yǐ hòu bié wàng le jì míng zi.' },
      { emoji: '📚', text: '从那天以后，我们都把书排好，也都记名字。', p: 'cóng nà tiān yǐ hòu, wǒ men dōu bǎ shū pái hǎo, yě dōu jì míng zi.' }
    ]
  },
  {
    id: 'b28',
    title: '一元和一块糕',
    pinyin: 'yī yuán hé yī kuài gāo',
    level: 6,
    levelName: '第 6 级 · 手里只有一元',
    cover: '💰',
    palette: ['#fff1cf', '#ffd6d6'],
    summary: '爷爷给我一元。糕要一元，糖也要一元，我只能要一样。门口的小朋友也想吃糕。',
    newChars: ['元', '块', '店', '半', '分', '只', '给', '想'],
    pages: [
      { emoji: '💰', text: '爷爷给我一元。', p: 'yé ye gěi wǒ yī yuán.' },
      { emoji: '🏪', text: '我拿一元去街上的小店。', p: 'wǒ ná yī yuán qù jiē shàng de xiǎo diàn.' },
      { emoji: '🍰', text: '店里有糕，一块糕是一元。', p: 'diàn lǐ yǒu gāo, yī kuài gāo shì yī yuán.' },
      { emoji: '🍬', text: '我也想要一块糖，糖也是一元。', p: 'wǒ yě xiǎng yào yī kuài táng, táng yě shì yī yuán.' },
      { emoji: '😕', text: '我只有一元，不能都要。', p: 'wǒ zhǐ yǒu yī yuán, bù néng dōu yào.' },
      { emoji: '🧒', text: '门口有一个小朋友，他也想吃糕。', p: 'mén kǒu yǒu yī gè xiǎo péng you, tā yě xiǎng chī gāo.' },
      { emoji: '🤝', text: '我用一元换了一块糕，把糕分开，给他一半。', p: 'wǒ yòng yī yuán huàn le yī kuài gāo, bǎ gāo fēn kāi, gěi tā yī bàn.' },
      { emoji: '😄', text: '小朋友笑了，我也笑了。', p: 'xiǎo péng you xiào le, wǒ yě xiào le.' },
      { emoji: '🚶', text: '回家的路上，我对爷爷说了这些。', p: 'huí jiā de lù shàng, wǒ duì yé ye shuō le zhè xiē.' },
      { emoji: '❤️', text: '爷爷说：一元不多，但你会分给朋友，这最好。', p: 'yé ye shuō: yī yuán bù duō, dàn nǐ huì fēn gěi péng you, zhè zuì hǎo.' }
    ]
  },
  {
    id: 'b29',
    title: '小蜂的花园',
    pinyin: 'xiǎo fēng de huā yuán',
    level: 6,
    levelName: '第 6 级 · 忙了一年',
    cover: '🐝',
    palette: ['#e6f5c9', '#ffe6b3'],
    summary: '春天种下花子，夏天拿水，秋天做蜜。冬天园里没有花了，屋里却有蜜，也有朋友。',
    newChars: ['蜂', '园', '养', '忙', '总', '为', '所', '以'],
    pages: [
      { emoji: '🐝', text: '小蜂有一个小花园。', p: 'xiǎo fēng yǒu yī gè xiǎo huā yuán.' },
      { emoji: '🌱', text: '春天，他在土里种下花的子。', p: 'chūn tiān, tā zài tǔ lǐ zhòng xià huā de zǐ.' },
      { emoji: '💧', text: '每天早上，他拿水给花苗。', p: 'měi tiān zǎo shang, tā ná shuǐ gěi huā miáo.' },
      { emoji: '☀️', text: '日光很好，花苗一天比一天高。', p: 'rì guāng hěn hǎo, huā miáo yī tiān bǐ yī tiān gāo.' },
      { emoji: '🌸', text: '过了一个月，园里的花都开了。', p: 'guò le yī gè yuè, yuán lǐ de huā dōu kāi le.' },
      { emoji: '🦋', text: '小蝶来了，小蚁也来了。', p: 'xiǎo dié lái le, xiǎo yǐ yě lái le.' },
      { emoji: '🍯', text: '小蜂天天忙，他做了好多蜜。', p: 'xiǎo fēng tiān tiān máng, tā zuò le hǎo duō mì.' },
      { emoji: '🐻', text: '老熊问：你为什么总是这么忙？', p: 'lǎo xióng wèn: nǐ wèi shén me zǒng shì zhè me máng?' },
      { emoji: '🌼', text: '小蜂说：我养花，所以花给我蜜；我有蜜，所以能送给朋友。', p: 'xiǎo fēng shuō: wǒ yǎng huā, suǒ yǐ huā gěi wǒ mì; wǒ yǒu mì, suǒ yǐ néng sòng gěi péng you.' },
      { emoji: '❄️', text: '冬天到了，园里没有花。', p: 'dōng tiān dào le, yuán lǐ méi yǒu huā.' },
      { emoji: '🏠', text: '但屋里有蜜，还有好多来看他的朋友。', p: 'dàn wū lǐ yǒu mì, hái yǒu hǎo duō lái kàn tā de péng you.' }
    ]
  },
  {
    id: 'b30',
    title: '长大以后',
    pinyin: 'zhǎng dà yǐ hòu',
    level: 6,
    levelName: '第 6 级 · 全班一同想一想',
    cover: '🌟',
    palette: ['#c8ebff', '#ffe0e6'],
    summary: '老师问全班：长大以后想做什么？医生、老师、农人、工人……最后老师问我，我说我还没想好。',
    newChars: ['工', '农', '修', '桥', '答', '每', '会', '要'],
    pages: [
      { emoji: '🧑‍🏫', text: '老师问：你们长大以后想做什么？', p: 'lǎo shī wèn: nǐ men zhǎng dà yǐ hòu xiǎng zuò shén me?' },
      { emoji: '👩‍⚕️', text: '小红答：我想做医生，帮病人。', p: 'xiǎo hóng dá: wǒ xiǎng zuò yī shēng, bāng bìng rén.' },
      { emoji: '👨‍🏫', text: '小明答：我想做老师，教小朋友读书写字。', p: 'xiǎo míng dá: wǒ xiǎng zuò lǎo shī, jiào xiǎo péng you dú shū xiě zì.' },
      { emoji: '👨‍🌾', text: '小青答：我想做农人，种果树，也种米。', p: 'xiǎo qīng dá: wǒ xiǎng zuò nóng rén, zhòng guǒ shù, yě zhòng mǐ.' },
      { emoji: '👷', text: '小星答：我想做工人，修路，也修桥。', p: 'xiǎo xīng dá: wǒ xiǎng zuò gōng rén, xiū lù, yě xiū qiáo.' },
      { emoji: '🚢', text: '小云答：我想开船，到海洋上去。', p: 'xiǎo yún dá: wǒ xiǎng kāi chuán, dào hǎi yáng shàng qù.' },
      { emoji: '🎶', text: '小月答：我想唱歌，唱给大家听。', p: 'xiǎo yuè dá: wǒ xiǎng chàng gē, chàng gěi dà jiā tīng.' },
      { emoji: '🤔', text: '老师问我：你想做什么？', p: 'lǎo shī wèn wǒ: nǐ xiǎng zuò shén me?' },
      { emoji: '😄', text: '我说：我还没想好，但我要每天学，每天问。', p: 'wǒ shuō: wǒ hái méi xiǎng hǎo, dàn wǒ yào měi tiān xué, měi tiān wèn.' },
      { emoji: '🌟', text: '老师笑了：这就最好。会问的人，长大都能做好。', p: 'lǎo shī xiào le: zhè jiù zuì hǎo. huì wèn de rén, zhǎng dà dōu néng zuò hǎo.' }
    ]
  }
]
