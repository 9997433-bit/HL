/**
 * ROUND11_H2（承接 ROUND10_H2 / ROUND9_H2 / ROUND8_H4）—— 拍照识字的识别精度基准。
 *
 * scripts/test-ocr.mjs 守的是取字规则（哪些字符算字、哪些字讲得了），
 * 它给一段假文本就能跑；真正会悄悄退化的那一半——语言包换了、tesseract 升级了、
 * 预处理的对比度拉伸写反了——只有让引擎去认一张真图才看得见。
 * 这个脚本就是那张网，三段各守一处：
 *
 *   1. 引擎跑分：十三张固定基准图（public/ocr/sample-photo.png +
 *      scripts/fixtures/ocr/*.png）跑一遍 chi_sim，逐张算召回率、
 *      核对关键字、盯住误检和置信度。图一个字节都不变，分数掉了就是引擎侧退化。
 *   2. 预处理：utils/ocr.js 的 preprocess() 是 DOM 代码，这里用一个极小的
 *      canvas 替身把它拉到 Node 里跑，验缩放边界与灰度/对比度拉伸的算法本身。
 *   3. 形近复核：认出来的字要能一路点进单字页的「考一考」，那道题的三个选项
 *      必须来自形近池（utils/distractors.js），不是随机抽的字。
 *
 * ROUND8_H4 的五张图全是「摆好了拍」的印刷体，一个总分掩住了各类版面的差别：
 * 平均分 100% 之下，手写字可能一个都认不出，谁也不知道。ROUND9_H2 把基准集
 * 扩到十张、按 tier 分类，每一类单独定线，退化落在哪一类上一眼就能看出来：
 *
 *   print 印刷体 · warm-light 暖光 · inverted 反色 · blur 失焦
 *   handwriting 手写 · low-light 低光 · busy-background 复杂背景 · perspective 斜拍
 *
 * 但这十张有一个共同的出身问题：全是浏览器渲染出来的。字形是系统字体画的、
 * 噪点是我们自己撒的、模糊是 CSS filter 加的——它们守得住引擎侧退化，守不住
 * 「真实世界长什么样」。十张合成图跑出总召回 100%，孩子拿手机拍小区告示牌
 * 却可能一个字都对不上，这段差距在合成图上永远看不见。
 *
 * ROUND10_H2 补的就是这一段：real-photo tier 收三张**真人用手机拍的**照片
 * （Wikimedia Commons，CC BY-SA，只裁剪缩放不做增强，见 gen-ocr-real-samples.mjs），
 * 台阶立刻显形——同一句「小心地滑」，警示锥上的印刷体 4/4，墙上的喷漆模板字
 * 只认得出 3/4，「滑」被读成「海」。这不是 bug，是这套离线引擎的真实边界，
 * 现在它被写进阈值里，谁再改预处理都得先跟这条线对账。
 *
 * ROUND11_H2 把这一类从三张扩到六张，并补上失败那一半的验收。
 * 三张只够证明「真实照片认得出」，证不了「哪一类认不出」——R10 那三张全是
 * 户外印刷标牌，同一种光、同一种字。新的三张各挑一类真实世界的字：
 *
 *   real-road-warning    马路三角警示牌，2001 年卡片机，画面自带压缩噪点
 *   real-toilet-sign     商场墙上的金属立体字，字和墙几乎一个亮度
 *   real-blackboard-press 真人粉笔写的落款，笔画有飞白（不是 JITTER 抖出来的）
 *
 * 另一半是话术：这套引擎在手写体、艺术字、褪色招牌上会稳定失手，
 * 「认不出」是常态而不是异常。界面在这半边只说一句「没认出来」就是把锅甩给孩子，
 * 所以这里加了一段断言，盯住 CameraOcrView 里那三条降级话术（光线 / 取景 / 换一张）
 * 与它们的出口按钮还在——话术被删掉，跑分再好看也没用。
 *
 * 基准图为什么不放 public/：见 scripts/gen-ocr-benchmark.mjs 的说明。
 * 浏览器里的整链（懒加载、Service Worker、点进单字页）由 scripts/smoke.mjs 覆盖，
 * 这里刻意只跑 Node，一秒出头就能给出分数，挂在 npm test 上不心疼。
 *
 * 用法：node scripts/test-ocr-accuracy.mjs [--json]
 */

import assert from 'node:assert/strict'
import { existsSync } from 'node:fs'
import { readFile } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'

import { CHARACTER_MAP, CHARACTERS } from '../src/data/characters.js'
import { similarChars } from '../src/data/similar-chars.js'
import { buildOptions, similarDistractors } from '../src/utils/distractors.js'
import { extractHanzi, OCR_PACK, preprocess, splitByLibrary } from '../src/utils/ocr.js'

