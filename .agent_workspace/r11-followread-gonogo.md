Model slug: claude-opus-4-6-20260421
# Round 11 H1 · 跟读产品化 Go/No-Go —— 五层门槛实测表

> 分支：`cursor/r11-literacy-followread-prod-9f67`；基线 `4236625`（R10 闭合 8/8）。
> 上游：`.agent_workspace/r9-followread-asr-evaluation.md` §5（门槛定义）、
> `.agent_workspace/r10-followread-v3-spike.md` §5（转生产前必须补齐的五条）。
> **结论先行：NO-GO，卡在 15 处。** 模型仍然一个字节都没进仓库，`available` 保持 `false`，
> 跟读在真机上继续走录音档。这一轮补的不是模型，是**判定这件事的那条路**：
> 冻结清单从五句话变成十条带证据、带阻塞项的结构化条目；评测集有了 36 条占位骨架
> （可扩到 300）和一个真能跑的聚合器；五层门槛第一次有了「谁来测、测出多少」的实测表。

## 1. 这一轮交付了什么

| 层 | 文件 | 职责 |
|---|---|---|
| 冻结清单 | `apps/literacy-app/public/asr/manifest.json` | `freezeChecklist` 10 条（id / layer / must / evidence / status / blocks）+ `goNoGo` 五层阈值表 + `evalSet` 指向评测集与本文档 |
| 评测集骨架 | `apps/literacy-app/scripts/data/asr-eval-set.json` | 12 个说话人 / 36 条占位片段，dev·threshold·final 说话人隔离，8 类异常齐全，目标 300 条 |
| 评测跑道 | `apps/literacy-app/scripts/test-asr-eval-set.mjs` | 24 项断言 + 7 场故障演练；算指标、算 Go/No-Go，`--json` 出机读报表 |
| 浏览器回归 | `apps/literacy-app/scripts/smoke.mjs`（`ROUND11_H1`） | 构建产物里的那一份清单：页面读得到、结构完整、`available=false` 时界面不冒充可用、`dist/asr` 模型字节为 0 |
| 评测集设计 | `.agent_workspace/r11-asr-eval-set.md` | 300 条怎么录、怎么标、怎么扩，以及为什么占位阶段不放音频 |

复跑：

```bash
npm --prefix apps/literacy-app run test:asr:evalset          # 24/24 + 7 场演练 + Go/No-Go 表
npm --prefix apps/literacy-app run test:asr:evalset -- --json # 机读报表
npm --prefix apps/literacy-app run test:speech                # 19/19（含新增的麦克风优先级断言）
npm run check:round11 && npm run check:round10                # H1 绿；R10 8/8 不退化
```

## 2. 五层门槛实测表（2026-08-27，`test-asr-eval-set.mjs` 现算）

「实测」一栏只填**这一轮真跑出来的数**。需要真模型或真机的一律留空——
括号里的模拟值是用占位条目的模拟转写跑出来的，**它证明的是算分管线通不通，不是模型好不好**，
所以一概不参与判定（详见 §4）。

| 层 | 门槛 | 阈值 | 实测 | 判定 | 谁来测 |
|---|---|---|---|---|---|
| 文本层 | `quietCharRecall` 安静集字符召回 | ≥ 0.90 | —（模拟 0.955） | 未实测 | 冻结集 |
| 文本层 | `noisyCharRecall` 噪声集字符召回 | ≥ 0.80 | —（模拟 0.900） | 未实测 | 冻结集 |
| 文本层 | `missDetectionRecall` 漏字检出召回 | ≥ 0.85 | —（模拟 1.000） | 未实测 | 冻结集 |
| 文本层 | `silenceFalseAccept` 静音误判率 | ≤ 0.01 | —（模拟 0.000） | 未实测 | 冻结集 |
| 诊断层 | `toneNearPrecision` tone/near 精确率 | ≥ 0.90 | — | 未实测 | 冻结集 |
| 诊断层 | `subgroupGap` 子组与总体最大差距 | ≤ 0.10 | — | 未实测 | 冻结集 |
| 性能层 | `p95LatencyMs` 句末到结果 P95 | ≤ 2500 ms | — | 未实测 | 中档 Android 真机 |
| 性能层 | `rtf` 实时因子 | ≤ 0.50 | — | 未实测 | 中档 Android 真机 |
| 性能层 | `peakMemoryMiB` 峰值新增内存 | ≤ 300 MiB | — | 未实测 | 中档 Android 真机 |
| 性能层 | `longTaskMs` 主线程最长任务 | ≤ 100 ms | — | 未实测 | 中档 Android 真机 |
| 资源层 | `packBytesMiB` 整包体积 | ≤ 60 MiB | —（清单里还没有文件） | 未实测 | harness |
| 资源层 | `precacheModelBytes` 进首屏预缓存的模型字节 | ≤ 0 | **0** | 达标（smoke） | smoke |
| 资源层 | `offlineRestartPass` 完整离线重启 | ≥ 20/20 | — | 未实测 | 中档 Android 真机 |
| 可靠性层 | `faultDrillsProtocol` 接线层故障演练覆盖 | ≥ 5 类 | **5/5** | 达标 | harness |
| 可靠性层 | `degradeMs` 最慢一次降档 | ≤ 2000 ms | **610 ms** | 达标 | harness |
| 可靠性层 | `faultDrillsOnDevice` 真机复演 | ≥ 5 类 | — | 未实测 | 中档 Android 真机 |
| 可靠性层 | `crossOriginRequests` 跨源请求 | ≤ 0 | **0** | 达标 | harness + smoke |

