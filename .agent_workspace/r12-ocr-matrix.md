Model slug: claude-opus-5-thinking-high-fast
# Round 12 H2 · 拍照识字真实样张矩阵（光照 × 角度 × 纸质）

> 清单：`apps/literacy-app/scripts/fixtures/ocr/real-samples.json`（`matrix` 段是词表，`samples[].tier` 是坐标）
> 重画：`npm --prefix apps/literacy-app run gen:ocr:real`
> 跑分：`npm --prefix apps/literacy-app run test:ocr:accuracy`
> 真机：`.agent_workspace/r12-ocr-device-harness.md`
> 署名：`THIRD_PARTY_NOTICES.md` §真实样张
>
> 一句话：**「真实照片从 6 张扩到 10 张」本身不是进展**，十张白天户外的正面蓝底白字
> 标牌能把任何一条「张数 ≥ N」的线轻松顶过去，而拍照识字在家长手里断掉的地方
> 一个也没多覆盖。所以这一轮扩样的产出不是十个 PNG，是一套坐标系——
> 每张样张必须报出它占哪一格，格子不许重样，harness 逐条核。

## 1. 为什么是三根轴

R9→R11 三轮里，真实样张是按「又找到一张带汉字的照片」往里加的。加到六张的时候
问题露出来了：`real-wall-stencil` 和 `real-road-warning` 都是白天、正对、户外硬质牌面，
它们同时红或者同时绿，第二张几乎没有独立的信息量。而线下真正会让家长
重拍三次的那几种照片——柜台上的热敏纸小票、侧着拍的店招、隔着挡风玻璃的路牌——
一张都没有。

**张数是替代指标，条件覆盖才是要守的东西。** 一张样张的价值在于它引入了一种
前面九张都没有的物理条件。于是把「条件」拆成三根正交的轴：

| 轴 | 它决定了什么 | 为什么单独成轴 |
|---|---|---|
| `light` 光照 | 笔画和背景的**明暗关系**：整体压暗、局部投影、自发光、逆光 | 直接决定 `preprocess()` 的对比拉伸有没有东西可拉 |
| `angle` 角度 | 字面在成像上的**几何形变**：正对 / 仰 / 俯 / 侧斜梯形 | Tesseract 的行分割假设文字基线水平，透视是它最先崩的地方 |
| `paper` 纸质 | 承载面的**材质与反射**：漆面、搪瓷、反光膜、亚克力、热敏纸、粉笔 | 决定噪声形态——反光膜是高光斑，热敏纸是纸纹，粉笔是断笔画 |

三根轴互不蕴含：一张热敏纸小票可以是俯拍手影下的，也可以是台灯下正对的，
两者对识别的挑战完全不同。所以坐标是三元组，不是一个 tag。

## 2. 词表（`real-samples.json` 的 `matrix` 段）

词表写在清单里而不是只写在这份文档里，是为了让 harness 能核：
`samples[].tier` 里出现词表之外的值直接判红，避免「同一种光照三个人写出三个词」。

- **light**：`daylight`（户外直射日光）· `dappled`（树影斑驳）· `overcast`（阴天漫射）·
  `shade`（檐下背阴）· `indoor-lamp`（室内顶灯）· `spotlight`（射灯直打）·
  `backlit`（灯箱自发光）· `hand-shadow`（拍照的手压出一片阴影）
- **angle**：`frontal`（基本正对）· `tilt-up`（仰拍）· `tilt-down`（俯拍）·
  `oblique`（侧斜，一头被透视压扁）
- **paper**：`painted-board` · `plastic-cone` · `concrete` · `enamel-metal` ·
  `reflective-sign` · `metal-letter` · `chalkboard` · `acrylic-plaque` ·
  `lightbox-film` · `thermal-paper`

## 3. 现状：十张样张占十个格

