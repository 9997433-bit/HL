#!/usr/bin/env node
/**
 * Round 19 H3 smoke probe — CharPlayStage 精美度。
 *
 * 稳定断言：舞台组件存在、六种 kind 仍可渲染、跳过/reduced-motion 底线仍在。
 *
 * 门槛断言（ROUND19_H3 可执行标记出现后才硬卡）：至少 3 类可感知升级
 *   1. 多拍节 timeline（gsap.timeline / beats / multi-beat）
 *   2. 道具命中反馈增强（hit / impact / pulse / celebrate 增强路径）
 *   3. 主题氛围层（atmosphere / ambience / theme-layer / mood）
 * 且 reduced-motion 可跳过或降级。
 *
 * 未合入前 ○ PENDING。`--require-ready` 升级为失败。
 */

import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'

const APP_ROOT = resolve(import.meta.dirname, '..')
const STAGE = resolve(APP_ROOT, 'src/components/CharPlayStage.vue')
const READY_MARKER = ['ROUND19', 'H3'].join('_')
const requireReady = process.argv.includes('--require-ready')

const stripComments = (source) =>
  source
    .replace(/<!--[\s\S]*?-->/g, '')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .replace(/^\s*\/\/.*$/gm, '')

const UPGRADE_CHECKS = [
  {
    id: 'multi-beat-timeline',
    label: '多拍节 timeline',
    // 契约：GSAP timeline（或等价）+ 拍节语义；可选 POLISH_BEATS 钩子
    test: (code) =>
      /POLISH_BEATS|data-polish-beats/i.test(code) ||
      ((/gsap\.timeline|timeline\s*\(/.test(code) || /多拍|拍节/i.test(code)) &&
        /beat|拍节|multi[- ]?beat|stagger/i.test(code)),
  },
  {
    id: 'hit-feedback',
    label: '道具命中反馈增强',
    // 现有 feedback.correct 微缩放不够；要有增强层/钩子
    test: (code) =>
      /POLISH_HIT|hitFeedback|propHit|data-polish-hit/i.test(code) ||
      (/命中|道具/.test(code) && /反馈|粒子|碎屑|描边|spark|burst|ripple|poof/i.test(code)),
  },
  {
    id: 'theme-atmosphere',
    label: '主题氛围层',
    test: (code) =>
      /POLISH_AMBIENCE|themeLayer|data-polish-ambience|play__atmosphere/i.test(code) ||
      /atmosphere|ambience|ambiance|氛围|mood|aura/i.test(code),
  },
]

export async function probePlayPolish() {
  const source = await readFile(STAGE, 'utf8')
  assert.ok(source.length > 500, 'CharPlayStage.vue looks empty')
  const code = stripComments(source)
  const ready = code.includes(READY_MARKER)

  // 稳定底线：跳过 + reduced-motion + 六种 kind
  assert.match(code, /skip|跳过/, 'CharPlayStage must keep a skip path')
  assert.match(
    code,
    /prefers-reduced-motion|reduceMotion|reduced\b/i,
    'CharPlayStage must keep a reduced-motion path',
  )
  for (const kind of ['pick', 'catch', 'assemble', 'watch', 'match', 'push']) {
    assert.match(code, new RegExp(`['"\`]${kind}['"\`]|kind\\s*===\\s*['"\`]${kind}`), `missing kind ${kind}`)
  }

  const upgrades = UPGRADE_CHECKS.map((check) => ({
    id: check.id,
    label: check.label,
    ok: check.test(code),
  }))
  const hit = upgrades.filter((row) => row.ok)

  if (!ready || hit.length < 3) {
    if (requireReady) {
      assert.ok(ready, `${READY_MARKER} marker is not available yet`)
      assert.ok(
        hit.length >= 3,
        `${READY_MARKER} needs ≥3 polish upgrades, found ${hit.length}: ${hit.map((r) => r.id).join(',') || 'none'}`,
      )
    }
    return {
      status: 'pending',
      ready,
      upgrades: hit.map((row) => row.id),
      missing: upgrades.filter((row) => !row.ok).map((row) => row.id),
      note:
        `marker=${ready}; polish upgrades ${hit.length}/3 ` +
        `(${hit.map((r) => r.id).join(',') || 'none'}); stable skip/reduced-motion/kinds passed`,
    }
  }

  assert.match(
    code,
    /prefers-reduced-motion|reduceMotion|reduced\b/i,
    'polish path must remain reduced-motion safe',
  )

  return {
    status: 'passed',
    ready,
    upgrades: hit.map((row) => row.id),
    missing: [],
    note: `CharPlayStage exposes ${hit.length} polish upgrades with reduced-motion`,
  }
}

if (import.meta.url === pathToFileURL(process.argv[1] ?? '').href) {
  const result = await probePlayPolish()
  const symbol = result.status === 'passed' ? '✓' : '○'
  console.log(
    `${symbol} ${READY_MARKER} ${result.status.toUpperCase()}: ${result.note}` +
      (result.missing?.length ? `; missing=${result.missing.join(',')}` : ''),
  )
}
