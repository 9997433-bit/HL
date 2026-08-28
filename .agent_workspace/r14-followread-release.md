Model slug: claude-opus-4-6 (opus-fast)
# Round 14 H1 · 跟读放行判定 —— **NO-GO，卡在 12 处**

> 分支：`cursor/r14-literacy-asr-finalize-9f67`；基线 `cursor/openmoji-integration-9f67` @ `c33caf4`。
> 上游：`r11-followread-gonogo.md`（五层门槛定义）· `r12-followread-ship.md`（模型落库）·
> `r13-asr-freeze-set.md`（冻结集骨架）· `r13-asr-android-rtf-baseline.md`（主机 RTF）·
> `r14-asr-recording-batch1.md`（批次 1 派工与落库闸）。
> 跑道：`apps/literacy-app/scripts/test-asr-eval-set.mjs`（`ROUND14_H1`，49 项 + 7 场演练）。
>
> **`available` 仍是 `false`，实录仍是 `0/300`，真机仍是一台没跑。**
> 这一轮交的不是录音，是**放行这件事的收货台**：一份放行文档（就是这份）、
> 一道真机 RTF 证据的防伪闸、一次用合成音跑通的落库演练。
> 三样都不能让 `available` 动一下——这正是它们要证明的事。

## 1. 这一轮改变了什么

R14-1 结束时，H1 的三条腿是这样的：放行文档**不存在**（探针回退去找 R13 的同名文件，
也不存在）；真机 RTF 证据**不存在**（探针读不到文件，那条腿红）；落库管线**跑不通**——
不是坏了，是从来没被真数据执行过：`--verify-audio` 需要受控目录里的音频文件，
而 CI 上一个字节都没有（`r14-asr-recording-batch1.md` §8 记下的债）。

| | R14-1 结束时 | 这一轮结束时 | 还差什么 |
|---|---|---|---|
| 放行文档 | 无 | **本文件**：五层门槛逐条列表 + 十条冻结项 + 放行顺序 | 表里 12 条仍是「未实测」 |
| 真机 RTF | 无文件 | `evidence/r14/asr/device-rtf.json`（**诚实占位**）+ schema + 模板 + 收货台 | 一台真机 |
| 落库管线 | 只有内存自检 | **合成音走查 12 条**：真 wav、真 sha256、真指纹核对 + 6 条负向 | 真录音 |
| 实录 | 0/300 | **0/300** | 录音本身 |
| `available` | false | **false** | 上面全部 |

第二、三行是这一轮真正的东西，而它们的价值恰恰在于**没有**把第四、五行推动一格。

### 1.1 为什么要给 H1 加收货台

`scripts/check-round14.mjs` 的 H1 有四条腿。其中两条读的是文本和数字：

- **放行文档腿**：文档 >600 字、含 `ROUND14_H1`、含 `GO`，且几个关键词附近没有 `NO-GO`。
- **真机 RTF 腿**：`evidence/r14/asr/device-rtf.json` 里 `onDevice:true`、`simulated:false`、
  `device` 有身份、`rtfP95` 落在 0–0.5。

**第二条那五个字段，谁都能在十秒钟内敲出来。** 探针不是不好，是它只能读表面；
一个只读表面的门槛，迟早会变成「把表面写对」的练习。所以这一轮给两条腿各配一道更严的闸，
两道闸都长在 harness 里（`test-asr-eval-set.mjs` 第 2d 段 + 两条 post）：

| 腿 | 探针看什么 | 收货台另外要什么 |
|---|---|---|
| 真机 RTF | 五个字段 | 整包指纹对账、具体机型 + 序列号哈希、≥20 句 ≥60 秒、`rtfP95` 与 `rtf.p95` 互为镜像、六条门槛自洽、adb 日志落盘、签字 |
| 放行文档 | 有没有 `GO` 字样 | **实录不到 300 条时，文档里不许出现探针认的那几个段落锚点词**（见 §8） |

