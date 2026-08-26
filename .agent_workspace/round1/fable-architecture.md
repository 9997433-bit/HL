# HLAudio Studio — 架构规划与产品需求文档（PRD + Architecture）

| 元信息 | 值 |
|---|---|
| 文档角色 | Round 1 全局规划（架构 & PRD 主文档，后续轮次的对齐契约） |
| 作者 | fable 架构子代理（`claude-fable-5-thinking-xhigh`, bc-001f86ec） |
| 日期 | 2026-08-26 |
| 分支 | `agent/audio-analysis-software` |
| 对标产品 | Adobe Audition（2024/2025 桌面版能力集） |
| 产品代号 | **HLAudio Studio**（Python 包名 `hlaudio`，项目文件扩展名 `.hlproj`） |

---

## 0. 执行摘要

HLAudio Studio 是一款以 Adobe Audition 为对标标准的专业级音频分析与处理软件，覆盖**波形编辑（破坏性）+ 多轨混音（非破坏性）+ 频谱分析/修复 + 批处理**四大工作面。

**核心架构决策（详见 §3）：**

1. **技术栈：Python 3.11+ / PySide6（Qt6）作为 UI Shell 与业务层；NumPy/SciPy 承载 DSP；sounddevice（PortAudio，含 ASIO/WASAPI/CoreAudio）负责设备 I/O；soundfile（libsndfile）+ ffmpeg 负责编解码；pedalboard（JUCE 绑定）作为 VST3/AU 插件宿主桥。** 预留 `native/` 原生逃生舱（Rust PyO3 或 C++ pybind11），仅当 Round 2 基准测试证明 Python 混音热路径无法满足实时截止期时启用。
2. **实时性模型：音频回调线程零分配、零锁、块式（block-based）处理**；UI ↔ 引擎通过无锁 SPSC 命令环与三缓冲计量数据交换；GC 在实时会话期间冻结。
3. **数据模型：非破坏性 Session（Track/Clip/Envelope/Bus 引用源媒体）+ 破坏性 Document（copy-on-write 分块音频存储，O(1) 撤销）**，项目文件为目录式 `.hlproj`（版本化 JSON + media/ + cache/）。
4. **验收即规格：所有性能与正确性指标（§7）都定义为可机器验证的门槛**（延迟 <10ms、EBU R128 合规向量 ±0.1 LU、32 轨×4 效果实时混音等），由 gpt-sol 基准代理执行，fable 审计代理裁决。

---

## 1. 产品定义（PRD）

### 1.1 定位与对标

单机桌面应用，服务「录音后期 / 音频修复 / 播客制作 / 声音设计 / 母带与响度合规」场景。对标 Adobe Audition 的完整工作流：**Waveform 编辑器**（快速破坏性编辑 + 频谱修复）与 **Multitrack 会话**（非破坏性混音、自动化、总线路由），二者共享同一批 DSP 与分析设施。

### 1.2 目标用户与核心场景

| 用户画像 | 核心场景 | 关键能力依赖 |
|---|---|---|
| 播客/有声书剪辑师 | 剪辑、去口水音/咔哒声、响度对齐 -16 LUFS、批量导出 | 波形编辑、DeClick、响度匹配、批处理 |
| 音频修复工程师 | 频谱定点修复、降噪（噪声样本）、去嗡声、去削波 | 频谱选区编辑、NR、DeHum、DeClip |
| 混音/声音设计师 | 多轨叠放、效果器链、总线发送、自动化包络 | Multitrack、EffectsRack、Bus/Send、Automation |
| 母带/合规工程师 | True Peak/LUFS 计量、限制器、导出多格式交付 | BS.1770 计量、TP Limiter、导出矩阵 |
| 分析用户（取证/科研） | 高分辨率频谱图、相位/统计分析、标记与区域导出 | SpectralAnalyzer、Markers、CSV 导出 |

### 1.3 范围与非目标

**非目标（明确排除，防止范围蔓延）：**

- 视频编辑/预览（仅接受视频容器中的音轨抽取，经 ffmpeg）。
- **MIDI 音序/钢琴卷帘/虚拟乐器**——现代 Audition 本身已于 CS5.5 起移除 MIDI 音序功能，本项目对齐该口径；MIDI 仅保留 P2 级「控制器映射」（推子/传输控制，`mido`/`python-rtmidi`）。
- 云协作、移动端、DAW 式 MIDI 作曲。
- OMF/AAF 工程互导（P2 之后再议；以分轨 stem 导出替代）。

---

## 2. Adobe Audition 能力矩阵与对标优先级

优先级定义：**P0 = MVP 必须（Round 1–2）；P1 = Pro 必须（Round 2–3）；P2 = 增值/延后（Round 3 或后续）**。

