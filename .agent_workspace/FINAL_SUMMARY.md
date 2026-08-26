# Audio Studio 三轮全局总结

生成日期：2026-08-26  
分支：`agent/audio-analysis-software`  
总结基线：Round 3 派发点 `6f93ab2`，加本报告、许可清单与最终同构性能回归  
版本候选：`0.1.0-alpha`

## 1. 结论

三轮交付把绿地仓库推进为一个可运行、可无头测试的单轨音频工作站
alpha：具备文件加载/导出、播放传输、波形与频谱显示、基础 DSP、响度分析、
非破坏式内核编辑、长文件流式播放、SPSC 队列、Qt 停靠面板，以及合规/性能
回归基建。

最终定位必须保持克制：当前成果是“专业音频分析与编辑底座”，不是 Adobe
Audition 的功能等价实现。多轨生产工作流、录音、工程持久化、批处理、插件宿主、
完整修复套件及真实硬件低延迟认证仍未闭环，因此只能发布 alpha，不能宣布
SOTA/Audition 级验收通过。

## 2. 架构

```text
PySide6 UI
  MainWindow / WaveformView / SpectrumPanel / EffectRack / meters
                               │ commands, views, analysis jobs
                               ▼
Qt-free core
  AudioEngine / SampleSource / EditSession / SPSC RingBuffer / transport
                               │ float32 blocks
                               ▼
DSP and analysis
  STFT/iSTFT / windows / gain / fades / EQ / BS.1770 / true peak
                               │
                               ▼
External runtime
  NumPy / SciPy / SoundFile+libsndfile / optional PyAudio+PortAudio
  FFmpeg is a discovered subprocess, not a linked or bundled library
```

关键边界：

- `audio_studio.core` 不依赖 Qt，设备/编辑/传输可以确定性单测。
- 音频以 `(frames, channels)` 的 `float32` 传递；时间以整型 sample frame 表示。
- `SampleSource.read_into` 是内存源、磁盘流式源和 `EditSession` 的统一读取面。
- feeder 与 render 通过单生产者/单消费者环传递预分配块；设备回调不做文件 I/O。
- UI 只调度分析和展示结果；频谱、响度和效果内核可脱离 GUI 验证。
- 原生 Rust/PyO3 逃生舱接口已规划，但现有代理指标未达到触发阈值，未引入双语言
  维护成本。

## 3. 三轮实现汇总

### Round 1：可听、可看、可测

- 建立 PyQt6 时代的桌面壳、音频引擎、Null/PyAudio 输出、传输、波形金字塔、
  选区、导入导出和电平表。
- 建立 STFT/iSTFT、8 种窗、频谱/瀑布数据、色图、增益/归一化/淡变/参数 EQ。
- 建立 12 个确定性 WAV fixtures、364 项应用测试、边界探针、开发容器、基准脚本
  和 Round 1 baseline。
- fable 冻结 PRD、架构边界、G1–G10 差距、SLO 与 Round 3 验收清单。

### Round 2：架构收敛与深度加固

- 从 PyQt6 迁移到 PySide6-Essentials，解除默认 GUI 栈的 GPL 分发冲突。
- 用 SPSC 环替换 mutex ring，打通 `read_into` 零额外块分配路径。
- 引入 `MemorySampleSource` / `StreamingSampleSource` 及有界解码块缓存。
- 引入 copy-on-write `EditSession`，支持 cut/paste/delete/silence/gain/fade/
  reverse/trim/insert，含 undo/redo 和播放读取协议。
- 将频谱、效果机架和响度分析接入 MainWindow；效果链支持 wet/dry、bypass 和实时
  preview。
- 实现产品侧 BS.1770 K-weighting、integrated loudness 与 LRA；True Peak
  candidate-window 优化从 Round 1 报告的约 356 ms 降到约 45 ms。
- 频谱渲染增加 reduction/colorization 两级缓存；记录首帧约 30 fps、仅换色图约
  57 fps 的中期证据。
- 增加独立 EBU oracle、null-roundtrip、SLO proxy、三平台 CI 定义、锁文件、
  性能 delta 和 realtime 逃生舱监控。

### Round 3：本子任务交付的发布准备

- 新增 `THIRD_PARTY_LICENSES.md`，覆盖所有声明的直接运行时依赖、CI 锁定传递
  依赖、关键 native/codec 组件、上游许可指针和分发义务。
