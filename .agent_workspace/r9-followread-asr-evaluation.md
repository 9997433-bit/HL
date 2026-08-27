Model slug: gpt-5.6-sol-xhigh-fast
# Round 9 · 跟读 v3 离线 ASR / 音素路线评估

> 基线：`ec733bb`；评估日期：2026-08-27；范围：快乐识字 Web/PWA 与 Capacitor Android。  
> 结论先行：**用 sherpa-onnx + 中文流式 Zipformer/Paraformer 做第一轮离线 ASR 试验，Vosk 做轻量对照，whisper.cpp 只做准确率上限对照；不把任一通用 ASR 的汉字转写直接称为“音素评分”。** 真正面向儿童的声母、韵母、声调诊断，需要带声学后验的参考文本受限对齐、儿童语音标注集和置信度校准，不能靠“识别出了哪个汉字”反推后直接上线。

## 1. 现状、目标与关键边界

当前 `useSpeechEval.js` 已有稳定的三档能力链：

1. `recognition`：家长显式打开浏览器 `SpeechRecognition` 后做汉字转写与逐字编辑距离；
2. `recording`：只有麦克风时仅按出声比例、时长和峰值给分，封顶 85，并提供本机 Blob 回放；
3. `listen-only`：没有或拒绝麦克风时只听范读、孩子自评，不伪造分数。

这条链的优点是失败可恢复、对能力边界表达诚实；缺点是 `SpeechRecognition` 是否离线由浏览器厂商决定，且默认实现通常只给文本，不给可用于发音诊断的逐帧音素后验。现有 `alignChars()` 回答的是“转写文字与原文是否相同”，不是“孩子的声母、韵母、声调是否准确”。例如目标“他”、转写“她”在朗读层完全同音；目标“妈”、转写“马”可能来自声调，也可能只是语言模型选字；当识别器已知要读的古诗时，它还可能把含糊语音自动纠正成原文，制造虚高分。

因此 v3 拆成两个互不冒充的目标：

- **离线转写层**：设备内完成 VAD、识别和文本对齐，替代不确定的云端 Web Speech；输出“文字跟读相似度”和不确定性。
- **发音诊断层**：以后从声学模型的 token/phone posterior 做参考文本受限对齐，才允许输出“某字声调可再听听”。低置信度必须显示“没听清”，不能显示红色错误。

“离线”也要分清：Web 首次下载几十 MB 模型需要网络，缓存完成后才能离线；Android 可以把选定模型随包分发或作为明确的可下载资源。不得把“首次使用仍要下载”宣传成开箱即离线。

## 2. 候选方案对比

