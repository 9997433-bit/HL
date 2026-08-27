# Round 3 — 架构签收报告与发布路线图（fable / claude-fable-5-thinking-xhigh）

| 元信息 | 值 |
|---|---|
| 文档角色 | Round 3 架构签收（已实现 vs 契约偏差最终态）+ v0.1.0-alpha 发布范围 + Post-MVP 路线图 |
| 作者 | fable 架构签收 & 发布路线图子代理（`claude-fable-5-thinking-xhigh`, bc-11509187） |
| 日期 | 2026-08-26 |
| 分支 | `agent/audio-analysis-software` |
| 签收基线 commit | `6f93ab2`（Round 2 全量合并 + Round 3 派发日志）；发布门槛状态复核至 `b90e0e9`（Round 3 gpt-sol CI 修复与许可清单合并后） |
| 上游文档 | R1：`fable-architecture.md`（架构契约）、`fable-sota-audit.md`（G1–G10 + 验收 checklist）；R2：`fable-convergence-audit.md`（DEV-01–18 + 冻结 API）、`fable-sota-round2-review.md`（G-1–G-8 中期门槛 + 许可裁决）、`performance-mid-report.md`、`slo-compliance-report.json` |
| 性质 | 签收裁决与发布规格。本文档不改动业务代码；随附的 README 更新见 §4 |

---

## 0. 执行摘要（签收裁决 TL;DR）

1. **架构签收：有保留通过（qualified sign-off）。** Round 1 选定的方案 B（Python 3.10+/PySide6/NumPy-SciPy/libsndfile，原生逃生舱预留）经两轮实现验证成立：本机全量 **652 + 21 项测试全绿**，单轨波形编辑器的闭环（打开 → 流式/内存播放 → COW 可撤销编辑 → 实时效果预览 → 响度/频谱分析 → 导出）已经存在——其中编辑闭环在 **API/命令层**成立并有测试覆盖，主窗口尚未暴露完整破坏性编辑菜单（保留意见 §1.5-④）。核心实时纪律（无锁 SPSC、feeder 解耦、零分配 `read_into` 读取面）落地。签收启动时 CI 在 HEAD 为红；签收过程中 Round 3 gpt-sol #5 的修复合并，**CI 三平台已转绿**（§1.1 证据更新）。
2. **Rust 逃生舱：终审不触发。** 全部实测（p99 0.844 ms / 预算 1.333 ms，利用率 31.6%；32 轨 × 4 效果 proxy 单核 48.6%；underrun 0）低于触发阈值。监控门禁（`tools/monitor-realtime.py --fail-on-trigger`）保留在库，复评条件见 §1.4。
3. **v0.1.0-alpha 可以发布，定位是「单轨波形编辑与分析工作站」而非多轨 DAW**；两个原发布阻断项（CI 转绿、`THIRD_PARTY_LICENSES.md`）已在本签收过程中由 Round 3 gpt-sol #5/#6 关闭（§2.5 门槛状态已更新）。
4. **Post-MVP 路线图**（§3）：v0.2 多轨完善 + 实时纪律收尾（关闭 DEV-02/08/09/10/15/19），v0.3 VST3 宿主（pedalboard optional extra）+ 修复套件 + 录音 + 批处理，v1.0 对齐 Round 1 SOTA 审计的全量 P0 checklist。

---

## 1. 架构签收报告

### 1.1 验证方法与证据

本签收不采信任何未经复现的完成声明。全部证据在签收基线 `6f93ab2` 上于 2026-08-26 本机（Linux x86_64, Python 3.12.3, PySide6-Essentials offscreen）复现：

| 证据 | 方法 | 结果 |
|---|---|---|
| 全量测试 | `QT_QPA_PLATFORM=offscreen pytest -q tests audio-studio/tests` | **652 passed（6.09 s）**：audio-studio 套件 632 + 根套件 20 |
| SLO/合规/golden | `pytest -q benchmarks/slo tests/compliance tests/golden` | **21 passed（1.48 s）** |
| CI 真实状态 | `gh run list` / `gh run view --log-failed` | 基线 `6f93ab2` 时 **failure**（run 32948286756：ubuntu Test 与 GUI smoke 死于 `ImportError: libEGL.so.1`——workflow 未装 Qt 系统库；macOS Test 死于 `ModuleNotFoundError: No module named 'tools'`）。**Round 3 gpt-sol #5 修复合并后转绿**：run 32949624137（commit `c908a7e`）**success** |
| 栈收敛 | `rg "PyQt6"` 全仓（含 --no-ignore） | **0 命中**；`pyproject.toml` 依赖 `PySide6-Essentials>=6.6`（LGPL），G-2 否决门通过 |
| GPL 依赖隔离 | 依赖声明审查 | 默认依赖树无 pedalboard / PyQt6 等 GPL 强传染组件（pedalboard 目前零引用，未来按裁决走 optional extra） |
| 实时/性能 | `performance-mid-report.md` + `slo-compliance-report.json` 复核 | 见 §1.4；9 项 Round 1 基线对比全部 ±10% 稳定区间 |

