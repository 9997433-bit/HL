import { existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

import { CHARACTERS } from '../src/data/characters.js'

const root = join(dirname(fileURLToPath(import.meta.url)), '..')
const candidates = [
  'src/data/char-play.js',
  'src/data/charPlay.js',
  'src/data/play-index.js',
  'src/utils/charPlay.js'
]
const relative = candidates.find((file) => existsSync(join(root, file)))

if (!relative) {
  console.log('SKIP ROUND15_H7：Play 引擎尚未合入，未找到 getCharPlay 模块')
  process.exit(0)
}

const module = await import(pathToFileURL(join(root, relative)))
const getCharPlay = module.getCharPlay ?? module.default?.getCharPlay
if (typeof getCharPlay !== 'function') {
  throw new TypeError(`${relative} 已存在但未导出 getCharPlay`)
}

const missing = []
for (const item of CHARACTERS) {
  const play = getCharPlay(item.char)
  if (!play || typeof play.template !== 'string' || !play.template.trim()) {
    missing.push(item.char)
  }
}

if (missing.length) {
  throw new Error(
    `getCharPlay 有 ${missing.length}/${CHARACTERS.length} 个空 template：${missing
      .slice(0, 20)
      .join('、')}`
  )
}

console.log(`PASS ROUND15_H7：getCharPlay ${CHARACTERS.length}/${CHARACTERS.length} template 非空`)
