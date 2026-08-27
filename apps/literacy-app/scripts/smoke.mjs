/**
 * 冒烟测试：用无头 Chrome 把 dist 里的每条路由都走一遍，
 * 收集控制台报错、未捕获异常和 Vue 警告，并顺手做几个交互。
 *
 * 用法：npm run build && node scripts/smoke.mjs
 */

import { createServer } from 'node:http'
import { readFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import { extname, join, normalize } from 'node:path'
import { fileURLToPath } from 'node:url'
import puppeteer from 'puppeteer-core'

import { BOOKS } from '../src/data/books.js'

const ROOT = fileURLToPath(new URL('..', import.meta.url))
const DIST = join(ROOT, 'dist')
const CHROME = '/usr/local/bin/google-chrome'

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2'
}

if (!existsSync(DIST)) {
  console.error('先跑 npm run build')
  process.exit(1)
}

const server = createServer(async (req, res) => {
  const url = new URL(req.url, 'http://localhost')
  let file = join(DIST, normalize(decodeURIComponent(url.pathname)))
  if (url.pathname === '/' || !existsSync(file)) file = join(DIST, 'index.html')
  try {
    const body = await readFile(file)
    res.writeHead(200, { 'content-type': MIME[extname(file)] ?? 'application/octet-stream' })
    res.end(body)
  } catch {
    res.writeHead(404).end('not found')
  }
})

await new Promise((r) => server.listen(0, r))
const base = `http://127.0.0.1:${server.address().port}`

const ROUTES = [
  ['首页地图', '/#/'],
  ['字表', '/#/learn'],
  ['单字详情 日', `/#/learn/${encodeURIComponent('日')}`],
  ['单字详情 说', `/#/learn/${encodeURIComponent('说')}`],
  ['听音识字', '/#/listen'],
  ['听音识字(旧路径)', '/#/game/listen'],
  ['小游戏大厅', '/#/games'],
  ['字迷宫', '/#/games/maze'],
  ['配对记忆', '/#/games/memory'],
  ['找不同', '/#/games/spot'],
  ['偏旁部首', '/#/radicals'],
  ['偏旁详情', '/#/radicals/shui'],
  ['绘本书架', '/#/books'],
  // 绘本从数据表生成：书目一多，漏测某一本比路由写错更容易发生。
  ...BOOKS.map((b) => [`绘本 ${b.id} L${b.level}《${b.title}》`, `/#/books/${b.id}`]),
  ['成语列表', '/#/idioms'],
  ['成语 守株待兔', '/#/idioms/szdt'],
  ['成语 画蛇添足', '/#/idioms/hstz'],
  ['成语 水滴石穿', '/#/idioms/sdsc'],
  ['成语 举一反三', '/#/idioms/jyfs'],
  ['成语 愚公移山', '/#/idioms/ygys'],
  ['成语 盲人摸象', '/#/idioms/mrmx'],
  ['成语 五颜六色', '/#/idioms/wyls'],
  ['字源馆', '/#/etymology'],
  ['字源 日（象形）', `/#/etymology/${encodeURIComponent('日')}`],
  ['字源 明（会意）', `/#/etymology/${encodeURIComponent('明')}`],
  ['家长中心', '/#/parent'],
  ['未知路由回落', '/#/nope/nope']
]

const IGNORE = [
  /Failed to load resource/i, // 离线环境下 CDN 兜底请求
  /net::ERR_/i,
  /favicon/i
]

const browser = await puppeteer.launch({
  executablePath: CHROME,
  headless: 'new',
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--mute-audio']
})

const problems = []
const rows = []

for (const [name, path] of ROUTES) {
  const page = await browser.newPage()
  await page.setViewport({ width: 420, height: 860, isMobile: true, hasTouch: true })
  const found = []

  page.on('console', (m) => {
    if (!['error', 'warning'].includes(m.type())) return
    const text = m.text()
    if (IGNORE.some((re) => re.test(text))) return
    found.push(`[${m.type()}] ${text}`)
  })
  page.on('pageerror', (e) => found.push(`[pageerror] ${e.message}`))

  try {
    await page.goto(base + path, { waitUntil: 'networkidle2', timeout: 20000 })
    // 路由组件是按需 chunk，networkidle2 之后还要等它挂上来
    await page
      .waitForFunction(() => (document.querySelector('#app')?.innerText ?? '').length > 40, {
        timeout: 8000
      })
      .catch(() => {})
    await new Promise((r) => setTimeout(r, 400))

    const info = await page.evaluate(() => {
      const app = document.querySelector('#app')
      const txt = app?.innerText ?? ''
      return {
        mounted: !!app && app.children.length > 0,
        chars: txt.replace(/\s+/g, '').length,
        // 明显的渲染事故：模板里漏出 NaN / undefined
        broken: /NaN|undefined|\[object Object\]/.test(txt),
        hash: location.hash,
        title: document.title
      }
    })

    // 详情页被重定向回列表，通常意味着 id 对不上（内容改名后最常见的回归）
    const want = path.slice(path.indexOf('#') + 1)
    if (info.hash && info.hash.slice(1) !== want && !path.includes('nope') && !path.includes('game/listen')) {
      found.push(`[route] 期望停在 ${want}，实际跳到 ${info.hash.slice(1)}`)
    }
    if (!info.mounted) found.push('[render] #app 为空，组件没挂载')
    if (info.broken) found.push('[render] 页面里出现 NaN / undefined / [object Object]')
    if (info.chars < 20) found.push(`[render] 页面内容过少（${info.chars} 字）`)

    rows.push({ name, path, chars: info.chars, issues: found.length })
  } catch (err) {
    found.push(`[navigate] ${err.message}`)
    rows.push({ name, path, chars: 0, issues: found.length })
  }

  if (found.length) problems.push({ name, path, found: [...new Set(found)] })
  await page.close()
}

/* ------------------------------------------------ 交互：听音识字玩一局 */
const inter = []
async function interact(label, path, fn) {
  const page = await browser.newPage()
  await page.setViewport({ width: 420, height: 860, isMobile: true, hasTouch: true })
  const errs = []
  page.on('console', (m) => {
    if (m.type() === 'error' && !IGNORE.some((re) => re.test(m.text()))) errs.push(m.text())
  })
  page.on('pageerror', (e) => errs.push(e.message))
  try {
    await page.goto(base + path, { waitUntil: 'networkidle2', timeout: 20000 })
    await new Promise((r) => setTimeout(r, 500))
    const note = await fn(page)
    inter.push({ label, ok: errs.length === 0, note, errs })
  } catch (err) {
    inter.push({ label, ok: false, note: err.message, errs })
  }
  await page.close()
}

const clickText = async (page, text) => {
  const done = await page.evaluate((t) => {
    const el = [...document.querySelectorAll('button, a')].find((b) =>
      b.innerText.replace(/\s+/g, '').includes(t)
    )
    if (!el) return false
    el.click()
    return true
  }, text)
  await new Promise((r) => setTimeout(r, 450))
  return done
}