- 固化 PySide6/libsndfile/soxr/FFmpeg 的 LGPL 动态替换与源码获取策略。
- 固化 pedalboard 仅可作为非默认 GPL optional path、ASIO 默认不包含、
  FFmpeg 只走 subprocess 且不得误捆 GPL full build 的裁决。
- 新增 `CHANGELOG.md`、本全局总结和 `.agent_workspace/round3/PR_BODY.md`。
- 重新运行同构 benchmark 并产出 `benchmark-final.json` 与
  `final-perf-delta.json`。

其余 Round 3 并发任务（多轨 MVP、产品计量/修复、CI/验收自动化、fable 终审）
不在 `6f93ab2` 快照内；orchestrator 合并后必须以实际 diff 和 CI 结果更新 PR
勾选项，不得用“已派发”替代“已交付”。

## 4. 测试与验证

### 已有自动化资产

- 应用层：类型不变量、加载/保存、重采样、传输状态、seek/loop、ring wrap 和
  underrun、峰值金字塔、Qt widgets、STFT/iSTFT、窗函数、效果、响度、频谱缓存。
- Round 2 引擎层：SPSC、内存/磁盘源、COW edits、深 undo/redo、并发 revision
  publication、零分配读取接口。
- 仓库层：极端 WAV 边界、WAV 16/24/32f data-chunk null test、EBU 3341/3342
  oracle、SLO proxies。
- 工程层：Linux/macOS/Windows workflow 定义、Qt offscreen tests、null-audio
  GUI smoke、performance artifact。

### 证据快照