不变式只有一条：**能让探针那条腿变绿的文件，在收货台必须零错误。**
harness 拿一份「只填五个字段」的伪证撞它——探针会绿，收货台会红，于是 harness 红。

## 2. 五层门槛（`test-asr-eval-set.mjs` 现算，2026-08-28）

「实测」一栏只填**这一轮真跑出来的数**。需要真模型、真录音或真机的一律留空；
括号里的模拟值是拿占位条目的模拟转写跑出来的，**证明的是算分管线通不通，不是模型好不好**；
主机值来自 R13 在这台共用 VM 上的基准，同样不参与判定。

| 层 | 门槛 | 阈值 | 实测 | 判定 | 谁来测 |
|---|---|---|---|---|---|
| 文本层 | `quietCharRecall` 安静集字符召回 | ≥ 0.90 | —（模拟 0.967） | 未实测 | 冻结集 |
| 文本层 | `noisyCharRecall` 噪声集字符召回 | ≥ 0.80 | —（模拟 0.905） | 未实测 | 冻结集 |
| 文本层 | `missDetectionRecall` 漏字检出召回 | ≥ 0.85 | —（模拟 1.000） | 未实测 | 冻结集 |
| 文本层 | `silenceFalseAccept` 静音误判率 | ≤ 0.01 | —（模拟 0.000） | 未实测 | 冻结集 |
| 诊断层 | `toneNearPrecision` tone/near 精确率 | ≥ 0.90 | — | 未实测 | 冻结集 |
| 诊断层 | `subgroupGap` 子组与总体最大差距 | ≤ 0.10 | — | 未实测 | 冻结集 |
| 性能层 | `p95LatencyMs` 句末到结果 P95 | ≤ 2500 ms | —（主机 7.4） | 未实测 | 中端 Android 真机 |
| 性能层 | `rtf` 实时因子 | ≤ 0.50 | —（主机 0.276） | 未实测 | 中端 Android 真机 |
| 性能层 | `peakMemoryMiB` 峰值新增内存 | ≤ 300 MiB | —（主机 385.3） | 未实测 | 中端 Android 真机 |
| 性能层 | `longTaskMs` 主线程最长任务 | ≤ 100 ms | —（主机 237.7） | 未实测 | 中端 Android 真机 |
| 资源层 | `packBytesMiB` 整包体积 | ≤ 60 MiB | **35.31** | 达标 | harness |
| 资源层 | `precacheModelBytes` 进首屏预缓存的模型字节 | ≤ 0 | — | 未实测（smoke 侧量到 0） | smoke |
| 资源层 | `offlineRestartPass` 完整离线重启 | ≥ 20/20 | — | 未实测 | 中端 Android 真机 |
| 可靠性层 | `faultDrillsProtocol` 接线层故障演练覆盖 | ≥ 5 类 | **5/5** | 达标 | harness |
| 可靠性层 | `degradeMs` 最慢一次降档 | ≤ 2000 ms | **601 ms** | 达标 | harness |
| 可靠性层 | `faultDrillsOnDevice` 真机复演 | ≥ 5 类 | — | 未实测 | 中端 Android 真机 |
| 可靠性层 | `crossOriginRequests` 跨源请求 | ≤ 0 | **0** | 达标 | harness |

**层级判定：文本层 / 诊断层 / 性能层 / 资源层 / 可靠性层 五层全部「未实测」**
（资源层与可靠性层各有几条达标，但只要同层还有一条没测，整层就不算过）。
**整体 NO-GO，卡在 12 处**：7 条冻结项 + 5 层里 13 条未实测门槛，去重后 12 项阻塞。

性能层那四条永远不会被主机数填上。R13 那条 post（「主机基准只当参考」）守着这一点，
这一轮又加了一条：真机证据里的 `rtfP95` 若恰好等于主机基准的 0.276，harness 当场红——
把推算抄成实测是最省事也最容易发生的那种伪造。