### 1.2 已实现清单（对照架构契约 §4/§5）

| 契约模块 | 落地形态（文件） | 已实现能力 | 签收状态 |
|---|---|---|---|
| AudioEngine（§5.1） | `core/engine.py`（≈600 行） | 传输状态机（play/pause/resume/stop/seek/loop/选区播放）、样本整型播放头（ring 补偿）、feeder 线程解耦、`set_source` 面向 `SampleSource` 编程、峰值/RMS 计量、采样率协商 + 重采样兜底 | ✅ 签收 |
| RT 基础设施（§4.2 / R2 §4.2 冻结） | `core/ring_buffer.py` | **无锁 SPSC 环**：单调递增读写计数、寻址取模 2 的幂、`read_into` 零分配 + 内建 pad、underrun 帧计数、producer/consumer 线程角色文档化 | ✅ 签收（冻结契约达成） |
| SampleSource（R2 §4.1 冻结） | `core/sample_source.py` + `core/sources.py` | 协议 + `MemorySampleSource`（=ArraySource）、`StreamingSampleSource`（=FileStreamSource，libsndfile 常开句柄块读，磁盘流式路径成立）、`open_source` 工厂；冻结名称经 `sources.py` 别名绑定 | ✅ 签收（名称绑定见 DEV-20） |
| EditSession（R2 §3 冻结） | `core/edit_session.py`（≈800 行） | COW 文档（不可变 `Chunk` + `Segment` 引用表）、**9 种可撤销命令**（Cut/Copy/Paste/Delete/Trim/InsertSilence/Silence/Gain/Fade/Reverse）、`UndoStack`（合并/clean 标记）、`EditSession` 聚合根**直接满足 SampleSource 协议**——编辑中播放无需摊平，换版本即热切换 | ✅ 签收（落位与命名偏差见 DEV-11/DEV-20） |
| EffectsDSP（§5.3） | `dsp/effects/`（base/eq/gain/fade） | `Effect` ABC（offline/streaming 一致性纪律、bypass、wet/dry）、`ParametricEQ`（RBJ 全族 biquad、sosfilt 带状态、解析频响验证）、`ThreeBandEQ`、`GainEffect`（防咔哒 ramp）、`NormalizeEffect`（peak/**true-peak**/RMS + ceiling）、`FadeEffect`（多曲线）、`EffectChain` | ✅ 签收（P0 集缺压缩/限制/门限，入 v0.2） |
| SpectralAnalyzer（§5.4） | `dsp/spectral.py`、`dsp/windows.py`、`dsp/loudness.py`、`dsp/util.py` | 校准 STFT（满幅正弦 = 0 dBFS、8 窗含 ENBW、log/linear 轴）、WOLA iSTFT **样本级精确重建**、实时频谱 + 瀑布缓冲、**产品侧 BS.1770-4 响度计**（任意采样率 K 加权系数推导、双级 gating、M/S/I/LRA）、True Peak 4× 多相过采样（60 s 归一化 356 ms → 45 ms） | ✅ 签收 |
| UI Shell（§5.5） | `ui/`（12 个模块） | MainWindow + **可停靠**频谱面板与效果机架（QDockWidget）、`EffectPreview` 实时预览插入、后台线程池积分响度 + 状态栏、WaveformView（min/max/RMS 金字塔、采样级缩放、选区/游标/削波标记）、传输条、电平表（峰值保持 + 削波锁存）、时间标尺、暗色主题、快捷键、拖放、最近文件、导出 | ✅ 签收 |
| 验证基建（G10） | `tests/`、`benchmarks/`、`tools/` | 652 项测试、EBU 3341/3342 独立 oracle（`tools/ebu_r128.py`，与产品实现**独立**——R12 自证风险已结构性解除）、WAV null test（16/24/32f SHA-256 位精确）、SLO 套件（6 proxy）、性能回归 harness（±10% 门）、逃生舱监控门禁、三平台 CI 矩阵 | ◐ 签收（CI 红，见 §1.5-①） |

