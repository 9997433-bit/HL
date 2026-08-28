/**
 * ROUND12_H2 —— 拍照识字的真机 / 模拟器 harness。
 * R13 起 scripts/android-sim.mjs 把 A 段作为 `ocr-device-a` step 调用（门禁 ROUND13_H2），
 * 失败样本回流纪律见 .agent_workspace/r13-ocr-regression-loop.md。
 * R14 起 A 段多守两件事（ROUND14_H2）：App 侧那份 WebView 实测矩阵在不在、分够不够，
 * 以及失败样本回流队列有没有逾期单——见下面的 A9 / A10。
 *
 * scripts/test-ocr-accuracy.mjs 守的是「引擎认得出多少字」，它在 Node 里跑，
 * 一秒出头就有分数。可拍照识字这条链上，最容易在真机上断、而在开发机上
 * 一次都不会断的，恰恰是引擎之外的那几段：
 *
 *   - 6 MB 的 wasm 内核和语言包能不能从 WebView 的同源目录里取到；
 *   - 断网之后 Service Worker 手里还有没有它们；
 *   - 「拍一张」按下去，Android 会不会真的调起后置摄像头；
 *   - 应用要了哪些权限，家长在安装页上看到的是不是「相机」两个字。
 *
 * 这些在桌面 Chrome 上全都是绿的。它们只在一台真机上、装成 APK、
 * 开着飞行模式的时候才会咬人——而这台 Cursor Cloud VM 上没有 adb，
 * 没有 Android SDK，也没有连着任何设备（口径见
 * .agent_workspace/ANDROID-DEVICE-CHECKLIST.md §1.1）。
 *
 * 所以这个脚本分成两段，而不是整体标一个 SKIP 就交差：
 *
 *   A 段 · 前提条件（VM 上照跑，失败即红）
 *     真机上会咬人的那几件事，绝大多数在源码和构建产物里就能查出来：
 *     引擎路径指没指到 CDN、worker 是不是 blob:（blob: 的 worker 不受
 *     Service Worker 控制，飞行模式下必挂）、SW 的 OCR 缓存会不会被下一次
 *     发版清掉、取图走的是 file input 还是 getUserMedia、清单里有没有
 *     多要一个 CAMERA 权限。这十来条是真断言，不是清单打勾——
 *     它们红了，真机上一定会出问题，不必等设备到位才发现。
 *
 *   B 段 · 真机执行（要 adb + 设备，VM 上 SKIP）
 *     R14 起这一段不再只是「把人和图送到位」，它自己就能把整条链走完（ROUND14_H2）：
 *     采设备指纹、push 十张真实样张、冷启计时、**用 CDP 接进设备上那个 WebView**，
 *     逐张喂进 App 真正的「相册选」input，从 DOM 上读回认出来的字，
 *     再开一次飞行模式复跑，最后落一份 evidence/r14/android/ocr-device-b.json。
 *
 *     为什么要接 CDP 而不是让 QA 用眼睛看：拍照识字在设备上会不会掉字，
 *     取决于 WebView 的 canvas 缩放插值、wasm SIMD 有没有生效、SW 缓存命不命中——
 *     这三件事人眼看不出来，只能逐张对字数。人还要做的那部分（相机取景、
 *     TalkBack、温升）留在 ANDROID-DEVICE-CHECKLIST，不混进这份证据。
 *
 * 退出码分三档，SKIP 有自己的一档，谁都不能拿 exit 0 冒充「真机验过了」：
 *
 *   0  跑到位且全绿（--section=a 时是 A 段全绿；默认全跑时要 B 段真的在设备上跑完）
 *   1  有断言红了——产品或构建的问题
 *   2  没有红，但 B 段没跑成（没设备 / 没装 App / 接不进 WebView）= SKIP
 *
 * 模拟器不算真机。检测到 emulator 时默认按「没有设备」处理（exit 2）；
 * 要拿模拟器验 harness 本身，加 --allow-emulator——那时证据落在
 * ocr-device-b.emulator.json 且强制 simulated:true，永远进不了 ocr-device-b.json，
 * check-round14 的 H2 也就永远不会被模拟器点绿。
 *
 * 用法：
 *   node scripts/test-ocr-device.mjs                 A 段全跑，B 段有设备才跑
 *   node scripts/test-ocr-device.mjs --section=a     只跑 A 段（android-sim 的 ocr-device-a）
 *   node scripts/test-ocr-device.mjs --json          机读汇总
 *   node scripts/test-ocr-device.mjs --require-device  给真机 CI 用：设备缺席大声报 exit 2
 *   node scripts/test-ocr-device.mjs --allow-emulator  拿模拟器验 harness（结论标 simulated）
 */