| 方案 | 中文与端侧能力 | Web/PWA 适配 | Android 适配 | 包体/性能信号 | 音素诊断能力 | 许可证与结论 |
|---|---|---|---|---|---|---|
| **sherpa-onnx**（Zipformer / Paraformer / SenseVoice） | 有中文流式和中英双语模型，适合短句实时识别 | 官方提供 WebAssembly 实时 ASR 构建与 JS 示例，可放 Worker；是本项目最短的统一技术路径 | 官方列出多 ABI APK 和中文模型，亦可原生接入 | 官方有名为 `zh-14M` 的小 Zipformer，另有更准但更大的模型；实际下载、内存、RTF 必须在目标机实测 | 高层识别结果仍主要是 token 文本；能否取 CTC/Transducer 后验取决于模型与接入层，不能默认等同 GOP | 运行时 Apache-2.0；**每个模型许可证另查**。推荐为首选部署底座 |
| **Vosk / Kaldi** | 官方 `vosk-model-small-cn-0.22` 为 42 MB，支持流式与词表重配置 | JS 绑定存在，但官方浏览器 WASM 产品路径和维护体验不如 sherpa-onnx，需额外验证 Worker、SIMD 和缓存 | 官方 Android 离线 demo 成熟，小模型明确面向 Android/RPi | 42 MB 小模型的公开中文测试错误率明显受数据集影响；大模型 1.3 GB 不适合本项目 | Kaldi 底层可做对齐，但 Vosk 常用 API 给词/文本结果；若为 GOP 深挖会显著增加图和模型工程 | 代码与列出的中文模型 Apache-2.0。作为轻量基线，不作为首选 Web 路线 |
| **whisper.cpp** | 多语言 Whisper 能识别普通话，对噪声和自由口语可作强基线 | 官方有 WASM、麦克风 stream 示例 | 官方有 Android 示例 | 未量化 tiny 75 MiB、base 142 MiB；量化可缩小，但小模型中文质量与内存仍需实测 | 输出是文本/分段或 token 时间，不是普通话声母韵母声调后验；短古诗还可能被语言先验“纠正” | whisper.cpp 为 MIT，模型条款另核。只做离线准确率对照，不建议成为首发评分内核 |
| **WeNet** | 中文训练生态、流式模型和自训练能力强，适合后续做儿童域适配 | 仓库的 `runtime/web` 是服务端/Gradio 路线，未提供与本项目同等成熟的纯浏览器 WASM 路线 | 官方有断网 Android 端侧中文 demo | 自训、导出和端侧调优自由度高，但维护训练管线与双运行时成本最高 | 最适合在有儿童标注语料后训练 CTC/phone head 或导出后验；不是当前低成本即插即用方案 | Apache-2.0。列为第二阶段研发底座，不用于 v3.0 首发 |
| **Picovoice Leopard** | 端侧、Web 和移动端产品化完整 | Web 可本地处理，但需要 AccessKey | 支持 Android/iOS | 商业 SDK，部署便利但受账号和授权约束 | 当前公开语言列表未含普通话 | 因**普通话缺失 + AccessKey/授权依赖**直接淘汰 |

### 2.1 为什么不直接选“准确率看起来最高”的 Whisper

本场景不是长音频听写，而是 3–10 秒、参考文本已知、儿童声线明显、希望解释漏字和声调。大语言先验擅长把句子整理通顺，却可能掩盖真实漏读；较大的模型也会冲击当前识字首屏 420 KB 预算、低端 Android WebView 内存和 PWA 更新可靠性。whisper.cpp 的跨平台价值很高，所以应作为盲测对照，但它没有天然解决普通话发音诊断。

### 2.2 为什么 sherpa-onnx 是“试验首选”而非“已定型依赖”

它同时有官方 WASM 实时路径和 Android 中文路径，且可替换多种 ONNX 模型，最适合先验证同一套音频与评分协议。但框架 Apache-2.0 不代表所有模型都同许可证；“14M”是模型命名/参数量信号，也不等于本项目最终压缩下载大小。合入依赖前必须冻结具体模型 URL、SHA-256、许可证、tokens 与量化文件，并补入 `THIRD_PARTY_NOTICES.md`。本轮不把未经设备基准和语料验收的二进制塞进发行包。

## 3. 推荐架构与三档降级契约

### 3.1 recognition 档内部替换，不新增第四档

保留对外的三个 mode，不让进度数据和界面分叉：

```text
点击“我来读”
  ├─ 本地模型已安装且 Worker 初始化成功 → recognition(source=offline-sherpa)
  ├─ 未安装；家长主动允许浏览器识别 → recognition(source=web-speech, mayNetwork=true)
  ├─ 本地引擎超时/崩溃/内存不足 + 麦克风可用 → recording（仍回放、响度分封顶 85）
  └─ 麦克风缺失或拒绝 → listen-only（无分数、自评）
```

本地引擎失败时**不得静默切到可能联网的 Web Speech**；只能降到 `recording`。模型下载应由家长点击“下载离线评测包”，显示大小、网络状态、存储占用和删除入口。Web 用独立版本化 Cache Storage 按需缓存，仿现有 OCR 包策略但不能污染首屏 precache；Android 再根据实测决定随 APK/AAB 分发还是首次下载。模型和 wasm 必须同源、自托管、校验哈希，不设第三方 CDN 运行时回退。

### 3.2 数据流

