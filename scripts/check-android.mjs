/**
 * Android 同步门禁：确保 Web 与 Android 壳层配置齐全，且 dist 可同步到 Capacitor 工程。
 */

import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const fails = []
const notes = []

const check = (ok, msg) => (ok ? notes.push(`✓ ${msg}`) : fails.push(`✗ ${msg}`))
const exists = (rel) => fs.existsSync(path.join(root, rel))
const read = (rel) => {
  try {
    return fs.readFileSync(path.join(root, rel), 'utf8')
  } catch {
    return ''
  }
}

const APPS = [
  {
    id: 'literacy',
    dir: 'apps/literacy-app',
    appId: 'com.hongen.literacy'
  },
  {
    id: 'math',
    dir: 'apps/math-app',
    appId: 'com.hongen.mathquest'
  }
]

check(exists('scripts/sync-android.sh'), 'sync-android.sh 存在')
check(exists('scripts/gen-pwa-icons.mjs'), 'gen-pwa-icons.mjs 存在')
check(read('package.json').includes('"sync:android"'), 'package.json 已接线 sync:android')
check(read('package.json').includes('"check:android"'), 'package.json 已接线 check:android')

for (const app of APPS) {
  const prefix = app.id === 'literacy' ? '识字' : '数学'
  const index = `${app.dir}/index.html`
  const manifest = `${app.dir}/public/manifest.webmanifest`
  const capConfig = `${app.dir}/capacitor.config.json`
  const androidGradle = `${app.dir}/android/app/build.gradle`
  const androidManifest = `${app.dir}/android/app/src/main/AndroidManifest.xml`

  check(exists(manifest), `${prefix} manifest.webmanifest 存在`)
  check(exists(`${app.dir}/public/icons/icon-192.png`), `${prefix} PWA icon-192 存在`)
  check(exists(`${app.dir}/public/icons/icon-512.png`), `${prefix} PWA icon-512 存在`)
  check(/manifest\.webmanifest/i.test(read(index)), `${prefix} index.html 已链接 manifest`)
  check(exists(capConfig), `${prefix} capacitor.config.json 存在`)

  const capJson = read(capConfig)
  check(capJson.includes(`"${app.appId}"`), `${prefix} Capacitor appId=${app.appId}`)
  check(capJson.includes('"webDir": "dist"'), `${prefix} Capacitor webDir=dist`)

  check(exists(androidGradle), `${prefix} android/app/build.gradle 存在`)
  check(exists(androidManifest), `${prefix} AndroidManifest.xml 存在`)

  const manifestXml = read(androidManifest)
  check(
    manifestXml.includes('android.permission.INTERNET') ||
      manifestXml.includes('uses-permission'),
    `${prefix} Android 权限声明存在`
  )
  check(
    /VIBRATE|vibrate/i.test(manifestXml) || /VIBRATE/.test(read(`${app.dir}/android/app/src/main/AndroidManifest.xml`)),
    `${prefix} Android 震动权限（答题反馈）`
  )
}

notes.forEach((n) => console.log(' ', n))
if (fails.length) {
  console.log('')
  fails.forEach((f) => console.log(' ', f))
}
console.log(`\nAndroid 同步门禁：${notes.length} 项通过，${fails.length} 项失败。`)
process.exit(fails.length ? 1 : 0)
