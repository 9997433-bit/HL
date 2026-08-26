# Round 3 — SOTA 最终验收审计（fable / claude-fable-5-thinking-xhigh）

- **审计角色：** Round 3 子代理 #1 — SOTA 最终验收审计（bc-63e6fdf0）
- **审计冻结 commit：** 主体取证于 `b90e0e9`（2026-08-26，含 Round 3 gpt-sol 两路产出：CI 修复 + 验收自动化、许可清单 + 发布文档）；成文期间子代理 #3 多轨产出合入（`edda345`），已按 §9 附录复验并并入判定。
- **前置文档：** Round 1 `fable-sota-audit.md`（§7 Round 3 checklist，基线 `1408e58`）、Round 2 `fable-sota-round2-review.md`（§5 八条中期门槛，基线 `2bd94c0`）
- **重要范围注记：** 截至 `edda345`，Round 3 子代理 #4（BS.1770 产品合规 & 修复套件，bc-c21cf033）**尚未合入**（PROGRESS.md 仍标 🔄）。本裁决只对已合入代码负责；在飞工作合入后须按 §7 的翻案条件重新点验，不自动继承本裁决。

---

## 0. 裁决（TL;DR）

> ### 「Audition 级 SOTA」验收：**No-Go**
>
> 30 项 checklist 判定：**P0 通过 4 / 部分 6 / 未过 10；P1 通过 0 / 部分 2 / 未过 8**（含 §9 附录对多轨合入的改判）。
> Round 1 验收规则（P0 全过 + P1 至多 2 项降级）远未满足——**16 项 P0 未达全过线，其中 10 项硬性未过构成一票否决**（清单见 §5）。
>
> ### 「0.1.0-alpha 专业音频分析/编辑底座」发布：**Go（有条件）**
>
> 全量测试三平台 CI 首次全绿、null test 位精确、产品级 BS.1770 响度计通过 3341/3342 已覆盖向量、许可清单完整自洽、120 步 undo/redo 自动化通过——作为**诚实定位的 alpha**（不宣称 Audition 级、不宣称 SOTA）可以放行。仓库自身的 `FINAL_SUMMARY.md` 与 `ci-acceptance-report.json`（`sota_claimed: false`）已采取同一立场，本审计予以确认。放行条件见 §6。

---

## 1. 审计方法与证据链

本审计延续 Round 2 原则：**不采信任何未经复现的声明**。所有结论可由 §8 命令复现。

| 证据 | 方法 | 结果 |
|------|------|------|
| 全量测试 | 审计 VM（Linux/Python 3.12.3，venv 安装 PySide6-Essentials 6.11.2 + Qt 系统库）运行 `QT_QPA_PLATFORM=offscreen pytest -q tests audio-studio/tests benchmarks/slo` | 冻结点 `b90e0e9`：**667 passed, 23 xfailed, 1 xpassed（5.87s）**（前一快照 `6f93ab2` 为 660 passed） |
| CI 真实状态 | `gh run list` / `gh run view --json jobs` 逐 run 核查 | run **32949624137**（commit `c908a7e`）**全部 6 job 绿**：Test（ubuntu/macos/windows，跑两套 pytest）、GUI smoke、Performance probes、PySide6 binding guard。HEAD `b90e0e9` 为纯文档提交，其后无新 run。**这是本项目历史上第一个绿色 CI run**（此前 Round 1–2 全部 failure，根因 libEGL 缺失 + `tools` 模块 rootdir 问题，本轮由 gpt-sol 修复：workflow 安装 Qt 系统库 + `pip install -e` 化解） |
| 验收自动化 | 逐行审读 `tests/acceptance/test_sota_checklist.py`（565 行，30 用例），核对每个"pass"是真实断言、每个 xfail 理由与代码事实一致 | 通过项判据经抽查属实（详见 §4 逐项）；发现 1 处过期 xfail（E3 XPASS，见 §6 条件 2） |
| 性能实测 | 审计 VM 直接实测 + 运行 `audio-studio/benchmarks/bench_stft.py` + 读取 `final-perf-delta.json` | True Peak 归一化 60s/48k 立体声 **63.0ms**（Round 2 门 <100ms ✓）；响度积分 60s **94.4ms**；STFT 60s **1792× realtime**；频谱 1920×1080 首绘 **27fps**（30fps 门边缘未过，本 VM 无 GPU）；perf-delta 9/9 指标对 Round 1 baseline **stable** |
| 代码事实 | grep/审读关键模块与 UI 集成面 | PyQt6 残留 **0 处**；`RingBuffer` 已重写为 lock-free SPSC；`EditSession` 9 命令核心完备但**未接入任何 UI 文件**；`AudioEngine.render_into` 仍调用 `_update_levels`（回调路径分配）；无录音路径/限幅器/压缩器/噪声门/TPDF 抖动/RF64/多轨/VST3/频谱修复/工作区持久化 |
| 许可 | 逐节审读 `THIRD_PARTY_LICENSES.md`（177 行）对照 Round 2 §4.4 五项必备内容 | **五项全数满足**（逐依赖表 + LGPL 重链接声明 + pedalboard GPL 隔离条款 + ASIO 默认不含声明 + 五清单交叉核对一致）；CI 增设 `! grep -rn PyQt6` 绑定守卫 |

