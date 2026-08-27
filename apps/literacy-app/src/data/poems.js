/**
 * 古诗启蒙语料 —— 24 首学前到小学低段最常背的诗。
 *
 * 和绘本（books.js）不同，古诗的正文是不能改的：一首《静夜思》里出现「望」「低」，
 * 就算孩子还没在字表里学到，也不能把它换成别的字。所以这里不用「只许出现已学字」
 * 那条硬约束，改成一条同样能自动化守住、但对古诗成立的约束：
 *
 *   正文里的每一个字，要么已经在 characters.js 的字表里（孩子学过），
 *   要么在下面的 POEM_GLOSS 里有拼音和一句话解释（跟读时当场教）。
 *
 * `verifyPoemCoverage()` 会逐字校验这一条，`npm run check:data` 会跑它。
 * 于是「这首诗里孩子有几个字没学过、分别是什么意思」永远是算出来的，
 * 不会因为字表长大或诗歌增补而对不上号——字表补上哪个字，它就自动从生字里退场。
 *
 * 字段：
 *   id          路由与进度记录用的稳定 id
 *   title       诗题
 *   titlePinyin 诗题拼音
 *   author      作者，佚名的乐府 / 民歌写朝代
 *   dynasty     朝代
 *   theme       主题（见 POEM_THEMES），长廊按它分组
 *   level       1-3，按「正文里孩子没学过的字有几个」定，不是按名气
 *   emoji       卡片图标
 *   palette     卡片渐变色（两个色值）
 *   summary     一句话说这首诗在写什么
 *   lines       逐句：text 正文、pinyin 逐字拼音（空格分隔，字数必须对上）、
 *               sense 这一句的白话
 *   tip         跟读前给孩子的一句提示
 *
 * 拼音按诗里的读法注，不一定等于字表里的常用读音（「斜」在《风》里读 xié，
 * 「谁」在《悯农》里读 shuí）——跟读时孩子听到的是哪个音，这里就写哪个音。
 */

import { CHARACTER_MAP } from './characters.js'

const PUNCTUATION = new Set([
  '，', '。', '！', '？', '：', '、', '；', '「', '」', '《', '》', '…', '—', ' ', '\n'
])

/**
 * 生字注解表：正文里出现、但字表还没收的字。
 *
 * 这是一张「字 → 拼音 + 一句话意思」的表，跟读界面点到哪个生字就弹哪一条。
 * 字表长大之后，这里的条目会自动失效（`poemNewChars()` 只挑字表里没有的字），
 * 所以不需要在扩字库时回来删——留着也不会重复显示。
 */