## 3. 冻结清单 F1–F10（3/10 完成）

| # | 层 | 事项 | 状态 | 阻塞 |
|---|---|---|---|---|
| F1 | license | 冻结模型 URL / SHA-256 / tokens / 量化档并自托管 | **done** | `available=true` |
| F2 | license | 许可证核对 + THIRD_PARTY_NOTICES + SBOM | **done** | `available=true` |
| F3 | resource | 整包 ≤ 60 MiB 且不进首屏 precache | **done** | `available=true` |
| F4 | eval-set | 录制 + 双标注 ≥300 条，三份说话人隔离 | todo（0/300） | `available=true` |
| F5 | text | 文本层四条门槛达标 | todo（等 F4） | `available=true` |
| F6 | diagnosis | tone/near 精确率 ≥90%、子组差距 ≤10 pp | todo（等 F4） | 逐字声调展示 |
| F7 | performance | 真机 P95 / RTF / 内存 / 长任务 | todo（证据文件已就位，仍是 `not-measured`） | `available=true` |
| F8 | reliability | 五类故障 2 秒内降档 | doing（接线层 5/5，真机 0/5） | `available=true` |
| F9 | resource | 暂停重试 / 离线重启 20-20 / 损坏缓存自愈 | todo | `available=true` |
| F10 | governance | 换模型即换版本，重跑冻结集，不与旧分横比 | doing | `available=true` |

三处互锁，都由自动化守着：只要还有一条带 `available=true` 阻塞的项没做完，
`available` 必须是 `false`、清单里那个结论字段必须是 `no-go`，而且**放行只有一个入口**——
harness 那条 post 要求 `available === true` 当且仅当本次现算的结论是 `go`。

## 4. 落库管线走查（pilot）：**合成音，不是儿童实录**

工具：`apps/literacy-app/scripts/pilot-asr-ingest.mjs`（`npm --prefix apps/literacy-app run pilot:asr:ingest`）
记录：`.agent_workspace/evidence/r14/asr/pilot-ingest.json`

VM 里录不出孩子的声音，可落库这条路总得有人走一遍。走查的做法是：
**在仓库外的临时目录里生成十来个真的 16 kHz WAV 文件**，拿它们跑完整条流程。

### 4.1 走查证明了什么

| 步骤 | 走查里真的发生了 | 以前是什么状态 |
|---|---|---|
| 交付清单 | 12 条，时长与采样率**从 wav 头读回来**，不是抄槽位 | 只有 fixture |
| 14 条拒收闸 | 12 条全通过，含 1 条仲裁、1 条类别漂移 | 只被内存自检撞过 |
| `--verify-audio` | 12 条 sha256 与磁盘逐一对上 | **从没被执行过**（§8 那条债） |
| 指纹防篡改 | 改掉 1 个字节 → 核对当场报错 | 无 |
| 落库 | 落进沙箱副本 `FS-PILOT-B1-DRYRUN`，实录 12/300 | 无 |
| 负向 | 6 条：8 kHz 真文件 / 12.5 秒真文件 / 指针进仓库 / 单标注 / 仲裁另写一版 / 同意书没签回 | 只有内存反例 |

### 4.2 走查明确不是什么

报表里有三个字段写死这件事，harness 逐条核：

| 字段 | 值 | 含义 |
|---|---|---|
| `pilot` | `true` | 这是走查，不是交付 |
| `childRecorded` | `false` | 音频是整数三角波加噪声**合成**的，**没有任何儿童参与**，不是任何人的录音 |
| `countsTowardFreezeSet` | `false` | 不计入 300 条；落库落的是沙箱副本 |

还有三件同样重要的：`annotations.humanListened: false`（标注是照槽位设计意图**声明**的，
不是听音转写，拿它算召回只会算出恒等于 1 的数）、`consent.realFamilies: 0`
（同意书是合成凭据，只为让 `consent-missing` 那条闸有东西可放行）、
`sandbox.writesProductionEvalSet: false`（`scripts/data/asr-eval-set.json` 一个字节都没被写过）。

