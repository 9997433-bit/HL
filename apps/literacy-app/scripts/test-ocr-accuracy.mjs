/**
 * ROUND9_H2（承接 ROUND8_H4）—— 拍照识字的识别精度基准。
 *
 * scripts/test-ocr.mjs 守的是取字规则（哪些字符算字、哪些字讲得了），
 * 它给一段假文本就能跑；真正会悄悄退化的那一半——语言包换了、tesseract 升级了、
 * 预处理的对比度拉伸写反了——只有让引擎去认一张真图才看得见。
 * 这个脚本就是那张网，三段各守一处：
 *
 *   1. 引擎跑分：九张固定基准图（public/ocr/sample-photo.png +
 *      scripts/fixtures/ocr/*.png）跑一遍 chi_sim，逐张算召回率、
 *      核对关键字、盯住误检和置信度。图一个字节都不变，分数掉了就是引擎侧退化。
 *   2. 预处理：utils/ocr.js 的 preprocess() 是 DOM 代码，这里用一个极小的
 *      canvas 替身把它拉到 Node 里跑，验缩放边界与灰度/对比度拉伸的算法本身。
 *   3. 形近复核：认出来的字要能一路点进单字页的「考一考」，那道题的三个选项
 *      必须来自形近池（utils/distractors.js），不是随机抽的字。
 *
 * ROUND8_H4 的五张图全是「摆好了拍」的印刷体，一个总分掩住了各类版面的差别：
 * 平均分 100% 之下，手写字可能一个都认不出，谁也不知道。ROUND9_H2 把基准集
 * 扩到九张、按 tier 分类，每一类单独定线，退化落在哪一类上一眼就能看出来：
 *
 *   print 印刷体 · warm-light 暖光 · inverted 反色 · blur 失焦
 *   handwriting 手写 · low-light 低光 · busy-background 复杂背景 · perspective 斜拍
 *
 * 后四类是 R9 新增，REQUIRED_TIERS 钉住它们不许被悄悄删掉。
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
const langDir = fileURLToPath(new URL('public/ocr/', appUrl)).replace(/\/$/, '')

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
 * .agent_workspace/acceptance-log-round9-h2.md。
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
const MIN_IMAGES = 8
const REQUIRED_TIERS = ['handwriting', 'low-light', 'busy-background', 'perspective']

/** tier 的中文名，只用于打分表和 --json 的可读性。 */
const TIER_LABEL = {
  print: '印刷体',
  'warm-light': '暖光',
  inverted: '反色',
  blur: '失焦',
  handwriting: '手写',
  'low-light': '低光',
  'busy-background': '复杂背景',
  perspective: '斜拍'
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
        marker: 'ROUND9_H2',
        supersedes: 'ROUND8_H4',
        imageCount: rows.length,
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
  console.log(
    `\n拍照识字精度基准：${rows.length} 张图 / ${byTier.length} 类版面，` +
      `总召回 ${hit}/${total}（${(overall * 100).toFixed(1)}%）；` +
      `${tests.length - failed} / ${tests.length} 项通过。`
  )
}

process.exit(failed ? 1 : 0)