export const POEM_GLOSS = {
  无: { p: 'wú', m: '没有' },
  亭: { p: 'tíng', m: '路边给人歇脚的小房子' },
  望: { p: 'wàng', m: '抬起头往远处看' },
  低: { p: 'dī', m: '往下，低下去' },
  可: { p: 'kě', m: '可以' },
  辰: { p: 'chén', m: '天上的星星' },
  项: { p: 'xiàng', m: '脖子' },
  浮: { p: 'fú', m: '轻轻漂在水面上' },
  拨: { p: 'bō', m: '用手把水划开' },
  清: { p: 'qīng', m: '干净、透亮' },
  枯: { p: 'kū', m: '草木干黄了' },
  荣: { p: 'róng', m: '草木长得又绿又旺' },
  尽: { p: 'jìn', m: '完了，一点也不剩' },
  吹: { p: 'chuī', m: '风吹过来' },
  依: { p: 'yī', m: '挨着、靠着' },
  入: { p: 'rù', m: '进去' },
  欲: { p: 'yù', m: '想要' },
  穷: { p: 'qióng', m: '看到最远的头' },
  呼: { p: 'hū', m: '大声叫它' },
  作: { p: 'zuò', m: '当作' },
  玉: { p: 'yù', m: '又白又亮的美石头' },
  盘: { p: 'pán', m: '圆圆的盘子' },
  瑶: { p: 'yáo', m: '神仙住的地方叫瑶台' },
  解: { p: 'jiě', m: '会、能够' },
  落: { p: 'luò', m: '掉下来' },
  竿: { p: 'gān', m: '一根一根的竹子' },
  斜: { p: 'xié', m: '歪着，不是直的' },
  童: { p: 'tóng', m: '小孩子' },
  言: { p: 'yán', m: '说' },
  采: { p: 'cǎi', m: '摘' },
  此: { p: 'cǐ', m: '这里' },
  知: { p: 'zhī', m: '知道' },
  处: { p: 'chù', m: '地方' },
  惜: { p: 'xī', m: '舍不得' },
  细: { p: 'xì', m: '又小又轻' },
  照: { p: 'zhào', m: '光照在上面' },
  尖: { p: 'jiān', m: '尖尖的小角' },
  立: { p: 'lì', m: '站着' },
  辞: { p: 'cí', m: '告别，说声再见就走' },
  帝: { p: 'dì', m: '这里指白帝城' },
  陵: { p: 'líng', m: '这里指江陵城' },
  两: { p: 'liǎng', m: '二，两边' },
  啼: { p: 'tí', m: '鸟和小兽的叫声' },
  住: { p: 'zhù', m: '停下来' },
  凌: { p: 'líng', m: '顶着，一点也不怕' },
  独: { p: 'dú', m: '就它一个' },
  自: { p: 'zì', m: '自己' },
  遥: { p: 'yáo', m: '很远很远' },
  暗: { p: 'àn', m: '悄悄的，看不见的' },
  炉: { p: 'lú', m: '香炉峰，一座山峰的名字' },
  紫: { p: 'zǐ', m: '紫色' },
  川: { p: 'chuān', m: '河' },
  直: { p: 'zhí', m: '笔直地，一直' },
  南: { p: 'nán', m: '南边' },
  何: { p: 'hé', m: '多么' },
  东: { p: 'dōng', m: '东边' },
  西: { p: 'xī', m: '西边' },
  北: { p: 'běi', m: '北边' },
  见: { p: 'jiàn', m: '看见' },
  闻: { p: 'wén', m: '听见' },
  响: { p: 'xiǎng', m: '声音传过来' },
  返: { p: 'fǎn', m: '照回来' },
  苔: { p: 'tái', m: '石头上绿绿的青苔' },
  眠: { p: 'mián', m: '睡觉' },
  觉: { p: 'jué', m: '发觉，没察觉到' },
  晓: { p: 'xiǎo', m: '天亮' },
  粒: { p: 'lì', m: '一颗一颗的' },
  粟: { p: 'sù', m: '谷子，一种粮食' },
  颗: { p: 'kē', m: '数粮食用的词' },
  闲: { p: 'xián', m: '空着，没种东西' },
  夫: { p: 'fū', m: '农夫，种地的人' },
  犹: { p: 'yóu', m: '还是' },
  死: { p: 'sǐ', m: '活不下去' },
  撑: { p: 'chēng', m: '用竹竿把小船顶着往前' },
  艇: { p: 'tǐng', m: '小船' },
  偷: { p: 'tōu', m: '悄悄地' },
  踪: { p: 'zōng', m: '走过留下的印子' },
  萍: { p: 'píng', m: '浮在水面上的浮萍' },
  禾: { p: 'hé', m: '田里的庄稼' },
  当: { p: 'dāng', m: '正对着' },
  滴: { p: 'dī', m: '一滴一滴地掉' },
  谁: { p: 'shuí', m: '哪一个人' },
  皆: { p: 'jiē', m: '全都' },
  辛: { p: 'xīn', m: '辛苦' },
  振: { p: 'zhèn', m: '震得整片林子都在响' },
  樾: { p: 'yuè', m: '路边连成一片树荫的大树' },
  意: { p: 'yì', m: '心里想着' },
  捕: { p: 'bǔ', m: '捉' },
  鸣: { p: 'míng', m: '叫' },
  闭: { p: 'bì', m: '合上' },
  李: { p: 'lǐ', m: '姓李，这里说的是李白' },
  将: { p: 'jiāng', m: '就要' },
  行: { p: 'xíng', m: '出发上路' },
  踏: { p: 'tà', m: '用脚打着拍子' },
  潭: { p: 'tán', m: '很深的水塘' },
  汪: { p: 'wāng', m: '姓汪，这里说的是汪伦' },
  伦: { p: 'lún', m: '汪伦，李白的好朋友' },
  绝: { p: 'jué', m: '一只也不剩' },
  径: { p: 'jìng', m: '小路' },
  灭: { p: 'miè', m: '看不见了' },
  孤: { p: 'gū', m: '孤零零的' },
  蓑: { p: 'suō', m: '草编的雨衣' },
  笠: { p: 'lì', m: '竹编的遮雨帽子' },
  翁: { p: 'wēng', m: '老爷爷' },
  钓: { p: 'diào', m: '钓鱼' },
  莺: { p: 'yīng', m: '黄莺，一种会唱歌的小鸟' },
  拂: { p: 'fú', m: '轻轻地扫过' },
  堤: { p: 'dī', m: '河边挡水的土坝' },
  醉: { p: 'zuì', m: '像喝醉了一样迷迷糊糊' },
  儿: { p: 'ér', m: '小孩子' },
  散: { p: 'sàn', m: '放学，各自回家' },
  归: { p: 'guī', m: '回来' },
  趁: { p: 'chèn', m: '赶紧借着这阵风' },
  鸢: { p: 'yuān', m: '纸鸢就是风筝' }
}