| 证据 | 结果 | 限制 |
|---|---|---|
| Round 1 应用套件 | 364 passed | Round 1 快照 |
| Round 2 合并进度记录 | 501+ tests | 以最终 CI 重跑为准 |
| SLO/compliance 报告 | 21 passed；6/6 headless proxies pass | `formal_slos_verified = 0` |
| Golden null roundtrip | PCM_16、PCM_24、FLOAT covered | 不等于全格式/BWF/RF64 |
| 最新预 Round 3 GitHub run | [failure](https://github.com/9997433-bit/HL/actions/runs/32948286756) | PR 前必须由新的 HEAD 绿跑替代 |

当前云机没有 PySide6，因此本子任务不能把文档生成时的本地环境冒充最终 GUI
验证环境。最终 PR 的测试声明必须引用 CI 或已安装锁定依赖后的完整重跑结果。

## 5. 最终性能

命令：

```bash
python3 tools/benchmark_audio.py \
  --output .agent_workspace/round3/benchmark-final.json
python3 tools/perf-regression.py \
  .agent_workspace/round3/benchmark-final.json \
  --output .agent_workspace/round3/final-perf-delta.json
```

Round 1 与 Round 3 使用同一 Python `3.12.3`、Linux host 描述和 workload
（FFT 2048×40、load repetitions 7、buffer 512），因此
`comparison_valid: true`。

| 指标 | Round 1 | Round 3 | Delta | 判定 |
|---|---:|---:|---:|---|
| 文件加载中位数 | 0.019336 ms | 0.019287 ms | -0.25% | stable |
| 文件加载聚合 | 0.275555 ms | 0.268508 ms | -2.56% | stable |
| FFT elapsed | 0.084797 s | 0.084708 s | -0.10% | stable |
| FFT throughput | 471.715/s | 472.208/s | +0.10% | stable |
| FFT sample throughput | 966,073/s | 967,082/s | +0.10% | stable |
| Python peak allocation | 276,730 B | 276,780 B | +0.018% | stable |
| Process peak RSS | 20,021,248 B | 20,037,632 B | +0.082% | stable |
| 44.1 kHz startup estimate | 11.629059 ms | 11.629025 ms | -0.0003% | stable |
| 48 kHz startup estimate | 10.686003 ms | 10.686589 ms | +0.0055% | stable |

汇总：`regression=0`、`improvement=0`、`stable=9`、`warnings=[]`。这里的 startup
是“文件加载中位数 + 一个 512-frame 输出 buffer”的模型，不是设备 round-trip
latency。

Round 2 的独立 realtime proxy 为 48 kHz/128、32 tracks×4 effects、500 callbacks：
p99 `0.844 ms`、underrun `0%`，低于 `1.33 ms` 逃生舱阈值。该结果仍不是实际插件
图、真实驱动或 10 分钟 wall-clock soak，不触发 Rust 迁移，也不构成硬件 SLO 认证。

## 6. 许可结论

- 默认 `pip install audio-studio` 声明树不含 PyQt6/pedalboard/ASIO，G-8 的
  “默认无强 GPL”方向成立。
- PySide6、Shiboken6 与 libsndfile 按 LGPL 动态使用；安装器必须保留许可文本、
  可替换性和对应源码入口。
- pedalboard 当前未声明、未导入、未打包。未来若提供 `plugins` extra，私用安装
  不改变本仓库源码许可；与应用合并分发则整个分发件必须履行 GPL-3.0。
- FFmpeg 当前是独立进程。若未来捆绑，仅允许审过 configure flags 的 LGPL build，
  附许可和匹配源码；不得把常见 GPL/nonfree full build 放进 MIT 安装器。
- ASIO SDK 不入仓、不默认启用。用户自行设置 `SD_ENABLE_ASIO` 不等于项目提供或
  再分发 ASIO。
- `THIRD_PARTY_LICENSES.md` 已逐项映射 fable §4.4 五项要求；正式二进制发布仍需
  对每个平台的实际 wheel/native artifact 生成 SBOM 并收集随包 notices。

## 7. 主要差距

### 产品能力

1. 单轨 UI 仍不是完整多轨 session：缺 mixer、bus/send、clip timeline、automation。
2. `EditSession` 内核没有完整接入菜单、波形操作、工程保存和崩溃恢复。
3. 缺录音/input/device hot-swap 的正式工作流。
4. 缺 batch queue、响度匹配批处理和多格式交付矩阵。
5. 缺生产级 VST3/AU host、扫描隔离、state restore 和 PDC。
6. 修复/动态效果不全：DeClick/DeHum/DeClip/NR、compressor、limiter、gate 等仍需
   以实际合并后的 Round 3 代码复核。

### 正确性与规模

1. EBU 3341/3342 只覆盖部分向量；产品 meter 与独立 oracle 的全矩阵对照未完成。
2. AES17、最高质量 SRC、TPDF dither、True Peak limiter 的发布门未闭环。
3. RF64/>4 GB 全流程、1 小时频谱首屏、100 文件 batch 等正式规模 SLO 未完成。
4. Streaming playback 已有，但分析、波形、编辑、导出并非全部 out-of-core。

### 实时、平台与 UX

1. 缺真实 WASAPI/CoreAudio/ALSA 设备 RTT、30/60 分钟播放录音 soak 与 xrun 证据。
2. Python SPSC 不加 Python mutex，但 GIL/OS scheduling 仍可能制造长尾。
3. 跨平台 workflow 已定义但当前最近一次 run 为红；新 HEAD 必须全绿。
4. accessibility、HiDPI、屏幕阅读器、WCAG 对比度和完整键盘闭环未终验。
5. 缺正式安装器、签名/notarization、artifact SBOM 和逐平台 license bundle。

## 8. 后续优先级

1. 合并 Round 3 并发分支后先跑完整 CI，修复所有平台而不是跳过失败项。
2. 用独立 oracle 完成产品 M/S/I/LRA/TP 全向量；补 AES17、SRC 与 dither gates。
3. 把 `EditSession` 接入 GUI 和工程持久化，再扩展多轨 timeline/mixer/routing。
4. 在真实三平台设备执行 128-frame RTT、长时 playback/recording soak 和 xrun 采样。
5. 完成 out-of-core waveform/analysis/edit/export 与 RF64 规模验证。
6. 在插件宿主需求确定后优先评估 MIT VST3 SDK 直接路径；pedalboard 仅作为明确的
   GPL 分发变体。
7. 生成 release lock + SBOM + license bundle，再决定是否制作桌面安装器。

## 9. 发布判定

`0.1.0-alpha` 可以作为工程预览候选，前提是 orchestrator 合并全部预期 Round 3
产物、更新本报告中对应事实，并取得新的完整 CI 绿跑。若 CI 仍红，或
`THIRD_PARTY_LICENSES.md` 与最终依赖 manifest 发生漂移，则不得创建“ready for
release”PR；应保持 draft/blocked 状态。
