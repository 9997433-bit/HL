/**
 * hanzi-writer 的获取入口。
 *
 * 早期这里是个 CDN <script> 注入器，断网就没有笔顺动画。现在库本身随包发布，
 * 笔顺数据走 utils/hanziData.js（离线优先、缺字才回退 CDN），
 * 所以这里只剩一层异步外壳，保持调用方原有的 `await loadHanziWriter()` 写法。
 */

import HanziWriterLib from 'hanzi-writer'

export function loadHanziWriter() {
  return Promise.resolve(HanziWriterLib)
}

export function isHanziWriterReady() {
  return true
}

export default HanziWriterLib
