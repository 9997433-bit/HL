Model slug: claude-opus-5-thinking-high-fast
# Round 13 H1 · 跟读离线 ASR 的 Android RTF 基准

> 脚本：`apps/literacy-app/scripts/bench-asr-rtf.mjs`（`npm --prefix apps/literacy-app run bench:asr:rtf`）
> 记录：`.agent_workspace/evidence/r13/asr-rtf/host-baseline.json`（`onDevice: false`）
> 装法：`apps/literacy-app/scripts/lib/asr-runtime.mjs`（与 `src/workers/sherpaAsrWorker.js` 的 `boot()` 同一份）
> 门槛：`public/asr/manifest.json` → `freezeChecklist.F7` / `goNoGo` 性能层
>
> **这台机器不是 Android 真机。** 这份文档里没有一个数字构成 F7 的验收证据，
> 真机那一段仍然 **未实测**，`[SKIP owner: Android QA]`。

## 1. F7 到底卡在哪

性能层四条门槛写的都是「中档 Android **真机**」：

| 指标 | 门槛 | 谁来测 | 现状 |
|---|---|---|---|
| `p95LatencyMs` 句末到结果 | ≤ 2500 ms | device | 未实测 |
| `rtf` 实时因子 | ≤ 0.5 | device | 未实测 |
| `peakMemoryMiB` 峰值新增内存 | ≤ 300 MiB | device | 未实测 |
| `longTaskMs` 主线程长任务 | ≤ 100 ms | device | 未实测 |

VM 里没有真机，也没有 adb。等真机排期期间，最坏的做法是什么都不量——
等三周之后才发现这个量化档在中端机上根本跑不动，那三周就白等了。
所以这一轮量的是**能在主机上量、且对真机有推断力的那部分**。

## 2. 量了什么

`bench-asr-rtf.mjs` 用与 Worker 完全相同的装法起引擎（共用 `lib/asr-runtime.mjs`，
两边不可能走岔），然后跑 5 趟同一段音频，逐项记：

- **RTF**：整趟解码耗时 ÷ 音频时长，取 min / p50 / p95 / max；
- **句末到结果**：`inputFinished()` 到拿到最终文本的那段等待，也就是孩子读完最后一个字之后盯着屏幕的时间；
- **逐帧解码**：每 100 ms 一帧（与 `pcm-capture.worklet.js` 送上来的粒度一致）的处理耗时分布；
- **内存**：进程 RSS 的基线 / 启动后 / 峰值；
- **CPU 标定回路**：一段定长、纯标量、不分配内存的 JS 循环（4 千万次 `Math.sqrt(i)/(i+1)`）。

音频是上游模型仓库自带的**成人**普通话示例（5.61 s，Apache-2.0）。
儿童的语速、拖音、共发音会让解码路径不一样——那部分归 F4 冻结集，这里量的只是吞吐。

## 3. 主机实测（2026-08-28，CI VM）

```
主机          Intel(R) Xeon(R) Processor × 4 核 / 15.6 GiB / linux 6.12.94+ / Node v22.14.0
负载          load1 19.39 → 18.41（共用 VM，contended: true）
模型          sherpa-onnx-streaming-zipformer-zh-14M-int8@2023-02-23+wasm1.12.15，35.31 MiB
标定回路      4 千万次，p50 321.6 ms
引擎启动      427.4 ms（含 wasm 编译）+ 建识别器 6380.6 ms
RTF           min 0.117 · p50 0.134 · p95 0.276 · max 0.276
句末到结果    p50 0.2 ms · p95 7.4 ms
逐帧解码      p50 0.1 ms · p95 77.9 ms · max 237.7 ms（285 帧）
内存          基线 45.9 MiB → 启动后 113.9 MiB → 峰值 431.2 MiB（增量 +385.3 MiB 上界）
识别结果      对我做了介绍那么我想说的是大家如果对我的研究感兴趣呢
```

**负载 19 的 4 核机器**——这台 VM 上同时跑着别的活。绝对耗时因此全部偏大，
两次连跑的 RTF p50 从 0.209 掉到 0.134 就是这个原因。所以下面的推算不用绝对值。

## 4. 怎么从主机推到真机

绝对耗时在共用 VM 上不可信，但**比值**可信：解码和标定回路都是单线程 CPU-bound，
争抢对两者的拖累是同一个系数，相除就抵掉了。

```
rtfPerLoopMs = RTF(p50) / 标定回路(p50) = 0.134 / 321.6 = 0.000417   ← 可跨机器、跨时间横比
deviceRtf   ≈ rtfPerLoopMs × deviceLoopMs
```

