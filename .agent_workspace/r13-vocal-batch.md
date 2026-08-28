Model slug: gpt-5.6-sol-xhigh-fast

# Round 13 H4：儿歌离线范唱批次

## 交付结论

`ROUND13_H4 = 'three-offline-vocal-guides'`。`songs.js` 现在为 sg1《一二三，爬上山》、
sg3《洗手歌》和 sg5《认字歌》各声明一条 `vocal` 路径，三份 Ogg 都在
`public/audio/songs/` 随包交付。儿歌页沿用独立的“听「啦」音范唱”入口：范唱不会
替换正常伴奏，停止、切歌和离开页面都会释放媒体对象。

这是固定音色演唱音高的合成「啦」音示范，不是中文歌词真人演唱。界面继续明确写
「啦」音，避免把合成人声描述成真人录音。Round 13 把 Round 12 的 sg5 单曲试点扩到
三首；sg1 与 sg3 的速度和逐字音符均直接取自 `songs.js`，因此范唱、旋律和逐字谱面
使用同一份节拍契约。

## 资产清单

| 歌曲 | `vocal` 资产 | BPM | 时长 | 字节 | SHA-256 |
|---|---|---:|---:|---:|---|
| sg1《一二三，爬上山》 | `sg1-climb-vocal-guide.ogg` | 96 | 18.800s | 82,289 | `5b0d63ca25b70c5f516e3258569c0cb45d9e0d1fafcb9d1e345a0dbaa2251ef2` |
| sg3《洗手歌》 | `sg3-wash-hands-vocal-guide.ogg` | 92 | 21.600s | 93,353 | `d0364297affba7c913c970a75a016537050c40c83ba215be06ed3df402e167af` |
| sg5《认字歌》 | `sg5-literacy-vocal-pilot.ogg` | 88 | 17.800s | 75,842 | `4aa66448bb55bce84e98bf6a5ebd1ebc6de2b2f7e70592029ca1e022641cc9ed` |

三份均为 Ogg/Vorbis、22,050Hz、单声道，超过 Round 13 探针要求的 8KiB。普通字一拍、
句末字两拍、句间留半拍；Piper 男声音高整体下移一个八度，保留 C3–C4 的舒适范唱
音域。每首使用不同 public 路径，门槛按去重资产计数。

## 生成来源与许可

- 生成器：`piper-tts==1.7.0`，仅用于开发期离线渲染，不进入 Web 或 Android 包。
- Voice：`sv_SE-nst-medium`；模型 revision
  `2f8dbe0bb0dde986411632bf014a13cdbe6596e7`，SHA-256
  `df011f56825a59dd1ef70407e60f63050e9246f43a3d7e471e`。
- 配置 revision `9f800697ad9dfc9533f9e6191d04da0ecdd204f5`，SHA-256
  `d45dd74cbb4eca58694bf04a97e243044092476f28a55ae26424f0653086980a`。
- Voice 模型卡声明 NST 训练数据为 CC0，由 KBLab / National Library of Sweden
  从零训练；Piper Voices 仓库为 MIT。发行包只含生成后的 Ogg，不含 Piper GPL
  运行时或 63.1MB ONNX 权重。
- 没有采用许可证标为 Unknown 的普通话 `huayan` 模型，也没有把这批「啦」音示范
  冒充中文歌词演唱。中文歌词真人范唱仍需另行取得演播者书面授权。

参考：

- `https://huggingface.co/rhasspy/piper-voices/raw/main/sv/sv_SE/nst/medium/MODEL_CARD`
- `https://www.nb.no/sprakbanken/en/resource-catalogue/oai-nb-no-sbr-17/`

## 可复现命令

取得并核对上述固定 revision 的模型与配置后，从仓库根目录运行：

```bash
python3 -m pip install --target /tmp/r13-piper piper-tts==1.7.0
PYTHONPATH=/tmp/r13-piper python3 apps/literacy-app/scripts/generate-song-vocal-pilot.py \
  --model /path/to/sv_SE-nst-medium.onnx \
  --config /path/to/sv_SE-nst-medium.onnx.json \
  --song sg1
PYTHONPATH=/tmp/r13-piper python3 apps/literacy-app/scripts/generate-song-vocal-pilot.py \
  --model /path/to/sv_SE-nst-medium.onnx \
  --config /path/to/sv_SE-nst-medium.onnx.json \
  --song sg3
```

`--song sg5` 可重建原有试点。脚本先拒绝哈希不符的输入，再固定 Piper 噪声参数、
估计「La」种子基频，用 FFmpeg rubberband 逐音移调和伸缩，最后做响度归一与
22.05kHz 回采样。

## 验收

- `npm run check:round13`：H4 必须报告三首范唱资产并命中 `ROUND13_H4`。
- 识字 smoke：构建产物中三条 `vocal` 都必须存在、具有 Ogg/MP3 魔数、至少 10KiB
  且路径去重；同时保留 sg5 范唱入口的实际播放与停止验证。
- `npm run check:data`：儿歌歌词、拼音和音符覆盖契约继续通过。