| # | 样张 | 文字 | light | angle | paper | 召回 | 置信度 |
|---|---|---|---|---|---|---|---|
| 1 | `real-park-sign` | 爱护花草 | dappled | tilt-down | painted-board | 4/4 | 78 |
| 2 | `real-floor-cone` | 小心地滑 | indoor-lamp | tilt-up | plastic-cone | 4/4 | 86 |
| 3 | `real-wall-stencil` | 小心地滑 | daylight | frontal | concrete | **3/4** | 70 |
| 4 | `real-road-warning` | 小心行人 | daylight | frontal | enamel-metal | 4/4 | 93 |
| 5 | `real-toilet-sign` | 洗手间 | spotlight | frontal | metal-letter | 3/3 | 84 |
| 6 | `real-blackboard-press` | 中华书局 | shade | frontal | chalkboard | 4/4 | 76 |
| 7 | `real-road-slogan` | 爱护环境光荣 | overcast | tilt-up | reflective-sign | 6/6 | 94 |
| 8 | `real-town-plaque` | 社会治安 | overcast | frontal | acrylic-plaque | 4/4 | 62 |
| 9 | `real-shop-oblique` | 良欣美食 | backlit | oblique | lightbox-film | 4/4 | 92 |
| 10 | `real-receipt-shadow` | 小碗米饭 | hand-shadow | tilt-down | thermal-paper | 4/4 | 64 |

7–10 是本轮新增。合计 **40/41（98%）**；唯一的丢字是 3 号水泥墙喷漆的「滑」——
喷漆模板把三点水和「骨」连成一片，这是真实的引擎边界，留着当回归哨兵，
不去调 crop 把它「修好」。

覆盖度：**10 个互不相同的格**，light 8 种取值、angle 4 种、paper 10 种。
`test-ocr-accuracy.mjs` 的下限分别是格 ≥8、light ≥6、angle ≥4、paper ≥8，
留出的余量刚好够将来替换掉一两张（比如某张原图在 Commons 上被删）而不立刻破线。

## 4. 实测曝光与锐度（`CameraOcrView` 的三条线就是从这张表来的）

`preprocess()` 在缩放和对比拉伸的那一趟像素循环里顺手量三个数，挂在
`canvas.photoStats` 上，由 `recognizePhoto()` 透到 `result.photo`：

- `luma`：拉伸**前**的平均亮度（0–255），照片整体多暗
- `span`：拉伸前的灰度跨度（p99 − p1），画面里有没有明暗层次
- `sharpness`：拉伸**后**横向相邻像素差的 99 分位，边缘有多陡

全部二十张基准图的实测值（`scripts/fixtures/ocr` + `public/ocr/sample-photo.png`）：

| 图 | luma | span | sharp | | 图 | luma | span | sharp |
|---|---|---|---|---|---|---|---|---|
| 示例字卡 | 234 | 238 | 30 | | `real-blackboard-press` | 31 | 211 | 27 |
| `angled-card` | 208 | 217 | 13 | | `real-floor-cone` | 66 | 107 | 26 |
| `blackboard` | 48 | 206 | 36 | | `real-park-sign` | 88 | 244 | 35 |
| `blurry-note` | 231 | 140 | 13 | | `real-receipt-shadow` | 82 | 112 | 32 |
| `book-page` | 239 | 229 | 53 | | `real-road-slogan` | 114 | 158 | 37 |
| `busy-bg` | 203 | 222 | 30 | | `real-road-warning` | 154 | 205 | 21 |
| `handwriting-daily` | 244 | 192 | 23 | | `real-shop-oblique` | 87 | 151 | 20 |
| `handwriting` | 243 | 191 | 20 | | `real-toilet-sign` | 211 | 235 | 17 |
| `low-light` | 29 | 110 | 32 | | `real-town-plaque` | 102 | 222 | 30 |
| `warm-light` | 190 | 167 | 6 | | `real-wall-stencil` | 144 | 211 | 31 |

定线原则只有一条：**宁可退回兜底话术，也不要对着一张其实没问题的照片说
「你拍糊了」。** 这二十张全都认得出来，谁都不该被分支挑出毛病，所以每条线
都压在这二十张最极端那张之外：