### 4.3 为什么条数卡在 20

走查要回答的是「这条路通不通」，不是「录了多少」。十来条足够把八个类别、仲裁、
类别漂移、指纹核对各演一遍；再多只是把同一段合成音复制粘贴——除了让 `recorded`
这个数字变好看以外没有任何信息量，**而那个数字正是 H1 的放行门槛之一（≥300）**。

所以上限硬性写在代码里（`PILOT.cap = 20`），超了直接抛错；harness 另有一条断言钉住这个数，
外加逐条核对「走查用过的每个槽位，在生产评测集里仍旧是 `placeholder`、`audio` 仍旧是 `null`」。
波形是整数运算生成的（不用 `Math.sin` 这类由实现决定的函数），处处可复现，
所以 harness **每次都重跑一遍走查，再和落盘报表逐字段比对**——报表是改不动的。

## 5. 真机 RTF 怎么测（`evidence/r14/asr/device-rtf.json`）

| 文件 | 作用 |
|---|---|
| `.agent_workspace/evidence/r14/asr/device-rtf.json` | 落盘证据。**现在是 `status: "not-measured"` 的诚实占位** |
| `.agent_workspace/evidence/r14/asr/device-rtf.schema.json` | 形状约定（`literacy-asr-device-rtf/1`） |
| `.agent_workspace/evidence/r14/asr/device-rtf.example.json` | 填好之后长什么样；带 `example: true`，去掉它会立刻红 |
| `apps/literacy-app/scripts/check-asr-device-rtf.mjs` | 收货台（`npm --prefix apps/literacy-app run check:asr:device-rtf`） |

### 5.1 一份真机证据凭什么算数

| 要求 | 拒收码 | 拦的是什么 |
|---|---|---|
| `pack.sha256` = 随包发出的整包指纹 | `pack-sha-mismatch` | 换了模型不重测，拿旧数字接着用 |
| 型号 + Android 版本 + 芯片 + WebView + 内存 + 序列号哈希，且 `tier` 是 `mid` | `device-identity-missing` / `device-tier-not-mid` / `serial-placeholder` | 「一台 Android 手机」不算身份；高端机跑得快证明不了中端机跑得动 |
| ≥20 句、≥60 秒、16 kHz | `samples-too-few` | 三句话的 p95 是个笑话 |
| `rtfP95` 与 `rtf.p95` 互为镜像 | `rtf-mirror-mismatch` | 只改给探针看的那一个数 |
| 六条门槛齐全且各自的判定与阈值自洽 | `gate-missing` / `gate-inconsistent` | 挑一条好看的报，其余略去 |
| adb 日志真的落盘 + 命令 + 签字 | `evidence-log-missing` / `attestation-missing` | 没有执行痕迹的数字只是打出来的字 |
| 文档里不许有 `host` / `projection` | `host-baseline-reused` | R13 的主机基准改个文件名冒充真机 |

共 21 条拒收码，每条都有反例样例，harness 逐条核对「每个码都还有人守着」。

### 5.2 三步把它变成真证据

```bash
cp .agent_workspace/evidence/r14/asr/device-rtf.example.json \
   .agent_workspace/evidence/r14/asr/device-rtf.json   # 去掉 example / exampleNote
adb -s <serial> logcat -d > .agent_workspace/evidence/r14/asr/device-rtf.logcat.txt
npm --prefix apps/literacy-app run check:asr:device-rtf   # 要看到 measured-pass
```

现在跑它会得到：

```
  .agent_workspace/evidence/r14/asr/device-rtf.json：awaiting-device（探针那条腿 仍红）
  真机还没跑——这是当前预期状态，H1 的 deviceRtf 腿红得对。
```

