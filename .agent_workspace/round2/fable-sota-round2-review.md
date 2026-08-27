# Round 2 — SOTA 差距复审与验收差距（fable / claude-fable-5-thinking-xhigh）

- **复审角色:** Round 2 子代理 #2 — SOTA 差距复审 & Round 2 验收差距（bc-0247424d）
- **复审基线 commit:** `2bd94c0`（2026-08-26，含并发 Round 2 gpt-sol 两路子代理已合并的产出；opus-fast 两路 bc-ded8025e / bc-32308bf7 在本复审冻结时尚未合并）
- **前置文档:** Round 1 `fable-sota-audit.md`（G1–G10 差距 + 30 项 Round 3 checklist，基线 `1408e58`）
- **TL;DR:**
  1. Round 1 交付属实且质量高于典型 MVP（**384 项测试本机全绿**、STFT/iSTFT 精确重建、RBJ EQ 带响应验证），但覆盖面窄：G1–G10 加权完成度约 **25%**，其中 G2（编辑核心）、G5（SRC/抖动）、G7（插件宿主）接近零。
  2. **G10（验证基建）是 Round 2 进展最大的域（≈45%）**：并发 gpt-sol 子代理已落地 BS.1770 独立 oracle、EBU 3341/3342 部分向量、WAV null test（bit 精确）、SLO 套件与三平台 CI 矩阵——但 **CI 在本复审时刻为红**（详见 §2.3），Round 1 简报中「CI workflow ✅」的声明经查从未成立。
  3. **许可格局已发生实质变化：** Steinberg 于 2025-10 将 VST3 SDK（3.8+）改为 **MIT**、ASIO 改为 **GPLv3/专有双许可**——Round 1 审计的 R2 风险需按 §4 裁决更新。同时发现一个 Round 1 未识别的**新许可缺陷：实现层使用 PyQt6（GPLv3/商业双许可）而 pyproject 声明 MIT**，两者在分发场景下不自洽，且 PyQt6 已扩散进 CI 依赖锁。
  4. §5 给出 Round 2 结束时的 **8 条可量化中期验收门槛**（含 4 条一票否决）。

---

## 1. 复审方法与证据链

本复审不采信任何未经复现的声明。证据获取方式：

| 证据 | 方法 | 结果 |
|------|------|------|
| 测试声明核实 | 本机安装依赖（含 Qt 系统库）后运行 `QT_QPA_PLATFORM=offscreen pytest -q tests audio-studio/tests` | **384 passed（2.13s）**；其中 audio-studio 套件单独 364 passed（与 Round 1 声明一致） |
| SLO/合规套件 | `pytest -q benchmarks/slo tests/compliance tests/golden` | **21 passed（1.56s）** |
| CI 真实状态 | `gh run list` / `gh run view --log-failed` 逐个核查 Round 1 与 HEAD 的 workflow run | Round 1 全部 **failure**；HEAD（run 32945491524）**failure**（§2.3） |
| 代码审查 | 通读 `audio-studio/`（≈5.9k 行实现 + 3.6k 行测试）、`tools/`、`benchmarks/`、`tests/` | 逐差距证据见 §2 |
| 许可事实 | Web 核实（Steinberg VST3 Developer Portal、steinbergmedia/vst3sdk、pedalboard 官方 license 页、python-sounddevice 文档，检索日 2026-08-26） | §4 |

---

## 2. G1–G10 完成度复审

### 2.1 逐项评估

完成度以 Round 1 审计 §3/§4 的 Round 3 P0 验收线为 100% 基准。