/** 长廊按主题分区，孩子按「想看什么」挑，而不是按朝代挑。 */
export const POEM_THEMES = [
  { id: 'nature', name: '山水风光', emoji: '⛰️', desc: '山、水、瀑布和远方' },
  { id: 'season', name: '四季时节', emoji: '🌸', desc: '春夏秋冬各有各的好看' },
  { id: 'animal', name: '鸟兽虫鱼', emoji: '🐦', desc: '会叫的、会飞的、会游的' },
  { id: 'child', name: '童趣生活', emoji: '🧒', desc: '小孩子在诗里玩什么' },
  { id: 'feeling', name: '心里的话', emoji: '💛', desc: '想家、想朋友、惜粮食' }
]

export const POEMS = [
  {
    id: 'hua',
    title: '画',
    titlePinyin: 'huà',
    author: '王维',
    dynasty: '唐',
    theme: 'nature',
    level: 1,
    emoji: '🖼️',
    palette: ['#ffe6b3', '#c8ebff'],
    summary: '画里的山有颜色，画里的水没声音——原来说的是一幅画。',
    tip: '这首诗是一个谜语，读完猜猜谜底是什么。',
    lines: [
      { text: '远看山有色，', pinyin: 'yuǎn kàn shān yǒu sè', sense: '远远看过去，山是有颜色的。' },
      { text: '近听水无声。', pinyin: 'jìn tīng shuǐ wú shēng', sense: '走近了听，水却一点声音也没有。' },
      { text: '春去花还在，', pinyin: 'chūn qù huā hái zài', sense: '春天都过去了，花还开着。' },
      { text: '人来鸟不惊。', pinyin: 'rén lái niǎo bù jīng', sense: '人走过来，鸟也不飞走。' }
    ]
  },
  {
    id: 'shancun',
    title: '山村咏怀',
    titlePinyin: 'shān cūn yǒng huái',
    author: '邵雍',
    dynasty: '宋',
    theme: 'nature',
    level: 1,
    emoji: '🏘️',
    palette: ['#d9f6f3', '#ffe0c2'],
    summary: '一到十全在诗里，走一趟小山村就把数字念了一遍。',
    tip: '一边读一边数，看看十个数字是不是都出现了。',
    lines: [
      { text: '一去二三里，', pinyin: 'yī qù èr sān lǐ', sense: '往前走了两三里路。' },
      { text: '烟村四五家。', pinyin: 'yān cūn sì wǔ jiā', sense: '看见炊烟里有四五户人家。' },
      { text: '亭台六七座，', pinyin: 'tíng tái liù qī zuò', sense: '路边有六七座小亭子。' },
      { text: '八九十枝花。', pinyin: 'bā jiǔ shí zhī huā', sense: '还开着八枝九枝十枝花。' }
    ]
  },
  {
    id: 'jingyesi',
    title: '静夜思',
    titlePinyin: 'jìng yè sī',
    author: '李白',
    dynasty: '唐',
    theme: 'feeling',
    level: 1,
    emoji: '🌕',
    palette: ['#e8e0ff', '#c8ebff'],
    summary: '半夜醒来看见月光，就想起了很远的家。',
    tip: '读到「思故乡」的时候，声音可以慢一点、轻一点。',
    lines: [
      { text: '床前明月光，', pinyin: 'chuáng qián míng yuè guāng', sense: '床前洒了一地月光。' },
      { text: '疑是地上霜。', pinyin: 'yí shì dì shàng shuāng', sense: '还以为是地上结了霜。' },
      { text: '举头望明月，', pinyin: 'jǔ tóu wàng míng yuè', sense: '抬起头看那轮亮亮的月亮。' },
      { text: '低头思故乡。', pinyin: 'dī tóu sī gù xiāng', sense: '低下头就想起了老家。' }
    ]
  },
  {
    id: 'yesushansi',
    title: '夜宿山寺',
    titlePinyin: 'yè sù shān sì',
    author: '李白',
    dynasty: '唐',
    theme: 'nature',
    level: 1,
    emoji: '🌌',
    palette: ['#c8ebff', '#e8e0ff'],
    summary: '山上的楼太高了，伸手好像就能摸到星星。',
    tip: '最后两句要小声读——诗里说话大声会吵到天上的人。',
    lines: [
      { text: '危楼高百尺，', pinyin: 'wēi lóu gāo bǎi chǐ', sense: '这座高楼有一百尺那么高。' },
      { text: '手可摘星辰。', pinyin: 'shǒu kě zhāi xīng chén', sense: '伸出手好像就能摘下星星。' },
      { text: '不敢高声语，', pinyin: 'bù gǎn gāo shēng yǔ', sense: '我不敢大声说话，' },
      { text: '恐惊天上人。', pinyin: 'kǒng jīng tiān shàng rén', sense: '怕吵醒了天上的人。' }
    ]
  },
  {
    id: 'yonge',
    title: '咏鹅',
    titlePinyin: 'yǒng é',
    author: '骆宾王',
    dynasty: '唐',
    theme: 'animal',
    level: 2,
    emoji: '🦢',
    palette: ['#d9f6f3', '#ffe6b3'],
    summary: '一只白鹅在水上唱歌划水，红脚掌一拨一拨的。',
    tip: '开头三个「鹅」要一个比一个响亮，像在喊它。',
    lines: [
      { text: '鹅，鹅，鹅，', pinyin: 'é é é', sense: '鹅呀，鹅呀，鹅呀！' },
      { text: '曲项向天歌。', pinyin: 'qū xiàng xiàng tiān gē', sense: '弯着脖子朝天上唱歌。' },
      { text: '白毛浮绿水，', pinyin: 'bái máo fú lǜ shuǐ', sense: '白白的羽毛漂在绿水上。' },
      { text: '红掌拨清波。', pinyin: 'hóng zhǎng bō qīng bō', sense: '红红的脚掌划开清亮的水波。' }
    ]
  },
  {
    id: 'cao',
    title: '赋得古原草送别（节选）',
    titlePinyin: 'fù dé gǔ yuán cǎo sòng bié',
    author: '白居易',
    dynasty: '唐',
    theme: 'season',
    level: 2,
    emoji: '🌱',
    palette: ['#d8f5c8', '#ffe6b3'],
    summary: '草一年枯一次，可是春风一吹，它又全长回来了。',
    tip: '「春风吹又生」要读得有精神，那是草又活过来了。',
    lines: [
      { text: '离离原上草，', pinyin: 'lí lí yuán shàng cǎo', sense: '原野上的草长得又密又高。' },
      { text: '一岁一枯荣。', pinyin: 'yī suì yī kū róng', sense: '每一年都要黄一回、绿一回。' },
      { text: '野火烧不尽，', pinyin: 'yě huǒ shāo bù jìn', sense: '野火怎么烧都烧不完，' },
      { text: '春风吹又生。', pinyin: 'chūn fēng chuī yòu shēng', sense: '春风一吹，它又长出来了。' }
    ]
  },
  {
    id: 'dengguanque',
    title: '登鹳雀楼',
    titlePinyin: 'dēng guàn què lóu',
    author: '王之涣',
    dynasty: '唐',
    theme: 'nature',
    level: 2,
    emoji: '🏯',
    palette: ['#ffe0c2', '#c8ebff'],
    summary: '想看得更远一点，那就再往上爬一层楼。',
    tip: '最后一句是这首诗最有名的话，读完想一想它在说什么。',
    lines: [
      { text: '白日依山尽，', pinyin: 'bái rì yī shān jìn', sense: '太阳挨着山头一点点落下去。' },
      { text: '黄河入海流。', pinyin: 'huáng hé rù hǎi liú', sense: '黄河的水一直流进大海。' },
      { text: '欲穷千里目，', pinyin: 'yù qióng qiān lǐ mù', sense: '要是想看到一千里那么远，' },
      { text: '更上一层楼。', pinyin: 'gèng shàng yī céng lóu', sense: '那就再往上爬一层楼。' }
    ]
  },
  {
    id: 'gulangyue',
    title: '古朗月行（节选）',
    titlePinyin: 'gǔ lǎng yuè xíng',
    author: '李白',
    dynasty: '唐',
    theme: 'feeling',
    level: 2,
    emoji: '🌝',
    palette: ['#e8e0ff', '#ffe6b3'],
    summary: '小时候不认识月亮，还把它叫成一只白玉盘子。',
    tip: '这是李白在讲他小时候的事，读起来可以带点笑意。',
    lines: [
      { text: '小时不识月，', pinyin: 'xiǎo shí bù shí yuè', sense: '小时候我还不认识月亮，' },
      { text: '呼作白玉盘。', pinyin: 'hū zuò bái yù pán', sense: '就把它叫成一只白玉盘子。' },
      { text: '又疑瑶台镜，', pinyin: 'yòu yí yáo tái jìng', sense: '又猜它是神仙台上的镜子，' },
      { text: '飞在青云端。', pinyin: 'fēi zài qīng yún duān', sense: '飞到青色的云头上去了。' }
    ]
  },
  {
    id: 'feng',
    title: '风',
    titlePinyin: 'fēng',
    author: '李峤',
    dynasty: '唐',
    theme: 'season',
    level: 2,
    emoji: '🍃',
    palette: ['#d9f6f3', '#d8f5c8'],
    summary: '整首诗一个「风」字也没有，可句句都是风。',
    tip: '读完找一找：诗里哪里藏着风？',
    lines: [
      { text: '解落三秋叶，', pinyin: 'jiě luò sān qiū yè', sense: '它能把秋天的叶子吹下来，' },
      { text: '能开二月花。', pinyin: 'néng kāi èr yuè huā', sense: '也能把二月的花吹开。' },
      { text: '过江千尺浪，', pinyin: 'guò jiāng qiān chǐ làng', sense: '刮过江面能掀起千尺高的浪，' },
      { text: '入竹万竿斜。', pinyin: 'rù zhú wàn gān xié', sense: '钻进竹林能把万根竹子吹歪。' }
    ]
  },
  {
    id: 'xunyinzhe',
    title: '寻隐者不遇',
    titlePinyin: 'xún yǐn zhě bù yù',
    author: '贾岛',
    dynasty: '唐',
    theme: 'nature',
    level: 2,
    emoji: '🌲',
    palette: ['#d8f5c8', '#c8ebff'],
    summary: '上山找一位老先生，只碰到他的小徒弟。',
    tip: '这首诗像一段对话，第三、四句是小童说的话。',
    lines: [
      { text: '松下问童子，', pinyin: 'sōng xià wèn tóng zǐ', sense: '我在松树下问一个小孩子。' },
      { text: '言师采药去。', pinyin: 'yán shī cǎi yào qù', sense: '他说师父采药去了。' },
      { text: '只在此山中，', pinyin: 'zhǐ zài cǐ shān zhōng', sense: '就在这座山里面，' },
      { text: '云深不知处。', pinyin: 'yún shēn bù zhī chù', sense: '可是云太厚，说不清在哪儿。' }
    ]
  },
  {
    id: 'xiaochi',
    title: '小池',
    titlePinyin: 'xiǎo chí',
    author: '杨万里',
    dynasty: '宋',
    theme: 'season',
    level: 2,
    emoji: '🪷',
    palette: ['#d9f6f3', '#ffd0d6'],
    summary: '小荷叶才露出一个尖角，蜻蜓就已经站上去了。',
    tip: '最后一句里有一只蜻蜓，读的时候想象它停在你手指上。',
    lines: [
      { text: '泉眼无声惜细流，', pinyin: 'quán yǎn wú shēng xī xì liú', sense: '泉眼静悄悄的，舍不得让水多流一点。' },
      { text: '树阴照水爱晴柔。', pinyin: 'shù yīn zhào shuǐ ài qíng róu', sense: '树影照在水里，喜欢这样的好天气。' },
      { text: '小荷才露尖尖角，', pinyin: 'xiǎo hé cái lù jiān jiān jiǎo', sense: '小荷叶刚露出一个尖尖的小角，' },
      { text: '早有蜻蜓立上头。', pinyin: 'zǎo yǒu qīng tíng lì shàng tóu', sense: '早就有一只蜻蜓站在上面了。' }
    ]
  },
  {
    id: 'zaofa',
    title: '早发白帝城',
    titlePinyin: 'zǎo fā bái dì chéng',
    author: '李白',
    dynasty: '唐',
    theme: 'nature',
    level: 2,
    emoji: '⛵',
    palette: ['#ffe6b3', '#c8ebff'],
    summary: '船顺水跑得飞快，一天就走完了一千里。',
    tip: '这首诗越读越快，最后一句像船一下子冲了出去。',
    lines: [
      { text: '朝辞白帝彩云间，', pinyin: 'zhāo cí bái dì cǎi yún jiān', sense: '早上从彩云围着的白帝城出发，' },
      { text: '千里江陵一日还。', pinyin: 'qiān lǐ jiāng líng yī rì huán', sense: '一千里外的江陵，一天就到了。' },
      { text: '两岸猿声啼不住，', pinyin: 'liǎng àn yuán shēng tí bù zhù', sense: '两边山上的猿一直在叫，' },
      { text: '轻舟已过万重山。', pinyin: 'qīng zhōu yǐ guò wàn chóng shān', sense: '小船已经穿过了一重又一重的山。' }
    ]
  },
  {
    id: 'meihua',
    title: '梅花',
    titlePinyin: 'méi huā',
    author: '王安石',
    dynasty: '宋',
    theme: 'season',
    level: 2,
    emoji: '🌺',
    palette: ['#ffd0d6', '#e8e0ff'],
    summary: '墙角的梅花不怕冷，隔很远就能闻到它的香。',
    tip: '读到「暗香来」时，深吸一口气，像真的闻到了一样。',
    lines: [
      { text: '墙角数枝梅，', pinyin: 'qiáng jiǎo shù zhī méi', sense: '墙角有那么几枝梅花。' },
      { text: '凌寒独自开。', pinyin: 'líng hán dú zì kāi', sense: '天那么冷，它一个人开着。' },
      { text: '遥知不是雪，', pinyin: 'yáo zhī bù shì xuě', sense: '离得老远我就知道那不是雪，' },
      { text: '为有暗香来。', pinyin: 'wèi yǒu àn xiāng lái', sense: '因为有一阵清香飘过来了。' }
    ]
  },
  {
    id: 'wanglushan',
    title: '望庐山瀑布',
    titlePinyin: 'wàng lú shān pù bù',
    author: '李白',
    dynasty: '唐',
    theme: 'nature',
    level: 3,
    emoji: '🏔️',
    palette: ['#c8ebff', '#d9f6f3'],
    summary: '瀑布从高高的山上冲下来，像银河从天上掉了下来。',
    tip: '最后一句要读得又高又亮，那是水从天上落下来的声音。',
    lines: [
      { text: '日照香炉生紫烟，', pinyin: 'rì zhào xiāng lú shēng zǐ yān', sense: '太阳照着香炉峰，升起一片紫色的雾。' },
      { text: '遥看瀑布挂前川。', pinyin: 'yáo kàn pù bù guà qián chuān', sense: '远远看瀑布像挂在山前的一条河。' },
      { text: '飞流直下三千尺，', pinyin: 'fēi liú zhí xià sān qiān chǐ', sense: '水笔直地往下冲了三千尺，' },
      { text: '疑是银河落九天。', pinyin: 'yí shì yín hé luò jiǔ tiān', sense: '真像天上的银河掉了下来。' }
    ]
  },
  {
    id: 'jiangnan',
    title: '江南',
    titlePinyin: 'jiāng nán',
    author: '汉乐府',
    dynasty: '汉',
    theme: 'animal',
    level: 3,
    emoji: '🐟',
    palette: ['#d9f6f3', '#d8f5c8'],
    summary: '荷叶下面的小鱼游来游去，东南西北到处都是它。',
    tip: '后面四句只换了一个字，读的时候把方向读清楚。',
    lines: [
      { text: '江南可采莲，', pinyin: 'jiāng nán kě cǎi lián', sense: '江南到了可以采莲蓬的时候。' },
      { text: '莲叶何田田。', pinyin: 'lián yè hé tián tián', sense: '荷叶长得多么密、多么好看。' },
      { text: '鱼戏莲叶间。', pinyin: 'yú xì lián yè jiān', sense: '小鱼在荷叶中间玩。' },
      { text: '鱼戏莲叶东，', pinyin: 'yú xì lián yè dōng', sense: '一会儿游到荷叶东边，' },
      { text: '鱼戏莲叶西，', pinyin: 'yú xì lián yè xī', sense: '一会儿游到荷叶西边，' },
      { text: '鱼戏莲叶南，', pinyin: 'yú xì lián yè nán', sense: '一会儿游到荷叶南边，' },
      { text: '鱼戏莲叶北。', pinyin: 'yú xì lián yè běi', sense: '一会儿又游到荷叶北边去了。' }
    ]
  },
  {
    id: 'luzhai',
    title: '鹿柴',
    titlePinyin: 'lù zhài',
    author: '王维',
    dynasty: '唐',
    theme: 'nature',
    level: 3,
    emoji: '🦌',
    palette: ['#d8f5c8', '#e8e0ff'],
    summary: '山里一个人也看不见，只听得见有人在说话。',
    tip: '这首诗很安静，用最轻的声音读它。',
    lines: [
      { text: '空山不见人，', pinyin: 'kōng shān bù jiàn rén', sense: '空空的山里看不到一个人。' },
      { text: '但闻人语响。', pinyin: 'dàn wén rén yǔ xiǎng', sense: '却听得见有人说话的声音。' },
      { text: '返景入深林，', pinyin: 'fǎn jǐng rù shēn lín', sense: '夕阳的光照进了深深的树林，' },
      { text: '复照青苔上。', pinyin: 'fù zhào qīng tái shàng', sense: '又落在绿绿的青苔上。' }
    ]
  },
  {
    id: 'chunxiao',
    title: '春晓',
    titlePinyin: 'chūn xiǎo',
    author: '孟浩然',
    dynasty: '唐',
    theme: 'season',
    level: 3,
    emoji: '🌸',
    palette: ['#ffd0d6', '#d8f5c8'],
    summary: '春天睡得太香了，醒来才发现外面全是鸟叫。',
    tip: '第一句像刚睡醒，可以读得慢一点、迷糊一点。',
    lines: [
      { text: '春眠不觉晓，', pinyin: 'chūn mián bù jué xiǎo', sense: '春天睡觉睡得香，天亮了都不知道。' },
      { text: '处处闻啼鸟。', pinyin: 'chù chù wén tí niǎo', sense: '到处都听得见小鸟在叫。' },
      { text: '夜来风雨声，', pinyin: 'yè lái fēng yǔ shēng', sense: '想起夜里有风声雨声，' },
      { text: '花落知多少。', pinyin: 'huā luò zhī duō shǎo', sense: '不知道打落了多少花瓣。' }
    ]
  },
  {
    id: 'minnong1',
    title: '悯农（其一）',
    titlePinyin: 'mǐn nóng qí yī',
    author: '李绅',
    dynasty: '唐',
    theme: 'feeling',
    level: 3,
    emoji: '🌾',
    palette: ['#ffe6b3', '#d8f5c8'],
    summary: '一粒种子能收一万颗粮，可种地的人还是吃不饱。',
    tip: '读完想一想：粮食是从哪里来的？',
    lines: [
      { text: '春种一粒粟，', pinyin: 'chūn zhòng yī lì sù', sense: '春天种下一粒谷子，' },
      { text: '秋收万颗子。', pinyin: 'qiū shōu wàn kē zǐ', sense: '秋天能收下一万颗粮食。' },
      { text: '四海无闲田，', pinyin: 'sì hǎi wú xián tián', sense: '天底下没有一块地是空着的，' },
      { text: '农夫犹饿死。', pinyin: 'nóng fū yóu è sǐ', sense: '种地的人却还是会饿肚子。' }
    ]
  },
  {
    id: 'chishang',
    title: '池上',
    titlePinyin: 'chí shàng',
    author: '白居易',
    dynasty: '唐',
    theme: 'child',
    level: 3,
    emoji: '🛶',
    palette: ['#d9f6f3', '#ffe6b3'],
    summary: '小孩偷偷采了莲蓬回来，水面上的痕迹把他出卖了。',
    tip: '这是一个小秘密被发现的故事，读到最后要偷偷笑一下。',
    lines: [
      { text: '小娃撑小艇，', pinyin: 'xiǎo wá chēng xiǎo tǐng', sense: '一个小孩子撑着小船，' },
      { text: '偷采白莲回。', pinyin: 'tōu cǎi bái lián huí', sense: '悄悄采了白莲蓬回来。' },
      { text: '不解藏踪迹，', pinyin: 'bù jiě cáng zōng jì', sense: '他不懂得把痕迹藏起来，' },
      { text: '浮萍一道开。', pinyin: 'fú píng yī dào kāi', sense: '水上的浮萍被划开了一道口子。' }
    ]
  },
  {
    id: 'minnong2',
    title: '悯农（其二）',
    titlePinyin: 'mǐn nóng qí èr',
    author: '李绅',
    dynasty: '唐',
    theme: 'feeling',
    level: 3,
    emoji: '🍚',
    palette: ['#ffe6b3', '#ffe0c2'],
    summary: '碗里的每一粒米，都是有人在大太阳底下一滴汗换来的。',
    tip: '吃饭的时候可以背这首诗，提醒自己不要剩饭。',
    lines: [
      { text: '锄禾日当午，', pinyin: 'chú hé rì dāng wǔ', sense: '中午最晒的时候还在地里锄草，' },
      { text: '汗滴禾下土。', pinyin: 'hàn dī hé xià tǔ', sense: '汗一滴一滴掉在庄稼下的土里。' },
      { text: '谁知盘中餐，', pinyin: 'shuí zhī pán zhōng cān', sense: '有谁知道盘子里的饭菜，' },
      { text: '粒粒皆辛苦。', pinyin: 'lì lì jiē xīn kǔ', sense: '每一粒都来得那么辛苦。' }
    ]
  },
  {
    id: 'suojian',
    title: '所见',
    titlePinyin: 'suǒ jiàn',
    author: '袁枚',
    dynasty: '清',
    theme: 'child',
    level: 3,
    emoji: '🐂',
    palette: ['#d8f5c8', '#ffe6b3'],
    summary: '放牛的小孩一路唱歌，忽然为了捉知了闭上了嘴。',
    tip: '最后一句要一下子停住，就像他真的不出声了。',
    lines: [
      { text: '牧童骑黄牛，', pinyin: 'mù tóng qí huáng niú', sense: '放牛的小孩骑在黄牛背上，' },
      { text: '歌声振林樾。', pinyin: 'gē shēng zhèn lín yuè', sense: '歌声把整片树林都震响了。' },
      { text: '意欲捕鸣蝉，', pinyin: 'yì yù bǔ míng chán', sense: '他想去捉那只正在叫的知了，' },
      { text: '忽然闭口立。', pinyin: 'hū rán bì kǒu lì', sense: '忽然闭上嘴，一动不动地站住了。' }
    ]
  },
  {
    id: 'zengwanglun',
    title: '赠汪伦',
    titlePinyin: 'zèng wāng lún',
    author: '李白',
    dynasty: '唐',
    theme: 'feeling',
    level: 3,
    emoji: '👋',
    palette: ['#c8ebff', '#ffd0d6'],
    summary: '船要开了，好朋友在岸上踏着拍子唱歌送他。',
    tip: '这是写给朋友的诗，读的时候想想你的好朋友。',
    lines: [
      { text: '李白乘舟将欲行，', pinyin: 'lǐ bái chéng zhōu jiāng yù xíng', sense: '李白坐上船正要出发，' },
      { text: '忽闻岸上踏歌声。', pinyin: 'hū wén àn shàng tà gē shēng', sense: '忽然听见岸上有人踏着脚唱歌。' },
      { text: '桃花潭水深千尺，', pinyin: 'táo huā tán shuǐ shēn qiān chǐ', sense: '桃花潭的水有一千尺那么深，' },
      { text: '不及汪伦送我情。', pinyin: 'bù jí wāng lún sòng wǒ qíng', sense: '也比不上汪伦送我的这份心意。' }
    ]
  },
  {
    id: 'jiangxue',
    title: '江雪',
    titlePinyin: 'jiāng xuě',
    author: '柳宗元',
    dynasty: '唐',
    theme: 'season',
    level: 3,
    emoji: '❄️',
    palette: ['#c8ebff', '#e8e0ff'],
    summary: '雪下得连鸟都不飞了，只剩一个老爷爷在江上钓鱼。',
    tip: '四句诗的头一个字连起来是「千万孤独」，找找看。',
    lines: [
      { text: '千山鸟飞绝，', pinyin: 'qiān shān niǎo fēi jué', sense: '一座座山上，一只鸟也看不见了。' },
      { text: '万径人踪灭。', pinyin: 'wàn jìng rén zōng miè', sense: '一条条小路上，人的脚印也没有了。' },
      { text: '孤舟蓑笠翁，', pinyin: 'gū zhōu suō lì wēng', sense: '一条小船上坐着披蓑衣戴斗笠的老人，' },
      { text: '独钓寒江雪。', pinyin: 'dú diào hán jiāng xuě', sense: '一个人在下雪的江上钓鱼。' }
    ]
  },
  {
    id: 'cunju',
    title: '村居',
    titlePinyin: 'cūn jū',
    author: '高鼎',
    dynasty: '清',
    theme: 'child',
    level: 3,
    emoji: '🪁',
    palette: ['#d8f5c8', '#c8ebff'],
    summary: '二月的村子里草长莺飞，孩子放学回来忙着放风筝。',
    tip: '读完可以去外面看看，有没有人在放风筝。',
    lines: [
      { text: '草长莺飞二月天，', pinyin: 'cǎo zhǎng yīng fēi èr yuè tiān', sense: '二月里草长起来了，黄莺也飞起来了。' },
      { text: '拂堤杨柳醉春烟。', pinyin: 'fú dī yáng liǔ zuì chūn yān', sense: '柳条轻轻扫着河堤，像喝醉了一样。' },
      { text: '儿童散学归来早，', pinyin: 'ér tóng sàn xué guī lái zǎo', sense: '小孩子放学回来得早，' },
      { text: '忙趁东风放纸鸢。', pinyin: 'máng chèn dōng fēng fàng zhǐ yuān', sense: '赶紧借着东风把风筝放上天。' }
    ]
  }
]

