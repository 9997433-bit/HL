import { existsSync } from 'node:fs'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { join } from 'node:path'
const SRC = fileURLToPath(new URL('../src/', import.meta.url))
export function resolve(specifier, context, next) {
  if (!specifier.startsWith('@/')) return next(specifier, context)
  let p = join(SRC, specifier.slice(2))
  if (!existsSync(p) && existsSync(`${p}.js`)) p = `${p}.js`
  return next(pathToFileURL(p).href, context)
}
