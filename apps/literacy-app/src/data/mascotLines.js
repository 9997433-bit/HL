/**
 * 学伴墨墨的陪跑台词。
 *
 * 分两层：
 *  - 「场景」按路由走（首页说去哪儿玩，绘本页说怎么读），一进页面就有话说；
 *  - 「阶段」按孩子此刻的状态走（刚开新字、连着答对、复习欠账、坐太久、
 *    答错卡住、好久没来……），同一个页面在不同状态下听到的是不同的墨墨。
 *
 * 阶段这一层是墨墨「有人格」的地方：它不复读固定鼓励语，而是先判断
 * 现在最该说哪一类话，再从那一类里轮着说。`pickMascotStage()` 就是这个判断，
 * 界面不必自己写一堆 if。
 *
 * 台词里不放 emoji：这些句子会直接交给 SpeechSynthesis 念，
 * 表情符号有的读作「笑脸」，有的干脆卡住，写成纯文字最稳。
 */

/** 阶段剧本的版本标记，随台词一起返回，探针与证据回填都认它。 */
export const ROUND16_H6_STAGE_SCRIPT = 'ROUND16_H6'

const trim = (list) => list.filter((line) => typeof line === 'string' && line.trim())

/** 名字可能是空的（家长没填），拼进句子前先兜一个称呼。 */
const who = (name) => (name && name.trim() ? name.trim() : '小朋友')

export const MASCOT_SCENES = {
  home: (ctx) =>
    trim([
      `${who(ctx.name)}，今天也来啦，我们一起去认几个新字吧。`,
      ctx.due > 0 && `有 ${ctx.due} 个字在等你复习，先把它们接回家好不好？`,
      ctx.streak > 1 && `你已经连着来了 ${ctx.streak} 天，坚持得真棒。`,
      ctx.learned > 0 && `我数了数，你已经认识 ${ctx.learned} 个字了。`,
      '点地图上的小站，就能开始今天的冒险。',
      '学累了就歇一会儿，我在这里等你。'
    ]),

  learn: (ctx) =>
    trim([
      '认一个字分三步：先看图，再听音，最后写一写。',
      ctx.nextChar && `要不要先学「${ctx.nextChar}」？我陪着你。`,
      ctx.due > 0 && `别忘了「要复习」里还有 ${ctx.due} 个老朋友。`,
      '写错了没关系，我们再来一次就好。',
      '笔顺跟着我慢慢走，写出来更好看。'
    ]),

  games: (ctx) =>
    trim([
      '玩游戏也是在识字，放心大胆地玩。',
      ctx.learned < 4
        ? '再学几个字，游戏里的题目就更热闹啦。'
        : `游戏里现在能出 ${ctx.learned} 个字的题目。`,
      '听音识字最练耳朵，听清楚了再选。',
      '在迷宫里迷路了？先想想那个字长什么样。',
      '配对记忆考眼力，记住卡片翻开的位置。'
    ]),

  books: (ctx) =>
    trim([
      '绘本里的字都是你学过的，一定读得下来。',
      ctx.books > 0 && `你已经读完 ${ctx.books} 本啦，今天再来一本吗？`,
      '读的时候用手指着字，一个一个读出声。',
      '遇到不认识的字就点一下，我来告诉你怎么读。',
      '读完一本，可以讲给爸爸妈妈听。'
    ]),

  idioms: (ctx) =>
    trim([
      '成语是四个字的小故事，听完你就懂了。',
      ctx.idioms > 0 && `你已经收下 ${ctx.idioms} 个成语故事，很厉害。`,
      '先看小剧场，再答一道题，就算学会啦。',
      '把成语讲给别人听一遍，记得最牢。',
      '不着急，一天认识一个成语就很棒。'
    ]),

  poems: (ctx) =>
    trim([
      '古诗要读出声才好听，我们一句一句来。',
      ctx.poems > 0 && `你已经读过 ${ctx.poems} 首诗了，今天再来一首吗？`,
      '先听我读一遍，你再跟着读，读错了没关系。',
      '诗里有没学过的字也不怕，点一下我就告诉你怎么念。',
      '会背了就读给爸爸妈妈听，他们一定很高兴。'
    ]),

  songs: (ctx) =>
    trim([
      '儿歌里的字都是你学过的，放开嗓子唱就行。',
      ctx.songs > 0 && `你已经唱会 ${ctx.songs} 首啦，今天换一首试试吗？`,
      '哪个字亮起来就唱哪个字，慢慢跟上调子。',
      '跑调也没关系，唱得开心比唱得准要紧。',
      '学会一首就唱给家里人听，他们准要拍手。'
    ])
}