await interact('FSRS：到期卡进入复习队列，未到期卡不进入', `/#/learn/${encodeURIComponent('日')}`, async (page) => {
  await page.evaluate(() => localStorage.clear())
  await page.reload({ waitUntil: 'networkidle2' })
  await new Promise((r) => setTimeout(r, 500))

  if (!(await clickText(page, '我认识这个字'))) {
    throw new Error('单字页缺少“我认识这个字”评分入口')
  }
  await page.goto(`${base}/#/learn/${encodeURIComponent('月')}`, {
    waitUntil: 'networkidle2',
    timeout: 20000
  })
  await new Promise((r) => setTimeout(r, 500))
  if (!(await clickText(page, '我认识这个字'))) {
    throw new Error('第二张单字卡无法提交评分')
  }

  const seeded = await page.evaluate(() => {
    const now = Date.now()
    const storageKeys = Object.keys(localStorage)

    for (const key of storageKeys) {
      let value
      try {
        value = JSON.parse(localStorage.getItem(key))
      } catch {
        continue
      }

      const cards = []
      const seen = new Set()
      const walk = (node, path = '$') => {
        if (!node || typeof node !== 'object' || seen.has(node)) return
        seen.add(node)
        if (
          typeof node.charId === 'string' &&
          Number.isFinite(node.due) &&
          Number.isFinite(node.stability)
        ) {
          cards.push({ node, path })
        }
        for (const [name, child] of Object.entries(node)) walk(child, `${path}.${name}`)
      }
      walk(value)

      const due = cards.find(({ node }) => node.charId === '日')
      const future = cards.find(({ node }) => node.charId === '月')
      if (!due || !future) continue

      due.node.due = now - 60_000
      future.node.due = now + 7 * 24 * 60 * 60 * 1000
      localStorage.setItem(key, JSON.stringify(value))
      return {
        key,
        count: cards.length,
        duePath: due.path,
        futurePath: future.path
      }
    }
    return null
  })

  if (!seeded) {
    throw new Error('作答后未在持久化进度中找到日、月两张 FSRS 卡')
  }

  // 改到期时间是直接写 localStorage 的，只切 hash 不会重新读档；
  // 刷新一次既能让改动生效，也顺带验证了记忆卡确实是从存档里恢复出来的。
  await page.goto(`${base}/#/learn`, { waitUntil: 'networkidle2', timeout: 20000 })
  await page.reload({ waitUntil: 'networkidle2', timeout: 20000 })
  await new Promise((r) => setTimeout(r, 600))
  if (!(await clickText(page, '要复习'))) {
    throw new Error('字表缺少“要复习”筛选入口')
  }

  const visible = await page.evaluate(() =>
    [...document.querySelectorAll('.cc')]
      .filter((node) => {
        const style = getComputedStyle(node)
        return style.display !== 'none' && style.visibility !== 'hidden' && node.getClientRects().length > 0
      })
      .map((node) => node.querySelector('.cc__char')?.textContent?.trim())
      .filter(Boolean)
  )
  if (!visible.includes('日')) throw new Error(`到期卡“日”没有进入复习队列：${visible.join('、')}`)
  if (visible.includes('月')) throw new Error('未到期卡“月”错误进入复习队列')

  const opened = await page.evaluate(() => {
    const card = [...document.querySelectorAll('.cc')].find(
      (node) => node.querySelector('.cc__char')?.textContent?.trim() === '日'
    )
    if (!card || card.getAttribute('aria-disabled') === 'true') return false
    card.click()
    return true
  })
  if (!opened) throw new Error('到期卡“日”在复习队列中不可打开')
  await page.waitForFunction(
    () => location.hash === `#/learn/${encodeURIComponent('日')}`,
    { timeout: 5000 }
  )

  return `持久化卡=${seeded.count}，到期“日”可见且可打开，未来“月”已排除`
})

await interact('字表：分页渲染且所有字可达', '/#/learn', async (page) => {
  const snapshot = () =>
    page.evaluate(() => {
      const text = document.body.innerText
      const total = Number(text.match(/共\s*(\d+)\s*个常用字/)?.[1] ?? 0)
      const chars = [...document.querySelectorAll('.cc')]
        .filter((node) => {
          const style = getComputedStyle(node)
          return (
            style.display !== 'none' &&
            style.visibility !== 'hidden' &&
            node.getClientRects().length > 0
          )
        })
        .map((node) => node.querySelector('.cc__char')?.textContent?.trim())
        .filter(Boolean)
      return { total, chars }
    })

  const first = await snapshot()
  if (first.total < 500) throw new Error(`字库规模只有 ${first.total}，Round 4 要求至少 500 字`)
  if (!first.chars.length) throw new Error('字表首屏没有渲染单字卡')
  if (first.chars.length >= first.total) {
    throw new Error(`首屏一次挂载 ${first.chars.length}/${first.total} 张卡片，未启用分页`)
  }

  const reached = new Set(first.chars)
  let mountedMax = first.chars.length
  let turns = 0
  let unchanged = 0
  let previous = first.chars.join('|')

  // 字表按单元翻页，单元数会随字库增长；上限只是防死循环，留足余量即可。
  while (reached.size < first.total && turns < 150) {
    const clicked = await page.evaluate(() => {
      const nextPattern = /下一页|下一批|加载更多|显示更多|查看更多|更多汉字/
      const controls = [...document.querySelectorAll('button, a')].filter((node) => {
        const style = getComputedStyle(node)
        return (
          !node.disabled &&
          node.getAttribute('aria-disabled') !== 'true' &&
          style.display !== 'none' &&
          style.visibility !== 'hidden' &&
          node.getClientRects().length > 0
        )
      })
      const control = controls.find((node) =>
        nextPattern.test(`${node.innerText} ${node.getAttribute('aria-label') ?? ''}`)
      )
      if (!control) return ''
      const label = control.innerText.trim() || control.getAttribute('aria-label') || '下一页'
      control.click()
      return label
    })
    if (!clicked) break

    turns += 1
    await new Promise((r) => setTimeout(r, 350))
    const current = await snapshot()
    mountedMax = Math.max(mountedMax, current.chars.length)
    current.chars.forEach((char) => reached.add(char))
    const signature = current.chars.join('|')
    unchanged = signature === previous ? unchanged + 1 : 0
    previous = signature
    if (unchanged >= 2) break
  }

  if (mountedMax > 50) {
    throw new Error(`分页过程中同时挂载 ${mountedMax} 张卡片，超过 50 张 DOM 预算`)
  }
  if (reached.size < first.total) {
    throw new Error(`分页只覆盖 ${reached.size}/${first.total} 个字（翻页 ${turns} 次）`)
  }

  return `总数=${first.total}，首屏=${first.chars.length}，最大挂载=${mountedMax}，翻页=${turns}`
})

await interact('听音识字：开始并答 3 题', '/#/listen', async (page) => {
  const started = await clickText(page, '开始')
  let answered = 0
  for (let i = 0; i < 3; i++) {
    const ok = await page.evaluate(() => {
      const cards = [...document.querySelectorAll('button')].filter(
        (b) => /^[\u4e00-\u9fa5]$/.test(b.innerText.trim().split('\n')[0])
      )
      if (!cards.length) return false
      cards[0].click()
      return true
    })
    if (ok) answered++
    await new Promise((r) => setTimeout(r, 1700))
  }
  return `开始按钮=${started}，作答 ${answered} 次`
})

await interact('绘本：连续翻页到读完', '/#/books/b1', async (page) => {
  let turns = 0
  for (let i = 0; i < 8; i++) {
    if (await clickText(page, '下一页')) turns++
    else if (await clickText(page, '读完啦')) {
      turns++
      break
    } else break
  }
  const done = await page.evaluate(() => document.body.innerText.includes('读完'))
  return `翻页 ${turns} 次，出现读完页=${done}`
})

await interact('成语：走完小剧场', '/#/idioms/szdt', async (page) => {
  let n = 0
  for (let i = 0; i < 8; i++) {
    const advanced =
      (await clickText(page, '接下来')) ||
      (await clickText(page, '下一幕')) ||
      (await clickText(page, '看懂了')) ||
      (await clickText(page, '后来呢'))
    if (!advanced) break
    n++
  }
  const shown = await page.evaluate(() => {
    const t = document.body.innerText
    return /告诉我们|寓意|想一想|懂了/.test(t)
  })
  return `推进 ${n} 步，剧场走到结尾=${shown}`
})