两次连跑分别得到 0.000447 与 0.000417（负载 22 与 19），差 7%——这个量确实稳。

`deviceLoopMs` 是**真机上跑同一段回路的耗时**，也是整份推算里唯一的假设：

| deviceLoopMs | 对应什么机器 | 推算 RTF | 对 0.5 的门槛 |
|---|---|---|---|
| 500 ms | 状态好的中端芯（近两年 2GHz 级大核，未热降频） | **0.21** | 有余量 |
| 1200 ms | 千元机，或连续跟读十分钟热降频之后 | **0.50** | 正好顶在线上 |

**推算区间 0.21–0.50，恰好压着门槛。** 这是这一轮最该被记住的一句话：
这个量化档在好机器上没问题，在低端机或降频之后会卡在红线，
而跟读恰恰是「连着读十分钟」的场景——热降频不是边缘情况，是常态。

### 真机那一趟怎么做（Android QA）

只需要量一个数，就能把推算变成半实测：

1. 在目标机型的 WebView（不是 Chrome）里跑同一段回路，取 5 次 p50：

   ```js
   // 常数不许改，改了就没法和 host-baseline.json 横比
   let acc = 0
   const t0 = performance.now()
   for (let i = 1; i <= 40_000_000; i += 1) acc += Math.sqrt(i) / (i + 1)
   const deviceLoopMs = performance.now() - t0
   ```

2. `deviceRtf ≈ 0.000417 × deviceLoopMs`，先算出预期值；
3. 再按 F7 的口径实测四条门槛，和预期值对照。对不上说明瓶颈不在 CPU 吞吐
   （多半是内存压力或 WebView 的 wasm 编译策略），那是另一类问题，值得单独查。

## 5. 另外三条门槛：主机能说什么、不能说什么

| 门槛 | 主机数 | 能推出什么 | 不能推出什么 |
|---|---|---|---|
| 句末到结果 ≤2500 ms | p95 7.4 ms | 流式解码是「边读边解」，句末只剩最后一帧的尾巴，**架构上就不会撞这条线** | 真机上的音频采集/权限/唤醒延迟不在这个数里 |
| 主线程长任务 ≤100 ms | 逐帧 p95 77.9 ms · max 237.7 ms | 单帧最长 237 ms，**远超 100 ms**；好在解码跑在 Worker 里，主线程不背这个耗时 | 真机是不是真的没把它排到主线程上，要靠真机 trace 看 |
| 峰值新增内存 ≤300 MiB | +385.3 MiB | 这是**上界**：Node 的 RSS 含 wasm 线性内存与 onnx 权重，且 Node 不急着回收 | 不能据此说真机会超 300 MiB，WebView 的口径完全不同 |

逐帧 max 237.7 ms 和内存 +385 MiB 这两个数，都不足以判 F7 不合格，
但足以让 F7 的真机排期**不要再往后拖**：它们是这一档最可能出事的两个地方。

## 6. 这份记录守着的那条规矩

主机数字好看是最危险的时候。所以 `test-asr-eval-set.mjs` 里有一条断言
（`ROUND13_H1 主机基准只当参考：真机那几条门槛仍旧未实测`）专门守着：

- `p95LatencyMs` / `rtf` / `peakMemoryMiB` / `longTaskMs` / `offlineRestartPass` / `faultDrillsOnDevice`
  这六项的**实测值必须恒为 `null`**；主机数只以 `host` 字段出现在报表里，显示为「（主机 0.276，不计入）」；
- 性能层的状态必须是 `unmeasured`，Go/No-Go 因此继续 `no-go`；
- `host-baseline.json` 的 `onDevice` 必须是 `false`、`projection.deviceVerdict` 不许是 `pass`。

换句话说：这份基准可以让人提前发现问题，但**不能让任何人少跑一次真机**。
F7 的状态仍是 `todo`，`available` 仍是 `false`。

## 7. 复现

```bash
npm --prefix apps/literacy-app run bench:asr:rtf          # 写 evidence/r13/asr-rtf/host-baseline.json
npm --prefix apps/literacy-app run bench:asr:rtf -- --passes 9 --json
npm --prefix apps/literacy-app run test:asr:evalset       # 33/33，性能层仍显示未实测
npm --prefix apps/literacy-app run test:asr:engine        # 8/8，落库回归
```

跑在负载不同的机器上，绝对值会飘，`rtfPerLoopMs` 不会——横比只看它。
