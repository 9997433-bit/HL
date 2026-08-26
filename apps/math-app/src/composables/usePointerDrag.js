import { onBeforeUnmount, reactive, ref } from 'vue'

/**
 * 指针拖拽（同时支持鼠标 / 触摸 / 触控笔）。
 * 用 Pointer Events 手写而非 HTML5 DnD，因为后者在移动端浏览器上基本不可用。
 *
 * 用法：
 *   const drag = usePointerDrag({ onDrop: (payload, zoneId) => {...} })
 *   drag.registerZone('cargo', el)
 *   <div @pointerdown="drag.start($event, payload)">
 */
export function usePointerDrag({ onDrop, onHoverChange } = {}) {
  const ghost = reactive({ active: false, x: 0, y: 0, payload: null })
  const hoveredZone = ref(null)
  const zones = new Map()

  function registerZone(id, el) {
    if (el) zones.set(id, el)
    else zones.delete(id)
  }

  function zoneAt(x, y) {
    for (const [id, el] of zones) {
      if (!el || !el.getBoundingClientRect) continue
      const r = el.getBoundingClientRect()
      if (x >= r.left && x <= r.right && y >= r.top && y <= r.bottom) return id
    }
    return null
  }

  function move(e) {
    if (!ghost.active) return
    ghost.x = e.clientX
    ghost.y = e.clientY
    const z = zoneAt(e.clientX, e.clientY)
    if (z !== hoveredZone.value) {
      hoveredZone.value = z
      onHoverChange?.(z)
    }
    e.preventDefault()
  }

  function end(e) {
    if (!ghost.active) return
    const z = zoneAt(e.clientX ?? ghost.x, e.clientY ?? ghost.y)
    const payload = ghost.payload
    stop()
    if (z && payload != null) onDrop?.(payload, z)
  }

  function stop() {
    ghost.active = false
    ghost.payload = null
    hoveredZone.value = null
    window.removeEventListener('pointermove', move)
    window.removeEventListener('pointerup', end)
    window.removeEventListener('pointercancel', stop)
  }

  function start(e, payload) {
    if (e.button != null && e.button !== 0) return
    ghost.active = true
    ghost.payload = payload
    ghost.x = e.clientX
    ghost.y = e.clientY
    window.addEventListener('pointermove', move, { passive: false })
    window.addEventListener('pointerup', end)
    window.addEventListener('pointercancel', stop)
  }

  onBeforeUnmount(stop)

  return { ghost, hoveredZone, start, stop, registerZone }
}
