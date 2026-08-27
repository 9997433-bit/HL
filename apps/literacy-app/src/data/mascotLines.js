/**
 * 学伴墨墨的陪跑台词。
 *
 * 每条核心路由一组：前面几句跟着当前进度走（「还有 3 个字要复习」），
 * 后面几句是通用的鼓励与玩法提示。孩子点一下墨墨就换下一句，同时朗读出来。
 *
 * 台词里不放 emoji：这些句子会直接交给 SpeechSynthesis 念，
 * 表情符号有的读作「笑脸」，有的干脆卡住，写成纯文字最稳。
 */

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
    ])
}

/** 取某个场景的台词；场景名写错时退回首页那组，界面上永远有话可说。 */
export function mascotLines(scene, ctx = {}) {
  const build = MASCOT_SCENES[scene] ?? MASCOT_SCENES.home
  return build(ctx)
}