**未实现（契约内、明确留给路线图）：** 多轨 Session/总线/图编译器（Round 3 opus #3 在飞）、录音路径、修复套件（DeClick/DeHum/DeClip/NR）、频谱选区编辑、VST3/AU 宿主、批处理、`.hlproj` ProjectManager、峰值 `.pk` 磁盘缓存、标记/区域、变速变调、SRC 定级与 TPDF 抖动。逐项版本归属见 §3。

### 1.3 契约偏差最终态（DEV-01–18 逐项结案 + 本轮新增 2 项）

图例：✅ 已收敛 ／ ⚖️ 裁决接受偏差（契约以此更新）／ ⏳ 遗留（列版本归属）。

| # | 偏差（R2 收敛审计） | 最终态 | 结案说明 |
|---|---|:---:|---|
| DEV-01 | PyQt6（GPL）而非 PySide6 | ✅ | 全仓零 PyQt6 引用；`PySide6-Essentials>=6.6` 入 pyproject/requirements；MIT 许可声明恢复自洽。G-2 否决门**通过** |
| DEV-02 | PyAudio 而非 sounddevice | ⏳ v0.2 | 未迁移：`PyAudioOutput` 仍是唯一硬件后端（optional extra `[audio]`）。不阻断 alpha（NullOutput 保证无设备可用），但 Windows 低延迟（WASAPI 独占）与 xrun 上报依赖 sounddevice，列 v0.2 |
| DEV-03 | 无 COW 文档/命令栈 | ✅ | `edit_session.py` 完整落地：COW 分段引用、9 命令、UndoStack；R2 冻结 §3.4 不变量（undo/redo 逐位一致、块共享、writeable=False）有测试覆盖 |
| DEV-04 | 无磁盘流式 | ✅（◐ 验证） | `StreamingSampleSource` 成立，feeder 面向协议编程。**未在真实 1 h/4 GB 文件上验证** U1/内存门槛——量尺存在、刻度未打，v0.2 收 |
| DEV-05 | 无多轨 Session | ⏳ R3 在飞 | Round 3 opus #3「多轨 Session MVP」进行中；签收以「合并 + CI 绿 + 测试全绿」为准（§2.5） |
| DEV-06 | mutex RingBuffer | ✅ | 无锁 SPSC 重写完成，单调计数 + 角色文档化，冻结契约的 hammer/环绕/零分配测试在套件内 |
| DEV-07 | 回调路径逐块分配 | ✅（残留见 DEV-19） | `read_into` 零分配读取面落地；但效果预览链引入了新的回调路径负载，单列 DEV-19 |
| DEV-08 | 计量无三缓冲 | ⏳ v0.2 | 峰值/RMS 仍由渲染回调直接发布（引用赋值原子性兜底）；三缓冲/预分配槽位未建。功能正确、纪律未达，随 EngineTelemetry 一起收 |
| DEV-09 | 块 1024、无 gc 纪律 | ⏳ v0.2 | `DEFAULT_BLOCK_SIZE` 仍 1024（21.3 ms @48 k）；全仓无 `gc.freeze/disable`。alpha 定位（非低延迟监听）下可接受，L1/L2 达标前必须关闭 |
| DEV-10 | 播放头块粒度 | ⏳ v0.2 | 无流时钟插值；游标精度 = 块周期。UI 30 Hz 轮询下可用，60 fps 游标平滑需要它 |
| DEV-11 | 包名/目录漂移 | ⚖️ + ⏳ | R2 裁决保留 `audio_studio` 包名——维持。但契约要求的模块边界（`timeline/ analysis/ project/` 子包）未建立：EditSession 落在 `core/`、响度/频谱落在 `dsp/`。v0.1 规模（≈8 k 行）下接受，v0.2 多轨落地时按边界重组 |
| DEV-12 | FxKernel 签名漂移 | ⚖️ + ⏳ | R2 折中裁决维持（Effect ABC 是正资产）；`prepare(max_block)` 与 `latency_samples()`（PDC 依据）仍未补——v0.3 插件宿主的前置项 |
| DEV-13 | 数组布局分裂 | ⚖️ | RT 路径统一 `(frames, channels)` ✓；dsp 内核保留 planar + `as_planar/restore_layout` 边界适配（有每块转置拷贝成本）。零拷贝 `process_block_fc` 适配器未建，随 v0.2 图编译器一起做 |
| DEV-14 | DSP/UI 未集成 | ✅ | 频谱/效果机架停靠面板 + `EffectPreview` + 后台响度扫描 + 状态栏全部落地 |
| DEV-15 | 无参数平滑 | ⏳ v0.2 | 引擎音量仍阶跃生效（`GainEffect` 的离线 ramp 不覆盖实时路径）；zipper noise 风险在 1024 块下听感有限，块降下来之前必须先做 |
| DEV-16 | 无 .hlproj/峰值磁盘缓存 | ⏳ v0.2 | 未开始；峰值金字塔仍每次 set_source 内存重建 |
| DEV-17 | CI 不覆盖 audio-studio | ✅ | 三平台矩阵 + GUI smoke + 性能探针覆盖两套测试；基线时 HEAD 红（ubuntu 缺 Qt 库、macOS `tools` 导入），Round 3 gpt-sol #5 修复合并后 **CI 转绿**（run 32949624137 success）。发布否决门①**已过** |
| DEV-18 | 无 THIRD_PARTY_LICENSES.md | ✅ | Round 3 gpt-sol #6 已交付：根目录 `THIRD_PARTY_LICENSES.md` + `CHANGELOG.md` + README 许可段（LGPL 动态链接义务、pedalboard/ASIO 预防性条款）。发布否决门②**已过**；与 R2 复审 §4.4 五项的逐项符合性由 Round 3 fable #1（SOTA 终审）复核 |
| **DEV-19（新）** | **EffectPreview 在设备渲染路径执行效果链** | ⏳ v0.2 | `EffectPreview` 包装 `AudioOutput`，链在设备回调线程逐块执行——与 R2 收敛注记「效果计算留在非 RT 线程（feeder 侧）」相悖。1024 块 + 轻量链下实测无 underrun，alpha 接受并在 README 限制中如实披露；v0.2 图编译器落地时移到 feeder/图执行侧 |
| **DEV-20（新）** | **冻结名称经别名绑定；RegionSource/LoopSource 未实现** | ⚖️ + ⏳ v0.2 | `sources.py` 把冻结名（ArraySource/FileStreamSource/ChunkTableSource）绑定到实现同一对象（非包装，isinstance 跨拼写成立）——**裁决：接受**，别名即契约的落地形态。`RegionSource/LoopSource` 组合器未实现，选区/循环逻辑仍在 transport 内——功能等价、结构未分解，随 v0.2 图编译器自然落位（届时 transport 的 loop/region 逻辑迁出） |

