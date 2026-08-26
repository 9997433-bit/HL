# 识字与数学教育 App 开源资源探针

> 核查日期：2026-08-26。许可证信息来自项目仓库的 `LICENSE`/`COPYING`、GitHub
> License API 或资源官网；引入新版本时仍应再次核查。本文是工程合规清单，不是法律意见。

## 快速结论

- 推荐基础组合：Vue 3 自研业务层 + [Hanzi Writer](https://github.com/chanind/hanzi-writer)
  （MIT）+ 独立缓存的 `hanzi-writer-data`（Arphic Public License）。
- 产品设计参考优先看 `hanzi-study`、`shukong-app`、`KidsMathQuest` 和
  `Math4Kids`；它们是宽松的 MIT 许可，但复制代码时仍要保留版权与许可文本。
- GCompris、TuxMath、Inkstone 等强 copyleft 项目适合研究教学流程，不宜直接把代码并入
  计划采用宽松许可证的 Web App。
- OpenMoji 可以商用，但必须署名；修改图标形成的衍生素材须继续使用 CC BY-SA 4.0。
- LottieFiles 与 Freesound 都是“逐条素材授权”，平台免费不等于任意文件都无条件可用。
- 本探针已落库 6 个 OpenMoji SVG、3 份汉字笔画样本、3 个本地合成 WAV 和 1 个自制
  Lottie，占位阶段不依赖登录下载或来源不明的素材。

## 一、识字 / 汉字项目

| 资源 | URL | 许可证 | 可借鉴用途 | 合规与技术备注 |
|---|---|---|---|---|
| `dhjz/hanzi-study` | https://github.com/dhjz/hanzi-study | MIT | 3–6 岁闯关、听音识字、点读、书写、护眼模式、10/100 内加减法、离线单页架构 | 截至核查日 README 称含 1200+ 汉字并支持多终端进度；复制时保留 MIT。仓库内古诗、语音、图片等内容仍应按文件来源复核，不能仅凭代码许可证推定全部内容权利。 |
| `vipzhicheng/shukong-app` | https://github.com/vipzhicheng/shukong-app | MIT | 笔顺动画、教材同步、查询、生字本、复习提醒、游戏化练习、Electron/Tauri/Android 多端设计 | Vue 3 + Vite + Tailwind + Hanzi Writer。Web 端默认从 CDN 取笔顺数据；离线版要自行缓存并带上 APL。 |
| `chanind/hanzi-writer` | https://github.com/chanind/hanzi-writer | **代码 MIT** | 汉字笔画动画、描摹和笔顺测验；可直接作为识字 App 的核心渲染库 | 代码可商用并修改，但要保留版权/许可。不要把 MIT 错套到笔画数据。官网许可页：https://hanziwriter.org/license.html |
| `chanind/hanzi-writer-data` | https://github.com/chanind/hanzi-writer-data | **Arphic Public License (APL)** | 9000+ 汉字的 SVG 路径、笔画中线和匹配数据；支持离线按字加载 | 分发时必须附 `ARPHICPL.TXT`；修改字体衍生数据后要遵守 APL 的再分发、修改说明和同等权利要求。CDN 示例：`https://cdn.jsdelivr.net/npm/hanzi-writer-data@latest/我.json`。 |
| `skishore/makemeahanzi` | https://github.com/skishore/makemeahanzi | **混合许可：LGPL-3.0+ / APL** | 字典、部件分解、笔画路径、静态/动画 SVG；Hanzi Writer 的上游数据源 | `dictionary.txt`/未另行标注的分布式源码受 LGPL；`graphics.txt`、SVG 与字体衍生图形受 APL。必须按文件处理，不能给整个仓库标成 MIT。许可说明：https://github.com/skishore/makemeahanzi/blob/master/COPYING |
| `nieldlr/hanzi` (HanziJS) | https://github.com/nieldlr/hanzi | **代码 MIT；数据各自授权** | 拼音、释义、词频、拆字、词典查询 | CEDICT、Leiden 词频、Jun Da 词频等数据有独立条款；README 明确 MIT 仅覆盖软件。若只需基础教学数据，优先自建小型事实数据集。 |
| `skishore/inkstone` | https://github.com/skishore/inkstone | GPL-3.0 | 离线识读/书写 App、间隔复习、移动端交互参考 | GPL 代码若并入并分发，组合程序通常也需按 GPL 提供对应源码；建议仅研究交互。 |
| `compupro/hanzi-study-tool` | https://github.com/compupro/hanzi-study-tool | GPL-3.0 | 鼠标书写、提示后自测的轻量原型 | 项目较旧且规模小，适合流程参考，不建议作为主依赖。 |

### 推荐集成边界

1. `hanzi-writer` 作为 npm 代码依赖，第三方声明中列 MIT。
2. `hanzi-writer-data` 作为单独的数据包/静态目录，并把 `ARPHICPL.TXT` 与发行包一起提供。
3. 拼音、儿童释义、例词和分级信息采用本项目审核过的数据文件，不直接拼接来源混杂的词典。
4. 若参考 GPL 项目的交互，只复用不受版权保护的抽象方法，不复制表达性代码、文案或素材。

## 二、儿童数学游戏项目

| 资源 | URL | 许可证 | 可借鉴用途 | 合规与技术备注 |
|---|---|---|---|---|
| `shesl-tinkerland/KidsMathQuest` | https://github.com/shesl-tinkerland/KidsMathQuest | MIT | 6–12 岁加减乘除、家长端/儿童端、定制题目、徽章、SQLite/PostgreSQL | React + TypeScript；适合参考家长配置、进度和题目生成接口。 |
| `schurick1502/Math4Kids` | https://github.com/schurick1502/Math4Kids | MIT | 1–4 年级心算、生命值/奖励、多人、离线 PWA、Android | 适合参考 PWA 缓存、触屏和渐进难度。引入代码要保留 MIT 声明。 |
| `zgjff/smartmatch` | https://github.com/zgjff/smartmatch | MIT | 中国小学 1–6 年级口算、随机出题、双人同屏 | 适合核对中国学段和对战反馈；具体教学大纲准确性仍需教研复核。 |
| `action-hong/arithmetic-game` | https://github.com/action-hong/arithmetic-game | MIT | Vue + TypeScript 四则运算猜式玩法 | 小型 Vue 原型，可参考 Nerdle 式输入和结果提示。 |
| `yourlin/calc24` | https://github.com/yourlin/calc24 | MIT | Vue 3 + TypeScript 24 点、拖拽、运算符和括号、中英双语 | 适合作为高龄段逻辑挑战模块；生成题目时要保证可解。 |
| `battermann/kids-math-quiz` | https://github.com/battermann/kids-math-quiz | MIT | Elm 编写的简单儿童数学问答 | 适合研究纯函数题目生成与状态机，UI/生态较旧。 |
| TuxMath | https://github.com/tux4kids/tuxmath | GPL-3.0+（编译程序；源码和数据存在混合许可） | 彗星防御剧情、逐级加速、四则运算、因数和分数 | 可研究“答案即攻击”的节奏；若复用文件，必须逐文件看 `COPYING`。 |
| GCompris Qt | https://github.com/gcompris/GCompris-qt | 整体 AGPL-3.0；内部多为 GPL-3.0+ | 2–12 岁统一活动框架、数感/算术/度量/逻辑、难度星级、教师工具 | 因模拟电路依赖导致整体 AGPL。若部署修改版网络服务，AGPL 有对应源码提供义务；建议仅作为课程与 UX 研究样本。 |

### 值得抽取的非代码模式

- 题目模板与数值生成分离；模板记录能力标签、难度、范围和解释。
- 用可重复的题目 ID 支持进度、错题本和家长报表，而不是只存最终得分。
- 答错提供一步解释和可操作的教具提示，不使用羞辱性反馈。
- 儿童端默认大触控区域、低文字密度、无广告；家长设置置于独立入口。
- 计时与生命值应可关闭，避免把焦虑当成难度。

## 三、动画、图标、音效与字体

### LottieFiles

- 搜索入口：
  - 数字：https://lottiefiles.com/free-animations/kids-numbers
  - 儿童学习：https://lottiefiles.com/free-animations/kids-learning
  - 字母：https://lottiefiles.com/free-animations/alphabet
- 许可：https://lottiefiles.com/page/license （Lottie Simple License）。
- 可用范围：站内标为免费且适用该许可的公开动画可下载、修改、展示和商用；署名不是强制但建议。
- 关键限制：不得抓取/汇编素材以复制或开发竞争动画库；派生文件仍受相同条款约束；不能假定
  Premium 或站外嵌入素材也适用免费许可。发布前要保存**具体动画页 URL、作者、下载日期和许可快照**。
- 本探针没有复制站内单条动画；`shared/assets/lottie/celebration.json` 是本项目自制占位动画，
  消除了具体作者与许可漂移风险。

### OpenMoji

- 项目：https://github.com/hfg-gmuend/openmoji
- 素材许可：CC BY-SA 4.0；辅助代码为 LGPL-3.0。
- 用途：奖励星星、目标、书本、数字、算盘、计数水果。
- 必须署名，建议原文：
  > All emojis designed by [OpenMoji](https://openmoji.org/) – the open-source
  > emoji and icon project. License:
  > [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
- 修改 SVG 或制作明显衍生图标时，衍生素材应继续采用 CC BY-SA 4.0，并说明修改。

### Freesound

- 平台许可 FAQ：https://beta.freesound.org/help/faq/
- 平台上主要存在 CC0、CC BY、CC BY-NC 三类，**必须按每条声音页面判断**：
  - CC0：可商用，无强制署名。
  - CC BY：可商用，须列标题、作者、来源、许可证并标记修改。
  - CC BY-NC：不得用于商业/含广告/付费产品，除非另获书面许可。
- 已核查候选：
  - `Correct Answer / That's Right!`，Beetlemuse，CC0：
    https://freesound.org/people/Beetlemuse/sounds/528957/
  - `UI Button Click Snap`，el_boss，CC0：
    https://freesound.org/people/el_boss/sounds/677860/
- Freesound 原文件通常要求登录下载，因此本探针未伪造下载链接，也未把预览流当原文件抓取。
  当前 `shared/assets/audio/*.wav` 是代码生成的正弦波占位音效，不包含上述录音。

### Google Fonts 中文字体

| 字体 | URL | 许可证 | 推荐用途 | 注意事项 |
|---|---|---|---|---|
| Noto Sans SC | https://fonts.google.com/noto/specimen/Noto+Sans+SC | SIL OFL 1.1 | 正文、数字、按钮和无障碍界面 | 可嵌入和商用；字体本身不可单独出售；随字体分发时要附 OFL；修改版不得擅用 Reserved Font Name。仓库：https://github.com/google/fonts/tree/main/ofl/notosanssc |
| LXGW WenKai | https://github.com/lxgw/LxgwWenKai | SIL OFL 1.1 | 汉字卡片、故事标题、接近手写的展示文本 | 可商用和嵌入；修改衍生字体仍须 OFL，遵守名称要求，不可单独出售字体。 |

为避免把约 10–20 MB 的完整 CJK 字体塞进探针提交，当前只落库 Noto Sans SC 的
`OFL-NotoSansSC.txt`。产品构建可在锁定版本后用字体子集化工具保留实际所需字形；子集字体仍须随附
OFL，且不要只依赖 Google Fonts 在线请求，以确保儿童离线模式和隐私要求。

## 四、已落库资源

### `shared/assets/openmoji/`

| 文件 | 上游文件 | 用途 |
|---|---|---|
| `apple.svg` | `color/svg/1F34E.svg` | 数数、加减法教具 |
| `target.svg` | `color/svg/1F3AF.svg` | 关卡目标 |
| `open-book.svg` | `color/svg/1F4D6.svg` | 阅读/识字入口 |
| `numbers.svg` | `color/svg/1F522.svg` | 数学入口 |
| `abacus.svg` | `color/svg/1F9EE.svg` | 数感与算盘模块 |
| `star.svg` | `color/svg/2B50.svg` | 奖励反馈 |
| `LICENSE.txt` | OpenMoji 根目录许可 | CC BY-SA 4.0 全文 |

原始 URL 统一为
`https://raw.githubusercontent.com/hfg-gmuend/openmoji/master/<上游文件>`。

### `shared/assets/hanzi-writer-data/`

- `人.json`、`日.json`、`山.json`：从
  `https://cdn.jsdelivr.net/npm/hanzi-writer-data@latest/<字>.json` 获取的离线笔画样本。
- `ARPHICPL.TXT`：从
  `https://raw.githubusercontent.com/chanind/hanzi-writer-data/master/ARPHICPL.TXT` 获取。
- 用途：在网络断开时验证笔顺动画、描摹和数据加载流程；正式产品应锁定包版本，不能长期依赖
  `@latest`。

### 本项目生成的占位资产

- `shared/assets/audio/tap.wav`：轻触按钮反馈。
- `shared/assets/audio/success.wav`：正确答案和过关和弦。
- `shared/assets/audio/try-again.wav`：温和的重试提示。
- `shared/assets/lottie/celebration.json`：星星缩放/旋转的最小 Lottie 动画。
- 这些文件由数学波形/基础矢量形状生成，不含外部录音或图形；可随本项目自由替换。

## 五、数据文件来源与许可

- `shared/data/common-hanzi.json`：人工整理的基础汉字、拼音、儿童释义和例词，至少 50 字。
- `shared/data/math-problems.json`：本项目编写的确定性示例题，覆盖数数、比较、加减乘除、规律、
  几何和应用题。
- `shared/data/idioms.json`：常见成语的事实性拼音与原创浅释。
- 三个文件均标记 `CC0-1.0`，不从受版权保护的教材或商业题库复制；释义仅作儿童原型，发布前应由
  语文/数学教研人员校对。

## 六、上线前许可检查清单

1. 建立 `THIRD_PARTY_NOTICES`，至少包含 Hanzi Writer MIT、Hanzi Writer Data APL、
   OpenMoji CC BY-SA 和随包分发字体的 OFL。
2. 把素材的作者、原始 URL、下载日期、版本/提交 SHA、许可证和本地文件名写入机器可读清单。
3. 不使用来源页缺失、只写“free”、无 LICENSE 或声称“仅供学习”的素材。
4. 商业发行默认排除 CC BY-NC 和带有 “personal use only” 的资源。
5. 更新 npm 包、笔画数据、字体或在线素材后重新跑许可证审计；许可证可能按版本变化。
6. 儿童 App 避免在运行时向素材 CDN、Google Fonts 或分析服务泄露设备信息；优先锁版本并离线打包。
7. 用 `scripts/verify-resources.sh` 在 CI 中检查 JSON 结构、数量、重复项、SVG/WAV/Lottie 完整性和
   必需许可文件。