---

## 2. Round 2 八条中期门槛复核（承诺追踪）

| # | 门 | 判定 | 证据 |
|---|----|:---:|------|
| **G-1** CI 门（否决） | **✓ 过** | run 32949624137 三平台矩阵 + GUI smoke + perf probes + 绑定守卫全绿；Test job 实跑 `tests` + `audio-studio/tests` 两套 |
| **G-2** 栈收敛/许可自洽门（否决） | **✓ 过** | PyQt6 命中 0；PySide6-Essentials 进入 pyproject/requirements/CI lock；pyproject MIT 声明与 LGPL 依赖树自洽；CI 守卫防回潮 |
| **G-3** 计量门 | **✗ 未过** | 要求 3341 cases 1–6 + ≥2 TP 用例；实际 3341 仅 cases 1–3、**TP 向量 0 个**（`TECH_3341_TRUE_PEAK_VECTORS` 不存在，A1-TP xfail）。超额部分：产品侧 `LoudnessMeter` 已存在并直接过 3341 1–3 / 3342 1–3（原要求仅 oracle） |
| **G-4** Null test 门（否决） | **◐ 部分** | 原 3 用例（16/24/32f SHA-256 位精确）保持绿且入 CI ✓；要求新增的「32f 处理链空载后仍 bit 精确」用例**未添加** |
| **G-5** 编辑门 | **◐ 部分** | 9 命令（delete/cut/paste/insert-silence/silence/gain/fade/reverse/trim）✓；**120 步 undo/redo 自动化过**（超 100 步要求，含内容位等断言）✓；「编辑全程源文件 SHA-256 不变」断言未落地（架构上 EditSession 为内存文档、不改源文件，但无测试留痕） |
| **G-6** 实时门 | **✗ 未过** | 要求产品级 render 实链计时；实际仍只有合成 proxy（p99 0.844ms）。且验收套件 C3 自证：`render_into` 内 `_update_levels` 在回调路径**分配 NumPy 数组**——回调纪律"零分配"审查不通过 |
| **G-7** 性能门 | **◐ 部分（3/4）** | ① True Peak 归一化 63ms < 100ms ✓（审计 VM 实测）；② STFT 1792× ≥ 1000× ✓；③ perf-regression 9/9 stable ✓；④ 频谱 1920×1080 首绘 27fps < 30fps（调色板重绘 54fps；无瓦片化帧时间证据）✗ |
| **G-8** 许可门（否决） | **✓ 过** | `THIRD_PARTY_LICENSES.md` 满足 §4.4 五项；默认依赖树无 GPL 强传染组件 |

四条否决门中 **G-1/G-2/G-8 干净通过，G-4 主体保持、增量欠一例**。相对 Round 2 冻结点（G-1/G-2/G-8 全红）这是实质兑现；G-3/G-6 的落空直接转化为 §5 的 P0 否决项。

---

## 3. 测试与规模概览