1. `AudioWorklet` 或受控录音层把输入转成 16 kHz 单声道 PCM；简单能量 VAD 只负责切静音，不参与“读对”判定。
2. 专用 Worker 加载 WASM 与模型，主线程只接收进度、partial/final tokens、时间戳和引擎置信信息；初始化和推理均设置超时与取消。
3. `recognitionProvider` 统一输出 `{ text, tokens, timings, confidence, source }`。现有 `evaluate()` 继续接受纯文本，未来新增字段必须只加不改。
4. v3.0 仅把转写与原文做字符/拼音候选对齐；v3.1 才引入声母、韵母、调类 token 的 CTC 后验与 reference-constrained alignment/GOP。
5. 原始 PCM、Blob 与局部后验默认只在内存；离开页面即释放。若未来征集改进语料，必须是独立家长同意、可撤回、明确保存期限的流程，不能复用麦克风授权。

页面应修正一处既有表述风险：`FollowReadView.vue` 目前写“两种都不会把声音传到别的地方”，但同页开关与 composable 已承认浏览器 `SpeechRecognition` 可能调用厂商在线服务。v3 接线前应改成“录音回放和离线评测不上传；浏览器逐字识别可能联网，需家长打开”。

## 4. 本轮纯函数 PoC 的定位

本轮追加 `phonemeMarks(reference, heard, lookupPinyin)` 与 `similarityV2(...)`，带 `ROUND9_H4` 标记，并加入 Node 单测。它不访问浏览器、不引入模型、不改 `evaluate()`，所以现有 `recognition → recording → listen-only` 三档完全不动。

PoC 先对字符做编辑距离对齐，再由调用方注入带调拼音：

- 同字，或不同字但拼音和调值相同：`hit`；
- 音节相同、调值不同：`tone` 候选；
- 声母或韵母相同：`near` 候选；
- 漏字、查不到拼音或差异大：`miss`；
- `similarityV2` 暂按 hit=1、tone=0.5、near=0.25，多读轻罚与 v1 一致。

这些权重只用于确定 API 形状与回归测试，**不是教学量表**。尤其 `tone` 只是“ASR 选字的拼音差异”，不能证明声波里的调型读错；因此 PoC 不接 UI、不写进度、不替换现有分数。多音字还必须由诗句逐位置拼音提供，不能只查全局 `CHARACTER_MAP` 的单一读音。待声学试验通过后，函数可消费引擎给出的候选音节/后验，而不用推翻渲染契约。

## 5. 基准集与 Go / No-Go 门槛

不能用 AISHELL、THCHS 等成人公开榜单代替儿童跟读验收。先建立经授权、去标识化的冻结集：建议至少 300 条 3–10 秒片段，覆盖 4–6 岁与 7–9 岁、不同性别/地区口音、手机与平板麦克风、安静/电视背景/远讲三种环境；另加静音、旁人说话、故意漏字、多读、重复、真实声调/声母错误。每条由两名普通话标注者独立标注，分歧仲裁；训练、调阈值、终验三份说话人隔离，禁止同一孩子跨集合泄漏。

建议在正式接线前冻结以下门槛（均是**提议值，尚未实测**）：

- 文本层：安静集字符召回 ≥90%，噪声集 ≥80%；漏字检出召回 ≥85%；静音/纯背景被判“读得好”的比例 ≤1%。
- 诊断层：只有当 `tone/near` 对人工标签的精确率 ≥90% 才允许逐字展示；宁可少提示，也不要冤枉儿童。任一年龄/性别/设备子组与总体差距 >10 个百分点即阻断。
- 性能层：中档 Android 真机 10 秒句末到结果 P95 ≤2.5 秒，实时因子 RTF ≤0.5，峰值新增内存 ≤300 MiB；Worker 推理不得造成主线程 >100 ms 长任务。
- 资源层：Web 可选评测包压缩下载目标 ≤60 MiB，不进入首屏 precache；首次下载可暂停/重试，完整离线重启 20/20 成功，损坏缓存能自动清除后降档。
- 可靠性层：飞行模式、模型 404、wasm 初始化失败、麦克风拒绝、低内存杀 Worker 五类故障都应在 2 秒内进入 `recording` 或 `listen-only`，不丢本轮交互、不触网兜底。