| # | 能力域 | Audition 基准表现 | 本项目目标 | 优先级 | 承载模块 |
|---|---|---|---|---|---|
| 1 | 波形编辑（破坏性） | 剪切/复制/粘贴/裁剪、增益、淡变、静音、反相、无限撤销 | 全对齐；COW 分块存储实现 O(1) 撤销 | **P0** | Timeline(Document)/UI |
| 2 | 多轨会话（非破坏性） | 无限轨、剪辑包络、交叉淡变、punch-in/循环录音、take 管理 | ≥128 轨；剪辑增益/声像包络、自动交叉淡变；录音 P1 | **P0**(编辑)/**P1**(录音) | Timeline/AudioEngine |
| 3 | 频谱显示与选区编辑 | 频谱/音高显示，框选/套索/画笔选区，选区内独立处理与愈合 | STFT 频谱图（线性/对数/Mel），矩形+套索选区，频谱愈合画笔 | **P0**(显示)/**P1**(选区编辑) | SpectralAnalyzer/UI |
| 4 | 降噪与修复套件 | 噪声样本降噪、自适应降噪、DeHum、DeClick、DeClip、嘶声抑制、频谱修复 | 谱减+Wiener NR（噪声样本）、DeHum 谐波梳状陷波、DeClick(AR 插值)、DeClip(样条重建)；自适应 NR P1 | **P0**(NR/DeClick)/**P1**(其余) | EffectsDSP(repair) |
| 5 | 效果器与机架 | 16 槽 Effects Rack、参数 EQ、动态、混响（算法+卷积）、延迟/调制、变调变速 | 内建 ≥15 种效果 + 每轨/剪辑/总线 8 槽机架、wet/dry、旁通、预设 | **P0**(核心 8 种)/**P1**(全量) | EffectsDSP/PluginHost |
| 6 | 混音总线 | 轨→总线→主控，发送(pre/post)，自动化（read/write/latch/touch） | 任意总线图（禁环）、发送、主控链；自动化 read/write 先行，latch/touch P1 | **P0**(路由)/**P1**(自动化写入) | AudioEngine/Timeline |
| 7 | 分析与计量 | 振幅统计、频率分析窗、相位仪、响度（BS.1770/R128）、匹配响度 | 全对齐 + EBU 合规向量测试；True Peak 4× 过采样 | **P0** | SpectralAnalyzer |
| 8 | 批处理 | 收藏夹宏、批量处理器、匹配响度批任务 | 无 UI 依赖的 pipeline API + CLI + 批处理面板 | **P1** | BatchProcessor |
| 9 | 低延迟硬件 I/O | ASIO/WASAPI/MME/CoreAudio，低延迟监听 | PortAudio 全后端；RTT <10ms @48k/128 样本（ASIO/WASAPI-Excl/CoreAudio） | **P0**(播放)/**P1**(<10ms 监听验证) | AudioEngine |
| 10 | MIDI | 现代 Audition：无音序，仅控制面板类 | 控制器映射（传输/推子）；无音序 | **P2** | UI Shell |
| 11 | 标记/区域 | Cue/CD 轨标记、区域、子剪辑、导出到 BWF cue chunk | 标记/区域/子剪辑，BWF cue 读写，CSV 导出 | **P0** | Timeline/ProjectManager |
| 12 | 导入/导出格式 | WAV/BWF、AIFF、MP3、AAC、FLAC、OGG，最高 32-bit float/192kHz | libsndfile 原生（WAV/AIFF/FLAC/OGG）+ ffmpeg（MP3/AAC/视频抽轨）；内部管线 float32，44.1–192kHz | **P0**(WAV/FLAC)/**P1**(MP3/AAC) | ProjectManager(io) |
| 13 | 变速变调 | 时间伸缩、音高换挡、Remix | 相位声码器（相位锁定）+ 重采样变调；瞬态保护 P2；Remix 不做 | **P1** | EffectsDSP(timefreq) |
| 14 | 插件宿主 | VST3/AU 扫描、参数暴露、状态持久化 | pedalboard 桥：VST3/AU 加载、参数枚举、状态 blob 存入项目 | **P1** | PluginHost |
| 15 | 会话/项目文件 | `.sesx`（XML）+ 媒体引用 | `.hlproj` 目录（JSON schema 版本化）+ `.hlprojz` 单文件归档 | **P0** | ProjectManager |

---

## 3. 技术栈选型论证

### 3.1 候选方案

| 方案 | 概述 |
|---|---|
| **A. C++17/20 + JUCE** | 行业标准（Audition 自身即 C++）；JUCE 提供设备 I/O、插件宿主、UI 框架 |
| **B. Python + PySide6 + NumPy/SciPy（+ 原生逃生舱）** | 科学计算生态承载 DSP；Qt6 承载专业级 UI；热路径可下沉原生模块 |
| **C. Electron/TypeScript 前端 + Rust 后端（cpal/dasp）** | Web 技术栈 UI + Rust 实时核心，IPC 桥接 |
| **D. 纯 Rust + egui/iced** | 单语言、实时安全，UI 生态较新 |

### 3.2 决策矩阵

评分 1–5（5 最优）。权重反映本项目的特殊约束：**由多代理在 3 轮内构建，验证必须可在无头 CI 中自动化**。

| 准则 | 权重 | A. C++/JUCE | B. Python/PySide6 | C. Electron+Rust | D. 纯 Rust |
|---|---|---|---|---|---|
| 实时音频能力（<10ms） | 20% | 5 | 3（块式+原生舱→4） | 4 | 5 |
| DSP/分析算法生态 | 20% | 3 | **5**（SciPy/librosa 级生态） | 2 | 3 |
| 代理迭代速度（编辑-运行环路） | 20% | 2（编译慢、模板报错难） | **5** | 3（双语言+IPC） | 3（借用检查曲线） |
| 无头可测试性（golden test/CI） | 15% | 3 | **5**（pytest + offscreen Qt） | 3 | 4 |
| 专业 UI（波形/频谱编辑器） | 10% | 4 | 4（QPainter/QOpenGL） | 4 | 2 |
| 插件宿主（VST3/AU） | 10% | 5 | 4（pedalboard/JUCE 桥） | 2 | 2 |
| 跨平台交付 | 5% | 4 | 4 | 4 | 4 |
| **加权总分** | | **3.55** | **4.55** | **3.05** | **3.45** |

### 3.3 最终决策

**采用方案 B：Python 3.11+ / PySide6 / NumPy+SciPy / sounddevice+soundfile / pedalboard，预留原生逃生舱。**

论证要点：

1. **本项目最大风险不是峰值性能，而是「3 轮内交付可验证的宽功能面」。** Audition 的能力矩阵 80% 是编辑模型、分析算法、UI 交互与文件格式——这些在 Python 中的实现与验证速度是 C++ 的 3–5 倍，且每一项 DSP 都能直接对照 SciPy 参考实现做 null test。
2. **实时性并非 Python 不可达，而是需要正确的架构**：PortAudio 回调以块（128–256 样本）为单位进入，块内全部计算走 NumPy/SciPy 的 C 内核（`sosfilt` 带状态、向量化增益/求和），单块 Python 解释器开销可控制在 <0.3ms；48kHz/128 样本的截止期为 2.67ms。风险点是 GC 停顿与 GIL 争用，缓解见 §4.2；**若 Round 2 实测 p99 回调耗时 >50% 截止期，触发预设逃生舱**（§3.4），仅重写混音内环，接口不变。
3. **pedalboard（Spotify 开源，JUCE 内核）弥合两个关键短板**：录音室品质效果器（可与自研效果 A/B 对照）与 VST3/AU 插件宿主——这原本是选 JUCE 的最强理由。
4. **方案 A 的编译-链接-调试环路对代理极不友好**（JUCE 工程一次全量构建数分钟起），且无头 CI 验证 GUI 与设备 I/O 的成本高；方案 C 的双进程 IPC 会使波形/频谱大数据渲染复杂化；方案 D 的 UI 生态尚不足以支撑频谱套索编辑这类重交互。

### 3.4 原生逃生舱（Escape Hatch）契约

- 位置 `native/hlrt/`，Rust + PyO3（备选 C++ + pybind11）。
- **触发条件（量化）**：Round 2 基准中，@48kHz/128 样本、32 轨 × 4 效果场景，回调 p99 耗时 > 1.33ms（50% 截止期），或 10 分钟压测 underrun 率 > 0.1%。
- **替换范围仅限**：混音图执行器内环（增益/声像/求和/计量）与参数平滑；效果器仍以 C 内核（SciPy/pedalboard）形式被调用。Python 侧 `AudioGraph` 接口不变。

### 3.5 许可证审查

| 依赖 | 许可证 | 备注 |
|---|---|---|
| PySide6 | LGPL-3.0 | 动态链接合规 |
| NumPy/SciPy/soundfile/sounddevice | BSD/MIT | 无风险 |
| **pedalboard** | **GPL-3.0**（JUCE 传染） | 本项目开源可用；若未来闭源商用，需以 JUCE 商业授权重写 PluginHost 桥——已隔离在 `plugins/bridge_pedalboard.py` 单文件内 |
| ffmpeg（外部二进制） | LGPL/GPL 构建 | 以 subprocess 调用，不链接 |
| soxr-python | LGPL | 动态调用 |

---

## 4. 系统架构

### 4.1 分层与模块图

```
┌────────────────────────── UI Shell (PySide6) ──────────────────────────┐
│ MainWindow │ WaveformView │ SpectralView │ MultitrackView │ MixerView  │
│ AnalysisPanels(响度/相位/频率) │ BatchPanel │ MarkersPanel │ Transport  │
└──────┬──────────────────────────────────────────────────────┬──────────┘
       │ Commands (undoable)                                   │ Meters/tiles (三缓冲)
┌──────▼──────────────┐   ┌───────────────────┐   ┌───────────▼──────────┐
│  ProjectManager     │   │     Timeline      │   │  SpectralAnalyzer    │
│ .hlproj 序列化/撤销  │◄──┤ Session/Document  │──►│ STFT/响度/统计/音高   │
│ 媒体缓存/峰值文件     │   │ Track/Clip/包络/标记│   │ (分析线程池)          │
└──────┬──────────────┘   └────────┬──────────┘   └──────────────────────┘
       │                           │ 编译为可播放图
┌──────▼───────────────────────────▼─────────────────────────────────────┐
│                      AudioEngine (实时核心)                             │
│ Transport │ AudioGraph(轨/总线/主控) │ 参数平滑 │ SPSC 命令环 │ 磁盘流送 │
└──────┬───────────────────────────────────────────────┬─────────────────┘
       │ 逐块调用                                        │ 设备回调
┌──────▼──────────────┐  ┌──────────────────┐  ┌───────▼─────────────────┐
│    EffectsDSP       │  │   PluginHost     │  │ sounddevice / PortAudio │
│ EQ/动态/混响/修复/    │  │ 内建注册表 +      │  │ ASIO/WASAPI/CoreAudio   │
│ 变速变调 (纯函数内核) │  │ VST3/AU(pedal-   │  │ 录放双工                 │
│                     │  │ board 桥)        │  └─────────────────────────┘
└─────────────────────┘  └──────────────────┘
```

依赖方向自上而下；**EffectsDSP 与 SpectralAnalyzer 为纯函数库（无 UI、无引擎依赖），可独立测试**——这是 golden test 体系的基础。

### 4.2 线程与实时性模型

| 线程 | 职责 | 实时纪律 |
|---|---|---|
| **音频回调线程**（PortAudio 拉起） | 执行已编译的 AudioGraph：读预取环→效果链→总线求和→计量→输出 | 零分配、零锁、零文件 I/O；仅消费 SPSC 命令环与预分配缓冲；参数变更经每块平滑（10–50ms 斜坡）防 zipper noise |
| **磁盘流送线程** | 按播放头预取剪辑音频进各轨 ring buffer（目标 ≥2s 前瞻） | 与回调线程仅通过无锁环交互 |
| **分析线程池**（2–N） | 频谱瓦片、峰值文件、响度扫描、离线渲染 | 可取消任务队列；结果经 Qt 信号回 UI |
| **UI 主线程** | Qt 事件循环、绘制、命令下发 | 计量数据经三缓冲读取，60fps 节流 |

**GC/GIL 缓解**：会话启动时 `gc.freeze()` + 实时期间 `gc.disable()`（编辑操作后手动分代回收）；回调内所有数组预分配复用；NumPy/SciPy C 内核执行期间释放 GIL，UI 线程持锁窗口被压缩到微秒级。

**延迟预算（@48kHz，目标 RTT <10ms）**：输入缓冲 128（2.67ms）+ 处理 <1.33ms + 输出缓冲 128（2.67ms）+ 驱动/硬件余量 ≈ 8–9.5ms。ASIO/WASAPI 独占/CoreAudio 下可达；MME/共享模式明确不承诺。

### 4.3 关键数据流

- **播放**：Session → `GraphCompiler` 产出不可变 `CompiledGraph`（拓扑排序的节点数组 + 预分配缓冲）→ 原子指针换入回调线程（旧图由 UI 线程回收）。编辑不打断播放。
- **破坏性编辑**：UI 命令 → `Document`（COW 分块）产生新版本 → 撤销栈仅存块引用差异 → 峰值缓存增量失效。
- **频谱瓦片**：可视区变更 → 瓦片键（clip, fft_size, hop, freq_scale, tile_x）→ 缓存命中或线程池计算 STFT → QImage 瓦片 → UI 合成。
- **录音（P1）**：回调线程写输入环 → 流送线程落盘 BWF（边录边写，崩溃可恢复）→ 停止后注册为 take。

---

## 5. 模块规格

### 5.1 AudioEngine（`hlaudio/core/`）

- **Transport**：播放/暂停/定位/循环/倒带；样本精确播放头（int64 样本计数，非浮点秒）。
- **AudioGraph**：节点 = TrackSource / EffectSlot / Send / Bus / Master / Meter；编译期检环、确定执行序；支持 solo/mute/静默尾音（混响 tail flush）。
- **DeviceManager**：枚举 PortAudio 设备/后端，采样率与缓冲协商，热切换（停图→换流→重启 <200ms）。
- **命令环**：UI→RT 单生产者单消费者环形缓冲（参数变更、传输命令）；RT→UI 计量三缓冲（峰值/RMS/TP per node）。
- 验收锚点：§7-L1/L2/T1。

### 5.2 Timeline（`hlaudio/timeline/`）

- **Session**（非破坏性）：`Track(audio|bus|master) → Clip(media_ref, src_in/out, tl_start, gain, fades, stretch) → Envelope(volume/pan/param, 点列+曲线形状)`；标记/区域挂 Session 与 Clip 两级；交叉淡变为剪辑重叠区属性。
- **Document**（破坏性波形编辑器）：COW 分块存储（块 = 2^18 样本 float32），编辑操作产生新块引用表；撤销/重做 = 引用表切换，O(1)。
- 所有编辑走 **Command 对象**（`do/undo/序列化`），UI 与批处理共用同一命令层。

### 5.3 EffectsDSP（`hlaudio/dsp/`）

纯函数/无状态类内核，签名统一 `process(x: ndarray[frames, ch], sr: int, state) -> (y, state)`：

- **filters**：RBJ biquad 全族、8 段参数 EQ、10/30 段图示 EQ、HP/LP/Shelf、DC 移除。
- **dynamics**：压缩器（前馈、软拐点、lookahead）、限制器（4× 过采样 True Peak）、门限/扩展器、多段压缩（P1）、De-esser。
- **timefreq**：相位声码器变速（相位锁定）、重采样变调（soxr）、瞬态保护（P2）。
- **space**：算法混响（8×8 FDN）、卷积混响（分块 FFT，P1）、延迟/回声、合唱/镶边、立体声宽度。
- **repair**：谱减+Wiener 降噪（噪声样本）、自适应 NR（P1）、DeClick（AR 模型插值）、DeClip（三次样条重建）、DeHum（基频+谐波梳状陷波）、频谱愈合（邻域插值 inpaint，P1）。
- **规格纪律**：每个效果附带解析参考（SciPy/闭式频响）与 golden 音频对，容差写进测试（§7-D 系列）。

### 5.4 SpectralAnalyzer（`hlaudio/analysis/`）

- **STFT 服务**：窗（Hann/Blackman-Harris/Kaiser）、FFT 512–32768、重叠 50–87.5%、线性/对数/Mel 频率轴；输出量化 dB 瓦片供 UI。
- **响度**：自研 BS.1770-4（K 加权、400ms 门控、Momentary/Short-term/Integrated、LRA per EBU Tech 3342）；以 EBU Tech 3341/3342 官方合规向量为验收（±0.1 LU）。
- **统计**：峰值、True Peak（4× 过采样）、窗式 RMS、波峰因数、DC 偏移、直方图。
- **相位**：相关度计（-1..+1）、Lissajous 哥尼奥图数据。
- **频率分析窗**：实时 FFT（平均/峰保持），播放中 ≥30fps 刷新。
- **音高轮廓**：YIN/pYIN（P2）。

### 5.5 UI Shell（`hlaudio/ui/`）

- 文档-视图 + QUndoStack 桥接命令层；双工作区（Waveform / Multitrack）与 Audition 同构，Docking 面板。
- **WaveformView**：峰值金字塔（多级 min/max 抽取，`.pk` 缓存）实现任意缩放 60fps；选区/滚动/吸附。
- **SpectralView**：瓦片化 QImage 频谱图 + 矩形/套索选区叠加；亮度/范围（dB floor）调节；与波形视图垂直分屏联动。
- **MultitrackView/MixerView**：轨头（增益/声像/静音/独奏/录音备）、剪辑拖拽/裁剪/交叉淡变、总线条与发送、自动化泳道。
- 渲染策略：先 QPainter+QImage 缓存（可无头测试），QOpenGL 仅在 Round 3 性能不达标时引入。
- 全键盘快捷键表 + 主题（暗色默认）。

### 5.6 ProjectManager（`hlaudio/project/`）

- `.hlproj` 目录式项目（§6）；保存 = 原子写（临时文件 + rename）+ 滚动备份。
- 媒体策略：引用或复制入 `media/`；离线媒体重链接向导。
- 峰值/频谱/冻结渲染缓存管理与失效。
- 导入导出：libsndfile 直读 + ffmpeg 转码管线；BWF cue/bext 元数据读写；标记 CSV 导出。

### 5.7 PluginHost（`hlaudio/plugins/`）

- **内建注册表**：所有自研效果以清单注册（id、参数 schema、预设、延迟补偿采样数）。
- **外部桥**（P1）：`bridge_pedalboard.py` 加载 VST3/AU，参数枚举→统一参数模型，状态 blob base64 入项目；扫描进程隔离（崩溃插件不拖垮主程序）。
- **延迟补偿（PDC）**：图编译期收集各节点 latency，向前对齐（P1）。

### 5.8 BatchProcessor（`hlaudio/batch/`）

- Pipeline = 命令序列（与 UI 同源）+ 文件匹配器 + 导出规格；JSON 可序列化为「宏」。
- CLI 入口 `hlaudio-batch run pipeline.json --in ... --out ...`，多进程并行，进度回报；批量响度匹配为内置模板。

---

## 6. 数据模型与文件格式

### 6.1 `.hlproj` 项目布局

```
MyProject.hlproj/
├── project.json          # 唯一真相源，schema 版本化
├── media/                # 复制入项目的源音频（BWF/原格式）
├── cache/
│   ├── peaks/*.pk        # 峰值金字塔（二进制，头含源 hash）
│   ├── spectral/*.tile   # 频谱瓦片缓存（可全量重建）
│   └── freeze/*.wav      # 轨道冻结渲染
└── backups/project.json.N
```

单文件交付格式 `.hlprojz` = 上述目录 zip（不含 cache/）。

### 6.2 `project.json` schema 摘要（v1）

```jsonc
{
  "schema_version": 1,
  "session": {
    "sample_rate": 48000, "bit_depth": "float32",
    "tracks": [{
      "id": "trk_01", "kind": "audio", "name": "Vox",
      "gain_db": 0.0, "pan": 0.0, "mute": false, "solo": false,
      "output": "bus_music",                    // 或 "master"
      "sends": [{"to": "bus_verb", "gain_db": -12.0, "pre_fader": false}],
      "rack": [{"fx": "hl.eq8", "params": {...}, "bypass": false},
               {"fx": "vst3:...uid...", "state_b64": "..."}],
      "automation": [{"target": "gain_db", "mode": "read",
                       "points": [{"t": 0, "v": 0.0, "curve": "linear"}]}],
      "clips": [{
        "id": "clp_01", "media": "med_01",
        "tl_start": 480000, "src_in": 0, "src_out": 960000,   // 全部为样本整数
        "gain_db": 0.0, "fade_in": {"len": 4800, "shape": "equal_power"},
        "stretch": {"ratio": 1.0, "mode": "pv"}
      }]
    }],
    "buses": [{"id": "bus_verb", "name": "Reverb", "rack": [...], "output": "master"}],
    "master": {"rack": [...], "gain_db": 0.0}
  },
  "media": [{"id": "med_01", "path": "media/vox.wav", "sha1": "...",
              "sample_rate": 48000, "channels": 2, "frames": 2880000}],
  "markers": [{"id": "m1", "t": 96000, "dur": 0, "name": "Verse", "kind": "cue"}]
}
```

约束：**时间一律为整型样本数**（避免浮点漂移）；所有 id 稳定且不可复用；未知字段保留（前向兼容）；`schema_version` 升级须附迁移函数。

### 6.3 缓存二进制格式

- **峰值文件 `.pk`**：头（magic、源 sha1、采样率、层级数）+ 每级 min/max int8 对（每级 2× 抽取，最底层 1:256）。任何源变更→头 hash 失效→后台重建。
- **频谱瓦片**：键 =（media_id, ch, fft, hop, scale, x0）；值 = uint8 dB 量化位图；LRU 上限 512MB，可全删。

### 6.4 支持格式矩阵

| 格式 | 导入 | 导出 | 路径 |
|---|---|---|---|
| WAV/BWF（16/24/32f，含 cue/bext） | P0 | P0 | libsndfile |
| FLAC / OGG / AIFF | P0 | P0 | libsndfile |
| MP3（CBR/VBR） | P0（libsndfile≥1.1 或 ffmpeg） | P1 | lame via ffmpeg |
| AAC/M4A | P1 | P1 | ffmpeg |
| 视频容器抽轨（mp4/mov/mkv） | P1 | — | ffmpeg |
| 采样率 | 8k–192kHz（内部 float32，soxr 高质量 SRC） | 同左 | soxr |

---

## 7. 性能指标与验收标准（SLO — 验收即规格）

每条均为机器可验证门槛；「验证轮」指首次强制达标的轮次。

**延迟与实时（L/T 系列）**

| ID | 指标 | 门槛 | 测法 | 验证轮 |
|---|---|---|---|---|
| L1 | 播放输出延迟 | 缓冲 ≤128 样本 @48k 稳定运行 | 10 分钟播放 underrun 率 <0.1% | R2 |
| L2 | 监听往返延迟（RTT） | **<10ms @48k**（ASIO/WASAPI-Excl/CoreAudio） | 物理/虚拟环回脉冲测量 | R3 |
| T1 | 混音吞吐 | 32 立体声轨 × 4 效果实时，CPU <60%（4 核参考机） | 基准场景脚本 | R2 |
| T2 | 回调耗时 | p99 <50% 块周期（1.33ms @128/48k） | 回调内计时直方图 | R2（逃生舱触发器） |
| T3 | 离线渲染速度 | 典型链 ≥10× 实时 | 渲染 10 分钟素材计时 | R2 |

**正确性（D 系列）**

| ID | 指标 | 门槛 | 验证轮 |
|---|---|---|---|
| D1 | EQ 频响 | 与解析式偏差 ≤±0.1dB（20Hz–20kHz） | R1–R2 |
| D2 | 响度计 | EBU Tech 3341/3342 全部合规向量 ±0.1 LU | R2 |
| D3 | True Peak | ITU-R BS.1770-4 附录测试信号 ±0.2dB | R2 |
| D4 | 效果 golden 回归 | 全部内建效果输出与 golden 波形逐样本容差内（1e-4 rel） | R1 起持续 |
| D5 | 降噪质量 | 合成谱噪声场景 SNR 提升 ≥12dB 且语音段 PESQ 不降 | R2 |
| D6 | 无损往返 | WAV→编辑（空操作）→WAV 逐位一致；剪切/粘贴样本精确 | R1 |
| D7 | 变速变调 | 1 octave 内正弦 THD+N < -40dB；时长误差 <1 样本/分钟 | R3 |

**UI 与规模（U 系列）**

| ID | 指标 | 门槛 | 验证轮 |
|---|---|---|---|
| U1 | 打开 1 小时 48k 立体声 WAV | 波形可见 <2s（峰值后台补全） | R2 |
| U2 | 频谱图渲染 | 10s 可视窗、FFT4096：滚动 ≥30fps；UI 全局 ≥60fps | R2 |
| U3 | 实时频率分析窗 | 播放中 ≥30fps 更新 | R2 |
| U4 | 撤销深度 | ≥1000 步破坏性编辑不超过源文件 2× 磁盘占用 | R2 |
| U5 | 批处理 | 100 文件「响度匹配+导出」≥8× 实时（8 核） | R3 |

---

## 8. 目录结构建议（仓库规范）

```
hl/
├── pyproject.toml            # 单包多模块；ruff+mypy+pytest 配置
├── README.md
├── src/hlaudio/
│   ├── core/                 # AudioEngine: graph.py, transport.py, devices.py,
│   │   └── rt/               #   ringbuffer.py, triplebuffer.py, smoothing.py
│   ├── dsp/                  # filters.py, dynamics.py, space.py, timefreq.py,
│   │   └── repair/           #   nr.py, declick.py, declip.py, dehum.py, heal.py
│   ├── analysis/             # stft.py, loudness.py, stats.py, phase.py, pitch.py
│   ├── timeline/             # session.py, document.py, clip.py, envelope.py,
│   │                         # markers.py, commands.py
│   ├── project/              # store.py, schema.py, media.py, peaks.py, iomedia.py
│   ├── plugins/              # registry.py, params.py, bridge_pedalboard.py
│   ├── batch/                # pipeline.py, cli.py
│   ├── ui/                   # app.py, mainwindow.py, theme.py, shortcuts.py
│   │   ├── waveform/  spectral/  multitrack/  mixer/  panels/
│   └── util/
├── native/hlrt/              # （按需）Rust PyO3 逃生舱，接口镜像 core/rt
├── tests/
│   ├── unit/                 # 每模块镜像
│   ├── dsp_golden/           # golden 波形 + 生成脚本（golden 由脚本再生，不入库大文件）
│   ├── compliance/           # EBU/ITU 向量测试
│   └── fixtures/             # 合成信号工厂（正弦/扫频/粉噪/含损伤样本）
├── benchmarks/               # T/L/U 系列场景脚本（pytest-benchmark + 自研 RT 压测）
├── docs/
└── .agent_workspace/         # 多代理协调区（不入发行包）
```

**约定**：UI 不得 import dsp 内核以外的私有符号；dsp/analysis 禁止 import ui/core（保持纯函数可测）；全仓 `ruff` + `mypy --strict`（dsp 与 core 强制，ui 宽松）。

## 9. 依赖清单

| 依赖 | 版本下限 | 用途 | 层 |
|---|---|---|---|
| Python | 3.11 | 运行时（3.12+ 优先，实测为准） | — |
| numpy | ≥1.26（兼容 2.x） | 数组/DSP 基座 | 必须 |
| scipy | ≥1.11 | sosfilt/信号处理/FFT 参考 | 必须 |
| PySide6 | ≥6.6 | UI Shell | 必须 |
| sounddevice | ≥0.4.6 | PortAudio 设备 I/O（Windows wheel 含 ASIO） | 必须 |
| soundfile | ≥0.12 | libsndfile 编解码 | 必须 |
| soxr | ≥0.3 | 高质量重采样 | 必须 |
| pedalboard | ≥0.9 | VST3/AU 宿主 + 参考效果（GPL 注意 §3.5） | P1 |
| ffmpeg（二进制） | ≥6.0 | MP3/AAC/视频抽轨（subprocess） | P1 |
| numba | 可选 | 个别递归内核 JIT（逃生舱前的中间档） | 可选 |
| mido + python-rtmidi | 可选 | P2 控制器映射 | P2 |
| pytest / pytest-qt / pytest-benchmark / hypothesis | 最新 | 测试与性能门 | dev |
| ruff / mypy | 最新 | 静态质量 | dev |

版本以 gpt-sol 环境探针（Round 1 #6 子代理）实测锁定为 `requirements.lock` 为准。

## 10. 里程碑路线图（MVP → Pro，映射轮次）

**M0「可听可看」（Round 1，进行中）**
仓库脚手架 + 上述目录规范落地；WAV/FLAC 读写；波形视图（峰值金字塔）+ 频谱图（离线 STFT 瓦片）；破坏性编辑核心（剪/复/粘/增益/淡变/归一化 + 撤销）;sounddevice 播放；振幅统计 + 频率分析窗初版；测试骨架 + 合成 fixtures + 基准骨架。
**出口判据**：D4/D6 通过；能打开→编辑→播放→导出一个 WAV。

**M1「多轨与修复」（Round 2 前半）**
Multitrack Session + 总线/发送/主控 + 图编译器；效果机架 + 内建效果 P0 集（EQ8、压缩、限制、门限、延迟、FDN 混响、DeClick、噪声样本 NR）；自动化 read；标记/区域 + BWF cue；MP3/AAC 导入。
**出口判据**：T1/T2/D1/D2/D3/D5/U1 达标；逃生舱决策点（T2）。

**M2「专业化」（Round 2 后半 → Round 3 前半）**
频谱选区编辑 + 愈合画笔；DeClip/DeHum/自适应 NR；变速变调；卷积混响；自动化 write/latch/touch；录音（punch/loop/take）；批处理 CLI+面板；VST3 宿主 + PDC；响度匹配。
**出口判据**：U2/U3/U4/T3 达标；D7 进入测试。

**M3「Pro 验收」（Round 3）**
延迟调优实测 L2（<10ms RTT）；U5 批处理规模验证；UI 打磨（快捷键表/主题/会话恢复）；`.hlprojz` 交付格式；文档；全量 SLO 回归 + fable 审计代理终验。

## 11. Round 2 任务建议（供 Parent Orchestrator 派发）

前置：Round 1 两个 opus-fast 代理（#3 引擎+GUI 骨架、#4 频谱+DSP）与本文档并发产出，**Round 2 第一优先级是向本契约收敛**。

**opus-fast A（核心引擎线）**
1. 将 #3 产出重构对齐 §5.1/§5.2/§8：AudioGraph 编译器、SPSC 命令环、三缓冲计量、磁盘流送线程、`gc.freeze` 纪律。
2. 实现 Multitrack Session 数据模型 + 图编译 + 总线/发送路由（M1 范围），通过 T1/T2 基准。
3. 若 gpt-sol 报告 T2 超标 → 按 §3.4 契约实现 `native/hlrt` Rust 内环（接口已冻结，可直接替换）。

**opus-fast B（DSP/分析线）**
1. 将 #4 产出对齐 §5.3/§5.4：统一 `process(x, sr, state)` 内核签名，补齐 P0 效果集（EQ8/压缩/限制/门限/延迟/FDN/DeClick/噪声样本 NR）。
2. 自研 BS.1770-4 响度计 + True Peak，通过 D2/D3 合规向量。
3. 频谱瓦片服务（键控缓存 + 线程池）与频谱选区数据结构，为 M2 愈合画笔铺路。

**gpt-sol A（基准与合规线）**
1. 落地 §7 全部 SLO 为可执行基准：`benchmarks/` 场景脚本（32 轨场景生成器、回调耗时直方图、underrun 计数、U1/U2 无头帧率测量）。
2. 下载/生成 EBU Tech 3341/3342 与 ITU True Peak 合规向量，接入 `tests/compliance/`。
3. 产出 Round 2 中期性能报告（明确 T2 是否触发逃生舱），交 fable 审计裁决。

**gpt-sol B（工程化线）**
1. CI 矩阵（Linux 无头 Qt offscreen + 可选 macOS/Windows）：ruff/mypy/pytest/基准冒烟；`requirements.lock` 锁定。
2. 崩溃恢复与项目原子写的故障注入测试（kill -9 中途保存）。
3. 探针边界：PortAudio 各后端在 CI 容器内的可用性矩阵（null device 回退策略），供 L 系列测试设计。

## 12. 风险登记表

| # | 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|---|
| R1 | Python 回调 p99 超截止期（GC/GIL） | 中 | 高 | §4.2 纪律 + §3.4 量化逃生舱（接口已冻结，重写面 <500 行） |
| R2 | 并发子代理产出结构漂移 | 高 | 中 | 本文档为契约；Round 2 首任务即收敛重构；目录规范 + CI 静态检查 |
| R3 | pedalboard GPL 传染 | 低 | 中 | 桥隔离单文件；核心功能不依赖它（仅 VST3 宿主与 A/B 参照） |
| R4 | CI 无音频设备致 L 系列不可测 | 高 | 中 | 引擎支持 null/file 设备驱动；L2 留待有硬件环境或环回虚拟设备 |
| R5 | 频谱编辑（套索+愈合）交互复杂度爆炸 | 中 | 中 | M2 才启动；先矩形选区，套索/画笔增量交付 |
| R6 | 大文件内存压力（1h 192k 多轨） | 中 | 中 | 全程流式 + 分块 COW + 峰值金字塔，禁止全量载入路径进入主干 |

---

## 附录 A：关键接口草案（冻结候选，Round 2 收敛用）

```python
# dsp 内核统一签名（无 UI/引擎依赖，可独立 golden 测试）
class FxKernel(Protocol):
    def prepare(self, sr: int, max_block: int, channels: int) -> FxState: ...
    def process(self, x: np.ndarray, state: FxState) -> tuple[np.ndarray, FxState]: ...
    def latency_samples(self) -> int: ...          # PDC 用
    params: ParamSchema                             # 声明式参数（名/范围/曲线/默认）

# 引擎图（编译后不可变，原子换入回调线程）
class AudioGraph:
    @classmethod
    def compile(cls, session: Session, sr: int, block: int) -> "CompiledGraph": ...
class CompiledGraph:
    def process_block(self, io: BlockIO) -> None: ...   # RT 线程唯一入口，零分配

# 分析服务
def stft_tiles(media: MediaRef, ch: int, fft: int, hop: int,
               scale: FreqScale, x0: int, n: int) -> np.ndarray: ...   # uint8 dB 瓦片
def loudness_scan(x: BlockIter, sr: int) -> LoudnessReport: ...        # BS.1770-4

# 项目
class ProjectStore:
    def save(self, project: Project, path: Path, *, atomic: bool = True) -> None: ...
    def load(self, path: Path) -> Project: ...          # 未知字段保留

# 命令（UI/批处理共用）
class Command(Protocol):
    def do(self, ctx: EditContext) -> None: ...
    def undo(self, ctx: EditContext) -> None: ...
    def to_json(self) -> dict: ...                      # 批处理宏序列化
```

## 附录 B：参考标准与测试向量

- ITU-R BS.1770-4（响度与 True Peak 算法）；EBU R128 + Tech 3341（响度计合规向量）+ Tech 3342（LRA 向量）。
- RBJ Audio EQ Cookbook（biquad 解析频响，D1 参考）。
- EBU BWF（bext/cue chunk，标记互换）。
- 合成损伤 fixtures：削波（硬/软）、咔哒（脉冲族）、50/60Hz 嗡声+谐波、加性粉噪/风扇噪，由 `tests/fixtures/` 脚本确定性生成（固定种子），供 D5 与修复套件回归。
