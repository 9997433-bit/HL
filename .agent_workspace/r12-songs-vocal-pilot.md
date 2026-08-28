Model slug: gpt-5.6-sol-xhigh-fast

# Round 12 H4：儿歌 13/13 与离线范唱试点

## 交付结论

`ROUND12_H4 = 'thirteen-offline-melodies-with-vocal-pilot'`。`songs.js` 的 13 首歌
现在各自指向一份随包的 Ogg 旋律，文件均大于 10KB；sg9–sg13 延续 R10/R11 的原创
谱面、22.05kHz 单声道加法合成与 Vorbis 管线。文件播放失败时仍自动回退 WebAudio，
不把离线资产支持差的旧 WebView 变成无声状态。

《认字歌》（sg5）另带 `sg5-literacy-vocal-pilot.ogg`。页面显示
“听「啦」音范唱”按钮，试听和停止都走独立状态，且不替换逐字同步的正常伴奏。
这条试点是 **Piper 合成的「啦」音旋律示范，不是中文歌词真人演唱**；界面和文档均
明确标注，避免把合成人声包装成真人录音。它用于验证固定人声音色、离线随包播放、
授权与体积链路，中文歌词演唱仍需要后续有书面授权的演播者录制。

## 资产清单

| 资产 | 时长 | 字节 | SHA-256 |
|---|---:|---:|---|
| `sg9-mothers-hands-melody.ogg` | 23.414s | 34,042 | `8ecba0923a17a33676f96918c4b968ae1879dd96edba3c742a50076c1e6c94ac` |
| `sg10-hands-feet-melody.ogg` | 15.918s | 24,525 | `9ee2a9d0a1fd46005aa9ed9b0dc63a305a20d6b6247b5b74b5d3b4a69589afc6` |
| `sg11-countdown-melody.ogg` | 18.140s | 26,947 | `e672d5289fd81f5955a56f297a7c3ba68a9f1ae96a114822974157fb33744fb9` |
| `sg12-wood-character-melody.ogg` | 20.667s | 31,036 | `c5c7799cd6fb04eefc0f150563265014851a2b51945a9cf2b30fce40b8e7d026` |
| `sg13-sorry-melody.ogg` | 21.136s | 31,361 | `3560181d7b014910bee2ae83679d417eade31a371f8aba1cee420384b71ef148` |
| `sg5-literacy-vocal-pilot.ogg` | 17.800s | 75,842 | `4aa66448bb55bce84e98bf6a5ebd1ebc6de2b2f7e70592029ca1e022641cc9ed` |

全部为 Ogg/Vorbis、22,050Hz、单声道。sg9–sg13 的谱面与 `songs.js` 对齐：普通字
一拍，句尾两拍，句间半拍；范唱同样使用 sg5 的 88 BPM 和音符走向，按成人男声
舒适音域整体下移一个八度到 C3–A3。

## Piper 输入、授权与边界

- 生成器：`piper-tts==1.7.0`，只在开发机离线渲染，不进入 Web/Android 包。
- Voice：`sv_SE-nst-medium`。模型 revision
  `2f8dbe0bb0dde986411632bf014a13cdbe6596e7`，SHA-256
  `df011f56825a59dd1efc080c38a65a1ef70407e60f63050e9246f43a3d7e471e`。
- 配置 revision `9f800697ad9dfc9533f9e6191d04da0ecdd204f5`，SHA-256
  `d45dd74cbb4eca58694bf04a97e243044092476f28a55ae26424f0653086980a`。
- 该 voice 的 `MODEL_CARD` 明示：NST 数据集为 **CC0**，KBLab / National
  Library of Sweden 从零训练。Piper Voices 仓库标 MIT。发行包只含生成后的 Ogg，
  不含 Piper GPL 运行时或 63.1MB ONNX 权重。
- 没有采用普通话 `huayan`：其模型卡把训练数据许可证写成 `Unknown`，不满足简报
  “CC0/自建/明确授权”的要求。没有用未知来源模型冒充完成度。

参考：

- `https://huggingface.co/rhasspy/piper-voices/raw/main/sv/sv_SE/nst/medium/MODEL_CARD`
- `https://www.nb.no/sprakbanken/en/resource-catalogue/oai-nb-no-sbr-17/`

## 可复现命令

先取得上述两个固定 revision 文件（或用 `piper.download_voices` 下载后让脚本校验
哈希），再运行：

```bash
python3 -m pip install --target /tmp/r12-piper piper-tts==1.7.0
PYTHONPATH=/tmp/r12-piper python3 apps/literacy-app/scripts/generate-song-vocal-pilot.py \
  --model /path/to/sv_SE-nst-medium.onnx \
  --config /path/to/sv_SE-nst-medium.onnx.json
```

脚本会拒绝哈希不符的 voice/config，固定 Piper 噪声参数，估计源「La」基频，再用
FFmpeg rubberband 按 sg5 音符移调、按拍速伸缩、响度归一并回采样到 22.05kHz。
完整旋律可用 `python3 apps/literacy-app/scripts/generate-song-audio.py` 重建，也可重复
`--song <asset-name>` 只生成指定歌曲。

## 验收口径

`check:round12` 的 H4 会在源码侧按去重路径检查 13 份 public 资产均 ≥10KB，并要求
范唱文档与 `ROUND12_H4`。识字 smoke 进一步在构建产物里校验 13/13 的 Ogg/MP3
魔数、体积和去重，校验范唱文件，再实际打开 sg5、点击范唱、确认进入 file 播放态并
可停止。`check:bundle` 用于确认这些按路由加载的音频没有被错误内联进 JavaScript。
