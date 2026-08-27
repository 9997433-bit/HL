# Round 2 — 架构收敛审计（fable / claude-fable-5-thinking-xhigh）

| 元信息 | 值 |
|---|---|
| 文档角色 | Round 2 架构收敛审计：偏差清单 + 迁移方案 + 冻结 API 规格 |
| 作者 | fable 架构收敛审计子代理（`claude-fable-5-thinking-xhigh`, bc-81118806） |
| 日期 | 2026-08-26 |
| 分支 | `agent/audio-analysis-software` |
| 审计基线 | `fe13122`（Round 2 派发日志）；实现基线 `74a0c07`（Round 1 收口） |
| 上游契约 | `.agent_workspace/round1/fable-architecture.md`（简称「架构契约」）、`fable-sota-audit.md`（G1–G10） |
| 性质 | **只含文档与规格，不含业务代码改动**。§3/§4/§5 的接口签名自本文档合入起冻结，实现子代理不得单方面变更；变更须经 fable 审计代理批准并更新本文档 |

---

## 0. 执行摘要

Round 1 交付了一个测试全绿（364 tests）的可用 MVP，但与架构契约存在**一处许可级偏差（PyQt6，GPL 传染）**、**两处架构级偏差（无 EditSession/COW 撤销、无磁盘流式）**、**一处实时纪律偏差（mutex RingBuffer + 回调路径逐块分配）**，以及若干结构/签名级漂移。本文档给出：

1. **§1 偏差清单**——18 项，按「许可 / 架构 / 实时 / 结构 / 工程」五类定级；
2. **§2 PySide6 迁移收敛方案**——17 文件 36 处引用的文件级改动 map、6 条机械替换规则、5 步 CI 验证门；
3. **§3 EditSession 命令模式 API**——`AudioChunk / ChunkTable / Document / EditCommand / UndoStack / EditSession` 冻结签名（COW 分块，O(1) 撤销）；
4. **§4 SampleSource 协议 + lock-free SPSC RingBuffer 替换契约**——零分配 `read_into` 读取面、SPSC 单调索引环、迁移兼容策略与验收测试；
5. **§5 Rust 逃生舱触发监控**——RT 安全的回调耗时直方图与 underrun 计数器规格、判决 JSON schema、判决程序纪律。

**结论先行：** 全部偏差均可在 Python 层收敛，无需提前触发逃生舱；PySide6 迁移是机械改动（预估 diff <300 行），真正的攻坚是 §3/§4 的两块新增子系统。建议实现顺序：**§2（半天级机械活，先解除许可风险）→ §4（SampleSource + SPSC，引擎内脏置换）→ §3（EditSession，建立在 §4 之上）→ §5（监控随 §4 一起落地）**。

---

## 1. Round 1 代码 vs 架构契约偏差清单

审计范围：`audio-studio/`（29 个源文件 + 12 个测试文件）、根目录 `tools/ tests/ scripts/ .github/`。逐条给出契约出处、现状证据（文件:行）、影响与收敛动作。

**严重度定义：** S1 = 阻断 Round 3 验收（许可/架构不可后补项）；S2 = 阻断 SLO 达标；S3 = 漂移，需收敛但不阻断。

### 1.1 许可与技术栈（S1）

| # | 偏差 | 契约出处 | 现状证据 | 影响 | 收敛动作 |
|---|---|---|---|---|---|
| DEV-01 | **Qt 绑定用 PyQt6（GPL-3.0/商业双许可）而非 PySide6（LGPL-3.0）** | 架构 §3.3/§3.5/§9（PySide6 ≥6.6，LGPL 动态链接合规） | 17 个文件 36 处 `PyQt6` 引用（清单见 §2.1）；`audio-studio/pyproject.toml:28`、`requirements.txt:5` | GPL 传染整个代码库，与 §3.5 许可矩阵直接冲突；且 PyQt6 与 pedalboard(GPL) 叠加后闭源路径完全关死 | **§2 迁移方案，Round 2 第一优先** |
| DEV-02 | **设备 I/O 用 PyAudio 而非 sounddevice** | 架构 §3.1/§9（sounddevice ≥0.4.6：wheel 自带 PortAudio、Windows 含 WASAPI/ASIO；CFFI 回调释放 GIL 更干净） | `core/output.py:213` `PyAudioOutput`；`pyproject.toml:32` `audio = ["PyAudio>=0.2.13"]`。讽刺的是根目录 `requirements.txt:5` 与 `scripts/probe-system.py` 已在用 `sounddevice==0.5.6` —— 同仓库两套后端 | PyAudio 需系统 PortAudio 头文件编译、无预编译 ASIO、双工/独占模式支持弱，L2(<10ms RTT) 在 Windows 上无法达标 | Round 2 新增 `SoundDeviceOutput(AudioOutput)` 后端并设为默认；`PyAudioOutput` 降级为可选；`AudioOutput` 抽象层保留（该抽象本身与契约兼容，是 Round 1 的正资产） |

### 1.2 架构级缺失（S1，对应 G1/G2）

