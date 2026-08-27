/**
 * 儿歌小舞台的语料。
 *
 * 十三首儿歌全是为这套字表新写的，不是抄来的童谣——好处不只是版权干净，
 * 而是能守住和分级绘本同一条硬约束：
 *
 *   歌词里的每一个字，都必须已经在 characters.js 的字表里。
 *
 * 古诗做不到这一条（《静夜思》里的「望」不能换成别的字），所以那边退而求其次
 * 用注解兜底；儿歌是我们自己写的，就该按绘本的标准来——孩子跟着唱的时候，
 * 屏幕上不该出现一个他没见过的字。`verifySongCoverage()` 逐字校验，
 * `npm run check:data` 会跑它。
 *
 * 没有音频文件。整套应用是「零素材」的：音效由振荡器合成、朗读走系统 TTS，
 * 儿歌也照这个路子——`notes` 是逐字的音名，播放时由 `utils/audio.js` 的
 * `playMelody()` 实时合成，人声那一路交给朗读。所以每首歌的 `audio` 都是 null，
 * 它留在数据结构里是为了以后真录了童声可以直接填进来，界面不必改。
 *
 * 字段：
 *   id          路由与进度记录用的稳定 id
 *   title       歌名
 *   titlePinyin 歌名拼音
 *   theme       主题（见 SONG_THEMES），小舞台按它分组
 *   emoji       卡片图标
 *   palette     卡片渐变色（两个色值）
 *   summary     一句话说这首歌在唱什么
 *   tip         唱之前给孩子的一句提示
 *   bpm         速度，60–110 之间；越小的孩子唱得越慢
 *   audio       录音地址，暂时都是 null（见上）
 *   lines       逐句：text 歌词、pinyin 逐字拼音（空格分隔，字数必须对上）、
 *               notes 逐字音名（个数也必须和汉字数对上，逐字高亮靠它）
 *
 * 旋律一律落在 C 大调五声音阶（C D E G A）上：没有半音，跑调也不难听，
 * 音域压在 C4–C5 一个八度里，正好是这个年龄段唱得上去的范围。
 */

import { CHARACTER_MAP } from './characters.js'
import { NOTE_HZ } from '../utils/audio.js'

const PUNCTUATION = new Set([
  '，', '。', '！', '？', '：', '、', '；', '「', '」', '《', '》', '…', '—', ' ', '\n'
])

/** 小舞台的分区。每个分区至少要有一首歌，否则点进去是空页面。 */
export const SONG_THEMES = [
  { id: 'count', name: '数一数', emoji: '🔢' },
  { id: 'nature', name: '大自然', emoji: '🌦️' },
  { id: 'life', name: '好习惯', emoji: '🧼' },
  { id: 'literacy', name: '认字歌', emoji: '🈶' },
  { id: 'manners', name: '有礼貌', emoji: '🤝' },
  { id: 'family', name: '一家人', emoji: '🏠' }
]