**结案统计：** 收敛 ✅ 8 项；裁决接受 ⚖️ 4 项（其中 2 项带 v0.2 尾巴）；遗留 ⏳ 8 项——全部有版本归属，无无主项。

### 1.4 Rust 逃生舱终审判定

**判定：不触发，维持 Python 实现。**

| 触发条件（架构 §3.4） | 阈值 | 实测 | 判定 |
|---|---|---|---|
| 回调 p99 @48 kHz/128, 32 轨 × 4 效果 | > 1.333 ms | **0.844 ms**（31.6% 预算） | 不触发 |
| 10 分钟压测 underrun 率 | > 0.1% | **0**（500/2000 回调两组 proxy） | 不触发 |
| 32×4 混音单核利用率（参考） | — | 48.6% | 贴近但有余量 |

判定性质说明：全部数据来自共享 vCPU 无头环境的合成 proxy（按 R2 §5.2 纪律属 `advisory`），且非 10 分钟 wall-clock soak。因此这是「**无证据支持触发**」而非「**已证明永不需要**」。复评条件维持不变并随本文档结转 v1.0 验收：真实设备实链 p99 > 1.33 ms、或 soak underrun > 0.1%、或引入 free-threading 构建（SPSC 环的 GIL 原子性论证失效，届时该环是第一个必须原生化的组件）。`native/hlrt` 接口预留（`read_into(out)` ↔ `&mut [f32]` 镜像）保持有效。

### 1.5 签收保留意见（四条，均已有归属）

