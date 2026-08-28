/**
 * ROUND12_H2 / ROUND13_H2 —— 拍照识字的真机 / 模拟器 harness。
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
 *     采设备指纹、把十张真实样张 push 进相册目录、把 App 拉到 /#/ocr、
 *     落一份证据 JSON。这一段的代码是实的：QA 拿一台机器插上就能跑，
 *     不需要先去把脚本写完。
 *
 *   C 段 · Android WebView 模拟（ROUND13_H2，加 --webview-sim 才跑）
 *     A 段查的是源码和构建产物，它证不了「这条链真的能认出字」。C 段把 dist
 *     架在 localhost 上（localhost 是安全上下文，SW 注册得了），用 Pixel 7 的
 *     UA + 移动视口 + 触控起一个无头 Chrome，然后走 App 自己的路：
 *     进 /#/ocr → 把十张真实样张塞进「拍一张」那个 file input → 等界面出结果。
 *     跑完再开飞行模式（setOfflineMode）重进一次，逐张重认。
 *
 *     这不是真机，WebView 也不是 Chrome：C 段绿不代表可以跳过 B 段。它顶下来的
 *     是另一件事——**在 VM 上，端到端地量出 App 真实的识别水平**。
 *     scripts/test-ocr-accuracy.mjs 拿 Node 引擎直跑原图，绕过了 preprocess()；
 *     C 段第一次跑就把这个差抓出来了：同样十张真实照片，引擎侧 40/41，
 *     App 侧只有 33/41（口径与定位见 .agent_workspace/r13-ocr-regression-loop.md）。
 *
 *   A9 段 · 失败样本回流队列（跟着 A 段一起跑）
 *     认错一次就该在队列里留一条，队列有状态、有 owner、有到期轮次。
 *     C 段发现的失败必须在队列里找得到对应记录，否则红——
 *     这是「回流」不至于变成一句口号的唯一办法。
 *
 * SKIP 不算通过，也不算失败——它会原样打出来并写进 --json 的 skipped[] 里，
 * 谁都不能拿 exit 0 冒充「真机验过了」。要在 CI 上强制必须有设备，
 * 加 --require-device，那时 SKIP 会转成 FAIL。
 *
 * 用法：
 *   node scripts/test-ocr-device.mjs                 A 段全跑，B 段有设备才跑
 *   node scripts/test-ocr-device.mjs --json          机读汇总
 *   node scripts/test-ocr-device.mjs --require-device  没设备直接红（给真机 CI 用）
 *   node scripts/test-ocr-device.mjs --webview-sim   加跑 C 段 Android WebView 模拟
 *   node scripts/test-ocr-device.mjs --sim-report    C 段结果写进 android-sim 报告的 ocr 段
 *   node scripts/test-ocr-device.mjs --webview-sim --record-failures  新失败追加进回流队列
 */

import { execFileSync } from 'node:child_process'
import {
  closeSync,
  existsSync,
  fstatSync,
  mkdirSync,
  openSync,
  readdirSync,
  readFileSync,
  readSync,
  statSync,
  writeFileSync
} from 'node:fs'
import { createServer } from 'node:http'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { gunzipSync } from 'node:zlib'

const appDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repoDir = path.resolve(appDir, '..', '..')
const asJson = process.argv.includes('--json')
const requireDevice = process.argv.includes('--require-device')

/** ROUND13_H2 —— C 段与 android-sim 报告 ocr 段共用的机读标记。 */
const ROUND13_H2 = 'ocr-android-sim-v1'

const simReportArg = process.argv.find((a) => a === '--sim-report' || a.startsWith('--sim-report='))
/** 写进 android-sim 报告的 ocr 段：默认落在 H6 那份报告旁边。 */
const simReportPath = simReportArg
  ? simReportArg.split('=')[1] || '.agent_workspace/evidence/r13/android-sim/report.json'
  : ''
const webviewSim = process.argv.includes('--webview-sim') || Boolean(simReportArg)
const recordFailures = process.argv.includes('--record-failures')

/** 与 capacitor.config.json / AndroidManifest 对齐，改包名要一起改。 */
const APP_ID = 'com.hongen.literacy'

/** 真机上「相册选」那条路要用的样张目录；push 进去之后 QA 逐张走一遍。 */
const DEVICE_DIR = '/sdcard/Download/hongen-ocr'

/**
 * 首次拍照要下载的那一坨。
 *
 * 6.0 MiB 不是拍脑袋：worker 0.11 + wasm 内核 3.72 + chi_sim 语言包 1.65 ≈ 5.5 MiB，
 * 留半兆余量。这条线一旦松开，最先付账的是低端安卓机上用移动流量的家长——
 * 而这件事在开发机上永远看不见。要换更大的语言包先改这条线，并在
 * .agent_workspace/r12-ocr-device-harness.md 里写清为什么值。
 */
const PACK_BUDGET_MIB = 6.0

/** adb push 的样张：低端机上推十张图不能变成一场等待。 */
const SAMPLE_MAX_KIB = 512
const SAMPLE_TOTAL_MAX_MIB = 2
const MIN_SAMPLES = 8

/** 失败样本回流队列：认错一次留一条，口径见 .agent_workspace/r13-ocr-regression-loop.md。 */
const QUEUE_FILE = 'scripts/fixtures/ocr/regressions/queue.json'

/**
 * C 段模拟的那台机器。
 *
 * UA 里的 `Version/4.0` 是 Android WebView 的标记，Chrome 大版本 120 对应
 * 当前主流的 System WebView。视口取 Pixel 7 的 CSS 像素与 DPR——按钮排布、
 * 触控热区都跟着它走，桌面视口下测不出「拍一张」被挤出屏幕这类问题。
 */
const WEBVIEW_UA =
  process.env.ANDROID_SIM_UA ??
  'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) ' +
    'Chrome/120.0.0.0 Mobile Safari/537.36 Version/4.0'
