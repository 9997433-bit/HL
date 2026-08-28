/**
 * 在一个 WebView / Chromium 页面里，把「拍照识字」这条链真的走一遍（ROUND14_H2）。
 *
 * 这些函数被两个地方共用，而且必须是同一份：
 *
 *   - scripts/test-ocr-device.mjs 的 B 段：接的是 Android 真机上那个 WebView
 *     （adb forward 出来的 devtools socket），喂的是 push 到设备上的样张；
 *   - 同一个脚本的 --self-test-ui：接的是本机 headless Chrome，喂的是仓库里的样张。
 *
 * 分成两份抄的话，能在开发机上验的那份和真机上跑的那份会慢慢分岔，
 * 到时候「本机自测是绿的」就再也说明不了任何事情。B 段唯一不能在开发机上
 * 预演的只有两件——adb forward 和设备侧的文件路径——把它们留在调用方，
 * 页面里的每一步都在这里，都能在本机先跑一遍。
 *
 * 全部走 CDP 的 DOM.setFileInputFiles，而不是去点系统选择器：选择器是系统 UI，
 * 每台设备的皮肤都不一样，点它等于把这段自动化绑死在某一台机器上。
 * 从 input 之后的每一步——preprocess、worker、wasm、DOM 渲染——都是 App 真的那一套。
 */

/** 「相册选」那个 input：带 capture 的是拍照那条路，安卓会跳过相册直接开相机。 */
export const ALBUM_INPUT = 'input[type=file]:not([capture])'

/** CameraOcrView 把状态挂在根节点的 data-phase 上，等待和判读都靠它。 */
export const PHASE = `document.querySelector('.page.ocr')?.dataset.phase`

/**
 * 一次识别的结果，从 DOM 上读——不从控制台日志里猜。
 *
 * 认出来的字分两堆摆：字库里有的进 .ocr__hit[data-char]，没有的挤在 .ocr__miss 那句话里。
 * 召回要算的是「引擎认出了几个字」，两堆都得数，不然「洗手间」的「洗」进了字库、
 * 「间」没进，就会被记成丢字。
 */
export const READ_RESULT = `(() => {
  const root = document.querySelector('.page.ocr')
  const known = [...document.querySelectorAll('.ocr__hit[data-char]')].map((el) => el.dataset.char)
  const miss = document.querySelector('.ocr__miss strong')?.textContent ?? ''
  const unknown = [...miss].filter((c) => /[\\u4e00-\\u9fff]/.test(c))
  const stat = document.querySelector('.ocr__stat')?.textContent?.replace(/\\s+/g, ' ').trim() ?? ''
  return {
    phase: root?.dataset.phase ?? '',
    trouble: document.querySelector('.ocr__trouble')?.dataset.trouble ?? '',
    known,
    unknown,
    stat,
    confidence: Number(stat.match(/把握 (\\d+)/)?.[1] ?? -1)
  }
})()`

/** 进「拍照识字」这一页。hash 路由，不用整页跳转，省掉一次壳层冷启。 */
export async function openOcrRoute(page, { timeout = 60_000 } = {}) {
  await page.evaluate(`window.location.hash = '#/ocr'`)
  await page.waitForFunction(`Boolean(${PHASE})`, { timeout, polling: 300 })
}

/**
 * 在喂下一张之前，先把 data-phase 的变化记下来。
 *
 * 上一张认完之后 phase 停在 'done'，所以「等 phase 变成 done」这个条件对第二张
 * 一进来就成立——十张样张会得出一份漂亮而且全都是第一张答案的报告。
 *
 * 第一版是去点「换一张」把它退回 idle，代价是把这段自动化绑在了按钮的文案上：
 * 那个按钮当时写的是「换一张」，而这里找的是「再来一张」，于是第二张直接卡死
 * （--self-test-ui 当场逮到）。改成记录 data-phase 的变化就跟文案无关了：
 * 谁也不会为了改一句按钮文字去动 phase 这个状态机。
 */
export async function armPhaseWatcher(page) {
  await page.evaluate(`(() => {
    const root = document.querySelector('.page.ocr')
    if (!root) throw new Error('页面上没有 .page.ocr，先 openOcrRoute()')
    window.__ocrPhaseObserver?.disconnect()
    window.__ocrPhaseLog = []
    const obs = new MutationObserver(() => window.__ocrPhaseLog.push(root.dataset.phase))
    obs.observe(root, { attributes: true, attributeFilter: ['data-phase'] })
    window.__ocrPhaseObserver = obs
  })()`)
}

/**
 * 给「相册选」那个 input 塞一张图，等 App 认完，把结果读回来。
 *
 * @param page      puppeteer 的 Page（真机上是 adb forward 之后连上的那个）
 * @param filePath  图片路径。**这个路径是给浏览器进程用的**：真机上得是设备上的
 *                  绝对路径，本机自测时是仓库里的路径。B 段之所以把样张推进
 *                  app 私有的 external files 目录，就是因为分区存储下 App 读不了
 *                  别家的 /sdcard/Download。
 * @param timeoutMs 第一张要连引擎一起装起来（近 6 MB 的 wasm + 语言包），给足时间。
 */
export async function recognizeInPage(page, filePath, timeoutMs = 120_000) {
  await armPhaseWatcher(page)
  const client = await page.createCDPSession()
  try {
    const { root } = await client.send('DOM.getDocument')
    const { nodeId } = await client.send('DOM.querySelector', {
      nodeId: root.nodeId,
      selector: ALBUM_INPUT
    })
    if (!nodeId) throw new Error(`页面里找不到「相册选」的 input（${ALBUM_INPUT}）`)
    await client.send('DOM.setFileInputFiles', { nodeId, files: [filePath] })
  } finally {
    await client.detach().catch(() => {})
  }
  await page.waitForFunction(
    `(window.__ocrPhaseLog ?? []).some((p) => p === 'done' || p === 'error')`,
    { timeout: timeoutMs, polling: 300 }
  )
  return page.evaluate(READ_RESULT)
}

/** 期望字里，这一次真的认出来了几个；引擎底线允许丢的那几个字单独摘出来。 */
export function scoreSample(expectText, result, allowedMisses = []) {
  const wanted = [...new Set(expectText)]
  const got = new Set([...result.known, ...result.unknown])
  const missed = wanted.filter((c) => !got.has(c))
  return {
    hit: wanted.length - missed.length,
    total: wanted.length,
    missed: missed.join(''),
    // 首屏认对 = 除引擎底线那几个字之外一个都没丢
    firstScreenCorrect: missed.every((c) => allowedMisses.includes(c))
  }
}
