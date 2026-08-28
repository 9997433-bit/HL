/**
 * ROUND12_H2 —— 拍照识字的真机 / 模拟器 harness。
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
 * SKIP 不算通过，也不算失败——它会原样打出来并写进 --json 的 skipped[] 里，
 * 谁都不能拿 exit 0 冒充「真机验过了」。要在 CI 上强制必须有设备，
 * 加 --require-device，那时 SKIP 会转成 FAIL。
 *
 * 用法：
 *   node scripts/test-ocr-device.mjs                 A 段全跑，B 段有设备才跑
 *   node scripts/test-ocr-device.mjs --json          机读汇总
 *   node scripts/test-ocr-device.mjs --require-device  没设备直接红（给真机 CI 用）
 */

import { execFileSync } from 'node:child_process'
import { existsSync, mkdirSync, readdirSync, readFileSync, statSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const appDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const repoDir = path.resolve(appDir, '..', '..')
const asJson = process.argv.includes('--json')
const requireDevice = process.argv.includes('--require-device')

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
        device: found.ok ? device : null,
        passed: passes.length,
        failed: fails.length,
        skipped: skips.length,
        evidence: evidencePath || null,
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
  if (evidencePath) console.log(`\n  证据：${path.relative(repoDir, evidencePath)}`)
  console.log(
    `\n拍照识字真机 harness：${passes.length} 项通过，${fails.length} 项失败，` +
      `${skips.length} 项 SKIP（${found.ok ? `设备 ${device.serial}` : found.why}）。`
  )
  if (skips.length) {
    console.log('SKIP 不是通过：真机那几项要由 owner 在设备上跑一遍并回填 evidence/r12/。')
  }
}

process.exit(fails.length ? 1 : 0)