| # | 差距域 | 完成度 | 已交付证据 | 剩余差距（决定性缺口） |
|---|--------|-------:|-----------|----------------------|
| G1 | 实时音频引擎 | **25%** | `AudioEngine`（480 行）：feeder 线程 + RingBuffer 解耦回调、ring 补偿播放头、峰值/RMS 计量、PortAudio/Null 双后端、设备拒绝采样率时自动重采样兜底；引擎层零 Qt 依赖 | RingBuffer 仍为 mutex（文档自认）；无录音路径；剪辑全量驻内存、无磁盘流式；回调纪律仅有合成 proxy 测量（p99 0.844ms/预算 31.6%），产品级回调链未测 |
| G2 | 非破坏编辑核心 | **5%** | `TimeRange` 选区 + 选区导出；README 明确自认「无编辑操作、无 undo」 | 剪切/粘贴/裁剪全缺、无命令栈/undo、无分段引用模型——**Audition 核心工作流仍不存在**（Round 2 opus bc-ded8025e 在做，未合并） |
| G3 | BS.1770/R128 计量链 | **35%** | ①产品侧：`true_peak_level` 4× 过采样（BS.1770 惯例）；②R2 新增：`tools/ebu_r128.py` 独立 oracle（任意采样率 K 加权系数推导、双级 gating、M/S/I、Tech 3342 LRA）+ 3341 cases 1–3（±0.1LU 全过）+ 3342 case 1（±1LU 过） | **产品内响度表不存在**（oracle 自身声明 `product_compliance_claimed: false`）；3341 True Peak 用例（cases 15+）未覆盖；无响度归一化效果；M/S 实时表未接 UI |
| G4 | 频谱视图与 STFT 编辑 | **40%** | `SpectralAnalyzer`：校准 STFT（满幅正弦=0dBFS）、WOLA iSTFT **样本级精确重建**（含破坏 COLA 的 hop 测试）、8 窗函数含 ENBW 校准、流式帧迭代；`SpectrogramWidget`（596 行）+ 色图（含色盲安全）+ 瀑布缓冲 | 频谱模块**未接入 MainWindow**（PROGRESS 自认）；无频谱选区编辑（S1 的 STFT 修改→重建链路未开工）；渲染实测 14fps，无瓦片化 |
| G5 | 高质量 SRC 与抖动 | **10%** | `loader.resample`：scipy `resample_poly`（gcd 化简的多相实现） | 未按 §4.3 测量（阻带/通带/THD+N 全无数据）；无 soxr 级依赖决策；**位深下变换无 TPDF 抖动**（`save_audio` 默认 PCM_24 直接重量化）；44.1↔48 质量未验证 |
| G6 | 专业效果链 | **30%** | Gain（防咔哒 ramp）、Normalize（peak/**true-peak**/RMS + ceiling）、Fade（多曲线）、`ParametricEQ`（RBJ 全族 biquad、sosfilt 带状态流式=离线一致性 1e-9、频响解析曲线）；测试以 ±0.1–0.2dB 容差验证响应 | 无压缩器/限幅器/噪声门（M8 缺半）；EQ 验证容差 0.1–0.2dB，**未达验收线 0.05dB**；True Peak 归一化性能 356ms/60s（Round 2 opus bc-32308bf7 在做）；无响度归一化（依赖 G3） |
| G7 | VST3/AU 插件宿主 | **5%** | 零代码。本复审完成许可裁决（§4）——**法务前置障碍已清除**，架构文档的 pedalboard 桥方案已有隔离设计 | 全部实现工作量仍在；给 5% 仅计许可决策与桥设计 |
| G8 | 跨平台音频后端 | **20%** | `AudioOutput` 抽象 + PyAudio(PortAudio)/Null 实现、无硬件时透明降级（CI 可用）、块回调协议清晰 | 无 WASAPI 独占/CoreAudio/ALSA 语义处理（独占模式、热插拔、采样率协商）；无输入（录音）流；三平台仅 CI 骨架、无设备实测 |
| G9 | 专业 UI 体系 | **25%** | MainWindow（430 行）：轨道面板/传输条/电平表（峰值保持+削波锁存）/时间标尺；WaveformView（568 行）：多分辨率 min/max/RMS 金字塔、采样级缩放、选区/播放头/削波标记；暗色主题、快捷键、拖放、最近文件 | 无停靠面板/工作区（M12 核心）；频谱视图未集成；无 HiDPI 验证、无 60fps 帧时间打点、无无障碍走查；PyQt6/PySide6 漂移未收敛 |
| G10 | 验证基建 | **45%** | R1：364 测试、12 fixtures、基准脚本+baseline JSON；**R2 新增**：三平台 CI 矩阵 + GUI 冒烟 + 性能探针 job、EBU oracle + 3341/3342 部分向量、**WAV null test（16/24/32f，SHA-256 位精确 + 变异侦测自检）**、SLO 套件（6 项 proxy）、性能回归 harness（±10% 门）、`monitor-realtime.py --fail-on-trigger` 逃生舱门禁 | **CI 当前为红**（§2.3）；3341 TP 用例与 cases 4–9 缺；AES17 THD+N 测量脚本缺；SLO 全部是 headless proxy（`formal_slos_verified: 0`）；EQ 扫频回归未入 CI |

