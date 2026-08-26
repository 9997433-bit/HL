import { createHash } from 'node:crypto'
import { readdir, readFile, writeFile } from 'node:fs/promises'
import { join, relative, resolve, sep } from 'node:path'

const MANIFEST_MARKER = '/* __PRECACHE_MANIFEST__ */'
const VERSION_MARKER = '__PRECACHE_VERSION__'

async function collectFiles(directory) {
  const files = []

  async function visit(currentDirectory) {
    const entries = await readdir(currentDirectory, { withFileTypes: true })
    await Promise.all(
      entries.map(async (entry) => {
        const fullPath = join(currentDirectory, entry.name)
        if (entry.isDirectory()) {
          await visit(fullPath)
        } else if (entry.isFile()) {
          files.push(relative(directory, fullPath).split(sep).join('/'))
        }
      }),
    )
  }

  await visit(directory)
  return files.sort()
}

/**
 * Injects every emitted file into public/sw.js after Vite has copied publicDir.
 * This includes lazy route chunks and public assets that Rollup's bundle does
 * not expose (for example literacy-app's complete hanzi-data directory).
 */
export function offlinePrecache({ serviceWorker = 'sw.js' } = {}) {
  let config

  return {
    name: 'offline-precache',
    apply: 'build',
    configResolved(resolvedConfig) {
      config = resolvedConfig
    },
    async closeBundle() {
      const outputDirectory = resolve(config.root, config.build.outDir)
      const serviceWorkerPath = join(outputDirectory, serviceWorker)
      const files = (await collectFiles(outputDirectory)).filter((file) => file !== serviceWorker)
      const hash = createHash('sha256')

      for (const file of files) {
        hash.update(file)
        hash.update(await readFile(join(outputDirectory, file)))
      }

      const source = await readFile(serviceWorkerPath, 'utf8')
      if (!source.includes(MANIFEST_MARKER) || !source.includes(VERSION_MARKER)) {
        throw new Error(`${serviceWorkerPath} is missing offline precache placeholders`)
      }

      const manifest = files.map((file) => `  ${JSON.stringify(`./${file}`)}`).join(',\n')
      const output = source
        .replace(MANIFEST_MARKER, manifest)
        .replaceAll(VERSION_MARKER, hash.digest('hex').slice(0, 12))

      await writeFile(serviceWorkerPath, output)
    },
  }
}