| 常量 | 值 | 依据 |
|---|---|---|
| `DIM_LUMA` / `DIM_SPAN` | 60 / 100（**且**关系） | 只看平均亮度会冤枉黑板：`low-light` 均值 29、`real-blackboard-press` 31，但两张的 span 都在 110 以上——画面是暗的，笔画不是，而且都认得出四个字。要求同时踩中「整体压暗」和「灰度全挤在一小段里」，二十张里没有一张满足 |
| `BLUR_SHARPNESS` | 6（严格小于） | 二十张的锐度落在 6–53，最软的是 `warm-light` 的 6，其次是 `angled-card` 与 `blurry-note` 的 13。线放在 6 且取严格小于——比基准集里最软的那张还软，才敢说这是糊了 |

代价是灵敏度：一张 luma 55 / span 130 的暗照片不会被判成 `dim`，会落回兜底三条。
这是有意选的方向——误判「你拍糊了」比说一句通用话术更伤人，尤其对着一张
其实拍得挺好的照片。要往回收，先扩这张表，别先改常量。

## 5. 已知缺口

矩阵的意义之一是让缺的那一格能被指名道姓，而不是含糊成「样本还不够多」：

| 缺口 | 为什么还没有 | 归谁 |
|---|---|---|
| 夜间霓虹 / LED 点阵屏 | Commons 上找到的几张都是行书或美术字，Tesseract `chi_sim` 认不出，收进来只会把 real 档召回拖到 75% 线下，且拖下去的原因与「夜间」无关 | 真机 harness B2：QA 夜里拍一张点阵屏 |
| 布幔 / 横幅（软性载体的褶皱形变） | 同上，找到的候选不是美术字就是字太小 | 真机 harness B2 |
| 极端 oblique（>45° 透视） | 现有最斜的是 9 号，约 25–30°。再斜的公开照片里汉字都糊到人眼也费劲 | 真机 harness B2：QA 站在店招正下方斜拍 |
| 手写体真实照片 | 基准集里有两张合成手写，但没有真实场景的手写照片 | 待定，优先级低于上面三条 |

这四格都不适合用「凑一张勉强的公开照片」补——那样只会让 real 档的召回下降，
而下降的原因和缺口本身无关，反倒把信号搅浑。它们的正确去处是真机 harness：
QA 手里有相机，能在指定条件下现拍，不受 Commons 有没有这张图的限制。

## 6. 加一张样张的流程

1. **挑图。** Commons 上找 CC / CC0 的原图，确认文字里每个汉字都在
   `src/data/characters.js` 的字库里——harness 有一条
   「基准图上的「X」不在字库里」的断言，库外字直接判红。
2. **定格。** 先想清楚这张要占哪一格。如果 `tier` 和现有十张里任何一张重样，
   说明它没带来新的真实条件——换一张，别加。
3. **调 crop。** 目标是缩放后字高落在 40–100 px。太小认不出，太大浪费体积。
   `crop` 是相对原图的 `[x0, y0, x1, y1]` 归一化坐标，`width` 是输出宽度。
4. **登记。** 往 `samples[]` 里加一条，`sha256` 填**原图**的哈希（生成脚本会核，
   Commons 换图时会当场红），`license` / `author` / `page` 照实填。
5. **重画 + 回填。** `npm run gen:ocr:real` 生成 PNG，
   `npm run test:ocr:accuracy` 跑分，把这条的 `expect.recall` / `confidence`
   下限按实测值往下留一点余量填进 `BENCHMARK`。
6. **署名。** 把这张加进 `THIRD_PARTY_NOTICES.md`——harness 会逐条比对
   清单与署名文件，漏一条就红。

## 7. harness 守的是什么

`test-ocr-accuracy.mjs`（44 项）里与矩阵直接相关的四条：

| 断言 | 挡住的偷懒方式 |
|---|---|
| `real ≥ 8` 张 | 一张都不扩 |
| 来自 ≥8 张**不同原图** | 一张图裁五刀充数 |
| ≥8 个**互不相同**的 `(light, angle, paper)` 格 | 十张全是白天正面标牌 |
| 每根轴 ≥ `{light: 6, angle: 4, paper: 8}` 种取值 | 格子不同但全挤在两三种光照里 |

外加 `tier` 的值必须出自 `matrix` 词表（防同义词漂移），以及 real 档整体召回
不低于 75%（防用一堆认不出的图把格子填满）。