1. **CI 曾为红（已解除，留痕）。** 签收启动时 652 项测试只在开发机复现过：ubuntu runner 缺 `libegl1` 等 Qt 系统库、macOS runner 根套件 `tools` 包不可导入。Round 3 gpt-sol #5 修复合并后三平台转绿（run 32949624137 success），本条解除；留痕是因为「CI 绿」曾在 Round 1 简报中被不实声明过（R2 复审 §2.3），签收必须记录验证链。
2. **SLO 全部是 headless proxy**（`formal_slos_verified: 0`）：L1/T1/T2/T3/U1/U2 的正式认证需要真实设备与真实 1 h 素材，v1.0 前完成；alpha 发布说明必须如实标注（§2.3 已含）。
3. **产品侧响度计的合规向量覆盖不全**：`dsp/loudness.py` 自带 3341 部分用例测试（case 1/2 级别）且与 oracle 实现独立，但全量 3341 cases + TP 用例 + 3342 的产品侧断言未入 CI——Round 3 opus #4「BS.1770 产品合规」在飞，其合并物按 R2 门槛 G-3 验收。
4. **编辑工作流未暴露到 UI。** `EditSession`（9 命令 + 撤销栈）在 `ui/` 下零引用：主窗口没有 Edit 菜单、编辑快捷键与 undo 桥接（R2 冻结面外的 `ui/undo_bridge.py` 未建）。编辑能力目前是「API 完备、测试覆盖、UI 不可达」——发布说明必须如实披露（§2.3-②），UI 暴露列 v0.2 首位工作包（§3）。

---

## 2. v0.1.0-alpha 发布范围

### 2.1 发布定位

**Audio Studio v0.1.0-alpha —— 单轨波形编辑与分析工作站（技术预览）。**
诚实口径：这是一个可用的破坏性波形编辑器 + 专业分析器，不是多轨 DAW，不是 Audition 替代品。发布物 = 源码 tag `v0.1.0-alpha`（pyproject 版本号已是 0.1.0）+ 本节功能清单/限制/系统要求（README Release Notes 段引用，见 §4）。不出安装器（v1.0 事项）。

### 2.2 功能清单

**文件 I/O**
- 导入：WAV/BWF、FLAC、MP3、Ogg/Vorbis、Opus、AIFF、W64、CAF、AU（libsndfile；本地缺的编码经 ffmpeg 兜底解码）；一律规范化为 float32 `(frames, channels)`。
- 导出：整段或选区（WAV/FLAC 等 libsndfile 可写格式）；空操作往返 16/24/32f **位精确**（golden test 保障）。

**播放引擎**
- 内存与磁盘流式双源（`SampleSource` 协议），feeder 线程 + 无锁 SPSC 环解耦设备回调；播放中编辑热切换。
- 传输：播放/暂停/继续/停止回卷、采样精确 seek、循环、选区限定播放；每通道峰值/RMS 计量。
- 后端：PortAudio（PyAudio）硬件输出；无硬件时自动降级为模拟时钟（GUI 与测试全功能可用）。

**编辑（可撤销，COW 无限历史；当前为 API/命令层能力，见限制②）**
- 剪切/复制/粘贴/删除/裁剪/静音选区/插入静音/增益/淡入淡出（多曲线）/反转；撤销 = 引用表切换 O(1)，历史共享存储；编辑期间源文件不被改写。

**效果与实时预览**
- 参数 EQ（RBJ 全族 biquad，解析频响验证）、三段 EQ、增益（防咔哒）、归一化（峰值/True Peak/RMS + ceiling）、淡变；效果链支持 bypass 与 wet/dry。
- 可停靠效果机架：试听（预览插入，不改样本）与提交（走可撤销命令）分离。

**分析与计量**
- 校准 STFT 频谱图（8 窗、log/linear 频率轴、满幅正弦 = 0 dBFS）、实时频谱、瀑布。
- BS.1770-4 响度计（任意采样率 K 加权、双级 gating、Momentary/Short-term/Integrated、EBU Tech 3342 LRA）、True Peak（4× 多相过采样）；后台积分响度入状态栏。
- 独立 EBU R128 oracle + 3341/3342 合规向量测试、SLO 套件、性能回归门禁随仓库交付。

**UI**
- 波形视图：min/max/RMS 金字塔任意缩放至采样级、选区/播放头/削波标记/时间格；静态波形 pixmap 缓存。
- 可停靠频谱与效果面板、传输条大时码、峰值保持电平表 + 削波锁存、暗色主题、全套快捷键、拖放打开、最近文件。
- 无头模式：`--offscreen --null-audio --exit-after N`（CI/脚本化冒烟）。