import assert from 'node:assert/strict'
import { execFileSync } from 'node:child_process'
import { existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { openOcrRoute, recognizeInPage, scoreSample } from './lib/ocr-webview-drive.mjs'

const appDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repoDir = path.resolve(appDir, '..', '..')
const argv = process.argv.slice(2)
const asJson = argv.includes('--json')
const requireDevice = argv.includes('--require-device')
const allowEmulator = argv.includes('--allow-emulator')
/** 出发去现场之前先在本机 Chrome 上把 B 段的页面操作预演一遍，见 runSelfTestUi()。 */
const selfTestUi = argv.includes('--self-test-ui')
/**
 * 只跑 A 段：android-sim 的 `ocr-device-a` step 走这条。
 *
 * 没有它，VM 上「B 段没设备」的 exit 2 会把那个 step 判红，而那个 step 问的
 * 本来就只是「前提条件绿不绿」。B 段没有单独跑的模式——A 段验的是 B 段的前提，
 * 前提红了再上设备只是浪费一次走查。
 */
const section = (argv.find((a) => a.startsWith('--section='))?.slice(10) ?? 'all').toLowerCase()
assert.ok(['a', 'all'].includes(section), `--section 只认 a / all，收到 ${section}`)
const runB = section !== 'a'

/** 退出码就是这份 harness 的对外契约，改它等于改所有调用方的判读。 */
const EXIT_OK = 0
const EXIT_FAIL = 1
const EXIT_SKIP = 2

/**
 * 机读标记与它的来路。
 *
 * 门禁读的是**去掉注释之后**的源码，所以这条链得活在常量里：check-round13 找
 * ROUND13_H2，check-round14 找 ROUND14_H2，删一枚就是让往轮的门禁当场退化。
 */
const MARKER = 'ROUND14_H2'
const SUPERSEDES = ['ROUND13_H2', 'ROUND12_H2']

/** 与 capacitor.config.json / AndroidManifest 对齐，改包名要一起改。 */
const APP_ID = 'com.hongen.literacy'

/** 真机上「相册选」那条路要用的样张目录；push 进去之后 QA 逐张走一遍。 */
const DEVICE_DIR = '/sdcard/Download/hongen-ocr'

/**
 * B 段自动走查用的样张目录。
 *
 * 和上面那个不是一回事：`/sdcard/Download/` 是给人用的（系统相册选择器里挑得到），
 * 而脚本用 CDP 的 DOM.setFileInputFiles 把路径直接塞给 file input 时，读文件的是
 * App 自己的进程——Android 10 起的分区存储下它读不了别家的 Download。
 * app-private 的 external files 目录不需要任何权限，adb 也写得进去。
 */
const DEVICE_SAMPLE_DIR = `/sdcard/Android/data/${APP_ID}/files/ocr-samples`

/** WebView 的 devtools socket 转出来的本地端口；被占了用 OCR_DEVICE_CDP_PORT 换一个。 */
const CDP_PORT = Number(process.env.OCR_DEVICE_CDP_PORT ?? 9333)

/**
 * 首次拍照要下载的那一坨。
 *
 * 6.0 MiB 不是拍脑袋：worker 0.11 + wasm 内核 3.72 + chi_sim 语言包 1.65 ≈ 5.5 MiB，
 * 留半兆余量。这条线一旦松开，最先付账的是低端安卓机上用移动流量的家长——
 * 而这件事在开发机上永远看不见。要换更大的语言包先改这条线，并在
 * .agent_workspace/r12-ocr-device-harness.md 里写清为什么值。
 */
const PACK_BUDGET_MIB = 6.0

/**
 * App 侧（WebView）真实样张的召回下限，与 scripts/test-ocr-app-matrix.mjs 同一条线。
 * 41 个字只准丢喷漆那张的「滑」——那是引擎自己的边界，Node 基准也认不出。
 */
const APP_RECALL_FLOOR = 40

/**
 * 设备侧召回下限，与 App 侧同一条线（ROUND14_H2）。
 *
 * 同一份 PNG 在 headless Chrome 和真机 WebView 上应当认出一样多的字——Tesseract 是
 * 确定性的。两边分家就说明设备侧另有东西在起作用（WebView 版本、wasm SIMD 没生效、
 * canvas 缩放插值不同），那正是 B 段唯一抓得到、A 段永远抓不到的东西。
 */
const DEVICE_RECALL_FLOOR = 40

/**
 * 「首屏认对」的张数下限（W2 口径）。
 *
 * 召回按字算，可孩子的体感是按张算的：十张里有一张整张认不出，比十张各丢一个字
 * 难受得多。所以除了字级下限，再守一条张级下限——期望字全中才算这张认对，
 * 引擎底线那几个字（queue.json 里 status:engine-limit 的）不计入。
 */
const FIRST_SCREEN_FLOOR = 9

/** 回流队列按轮次记账：本轮之前该修完的单还挂着，就是逾期。 */
const CURRENT_ROUND = 14

/**
 * 引擎底线要复核的轮次：engine-limit 不是「永远不修」，是「这一轮不修」。
 * 到了这一轮没人复核，A11 就把它重新变成一张要处理的单子。
 */
const ENGINE_LIMIT_REVIEW_BY = 16

/** adb push 的样张：低端机上推十张图不能变成一场等待。 */
const SAMPLE_MAX_KIB = 512
const SAMPLE_TOTAL_MAX_MIB = 2
const MIN_SAMPLES = 8

const passes = []
const fails = []
const skips = []

const pass = (msg) => passes.push(msg)
const fail = (msg) => fails.push(msg)
const check = (ok, msg, detail = '') => (ok ? pass(msg) : fail(detail ? `${msg} —— ${detail}` : msg))

/**
 * VM 上做不到的事只有一种交代方式：说清楚是谁、缺什么、到位之后跑哪条命令。
 * 「以后再说」不算 SKIP。
 */
const skip = (msg, owner, why) => skips.push({ msg, owner, why })

const read = (rel, base = appDir) => {
  try {
    return readFileSync(path.join(base, rel), 'utf8')
  } catch {
    return ''
  }
}
const has = (rel, base = appDir) => existsSync(path.join(base, rel))
const bytesOf = (rel, base = appDir) => {
  try {
    return statSync(path.join(base, rel)).size
  } catch {
    return 0
  }
}

/* ================================================================ A 段 · 前提条件 */

/* --- A1 Capacitor 壳层：WebView 里的 origin 决定了 SW 能不能注册 --- */
{
  const cap = read('capacitor.config.json')
  check(cap.includes(`"${APP_ID}"`), `A1 Capacitor appId = ${APP_ID}`, `capacitor.config.json 里是别的包名`)
  check(/"webDir"\s*:\s*"dist"/.test(cap), 'A1 webDir = dist，cap copy 搬的是构建产物')
  // androidScheme 不是 https 的话 WebView 跑在 http://localhost 上：
  // 那是个不安全上下文，Service Worker 根本注册不了，
  // 于是「下过一次就能离线认字」这条承诺在真机上直接不成立。
  check(
    /"androidScheme"\s*:\s*"https"/.test(cap),
    'A1 androidScheme = https，WebView 是安全上下文，SW 注册得了',
    '改成 http 之后 SW 不注册，真机离线认字会整条失效'
  )
}

/* --- A2 引擎资源全部同源：断网的平板上 CDN 是一条死路 --- */
{
  const ocr = read('src/utils/ocr.js')
  for (const [what, key] of [
    ['worker 脚本', 'workerPath'],
    ['wasm 内核', 'corePath'],
    ['语言包目录', 'langPath']
  ]) {
    check(
      new RegExp(`${key}:\\s*ocrAssetUrl\\(`).test(ocr),
      `A2 ${what}（${key}）走同源 ocrAssetUrl()`,
      '指到别处就等于把离线识字交给网络'
    )
  }
  // 只盯字符串字面量里的 CDN 域名：注释里提 jsDelivr 是在解释「为什么不能走它」，
  // 真正会把离线识字送回网络的是代码里写死的那个 URL。
  check(
    !/["'`]https?:\/\/[^"'`]*(jsdelivr|unpkg|cdnjs)/i.test(ocr),
    'A2 utils/ocr.js 里没有写死的 CDN 地址',
    'tesseract.js 默认从 jsDelivr 取包，回退到默认值在飞行模式下就是 404'
  )
  // blob: 起的 worker 属于 opaque origin，不在 Service Worker 的控制范围内，
  // 它内部的 importScripts / fetch 拿不到 OCR 缓存。在线时一切正常，
  // 飞行模式下才会挂——正是那种只有真机能发现、发现了又极难定位的问题。
  check(
    /workerBlobURL:\s*false/.test(ocr),
    'A2 workerBlobURL: false，worker 归 Service Worker 管',
    '改成 true 之后离线认字会在真机上静默失败'
  )
  // Capacitor 把 dist 挂在 https://localhost/ 根上，写死 /ocr/ 也能跑；
  // 用 baseURI 是为了让子目录部署的 Web 版和 WebView 共用同一份代码。
  check(
    /new URL\(`ocr\/\$\{file\}`,\s*document\.baseURI\)/.test(ocr),
    'A2 ocrAssetUrl 按 baseURI 拼相对路径，Web 子目录与 WebView 共用一套'
  )
}

/* --- A3 引擎包落盘、清单对得上、体积在预算内 --- */
{
  // worker / wasm / manifest 由 prebuild 的 gen-ocr-assets.mjs 从 node_modules 复制，
  // 且被 .gitignore 排除。全都不在 = 这个仓库还没构建过，不是退化。
  const packFiles = ['chi_sim.traineddata.gz', 'tesseract-core-simd-lstm.wasm.js', 'worker.min.js']
  const present = packFiles.filter((f) => has(`public/ocr/${f}`))
  if (!has('public/ocr/manifest.json') && present.length <= 1) {
    skip(
      'A3 引擎包体检',
      '本机',
      '还没生成过 public/ocr/（gen-ocr-assets.mjs 挂在 prebuild 上）：先跑 npm run build 或 npm run gen:ocr'
    )
  } else {
    check(has('public/ocr/manifest.json'), 'A3 public/ocr/manifest.json 在')
    let manifest = null
    try {
      manifest = JSON.parse(read('public/ocr/manifest.json'))
    } catch {
      fail('A3 manifest.json 解析不了，useOcr 的 readPack() 会报「识字包没装上」')
    }
    let total = 0
    for (const file of packFiles) {
      const bytes = bytesOf(`public/ocr/${file}`)
      total += bytes
      check(bytes > 0, `A3 ${file} 落盘（${(bytes / 1024).toFixed(0)} KiB）`)
      const declared = manifest?.files?.find((f) => f.name === file)?.bytes
      // 清单里的字节数就是界面上那句「要下 5.5 MB」的来源。对不上不会报错，
      // 只会让孩子等的时间和看到的数字长期不一致。
      if (bytes > 0) {
        check(
          declared === bytes,
          `A3 ${file} 的清单字节数与磁盘一致`,
          `清单写 ${declared}，磁盘 ${bytes}——重跑 npm run gen:ocr`
        )
      }
    }
    const mib = total / 1024 / 1024
    check(
      mib <= PACK_BUDGET_MIB,
      `A3 引擎包合计 ${mib.toFixed(2)} MiB ≤ ${PACK_BUDGET_MIB} MiB`,
      '首次拍照要在移动网络上下完这一坨，超预算先去看看能不能换更小的语言包'
    )
    check(has('public/ocr/sample-photo.png'), 'A3 示例图在，没相机权限也走得完整条链')
  }
}

/* --- A4 Service Worker：下过一次的 6 MB 不能被下一次发版清掉 --- */
{
  const sw = read('public/sw.js')
  const ocrCache = sw.match(/const OCR_CACHE\s*=\s*'([^']+)'/)?.[1]
  const prefix = sw.match(/const CACHE_PREFIX\s*=\s*'([^']+)'/)?.[1]
  check(Boolean(ocrCache), 'A4 sw.js 里有独立的 OCR_CACHE')
  // activate 时会删掉所有以 CACHE_PREFIX 开头的旧缓存。OCR 包要是也用这个前缀，
  // 每发一版孩子都得重下 5.5 MB——桌面上感觉不到，按流量计费的手机上感觉得到。
  check(
    Boolean(ocrCache && prefix && !ocrCache.startsWith(prefix)),
    'A4 OCR 缓存名不带版本前缀，换版本不会被 activate 清掉',
    `OCR_CACHE=${ocrCache} 撞上了 CACHE_PREFIX=${prefix}`
  )
  // 把 404 或半截的 range 响应存进缓存，离线时会一直坏下去，且清缓存前好不了
  check(
    /response\.ok\s*&&\s*response\.status === 200/.test(sw),
    'A4 只缓存完整的 200 响应，不会把半截的 wasm 钉死在缓存里'
  )
  check(
    /exclude:\s*\[[^\]]*ocr\\?\//.test(read('vite.config.js')),
    'A4 预缓存排除了 OCR 大文件，装 SW 时不会先拉 6 MB'
  )
}

