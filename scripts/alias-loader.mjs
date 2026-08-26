/**
 * 仓库级 `@/` 解析钩子。
 *
 * 两个 App 的源码都用 Vite 的 `@/` 指向自己的 `src/`，Node 直接 import 这些模块时
 * 解析不了。这里按「谁 import 的就用谁的 app 根目录」来还原：`@/utils/random`
 * 从 apps/math-app/src 下的文件引入就落到 math-app，从 literacy-app 引入就落到
 * literacy-app，不会串到另一个 App 去。
 */
import { existsSync } from 'node:fs'
import { fileURLToPath, pathToFileURL } from 'node:url'
import { join } from 'node:path'

const APP_SRC = /^(.*\/apps\/[^/]+\/src)\//

export function resolve(specifier, context, next) {
  if (!specifier.startsWith('@/')) return next(specifier, context)
  const parent = context.parentURL ? fileURLToPath(context.parentURL) : ''
  const src = APP_SRC.exec(parent.replace(/\\/g, '/'))?.[1]
  if (!src) return next(specifier, context)
  let target = join(src, specifier.slice(2))
  if (!existsSync(target) && existsSync(`${target}.js`)) target = `${target}.js`
  return next(pathToFileURL(target).href, context)
}