const asJson = process.argv.includes('--json')
const appUrl = new URL('../', import.meta.url)
const repoUrl = new URL('../../', appUrl)
const langDir = fileURLToPath(new URL('public/ocr/', appUrl)).replace(/\/$/, '')

/** 真实样张的出处 / 授权 / 裁剪框，和 real-*.png 一一对应（见 gen-ocr-real-samples.mjs）。 */
const realSamples = JSON.parse(
  await readFile(new URL('scripts/fixtures/ocr/real-samples.json', appUrl), 'utf8')
)
const notices = await readFile(new URL('THIRD_PARTY_NOTICES.md', repoUrl), 'utf8')

/**
 * 基准集。
 *
 * tier    这张图代表的版面类别，分数按 tier 汇总（见 §输出）
 * name    人读的图名
 * expect  图上印的字（去重后就是这张图的满分）
 * keyword 无论如何都得认出来的字：召回率还能靠别的字凑，这几个字丢了
 *         就意味着这类版面（小字 / 反色 / 失焦 / 手写）整体塌了
 * recall  召回率下限，取实测值往下留一档余量（实测见 §结果）
 * conf    Tesseract 自报的置信度下限
 * noise   误检额度，缺省用 MAX_NOISE；只有复杂背景那类才配得上更宽的额度
 *
 * 阈值只在换图或换语言包时才动，动之前先跑一遍 --json 把实测记进
 * .agent_workspace/acceptance-log-round10-h2.md。
 */
const BENCHMARK = [
  {
    tier: 'print',
    name: '示例字卡 日月山水',
    file: `public/ocr/${OCR_PACK.sample}`,
    expect: '日月山水',
    keyword: '日月山水',
    recall: 1,
    conf: 80
  },
  {
    tier: 'print',
    name: '绘本内页 小字两行',
    file: 'scripts/fixtures/ocr/book-page.png',
    expect: '白云青山绿水花草鱼鸟人家',
    keyword: '青山绿水',
    recall: 0.9,
    conf: 70
  },
  {
    tier: 'warm-light',
    name: '暖光字卡 偏黄低对比',
    file: 'scripts/fixtures/ocr/warm-light.png',
    expect: '上下左右',
    keyword: '上下',
    recall: 0.75,
    conf: 45
  },
  {
    tier: 'inverted',
    name: '黑板 深底白字',
    file: 'scripts/fixtures/ocr/blackboard.png',
    expect: '天地人和',
    keyword: '天',
    recall: 0.75,
    conf: 70
  },
  {
    tier: 'blur',
    name: '便签 拍糊的小字',
    file: 'scripts/fixtures/ocr/blurry-note.png',
    expect: '今天我们一起读书写字画',
    keyword: '读书',
    recall: 0.7,
    conf: 70
  },
  {
    // 手写：没有可用的手写中文字体，基准图用逐字抖动逼近「写不齐」。
    // 认不出真人手写是这套引擎的已知边界，这张守的是「模拟手写也别整页塌」。
    tier: 'handwriting',
    name: '作业本 手写四季',
    file: 'scripts/fixtures/ocr/handwriting.png',
    expect: '春夏秋冬',
    keyword: '春',
    recall: 0.75,
    conf: 65
  },
  {
    tier: 'handwriting',
    name: '竖格本 手写天地人和',
    file: 'scripts/fixtures/ocr/handwriting-daily.png',
    expect: '天地人和',
    keyword: '天',
    recall: 0.75,
    conf: 65
  },
  {
    tier: 'low-light',
    name: '夜里低光 深底暗字带噪点',
    file: 'scripts/fixtures/ocr/low-light.png',
    expect: '风雨雷电',
    keyword: '风',
    recall: 0.75,
    conf: 70
  },
  {
    // 花桌布 + 圆点 + 蜡笔：背景纹理本身就长得像笔画，误检额度给到 3。
    // 这里放宽的是「认出图上没有的字」，召回率一分没让。
    tier: 'busy-background',
    name: '花桌布 复杂背景字卡',
    file: 'scripts/fixtures/ocr/busy-bg.png',
    expect: '红黄蓝绿',
    keyword: '红',
    recall: 0.75,
    conf: 40,
    noise: 3
  },
  {
    tier: 'perspective',
    name: '斜拍字卡 透视加手影',
    file: 'scripts/fixtures/ocr/angled-card.png',
    expect: '手口耳目',
    keyword: '手',
    recall: 0.75,
    conf: 70
  },
  {
    // 以下三张是 ROUND10_H2 的真实照片，不是画出来的：Commons 上的 CC BY-SA 手机照，
    // 只裁剪缩放、不做任何增强（gen-ocr-real-samples.mjs），阈值也就跟着真实水平走。
    tier: 'real-photo',
    name: '真实照片 绿化带告示牌「爱护花草」',
    file: 'scripts/fixtures/ocr/real-park-sign.png',
    expect: '爱护花草',
    keyword: '花草',
    recall: 0.75,
    conf: 55
  },
  {
    tier: 'real-photo',
    name: '真实照片 商场警示锥「小心地滑」',
    file: 'scripts/fixtures/ocr/real-floor-cone.png',
    expect: '小心地滑',
    keyword: '小心',
    recall: 0.75,
    conf: 60
  },
  {
    // 同一句话、两种落地方式：警示锥上是印刷体，这张是墙上的喷漆模板字。
    // 模板字的笔画被镂空条断开，「滑」稳定地被读成「海」——4 个字只认得出 3 个。
    // 下限压到 0.5 不是放水，是承认这就是当前引擎在喷漆字上的真实水平；
    // 哪天换了语言包能认出「滑」了，回来把线抬上去。
    tier: 'real-photo',
    name: '真实照片 水泥墙喷漆「小心地滑」',
    file: 'scripts/fixtures/ocr/real-wall-stencil.png',
    expect: '小心地滑',
    keyword: '小心',
    recall: 0.5,
    conf: 45
  },
  {
    // ROUND11_H2 的三张。R10 那三张都是白天户外的印刷标牌，这三张各换一种真实条件：
    // 老相机的压缩噪点、金属字与墙面几乎同亮度、真人粉笔的飞白。
    tier: 'real-photo',
    name: '真实照片 马路警示牌「小心行人」',
    file: 'scripts/fixtures/ocr/real-road-warning.png',
    expect: '小心行人',
    keyword: '小心',
    recall: 0.75,
    conf: 70
  },
  {
    // 金属立体字最难的不是字形而是对比度：字面和墙面反射同一盏射灯，
    // 灰度直方图几乎重合，全靠 preprocess() 那一步把跨度拉满才认得出来。
    tier: 'real-photo',
    name: '真实照片 商场金属立体字「洗手间」',
    file: 'scripts/fixtures/ocr/real-toilet-sign.png',
    expect: '洗手间',
    keyword: '手间',
    recall: 0.66,
    conf: 60
  },
  {
    // 真人粉笔字。合成的 handwriting tier 是把印刷体逐字抖出来的，笔画仍然完整；
    // 这张的飞白是粉笔真的没吃上墨的地方，断口位置不讲道理——
    // 这是「手写」这一类里唯一一张没有作弊的图。
    tier: 'real-photo',
    name: '真实照片 黑板粉笔落款「中华书局」',
    file: 'scripts/fixtures/ocr/real-blackboard-press.png',
    expect: '中华书局',
    keyword: '中华',
    recall: 0.75,
    conf: 60
  }
]

