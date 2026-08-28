# `evidence/r14/asr/` —— 跟读放行用的两份证据

> 归属：Round 14 H1（`scripts/check-round14.mjs`）
> 收货台：`apps/literacy-app/scripts/check-asr-device-rtf.mjs`（`npm --prefix apps/literacy-app run check:asr:device-rtf`）
> 口径：`.agent_workspace/r14-followread-release.md`

这个目录只放两类东西：**真机性能证据**和**落库管线走查记录**。两者都不是评测数据，
也都不能单独把跟读放行——放行是 Go/No-Go 五层门槛整体判定的结果。

| 文件 | 是什么 | 现在的状态 |
|---|---|---|
| `device-rtf.json` | 中端 Android 真机的 RTF / 延迟 / 内存 / 长任务实测 | **`not-measured` 诚实占位**：VM 里没有真机也没有 adb |
| `device-rtf.schema.json` | 上面那份文件的形状约定 | — |
| `device-rtf.example.json` | 填好之后长什么样（值全是编的，`example: true`） | — |
| `pilot-ingest.json` | 落库管线的合成音空载走查记录 | 每次跑 harness 都会被重跑核对 |

## 1. `device-rtf.json`：为什么它现在是红的，而且红得对

`check-round14.mjs` 的 H1 读这份文件时只看五件事：文件 ≥100 字节、`onDevice:true`、
`simulated:false`、`device` 有身份、`rtfP95` 是 0–0.5 之间的有限数。**这五件事谁都能敲出来。**

所以这里加了一道比探针严得多的收货台。它问的是「凭什么算数」：

- **测的是发出去的那个包**：`pack.sha256` 必须等于 `public/asr/manifest.json` 的整包指纹。
- **测的是一台具体的机器**：型号、Android 版本、芯片、WebView 版本、内存，
  外加序列号的 sha256（落哈希不落明文）。`tier` 必须是 `mid`——门槛写的是中端机。
- **量了一段够长的音**：≥20 句、≥60 秒、16 kHz。
- **`rtfP95` 只是 `rtf.p95` 的镜像**：两处对不上，说明有人只改了给探针看的那一个数。
- **六条真机门槛齐全且自洽**：RTF / 句末延迟 / 峰值内存 / 长任务 / 离线重启 / 故障复演，
  每条的 `verdict` 都要和阈值算出来的一致。
- **有执行痕迹和签字**：adb 日志真的落盘、写清跑的哪条命令、谁在什么时候签的。

还有一条反着来的闸：`evidence/r13/asr-rtf/host-baseline.json` 那份主机基准长得很像这份文件，
改个文件名就能冒充真机。只要文档里出现 `host` 或 `projection`，收货台直接判 `host-baseline-reused`。

**不变式**：任何能让 H1 那条腿变绿的文件，在收货台必须零错误。
`test-asr-eval-set.mjs` 拿一份「只填五个字段」的伪证撞这条不变式——探针会绿，收货台会红，
于是 harness 红。这条捷径走不通。

### 怎么把它变成真证据

```bash
# 1. 照模板填（值全部换成真机上量出来的）
cp .agent_workspace/evidence/r14/asr/device-rtf.example.json \
   .agent_workspace/evidence/r14/asr/device-rtf.json
#    去掉 example / exampleNote 两个字段

# 2. adb 日志落到 evidence.log 指的那个路径
adb -s <serial> logcat -d > .agent_workspace/evidence/r14/asr/device-rtf.logcat.txt

# 3. 过收货台
npm --prefix apps/literacy-app run check:asr:device-rtf

# 4. 跑 harness 与探针
npm --prefix apps/literacy-app run test:asr:evalset
npm run check:round14
```

第 3 步要看到 `measured-pass`。看到 `invalid` 就照拒收码逐条修；
看到 `awaiting-device` 说明 `status` 还写着 `not-measured`。

### 一条提醒

四条真机门槛全绿只解开冻结清单的 **F7** 一条。`available:true` 要的是整份 Go/No-Go 为 `go`，
而 **F4（实录 300 条儿童跟读）** 不到位时它永远不是 `go`。
真机测完就翻 `available` 是这一轮明确拒绝的那条路。

## 2. `pilot-ingest.json`：合成音走查，不是录音

这份记录来自 `apps/literacy-app/scripts/pilot-asr-ingest.mjs`。它在临时目录里生成十来个
真的 16 kHz WAV 文件（整数三角波加噪声），拿它们走一遍完整的落库流程：
构造交付清单 → 过 14 条拒收闸 → 核对磁盘音频的 sha256 → 落库进一份沙箱副本 →
再故意改一个字节确认指纹核对会红。

它补的是 `r14-asr-recording-batch1.md` §8 记下的那条债：`--verify-audio` 在 CI 上从没被执行过。

**它明确不是什么**（报表里三个字段写死这一点）：

| 字段 | 值 | 含义 |
|---|---|---|
| `pilot` | `true` | 这是走查，不是交付 |
| `childRecorded` | `false` | 音频是合成的，没有任何儿童参与 |
| `countsTowardFreezeSet` | `false` | 不计入 300 条，落库落的是沙箱副本 |

条数硬性卡在 **20**（`PILOT.cap`）。走查要证明的是路通不通，不是录了多少；
再多只是把同一段合成音复制粘贴，除了让 `recorded` 这个数字好看以外没有信息量——
而那个数字正是 H1 的放行门槛之一。`scripts/data/asr-eval-set.json` 一个字节都不会被它写过，
harness 每次都会重跑一遍走查并与这份报表逐字段比对（波形是整数运算生成的，处处可复现）。
