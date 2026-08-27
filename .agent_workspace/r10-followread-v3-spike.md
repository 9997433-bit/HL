Model slug: claude-opus-4-5-20251101
# Round 10 H1 · 跟读 v3 离线 ASR（sherpa-onnx WASM Worker）spike 记录

> 分支：`cursor/r10-literacy-followread-v3-9f67`；基线 `d89c455`。
> 上游依据：`.agent_workspace/r9-followread-asr-evaluation.md`（R9 评估，结论是「下一轮以
> sherpa-onnx 中文流式小模型做 Worker + Cache Storage spike」）。
> 结论先行：**接线已经做完并进了回归，模型没有随版本分发。** 清单里 `available:false`，
> 因此真机上这一档现在一律判不可用，跟读留在录音档——这正是要验的失败路径。

## 1. 这一轮做了什么

| 层 | 文件 | 职责 |
|---|---|---|
| 包管理 | `apps/literacy-app/src/utils/offlineAsr.js` | 清单校验、版本化 Cache Storage、逐文件 sha256、四档降级判定、16 kHz 重采样 |
| 推理 | `apps/literacy-app/src/workers/sherpaAsrWorker.js` | 模块 Worker：从缓存取 wasm 胶水与二进制、建流式 recognizer、partial/final 回传 |
| 采音 | `apps/literacy-app/public/asr/pcm-capture.worklet.js` | AudioWorklet 攒够 2048 点再交给主线程，主线程重采样成 16 kHz Int16 |
| 清单 | `apps/literacy-app/public/asr/manifest.json` | 冻结位：modelId / modelVersion / license / files[sha256]；当前 `available:false` |
| 接线 | `src/composables/useSpeechEval.js` | 第四档 `offline-asr`，失败只降 `recording`；结果对象加 `source/modelVersion/confidence` |
| 界面 | `src/components/FollowReadPanel.vue` | 离线评测包状态、下载/删除/重查、进度条、`data-tier`/`data-source` |
| 回归 | `scripts/test-speech-eval.mjs`、`scripts/smoke.mjs` | 4 条 Node 单测 + `ROUND10_H1_SMOKE` 浏览器用例 |

## 2. 四档降级契约（对外仍是三档）

```text
点击「我来读」
  ├─ 离线评测包已装 + Worker 起得来 → offline-asr（mode=recognition, source=offline-sherpa）
  ├─ 未装；家长显式打开浏览器识别   → recognition（source=web-speech，可能联网）
  ├─ 本地引擎超时/崩溃/没听清 + 有麦克风 → recording（回放 + 响度分封顶 85）
  └─ 麦克风缺失或被拒绝            → listen-only（无分数，孩子自评）
```

`modeOfTier()` 把 `offline-asr` 映射回 `recognition`，所以进度存档、`FollowReadPanel`
的 `data-mode` 和 R8 H5 的既有断言都不分叉；新增的 `data-tier` / `data-source`
才是 v3 的观测点。

**失败只许往下降。** `chooseTier()` 里 `offlineFault` 一旦为真，直接落到 `recording`
（没有麦克风则 `listen-only`），即使家长此前打开过浏览器识别也不改用它——
本地引擎崩了就顺手把音频送去厂商在线服务，等于替家长做了隐私决定。
单测 `四档降级：离线优先，引擎失败只降到录音档…` 钉住这条。

## 3. 隐私与资源默认值（未变）

- 浏览器 `SpeechRecognition` 默认关闭，要家长在跟读页勾选；这一轮没动这个默认值。
- 离线评测包**家长点了才下**：`probeOfflinePack()` 只读同源清单和本机缓存，
  `installOfflinePack()` 才发起下载，界面显示大小、进度和删除入口。
- 模型不进首屏 precache：`vite.config.js` 排除 `asr/models/`，包体走
  `literacy-app-asr-pack-<modelId>-<modelVersion>` 这个独立缓存，换模型即换缓存。
- 运行时不回退任何第三方 CDN；smoke 用例会统计跨源请求，必须为 0。
- PCM / 录音 Blob 只在内存和 Worker 之间传递，页面一关即释放。

## 4. 已实测（本轮）

| 项 | 结果 |
|---|---|
| `node scripts/test-speech-eval.mjs` | 18/18（新增 4 条：清单冻结、四档降级、三档映射、采音管线） |
| `node scripts/smoke.mjs` | 163 路由 + 35 交互，0 问题；`ROUND10_H1` 用例：`四档=recording，装包失败后降到 recording，0 个跨源请求` |
| `node scripts/check-bundle.mjs` | 首屏 JS 322 KB / 420 KB 预算；Worker 单独成块（`sherpaAsrWorker-*.js`），不进首屏 |
| `npm run check:round10` | H1 ✓ |
| `npm run check:round9` | 8/8 不退化 |

`FollowReadPanel` 分块从 12.77 KB 涨到 23.49 KB（gzip 6.41 → 10.83 KB）——
按需路由块，不计首屏预算。

## 5. 还没做（转生产前必须补齐）

沿用 R9 评估 §5 的门槛，一条都没有因为「接线完成」而放宽：

1. **冻结模型**：URL、SHA-256、tokens、量化档、许可证；补 `THIRD_PARTY_NOTICES.md` 与 SBOM。
   仓库里现在一个模型字节都没有，`available` 置 true 之前不许合。
2. **儿童冻结集**：≥300 条 3–10 秒片段，双标注仲裁，说话人隔离；安静集字符召回 ≥90%、
   噪声集 ≥80%、漏字召回 ≥85%、静音误判 ≤1%。
3. **设备基准**：中档 Android 真机 P95 ≤2.5 秒、RTF ≤0.5、峰值内存 ≤300 MiB，
   主线程无 >100 ms 长任务。当前只在桌面 Chromium 上验了失败路径。
4. **五类故障演练**：飞行模式、模型 404、wasm 初始化失败、麦克风拒绝、低内存杀 Worker，
   都要 2 秒内降到 `recording` / `listen-only`。本轮只覆盖了「清单不可用」这一类。
5. **音素诊断仍不发布**：`phonemeMarks/similarityV2`（R9 PoC）依旧不接界面。
   通用 ASR 给的是汉字转写，不是声母韵母声调后验；`tone/near` 精确率 ≥90% 之前不逐字展示。

## 6. Worker 适配边界（下一位接手的人先看这里）

`sherpaAsrWorker.js` 假定胶水脚本是 ESM 且导出 Emscripten 工厂函数，
运行时对象上挂 `createOnlineRecognizer`。上游若给的是经典脚本（`importScripts` 形态），
需要在 `boot()` 里加一层适配，而不是把加载逻辑散到主线程；主线程只认
`ready / partial / final / error` 四种消息，换引擎不该影响这条协议。
任何加载失败都必须 `post({type:'error'})`，让 `useSpeechEval` 走 `offlineFault` 降档。