| 快照 | 测试 | 备注 |
|------|------|------|
| Round 1（`74a0c07`） | 364 passed | 应用套件 |
| Round 2 冻结（`2bd94c0`） | 384 + 21 passed | +验证基建 |
| Round 2 合并（`f8cf6ef`） | ~632 passed | +引擎/编辑/预览/响度 |
| **Round 3 冻结（`b90e0e9`）** | **667 passed + 23 xfailed + 1 xpassed** | +30 项验收自动化套件（7 真实断言过、23 缺口显式 xfail）；CI 首绿 |

xfail 机制评价：**这是本项目三轮以来在"防止演示级冒充专业级"上最重要的工程决定**——缺口被编码为可执行断言（缺证据报告文件即 fail），补齐实现后自动转 XPASS 暴露，既保 CI 绿又不虚报。审计抽查 23 条 xfail 理由与代码事实**全部一致**（唯 E3 已过期，见 §6）。

---

## 4. Round 3 Checklist 逐项判定（30 项）

> 原 §7 为 29 条 bullet；验收套件将 A1（响度+TP 合并条）拆为两项、总数 30，本审计采认该拆分。
> 图例：✓ 过（有自动化/可复现证据）／◐ 部分（能力或判据部分达成）／✗ 未过。
> 「验收套件」= `tests/acceptance/test_sota_checklist.py` 冻结点运行结果。

### A. 合规与精度（9 项：7×P0 + 2×P1）

| # | 级 | 项目 | 判定 | 证据与差距 |
|---|----|------|:---:|-----------|
| A1-LUFS | P0 | EBU 3341 响度 ≤±0.1 LU | **◐** | **产品级** `LoudnessMeter`（`dsp/loudness.py`，K 加权由模拟原型任意采样率重推导 + 双级 gating，与 oracle `tools/ebu_r128.py` 无交叉 import——满足 Round 2 新增 E6 独立性要求）对 3341 cases 1–3 全过 ±0.1LU（实测偏差 ≤0.06LU），CI 自动。**差距：cases 4–9（gating 压力/绝对门/相对门用例）向量未合成**，覆盖不完整 |
| A1-TP | P0 | 3341 True Peak 用例 +0.2/−0.4 dB | **✗** | `TECH_3341_TRUE_PEAK_VECTORS` 不存在（验收套件 xfail 自认）。产品有 4× 过采样 `true_peak_level` 且有单元测试，但无 3341 TP 合规向量 |
| A2 | P0 | 3342 LRA ≤±1 LU | **◐** | 产品 `loudness_range` 过 3342 cases 1–3（±1LU，CI 自动）；其余 LRA 用例（含真实素材类）未覆盖 |
| A3 | P0 | Null test 16/24/32f bit 精确 | **✓** | `tests/golden`（fmt 字段 + data chunk SHA-256，含变异侦测自检）+ 验收套件 A3 双路覆盖，三平台 CI 绿 |
| A4 | P0 | 参数 EQ vs 解析解 <0.05 dB | **◐** | 验收套件：20Hz–20kHz 2048 点几何扫频，`magnitude_response_db` 对**独立实现的** RBJ 解析参考最大偏差 <0.05dB ✓。**判据保留**：①仅 1 组参数（peaking 2137Hz/+9.25dB/Q1.37），"任意常用参数组"未扫；②验证的是响应函数（系数正确性），实际 sosfilt 处理路径的实测扫频仍停在 0.1–0.2dB 容差旧测试 |
| A5 | P0 | SRC 96k→44.1k 镜像 <−120dBFS、THD+N <−130dBFS | **✗** | SRC 仍为 scipy `resample_poly`，无 quality 参数、无测量脚本、无数据（xfail）。Round 1 审计"此项不接受够用了"的红线原样存续，**三轮无人认领** |
| A6 | P0 | True Peak 限幅器 ISP 向量 | **✗** | 限幅器不存在（效果目录仅 gain/normalize/fade/eq）。在飞子代理 #4 范围，未合入 |
| A7 | P1 | TPDF 抖动频谱验证 | **✗** | `quantize_with_tpdf` 不存在；`save_audio` 仍无抖动直接重量化（Round 2 已记录的音质缺陷，未修复） |
| A8 | P1 | AES17 THD+N 测量脚本 | **✗** | `tools/aes17.py` 不存在 |

### B. 功能完备（8 项：4×P0 + 4×P1）

