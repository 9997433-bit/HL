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
      {
        emoji: '🐟', text: '水里有鱼。', p: 'shuǐ lǐ yǒu yú.',
        sceneBg: 'water',
        sceneAlt: '水里有鱼',
        scene: [
          { e: '🐟', x: 38, y: 62, s: 1.5, m: 'sway' },
          { e: '🐠', x: 66, y: 74, s: 1.2, m: 'sway' },
          { e: '🫧', x: 54, y: 44, s: 0.8, m: 'float' },
          { e: '🌊', x: 22, y: 84, s: 1.3, m: 'drift' }
        ]
      },
      {
        emoji: '🦐', text: '水里有虾，虾很小。', p: 'shuǐ lǐ yǒu xiā, xiā hěn xiǎo.',
        sceneBg: 'water',
        sceneAlt: '水里有虾，虾很小',
        scene: [
          { e: '🦐', x: 44, y: 70, s: 0.9, m: 'sway' },
          { e: '🦐', x: 66, y: 80, s: 0.7, m: 'sway' },
          { e: '🌿', x: 80, y: 62, s: 1, m: 'sway' },
          { e: '🌊', x: 20, y: 86, s: 1.3, m: 'drift' }
        ]
      },
      {
        emoji: '🦀', text: '石头下有蟹。', p: 'shí tou xià yǒu xiè.',
        sceneBg: 'water',
        sceneAlt: '石头下有蟹',
        scene: [
          { e: '🪨', x: 34, y: 60, s: 1.8 },
          { e: '🦀', x: 56, y: 80, s: 1.2, m: 'sway' },
          { e: '🫧', x: 70, y: 46, s: 0.7, m: 'float' },
          { e: '🌊', x: 16, y: 88, s: 1.2, m: 'drift' }
        ]
      },
      {
        emoji: '🐢', text: '水里还有龟，龟很慢。', p: 'shuǐ lǐ hái yǒu guī, guī hěn màn.',
        sceneBg: 'water',
        sceneAlt: '水里有龟，龟很慢',
        scene: [
          { e: '🐢', x: 48, y: 74, s: 1.6, m: 'drift' },
          { e: '🐟', x: 74, y: 58, s: 0.9, m: 'sway' },
          { e: '🫧', x: 30, y: 48, s: 0.7, m: 'float' },
          { e: '🌿', x: 18, y: 82, s: 1, m: 'sway' }
        ]
      },
      {
        emoji: '🐸', text: '岸上有蛙，蛙会跳。', p: 'àn shàng yǒu wā, wā huì tiào.',
        sceneBg: 'field',
        sceneAlt: '岸上有蛙，蛙会跳',
        scene: [
          { e: '🐸', x: 54, y: 70, s: 1.4, m: 'float' },
          { e: '🌾', x: 22, y: 78, s: 1.2, m: 'sway' },
          { e: '🪨', x: 78, y: 84, s: 1.1 },
          { e: '🌊', x: 44, y: 90, s: 1.2, m: 'drift' }
        ]
      },
      {
        emoji: '🌊', text: '水里的朋友真多！', p: 'shuǐ lǐ de péng you zhēn duō!',
        sceneBg: 'water',
        sceneAlt: '水里的朋友真多',
        scene: [
          { e: '🐟', x: 26, y: 58, s: 1.1, m: 'sway' },
          { e: '🐢', x: 82, y: 64, s: 1.2, m: 'drift' },
          { e: '🦐', x: 46, y: 70, s: 0.9, m: 'sway' },
          { e: '🐸', x: 14, y: 80, s: 1, m: 'float' },
          { e: '🦀', x: 66, y: 82, s: 1.1, m: 'sway' }
        ]
      }
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
      {
        emoji: '🐦', text: '天上有鸟，鸟会飞。', p: 'tiān shàng yǒu niǎo, niǎo huì fēi.',
        sceneBg: 'sky',
        sceneAlt: '天上有鸟，鸟会飞',
        scene: [
          { e: '☀️', x: 80, y: 18, s: 1, m: 'float' },
          { e: '☁️', x: 26, y: 22, s: 1.2, m: 'drift' },
          { e: '🐦', x: 54, y: 30, s: 1.3, m: 'float' },
          { e: '🌳', x: 30, y: 80, s: 1.6 }
        ]
      },
      {
        emoji: '🦋', text: '花上有蝶，蝶也会飞。', p: 'huā shàng yǒu dié, dié yě huì fēi.',
        sceneBg: 'field',
        sceneAlt: '花上有蝶，蝶也会飞',
        scene: [
          { e: '🦋', x: 56, y: 44, s: 1.2, m: 'float' },
          { e: '🌸', x: 40, y: 74, s: 1.2, m: 'sway' },
          { e: '🌼', x: 70, y: 80, s: 1, m: 'sway' },
          { e: '🌿', x: 18, y: 84, s: 1.1, m: 'sway' }
        ]
      },
      {
        emoji: '🐝', text: '蜂在花上飞，蜂会做蜜。', p: 'fēng zài huā shàng fēi, fēng huì zuò mì.',
        sceneBg: 'field',
        sceneAlt: '蜂在花上飞，蜂会做蜜',
        scene: [
          { e: '🐝', x: 52, y: 46, s: 1.1, m: 'float' },
          { e: '🌻', x: 32, y: 74, s: 1.4, m: 'sway' },
          { e: '🍯', x: 78, y: 76, s: 1.1 },
          { e: '🌺', x: 64, y: 86, s: 1, m: 'sway' }
        ]
      },
      {
        emoji: '🐜', text: '蚁不会飞，蚁在地上走。', p: 'yǐ bù huì fēi, yǐ zài dì shàng zǒu.',
        sceneBg: 'field',
        sceneAlt: '蚁在地上走，不会飞',
        scene: [
          { e: '🪨', x: 80, y: 70, s: 1 },
          { e: '🌿', x: 22, y: 76, s: 1.1, m: 'sway' },
          { e: '🐜', x: 46, y: 80, s: 0.9, m: 'drift' },
          { e: '🐜', x: 62, y: 88, s: 0.8, m: 'drift' }
        ]
      },
      {
        emoji: '✈️', text: '天上有飞机，飞机很大。', p: 'tiān shàng yǒu fēi jī, fēi jī hěn dà.',
        sceneBg: 'sky',
        sceneAlt: '天上有飞机，飞机很大',
        scene: [
          { e: '☁️', x: 22, y: 26, s: 1.2, m: 'drift' },
          { e: '✈️', x: 52, y: 34, s: 1.9, m: 'drift' },
          { e: '☁️', x: 82, y: 44, s: 1, m: 'drift' },
          { e: '🏠', x: 36, y: 84, s: 1.1 }
        ]
      },
      {
        emoji: '☁️', text: '我看天上，天上真高！', p: 'wǒ kàn tiān shàng, tiān shàng zhēn gāo!',
        sceneBg: 'sky',
        sceneAlt: '我看天上，天上真高',
        scene: [
          { e: '☀️', x: 78, y: 20, s: 1.1, m: 'float' },
          { e: '✈️', x: 30, y: 26, s: 0.9, m: 'drift' },
          { e: '🐦', x: 56, y: 34, s: 0.9, m: 'float' },
          { e: '🙋', x: 50, y: 82, s: 1.5 }
        ]
      }
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
      {
        emoji: '🌲', text: '山上有松，松很高。', p: 'shān shàng yǒu sōng, sōng hěn gāo.',
        sceneBg: 'field',
        sceneAlt: '山上有松，松很高',
        scene: [
          { e: '⛰️', x: 26, y: 52, s: 2 },
          { e: '🌲', x: 62, y: 60, s: 1.7 },
          { e: '🌲', x: 80, y: 74, s: 1.3 },
          { e: '🌿', x: 40, y: 86, s: 1, m: 'sway' }
        ]
      },
      {
        emoji: '🌳', text: '山下有柳，柳的枝很长。', p: 'shān xià yǒu liǔ, liǔ de zhī hěn cháng.',
        sceneBg: 'field',
        sceneAlt: '山下有柳，柳枝很长',
        scene: [
          { e: '⛰️', x: 22, y: 44, s: 1.8 },
          { e: '🌳', x: 58, y: 66, s: 1.9, m: 'sway' },
          { e: '🌊', x: 78, y: 84, s: 1.2, m: 'drift' },
          { e: '🌿', x: 36, y: 88, s: 1, m: 'sway' }
        ]
      },
      {
        emoji: '🍑', text: '园里有桃，桃是红的。', p: 'yuán lǐ yǒu táo, táo shì hóng de.',
        sceneBg: 'field',
        sceneAlt: '园里有桃，桃是红的',
        scene: [
          { e: '🌳', x: 34, y: 58, s: 1.8 },
          { e: '🍑', x: 60, y: 70, s: 1.2, m: 'float' },
          { e: '🍑', x: 76, y: 82, s: 1 },
          { e: '🌸', x: 18, y: 84, s: 1, m: 'sway' }
        ]
      },
      {
        emoji: '🌰', text: '树上有枣，枣也是红的。', p: 'shù shàng yǒu zǎo, zǎo yě shì hóng de.',
        sceneBg: 'field',
        sceneAlt: '树上有枣，枣是红的',
        scene: [
          { e: '🌳', x: 40, y: 56, s: 1.9 },
          { e: '🌰', x: 62, y: 70, s: 1, m: 'float' },
          { e: '🌰', x: 74, y: 82, s: 0.9 },
          { e: '🌿', x: 20, y: 86, s: 1, m: 'sway' }
        ]
      },
      {
        emoji: '🍐', text: '那是梨树，梨是黄的。', p: 'nà shì lí shù, lí shì huáng de.',
        sceneBg: 'field',
        sceneAlt: '那是梨树，梨是黄的',
        scene: [
          { e: '☀️', x: 84, y: 20, s: 1, m: 'float' },
          { e: '🌳', x: 36, y: 58, s: 1.8 },
          { e: '🍐', x: 60, y: 72, s: 1.1, m: 'float' },
          { e: '🍐', x: 74, y: 84, s: 0.9 }
        ]
      },
      {
        emoji: '🍃', text: '树多，叶也多。', p: 'shù duō, yè yě duō.',
        sceneBg: 'field',
        sceneAlt: '树多，叶也多',
        scene: [
          { e: '🌲', x: 46, y: 56, s: 1.4 },
          { e: '🌳', x: 24, y: 64, s: 1.5 },
          { e: '🌳', x: 68, y: 70, s: 1.6 },
          { e: '🍃', x: 34, y: 86, s: 0.9, m: 'drift' },
          { e: '🍃', x: 58, y: 88, s: 1, m: 'drift' }
        ]
      }
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
      {
        emoji: '👀', text: '这是我的眼。', p: 'zhè shì wǒ de yǎn.',
        sceneBg: 'room',
        sceneAlt: '这是我的眼',
        scene: [
          { e: '👀', x: 54, y: 50, s: 1.9, m: 'float' },
          { e: '🧒', x: 28, y: 78, s: 1.4 },
          { e: '👉', x: 72, y: 76, s: 1.1 }
        ]
      },
      {
        emoji: '👂', text: '这是我的耳。', p: 'zhè shì wǒ de ěr.',
        sceneBg: 'room',
        sceneAlt: '这是我的耳',
        scene: [
          { e: '👂', x: 56, y: 50, s: 1.8, m: 'float' },
          { e: '🔔', x: 78, y: 62, s: 1, m: 'sway' },
          { e: '🧒', x: 30, y: 78, s: 1.4 }
        ]
      },
      {
        emoji: '👃', text: '这是我的鼻。', p: 'zhè shì wǒ de bí.',
        sceneBg: 'room',
        sceneAlt: '这是我的鼻',
        scene: [
          { e: '👃', x: 56, y: 50, s: 1.8, m: 'float' },
          { e: '🌸', x: 78, y: 68, s: 1, m: 'sway' },
          { e: '🧒', x: 30, y: 80, s: 1.4 }
        ]
      },
      {
        emoji: '👄', text: '这是我的嘴。', p: 'zhè shì wǒ de zuǐ.',
        sceneBg: 'room',
        sceneAlt: '这是我的嘴',
        scene: [
          { e: '🎵', x: 78, y: 44, s: 1, m: 'float' },
          { e: '👄', x: 54, y: 54, s: 1.7, m: 'float' },
          { e: '🧒', x: 28, y: 80, s: 1.4 }
        ]
      },
      {
        emoji: '✋', text: '这是我的手，手上有指。', p: 'zhè shì wǒ de shǒu, shǒu shàng yǒu zhǐ.',
        sceneBg: 'room',
        sceneAlt: '这是我的手，手上有指',
        scene: [
          { e: '✋', x: 54, y: 50, s: 2 },
          { e: '👐', x: 76, y: 76, s: 1.2 },
          { e: '🧒', x: 26, y: 80, s: 1.4 }
        ]
      },
      {
        emoji: '🦶', text: '这是我的脚，脚会走路。', p: 'zhè shì wǒ de jiǎo, jiǎo huì zǒu lù.',
        sceneBg: 'room',
        sceneAlt: '这是我的脚，脚会走路',
        scene: [
          { e: '🧒', x: 26, y: 70, s: 1.4 },
          { e: '🦶', x: 52, y: 60, s: 1.8 },
          { e: '👟', x: 76, y: 86, s: 1.1, m: 'float' }
        ]
      },
      {
        emoji: '🧒', text: '这都是我的身体。', p: 'zhè dōu shì wǒ de shēn tǐ.',
        sceneBg: 'room',
        sceneAlt: '这都是我的身体',
        scene: [
          { e: '👀', x: 30, y: 38, s: 0.9, m: 'float' },
          { e: '👂', x: 70, y: 42, s: 0.9, m: 'float' },
          { e: '✋', x: 82, y: 66, s: 0.9 },
          { e: '🧒', x: 50, y: 76, s: 2.1 },
          { e: '🦶', x: 20, y: 86, s: 0.9 }
        ]
      }
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
      {
        emoji: '🍚', text: '桌上有米饭。', p: 'zhuō shàng yǒu mǐ fàn.',
        sceneBg: 'room',
        sceneAlt: '桌上有米饭',
        scene: [
          { e: '🍚', x: 50, y: 62, s: 1.6 },
          { e: '🥢', x: 74, y: 70, s: 1.1 },
          { e: '🪑', x: 24, y: 80, s: 1.3 }
        ]
      },
      {
        emoji: '🥬', text: '桌上有菜，菜是绿的。', p: 'zhuō shàng yǒu cài, cài shì lǜ de.',
        sceneBg: 'room',
        sceneAlt: '桌上有菜，菜是绿的',
        scene: [
          { e: '🥬', x: 48, y: 58, s: 1.6, m: 'float' },
          { e: '🍚', x: 24, y: 74, s: 1.1 },
          { e: '🥗', x: 74, y: 80, s: 1.1 }
        ]
      },
      {
        emoji: '🥚', text: '碗里有一个蛋。', p: 'wǎn lǐ yǒu yī gè dàn.',
        sceneBg: 'room',
        sceneAlt: '碗里有一个蛋',
        scene: [
          { e: '🥚', x: 50, y: 52, s: 1.2, m: 'float' },
          { e: '🥢', x: 78, y: 66, s: 1 },
          { e: '🥣', x: 50, y: 76, s: 1.7 }
        ]
      },
      {
        emoji: '🥛', text: '杯里有奶，奶是白的。', p: 'bēi lǐ yǒu nǎi, nǎi shì bái de.',
        sceneBg: 'room',
        sceneAlt: '杯里有奶，奶是白的',
        scene: [
          { e: '🥛', x: 50, y: 60, s: 1.6, m: 'float' },
          { e: '🍚', x: 24, y: 76, s: 1.2 },
          { e: '🥬', x: 76, y: 82, s: 1.1 }
        ]
      },
      {
        emoji: '🍲', text: '还有一碗汤，汤很热。', p: 'hái yǒu yī wǎn tāng, tāng hěn rè.',
        sceneBg: 'room',
        sceneAlt: '还有一碗汤，汤很热',
        scene: [
          { e: '♨️', x: 50, y: 40, s: 1, m: 'float' },
          { e: '🍲', x: 50, y: 64, s: 1.7 },
          { e: '🥢', x: 24, y: 74, s: 1 },
          { e: '🥣', x: 76, y: 82, s: 1.1 }
        ]
      },
      {
        emoji: '😋', text: '这些我都爱吃！', p: 'zhè xiē wǒ dōu ài chī!',
        sceneBg: 'room',
        sceneAlt: '这些我都爱吃',
        scene: [
          { e: '🥬', x: 48, y: 58, s: 1.1 },
          { e: '🍚', x: 28, y: 68, s: 1.2 },
          { e: '🍲', x: 68, y: 72, s: 1.2 },
          { e: '🥛', x: 84, y: 82, s: 1 },
          { e: '😋', x: 44, y: 86, s: 1.4, m: 'float' }
        ]
      }
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
      {
        emoji: '👕', text: '这是我的衣。', p: 'zhè shì wǒ de yī.',
        sceneBg: 'room',
        sceneAlt: '这是我的衣',
        scene: [
          { e: '🪟', x: 80, y: 40, s: 1.1 },
          { e: '👕', x: 52, y: 54, s: 1.9, m: 'float' },
          { e: '🧒', x: 26, y: 80, s: 1.3 }
        ]
      },
      {
        emoji: '👖', text: '这是我的裤。', p: 'zhè shì wǒ de kù.',
        sceneBg: 'room',
        sceneAlt: '这是我的裤',
        scene: [
          { e: '👖', x: 52, y: 56, s: 1.8, m: 'float' },
          { e: '🧒', x: 26, y: 78, s: 1.3 },
          { e: '🪑', x: 80, y: 84, s: 1.1 }
        ]
      },
      {
        emoji: '🧦', text: '这是我的袜。', p: 'zhè shì wǒ de wà.',
        sceneBg: 'room',
        sceneAlt: '这是我的袜',
        scene: [
          { e: '🧦', x: 52, y: 56, s: 1.6, m: 'float' },
          { e: '🧒', x: 26, y: 78, s: 1.3 },
          { e: '🧺', x: 80, y: 86, s: 1.1 }
        ]
      },
      {
        emoji: '👟', text: '这是我的鞋。', p: 'zhè shì wǒ de xié.',
        sceneBg: 'room',
        sceneAlt: '这是我的鞋',
        scene: [
          { e: '🧒', x: 26, y: 72, s: 1.3 },
          { e: '👟', x: 50, y: 78, s: 1.7 },
          { e: '👟', x: 72, y: 86, s: 1.4 }
        ]
      },
      {
        emoji: '🧢', text: '这是我的帽。', p: 'zhè shì wǒ de mào.',
        sceneBg: 'room',
        sceneAlt: '这是我的帽',
        scene: [
          { e: '🧢', x: 52, y: 46, s: 1.7, m: 'float' },
          { e: '👕', x: 78, y: 70, s: 1.1 },
          { e: '🧒', x: 30, y: 80, s: 1.5 }
        ]
      },
      {
        emoji: '🎒', text: '衣裤鞋帽，都是我的。', p: 'yī kù xié mào, dōu shì wǒ de.',
        sceneBg: 'room',
        sceneAlt: '衣裤鞋帽都是我的',
        scene: [
          { e: '🧢', x: 26, y: 40, s: 1, m: 'float' },
          { e: '👕', x: 46, y: 56, s: 1.2 },
          { e: '👖', x: 66, y: 70, s: 1.1 },
          { e: '🎒', x: 18, y: 82, s: 1.2 },
          { e: '👟', x: 82, y: 86, s: 1 }
        ]
      }
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
      {
        emoji: '🌸', text: '园里有花。', p: 'yuán lǐ yǒu huā.',
        sceneBg: 'field',
        sceneAlt: '园里有花',
        scene: [
          { e: '☀️', x: 82, y: 20, s: 1, m: 'float' },
          { e: '🌸', x: 46, y: 66, s: 1.5, m: 'sway' },
          { e: '🌺', x: 70, y: 78, s: 1.2, m: 'sway' },
          { e: '🌿', x: 22, y: 84, s: 1.1, m: 'sway' }
        ]
      },
      {
        emoji: '🌿', text: '园里有草，草不高。', p: 'yuán lǐ yǒu cǎo, cǎo bù gāo.',
        sceneBg: 'field',
        sceneAlt: '园里有草，草不高',
        scene: [
          { e: '🌸', x: 78, y: 68, s: 1, m: 'sway' },
          { e: '🌿', x: 40, y: 78, s: 1.2, m: 'sway' },
          { e: '🌾', x: 20, y: 82, s: 1.1, m: 'sway' },
          { e: '🌱', x: 62, y: 88, s: 1, m: 'sway' }
        ]
      },
      {
        emoji: '🌹', text: '红花在左边，黄花在右边。', p: 'hóng huā zài zuǒ bian, huáng huā zài yòu bian.',
        sceneBg: 'field',
        sceneAlt: '红花在左边，黄花在右边',
        scene: [
          { e: '☁️', x: 50, y: 24, s: 1, m: 'drift' },
          { e: '🌹', x: 24, y: 70, s: 1.5, m: 'sway' },
          { e: '🌻', x: 76, y: 72, s: 1.5, m: 'sway' },
          { e: '🌿', x: 50, y: 86, s: 1.1, m: 'sway' }
        ]
      },
      {
        emoji: '🍀', text: '草是绿的，叶也是绿的。', p: 'cǎo shì lǜ de, yè yě shì lǜ de.',
        sceneBg: 'field',
        sceneAlt: '草是绿的，叶也是绿的',
        scene: [
          { e: '🍃', x: 60, y: 56, s: 1, m: 'drift' },
          { e: '🌳', x: 18, y: 60, s: 1.5 },
          { e: '🌿', x: 34, y: 78, s: 1.4, m: 'sway' },
          { e: '🌱', x: 72, y: 86, s: 1.1, m: 'sway' }
        ]
      },
      {
        emoji: '🐝', text: '蜂来了，蝶也来了。', p: 'fēng lái le, dié yě lái le.',
        sceneBg: 'field',
        sceneAlt: '蜂来了，蝶也来了',
        scene: [
          { e: '🐝', x: 40, y: 44, s: 1.1, m: 'float' },
          { e: '🦋', x: 66, y: 52, s: 1.2, m: 'float' },
          { e: '🌻', x: 30, y: 78, s: 1.3, m: 'sway' },
          { e: '🌸', x: 72, y: 86, s: 1.1, m: 'sway' }
        ]
      },
      {
        emoji: '🌼', text: '我爱这个花园。', p: 'wǒ ài zhè gè huā yuán.',
        sceneBg: 'field',
        sceneAlt: '我爱这个花园',
        scene: [
          { e: '❤️', x: 50, y: 32, s: 1, m: 'float' },
          { e: '🦋', x: 62, y: 46, s: 1, m: 'float' },
          { e: '🌸', x: 24, y: 72, s: 1.1, m: 'sway' },
          { e: '🌻', x: 76, y: 76, s: 1.2, m: 'sway' },
          { e: '🙋', x: 48, y: 84, s: 1.5 }
        ]
      }
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
      {
        emoji: '🚗', text: '路上有车。', p: 'lù shàng yǒu chē.',
        sceneBg: 'sky',
        sceneAlt: '路上有车',
        scene: [
          { e: '☁️', x: 76, y: 24, s: 1.1, m: 'drift' },
          { e: '🌳', x: 20, y: 60, s: 1.4 },
          { e: '🚗', x: 48, y: 76, s: 1.6, m: 'drift' },
          { e: '🛣️', x: 50, y: 90, s: 1.4 }
        ]
      },
      {
        emoji: '🚌', text: '大车很慢，小车很快。', p: 'dà chē hěn màn, xiǎo chē hěn kuài.',
        sceneBg: 'sky',
        sceneAlt: '大车很慢，小车很快',
        scene: [
          { e: '☁️', x: 24, y: 24, s: 1, m: 'drift' },
          { e: '🚌', x: 30, y: 72, s: 1.8, m: 'drift' },
          { e: '🚗', x: 70, y: 82, s: 1.2, m: 'drift' },
          { e: '🛣️', x: 50, y: 92, s: 1.3 }
        ]
      },
      {
        emoji: '🚲', text: '我会骑车。', p: 'wǒ huì qí chē.',
        sceneBg: 'sky',
        sceneAlt: '我会骑车',
        scene: [
          { e: '☀️', x: 82, y: 20, s: 1, m: 'float' },
          { e: '🌳', x: 20, y: 64, s: 1.4 },
          { e: '🧒', x: 52, y: 58, s: 1.2 },
          { e: '🚲', x: 52, y: 80, s: 1.6, m: 'drift' }
        ]
      },
      {
        emoji: '🚂', text: '铁路上有火车，火车很长。', p: 'tiě lù shàng yǒu huǒ chē, huǒ chē hěn cháng.',
        sceneBg: 'sky',
        sceneAlt: '铁路上有火车，火车很长',
        scene: [
          { e: '⛰️', x: 22, y: 42, s: 1.6 },
          { e: '🚂', x: 30, y: 72, s: 1.6, m: 'drift' },
          { e: '🚃', x: 54, y: 78, s: 1.3, m: 'drift' },
          { e: '🚃', x: 78, y: 84, s: 1.2, m: 'drift' }
        ]
      },
      {
        emoji: '⛵', text: '河上有船，船不走路。', p: 'hé shàng yǒu chuán, chuán bù zǒu lù.',
        sceneBg: 'water',
        sceneAlt: '河上有船，船不走路',
        scene: [
          { e: '⛰️', x: 20, y: 46, s: 1.5 },
          { e: '⛵', x: 52, y: 68, s: 1.6, m: 'drift' },
          { e: '🌊', x: 34, y: 84, s: 1.3, m: 'sway' },
          { e: '🌊', x: 74, y: 90, s: 1.2, m: 'sway' }
        ]
      },
      {
        emoji: '🚦', text: '路上车多，我们要小心。', p: 'lù shàng chē duō, wǒ men yào xiǎo xīn.',
        sceneBg: 'sky',
        sceneAlt: '路上车多，我们要小心',
        scene: [
          { e: '🚦', x: 76, y: 56, s: 1.4, m: 'float' },
          { e: '🚗', x: 34, y: 74, s: 1.2, m: 'drift' },
          { e: '🧒', x: 18, y: 82, s: 1.2 },
          { e: '🚌', x: 58, y: 86, s: 1.3, m: 'drift' }
        ]
      }
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
      {
        emoji: '🛋️', text: '屋里有桌，也有椅。', p: 'wū lǐ yǒu zhuō, yě yǒu yǐ.',
        sceneBg: 'room',
        sceneAlt: '屋里有桌，也有椅',
        scene: [
          { e: '💡', x: 54, y: 24, s: 1, m: 'float' },
          { e: '🪟', x: 22, y: 38, s: 1.2 },
          { e: '🛋️', x: 38, y: 74, s: 1.6 },
          { e: '🪑', x: 68, y: 82, s: 1.3 }
        ]
      },
      {
        emoji: '🛏️', text: '屋里有床，床上有毯。', p: 'wū lǐ yǒu chuáng, chuáng shàng yǒu tǎn.',
        sceneBg: 'room',
        sceneAlt: '屋里有床，床上有毯',
        scene: [
          { e: '💡', x: 56, y: 24, s: 1, m: 'float' },
          { e: '🪟', x: 22, y: 38, s: 1.2 },
          { e: '🧸', x: 68, y: 62, s: 1, m: 'float' },
          { e: '🛏️', x: 46, y: 78, s: 1.8 }
        ]
      },
      {
        emoji: '💡', text: '屋里有灯，灯很亮。', p: 'wū lǐ yǒu dēng, dēng hěn liàng.',
        sceneBg: 'room',
        sceneAlt: '屋里有灯，灯很亮',
        scene: [
          { e: '💡', x: 52, y: 32, s: 1.6, m: 'float' },
          { e: '✨', x: 74, y: 46, s: 1, m: 'float' },
          { e: '🛋️', x: 36, y: 80, s: 1.3 },
          { e: '🪑', x: 74, y: 86, s: 1.1 }
        ]
      },
      {
        emoji: '🪟', text: '屋里有窗，窗外有树。', p: 'wū lǐ yǒu chuāng, chuāng wài yǒu shù.',
        sceneBg: 'room',
        sceneAlt: '屋里有窗，窗外有树',
        scene: [
          { e: '🌳', x: 76, y: 38, s: 1.2 },
          { e: '🪟', x: 44, y: 50, s: 1.8 },
          { e: '🪑', x: 26, y: 84, s: 1.2 },
          { e: '🛋️', x: 66, y: 88, s: 1.2 }
        ]
      },
      {
        emoji: '🚪', text: '屋里有门，门开了。', p: 'wū lǐ yǒu mén, mén kāi le.',
        sceneBg: 'room',
        sceneAlt: '屋里有门，门开了',
        scene: [
          { e: '💡', x: 26, y: 28, s: 1, m: 'float' },
          { e: '🚪', x: 48, y: 60, s: 1.8 },
          { e: '🪑', x: 20, y: 82, s: 1.1 },
          { e: '🧒', x: 74, y: 84, s: 1.2 }
        ]
      },
      {
        emoji: '🏠', text: '这就是我的家。', p: 'zhè jiù shì wǒ de jiā.',
        sceneBg: 'field',
        sceneAlt: '这就是我的家',
        scene: [
          { e: '☀️', x: 82, y: 20, s: 1, m: 'float' },
          { e: '🏠', x: 50, y: 58, s: 2 },
          { e: '🌳', x: 22, y: 74, s: 1.3 },
          { e: '🌸', x: 78, y: 82, s: 1, m: 'sway' },
          { e: '🧒', x: 56, y: 88, s: 1.2 }
        ]
      }
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
      {
        emoji: '🌾', text: '田里有稻。', p: 'tián lǐ yǒu dào.',
        sceneBg: 'field',
        sceneAlt: '田里有稻',
        scene: [
          { e: '☀️', x: 80, y: 20, s: 1, m: 'float' },
          { e: '⛰️', x: 20, y: 46, s: 1.5 },
          { e: '🌾', x: 44, y: 74, s: 1.5, m: 'sway' },
          { e: '🌾', x: 66, y: 86, s: 1.3, m: 'sway' }
        ]
      },
      {
        emoji: '🌽', text: '田里有麦，麦是黄的。', p: 'tián lǐ yǒu mài, mài shì huáng de.',
        sceneBg: 'field',
        sceneAlt: '田里有麦，麦是黄的',
        scene: [
          { e: '☀️', x: 82, y: 20, s: 1, m: 'float' },
          { e: '⛰️', x: 20, y: 46, s: 1.4 },
          { e: '🌽', x: 44, y: 74, s: 1.4 },
          { e: '🌾', x: 70, y: 84, s: 1.2, m: 'sway' }
        ]
      },
      {
        emoji: '🫘', text: '田里有豆，豆很小。', p: 'tián lǐ yǒu dòu, dòu hěn xiǎo.',
        sceneBg: 'field',
        sceneAlt: '田里有豆，豆很小',
        scene: [
          { e: '☀️', x: 82, y: 22, s: 1, m: 'float' },
          { e: '🌱', x: 30, y: 76, s: 1.1, m: 'sway' },
          { e: '🫘', x: 48, y: 82, s: 0.9 },
          { e: '🫘', x: 62, y: 88, s: 0.8 }
        ]
      },
      {
        emoji: '🐄', text: '田边有牛，牛在吃草。', p: 'tián biān yǒu niú, niú zài chī cǎo.',
        sceneBg: 'field',
        sceneAlt: '田边有牛，牛在吃草',
        scene: [
          { e: '⛰️', x: 20, y: 44, s: 1.4 },
          { e: '🌾', x: 24, y: 78, s: 1.2, m: 'sway' },
          { e: '🐄', x: 52, y: 76, s: 1.7 },
          { e: '🌿', x: 76, y: 86, s: 1.1, m: 'sway' }
        ]
      },
      {
        emoji: '👨‍🌾', text: '农人在田里忙。', p: 'nóng rén zài tián lǐ máng.',
        sceneBg: 'field',
        sceneAlt: '农人在田里忙',
        scene: [
          { e: '☀️', x: 82, y: 20, s: 1, m: 'float' },
          { e: '👨‍🌾', x: 50, y: 74, s: 1.6 },
          { e: '🌾', x: 24, y: 82, s: 1.2, m: 'sway' },
          { e: '🌾', x: 76, y: 86, s: 1.2, m: 'sway' }
        ]
      },
      {
        emoji: '🌞', text: '日光下，田很亮。', p: 'rì guāng xià, tián hěn liàng.',
        sceneBg: 'dawn',
        sceneAlt: '日光下，田很亮',
        scene: [
          { e: '☀️', x: 70, y: 24, s: 1.6, m: 'float' },
          { e: '⛰️', x: 18, y: 48, s: 1.4 },
          { e: '🌾', x: 34, y: 78, s: 1.3, m: 'sway' },
          { e: '🌾', x: 62, y: 88, s: 1.2, m: 'sway' }
        ]
      }
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
      {
        emoji: '🍎', text: '苹果是红的，很甜。', p: 'píng guǒ shì hóng de, hěn tián.',
        sceneBg: 'room',
        sceneAlt: '苹果是红的',
        scene: [
          { e: '🍎', x: 50, y: 60, s: 1.8, m: 'float' },
          { e: '🍎', x: 74, y: 78, s: 1.1 },
          { e: '🍃', x: 28, y: 72, s: 0.9, m: 'sway' },
          { e: '🧺', x: 30, y: 88, s: 1.2 }
        ]
      },
      {
        emoji: '🍐', text: '梨是黄的，也很甜。', p: 'lí shì huáng de, yě hěn tián.',
        sceneBg: 'room',
        sceneAlt: '梨是黄的',
        scene: [
          { e: '🍐', x: 48, y: 60, s: 1.7, m: 'float' },
          { e: '🍐', x: 72, y: 78, s: 1.1 },
          { e: '🍎', x: 24, y: 80, s: 0.9 },
          { e: '🧺', x: 52, y: 90, s: 1.2 }
        ]
      },
      {
        emoji: '🍇', text: '葡萄小小的，一口一个。', p: 'pú táo xiǎo xiǎo de, yī kǒu yī gè.',
        sceneBg: 'room',
        sceneAlt: '葡萄小小的',
        scene: [
          { e: '🍇', x: 50, y: 58, s: 1.6, m: 'float' },
          { e: '🍇', x: 74, y: 76, s: 1 },
          { e: '🍇', x: 26, y: 78, s: 0.8 },
          { e: '🍽️', x: 50, y: 90, s: 1.2 }
        ]
      },
      {
        emoji: '🍊', text: '橘是黄的，有点酸。', p: 'jú shì huáng de, yǒu diǎn suān.',
        sceneBg: 'room',
        sceneAlt: '橘是黄的，有点酸',
        scene: [
          { e: '🍊', x: 48, y: 58, s: 1.6, m: 'float' },
          { e: '🍊', x: 70, y: 74, s: 1.1 },
          { e: '🍊', x: 26, y: 80, s: 0.9 },
          { e: '🧺', x: 54, y: 90, s: 1.2 }
        ]
      },
      {
        emoji: '🍉', text: '瓜很大，瓜里是红的。', p: 'guā hěn dà, guā lǐ shì hóng de.',
        sceneBg: 'field',
        sceneAlt: '瓜很大，瓜里是红的',
        scene: [
          { e: '☀️', x: 82, y: 20, s: 1, m: 'float' },
          { e: '🍉', x: 46, y: 66, s: 2.1 },
          { e: '🍉', x: 74, y: 82, s: 1.1 },
          { e: '🌿', x: 20, y: 84, s: 1.1, m: 'sway' }
        ]
      },
      {
        emoji: '😋', text: '果子真多，我都爱吃。', p: 'guǒ zǐ zhēn duō, wǒ dōu ài chī.',
        sceneBg: 'room',
        sceneAlt: '果子真多，我都爱吃',
        scene: [
          { e: '🍎', x: 28, y: 58, s: 1.1 },
          { e: '🍐', x: 46, y: 66, s: 1.1 },
          { e: '🍇', x: 64, y: 72, s: 1 },
          { e: '🍊', x: 82, y: 80, s: 1 },
          { e: '😋', x: 44, y: 88, s: 1.5, m: 'float' }
        ]
      }
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
      {
        emoji: '☀️', text: '白天，天上有日。', p: 'bái tiān, tiān shàng yǒu rì.',
        sceneBg: 'sky',
        sceneAlt: '白天，天上有日',
        scene: [
          { e: '☀️', x: 72, y: 22, s: 1.6, m: 'float' },
          { e: '☁️', x: 28, y: 28, s: 1.2, m: 'drift' },
          { e: '🌳', x: 24, y: 78, s: 1.5 },
          { e: '🏠', x: 62, y: 84, s: 1.3 }
        ]
      },
      {
        emoji: '🌤️', text: '白天很亮，我在外边玩。', p: 'bái tiān hěn liàng, wǒ zài wài bian wán.',
        sceneBg: 'field',
        sceneAlt: '白天很亮，我在外边玩',
        scene: [
          { e: '☀️', x: 80, y: 20, s: 1.3, m: 'float' },
          { e: '🌳', x: 22, y: 66, s: 1.5 },
          { e: '🙋', x: 52, y: 78, s: 1.6 },
          { e: '🌸', x: 76, y: 86, s: 1, m: 'sway' }
        ]
      },
      {
        emoji: '🌙', text: '夜里，天上有月。', p: 'yè lǐ, tiān shàng yǒu yuè.',
        sceneBg: 'night',
        sceneAlt: '夜里，天上有月',
        scene: [
          { e: '🌙', x: 70, y: 24, s: 1.6, m: 'float' },
          { e: '⭐', x: 34, y: 30, s: 0.9, m: 'float' },
          { e: '🌳', x: 22, y: 76, s: 1.4 },
          { e: '🏠', x: 60, y: 84, s: 1.3 }
        ]
      },
      {
        emoji: '⭐', text: '夜里有星，星很多。', p: 'yè lǐ yǒu xīng, xīng hěn duō.',
        sceneBg: 'night',
        sceneAlt: '夜里有星，星很多',
        scene: [
          { e: '⭐', x: 24, y: 26, s: 0.9, m: 'float' },
          { e: '⭐', x: 52, y: 20, s: 1.1, m: 'float' },
          { e: '⭐', x: 78, y: 34, s: 0.8, m: 'float' },
          { e: '🌙', x: 44, y: 44, s: 1.2, m: 'float' },
          { e: '🏠', x: 56, y: 86, s: 1.2 }
        ]
      },
      {
        emoji: '💡', text: '夜里，屋里的灯亮了。', p: 'yè lǐ, wū lǐ de dēng liàng le.',
        sceneBg: 'room',
        sceneAlt: '屋里的灯亮了',
        scene: [
          { e: '💡', x: 50, y: 30, s: 1.7, m: 'float' },
          { e: '🪟', x: 20, y: 44, s: 1.2 },
          { e: '🛋️', x: 40, y: 80, s: 1.4 },
          { e: '🪑', x: 74, y: 86, s: 1.2 }
        ]
      },
      {
        emoji: '😴', text: '夜深了，我要睡了。', p: 'yè shēn le, wǒ yào shuì le.',
        sceneBg: 'night',
        sceneAlt: '夜深了，我要睡了',
        scene: [
          { e: '🌙', x: 78, y: 22, s: 1.1, m: 'float' },
          { e: '🪟', x: 22, y: 40, s: 1.2 },
          { e: '🧸', x: 74, y: 70, s: 1, m: 'float' },
          { e: '🛏️', x: 46, y: 80, s: 1.8 }
        ]
      }
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
      {
        emoji: '⬆️', text: '天在上边。', p: 'tiān zài shàng bian.',
        sceneBg: 'sky',
        sceneAlt: '天在上边',
        scene: [
          { e: '⬆️', x: 50, y: 26, s: 1.7, m: 'float' },
          { e: '☁️', x: 24, y: 34, s: 1.1, m: 'drift' },
          { e: '☀️', x: 80, y: 22, s: 1, m: 'float' },
          { e: '🌳', x: 34, y: 84, s: 1.3 }
        ]
      },
      {
        emoji: '⬇️', text: '地在下边。', p: 'dì zài xià bian.',
        sceneBg: 'field',
        sceneAlt: '地在下边',
        scene: [
          { e: '⬇️', x: 50, y: 58, s: 1.7, m: 'float' },
          { e: '🌿', x: 24, y: 82, s: 1.2, m: 'sway' },
          { e: '🪨', x: 74, y: 86, s: 1.1 },
          { e: '🌱', x: 46, y: 90, s: 1, m: 'sway' }
        ]
      },
      {
        emoji: '⬅️', text: '我的左手在左边。', p: 'wǒ de zuǒ shǒu zài zuǒ bian.',
        sceneBg: 'room',
        sceneAlt: '我的左手在左边',
        scene: [
          { e: '⬅️', x: 22, y: 46, s: 1.5, m: 'float' },
          { e: '✋', x: 34, y: 66, s: 1.6 },
          { e: '🧒', x: 62, y: 80, s: 1.5 }
        ]
      },
      {
        emoji: '➡️', text: '我的右手在右边。', p: 'wǒ de yòu shǒu zài yòu bian.',
        sceneBg: 'room',
        sceneAlt: '我的右手在右边',
        scene: [
          { e: '➡️', x: 80, y: 46, s: 1.5, m: 'float' },
          { e: '✋', x: 68, y: 66, s: 1.6 },
          { e: '🧒', x: 38, y: 80, s: 1.5 }
        ]
      },
      {
        emoji: '🚪', text: '前边有门，后边有窗。', p: 'qián bian yǒu mén, hòu bian yǒu chuāng.',
        sceneBg: 'room',
        sceneAlt: '前边有门，后边有窗',
        scene: [
          { e: '🪟', x: 78, y: 44, s: 1.4 },
          { e: '🚪', x: 34, y: 58, s: 1.8 },
          { e: '🧒', x: 56, y: 82, s: 1.4 },
          { e: '🪑', x: 84, y: 88, s: 1 }
        ]
      },
      {
        emoji: '🧭', text: '上下左右，我都会说！', p: 'shàng xià zuǒ yòu, wǒ dōu huì shuō!',
        sceneBg: 'room',
        sceneAlt: '上下左右我都会说',
        scene: [
          { e: '⬆️', x: 50, y: 28, s: 1.1, m: 'float' },
          { e: '⬅️', x: 24, y: 54, s: 1.1, m: 'float' },
          { e: '➡️', x: 76, y: 54, s: 1.1, m: 'float' },
          { e: '⬇️', x: 50, y: 92, s: 1.1, m: 'float' },
          { e: '🧒', x: 50, y: 68, s: 1.7 }
        ]
      }
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
      {
        emoji: '🏃', text: '我会走，也会跑。', p: 'wǒ huì zǒu, yě huì pǎo.',
        sceneBg: 'field',
        sceneAlt: '我会走，也会跑',
        scene: [
          { e: '🚶', x: 28, y: 72, s: 1.4 },
          { e: '🏃', x: 60, y: 78, s: 1.7, m: 'drift' },
          { e: '🌳', x: 84, y: 62, s: 1.3 },
          { e: '🌿', x: 18, y: 88, s: 1, m: 'sway' }
        ]
      },
      {
        emoji: '🤸', text: '我会跳，跳很高。', p: 'wǒ huì tiào, tiào hěn gāo.',
        sceneBg: 'field',
        sceneAlt: '我会跳，跳很高',
        scene: [
          { e: '✨', x: 66, y: 34, s: 0.9, m: 'float' },
          { e: '🤸', x: 50, y: 56, s: 1.8, m: 'float' },
          { e: '🌳', x: 20, y: 70, s: 1.4 },
          { e: '🌿', x: 76, y: 88, s: 1.1, m: 'sway' }
        ]
      },
      {
        emoji: '🪑', text: '我会坐，也会站。', p: 'wǒ huì zuò, yě huì zhàn.',
        sceneBg: 'room',
        sceneAlt: '我会坐，也会站',
        scene: [
          { e: '🧒', x: 68, y: 70, s: 1.5 },
          { e: '🪑', x: 32, y: 76, s: 1.5 },
          { e: '🛋️', x: 76, y: 88, s: 1.1 }
        ]
      },
      {
        emoji: '🍚', text: '我会吃饭，也会喝水。', p: 'wǒ huì chī fàn, yě huì hē shuǐ.',
        sceneBg: 'room',
        sceneAlt: '我会吃饭，也会喝水',
        scene: [
          { e: '🍚', x: 38, y: 62, s: 1.4 },
          { e: '🥛', x: 66, y: 64, s: 1.3, m: 'float' },
          { e: '🥢', x: 84, y: 76, s: 1 },
          { e: '🧒', x: 50, y: 84, s: 1.5 }
        ]
      },
      {
        emoji: '🎤', text: '我会唱歌，也会笑。', p: 'wǒ huì chàng gē, yě huì xiào.',
        sceneBg: 'room',
        sceneAlt: '我会唱歌，也会笑',
        scene: [
          { e: '🎵', x: 30, y: 36, s: 1, m: 'float' },
          { e: '🎤', x: 66, y: 56, s: 1.4, m: 'float' },
          { e: '🧒', x: 46, y: 78, s: 1.6 },
          { e: '😄', x: 80, y: 84, s: 1.2, m: 'float' }
        ]
      },
      {
        emoji: '😄', text: '我会的真多！', p: 'wǒ huì de zhēn duō!',
        sceneBg: 'field',
        sceneAlt: '我会的真多',
        scene: [
          { e: '🎵', x: 74, y: 32, s: 0.9, m: 'float' },
          { e: '🤸', x: 26, y: 58, s: 1.2, m: 'float' },
          { e: '🏃', x: 68, y: 68, s: 1.2, m: 'drift' },
          { e: '🎤', x: 84, y: 82, s: 1 },
          { e: '😄', x: 46, y: 84, s: 1.6, m: 'float' }
        ]
      }
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
      {
        emoji: '🐛', text: '一只小虫在叶上。', p: 'yī zhī xiǎo chóng zài yè shàng.',
        sceneBg: 'field',
        sceneAlt: '一只小虫在叶上',
        scene: [
          { e: '🌳', x: 78, y: 56, s: 1.4 },
          { e: '🍃', x: 46, y: 70, s: 1.4, m: 'sway' },
          { e: '🐛', x: 46, y: 62, s: 1.1, m: 'sway' },
          { e: '🌿', x: 20, y: 86, s: 1.1, m: 'sway' }
        ]
      },
      {
        emoji: '🐜', text: '二只蚁在地上。', p: 'èr zhī yǐ zài dì shàng.',
        sceneBg: 'field',
        sceneAlt: '二只蚁在地上',
        scene: [
          { e: '🌿', x: 22, y: 74, s: 1.1, m: 'sway' },
          { e: '🪨', x: 80, y: 72, s: 1 },
          { e: '🐜', x: 44, y: 82, s: 0.9, m: 'drift' },
          { e: '🐜', x: 62, y: 88, s: 0.8, m: 'drift' }
        ]
      },
      {
        emoji: '🐝', text: '三只蜂在花上。', p: 'sān zhī fēng zài huā shàng.',
        sceneBg: 'field',
        sceneAlt: '三只蜂在花上',
        scene: [
          { e: '🐝', x: 40, y: 44, s: 1, m: 'float' },
          { e: '🐝', x: 62, y: 52, s: 0.9, m: 'float' },
          { e: '🐝', x: 78, y: 40, s: 0.8, m: 'float' },
          { e: '🌻', x: 34, y: 78, s: 1.4, m: 'sway' },
          { e: '🌸', x: 70, y: 86, s: 1.1, m: 'sway' }
        ]
      },
      {
        emoji: '🦋', text: '四只蝶在风里。', p: 'sì zhī dié zài fēng lǐ.',
        sceneBg: 'sky',
        sceneAlt: '四只蝶在风里',
        scene: [
          { e: '🦋', x: 30, y: 34, s: 1, m: 'float' },
          { e: '🦋', x: 54, y: 46, s: 1.1, m: 'float' },
          { e: '🦋', x: 74, y: 32, s: 0.9, m: 'float' },
          { e: '🦋', x: 62, y: 62, s: 0.8, m: 'float' },
          { e: '🌸', x: 40, y: 86, s: 1.1, m: 'sway' }
        ]
      },
      {
        emoji: '🔢', text: '我数一数：一，二，三，四。', p: 'wǒ shǔ yī shǔ: yī, èr, sān, sì.',
        sceneBg: 'field',
        sceneAlt: '我数一数',
        scene: [
          { e: '🐛', x: 24, y: 58, s: 0.9, m: 'sway' },
          { e: '🐜', x: 44, y: 66, s: 0.8, m: 'drift' },
          { e: '🐝', x: 64, y: 58, s: 0.9, m: 'float' },
          { e: '🦋', x: 82, y: 48, s: 1, m: 'float' },
          { e: '🧒', x: 50, y: 84, s: 1.6 }
        ]
      },
      {
        emoji: '🌸', text: '一共十只小虫！', p: 'yī gòng shí zhī xiǎo chóng!',
        sceneBg: 'field',
        sceneAlt: '一共十只小虫',
        scene: [
          { e: '🦋', x: 32, y: 38, s: 0.9, m: 'float' },
          { e: '🐝', x: 66, y: 44, s: 0.9, m: 'float' },
          { e: '🐛', x: 22, y: 70, s: 0.9, m: 'sway' },
          { e: '🐜', x: 50, y: 78, s: 0.8, m: 'drift' },
          { e: '🌸', x: 78, y: 78, s: 1.1, m: 'sway' },
          { e: '🌿', x: 44, y: 90, s: 1, m: 'sway' }
        ]
      }
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
      {
        emoji: '⭕', text: '日是圆的。', p: 'rì shì yuán de.',
        sceneBg: 'sky',
        sceneAlt: '日是圆的',
        scene: [
          { e: '☀️', x: 52, y: 32, s: 2, m: 'float' },
          { e: '☁️', x: 22, y: 30, s: 1.1, m: 'drift' },
          { e: '🌳', x: 34, y: 84, s: 1.3 }
        ]
      },
      {
        emoji: '🌕', text: '月也会是圆的。', p: 'yuè yě huì shì yuán de.',
        sceneBg: 'night',
        sceneAlt: '月也是圆的',
        scene: [
          { e: '🌕', x: 52, y: 32, s: 1.9, m: 'float' },
          { e: '⭐', x: 22, y: 26, s: 0.8, m: 'float' },
          { e: '🏠', x: 56, y: 84, s: 1.3 }
        ]
      },
      {
        emoji: '🔲', text: '窗是方的。', p: 'chuāng shì fāng de.',
        sceneBg: 'room',
        sceneAlt: '窗是方的',
        scene: [
          { e: '🪟', x: 48, y: 48, s: 2 },
          { e: '🪑', x: 24, y: 84, s: 1.2 },
          { e: '🛋️', x: 72, y: 88, s: 1.2 }
        ]
      },
      {
        emoji: '📦', text: '箱是方的。', p: 'xiāng shì fāng de.',
        sceneBg: 'room',
        sceneAlt: '箱是方的',
        scene: [
          { e: '📦', x: 44, y: 62, s: 1.8 },
          { e: '📦', x: 72, y: 80, s: 1.2 },
          { e: '🪑', x: 22, y: 84, s: 1.1 }
        ]
      },
      {
        emoji: '⚽', text: '球是圆的，我会打球。', p: 'qiú shì yuán de, wǒ huì dǎ qiú.',
        sceneBg: 'field',
        sceneAlt: '球是圆的，我会打球',
        scene: [
          { e: '☀️', x: 82, y: 20, s: 1, m: 'float' },
          { e: '⚽', x: 66, y: 74, s: 1.5, m: 'drift' },
          { e: '🧒', x: 34, y: 76, s: 1.6 },
          { e: '🌳', x: 16, y: 62, s: 1.3 }
        ]
      },
      {
        emoji: '🍽️', text: '碗是圆的，桌是方的。', p: 'wǎn shì yuán de, zhuō shì fāng de.',
        sceneBg: 'room',
        sceneAlt: '碗是圆的，桌是方的',
        scene: [
          { e: '🥣', x: 42, y: 62, s: 1.6 },
          { e: '🍚', x: 66, y: 68, s: 1.2 },
          { e: '🥢', x: 82, y: 78, s: 1 },
          { e: '📦', x: 20, y: 84, s: 1.1 }
        ]
      },
      {
        emoji: '👀', text: '圆的方的，我都认识。', p: 'yuán de fāng de, wǒ dōu rèn shi.',
        sceneBg: 'room',
        sceneAlt: '圆的方的我都认识',
        scene: [
          { e: '⭕', x: 28, y: 44, s: 1.3, m: 'float' },
          { e: '🔲', x: 72, y: 44, s: 1.3, m: 'float' },
          { e: '⚽', x: 20, y: 78, s: 1 },
          { e: '📦', x: 80, y: 80, s: 1 },
          { e: '🧒', x: 50, y: 80, s: 1.6 }
        ]
      }
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
      {
        emoji: '❄️', text: '冬天很冷。', p: 'dōng tiān hěn lěng.',
        sceneBg: 'snow',
        sceneAlt: '冬天很冷',
        scene: [
          { e: '❄️', x: 28, y: 28, s: 1, m: 'float' },
          { e: '❄️', x: 72, y: 38, s: 0.8, m: 'float' },
          { e: '🌲', x: 20, y: 70, s: 1.6 },
          { e: '⛄', x: 58, y: 80, s: 1.6 }
        ]
      },
      {
        emoji: '🧣', text: '天冷了，我要帽，也要一身厚衣。', p: 'tiān lěng le, wǒ yào mào, yě yào yī shēn hòu yī.',
        sceneBg: 'snow',
        sceneAlt: '天冷了，我要帽和厚衣',
        scene: [
          { e: '❄️', x: 78, y: 28, s: 0.8, m: 'float' },
          { e: '🧢', x: 50, y: 44, s: 1.2, m: 'float' },
          { e: '🧣', x: 74, y: 66, s: 1.2, m: 'sway' },
          { e: '🧒', x: 42, y: 78, s: 1.7 }
        ]
      },
      {
        emoji: '☀️', text: '夏天很热。', p: 'xià tiān hěn rè.',
        sceneBg: 'field',
        sceneAlt: '夏天很热',
        scene: [
          { e: '☀️', x: 66, y: 24, s: 2, m: 'float' },
          { e: '🌳', x: 22, y: 66, s: 1.6 },
          { e: '🌻', x: 76, y: 80, s: 1.3, m: 'sway' },
          { e: '🌿', x: 40, y: 88, s: 1.1, m: 'sway' }
        ]
      },
      {
        emoji: '🍉', text: '天热了，我吃瓜，也喝水。', p: 'tiān rè le, wǒ chī guā, yě hē shuǐ.',
        sceneBg: 'field',
        sceneAlt: '天热了，我吃瓜',
        scene: [
          { e: '☀️', x: 82, y: 20, s: 1.2, m: 'float' },
          { e: '🍉', x: 66, y: 66, s: 1.4, m: 'float' },
          { e: '🥛', x: 24, y: 72, s: 1.1 },
          { e: '🧒', x: 46, y: 82, s: 1.6 }
        ]
      },
      {
        emoji: '🔥', text: '火很热，我不去摸。', p: 'huǒ hěn rè, wǒ bù qù mō.',
        sceneBg: 'room',
        sceneAlt: '火很热，我不去摸',
        scene: [
          { e: '🔥', x: 64, y: 62, s: 1.6, m: 'float' },
          { e: '🧒', x: 32, y: 78, s: 1.6 },
          { e: '🪑', x: 84, y: 86, s: 1.1 }
        ]
      },
      {
        emoji: '🌡️', text: '冷和热，我都能说。', p: 'lěng hé rè, wǒ dōu néng shuō.',
        sceneBg: 'room',
        sceneAlt: '冷和热，我都能说',
        scene: [
          { e: '❄️', x: 26, y: 44, s: 1.2, m: 'float' },
          { e: '🔥', x: 74, y: 46, s: 1.3, m: 'float' },
          { e: '🌡️', x: 50, y: 62, s: 1.3, m: 'sway' },
          { e: '🧒', x: 50, y: 84, s: 1.5 }
        ]
      }
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
      {
        emoji: '🐱', text: '我家有一只猫。', p: 'wǒ jiā yǒu yī zhī māo.',
        sceneBg: 'room',
        sceneAlt: '我家有一只猫',
        scene: [
          { e: '🪟', x: 78, y: 40, s: 1.1 },
          { e: '🐱', x: 48, y: 68, s: 1.7, m: 'float' },
          { e: '🛋️', x: 26, y: 84, s: 1.3 }
        ]
      },
      {
        emoji: '🐶', text: '我家有一只狗。', p: 'wǒ jiā yǒu yī zhī gǒu.',
        sceneBg: 'room',
        sceneAlt: '我家有一只狗',
        scene: [
          { e: '🚪', x: 78, y: 54, s: 1.4 },
          { e: '🐶', x: 46, y: 72, s: 1.7, m: 'float' },
          { e: '🪑', x: 22, y: 86, s: 1.2 }
        ]
      },
      {
        emoji: '🐟', text: '猫爱吃鱼。', p: 'māo ài chī yú.',
        sceneBg: 'room',
        sceneAlt: '猫爱吃鱼',
        scene: [
          { e: '🐱', x: 40, y: 62, s: 1.6 },
          { e: '🐟', x: 68, y: 76, s: 1.2, m: 'sway' },
          { e: '🥣', x: 68, y: 88, s: 1.2 }
        ]
      },
      {
        emoji: '🍖', text: '狗爱吃肉。', p: 'gǒu ài chī ròu.',
        sceneBg: 'room',
        sceneAlt: '狗爱吃肉',
        scene: [
          { e: '🐶', x: 40, y: 62, s: 1.6 },
          { e: '🍖', x: 68, y: 76, s: 1.2, m: 'float' },
          { e: '🥣', x: 68, y: 88, s: 1.2 }
        ]
      },
      {
        emoji: '😺', text: '猫在椅上睡。', p: 'māo zài yǐ shàng shuì.',
        sceneBg: 'room',
        sceneAlt: '猫在椅上睡',
        scene: [
          { e: '🪟', x: 22, y: 38, s: 1.1 },
          { e: '💤', x: 70, y: 52, s: 1, m: 'float' },
          { e: '🐱', x: 54, y: 68, s: 1.4, m: 'float' },
          { e: '🪑', x: 54, y: 84, s: 1.6 }
        ]
      },
      {
        emoji: '🐕', text: '狗在门口看家。', p: 'gǒu zài mén kǒu kàn jiā.',
        sceneBg: 'room',
        sceneAlt: '狗在门口看家',
        scene: [
          { e: '🌳', x: 84, y: 34, s: 1.1 },
          { e: '🪟', x: 76, y: 52, s: 1.1 },
          { e: '🚪', x: 34, y: 58, s: 1.8 },
          { e: '🐶', x: 58, y: 82, s: 1.4 }
        ]
      },
      {
        emoji: '❤️', text: '猫和狗都是我的伙伴。', p: 'māo hé gǒu dōu shì wǒ de huǒ bàn.',
        sceneBg: 'room',
        sceneAlt: '猫和狗都是我的伙伴',
        scene: [
          { e: '❤️', x: 50, y: 34, s: 1, m: 'float' },
          { e: '🐱', x: 26, y: 70, s: 1.3, m: 'float' },
          { e: '🐶', x: 74, y: 74, s: 1.3, m: 'float' },
          { e: '🧒', x: 50, y: 82, s: 1.6 }
        ]
      }
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
      {
        emoji: '🌅', text: '早上，日来了。', p: 'zǎo shang, rì lái le.',
        sceneBg: 'dawn',
        sceneAlt: '早上，日来了',
        scene: [
          { e: '☀️', x: 62, y: 30, s: 1.7, m: 'float' },
          { e: '⛰️', x: 22, y: 52, s: 1.6 },
          { e: '🐦', x: 80, y: 40, s: 0.9, m: 'float' },
          { e: '🌳', x: 44, y: 84, s: 1.3 }
        ]
      },
      {
        emoji: '🥣', text: '早上，我吃饭。', p: 'zǎo shang, wǒ chī fàn.',
        sceneBg: 'room',
        sceneAlt: '早上，我吃饭',
        scene: [
          { e: '🪟', x: 80, y: 38, s: 1.1 },
          { e: '🥣', x: 42, y: 64, s: 1.5 },
          { e: '🥢', x: 68, y: 74, s: 1 },
          { e: '🧒', x: 30, y: 82, s: 1.5 }
        ]
      },
      {
        emoji: '🎒', text: '早上，我去学校。', p: 'zǎo shang, wǒ qù xué xiào.',
        sceneBg: 'sky',
        sceneAlt: '早上，我去学校',
        scene: [
          { e: '☁️', x: 26, y: 24, s: 1.1, m: 'drift' },
          { e: '🏫', x: 74, y: 60, s: 1.7 },
          { e: '🎒', x: 34, y: 72, s: 1.1 },
          { e: '🧒', x: 38, y: 84, s: 1.5 }
        ]
      },
      {
        emoji: '🌇', text: '晚上，日下山了。', p: 'wǎn shang, rì xià shān le.',
        sceneBg: 'dusk',
        sceneAlt: '晚上，日下山了',
        scene: [
          { e: '☀️', x: 68, y: 46, s: 1.3, m: 'float' },
          { e: '⛰️', x: 30, y: 56, s: 1.7 },
          { e: '🐦', x: 20, y: 34, s: 0.8, m: 'float' },
          { e: '🌳', x: 76, y: 84, s: 1.2 }
        ]
      },
      {
        emoji: '📖', text: '晚上，我读书。', p: 'wǎn shang, wǒ dú shū.',
        sceneBg: 'room',
        sceneAlt: '晚上，我读书',
        scene: [
          { e: '💡', x: 72, y: 30, s: 1.2, m: 'float' },
          { e: '📖', x: 48, y: 64, s: 1.5 },
          { e: '🧒', x: 30, y: 76, s: 1.5 },
          { e: '🪑', x: 74, y: 86, s: 1.1 }
        ]
      },
      {
        emoji: '🛏️', text: '晚上，我在床上睡。', p: 'wǎn shang, wǒ zài chuáng shàng shuì.',
        sceneBg: 'night',
        sceneAlt: '晚上，我在床上睡',
        scene: [
          { e: '🌙', x: 76, y: 24, s: 1.2, m: 'float' },
          { e: '🪟', x: 24, y: 40, s: 1.2 },
          { e: '🧸', x: 74, y: 70, s: 1, m: 'float' },
          { e: '🛏️', x: 44, y: 80, s: 1.8 }
        ]
      }
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
      {
        emoji: '🔔', text: '铃有声音。', p: 'líng yǒu shēng yīn.',
        sceneBg: 'room',
        sceneAlt: '铃有声音',
        scene: [
          { e: '🔔', x: 50, y: 52, s: 1.8, m: 'sway' },
          { e: '🎵', x: 76, y: 38, s: 1, m: 'float' },
          { e: '🪟', x: 22, y: 44, s: 1.1 }
        ]
      },
      {
        emoji: '🐦', text: '鸟的声音很好听。', p: 'niǎo de shēng yīn hěn hǎo tīng.',
        sceneBg: 'sky',
        sceneAlt: '鸟的声音很好听',
        scene: [
          { e: '☁️', x: 24, y: 24, s: 1.1, m: 'drift' },
          { e: '🐦', x: 56, y: 38, s: 1.4, m: 'float' },
          { e: '🎵', x: 78, y: 28, s: 0.9, m: 'float' },
          { e: '🌳', x: 34, y: 82, s: 1.5 }
        ]
      },
      {
        emoji: '🌧️', text: '雨的声音在窗外。', p: 'yǔ de shēng yīn zài chuāng wài.',
        sceneBg: 'storm',
        sceneAlt: '雨的声音在窗外',
        scene: [
          { e: '🌧️', x: 66, y: 28, s: 1.4, m: 'drift' },
          { e: '💧', x: 74, y: 52, s: 0.8, m: 'float' },
          { e: '🪟', x: 38, y: 58, s: 1.8 },
          { e: '🌳', x: 84, y: 78, s: 1.1 }
        ]
      },
      {
        emoji: '🎵', text: '妈妈的歌很好听。', p: 'mā ma de gē hěn hǎo tīng.',
        sceneBg: 'room',
        sceneAlt: '妈妈的歌很好听',
        scene: [
          { e: '🎶', x: 30, y: 34, s: 1, m: 'float' },
          { e: '🎵', x: 74, y: 40, s: 0.9, m: 'float' },
          { e: '👩', x: 62, y: 72, s: 1.6 },
          { e: '🧒', x: 34, y: 82, s: 1.3 }
        ]
      },
      {
        emoji: '🥁', text: '鼓的声音很重。', p: 'gǔ de shēng yīn hěn zhòng.',
        sceneBg: 'room',
        sceneAlt: '鼓的声音很重',
        scene: [
          { e: '🎵', x: 76, y: 40, s: 0.9, m: 'float' },
          { e: '🥁', x: 52, y: 66, s: 1.7 },
          { e: '🧒', x: 24, y: 80, s: 1.4 }
        ]
      },
      {
        emoji: '👂', text: '我用耳听，声音真多。', p: 'wǒ yòng ěr tīng, shēng yīn zhēn duō.',
        sceneBg: 'room',
        sceneAlt: '我用耳听，声音真多',
        scene: [
          { e: '🎵', x: 34, y: 32, s: 0.9, m: 'float' },
          { e: '🐦', x: 76, y: 40, s: 0.9, m: 'float' },
          { e: '👂', x: 50, y: 58, s: 1.7, m: 'float' },
          { e: '🔔', x: 22, y: 76, s: 1.1, m: 'sway' },
          { e: '🥁', x: 78, y: 82, s: 1.1 }
        ]
      }
    ]
  }
]