| # | 偏差 | 契约出处 | 现状证据 | 影响 | 收敛动作 |
|---|---|---|---|---|---|
| DEV-03 | **无 Document/COW 分块存储，无 Command/UndoStack** | 架构 §5.2（COW 块 = 2^18 样本、O(1) 撤销）、附录 A `Command` Protocol、审计 G2 | 全仓无任何 undo 相关代码；编辑=对 `AudioBuffer.data` 整体重算（`dsp/effects/*` 返回全新数组）；`engine.set_clip()` 直接替换 clip | 无法支撑 U4（≥1000 步撤销 ≤2× 磁盘占用）与 M2（≥100 步 undo）；后补成本随功能面增长而放大 | **§3 冻结 API，opus-fast A 实现** |
| DEV-04 | **无磁盘流式，全量载入唯一路径** | 架构 §4.2 磁盘流送线程、风险 R6（「禁止全量载入路径进入主干」）、审计 §3.3 大文件（4GB RF64 峰值内存 <1GB） | `core/loader.py:133` `sf.read(str(path), dtype="float32", always_2d=True)` 一次性读全файла；`engine._pump_once()` 从 `self._clip.buffer.data[pos:pos+n]` 切片（`engine.py:445`） | 1h/48k/立体声 float32 ≈ 1.3GB 内存；4GB RF64 直接 OOM；U1（打开 <2s）在大文件上不可达 | **§4.1 SampleSource 协议**；feeder 线程改为从 source 拉取；`load_audio` 保留为小文件快路径 |
| DEV-05 | **无 Session/Timeline/多轨数据模型** | 架构 §5.2 Session、能力矩阵 #2/#6 | 单 clip 单轨引擎（`engine._clip`）；`ui/track_panel.py` 是单轨视图 | M1 里程碑（多轨+总线+图编译）无从谈起 | Round 2 后半启动；**先落 §3 EditSession（波形编辑器路径），Session 数据模型另行规格**（不在本文档冻结范围，避免过早设计） |

### 1.3 实时纪律（S2，对应 G1）

| # | 偏差 | 契约出处 | 现状证据 | 影响 | 收敛动作 |
|---|---|---|---|---|---|
| DEV-06 | **RingBuffer 用 `threading.Lock`** | 架构 §4.2「音频回调线程零分配、零锁」 | `core/ring_buffer.py:36` `self._lock = threading.Lock()`；`read()/write()/available_*` 全部持锁 | 回调线程可能阻塞在 feeder 持锁窗口上（GIL 之外的第二重阻塞源）；优先级反转风险 | **§4.2 SPSC 契约替换** |
| DEV-07 | **设备回调路径逐块分配** | 同上「零分配」 | `ring_buffer.read()` 每次 `np.zeros` 新数组（`ring_buffer.py:108`）；`engine.render()` 中 `block * SAMPLE_DTYPE(gain)` 再分配（`engine.py:332`）；`_update_levels()` 在设备线程做 `np.max/np.sqrt` 并构造 `LevelReading` + 两个 tuple（`engine.py:336-343`）；`output._render()` 的 `np.asarray/np.vstack/ascontiguousarray` 兜底路径同样分配 | 每块 3–6 次小分配 → GC 压力 → 回调耗时长尾，直接威胁 T2(p99<1.33ms) | `read_into(out)` 零分配读取（§4.2）；gain 用 `np.multiply(out, g, out=out)` 原位；电平计算移出回调（消费侧从计量三缓冲读，或以预分配标量槽发布 peak²，UI 侧开方） |
| DEV-08 | **计量数据无三缓冲，`self._levels` 竞态发布** | 架构 §4.2 计量三缓冲 | `engine.py:341` 设备线程直接赋值 `self._levels`，UI 线程 `levels` property 直读 | CPython 引用赋值原子性掩盖了问题，功能上「碰巧正确」，但对象构造在 RT 线程且无节流 | 随 §5 遥测设施一并落地：peak/RMS 写入预分配 float64 数组槽位，UI 侧 copy-on-read |
| DEV-09 | **块大小默认 1024，无 gc 纪律** | 架构 §4.2（128–256 块 + `gc.freeze()`/`gc.disable()`） | `output.py:26` `DEFAULT_BLOCK_SIZE=1024`；全仓无 `gc.` 调用 | 1024@48k = 21.3ms 单缓冲，L1/L2 不可达；GC 停顿未防护 | 默认块降至 256（null 后端）/128（硬件后端实测协商）；播放会话入口加 `gc.freeze()+gc.disable()`、停止时恢复并手动 `gc.collect(0)` |
| DEV-10 | **播放头精度 = 块粒度，无流时钟插值** | 架构 §5.1 样本精确播放头；PROGRESS「stream time 块内插值」 | `engine.position` = `_source_pos - ring.available_read`（`engine.py:231`），只在块边界跳变 | 60fps 游标每 21ms 跳一次（块 1024 时肉眼可见）；标记吸附误差 | telemetry 记录「最近回调的 (host_time, frame_count)」，UI 读取时按 `perf_counter` 差值内插 |

### 1.4 结构与签名漂移（S3）

| # | 偏差 | 契约出处 | 现状证据 | 收敛动作 |
|---|---|---|---|---|
| DEV-11 | **包名/目录：`audio-studio/audio_studio/{core,dsp,ui}` vs 契约 `src/hlaudio/{core,dsp,analysis,timeline,project,plugins,batch,ui}`** | 架构 §8 | 目录树实测 | **裁决：保留 `audio_studio` 包名**（364 测试与全部 import 建立其上，改名是纯成本零收益；契约的价值在模块边界而非名字）。但**模块边界必须对齐**：Round 2 新增代码落位 `audio_studio/{timeline,analysis,project}`；`hlaudio` 名称废止，架构契约以本条为准更新 |
| DEV-12 | **DSP 内核签名：`Effect._process_planar(audio(ch,samples), sr)` vs 契约 `FxKernel.prepare(sr, max_block, ch) -> FxState; process(x(frames,ch), state) -> (y, state)`** | 架构附录 A | `dsp/effects/base.py:53`；状态藏在实例属性而非显式 FxState；无 `latency_samples()`；无声明式 `ParamSchema`（只有 `parameters()` 快照） | 折中裁决：**保留 Effect ABC 作为便利层**（其 offline/streaming 一致性测试纪律是正资产），但 Round 2 需补三件事：① `prepare()` 增加 `max_block` 参数（预分配依据）；② 增加 `latency_samples() -> int`（默认 0，PDC 依据）；③ 布局统一——见 DEV-13 |
| DEV-13 | **数组布局分裂：core/ui 用 `(frames, channels)`，dsp 用 planar `(channels, samples)`** | 架构附录 A（`x: ndarray[frames, ch]`） | `core/types.py:98` vs `dsp/effects/base.py:34`；`dsp/util.as_planar` 在边界上反复转置拷贝 | 引擎实时路径挂接 EffectChain 时每块两次转置拷贝不可接受。裁决：**RT 流式路径以 `(frames, channels)` 为唯一布局**（与 ring、设备、SampleSource 一致）；dsp 离线路径可保留 planar 内核但须提供 `process_block_fc(out_inplace)` 零拷贝适配（实施细节交 opus-fast B） |
| DEV-14 | **DSP/UI 未集成** | 架构 §4.1（SpectralView 停靠、EffectsRack 入 render 路径） | `ui/main_window.py` 未 import `spectrogram_widget` 与 `dsp/`；`SpectrogramWidget` 仅测试引用 | Round 2 opus-fast B 任务：Spectrogram 停靠面板 + EffectChain 挂 feeder 路径（**注意：挂 feeder/pump 侧而非 render 回调侧**，效果计算留在非 RT 线程） |
| DEV-15 | **`engine.render()` 内 mute/volume 直读 UI 线程写入的 Python 属性，无参数平滑** | 架构 §4.2 参数平滑（10–50ms 斜坡） | `engine.py:330-332`：`gain` 阶跃生效 | zipper noise；Round 2 在 render 内做每块线性斜坡（预分配 ramp 缓冲），目标 10ms |
| DEV-16 | **无 `.hlproj`/ProjectManager、无峰值 `.pk` 磁盘缓存** | 架构 §5.6/§6 | `core/peaks.py` 为内存金字塔，每次 `set_clip` 重建（`engine.py:135`） | M1 后半启动；峰值磁盘缓存随 §4.1 SampleSource 落地时一并规格化（大文件打开 <2s 依赖它） |

