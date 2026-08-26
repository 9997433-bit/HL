/**
 * Canvas 舞台封装 — 高频交互玩法(点数拖拽/七巧板/数独手写/迷宫)的渲染基座。
 * 职责:DPR 适配、尺寸自适应、指针事件坐标映射、渲染循环。
 * 具体玩法在 Round 2 以 scene 对象接入:{ render(ctx, size), onPointer(type, x, y) }。
 */
export class Stage {
  constructor(canvas) {
    this.canvas = canvas
    this.ctx = canvas.getContext('2d')
    this.scene = null
    this.running = false
    this._raf = 0
    this._onResize = () => this.resize()
    this._onPointer = (e) => this._handlePointer(e)

    window.addEventListener('resize', this._onResize)
    for (const type of ['pointerdown', 'pointermove', 'pointerup']) {
      canvas.addEventListener(type, this._onPointer)
    }
    this.resize()
  }

  resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2)
    const rect = this.canvas.getBoundingClientRect()
    this.canvas.width = Math.round(rect.width * dpr)
    this.canvas.height = Math.round(rect.height * dpr)
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
    this.size = { width: rect.width, height: rect.height }
  }

  setScene(scene) {
    this.scene = scene
  }

  start() {
    if (this.running) return
    this.running = true
    const loop = () => {
      if (!this.running) return
      this.ctx.clearRect(0, 0, this.size.width, this.size.height)
      this.scene?.render?.(this.ctx, this.size)
      this._raf = requestAnimationFrame(loop)
    }
    loop()
  }

  stop() {
    this.running = false
    cancelAnimationFrame(this._raf)
  }

  _handlePointer(e) {
    if (!this.scene?.onPointer) return
    const rect = this.canvas.getBoundingClientRect()
    this.scene.onPointer(e.type, e.clientX - rect.left, e.clientY - rect.top, e)
  }

  destroy() {
    this.stop()
    window.removeEventListener('resize', this._onResize)
    for (const type of ['pointerdown', 'pointermove', 'pointerup']) {
      this.canvas.removeEventListener(type, this._onPointer)
    }
  }
}