### 2.2 总体判定

按 Round 1 审计的验收风险权重（G1/G2/G3/G10 各 15%，G4/G6 各 10%，G5/G8/G9 各 8%，G7 6%）：

**加权完成度 ≈ 25%。**

结构性结论：Round 1+2（至冻结点）的投入呈「分析/验证强、编辑/工作流弱」的偏态——频谱分析与验证基建已接近专业底座，但 **Audition 之所以是 Audition 的部分（非破坏编辑、修复、插件、多轨）仍为 0–5%**。Round 2 剩余时间与 Round 3 必须把重心压到 G2/G3(产品侧)/G5/G6 下半场，否则最终交付将是「优秀的音频分析器 + 播放器」，而非音频工作站。

### 2.3 对 Round 1 简报声明的更正（审计留痕）

| PROGRESS.md 声明 | 核查结果 |
|------------------|---------|
| 「364 tests 全绿」 | **属实**（本机复现 2.07s；合并 R2 产出后 384+21 全绿） |
| 「测试基建 … CI workflow ✅」 | **不成立**。Round 1 期间 CI 从未绿过：runs 32943431132/32943467676/32943500638 全部 failure（`ModuleNotFoundError: No module named 'tools'`——workflow 在 repo 根跑 pytest 却未装包/未设 rootdir） |
| （R2 新 CI）三平台矩阵 | 已落地但 **HEAD 仍红**（run 32945491524）：ubuntu/windows 的 Test job 死于 pytest-qt 导入 QtGui（ubuntu runner 缺 `libegl1` 等 Qt 系统库——与本机复现路径一致，装库后即绿）；GUI smoke 同因失败；performance-probes 独绿 |

CI 红的根因是 runner 环境配置而非代码缺陷（本机同环境修复后 384 项全过），修复量小——但**「CI 绿」是一切质量声明的前提**，列为 §5 一票否决门。

---

## 3. Round 3 Checklist 更新（30 项 + 新增 2 项）

图例：✗ 未开始 ／ ◐ 部分 ／ ✓ 已达成（有自动化证据）。**【R2】= Round 2 结束前必须关闭**（进入 §5 门槛）。

### A. 合规与精度

| 状态 | 项目 | 复审备注 |
|:---:|------|---------|
| ◐ 【R2】 | [P0] EBU 3341 响度 ≤±0.1LU；TP 用例 +0.2/−0.4dB | oracle 对 cases 1–3 已过且入测试；**R2 须扩至 cases 1–6 + 至少 2 个 TP 用例并入 CI** |
| ◐ | [P0] 3342 LRA ≤±1LU | case 1 已过；R2 保持，R3 补齐全部 cases |
| ✓ 【R2】 | [P0] Null test 16/24/32f bit 精确 | `tests/golden/test_null_roundtrip.py` 已达成（fmt 字段+data chunk SHA-256）；R2 义务=保持 CI 绿 |
| ◐ 【R2】 | [P0] EQ 幅频 vs 解析解 <0.05dB | 现有测试容差 0.1–0.2dB；**R2 须收紧至 0.05dB 并做 20Hz–20kHz 扫频回归** |
| ✗ | [P0] SRC 96k→44.1k 镜像 <−120dBFS、THD+N <−130dBFS | 无测量。**R2 至少交付测量脚本与现状数据**（达标与否是 R3 的事，先有尺子） |
| ✗ | [P0] True Peak 限幅器 ISP 向量 | 限幅器不存在 |
| ✗ | [P1] TPDF 抖动频谱验证 | 抖动不存在（且 `save_audio` 默认 PCM_24 无抖动重量化，风险已在 §2.1 G5 记录） |
| ✗ | [P1] AES17 THD+N 测量脚本 | 未开始 |

### B. 功能完备