`precacheModelBytes` 由 smoke 在构建产物上验：`dist/asr` 里除了 `manifest.json`
和 `pcm-capture.worklet.js` 不许有第三个文件，`dist/sw.js` 的预缓存清单里不许出现
`asr/models/`。这一条现在是真的量出来的 0，不是「配置里写了 exclude」。

**层级结论：文本层 / 诊断层 / 性能层 / 资源层 未实测，可靠性层四条里三条达标、真机复演未做。**
整体 **NO-GO**。

## 3. 故障演练（接线层，7 场）

R9 §5 要求五类故障都在 2 秒内落到 `recording` / `listen-only` 且不触网兜底。
真机复演要等模型到位，但**降档逻辑本身现在就能验**：harness 用 `fetch` / `CacheStorage` /
`Worker` 的替身在 Node 里跑 `offlineAsr.js` 这一层，每一场都量了耗时。

| # | 故障类 | 结果 | 耗时 |
|---|---|---|---|
| D1 | 飞行模式 | `probe=unavailable` → `recording`，0 个跨源请求 | 0 ms |
| D2 | 模型 404 | `models/engine.wasm 下载失败（HTTP 404）`，缓存清空 → `recording` | 150 ms |
| D3 | wasm 初始化失败 | Worker 报 error，`ready` 拒绝 → `recording`（家长此前打开过浏览器识别也不改用） | 0 ms |
| D4 | 麦克风拒绝 | → `listen-only`；**离线包已装好也一样** | 0 ms |
| D5 | 低内存杀 Worker | 收尾拿回半句「床前」并标 `degraded` → `recording` | 610 ms |
| D6 | 整包指纹不符（资源层附加） | `指纹对不上，整包作废`，缓存清空 | 9 ms |
| D7 | 正向对照（资源层附加） | 清单齐全 → 2 个文件校验通过 → 探测转 `ready` → 升到 `offline-asr` | 12 ms |

D7 是这套跑道最要紧的一场：它证明「模型来了以后这条路是通的」——
装包、逐文件核 sha256、版本化缓存命名、探测转 ready、档位升到离线，一步都不缺。
现在之所以停在 no-go，是因为没有模型和冻结集，不是因为路没修好。

**演练里发现并修掉的一处真问题**（D4）：`chooseTier()` 原来把 `offlineReady`
排在麦克风判定之前，于是「离线包装好了 + 家长拒绝麦克风」会停在 `offline-asr`——
没有音频却进识别档，孩子读完会拿到一个凭空的 0 分。现在没有麦克风一律先落 `listen-only`
（`src/utils/offlineAsr.js`），`test-speech-eval.mjs` 加了一条断言钉住。

## 4. 管线自检（模拟转写）——为什么它不算模型指标

| 指标 | 模拟值 | 分母 |
|---|---|---|
| 安静集字符召回 | 95.5% | 88 字 |
| 噪声集字符召回 | 90.0% | 60 字 |
| 漏字检出召回 | 100.0% | 6 个设计漏字 |
| 静音误判率 | 0.0% | 6 条无人朗读样本 |