export const POEM_MAP = new Map(POEMS.map((p) => [p.id, p]))

export const TOTAL_POEMS = POEMS.length

export function getPoem(id) {
  return POEM_MAP.get(id) ?? null
}

/** 整首诗的正文，不含标点。 */
export function charsInPoem(poem) {
  return [...poem.lines.map((l) => l.text).join('')].filter((ch) => !PUNCTUATION.has(ch))
}

/** 一句诗拆成「字 + 这个字的拼音」，跟读界面逐字高亮就靠它。 */
export function syllablesOfLine(line) {
  const chars = [...line.text]
  const pinyin = line.pinyin.trim().split(/\s+/)
  let index = 0
  return chars.map((ch) => {
    const punct = PUNCTUATION.has(ch)
    return { char: ch, pinyin: punct ? '' : (pinyin[index++] ?? ''), punct }
  })
}

/**
 * 这首诗里孩子还没学过的字 + 它的拼音和意思。
 * 字表收了哪个字，它就自动从这份名单里消失。
 */
export function poemNewChars(poem) {
  const out = []
  const seen = new Set()
  for (const ch of charsInPoem(poem)) {
    if (seen.has(ch) || CHARACTER_MAP.has(ch)) continue
    seen.add(ch)
    const gloss = POEM_GLOSS[ch]
    out.push({ c: ch, p: gloss?.p ?? '', m: gloss?.m ?? '' })
  }
  return out
}