/** 整套基准集的总召回率下限：单张可以差一点，合起来不许掉到这条线下。 */
const OVERALL_RECALL = 0.9

/** 一张图里认出来的、图上根本没有的字：偶尔一个是笔画粘连，成串出现就是引擎在瞎猜。 */
const MAX_NOISE = 2

/**
 * 基准集的规模与覆盖下限。
 *
 * 光有总分不够：五张印刷体图也能跑出 100%，可孩子拍的是作业本上的手写字、
 * 是天黑了没开灯的桌面、是花桌布上摆着的字卡。这两条钉住「扩样不许缩回去」——
 * 删图、砍 tier 都会当场红灯，而不是等某天线上认不出来了才发现。
 */
const MIN_IMAGES = 15
const REQUIRED_TIERS = [
  'handwriting',
  'low-light',
  'busy-background',
  'perspective',
  'real-photo'
]

/**
 * real-photo tier 单独的规模与分数下限。
 *
 * 这一类最容易被「省事」掉：真实照片要找授权、要核哈希、分数还不好看，
 * 换谁都想删两张换回合成图。两条线拦着——张数（ROUND11_H2 把门槛从 2 抬到 5）
 * 和这一类自己的召回率，掉下去就说明真实场景的识别塌了，而不是总分里的一点噪声。
 *
 * 张数这条线有个便宜的绕法：从同一张原图上裁五个位置，数字立刻够了，
 * 可光线、镜头、字体全是同一套，等于什么都没扩。MIN_REAL_SOURCES 堵的就是这条路——
 * 五张真实样张必须来自五张**不同的原始照片**（按清单里的 page 去重）。
 */
const MIN_REAL_IMAGES = 5
const MIN_REAL_SOURCES = 5
const REAL_TIER = 'real-photo'
const REAL_TIER_RECALL = 0.75

/** tier 的中文名，只用于打分表和 --json 的可读性。 */
const TIER_LABEL = {
  print: '印刷体',
  'warm-light': '暖光',
  inverted: '反色',
  blur: '失焦',
  handwriting: '手写',
  'low-light': '低光',
  'busy-background': '复杂背景',
  perspective: '斜拍',
  'real-photo': '真实照片'
}

/* ------------------------------------------------------------------ 跑分 */

const tests = []
const test = (name, fn) => tests.push({ name, fn })
const rows = []

