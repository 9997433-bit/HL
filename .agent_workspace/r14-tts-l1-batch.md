Model slug: gpt-5.6-sol
# Round 14 · L1 单元离线朗读批次

> 日期：2026-08-28
> 门禁：`ROUND14_H5` / `ROUND14_H5_SMOKE`
> 范围：首单元 `u1「我和数字」`，12 张字卡 ×「单字 + 例句」= **24 份资产**

## 1. 批次结论

本批把 Round 12 仅覆盖《静夜思》的 Kokoro 离线试点扩到 L1 首单元字卡。每张卡的“听这个字”“听音选字”和“读一句话”优先播放随包 Ogg/Opus；未知字、未覆盖的词语、资源缺失、解码失败或浏览器拒播时，继续回退设备 `zh-CN` SpeechSynthesis。应用不携带模型或推理运行时，播放链没有第三方网络地址。

工程交付为 **GO**：24 份音频均落在 `apps/literacy-app/public/audio/tts-l1/`，总计 **263,995 bytes / 42.634 秒**；12 张卡都具备单字和例句两种资产，最小文件 5,851 bytes。`manifest.json` 冻结每份文本、字节数、时长与 SHA256，浏览器 smoke 还会在构建产物中复算哈希并实际点击“一”的单字与例句入口。

内容发布仍为 **teacher-review-required**：这些是合成语音，不是真人录音；尚未记录两名普通话教师的逐条听审，不能写成“真人范读”或宣称已完成主观听感终验。W5 签核前应特别复听轻声“们/个”、变调“一”及例句停连。

## 2. 冻结生成参数

| 项 | 值 |
|---|---|
| 引擎 | `kokoro==0.9.4` / `misaki==0.9.4` |
| 模型 | `hexgrad/Kokoro-82M-v1.1-zh` |
| revision | `01e7505bd6a7a2ac4975463114c3a7650a9f7218` |
| 模型 SHA256 | `b1d8410fa44dfb5c15471fd6c4225ea6b4e9ac7fa03c98e8bea47a9928476e2b` |
| voice | `zf_001` |
| voice 实物 SHA256 | `9bdc9a87e13e9bb1ea3e7803259c2ecbfebaeeb2ff80b5d0c76df1a464c1c962` |
| 推理 | `lang_code=z`，CPU，speed `0.88`，24 kHz mono |
| 发行编码 | Ogg/Opus，24 kHz mono，48 kbps CBR，`application=voip` |
| 模型许可 | Apache-2.0（[模型卡](https://huggingface.co/hexgrad/Kokoro-82M-v1.1-zh)） |

模型与 voice 仅用于构建期生成，未提交仓库、未进入 Web/PWA/Android 包。课程文本来自 `src/data/chars/u1.js`；内容许可边界遵循根目录 `CONTENT_LICENSE.md`。

## 3. 资产清单

| # | 字卡 | 单字文件（bytes / ms） | 例句文件（bytes / ms） |
|---:|---|---|---|
| 1 | 一 `yī` | `u1-01-yi-char.ogg`（5,972 / 956） | `u1-01-yi-sentence.ogg`（16,311 / 2,656） |
| 2 | 二 `èr` | `u1-02-er-char.ogg`（5,851 / 932） | `u1-02-er-sentence.ogg`（15,585 / 2,532） |
| 3 | 三 `sān` | `u1-03-san-char.ogg`（6,214 / 982） | `u1-03-san-sentence.ogg`（16,795 / 2,732） |
| 4 | 上 `shàng` | `u1-04-shang-char.ogg`（6,483 / 1,032） | `u1-04-shang-sentence.ogg`（15,585 / 2,532） |
| 5 | 下 `xià` | `u1-05-xia-char.ogg`（6,362 / 1,006） | `u1-05-xia-sentence.ogg`（14,738 / 2,382） |
| 6 | 人 `rén` | `u1-06-ren-char.ogg`（5,972 / 956） | `u1-06-ren-sentence.ogg`（15,101 / 2,456） |
| 7 | 口 `kǒu` | `u1-07-kou-char.ogg`（6,362 / 1,006） | `u1-07-kou-sentence.ogg`（14,738 / 2,382） |
| 8 | 大 `dà` | `u1-08-da-char.ogg`（5,972 / 956） | `u1-08-da-sentence.ogg`（16,795 / 2,732） |
| 9 | 小 `xiǎo` | `u1-09-xiao-char.ogg`（6,483 / 1,032） | `u1-09-xiao-sentence.ogg`（15,585 / 2,532） |
| 10 | 我 `wǒ` | `u1-10-wo-char.ogg`（5,851 / 932） | `u1-10-wo-sentence.ogg`（15,706 / 2,556） |
| 11 | 个 `gè` | `u1-11-ge-char.ogg`（5,851 / 932） | `u1-11-ge-sentence.ogg`（16,069 / 2,606） |
| 12 | 们 `men` | `u1-12-men-char.ogg`（5,851 / 932） | `u1-12-men-sentence.ogg`（17,763 / 2,882） |

完整 64 位 SHA256 见同目录 `manifest.json`；smoke 不信任表格汇总，会读取每份构建后文件重新计算。

## 4. 接线与并发规则

- `src/utils/offlineTts.js` 以课程汉字作为稳定 key，只允许 `character` / `sentence` 两类白名单路径；原《静夜思》API 保持兼容。
- `CharDetailView.vue` 对 L1 卡显示“离线老师范读”，并在页面根节点标记 `data-tts="offline-l1"`；其余字卡保持 `system`。
- 每次新朗读先取消上一份本地音频和系统 SpeechSynthesis。异步播放用递增 run id 防止“旧本地音频被取消后又触发旧文本系统回退”的竞态。
- 关闭家长设置里的朗读时不会绕过静音设置播放本地资产；切字、离页和切后台都会取消。
- 词语不在本批冻结范围，仍走系统 TTS；这样不会把单字素材错误复用成词内读音。

## 5. 自动门与人工听审

`ROUND14_H5_SMOKE` 同时验证：

1. dist 清单可解析，marker 为 `ROUND14_H5`；
2. 去重音频 ≥20，实交 24；12 张卡均有单字和例句；
3. 每份 ≥4 KiB、Ogg 魔数 + `OpusHead`、时长 ≥500 ms；
4. 清单 bytes、总字节、总时长、逐份 SHA256 与构建产物完全一致；
5. 浏览器点击“一”的单字和例句后，两次都从同源 `audio/tts-l1/` 得到 `audio/ogg` 200 响应。

人工 W5 量表仍需两名普通话教师逐条记录：字音/声调、轻声与变调、停连、可懂度、异常噪声；关键错音必须为 0。若任一条失败，只重生成对应条目并更新清单哈希，不允许静默替换。

## 6. 复验命令

```bash
npm --prefix apps/literacy-app run build
npm --prefix apps/literacy-app run smoke
npm run check:round14
```

`check:round14` 在其余 R14 分支尚未集成时整体非零属于预期；本分支应看到 H5 单项 PASS。