### 1.5 工程与验证基建（S2，对应 G10）

| # | 偏差 | 契约出处 | 现状证据 | 收敛动作 |
|---|---|---|---|---|
| DEV-17 | **CI 不构建、不测试 `audio-studio/`** | 架构 §11 gpt-sol B（CI 矩阵：ruff/mypy/pytest 全仓） | `.github/workflows/audio-tests.yml` 触发路径仅 `tools/** tests/**`，job 仅 `ruff check tools tests` + 根目录 `pytest -q`（7 个边界测试）。**364 个测试从未在 CI 跑过** | §2.3 给出 CI 验证步骤，与 PySide6 迁移同一 PR 落地（迁移正确性本身依赖它） |
| DEV-18 | **无 `THIRD_PARTY_LICENSES.md`** | 审计 R2、架构 §3.5 | 全仓不存在 | 随 §2 迁移 PR 建立初版（PySide6/numpy/scipy/soundfile/sounddevice/libsndfile/PortAudio），后续依赖变更强制同步更新 |

**正资产确认（避免收敛过度）：** ① `AudioOutput` 抽象 + `NullOutput(realtime=False)` 确定性泵送是无头 CI 的正确设计，保留；② `Effect` 的 offline/streaming 等价测试纪律优于契约原文，保留并写回契约；③ `TimeRange` 整型样本时间、`SAMPLE_DTYPE=float32`、core 零 Qt 依赖，均与契约一致；④ `tests/conftest.py` 的确定性引擎 fixture 体系是 §3/§4 验收测试的现成基座。

---

## 2. PySide6 迁移收敛方案

### 2.1 文件级改动 map

改动分四类：**[I]** 仅 import 行、**[S]** import + `pyqtSignal/pyqtSlot` 符号、**[C]** 配置/依赖、**[D]** 文案。每文件列出精确改动面（行号为当前 HEAD `fe13122`）：

| 文件 | 类 | 改动点 |
|---|---|---|
| `audio_studio/ui/main_window.py` | S | L7 `from PySide6.QtCore import Qt, QTimer, Slot`；L8-18 `PyQt6→PySide6`；L339 `@pyqtSlot(object)→@Slot(object)` |
| `audio_studio/ui/waveform_view.py` | S | L19-31 模块替换；L61-64 4× `pyqtSignal→Signal` |
| `audio_studio/ui/transport_bar.py` | S | L5-6 模块替换；L39-44 6× `pyqtSignal→Signal` |
| `audio_studio/ui/track_panel.py` | S | L9-10 模块替换；L34-35, L97-99 5× `pyqtSignal→Signal` |
| `audio_studio/ui/spectrogram_widget.py` | S | L1 docstring、L30-42 模块替换；L106/109/112 3× `pyqtSignal→Signal`；L323（测试辅助内 QPainter import） |
| `audio_studio/ui/time_ruler.py` | S | L5-7 模块替换；L18 `pyqtSignal→Signal` |
| `audio_studio/ui/level_meter.py` | I | L11-13 模块替换 |
| `audio_studio/ui/theme.py` | I | L12 模块替换 |
| `audio_studio/ui/__init__.py` | D | docstring "PyQt6 front-end widgets" → "PySide6 front-end widgets" |
| `audio_studio/app.py` | I | L47-48 模块替换 |
| `tests/conftest.py` | I | L96 模块替换 |
| `tests/test_ui.py` | I | L133 `QPixmap` import 替换 |
| `tests/test_spectrogram_widget.py` | I | L23 `pytest.importorskip("PySide6")`；L25-27, L323 模块替换 |
| `tests/test_dsp_integration.py` | I | L44-45 importorskip + import 替换 |
| `benchmarks/bench_stft.py` | I | L308 模块替换 |
| `pyproject.toml` | C | L28 `"PyQt6>=6.5"` → `"PySide6>=6.6"`；`[tool.pytest.ini_options]` 增加 `qt_api = "pyside6"`（pytest-qt 绑定选择，防止环境残留 PyQt6 时被误选） |
| `requirements.txt` | C | L5 `PyQt6>=6.5` → `PySide6>=6.6`；L10 `PyAudio` 移入注释/可选（DEV-02 同 PR 或紧随 PR 处理均可，但 requirements 不得再默认装 PyAudio） |
| `requirements-dev.txt` | C | 无直接改动（继承 requirements.txt）；确认 `pytest-qt>=4.2` 支持 pyside6 ✓ |
| `README.md`（audio-studio） | D | L10 架构图文案 `PyQt6→PySide6` |
| `.github/workflows/audio-tests.yml` | C | 见 §2.3 |

