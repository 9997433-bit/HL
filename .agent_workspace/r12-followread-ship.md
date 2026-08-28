Model slug: claude-opus-5-thinking-high-fast
# Round 12 H1 · 跟读离线模型落库交付 —— 35.31 MiB 进了仓库，`available` 仍是 `false`

> 分支：`cursor/r12-literacy-asr-ship-9f67`；基线 `7c2e6e7`（R12 编排起点，`check:round11` 8/8）。
> 上游：`.agent_workspace/round11-hongen-audit.md` §5.1-1（R12 归属）、
> `apps/literacy-app/public/asr/manifest.json` 的 `freezeChecklist`、
> `.agent_workspace/r11-followread-gonogo.md` §6（从 NO-GO 到 GO 的顺序）。
>
> **结论先行：模型真落库了，结论仍是 NO-GO。**
> R11 交的是「凭什么把 `available` 置成 true」那条路；这一轮交的是那条路上的**头三格**——
> F1 逐文件自托管、F2 许可证核对、F3 整包预算。剩下的七格里，卡死放行的是 F4（儿童冻结集没录）
> 和 F7（真机性能没测）。仓库里现在有 35.31 MiB 的中文流式模型、有一条在 Node 里
> **真解出中文**的引擎回归，孩子那一侧**一个像素都没变**：点「我来读」还是录音回放。
> 这不是保守，是这轮明确要守的那道缝——**落库不等于放行**。

## 1. 这一轮落了什么

| 层 | 文件 | 职责 |
|---|---|---|
| 落库脚本 | `apps/literacy-app/scripts/gen-asr-pack.mjs` | 按写死的 release tag / 模型 revision 取件、改一处胶水、逐文件回写 `manifest.files[]`；`--verify` 只核对不下载 |
| 整包 | `apps/literacy-app/public/asr/models/`（7 个文件 / 35.31 MiB） | sherpa-onnx v1.12.15 WASM 运行时 + zh-14M **int8** 流式 Zipformer transducer |
| 清单 | `public/asr/manifest.json` | `files[]` 逐项 path/role/bytes/sha256；新增 `source.files[]` 记上游 URL + **上游** sha256 + 许可证 + 改动说明 |
| 引擎回归 | `scripts/test-asr-engine.mjs`（`npm run test:asr:engine`） | 按 Worker 的装法在 Node 里真起引擎，喂一条真实中文语音，出转写 / 字符召回 / 桌面 RTF |
| 接线 | `src/workers/sherpaAsrWorker.js`、`src/utils/offlineAsr.js` | 对上真实产物形状；`parseManifest` 从查 2 个角色改成查 7 个；新增 `packAssetUrl()`（整包文件按站点根相对路径取） |
| 浏览器回归 | `scripts/smoke.mjs`（`ROUND12_H1_SMOKE`） | 首屏 0 次模型请求、同源可取且字节对得上、`available=false` 时界面照旧停在录音档 |
| 合规 | `THIRD_PARTY_NOTICES.md` 第二节 | 逐文件出处表 + Apache-2.0 第 4(b) 条要求的修改说明 |

复跑：

```bash
npm --prefix apps/literacy-app run verify:asr:pack   # 7 个文件逐项核 sha256，整包 35.31 MiB
npm --prefix apps/literacy-app run test:asr:engine   # 8/8：装得起来 + 解得出中文 + RTF
npm --prefix apps/literacy-app run test:asr:evalset  # 26/26 + 7 场故障演练 + Go/No-Go 表
npm --prefix apps/literacy-app run test:speech       # 18/18
npm --prefix apps/literacy-app run build && npm --prefix apps/literacy-app run smoke
npm run check:round12 && npm run check:round11       # H1 绿；R11 8/8 不退化
```

## 2. 选型：为什么是 zh-14M int8

预算是 60 MiB，而整包不只有模型——WASM 运行时本身就占 11 MiB。逐个量过：

| 候选 | int8 整包 | 判 |
|---|---|---|
| **zh-14M streaming zipformer**（`csukuangfj/sherpa-onnx-streaming-zipformer-zh-14M-2023-02-23`） | encoder 20.62 + decoder 1.80 + joiner 1.71 + tokens 0.05 = **24.18 MiB** | **选中**，加运行时 11.13 MiB 共 35.31 MiB |
| bilingual zh-en 2023-02-20 | int8 encoder 单文件就 **173.5 MiB** | 出局，超预算近 3 倍 |
| 官方 wasm asr 整包（带 `.data`） | `.data` 里是 182 MiB 英文大模型 | 出局；且整包会退化成一个不透明大 blob，逐文件 sha256 无从谈起 |