| # | 级 | 项目 | 判定 | 证据与差距 |
|---|----|------|:---:|-----------|
| B1 | P0 | M1–M13 逐项演示 | **✗** | 无证据清单（xfail）。审计盘点：M1 ✗（**无录音路径**，播放侧 ✓）；M2 ◐（EditSession 核心完备但 **UI 零接线**——`ui/` 目录无一处 import EditSession，用户在应用内无法剪切/粘贴/撤销）；M3 ◐（金字塔波形/采样级缩放 ✓，peak file 持久缓存 ✗）；M4 ◐（STFT 频谱停靠面板 ✓，与波形联动选区 ✗）；M5 ◐（WAV/FLAC/MP3/OGG/AIFF + ffmpeg 兜底 ✓；RF64/bext ✗）；M6 ◐（M/S/I/LRA/TP 产品计量 ✓ 且入状态栏，EBU Mode 全向量 ✗）；M7 ◐（振幅统计/实时频谱 ✓，相位相关表 ✗）；M8 ◐（增益/峰值+真峰归一化/淡变/EQ ✓；**响度归一化/压缩/限幅/噪声门 ✗**）；M9 ✗（无降噪）；M10 ✗（SRC 未定级、无抖动）；M11 ◐（三平台 CI 绿 ✓，音频后端仅 PortAudio 一层）；M12 ◐（停靠×2/暗色/快捷键 ✓，工作区/60fps/HiDPI ✗）；M13 ◐（golden/3341 部分 ✓，AES17 ✗） |
| B2 | P0 | 1h 文件：打开<3s/频谱首屏<2s/离线处理<30s | **✗** | 仅 60s 级 headless proxy（U1 解码 8.4ms/60s、频谱首绘 36.5ms/60s，外推乐观但**外推不是证据**）；1h 实测无 |
| B3 | P0 | 4GB RF64 流式、内存<1GB | **✗** | loader 无 RF64 处理；`SampleSource` 流式读取面已就位（架构前提具备）但大文件端到端证据无 |
| B4 | P0 | undo/redo 100 步跨效果自动化 | **✓** | 验收套件：120 步 gain 编辑 → 120 步 undo（内容与原始位等）→ 120 步 redo（内容与终态位等），`undo_limit=150` 驱逐语义另有测试，CI 绿 |
| B5 | P1 | 频谱选区衰减/DeClick/DeHum | **✗** | `dsp/spectral.py` 无 `attenuate_selection/delete_selection/declick/dehum`（xfail）；iSTFT 精确重建底座三轮就绪但修复算法始终未开工。在飞 #4 范围 |
| B6 | P1 | VST3 宿主 3 插件 + PDC null test | **✗** | `audio_studio/plugins/` 不存在。法务障碍 Round 2 已清除（VST3 SDK→MIT），纯实现缺位，G7 三轮停在 ~5% |
| B7 | P1 | 批处理 10 文件→−16LUFS→FLAC | **✗** | `core/batch.py` 不存在。注：其料件（产品响度计 + FLAC 导出）均已就绪，此项是低垂果实 |
| B8 | P1 | 多轨 32 轨 + 包络 + 总线 | **◐** | `edda345` 合入 `core/session.py`（1,018 行：Clip 引用式非破坏模型 + 逐 clip 音量包络 + Track 音量/声像/静音/独奏 + MasterBus + SessionMixer 求和）与 `MultitrackView`（接入 MainWindow），108 项测试含求和 null test/对齐/mute-solo ✓。**差距：** 32 轨实时回放零 dropout 证据与 `multitrack-report.json` 无；验收套件 B8 判据（按 `core/multitrack.py` 路径探测）未随实现重接，仍 xfail。详见 §9 |

### C. 实时与稳定（4 项：3×P0 + 1×P1）