const WEBVIEW_VIEWPORT = {
  width: 412,
  height: 915,
  deviceScaleFactor: 2.625,
  isMobile: true,
  hasTouch: true
}
const CHROME = process.env.CHROME_PATH ?? '/usr/local/bin/google-chrome'

/** wasm SIMD 从 Chromium 91 起才有，低于这条线 useOcr 走「浏览器太旧」那条降级分支。 */
const MIN_CHROMIUM = 91

/** sw.js 里那个不带版本前缀的 OCR 缓存名；C 段要在运行时确认它真的建起来了。 */
const OCR_CACHE_NAME = 'literacy-app-ocr-pack'

/**
 * C 段的召回基线：**App 侧实测**，不是引擎侧跑分。
 *
 * 两个数字差得很远，差的地方就是这张表存在的理由：同样十张真实照片，
 * test-ocr-accuracy.mjs 拿 Node 引擎直跑原图得 40/41，而 App 的完整链路
 * （preprocess 缩放 + 灰度 + 对比度拉伸 → 同一个引擎）只有 33/41。
 * 掉的八个字全落在四张小字实拍上，根因已定位到 preprocess 的全局对比度拉伸
 * （回流队列 r13-webview-*，定位过程见 r13-ocr-regression-loop.md §3）。
 *
 * 所以这里记的是**今天的真实水平**，作用是防退化，不是给现状发合格证：
 * 低于这条线当场红；高于它也要来改这张表——涨了同样是行为变了，
 * 得有人确认是修好了而不是碰巧。
 */
const WEBVIEW_BASELINE = {
  'real-park-sign': { hit: 4, total: 4 },
  'real-floor-cone': { hit: 4, total: 4 },
  'real-wall-stencil': { hit: 3, total: 4 },
  'real-road-warning': { hit: 4, total: 4 },
  'real-toilet-sign': { hit: 2, total: 3 },
  'real-blackboard-press': { hit: 2, total: 4 },
  'real-road-slogan': { hit: 6, total: 6 },
  'real-town-plaque': { hit: 2, total: 4 },
  'real-shop-oblique': { hit: 4, total: 4 },
  'real-receipt-shadow': { hit: 2, total: 4 }
}
const WEBVIEW_TOTAL_FLOOR = Object.values(WEBVIEW_BASELINE).reduce((n, b) => n + b.hit, 0)

/** cap copy 之后引擎包该出现在 APK 里的位置。 */
const APK_PATH = 'android/app/build/outputs/apk/debug/app-debug.apk'
const APK_ASSET_PREFIX = 'assets/public/'

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

/**
 * 当前是第几轮：取仓库里最大的那个 check-round<N>.mjs。
 *
 * 回流队列的到期检查要拿它作参照。写死一个 13 的话，下一轮没人记得改，
 * 「到期未处理」这条规矩就自己失效了；跟着门禁文件走，新一轮的门禁一落地，
 * 逾期的记录当天变红。
 */
const currentRound = (() => {
  let max = 0
  try {
    for (const f of readdirSync(path.join(repoDir, 'scripts'))) {
      const n = Number(f.match(/^check-round(\d+)\.mjs$/)?.[1])
      if (Number.isInteger(n) && n > max) max = n
    }
  } catch {
    /* 拿不到就当第 0 轮：只会让到期检查更宽松，不会误红 */
  }
  return max
})()

/**
 * 读 APK 的中央目录。
 *
 * APK 就是个 zip，看引擎包在不在包里、有多大，不必解压、不必落盘，
 * 也不必依赖系统上有没有 unzip / aapt。返回 entry 名 → { bytes, compressed }。
 */
