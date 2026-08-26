/**
 * 单元「常用小词」的字义、组词与例句。
 *
 * 只有真正翻到这个单元（或打开单元里某个字）时才会加载，
 * 字表索引在 ../char-index.js。
 */

export default {
  '这': {
    meaning: '指离自己近的人或东西。',
    words: [
      { w: '这个', p: 'zhè ge' },
      { w: '这里', p: 'zhè lǐ' },
      { w: '这些', p: 'zhè xiē' }
    ],
    sentence: { text: '这是我的本子。', p: 'zhè shì wǒ de běn zi.' }
  },
  '那': {
    meaning: '指离自己远的人或东西。',
    words: [
      { w: '那个', p: 'nà ge' },
      { w: '那里', p: 'nà lǐ' },
      { w: '那天', p: 'nà tiān' }
    ],
    sentence: { text: '那是老师的书。', p: 'nà shì lǎo shī de shū.' }
  },
  '什': {
    meaning: '和「么」连在一起，用来问事情。',
    words: [
      { w: '什么', p: 'shén me' },
      { w: '为什么', p: 'wèi shén me' },
      { w: '什么时候', p: 'shén me shí hou' }
    ],
    sentence: { text: '这是什么？', p: 'zhè shì shén me?' }
  },
  '么': {
    meaning: '常跟在「什、怎、这」后面，读轻声。',
    words: [
      { w: '什么', p: 'shén me' },
      { w: '怎么', p: 'zěn me' },
      { w: '这么', p: 'zhè me' }
    ],
    sentence: { text: '你想吃什么？', p: 'nǐ xiǎng chī shén me?' }
  },
  '都': {
    meaning: '表示全部，一个也不少。',
    words: [
      { w: '都是', p: 'dōu shì' },
      { w: '都好', p: 'dōu hǎo' },
      { w: '都来', p: 'dōu lái' }
    ],
    sentence: { text: '我们都很开心。', p: 'wǒ men dōu hěn kāi xīn.' }
  },
  '要': {
    meaning: '想得到，也表示应该、将要。',
    words: [
      { w: '要好', p: 'yào hǎo' },
      { w: '不要', p: 'bù yào' },
      { w: '要来', p: 'yào lái' }
    ],
    sentence: { text: '我要一杯水。', p: 'wǒ yào yī bēi shuǐ.' }
  },
  '能': {
    meaning: '做得到、可以。',
    words: [
      { w: '能行', p: 'néng xíng' },
      { w: '不能', p: 'bù néng' },
      { w: '能干', p: 'néng gàn' }
    ],
    sentence: { text: '我能自己走去学校。', p: 'wǒ néng zì jǐ zǒu qù xué xiào.' }
  },
  '想': {
    meaning: '在心里琢磨，也表示很希望。',
    words: [
      { w: '想想', p: 'xiǎng xiang' },
      { w: '想家', p: 'xiǎng jiā' },
      { w: '想学', p: 'xiǎng xué' }
    ],
    sentence: { text: '我想学会写这个字。', p: 'wǒ xiǎng xué huì xiě zhè ge zì.' }
  },
  '用': {
    meaning: '拿东西来做事，就是用。',
    words: [
      { w: '有用', p: 'yǒu yòng' },
      { w: '用心', p: 'yòng xīn' },
      { w: '用手', p: 'yòng shǒu' }
    ],
    sentence: { text: '我用右手写字。', p: 'wǒ yòng yòu shǒu xiě zì.' }
  },
  '做': {
    meaning: '动手去干一件事。',
    words: [
      { w: '做事', p: 'zuò shì' },
      { w: '做好', p: 'zuò hǎo' },
      { w: '做饭', p: 'zuò fàn' }
    ],
    sentence: { text: '母亲在做饭。', p: 'mǔ qīn zài zuò fàn.' }
  },
  '给': {
    meaning: '把东西交到别人手里。',
    words: [
      { w: '给你', p: 'gěi nǐ' },
      { w: '给我', p: 'gěi wǒ' },
      { w: '送给', p: 'sòng gěi' }
    ],
    sentence: { text: '我把苹果给妹妹。', p: 'wǒ bǎ píng guǒ gěi mèi mei.' }
  },
  '把': {
    meaning: '「把书拿来」里的把，用来提前说出被动作的东西。',
    words: [
      { w: '一把', p: 'yī bǎ' },
      { w: '把手', p: 'bǎ shǒu' },
      { w: '把门', p: 'bǎ mén' }
    ],
    sentence: { text: '请把书放在桌上。', p: 'qǐng bǎ shū fàng zài zhuō shàng.' }
  }
}