| # | 级 | 项目 | 判定 | 证据与差距 |
|---|----|------|:---:|-----------|
| C1 | P0 | 48k/256 回放 30min 零 dropout | **✗** | 云端无声卡；proxy（2000 回调 0 underrun）不能替代硬件 soak（xfail 如实自认）。**结构性受限项**：需真实工作站执行 |
| C2 | P0 | 60min 录音零丢样 | **✗** | 录音路径**根本不存在**（引擎无输入流）——非证据缺失而是功能缺失，M1 连带 |
| C3 | P0 | 回调 p99 <50% 预算 + 零分配/零锁审查 | **✗** | 计时侧 proxy p99 0.844ms（31.6% 预算）曾达标，但**代码审查不过**：`render_into` 调用 `_update_levels` 在回调路径分配 NumPy 数组/元组（验收套件 C3 以 `inspect.getsource` 断言自证）。正面进展：`RingBuffer` 已从 mutex 重写为 lock-free SPSC（Round 2 遗留问题闭环） |
| C4 | P1 | 往返延迟实测 <15ms@128 | **✗** | 需硬件 loopback，无 |

### D. UI/UX 与无障碍（5 项：3×P0 + 2×P1）

| # | 级 | 项目 | 判定 | 证据与差距 |
|---|----|------|:---:|-----------|
| D1 | P0 | 60fps 表头/HiDPI/暗色默认 | **✗** | 暗色默认 ✓（1/3 子判据）；`UI_REFRESH_MS=33`（30Hz 刷新，60fps 判据结构性不满足）；帧时间打点与 HiDPI 2x 验证均无 |
| D2 | P0 | 停靠面板 + 两套工作区 + 布局持久化 | **◐** | 频谱 + 效果机架两个 QDockWidget ✓；工作区预设（editing/metering）与 `saveState/restoreState` 持久化 ✗ |
| D3 | P0 | 键盘完整工作流 | **◐** | 传输（Space）/缩放（Ctrl+=/-/0）/打开/导出快捷键 ✓；但编辑命令未接 UI（无编辑快捷键可言），无鼠标闭环证据（keyboard-workflow-report 不存在） |
| D4 | P1 | WCAG AA / 色盲安全 / 屏幕阅读器 | **◐** | 主题对比度断言（text/window ≥4.5:1）✓ + viridis 色盲安全色图 ✓；控件无障碍语义标签 0 处、屏幕阅读器走查无 |
| D5 | P1 | UI 缩放 100–200% | **✗** | 无验证 |

### E. 跨平台与工程质量（4 项：3×P0 + 1×P1）

| # | 级 | 项目 | 判定 | 证据与差距 |
|---|----|------|:---:|-----------|
| E1 | P0 | 三平台 CI 全绿 | **✓** | run 32949624137（`c908a7e`）6/6 job 绿：ubuntu/macos/windows Test（两套 pytest 691 项）+ GUI smoke + perf probes + PySide6 守卫。修复内容（Qt 系统库安装、`pip install -e` 解 `tools` 导入、产品响度测试显式入命令）经审计核实。注记：HEAD `b90e0e9` 为纯文档提交无新 run，绿证据取自其父提交 |
| E2 | P0 | DSP golden 三平台一致 ≤1e-9 | **◐** | 代理信号：三平台跑**同一** golden/DSP 断言套件全绿（隐含平台内各自 bit 精确）；但跨平台**产物比对工件**（同输入三平台输出 diff ≤1e-9）未生成（xfail）。CI 已绿，此项现在是顺手可收的 |
| E3 | P0 | THIRD_PARTY_LICENSES.md 完整自洽 | **✓** | 177 行清单满足 Round 2 §4.4 全部五项：①逐依赖名称/版本/许可/上游/指针（含 wheel 捆绑物 libsndfile/OpenBLAS/GCC runtime/编解码器）；②LGPL 组件动态链接与源码获取声明；③pedalboard「optional extra=GPL 分发」隔离条款；④ASIO 默认不含 + `SD_ENABLE_ASIO` 用户自主声明；⑤与 pyproject/requirements×2/CI lock 交叉核对一致 + 发布前 SBOM 检查单。**验收套件中此项仍挂过期 xfail 标记（现为 XPASS），须摘除**（§6 条件 2） |
| E4 | P1 | 崩溃自动恢复 | **✗** | 无实现（工程持久化 S8 整体未开工） |

### 汇总

| | ✓ 过 | ◐ 部分 | ✗ 未过 |
|---|:---:|:---:|:---:|
| **P0（20 项）** | 4（A3、B4、E1、E3） | 6（A1-LUFS、A2、A4、D2、D3、E2） | 10 |
| **P1（10 项）** | 0 | 2（D4、B8@`edda345`） | 8 |

