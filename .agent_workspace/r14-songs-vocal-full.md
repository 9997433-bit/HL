Model slug: gpt-5.6-sol

# Round 14 H4：真人声源儿歌范唱批次

## 交付结论

`ROUND14_H4 = 'nine-human-studio-vocal-guides'`。本批为 sg4 与 sg6–sg13
共九首尚无范唱的儿歌新增随包 Ogg 资产，并在 `songs.js` 逐首设置
`humanStudio: true`。本分支因此把 Round 14 的真人声源覆盖从 0/13 提升到
**9/13**，超过本轮“至少 7 首”的阶段目标。sg1、sg2、sg3、sg5 尚未进入这一
真人声源批次；其中 sg1、sg3、sg5 的旧 Piper 合成「啦」音仍保留且没有被虚标为
`humanStudio`。所以本分支不会宣称已达 13/13 全库终局，Round 14 H4 探针在后续
收尾分支补齐余下四首之前保持红灯是预期行为。

九份新增成品都来自真实专业歌手的棚录元音，不是 Piper/TTS。为避免暗示歌手录过
本项目中文歌词，界面准确写作“真人声源「啊」音范唱”：成品示范原创谱面的音高、
节拍与换气位置，但不构成中文歌词演唱。

## 资产清单

| 歌曲 | `vocal` 文件 | BPM | 时长 | 字节 | SHA-256 |
|---|---|---:|---:|---:|---|
| sg4《大树和小鸟》 | `sg4-tree-bird-vocal-human.ogg` | 104 | 18.500s | 87,268 | `c134056f81f2876dd1f7a4dfdf7a9e8e87b562d6e87924242e9d30bdca8a9e4c` |
| sg6《你好和谢谢》 | `sg6-hello-thanks-vocal-human.ogg` | 90 | 17.400s | 80,274 | `07e41578008efb02cb05eabebcd41f989c9d27c11ffee18d0c79c6a1eb284ff3` |
| sg7《四季歌》 | `sg7-four-seasons-vocal-human.ogg` | 84 | 18.600s | 85,433 | `801bf4b540077c5d2d5420624476b077919c8e272dded3c62ee0be7dd3bf07af` |
| sg8《一家人》 | `sg8-family-vocal-human.ogg` | 94 | 20.500s | 96,181 | `85619700fdea2691dbc0187a7e345e887ab1be1c6f4e56e47e2b4e135b8658f2` |
| sg9《妈妈的手》 | `sg9-mothers-hands-vocal-human.ogg` | 82 | 23.500s | 108,899 | `3ef55a33d7b120784d0bc7b9e28a291ec3920e0f7e0a545ef46a2672807fa901` |
| sg10《小手小脚》 | `sg10-hands-feet-vocal-human.ogg` | 98 | 16.000s | 73,861 | `a707b26c4773d0e7cca21b6ad2aac5f44ed7c3c3ed09b2c54bf9e8a94f57297e` |
| sg11《从十数到一》 | `sg11-countdown-vocal-human.ogg` | 86 | 18.200s | 83,264 | `3ca1c1a44f9c55d923f6ca8dd133e435e09ea2d9eb9384bb709126315e9d2027` |
| sg12《木字歌》 | `sg12-wood-character-vocal-human.ogg` | 90 | 20.700s | 96,015 | `b93be7edd02d3dffa18505d69791179609fc3bbe04f858fb22669a48b7a9a17a` |
| sg13《对不起，没关系》 | `sg13-sorry-vocal-human.ogg` | 88 | 21.200s | 97,990 | `5e6696deba2e86bbbe51895eac27205aa137b6bc39787228fff7075a7f90a4c1` |

全部文件是 Ogg/Vorbis、22,050Hz、单声道，体积均明显超过 H4 的 10,240B
地板，路径互不重复。普通字一拍、句末字两拍、句间半拍，音符序列与
`songs.js` 同源。制作时优先使用源琶音中的 C4/E4/G4/C5 实录音符；只让 D4
和 A4 从相邻实录音高移动两个半音，避免单样本跨八度拉伸造成的机械感。最终统一
到 -18 LUFS、true peak -2dB，并保留短起音和句间换气空间。

## 真人声源、许可与修改

- 数据集：VocalSet 1.2，DOI
  <https://doi.org/10.5281/zenodo.1442513>。
- 作者/版权归属：Julia Wilkins、Prem Seetharaman、Alison Wahl、Bryan Pardo
  （2018）。
- 许可：[Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/)；
  允许复制与改编，要求适当署名、链接许可证并说明修改。
- 固定输入：匿名专业歌手的 straight-vowel C 大调琶音，在
  `Bill13579/vocalset-mirror` 映射为 `default/train` row 55；44.1kHz、
  16-bit、mono、7.592971s。输入 SHA-256 为
  `451381cd80d9006251a3af694251abb9c756bafa5051130635142abbc210f3de`。
- 修改：裁取四段稳定音，按项目谱面校准音高、时值伸缩、逐音淡入淡出、拼接句间
  静音、响度归一、回采样并转码 Ogg。原始数据集或完整源 WAV 不随 App 分发。
- 署名与修改说明已同步到根目录 `THIRD_PARTY_NOTICES.md`、
  `CONTENT_LICENSE.md` 和 `public/audio/songs/README.md`，构建包会继续携带根
  NOTICE。

## 可复现命令

先从上述固定数据行取得 WAV 并核对输入 SHA-256，再从仓库根目录运行：

```bash
sha256sum /path/to/vocalset-straight-a.wav
for song in sg4 sg6 sg7 sg8 sg9 sg10 sg11 sg12 sg13; do
  python3 apps/literacy-app/scripts/generate-song-vocal-pilot.py \
    --human-source /path/to/vocalset-straight-a.wav \
    --song "$song"
done
```

生成器会先拒绝哈希、声道、位深或采样率不符的输入，再从实录琶音裁出四个近邻
多采样。FFmpeg `rubberband` 只负责调音与时长适配，`loudnorm` 负责统一播放响度；
这些工具均只在开发期使用，不进入浏览器或 Android 包。

## 验收口径

数据侧应看到 13 首歌、九首 `humanStudio === true` 且九条新增 `vocal` 指向
public 下不同的有效音频；每份成品须有 `OggS` 魔数、≥10KiB、22.05kHz 单声道，
且时长与对应 BPM/音符数一致。`npm run check:data`、Round 12 和 Round 13 门禁
必须不退化。`npm run check:round14` 在本阶段应报告 `humanVocal=9/13`，不是
13/13；余下 sg1、sg2、sg3、sg5 的真人声源替换及全库盲听签核留给 H4 收尾批次。