function apkEntries(abs) {
  let fd = -1
  try {
    fd = openSync(abs, 'r')
    const size = fstatSync(fd).size
    // EOCD 在文件末尾，注释最长 64 KiB，往回读这么多一定够
    const tailLen = Math.min(size, 66_000)
    const tail = Buffer.alloc(tailLen)
    readSync(fd, tail, 0, tailLen, size - tailLen)
    let eocd = -1
    for (let i = tail.length - 22; i >= 0; i -= 1) {
      if (tail.readUInt32LE(i) === 0x06054b50) {
        eocd = i
        break
      }
    }
    if (eocd < 0) return null
    const count = tail.readUInt16LE(eocd + 10)
    const cdSize = tail.readUInt32LE(eocd + 12)
    const cdOffset = tail.readUInt32LE(eocd + 16)
    // 0xffffffff 是 zip64 的标记：debug APK 到不了 4 GiB，真到了就别硬猜
    if (cdOffset === 0xffffffff || cdSize === 0xffffffff) return null
    const cd = Buffer.alloc(cdSize)
    readSync(fd, cd, 0, cdSize, cdOffset)
    const entries = new Map()
    let p = 0
    for (let i = 0; i < count && p + 46 <= cd.length; i += 1) {
      if (cd.readUInt32LE(p) !== 0x02014b50) break
      const nameLen = cd.readUInt16LE(p + 28)
      const extraLen = cd.readUInt16LE(p + 30)
      const commentLen = cd.readUInt16LE(p + 32)
      entries.set(cd.toString('utf8', p + 46, p + 46 + nameLen), {
        compressed: cd.readUInt32LE(p + 20),
        bytes: cd.readUInt32LE(p + 24)
      })
      p += 46 + nameLen + extraLen + commentLen
    }
    return entries
  } catch {
    return null
  } finally {
    if (fd >= 0) closeSync(fd)
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

  // assets/ 目录对了，不等于装机的那个 APK 里也对：Gradle 的 mergeAssets 有自己的
  // 增量缓存，改完 web 产物只跑 cap copy 而不重新打包，装出来的还是上一版的字。
  // APK 是真正发给孩子的那份，所以有包就直接翻包里的中央目录。
  if (!has(APK_PATH)) {
    skip(
      'A8 APK 包里的 OCR 引擎包',
      '本机 / Android Build',
      `还没出过 debug 包（${APK_PATH} 不存在）：先 npm run sync:android:literacy，` +
        '再 (cd apps/literacy-app/android && ./gradlew assembleDebug)'
    )
  } else {
    const entries = apkEntries(path.join(appDir, APK_PATH))
    check(Boolean(entries?.size), 'A8 APK 的中央目录读得出来')
    for (const f of ['ocr/worker.min.js', 'ocr/tesseract-core-simd-lstm.wasm.js', 'ocr/sample-photo.png']) {
      const entry = entries?.get(`${APK_ASSET_PREFIX}${f}`)
      const onDisk = bytesOf(`public/${f}`)
      check(
        Boolean(entry) && (!onDisk || entry.bytes === onDisk),
        `A8 APK 里的 ${f} 与 public/ 同字节（${((entry?.bytes ?? 0) / 1024).toFixed(0)} KiB）`,
        entry
          ? `包里 ${entry.bytes} 字节、磁盘 ${onDisk} 字节——重跑 sync:android:literacy 再出包`
          : '包里根本没有这个文件，装机后一按「开始认字」就 404'
      )
    }

    // 语言包要单独说（ROUND13_H2）。Gradle 合并 assets 时会把 .gz 解开、去掉后缀：
    // 仓库里的 chi_sim.traineddata.gz 装进包里变成 chi_sim.traineddata，
    // 字节数正好等于本机 gunzip 的结果。所以这里认两个名字，但要求**认出来的那个
    // 名字，字节数必须对得上**——包里躺着一份别的版本的语言包，比缺了更难查。
    const gz = entries?.get(`${APK_ASSET_PREFIX}ocr/chi_sim.traineddata.gz`)
    const plain = entries?.get(`${APK_ASSET_PREFIX}ocr/chi_sim.traineddata`)
    let expanded = 0
    try {
      expanded = gunzipSync(readFileSync(path.join(appDir, 'public/ocr/chi_sim.traineddata.gz'))).length
    } catch {
      expanded = 0
    }
    check(
      (gz && gz.bytes === bytesOf('public/ocr/chi_sim.traineddata.gz')) ||
        (plain && expanded > 0 && plain.bytes === expanded),
      plain
        ? `A8 语言包在 APK 里是解压后的 chi_sim.traineddata（${(plain.bytes / 1024 / 1024).toFixed(2)} MiB，` +
            '与本机 gunzip 同字节）——运行时按这个名字取，见 utils/ocr.js 的语言包探名'
        : `A8 语言包 chi_sim.traineddata.gz 在 APK 里（${((gz?.bytes ?? 0) / 1024).toFixed(0)} KiB）`,
      plain
        ? `包里的 chi_sim.traineddata 是 ${plain.bytes} 字节，本机 gunzip 出来是 ${expanded} 字节`
        : '包里两个名字都没有：装机后取语言包必 404，拍照识字整条不可用'
    )
  }
}

/* --- A9 失败样本回流队列：认错一次要留得下一条 --- */

/** C 段与真机走查都往这里回流，A9 只体检，不改内容。 */
let queue = null
{
  const raw = read(QUEUE_FILE)
  if (!raw) {
    fail(`A9 回流队列 ${QUEUE_FILE} 不在——拍照识字认错之后没有地方落账`)
  } else {
    try {
      queue = JSON.parse(raw)
    } catch (err) {
      fail(`A9 回流队列解析不了：${err.message}`)
    }
  }
}
if (queue) {
  const reasons = Object.keys(queue.reasons ?? {})
  const states = Object.keys(queue.states ?? {})
  const sources = Object.keys(queue.sources ?? {})
  check(reasons.length >= 5 && states.length >= 4 && sources.length >= 3, 'A9 队列的 reason / status / source 三张词表都在')

  // 界面把失败分成几岔，队列就得认得几岔。CameraOcrView 里加一种新的 reason
  // 而队列不知道，回流上来的记录只能塞进「其它」，分类当场失真——
  // 所以这里直接去 view 里把分岔读出来对账，而不是两边各写一份常量。
  const reasonBlock =
    read('src/views/CameraOcrView.vue').match(/const reason = computed\([\s\S]*?\n\}\)/)?.[0] ?? ''
  const uiReasons = [...new Set([...reasonBlock.matchAll(/'([a-z]+)'/g)].map((m) => m[1]))]
  const unknownUi = uiReasons.filter((r) => !reasons.includes(r))
  check(
    uiReasons.length >= 3 && unknownUi.length === 0,
    `A9 界面的 ${uiReasons.length} 种失败分岔在队列词表里都有对应`,
    `界面有而队列没有的 reason：${unknownUi.join('、') || '（没读到 reason 分支，正则该跟着 view 改）'}`
  )

  const records = Array.isArray(queue.records) ? queue.records : []
  const ids = new Set()
  const problems = []
  for (const r of records) {
    const at = `记录 ${r?.id ?? '(无 id)'}`
    if (!r?.id) problems.push('有记录没写 id')
    else if (ids.has(r.id)) problems.push(`${at} 的 id 重了`)
    else ids.add(r.id)
    if (!reasons.includes(r?.reason)) problems.push(`${at} 的 reason「${r?.reason}」不在词表里`)
    if (!states.includes(r?.status)) problems.push(`${at} 的 status「${r?.status}」不在词表里`)
    if (!sources.includes(r?.source)) problems.push(`${at} 的 source「${r?.source}」不在词表里`)
    if (!r?.expected) problems.push(`${at} 没写期望文字，后来的人对不了账`)
    if (!/^\d{4}-\d{2}-\d{2}/.test(String(r?.capturedAt ?? ''))) problems.push(`${at} 的 capturedAt 不是日期`)
    // 「以后再说」不算回流：没人认领、没有到期轮次的记录会一直躺在队列里
    if (['new', 'triaged'].includes(r?.status)) {
      if (!r?.owner) problems.push(`${at} 还没人认领（status=${r.status} 必须有 owner）`)
      if (!Number.isInteger(r?.dueRound)) problems.push(`${at} 没写 dueRound`)
      else if (r.dueRound < currentRound) {
        problems.push(`${at} 已过期：说好第 ${r.dueRound} 轮处理，现在是第 ${currentRound} 轮`)
      }
    }
    // 固化成基准样张才算真的守住了：图必须在，清单里也得有它
    if (r?.status === 'promoted') {
      const name = r.promotedTo ?? r.sample
      if (!has(`scripts/fixtures/ocr/${name}.png`)) problems.push(`${at} 说已固化成 ${name}.png，图却不在`)
    }
    if (r?.status === 'accepted-limit' && String(r?.note ?? '').length < 40) {
      problems.push(`${at} 判成引擎边界却没写清为什么`)
    }
  }
  check(problems.length === 0, `A9 回流队列 ${records.length} 条记录字段齐全、状态合法、没到期`, problems.join('；'))
}