**G1–G10 加权完成度（沿用 Round 1 权重）≈ 44%**（G10 验证基建 ~75%、G3 计量 ~55%、G2 编辑核心 ~40% 为三大拉动项；G5 SRC ~10%、G7 插件 ~5% 三轮未动）。距 Round 2 冻结点的 25% 有实质推进，但曲线形状不变：**分析/验证/合规强，编辑工作流/修复/插件/多轨弱**——最终交付物是「测量精确、工程可信的音频分析器 + 编辑内核」，尚不是音频工作站。

---

## 5. P0 一票否决项清单

按 Round 1 §7 规则，以下任何一项不闭合即不得宣布「Audition 级」。**硬性未过 10 项**（按补救成本从低到高排序）：

| # | 项 | 缺口本质 | 补救量级 |
|---|----|---------|---------|
| V1 | A1-TP | 3341 TP 向量未合成（产品 4×过采样 TP 已有、只缺合规向量与断言） | 小：向量合成脚本 + ~5 断言 |
| V2 | A6 | True Peak 限幅器不存在 | 中：新效果 + ISP 向量（在飞 #4 范围） |
| V3 | A5 | SRC 质量未测量、未定级（三轮无人认领，Round 1 红线） | 中：接入 soxr 级依赖 + 测量脚本，或实测现 SRC 出数据 |
| V4 | D1 | 30Hz UI 时钟 + 无帧时间/HiDPI 证据 | 中：刷新率改造 + 打点报告 |
| V5 | B2 | 1h 文件三项性能只有 60s proxy 外推 | 中：真实 1h fixture 实测（B3 若闭合可共用） |
| V6 | E2 | 跨平台 golden 产物比对工件缺（CI 已绿，条件已具备） | 小：CI 上传产物 + 比对 job |
| V7 | C3 | 回调路径 `_update_levels` 分配内存，零分配审查不过 | 中：计量出回调（预分配/SPSC 回传），产品实链直方图 |
| V8 | B3 | RF64 >4GB 流式全流程无 | 大：loader RF64 + 端到端内存证据 |
| V9 | B1 | M1–M13 无逐项证据清单；且 M1 录音、M8 半数动态效果、M9 降噪为实打实功能缺失，**M2 编辑核心未接 UI** | 大：跨多域 |
| V10 | C1/C2 | 硬件 30min 回放 + 60min 录音 soak（C2 另含录音功能本体缺失） | 大：需真实设备；录音路径从零 |

**部分达成、但按验收线仍拦截的 P0 共 6 项**：A1-LUFS / A2（向量覆盖不全）、A4（单参数组 + 响应函数级验证）、D2（无工作区持久化）、D3（编辑无键盘通路）、E2（无跨平台比对工件）。

P1 侧 10 项中 8 项未过（B8 经 §9 改判为部分），仍远超「至多 2 项降级」额度——即使 P0 全绿，P1 亦独立构成 No-Go。

---

## 6. Alpha 发布放行条件（Go 的约束）

1. **定位措辞锁定：** PR/CHANGELOG/README 不得出现「Audition 级达成」「SOTA」字样；采用 `FINAL_SUMMARY.md` 已有的「专业音频分析与编辑底座 alpha」口径。`ci-acceptance-report.json` 的 `sota_claimed: false` 必须保留并随每次验收再生成。
2. **验收套件卫生：** 摘除 E3 的过期 xfail 标记（当前 XPASS）；建议全部 xfail 改 `strict=True`，使未来任何缺口补齐都强制显式转正，防止"静默达成"绕过审计。
3. **在飞工作合入纪律：** 子代理 #3（多轨）/#4（BS.1770 合规与修复）合入时，必须挂接对应 xfail 项转正（B8、A6、B5、A1-TP 等）并保持 CI 绿；合入后由验收审计复核，不接受自宣。
4. **诚实标注结构性受限项：** C1/C2/C4/D4-屏幕阅读器等需硬件/人工的项，在发布说明中标注「未认证」，不得以 proxy 数据暗示已达标。

---

## 7. 翻案条件（No-Go → Go 的最短路径）