await interact('听音识字：换皮到地鼠草地', '/#/listen', async (page) => {
  const picked = await clickText(page, '地鼠草地')
  await clickText(page, '开始')
  const scene = await page.evaluate(() => ({
    board: !!document.querySelector('.board--mole'),
    moles: document.querySelectorAll('.opt--mole').length,
    fish: document.querySelectorAll('.opt--fish').length
  }))
  if (!picked) throw new Error('找不到「地鼠草地」换皮按钮')
  if (!scene.board || scene.moles !== 4) {
    throw new Error(`换皮没生效：board--mole=${scene.board}，地鼠 ${scene.moles} 只`)
  }
  if (scene.fish) throw new Error('换皮后还残留着钓鱼池的皮')
  return `选中地鼠草地=${picked}，渲染 ${scene.moles} 只地鼠`
})

/* ---------------------------------------------- 交互：三款识字小游戏各走一局 */

await interact('字迷宫：只用键盘走到目标字并踩中', '/#/games/maze', async (page) => {
  if (!(await clickText(page, '进迷宫'))) throw new Error('字迷宫缺少「进迷宫」入口')
  await page.waitForSelector('.maze__cell[data-player="true"]', { timeout: 8000 })

  // 开局焦点要自己落到迷宫上，键盘用户不该先按一串 Tab 才能走第一步
  const focused = await page.evaluate(
    () => document.activeElement?.classList.contains('maze__stage') ?? false
  )
  if (!focused) throw new Error('进迷宫后焦点没有落到迷宫区，键盘走不了')

  const readMaze = () =>
    page.evaluate(() => {
      const maze = document.querySelector('.maze')
      if (!maze) return null
      const cells = [...maze.querySelectorAll('.maze__cell')].map((node) => ({
        x: Number(node.dataset.x),
        y: Number(node.dataset.y),
        wall: node.dataset.wall === 'true',
        char: node.dataset.char ?? '',
        player: node.dataset.player === 'true'
      }))
      const hud = document.body.innerText
      return {
        cols: Number(maze.dataset.cols),
        rows: Number(maze.dataset.rows),
        cells,
        target: document.querySelector('.quest__char')?.textContent.trim() ?? '',
        score: Number(hud.match(/⭐\s*(\d+)/)?.[1] ?? 0)
      }
    })

  const board = await readMaze()
  if (!board) throw new Error('迷宫没有渲染出来')
  if (board.cells.length !== board.cols * board.rows) {
    throw new Error(`迷宫格子数 ${board.cells.length} 与 ${board.cols}×${board.rows} 对不上`)
  }
  if (!board.cells.some((c) => c.wall)) throw new Error('迷宫里一堵墙都没有，等于没有迷宫')
  if (!board.target) throw new Error('题面没有显示要找的字')

  const me = board.cells.find((c) => c.player)
  const goal = board.cells.find((c) => c.char === board.target)
  if (!goal) throw new Error(`目标字「${board.target}」没有摆进迷宫`)

  // 迷宫是完美迷宫（无环全连通），BFS 出来的就是唯一那条路
  const key = (x, y) => `${x},${y}`
  const open = new Map(board.cells.filter((c) => !c.wall).map((c) => [key(c.x, c.y), c]))
  const prev = new Map([[key(me.x, me.y), null]])
  const queue = [me]
  while (queue.length) {
    const cur = queue.shift()
    if (cur.x === goal.x && cur.y === goal.y) break
    for (const [dx, dy] of [
      [0, -1],
      [0, 1],
      [-1, 0],
      [1, 0]
    ]) {
      const next = open.get(key(cur.x + dx, cur.y + dy))
      if (!next || prev.has(key(next.x, next.y))) continue
      prev.set(key(next.x, next.y), cur)
      queue.push(next)
    }
  }
  if (!prev.has(key(goal.x, goal.y))) throw new Error('目标字所在的格子走不到，迷宫不连通')

  const path = []
  for (let node = goal; node; node = prev.get(key(node.x, node.y))) path.unshift(node)

  const KEY_OF = { '0,-1': 'ArrowUp', '0,1': 'ArrowDown', '-1,0': 'ArrowLeft', '1,0': 'ArrowRight' }
  for (let i = 1; i < path.length; i += 1) {
    const step = KEY_OF[`${path[i].x - path[i - 1].x},${path[i].y - path[i - 1].y}`]
    await page.keyboard.press(step)
    await new Promise((r) => setTimeout(r, 90))
  }

  await page.waitForFunction(
    () => Number(document.body.innerText.match(/⭐\s*(\d+)/)?.[1] ?? 0) >= 1,
    { timeout: 6000 }
  )
  const said = await page.evaluate(
    () => document.querySelector('.maze-game .sr-only[aria-live="polite"]')?.innerText ?? ''
  )
  if (!/踩中了|已经找到/.test(said)) throw new Error(`踩中目标字后没有播报：「${said}」`)

  // 撞墙也要有反馈，否则读屏用户只会觉得按键失灵
  await page.keyboard.press('ArrowUp')
  await page.keyboard.press('ArrowLeft')
  await new Promise((r) => setTimeout(r, 200))

  return `迷宫 ${board.cols}×${board.rows}，键盘走 ${path.length - 1} 步踩中「${board.target}」`
})