/* ============================================================ B 段 · 真机执行 */

const device = { serial: '', model: '', release: '', sdk: '', webview: '', size: '', density: '' }
let evidencePath = ''

function adb(args, serial = '') {
  return execFileSync('adb', serial ? ['-s', serial, ...args] : args, {
    encoding: 'utf8',
    timeout: 60_000,
    stdio: ['ignore', 'pipe', 'pipe']
  }).trim()
}

function findDevice() {
  try {
    execFileSync('adb', ['version'], { stdio: 'ignore', timeout: 10_000 })
  } catch {
    return { ok: false, why: '这台机器上没有 adb（Cursor Cloud VM 不带 Android SDK）' }
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
  return { ok: true, serial: serials[0], all: serials }
}

const found = findDevice()

if (!found.ok) {
  // 这四条是真机上唯一验得了的东西，一条都不能悄悄放过去。
  for (const [what, how] of [
    ['B1 设备指纹（型号 / Android 版本 / WebView 版本 / 分辨率）', 'node scripts/test-ocr-device.mjs'],
    [`B2 十张真实样张 push 到 ${DEVICE_DIR}，逐格走「相册选」`, 'node scripts/test-ocr-device.mjs'],
    ['B3 冷启 → /#/ocr → 首次下引擎包耗时与峰值内存', 'node scripts/test-ocr-device.mjs'],
    ['B4 飞行模式下重进 /#/ocr，引擎从 SW 缓存里起来', '飞行模式后重跑 B3']
  ]) {
    skip(what, 'Android QA', `${found.why}；设备到位后执行：${how}`)
  }
} else {
  device.serial = found.serial
  const prop = (key) => {
    try {
      return adb(['shell', 'getprop', key], device.serial)
    } catch {
      return ''
    }
  }
  device.model = prop('ro.product.model')
  device.release = prop('ro.build.version.release')
  device.sdk = prop('ro.build.version.sdk')
  try {
    device.size = adb(['shell', 'wm', 'size'], device.serial).replace(/\s+/g, ' ')
    device.density = adb(['shell', 'wm', 'density'], device.serial).replace(/\s+/g, ' ')
  } catch {
    /* 某些模拟器镜像上没有 wm，采不到不算失败 */
  }
  // WebView 版本是拍照识字最要紧的一条环境信息：wasm SIMD 要 Chromium 91+，
  // 低于这个版本 useOcr 会走到「浏览器太旧」那条分支，跟引擎本身无关。
  try {
    const dump = adb(['shell', 'dumpsys', 'package', 'com.google.android.webview'], device.serial)
    device.webview = dump.match(/versionName=([\w.]+)/)?.[1] ?? ''
  } catch {
    device.webview = ''
  }
  check(Boolean(device.model), `B1 设备指纹：${device.model} · Android ${device.release}（API ${device.sdk}）`)
  const chromium = Number(device.webview.split('.')[0] || 0)
  check(
    chromium >= 91,
    `B1 System WebView ${device.webview || '未知'}（wasm SIMD 需要 Chromium 91+）`,
    '这台设备的 WebView 太旧，拍照识字会落到「浏览器太旧」那条降级分支'
  )

  // 把样张推进相册目录，QA 就能用「相册选」按矩阵一格一格走，
  // 不必现场去找一块暗的招牌或者一张糊的照片。
  const dir = path.join(appDir, 'scripts/fixtures/ocr')
  const samples = readdirSync(dir).filter((f) => /^real-.*\.png$/.test(f))
  let pushed = 0
  try {
    adb(['shell', 'mkdir', '-p', DEVICE_DIR], device.serial)
    for (const f of samples) {
      adb(['push', path.join(dir, f), `${DEVICE_DIR}/${f}`], device.serial)
      pushed += 1
    }
    // 不扫一遍媒体库的话，相册选择器里看不见刚推上去的图
    adb(
      ['shell', 'am', 'broadcast', '-a', 'android.intent.action.MEDIA_SCANNER_SCAN_FILE', '-d', `file://${DEVICE_DIR}`],
      device.serial
    )
  } catch (err) {
    fail(`B2 样张 push 失败（已推 ${pushed}/${samples.length}）：${err.message}`)
  }
  check(pushed === samples.length, `B2 ${pushed}/${samples.length} 张真实样张已进 ${DEVICE_DIR}`)

  let installed = false
  try {
    installed = adb(['shell', 'pm', 'list', 'packages', APP_ID], device.serial).includes(APP_ID)
  } catch {
    installed = false
  }
  if (!installed) {
    skip(
      `B3 冷启 ${APP_ID} 到 /#/ocr`,
      'Android Build',
      `设备上没装 ${APP_ID}：先 npm run sync:android:literacy && (cd apps/literacy-app/android && ./gradlew assembleDebug) 再 adb install -r`
    )
    skip('B4 飞行模式下引擎从 SW 缓存起来', 'Android QA', '要先装上 App')
  } else {
    try {
      adb(['shell', 'am', 'force-stop', APP_ID], device.serial)
      adb(['shell', 'am', 'start', '-n', `${APP_ID}/.MainActivity`], device.serial)
      pass(`B3 已冷启 ${APP_ID}，请在设备上走到「拍照识字」并逐张选 ${DEVICE_DIR} 里的样张`)
    } catch (err) {
      fail(`B3 拉不起 ${APP_ID}：${err.message}`)
    }
    // 引擎包在不在缓存里、认得出几个字，这些要在 WebView 里看，
    // 脚本给不出结论——但它把人和图都送到了位。
    skip(
      'B4 飞行模式下重进 /#/ocr，确认引擎从 SW 缓存起来、十张样张的识别结果',
      'Android QA',
      `照着 .agent_workspace/r12-ocr-device-harness.md §3 的表逐格记录，回填到 evidence/r12/`
    )
  }

  const evDir = path.join(repoDir, '.agent_workspace/evidence/r12')
  mkdirSync(evDir, { recursive: true })
  evidencePath = path.join(evDir, `ocr-device-${device.serial.replace(/[^\w.-]/g, '_')}.json`)
  writeFileSync(
    evidencePath,
    `${JSON.stringify(
      {
        marker: 'ROUND12_H2',
        capturedAt: new Date().toISOString(),
        appId: APP_ID,
        device,
        pushedSamples: pushed,
        deviceDir: DEVICE_DIR,
        installed,
        passes,
        fails,
        skips
      },
      null,
      2
    )}\n`
  )
}

/* ========================================== C 段 · Android WebView 模拟（R13） */

/**
 * 这一段跑的是 App 自己，不是引擎。
 *
 * A 段查源码、B 段要设备，中间空着的是最要紧的一问：**这条链现在到底能认出
 * 多少字**。C 段把 dist 架在 127.0.0.1 上（localhost 属安全上下文，SW 注册得了，
 * 和 Capacitor 把 dist 挂在 https://localhost/ 是同一类环境），用 Pixel 7 的 UA
 * 与视口起一个无头 Chrome，然后老老实实走界面：进 /#/ocr、把样张塞进
 * 「拍一张」那个 input、等 data-phase 变成 done、从 DOM 上读认出来的字。
 *
 * 读 DOM 而不是读引擎返回值，是因为孩子看到的就是 DOM：字进没进字库、
 * 「把握不大」那张卡亮没亮，都在这一层才成立。
 */
const webview = {
  ran: false,
  userAgent: WEBVIEW_UA,
  viewport: `${WEBVIEW_VIEWPORT.width}×${WEBVIEW_VIEWPORT.height}@${WEBVIEW_VIEWPORT.deviceScaleFactor}x`,
  chromium: '',
  serviceWorker: false,
  cachedPack: [],
  samples: [],
  offline: { ran: false, matched: 0 },
  apkLayout: null,
  hit: 0,
  total: 0,
  pageErrors: []
}

if (webviewSim) {
  const dist = path.join(appDir, 'dist')
  const puppeteer = await import('puppeteer-core').catch(() => null)
  if (!existsSync(dist)) {
    skip('C 段 Android WebView 模拟', '本机', '还没构建过：先跑 npm --prefix apps/literacy-app run build')
  } else if (!puppeteer) {
    skip('C 段 Android WebView 模拟', '本机', 'puppeteer-core 没装上：先跑 npm install')
  } else if (!existsSync(CHROME)) {
    skip('C 段 Android WebView 模拟', '本机', `没找到 Chrome（${CHROME}）：用 CHROME_PATH 指一个`)
  } else {
    webview.ran = true
    /**
     * Gradle 打包 assets 时会把 `.gz` 解开、去掉后缀（实测 chi_sim.traineddata.gz
     * 1730011 字节 → APK 里的 chi_sim.traineddata 2469156 字节，与本机 gunzip 一致）。
     * apkLayout=true 时服务器就按那个布局供文件：`.gz` 一律 404，解压后的名字才有。
     */
    const MIME = {
      '.html': 'text/html; charset=utf-8',
      '.js': 'text/javascript; charset=utf-8',
      '.css': 'text/css; charset=utf-8',
      '.json': 'application/json; charset=utf-8',
      '.png': 'image/png',
      '.svg': 'image/svg+xml',
      '.gz': 'application/gzip',
      '.webmanifest': 'application/manifest+json'
    }
    const gzSuffix = '/ocr/chi_sim.traineddata.gz'
    const serveDist = async (apkLayout = false) => {
      const server = createServer((req, res) => {
        const pathname = new URL(req.url, 'http://127.0.0.1').pathname
        if (apkLayout && pathname.endsWith(gzSuffix)) {
          res.writeHead(404).end('404')
          return
        }
        let file = path.join(dist, decodeURIComponent(pathname))
        if (apkLayout && pathname.endsWith('/ocr/chi_sim.traineddata')) {
          const body = gunzipSync(readFileSync(path.join(dist, 'ocr/chi_sim.traineddata.gz')))
          res.writeHead(200, { 'content-type': 'application/octet-stream', 'content-length': body.length })
          res.end(body)
          return
        }
        // SPA 兜底：hash 路由之外的任何 404 都回 index.html，跟 Capacitor 壳层一致
        if (!existsSync(file) || statSync(file).isDirectory()) file = path.join(dist, 'index.html')
        try {
          const body = readFileSync(file)
          res.writeHead(200, {
            'content-type': MIME[path.extname(file)] ?? 'application/octet-stream',
            'content-length': body.length
          })
          res.end(body)
        } catch {
          res.writeHead(404).end('404')
        }
      })
      await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve))
      return { server, base: `http://127.0.0.1:${server.address().port}` }
    }
    const { server, base } = await serveDist()

    const browser = await puppeteer.default.launch({
      executablePath: CHROME,
      headless: 'new',
      args: ['--no-sandbox', '--disable-dev-shm-usage']
    })
    try {
      // browser.version() 形如 Chrome/148.0.7778.96 或 HeadlessChrome/120.0.6099.109
      webview.chromium = (await browser.version()).replace(/^[A-Za-z]+\//, '')
      const major = Number(webview.chromium.split('.')[0] || 0)
      check(
        major >= MIN_CHROMIUM,
        `C1 模拟用的 Chromium ${webview.chromium}（wasm SIMD 需要 ${MIN_CHROMIUM}+）`,
        '这个 Chromium 太旧，测出来的是降级分支，不是拍照识字'
      )

      const page = await browser.newPage()
      await page.setUserAgent(WEBVIEW_UA)
      await page.setViewport(WEBVIEW_VIEWPORT)
      page.on('pageerror', (err) => webview.pageErrors.push(String(err).slice(0, 200)))

      await page.goto(`${base}/#/ocr`, { waitUntil: 'networkidle2', timeout: 60_000 })
      await page.waitForSelector('.page.ocr', { timeout: 30_000 })
      check(true, `C1 Android UA + ${webview.viewport} 视口下 /#/ocr 起得来`)

      // 「下过一次就能离线认字」的前提是 SW 注册得上。A1 从 androidScheme 推出这一条，
      // 这里是运行时的实证：没有 active 的 SW，后面的飞行模式那一段就是假的。
      webview.serviceWorker = await page.evaluate(() =>
        navigator.serviceWorker
          ? navigator.serviceWorker.ready.then((r) => Boolean(r.active)).catch(() => false)
          : false
      )
      check(webview.serviceWorker, 'C2 Service Worker 在 WebView 里注册并激活了')

      const packReady = await page.$eval('.ocr__pack', (el) => el.dataset.ready === 'true')
      check(packReady, 'C2 界面读到了识字包清单（「离线识字包 5.5 MB」那句是真的）')

      // A5 查的是 .vue 源码里的 capture；这里查的是浏览器手上的那棵 DOM——
      // 条件渲染、属性透传出岔子的时候，两者会不一样。
      const inputs = await page.$$eval('input[type=file]', (els) =>
        els.map((el) => ({ capture: el.getAttribute('capture'), accept: el.getAttribute('accept') }))
      )
      check(
        inputs.length === 2 &&
          inputs.filter((i) => i.capture === 'environment').length === 1 &&
          inputs.filter((i) => !i.capture).length === 1,
        'C3 DOM 里「拍一张」带 capture=environment、「相册选」不带',
        `实际拿到 ${JSON.stringify(inputs)}`
      )

      const dir = path.join(appDir, 'scripts/fixtures/ocr')
      let manifest = { samples: [] }
      try {
        manifest = JSON.parse(read('scripts/fixtures/ocr/real-samples.json'))
      } catch {
        fail('C4 读不出 real-samples.json，没法知道每张样张该认出什么字')
      }

      /**
       * 认一张：先按「换一张」回到 idle，再把文件塞进 input，等界面自己出结果。
       *
       * 超时返回 null 而不是抛。取语言包 404 的时候 tesseract 不会报错，
       * 它就那么停在「正在翻汉字词典」上——孩子看到的是一条永远走不完的进度条。
       * 这种「卡住」和「认错了」一样是失败，得当成断言红掉，而不是让脚本崩在半路。
       */
      const recognizerFor = (page, timeout = 120_000) => async (file) => {
        await page.evaluate(() => {
          const again = [...document.querySelectorAll('button')].find((b) =>
            b.textContent.includes('换一张')
          )
          again?.click()
        })
        const input = await page.$('input[type=file][capture="environment"]')
        const started = Date.now()
        await input.uploadFile(file)
        try {
          await page.waitForFunction(
            () => ['done', 'error'].includes(document.querySelector('.page.ocr')?.dataset.phase),
            { timeout, polling: 300 }
          )
        } catch {
          return null
        }
        const out = await page.evaluate(() => ({
          phase: document.querySelector('.page.ocr')?.dataset.phase ?? '',
          trouble: document.querySelector('[data-trouble]')?.dataset.trouble ?? '',
          known: [...document.querySelectorAll('.ocr__hit[data-char]')]
            .map((el) => el.dataset.char)
            .join(''),
          // 认出来了但不在字库里的字照样算认出来了：这里量的是引擎，不是字表大小
          unknown: document.querySelector('.ocr__miss strong')?.textContent?.replace(/\s+/g, '') ?? '',
          confidence: Number(
            document.querySelector('.ocr__stat')?.textContent?.match(/把握\s*(\d+)/)?.[1] ?? 0
          )
        }))
        return { ...out, ms: Date.now() - started }
      }
      const recognize = recognizerFor(page)

      const score = (expected, out) => {
        const got = new Set([...out.known, ...out.unknown])
        return [...expected].filter((c) => got.has(c)).length
      }

      for (const sample of manifest.samples) {
        const file = path.join(dir, `${sample.name}.png`)
        if (!existsSync(file)) {
          fail(`C4 样张 ${sample.name}.png 不在`)
          continue
        }
        const out = await recognize(file)
        if (!out) {
          fail(`C4 ${sample.name} 认字卡住了：两分钟没等到结果，进度条一直在走`)
          continue
        }
        const floor = WEBVIEW_BASELINE[sample.name]
        const hit = score(sample.text, out)
        webview.samples.push({
          name: sample.name,
          tier: sample.tier,
          expected: sample.text,
          got: out.known + out.unknown,
          hit,
          total: [...sample.text].length,
          floor: floor?.hit ?? null,
          confidence: out.confidence,
          trouble: out.trouble,
          ms: out.ms
        })
        webview.hit += hit
        webview.total += [...sample.text].length
        if (!floor) {
          fail(`C4 ${sample.name} 没有 App 侧基线：新样张要先跑一遍再把实测写进 WEBVIEW_BASELINE`)
        } else {
          check(
            hit >= floor.hit,
            `C4 ${sample.name} 认出 ${hit}/${[...sample.text].length}（基线 ${floor.hit}，把握 ${out.confidence} 分）`,
            `跌到基线 ${floor.hit} 以下，认出的是「${out.known + out.unknown}」`
          )
        }
      }
      check(
        webview.hit >= WEBVIEW_TOTAL_FLOOR,
        `C4 十张真实样张合计 ${webview.hit}/${webview.total}（基线 ${WEBVIEW_TOTAL_FLOOR}）`,
        `合计跌破基线 ${WEBVIEW_TOTAL_FLOOR}`
      )
      // 认得不准却一声不吭，比认不出更糟：孩子会把错字当成对的。
      const quietlyWrong = webview.samples.filter((s) => s.hit < s.total && !s.trouble)
      check(
        quietlyWrong.length === 0,
        'C5 认不全的样张，界面都亮了降级卡（data-trouble）',
        `这几张认错了却没给任何提示：${quietlyWrong.map((s) => s.name).join('、')}`
      )

      webview.cachedPack = await page.evaluate(async (cacheName) => {
        if (!(await caches.has(cacheName))) return []
        const cache = await caches.open(cacheName)
        return (await cache.keys()).map((r) => new URL(r.url).pathname)
      }, OCR_CACHE_NAME)
      check(
        ['worker.min.js', 'tesseract-core-simd-lstm.wasm.js', 'chi_sim.traineddata.gz'].every((f) =>
          webview.cachedPack.some((p) => p.endsWith(f))
        ),
        `C6 引擎三件套进了 ${OCR_CACHE_NAME} 缓存（${webview.cachedPack.length} 项）`,
        `缓存里只有 ${webview.cachedPack.join('、') || '（空）'}`
      )

      /* --- 飞行模式：断网之后这一整套还得从缓存里起来 --- */
      await page.setOfflineMode(true)
      await page.reload({ waitUntil: 'domcontentloaded', timeout: 60_000 })
      await page.waitForSelector('.page.ocr', { timeout: 30_000 })
      webview.offline.ran = true
      check(true, 'C7 飞行模式下重进 /#/ocr，页面从 Service Worker 缓存里起来了')

      for (const before of webview.samples) {
        const sample = manifest.samples.find((s) => s.name === before.name)
        const out = await recognize(path.join(dir, `${before.name}.png`))
        const hit = out ? score(sample.text, out) : -1
        if (hit === before.hit) webview.offline.matched += 1
        else fail(`C7 ${before.name} 断网后认出 ${hit} 个字，在线时是 ${before.hit} 个`)
      }
      check(
        webview.offline.matched === webview.samples.length,
        `C7 断网重认十张，逐张与在线结果一致（${webview.offline.matched}/${webview.samples.length}）`,
        '断网前后结果不一样，说明离线走的不是同一套引擎或同一份语言包'
      )

      check(
        webview.pageErrors.length === 0,
        'C8 整条链路没有未捕获异常',
        `WebView 里抛了：${webview.pageErrors.join(' | ')}`
      )

      /* --- C10 按 Gradle 打包后的 assets 布局再走一遍 --- */

      // 上面那一整段跑的是 dist 的布局，可装到机器上的不是 dist：Gradle 合并 assets
      // 时把 chi_sim.traineddata.gz 解开成了 chi_sim.traineddata，带 .gz 的那个名字
      // 在 APK 里根本不存在（A8 已经从真包的中央目录里读出来了）。这一段就按那个布局
      // 起第二个服务器——换个端口就是换个源，SW 和 caches 都是干净的——再让 App
      // 完整认一遍。它守的是 utils/ocr.js 里那次语言包探名：探名没了，这里当场 404。
      const apk = await serveDist(true)
      try {
        const apkPage = await browser.newPage()
        await apkPage.setUserAgent(WEBVIEW_UA)
        await apkPage.setViewport(WEBVIEW_VIEWPORT)
        const apkErrors = []
        apkPage.on('pageerror', (err) => apkErrors.push(String(err).slice(0, 200)))
        await apkPage.goto(`${apk.base}/#/ocr`, { waitUntil: 'networkidle2', timeout: 60_000 })
        await apkPage.waitForSelector('.page.ocr', { timeout: 30_000 })
        await apkPage.evaluate(() =>
          navigator.serviceWorker ? navigator.serviceWorker.ready.catch(() => {}) : null
        )
        const probe = manifest.samples[0]
        // 取不到语言包时界面会一直停在「正在翻汉字词典」，所以这里给一分钟就够了
        const out = await recognizerFor(apkPage, 60_000)(path.join(dir, `${probe.name}.png`))
        const hit = out ? score(probe.text, out) : 0
        webview.apkLayout = {
          sample: probe.name,
          expected: probe.text,
          got: out ? out.known + out.unknown : '',
          hit,
          total: [...probe.text].length,
          phase: out?.phase ?? 'stuck'
        }
        check(
          out?.phase === 'done' && hit >= (WEBVIEW_BASELINE[probe.name]?.hit ?? 1),
          `C10 按 APK 的 assets 布局（语言包已被 Gradle 解成 .traineddata）仍认出 ` +
            `${hit}/${[...probe.text].length}`,
          out
            ? `装机后的布局下认不出来了（phase=${out.phase}，认出「${out.known + out.unknown}」）：` +
              'utils/ocr.js 的语言包探名没生效，真机上一按「开始认字」就会 404'
            : '装机后的布局下卡在「正在翻汉字词典」上再没动过——语言包 404，' +
              'tesseract 不报错也不放手，孩子看到的是一条永远走不完的进度条'
        )
        await apkPage.close()
      } finally {
        apk.server.close()
      }
    } finally {
      await browser.close().catch(() => {})
      server.close()
    }

    /* --- C9 认错的样张必须在回流队列里找得到 --- */
    if (queue) {
      const known = new Set(
        (queue.records ?? []).filter((r) => r.status !== 'fixed').map((r) => r.sample)
      )
      const missing = webview.samples.filter((s) => s.hit < s.total && !known.has(s.name))
      if (missing.length && recordFailures) {
        const today = new Date().toISOString().slice(0, 10)
        for (const s of missing) {
          queue.records.push({
            id: `r${currentRound}-webview-${s.name.replace(/^real-/, '')}`,
            capturedAt: today,
            source: 'webview-sim',
            sample: s.name,
            tier: s.tier ?? null,
            reason: s.trouble || 'partial',
            expected: s.expected,
            got: s.got,
            missed: [...s.expected].filter((c) => !s.got.includes(c)).join(''),
            status: 'new',
            owner: '识字 App',
            dueRound: currentRound + 1,
            note: `--record-failures 自动回流：App 侧认出 ${s.hit}/${s.total}，把握 ${s.confidence} 分。还没人看过，先定位再改状态。`,
            repro: 'node scripts/test-ocr-device.mjs --webview-sim'
          })
        }
        writeFileSync(path.join(appDir, QUEUE_FILE), `${JSON.stringify(queue, null, 2)}\n`)
        pass(`C9 ${missing.length} 条新失败已回流进队列（--record-failures）`)
      } else {
        check(
          missing.length === 0,
          `C9 认不全的样张在回流队列里都有记录（${webview.samples.filter((s) => s.hit < s.total).length} 条）`,
          `队列里没有这几张的记录：${missing.map((s) => s.name).join('、')}——` +
            '加 --record-failures 先把它们收进队列，再逐条定位'
        )
      }
    }
  }
} else {
  skip(
    'C 段 Android WebView 模拟（十张样张走 App 完整链路 + 飞行模式重认）',
    '本机 / Android 模拟',
    '这一段要起无头 Chrome，默认不跑：加 --webview-sim，或跑 npm run android:sim'
  )
}