合计：**19 个文件**，其中机械替换 17 个（36 处模块引用 + 26 处符号重命名），配置 2 个。无一处需要逻辑改写——已逐文件核对，未发现 PyQt6 独有 API（见 §2.2 规则 5 的核对清单）。

### 2.2 import 替换规则（机械可执行，供实现代理直接照做）

1. **模块名：** `PyQt6.QtCore / PyQt6.QtGui / PyQt6.QtWidgets` → 同名 `PySide6.*`。本仓库只用到这三个子模块（已核实，无 QtOpenGL/QtMultimedia）。
2. **信号/槽符号：** `pyqtSignal → Signal`，`pyqtSlot → Slot`（均自 `PySide6.QtCore` import）。本仓库无 `pyqtProperty`、无 `pyqtBoundSignal` 类型标注。`Signal(object)`/`Signal(int)`/`Signal(float, float, float)` 等签名语义在 PySide6 完全一致，`@Slot(object)` 同。
3. **测试跳过守卫：** `pytest.importorskip("PyQt6") → pytest.importorskip("PySide6")`。
4. **禁止兼容垫片：** 不引入 `qtpy`/`QT_API` 抽象层——契约只认 PySide6 一个绑定，垫片属过度设计且引入新依赖。
5. **无需改动项（已逐项核对本仓库代码，均为 Qt6 双绑定一致 API）：** `QAction` 位于 `QtGui` ✓（`main_window.py:8` 已正确）；全限定枚举 `Qt.AlignmentFlag.AlignHCenter`、`QSizePolicy.Policy.*` ✓；`QApplication.exec()`（非 `exec_`，全仓无 `exec_` 调用）✓；`QMouseEvent.position()` 返回 `QPointF` ✓；`QImage`/`QPixmap`/`QPainter`/`QLinearGradient` 构造签名 ✓。**唯一需警惕的语义差**：PySide6 的 `Signal` 在类未实例化前是 `Signal` 描述符而非 `pyqtSignal` 对象——本仓库无对信号对象本身的自省，无影响。
6. **双绑定互斥：** PyQt6 与 PySide6 同进程加载两份 Qt 动态库会段错误。迁移 PR 必须**同时**从所有 requirements/pyproject 移除 PyQt6，且 CI 加静态守卫（§2.3 第 1 步）。开发者本地残留 PyQt6 无害（`qt_api = "pyside6"` 已钉死 pytest-qt），但 `pip uninstall PyQt6 PyQt6-Qt6 PyQt6-sip` 应写入迁移 PR 说明。

### 2.3 CI 验证步骤（与迁移同一 PR 落地，修复 DEV-17）

`.github/workflows/audio-tests.yml` 增加 `audio-studio` job（触发路径追加 `audio-studio/**`），步骤按序：

1. **禁绑定回归守卫（静态）：** `! grep -rn "PyQt6" audio-studio/ --include="*.py" --include="*.toml" --include="*.txt"` —— 命中即 fail。这是防止后续代理凭训练惯性写回 PyQt6 的长效闸门（本次漂移的根因正是实现代理默认习惯）。
2. **安装：** `sudo apt-get install -y libegl1 libgl1 libxkbcommon-x11-0 libsndfile1`（PySide6 offscreen 平台插件的最小系统依赖）+ `pip install -e "audio-studio[dev]"`。
3. **绑定唯一性断言（动态）：** `python -c "import PySide6, sys; assert 'PyQt6' not in sys.modules; import importlib.util; assert importlib.util.find_spec('PyQt6') is None"`。
4. **全量测试：** `QT_QPA_PLATFORM=offscreen pytest audio-studio/tests -q` —— 364 个测试首次入 CI，全绿为迁移完成的唯一判据（tests 侧对 Qt 的使用集中在 conftest/qapp 与 3 个 widget 测试文件，迁移后即为 PySide6 的行为回归验证）。
5. **无头冒烟：** `python -m audio_studio --offscreen --null-audio --exit-after 2`（退出码 0）；随后 `ruff check audio-studio` + `mypy audio-studio/audio_studio`。

**回滚预案：** 迁移为单 commit；若第 4 步出现绑定相关失败且 2 小时内不可定位，revert 该 commit、记录失败细节到本文件附录后重试——不允许「PyQt6/PySide6 混着先跑」的中间态进主干。

---

## 3. EditSession 命令模式 API 规格（冻结）

**落位：** `audio_studio/timeline/`（新增：`chunks.py`、`document.py`、`commands.py`、`undo.py`、`session.py`）。全部零 Qt 依赖；UI 桥接（QUndoStack 镜像）另放 `audio_studio/ui/undo_bridge.py`，不在冻结面内。

**设计原则：** ① 存储不可变（COW），编辑产生新引用表；② 撤销 = 引用表切换，O(1) 时间、O(块引用) 空间；③ Command 是「表切换 + 元数据」的薄壳，可 JSON 序列化供批处理宏复用（架构附录 A `Command` Protocol 的落地形态）。

### 3.1 COW 分块存储