await interact('配对记忆：翻牌配对直到全清', '/#/games/memory', async (page) => {
  if (!(await clickText(page, '开始翻牌'))) throw new Error('配对记忆缺少「开始翻牌」入口')
  await page.waitForSelector('.mcard', { timeout: 8000 })

  const snapshot = () =>
    page.evaluate(() =>
      [...document.querySelectorAll('.mcard')].map((node) => ({
        state: node.dataset.state ?? '',
        face: node.dataset.face ?? '',
        char: node.dataset.char ?? ''
      }))
    )

  const opening = await snapshot()
  if (!opening.length) throw new Error('牌桌上一张牌都没有')
  if (opening.some((card) => card.char)) {
    throw new Error('盖着的牌把汉字写进了 DOM，读屏会直接把答案念出来')
  }

  /** 一律走键盘：聚焦那张牌，回车翻开——顺带证明牌是真的可聚焦按钮。 */
  const flipCard = async (index) => {
    const focused = await page.evaluate((i) => {
      const node = document.querySelectorAll('.mcard')[i]
      if (!node || node.disabled) return false
      node.focus()
      return document.activeElement === node
    }, index)
    if (!focused) return false
    await page.keyboard.press('Enter')
    return true
  }

  /** 像人一样玩：翻开过的牌记在 known 里，凑齐一对就去收。 */
  const known = new Map()
  let flips = 0
  for (let turn = 0; turn < 40; turn += 1) {
    const cards = await snapshot()
    if (!cards.length) break

    cards.forEach((card, i) => {
      if (card.char) known.set(i, `${card.char}|${card.face}`)
    })
    const down = cards
      .map((card, i) => ({ ...card, i }))
      .filter((card) => card.state === 'down')
    if (!down.length) break

    const remembered = down.filter((card) => known.has(card.i))
    const pair = remembered.find((a) =>
      remembered.some(
        (b) =>
          b.i !== a.i &&
          known.get(b.i).split('|')[0] === known.get(a.i).split('|')[0] &&
          known.get(b.i).split('|')[1] !== known.get(a.i).split('|')[1]
      )
    )

    let first
    let second
    if (pair) {
      first = pair.i
      second = remembered.find(
        (b) =>
          b.i !== pair.i &&
          known.get(b.i).split('|')[0] === known.get(pair.i).split('|')[0] &&
          known.get(b.i).split('|')[1] !== known.get(pair.i).split('|')[1]
      ).i
    } else {
      first = (down.find((card) => !known.has(card.i)) ?? down[0]).i
    }

    if (!(await flipCard(first))) break
    flips += 1
    await new Promise((r) => setTimeout(r, 260))

    if (second === undefined) {
      const afterFirst = await snapshot()
      afterFirst.forEach((card, i) => {
        if (card.char) known.set(i, `${card.char}|${card.face}`)
      })
      const face = known.get(first)
      const partner = afterFirst
        .map((card, i) => ({ ...card, i }))
        .find(
          (card) =>
            card.i !== first &&
            card.state === 'down' &&
            known.has(card.i) &&
            known.get(card.i).split('|')[0] === face?.split('|')[0] &&
            known.get(card.i).split('|')[1] !== face?.split('|')[1]
        )
      second =
        partner?.i ??
        afterFirst
          .map((card, i) => ({ ...card, i }))
          .find((card) => card.i !== first && card.state === 'down' && !known.has(card.i))?.i
    }
    if (second === undefined) break

    if (!(await flipCard(second))) break
    flips += 1
    await new Promise((r) => setTimeout(r, 300))

    const settled = await snapshot()
    settled.forEach((card, i) => {
      if (card.char) known.set(i, `${card.char}|${card.face}`)
    })
    // 配错了要等它盖回去，锁着的时候点什么都没用
    if (settled[first]?.state !== 'matched') await new Promise((r) => setTimeout(r, 950))
  }

  // 最后一对配上之后，结算页要过一小会儿才顶上来
  await page
    .waitForFunction(() => document.body.innerText.includes('全部配对完成'), { timeout: 4000 })
    .catch(() => {})
  const done = await page.evaluate(() => document.body.innerText.includes('全部配对完成'))
  if (!done) throw new Error(`翻了 ${flips} 次还没配完，牌桌没有清空`)

  return `只用回车翻 ${flips} 次清空牌桌，盖着的牌不泄露答案`
})

await interact('找不同：找出唯一不同的字，键盘连过 3 关', '/#/games/spot', async (page) => {
  if (!(await clickText(page, '开始找'))) throw new Error('找不同缺少「开始找」入口')
  await page.waitForSelector('.spot__cell', { timeout: 8000 })

  let solved = 0
  for (let r = 0; r < 3; r += 1) {
    await page.waitForFunction(
      () => document.querySelector('.spot')?.dataset.answered === 'false',
      { timeout: 8000 }
    )
    const board = await page.evaluate(() => {
      const cells = [...document.querySelectorAll('.spot__cell')]
      const counts = {}
      for (const node of cells) counts[node.dataset.char] = (counts[node.dataset.char] ?? 0) + 1
      const odd = Object.keys(counts).find((char) => counts[char] === 1)
      return {
        total: cells.length,
        kinds: Object.keys(counts).length,
        odd,
        index: cells.findIndex((node) => node.dataset.char === odd)
      }
    })
    if (board.total < 9) throw new Error(`格子只有 ${board.total} 个，题面太小`)
    if (board.kinds !== 2 || !board.odd) {
      throw new Error(`一关里出现 ${board.kinds} 种字，「找不同」应当只有 1 个字与众不同`)
    }

    // 只用键盘作答：聚焦那个格子，回车提交
    await page.evaluate((i) => document.querySelectorAll('.spot__cell')[i].focus(), board.index)
    await page.keyboard.press('Enter')
    await new Promise((r2) => setTimeout(r2, 450))

    const said = await page.evaluate(
      () => document.querySelector('.spot-game .sr-only[aria-live="polite"]')?.innerText ?? ''
    )
    if (!/答对了/.test(said)) throw new Error(`第 ${r + 1} 关按回车没有判对：「${said}」`)
    solved += 1
    await new Promise((r2) => setTimeout(r2, 900))
  }

  const score = await page.evaluate(() =>
    Number(document.body.innerText.match(/⭐\s*(\d+)/)?.[1] ?? 0)
  )
  if (score < solved) throw new Error(`连过 ${solved} 关但计分只有 ${score}`)

  return `键盘连过 ${solved} 关，计分 ${score}`
})

await interact('绘本：逐句朗读高亮 + 点字发音', '/#/books/b1', async (page) => {
  await clickText(page, '读给我听')
  await new Promise((r) => setTimeout(r, 600))

  const lit = await page.evaluate(() => {
    const marked = [...document.querySelectorAll('.glyph.is-reading')]
    const all = document.querySelectorAll('.glyph').length
    return { marked: marked.length, all, text: marked.map((n) => n.innerText).join('') }
  })
  if (!lit.marked) throw new Error('点了「读给我听」但没有任何字被高亮')
  if (lit.marked >= lit.all) throw new Error('整页都高亮了，说明没有逐句只是整页刷色')

  // 点一个字：应当停下逐句朗读，并弹出这个字的拼音释义
  const tapped = await page.evaluate(() => {
    const g = [...document.querySelectorAll('.glyph')].find(
      (n) => !n.classList.contains('glyph--punct')
    )
    if (!g) return null
    g.click()
    return g.innerText.trim()
  })
  await new Promise((r) => setTimeout(r, 350))
  const peek = await page.evaluate(() => {
    const box = document.querySelector('.peek')
    return box ? box.innerText.replace(/\s+/g, ' ').trim() : ''
  })
  if (!peek.includes(tapped)) throw new Error(`点「${tapped}」没有弹出发音卡片`)

  return `高亮 ${lit.marked}/${lit.all} 字（「${lit.text}」），点「${tapped}」弹出：${peek}`
})

await interact('成语头图：跟着 data-theme 换色', '/#/idioms/szdt', async (page) => {
  const read = () =>
    page.evaluate(() => {
      const hero = document.querySelector('.hero')
      return hero ? getComputedStyle(hero).backgroundImage : ''
    })
  const sunny = await read()
  await page.evaluate(() => {
    document.documentElement.dataset.theme = 'night'
  })
  await new Promise((r) => setTimeout(r, 350))
  const night = await read()

  if (!sunny || sunny === 'none') throw new Error('头图没有渐变背景')
  if (sunny === night) throw new Error('切到夜间主题后头图配色没变，说明还是写死的调色板')
  return '明亮 / 夜间两套主题下头图背景各不相同'
})

// 用 b3：前面的绘本用例已经把 b1 读完了，而「第一次读完」才发庆祝
await interact('庆祝动画：可以立刻跳过', '/#/books/b3', async (page) => {
  await page.waitForFunction(() => /下一页|读完啦/.test(document.body.innerText), { timeout: 10000 })
  for (let i = 0; i < 8; i++) {
    if (await clickText(page, '下一页')) continue
    if (await clickText(page, '读完啦')) break
    break
  }
  await page.waitForSelector('.cel', { timeout: 5000 })

  const before = await page.evaluate(() => ({
    open: !!document.querySelector('.cel'),
    skip: !!document.querySelector('.cel__skip')
  }))
  if (!before.open) throw new Error('读完整本没有弹出庆祝层')
  if (!before.skip) throw new Error('庆祝层没有跳过按钮')

  await page.evaluate(() => document.querySelector('.cel__skip').click())
  await new Promise((r) => setTimeout(r, 250))
  const gone = await page.evaluate(() => !document.querySelector('.cel'))
  if (!gone) throw new Error('点了跳过但庆祝层还在')

  // 跳过后状态要和播完一样：奖励的星星已经进账，读完页正常显示
  const settled = await page.evaluate(() => document.body.innerText.includes('读完啦'))
  if (!settled) throw new Error('跳过庆祝后没有回到读完页')
  return '庆祝层弹出 → 点跳过 → 立即回到读完页'
})