/* ============================ android-sim 报告的 ocr 段（ROUND13_H2 与 H6 联动） */

/**
 * H6 的 android-sim.mjs 负责出双 APK 和 smoke，拍照识字这一段的结论由这里给。
 *
 * 写两份：一份是独立的 ocr-section.json（android-sim 跑完会把它读进 report.ocr），
 * 一份直接就地更新 report.json 的 ocr 段——单独重跑这个脚本时不必再走一遍
 * 十几分钟的出包流程，报告里的 OCR 结论也不会停在上一次。
 */
let simSection = null
if (simReportPath) {
  const reportAbs = path.isAbsolute(simReportPath) ? simReportPath : path.join(repoDir, simReportPath)
  const evidenceDir = path.dirname(reportAbs)
  simSection = {
    marker: ROUND13_H2,
    simulated: true,
    note: 'VM 里的 Android WebView 模拟（UA + 移动视口 + localhost 安全上下文），不等价真机签核',
    capturedAt: new Date().toISOString(),
    pass: fails.length === 0 && webview.ran,
    webviewRan: webview.ran,
    userAgent: webview.userAgent,
    viewport: webview.viewport,
    chromium: webview.chromium,
    serviceWorker: webview.serviceWorker,
    cachedPack: webview.cachedPack,
    recall: {
      hit: webview.hit,
      total: webview.total,
      floor: WEBVIEW_TOTAL_FLOOR,
      // 引擎侧 40/41 的那份跑分在 test-ocr-accuracy.mjs，两个数字差在 preprocess 上
      note: 'App 完整链路实测，与 test-ocr-accuracy.mjs 的引擎侧跑分不是一回事'
    },
    offline: webview.offline,
    apkLayout: webview.apkLayout,
    samples: webview.samples,
    reflux: {
      queue: `apps/literacy-app/${QUEUE_FILE}`,
      design: '.agent_workspace/r13-ocr-regression-loop.md',
      records: queue?.records?.length ?? 0,
      open: (queue?.records ?? []).filter((r) => ['new', 'triaged'].includes(r.status)).length
    },
    assertions: { passed: passes.length, failed: fails.length, skipped: skips.length },
    fails,
    deviceSkips: skips.filter((s) => s.owner === 'Android QA').map((s) => s.msg)
  }
  mkdirSync(evidenceDir, { recursive: true })
  writeFileSync(path.join(evidenceDir, 'ocr-section.json'), `${JSON.stringify(simSection, null, 2)}\n`)
  if (existsSync(reportAbs)) {
    try {
      const report = JSON.parse(readFileSync(reportAbs, 'utf8'))
      report.ocr = simSection
      writeFileSync(reportAbs, `${JSON.stringify(report, null, 2)}\n`)
    } catch (err) {
      fail(`android-sim 报告 ${simReportPath} 更新不了：${err.message}`)
    }
  }
}