/**
 * 阶段剧本。
 *
 * `when` 判断此刻是不是这个阶段，`lines` 给这个阶段的台词。
 * 数组顺序就是优先级：越靠前越「打断」后面的——孩子坐了半小时还在硬撑时，
 * 「该歇歇了」比「还有 3 个字要复习」重要得多。
 */
export const MASCOT_STAGES = [
  {
    id: 'comeback',
    label: '久别重逢',
    when: (ctx) => (ctx.daysAway ?? 0) >= 3,
    lines: (ctx) =>
      trim([
        `好久不见，${who(ctx.name)}，你的字我都替你收着呢。`,
        (ctx.daysAway ?? 0) > 0 && `你有 ${ctx.daysAway} 天没来啦，我们先认几个老字热热身。`,
        '忘掉的字不算丢，再认一次它就回来了。',
        '先别急着学新字，把上次学的捡起来更要紧。'
      ])
  },
  {
    id: 'fatigue',
    label: '该歇歇了',
    when: (ctx) => Boolean(ctx.restDue) || (ctx.sessionMinutes ?? 0) >= 15,
    lines: (ctx) =>
      trim([
        (ctx.sessionMinutes ?? 0) > 0
          ? `我们已经连着学了 ${ctx.sessionMinutes} 分钟，眼睛要歇一歇了。`
          : '学了好一会儿了，眼睛要歇一歇。',
        '站起来走两步，看看远处的绿色，再回来找我。',
        '累的时候记不住字，歇一下反而学得快。',
        '去喝口水吧，我就在这儿等你。',
        '今天学得够多啦，剩下的留给明天也不亏。'
      ])
  },
  {
    id: 'mastered',
    label: '刚掌握',
    when: (ctx) => Boolean(ctx.justMastered),
    lines: (ctx) =>
      trim([
        ctx.lastChar
          ? `「${ctx.lastChar}」你已经真掌握了，可以骄傲一下。`
          : '这个字你已经真掌握了，可以骄傲一下。',
        (ctx.mastered ?? 0) > 0 && `你已经掌握 ${ctx.mastered} 个字，这可不是小数目。`,
        '掌握了的字也会慢慢变淡，过几天我再喊你来看一眼。',
        '把刚学会的字写给家里人看，他们准要惊讶。'
      ])
  },
  {
    id: 'combo',
    label: '连着答对',
    when: (ctx) => (ctx.combo ?? 0) >= 3,
    lines: (ctx) =>
      trim([
        `连着答对 ${ctx.combo} 个啦，你今天状态真好。`,
        '太顺了，我都快跟不上你的速度了。',
        '连对的时候也别飘，下一题还是读完再选。',
        '这一串答对说明你是真记住了，不是蒙的。',
        '再对两个，我就要给你鼓掌了。'
      ])
  },
  {
    id: 'encourage',
    label: '答错了',
    when: (ctx) => (ctx.recentWrong ?? 0) > 0,
    lines: (ctx) =>
      trim([
        ctx.lastChar
          ? `「${ctx.lastChar}」认错了不要紧，我小时候也常把它看岔。`
          : '错一个字不要紧，我小时候也常常认岔。',
        '我们再看一遍这个字，这次一定能记住。',
        '不会只是还没学会，不是学不会。',
        (ctx.learned ?? 0) > 0
          ? `你已经认识 ${ctx.learned} 个字了，慢一点也在往前走。`
          : '慢一点没关系，你正在往前走。',
        '先深呼吸，再看一遍题目，答案就藏在里面。'
      ])
  },
  {
    id: 'review',
    label: '要复习',
    when: (ctx) => (ctx.due ?? 0) > 0,
    lines: (ctx) =>
      trim([
        `有 ${ctx.due} 个老朋友在等你，先去打个招呼吧。`,
        '复习不是重学一遍，是把快忘的字捞回来。',
        '想不起来也别急，看一眼答案再记一次就好。',
        '今天把它们复习完，明天它们就不容易跑掉了。',
        '复习过的字会记得更久，这是记忆曲线告诉我的。'
      ])
  },
  {
    id: 'finish',
    label: '今天够了',
    when: (ctx) => Boolean(ctx.dailyLimitReached),
    lines: (ctx) =>
      trim([
        '今天的新字学完啦，剩下的时间读本绘本吧。',
        (ctx.streak ?? 0) > 1
          ? `连着来了 ${ctx.streak} 天，这个习惯比多认几个字更值钱。`
          : '明天再来，我们就算连上两天啦。',
        '今天到这里就很好，认字是长跑不是冲刺。',
        '走之前挑一个今天最喜欢的字，读三遍再关掉。'
      ])
  },
  {
    id: 'newChar',
    label: '要学新字',
    when: (ctx) => Boolean(ctx.nextChar),
    lines: (ctx) =>
      trim([
        `今天的新朋友是「${ctx.nextChar}」，我们先看看它长什么样。`,
        '新字先认样子，再认声音，最后才动手写。',
        '刚见面觉得陌生很正常，多看两眼它就熟了。',
        (ctx.newCharsToday ?? 0) > 0
          ? `今天已经认下 ${ctx.newCharsToday} 个新字，这个是加餐。`
          : '今天的第一个新字，我们慢慢来。',
        '认完这个新字，记得自己再读一遍给我听。'
      ])
  },
  {
    id: 'idle',
    label: '随便聊聊',
    when: () => true,
    lines: (ctx) =>
      trim([
        `我是墨墨，${who(ctx.name)}学字的时候我一直都在。`,
        '每个字都藏着一幅小画，看久了就能看出来。',
        '想听哪个字的故事？点一下它我就讲。',
        '慢慢来，认字这件事急不得。'
      ])
  }
]