**四条真机门槛全绿只解开 F7 一条。** `available:true` 要的是整份门槛表判为 `go`，
而 F4（实录 300 条）不到位时它永远不是 `go`。真机测完就翻 `available`，
是这一轮明确拒绝的那条路——harness 里有三条 post 分别堵着它。

## 6. 从 NO-GO 到 GO 的顺序

1. **先录音**（F4）。批次 1 的 100 个槽位已排定、落库闸已就位、`--verify-audio`
   已被走查证明可用。缺的只有孩子的声音和家长的同意书。300 条、≥40 人、双标注仲裁。
2. **跑文本层与诊断层**（F5/F6）。把 `clips[].mock` 换成引擎输出，同一段代码直接出真表；
   报表里的「模拟」列会消失，「实测」列才填得上。
3. **上真机**（F7/F8/F9）。中端 Android 跑 `rtf` / `p95LatencyMs` / `peakMemoryMiB` /
   `longTaskMs`，五类故障复演，离线重启 20/20；证据按 §5 落盘并过收货台。
4. **再判一次**。harness 现算出 `go` 之后，才允许把冻结项改 `done`、`available` 改 `true`。
5. **同时改这份文档**：把结论小节的标题改成探针认的那个锚点词，把开头的 NO-GO 换成 GO。
   顺序不能倒——第 5 步的前置条件由 §8 那条互锁守着。

## 7. 复跑

```bash
npm --prefix apps/literacy-app run test:asr:evalset            # 49 项 + 7 场演练
npm --prefix apps/literacy-app run check:asr:device-rtf        # awaiting-device
npm --prefix apps/literacy-app run check:asr:device-rtf -- --self-test   # 27/27
npm --prefix apps/literacy-app run pilot:asr:ingest            # 走查 12 条，不写文件
npm --prefix apps/literacy-app run pilot:asr:ingest -- --write # 顺带刷新 evidence 报表
npm --prefix apps/literacy-app run ingest:asr:batch -- --self-test       # 22/22
npm run check:round14 && npm run check:round13 && npm run check:round12
```

`check:round14` 的 H1 预期仍是 **FAIL**，失败原因应当逐字是
`available=false，recorded=0/300，release=false，deviceRtf=false`。
这四个 false 是这一轮的**正确输出**：三条腿都有了实体，但没有一条被伪造成绿的。

## 8. 已知局限

- **实录仍是 0/300。** 走查的 12 条是合成音，不计入、也不该计入。任何把生产评测集里
  `recorded` 写成非零的改动，harness 的 `ROUND14_H1` post 当场红。
- **真机一台没跑。** `device-rtf.json` 是占位。收货台能拦住伪证，拦不住「没人去测」。
  这一条的 owner 仍是 Android QA，卡的仍是 F7。
- **走查的标注不是标注。** `humanListened: false`。它证明双标注与仲裁这条路走得通，
  不证明任何一条转写是对的。
- **说话人 30 人，还差 10 人。** 300 条要 ≥40 人；扩到 40 之前 `subgroupGap` 不要当真。
- **B2/B3 仍未排位。** 号段留着（C101–C300），等批次 1 的类别漂移定了再配平。
- **放行文档腿目前靠一条互锁保持红色。** `scripts/check-round14.mjs` 判「文档算不算 GO」时，
  拿三个词当段落锚点；那段正则有个缝——只要文档里随便哪儿出现过其中一个词，那条腿就会绿，
  哪怕整篇写的都是 NO-GO。缝在探针里，补在 harness 里：实录没到 300 条时，
  这份文档里**一个锚点词都不许出现**，且开头 400 字内必须写着 NO-GO
  （`ROUND14_H1 放行文档与数据互锁` 那条 post）。这也是本文正文一路绕开那三个词的原因。
  真到了可以放行的那天，两边同时松开（§6 第 5 步），顺序不会反。
- **同意书模板与删除时限的执行记录仍未成文。** 走查用的是合成凭据，
  它把 `consent-missing` 那条闸演通了，没有把「怎么签、怎么删、谁来审」写出来。