/* ==================================================================== 输出 */

if (requireDevice) {
  for (const s of skips) fail(`${s.msg}（--require-device：SKIP 当失败算）—— ${s.why}`)
  skips.length = 0
}

if (asJson) {
  console.log(
    JSON.stringify(
      {
        marker: 'ROUND12_H2',
        simMarker: ROUND13_H2,
        device: found.ok ? device : null,
        webview: webview.ran ? webview : null,
        queue: queue
          ? {
              records: queue.records.length,
              open: queue.records.filter((r) => ['new', 'triaged'].includes(r.status)).length
            }
          : null,
        passed: passes.length,
        failed: fails.length,
        skipped: skips.length,
        evidence: evidencePath || null,
        simReport: simReportPath || null,
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
  if (webview.ran) {
    console.log(
      `\n  Android WebView 模拟（simulated，不等价真机）：Chromium ${webview.chromium} · ` +
        `${webview.viewport} · 十张真实样张 ${webview.hit}/${webview.total}，` +
        `断网重认一致 ${webview.offline.matched}/${webview.samples.length}`
    )
  }
  if (evidencePath) console.log(`\n  证据：${path.relative(repoDir, evidencePath)}`)
  if (simReportPath) console.log(`  android-sim ocr 段：${simReportPath}`)
  console.log(
    `\n拍照识字真机 harness：${passes.length} 项通过，${fails.length} 项失败，` +
      `${skips.length} 项 SKIP（${found.ok ? `设备 ${device.serial}` : found.why}）。`
  )
  if (skips.length) {
    console.log('SKIP 不是通过：真机那几项要由 owner 在设备上跑一遍并回填 evidence/r12/。')
  }
}

process.exit(fails.length ? 1 : 0)