/** 阶段 id → 定义，`mascotStageLines('review')` 这种直接点名的写法用它。 */
const STAGE_BY_ID = Object.fromEntries(MASCOT_STAGES.map((s) => [s.id, s]))

/**
 * 按当前状态挑出该说哪一类话。
 * 永远有结果：最后一个阶段 `idle` 的 `when` 恒为真。
 */
export function pickMascotStage(ctx = {}) {
  const stage = MASCOT_STAGES.find((s) => s.when(ctx)) ?? STAGE_BY_ID.idle
  return { id: stage.id, label: stage.label, script: ROUND16_H6_STAGE_SCRIPT }
}

/** 某个阶段的台词；不传阶段名就按当前状态自己挑一个。 */
export function mascotStageLines(stageId, ctx = {}) {
  const stage = STAGE_BY_ID[stageId] ?? STAGE_BY_ID[pickMascotStage(ctx).id]
  return stage ? stage.lines(ctx) : []
}

/** 阶段台词的总条数，验收与证据回填直接读它，不必去数源码里的引号。 */
export function countMascotStageLines(ctx = {}) {
  const probe = {
    name: '小朋友',
    nextChar: '人',
    lastChar: '人',
    learned: 12,
    mastered: 5,
    due: 3,
    streak: 4,
    combo: 5,
    daysAway: 5,
    sessionMinutes: 20,
    newCharsToday: 2,
    ...ctx
  }
  return MASCOT_STAGES.reduce((n, s) => n + s.lines(probe).length, 0)
}

/**
 * 取台词：当前阶段的话排在前面，场景常驻语垫在后面。
 * 场景名写错时退回首页那组，界面上永远有话可说。
 */
export function mascotLines(scene, ctx = {}) {
  const build = MASCOT_SCENES[scene] ?? MASCOT_SCENES.home
  const stage = pickMascotStage(ctx)
  return [...mascotStageLines(stage.id, ctx), ...build(ctx)]
}