```python
# audio_studio/timeline/chunks.py

CHUNK_FRAMES: Final[int] = 1 << 18            # 2^18 帧/块（架构 §5.2）；末块允许短块

class AudioChunk:
    """不可变 PCM 块。data 为 (frames, channels) float32，
    构造后必须 data.setflags(write=False)——违反即 bug。"""
    __slots__ = ("data", "_hash")
    data: np.ndarray

    def __init__(self, data: np.ndarray) -> None: ...
    @property
    def n_frames(self) -> int: ...
    @property
    def n_channels(self) -> int: ...
    @property
    def nbytes(self) -> int: ...


class ChunkRef(NamedTuple):
    """表项：对块内子区间的引用（零拷贝切片的关键）。"""
    chunk: AudioChunk
    start: int          # 块内起始帧（含）
    length: int         # 引用帧数；0 < length <= chunk.n_frames - start


class ChunkTable:
    """不可变块引用序列 = 一个文档版本的音频内容。
    所有「编辑」都是产生新 ChunkTable 的纯函数；共享未触及的块。"""
    __slots__ = ("_refs", "_cum", "_channels", "_sample_rate")

    def __init__(self, refs: Sequence[ChunkRef], sample_rate: int, channels: int) -> None: ...

    # -- 查询 ------------------------------------------------------------
    @property
    def sample_rate(self) -> int: ...
    @property
    def n_channels(self) -> int: ...
    @property
    def n_frames(self) -> int: ...                       # O(1)，构造时预求和
    def read_into(self, out: np.ndarray, start: int) -> int:
        """把 [start, start+len(out)) 拷入 out，返回实拷帧数。
        二分定位块（_cum 前缀和），零额外分配。这是播放/导出/峰值的唯一读取面，
        使 ChunkTable 可直接适配 §4.1 SampleSource。"""
    def storage_bytes(self) -> int:
        """全表引用的去重块字节数（按 id(chunk) 去重）。U4 验收
        （1000 步撤销 ≤ 2× 源文件）以 UndoStack 全历史的本值度量。"""

    # -- 编辑原语（全部返回新表，self 不变）-------------------------------
    def slice(self, rng: TimeRange) -> "ChunkTable":     # 纯引用调整，零样本拷贝
    def splice(self, at: int, remove: int, insert: "ChunkTable | None") -> "ChunkTable":
        """删除 [at, at+remove) 并在 at 处插入 insert。
        剪切/粘贴/删除/插入静音全部归约到此原语。
        成本 O(触及边界的 ≤2 个块重建 + 引用表拷贝)。"""
    def map_range(self, rng: TimeRange,
                  fn: Callable[[np.ndarray], np.ndarray]) -> "ChunkTable":
        """对 [rng) 内样本应用 fn（增益/淡变/归一化/任意 Effect.process），
        仅重建触及的块，其余共享。fn 接收/返回 (frames, channels) float32；
        fn 不得原位修改输入。"""

    @classmethod
    def from_array(cls, data: np.ndarray, sample_rate: int) -> "ChunkTable": ...
    @classmethod
    def from_source(cls, source: "SampleSource",
                    progress: Callable[[float], None] | None = None) -> "ChunkTable": ...
```

### 3.2 Document 与 Command

```python
# audio_studio/timeline/document.py

class Document:
    """破坏性波形编辑器的可变外壳：持有「当前 ChunkTable」并广播换表事件。
    单写者（UI 线程/批处理线程）；播放侧通过 snapshot() 取不可变引用，天然无锁。"""

    def __init__(self, table: ChunkTable, *, source_path: Path | None = None) -> None: ...

    @property
    def table(self) -> ChunkTable: ...
    def snapshot(self) -> ChunkTable:
        """播放/分析用：返回当前表的不可变引用。之后的编辑不影响已取快照。"""
    def swap(self, new_table: ChunkTable) -> ChunkTable:
        """原子换表，返回旧表。仅允许 EditCommand.do/undo 调用。
        换表后依序触发 change_listeners（峰值失效、播放源热切换等）。"""
    def add_change_listener(
        self, fn: Callable[[ChunkTable, ChunkTable], None]) -> None: ...
        # fn(old, new)；监听器在写者线程执行，必须快速返回


# audio_studio/timeline/commands.py

@runtime_checkable
class EditCommand(Protocol):
    """架构附录 A Command Protocol 的冻结形态。"""
    label: str                                   # UI 撤销菜单文案，如 "Delete Selection"

    def do(self, doc: Document) -> None: ...
    def undo(self, doc: Document) -> None: ...
    def merge_with(self, next_cmd: "EditCommand") -> bool:
        """连续微操作合并（如拖动增益）。合并成功返回 True 并吸收 next_cmd；
        默认实现返回 False。"""
    def to_json(self) -> dict:
        """批处理宏序列化：只序列化「意图参数」（如 {op:"gain", db:-6, range:[a,b)}），
        不序列化块引用。from_json 重放时按参数重新计算。"""
    @classmethod
    def from_json(cls, payload: dict) -> "EditCommand": ...


class TableSwapCommand:
    """通用实现：预计算 after 表，do/undo = O(1) 换表。
    before 在首次 do() 时捕获。所有内建编辑命令
    （SpliceCommand / ApplyEffectCommand / GainCommand / FadeCommand ...）
    继承或组合它；自定义命令只需给出 build(table)->table 纯函数与 to_json 参数。"""
    label: str
    def __init__(self, label: str,
                 build: Callable[[ChunkTable], ChunkTable],
                 params: dict) -> None: ...
    def do(self, doc: Document) -> None: ...     # 首次调用缓存 before/after
    def undo(self, doc: Document) -> None: ...   # doc.swap(self._before)
```

### 3.3 UndoStack 与 EditSession

