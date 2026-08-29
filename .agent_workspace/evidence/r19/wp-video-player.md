# R19 · H4 剖析「视频级」讲解播放器

> 分支 `cursor/r19-wp-video-player-9f67`（基线 `cursor/r19-orchestration-9f67`）
> 探针：可执行 `ROUND19_H4`（`wp-lesson-player`）——剥注释后仍在源码

## 一句话

应用题剖析不再只是静态摊步：`WpAnalysisPanel` 用**程序化时间轴**把「图示理解 → 分步 why」串成可播/可暂停、有进度的讲解课；可选 TTS 读 why（失败静默）。**不塞真实 MP4**。

## 交付物

| 文件 | 作用 |
|---|---|
| `apps/math-app/src/utils/wpExplainPlayer.js` | 时间轴构建 + `ROUND19_H4` + 进度/摊步纯函数 |
| `apps/math-app/src/utils/wpAnalysis.js` | 再导出 `ROUND19_H4`，与既有剖析链同入口 |
| `apps/math-app/src/components/WpAnalysisPanel.vue` | 「讲解播放」控件：播/暂停、进度条、TTS 开关、reduced-motion 手动档 |

## 时间轴怎么算「视频级」

每道题 `buildAnalysis()` 之后：

1. **cue 0 · 图示**（默认 2.8s）——只亮图示段，旁白读 headline/caption  
2. **cue 1…n · 分步**（每步默认 3.2s）——按序摊开 `step.why`，当前步高亮  
3. 播完 → 状态 `done`，步骤摊齐（判题前得数仍盖住）

进度 = 已播 cue 时长之和 ÷ 总时长；暂停保留已过时间，继续从断点走。

## 控件与数据钩子

| 钩子 | 含义 |
|---|---|
| `data-lesson-player="wp-lesson-player"` | `ROUND19_H4` 可执行绑定（架构 §3.5） |
| `data-wp-player-state` | `idle` / `playing` / `paused` / `ended` / `manual` |
| `data-wp-player-motion` | `auto` 或 `manual`（reduced-motion） |
| `data-wp-player-progress` | 0–100 |
| `data-wp-play-toggle` | 播放 / 暂停 / 继续 / 重播 |
| `data-wp-tts` | 朗读 why（关则不调用 SpeechSynthesis） |
| `data-wp-next-step` | 手动「再看一步」（减弱动效主路径） |

## reduced-motion

`reducedMotion()`（家长关动效 **或** `prefers-reduced-motion: reduce`）为真时：

- `data-wp-player-motion="manual"`，状态 `manual`
- **不出现**自动播放按钮，提示「请手动点步」
- 不建 setTimeout 推进；既有「再看一步 / 全部摊开」照旧

## TTS

走既有 `utils/speech.js` 的 `speak` / `cancelSpeech`：

- 切 cue / 暂停 / 换题 / 卸载时 cancel
- `speak` 返回 false 或抛错 → **静默**，时间轴不停

## 自检（本机）

```text
node 导入 wpExplainPlayer + wpAnalysis
  ROUND19_H4 === 'wp-lesson-player' ✓
  2 步题 → 3 cues（diagram + 2 steps）✓
  shownStepsForCue(diagram)=0，最后一步=2 ✓
  progressOf 末尾 = 1 ✓

剥注释扫描 math-app src：
  ROUND19_H4 / 播放|暂停 / 进度 / reducedMotion / speak / buildExplainTimeline ✓
  无 .mp4 / video/mp4 ✓

npm run check:round19  → H4 绿（其余门槛由并行岗交付）
```

## 与 H5 的边界

播放器只吃 `buildAnalysis` 产出的 `why` / `steps[].why`；扩写手写链（ROUND19_H5）时保持步数与 `buildAnalysis` 对齐（R18 红线），播放器无需改契约。