许可证：运行时与模型上游都标 Apache-2.0（模型卡一手核对），已写进 `THIRD_PARTY_NOTICES.md`
并逐文件列出上游 sha256。模型权重由上游从
`marcoyang/sherpa-ncnn-streaming-zipformer-zh-14M-2023-02-23` 导出，本项目未二次训练、未改权重。

### 2.1 为什么胶水被改了一处，以及怎么保证只改了这一处

官方 WASM 产物是 `emcc --preload-file` 打出来的：模型被压进配套的 `.data`，
每个文件的字节区间**写死在胶水 JS 的 `loadPackage({...})` 里**。我们不要那份 182 MiB 的英文
`.data`，于是把元数据换成空包（`{"files":[],"remote_package_size":0}`），
改由 Worker 在 `onRuntimeInitialized` 之后用 `FS_createDataFile` 把中文 int8 模型写进 MEMFS。

这么做换来的是**逐文件 sha256**：七个文件各自可核、可换、可追溯，而不是一个 25 MiB 的黑盒。
代价是胶水不再与上游逐字节相同，所以三处一起守着：

- `gen-asr-pack.mjs` 只做一次正则替换，发现胶水里有第二处 `loadPackage` 就拒绝改；
- `manifest.source.files[]` 同时记着改动前的 `upstreamSha256` 和落库后的 `sha256`；
- `test-asr-engine.mjs` 有一条断言：胶水里 `loadPackage(` 只许出现一次，且必须是空包形态。

## 3. 引擎实跑（`test-asr-engine.mjs`，8/8）

装法与 `sherpaAsrWorker.js` 的 `boot()` 完全一致——非 MODULARIZE 胶水用 `new Function` 递
`Module`、`getPreloadedPackage` 返回空 buffer、模型运行时写进 MEMFS、
`createOnlineRecognizer` 从 asr-api 那份 JS 里取。两边哪天走岔，这里先红。

| 项 | 实测（Node v22.14.0 / 桌面 Linux VM，单线程，连跑 4 次） |
|---|---|
| 引擎启动（含 11 MiB wasm 编译 + 写 4 个模型进 MEMFS） | **72–96 ms** |
| 建识别器（onnxruntime 载入 int8 三件套） | **1373–1509 ms** |
| 解码 5.61 秒音频 | **254–349 ms** |
| 桌面实时因子 RTF | **0.045–0.062** |
| 转写 | `对我做了介绍那么我想说的是大家如果对我的研究感兴趣呢` |
| 逐字对齐字符召回（对上游公布参考） | **100.0%**（25/25 字） |

**这不是模型指标，请不要拿去填五层门槛。** 音频是上游模型仓库自带的示例
（成人普通话，Apache-2.0，sha256 记在 `manifest.source.engineFixture`）。它回答的是四个问题：

1. 落库的这 35 MiB 装得起来吗——装得起来，且**全程零网络请求**（harness 把 `fetch` 换成会抛的替身）；
2. 中文流式 transducer 的解码路径通不通——通，出来的是纯汉字，不是空串也不是乱码；
3. 引擎输出接得进 `speechEval` 的逐字对齐吗——接得进，召回算得出来；
4. 桌面这一档的性能量级——RTF 在 0.05 上下，离真机门槛（≤0.5）还有一个数量级的余量；
   但**「建识别器」那 1.4 秒**是真机上最值得盯的一格：低端 Android 的 onnxruntime
   初始化只会更慢，而 R9 §5 给降档留的预算总共就 2 秒。

第 4 点是这一轮新暴露的风险，写在这里不是为了好看：**冷启动很可能是真机上第一个撞线的门槛，
不是识别精度。** 真机测的时候先量它。

## 4. 五层门槛实测表（R12 复算，`test-asr-eval-set.mjs` 现算）

「实测」一栏只填这一轮真跑出来的数。**加粗**是本轮新增或改变的格。

