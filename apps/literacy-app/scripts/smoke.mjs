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
  ['偏旁部首', '/#/radicals'],
  ['偏旁详情', '/#/radicals/shui'],
  ['绘本书架', '/#/books'],
  ['绘本 b1', '/#/books/b1'],
  ['绘本 b2', '/#/books/b2'],
  ['绘本 b3', '/#/books/b3'],
  ['绘本 b4', '/#/books/b4'],
  ['绘本 b5', '/#/books/b5'],
  ['成语列表', '/#/idioms'],
  ['成语 守株待兔', '/#/idioms/szdt'],
  ['成语 画蛇添足', '/#/idioms/hstz'],
  ['成语 水滴石穿', '/#/idioms/sdsc'],
  ['成语 举一反三', '/#/idioms/jyfs'],
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

  return `持久化卡=${seeded.count}，到期“日”可见，未来“月”已排除`
})

await interact('200 字字表：分页渲染且所有字可达', '/#/learn', async (page) => {
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
  if (first.total < 200) throw new Error(`字库规模只有 ${first.total}，Round 3 要求至少 200 字`)
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
  while (reached.size < first.total && turns < 40) {
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
  for (let i = 0; i < 8; i++) {
    if (await clickText(page, '下一页')) continue
    if (await clickText(page, '读完啦')) break
    break
  }
  await new Promise((r) => setTimeout(r, 400))

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