### 2.3 已知限制（发布说明原文级）

1. 单轨、单剪辑；无多轨会话、混音总线与自动化（v0.2）。
2. 编辑命令层（9 命令 + 撤销）已实现并有测试覆盖，但主窗口尚未暴露完整的破坏性编辑菜单/快捷键工作流——GUI 内可编辑面目前限于效果机架提交路径（v0.2 首位收口）。
3. 无录音路径（v0.3）。
4. 无修复套件（DeClick/DeHum/DeClip/降噪）与频谱选区编辑（v0.3）。
5. 无 VST3/AU 插件宿主；pedalboard 桥将以 optional extra 形式在 v0.3 提供（GPL 边界见许可裁决）。
6. 无项目文件（`.hlproj`）、标记/区域、批处理、峰值磁盘缓存（v0.2/v0.3）。
7. 非低延迟：默认块 1024（≈21 ms @48 kHz），无 WASAPI 独占/ASIO/CoreAudio 独占语义；播放头精度为块粒度。
8. 效果预览链在设备回调路径上执行（轻量链实测无 underrun，重链可能触发丢块）；提交效果不受影响。
9. SRC 质量未按 §4.3 定级，位深下变换无 TPDF 抖动——母带级导出请保持源采样率/浮点位深。
10. 产品响度计已过部分 EBU 3341 用例；全量合规向量认证进行中，严格合规场景请用随附 oracle（`tools/ebu_r128.py`）复核。
11. 性能 SLO 数据为无头 proxy 测量，非真实设备认证；循环回绕无交叉淡变。
12. 大文件可流式播放，但编辑历史与峰值金字塔驻内存；4 GB RF64 全流程未验证。

### 2.4 系统要求

| 项 | 要求 |
|---|---|
| Python | ≥ 3.10（验证基线 3.12） |
| 操作系统 | Windows 10+ / macOS 12+ / Linux（Ubuntu 22.04+ 验证基线；三平台 CI 认证以 tag 时 CI 绿为准） |
| 必装依赖 | `numpy>=1.24`、`scipy>=1.10`、`soundfile>=0.12.1`（自带 libsndfile）、`PySide6-Essentials>=6.6` |
| 可选：硬件输出 | `PyAudio>=0.2.13`（extra `[audio]`；需系统 PortAudio：`portaudio19-dev` / `brew install portaudio`）。缺失时自动用模拟时钟，无声但全功能 |
| 可选：扩展解码 | `ffmpeg` 二进制在 PATH（subprocess 调用，不链接） |
| Linux 无头/容器 | Qt 运行库：`libegl1 libgl1 libxkbcommon-x11-0 libdbus-1-3 libxcb-*`（清单见 audio-studio/README） |
| 内存 | 播放可流式；编辑会话按素材长度 + 历史增量驻内存，1 h 48 k 立体声编辑建议 ≥4 GB 可用内存 |
| 许可 | 项目 MIT；PySide6（LGPL-3.0）动态链接、libsndfile（LGPL-2.1+）经 wheel 动态库——义务清单以 `THIRD_PARTY_LICENSES.md`（发布门槛②）为准 |

### 2.5 发布门槛（tag `v0.1.0-alpha` 前的一票否决项）

| # | 门 | 判据 | 状态/归属 |
|---|---|---|---|
| ① | **CI 绿** | `Audio CI` 三平台矩阵 + GUI smoke + 性能探针全部 job 绿 | ✅ **已过**（Round 3 gpt-sol #5；run 32949624137 success @ `c908a7e`） |
| ② | **许可清单** | `THIRD_PARTY_LICENSES.md` 满足 R2 复审 §4.4 五项（含 LGPL 动态链接声明、pedalboard/ASIO 预防性条款、与依赖声明三方一致） | ✅ **已交付**（Round 3 gpt-sol #6；逐项符合性由 fable #1 终审复核） |
| ③ | README/Release Notes 与实现一致 | 过时限制修正 + Release Notes 段落地 | ✅ 本子代理（随本文档交付，§4） |
| ④ | 版本与 tag | pyproject `0.1.0` 确认；tag `v0.1.0-alpha` 由 orchestrator 在最新 HEAD CI 绿后打（后续合并每次重验） | orchestrator |