```python
# audio_studio/timeline/undo.py

class UndoStack:
    """零 Qt 依赖。UI 侧由 ui/undo_bridge.py 镜像到 QUndoStack（仅镜像
    can_undo/can_redo/label 状态，命令本体始终在本栈执行——单一真相源）。"""

    def __init__(self, *, limit: int = 0) -> None: ...   # 0 = 无限（U4 门槛下默认）

    def push(self, cmd: EditCommand, doc: Document) -> None:
        """执行 cmd.do(doc) 并入栈；先尝试与栈顶 merge_with；
        截断 redo 分支；超出 limit 时从栈底逐出（逐出即释放其 before 表引用）。"""
    def undo(self, doc: Document) -> None: ...
    def redo(self, doc: Document) -> None: ...
    @property
    def can_undo(self) -> bool: ...
    @property
    def can_redo(self) -> bool: ...
    @property
    def undo_label(self) -> str | None: ...
    @property
    def redo_label(self) -> str | None: ...
    def set_clean(self) -> None: ...                      # 保存点标记
    @property
    def is_clean(self) -> bool: ...                       # 脏标记 = 窗口标题 '*'
    def clear(self) -> None: ...
    def history_storage_bytes(self) -> int:
        """全历史（含当前表）去重块占用——U4 验收探针。"""
    def add_listener(self, fn: Callable[[], None]) -> None: ...  # 栈状态变更通知


# audio_studio/timeline/session.py

class EditSession:
    """波形编辑器的聚合根：Document + UndoStack + 选区 + 剪贴板。
    UI 与 BatchProcessor 共用此层——批处理 = 无 UI 地 execute 一串 from_json 命令。"""

    def __init__(self, doc: Document) -> None: ...

    doc: Document
    undo_stack: UndoStack
    @property
    def selection(self) -> TimeRange | None: ...
    def set_selection(self, rng: TimeRange | None) -> None: ...

    def execute(self, cmd: EditCommand) -> None: ...      # == undo_stack.push(cmd, doc)

    # 内建高层操作（全部实现为构造命令 + execute，禁止绕过命令层改表）：
    def cut(self) -> None: ...                            # 选区 → 剪贴板 + splice 删除
    def copy(self) -> None: ...
    def paste(self, at: int | None = None) -> None: ...
    def delete_selection(self) -> None: ...
    def crop_to_selection(self) -> None: ...
    def insert_silence(self, at: int, n_frames: int) -> None: ...
    def apply_effect(self, effect: "Effect",
                     rng: TimeRange | None = None) -> None:
        """离线套用 dsp.Effect 到选区（None=全文档）：
        map_range(rng, lambda x: effect.process(x, sr)) 包装为 TableSwapCommand。
        这是 DSP↔编辑层的唯一集成点（DEV-14 收敛路径之一）。"""
```

### 3.4 冻结判据与验收锚点

- **不变量测试（实现必须附带）：** ① 任意命令序列后 `undo × n → redo × n` 得到逐位一致的表内容；② `AudioChunk.data.flags.writeable is False` 全程成立；③ splice/map_range 后未触及块 `id()` 相同（共享验证）；④ 1000 次随机编辑后 `history_storage_bytes() <= 2 × 源字节数`（U4，编辑区间按典型分布 ≤10% 文档长度采样）；⑤ `to_json → from_json → do` 与原命令 `do` 结果逐位一致（D6 的宏一致性变体）。
- **与引擎集成：** `ChunkTable.read_into` 使 Document 可直接包装为 §4.1 的 `SampleSource`——编辑后换表 = 播放源热切换（feeder 下一次 pump 生效），无需停播。
- **明确不在本次冻结面内：** 多轨 Session/Clip/Envelope（DEV-05）、峰值增量失效协议、磁盘 spill（>内存的历史落盘）。它们依赖本层但另行规格。

---

## 4. SampleSource 协议与 lock-free SPSC RingBuffer 替换契约（冻结）

### 4.1 SampleSource 协议

**落位：** `audio_studio/core/sources.py`。**动机（DEV-04）：** 把「音频从哪来」从 `AudioEngine._clip.buffer.data` 切片中抽出，统一内存 / 磁盘流式 / 编辑文档三种来源；feeder 线程面向协议编程。

```python
# audio_studio/core/sources.py

@runtime_checkable
class SampleSource(Protocol):
    """帧寻址的只读音频源。契约：
    - read_into 除首次 open 外零分配（out 由调用方预分配复用）；
    - 单读者：任意时刻至多一个线程调用 read_into（feeder 线程）。
      多读者各自持有独立实例（peaks 扫描线程另开句柄）；
    - RT 禁入：read_into 允许阻塞（磁盘 I/O），因此【禁止】在设备回调中调用；
      回调只从 RingBuffer 读——这是引擎的结构性防线；
    - 错误策略：I/O 失败时零填充 out、返回实读帧数并置 last_error，
      不抛异常穿越 feeder 循环。"""

    @property
    def sample_rate(self) -> int: ...
    @property
    def n_channels(self) -> int: ...
    @property
    def n_frames(self) -> int: ...                        # 未知长度（录音流）返回 -1；MVP 一律已知
    @property
    def exact(self) -> bool: ...                          # True: read_into 无阻塞（内存源）
    @property
    def last_error(self) -> Exception | None: ...

    def read_into(self, out: np.ndarray, start: int) -> int:
        """把 [start, start + out.shape[0]) 拷入 out（(frames, channels) float32,
        C 连续）。返回实拷帧数 n；n < len(out) 表示越尾或出错，[n:] 已零填充。"""
    def close(self) -> None: ...
```

**冻结的实现体清单**（签名同协议，只列构造器）：

| 类 | 构造 | 说明 |
|---|---|---|
| `ArraySource` | `(data: np.ndarray, sample_rate: int)` | 包装现有 `AudioBuffer`；`exact=True`。Round 1 行为的兼容路径 |
| `FileStreamSource` | `(path: Path, *, block_hint: int = 65536)` | `soundfile.SoundFile` 句柄 + `seek`；持句柄常开，`read_into` 内 `sf.read(out=...)` 直填。支持 RF64/BWF（libsndfile 原生）。这是 U1/大文件门槛的承载体 |
| `ChunkTableSource` | `(doc: Document)` | 每次 read 前比较 `doc.table` 引用，变了就换表（播放中编辑热切换）；委托 `ChunkTable.read_into` |
| `RegionSource` | `(inner: SampleSource, region: TimeRange)` | 选区播放组合器 |
| `LoopSource` | `(inner: SampleSource)` | 循环组合器（越尾回卷）；engine 的 loop 逻辑迁入此处 |