| 状态 | 项目 | 复审备注 |
|:---:|------|---------|
| ◐ | [P0] M1–M13 逐项演示 | 现状约 M3◐/M4◐/M5◐/M7◐/M12◐，其余 ✗ |
| ◐ | [P0] 1h 文件打开<3s/频谱首屏<2s/离线处理<30s | 仅 1min 级 proxy 数据；R3 用真实 1h 文件测 |
| ✗ | [P0] 4GB RF64 流式、内存<1GB | 全内存架构，依赖 G2 重构 |
| ✗ 【R2】 | [P0] undo/redo 100 步自动化 | **R2 门槛**（bc-ded8025e 在做）：至少 cut/copy/paste/trim/silence + 100 步 undo 的自动化测试 |
| ✗ | [P1] 频谱选区衰减/DeClick/DeHum 演示 | iSTFT 底座已备（G4 40% 中最有价值的部分），R3 实现 |
| ✗ | [P1] VST3 宿主 3 插件 + PDC null test | 许可已裁决（§4），R3 实现 |
| ✗ | [P1] 批处理 10 文件→−16LUFS→FLAC | 依赖产品侧 R128 |
| ✗ | [P1] 多轨 32 轨 + 包络 + 总线 | 未开始 |

### C. 实时与稳定

| 状态 | 项目 | 复审备注 |
|:---:|------|---------|
| ◐ | [P0] 48k/256 回放 30min 零 dropout | proxy：2000 回调 0 underrun；**真实设备 soak 留 R3**（云端无声卡，标注 degraded） |
| ✗ | [P0] 60min 录音零丢样 | 录音路径不存在 |
| ◐ 【R2】 | [P0] 回调 p99 <50% 预算 + 零分配/零锁审查 | monitor-realtime 门禁已备；**R2 须测产品 render 路径（EQ+gain 实链）而非合成循环**，并出直方图工件 |
| ✗ | [P1] 往返延迟实测 <15ms@128 | 需硬件 |

### D. UI/UX 与无障碍

| 状态 | 项目 | 复审备注 |
|:---:|------|---------|
| ◐ | [P0] 60fps 表头/HiDPI/暗色默认 | 暗色✓；帧时间打点与 HiDPI 验证 ✗ |
| ✗ | [P0] 停靠面板 + 两套工作区 | 未开始；**R2 至少完成频谱视图停靠集成**（bc-32308bf7 范围） |
| ◐ | [P0] 键盘完整工作流 | 传输/缩放/选区快捷键 ✓；编辑操作待 G2 |
| ✗ | [P1] WCAG AA / 屏幕阅读器 / 色盲安全 | 色盲安全色图已有（colormaps.py），其余未开始 |
| ✗ | [P1] UI 缩放 100–200% | 未验证 |

### E. 跨平台与工程质量

| 状态 | 项目 | 复审备注 |
|:---:|------|---------|
| ◐ 【R2】 | [P0] 三平台 CI 全绿 | 矩阵已建，**当前红**——R2 一票否决门（§5 G-1） |
| ✗ | [P0] DSP golden 三平台一致 ≤1e-9 | 矩阵绿后在三平台跑同一 golden 断言即得，R2 顺手可收 |
| ✗ 【R2】 | [P0] THIRD_PARTY_LICENSES.md 完整自洽 | **R2 门槛**，按 §4.4 清单落地 |
| ✗ | [P1] 崩溃恢复演示 | 未开始 |

### 新增项（本复审追加，计入 Round 3 验收）

| 状态 | 项目 | 理由 |
|:---:|------|------|
| ✗ 【R2】 | **[P0] E5 栈收敛：仓库内唯一 Qt 绑定为 PySide6** | PyQt6 与项目 MIT 声明在分发场景冲突（§4.2-B），且已扩散至 `.github/requirements.lock`；越晚切换成本越高（当前 9 个 UI 文件、量级为 import 行与少量枚举差异） |
| ✗ | [P1] E6 产品侧 R128 表（M/S/I/LRA/TP）与 oracle 在 3341 全用例偏差 ≤0.05LU | oracle 只是尺子；产品必须自己达标。R3 验收时 oracle 与产品实现必须**独立**（不共享滤波器代码），否则合规验证是自证 |

---

## 4. 许可合规裁决文档

> 本节为正式裁决（供 orchestrator 与实现子代理直接执行）。事实核查日 2026-08-26；来源：Steinberg VST3 Developer Portal / steinbergmedia GitHub、spotify/pedalboard 官方 license 页、python-sounddevice 官方文档。

### 4.1 事实基础更新（相对 Round 1 审计 R2 风险）

