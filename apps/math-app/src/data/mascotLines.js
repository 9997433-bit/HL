/**
 * 吉祥物「小算」的陪跑台词。
 *
 * 和识字 App 的墨墨同一套结构，分两层：
 *  - 「场景」按路由走（首页讲今天去哪颗星球，答题页讲怎么想）；
 *  - 「阶段」按孩子此刻的状态走（连着答对、错题欠账、坐太久、好久没来……）。
 *
 * 阶段这一层让小算不只是个会说吉祥话的摆设：它先判断现在最该说哪一类话，
 * 再从那一类里轮着说。`pickMascotStage()` 就是这个判断。
 *
 * 台词里不放 emoji：这些句子会直接交给 SpeechSynthesis 念，
 * 表情符号有的读成「笑脸」，有的直接卡住，写成纯文字最稳。
 */

/** 阶段剧本的版本标记，和识字 App 共用一个口径。 */
export const ROUND16_H6_STAGE_SCRIPT = 'ROUND16_H6'

const trim = (list) => list.filter((line) => typeof line === 'string' && line.trim())

export const MASCOT_SCENES = {
  home: (ctx) =>
    trim([
      '欢迎回到数学星球，今天想先去哪一颗？',
      ctx.dailyCompleted
        ? `今天的冒险已经做完啦，连续打卡 ${ctx.streak} 天。`
        : `今日冒险只有 ${ctx.dailyTotal} 道题，做完就能打卡。`,
      ctx.stars > 0 && `你已经收集了 ${ctx.stars} 颗星星。`,
      '灰色的星球还没解锁，多做几题就能点亮它。',
      '想不出来的时候点提示，我给你搭个梯子。',
      '慢慢想比抢着答重要得多。'
    ]),

  daily: (ctx) =>
    trim([
      `今天的 ${ctx.dailyTotal} 道题我陪你一起做。`,
      '先把题读完，再看选项，不着急。',
      '算错了也没关系，我们一起看看是哪一步差了一点。',
      '连着答对会有额外的星星哦。',
      ctx.streak > 0 && `已经连续打卡 ${ctx.streak} 天了，今天也别断。`,
      '做完就可以去点亮别的星球啦。'
    ])
}

/**
 * 阶段剧本。数组顺序就是优先级：越靠前越「打断」后面的。
 */
export const MASCOT_STAGES = [
  {
    id: 'comeback',
    label: '久别重逢',
    when: (ctx) => (ctx.daysAway ?? 0) >= 3,
    lines: (ctx) =>
      trim([
        '好久不见，你的星星我一颗都没弄丢。',
        (ctx.daysAway ?? 0) > 0 && `隔了 ${ctx.daysAway} 天没来，我们先做两道简单的热热身。`,
        '手生很正常，做几题就找回感觉了。',
        '先别挑最难的星球，从会的那颗开始。'
      ])
  },
  {
    id: 'fatigue',
    label: '该歇歇了',
    when: (ctx) => (ctx.todayMinutes ?? 0) >= 20,
    lines: (ctx) =>
      trim([
        (ctx.todayMinutes ?? 0) > 0
          ? `今天已经算了 ${ctx.todayMinutes} 分钟，眼睛该歇一歇了。`
          : '算了好一会儿了，眼睛该歇一歇。',
        '越累越容易算错，休息五分钟再回来更划算。',
        '起来走两步，回来我们再战最后一题。',
        '今天到这里就很好，明天星球还在。'
      ])
  },
  {
    id: 'combo',
    label: '连着答对',
    when: (ctx) => (ctx.combo ?? 0) >= 3,
    lines: (ctx) =>
      trim([
        `连着答对 ${ctx.combo} 道啦，手感真好。`,
        '这一串答对说明方法找对了，不是运气。',
        '越顺越要把题读完，别被相近的选项骗了。',
        '再对两道，今天的星星就到手了。'
      ])
  },
  {
    id: 'wrongBook',
    label: '错题欠账',
    when: (ctx) => (ctx.wrongCount ?? 0) >= 3,
    lines: (ctx) =>
      trim([
        `错题本里还欠着 ${ctx.wrongCount} 道，做掉两道再去新星球吧。`,
        '错题重做一遍才算真会，不然下次还会栽在同一步。',
        '先看错在哪一步，再动手算，比闷头重算快得多。',
        '错题清空的那一刻最痛快，我们离它不远了。'
      ])
  },
  {
    id: 'encourage',
    label: '算错了',
    when: (ctx) => (ctx.recentWrong ?? 0) > 0,
    lines: (ctx) =>
      trim([
        '算错一道很正常，我们看看是哪一步差了一点。',
        '把题目再读一遍，很多时候错在没读完。',
        '不会只是还没学会，不是学不会。',
        '要不要先看一段演示？看完再算这类题会顺很多。',
        '慢一点算对，比快十道错八道强。'
      ])
  },
  {
    id: 'daily',
    label: '今日冒险',
    when: (ctx) => !ctx.dailyCompleted,
    lines: (ctx) =>
      trim([
        (ctx.dailyTotal ?? 0) > 0
          ? `今日冒险还差 ${Math.max(0, (ctx.dailyTotal ?? 0) - (ctx.dailyDone ?? 0))} 道题就打卡了。`
          : '今日冒险随时可以开始。',
        '每天几道题，比一个周末做一百道管用。',
        '做完今天的题，连续天数就又加一。',
        '先做今日冒险，再自由挑星球，节奏最舒服。'
      ])
  },
  {
    id: 'finish',
    label: '今天够了',
    when: (ctx) => Boolean(ctx.dailyCompleted),
    lines: (ctx) =>
      trim([
        '今天的冒险已经完成，剩下的时间随便逛。',
        (ctx.streak ?? 0) > 1
          ? `连着打卡 ${ctx.streak} 天了，这个习惯比多做十题值钱。`
          : '明天再来，我们就算连上两天啦。',
        '想再练就去错题本，那里的题最值得做。',
        '走之前挑一道今天最难的题，讲给家里人听。'
      ])
  },
  {
    id: 'idle',
    label: '随便聊聊',
    when: () => true,
    lines: () =>
      trim([
        '我是小算，你算题的时候我一直都在。',
        '每道题都能画出来，画出来就不难了。',
        '想不出来就点提示，我给你搭个梯子。',
        '慢慢想比抢着答重要得多。'
      ])
  }
]

const STAGE_BY_ID = Object.fromEntries(MASCOT_STAGES.map((s) => [s.id, s]))

/** 按当前状态挑出该说哪一类话；最后一个阶段恒为真，永远有结果。 */
export function pickMascotStage(ctx = {}) {
  const stage = MASCOT_STAGES.find((s) => s.when(ctx)) ?? STAGE_BY_ID.idle
  return { id: stage.id, label: stage.label, script: ROUND16_H6_STAGE_SCRIPT }
}

/** 某个阶段的台词；不传阶段名就按当前状态自己挑一个。 */
export function mascotStageLines(stageId, ctx = {}) {
  const stage = STAGE_BY_ID[stageId] ?? STAGE_BY_ID[pickMascotStage(ctx).id]
  return stage ? stage.lines(ctx) : []
}

/** 阶段台词的总条数，验收与证据回填直接读它。 */
export function countMascotStageLines(ctx = {}) {
  const probe = {
    stars: 30,
    dailyDone: 2,
    dailyTotal: 6,
    dailyCompleted: false,
    streak: 4,
    combo: 5,
    wrongCount: 4,
    recentWrong: 1,
    daysAway: 5,
    todayMinutes: 25,
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