/* --- A5 取图这一步：Android WebView 里只有 file input 是开箱即用的 --- */
{
  const view = read('src/views/CameraOcrView.vue')
  check(
    /capture="environment"/.test(view),
    'A5 「拍一张」带 capture="environment"，安卓直接调后置摄像头'
  )
  check(/accept="image\/\*"/.test(view), 'A5 file input 限定 image/*')
  // getUserMedia 在 Android WebView 里要 app 侧实现 onPermissionRequest 才给过，
  // Capacitor 默认壳层没接这一段：桌面 Chrome 上一路顺，装到手机上就是黑屏。
  check(
    !/navigator\.mediaDevices|getUserMedia\(/.test(view),
    'A5 没有调 getUserMedia，WebView 里不需要额外的权限桥接',
    'WebView 默认拒绝 getUserMedia，这条路在真机上是黑屏'
  )
  // 相册那个 input 不能带 capture，否则安卓会跳过相册直接开相机——
  // 「电脑上没摄像头也能选照片」这条路就没了
  const albumBlock = view.match(/ref="albumInput"[\s\S]{0,240}?\/>/)?.[0] ?? ''
  check(
    Boolean(albumBlock) && !/capture=/.test(albumBlock),
    'A5 「相册选」的 input 不带 capture，不会被安卓劫持成拍照'
  )
}

/* --- A6 权限：家长在安装页上看到的每一条都要有出处 --- */
{
  const xml = read('android/app/src/main/AndroidManifest.xml')
  check(Boolean(xml), 'A6 AndroidManifest.xml 在')
  check(xml.includes('android.permission.INTERNET'), 'A6 声明了 INTERNET（首次下引擎包要用）')
  // 走 file input 时，拍照是系统相机那个 app 在做，我们只拿回一个 Uri。
  // 多申请一条 CAMERA 不会让功能更好使，只会在商店审核和家长眼前多一行
  // 「此应用可以拍摄照片和录制视频」。
  check(
    !xml.includes('android.permission.CAMERA'),
    'A6 没有多要 CAMERA 权限（file input 由系统相机代拍）',
    '走 file input 却申请 CAMERA，等于凭空吓一次家长'
  )
  check(
    !/READ_EXTERNAL_STORAGE|READ_MEDIA_IMAGES/.test(xml),
    'A6 没有多要相册读取权限（选图走的是系统选择器）'
  )
}

/* --- A7 要推给设备的真实样张 --- */
{
  const dir = path.join(appDir, 'scripts/fixtures/ocr')
  const files = existsSync(dir) ? readdirSync(dir).filter((f) => /^real-.*\.png$/.test(f)) : []
  check(
    files.length >= MIN_SAMPLES,
    `A7 真实样张 ${files.length} 张（下限 ${MIN_SAMPLES}），够铺开一轮真机走查`
  )
  let total = 0
  const oversized = []
  for (const f of files) {
    const kib = bytesOf(`scripts/fixtures/ocr/${f}`) / 1024
    total += kib
    if (kib > SAMPLE_MAX_KIB) oversized.push(`${f} ${kib.toFixed(0)} KiB`)
  }
  check(
    oversized.length === 0,
    `A7 每张样张 ≤ ${SAMPLE_MAX_KIB} KiB`,
    `超了：${oversized.join('、')}`
  )
  check(
    total / 1024 <= SAMPLE_TOTAL_MAX_MIB,
    `A7 样张合计 ${(total / 1024).toFixed(2)} MiB ≤ ${SAMPLE_TOTAL_MAX_MIB} MiB，adb push 不至于等太久`
  )
  // 真机走查要照着矩阵一格一格走，清单里没有 tier 就只能凭图名瞎猜
  let tiered = 0
  try {
    const manifest = JSON.parse(read('scripts/fixtures/ocr/real-samples.json'))
    tiered = manifest.samples.filter(
      (s) => s?.tier?.light && s?.tier?.angle && s?.tier?.paper
    ).length
  } catch {
    tiered = 0
  }
  check(
    tiered >= MIN_SAMPLES,
    `A7 ${tiered} 张样张带着光照/角度/纸质坐标，真机走查照着格子走`,
    '缺 tier 的样张在真机报告里说不清覆盖了哪一类'
  )
}

/* --- A8 cap sync 之后，OCR 包真的进了 APK 的 assets --- */
{
  const assets = 'android/app/src/main/assets/public'
  if (!has(assets)) {
    skip(
      'A8 APK assets 里的 OCR 包',
      '本机 / Android Build',
      `还没同步过（${assets} 不存在）：先跑 npm run sync:android:literacy`
    )
  } else {
    // cap copy 漏掉 public/ 下的大文件不会报错，只会让装机之后一按「开始认字」
    // 就 404。装出 APK 之前在这里拦下来最便宜。
    for (const f of ['ocr/chi_sim.traineddata.gz', 'ocr/sample-photo.png', 'index.html']) {
      check(has(`${assets}/${f}`), `A8 assets/public/${f} 已随 cap copy 进包`)
    }
  }
}

/* --- A9 App 侧那份 WebView 实测矩阵：预处理有没有偷偷把字吃掉（ROUND14_H2） --- */
{
  const rel = '.agent_workspace/evidence/r14/ocr/app-webview-matrix.json'
  let matrix = null
  try {
    matrix = JSON.parse(read(rel, repoDir))
  } catch {
    matrix = null
  }
  if (!matrix) {
    fail(`A9 缺 ${rel}——先跑 npm --prefix apps/literacy-app run test:ocr:app`)
  } else {
    const got = Number(matrix.passCount ?? 0)
    const all = Number(matrix.total ?? 0)
    // Node 基准（test-ocr-accuracy）跑的是原图，App 里那张图先过 preprocess()。
    // 两个数一分家，R13 收线时才看见 App 侧只有 33/41——七个字丢在预处理里，
    // 而原图基准一分都没掉。这条线就是不让它再分家。
    check(
      got >= APP_RECALL_FLOOR && all >= 41,
      `A9 App 侧（WebView）真实样张召回 ${got}/${all} ≥ ${APP_RECALL_FLOOR}/41`,
      '预处理又把字吃掉了：逐张对账看矩阵 JSON 的 samples 段'
    )
    // 这份是 VM 上的 headless Chrome。它证得了预处理，证不了设备——
    // 两件事混成一句「真机验过了」，是这套 evidence 最容易出的假。
    check(
      matrix.simulated === true && matrix.onDevice !== true,
      'A9 矩阵 JSON 自报 simulated:true，没有冒充真机',
      '真机结论只认 B 段落在 evidence/r14/android/ 的那一份'
    )
  }
}

const QUEUE_REL = 'scripts/fixtures/ocr/regressions/queue.json'
const regressionQueue = (() => {
  try {
    return JSON.parse(read(QUEUE_REL))
  } catch {
    return null
  }
})()
const queueItems = Array.isArray(regressionQueue?.items) ? regressionQueue.items : []

/**
 * 引擎底线清单：queue.json 里 status:'engine-limit' 那几条允许丢的字（ROUND14_H2）。
 *
 * 「这个字引擎本来就认不出」不能是脚本里一个写死的常量——写死了就没人知道它是
 * 哪一天、凭什么被放进来的，也没人会再去看它。所以底线只有一个来源：队列里那张
 * 带根因、带复核轮次的单子。B 段扣分时按它扣，A11 反过来守它没烂掉。
 */
const engineLimit = new Map(
  queueItems
    .filter((i) => i?.status === 'engine-limit' && i.sample)
    .map((i) => [i.sample, { id: i.id, chars: [...String(i.engineMissed ?? '')], item: i }])
)

/* --- A10 失败样本回流队列：修好的要关单，没修的不许逾期（ROUND14_H2） --- */
{
  const rel = QUEUE_REL
  const items = queueItems
  check(items.length >= 1, `A10 回流队列在（${items.length} 条）`, `${rel} 读不出 items`)
  // 关单要给根因。只把 status 改成 closed、不写清是什么把字吃掉的，
  // 下一次同样的坑还会再踩一遍。
  const sloppy = items.filter((i) => i.status === 'closed' && !i.rootCause)
  check(sloppy.length === 0, 'A10 关掉的单都写了根因', `缺 rootCause：${sloppy.map((i) => i.id).join('、')}`)
  const overdue = items.filter(
    (i) => (i.status === 'new' || i.status === 'triaged') && Number(i.dueRound) <= CURRENT_ROUND
  )
  check(
    overdue.length === 0,
    `A10 没有逾期单（本轮 R${CURRENT_ROUND}）`,
    `逾期：${overdue.map((i) => `${i.id}(R${i.dueRound})`).join('、')}`
  )
}

/* --- A11 引擎底线单：不排期不等于不记账（ROUND14_H2） --- */
{
  // engine-limit 是队列里唯一一种「不修也算处理完」的状态，所以它最容易变成
  // 一个垃圾桶：认不出的字往里一扔，队列就干净了。四条硬要求把这条路堵死——
  // 说清丢的是哪个字、为什么是引擎而不是我们的问题、什么情况下重新排期、
  // 以及最晚哪一轮必须有人再看一眼。
  const limits = queueItems.filter((i) => i?.status === 'engine-limit')
  check(
    limits.length === engineLimit.size,
    `A11 ${limits.length} 条引擎底线单都指名了样张`,
    '缺 sample 字段的底线单对不上任何一张回归样张，B 段扣不出分'
  )
  const vague = limits.filter(
    (i) => !String(i.engineMissed ?? '').trim() || !String(i.rootCause ?? '').trim()
  )
  check(
    vague.length === 0,
    'A11 引擎底线单都写清了丢哪个字、为什么是引擎的边界',
    `缺 engineMissed / rootCause：${vague.map((i) => i.id).join('、')}`
  )
  // 「什么情况下重新排期」是这类单子唯一的出口：换语言包、换引擎版本、
  // 补一张同格样张——写不出出口，就说明它根本没被想清楚，只是被放弃了。
  const noExit = limits.filter((i) => String(i.reopenIf ?? '').trim().length < 8)
  check(
    noExit.length === 0,
    'A11 引擎底线单都写了重新排期的条件（reopenIf）',
    `缺 reopenIf：${noExit.map((i) => i.id).join('、')}`
  )
  const stale = limits.filter(
    (i) => !Number.isInteger(i.reviewRound) || Number(i.reviewRound) <= CURRENT_ROUND
  )
  check(
    stale.length === 0,
    `A11 引擎底线单都挂着复核轮次（≥R${CURRENT_ROUND + 1}，当前口径 R${ENGINE_LIMIT_REVIEW_BY}）`,
    `复核轮次缺失或已过期：${stale.map((i) => `${i.id}(${i.reviewRound ?? '无'})`).join('、')}`
  )
  // 底线单认的字必须真的属于那张样张，否则 B 段会凭空多扣或少扣一个字
  let manifest = null
  try {
    manifest = JSON.parse(read('scripts/fixtures/ocr/real-samples.json'))
  } catch {
    manifest = null
  }
  const orphan = [...engineLimit.entries()].filter(([name, limit]) => {
    const sample = manifest?.samples?.find((s) => s.name === name)
    return !sample || limit.chars.some((c) => !sample.text.includes(c))
  })
  check(
    orphan.length === 0,
    'A11 底线单里的字都出自对应样张的期望文字',
    `对不上：${orphan.map(([name, l]) => `${l.id}/${name}`).join('、')}`
  )
}

/* ============================================================ B 段 · 真机执行 */

const device = {
  serial: '',
  model: '',
  release: '',
  sdk: '',
  webview: '',
  size: '',
  density: '',
  emulator: false,
  fingerprint: ''
}

/**
 * B 段的机读结论，字段名对齐 .agent_workspace/round14-architecture.md §2.3。
 *
 * 探针只读 pass / onDevice / simulated 三个字段，别的都是给人看的溯源。
 * 但恰恰因为探针只读三个字段，这份 JSON 更要把「凭什么 pass」摊开写：
 * 哪台机器、哪十张图、每张认出几个字、飞行模式下还剩几个——否则下一轮
 * 谁也说不清这一次的绿灯是怎么来的。
 */
const bReport = {
  marker: MARKER,
  supersedes: SUPERSEDES,
  schema: 'ocr-device-b/1',
  capturedAt: '',
  /** 三态：pass = 设备上跑完且全绿；fail = 有断言红；skipped = 没跑成，不是通过。 */
  status: 'skipped',
  pass: false,
  onDevice: false,
  simulated: false,
  emulator: false,
  exitCode: EXIT_SKIP,
  appId: APP_ID,
  device: null,
  deviceDir: DEVICE_DIR,
  sampleDir: DEVICE_SAMPLE_DIR,
  samples: 0,
  firstScreenCorrect: 0,
  firstScreenFloor: FIRST_SCREEN_FLOOR,
  recall: { hit: 0, total: 0, floor: DEVICE_RECALL_FLOOR },
  coldStartMs: null,
  peakPssKib: null,
  offline: null,
  engineLimit: [...engineLimit.entries()].map(([sample, l]) => ({
    id: l.id,
    sample,
    chars: l.chars.join(''),
    reviewRound: l.item?.reviewRound ?? null
  })),
  rows: [],
  steps: [],
  skips: [],
  notes: []
}

const bstep = (id, status, msg, detail = '') => {
  bReport.steps.push({ id, status, msg, detail })
  if (status === 'pass') pass(`${id} ${msg}`)
  else if (status === 'fail') fail(detail ? `${id} ${msg} —— ${detail}` : `${id} ${msg}`)
}
const bcheck = (ok, id, msg, detail = '') => bstep(id, ok ? 'pass' : 'fail', msg, detail)
const bskip = (id, msg, owner, why) => {
  bReport.steps.push({ id, status: 'skip', msg, detail: why })
  skip(`${id} ${msg}`, owner, why)
}

function adb(args, serial = '', timeout = 60_000) {
  return execFileSync('adb', serial ? ['-s', serial, ...args] : args, {
    encoding: 'utf8',
    timeout,
    stdio: ['ignore', 'pipe', 'pipe']
  }).trim()
}

const quietAdb = (args, serial = '', timeout = 60_000) => {
  try {
    return adb(args, serial, timeout)
  } catch {
    return ''
  }
}

/**
 * 模拟器不是真机。
 *
 * 一台 x86 模拟器上跑出来的召回和真机差不多——正因为差不多，它才最像一份
 * 可以拿来交差的证据。可它证不了的恰恰是 B 段存在的理由：真机的 WebView 版本、
 * 真机的内存、真机上 wasm SIMD 有没有真的走 SIMD。所以判定放在这里，
 * 而不是留给写报告的人自觉。
 */
function looksLikeEmulator(serial, props) {
  const blob = `${serial} ${props.fingerprint} ${props.model} ${props.characteristics} ${props.hardware}`
  return props.qemu === '1' || /emulator|sdk_gphone|generic|goldfish|ranchu/i.test(blob)
}

function findDevice() {
  try {
    execFileSync('adb', ['version'], { stdio: 'ignore', timeout: 10_000 })
  } catch {
    return { ok: false, why: '这台机器上没有 adb（Cursor Cloud VM 默认不带 Android SDK）' }
  }
  let list = ''
  try {
    list = adb(['devices'])
  } catch (err) {
    return { ok: false, why: `adb devices 起不来：${err.message}` }
  }
  const serials = list
    .split('\n')
    .slice(1)
    .map((line) => line.trim().split(/\s+/))
    .filter(([, state]) => state === 'device')
    .map(([serial]) => serial)
  if (!serials.length) return { ok: false, why: 'adb 在，但没有处于 device 状态的设备或模拟器' }

  // 有多台时优先挑真机：插着一台手机又开着模拟器的开发机上，挑错一台就等于
  // 让这轮证据默默降级成模拟结论。
  const scored = serials.map((serial) => {
    const props = {
      fingerprint: quietAdb(['shell', 'getprop', 'ro.build.fingerprint'], serial, 15_000),
      model: quietAdb(['shell', 'getprop', 'ro.product.model'], serial, 15_000),
      characteristics: quietAdb(['shell', 'getprop', 'ro.build.characteristics'], serial, 15_000),
      hardware: quietAdb(['shell', 'getprop', 'ro.hardware'], serial, 15_000),
      qemu: quietAdb(['shell', 'getprop', 'ro.kernel.qemu'], serial, 15_000)
    }
    return { serial, props, emulator: looksLikeEmulator(serial, props) }
  })
  const real = scored.find((s) => !s.emulator)
  const picked = real ?? scored[0]
  if (picked.emulator && !allowEmulator) {
    return {
      ok: false,
      emulatorOnly: true,
      why:
        `只连着模拟器（${picked.serial}${picked.props.model ? ` · ${picked.props.model}` : ''}），` +
        '模拟器不能当真机结论：要验 harness 本身加 --allow-emulator（结论会标 simulated）'
    }
  }
  return { ok: true, serial: picked.serial, all: serials, emulator: picked.emulator, props: picked.props }
}

/* --- B1 设备指纹 --- */

function collectFingerprint(serial) {
  device.serial = serial
  const prop = (key) => quietAdb(['shell', 'getprop', key], serial, 15_000)
  device.model = prop('ro.product.model')
  device.release = prop('ro.build.version.release')
  device.sdk = prop('ro.build.version.sdk')
  device.fingerprint = prop('ro.build.fingerprint')
  device.size = quietAdb(['shell', 'wm', 'size'], serial, 15_000).replace(/\s+/g, ' ')
  device.density = quietAdb(['shell', 'wm', 'density'], serial, 15_000).replace(/\s+/g, ' ')
  // WebView 版本是拍照识字最要紧的一条环境信息：wasm SIMD 要 Chromium 91+，
  // 低于这个版本 useOcr 会走到「浏览器太旧」那条分支，跟引擎本身无关。
  // 装了 Chrome 当 WebView 实现的机器上 com.google.android.webview 可能查不到，
  // 所以再往下问一次 WebView 自己报的 UA。
  for (const pkg of ['com.google.android.webview', 'com.android.webview', 'com.android.chrome']) {
    const dump = quietAdb(['shell', 'dumpsys', 'package', pkg], serial, 30_000)
    const version = dump.match(/versionName=([\w.]+)/)?.[1]
    if (version) {
      device.webview = version
      device.webviewPackage = pkg
      break
    }
  }
}

/* --- B4 的 WebView 通道：adb forward + CDP --- */

/**
 * 找到 App 那个 WebView 的 devtools socket。
 *
 * 名字是 `webview_devtools_remote_<浏览器进程 pid>`，而 WebView 的浏览器进程
 * 就是 App 自己的进程。渲染进程也会挂一个 `..._<renderer pid>` 的 socket，
 * 接错了那个就只能看见一个空白 target，所以先按 pid 对号。
 */
function webviewSocket(serial) {
  const unix = quietAdb(['shell', 'cat', '/proc/net/unix'], serial, 20_000)
  const names = [...new Set([...unix.matchAll(/(webview_devtools_remote_\w+)/g)].map((m) => m[1]))]
  const pid = quietAdb(['shell', 'pidof', APP_ID], serial, 15_000).split(/\s+/)[0]
  return names.find((n) => pid && n.endsWith(`_${pid}`)) ?? names[0] ?? ''
}

async function cdpJson(pathname) {
  const res = await fetch(`http://127.0.0.1:${CDP_PORT}${pathname}`)
  if (!res.ok) throw new Error(`${pathname} 返回 ${res.status}`)
  return res.json()
}

async function setAirplaneMode(serial, on) {
  // API 30 起 shell 就能开关飞行模式；老机器退回 settings + 广播（要 root 才广播得动，
  // 广播不出去时飞行模式仍然会被 settings 那半条打开，够用了）。
  try {
    adb(['shell', 'cmd', 'connectivity', 'airplane-mode', on ? 'enable' : 'disable'], serial, 30_000)
    return true
  } catch {
    quietAdb(['shell', 'settings', 'put', 'global', 'airplane_mode_on', on ? '1' : '0'], serial)
    quietAdb(
      ['shell', 'am', 'broadcast', '-a', 'android.intent.action.AIRPLANE_MODE', '--ez', 'state', String(on)],
      serial
    )
    return false
  }
}

/**
 * B 段主流程。
 *
 * 每一步都往 bReport.steps 里记一行：这份证据将来要回答的问题是
 * 「哪一步在哪台机器上红的」，而不是「总共几项通过」。
 */
async function runDeviceSection(found) {
  const serial = found.serial
  collectFingerprint(serial)
  device.emulator = Boolean(found.emulator)
  bReport.emulator = device.emulator
  // 模拟器上跑出来的一切都只能算模拟：onDevice 保持 false，
  // 证据也不会写进 ocr-device-b.json，H2 那条腿点不亮。
  bReport.onDevice = !device.emulator
  bReport.simulated = device.emulator
  bReport.device = { ...device }

  bcheck(
    Boolean(device.model),
    'B1',
    `设备指纹：${device.model || '未知型号'} · Android ${device.release}（API ${device.sdk}）` +
      `${device.emulator ? ' · 模拟器' : ''}`,
    'getprop 取不到型号，这台设备的连接不稳'
  )
  const chromium = Number(String(device.webview).split('.')[0] || 0)
  bcheck(
    chromium >= 91,
    'B1',
    `System WebView ${device.webview || '未知'}（wasm SIMD 需要 Chromium 91+）`,
    '这台设备的 WebView 太旧，拍照识字会落到「浏览器太旧」那条降级分支'
  )

  /* --- B2 样张铺开：给人的那份进相册，给脚本的那份进 app 私有目录 --- */
  const fixtureDir = path.join(appDir, 'scripts/fixtures/ocr')
  const sampleFiles = readdirSync(fixtureDir)
    .filter((f) => /^real-.*\.png$/.test(f))
    .sort()
  let pushed = 0
  try {
    quietAdb(['shell', 'mkdir', '-p', DEVICE_DIR], serial)
    adb(['shell', 'mkdir', '-p', DEVICE_SAMPLE_DIR], serial)
    for (const f of sampleFiles) {
      adb(['push', path.join(fixtureDir, f), `${DEVICE_SAMPLE_DIR}/${f}`], serial)
      quietAdb(['push', path.join(fixtureDir, f), `${DEVICE_DIR}/${f}`], serial)
      pushed += 1
    }
    // 不扫一遍媒体库的话，相册选择器里看不见刚推上去的图
    quietAdb(
      ['shell', 'am', 'broadcast', '-a', 'android.intent.action.MEDIA_SCANNER_SCAN_FILE', '-d', `file://${DEVICE_DIR}`],
      serial
    )
  } catch (err) {
    bstep('B2', 'fail', `样张 push 失败（已推 ${pushed}/${sampleFiles.length}）`, err.message)
  }
  const onDeviceCount = quietAdb(['shell', 'ls', DEVICE_SAMPLE_DIR], serial)
    .split('\n')
    .filter((f) => /^real-.*\.png$/.test(f.trim())).length
  bcheck(
    pushed === sampleFiles.length && onDeviceCount === sampleFiles.length,
    'B2',
    `${onDeviceCount}/${sampleFiles.length} 张真实样张已进设备（${DEVICE_SAMPLE_DIR} + ${DEVICE_DIR}）`,
    `push 了 ${pushed} 张，设备上数出来 ${onDeviceCount} 张`
  )

  /* --- B3 冷启：装没装、起不起得来、起来花了多久、占多少内存 --- */
  const installed = quietAdb(['shell', 'pm', 'list', 'packages', APP_ID], serial).includes(APP_ID)
  if (!installed) {
    bskip(
      'B3',
      `冷启 ${APP_ID} 到 /#/ocr`,
      'Android Build',
      `设备上没装 ${APP_ID}：先 npm run sync:android:literacy && (cd apps/literacy-app/android && ./gradlew assembleDebug) 再 adb install -r`
    )
    bskip('B4', '设备侧十张样张的识别结果', 'Android QA', '要先装上 App')
    bskip('B5', '飞行模式下引擎从 SW 缓存起来', 'Android QA', '要先装上 App')
    return
  }
  quietAdb(['shell', 'am', 'force-stop', APP_ID], serial)
  let launch = ''
  try {
    launch = adb(['shell', 'am', 'start', '-W', '-n', `${APP_ID}/.MainActivity`], serial, 120_000)
  } catch (err) {
    bstep('B3', 'fail', `拉不起 ${APP_ID}`, err.message)
    return
  }
  bReport.coldStartMs = Number(launch.match(/TotalTime:\s*(\d+)/)?.[1] ?? 0) || null
  bcheck(
    /Status:\s*ok/i.test(launch) || Boolean(bReport.coldStartMs),
    'B3',
    `冷启 ${APP_ID} 用时 ${bReport.coldStartMs ?? '未知'} ms`,
    launch.split('\n').slice(0, 3).join(' / ')
  )

  /* --- B4 接进 WebView，逐张认 --- */
  const socket = webviewSocket(serial)
  if (!socket) {
    bskip(
      'B4',
      '接进 App 的 WebView 逐张认字',
      'Android Build',
      'WebView 没开远程调试：debug 包才有（Capacitor 在 debuggable 构建里调 setWebContentsDebuggingEnabled）。' +
        '装 release 包时这一段只能由 QA 用眼睛走 ANDROID-DEVICE-CHECKLIST §4'
    )
    bskip('B5', '飞行模式下引擎从 SW 缓存起来', 'Android QA', '接不进 WebView 就读不回识别结果')
    return
  }

  const puppeteer = await import('puppeteer-core').then((m) => m.default ?? m)
  quietAdb(['forward', '--remove', `tcp:${CDP_PORT}`], serial)
  adb(['forward', `tcp:${CDP_PORT}`, `localabstract:${socket}`], serial)
  let browser = null
  let restoreAirplane = false
  try {
    const version = await cdpJson('/json/version')
    bReport.webViewUserAgent = version['User-Agent'] ?? ''
    bReport.webViewBrowser = version.Browser ?? ''
    if (!version.webSocketDebuggerUrl) {
      throw new Error('WebView 的 /json/version 没给 webSocketDebuggerUrl，这个 WebView 版本接不了浏览器级 CDP')
    }
    browser = await puppeteer.connect({
      browserWSEndpoint: version.webSocketDebuggerUrl,
      defaultViewport: null
    })
    const pages = await browser.pages()
    const page =
      pages.find((p) => /^https?:\/\/localhost/.test(p.url())) ?? pages.find((p) => p.url() !== 'about:blank')
    if (!page) throw new Error('WebView 里没有可用的页面 target')
    bReport.pageUrl = page.url()
    // 壳层是不是跑在安全上下文里，只有在设备上问才算数：A1 查的是配置，这里查的是事实。
    const secure = await page.evaluate('({ origin: location.origin, isSecureContext, sw: Boolean(navigator.serviceWorker) })')
    bcheck(
      secure.isSecureContext === true,
      'B4',
      `WebView 跑在安全上下文（${secure.origin}），Service Worker 注册得了`,
      'androidScheme 不是 https，SW 注册不了，离线认字整条失效'
    )

    await openOcrRoute(page)
    const manifest = JSON.parse(read('scripts/fixtures/ocr/real-samples.json'))
    const wantedByName = new Map(manifest.samples.map((s) => [s.name, s]))

    let hit = 0
    let total = 0
    let firstScreen = 0
    let index = 0
    for (const file of sampleFiles) {
      const name = file.replace(/\.png$/, '')
      const sample = wantedByName.get(name)
      if (!sample) continue
      index += 1
      // 第一张要连引擎一起装起来（近 6 MB 的 wasm + 语言包），给足时间；
      // 后面几张 worker 常驻，慢下来本身就是信号。
      const budget = index === 1 ? 300_000 : 120_000
      const started = Date.now()
      let out = null
      try {
        out = await recognizeInPage(page, `${DEVICE_SAMPLE_DIR}/${file}`, budget)
      } catch (err) {
        bstep('B4', 'fail', `${name} 在设备上没跑完`, err.message)
        continue
      }
      const ms = Date.now() - started
      const allowed = engineLimit.get(name)?.chars ?? []
      const score = scoreSample(sample.text, out, allowed)
      hit += score.hit
      total += score.total
      if (score.firstScreenCorrect) firstScreen += 1
      bReport.rows.push({
        name,
        tier: sample.tier,
        expect: sample.text,
        hit: score.hit,
        total: score.total,
        missed: score.missed,
        engineLimitAllowed: allowed.join(''),
        firstScreenCorrect: score.firstScreenCorrect,
        confidence: out.confidence,
        phase: out.phase,
        ms
      })
    }

    bReport.samples = bReport.rows.length
    bReport.recall = { hit, total, floor: DEVICE_RECALL_FLOOR }
    bReport.firstScreenCorrect = firstScreen
    bcheck(
      bReport.rows.length >= MIN_SAMPLES,
      'B4',
      `设备上逐张走完 ${bReport.rows.length} 张真实样张`,
      `只走完 ${bReport.rows.length} 张，下限 ${MIN_SAMPLES}`
    )
    bcheck(
      hit >= DEVICE_RECALL_FLOOR,
      'B4',
      `设备侧召回 ${hit}/${total} ≥ ${DEVICE_RECALL_FLOOR}`,
      'App 侧矩阵是 40/41 而设备上更低：差在 WebView 的 canvas 实现或 wasm SIMD，逐张看 rows'
    )
    bcheck(
      firstScreen >= FIRST_SCREEN_FLOOR,
      'B4',
      `${firstScreen}/${bReport.rows.length} 张首屏认对（下限 ${FIRST_SCREEN_FLOOR}，引擎底线字不计）`,
      '整张认不出比每张丢一个字难受得多，这条线守的是体感'
    )
    bReport.peakPssKib =
      Number(
        quietAdb(['shell', 'dumpsys', 'meminfo', APP_ID], serial, 60_000).match(
          /TOTAL(?:\s+PSS)?:?\s+(\d+)/
        )?.[1] ?? 0
      ) || null

    /* --- B5 飞行模式：下过一次的 6 MB 还在不在 --- */
    const online = bReport.rows[0]
    if (!online) {
      bskip('B5', '飞行模式下复跑一张', 'Android QA', 'B4 一张都没跑成，没有可比的基线')
    } else {
      const viaShell = await setAirplaneMode(serial, true)
      restoreAirplane = true
      await new Promise((r) => setTimeout(r, 4000))
      await page.reload({ waitUntil: 'load', timeout: 120_000 })
      await openOcrRoute(page)
      const packOk = await page.evaluate(
        `fetch(new URL('ocr/manifest.json', document.baseURI).href, { cache: 'force-cache' })
           .then((r) => r.ok).catch(() => false)`
      )
      const offlineOut = await recognizeInPage(page, `${DEVICE_SAMPLE_DIR}/${online.name}.png`, 300_000)
      const offlineHit = scoreSample(online.expect, offlineOut).hit
      bReport.offline = {
        airplaneModeVia: viaShell ? 'cmd connectivity' : 'settings + broadcast',
        sample: online.name,
        onlineHit: online.hit,
        offlineHit,
        total: online.total,
        packFetchOk: packOk === true
      }
      bcheck(packOk === true, 'B5', '飞行模式下引擎清单仍取得到（同源资源没走网络）')
      bcheck(
        offlineHit === online.hit,
        'B5',
        `飞行模式下复跑 ${online.name}：${offlineHit}/${online.total}，与联网时一致`,
        `联网 ${online.hit}/${online.total}，断网 ${offlineHit}/${online.total}——引擎在断网后没能从缓存起来`
      )
    }
  } catch (err) {
    bstep('B4', 'fail', '设备侧 WebView 走查中断', err.message)
  } finally {
    if (restoreAirplane) await setAirplaneMode(serial, false)
    if (browser) await browser.disconnect().catch(() => {})
    quietAdb(['forward', '--remove', `tcp:${CDP_PORT}`], serial)
  }

  // 脚本走完的是「同一张 PNG 在设备上认出几个字」。真机上还剩下几件只有人能做的事，
  // 它们不进这份证据，但也不许因此消失——写进 notes，由 ANDROID-DEVICE-CHECKLIST 兜。
  bReport.notes.push(
    `相机取景、权限弹窗、TalkBack 与温升仍由 Android QA 按 ANDROID-DEVICE-CHECKLIST §4 走，样张已推到 ${DEVICE_DIR}`
  )
}

/* ------------------------- S 段 · 在本机 Chrome 上预演 B 段的页面操作 ------ */

/**
 * B 段里唯一没法在开发机上预演的，只有 adb forward 和设备侧那条文件路径。
 * 页面里的每一步——进 /#/ocr、清上一张、把图塞进「相册选」、等 phase 变成 done、
 * 从 DOM 上读回认出来的字——都可以先在本机的 headless Chrome 上跑一遍。
 *
 * 这段不产出任何设备结论，也不写 evidence/r14/android/：它证的是「这段自动化本身
 * 没写错」。QA 带着设备出发之前先跑它，省得到了现场才发现选择器变了。
 */
async function runSelfTestUi() {
  const distDir = path.join(appDir, 'dist')
  if (!existsSync(path.join(distDir, 'index.html'))) {
    skip('S1 本机预演 B 段页面操作', '本机', '还没构建过：先跑 npm --prefix apps/literacy-app run build')
    return
  }
  const { createServer } = await import('node:http')
  const puppeteer = await import('puppeteer-core').then((m) => m.default ?? m)
  const MIME = {
    '.html': 'text/html; charset=utf-8',
    '.js': 'text/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png': 'image/png',
    '.svg': 'image/svg+xml',
    '.wasm': 'application/wasm',
    '.gz': 'application/gzip'
  }
  const server = createServer((req, res) => {
    const url = new URL(req.url, 'http://127.0.0.1')
    let file = path.join(distDir, path.normalize(decodeURIComponent(url.pathname)))
    if (!file.startsWith(distDir) || !existsSync(file) || statSync(file).isDirectory()) {
      file = path.join(distDir, 'index.html')
    }
    res.writeHead(200, { 'content-type': MIME[path.extname(file)] ?? 'application/octet-stream' })
    res.end(readFileSync(file))
  })
  await new Promise((r) => server.listen(0, '127.0.0.1', r))
  const base = `http://127.0.0.1:${server.address().port}`
  const browser = await puppeteer.launch({
    executablePath: process.env.CHROME_PATH ?? '/usr/local/bin/google-chrome',
    headless: 'new',
    args: ['--no-sandbox', '--disable-dev-shm-usage']
  })
  try {
    const page = await browser.newPage()
    await page.goto(`${base}/#/ocr`, { waitUntil: 'load', timeout: 60_000 })
    await openOcrRoute(page)
    pass('S1 /#/ocr 打得开，CameraOcrView 的 data-phase 在')

    const manifest = JSON.parse(read('scripts/fixtures/ocr/real-samples.json'))
    // 两张够了：第一张验「从零到 done 读得回字」，第二张验连着喂不会读到上一张的答案。
    const picks = manifest.samples.slice(0, 2)
    const seen = []
    for (const [i, sample] of picks.entries()) {
      const file = path.join(appDir, `scripts/fixtures/ocr/${sample.name}.png`)
      const started = Date.now()
      const out = await recognizeInPage(page, file, i === 0 ? 300_000 : 120_000)
      const ms = Date.now() - started
      const allowed = engineLimit.get(sample.name)?.chars ?? []
      const score = scoreSample(sample.text, out, allowed)
      const chars = [...out.known, ...out.unknown].join('')
      seen.push({ name: sample.name, chars, ...score, ms })
      check(
        out.phase === 'done' && score.hit > 0,
        `S2 ${sample.name}：本机 Chrome 上走完整条链，读回「${chars}」` +
          `（${score.hit}/${score.total}，${(ms / 1000).toFixed(1)} 秒）`,
        `phase=${out.phase}，读回 ${score.hit}/${score.total}——选择器或等待条件跟界面对不上了`
      )
    }
    // 两张图的字不一样，读回来的却一模一样 = 第二张读到的是上一张留在 DOM 上的答案，
    // 也就是 armPhaseWatcher 没起作用。这正是 B 段最容易出的假绿灯：十张全绿，
    // 而其实只认了一张。
    check(
      seen.length === picks.length && seen[0]?.chars !== seen[1]?.chars,
      'S3 连着喂两张读回来的是两份结果，没有把上一张的答案当成这一张的',
      `两张都读回「${seen[0]?.chars ?? ''}」`
    )
  } catch (err) {
    fail(`S1 本机预演失败：${err.message}`)
  } finally {
    await browser.close().catch(() => {})
    server.close()
  }
}

if (selfTestUi) await runSelfTestUi()

const found = runB ? findDevice() : { ok: false, why: '--section=a：这一趟只跑 A 段' }

if (runB && !found.ok) {
  // 设备缺席不是「通过」，也不是产品失败。四条 SKIP 原样列出来，
  // 退出码走 2 那一档——谁也没法拿它当绿灯，也没法拿它当红灯甩给识字模块。
  for (const [id, what, how] of [
    ['B1', '设备指纹（型号 / Android 版本 / WebView 版本 / 分辨率）', 'node scripts/test-ocr-device.mjs'],
    ['B2', `十张真实样张 push 到 ${DEVICE_SAMPLE_DIR} 与 ${DEVICE_DIR}`, 'node scripts/test-ocr-device.mjs'],
    ['B3', '冷启 → /#/ocr → 冷启耗时与峰值内存', 'node scripts/test-ocr-device.mjs'],
    ['B4', '接进 WebView 逐张认字（设备侧召回 ≥40/41、首屏认对 ≥9/10）', 'node scripts/test-ocr-device.mjs --require-device'],
    ['B5', '飞行模式下复跑一张，确认引擎从 SW 缓存起来', 'node scripts/test-ocr-device.mjs --require-device']
  ]) {
    bskip(id, what, 'Android QA', `${found.why}；设备到位后执行：${how}`)
  }
} else if (runB) {
  await runDeviceSection(found)
}

/* ============================================== 结论、证据落盘与退出码 */

/**
 * --require-device 的口径（ROUND14_H2 起改过一次）。
 *
 * 老口径是「所有 SKIP 一律当 FAIL」，于是设备没插上和 App 装错了会得到同一个
 * exit 1。真机 CI 上这两件事该找的人完全不同：前者是把机器插上，后者是去改代码。
 * 现在分开——设备缺席走 exit 2 并大声说出来；设备在，剩下的 SKIP 才当 FAIL，
 * 因为那时候「跑不了」就是真的有东西坏了。
 */
const deviceAbsent = runB && !found.ok
if (requireDevice && !deviceAbsent) {
  for (const s of skips) fail(`${s.msg}（--require-device：设备在，SKIP 当失败算）—— ${s.why}`)
  skips.length = 0
}

bReport.capturedAt = new Date().toISOString()
bReport.skips = skips.map((s) => ({ msg: s.msg, owner: s.owner, why: s.why }))
// B 段的绿灯是这么来的：一步没红、十张走完、字级和张级两条线都过、断网复跑一致。
// 少任何一条都只能是 skipped——「没红」不等于「验过了」。
const bStepsRed = bReport.steps.some((s) => s.status === 'fail')
const bStepsRan = bReport.steps.some((s) => s.status === 'pass')
bReport.pass =
  runB &&
  found.ok &&
  !bStepsRed &&
  bStepsRan &&
  bReport.samples >= MIN_SAMPLES &&
  bReport.recall.hit >= DEVICE_RECALL_FLOOR &&
  bReport.firstScreenCorrect >= FIRST_SCREEN_FLOOR &&
  bReport.offline?.packFetchOk === true &&
  bReport.offline?.offlineHit === bReport.offline?.onlineHit
bReport.status = bStepsRed ? 'fail' : bReport.pass ? 'pass' : 'skipped'

let exitCode = EXIT_OK
if (fails.length) exitCode = EXIT_FAIL
else if (runB && !bReport.pass) exitCode = EXIT_SKIP
bReport.exitCode = exitCode

/**
 * 证据落点。
 *
 * 真机跑出来的落 ocr-device-b.json——check-round14 的 H2 只认这个名字。
 * 模拟器跑出来的落 ocr-device-b.emulator.json 且带 simulated:true，
 * 两个文件名从头到尾不重叠，所以「拿模拟器点亮 H2」这件事在文件系统层面就做不到。
 * 什么都没跑成时，只有 --require-device（也就是真机 CI）才会落一份 SKIP 台账：
 * 日常在 VM 上跑一遍不该往证据目录里丢文件。
 */
let evidencePath = ''
if (runB && (found.ok || requireDevice)) {
  const evDir = path.join(repoDir, '.agent_workspace/evidence/r14/android')
  mkdirSync(evDir, { recursive: true })
  const name = bReport.emulator
    ? 'ocr-device-b.emulator.json'
    : found.ok
      ? 'ocr-device-b.json'
      : 'ocr-device-b.skip.json'
  evidencePath = path.join(evDir, name)
  writeFileSync(evidencePath, `${JSON.stringify(bReport, null, 2)}\n`)
}

if (asJson) {
  console.log(
    JSON.stringify(
      {
        marker: MARKER,
        supersedes: SUPERSEDES,
        section,
        device: found.ok ? device : null,
        passed: passes.length,
        failed: fails.length,
        skipped: skips.length,
        exitCode,
        deviceSection: {
          status: bReport.status,
          pass: bReport.pass,
          onDevice: bReport.onDevice,
          simulated: bReport.simulated,
          samples: bReport.samples,
          recall: bReport.recall,
          firstScreenCorrect: bReport.firstScreenCorrect,
          offline: bReport.offline
        },
        evidence: evidencePath ? path.relative(repoDir, evidencePath) : null,
        passes,
        fails,
        skips
      },
      null,
      2
    )
  )
} else {
  for (const p of passes) console.log(`  ✓ ${p}`)
  for (const s of skips) console.log(`  ⃠ [SKIP owner: ${s.owner}] ${s.msg}\n      ${s.why}`)
  for (const f of fails) console.log(`  ✗ ${f}`)
  for (const r of bReport.rows) {
    console.log(
      `  ${r.firstScreenCorrect ? '✓' : '◐'} ${r.name}：${r.hit}/${r.total}` +
        ` · 把握 ${r.confidence} · ${(r.ms / 1000).toFixed(1)} 秒` +
        `${r.missed ? ` · 丢字「${r.missed}」` : ''}` +
        `${r.engineLimitAllowed ? `（底线「${r.engineLimitAllowed}」不计）` : ''}`
    )
  }
  if (evidencePath) console.log(`\n  证据：${path.relative(repoDir, evidencePath)}`)
  console.log(
    `\n拍照识字真机 harness [${[MARKER, ...SUPERSEDES].join('/')}]：` +
      `${passes.length} 项通过，${fails.length} 项失败，` +
      `${skips.length} 项 SKIP（${found.ok ? `设备 ${device.serial}${device.emulator ? '（模拟器）' : ''}` : found.why}）。`
  )
  if (runB) {
    console.log(
      `B 段：${bReport.status}` +
        `${bReport.samples ? ` · 设备侧召回 ${bReport.recall.hit}/${bReport.recall.total}` : ''}` +
        `${bReport.samples ? ` · 首屏认对 ${bReport.firstScreenCorrect}/${bReport.samples}` : ''}` +
        ` · onDevice=${bReport.onDevice}${bReport.simulated ? ' · simulated=true（模拟器，不作真机结论）' : ''}` +
        ` · exit ${exitCode}`
    )
  }
  if (requireDevice && deviceAbsent) {
    console.log(
      `--require-device 要求设备在场，而这一趟没有：${found.why}。` +
        '这不是产品失败，也不是通过——CI 上按 exit 2 单独归一类，别和 exit 1 混在一起报警。'
    )
  }
  if (exitCode === EXIT_SKIP) {
    console.log(
      'exit 2 = SKIP，不是通过：真机那几项要由 owner 带设备跑一遍，' +
        '证据落 .agent_workspace/evidence/r14/android/ocr-device-b.json。'
    )
  }
}

process.exit(exitCode)