1. **VST3 SDK：自 3.8 版（2025-10-20）起 MIT 许可。** GPLv3/Steinberg 专有双许可模式**已不再提供**。商业/闭源/开源集成均无需协议签署，仅需保留版权与许可文本；Steinberg 商标/logo 使用另循商标指引（可选）。→ Round 1 审计「VST3 走 GPLv3 则整项目须兼容」的约束**对直接使用 SDK 的路径已失效**。
2. **ASIO SDK：自 2025-10 起 GPLv3/专有双许可**（此前纯专有）。专有路径仍要求 Steinberg 签署书面协议且 SDK 不得再分发；GPLv3 路径允许再分发但传染整个组合作品。
3. **pedalboard（Spotify）：仍为 GPLv3，且不受 VST3 SDK 转 MIT 影响**——其 GPL 属性主要来自静态编入的 JUCE 6（GPL/商业双许可）、Rubber Band（GPLv2+/商业）与 FFTW（GPLv2+），VST3 SDK 只是其中一项。
4. **python-sounddevice：MIT；自 0.5.0 起 Windows wheel 默认 DLL 不含 ASIO**，0.5.1+ 同时附带 ASIO 构建的 PortAudio DLL，仅当用户设置环境变量 `SD_ENABLE_ASIO` 时加载。
5. **本仓库新事实：实现层使用 PyQt6**（Riverbank，GPLv3/商业双许可），而 `audio-studio/pyproject.toml` 声明 `license = MIT`，且 PyQt6 已进入 `.github/requirements.lock`。架构文档（fable-architecture.md §3.5）选定的是 PySide6（LGPL-3.0）。

### 4.2 分发策略裁决

| # | 组件 | 许可 | **裁决** |
|---|------|------|---------|
| A | **VST3 宿主（经 pedalboard）** | pedalboard GPLv3（JUCE6+RubberBand+FFTW 静态编入） | **pedalboard 不得进入默认依赖**。作为 optional extra（`pip install audio-studio[plugins]`）+ 运行时延迟导入 + 单文件桥（架构文档 `bridge_pedalboard.py` 隔离设计维持）。核心应用不 import 它即不受传染；**一旦随应用一同分发（含打包进安装器），该分发件整体须按 GPLv3 提供**——届时在安装器内单独声明。长期（P2）：VST3 SDK 已 MIT，原生逃生舱（C++/Rust）可自建 MIT 路径宿主，彻底摆脱 GPL；Round 2/3 不投入 |
| B | **Qt 绑定（当前 PyQt6）** | PyQt6：GPLv3/商业；PySide6：LGPL-3.0 | **裁决：Round 2 收敛到 PySide6（一票否决门 §5 G-2）。** 现状「MIT 项目 + PyQt6 依赖」在源码仓库阶段勉强成立（PyQt6 未被再分发），但任何二进制分发/wheel 捆绑场景立即不成立——要么全项目转 GPLv3，要么买 Riverbank 商业许可。PySide6 走 LGPL 动态链接：义务=附许可文本+保证 Qt 库可替换（wheel 共享库天然满足；打包时禁止静态冻结 Qt） |
| C | **ASIO** | GPLv3/专有（Steinberg 签署） | **默认不做 ASIO，维持 Round 1 裁决**：Windows 低延迟走 WASAPI 独占。允许文档化的用户侧 opt-in：sounddevice≥0.5.1 自带 ASIO DLL，由**用户自行**设置 `SD_ENABLE_ASIO`——本项目不默认设置该变量、不在仓库引入任何 ASIO SDK 代码、不在营销面宣称 ASIO 支持。若未来正式支持：GPLv3 路径 → 全项目转 GPL（与裁决 B 冲突，不选）；专有路径 → 与 Steinberg 签署协议（P2，商业化时再议） |
| D | **ffmpeg** | LGPL-2.1+ 核心；`--enable-gpl` 构建含 GPL 组件（x264 等） | **仅以 subprocess 调用独立二进制**（现状 `loader.py` 已如此，合规✓），**不链接、不默认捆绑**：运行时 `shutil.which` 发现 + About 框如实报告（现状✓）。若 Round 3 安装器决定捆绑：只捆绑 **LGPL 构建**（无 x264/x265），附 ffmpeg 许可文本 + 对应源码的书面获取指引；备选=首次运行引导用户自装（Windows `winget`，macOS `brew`）。**禁止**捆绑常见的 GPL 全家桶构建（gyan.dev full 等）除非全项目按 GPL 分发 |
| E | **libsndfile（经 soundfile wheel 捆绑）** | LGPL-2.1+（wrapper 本身 BSD/MIT 系） | **允许，义务轻**：动态库形式满足 LGPL 重链接要求；在 THIRD_PARTY_LICENSES.md 收录许可文本与源码指引。MP3 经 libsndfile≥1.1（LAME/mpg123，LGPL；MP3 专利 2017 已过期）→ MP3 读写**放行**，Round 1 审计 R9 中 MP3 顾虑撤销。AAC 维持「仅系统编码器」裁决不变 |
| F | 其余运行时 | numpy/scipy（BSD）、soundfile wrapper（BSD）、PortAudio（MIT 式）、PyAudio（MIT）、sounddevice（MIT）、soxr/python-soxr（LGPL-2.1，拟引入，同 E 处理） | 无风险；一并入清单 |