**范围弹性条款：** Round 3 另有两路在飞实现（opus #3 多轨 Session MVP——签收定稿时已开始向分支推送、opus #4 BS.1770 产品合规）。若在 tag 前合并且满足「CI 绿 + 全量测试绿 + 对应 R2 门槛（G-5 类比/G-3）通过」，则并入 v0.1.0-alpha 范围并同步更新 §2.2/§2.3（多轨从限制①中移除或改写为「多轨 MVP：能力边界……」）；若未合并或未达标，按本文档口径发布，不等待。**合并以验证为准，不以完成声明为准。**

---

## 3. Post-MVP 路线图

原则：每个版本有可机器验证的出口判据（映射架构 §7 SLO ID 与 R1 审计 checklist），版本间不留无主偏差。工作量刻画用「必须动的子系统 + 侵入度」，不用日历时间。

### v0.2「多轨完善」——把编辑器变成工作站的骨架

| 工作包 | 内容 | 关闭的偏差/差距 |
|---|---|---|
| 编辑工作流 UI 暴露 | 主窗口 Edit 菜单 + 编辑快捷键 + `ui/undo_bridge.py`（QUndoStack 镜像，命令本体留在 `EditSession`——R2 §3.3 纪律）；编辑后波形/峰值增量刷新 | §1.5-④、G-5 的 UI 半场 |
| 多轨数据模型 | Session（Track/Clip/Envelope/Bus/Send/Master）+ 图编译器（拓扑排序、不可变 CompiledGraph 原子换入）+ 自动化 read；在 Round 3 多轨 MVP 合并物基础上按契约 §5.2 补全 | DEV-05、G2 后半 |
| 播放源组合器 | `RegionSource/LoopSource` 落地，transport 的选区/循环逻辑迁出；循环点交叉淡变 | DEV-20 尾巴 |
| 实时纪律收尾 | sounddevice 后端（含 xrun 上报）、块 256/128 协商、`gc.freeze/disable` 纪律、引擎参数平滑（10 ms 斜坡）、播放头流时钟插值、EffectPreview 迁至 feeder/图执行侧、计量三缓冲 + 内嵌 EngineTelemetry（R2 §5.1 规格） | DEV-02/08/09/10/15/19 |
| 效果 P0 补全 | 压缩器（软拐点 lookahead）、True Peak 限制器（ISP 向量验收）、噪声门、延迟、FDN 混响；EQ 验证容差收紧至 0.05 dB | G6、M8 缺口 |
| 响度工作流 | 产品响度计过 3341 全量 + TP 用例 + 3342（承接 Round 3 opus #4）；响度归一化效果（R128/-14/-24 预设） | G3 收口、§1.5-③ |
| 项目与缓存 | `.hlproj` 目录式项目（schema v1、原子写）、峰值 `.pk` 磁盘缓存、标记/区域 + BWF cue 读写 | DEV-16、M11(标记) |
| 结构重组 | `timeline/ analysis/ project/` 子包边界按契约建立（编辑/多轨模型出 core，响度/统计出 dsp） | DEV-11 尾巴 |

**出口判据：** T1（32 轨 × 4 效果实时 CPU<60%）、T2（实链 p99 < 1.33 ms）、U1（真实 1 h 文件 <2 s 可见）、U4（1000 步撤销 ≤2× 磁盘）、G-3 全量、D1（EQ 0.05 dB）、D3（TP 限制器 ISP 向量）；`FileStreamSource` 1 h WAV 播放内存峰值 <200 MB。

### v0.3「VST3 与修复」——补上 Audition 之所以是 Audition 的部分

| 工作包 | 内容 | 关闭的偏差/差距 |
|---|---|---|
| VST3/AU 宿主 | pedalboard 桥（optional extra `[plugins]`、`bridge_pedalboard.py` 单文件隔离、运行时延迟导入）：扫描（进程隔离）、参数枚举 → 统一参数模型、状态 blob 入项目、PDC（依赖 DEV-12 尾巴：`latency_samples()` 补齐）。分发场景 GPL 义务按 R2 裁决 §4.2-A 声明 | G7、S4、DEV-12 |
| 修复套件最小闭环 | DeClick（AR 插值）、DeHum（基频 + 谐波梳状陷波）、噪声样本 NR（谱减 + Wiener）；频谱选区编辑（矩形选区衰减/删除 → iSTFT 重建——WOLA 精确重建底座已具备） | G4→S1、S2、M9 |
| 录音 | 输入流 + 录音环 + BWF 边录边写（崩溃可恢复）、take 注册 | M1 后半、C 系列录音门 |
| 批处理 | pipeline API + CLI（`EditCommand` 序列化已预留宏格式）、批量响度匹配模板 | S5、M8(响度归一) |
| SRC/抖动定级 | 按 §4.3 测量现状 → 不达标即引入 soxr；位深下变换 TPDF 抖动 | G5 |

