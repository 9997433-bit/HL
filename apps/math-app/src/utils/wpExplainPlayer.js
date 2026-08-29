/**
 * 应用题「讲解播放」时间轴（ROUND19_H4）。
 *
 * 洪恩式剖析课像一段 20–40 秒短视频；我们不塞真实 MP4，而是用程序化
 * 时间轴把「图示理解 → 分步 why」串成可播/可暂停的讲解：
 *
 *   · 每道题按 buildAnalysis 的图示 + steps 生成 cue 列表
 *   · 播放器只吃 cue（时长、旁白文案、对应步下标），不关心母题怎么拆
 *   · TTS 读 why 是增强项——SpeechSynthesis 失败就静默，时间轴照常走
 *   · reduced-motion 下不自动推进，交给面板的「再看一步」手动点
 *
 * 探针记号：`ROUND19_H4` 必须出现在可执行代码里（注释不算）。
 */

/** 可执行探针标记 —— 面板 `:data-lesson-player` 绑定它（契约见 round19-architecture §3.5）。 */
export const ROUND19_H4 = 'wp-lesson-player'

/** 图示段默认停留（毫秒）。 */
export const DIAGRAM_MS = 2800

/** 每一步默认停留（毫秒）；旁白再长也会在切 cue 时被 cancelSpeech 打断。 */
export const STEP_MS = 3200

/**
 * 把剖析数据摊成一条程序化时间轴。
 * @param {{ why?: string, diagram?: { caption?: string }, steps?: Array<{ why?: string }> }} analysis
 * @returns {Array<{ id: string, kind: 'diagram'|'step', label: string, durationMs: number, speakText: string, stepIndex: number }>}
 */
export function buildExplainTimeline(analysis) {
  const steps = Array.isArray(analysis?.steps) ? analysis.steps : []
  const cues = [
    {
      id: 'diagram',
      kind: 'diagram',
      label: '图示理解',
      durationMs: DIAGRAM_MS,
      speakText: String(analysis?.why || analysis?.diagram?.caption || '').trim(),
      /** -1 = 只亮图示，分步还没摊开 */
      stepIndex: -1,
    },
  ]
  for (let i = 0; i < steps.length; i += 1) {
    cues.push({
      id: `step-${i}`,
      kind: 'step',
      label: `第 ${i + 1} 步`,
      durationMs: STEP_MS,
      speakText: String(steps[i]?.why || '').trim(),
      stepIndex: i,
    })
  }
  return cues
}

/**
 * 0–1 进度：已播完的 cue 时长 + 当前 cue 已过时间。
 * @param {ReturnType<typeof buildExplainTimeline>} cues
 * @param {number} cueIndex
 * @param {number} cueElapsedMs
 */
export function progressOf(cues, cueIndex, cueElapsedMs = 0) {
  if (!cues.length) return 0
  const total = cues.reduce((sum, cue) => sum + cue.durationMs, 0) || 1
  let done = 0
  const capped = Math.max(0, Math.min(cueIndex, cues.length))
  for (let i = 0; i < capped; i += 1) done += cues[i].durationMs
  if (capped < cues.length) {
    done += Math.max(0, Math.min(cueElapsedMs, cues[capped].durationMs))
  }
  return Math.min(1, done / total)
}

/** 当前 cue 对应该摊开几步（diagram → 0，第 n 步 → n+1）。 */
export function shownStepsForCue(cue) {
  if (!cue || cue.stepIndex < 0) return 0
  return cue.stepIndex + 1
}