| 层 | 门槛 | 阈值 | R11 实测 | **R12 实测** | 判定 | 谁来测 |
|---|---|---|---|---|---|---|
| 文本层 | `quietCharRecall` | ≥ 0.90 | — | —（模拟 0.955） | 未实测 | 冻结集 |
| 文本层 | `noisyCharRecall` | ≥ 0.80 | — | —（模拟 0.900） | 未实测 | 冻结集 |
| 文本层 | `missDetectionRecall` | ≥ 0.85 | — | —（模拟 1.000） | 未实测 | 冻结集 |
| 文本层 | `silenceFalseAccept` | ≤ 0.01 | — | —（模拟 0.000） | 未实测 | 冻结集 |
| 诊断层 | `toneNearPrecision` | ≥ 0.90 | — | — | 未实测 | 冻结集 |
| 诊断层 | `subgroupGap` | ≤ 0.10 | — | — | 未实测 | 冻结集 |
| 性能层 | `p95LatencyMs` | ≤ 2500 ms | — | — | 未实测 | 中档 Android 真机 |
| 性能层 | `rtf` | ≤ 0.50 | — | —（桌面 **0.045–0.062**，不计入） | 未实测 | 中档 Android 真机 |
| 性能层 | `peakMemoryMiB` | ≤ 300 MiB | — | — | 未实测 | 中档 Android 真机 |
| 性能层 | `longTaskMs` | ≤ 100 ms | — | — | 未实测 | 中档 Android 真机 |
| 资源层 | `packBytesMiB` | ≤ 60 MiB | —（清单里还没有文件） | **35.31** | **达标** | harness |
| 资源层 | `precacheModelBytes` | ≤ 0 | 0 | **0**（口径改了，见 §5） | 达标 | smoke |
| 资源层 | `offlineRestartPass` | ≥ 20/20 | — | — | 未实测 | 中档 Android 真机 |
| 可靠性层 | `faultDrillsProtocol` | ≥ 5 类 | 5/5 | 5/5 | 达标 | harness |
| 可靠性层 | `degradeMs` | ≤ 2000 ms | 610 ms | **601 ms** | 达标 | harness |
| 可靠性层 | `faultDrillsOnDevice` | ≥ 5 类 | — | — | 未实测 | 中档 Android 真机 |
| 可靠性层 | `crossOriginRequests` | ≤ 0 | 0 | **0** | 达标 | harness + smoke |

**层级结论：资源层从「未实测」翻成两条达标一条待真机；文本层 / 诊断层 / 性能层原地不动。**
整体仍 **NO-GO**。

## 5. 冻结清单：3/10（R11 是 0/10）

| # | 层 | 事项 | R11 | **R12** | 证据 |
|---|---|---|---|---|---|
| F1 | license | 冻结 URL / SHA-256 / tokens / 量化档并自托管 | todo | **done** | `files[]` 七角色齐全 + `source.files[]` 逐项上游 sha256；`test-asr-engine` 每次现核 |
| F2 | license | 许可证核对 + NOTICES + SBOM | todo | **done** | 双方 Apache-2.0；NOTICES 第二节逐文件表 + 修改说明 |
| F3 | resource | 整包 ≤60 MiB 且不进首屏 precache | doing | **done** | 实测 35.31 MiB；smoke 量到首屏 0 次模型请求 |
| F4 | eval-set | 儿童冻结集 ≥300 条、双标注、说话人隔离 | todo | todo | **卡放行的第一格** |
| F5 | text | 文本层四条门槛达标 | todo | todo | 等 F4 |
| F6 | diagnosis | tone/near 精确率、子组差距 | todo | todo | 不阻塞放行 |
| F7 | performance | 真机 P95 / RTF / 内存 / 长任务 | todo | todo | **卡放行的第二格**；先量冷启动 |
| F8 | reliability | 五类故障 2 秒内降档 | doing | doing | 接线层 5/5；真机 0/5 |
| F9 | resource | 暂停重试 / 离线重启 20-20 / 缓存自愈 | todo | todo | 整包作废路径已由 D6 覆盖 |
| F10 | governance | 换模型即换版本，重跑冻结集 | doing | doing | `modelVersion` 现在与上游 revision + release tag 绑定（`2023-02-23+wasm1.12.15`） |

### 5.1 两条规矩在这一轮改了口径，得说清楚

R11 有两条断言在「仓库里一个模型字节都没有」的前提下是对的，模型落库之后它们挡的是正确的事。
两条都不是放松，是把「守什么」说得更准：

**其一：`available=false` 时 `files[]` 必须为空 → 改成 `files[]` 必须逐项核得上。**
旧规矩把「落库」和「放行」硬绑在一起，结果只剩两条路：要么不落库，要么提前放行——
而 R12 要做的恰恰是第三条。新规矩：`files[]` 随时可以齐全，但每一项都要在磁盘上
bytes / sha256 对得上、七角色齐全、整包不超预算；**`available` 仍旧只由 Go/No-Go 说了算**
（`test-asr-eval-set.mjs` 最后那条「清单结论要和实测结论一致」原样保留，
smoke 里「冻结项没做完 available 必须是 false」也原样保留）。

