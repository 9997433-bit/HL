# THIRD PARTY NOTICES · 第三方组件与素材声明

本文件列出「洪恩式教育双 App」（`apps/literacy-app` 快乐识字、`apps/math-app` MathQuest）
及本仓库共享资源所使用的全部第三方代码、数据与素材，以及各自的许可证义务。

- 适用范围：本仓库源代码、`npm run build:all` 产出的
  `dist/hongen-literacy-app.zip` 与 `dist/hongen-math-app.zip`，以及任何据此部署的静态站点。
- 版本以根目录 `package-lock.json` 锁定为准；下表版本为本文件更新时的实测安装版本。
- 再分发本项目（源码或构建产物）时，请将本文件一并分发。打包脚本
  `scripts/build-all.sh` 会自动把本文件放入两个 zip。
- 更新任何依赖、笔顺数据或素材后，须同步更新本文件并重跑
  `bash scripts/verify-resources.sh`（合规项 C-2，见
  `.agent_workspace/sota-acceptance-criteria.md`）。

---

## 一、随构建产物分发的运行时依赖

以下库的代码会被 Vite 打进 `dist/assets/*.js`，随两个 zip 分发。

| 组件 | 版本 | 许可证 | 版权 | 使用方 |
|---|---|---|---|---|
| [Vue](https://github.com/vuejs/core) | 3.5.x | MIT | Copyright (c) 2018-present, Yuxi (Evan) You | 双 App |
| [Vue Router](https://github.com/vuejs/router) | 4.x | MIT | Copyright (c) 2019-present Eduardo San Martin Morote | 双 App |
| [Pinia](https://github.com/vuejs/pinia) | 2.x | MIT | Copyright (c) 2019-present Eduardo San Martin Morote | 双 App |
| [GSAP](https://github.com/greensock/GSAP) | 3.x | [GSAP Standard License](https://gsap.com/standard-license) | Copyright (c) 2008-2026, GreenSock, Inc. | 双 App |
| [Hanzi Writer](https://github.com/chanind/hanzi-writer) | 3.7.x | MIT | Copyright (c) 2014 David Chanin | 识字 App |
| [Tesseract.js](https://github.com/naptha/tesseract.js) | 7.0.x | Apache-2.0 | Copyright (c) 2016 Kevin Kwok | 识字 App |
| [tesseract.js-core](https://github.com/naptha/tesseract.js-core) | 7.0.x | Apache-2.0 | Copyright (c) 2016 Kevin Kwok；含 Tesseract OCR（Apache-2.0，Copyright Google Inc.）与 Leptonica（BSD-2-Clause）的 wasm 编译产物 | 识字 App |

MIT 许可证全文见本文件「附录 A」，对上表全部 MIT 组件适用（版权行各自替换）。

**GSAP 说明**：GSAP 不是 MIT 许可证。自 3.13 起 GSAP 依
[GSAP Standard License](https://gsap.com/standard-license) 免费提供（含商业使用），
但该许可证禁止将 GSAP 用于构建与 GSAP 竞争的动画工具，并有其他条款。
本项目仅将其作为应用内动画库使用，符合该许可证；升级 GSAP 版本时应复核许可证是否变更。

**Tesseract.js 说明**：只有主线程那一小段（`createWorker`）会被 Vite 打进
`dist/assets/`，且是懒加载块。真正干活的 `worker.min.js` 与 wasm 内核
`tesseract-core-simd-lstm.wasm.js` 由 `apps/literacy-app/scripts/gen-ocr-assets.mjs`
从 npm 包原样复制到 `public/ocr/`，作为独立文件随 dist 与 zip 分发（未修改）。
Apache-2.0 要求随附许可证与 NOTICE：许可证全文见「附录 B」指向的上游地址，
两个包的 `LICENSE` 文件保留在 `node_modules` 中。

## 二、随构建产物分发的第三方数据

### Hanzi Writer Data（汉字笔顺数据）— Arphic Public License

- 上游：[chanind/hanzi-writer-data](https://github.com/chanind/hanzi-writer-data)（npm `hanzi-writer-data` 2.0.x），
  数据源自 [skishore/makemeahanzi](https://github.com/skishore/makemeahanzi)，
  底层字形版权归 Arphic Technology Co., Ltd.（文鼎科技）。
- 许可证：**Arphic Public License（APL）**。注意 MIT 只覆盖 Hanzi Writer 的代码，
  不覆盖笔顺数据；两者不可混淆。
- 本仓库的分发位置：
  - `apps/literacy-app/public/hanzi-data/`：由 `scripts/gen-hanzi-data.mjs`
    从 npm 包裁剪出的 200+ 字离线笔顺 JSON（仅保留 `strokes`/`medians` 字段，属 APL 意义上的
    修改/衍生数据），随识字 App 的 dist 与 zip 分发，并被 Service Worker 预缓存。
  - `shared/assets/hanzi-writer-data/`：3 个离线样本（`人.json`、`日.json`、`山.json`）。
- **义务**：APL 要求再分发（含修改后的数据）时随附许可证全文。本仓库在上述两个目录中
  各放置一份 `ARPHICPL.TXT`；`gen-hanzi-data.mjs` 每次重新生成数据时会自动复制该文件，
  请勿从发行包中删除。
- 运行时回退：本地缺字时识字 App 会从
  `https://cdn.jsdelivr.net/npm/hanzi-writer-data@2/` 拉取单字 JSON（同为 APL 数据）。
  课程字表全部离线内置，正常使用不触发该请求。

### Tesseract chi_sim 语言包（简体中文 OCR 模型）— Apache-2.0

- 上游：[tesseract-ocr/tessdata_fast](https://github.com/tesseract-ocr/tessdata_fast)，
  经 [tessdata.projectnaptha.com](https://tessdata.projectnaptha.com/4.0.0_fast/) 分发的
  gzip 副本。版权归 Google Inc. 及 Tesseract OCR 贡献者。
- 许可证：**Apache-2.0**，与 Tesseract OCR 本体一致。
- 本仓库的分发位置：`apps/literacy-app/public/ocr/chi_sim.traineddata.gz`
  （1.7 MB，未修改的上游文件，入库以保证断网也能构建与识字）。
- **义务**：随附 Apache-2.0 许可证（见「附录 B」）并保留版权声明；本文件即为声明载体。
  未对模型做任何修改，无需附加修改说明。

### 离线跟读评测包（sherpa-onnx WASM 运行时 + 中文流式 Zipformer int8 模型）— Apache-2.0

- 位置：`apps/literacy-app/public/asr/models/`，共 7 个文件、合计 **35.31 MiB**。
  逐文件的 `bytes` / `sha256` / 上游出处冻结在
  `apps/literacy-app/public/asr/manifest.json` 的 `files[]` 与 `source.files[]` 里，
  由 `scripts/test-asr-engine.mjs` 每次跑测时现核。
- 复现：`npm --prefix apps/literacy-app run gen:asr:pack`（脚本
  `scripts/gen-asr-pack.mjs` 里写死了 release tag 与模型 revision）。
- 分发状态：这些文件**会**随 dist 与 zip 分发（自托管是硬约束：运行时不许回退到任何
  第三方 CDN），但**不进首屏 precache**——只有家长在跟读页点「下载离线评测包」
  才会取，取完存进版本化 Cache Storage。当前 `available:false`，即这一档尚未放行。

| 文件 | 上游 | 许可证 | 修改 |
|---|---|---|---|
| `sherpa-onnx-wasm-main-asr.js` | [k2-fsa/sherpa-onnx](https://github.com/k2-fsa/sherpa-onnx) v1.12.15 release 资产 `sherpa-onnx-wasm-simd-v1.12.15-en-asr-zipformer.tar.bz2` | Apache-2.0 | **有**，见下 |
| `sherpa-onnx-wasm-main-asr.wasm` | 同上 | Apache-2.0 | 无 |
| `sherpa-onnx-asr.js` | 同上 | Apache-2.0 | 无 |
| `encoder.int8.onnx` | [csukuangfj/sherpa-onnx-streaming-zipformer-zh-14M-2023-02-23](https://huggingface.co/csukuangfj/sherpa-onnx-streaming-zipformer-zh-14M-2023-02-23) @ `204ad334` 的 `encoder-epoch-99-avg-1.int8.onnx` | Apache-2.0（上游模型卡） | 无（仅重命名） |
| `decoder.int8.onnx` | 同上 `decoder-epoch-99-avg-1.int8.onnx` | Apache-2.0 | 无（仅重命名） |
| `joiner.int8.onnx` | 同上 `joiner-epoch-99-avg-1.int8.onnx` | Apache-2.0 | 无（仅重命名） |
| `tokens.txt` | 同上 | Apache-2.0 | 无 |

- **修改说明（Apache-2.0 第 4(b) 条要求标明）**：`sherpa-onnx-wasm-main-asr.js` 相对上游
  只改了一处——Emscripten `--preload-file` 生成的 `loadPackage({...})` 元数据被替换成
  `loadPackage({"files":[],"remote_package_size":0})`。原因是官方产物把一个 182 MiB 的
  英文大模型打进了配套 `.data`，我们不带那份 `.data`，改由 Worker 在运行时把中文 int8
  模型写进 Emscripten MEMFS。改动前后的 sha256 都记在 `manifest.source.files[]` 里
  （`upstreamSha256` 为改动前），`test-asr-engine.mjs` 有一条断言钉住「全文只此一处改动」。
- **模型来源链**：上游模型卡声明由
  [marcoyang/sherpa-ncnn-streaming-zipformer-zh-14M-2023-02-23](https://huggingface.co/marcoyang/sherpa-ncnn-streaming-zipformer-zh-14M-2023-02-23)
  经 icefall `export-onnx-zh.py` 导出（脚本随模型仓库分发）。本项目按上游模型卡标注的
  Apache-2.0 再分发；训练语料的授权由上游承担，本仓库未做二次训练也未修改权重。
- **义务**：随附 Apache-2.0 许可证（见「附录 B」）、保留版权声明、标明上述修改。本文件即声明载体。

### 引擎回归音频 `upstream-zh-0.wav` — Apache-2.0（随模型仓库）

- 位置：`apps/literacy-app/scripts/fixtures/asr/upstream-zh-0.wav`（175 KB，
  上游模型仓库 `test_wavs/0.wav` 的未修改副本，成人普通话 5.61 秒）。
- 用途：`scripts/test-asr-engine.mjs` 的引擎回归输入——证明落库的那 35 MiB 装得起来、
  解得出中文。**不进 `public/`、不打进 dist、不随 zip 分发**，也**不是**儿童冻结集
  （后者按 `.agent_workspace/r11-asr-eval-set.md` 另行录制，音频存仓库外）。
- 许可证：随上游模型仓库的 Apache-2.0；sha256 记在 `manifest.source.engineFixture`。

## 三、仓库内第三方素材（当前未打入 App 产物）

### OpenMoji 图标 — CC BY-SA 4.0

- 上游：[hfg-gmuend/openmoji](https://github.com/hfg-gmuend/openmoji)
- 位置：`shared/assets/openmoji/`（`apple.svg`、`target.svg`、`open-book.svg`、
  `numbers.svg`、`abacus.svg`、`star.svg`，为上游 color/svg 的未修改副本，仅重命名）。
- 许可证：素材为 [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)
  （全文见 `shared/assets/openmoji/LICENSE.txt`）；OpenMoji 辅助代码为 LGPL-3.0（本仓库未使用其代码）。
- **署名（分发或在界面中使用这些图标时必须保留）**：

  > All emojis designed by [OpenMoji](https://openmoji.org/) – the open-source emoji
  > and icon project. License:
  > [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).

- 若修改这些 SVG 形成衍生图标，衍生素材必须继续采用 CC BY-SA 4.0 并注明修改。
- 现状：两 App 导航、首页地图、字卡状态角标与庆祝层等界面已引用 OpenMoji SVG
  （通过 `@shared/components/OpenMojiIcon.vue` 打包进 dist）；署名见各 App 家长中心页脚。
  其余数据文件里的 emoji 字段会在有对应 SVG 时自动替换，缺映射时仍回退为系统 emoji。

### OCR 真实样张（Wikimedia Commons 照片）— CC BY-SA 2.0 / 3.0 / 4.0 与 CC0 1.0

- 位置：`apps/literacy-app/scripts/fixtures/ocr/real-*.png`，出处清单
  `apps/literacy-app/scripts/fixtures/ocr/real-samples.json`（含原图 URL 与 sha256）。
- 用途：拍照识字精度基准（`scripts/test-ocr-accuracy.mjs` 的 `real-photo` tier）的
  测试输入。**不进 `public/`、不打进 dist、不随两个 zip 分发**，只存在于源码仓库。
- 处理方式：由 `apps/literacy-app/scripts/gen-ocr-real-samples.mjs` 从原图裁剪、
  等比缩小、另存为 PNG，未做任何画面增强或内容改动。裁剪与缩放构成演绎作品，
  故本目录下的 `real-*.png` 按与各自原图**相同的许可证**再分发：CC BY-SA 的几张
  沿用同版本 CC BY-SA，CC0 的那张仍为 CC0（署名非义务，但照样列出来）。
- **署名（再分发本仓库源码时必须保留）**：

  | 文件 | 原图 | 作者 | 许可证 |
  |---|---|---|---|
  | `real-park-sign.png` | [爱护花草 禁止踩踏 (54210037159).jpg](https://commons.wikimedia.org/wiki/File:%E7%88%B1%E6%8A%A4%E8%8A%B1%E8%8D%89_%E7%A6%81%E6%AD%A2%E8%B8%A9%E8%B8%8F_(54210037159).jpg) | メイド理世 | [CC BY-SA 2.0](https://creativecommons.org/licenses/by-sa/2.0) |
  | `real-floor-cone.png` | [小心地滑，广东省广州市从化区创业路，2024年5月26日.jpg](https://commons.wikimedia.org/wiki/File:%E5%B0%8F%E5%BF%83%E5%9C%B0%E6%BB%91%EF%BC%8C%E5%B9%BF%E4%B8%9C%E7%9C%81%E5%B9%BF%E5%B7%9E%E5%B8%82%E4%BB%8E%E5%8C%96%E5%8C%BA%E5%88%9B%E4%B8%9A%E8%B7%AF%EF%BC%8C2024%E5%B9%B45%E6%9C%8826%E6%97%A5.jpg) | メイド理世 | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) |
  | `real-wall-stencil.png` | [小心地滑.jpeg](https://commons.wikimedia.org/wiki/File:%E5%B0%8F%E5%BF%83%E5%9C%B0%E6%BB%91.jpeg) | Richard923888 | [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0) |
  | `real-road-warning.png` | [Watch out for pedestrians! 小心行人 (6269606152).jpg](https://commons.wikimedia.org/wiki/File:Watch_out_for_pedestrians!_%E5%B0%8F%E5%BF%83%E8%A1%8C%E4%BA%BA_(6269606152).jpg) | Joybot | [CC BY-SA 2.0](https://creativecommons.org/licenses/by-sa/2.0) |
  | `real-toilet-sign.png` | [洗手间，2024年7月1日.jpg](https://commons.wikimedia.org/wiki/File:%E6%B4%97%E6%89%8B%E9%97%B4%EF%BC%8C2024%E5%B9%B47%E6%9C%881%E6%97%A5.jpg) | メイド理世 | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) |
  | `real-blackboard-press.png` | [华东师大图书馆前黑板.jpg](https://commons.wikimedia.org/wiki/File:%E5%8D%8E%E4%B8%9C%E5%B8%88%E5%A4%A7%E5%9B%BE%E4%B9%A6%E9%A6%86%E5%89%8D%E9%BB%91%E6%9D%BF.jpg) | Lt2818 | [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0) |
  | `real-road-slogan.png` | [格尔木215国道上的三语《爱护环境光荣》标语.jpg](https://commons.wikimedia.org/wiki/File:%E6%A0%BC%E5%B0%94%E6%9C%A8215%E5%9B%BD%E9%81%93%E4%B8%8A%E7%9A%84%E4%B8%89%E8%AF%AD%E3%80%8A%E7%88%B1%E6%8A%A4%E7%8E%AF%E5%A2%83%E5%85%89%E8%8D%A3%E3%80%8B%E6%A0%87%E8%AF%AD.jpg) | Liuxingy | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) |
  | `real-town-plaque.png` | [永汉镇社会治安综合治理中心，惠州市龙门县（2026年5月2日）.jpg](https://commons.wikimedia.org/wiki/File:%E6%B0%B8%E6%B1%89%E9%95%87%E7%A4%BE%E4%BC%9A%E6%B2%BB%E5%AE%89%E7%BB%BC%E5%90%88%E6%B2%BB%E7%90%86%E4%B8%AD%E5%BF%83%EF%BC%8C%E6%83%A0%E5%B7%9E%E5%B8%82%E9%BE%99%E9%97%A8%E5%8E%BF%EF%BC%882026%E5%B9%B45%E6%9C%882%E6%97%A5%EF%BC%89.jpg) | 茅野ふたば | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) |
  | `real-shop-oblique.png` | [良欣美食，惠州市龙门县（2026年5月2日）.jpg](https://commons.wikimedia.org/wiki/File:%E8%89%AF%E6%AC%A3%E7%BE%8E%E9%A3%9F%EF%BC%8C%E6%83%A0%E5%B7%9E%E5%B8%82%E9%BE%99%E9%97%A8%E5%8E%BF%EF%BC%882026%E5%B9%B45%E6%9C%882%E6%97%A5%EF%BC%89.jpg) | 茅野ふたば | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) |
  | `real-receipt-shadow.png` | [小四川世博店 23台点菜単（2025年10月4日）.jpg](https://commons.wikimedia.org/wiki/File:%E5%B0%8F%E5%9B%9B%E5%B7%9D%E4%B8%96%E5%8D%9A%E5%BA%97_23%E5%8F%B0%E7%82%B9%E8%8F%9C%E5%8D%98%EF%BC%882025%E5%B9%B410%E6%9C%884%E6%97%A5%EF%BC%89.jpg) | 茅野ふたば | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0) |

- 这张表不是写完就算：`test-ocr-accuracy.mjs` 会逐张核对清单里的出处链接与作者
  是否出现在本文件里，漏一条当场红灯。换样张时先改 `real-samples.json`，
  再跑 `npm run gen:ocr:real`，最后把新的署名补进这张表。

### Noto Sans SC 字体 — SIL OFL 1.1（仅许可证文本，未内置字体）

- 上游：[google/fonts/ofl/notosanssc](https://github.com/google/fonts/tree/main/ofl/notosanssc)
- 位置：`shared/assets/fonts/OFL-NotoSansSC.txt`（SIL Open Font License 1.1 全文）。
- 现状：两 App 均使用系统字体栈，**未内置任何字体二进制**，运行时也不请求 Google Fonts。
  若未来内置 Noto Sans SC（含子集化产物），必须把 OFL 文本随字体一起分发，
  且不得单独出售字体、不得擅用 Reserved Font Name。

## 四、本项目原创内容（非第三方，列出以厘清边界）

- `shared/assets/audio/*.wav`：正弦波合成占位音效；`shared/assets/lottie/celebration.json`：
  自制 Lottie 动画。均为本项目生成，不含外部录音或图形。
- `shared/data/common-hanzi.json`、`math-problems.json`、`idioms.json`：本项目整理的
  教学数据，声明为 CC0-1.0。
- 两 App 的课程数据（`src/data/*.js`）、音效（Web Audio 现场合成）、朗读
  （浏览器 Web Speech API）均不含第三方素材，运行时零第三方域名请求
  （唯一例外见「二、运行时回退」）。

## 五、开发 / 构建 / 测试依赖（不随产物分发）

以下工具仅在开发与 CI 中运行，其代码不会进入 dist 或 zip，列出以便审计：

| 组件 | 版本 | 许可证 | 用途 |
|---|---|---|---|
| [Vite](https://github.com/vitejs/vite) | 5.x | MIT | 构建 |
| [@vitejs/plugin-vue](https://github.com/vitejs/vite-plugin-vue) | 5.x | MIT | 构建 |
| [hanzi-writer-data](https://github.com/chanind/hanzi-writer-data) | 2.0.x | APL | 笔顺数据源（裁剪产物随包分发，见第二节） |
| [puppeteer-core](https://github.com/puppeteer/puppeteer) | 25.x | Apache-2.0 | smoke / 离线 / 验收测试 |
| [axe-core](https://github.com/dequelabs/axe-core) | 4.13.x | MPL-2.0 | 无障碍扫描 |

## 六、许可证义务速查

| 许可证 | 义务要点 | 本仓库的落实 |
|---|---|---|
| MIT | 保留版权与许可声明 | 本文件附录 A + 各包 LICENSE 保留在 node_modules / 本文件中 |
| APL | 再分发附许可证全文；标明修改 | 两处 `ARPHICPL.TXT` 随数据分发；裁剪方式在第二节与生成脚本头注释中说明 |
| CC BY-SA 4.0 | 署名；衍生同许可 | 署名文本见第三节；`LICENSE.txt` 在素材目录内 |
| CC BY-SA 2.0 / 3.0（OCR 真实样张） | 署名；衍生同许可 | 署名表见第三节「OCR 真实样张」；裁剪后的 `real-*.png` 沿用原图许可，仅存在于源码仓库 |
| OFL 1.1 | 字体随附许可证；不得单独出售 | 未内置字体；许可证文本已预置 |
| GSAP Standard | 不得用于竞争性动画工具等 | 仅作应用内动画库使用 |
| Apache-2.0（随产物分发） | 保留版权与 NOTICE；标明修改 | Tesseract.js / wasm 内核 / chi_sim 语言包均为未修改副本，声明见第一、二节；离线跟读评测包中 `sherpa-onnx-wasm-main-asr.js` 有一处修改，已在第二节逐字说明并由断言钉住 |

---

## 附录 A：MIT License 全文

以下文本适用于第一、五节中标注 MIT 的全部组件，版权行以各组件为准：

```text
MIT License

Copyright (c) <holder>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 附录 B：其余许可证全文位置

| 许可证 | 全文位置 |
|---|---|
| Arphic Public License | `apps/literacy-app/public/hanzi-data/ARPHICPL.TXT`、`shared/assets/hanzi-writer-data/ARPHICPL.TXT` |
| CC BY-SA 4.0 | `shared/assets/openmoji/LICENSE.txt`，或 <https://creativecommons.org/licenses/by-sa/4.0/legalcode> |
| SIL OFL 1.1 | `shared/assets/fonts/OFL-NotoSansSC.txt` |
| GSAP Standard License | <https://gsap.com/standard-license>（随版本变化，升级时核对） |
| Apache-2.0（Tesseract.js / wasm 内核 / chi_sim 语言包） | `node_modules/tesseract.js/LICENSE.md`、`node_modules/tesseract.js-core/LICENSE`，或 <https://www.apache.org/licenses/LICENSE-2.0> |
| Apache-2.0（sherpa-onnx 运行时 / zh-14M int8 模型 / 引擎回归音频） | <https://github.com/k2-fsa/sherpa-onnx/blob/master/LICENSE>、上游模型卡，或 <https://www.apache.org/licenses/LICENSE-2.0> |
| Apache-2.0（仅开发依赖） | <https://www.apache.org/licenses/LICENSE-2.0> |
| MPL-2.0（仅开发依赖） | <https://www.mozilla.org/MPL/2.0/> |

---

*最近核对：2026-08-26（Round 3）。核对方式：`package-lock.json` 安装版本 +
各包 LICENSE 文件 + 上游仓库许可证页。本文件是工程合规清单，不构成法律意见。*