这些数字是拿占位条目里**我们自己写的**模拟转写喂给真正的聚合器算出来的。
换任何模型它们都不会变，所以它们回答不了「这个模型行不行」。它们回答的是另外四个问题，
而这四个问题在真数据到位之前必须先有答案：

1. 安静集和噪声集有没有被分开算（88 字 / 60 字两个独立分母）；
2. 「孩子漏了哪几个字」能不能被逐字对齐原样标出来（6/6）；
3. 没出声的样本会不会被夸（0/6 —— 一条都不许）；
4. 聚合器对退化敏不敏感：把识别结果换成空串，召回立刻掉到 0，不会自说自话。

真模型接上以后，把 `clips[].mock` 换成引擎输出、`status` 改 `recorded`、补上双标注仲裁，
同一段代码直接出真实指标——报表里的「模拟」列会消失，「实测」列才填得上。

## 5. 冻结清单状态（0/10 完成）

| # | 层 | 事项 | 状态 | 阻塞 |
|---|---|---|---|---|
| F1 | license | 冻结模型 URL / SHA-256 / tokens / 量化档并自托管 | todo | `available=true` |
| F2 | license | 许可证核对 + THIRD_PARTY_NOTICES + SBOM | todo | `available=true` |
| F3 | resource | 整包 ≤ 60 MiB 且不进首屏 precache | doing（precache 侧已由 smoke 量到 0） | `available=true` |
| F4 | eval-set | 录制 + 双标注 ≥300 条，三份说话人隔离 | todo | `available=true` |
| F5 | text | 文本层四条门槛达标 | todo | `available=true` |
| F6 | diagnosis | tone/near 精确率 ≥90%、子组差距 ≤10 pp | todo | 逐字声调展示（不阻塞发布） |
| F7 | performance | 真机 P95 / RTF / 内存 / 长任务 | todo | `available=true` |
| F8 | reliability | 五类故障 2 秒内降档 | doing（接线层 5/5，真机 0/5） | `available=true` |
| F9 | resource | 暂停重试 / 离线重启 20-20 / 损坏缓存自愈 | todo（整包作废路径已由 D6 覆盖） | `available=true` |
| F10 | governance | 换模型即换版本，重跑冻结集，不与旧分横比 | doing | `available=true` |

清单和结论是**互锁**的，三处都由自动化守着：只要还有一条带 `available=true` 阻塞的项没做完，
`available` 必须是 `false`、`goNoGo.verdict` 必须是 `no-go`、`files[]` 必须是空的。
谁想把 `available` 改成 `true`，harness 会当场要求这十条全绿、清单过 `parseManifest()` 校验、
且这次实测算出来的结论也是 `go`——想靠改一个布尔值发布是改不动的。

## 6. 从 NO-GO 到 GO 的顺序

1. **先录音，后选模**。冻结集不到位，模型比选就是在比谁更会讨好成人朗读。
   按 `.agent_workspace/r11-asr-eval-set.md` 的口径录到 300 条、双标注仲裁完成（F4）。
2. **冻结候选模型**（F1/F2）：sherpa-onnx 中文流式 Zipformer 打头，Vosk 42 MB 与
   whisper.cpp 量化档做对照；三者都只填 `files[]` + sha256，跑完再决定哪个进包。
3. **跑文本层**（F5）：`test-asr-eval-set.mjs` 把 `mock` 换成引擎输出即可出表。
   文本层过、诊断层不过，仍可发「离线逐字跟读（实验）」，但只显示命中/漏读。
4. **上真机**（F7/F8/F9）：中档 Android 跑性能与五类故障复演、离线重启 20/20。
5. **再判一次**：harness 输出 `go` 之后，才允许把十条冻结项改成 `done`、`available` 改 `true`。

顺序不能倒。倒过来最省事的走法——先把模型塞进包里再补证据——正是这一轮明确拒绝的那条路。

## 7. 这一轮的实测环境

- Node v22.14.0；Chromium headless（smoke）；桌面 Linux，无真机。
- `test-asr-eval-set.mjs`：24/24 项通过，7 场演练，总耗时 < 1 s。
- `test-speech-eval.mjs`：19/19（新增麦克风优先级断言 1 条）。
- `smoke.mjs`：`ROUND11_H1` 通过 —— 冻结清单 0/10、五层门槛齐全、结论 `no-go`、
  `available=false`、`dist/asr` 模型字节 0、档位 `recording`。
- `check:round10`：8/8 不退化；`check:round11`：H1 ✓。
