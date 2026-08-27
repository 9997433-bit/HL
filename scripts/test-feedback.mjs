/**
 * shared/composables/useFeedback.js 的行为回归。
 *
 * 三条通道的降级是这个 composable 存在的理由，所以专门用一个假 DOM 把它们
 * 逐档验一遍：没有震动能力的设备、开了「减少动效」的孩子、音效实现抛错的浏览器，
 * 任何一档下「答对了」都仍然要有反馈，而且不能在页面上留下粒子层。
 */

import assert from 'node:assert/strict'

const { createFeedback, HAPTIC_PATTERNS } = await import(
  new URL('../shared/composables/useFeedback.js', import.meta.url)
)

/* ------------------------------------------------------------------ 假 DOM */

function fakeElement(tag = 'div') {
  const el = {
    tagName: tag,
    style: { cssText: '' },
    children: [],
    parentNode: null,
    animations: [],
    textContent: '',
    setAttribute() {},
    getBoundingClientRect: () => ({ left: 100, top: 80, width: 40, height: 20 }),
    appendChild(child) {
      child.parentNode = el
      el.children.push(child)
      return child
    },
    remove() {
      const list = el.parentNode?.children
      if (list) list.splice(list.indexOf(el), 1)
      el.parentNode = null
    },
    animate(keyframes, options) {
      el.animations.push({ keyframes, options })
      return { finished: Promise.resolve() }
    }
  }
  return el
}

/** 装一套刚好够 useFeedback 用的浏览器环境，返回拆装函数与探针。 */
function installDom({ reduceMotion = false, vibrate = true, animate = true, tapped = true } = {}) {
  const body = fakeElement('body')
  const timers = []
  const vibrations = []

  const document = {
    body,
    createElement: (tag) => {
      const el = fakeElement(tag)
      if (!animate) delete el.animate
      return el
    }
  }
  const window = {
    matchMedia: (query) => ({ matches: reduceMotion && query.includes('reduced-motion') }),
    setTimeout: (fn) => {
      timers.push(fn)
      return timers.length
    },
    addEventListener: () => {}
  }
  const navigator = { userActivation: { hasBeenActive: tapped } }
  if (vibrate) {
    navigator.vibrate = (pattern) => {
      vibrations.push(pattern)
      return true
    }
  }

  // Node 22 自带只读的 globalThis.navigator，只能用属性描述符盖过去
  const names = ['window', 'document', 'navigator']
  const saved = names.map((name) => [name, Object.getOwnPropertyDescriptor(globalThis, name)])
  const stubs = { window, document, navigator }
  for (const name of names) {
    Object.defineProperty(globalThis, name, {
      value: stubs[name],
      configurable: true,
      writable: true
    })
  }

  return {
    body,
    vibrations,
    /** 把 setTimeout 排的清理任务全部跑完，模拟动画播完之后的那一刻。 */
    flush: () => timers.splice(0).forEach((fn) => fn()),
    restore: () => {
      for (const [name, descriptor] of saved) {
        if (descriptor) Object.defineProperty(globalThis, name, descriptor)
        else delete globalThis[name]
      }
    }
  }
}

const run = (name, fn) => {
  try {
    fn()
    console.log(`  ✓ ${name}`)
  } catch (error) {
    console.error(`  ✗ ${name}`)
    throw error
  }
}

/* -------------------------------------------------------------------- 用例 */

console.log('[useFeedback] 共用正反馈')

run('答对：音效 / 震动 / 粒子三条通道同时到位', () => {
  const dom = installDom()
  try {
    const cues = []
    const feedback = createFeedback({ sound: { correct: (streak) => cues.push(streak) } })
    const result = feedback.correct(document.createElement('button'), { cueArg: 4 })

    assert.deepEqual(cues, [4], 'cueArg 要原样透传给音效钩子')
    assert.deepEqual(result, {
      sound: true,
      haptics: true,
      particles: true,
      motion: false,
      reducedMotion: false
    })
    assert.deepEqual(dom.vibrations, [HAPTIC_PATTERNS.correct])
    assert.equal(dom.body.children.length, 1, '粒子层挂在 body 上')
    assert.equal(dom.body.children[0].children.length, 14, '默认撒 14 颗')

    dom.flush()
    assert.equal(dom.body.children.length, 0, '动画播完粒子层必须自己收走')
  } finally {
    dom.restore()
  }
})

run('设备不支持震动：静默跳过，其余反馈照常', () => {
  const dom = installDom({ vibrate: false })
  try {
    const feedback = createFeedback({ sound: { correct: () => {} } })
    const result = feedback.correct(document.createElement('button'))
    assert.equal(result.haptics, false)
    assert.equal(result.sound, true)
    assert.equal(result.particles, true)
    dom.flush()
  } finally {
    dom.restore()
  }
})