若后续轮次追求翻案，按投入产出排序：V1、V6（合计约一日内工作量级的小项）→ V2+V3（A 组精度闭环，#4 在飞）→ V7（回调计量出内环）→ V4/V5 → B1 证据清单化（把已有能力逐 M 项固化成 manifest，M2 的 UI 接线是其中最高价值单项）→ V8/V9/V10。P1 侧优先 B7（批处理，料件全备）与 D4（对比度已过半）。
**结构性判断维持 Round 2 §2.2 结论：** 除非 G2-UI 接线、录音、修复套件、多轨四线同时闭合，否则「Audition 级」在本代际不可宣。

---

## 8. 证据复现命令（附录 §9 前的主体取证基于 `b90e0e9`）

```bash
# 环境（Ubuntu）：
sudo apt-get install -y libegl1 libgl1 libxkbcommon-x11-0 libxcb-cursor0 portaudio19-dev
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt pytest-qt "PySide6-Essentials>=6.6" PyAudio
pip install -e audio-studio --no-deps

# 全量测试（冻结点预期 667 passed, 23 xfailed, 1 xpassed）：
QT_QPA_PLATFORM=offscreen python -m pytest -q tests audio-studio/tests benchmarks/slo

# 30 项验收明细：
QT_QPA_PLATFORM=offscreen python -m pytest tests/acceptance -v -rX -rx

# CI 状态：
gh run list --branch agent/audio-analysis-software -L 5
gh run view 32949624137 --json jobs

# 性能抽测：
QT_QPA_PLATFORM=offscreen python audio-studio/benchmarks/bench_stft.py

# 栈收敛与许可：
grep -ri pyqt6 audio-studio/ .github/ requirements*.txt | wc -l   # 预期 0
ls THIRD_PARTY_LICENSES.md
```

---

## 9. 附录：`edda345` 多轨合入的即时复验（成文期间落地）

本报告主体取证冻结于 `b90e0e9` 后、推送前，子代理 #3（opus-fast，多轨 Session MVP）产出合入至 `edda345`（+3,521 行）。按最终验收职责即时复验：

| 复验点 | 结果 |
|--------|------|
| 全量测试 | **775 passed, 23 xfailed, 1 xpassed（6.36s）**——新增 108 项 `test_session.py` 全绿，无回归 |
| 交付实质 | `core/session.py`：Clip（引用式非破坏 + 逐 clip 增益/淡变/**音量包络**）、Track（音量/声像/静音/独奏）、MasterBus、SessionMixer（求和实现 `SampleSource` 接口，可直接喂引擎）；`core/sources.py` 补齐 **RegionSource/LoopSource**（Round 2 遗留的架构契约缺口就此关闭）；`MultitrackView`（812 行）接入 MainWindow View 菜单 |
| 测试质量 | 含求和 null test（正负对消）、样本对齐、mute/solo 语义、包络插值——非演示级 |
| 仍缺 | 32 轨**实时回放零 dropout** 证据（`multitrack-report.json`）；验收套件 B8 探测路径为 `core/multitrack.py`，与实际 `core/session.py` 不符，**xfail 未随实现重接**（同 §6 条件 2 的套件卫生问题）；无轨道级效果插入与子总线 |
| 改判 | B8：✗ → **◐**；Round 2 遗留清单第 5 条（RegionSource/LoopSource）关闭 |
| 对裁决影响 | **无**——B8 为 P1，P0 否决清单（§5）原样成立；P1 未过仍有 8 项。G2 编辑核心加权估值由 ~40% 上修至 ~50%,总加权 ≈ **46%** |

子代理 #4（BS.1770 产品合规 & 修复套件）在本报告推送时仍未合入；其落地对应 A1-TP/A6/B5 三项，合入后按 §7 复核。

---

*— fable（claude-fable-5-thinking-xhigh），Round 3 SOTA 最终验收审计子代理（bc-63e6fdf0），2026-08-26。主体冻结 `b90e0e9`，附录复验至 `edda345`；仅新增本文档，未改动任何业务代码。裁决：Audition 级 SOTA **No-Go**（10 项 P0 硬否决）；0.1.0-alpha 底座定位 **Go（受 §6 四条件约束）**。*
