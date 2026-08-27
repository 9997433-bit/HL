/**
 * 吉祥物「小算」的陪跑台词。
 *
 * 首页讲今天去哪儿、今日冒险还差几题；答题页讲怎么想、错了怎么办。
 * 孩子点一下小算就换下一句，同时读出来。
 *
 * 台词里不放 emoji：这些句子会直接交给 SpeechSynthesis 念，
 * 表情符号有的读成「笑脸」，有的直接卡住，写成纯文字最稳。
 */

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

/** 取某个场景的台词；场景名写错时退回首页那组，界面上永远有话可说。 */
export function mascotLines(scene, ctx = {}) {
  const build = MASCOT_SCENES[scene] ?? MASCOT_SCENES.home
  return build(ctx)
}