const missingAssets = [
  ...BENCHMARK.map((c) => c.file),
  `public/ocr/${OCR_PACK.lang}.traineddata.gz`
].filter((rel) => !existsSync(fileURLToPath(new URL(rel, appUrl))))

async function createEngine() {
  const { createWorker, OEM } = await import('tesseract.js').catch(() => {
    throw new Error('tesseract.js 没装上，先跑 npm install（识别精度基准跑不了）')
  })
  // 与 utils/ocr.js 一致：只用 LSTM 引擎、语言包读同一份 public/ocr/chi_sim.traineddata.gz。
  // cacheMethod: 'none' —— 不往仓库里落 .traineddata 缓存文件。
  return createWorker(OCR_PACK.lang, OEM.LSTM_ONLY, {
    langPath: langDir,
    gzip: true,
    cacheMethod: 'none',
    logger: () => {}
  })
}

async function runBenchmark() {
  assert.equal(missingAssets.length, 0, `基准图/语言包缺失：${missingAssets.join('、')}`)
  const worker = await createEngine()
  try {
    for (const item of BENCHMARK) {
      const started = Date.now()
      const { data } = await worker.recognize(fileURLToPath(new URL(item.file, appUrl)))
      const ms = Date.now() - started
      const chars = extractHanzi(data.text)
      const wanted = [...new Set(item.expect)]
      const hit = wanted.filter((c) => chars.includes(c))
      const noise = chars.filter((c) => !wanted.includes(c))
      rows.push({
        name: item.name,
        recall: hit.length / wanted.length,
        hit: hit.length,
        total: wanted.length,
        missed: wanted.filter((c) => !chars.includes(c)).join(''),
        noise: noise.join(''),
        confidence: Math.round(data.confidence ?? 0),
        ms,
        item
      })
    }
  } finally {
    await worker.terminate()
  }
}

for (const item of BENCHMARK) {
  test(`「${item.name}」认得出，且认出来的字讲得了`, () => {
    const row = rows.find((r) => r.item === item)
    assert.ok(row, '这张基准图没跑到')
    assert.ok(
      row.recall >= item.recall,
      `召回率 ${(row.recall * 100).toFixed(0)}%（下限 ${(item.recall * 100).toFixed(0)}%），` +
        `丢了「${row.missed}」`
    )
    for (const char of item.keyword) {
      assert.ok(!row.missed.includes(char), `关键字「${char}」没认出来`)
    }
    assert.ok(
      row.noise.length <= (item.noise ?? MAX_NOISE),
      `认出了 ${row.noise.length} 个图上没有的字：「${row.noise}」` +
        `（额度 ${item.noise ?? MAX_NOISE}）`
    )
    assert.ok(row.confidence >= item.conf, `置信度 ${row.confidence}（下限 ${item.conf}）`)

    // 认出来却不在字库里的字，界面只能说「还没进字库」——基准图上的字必须全都讲得了
    const { unknown } = splitByLibrary([...item.expect])
    assert.equal(unknown.length, 0, `基准图上的「${unknown.join('')}」不在字库里`)
  })
}

test('整套基准集的总召回率守住下限', () => {
  const hit = rows.reduce((n, r) => n + r.hit, 0)
  const total = rows.reduce((n, r) => n + r.total, 0)
  assert.ok(
    hit / total >= OVERALL_RECALL,
    `总召回率 ${(hit / total * 100).toFixed(1)}%（${hit}/${total}，下限 ${OVERALL_RECALL * 100}%）`
  )
})

test(`基准集不少于 ${MIN_IMAGES} 张，难拍的那几类一张都不许少`, () => {
  assert.ok(
    BENCHMARK.length >= MIN_IMAGES,
    `基准集只剩 ${BENCHMARK.length} 张（下限 ${MIN_IMAGES}）`
  )
  const tiers = new Set(BENCHMARK.map((c) => c.tier))
  const missing = REQUIRED_TIERS.filter((t) => !tiers.has(t))
  assert.equal(
    missing.length,
    0,
    `少了这些 tier：${missing.map((t) => `${TIER_LABEL[t] ?? t}(${t})`).join('、')}`
  )
  for (const item of BENCHMARK) {
    assert.ok(TIER_LABEL[item.tier], `「${item.name}」的 tier「${item.tier}」没有登记中文名`)
  }
})

test(`真实照片不少于 ${MIN_REAL_IMAGES} 张，这一类的召回率单独守线`, () => {
  const real = BENCHMARK.filter((c) => c.tier === REAL_TIER)
  assert.ok(
    real.length >= MIN_REAL_IMAGES,
    `真实照片只剩 ${real.length} 张（下限 ${MIN_REAL_IMAGES}）`
  )
  for (const item of real) {
    assert.match(
      item.file,
      /\/real-[a-z0-9-]+\.png$/,
      `「${item.name}」的文件名不是 real-*.png：${item.file}`
    )
  }
  const picked = rows.filter((r) => r.item.tier === REAL_TIER)
  assert.equal(picked.length, real.length, '有真实照片没跑到')
  const hit = picked.reduce((n, r) => n + r.hit, 0)
  const total = picked.reduce((n, r) => n + r.total, 0)
  assert.ok(
    hit / total >= REAL_TIER_RECALL,
    `真实照片召回率 ${(hit / total * 100).toFixed(1)}%（${hit}/${total}，` +
      `下限 ${REAL_TIER_RECALL * 100}%）`
  )
})

