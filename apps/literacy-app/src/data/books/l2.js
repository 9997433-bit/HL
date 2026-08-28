/**
 * 第 2 级扩展绘本 —— 由 scripts/gen-books.mjs 生成，请勿手改。
 * 正文改动请编辑 scripts/data/book-seed-*.mjs 后重新生成。
 */

export const LEVEL_2_BOOKS = [
  {
    id: 'bx21',
    title: '小猫找妈妈',
    pinyin: 'xiǎo māo zhǎo mā ma',
    level: 2,
    levelName: '第 2 级 · 大家都来帮一把',
    cover: '🐱',
    palette: ['#e8e0ff', '#fff1cf'],
    summary: '小猫找不到妈妈，鸟在天上看，鱼在水里找，老牛说：她在山下。',
    newChars: ['猫', '找', '到', '妈', '哭', '地', '方', '鸟'],
    pages: [
      {
        emoji: '🐱', text: '小猫找不到妈妈。', p: 'xiǎo māo zhǎo bù dào mā ma.',
        sceneBg: 'field',
        sceneAlt: '小猫找不到妈妈',
        scene: [
          { e: '🌳', x: 78, y: 56, s: 1.5 },
          { e: '🐱', x: 44, y: 74, s: 1.6, m: 'float' },
          { e: '🌿', x: 20, y: 86, s: 1.1, m: 'sway' }
        ]
      },
      {
        emoji: '😿', text: '小猫哭了：妈妈在什么地方？', p: 'xiǎo māo kū le: mā ma zài shén me dì fāng?',
        sceneBg: 'field',
        sceneAlt: '小猫哭了',
        scene: [
          { e: '🌳', x: 22, y: 58, s: 1.4 },
          { e: '😿', x: 52, y: 70, s: 1.8, m: 'float' },
          { e: '🪨', x: 80, y: 82, s: 1.1 },
          { e: '🌿', x: 30, y: 88, s: 1, m: 'sway' }
        ]
      },
      {
        emoji: '🐦', text: '小鸟说：我在天上看一看。', p: 'xiǎo niǎo shuō: wǒ zài tiān shàng kàn yī kàn.',
        sceneBg: 'sky',
        sceneAlt: '小鸟在天上看',
        scene: [
          { e: '☁️', x: 26, y: 22, s: 1.1, m: 'drift' },
          { e: '🐦', x: 58, y: 34, s: 1.4, m: 'float' },
          { e: '🌳', x: 82, y: 66, s: 1.3 },
          { e: '🐱', x: 34, y: 82, s: 1.2 }
        ]
      },
      {
        emoji: '🐟', text: '小鱼说：我在水里找一找。', p: 'xiǎo yú shuō: wǒ zài shuǐ lǐ zhǎo yī zhǎo.',
        sceneBg: 'water',
        sceneAlt: '小鱼在水里找',
        scene: [
          { e: '🐟', x: 56, y: 62, s: 1.5, m: 'sway' },
          { e: '🫧', x: 72, y: 46, s: 0.7, m: 'float' },
          { e: '🌊', x: 24, y: 84, s: 1.3, m: 'drift' },
          { e: '🐱', x: 30, y: 66, s: 1.2 }
        ]
      },
      {
        emoji: '🐄', text: '老牛说：我看到你妈妈在山下。', p: 'lǎo niú shuō: wǒ kàn dào nǐ mā ma zài shān xià.',
        sceneBg: 'field',
        sceneAlt: '老牛说妈妈在山下',
        scene: [
          { e: '⛰️', x: 22, y: 44, s: 1.6 },
          { e: '🐄', x: 62, y: 70, s: 1.7 },
          { e: '🐱', x: 30, y: 80, s: 1.2 },
          { e: '🌾', x: 84, y: 86, s: 1.1, m: 'sway' }
        ]
      },
      {
        emoji: '🐈', text: '小猫走到山下，妈妈就在树下。', p: 'xiǎo māo zǒu dào shān xià, mā ma jiù zài shù xià.',
        sceneBg: 'field',
        sceneAlt: '小猫走到山下，妈妈在树下',
        scene: [
          { e: '⛰️', x: 20, y: 40, s: 1.5 },
          { e: '🌳', x: 68, y: 56, s: 1.7 },
          { e: '🐈', x: 70, y: 78, s: 1.4 },
          { e: '🐱', x: 40, y: 84, s: 1.2, m: 'drift' }
        ]
      },
      {
        emoji: '😻', text: '小猫说：谢谢大家！', p: 'xiǎo māo shuō: xiè xiè dà jiā!',
        sceneBg: 'field',
        sceneAlt: '小猫说谢谢大家',
        scene: [
          { e: '❤️', x: 50, y: 30, s: 1, m: 'float' },
          { e: '🐦', x: 24, y: 44, s: 0.9, m: 'float' },
          { e: '🐟', x: 78, y: 60, s: 0.9, m: 'sway' },
          { e: '🐄', x: 22, y: 76, s: 1.2 },
          { e: '🐱', x: 54, y: 82, s: 1.4, m: 'float' }
        ]
      }
    ]
  },
  {
    id: 'bx22',
    title: '帽飞走了',
    pinyin: 'mào fēi zǒu le',
    level: 2,
    levelName: '第 2 级 · 会爬树的朋友',
    cover: '🧢',
    palette: ['#ffe0c2', '#e6f5c9'],
    summary: '风一来，新帽飞到树上。小猴说：别急，我会爬树。',
    newChars: ['新', '帽', '风', '飞', '走', '追', '到', '树'],
    pages: [
      {
        emoji: '🧢', text: '我有一个新帽。', p: 'wǒ yǒu yī gè xīn mào.',
        sceneBg: 'field',
        sceneAlt: '我有一个新帽',
        scene: [
          { e: '🧢', x: 52, y: 48, s: 1.6, m: 'float' },
          { e: '🧒', x: 44, y: 76, s: 1.6 },
          { e: '🌳', x: 80, y: 66, s: 1.3 }
        ]
      },
      {
        emoji: '💨', text: '风来了，帽飞走了。', p: 'fēng lái le, mào fēi zǒu le.',
        sceneBg: 'sky',
        sceneAlt: '风来了，帽飞走了',
        scene: [
          { e: '💨', x: 26, y: 34, s: 1.3, m: 'drift' },
          { e: '🧢', x: 62, y: 40, s: 1.3, m: 'drift' },
          { e: '🌳', x: 82, y: 70, s: 1.3, m: 'sway' },
          { e: '🧒', x: 34, y: 84, s: 1.4 }
        ]
      },
      {
        emoji: '🏃', text: '我追帽，帽飞到树上。', p: 'wǒ zhuī mào, mào fēi dào shù shàng.',
        sceneBg: 'field',
        sceneAlt: '我追帽，帽飞到树上',
        scene: [
          { e: '🧢', x: 66, y: 44, s: 1.1, m: 'float' },
          { e: '🌳', x: 70, y: 64, s: 1.9 },
          { e: '🏃', x: 30, y: 80, s: 1.6, m: 'drift' },
          { e: '🌿', x: 16, y: 88, s: 1, m: 'sway' }
        ]
      },
      {
        emoji: '🐒', text: '小猴说：别急，我会爬树。', p: 'xiǎo hóu shuō: bié jí, wǒ huì pá shù.',
        sceneBg: 'field',
        sceneAlt: '小猴说他会爬树',
        scene: [
          { e: '🧢', x: 74, y: 40, s: 1, m: 'float' },
          { e: '🌳', x: 74, y: 62, s: 1.7 },
          { e: '🐒', x: 46, y: 70, s: 1.5, m: 'float' },
          { e: '🧒', x: 22, y: 82, s: 1.3 }
        ]
      },
      {
        emoji: '🌳', text: '小猴上树，把帽拿下来。', p: 'xiǎo hóu shàng shù, bǎ mào ná xià lái.',
        sceneBg: 'field',
        sceneAlt: '小猴上树，把帽拿下来',
        scene: [
          { e: '🐒', x: 62, y: 46, s: 1.4, m: 'float' },
          { e: '🧢', x: 74, y: 56, s: 1, m: 'float' },
          { e: '🌳', x: 66, y: 68, s: 1.8 },
          { e: '🧒', x: 26, y: 82, s: 1.4 }
        ]
      },
      {
        emoji: '🙏', text: '我说：谢谢你！', p: 'wǒ shuō: xiè xiè nǐ!',
        sceneBg: 'field',
        sceneAlt: '我说谢谢你',
        scene: [
          { e: '🙏', x: 40, y: 62, s: 1.5, m: 'float' },
          { e: '🐒', x: 72, y: 74, s: 1.3 },
          { e: '🧒', x: 30, y: 82, s: 1.4 },
          { e: '🌳', x: 84, y: 56, s: 1.2 }
        ]
      },
      {
        emoji: '😄', text: '小猴说：不用谢，我们是朋友。', p: 'xiǎo hóu shuō: bù yòng xiè, wǒ men shì péng you.',
        sceneBg: 'field',
        sceneAlt: '小猴说我们是朋友',
        scene: [
          { e: '❤️', x: 50, y: 34, s: 1, m: 'float' },
          { e: '🧢', x: 32, y: 52, s: 0.9, m: 'float' },
          { e: '🐒', x: 66, y: 76, s: 1.4, m: 'float' },
          { e: '🧒', x: 36, y: 80, s: 1.4 },
          { e: '🌳', x: 86, y: 62, s: 1.2 }
        ]
      }
    ]
  },
  {
    id: 'bx23',
    title: '小狗和骨头',
    pinyin: 'xiǎo gǒu hé gǔ tóu',
    level: 2,
    levelName: '第 2 级 · 水里的那只狗',
    cover: '🐶',
    palette: ['#c8ebff', '#e8e0ff'],
    summary: '桥上的小狗看到水里也有一只狗，一开口，骨头就没了。',
    newChars: ['狗', '根', '骨', '头', '拿', '走', '过', '座'],
    pages: [
      {
        emoji: '🐶', text: '小狗有一根骨头。', p: 'xiǎo gǒu yǒu yī gēn gǔ tóu.',
        sceneBg: 'field',
        sceneAlt: '小狗有一根骨头',
        scene: [
          { e: '🐶', x: 46, y: 70, s: 1.7 },
          { e: '🦴', x: 70, y: 82, s: 1.2, m: 'float' },
          { e: '🌿', x: 20, y: 86, s: 1.1, m: 'sway' }
        ]
      },
      {
        emoji: '🌉', text: '小狗拿骨头走过一座桥。', p: 'xiǎo gǒu ná gǔ tóu zǒu guò yī zuò qiáo.',
        sceneBg: 'water',
        sceneAlt: '小狗拿骨头走过桥',
        scene: [
          { e: '🌉', x: 52, y: 54, s: 1.8 },
          { e: '🐶', x: 44, y: 70, s: 1.3, m: 'drift' },
          { e: '🦴', x: 58, y: 74, s: 0.8 },
          { e: '🌊', x: 26, y: 88, s: 1.2, m: 'drift' }
        ]
      },
      {
        emoji: '💧', text: '水里也有一只狗，那只狗也有骨头。', p: 'shuǐ lǐ yě yǒu yī zhī gǒu, nà zhī gǒu yě yǒu gǔ tóu.',
        sceneBg: 'water',
        sceneAlt: '水里也有一只狗',
        scene: [
          { e: '🐶', x: 46, y: 52, s: 1.4 },
          { e: '🦴', x: 60, y: 58, s: 0.8 },
          { e: '🐕', x: 46, y: 78, s: 1.3, m: 'sway' },
          { e: '🌊', x: 78, y: 88, s: 1.2, m: 'drift' }
        ]
      },
      {
        emoji: '😠', text: '小狗一开口，骨头没了。', p: 'xiǎo gǒu yī kāi kǒu, gǔ tóu méi le.',
        sceneBg: 'water',
        sceneAlt: '小狗一开口，骨头没了',
        scene: [
          { e: '🐶', x: 42, y: 54, s: 1.5 },
          { e: '🦴', x: 62, y: 72, s: 0.9, m: 'float' },
          { e: '🫧', x: 76, y: 60, s: 0.7, m: 'float' },
          { e: '🌊', x: 30, y: 88, s: 1.2, m: 'drift' }
        ]
      },
      {
        emoji: '😢', text: '小狗看水里，那只狗也没了。', p: 'xiǎo gǒu kàn shuǐ lǐ, nà zhī gǒu yě méi le.',
        sceneBg: 'water',
        sceneAlt: '小狗看水里，那只狗也没了',
        scene: [
          { e: '😢', x: 44, y: 50, s: 1.5, m: 'float' },
          { e: '🌊', x: 52, y: 76, s: 1.4, m: 'sway' },
          { e: '🫧', x: 74, y: 68, s: 0.7, m: 'float' },
          { e: '🌉', x: 22, y: 40, s: 1.1 }
        ]
      },
      {
        emoji: '🐕', text: '妈妈说：水里的就是你，不是别的狗。', p: 'mā ma shuō: shuǐ lǐ de jiù shì nǐ, bù shì bié de gǒu.',
        sceneBg: 'water',
        sceneAlt: '妈妈说水里的就是你',
        scene: [
          { e: '🌉', x: 24, y: 38, s: 1.1 },
          { e: '🐕', x: 66, y: 60, s: 1.6 },
          { e: '🐶', x: 40, y: 68, s: 1.3 },
          { e: '🌊', x: 54, y: 88, s: 1.3, m: 'drift' }
        ]
      },
      {
        emoji: '💡', text: '小狗明白了：我有的，不能扔。', p: 'xiǎo gǒu míng bai le: wǒ yǒu de, bù néng rēng.',
        sceneBg: 'field',
        sceneAlt: '小狗明白了',
        scene: [
          { e: '💡', x: 66, y: 44, s: 1.2, m: 'float' },
          { e: '🐶', x: 44, y: 70, s: 1.6 },
          { e: '🦴', x: 72, y: 82, s: 1.1 },
          { e: '🌿', x: 20, y: 88, s: 1, m: 'sway' }
        ]
      }
    ]
  },
  {
    id: 'bx24',
    title: '小鸭下水',
    pinyin: 'xiǎo yā xià shuǐ',
    level: 2,
    levelName: '第 2 级 · 怕水的头一天',
    cover: '🦆',
    palette: ['#ffd6d6', '#d9f6f3'],
    summary: '小鸭站在岸上不敢下水，妈妈说：下来，水不深。',
    newChars: ['鸭', '头', '怕', '站', '岸', '走', '妈', '深'],
    pages: [
      {
        emoji: '🦆', text: '小鸭头一天下水。', p: 'xiǎo yā tóu yī tiān xià shuǐ.',
        sceneBg: 'water',
        sceneAlt: '小鸭头一天下水',
        scene: [
          { e: '🦆', x: 50, y: 62, s: 1.7, m: 'sway' },
          { e: '🌊', x: 26, y: 84, s: 1.3, m: 'drift' },
          { e: '🌿', x: 80, y: 76, s: 1.1, m: 'sway' }
        ]
      },
      {
        emoji: '😰', text: '小鸭很怕，站在岸上不走。', p: 'xiǎo yā hěn pà, zhàn zài àn shàng bù zǒu.',
        sceneBg: 'water',
        sceneAlt: '小鸭站在岸上不走',
        scene: [
          { e: '🌾', x: 24, y: 66, s: 1.2, m: 'sway' },
          { e: '🦆', x: 34, y: 76, s: 1.4 },
          { e: '🪨', x: 20, y: 88, s: 1.1 },
          { e: '🌊', x: 70, y: 86, s: 1.3, m: 'drift' }
        ]
      },
      {
        emoji: '🐤', text: '鸭妈妈说：下来，水不深。', p: 'yā mā ma shuō: xià lái, shuǐ bù shēn.',
        sceneBg: 'water',
        sceneAlt: '鸭妈妈说水不深',
        scene: [
          { e: '🦆', x: 30, y: 68, s: 1.2 },
          { e: '🐤', x: 62, y: 72, s: 1.4, m: 'sway' },
          { e: '🌊', x: 78, y: 88, s: 1.2, m: 'drift' },
          { e: '🌿', x: 16, y: 84, s: 1, m: 'sway' }
        ]
      },
      {
        emoji: '💧', text: '小鸭一脚下水，水到腿上。', p: 'xiǎo yā yī jiǎo xià shuǐ, shuǐ dào tuǐ shàng.',
        sceneBg: 'water',
        sceneAlt: '小鸭一脚下水',
        scene: [
          { e: '🐤', x: 46, y: 62, s: 1.5, m: 'float' },
          { e: '🫧', x: 64, y: 72, s: 0.7, m: 'float' },
          { e: '🌊', x: 46, y: 84, s: 1.4, m: 'sway' },
          { e: '🌿', x: 82, y: 78, s: 1, m: 'sway' }
        ]
      },
      {
        emoji: '🌊', text: '小鸭会了！他在水里前后走。', p: 'xiǎo yā huì le! tā zài shuǐ lǐ qián hòu zǒu.',
        sceneBg: 'water',
        sceneAlt: '小鸭在水里前后走',
        scene: [
          { e: '🐤', x: 38, y: 66, s: 1.4, m: 'drift' },
          { e: '🌊', x: 22, y: 82, s: 1.2, m: 'drift' },
          { e: '🌊', x: 70, y: 88, s: 1.3, m: 'drift' },
          { e: '🫧', x: 78, y: 62, s: 0.7, m: 'float' }
        ]
      },
      {
        emoji: '🐟', text: '水里有鱼，鱼从他脚下过。', p: 'shuǐ lǐ yǒu yú, yú cóng tā jiǎo xià guò.',
        sceneBg: 'water',
        sceneAlt: '水里有鱼从他脚下过',
        scene: [
          { e: '🐤', x: 44, y: 58, s: 1.3, m: 'sway' },
          { e: '🐟', x: 62, y: 76, s: 1, m: 'sway' },
          { e: '🐟', x: 26, y: 82, s: 0.9, m: 'sway' },
          { e: '🫧', x: 80, y: 66, s: 0.7, m: 'float' }
        ]
      },
      {
        emoji: '😄', text: '小鸭说：水里真好玩！', p: 'xiǎo yā shuō: shuǐ lǐ zhēn hǎo wán!',
        sceneBg: 'water',
        sceneAlt: '小鸭说水里真好玩',
        scene: [
          { e: '☀️', x: 80, y: 20, s: 1.1, m: 'float' },
          { e: '🐤', x: 44, y: 64, s: 1.5, m: 'float' },
          { e: '🦆', x: 70, y: 74, s: 1.2, m: 'sway' },
          { e: '🌊', x: 30, y: 88, s: 1.3, m: 'drift' }
        ]
      }
    ]
  },
  {
    id: 'bx25',
    title: '一个大瓜',
    pinyin: 'yī gè dà guā',
    level: 2,
    levelName: '第 2 级 · 三个人一同拿',
    cover: '🍉',
    palette: ['#e6f5c9', '#ffe6b3'],
    summary: '一个人拿不走的大瓜，哥哥姐姐一来就拿回家了。',
    newChars: ['田', '瓜', '拿', '走', '哥', '同', '姐', '妈'],
    pages: [
      {
        emoji: '🍉', text: '田里有一个大瓜。', p: 'tián lǐ yǒu yī gè dà guā.',
        sceneBg: 'field',
        sceneAlt: '田里有一个大瓜',
        scene: [
          { e: '☀️', x: 82, y: 20, s: 1, m: 'float' },
          { e: '🍉', x: 50, y: 70, s: 2 },
          { e: '🌾', x: 22, y: 82, s: 1.2, m: 'sway' },
          { e: '🌿', x: 78, y: 88, s: 1, m: 'sway' }
        ]
      },
      {
        emoji: '🙋', text: '我一个人拿不走。', p: 'wǒ yī gè rén ná bù zǒu.',
        sceneBg: 'field',
        sceneAlt: '我一个人拿不走',
        scene: [
          { e: '🍉', x: 58, y: 72, s: 1.9 },
          { e: '🧒', x: 28, y: 78, s: 1.5 },
          { e: '🌾', x: 84, y: 86, s: 1.1, m: 'sway' }
        ]
      },
      {
        emoji: '👦', text: '哥哥来了，我们一同拿。', p: 'gē ge lái le, wǒ men yī tóng ná.',
        sceneBg: 'field',
        sceneAlt: '哥哥来了，我们一同拿',
        scene: [
          { e: '🍉', x: 52, y: 70, s: 1.8 },
          { e: '👦', x: 76, y: 76, s: 1.5 },
          { e: '🧒', x: 26, y: 80, s: 1.4 },
          { e: '🌾', x: 90, y: 88, s: 1, m: 'sway' }
        ]
      },
      {
        emoji: '👧', text: '姐姐也来了，三个人拿走了大瓜。', p: 'jiě jie yě lái le, sān gè rén ná zǒu le dà guā.',
        sceneBg: 'field',
        sceneAlt: '姐姐也来了，三个人拿大瓜',
        scene: [
          { e: '🍉', x: 50, y: 66, s: 1.6 },
          { e: '👧', x: 78, y: 74, s: 1.4 },
          { e: '👦', x: 64, y: 82, s: 1.3 },
          { e: '🧒', x: 24, y: 82, s: 1.3 }
        ]
      },
      {
        emoji: '🔪', text: '妈妈把瓜切开，瓜里是红的。', p: 'mā ma bǎ guā qiē kāi, guā lǐ shì hóng de.',
        sceneBg: 'room',
        sceneAlt: '妈妈把瓜切开，瓜里是红的',
        scene: [
          { e: '🔪', x: 72, y: 52, s: 1.2, m: 'sway' },
          { e: '🍉', x: 46, y: 64, s: 1.7 },
          { e: '👩', x: 78, y: 78, s: 1.4 },
          { e: '🍽️', x: 26, y: 84, s: 1.2 }
        ]
      },
      {
        emoji: '😋', text: '一人一片，又甜又凉。', p: 'yī rén yī piàn, yòu tián yòu liáng.',
        sceneBg: 'room',
        sceneAlt: '一人一片，又甜又凉',
        scene: [
          { e: '🍉', x: 34, y: 60, s: 1.2, m: 'float' },
          { e: '🍉', x: 64, y: 66, s: 1.1, m: 'float' },
          { e: '😋', x: 48, y: 82, s: 1.6, m: 'float' },
          { e: '🍽️', x: 82, y: 88, s: 1.1 }
        ]
      },
      {
        emoji: '👏', text: '爸爸说：大家一同做，就不重了。', p: 'bà ba shuō: dà jiā yī tóng zuò, jiù bù zhòng le.',
        sceneBg: 'room',
        sceneAlt: '大家一同做就不重了',
        scene: [
          { e: '👏', x: 50, y: 34, s: 1.1, m: 'float' },
          { e: '👨', x: 24, y: 70, s: 1.4 },
          { e: '👩', x: 76, y: 72, s: 1.4 },
          { e: '🧒', x: 40, y: 84, s: 1.3 },
          { e: '🍉', x: 62, y: 88, s: 1 }
        ]
      }
    ]
  },
  {
    id: 'bx26',
    title: '我帮妈妈买菜',
    pinyin: 'wǒ bāng mā ma mǎi cài',
    level: 2,
    levelName: '第 2 级 · 在市里数一数',
    cover: '🧺',
    palette: ['#fff1cf', '#ffd6d6'],
    summary: '买菜、买豆、数十个蛋，回家路上妈妈说：你会帮忙了。',
    newChars: ['今', '妈', '市', '买', '菜', '豆', '蛋', '数'],
    pages: [
      {
        emoji: '🧺', text: '今天，我和妈妈去市里买菜。', p: 'jīn tiān, wǒ hé mā ma qù shì lǐ mǎi cài.',
        sceneBg: 'sky',
        sceneAlt: '我和妈妈去市里买菜',
        scene: [
          { e: '☁️', x: 24, y: 22, s: 1.1, m: 'drift' },
          { e: '🏠', x: 78, y: 58, s: 1.4 },
          { e: '👩', x: 54, y: 76, s: 1.5 },
          { e: '🧒', x: 30, y: 82, s: 1.3 },
          { e: '🧺', x: 70, y: 88, s: 1 }
        ]
      },
      {
        emoji: '🥬', text: '我们买了菜，也买了豆。', p: 'wǒ men mǎi le cài, yě mǎi le dòu.',
        sceneBg: 'room',
        sceneAlt: '我们买了菜，也买了豆',
        scene: [
          { e: '🥬', x: 42, y: 62, s: 1.6, m: 'float' },
          { e: '🫘', x: 68, y: 74, s: 0.9 },
          { e: '🧺', x: 44, y: 86, s: 1.4 },
          { e: '🧒', x: 78, y: 84, s: 1.2 }
        ]
      },
      {
        emoji: '🥚', text: '妈妈说：还要十个蛋。', p: 'mā ma shuō: hái yào shí gè dàn.',
        sceneBg: 'room',
        sceneAlt: '妈妈说还要十个蛋',
        scene: [
          { e: '🥚', x: 44, y: 58, s: 1.1, m: 'float' },
          { e: '🥚', x: 58, y: 66, s: 1 },
          { e: '👩', x: 76, y: 76, s: 1.4 },
          { e: '🧺', x: 30, y: 84, s: 1.3 }
        ]
      },
      {
        emoji: '🧒', text: '我数一数：一，二，三……十个。', p: 'wǒ shǔ yī shǔ: yī, èr, sān…… shí gè.',
        sceneBg: 'room',
        sceneAlt: '我数一数，一共十个',
        scene: [
          { e: '🔢', x: 74, y: 44, s: 1.1, m: 'float' },
          { e: '🥚', x: 40, y: 62, s: 1 },
          { e: '🧒', x: 52, y: 80, s: 1.5 },
          { e: '🧺', x: 24, y: 86, s: 1.2 }
        ]
      },
      {
        emoji: '💰', text: '妈妈把钱给店里的人。', p: 'mā ma bǎ qián gěi diàn lǐ de rén.',
        sceneBg: 'room',
        sceneAlt: '妈妈把钱给店里的人',
        scene: [
          { e: '💰', x: 50, y: 54, s: 1.3, m: 'float' },
          { e: '👩', x: 30, y: 74, s: 1.4 },
          { e: '🧑', x: 74, y: 74, s: 1.4 },
          { e: '🧺', x: 50, y: 88, s: 1.1 }
        ]
      },
      {
        emoji: '🛍️', text: '我拿一个小袋，妈妈拿大袋。', p: 'wǒ ná yī gè xiǎo dài, mā ma ná dà dài.',
        sceneBg: 'room',
        sceneAlt: '我拿小袋，妈妈拿大袋',
        scene: [
          { e: '🛍️', x: 68, y: 62, s: 1.5, m: 'sway' },
          { e: '👩', x: 76, y: 78, s: 1.4 },
          { e: '🛍️', x: 30, y: 70, s: 1, m: 'sway' },
          { e: '🧒', x: 26, y: 84, s: 1.3 }
        ]
      },
      {
        emoji: '😄', text: '回家的路上，妈妈说：你会帮忙了！', p: 'huí jiā de lù shàng, mā ma shuō: nǐ huì bāng máng le!',
        sceneBg: 'sky',
        sceneAlt: '回家的路上，妈妈说我会帮忙了',
        scene: [
          { e: '☁️', x: 78, y: 24, s: 1.1, m: 'drift' },
          { e: '🏠', x: 24, y: 60, s: 1.5 },
          { e: '👩', x: 60, y: 76, s: 1.5 },
          { e: '🧒', x: 42, y: 84, s: 1.3 },
          { e: '🛍️', x: 80, y: 84, s: 1 }
        ]
      }
    ]
  },
  {
    id: 'bx27',
    title: '小马过河',
    pinyin: 'xiǎo mǎ guò hé',
    level: 2,
    levelName: '第 2 级 · 深浅要去试',
    cover: '🐴',
    palette: ['#c8ebff', '#e6f5c9'],
    summary: '小鼠说水深，老牛说水浅。妈妈说：你去试一试。',
    newChars: ['马', '过', '河', '鼠', '深', '老', '牛', '浅'],
    pages: [
      { emoji: '🐴', text: '小马要过河。', p: 'xiǎo mǎ yào guò hé.' },
      { emoji: '🐿️', text: '小鼠说：水很深，别过！', p: 'xiǎo shǔ shuō: shuǐ hěn shēn, bié guò!' },
      { emoji: '🐄', text: '老牛说：水很浅，能过。', p: 'lǎo niú shuō: shuǐ hěn qiǎn, néng guò.' },
      { emoji: '🤔', text: '小马不明白：为什么一个说深，一个说浅？', p: 'xiǎo mǎ bù míng bai: wèi shén me yī gè shuō shēn, yī gè shuō qiǎn?' },
      { emoji: '🐎', text: '妈妈说：你去试一试。', p: 'mā ma shuō: nǐ qù shì yī shì.' },
      { emoji: '💧', text: '小马下了水，水到他的腿。', p: 'xiǎo mǎ xià le shuǐ, shuǐ dào tā de tuǐ.' },
      { emoji: '😄', text: '小马说：水不深也不浅，我能过！', p: 'xiǎo mǎ shuō: shuǐ bù shēn yě bù qiǎn, wǒ néng guò!' }
    ]
  },
  {
    id: 'bx28',
    title: '风来了',
    pinyin: 'fēng lái le',
    level: 2,
    levelName: '第 2 级 · 风走过的地方',
    cover: '💨',
    palette: ['#ffe0e6', '#fff1cf'],
    summary: '叶飞了，云走了，帽也飞了。关上窗，风就停了。',
    newChars: ['风', '树', '叶', '飞', '地', '纸', '片', '走'],
    pages: [
      { emoji: '💨', text: '风来了。', p: 'fēng lái le.' },
      { emoji: '🍃', text: '树上的叶飞了一地。', p: 'shù shàng de yè fēi le yī dì.' },
      { emoji: '🎏', text: '我的纸片也飞走了。', p: 'wǒ de zhǐ piàn yě fēi zǒu le.' },
      { emoji: '☁️', text: '天上的云走很快。', p: 'tiān shàng de yún zǒu hěn kuài.' },
      { emoji: '🌀', text: '风大了，我的帽也飞了。', p: 'fēng dà le, wǒ de mào yě fēi le.' },
      { emoji: '🏠', text: '我回到屋里，关上窗。', p: 'wǒ huí dào wū lǐ, guān shàng chuāng.' },
      { emoji: '🌤️', text: '风停了，天又亮了。', p: 'fēng tíng le, tiān yòu liàng le.' }
    ]
  },
  {
    id: 'bx29',
    title: '雪天的早上',
    pinyin: 'xuě tiān de zǎo shang',
    level: 2,
    levelName: '第 2 级 · 白白的一天',
    cover: '❄️',
    palette: ['#d9f6f3', '#ffe0c2'],
    summary: '开门就是雪，和弟弟做了一个雪人，回屋喝一杯热茶。',
    newChars: ['早', '开', '门', '地', '雪', '树', '白', '屋'],
    pages: [
      { emoji: '❄️', text: '早上开门，地上都是雪。', p: 'zǎo shang kāi mén, dì shàng dōu shì xuě.' },
      { emoji: '⬜', text: '树是白的，屋顶也是白的。', p: 'shù shì bái de, wū dǐng yě shì bái de.' },
      { emoji: '🧤', text: '妈妈给我一顶帽，一身厚衣。', p: 'mā ma gěi wǒ yī dǐng mào, yī shēn hòu yī.' },
      { emoji: '⛄', text: '我和弟弟做了一个雪人。', p: 'wǒ hé dì di zuò le yī gè xuě rén.' },
      { emoji: '👃', text: '雪人有眼，也有鼻。', p: 'xuě rén yǒu yǎn, yě yǒu bí.' },
      { emoji: '🌨️', text: '雪还在下，我们都笑了。', p: 'xuě hái zài xià, wǒ men dōu xiào le.' },
      { emoji: '🍵', text: '回到屋里，一杯热茶真暖。', p: 'huí dào wū lǐ, yī bēi rè chá zhēn nuǎn.' }
    ]
  },
  {
    id: 'bx30',
    title: '小兔的菜园',
    pinyin: 'xiǎo tù de cài yuán',
    level: 2,
    levelName: '第 2 级 · 种下去才有',
    cover: '🐰',
    palette: ['#e8e0ff', '#c8ebff'],
    summary: '春天种菜，天天浇水，一个月后菜长大了，送给老牛。',
    newChars: ['兔', '菜', '园', '春', '地', '种', '每', '早'],
    pages: [
      { emoji: '🐰', text: '小兔有一个小菜园。', p: 'xiǎo tù yǒu yī gè xiǎo cài yuán.' },
      { emoji: '🌱', text: '春天，他在地里种菜。', p: 'chūn tiān, tā zài dì lǐ zhòng cài.' },
      { emoji: '💧', text: '每天早上，他给菜苗浇水。', p: 'měi tiān zǎo shang, tā gěi cài miáo jiāo shuǐ.' },
      { emoji: '☀️', text: '日光好，菜苗一天比一天高。', p: 'rì guāng hǎo, cài miáo yī tiān bǐ yī tiān gāo.' },
      { emoji: '🥬', text: '过了一个月，菜都长大了。', p: 'guò le yī gè yuè, cài dōu zhǎng dà le.' },
      { emoji: '🧺', text: '小兔收了菜，送给旁边的老牛。', p: 'xiǎo tù shōu le cài, sòng gěi páng bian de lǎo niú.' },
      { emoji: '😄', text: '老牛说：你种的菜真好！', p: 'lǎo niú shuō: nǐ zhòng de cài zhēn hǎo!' }
    ]
  },
  {
    id: 'bx31',
    title: '小蚁搬米',
    pinyin: 'xiǎo yǐ bān mǐ',
    level: 2,
    levelName: '第 2 级 · 半路上的一场雨',
    cover: '🐜',
    palette: ['#ffe6b3', '#ffd6d6'],
    summary: '背上一个米走回家，半路下雨，在一片叶下等一等。',
    newChars: ['蚁', '路', '找', '到', '米', '放', '背', '重'],
    pages: [
      { emoji: '🐜', text: '小蚁在路上找到一个米。', p: 'xiǎo yǐ zài lù shàng zhǎo dào yī gè mǐ.' },
      { emoji: '🎒', text: '他把米放到背上。', p: 'tā bǎ mǐ fàng dào bèi shang.' },
      { emoji: '🚶', text: '米不重，小蚁走很快。', p: 'mǐ bù zhòng, xiǎo yǐ zǒu hěn kuài.' },
      { emoji: '🌧️', text: '走到半路，雨来了。', p: 'zǒu dào bàn lù, yǔ lái le.' },
      { emoji: '🍃', text: '小蚁在一片叶下停了停。', p: 'xiǎo yǐ zài yī piàn yè xià tíng le tíng.' },
      { emoji: '☀️', text: '雨停了，小蚁又走。', p: 'yǔ tíng le, xiǎo yǐ yòu zǒu.' },
      { emoji: '🏠', text: '到家了，妈妈说：你真勤快！', p: 'dào jiā le, mā ma shuō: nǐ zhēn qín kuài!' }
    ]
  },
  {
    id: 'bx32',
    title: '有人敲门',
    pinyin: 'yǒu rén qiāo mén',
    level: 2,
    levelName: '第 2 级 · 门外是婆婆',
    cover: '🚪',
    palette: ['#e6f5c9', '#c8ebff'],
    summary: '读书读到一半，门响了。门外是婆婆，手里有一袋糕。',
    newChars: ['屋', '读', '书', '敲', '门', '问', '婆', '开'],
    pages: [
      { emoji: '🚪', text: '我在屋里读书，有人敲门。', p: 'wǒ zài wū lǐ dú shū, yǒu rén qiāo mén.' },
      { emoji: '👂', text: '我问：是什么人？', p: 'wǒ wèn: shì shén me rén?' },
      { emoji: '👵', text: '门外说：是我，你的婆婆。', p: 'mén wài shuō: shì wǒ, nǐ de pó po.' },
      { emoji: '😄', text: '我开门，婆婆手里有一袋糕。', p: 'wǒ kāi mén, pó po shǒu lǐ yǒu yī dài gāo.' },
      { emoji: '🍰', text: '婆婆说：这是给你的。', p: 'pó po shuō: zhè shì gěi nǐ de.' },
      { emoji: '🍵', text: '我给婆婆拿一杯茶。', p: 'wǒ gěi pó po ná yī bēi chá.' },
      { emoji: '❤️', text: '婆婆笑了，我也笑了。', p: 'pó po xiào le, wǒ yě xiào le.' }
    ]
  },
  {
    id: 'bx33',
    title: '小熊的蜜',
    pinyin: 'xiǎo xióng de mì',
    level: 2,
    levelName: '第 2 级 · 拿了要还',
    cover: '🐻',
    palette: ['#ffd6d6', '#e8e0ff'],
    summary: '小熊拿了蜂的蜜，脸红了。他给蜂种了满山的花。',
    newChars: ['熊', '爱', '吃', '蜜', '树', '找', '到', '碗'],
    pages: [
      { emoji: '🐻', text: '小熊爱吃蜜。', p: 'xiǎo xióng ài chī mì.' },
      { emoji: '🍯', text: '他在树下找到一碗蜜。', p: 'tā zài shù xià zhǎo dào yī wǎn mì.' },
      { emoji: '🐝', text: '蜂说：这是我们做的蜜。', p: 'fēng shuō: zhè shì wǒ men zuò de mì.' },
      { emoji: '😳', text: '小熊的脸红了。', p: 'xiǎo xióng de liǎn hóng le.' },
      { emoji: '🌸', text: '小熊说：我给你们种花，好不好？', p: 'xiǎo xióng shuō: wǒ gěi nǐ men zhòng huā, hǎo bù hǎo?' },
      { emoji: '🌼', text: '春天，山上开满了花。', p: 'chūn tiān, shān shàng kāi mǎn le huā.' },
      { emoji: '🍯', text: '蜂做了好多蜜，也分给小熊。', p: 'fēng zuò le hǎo duō mì, yě fēn gěi xiǎo xióng.' }
    ]
  },
  {
    id: 'bx34',
    title: '我的新鞋',
    pinyin: 'wǒ de xīn xié',
    level: 2,
    levelName: '第 2 级 · 湿了也别怕',
    cover: '👟',
    palette: ['#fff1cf', '#d9f6f3'],
    summary: '新鞋在水边湿了，我怕妈妈说我，回家就把鞋洗干净。',
    newChars: ['妈', '买', '双', '新', '鞋', '蓝', '路', '跑'],
    pages: [
      { emoji: '👟', text: '妈妈买了一双新鞋给我。', p: 'mā ma mǎi le yī shuāng xīn xié gěi wǒ.' },
      { emoji: '😄', text: '新鞋是蓝的，很好看。', p: 'xīn xié shì lán de, hěn hǎo kàn.' },
      { emoji: '🏃', text: '我在路上跑，鞋很轻。', p: 'wǒ zài lù shàng pǎo, xié hěn qīng.' },
      { emoji: '💧', text: '走到水边，我的鞋湿了。', p: 'zǒu dào shuǐ biān, wǒ de xié shī le.' },
      { emoji: '😟', text: '我怕妈妈说我。', p: 'wǒ pà mā ma shuō wǒ.' },
      { emoji: '🧼', text: '回家后，我洗了鞋，也洗了脚。', p: 'huí jiā hòu, wǒ xǐ le xié, yě xǐ le jiǎo.' },
      { emoji: '👏', text: '妈妈说：你会洗，真好。', p: 'mā ma shuō: nǐ huì xǐ, zhēn hǎo.' }
    ]
  },
  {
    id: 'bx35',
    title: '门外打球',
    pinyin: 'mén wài dǎ qiú',
    level: 2,
    levelName: '第 2 级 · 一同玩才好玩',
    cover: '⚽',
    palette: ['#ffe0c2', '#c8ebff'],
    summary: '一脚把球打到树下，一只小狗把球送了回来。',
    newChars: ['门', '打', '球', '明', '脚', '飞', '远', '红'],
    pages: [
      { emoji: '⚽', text: '我们在门外打球。', p: 'wǒ men zài mén wài dǎ qiú.' },
      { emoji: '🧒', text: '小明一脚，球飞很远。', p: 'xiǎo míng yī jiǎo, qiú fēi hěn yuǎn.' },
      { emoji: '🏃', text: '小红去追球。', p: 'xiǎo hóng qù zhuī qiú.' },
      { emoji: '🌳', text: '球到了树下。', p: 'qiú dào le shù xià.' },
      { emoji: '🐕', text: '一只小狗把球送来。', p: 'yī zhī xiǎo gǒu bǎ qiú sòng lái.' },
      { emoji: '😄', text: '大家都笑了。', p: 'dà jiā dōu xiào le.' },
      { emoji: '🤝', text: '打球要一同玩，才好玩。', p: 'dǎ qiú yào yī tóng wán, cái hǎo wán.' }
    ]
  },
  {
    id: 'bx36',
    title: '母鸡下蛋',
    pinyin: 'mǔ jī xià dàn',
    level: 2,
    levelName: '第 2 级 · 一天数一个',
    cover: '🐔',
    palette: ['#c8ebff', '#ffe6b3'],
    summary: '母鸡一天下一个蛋，我一天数一个，一个月后篮子满了。',
    newChars: ['家', '只', '母', '鸡', '今', '蛋', '数', '明'],
    pages: [
      { emoji: '🐔', text: '我家有一只母鸡。', p: 'wǒ jiā yǒu yī zhī mǔ jī.' },
      { emoji: '🥚', text: '今天，母鸡下了一个蛋。', p: 'jīn tiān, mǔ jī xià le yī gè dàn.' },
      { emoji: '☝️', text: '我数一数：一个。', p: 'wǒ shǔ yī shǔ: yī gè.' },
      { emoji: '🍳', text: '明天，母鸡又下了一个。', p: 'míng tiān, mǔ jī yòu xià le yī gè.' },
      { emoji: '✌️', text: '我数一数：二个。', p: 'wǒ shǔ yī shǔ: èr gè.' },
      { emoji: '🧺', text: '一个月后，篮里有好多蛋。', p: 'yī gè yuè hòu, lán lǐ yǒu hǎo duō dàn.' },
      { emoji: '😄', text: '妈妈说：这些都是你数的，真好。', p: 'mā ma shuō: zhè xiē dōu shì nǐ shǔ de, zhēn hǎo.' }
    ]
  },
  {
    id: 'bx37',
    title: '小猫上树',
    pinyin: 'xiǎo māo shàng shù',
    level: 2,
    levelName: '第 2 级 · 上去容易下来难',
    cover: '🐱',
    palette: ['#ffe6b3', '#c8ebff'],
    summary: '为了看鸟爬上树，下不来了。爸爸站在树下举手抱他。',
    newChars: ['猫', '到', '树', '鸟', '爬', '飞', '走', '哭'],
    pages: [
      { emoji: '🐱', text: '小猫看到树上有鸟。', p: 'xiǎo māo kàn dào shù shàng yǒu niǎo.' },
      { emoji: '🌳', text: '小猫爬上树。', p: 'xiǎo māo pá shàng shù.' },
      { emoji: '🐦', text: '鸟飞走了。', p: 'niǎo fēi zǒu le.' },
      { emoji: '😿', text: '小猫下不来，在树上哭。', p: 'xiǎo māo xià bù lái, zài shù shàng kū.' },
      { emoji: '👨', text: '爸爸走到树下，举手要抱他。', p: 'bà ba zǒu dào shù xià, jǔ shǒu yào bào tā.' },
      { emoji: '🤲', text: '小猫跳下来，爸爸抱好他。', p: 'xiǎo māo tiào xià lái, bà ba bào hǎo tā.' },
      { emoji: '😺', text: '小猫说：以后我不上这么高的树了。', p: 'xiǎo māo shuō: yǐ hòu wǒ bù shàng zhè me gāo de shù le.' }
    ]
  },
  {
    id: 'bx38',
    title: '弟弟哭了',
    pinyin: 'dì di kū le',
    level: 2,
    levelName: '第 2 级 · 一间屋找一遍',
    cover: '👶',
    palette: ['#d9f6f3', '#ffe0e6'],
    summary: '弟弟的小熊不见了，床下没有，椅后没有，篮里找到了。',
    newChars: ['弟', '哭', '问', '找', '到', '熊', '床', '椅'],
    pages: [
      { emoji: '👶', text: '弟弟哭了。', p: 'dì di kū le.' },
      { emoji: '🤔', text: '我问：你为什么哭？', p: 'wǒ wèn: nǐ wèi shén me kū?' },
      { emoji: '🧸', text: '弟弟说：我找不到我的小熊。', p: 'dì di shuō: wǒ zhǎo bù dào wǒ de xiǎo xióng.' },
      { emoji: '🛏️', text: '我在床下找，没有。', p: 'wǒ zài chuáng xià zhǎo, méi yǒu.' },
      { emoji: '🪑', text: '我在椅后找，也没有。', p: 'wǒ zài yǐ hòu zhǎo, yě méi yǒu.' },
      { emoji: '🧺', text: '我在篮里找到了小熊！', p: 'wǒ zài lán lǐ zhǎo dào le xiǎo xióng!' },
      { emoji: '😄', text: '弟弟不哭了，他抱好小熊笑了。', p: 'dì di bù kū le, tā bào hǎo xiǎo xióng xiào le.' }
    ]
  },
  {
    id: 'bx39',
    title: '小燕来了',
    pinyin: 'xiǎo yàn lái le',
    level: 2,
    levelName: '第 2 级 · 檐下的新家',
    cover: '🐦',
    palette: ['#e8e0ff', '#fff1cf'],
    summary: '春天小燕从远方来，一次一次拿草和泥，在檐下做了一个家。',
    newChars: ['春', '到', '燕', '从', '远', '方', '家', '檐'],
    pages: [
      { emoji: '🐦', text: '春天到了，小燕从远方来。', p: 'chūn tiān dào le, xiǎo yàn cóng yuǎn fāng lái.' },
      { emoji: '🏠', text: '小燕在我家的檐下做家。', p: 'xiǎo yàn zài wǒ jiā de yán xià zuò jiā.' },
      { emoji: '🌿', text: '他一次一次拿来草和泥。', p: 'tā yī cì yī cì ná lái cǎo hé ní.' },
      { emoji: '🥚', text: '过了几天，家里有了蛋。', p: 'guò le jǐ tiān, jiā lǐ yǒu le dàn.' },
      { emoji: '🐣', text: '又过了几天，小燕有了娃。', p: 'yòu guò le jǐ tiān, xiǎo yàn yǒu le wá.' },
      { emoji: '🐛', text: '燕妈妈天天去找虫。', p: 'yàn mā ma tiān tiān qù zhǎo chóng.' },
      { emoji: '😄', text: '我在窗前看，一天也看不完。', p: 'wǒ zài chuāng qián kàn, yī tiān yě kàn bù wán.' }
    ]
  },
  {
    id: 'bx40',
    title: '我们去公园',
    pinyin: 'wǒ men qù gōng yuán',
    level: 2,
    levelName: '第 2 级 · 周日的半天',
    cover: '🌳',
    palette: ['#ffe0c2', '#e6f5c9'],
    summary: '公园里有花有树，池里有鸭，一人一个苹果，玩到天晚。',
    newChars: ['今', '周', '公', '园', '花', '树', '池', '鸭'],
    pages: [
      { emoji: '🌳', text: '今天是周日，我们去公园。', p: 'jīn tiān shì zhōu rì, wǒ men qù gōng yuán.' },
      { emoji: '🌸', text: '公园里有花，也有大树。', p: 'gōng yuán lǐ yǒu huā, yě yǒu dà shù.' },
      { emoji: '🦆', text: '池里有鸭，鸭在水上。', p: 'chí lǐ yǒu yā, yā zài shuǐ shàng.' },
      { emoji: '⚽', text: '弟弟在草地上玩球。', p: 'dì di zài cǎo dì shàng wán qiú.' },
      { emoji: '🍎', text: '妈妈拿来苹果，一人一个。', p: 'mā ma ná lái píng guǒ, yī rén yī gè.' },
      { emoji: '🎨', text: '爸爸给我们画了一张图。', p: 'bà ba gěi wǒ men huà le yī zhāng tú.' },
      { emoji: '🌇', text: '天晚了，我们回家。公园真好玩。', p: 'tiān wǎn le, wǒ men huí jiā. gōng yuán zhēn hǎo wán.' }
    ]
  }
]