export const SONGS = [
  {
    id: 'sg1',
    title: '一二三，爬上山',
    titlePinyin: 'yī èr sān, pá shàng shān',
    theme: 'count',
    emoji: '⛰️',
    palette: ['#ffe6b3', '#c8ebff'],
    summary: '一边爬山一边数数，从一数到十就到家了。',
    tip: '数到几就伸几根手指，边唱边数最容易记住。',
    bpm: 96,
    audio: null,
    lines: [
      {
        text: '一二三，爬上山，',
        pinyin: 'yī èr sān pá shàng shān',
        notes: ['C4', 'D4', 'E4', 'G4', 'G4', 'E4']
      },
      {
        text: '四五六，看白云。',
        pinyin: 'sì wǔ liù kàn bái yún',
        notes: ['D4', 'E4', 'G4', 'E4', 'D4', 'C4']
      },
      {
        text: '七八九，数星星，',
        pinyin: 'qī bā jiǔ shǔ xīng xīng',
        notes: ['E4', 'G4', 'A4', 'C5', 'C5', 'A4']
      },
      {
        text: '数到十，回家门。',
        pinyin: 'shǔ dào shí huí jiā mén',
        notes: ['G4', 'E4', 'D4', 'E4', 'D4', 'C4']
      }
    ]
  },
  {
    id: 'sg2',
    title: '小雨点',
    titlePinyin: 'xiǎo yǔ diǎn',
    theme: 'nature',
    emoji: '🌧️',
    palette: ['#c8ebff', '#d9f6f3'],
    summary: '一颗小雨点掉到花上、田里，最后掉进心里。',
    tip: '唱「沙沙沙」的时候，手指在桌上轻轻点三下。',
    bpm: 100,
    audio: null,
    lines: [
      {
        text: '小雨点，沙沙沙，',
        pinyin: 'xiǎo yǔ diǎn shā shā shā',
        notes: ['G4', 'A4', 'G4', 'E4', 'E4', 'D4']
      },
      {
        text: '打在花上开朵花。',
        pinyin: 'dǎ zài huā shàng kāi duǒ huā',
        notes: ['C4', 'D4', 'E4', 'G4', 'A4', 'G4', 'E4']
      },
      {
        text: '流到田里长青苗，',
        pinyin: 'liú dào tián lǐ zhǎng qīng miáo',
        notes: ['E4', 'G4', 'A4', 'C5', 'A4', 'G4', 'E4']
      },
      {
        text: '走进心里笑哈哈。',
        pinyin: 'zǒu jìn xīn lǐ xiào hā hā',
        notes: ['G4', 'E4', 'D4', 'C4', 'D4', 'E4', 'C4']
      }
    ]
  },
  {
    id: 'sg3',
    title: '洗手歌',
    titlePinyin: 'xǐ shǒu gē',
    theme: 'life',
    emoji: '🧼',
    palette: ['#d9f6f3', '#ffe0c2'],
    summary: '手心手背都要洗到，洗完才好吃饭。',
    tip: '一句歌洗一遍手，唱完四句正好够。',
    bpm: 92,
    audio: null,
    lines: [
      {
        text: '手心手背洗一洗，',
        pinyin: 'shǒu xīn shǒu bèi xǐ yī xǐ',
        notes: ['E4', 'E4', 'G4', 'G4', 'A4', 'G4', 'E4']
      },
      {
        text: '十个指头都要过。',
        pinyin: 'shí gè zhǐ tóu dōu yào guò',
        notes: ['D4', 'D4', 'E4', 'E4', 'G4', 'E4', 'D4']
      },
      {
        text: '水儿流，泡泡多，',
        pinyin: 'shuǐ ér liú pào pào duō',
        notes: ['C5', 'A4', 'G4', 'A4', 'G4', 'E4']
      },
      {
        text: '洗完小手好吃饭。',
        pinyin: 'xǐ wán xiǎo shǒu hǎo chī fàn',
        notes: ['G4', 'E4', 'D4', 'C4', 'E4', 'D4', 'C4']
      }
    ]
  },
  {
    id: 'sg4',
    title: '大树和小鸟',
    titlePinyin: 'dà shù hé xiǎo niǎo',
    theme: 'nature',
    emoji: '🌳',
    palette: ['#e2f7d5', '#ffe6b3'],
    summary: '大树替小鸟挡住风，风越大，小鸟唱得越欢。',
    tip: '唱到「动一动」，可以站起来跟着摆一摆。',
    bpm: 104,
    audio: null,
    lines: [
      {
        text: '大树高，小鸟小，',
        pinyin: 'dà shù gāo xiǎo niǎo xiǎo',
        notes: ['C4', 'E4', 'G4', 'E4', 'D4', 'C4']
      },
      {
        text: '树上有个小小家。',
        pinyin: 'shù shàng yǒu gè xiǎo xiǎo jiā',
        notes: ['E4', 'G4', 'A4', 'G4', 'E4', 'D4', 'C4']
      },
      {
        text: '风来了，动一动，',
        pinyin: 'fēng lái le dòng yī dòng',
        notes: ['G4', 'A4', 'C5', 'A4', 'G4', 'E4']
      },
      {
        text: '小鸟唱歌真快活。',
        pinyin: 'xiǎo niǎo chàng gē zhēn kuài huó',
        notes: ['E4', 'G4', 'E4', 'D4', 'E4', 'D4', 'C4']
      }
    ]
  },
  {
    id: 'sg5',
    title: '认字歌',
    titlePinyin: 'rèn zì gē',
    theme: 'literacy',
    emoji: '🈶',
    palette: ['#ffe0c2', '#e8e0ff'],
    summary: '十个最好写的字排成两行，一天认五个刚刚好。',
    tip: '一个字一个音，唱一遍，再在空中写一遍。',
    bpm: 88,
    audio: null,
    lines: [
      {
        text: '日月水火土，',
        pinyin: 'rì yuè shuǐ huǒ tǔ',
        notes: ['C4', 'D4', 'E4', 'G4', 'A4']
      },
      {
        text: '山石田禾木。',
        pinyin: 'shān shí tián hé mù',
        notes: ['A4', 'G4', 'E4', 'D4', 'C4']
      },
      {
        text: '一笔一画写，',
        pinyin: 'yī bǐ yī huà xiě',
        notes: ['E4', 'E4', 'G4', 'G4', 'A4']
      },
      {
        text: '一天认五个。',
        pinyin: 'yī tiān rèn wǔ gè',
        notes: ['G4', 'E4', 'D4', 'E4', 'C4']
      }
    ]
  },
  {
    id: 'sg6',
    title: '你好和谢谢',
    titlePinyin: 'nǐ hǎo hé xiè xie',
    theme: 'manners',
    emoji: '🤝',
    palette: ['#ffd9e0', '#ffe6b3'],
    summary: '见面、分手、被人帮忙，各有一句该说的话。',
    tip: '唱完就找家里人试一遍，说出口才算学会。',
    bpm: 90,
    audio: null,
    lines: [
      {
        text: '见面说你好，',
        pinyin: 'jiàn miàn shuō nǐ hǎo',
        notes: ['G4', 'E4', 'G4', 'A4', 'C5']
      },
      {
        text: '分手说再见。',
        pinyin: 'fēn shǒu shuō zài jiàn',
        notes: ['A4', 'G4', 'E4', 'D4', 'C4']
      },
      {
        text: '别人帮了我，',
        pinyin: 'bié rén bāng le wǒ',
        notes: ['E4', 'G4', 'A4', 'G4', 'E4']
      },
      {
        text: '我说谢谢你。',
        pinyin: 'wǒ shuō xiè xie nǐ',
        notes: ['D4', 'E4', 'D4', 'C4', 'C4']
      }
    ]
  },
  {
    id: 'sg7',
    title: '四季歌',
    titlePinyin: 'sì jì gē',
    theme: 'nature',
    emoji: '🍂',
    palette: ['#e8e0ff', '#d9f6f3'],
    summary: '一句一个季节，唱完一遍就是一整年。',
    tip: '唱到哪个季节，就想想那时候窗外是什么样子。',
    bpm: 84,
    audio: null,
    lines: [
      {
        text: '春天花儿开，',
        pinyin: 'chūn tiān huā ér kāi',
        notes: ['C4', 'E4', 'G4', 'A4', 'G4']
      },
      {
        text: '夏天太阳高。',
        pinyin: 'xià tiān tài yáng gāo',
        notes: ['E4', 'G4', 'C5', 'A4', 'G4']
      },
      {
        text: '秋天果子甜，',
        pinyin: 'qiū tiān guǒ zi tián',
        notes: ['A4', 'G4', 'E4', 'D4', 'E4']
      },
      {
        text: '冬天下大雪。',
        pinyin: 'dōng tiān xià dà xuě',
        notes: ['G4', 'E4', 'D4', 'C4', 'C4']
      }
    ]
  },
  {
    id: 'sg8',
    title: '一家人',
    titlePinyin: 'yī jiā rén',
    theme: 'family',
    emoji: '🏠',
    palette: ['#ffd9e0', '#e2f7d5'],
    summary: '把家里人一个一个唱一遍，最后大家挤在一句里。',
    tip: '唱到谁，就指一指他坐的地方。',
    bpm: 94,
    audio: null,
    lines: [
      {
        text: '爸爸妈妈和我，',
        pinyin: 'bà ba mā ma hé wǒ',
        notes: ['C4', 'C4', 'D4', 'D4', 'E4', 'G4']
      },
      {
        text: '爷爷奶奶笑呵呵。',
        pinyin: 'yé ye nǎi nai xiào hē hē',
        notes: ['E4', 'E4', 'G4', 'G4', 'A4', 'G4', 'E4']
      },
      {
        text: '哥哥姐姐牵小手，',
        pinyin: 'gē ge jiě jie qiān xiǎo shǒu',
        notes: ['G4', 'A4', 'C5', 'A4', 'G4', 'E4', 'D4']
      },
      {
        text: '一家人，真快活。',
        pinyin: 'yī jiā rén zhēn kuài huó',
        notes: ['E4', 'G4', 'E4', 'D4', 'D4', 'C4']
      }
    ]
  },
  {
    id: 'sg9',
    title: '妈妈的手',
    titlePinyin: 'mā ma de shǒu',
    theme: 'family',
    emoji: '🤲',
    palette: ['#ffe0c2', '#ffd9e0'],
    summary: '一双大手和一双小手，合起来像两朵花。',
    tip: '唱最后一句时，把自己的手放进大人手心里比一比。',
    bpm: 82,
    audio: null,
    lines: [
      {
        text: '妈妈的手真暖和，',
        pinyin: 'mā ma de shǒu zhēn nuǎn huo',
        notes: ['C4', 'D4', 'E4', 'G4', 'A4', 'G4', 'E4']
      },
      {
        text: '摸摸我的头。',
        pinyin: 'mō mō wǒ de tóu',
        notes: ['D4', 'E4', 'D4', 'C4', 'C4']
      },
      {
        text: '我把小手放上去，',
        pinyin: 'wǒ bǎ xiǎo shǒu fàng shàng qù',
        notes: ['E4', 'G4', 'A4', 'C5', 'A4', 'G4', 'E4']
      },
      {
        text: '一大一小两朵花。',
        pinyin: 'yī dà yī xiǎo liǎng duǒ huā',
        notes: ['G4', 'E4', 'D4', 'E4', 'D4', 'C4', 'C4']
      }
    ]
  },
  {
    id: 'sg10',
    title: '小手小脚',
    titlePinyin: 'xiǎo shǒu xiǎo jiǎo',
    theme: 'life',
    emoji: '🧒',
    palette: ['#d9f6f3', '#e2f7d5'],
    summary: '手、脚、眼睛、耳朵，每样各会做一件事。',
    tip: '唱到哪一样，就动一动身上的那一样。',
    bpm: 98,
    audio: null,
    lines: [
      {
        text: '小手会拿笔，',
        pinyin: 'xiǎo shǒu huì ná bǐ',
        notes: ['C4', 'D4', 'E4', 'G4', 'A4']
      },
      {
        text: '小脚会走路。',
        pinyin: 'xiǎo jiǎo huì zǒu lù',
        notes: ['A4', 'G4', 'E4', 'D4', 'C4']
      },
      {
        text: '小眼看星星，',
        pinyin: 'xiǎo yǎn kàn xīng xīng',
        notes: ['E4', 'G4', 'A4', 'C5', 'C5']
      },
      {
        text: '小耳听风雨。',
        pinyin: 'xiǎo ěr tīng fēng yǔ',
        notes: ['A4', 'G4', 'E4', 'D4', 'C4']
      }
    ]
  },
  {
    id: 'sg11',
    title: '从十数到一',
    titlePinyin: 'cóng shí shǔ dào yī',
    theme: 'count',
    emoji: '🔟',
    palette: ['#c8ebff', '#e8e0ff'],
    summary: '从十倒着数回一，一个都不许漏掉。',
    tip: '数一个收一根手指，收完十根正好唱完两句。',
    bpm: 86,
    audio: null,
    lines: [
      {
        text: '十九八七六，',
        pinyin: 'shí jiǔ bā qī liù',
        notes: ['C5', 'A4', 'G4', 'E4', 'D4']
      },
      {
        text: '五四三二一。',
        pinyin: 'wǔ sì sān èr yī',
        notes: ['A4', 'G4', 'E4', 'D4', 'C4']
      },
      {
        text: '一个也不少，',
        pinyin: 'yī gè yě bù shǎo',
        notes: ['C4', 'D4', 'E4', 'G4', 'A4']
      },
      {
        text: '明天再来数。',
        pinyin: 'míng tiān zài lái shǔ',
        notes: ['G4', 'E4', 'D4', 'E4', 'C4']
      }
    ]
  },
  {
    id: 'sg12',
    title: '木字歌',
    titlePinyin: 'mù zì gē',
    theme: 'literacy',
    emoji: '🌲',
    palette: ['#e2f7d5', '#c8ebff'],
    summary: '一个木、两个木、三个木，越叠越多就成了森。',
    tip: '唱一句，用手指在桌上叠一叠：一个木、两个木、三个木。',
    bpm: 90,
    audio: null,
    lines: [
      {
        text: '一个木，是小树，',
        pinyin: 'yī gè mù shì xiǎo shù',
        notes: ['C4', 'D4', 'E4', 'G4', 'A4', 'G4']
      },
      {
        text: '两个木，成树林。',
        pinyin: 'liǎng gè mù chéng shù lín',
        notes: ['E4', 'G4', 'A4', 'C5', 'A4', 'G4']
      },
      {
        text: '三个木，是大森，',
        pinyin: 'sān gè mù shì dà sēn',
        notes: ['G4', 'A4', 'C5', 'A4', 'G4', 'E4']
      },
      {
        text: '木多林大记心里。',
        pinyin: 'mù duō lín dà jì xīn lǐ',
        notes: ['E4', 'G4', 'E4', 'D4', 'E4', 'D4', 'C4']
      }
    ]
  },
  {
    id: 'sg13',
    title: '对不起，没关系',
    titlePinyin: 'duì bù qǐ, méi guān xì',
    theme: 'manners',
    emoji: '🫱',
    palette: ['#ffe6b3', '#ffd9e0'],
    summary: '做错了要说一句，被说了也要回一句，两句配成一对。',
    tip: '前两句你唱，后两句请家里人唱，唱成一问一答。',
    bpm: 88,
    audio: null,
    lines: [
      {
        text: '不小心，做错了，',
        pinyin: 'bù xiǎo xīn zuò cuò le',
        notes: ['G4', 'A4', 'G4', 'E4', 'D4', 'C4']
      },
      {
        text: '我说一声对不起。',
        pinyin: 'wǒ shuō yī shēng duì bù qǐ',
        notes: ['C4', 'D4', 'E4', 'G4', 'A4', 'G4', 'E4']
      },
      {
        text: '你笑一笑点点头，',
        pinyin: 'nǐ xiào yī xiào diǎn diǎn tóu',
        notes: ['E4', 'G4', 'A4', 'C5', 'A4', 'G4', 'E4']
      },
      {
        text: '说声没关系。',
        pinyin: 'shuō shēng méi guān xì',
        notes: ['G4', 'E4', 'D4', 'C4', 'C4']
      }
    ]
  }
]