**其一点五：`files[].path` 从「`public/asr/` 内相对」改成「站点根相对」（`asr/models/…`）。**
以前只有运行时一个消费者，怎么写都行；现在落库校验（harness）、构建产物核对（smoke）、
门禁探针三处都要按「这个文件被发出去的那个路径」去找它。写成发出去的样子，
三处不用各自心算一遍前缀。`parseManifest()` 顺手把它变成一条硬约束：
路径必须以 `asr/` 开头，`ocr/chi_sim.traineddata.gz` 这种同源但不属于本包的路径也一律拒绝。

**其二：`dist/asr` 里不许有第三个文件 → 改成分三条量。**
那条断言的**意图**从来不是「包里没有模型」，而是「没人替访客提前下载它」。落库之后
按意图重写成四条，比原来严：① `dist/asr` 顶层仍只有 `manifest.json` 与 worklet，
模型一律在 `models/` 下；② `models/` 的字节数必须与清单 `files[]` 的声明**完全相等**
（发出去的和冻结的不是同一份，当场红）；③ 整包 ≤60 MiB；④ 首屏跑完，
浏览器对 `asr/models/` 的请求数必须是 **0**。

## 6. `ROUND12_H1_SMOKE` 验到了什么（浏览器，真产物）

跑在 `dist` 上、走真实路由的一条交互用例，实测输出：

```
整包 35.31 MiB / 7 个文件（7 个角色），首屏 0 次模型请求；抽验 sherpa-onnx-asr.js、encoder.int8.onnx 同源可取且字节对得上；available=false，档位 recording→recording，0 个跨源请求
```

逐条对应：**首屏 0 次模型请求**（家长不点，一个字节都不动）；
**抽最大和最小两个文件按同源地址真取一次**，取回的字节数必须与清单一致
（路径写错或漏发就红）；**七个角色齐全、每项 sha256 是 64 位十六进制**；
**`available=false` 时档位停在 `recording`、入口上写的还是「下载」**；
家长真点一次下载——这一版清单不放行，界面必须落到 `failed`、给出原因、
不许替家长打开浏览器识别，**全程 0 个跨源请求**。

## 7. 从这里到 GO，还剩什么

顺序没变（`r11-followread-gonogo.md` §6），但起点前移了两格：

1. ~~选模型、冻结、自托管~~ —— **本轮完成**（F1/F2/F3）。
2. **录冻结集**（F4）。按 `.agent_workspace/r11-asr-eval-set.md` 录到 300 条、双标注仲裁完成。
   到位之后 `test-asr-eval-set.mjs` 把 `clips[].mock` 换成本轮这套引擎的真实输出，
   文本层四个数当场就出来——算分管线 R11 已经验过，等的只是数据。
3. **上真机**（F7/F8/F9）。**先量冷启动**：本轮桌面上光「建识别器」这一步就要 1.4 秒上下，
   低端 Android 只会更慢，而降档预算是 2 秒。其次才是 P95 / RTF / 内存 / 离线重启 20/20。
4. **再判一次**。harness 输出 `go` 之后，才允许把十条冻结项改成 done、`available` 改 `true`。

想抄近路的走法只有一条——把 `available` 直接改成 `true`。它改不动：
`test-asr-eval-set.mjs` 会要求十条全绿 + `parseManifest()` 过 + 本次实测结论也是 `go`，
smoke 还会在浏览器里再核一遍。这一轮往包里塞了 35 MiB，那道锁一点没松。

## 8. 这一轮的实测环境

- Node v22.14.0；Chromium headless（smoke）；桌面 Linux VM，无真机、无 Android SDK。
- `test-asr-engine.mjs`：8/8。`test-asr-eval-set.mjs`：26/26 + 7 场故障演练。
- `test-speech-eval.mjs`：18/18（清单夹具跟着长到七角色，另加三条缺角色必须被拒的用例）。
- `smoke.mjs`：164 条路由 + 39 项交互，0 项有问题；`ROUND11_H1` 与 `ROUND12_H1` 均通过。
- `check:round12`：H1 ✓。`check:round11`：8/8 不退化。
- 真机项一律 `[SKIP owner: Android QA]`：性能层四条、`offlineRestartPass`、`faultDrillsOnDevice`。
