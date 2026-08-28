Model slug: claude-opus-4-6-fast（Round 14-3 收尾批次；前九首由 gpt-5.6-sol 于 Round 14-1 交付）

# Round 14 H4：真人声源儿歌范唱全库批次（13/13）

## 交付结论

`ROUND14_H4 = 'thirteen-human-studio-vocal-guides'`。`songs.js` 的 **13 首儿歌
全部** 带 `vocal` 随包 Ogg 范唱且逐首标注 `humanStudio: true`，真人声源覆盖从
Round 14-1 的 **9/13** 收口到 **13/13**。

本批（Round 14-3）新增 sg1、sg2、sg3、sg5 四份成品：

- sg2《小雨点》此前**完全没有**范唱，本批首次补齐；
- sg1《一二三，爬上山》、sg3《洗手歌》、sg5《认字歌》此前挂的是 Round 12/13 的
  Piper 合成「啦」音，本批用同一份真人棚录声源重制，并把三份 Piper Ogg
  （`sg1-climb-vocal-guide.ogg`、`sg3-wash-hands-vocal-guide.ogg`、
  `sg5-literacy-vocal-pilot.ogg`）从 `public/` 删除，避免包里同时躺着两代资产。

十三份成品都来自真实专业歌手的棚录元音，不是 Piper/TTS。为避免暗示歌手录过本项目
中文歌词，界面准确写作“真人声源「啊」音范唱”：成品示范原创谱面的音高、节拍与换气
位置，但不构成中文歌词演唱。

## 资产清单（13/13）

| 歌曲 | `vocal` 文件 | BPM | 时长 | 字节 | SHA-256 | 批次 |
|---|---|---:|---:|---:|---|---|
| sg1《一二三，爬上山》 | `sg1-climb-vocal-human.ogg` | 96 | 18.800s | 87,719 | `c5d24d4607312f23af0a8a71735b6ca9e205f215fb1d40d5b0c196cad0c417a7` | R14-3 |
| sg2《小雨点》 | `sg2-raindrop-vocal-human.ogg` | 100 | 19.800s | 93,419 | `414746a5cca59f0325159d22c94eca9785681dd90b4f24f834888fde096e7e68` | R14-3 |
| sg3《洗手歌》 | `sg3-wash-hands-vocal-human.ogg` | 92 | 21.600s | 100,811 | `5dbb24e1f96ff903108b48d17d894886c9984c344d3a43326c25d7bde8973eae` | R14-3 |
| sg4《大树和小鸟》 | `sg4-tree-bird-vocal-human.ogg` | 104 | 18.500s | 87,268 | `c134056f81f2876dd1f7a4dfdf7a9e8e87b562d6e87924242e9d30bdca8a9e4c` | R14-1 |
| sg5《认字歌》 | `sg5-literacy-vocal-human.ogg` | 88 | 17.800s | 82,207 | `59e0d0afbd12cb7030e1fb07bdd2ad20d27ed6ca08a244baa7c12d22852c9dca` | R14-3 |
| sg6《你好和谢谢》 | `sg6-hello-thanks-vocal-human.ogg` | 90 | 17.400s | 80,274 | `07e41578008efb02cb05eabebcd41f989c9d27c11ffee18d0c79c6a1eb284ff3` | R14-1 |
| sg7《四季歌》 | `sg7-four-seasons-vocal-human.ogg` | 84 | 18.600s | 85,433 | `801bf4b540077c5d2d5420624476b077919c8e272dded3c62ee0be7dd3bf07af` | R14-1 |
| sg8《一家人》 | `sg8-family-vocal-human.ogg` | 94 | 20.500s | 96,181 | `85619700fdea2691dbc0187a7e345e887ab1be1c6f4e56e47e2b4e135b8658f2` | R14-1 |
| sg9《妈妈的手》 | `sg9-mothers-hands-vocal-human.ogg` | 82 | 23.500s | 108,899 | `3ef55a33d7b120784d0bc7b9e28a291ec3920e0f7e0a545ef46a2672807fa901` | R14-1 |
| sg10《小手小脚》 | `sg10-hands-feet-vocal-human.ogg` | 98 | 16.000s | 73,861 | `a707b26c4773d0e7cca21b6ad2aac5f44ed7c3c3ed09b2c54bf9e8a94f57297e` | R14-1 |
| sg11《从十数到一》 | `sg11-countdown-vocal-human.ogg` | 86 | 18.200s | 83,264 | `3ca1c1a44f9c55d923f6ca8dd133e435e09ea2d9eb9384bb709126315e9d2027` | R14-1 |
| sg12《木字歌》 | `sg12-wood-character-vocal-human.ogg` | 90 | 20.700s | 96,015 | `b93be7edd02d3dffa18505d69791179609fc3bbe04f858fb22669a48b7a9a17a` | R14-1 |
| sg13《对不起，没关系》 | `sg13-sorry-vocal-human.ogg` | 88 | 21.200s | 97,990 | `5e6696deba2e86bbbe51895eac27205aa137b6bc39787228fff7075a7f90a4c1` | R14-1 |

全部文件是 Ogg/Vorbis、22,050Hz、单声道、**单一音频流**，体积均明显超过 H4 的
10,240B 地板，路径互不重复。普通字一拍、句末字两拍、句间半拍，音符序列与
`songs.js` 同源；时长可由 `60/BPM ×（每句音符数 + 1 拍句末延长 + 0.5 拍句间）`
逐首反算，四份新成品与该公式一致。制作时优先使用源琶音中的 C4/E4/G4/C5 实录音符；
只让 D4 和 A4 从相邻实录音高移动两个半音，避免单样本跨八度拉伸造成的机械感。最终
统一到 -18 LUFS、true peak -2dB，并保留短起音和句间换气空间。

