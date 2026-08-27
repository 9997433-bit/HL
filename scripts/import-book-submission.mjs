/**
 * 绘本社区投稿导入器 —— .agent_workspace/BOOK-COMMUNITY-SUBMISSION.md 里 S3/S5 两步的自动化。
 *
 * 规范把投稿的判据分成 A 类（机器硬拦截）和 B 类（人工评审），这个脚本负责 A 类里
 * 除生成物之外的全部：
 *   A-1 形状        —— ajv 按规范 §3.5 的 JSON Schema 校验；schema 直接从文档里抠，
 *                      不在这儿抄一份，免得文档改了代码还按老规矩收稿；
 *   A-2/A-6 用字    —— 正文和书名都只能用 char-index.js 里的字；
 *   A-3 多音字      —— STRICT 名单里的字必须被 book-pinyin.mjs 的词条覆盖；
 *   A-4 书名唯一    —— 与 core.js + 六个种子文件里的书名比对；
 *   A-5 页数下限    —— 按分级查 MIN_PAGES。
 * A-2/A-3 走的是生成器同一套 book-text.mjs，所以这里说能过，gen:books 就不会翻脸。
 * A-7 ~ A-10 是生成物层面的约束，仍由 check:data 守。
 *
 * 用法：
 *   node scripts/import-book-submission.mjs <submission.json>     校验并合入种子 + 重跑 gen:books
 *   node scripts/import-book-submission.mjs <submission.json> --dry-run   只校验，不落盘
 *   node scripts/import-book-submission.mjs --check-all           校验已归档投稿 + 自检夹具（CI 用）
 *
 * 任何一条 A 类规则红灯都以非零码退出，且不写任何文件。
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { spawnSync } from 'node:child_process'

import Ajv2020 from 'ajv/dist/2020.js'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const appDir = path.join(root, 'apps/literacy-app')
const seedDir = path.join(appDir, 'scripts/data')
const submissionDir = path.join(seedDir, 'submissions')
const fixtureDir = path.join(appDir, 'scripts/fixtures/submissions')
const specFile = path.join(root, '.agent_workspace/BOOK-COMMUNITY-SUBMISSION.md')
const noticesFile = path.join(root, 'THIRD_PARTY_NOTICES.md')

const appImport = (rel) => import(pathToFileURL(path.join(appDir, rel)).href)

const { MIN_PAGES, PUNCT, toPinyin } = await appImport('scripts/book-text.mjs')

/* 单句长度只是 S4 的建议，超了给提示不给红灯（规范 §3.2）。 */
const SENTENCE_HINT = { 1: 10, 2: 14, 3: 18, 4: 24, 5: 24, 6: 24 }

/**
 * schema 只有一份，就写在规范 §3.5 的代码块里。
 * 从文档里抠出来而不是在这儿复制，是为了让「文档改了、CI 还按老规矩收稿」这种
 * 分叉根本没有存在的余地——抠不到就直接报错，不做静默兜底。
 */
function loadSchema() {
  const doc = fs.readFileSync(specFile, 'utf8')
  for (const block of doc.matchAll(/```json\n([\s\S]*?)```/g)) {
    let parsed
    try {
      parsed = JSON.parse(block[1])
    } catch {
      continue
    }
    if (typeof parsed?.$id === 'string' && parsed.$id.includes('book-submission')) return parsed
  }
  throw new Error(
    `在 ${path.relative(root, specFile)} 里找不到投稿 JSON Schema（应是含 $id book-submission-* 的 json 代码块）`
  )
}

const ajv = new Ajv2020({ allErrors: true, strict: false })
const validateShape = ajv.compile(loadSchema())