export const SONG_MAP = new Map(SONGS.map((s) => [s.id, s]))

export function getSong(id) {
  return SONG_MAP.get(id) || null
}

/** 一首歌里出现的所有汉字（去重、保持出现顺序）。 */
export function charsInSong(song) {
  const seen = []
  const set = new Set()
  for (const line of song.lines) {
    for (const ch of line.text) {
      if (PUNCTUATION.has(ch) || set.has(ch)) continue
      set.add(ch)
      seen.push(ch)
    }
  }
  return seen
}

/**
 * 一句歌词拆成「字 + 拼音 + 音名」，逐字高亮和逐音播放共用这一份。
 *
 * `at` 是这个字在 `notes` 里的下标，标点是 -1。界面必须按 `at` 判断「唱到我了」
 * 而不是按它在这一行里的位置——逗号不占音符，按位置数会整句错开一格。
 */
export function syllablesOfSongLine(line) {
  const pinyin = line.pinyin.trim().split(/\s+/)
  let index = 0
  return [...line.text].map((ch) => {
    if (PUNCTUATION.has(ch)) return { char: ch, pinyin: '', note: '', at: -1, punct: true }
    const at = index++
    return { char: ch, pinyin: pinyin[at] ?? '', note: line.notes[at] ?? '', at, punct: false }
  })
}