**引擎改造点（实现代理照做）：** `AudioEngine` 增加 `set_source(source: SampleSource)`；`set_clip` 重实现为 `set_source(ArraySource(...))`（外部 API 不破坏，364 测试不动）；`_pump_once` 的 `self._clip.buffer.data[pos:pos+n]` 切片改为 `n = source.read_into(self._scratch[:n], pos)`，`self._scratch` 为构造时预分配的 `(block_size, channels)` 缓冲。

### 4.2 lock-free SPSC RingBuffer 替换契约

**落位：** 重写 `audio_studio/core/ring_buffer.py`（同模块名，类名沿用 `RingBuffer`，构造签名兼容——`test_ring_buffer.py` 的既有用例应在最小修订下继续通过；`read(n, pad=True)` 的分配式返回保留为**非 RT 便利方法**，RT 路径一律走新增的 `read_into`）。

```python
class RingBuffer:
    """无锁 SPSC 帧环。线程模型（违反即未定义行为，测试需断言文档化）：
      producer 线程（feeder）：write / write_available / write_into_views
      consumer 线程（设备回调）：read_into / read_available / drop
      任意线程（两端静止时）：clear —— 仅允许在 stop/seek 停泵窗口调用
    正确性机制：
      _write_pos / _read_pos 为【单调递增】的 Python int（不取模存储；
      寻址时 & (capacity-1)，capacity 强制 2 的幂）。
      producer 只写 _write_pos，consumer 只写 _read_pos；
      CPython 下 int 属性 load/store 由 GIL 保证原子且有 happens-before——
      先写数据区、后发布 _write_pos，读侧先读 _write_pos、后读数据区，
      顺序由解释器字节码边界保证。
      【free-threading 注记】nogil 构建（3.13t+）下该保证失效，须改用
      threading 原子或迁移 native 环——已登记为逃生舱评估项（§5.4）。"""

    def __init__(self, capacity: int, channels: int) -> None:
        """capacity 上取整到 2 的幂。缓冲区 (capacity, channels) float32 预分配。"""

    @property
    def capacity(self) -> int: ...
    @property
    def channels(self) -> int: ...

    # ---- producer 端 ----------------------------------------------------
    def write_available(self) -> int:                     # capacity - (w - r)，可能低估，安全
    def write(self, frames: np.ndarray) -> int:
        """拷入 ≤ write_available() 帧，返回实写数；不足不阻塞不覆盖。
        实现：≤2 段 slice 赋值 + 一次 _write_pos 发布（发布必须在数据拷贝之后）。"""

    # ---- consumer 端（RT 回调；本组方法契约为零分配、零锁、O(n) memcpy）----
    def read_available(self) -> int:                      # w - r，可能低估，安全
    def read_into(self, out: np.ndarray) -> int:
        """拷出 ≤ len(out) 帧到 out，返回实读数 n；[n:] 零填充（pad 语义内建）。
        返回 n < len(out) 即 underrun，由调用方计数（§5.1）。"""
    def drop(self, n_frames: int) -> int:                 # 快进丢弃，seek 优化用

    # ---- 停泵窗口 --------------------------------------------------------
    def clear(self) -> None:
        """r = w 归零队列。调用方必须保证两端均已静止（引擎在 seek/stop 时
        先停 feeder、设备回调因 state != PLAYING 已不触环）。"""
```

**从旧实现迁移的行为差异（引擎侧同 PR 适配）：**

| 旧行为 | 新契约 | 引擎适配 |
|---|---|---|
| `read(n, pad=True)` 每次分配返回数组 | `read_into(out)` 零分配 | `render()` 持预分配 `_out_block`，`read_into` 后原位乘 gain（DEV-07） |
| `available_read/available_write` 持锁精确 | 无锁近似（对己方精确、对对方保守低估） | 语义兼容：feeder 「不足一块就等」与回调「不足即 pad」在低估下依然正确 |
| `peek()` 任意线程 | 移除（计量不再从环偷看，改走 §5 遥测槽） | `_update_levels` 移出回调 |
| `clear()` 任意时刻持锁安全 | 仅停泵窗口 | `seek()` 现有实现已在锁内先行清环——改为：置 seek 标记→feeder 停泵→clear→重定位→复泵（实现代理注意此处顺序） |
| `__len__` | 移除（与 available 语义重复） | 测试改用 `read_available()` |

**验收测试（合入门槛）：** ① 双线程 hammer：producer 以随机块长写入单调序列 10⁷ 帧，consumer 随机块长读出，断言序列无缺失、无重复、无撕裂帧（帧内通道值配对校验）；② 环绕边界：capacity±1 处的分段拷贝正确性；③ 分配审计：`read_into`/`write` 在 `tracemalloc` 下增量分配为 0（预热后）；④ 既有 `test_ring_buffer.py` 语义等价用例全绿。

---

## 5. Rust 逃生舱触发条件监控指标

**触发条件（架构 §3.4 原文，不变）：** @48kHz/128 样本、32 轨 × 4 效果场景，回调 **p99 耗时 > 1.33ms**（50% 截止期），或 10 分钟压测 **underrun 率 > 0.1%**。本节定义「怎么量、量什么、谁裁决」。

### 5.1 遥测数据结构（落位 `audio_studio/core/telemetry.py`，随 §4 同 PR 落地）

```python
class CallbackTimer:
    """RT 侧回调耗时直方图。写侧契约：零分配、零锁、O(1)。
    bins: 预分配 int64[128]，对数刻度覆盖 10µs–100ms
      （bin = floor(32 * log2(dt_us / 10))，clip 到 [0,127]）；
    记录：回调入口/出口各一次 perf_counter_ns()，差值入桶 bins[i] += 1，
      同步维护 _count/_max_ns（单写者，无需原子）。
    读侧：snapshot() 在 UI/基准线程 copy-on-read，从直方图重建
      p50/p95/p99/p99.9（桶上界保守插值）与 max。"""

class UnderrunCounter:
    """underrun 双口径（都要，语义不同）：
      block_underruns: read_into 返回 n < 请求帧数的回调次数（率的分子）；
      missing_frames:  累计缺帧数（严重度）；
      device_xruns:    后端上报的 xrun（sounddevice CallbackFlags
                       output_underflow；PyAudio 无此信息——DEV-02 的又一动机）。
    underrun_rate = block_underruns / total_callbacks。"""

class EngineTelemetry:
    """聚合根，挂在 AudioEngine 上。
    snapshot() -> TelemetrySnapshot（冻结 dataclass）：
      callbacks_total, p50_ms, p95_ms, p99_ms, p999_ms, max_ms,
      deadline_ms（block/sr 派生）, headroom_p99（= 1 - p99/deadline）,
      block_underruns, missing_frames, device_xruns, underrun_rate,
      duration_s, sample_rate, block_size, gc_frozen: bool
    reset() 供压测分段。"""
```