**出口判据：** VST3 三款主流插件加载/状态恢复/PDC null test（至少 Linux+一桌面平台）；DeClick/DeHum/NR 各一条合成损伤 fixture 回归（D5：SNR +12 dB）；批处理 10 文件 → −16 LUFS → FLAC 一键；SRC 报告入库（达标或已切 soxr）；60 min 录音零丢样。

### v1.0「SOTA 对齐」——对 Round 1 审计 §7 全量验收

| 工作包 | 内容 |
|---|---|
| 全量 P0 checklist | R1 审计 M1–M13 逐项自动化/录屏证据；[P1] 允许 ≤2 项书面降级 |
| 实时终验 | 真实设备 L2（<10 ms RTT 独占后端实测）、48 k/256 回放 30 min 零 dropout soak、回调直方图 p99 <50% 预算（实链）；逃生舱按 §1.4 复评条件终审（含 free-threading 评估） |
| 规模终验 | 4 GB RF64 全流程内存 <1 GB、真实 1 h 素材 U1/U2/U5、批处理 8× 实时 |
| 修复进阶 | DeClip（样条重建）、自适应 NR、频谱愈合画笔、变速变调（D7：THD+N < −40 dB） |
| 无障碍与 UI 打磨 | 键盘完整工作流录屏、WCAG 2.2 AA 对比度表、屏幕阅读器单平台走查、UI 缩放 100–200%、HiDPI 验证、60 fps 帧时间打点 |
| 交付工程 | 桌面安装器（LGPL 重链接义务落实）、`.hlprojz` 单文件归档、崩溃恢复（kill -9 演示）、会话恢复 |

**出口判据：** R1 审计 §7 checklist P0 全过 = 允许宣布「Audition 级基线」；fable 终审出验收报告。

### 路线图外（明确不承诺）

ML 降噪/源分离、Dolby Atmos/ADM、视频预览、OMF/AAF、CLAP/LV2、MIDI 音序——维持 R1 审计 P2 口径，防隐性承诺。

---

## 4. README 变更说明（随本文档同 commit 交付）

1. **根 `README.md`**：从占位符（仅 `# HL`）扩为项目导览——指向 `audio-studio/`（产品）、`.agent_workspace/`（多代理文档链）、当前状态与发布口径一句话。
2. **`audio-studio/README.md`**：
   - 「What the MVP does」补充 Round 2 落地的编辑/效果/分析/停靠面板能力小节；
   - 「Known limitations」按 §2.3 口径重写——删除已失效条目（"no editing operations / no undo"、"RingBuffer uses a mutex"、"clip held fully in RAM" 均已过时），补充如实的新限制（无录音/修复/插件、预览链在回调路径、SRC 未定级等）；
   - 追加「Release notes — v0.1.0-alpha」段：功能清单摘要 + 限制 + 系统要求指针 + 发布门槛状态。

---

## 附：定稿后补记（同日，分支推进至 `508bf5b` 后复核）

1. **多轨 Session MVP 已合并**（opus #3，commit `edda345`）：§2.5 范围弹性条款生效——多轨能力按 fable #1 终审的补充定级（B8 重定为 partial）进入 v0.1.0-alpha 口径，§2.3 限制①相应从「无多轨会话」收窄为「多轨为 MVP 边界，混音工作流未完成」。
2. **最终 HEAD 全量复验：767 passed / 23 xfailed / 1 xpassed（6.61 s）**——较签收基线新增 115 项（多轨 + 验收自动化套件）；唯一 xpass 是验收 checklist E3（其 xfail 标记仍假定许可清单缺失，实际已落地，属良性过期标记，归验收套件维护方收口）。
3. **fable #1 SOTA 终审已出具**（`403e777`）：「Audition-class No-Go / alpha conditional Go」——与本签收 §2.1 的发布定位一致，两份文档互为印证。

*— fable（claude-fable-5-thinking-xhigh），Round 3 架构签收 & 发布路线图子代理（bc-11509187），2026-08-26。签收证据均可按 §1.1 方法复现；本文档只对已验证事实签字，在飞工作以合并后验证为准。*
