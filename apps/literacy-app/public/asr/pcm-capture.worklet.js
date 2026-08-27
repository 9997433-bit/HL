/**
 * 跟读 v3 · 采音 AudioWorklet。
 *
 * 麦克风的每一帧只有 128 个采样点，逐帧 postMessage 会把主线程淹了；
 * 这里攒够 2048 点（16 kHz 下约 128 毫秒）再交一次，交完就换新缓冲区，
 * 避免把同一块内存交给两条线程。
 *
 * 它只搬运音频，不做判定：静音、响度、读没读完都由上层算。
 * 音频到此为止——只发给同页面的主线程，不写盘、不上传。
 */
const CHUNK = 2048

class PcmCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this.buffer = new Float32Array(CHUNK)
    this.filled = 0
    this.stopped = false
    this.port.onmessage = (event) => {
      if (event.data?.type === 'stop') this.stopped = true
    }
  }

  process(inputs) {
    if (this.stopped) return false
    const channel = inputs[0]?.[0]
    if (!channel) return true

    for (let i = 0; i < channel.length; i += 1) {
      this.buffer[this.filled] = channel[i]
      this.filled += 1
      if (this.filled === CHUNK) {
        const chunk = this.buffer
        this.buffer = new Float32Array(CHUNK)
        this.filled = 0
        this.port.postMessage({ type: 'pcm', chunk, sampleRate }, [chunk.buffer])
      }
    }
    return true
  }
}

registerProcessor('pcm-capture', PcmCaptureProcessor)
