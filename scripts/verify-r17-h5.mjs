/**
 * 走一遍 ROUND17_H5 的两条关键路径，确认学伴真的在那儿说话（不是只挂了个标记）。
 * 用法：先各自 npm run build，再 node scripts/verify-r17-h5.mjs
 */
import { createServer } from 'node:http'
import { readFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { extname, join, normalize } from 'node:path'
import { fileURLToPath } from 'node:url'
import puppeteer from 'puppeteer-core'

const ROOT = fileURLToPath(new URL('..', import.meta.url))
const CHROME = process.env.CHROME_PATH ?? '/usr/local/bin/google-chrome'
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2'
}

function serve(dist) {
  const server = createServer(async (req, res) => {
    const url = new URL(req.url, 'http://localhost')
    let file = join(dist, normalize(decodeURIComponent(url.pathname)))
    if (url.pathname === '/' || !existsSync(file)) file = join(dist, 'index.html')
    try {
      const body = await readFile(file)
      res.writeHead(200, { 'content-type': MIME[extname(file)] ?? 'application/octet-stream' })
      res.end(body)
    } catch {
      res.writeHead(404).end('not found')
    }
  })
  return new Promise((resolve) => server.listen(0, () => resolve(server)))
}

const results = []
const note = (ok, msg) => {
  results.push({ ok, msg })
  console.log(`${ok ? '✓' : '✗'} ${msg}`)
}

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

/**
 * 换步/换题时选项是带位移动画进场的，动画没落地就点会点空。
 * 这里等一拍再点，等的是动效而不是业务逻辑。
 */
const settleClick = async (page, selector) => {
  await page.waitForSelector(selector)
  await sleep(700)
  await page.click(selector)
}

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: 'new',
  args: ['--no-sandbox', '--disable-dev-shm-usage']
})

/* ------------------------------------------------- 识字：单字五步页 */
{
  const server = await serve(join(ROOT, 'apps/literacy-app/dist'))
  const base = `http://127.0.0.1:${server.address().port}`
  const page = await browser.newPage()
  await page.goto(`${base}/#/learn/${encodeURIComponent('日')}`, { waitUntil: 'networkidle0' })
  await page.waitForSelector('.detail[data-coach]')

  const marker = await page.$eval('.detail', (el) => el.dataset.coach)
  note(marker === 'ROUND17_H5', `单字页挂上标记 data-coach=${marker}`)

  const read = () =>
    page.$eval('.panel__coach .mascot__bubble', (el) => el.textContent.trim()).catch(() => '')

  const playLine = await read()
  note(Boolean(playLine), `「玩」这一步墨墨开口：${playLine.slice(0, 28)}`)

  // 手动跳到「练一练」，台词应该换成这一步自己的话
  await settleClick(page, '.rail__step[data-step="intro"]')
  await settleClick(page, '.rail__step[data-step="listen"]')
  await page.waitForFunction(() => document.querySelectorAll('.opt--char').length > 0)
  await sleep(700)
  const listenLine = await read()
  note(listenLine.includes('这一步考耳朵') || listenLine !== playLine,
    `换到「练」说的是这一步的话：${listenLine.slice(0, 28)}`)

  // 故意答错：阶段应该切到「答错了」，台词跟着换成安慰
  const wrong = await page.$$eval('.opt--char', (els) =>
    els.map((el) => el.dataset.char).filter((c) => c !== '日')
  )
  await settleClick(page, `.opt--char[data-char="${wrong[0]}"]`)
  await sleep(400)
  const stage = await page.$eval('.detail', (el) => el.dataset.coachStage)
  const wrongLine = await read()
  note(stage === 'encourage', `答错后阶段切到 ${stage}`)
  note(wrongLine !== listenLine, `答错后墨墨改口安慰：${wrongLine.slice(0, 30)}`)

  // 点一下墨墨：丢掉临时那句，回到轮换台词。轮换偶尔会转回同一句，多点两下再判
  let tapped = wrongLine
  for (let i = 0; i < 3 && tapped === wrongLine; i += 1) {
    await page.click('.panel__coach .mascot__btn')
    await sleep(300)
    tapped = await read()
  }
  note(Boolean(tapped) && tapped !== wrongLine, `点一下换下一句：${tapped.slice(0, 30)}`)

  await page.close()
  server.close()
}

/* ------------------------------------------------------ 数学：答题壳 */
{
  const server = await serve(join(ROOT, 'apps/math-app/dist'))
  const base = `http://127.0.0.1:${server.address().port}`
  const page = await browser.newPage()
  await page.goto(`${base}/#/arithmetic`, { waitUntil: 'networkidle0' })
  await page.waitForSelector('.quiz-shell[data-coach]')

  const marker = await page.$eval('.quiz-shell', (el) => el.dataset.coach)
  note(marker === 'ROUND17_H5', `答题壳挂上标记 data-coach=${marker}`)

  const say = () => page.$eval('.quiz-stage .say', (el) => el.textContent.trim())
  const before = await say()

  // 哪个选项是对的题面上看不出来，就轮着选，选到错的为止——连错才走得到
  // 「算错了」那组台词
  let wronged = false
  for (let i = 0; i < 6 && !wronged; i += 1) {
    await page.waitForSelector('.options .opt')
    await sleep(700)
    const count = await page.$$eval('.options .opt', (els) => els.length)
    await page.$$eval('.options .opt', (els, k) => els[k]?.click(), i % count)
    await sleep(500)
    wronged = (await page.$('.opt.bad')) !== null
    await sleep(1600)
  }
  note(wronged, '答题壳里答错了一道，进入「算错了」阶段')

  const stage = await page.$eval('.quiz-shell', (el) => el.dataset.coachStage)
  const after = await say()
  note(stage === 'encourage', `答错后阶段切到 ${stage}`)
  note(after !== before, `下一题的开场白由小算接手：${after.slice(0, 34)}`)

  // 点一下小算：换一句写进台词行
  await page.click('.stage-head .mascot')
  await sleep(300)
  const tapped = await say()
  note(tapped !== after, `点一下小算换一句：${tapped.slice(0, 34)}`)

  await page.close()
  server.close()
}

await browser.close()

const bad = results.filter((r) => !r.ok)
console.log(`\nROUND17_H5 走查：${results.length - bad.length}/${results.length} 通过`)
process.exitCode = bad.length ? 1 : 0