/** 正文里有多少比例的字是孩子已经学过的，长廊按它排「读起来轻松不轻松」。 */
export function poemKnownRatio(poem) {
  const chars = charsInPoem(poem)
  if (!chars.length) return 0
  const known = chars.filter((ch) => CHARACTER_MAP.has(ch)).length
  return known / chars.length
}

/**
 * 内容自检：
 *   1. 正文里的每个字，要么在字表里，要么在 POEM_GLOSS 里有注解；
 *   2. 每句的拼音音节数要和这句的汉字数对得上，否则逐字高亮会错位。
 */
export function verifyPoemCoverage() {
  const problems = []
  for (const poem of POEMS) {
    const unglossed = [
      ...new Set(charsInPoem(poem).filter((ch) => !CHARACTER_MAP.has(ch) && !POEM_GLOSS[ch]))
    ]
    const misaligned = poem.lines
      .map((line, i) => {
        const chars = [...line.text].filter((ch) => !PUNCTUATION.has(ch)).length
        const syllables = line.pinyin.trim().split(/\s+/).filter(Boolean).length
        return chars === syllables ? null : `第 ${i + 1} 句 ${chars} 字 / ${syllables} 音`
      })
      .filter(Boolean)
    if (unglossed.length || misaligned.length) {
      problems.push({ poem: poem.title, unglossed, misaligned })
    }
  }
  return problems
}
