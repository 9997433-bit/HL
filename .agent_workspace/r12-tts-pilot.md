Model slug: gpt-5.6-sol-xhigh-fast
# Round 12 X1 离线 TTS 试点

> 日期：2026-08-28  
> 门禁：`ROUND12_H7`  
> 试点：快乐识字《静夜思》四句固定范读

## 选型结论

X1 采用“**构建期 Kokoro 中文 TTS 生成 + 发行时仅携带逐句 Opus 资产**”做首条离线试点。应用不下载模型、不上传文本，也不把推理运行时塞进首包。《静夜思》详情页点击“读给我听”后，按稳定 poem ID `jingyesi` 逐句播放本地文件并同步高亮；资产不存在、解码失败或浏览器拒绝播放时，立即回退现有 `zh-CN` 系统 `SpeechSynthesis`。字幕、逐字拼音和家长关闭朗读的设置保持有效。

没有沿用 R11 评估里的 `zh_CN-huayan-medium` Piper voice：该 voice 的训练数据授权仍不明确，且模型与运行时会显著突破当前首包预算。Kokoro `hexgrad/Kokoro-82M-v1.1-zh` 模型卡标为 Apache-2.0，并说明中文专业数据由提供方宽松授权，适合做受控试点；这仍不等于音质已经通过儿童教育发布门槛。

## 冻结输入与可复现信息

| 项 | 冻结值 |
|---|---|
| 文本 | 床前明月光，／疑是地上霜。／举头望明月，／低头思故乡。 |
| 生成器 | `kokoro==0.9.4`、`misaki==0.9.4` |
| 模型 | `hexgrad/Kokoro-82M-v1.1-zh` |
| revision | `01e7505bd6a7a2ac4975463114c3a7650a9f7218` |
| 模型 SHA256 | `b1d8410fa44dfb5c15471fd6c4225ea6b4e9ac7fa03c98e8bea47a9928476e2b` |
| voice | `zf_001` |
| voice SHA256 | `b759a65788991932d031d6fc8440f7a8efc402273fc1c2ca9d52ffd8a16a6666` |
| 生成参数 | 普通话 `lang_code=z`，CPU，speed `0.88`，24 kHz mono |
| 发行编码 | Ogg/Opus，24 kHz mono，目标 32 kbps VBR |
| 许可来源 | [模型卡](https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh)，Apache-2.0 |

模型和 voice 权重只用于构建期生成，未提交仓库、未进入 Web/PWA/Android 发行包。每次重生成必须锁定上述 revision，重新记录产物哈希并进行普通话人工复核，不允许无记录地换 voice 或使用 `main` 漂移版本。

## 随包资产

资产目录：`apps/literacy-app/public/audio/tts-pilot/`；总音频 **33,342 bytes**，约 **9.95 秒**。`manifest.json` 保存来源、编码、文本、时长和逐文件 SHA256。

| 行 | 文件 | bytes | 时长 | SHA256 |
|---:|---|---:|---:|---|
| 1 | `jingyesi-1.ogg` | 8,609 | 2.557 s | `b21f64aa20a3cf34b3669f4d0f32b71fad0d760e5520e306c9bbf95709ed13c3` |
| 2 | `jingyesi-2.ogg` | 7,834 | 2.357 s | `76c46f51c483f2fccbbc1f9b3d873716138aa7eba65a81ef76a9b85cbf86ca76` |
| 3 | `jingyesi-3.ogg` | 8,467 | 2.507 s | `7d117e1eb2565eaa195e3342f02104584051c146528540f6db60902a4bce1613` |
| 4 | `jingyesi-4.ogg` | 8,432 | 2.532 s | `32494e40b054d5ffcd49fea10b87ec44188537ed429c8322b6e9a176a996a68e` |

## 接线与降级

- `src/utils/offlineTts.js` 维护稳定内容 ID 到本地资产的白名单，控制单实例播放、取消、语速和失败返回；它没有网络路径。
- `PoemDetailView.vue` 对 `jingyesi` 逐句优先调用离线资产；页面切换、重复点击、点单字或组件卸载都会取消旧播放，避免两路声音重叠。
- `App.vue` 在切后台和应用卸载时同时取消离线资产与系统朗读。
- 非试点诗、缺失行和解码/播放失败保持原系统 TTS 路径；朗读关闭时不播放资产。
- 页面明确显示“离线范读试点”，不把合成声音冒充真人录音。

## 试点判定

工程门 **Go**：文件魔数/解码、24 kHz mono、哈希清单、构建复制、无网络依赖和系统 TTS 回退可自动验证；新增音频远低于 5 MiB 试点预算。

内容发布门仍为 **No-Go / 待人工复核**：至少两名普通话教师需逐字确认“床、疑、举、故乡”的声调、停连和末句情绪，关键错音必须为 0；再由主持试用按 `FEEDBACK-LOOP.md` 收集儿童可懂度和不适反馈。未完成该量表前只能标记 pilot，不能据此批量生成 24 首古诗，也不能宣称通过商店正式发布审核。