**采集点纪律：** 打点包住**整个设备回调**（`output._render` 入口到返回），而非仅 `engine.render()`——numpy→bytes 转换与兜底分支都在截止期内。电平计量（DEV-08）改为：回调内把块 peak²/sum² 写入预分配 float64 槽位（`_meter_slots[ch]`，单写者），UI 定时器 copy-on-read 后开方/求 dB——RT 侧不再构造任何对象。

### 5.2 判决场景与报告 schema

**基准场景（`benchmarks/bench_escape_hatch.py`，gpt-sol A 实现）：** 48kHz / block=128 / 32 立体声轨（合成正弦+噪声，`ArraySource` 排除磁盘变量）× 每轨 4 效果（EQ8 + 压缩 + 延迟 + 增益——P0 集内最重组合），混音求和到主控。CI 冒烟跑 60s（回归趋势），**判决跑 10 分钟且必须在专用参考机（≥4 物理核、无邻户干扰）**——共享 vCPU 容器的 p99 长尾是调度噪声，不构成触发依据；报告须标注 `environment: dedicated | shared`，shared 环境结果一律 `verdict: advisory`。

**报告文件 `benchmarks/reports/escape-hatch-verdict.json`：**

```jsonc
{
  "schema": 1,
  "scenario": {"sr": 48000, "block": 128, "tracks": 32, "fx_per_track": 4,
                "duration_s": 600},
  "environment": {"kind": "dedicated", "cpu": "...", "cores": 4,
                   "python": "3.12.x", "gil": true, "gc_frozen": true},
  "results": {"p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0, "p999_ms": 0.0,
               "max_ms": 0.0, "deadline_ms": 2.667, "budget_ms": 1.333,
               "underrun_rate": 0.0, "device_xruns": 0},
  "thresholds": {"p99_budget_ms": 1.333, "underrun_rate_max": 0.001},
  "verdict": "pass | trigger_escape_hatch | advisory",
  "notes": ""
}
```

### 5.3 判决程序

1. gpt-sol A 产出报告 → fable 审计代理复核环境标注与直方图形状（p99.9/max 离群须解释：GC？页错误？调度？）后裁决。
2. `verdict: trigger_escape_hatch` 时按架构 §3.4 启动 `native/hlrt`（Rust+PyO3），**替换面仅限混音内环与参数平滑**；§4.2 的 `RingBuffer` 接口与 §4.1 `SampleSource` 均已按「可被原生实现镜像」设计（`read_into(out)` 即 Rust 侧 `&mut [f32]` 填充），接口不再变。
3. 触发前的中间档（按序尝试，任一使 p99 回到预算内即止）：块内核 numba JIT → 效果链预编译为扁平 sosfilt 级联 → 计量降采样。**禁止**以增大 block size 的方式「达标」——那是改题目不是解题。

### 5.4 附带评估项

- **free-threading 风险登记：** §4.2 的原子性论证依赖 GIL。若 Round 3 评估 nogil 构建，SPSC 环是第一个必须原生化的组件——记入逃生舱评估范围。
- **报警前置：** `EngineTelemetry` 随 §4 落地后，所有既有播放测试免费获得回调耗时数据；`realtime_engine` fixture 的用例应断言 `underrun_rate == 0`，把实时退化从「Round 2 末基准发现」提前到「任意 PR 单测发现」。

---

## 6. 收敛执行顺序与验收出口（供 orchestrator 对表）

| 序 | 工作包 | 承接 | 内容 | 出口判据 |
|---|---|---|---|---|
| 1 | PySide6 迁移 + CI | opus-fast（任一） | §2 全部：19 文件替换、CI 新 job、绑定守卫、THIRD_PARTY_LICENSES.md 初版 | CI 5 步全绿；仓库零 `PyQt6` 引用 |
| 2 | SPSC + SampleSource + 遥测 | opus-fast A | §4.1/§4.2/§5.1：环重写、sources.py、engine 适配（含 sounddevice 后端 DEV-02、块 256/128、gc 纪律 DEV-09、参数斜坡 DEV-15） | §4.2 四项验收测试 + 既有引擎测试全绿；`FileStreamSource` 播 1h WAV 内存峰值 <200MB |
| 3 | EditSession | opus-fast A | §3 全部 + `ui/undo_bridge.py` + MainWindow 挂 Edit 菜单 | §3.4 五项不变量测试；D6（空操作往返逐位一致）经命令层复验 |
| 4 | DSP/UI 集成 | opus-fast B | DEV-13 布局适配、DEV-14 频谱停靠 + `apply_effect` 走命令层、True Peak 优化 | 频谱面板可视；`apply_effect` 可撤销；集成测试入 CI |
| 5 | 逃生舱判决 | gpt-sol A + fable | §5.2 场景脚本 + 报告 + 裁决 | `escape-hatch-verdict.json` 入库，PROGRESS.md 记录裁决 |

**本文档冻结面：** §3.1–§3.3、§4.1–§4.2 的类/方法签名，§5.2 的 JSON schema。实现中发现签名不可行时，流程是「提议→fable 复核→改本文档→再改代码」，不允许反向。

*— fable（claude-fable-5-thinking-xhigh），Round 2 架构收敛审计子代理（bc-81118806），2026-08-26*