### 4.3 分发场景义务矩阵

| 场景 | 义务 |
|------|------|
| ①源码仓库（现状） | pyproject 许可声明与依赖自洽（当前**不自洽**，见 B）；THIRD_PARTY_LICENSES.md 入库 |
| ②PyPI wheel | 不捆绑 Qt/ffmpeg 二进制 → 依赖声明即可；pedalboard 只出现在 extras |
| ③桌面安装器（R3） | PySide6/libsndfile/soxr 的 LGPL 文本 + 重链接可行性；ffmpeg 按裁决 D；若含 plugins extra 则整包 GPLv3 声明或拆分下载 |

### 4.4 THIRD_PARTY_LICENSES.md 必备内容（【R2】P0，验收标准）

1. 每个运行时依赖一节：名称/版本/许可证/上游 URL/许可全文或指针；
2. LGPL 组件（PySide6、libsndfile、soxr、ffmpeg 若捆绑）额外注明动态链接声明与源码获取方式；
3. pedalboard 单独一节，注明「optional extra，启用后分发件按 GPLv3」；
4. ASIO 一节：声明默认不含 ASIO、`SD_ENABLE_ASIO` 为用户自主行为；
5. 与 `pyproject.toml`/`requirements*.txt`/`.github/requirements.lock` 三方交叉一致（CI 可做简单一致性 lint）。

---

## 5. Round 2 中期验收门槛（8 条，全部可量化 pass/fail）

> 规则：**G-1/G-2/G-4/G-8 为一票否决**；其余 4 条允许至多 1 条降级但须在 PROGRESS.md 书面说明降级原因与 R3 补救计划。

| # | 门 | Pass 判据（量化） | 验证方法 |
|---|----|------------------|---------|
| **G-1** | **CI 门**（否决） | 分支 HEAD 上 `Audio CI` workflow 三平台矩阵 + GUI smoke + performance-probes **全部 job 绿**，且 Test job 实际执行 `tests` + `audio-studio/tests` 两套（≥384 项，0 fail 0 error） | `gh run list --branch agent/audio-analysis-software -L1` 状态 = success |
| **G-2** | **栈收敛/许可自洽门**（否决） | `grep -ri pyqt6 audio-studio/ .github/ requirements*.txt` 命中数 = 0；PySide6 出现在 pyproject 与 lock；pyproject 许可声明与 §4.2 裁决一致 | grep + 人工核对 pyproject |
| **G-3** | 计量门 | EBU 3341 cases 1–6 偏差 ≤±0.1LU、≥2 个 TP 用例在 +0.2/−0.4dB、3342 case 1 ≤±1LU，全部以 pytest 断言入 CI；产品侧 `true_peak_level` 在 TP 用例上与 oracle 判据一致 | `pytest tests/compliance` 通过且用例数 ≥9 |
| **G-4** | **Null test 门**（否决） | WAV 16/24/32f 导入→导出 data chunk SHA-256 逐位一致（现有 3 用例保持绿），新增「32f 处理链空载（增益 0dB EQ bypass）后仍 bit 精确」1 例 | `pytest tests/golden` |
| **G-5** | 编辑门 | EditSession 支持 cut/copy/paste/trim/silence；**undo/redo ≥100 步**自动化测试过；编辑全程源文件 SHA-256 不变 | 新增 pytest（编辑序列随机化 + 状态还原断言 + 文件 hash 断言） |
| **G-6** | 实时门 | 产品级 render 路径（真实 `AudioEngine.render` + ≥3 段 EQ + gain 实链，非合成循环）@48kHz/128：**p99 < 1.33ms（50% 预算）且 ≥2000 连续回调 underrun = 0**；直方图 JSON 作为 CI 工件上传 | `monitor-realtime.py --fail-on-trigger` 接产品链路 |
| **G-7** | 性能门 | ①True Peak 归一化 60s/48k 立体声 **<100ms**（现 356ms）；②STFT 60s ≥1000× realtime（保持）；③`perf-regression.py` 对 Round 1 baseline 无 >10% 不利回归；④频谱渲染 1920×1080 ≥30fps **或** 提交瓦片/缓存实现的帧时间证据 | benchmark JSON 对比 |
| **G-8** | **许可门**（否决） | `THIRD_PARTY_LICENSES.md` 存在且满足 §4.4 全部 5 项；默认依赖树（`pip install audio-studio` 解析结果）中无 GPL 强传染组件（pedalboard/PyQt6） | 文件审查 + `pip show` 依赖树 |