若文本层通过而诊断层未过，仍可发布“离线逐字跟读（实验）”，但只显示命中/漏读和“没听清”，隐藏声调/近音标签；若性能或可靠性不过，则保持 v2，不让模型包拖累全体用户。

## 6. 分阶段交付建议

### 阶段 A：离线引擎盲测

用同一批冻结 wav 比较 sherpa-onnx 小中文流式模型、Vosk 42 MB 中文小模型、whisper.cpp tiny/base 量化档。记录模型精确版本、许可证、SHA、下载大小、CER、漏字召回、RTF、峰值内存，不先看品牌选结果。浏览器测 Chromium 桌面与 Android WebView，Android 原生仅作为对照，避免一开始维护两套评分逻辑。

### 阶段 B：灰度接入离线 recognition

只接胜出的 sherpa/Vosk provider，模型管理和 Worker 均放实验开关后；结果对象新增 `source`、`confidence`、`modelVersion`，旧字段不删。引擎不可用时沿既有两级降档。在线 Web Speech 保持默认关闭，并把隐私文案修正为一致表述。

### 阶段 C：声学诊断研究

若产品确实需要“声调错在哪”，以 WeNet/icefall 训练或微调普通话 initial/final/tone CTC 头，输入已知诗句的规范拼音序列，比较 forced alignment、self-aligned GOP 与 alignment-free GOP。儿童语音的共发音、年龄和口音会让边界不稳定，不能套成人阈值。先校准“是否展示提示”的精确率，再讨论百分制；音高轨迹可作为声调辅助特征，但不能脱离音节、基频可用率和儿童声区单独裁决。

### 阶段 D：发行与治理

锁定模型许可证与 NOTICE、生成 SBOM/哈希、补离线升级/回滚测试、记录不同设备性能证据。模型变更视为评分规则变更：必须版本化、重跑冻结集，不能后台替换后继续与旧历史最高分横向比较。

## 7. 最终决策

- **现在做**：保留本轮纯函数 PoC；下一轮以 sherpa-onnx 中文流式小模型做 Worker + Cache Storage spike，同时跑 Vosk 和 whisper.cpp 对照。
- **现在不做**：不新增生产依赖、不下载模型、不把 `similarityV2` 接界面、不承诺“音素准确率”、不改变 recording 85 分封顶或 listen-only 无分数。
- **转生产条件**：儿童冻结集、低端设备性能、五类失败降档、许可证四项证据齐全；逐字 tone/near 还需单独达到高精确率门槛。

这一路线优先保证“不误伤孩子”和“离线失败仍能练习”。通用 ASR 解决的是听写，发音评测解决的是带参考文本的声学诊断；两者相关但不等价，v3 的成败取决于是否守住这条边界。

## 8. 参考资料（上游/论文）

- sherpa-onnx WebAssembly 实时识别：<https://k2-fsa.github.io/sherpa/onnx/wasm/index.html>
- sherpa-onnx WASM 构建与中文模型示例：<https://k2-fsa.github.io/sherpa/onnx/wasm/build.html>
- sherpa-onnx Android 中文 APK、模型与许可证提醒：<https://k2-fsa.github.io/sherpa/onnx/android/apk-cn.html>
- Vosk 官方能力与流式 API：<https://alphacephei.com/vosk/>
- Vosk 中文模型大小、测试集指标和许可证：<https://alphacephei.com/vosk/models>
- whisper.cpp 平台支持、模型大小与 WASM/Android 示例：<https://github.com/ggerganov/whisper.cpp>
- WeNet Android 断网端侧 demo：<https://github.com/wenet-e2e/wenet/tree/main/runtime/android>
- WeNet runtime 支持矩阵：<https://github.com/wenet-e2e/wenet/tree/main/runtime>
- Leopard 支持语言与 AccessKey 约束：<https://picovoice.ai/docs/leopard/>
- CTC 音素评测中强制对齐、儿童语音与插删错误的局限：<https://www.isca-archive.org/interspeech_2024/cao24b_interspeech.pdf>
- CTC-GOP 与音系知识、对齐成本：<https://doi.org/10.21437/interspeech.2025-829>