await interact('家长中心：过验证并切主题', '/#/parent', async (page) => {
  const solved = await page.evaluate(() => {
    const label = document.body.innerText.match(/(\d+)\s*\+\s*(\d+)/)
    const input = document.querySelector('input[type="number"]')
    if (!label || !input) return false
    const setter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype,
      'value'
    ).set
    setter.call(input, String(Number(label[1]) + Number(label[2])))
    input.dispatchEvent(new Event('input', { bubbles: true }))
    return true
  })
  await new Promise((r) => setTimeout(r, 200))
  await clickText(page, '进入')
  const inside = await page.evaluate(() => document.body.innerText.includes('使用设置'))
  const switched = await clickText(page, '护眼模式')
  await new Promise((r) => setTimeout(r, 350))
  const theme = await page.evaluate(() => document.documentElement.dataset.theme)
  // 主题要能写进 localStorage，刷新后保持
  await page.reload({ waitUntil: 'networkidle2' })
  await new Promise((r) => setTimeout(r, 400))
  const after = await page.evaluate(() => document.documentElement.dataset.theme)
  return `解锁=${solved && inside}，点护眼=${switched}，theme=${theme}，刷新后=${after}`
})

await interact('进度追踪：学过的字刷新后仍在', `/#/learn/${encodeURIComponent('山')}`, async (page) => {
  await new Promise((r) => setTimeout(r, 800))
  const stored = await page.evaluate(() => {
    const key = Object.keys(localStorage).find((k) => (localStorage.getItem(k) ?? '').includes('"chars"'))
    if (!key) return null
    const data = JSON.parse(localStorage.getItem(key))
    const s = data.data ?? data
    return { key, chars: Object.keys(s.chars ?? {}) }
  })
  if (!stored) return '没有找到进度存档'

  // 换个字再回来，确认累加而不是覆盖
  await page.goto(page.url().replace(/#.*$/, `#/learn/${encodeURIComponent('水')}`))
  await new Promise((r) => setTimeout(r, 800))
  await page.reload({ waitUntil: 'networkidle2' })
  await new Promise((r) => setTimeout(r, 800))

  const after = await page.evaluate((key) => {
    const data = JSON.parse(localStorage.getItem(key))
    const s = data.data ?? data
    return Object.keys(s.chars ?? {})
  }, stored.key)

  const ok = after.includes('山') && after.includes('水')
  return `存档键=${stored.key}，刷新后记录了 ${after.length} 个字（山+水 都在=${ok}）`
})

await interact('描红：键盘替代通道可以写完整个字', `/#/learn/${encodeURIComponent('日')}`, async (page) => {
  await page.evaluate(() => localStorage.clear())
  await page.reload({ waitUntil: 'networkidle2' })
  await page.waitForSelector('.hz__host svg', { timeout: 8000 })

  if (!(await clickText(page, '我来写'))) throw new Error('单字页缺少「我来写」描红入口')
  await new Promise((r) => setTimeout(r, 400))

  const staged = await page.evaluate(() => {
    const stage = document.querySelector('.hz__stage')
    return {
      focusable: stage?.getAttribute('tabindex') === '0',
      focused: document.activeElement === stage,
      labelled: (stage?.getAttribute('aria-label') ?? '').includes('Esc'),
      live: document.querySelector('.hz__hint')?.getAttribute('aria-live') === 'polite'
    }
  })
  if (!staged.focusable) throw new Error('描红时田字格不可聚焦，键盘进不去')
  if (!staged.focused) throw new Error('进入描红后焦点没有落到田字格上')
  if (!staged.labelled) throw new Error('描红区没有说明键盘怎么用')
  if (!staged.live) throw new Error('描红提示不是 aria-live 播报区')

  // 「日」四笔：只用键盘，一笔一笔写完
  for (let i = 0; i < 6; i++) {
    const done = await page.evaluate(() => /满分|写完啦/.test(document.querySelector('.hz__hint')?.innerText ?? ''))
    if (done) break
    await page.keyboard.press('Space')
    await new Promise((r) => setTimeout(r, 320))
  }

  const finished = await page.evaluate(() => ({
    hint: document.querySelector('.hz__hint')?.innerText.trim() ?? '',
    traced: JSON.parse(localStorage.getItem('happy-literacy:v1') ?? '{}')?.chars?.['日']?.traced ?? 0
  }))
  if (!/满分|写完啦/.test(finished.hint)) {
    throw new Error(`键盘写完全部笔画后没有完成提示：「${finished.hint}」`)
  }
  if (finished.traced < 1) throw new Error('键盘写完一个字没有记进「会写了」')

  // 跳过通道：再进一次描红，按 Esc 应当直接退出
  if (!(await clickText(page, '我来写'))) throw new Error('完成后无法再次进入描红')
  await new Promise((r) => setTimeout(r, 300))
  await page.keyboard.press('Escape')
  await new Promise((r) => setTimeout(r, 300))
  const escaped = await page.evaluate(() => ({
    quizOff: document.querySelector('.hz__stage')?.getAttribute('tabindex') !== '0',
    hint: document.querySelector('.hz__hint')?.innerText ?? ''
  }))
  if (!escaped.quizOff) throw new Error('按 Esc 之后还停在描红状态')
  if (!escaped.hint.includes('跳过')) throw new Error('跳过描红没有给出提示')

  return `键盘写完「日」（traced=${finished.traced}），Esc 可跳过`
})

/** 在田字格里拖一笔；坐标是 svg 内的相对位置（0-1）。 */
const drawStroke = async (page, from, to) => {
  const box = await page.evaluate(() => {
    const svg = document.querySelector('.hz__host svg')
    if (!svg) return null
    const r = svg.getBoundingClientRect()
    return { x: r.x, y: r.y, w: r.width, h: r.height }
  })
  if (!box) throw new Error('田字格里没有 svg，无法模拟书写')
  const at = (t) => ({ x: box.x + t.x * box.w, y: box.y + t.y * box.h })
  const a = at(from)
  const b = at(to)
  await page.mouse.move(a.x, a.y)
  await page.mouse.down()
  for (let i = 1; i <= 8; i += 1) {
    await page.mouse.move(a.x + ((b.x - a.x) * i) / 8, a.y + ((b.y - a.y) * i) / 8)
  }
  await page.mouse.up()
  await new Promise((r) => setTimeout(r, 220))
}

const phaseOf = (page) => page.evaluate(() => document.querySelector('.detail')?.dataset.phase ?? '')

const waitPhase = (page, want, timeout = 12000) =>
  page.waitForFunction(
    (id) => document.querySelector('.detail')?.dataset.phase === id,
    { timeout },
    want
  )

await interact('单字五步状态机：认→写→听→考→奖自动衔接', `/#/learn/${encodeURIComponent('日')}`, async (page) => {
  await page.evaluate(() => localStorage.clear())
  await page.reload({ waitUntil: 'networkidle2' })
  await page.waitForSelector('.rail__step', { timeout: 8000 })

  const rail = await page.evaluate(() =>
    [...document.querySelectorAll('.rail__step')].map((n) => n.dataset.step)
  )
  const want = ['intro', 'trace', 'listen', 'quiz', 'reward']
  if (rail.join(',') !== want.join(',')) {
    throw new Error(`步骤条不是五步 ${want.join('→')}，实际是 ${rail.join('→')}`)
  }
  if ((await phaseOf(page)) !== 'intro') throw new Error('进页面没有停在「认一认」')

  // 认一认：听一次读音就应当自动排上「写一写」
  if (!(await clickText(page, '怎么读'))) throw new Error('「认一认」缺少听读音按钮')
  const queued = await page.evaluate(() => document.querySelector('.autonext')?.innerText ?? '')
  if (!queued.includes('写一写')) throw new Error(`听完读音没有预告下一步：「${queued}」`)
  if (!queued.includes('等一下')) throw new Error('自动衔接没有给「等一下」的按停出口')
  await waitPhase(page, 'trace')

  // 写一写：进入这一步田字格会自己开始描红，用「写下一笔」写完
  await page.waitForFunction(
    () => document.querySelector('.hz__stage')?.getAttribute('tabindex') === '0',
    { timeout: 8000 }
  )
  for (let i = 0; i < 8; i += 1) {
    const done = await page.evaluate(() =>
      /满分|写完啦/.test(document.querySelector('.hz__hint')?.innerText ?? '')
    )
    if (done) break
    if (!(await clickText(page, '写下一笔'))) break
  }
  await waitPhase(page, 'listen')

  // 听一听 / 考一考：都选正确项，每一步作答后自动进入下一步
  const pickAnswer = async (label) => {
    await page.waitForSelector('.opt[data-char="日"]', { timeout: 8000 })
    const ok = await page.evaluate(() => {
      const btn = document.querySelector('.opt[data-char="日"]')
      if (!btn || btn.disabled) return false
      btn.click()
      return true
    })
    if (!ok) throw new Error(`「${label}」里点不到正确选项`)
  }
  await pickAnswer('听一听')
  await waitPhase(page, 'quiz')
  await pickAnswer('考一考')
  await waitPhase(page, 'reward')

  const settled = await page.evaluate(() => {
    const saved = JSON.parse(localStorage.getItem('happy-literacy:v1') ?? '{}')
    return {
      flows: saved.flowsCompleted ?? 0,
      charFlows: saved.chars?.['日']?.flows ?? 0,
      traced: saved.chars?.['日']?.traced ?? 0,
      steps: [...document.querySelectorAll('.rail__step.is-done')].map((n) => n.dataset.step),
      reward: document.querySelector('.reward')?.innerText.replace(/\s+/g, ' ').trim() ?? ''
    }
  })
  if (settled.flows < 1) throw new Error('走完五步没有记下一次完整闭环')
  if (settled.charFlows < 1) throw new Error('「日」自己的闭环次数没有加上')
  if (settled.traced < 1) throw new Error('五步里的描红没有记进「会写了」')
  for (const step of ['intro', 'trace', 'listen', 'quiz']) {
    if (!settled.steps.includes(step)) throw new Error(`步骤条上「${step}」没有标成已完成`)
  }
  if (!settled.reward) throw new Error('「领奖励」这一步是空的')

  // 手动回跳：点步骤条应当能回到前面的步骤
  await page.evaluate(() => document.querySelector('.rail__step[data-step="listen"]')?.click())
  await waitPhase(page, 'listen', 5000)

  return `五步自动衔接完成（闭环 ${settled.flows} 次，描红 ${settled.traced} 遍），步骤条可回跳`
})

await interact('描红：同一笔连错 3 次自动示范这一笔', `/#/learn/${encodeURIComponent('日')}`, async (page) => {
  await page.evaluate(() => localStorage.clear())
  await page.reload({ waitUntil: 'networkidle2' })
  await page.waitForSelector('.hz__host svg', { timeout: 8000 })

  if (!(await clickText(page, '我来写'))) throw new Error('单字页缺少「我来写」描红入口')
  await new Promise((r) => setTimeout(r, 400))

  // 「日」第一笔是左边的竖；沿着顶边横着划三次，三次都不该被判对
  for (let i = 0; i < 3; i += 1) {
    await drawStroke(page, { x: 0.15, y: 0.08 }, { x: 0.85, y: 0.08 })
  }
  await page.waitForFunction(() => Number(document.querySelector('.hz')?.dataset.demos ?? 0) >= 1, {
    timeout: 8000
  })

  const state = await page.evaluate(() => ({
    demos: Number(document.querySelector('.hz')?.dataset.demos ?? 0),
    mistakes: Number(document.querySelector('.hz')?.dataset.mistakes ?? 0),
    hint: document.querySelector('.hz__hint')?.innerText.trim() ?? '',
    label: document.querySelector('.hz__stage')?.getAttribute('aria-label') ?? ''
  }))
  if (state.mistakes < 3) throw new Error(`只记到 ${state.mistakes} 次错笔，没能连错 3 次`)
  if (!/示范|看我写/.test(state.hint)) throw new Error(`自动示范没有播报出来：「${state.hint}」`)
  if (!state.label.includes('示范')) throw new Error('描红区没有说明连错会自动示范')

  // 示范完要把测验接回原处：还能继续写，写满全部笔画照样算完成
  await page.waitForFunction(
    () => !/示范|看我写/.test(document.querySelector('.hz__hint')?.innerText ?? ''),
    { timeout: 8000 }
  )
  for (let i = 0; i < 8; i += 1) {
    const done = await page.evaluate(() =>
      /满分|写完啦/.test(document.querySelector('.hz__hint')?.innerText ?? '')
    )
    if (done) break
    if (!(await clickText(page, '写下一笔'))) break
  }
  const finished = await page.evaluate(() => ({
    hint: document.querySelector('.hz__hint')?.innerText.trim() ?? '',
    traced: JSON.parse(localStorage.getItem('happy-literacy:v1') ?? '{}')?.chars?.['日']?.traced ?? 0
  }))
  if (!/写完啦|满分/.test(finished.hint)) {
    throw new Error(`示范后接不回测验，没写完：「${finished.hint}」`)
  }
  if (finished.traced < 1) throw new Error('示范后写完的这一遍没有记进「会写了」')
  if (!/错了\s*\d+\s*次/.test(finished.hint)) {
    throw new Error(`示范前的错笔数被重启测验清零了：「${finished.hint}」`)
  }

  return `连错 ${state.mistakes} 次触发 ${state.demos} 次自动示范，接回测验后写完（${finished.hint}）`
})

await interact('徽章：学会第一个字就点亮，首页与家长中心都看得见', '/#/', async (page) => {
  await page.evaluate(() => localStorage.clear())
  await page.goto(`${page.url().replace(/#.*$/, '')}#/learn/${encodeURIComponent('日')}`, {
    waitUntil: 'networkidle2'
  })
  await new Promise((r) => setTimeout(r, 700))

  const stored = await page.evaluate(
    () => Object.keys(JSON.parse(localStorage.getItem('happy-literacy:v1') ?? '{}').badges ?? {})
  )
  if (!stored.includes('first-step')) {
    throw new Error(`学会第一个字后没有解锁「启蒙芽」，存档里只有：${stored.join('、') || '空'}`)
  }

  await page.goto(page.url().replace(/#.*$/, '#/'), { waitUntil: 'networkidle2' })
  await new Promise((r) => setTimeout(r, 500))
  const home = await page.evaluate(() => ({
    shelf: !!document.querySelector('.badges'),
    lit: document.querySelectorAll('.badge[data-unlocked="true"]').length,
    first: document.querySelector('.badge[data-badge="first-step"]')?.dataset.unlocked,
    chip: /徽章\s*\d+\/\d+/.test(document.body.innerText)
  }))
  if (!home.shelf) throw new Error('首页没有徽章架')
  if (home.first !== 'true') throw new Error('首页徽章架上「启蒙芽」还是灰的')
  if (!home.chip) throw new Error('首页顶部没有徽章数量')

  await page.goto(page.url().replace(/#.*$/, '#/parent'), { waitUntil: 'networkidle2' })
  // 家长中心是按需 chunk，机器忙的时候几百毫秒挂不上来；等口算门真出现再答题
  await page.waitForSelector('input[type="number"]', { timeout: 10000 })
  await page.evaluate(() => {
    const label = document.body.innerText.match(/(\d+)\s*\+\s*(\d+)/)
    const input = document.querySelector('input[type="number"]')
    if (!label || !input) return
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set
    setter.call(input, String(Number(label[1]) + Number(label[2])))
    input.dispatchEvent(new Event('input', { bubbles: true }))
  })
  await new Promise((r) => setTimeout(r, 200))
  await clickText(page, '进入')
  await page.waitForSelector('.badge', { timeout: 10000 }).catch(() => {})

  const parent = await page.evaluate(() => ({
    total: document.querySelectorAll('.badge').length,
    lit: document.querySelectorAll('.badge[data-unlocked="true"]').length,
    locked: document.querySelectorAll('.badge[data-unlocked="false"] .badge__fill').length,
    wall: document.body.innerText.includes('成就徽章墙')
  }))
  if (!parent.wall) throw new Error('家长中心没有徽章墙')
  if (parent.total < 5) throw new Error(`徽章种类只有 ${parent.total} 种，Round 4 要求至少 5 种`)
  if (parent.lit < 1) throw new Error('家长中心徽章墙上一枚都没点亮')
  if (!parent.locked) throw new Error('未解锁的徽章没有显示进度条')

  return `首页点亮 ${home.lit} 枚；家长中心共 ${parent.total} 枚（点亮 ${parent.lit}，${parent.locked} 枚带进度条）`
})

await interact('播报：答题与庆祝都有 aria-live', '/#/listen', async (page) => {
  await clickText(page, '开始游戏')
  await new Promise((r) => setTimeout(r, 600))

  const region = await page.evaluate(() => {
    const node = [...document.querySelectorAll('[aria-live="polite"]')].find((n) =>
      n.classList.contains('sr-only')
    )
    return node ? node.innerText.trim() : ''
  })
  if (!/第\s*\d+\s*关/.test(region)) throw new Error(`答题开始没有播报关卡：「${region}」`)

  await page.evaluate(() => document.querySelector('.opt')?.click())
  await new Promise((r) => setTimeout(r, 500))
  const answered = await page.evaluate(
    () =>
      [...document.querySelectorAll('.sr-only[aria-live="polite"]')]
        .map((n) => n.innerText.trim())
        .join(' ')
  )
  if (!/答对了|正确答案/.test(answered)) throw new Error(`作答后没有播报对错：「${answered}」`)

  // 庆祝浮层：读完一本没读过的绘本
  await page.goto(page.url().replace(/#.*$/, '#/books/b2'), { waitUntil: 'networkidle2' })
<<<<<<< HEAD
  // 绘本页也是按需 chunk：翻页按钮没挂上来就开始点，会一页都翻不到
  await page.waitForFunction(() => /下一页|读完啦/.test(document.body.innerText), { timeout: 10000 })
=======
  // 换 hash 不重新加载文档，goto 立刻就返回；绘本视图是按需 chunk，
  // 机器忙的时候几百毫秒挂不上来，翻页按钮还不存在，整本书就会一页没翻完
  await page.waitForSelector('.reader .spread', { timeout: 10000 })
>>>>>>> 9357d59 (test(识字 smoke): 绘本视图挂上来再翻页，修掉庆祝浮层探针的偶发失败)
  for (let i = 0; i < 8; i++) {
    if (await clickText(page, '下一页')) {
      // 翻到最后一页就发庆祝，而庆祝几秒后会自动收场：
      // 一看见浮层就停手，别把剩下的空翻页耗在它的展示时间里
      if (await page.$('.cel')) break
      continue
    }
    if (await clickText(page, '读完啦')) break
    break
  }
  await page.waitForSelector('.cel', { timeout: 5000 })
  const celebration = await page.evaluate(() => {
    const layer = document.querySelector('.cel')
    if (!layer) return null
    const live = layer.querySelector('[aria-live="polite"]')
    return { text: live?.innerText.trim() ?? '', prohibited: !!layer.querySelector('span[aria-label]:not([role])') }
  })
  if (!celebration) throw new Error('读完绘本没有弹出庆祝层')
  if (!celebration.text) throw new Error('庆祝层没有播报内容')
  if (!celebration.text.includes('跳过')) throw new Error('庆祝播报没有告诉用户可以跳过')
  if (celebration.prohibited) throw new Error('庆祝层里有 span 直接挂 aria-label（axe aria-prohibited-attr）')

  return `答题播报「${region.slice(0, 14)}…」，庆祝播报「${celebration.text.slice(0, 18)}…」`
})

await interact('设计令牌：识字 App 用的是共享令牌层', '/#/', async (page) => {
  const tokens = await page.evaluate(() => {
    const cs = getComputedStyle(document.documentElement)
    const read = (name) => cs.getPropertyValue(name).trim()
    return {
      shared: read('--tap-hero'),
      palette: read('--mango-500'),
      textSoft: read('--text-soft'),
      artTint: read('--art-tint')
    }
  })
  if (!tokens.shared || !tokens.palette) {
    throw new Error('没有读到 shared/styles/design-tokens.css 里的令牌，说明没接进来')
  }
  if (!tokens.artTint) throw new Error('识字 App 自己的 --art-tint 丢了')
  return `共享令牌 --tap-hero=${tokens.shared}，--mango-500=${tokens.palette}，--text-soft=${tokens.textSoft}`
})

/* ------------------------------------------------------------ 字源演变 */

/** 等演变动画走到收尾状态，再把舞台上的东西数一遍。 */
const readStage = (page) =>
  page.evaluate(() => {
    const el = document.querySelector('.ety')
    if (!el) return null
    const strokes = [...el.querySelectorAll('.ety__stroke')]
    const frames = [...el.querySelectorAll('.ety__frame')]
    return {
      stage: el.dataset.stage,
      kind: el.dataset.kind,
      ink: el.querySelectorAll('.ety__ink').length,
      parts: el.querySelectorAll('.ety__part').length,
      strokes: strokes.length,
      masked: strokes.filter((p) => p.getAttribute('mask')).length,
      reveals: el.querySelectorAll('.ety__reveal').length,
      visibleFrames: frames.filter((f) => Number(getComputedStyle(f).opacity) > 0.9).length,
      text: el.querySelector('.ety__text')?.innerText.replace(/\s+/g, ' ').trim() ?? '',
      live: el.querySelector('.sr-only[aria-live="polite"]')?.innerText.trim() ?? ''
    }
  })

const waitStageDone = (page) =>
  page.waitForFunction(
    () => ['done', 'static'].includes(document.querySelector('.ety')?.dataset.stage),
    { timeout: 20000 }
  )

await interact(
  '字源馆：象形字从小图演变到笔画',
  `/#/etymology/${encodeURIComponent('日')}`,
  async (page) => {
    await page.waitForSelector('.ety[data-ready="true"]', { timeout: 12000 })
    await waitStageDone(page)
    const s = await readStage(page)
    if (s.kind !== 'xiang') throw new Error(`「日」应当归在象形，实际是 ${s.kind}`)
    if (s.ink < 2) throw new Error(`第一帧的小图只画出了 ${s.ink} 笔`)
    if (s.strokes < 3) throw new Error(`第二帧只画出了 ${s.strokes} 笔，笔顺数据没接上`)
    if (s.masked !== s.strokes) throw new Error('笔画没有挂上遮罩，「一笔一笔写」的动画不会生效')
    if (s.reveals !== s.strokes) throw new Error(`遮罩 ${s.reveals} 条对不上 ${s.strokes} 笔`)
    if (!s.text.includes('象形')) throw new Error(`配文里没有说明这是什么字：「${s.text}」`)
    if (!s.live) throw new Error('演变过程没有任何 aria-live 播报')
    return `象形「日」：小图 ${s.ink} 笔 → 楷书 ${s.strokes} 笔（${s.masked} 笔逐笔显出）`
  }
)

await interact(
  '字源馆：形声字先拆零件，切字后重新演一遍',
  `/#/etymology/${encodeURIComponent('河')}`,
  async (page) => {
    await page.waitForSelector('.ety[data-ready="true"]', { timeout: 12000 })
    await waitStageDone(page)
    const he = await readStage(page)
    if (he.kind !== 'xing') throw new Error(`「河」应当归在形声，实际是 ${he.kind}`)
    if (he.parts !== 2) throw new Error(`形声字第一帧应当摆出两个零件，实际 ${he.parts} 个`)
    if (he.ink !== 0) throw new Error('形声字不该画小图')
    if (!he.strokes) throw new Error('形声字第二帧没有笔画')

    // 换一个字：舞台要重新从「看图」演起，而不是停在上一个字的收尾状态
    const picked = await page.evaluate(() => {
      const btn = [...document.querySelectorAll('.glyphbtn')].find((b) => b.innerText.trim() === '山')
      if (!btn) return false
      btn.click()
      return true
    })
    if (!picked) throw new Error('字表里点不到「山」')
    await page.waitForFunction(() => document.querySelector('.ety')?.dataset.char === '山', {
      timeout: 8000
    })
    await waitStageDone(page)
    const shan = await readStage(page)
    if (shan.kind !== 'xiang') throw new Error('换到「山」以后分类没跟着换')
    if (!shan.ink) throw new Error('换字后第一帧的小图没有重新画出来')
    return `形声「河」拆成 ${he.parts} 个零件；换到象形「山」后重演（小图 ${shan.ink} 笔）`
  }
)

await interact(
  '字源馆：系统要求减少动态时降级成两幅静图',
  `/#/etymology/${encodeURIComponent('日')}`,
  async (page) => {
    await page.emulateMediaFeatures([{ name: 'prefers-reduced-motion', value: 'reduce' }])
    await page.reload({ waitUntil: 'networkidle2', timeout: 20000 })
    await page.waitForSelector('.ety[data-ready="true"]', { timeout: 12000 })
    await new Promise((r) => setTimeout(r, 600))

    const s = await readStage(page)
    if (s.stage !== 'static') throw new Error(`减少动态时应当直接进静止模式，实际 stage=${s.stage}`)
    if (s.masked !== 0) throw new Error('静止模式下笔画还挂着遮罩，会有一半笔画显不出来')
    if (s.visibleFrames < 2) throw new Error(`静止模式要把两幅图都摆出来，实际只看得到 ${s.visibleFrames} 幅`)
    if (!s.ink || !s.strokes) throw new Error('静止模式下小图或字形是空的')
    if (!s.text.includes('象形')) throw new Error('静止模式下配文丢了')

    // 不动，但该说的一句不能少：文字说明和播报都要还在
    if (!s.live.includes('减少动态')) {
      throw new Error(`静止模式没有告诉用户动画为什么没播：「${s.live}」`)
    }
    const noReplay = await page.evaluate(() =>
      [...document.querySelectorAll('.ety__acts .btn')].every((b) => !b.innerText.includes('再演一遍'))
    )
    if (!noReplay) throw new Error('减少动态时还留着「再演一遍」按钮')
    return `静止模式：两幅图并排（小图 ${s.ink} 笔 + 楷书 ${s.strokes} 笔），无遮罩、无时间线`
  }
)

await interact(
  '单字页：字源动画点开才下载',
  `/#/learn/${encodeURIComponent('山')}`,
  async (page) => {
    const isStageChunk = (url) => {
      const file = url.split('/').pop() ?? ''
      return /^EtymologyStage-/.test(file) || /^etymology-(?!index-)/.test(file)
    }
    const asked = []
    page.on('request', (r) => {
      if (isStageChunk(r.url())) asked.push(r.url().split('/').pop())
    })

    await page.reload({ waitUntil: 'networkidle2', timeout: 20000 })
    await page.waitForSelector('#char-origin-panel', { timeout: 8000 })
    await new Promise((r) => setTimeout(r, 400))
    if (asked.length) throw new Error(`还没点就下载了字源分块：${asked.join('、')}`)

    const collapsed = await page.evaluate(() => {
      const btn = document.querySelector('[aria-controls="char-origin-panel"]')
      return { expanded: btn?.getAttribute('aria-expanded'), stage: !!document.querySelector('.ety') }
    })
    if (collapsed.expanded !== 'false') throw new Error('入口按钮没有正确标注 aria-expanded')
    if (collapsed.stage) throw new Error('还没点开，演变舞台就已经挂在页面上了')

    await page.evaluate(() => document.querySelector('[aria-controls="char-origin-panel"]').click())
    await page.waitForSelector('.ety[data-ready="true"]', { timeout: 12000 })
    await waitStageDone(page)

    if (!asked.length) throw new Error('点开之后也没有请求字源分块，说明它被打进了主包')
    const s = await readStage(page)
    if (!s.ink || !s.strokes) throw new Error('单字页里的演变舞台是空的')
    const expanded = await page.evaluate(
      () => document.querySelector('[aria-controls="char-origin-panel"]')?.getAttribute('aria-expanded')
    )
    if (expanded !== 'true') throw new Error('展开后 aria-expanded 没有跟着变')

    return `点开前 0 个请求，点开后加载 ${asked.length} 个分块（${asked.join('、')}）并演完`
  }
)

await interact('单字页：笔顺数据可用', `/#/learn/${encodeURIComponent('日')}`, async (page) => {
  await new Promise((r) => setTimeout(r, 1500))
  return await page.evaluate(() => {
    const paths = document.querySelectorAll('#app svg path')
    const note = document.body.innerText.includes('需要联网') ? '显示了离线提示' : '无离线提示'
    return `svg path 数=${paths.length}，${note}`
  })
})

await browser.close()
server.close()

/* ------------------------------------------------------------------ 输出 */
console.log('\n路由渲染：')
for (const r of rows) {
  console.log(`  ${r.issues ? '✗' : '✓'} ${r.name.padEnd(18)} ${r.path.padEnd(30)} ${r.chars} 字`)
}

console.log('\n交互：')
for (const i of inter) {
  console.log(`  ${i.ok ? '✓' : '✗'} ${i.label} — ${i.note}`)
  i.errs.slice(0, 3).forEach((e) => console.log(`      ! ${e}`))
}

if (problems.length) {
  console.log('\n问题明细：')
  for (const p of problems) {
    console.log(`  ${p.name} (${p.path})`)
    p.found.slice(0, 6).forEach((f) => console.log(`    - ${f}`))
  }
}

const failed = problems.length + inter.filter((i) => !i.ok).length
console.log(`\n共 ${ROUTES.length} 条路由 + ${inter.length} 项交互，${failed} 项有问题。`)
process.exit(failed ? 1 : 0)