**门槛与在飞工作的映射：** G-5 → opus bc-ded8025e；G-6/G-7① → opus bc-32308bf7；G-1/G-3 → gpt-sol 两路（大部分已交付，差 CI 转绿与 TP 用例）；G-2/G-8 → 需 orchestrator 显式指派（当前**无人认领**，最大落空风险）。

---

## 6. 风险更新（相对 Round 1 §6）

| # | 风险 | 变化 | 说明 |
|---|------|------|------|
| R2 许可 | **部分解除 + 新增** | VST3 转 MIT 解除主要法务障碍；但新发现 PyQt6/MIT 不自洽（§4.2-B），且已扩散进 CI lock——每多一轮扩散，切换成本线性上升 |
| R1 技术栈漂移 | **恶化后收敛中** | PyQt6 漂移坐实；本裁决 + G-2 否决门给出强制收敛机制 |
| R3 实时性 | **缓解** | proxy p99 0.844ms（31.6% 预算）+ 32×4 混音 48.6% 单核——**贴近逃生舱阈值但未触发**；维持「不迁移 Rust」结论，条件同 performance-mid-report（实链 p99>1.33ms 或 underrun>0.1% 即重评） |
| R4 演示级 DSP | **实质缓解** | null test/EBU 向量/回归门已立；剩 AES17 与 EQ 0.05dB 收紧 |
| 新增 R11 | **G5/G2 无人认领** | Round 2 dispatch 中 SRC/抖动完全无人做，编辑核心只有单路 opus；若 R2 收口时 G-5 未过，R3 的 4GB 流式 + 频谱编辑 + 插件宿主将同时压在一轮内，**范围性失败概率高** |
| 新增 R12 | **合规自证风险** | 产品响度表若复用 `tools/ebu_r128.py` 代码，3341 验证退化为自证；R3 验收要求两实现独立（§3 新增 E6 已锁定） |

---

## 7. 给 orchestrator 的收口顺序建议

1. **立即：** 指派 CI 转绿（ubuntu runner 补 Qt 系统库 `libegl1 libgl1 libxkbcommon-x11-0 libxcb-*`；windows job 单独排障）——所有质量声明都悬在这上面。
2. **立即：** 指派 G-2/G-8（PySide6 切换 + THIRD_PARTY_LICENSES.md）——机械工作量小、拖延成本高、当前无主。
3. **本轮内：** 验收 opus 两路合并物时直接套 G-5/G-6/G-7 判据，不接受无自动化证据的完成声明。
4. **R3 排程输入：** 按 §2.2 的偏态结论，Round 3 首位排 G2 延展（流式/RF64）与 G4→S1（频谱编辑最小闭环），G7 插件宿主若资源紧张降为单平台演示。

---

*— fable（claude-fable-5-thinking-xhigh），Round 2 SOTA 差距复审子代理（bc-0247424d），2026-08-26。复审证据均可由 §1 方法复现；本文档只陈述已验证事实与裁决，未合并的在飞工作不计入完成度。*