test(`真实照片来自至少 ${MIN_REAL_SOURCES} 张不同的原图，不是一张图裁五刀`, () => {
  const real = BENCHMARK.filter((c) => c.tier === REAL_TIER)
  const declared = new Map(realSamples.samples.map((s) => [s.name, s]))
  const pages = new Set()
  for (const item of real) {
    const name = item.file.replace(/^.*\//, '').replace(/\.png$/, '')
    const page = declared.get(name)?.page
    assert.ok(page, `「${name}」在清单里查不到 page，说不清它是从哪张照片裁的`)
    pages.add(page)
  }
  assert.ok(
    pages.size >= MIN_REAL_SOURCES,
    `${real.length} 张真实样张只来自 ${pages.size} 张原图（下限 ${MIN_REAL_SOURCES}）`
  )
})

test('每张真实照片都留着出处与授权，署名同步进 THIRD_PARTY_NOTICES', () => {
  const declared = new Map(realSamples.samples.map((s) => [s.name, s]))
  for (const item of BENCHMARK.filter((c) => c.tier === REAL_TIER)) {
    const name = item.file.replace(/^.*\//, '').replace(/\.png$/, '')
    const sample = declared.get(name)
    assert.ok(sample, `「${name}.png」不在 fixtures/ocr/real-samples.json 里，出处不明`)
    for (const field of ['page', 'file', 'author', 'license', 'licenseUrl', 'sha256']) {
      assert.ok(sample[field], `「${name}」缺 ${field}——授权信息不齐就不能再分发`)
    }
    assert.equal(sample.text, item.expect, `「${name}」清单里的字和基准集对不上`)
    // 裁剪框写死在清单里，图才可能一个字节都不变；顺手挡住 [0,0,1,1] 这种「没裁」
    assert.equal(sample.crop.length, 4, `「${name}」的裁剪框不是四个数`)
    assert.ok(
      sample.crop[0] < sample.crop[2] && sample.crop[1] < sample.crop[3],
      `「${name}」的裁剪框反了`
    )
    assert.ok(
      notices.includes(sample.page),
      `THIRD_PARTY_NOTICES.md 里没有「${name}」的出处链接，CC BY-SA 的署名义务没尽到`
    )
    assert.ok(
      notices.includes(sample.author),
      `THIRD_PARTY_NOTICES.md 里没有「${name}」的作者署名「${sample.author}」`
    )
  }
})

/* -------------------------------------------------- 失败降级话术（界面侧） */

/**
 * ROUND11_H2 的另一半：认不出的时候界面说什么。
 *
 * 上面那堆阈值守的是「认得出多少」，可这套离线引擎在手写体、艺术字、
 * 褪色招牌上会稳定失手——喷漆那张到今天也只有 3/4。既然失败是常态的一半，
 * 那半边的文案就得跟跑分一样被守住：只说一句「没认出来」等于告诉孩子
 * 是他拍得不好，而真正改得动的只有光线、取景，以及承认换一张更快。
 *
 * 这里读的是 CameraOcrView.vue 的源码而不是跑浏览器：话术被删、失败分支
 * 被砍、出口按钮被拿掉，都是一次源码改动，Node 里一秒就能拦下。
 * 渲染出来长什么样由 scripts/smoke.mjs 那条拍照识字用例覆盖。
 */
const cameraSource = await readFile(new URL('src/views/CameraOcrView.vue', appUrl), 'utf8')

test('认不出时给的是三条能照做的话术：光线、取景、换一张', () => {
  const tips = cameraSource.match(/const RETRY_TIPS\s*=\s*\[[\s\S]*?\n\]/)?.[0]
  assert.ok(tips, 'CameraOcrView 里找不到 RETRY_TIPS——失败话术被删了')
  const lines = [...tips.matchAll(/text:\s*'([^']+)'/g)].map((m) => m[1])
  assert.ok(lines.length >= 3, `只剩 ${lines.length} 条降级话术（下限 3）`)
  for (const [what, pattern] of [
    ['光线', /光|亮|影|反光/],
    ['取景', /凑近|近一点|占满|端稳|清楚/],
    ['换一张', /换一张|换张|另一张/]
  ]) {
    assert.ok(lines.some((t) => pattern.test(t)), `三条话术里没有「${what}」这一条`)
  }
  // 把边界说破，孩子才不会对着同一张手写照片反复重拍
  assert.ok(
    /手写|艺术字|褪色/.test(lines.join('')),
    '话术没有说明它认不了哪一类字，孩子只会以为是自己拍得不好'
  )
})

test('三种失败都落到同一张降级卡上，并且卡里带得走的出口', () => {
  for (const [what, pattern] of [
    ['认了一场空', /const blank\s*=\s*computed/],
    ['认得不准', /const shaky\s*=\s*computed/],
    ['引擎出错', /phase\.value === 'error'/]
  ]) {
    assert.match(cameraSource, pattern, `失败分支「${what}」没了`)
  }
  assert.match(
    cameraSource,
    /const troubled\s*=\s*computed\([\s\S]*?blank\.value[\s\S]*?shaky\.value[\s\S]*?error/,
    'troubled 没有把三种失败并到一起，会漏掉其中一种'
  )
  assert.match(cameraSource, /v-if="troubled"/, '降级卡没有挂到 troubled 上')
  assert.match(cameraSource, /data-trouble=/, '降级卡缺 data-trouble，smoke 与读屏都定位不到它')
  // 只讲道理不给出口等于把人堵在原地
  assert.match(cameraSource, /再拍一张/, '降级卡里没有「再拍一张」')
  assert.match(cameraSource, /试一张示例/, '降级卡里没有「试一张示例」这条自证路径')
})

test('低置信度的提醒线，跟真实样张的实测分数对得上', () => {
  const line = Number(cameraSource.match(/const SHAKY_CONFIDENCE\s*=\s*(\d+)/)?.[1])
  assert.ok(Number.isFinite(line), 'CameraOcrView 里找不到 SHAKY_CONFIDENCE')
  const floors = BENCHMARK.filter((c) => c.tier === REAL_TIER).map((c) => c.conf)
  // 提醒线要压在最难的那几张真实照片之上，否则喷漆字那种「认错了还挺自信」
  // 的结果一句提醒都不会有；也不能高到把警示锥那种干干净净的照片也标成可疑
  assert.ok(
    line > Math.min(...floors),
    `提醒线 ${line} 不高于最低的真实样张置信度下限 ${Math.min(...floors)}，等于从不提醒`
  )
  assert.ok(
    line <= Math.max(...floors),
    `提醒线 ${line} 高过所有真实样张的下限 ${Math.max(...floors)}，会把认对的也标成可疑`
  )
})

/* -------------------------------------------------------------- 预处理 */

/**
 * preprocess() 只用到 canvas 的四个方法，这里给它一个替身：
 * drawImage 按目标尺寸从「图」上取样，getImageData 把同一块 buffer 交回去，
 * 于是 putImageData 之后还能直接读到拉伸后的像素。
 *
 * 用替身而不是真解一张 PNG：要验的是缩放边界和对比度拉伸这套算术，
 * 合成一张已知灰阶的图反而看得更准，也省掉一个 PNG 解码依赖。
 */
function withCanvasShim(run) {
  const previous = globalThis.document
  globalThis.document = {
    createElement(tag) {
      assert.equal(tag, 'canvas', `preprocess 不该创建 <${tag}>`)
      const canvas = { width: 0, height: 0 }
      let buffer = null
      canvas.getContext = () => ({
        drawImage(source, _x, _y, width, height) {
          buffer = new Uint8ClampedArray(width * height * 4)
          for (let y = 0; y < height; y += 1) {
            for (let x = 0; x < width; x += 1) {
              const [r, g, b] = source.sample(x / Math.max(1, width - 1))
              const i = (y * width + x) * 4
              buffer[i] = r
              buffer[i + 1] = g
              buffer[i + 2] = b
              buffer[i + 3] = 255
            }
          }
        },
        getImageData: (_x, _y, width, height) => ({ data: buffer, width, height }),
        putImageData: () => {}
      })
      return canvas
    }
  }
  try {
    return run()
  } finally {
    if (previous === undefined) delete globalThis.document
    else globalThis.document = previous
  }
}

/** 一条横向灰阶：from → to，用来看对比度到底有没有被拉满。 */
const grayImage = (width, height, from = 0, to = 255) => ({
  naturalWidth: width,
  naturalHeight: height,
  sample(t) {
    const v = Math.round(from + (to - from) * t)
    return [v, v, v]
  }
})

const channels = (canvas) => {
  const { data } = canvas.getContext().getImageData(0, 0, canvas.width, canvas.height)
  let min = 255
  let max = 0
  for (let i = 0; i < data.length; i += 4) {
    assert.equal(data[i], data[i + 1], '预处理后 R、G 不一致，没转成灰度')
    assert.equal(data[i], data[i + 2], '预处理后 R、B 不一致，没转成灰度')
    assert.equal(data[i + 3], 255, '预处理后出现了半透明像素')
    if (data[i] < min) min = data[i]
    if (data[i] > max) max = data[i]
  }
  return { min, max }
}

test('大图缩到长边 1280，小图放大到短边 640，识别既不烧时间也不糊笔画', () => {
  withCanvasShim(() => {
    const big = preprocess(grayImage(2400, 1600))
    assert.equal(big.width, 1280)
    assert.equal(big.height, 853)

    const small = preprocess(grayImage(320, 240))
    assert.equal(small.height, 640)
    assert.equal(small.width, 853)

    // 已经落在 640–1280 之间的照片原样送进引擎，不做无谓重采样
    const fit = preprocess(grayImage(1000, 700))
    assert.equal(fit.width, 1000)
    assert.equal(fit.height, 700)
  })
})

test('暖光下的灰阶被拉满 0–255，暗部的笔画才浮得出来', () => {
  withCanvasShim(() => {
    const { min, max } = channels(preprocess(grayImage(800, 640, 92, 176)))
    assert.equal(min, 0, '最暗的像素没有被拉到 0')
    assert.equal(max, 255, '最亮的像素没有被拉到 255')
  })
})

test('几乎纯色的照片不拉对比度，免得把噪点放大成假笔画', () => {
  withCanvasShim(() => {
    const { min, max } = channels(preprocess(grayImage(800, 640, 126, 130)))
    assert.ok(max - min <= 8, `灰阶跨度 ${max - min} 被放大了`)
  })
})

test('空图片当场说清楚，不把 0×0 的画布喂给引擎', () => {
  withCanvasShim(() => {
    assert.throws(() => preprocess(grayImage(0, 0)), /照片是空的/)
  })
})

/* --------------------------------------------------- 形近复核（考一考） */

const detailSource = await readFile(new URL('src/views/CharDetailView.vue', appUrl), 'utf8')

test('CharDetailView 的选项来自形近池，没有退回随机抽字', () => {
  assert.match(
    detailSource,
    /import\s*\{[^}]*\bsimilarDistractors\b[^}]*\}\s*from\s*'@\/utils\/distractors\.js'/,
    'CharDetailView 没有从 @/utils/distractors.js 取干扰项'
  )
  for (const [step, fn] of [['听一听', 'buildListen'], ['考一考', 'buildQuiz']]) {
    const body = detailSource.match(new RegExp(`function ${fn}\\s*\\([\\s\\S]*?\\n}`))?.[0]
    assert.ok(body, `CharDetailView 里找不到 ${fn}()`)
    assert.match(body, /similarDistractors\s*\(/, `${step}（${fn}）没走形近池`)
  }
})

test('基准图上的字，考一考的干扰项都是形近字', () => {
  const chars = [...new Set(BENCHMARK.flatMap((c) => [...c.expect]))]
  const checked = []
  for (const char of chars) {
    // 形近库里的字偶尔超出当前字表（如生僻的形近字），排掉之后才是真的能出题的那些
    const near = similarChars(char).filter((c) => CHARACTER_MAP.has(c))
    if (!near.length) continue
    checked.push(char)
    const picks = similarDistractors(char, 3)
    assert.equal(picks.length, 3, `「${char}」只凑出 ${picks.length} 个干扰项`)
    assert.ok(!picks.some((e) => e.char === char), `「${char}」的干扰项里混进了它自己`)
    assert.equal(new Set(picks.map((e) => e.char)).size, 3, `「${char}」的干扰项重复了`)
    // 最像的那个每轮都在场：孩子每次都得在「日 / 旦」之间做一次真的辨认
    assert.equal(picks[0].char, near[0], `「${char}」最像的「${near[0]}」没有固定出现`)
    // 形近库给得出几个就得用几个，剩下的名额才轮到同部首 / 笔画相近来填
    const wantFromPool = Math.min(3, near.length)
    const fromPool = picks.filter((e) => near.includes(e.char)).length
    assert.equal(fromPool, wantFromPool, `「${char}」只有 ${fromPool} 个干扰项来自形近库`)
  }
  assert.ok(checked.length >= 20, `只有 ${checked.length} 个基准字有形近库条目`)
})

test('形近库里没有的字，退回同部首 / 笔画相近，而不是空着', () => {
  const orphan = CHARACTERS.find((e) => similarChars(e.char).length === 0)
  if (!orphan) return
  const picks = similarDistractors(orphan.char, 3)
  assert.equal(picks.length, 3, `「${orphan.char}」没凑够干扰项`)
  const close = picks.filter(
    (e) => e.radical === orphan.radical || Math.abs((e.strokes ?? 0) - (orphan.strokes ?? 0)) <= 2
  )
  assert.ok(close.length >= 1, `「${orphan.char}」的干扰项全是八竿子打不着的字`)
})

test('buildOptions 出的是「正确答案 + 干扰项」，一道题四个不重样的选项', () => {
  const target = CHARACTER_MAP.get('日')
  const options = buildOptions(target, 4)
  assert.equal(options.length, 4)
  assert.equal(new Set(options.map((o) => o.char)).size, 4, '选项里有重复的字')
  assert.ok(options.includes(target), '选项里没有正确答案')
})

/* ------------------------------------------------------------------ 输出 */

let failed = 0
const failures = []
try {
  await runBenchmark()
} catch (err) {
  failed += 1
  failures.push(`基准集跑分：${err.message}`)
  if (!asJson) console.log(`  ✗ 基准集跑分\n      ${err.message}`)
}

for (const { name, fn } of tests) {
  try {
    await fn()
    if (!asJson) console.log(`  ✓ ${name}`)
  } catch (err) {
    failed += 1
    failures.push(`${name}：${err.message}`)
    if (!asJson) console.log(`  ✗ ${name}\n      ${err.message}`)
  }
}

const hit = rows.reduce((n, r) => n + r.hit, 0)
const total = rows.reduce((n, r) => n + r.total, 0)
const overall = total ? hit / total : 0

/** 真实样张在报表里要跟着授权走，别让人只看见分数、忘了这图是别人的。 */
const licenseOf = (item) => {
  const name = item.file.replace(/^.*\//, '').replace(/\.png$/, '')
  const sample = realSamples.samples.find((s) => s.name === name)
  return sample ? `${sample.license} · ${sample.author}` : '出处不明'
}

/** 按 tier 归并：总分掩住的那一类退化，只有分类分数看得见。 */
const byTier = []
for (const item of BENCHMARK) {
  const bucket =
    byTier.find((t) => t.tier === item.tier) ??
    byTier[byTier.push({ tier: item.tier, label: TIER_LABEL[item.tier] ?? item.tier, images: 0, hit: 0, total: 0 }) - 1]
  const row = rows.find((r) => r.item === item)
  bucket.images += 1
  bucket.hit += row?.hit ?? 0
  bucket.total += row?.total ?? [...new Set(item.expect)].length
}

if (asJson) {
  console.log(
    JSON.stringify(
      {
        marker: 'ROUND11_H2',
        supersedes: 'ROUND10_H2',
        imageCount: rows.length,
        realImageCount: rows.filter((r) => r.item.tier === REAL_TIER).length,
        realSourceCount: new Set(
          BENCHMARK.filter((c) => c.tier === REAL_TIER).map(
            (c) =>
              realSamples.samples.find(
                (s) => s.name === c.file.replace(/^.*\//, '').replace(/\.png$/, '')
              )?.page
          )
        ).size,
        overallRecall: Number(overall.toFixed(4)),
        hit,
        total,
        tiers: byTier.map((t) => ({
          tier: t.tier,
          label: t.label,
          images: t.images,
          recall: Number((t.total ? t.hit / t.total : 0).toFixed(4)),
          hit: t.hit,
          total: t.total
        })),
        images: rows.map((r) => ({
          tier: r.item.tier,
          name: r.name,
          file: r.item.file,
          ...(r.item.tier === REAL_TIER ? { license: licenseOf(r.item) } : {}),
          recall: Number(r.recall.toFixed(4)),
          hit: r.hit,
          total: r.total,
          missed: r.missed,
          noise: r.noise,
          confidence: r.confidence,
          ms: r.ms
        })),
        passed: tests.length - failed,
        tests: tests.length,
        failures
      },
      null,
      2
    )
  )
} else {
  console.log('')
  for (const r of rows) {
    console.log(
      `  [${TIER_LABEL[r.item.tier] ?? r.item.tier}] ${r.name}：` +
        `召回 ${r.hit}/${r.total}（${(r.recall * 100).toFixed(0)}%）` +
        ` · 置信度 ${r.confidence} · ${r.ms} ms` +
        `${r.missed ? ` · 丢字「${r.missed}」` : ''}${r.noise ? ` · 误检「${r.noise}」` : ''}`
    )
  }
  console.log('')
  for (const t of byTier) {
    console.log(
      `  ${t.label}（${t.images} 张）：${t.hit}/${t.total}` +
        `（${(t.total ? t.hit / t.total * 100 : 0).toFixed(0)}%）`
    )
  }
  const real = rows.filter((r) => r.item.tier === REAL_TIER)
  if (real.length) {
    console.log('\n  真实样张出处（CC BY-SA 的几张，随仓库再分发需保留署名）：')
    for (const r of real) {
      console.log(`    ${r.item.file.replace(/^.*\//, '')} — ${licenseOf(r.item)}`)
    }
  }
  console.log(
    `\n拍照识字精度基准：${rows.length} 张图 / ${byTier.length} 类版面` +
      `（其中真实照片 ${real.length} 张），` +
      `总召回 ${hit}/${total}（${(overall * 100).toFixed(1)}%）；` +
      `${tests.length - failed} / ${tests.length} 项通过。`
  )
}

process.exit(failed ? 1 : 0)