/** ajv 的报错原文对投稿人不友好，翻成规范 §6.2 那种一句话一条的说法。 */
function describe(err) {
  const at = err.instancePath ? err.instancePath.replace(/^\//, '').replace(/\//g, '.') : '(顶层)'
  switch (err.keyword) {
    case 'additionalProperties':
      return `多了不允许的字段 ${err.params.additionalProperty}${
        err.instancePath ? `（在 ${at}）` : ''
      } —— 这些字段由 gen-books.mjs 生成`
    case 'required':
      return `缺字段 ${err.params.missingProperty}${err.instancePath ? `（在 ${at}）` : ''}`
    case 'enum':
      return `${at} 只接受 ${err.params.allowedValues.join(' / ')}`
    case 'const':
      return `${at} 必须是 ${JSON.stringify(err.params.allowedValue)}`
    case 'pattern':
      return `${at} 含非法字符：正文只能用字表汉字和 ，。！？：、；…— 九个全角标点`
    case 'minItems':
      return `${at} 至少要 ${err.params.limit} 项`
    case 'maxItems':
      return `${at} 最多 ${err.params.limit} 项`
    case 'minLength':
    case 'maxLength':
      return `${at} 长度要求 ${err.keyword === 'minLength' ? '≥' : '≤'} ${err.params.limit}`
    default:
      return `${at} ${err.message}`
  }
}

/** core.js + 六个种子文件里已经占用的书名。 */
async function loadUsedTitles() {
  const { CORE_BOOKS } = await appImport('src/data/books/core.js')
  const { BOOK_SEED } = await appImport('scripts/data/book-seed.mjs')
  const titles = new Map()
  const bump = (t) => titles.set(t, (titles.get(t) ?? 0) + 1)
  CORE_BOOKS.forEach((b) => bump(b.title))
  BOOK_SEED.forEach((b) => bump(b.t))
  return titles
}

/**
 * 一份投稿走完全部 A 类规则。
 *
 * `titlePolicy` 决定 A-4 怎么算书名撞车：
 *   new      待合入的新投稿，书名一次都不许被占；
 *   archived 已归档进 scripts/data/submissions/ 的老投稿，理应在种子里正好出现一次，
 *            零次说明忘了合种子，两次才是真撞车；
 *   lenient  自检夹具，只拦真撞车——夹具那个故事哪天被真的合进种子，门禁不该跟着红。
 */
function inspect(data, { usedTitles, titlePolicy = 'new' }) {
  const findings = []
  const hints = []
  const seen = new Set()
  /* 同一条毛病别报两遍：注音要先独立扫一次用字，越界字天然会被记两次。 */
  const fail = (rule, msg) => {
    const key = `${rule}|${msg}`
    if (seen.has(key)) return
    seen.add(key)
    findings.push({ rule, msg })
  }

  if (!validateShape(data)) {
    /* if/then 只是页数下限那几条规则的外壳，报「must match then schema」对投稿人毫无信息。 */
    for (const err of validateShape.errors) {
      if (err.keyword === 'if') continue
      fail('A-1', describe(err))
    }
  }

  /* 形状错了也把内容规则跑完：投稿人应该一次拿到全部反馈，而不是修一条炸一条。 */
  const level = Number.isInteger(data?.level) ? data.level : null
  const pages = Array.isArray(data?.pages) ? data.pages : []
  const title = typeof data?.title === 'string' ? data.title : ''

  const textErrors = []
  if (title) toPinyin(title, `《${title}》书名`, textErrors)
  pages.forEach((page, i) => {
    if (typeof page?.text === 'string') {
      toPinyin(page.text, `《${title || '?'}》第 ${i + 1} 页`, textErrors)
    }
  })
  for (const msg of textErrors) {
    if (msg.includes('多音字')) fail('A-3', msg)
    else fail(msg.includes('书名') ? 'A-6' : 'A-2', msg)
  }

  if (title) {
    const used = usedTitles.get(title) ?? 0
    if (titlePolicy === 'new' && used > 0) {
      fail('A-4', `书名重复：《${title}》已经被现有书目占用`)
    } else if (titlePolicy !== 'new' && used > 1) {
      fail('A-4', `书名重复：《${title}》在书目里出现了 ${used} 次`)
    }
    if (titlePolicy === 'archived' && used === 0) {
      hints.push(`《${title}》还没合进种子文件，PR 里别忘了 book-seed-l*.mjs`)
    }
  }

  if (level !== null) {
    const need = MIN_PAGES[level] ?? 5
    if (pages.length < need) {
      fail('A-5', `第 ${level} 级要 ≥ ${need} 页，只有 ${pages.length} 页`)
    }
    const limit = SENTENCE_HINT[level] ?? 24
    pages.forEach((page, i) => {
      const text = typeof page?.text === 'string' ? page.text : ''
      const hanzi = [...text].filter((ch) => PUNCT[ch] === undefined).length
      if (hanzi > limit) {
        hints.push(`第 ${i + 1} 页 ${hanzi} 字，超过 L${level} 建议的 ${limit} 字，S4 多半会要求拆句`)
      }
    })
  }

  return { findings, hints }
}

const q = (s) => `'${String(s).replace(/\\/g, '\\\\').replace(/'/g, "\\'")}'`

/** 投稿 JSON → 种子条目源码。缩进和现有种子文件对齐，合入后 diff 里看不出是机器写的。 */
function renderSeedEntry(data) {
  const pages = data.pages.map((p) => `      [${q(p.emoji)}, ${q(p.text)}]`).join(',\n')
  return `  {
    t: ${q(data.title)},
    sub: ${q(data.sub)},
    cover: ${q(data.cover)},
    summary: ${q(data.summary)},
    pages: [
${pages}
    ]
  }`
}

/** 追加到 book-seed-l{N}.mjs 末尾那个数组里，返回原文以便回滚。 */
function appendSeed(level, entry) {
  const file = path.join(seedDir, `book-seed-l${level}.mjs`)
  const before = fs.readFileSync(file, 'utf8')
  const body = before.trimEnd()
  if (!body.endsWith(']')) throw new Error(`${path.relative(root, file)} 结尾不是数组，改坏了？`)
  const inner = body.slice(0, -1).trimEnd()
  const sep = inner.endsWith('[') ? '\n' : ',\n'
  fs.writeFileSync(file, `${inner}${sep}${entry}\n]\n`)
  return { file, before }
}

/** CC-BY-4.0 的投稿要署名（规范 §3.4）；CC0 只在 PR 记录里留痕，不动这个文件。 */
function attribute(data) {
  if (data.contributor.license !== 'CC-BY-4.0') return null
  const before = fs.readFileSync(noticesFile, 'utf8')
  const heading = '## 社区投稿绘本（CC BY 4.0）'
  const line = `- 《${data.title}》—— ${data.contributor.name}`
  if (before.includes(line)) return null

  let next
  const at = before.indexOf(heading)
  if (at === -1) {
    /* 文件末尾是「最近核对」那段落款，新章节插在它前面，别把落款顶到中间去。 */
    const footer = before.lastIndexOf('\n---\n')
    const section = `${heading}\n\n${line}\n`
    next =
      footer === -1
        ? `${before.trimEnd()}\n\n${section}`
        : `${before.slice(0, footer).trimEnd()}\n\n${section}\n${before.slice(footer + 1)}`
  } else {
    const rest = before.slice(at + heading.length)
    const breakAt = rest.search(/\n#{1,6} |\n---/)
    const end = breakAt === -1 ? before.length : at + heading.length + breakAt
    next = `${before.slice(0, end).trimEnd()}\n${line}\n${before.slice(end)}`
  }
  fs.writeFileSync(noticesFile, next)
  return { file: noticesFile, before }
}

function report(label, { findings, hints }) {
  if (findings.length) {
    console.log(`✗ ${label}`)
    for (const f of findings) console.log(`  ${f.rule.padEnd(4)} ✗ ${f.msg}`)
  } else {
    console.log(`✓ ${label}`)
  }
  for (const h of hints) console.log(`       · ${h}`)
  return findings
}

function readJson(file) {
  try {
    return { data: JSON.parse(fs.readFileSync(file, 'utf8')) }
  } catch (e) {
    return { error: e.message }
  }
}

/* ------------------------------------------------------------------ CLI */

const argv = process.argv.slice(2)
const flags = new Set(argv.filter((a) => a.startsWith('--')))
const files = argv.filter((a) => !a.startsWith('--'))
const usedTitles = await loadUsedTitles()

/**
 * CI 用的批量校验：已归档的投稿 + 两份自检夹具。
 * 夹具是这道门禁的看门狗——只跑归档投稿的话，目录空着时门禁会一直绿，
 * 校验器什么时候悄悄坏掉都没人知道。
 */
async function checkAll() {
  let bad = 0
  const archived = fs.existsSync(submissionDir)
    ? fs.readdirSync(submissionDir).filter((f) => f.endsWith('.json')).sort()
    : []
  console.log(`[投稿校验] 已归档投稿 ${archived.length} 份`)
  for (const name of archived) {
    const { data, error } = readJson(path.join(submissionDir, name))
    if (error) {
      console.log(`✗ ${name}：JSON 解析失败 —— ${error}`)
      bad += 1
      continue
    }
    bad += report(name, inspect(data, { usedTitles, titlePolicy: 'archived' })).length ? 1 : 0
  }

  /*
   * 夹具的预期结论写死在这里：合格的必须全绿，规范 §6.2 那份反面教材必须踩中这些规则。
   * 正向夹具按 lenient 判书名——那个故事哪天被真的收进书目，这道门禁不该跟着红；
   * 反面夹具按 new 判，它撞的是 core.js 里的《大大小小》，那本书不会消失。
   */
  const expected = {
    'valid-l2-xiaomaoheyueliang.json': { titlePolicy: 'lenient', rules: [] },
    'rejected-l3-dadaxiaoxiao.json': {
      titlePolicy: 'new',
      rules: ['A-1', 'A-2', 'A-3', 'A-4', 'A-5']
    }
  }
  console.log(`[投稿校验] 自检夹具 ${Object.keys(expected).length} 份`)
  for (const [name, { titlePolicy, rules: want }] of Object.entries(expected)) {
    const file = path.join(fixtureDir, name)
    if (!fs.existsSync(file)) {
      console.log(`✗ 夹具 ${name} 不见了`)
      bad += 1
      continue
    }
    const { data, error } = readJson(file)
    if (error) {
      console.log(`✗ 夹具 ${name}：JSON 解析失败 —— ${error}`)
      bad += 1
      continue
    }
    const got = [
      ...new Set(inspect(data, { usedTitles, titlePolicy }).findings.map((f) => f.rule))
    ].sort()
    const ok = got.join(',') === want.join(',')
    console.log(`${ok ? '✓' : '✗'} 夹具 ${name}：命中 [${got.join(' ')}]，预期 [${want.join(' ')}]`)
    if (!ok) bad += 1
  }

  console.log(
    bad
      ? `\n投稿校验失败：${bad} 份不合格。`
      : `\n投稿校验通过：${archived.length} 份归档投稿 + ${Object.keys(expected).length} 份夹具全绿。`
  )
  return bad ? 1 : 0
}

async function importOne(file, { dryRun }) {
  if (!fs.existsSync(file)) {
    console.error(`找不到投稿文件：${file}`)
    return 1
  }
  const { data, error } = readJson(file)
  if (error) {
    console.error(`JSON 解析失败：${error}`)
    return 1
  }
  const label = `${path.basename(file)}${data?.title ? ` 《${data.title}》` : ''}`
  if (report(label, inspect(data, { usedTitles })).length) {
    console.error('\nA 类规则未全绿，未写任何文件。修完再来一次。')
    return 1
  }
  if (dryRun) {
    console.log('\n--dry-run：A 类全绿，没有落盘。')
    return 0
  }

  const rollback = []
  try {
    fs.mkdirSync(submissionDir, { recursive: true })
    const archived = path.join(submissionDir, path.basename(file))
    if (path.resolve(file) !== archived) {
      if (fs.existsSync(archived)) throw new Error(`${path.relative(root, archived)} 已存在`)
      fs.copyFileSync(file, archived)
      rollback.push(() => fs.rmSync(archived, { force: true }))
    }

    const seed = appendSeed(data.level, renderSeedEntry(data))
    rollback.push(() => fs.writeFileSync(seed.file, seed.before))

    const notice = attribute(data)
    if (notice) rollback.push(() => fs.writeFileSync(notice.file, notice.before))

    const gen = spawnSync(process.execPath, ['scripts/gen-books.mjs'], {
      cwd: appDir,
      encoding: 'utf8',
      stdio: 'inherit'
    })
    if (gen.status !== 0) throw new Error('gen:books 失败（详见上方报错）')

    console.log(`\n已合入 ${path.relative(root, seed.file)} 并重跑生成器。`)
    console.log('接着跑：cd apps/literacy-app && npm run check:data')
    return 0
  } catch (e) {
    rollback.reverse().forEach((undo) => undo())
    console.error(`\n导入失败，已回滚：${e.message}`)
    return 1
  }
}

let code = 0
if (flags.has('--check-all')) {
  code = await checkAll()
} else if (files.length === 1) {
  code = await importOne(path.resolve(files[0]), { dryRun: flags.has('--dry-run') })
} else {
  console.error('用法：node scripts/import-book-submission.mjs <submission.json> [--dry-run]')
  console.error('      node scripts/import-book-submission.mjs --check-all')
  code = 1
}
process.exit(code)