/** 整首歌的音名序列，播放时一次交给 `playMelody()`。 */
export function melodyOfSong(song) {
  return song.lines.flatMap((line) => line.notes)
}

const PITCH_LO = Math.log2(Math.min(...Object.values(NOTE_HZ)))
const PITCH_HI = Math.log2(Math.max(...Object.values(NOTE_HZ)))

/**
 * 音名在整套音域里的相对高度：最低音 0，最高音 1，不认识的音名给中间值。
 *
 * ROUND9_H1 的逐字动画拿它当抬升幅度。听不出音高的孩子（或者家长把音效关了的
 * 场合）也能从字跳得高还是低看出旋律往哪走——高亮从「亮一下」变成了一条看得见
 * 的旋律线。取对数是因为频率是指数排列的，直接按 Hz 插值会把高音区压扁。
 */
export function pitchOfNote(note) {
  const hz = NOTE_HZ[note]
  if (!hz) return 0.5
  return (Math.log2(hz) - PITCH_LO) / (PITCH_HI - PITCH_LO)
}

/**
 * 内容自检：
 *   1. 歌词里的每个字都在字表里（孩子唱到的字都是学过的）；
 *   2. 每句的拼音音节数、音名个数都要和这句的汉字数对得上——
 *      错一个，逐字高亮就会整句错位一格，是肉眼最难发现的那种回归；
 *   3. 音名必须在 NOTE_HZ 里，否则那个字唱到时是一段静音。
 */
export function verifySongCoverage() {
  const problems = []
  for (const song of SONGS) {
    const unknown = charsInSong(song).filter((ch) => !CHARACTER_MAP.has(ch))
    const misaligned = []
    const badNotes = []
    song.lines.forEach((line, i) => {
      const chars = [...line.text].filter((ch) => !PUNCTUATION.has(ch)).length
      const syllables = line.pinyin.trim().split(/\s+/).filter(Boolean).length
      if (chars !== syllables || chars !== line.notes.length) {
        misaligned.push(`第 ${i + 1} 句 ${chars} 字 / ${syllables} 音 / ${line.notes.length} 个音名`)
      }
      badNotes.push(...line.notes.filter((note) => !(note in NOTE_HZ)))
    })
    if (unknown.length || misaligned.length || badNotes.length) {
      problems.push({ song: song.title, unknown, misaligned, badNotes: [...new Set(badNotes)] })
    }
  }
  return problems
}