R14-1 的九份成品字节与哈希在本批次逐一复核，与 Round 14-1 记录完全一致，未被本批
重新渲染。

## 生成器修复：多余音频流

R14-3 渲染 sg5 时暴露出 `generate-song-vocal-pilot.py` 的一个真实缺陷：sg5《认字歌》
的谱面只用到 C4/D4/E4/G4/A4，不含 C5，于是 C5 那路种子在 filter graph 里没有任何
消费者，留下一个**未命名输出**。ffmpeg 会把未命名的 filter 输出自动映射进输出文件，
成品因此多带了一条把整段 C5 种子原样塞进去的音频流（88,530B、双流）。本批修了两处：

1. `render_guide()` 先按谱面实际用到的音源裁剪 `sources`，不给未使用的种子建输入；
2. 新增 `assert_single_stream()`，落盘后用 ffprobe 断言成品恰好一条流。

修复后 sg5 回到单流 82,207B。已落库的十三份成品逐一过 ffprobe 复核，`streams=1`
全绿——R14-1 的九首都用到 C5，没有踩到这个坑，因此无需重渲。

## 真人声源、许可与修改

- 数据集：VocalSet 1.2，DOI <https://doi.org/10.5281/zenodo.1442513>。
- 作者/版权归属：Julia Wilkins、Prem Seetharaman、Alison Wahl、Bryan Pardo（2018）。
- 许可：[Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/)；
  允许复制与改编，要求适当署名、链接许可证并说明修改。
- 固定输入：匿名专业歌手的 straight-vowel C 大调琶音，在
  `Bill13579/vocalset-mirror` 映射为 `default/train` row 55；44.1kHz、16-bit、
  mono、7.592971s。输入 SHA-256 为
  `451381cd80d9006251a3af694251abb9c756bafa5051130635142abbc210f3de`。本批次重新
  取回该行并核对，哈希与 Round 14-1 记录逐字节一致，四份新成品与九份旧成品同源。
- 修改：裁取四段稳定音，按项目谱面校准音高、时值伸缩、逐音淡入淡出、拼接句间静音、
  响度归一、回采样并转码 Ogg。原始数据集或完整源 WAV 不随 App 分发。
- 署名与修改说明已同步到根目录 `THIRD_PARTY_NOTICES.md`、`CONTENT_LICENSE.md` 和
  `public/audio/songs/README.md`（均已从「九份」改口径为「十三份 / 全库」），构建包
  会继续携带根 NOTICE。

## 可复现命令

先从上述固定数据行取得 WAV 并核对输入 SHA-256，再从仓库根目录运行：

```bash
sha256sum /path/to/vocalset-straight-a.wav
for song in sg1 sg2 sg3 sg4 sg5 sg6 sg7 sg8 sg9 sg10 sg11 sg12 sg13; do
  python3 apps/literacy-app/scripts/generate-song-vocal-pilot.py \
    --human-source /path/to/vocalset-straight-a.wav \
    --song "$song"
done
```

本批实际只跑了 `sg1 sg2 sg3 sg5` 四首；其余九首沿用 R14-1 落库成品。生成器会先拒绝
哈希、声道、位深或采样率不符的输入，再从实录琶音裁出四个近邻多采样。FFmpeg
`rubberband` 只负责调音与时长适配，`loudnorm` 负责统一播放响度；这些工具均只在开发
期使用，不进入浏览器或 Android 包。Round 12/13 的 Piper 路径仍保留在生成器里
（`--model` / `--config` + `legacy_asset`），只是产物不再随包分发。

## 验收口径与实测

数据侧应看到 13 首歌、**十三首** `humanStudio === true` 且十三条 `vocal` 指向 public
下互不重复的有效音频；每份成品须有 `OggS` 魔数、≥10KiB、22.05kHz 单声道单流，且时长
与对应 BPM/音符数一致。

本分支实测（`18d6e4c` 基线 → 本分支）：

| 门禁 | 基线 | 本分支 | 说明 |
|---|---|---|---|
| `check:round14` H4 | ✗ `humanVocal=9/13` | ✓ `范唱全库 13/13 真人 + ROUND14_H4` | 本批目标 |
| `check:round14` 总计 | 2/8 | **3/8** | H3、H4、H5 绿 |
| `check:round13` | 6/8 | 6/8 | H4「范唱批次 13 首（≥3）+ 13/13 音频」仍绿，无退化 |
| `check:round12` | 8/8 | 8/8 | 无退化 |
| `literacy-app` `check:data` | 80/0 | 80/0 | 无退化 |

**H8 仍红，且不在本批可解范围**：`check:round14` 的 H8 要求 `check:round13`
8/8，而 R13 的 H6（Android 模拟闭环）与 H7（商店实提）在无真机、无 Console 回执的
前提下无法诚实翻绿——这两项分别归 Round 14-3 的 #16 与 #15。因此本分支交付的诚实
上限是 `check:round14` 3/8，简报里 4/8 的预期需要 H8 依赖项先落地；本分支不做任何
伪造真机或伪造提交回执的动作来凑数。

盲听签核（≥3 人、含至少 1 名目标年龄段儿童家长）仍属线下环节，本分支未执行、
未代签，标记为 BLOCKED（owner：体验终审 #13）。