run('页面还没被点过：不去碰 vibrate，免得浏览器报错', () => {
  const dom = installDom({ tapped: false })
  try {
    const feedback = createFeedback({ sound: { correct: () => {} } })
    const result = feedback.correct(document.createElement('button'))
    assert.equal(result.haptics, false)
    assert.deepEqual(dom.vibrations, [], '首次手势之前一次都不能调用')
    assert.equal(result.particles, true, '粒子不受手势限制')
    dom.flush()
  } finally {
    dom.restore()
  }
})

run('家长关掉震动：不再调用 navigator.vibrate', () => {
  const dom = installDom()
  try {
    const feedback = createFeedback({ sound: { correct: () => {} }, haptics: () => false })
    assert.equal(feedback.correct(document.createElement('button')).haptics, false)
    assert.deepEqual(dom.vibrations, [])
    dom.flush()
  } finally {
    dom.restore()
  }
})

run('减少动效：不撒粒子、不抖动，震动缩成一下，音效照旧', () => {
  const dom = installDom({ reduceMotion: true })
  try {
    const feedback = createFeedback({ sound: { correct: () => {}, wrong: () => {} } })
    const target = document.createElement('button')

    const right = feedback.correct(target)
    assert.equal(right.reducedMotion, true)
    assert.equal(right.particles, false)
    assert.equal(right.sound, true)
    assert.equal(dom.body.children.length, 0, '减少动效时一个粒子节点都不该建')

    const missed = feedback.wrong(target)
    assert.equal(missed.motion, false, '抖动同样要降级')
    assert.deepEqual(dom.vibrations, [[HAPTIC_PATTERNS.correct[0]], [HAPTIC_PATTERNS.wrong[0]]])
  } finally {
    dom.restore()
  }
})

run('App 自己的减少动效开关与系统偏好取并集', () => {
  const dom = installDom({ reduceMotion: false })
  try {
    let appReduced = false
    const feedback = createFeedback({ reducedMotion: () => appReduced })
    assert.equal(feedback.reducedMotion(), false)
    appReduced = true
    assert.equal(feedback.reducedMotion(), true)
    assert.equal(feedback.burst(document.createElement('div')), false)
  } finally {
    dom.restore()
  }
})

run('答错：走抖动而不是粒子', () => {
  const dom = installDom()
  try {
    const feedback = createFeedback({ sound: { wrong: () => {} } })
    const target = document.createElement('button')
    const result = feedback.wrong(target)
    assert.equal(result.motion, true)
    assert.equal(result.particles, false)
    assert.equal(target.animations.length, 1)
    assert.deepEqual(dom.vibrations, [HAPTIC_PATTERNS.wrong])
  } finally {
    dom.restore()
  }
})

run('音效实现抛错（AudioContext 未激活）不影响其余反馈', () => {
  const dom = installDom()
  try {
    const feedback = createFeedback({
      sound: {
        correct: () => {
          throw new Error('AudioContext was not allowed to start')
        }
      }
    })
    const result = feedback.correct(document.createElement('button'))
    assert.equal(result.sound, false)
    assert.equal(result.particles, true)
    assert.equal(result.haptics, true)
    dom.flush()
  } finally {
    dom.restore()
  }
})

run('浏览器没有 Web Animations API：跳过动画但绝不残留节点', () => {
  const dom = installDom({ animate: false })
  try {
    const feedback = createFeedback({ sound: { correct: () => {} } })
    feedback.correct(document.createElement('button'))
    assert.equal(dom.body.children.length, 1)
    dom.flush()
    assert.equal(dom.body.children.length, 0)
  } finally {
    dom.restore()
  }
})

run('dispose：组件卸载时把在场的粒子层一次收干净', () => {
  const dom = installDom()
  try {
    const feedback = createFeedback({})
    feedback.burst(document.createElement('div'))
    feedback.burst(document.createElement('div'))
    assert.equal(dom.body.children.length, 2)
    feedback.dispose()
    assert.equal(dom.body.children.length, 0)
  } finally {
    dom.restore()
  }
})

run('没有靶子元素也不炸：只走音效与震动', () => {
  const dom = installDom()
  try {
    const feedback = createFeedback({ sound: { tap: () => {} } })
    const result = feedback.tap(null)
    assert.equal(result.sound, true)
    assert.equal(result.particles, false)
  } finally {
    dom.restore()
  }
})

console.log('[useFeedback] 全部通过。')
