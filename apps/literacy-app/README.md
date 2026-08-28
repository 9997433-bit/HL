# 快乐识字 · literacy-app

开源儿童识字 Web 应用(3–8 岁),对标并力争超越「洪恩识字」:
单字学习 / 笔顺描红 / 听音识字 / 偏旁字源 / 分级绘本 / 成语启蒙 / 家长中心,
全部本地运行、离线可用、零跟踪、无订阅墙。

> 架构决策与竞品审计详见仓库根目录 `.agent_workspace/literacy-architecture.md`。

**版本状态（Round 5 进行中）**：Round 3 交付 200 字 / 16 单元、axe serious 清零、
描红键盘替代与 aria-live 播报、设计令牌迁移。Round 4 把字库扩到 500 字 / 33 单元，
课文按单元切包懒加载，并在家长中心加了学习计划（每日新字上限 + 单元选择）。
Round 5 把字库扩到 1000 字 / 58 单元，并把整份字表改成脚本生成：
`scripts/data/char-seed.txt` 是唯一真源，`npm run gen:corpus` 产出
`src/data/char-index.js`、`src/data/unit-index.js`、`src/data/chars/` 和
`shared/data/common-hanzi.json`。Round 6 按《通用规范汉字表》一级字表的字序
续到 1820 字 / 99 单元，单元名录也一并由 seed 生成。
终验实测见 `.agent_workspace/GLOBAL-SUMMARY-REPORT.md`。

## 快速开始

```bash
npm install
npm run dev        # predev 会自动执行 gen:hanzi 裁剪离线笔顺数据
npm run build      # 产物在 dist/,base 为 './',可部署到任意子目录
npm run preview
```

`npm run gen:hanzi` 从 `hanzi-writer-data`(devDependency)裁剪课程字表所需的
笔顺 JSON 到 `public/hanzi-data/`,运行时优先读本地、缺字才回退 jsDelivr CDN,
保证断网时核心字表仍能播放笔顺动画。笔顺数据受 Arphic Public License 约束,
生成脚本会把 `ARPHICPL.TXT` 一并写入该目录随包分发,不要删除。

`npm run gen:ocr` 把拍照识字要用的 Tesseract.js worker 与 wasm 内核从 `node_modules`
复制到 `public/ocr/`（`prebuild` / `predev` 会自动跑）。这两个文件是生成物、不入库；
同目录下入库的只有 chi_sim 语言包 `chi_sim.traineddata.gz` 和示例照片
`sample-photo.png`（改图跑 `node scripts/gen-ocr-sample.mjs` 重画）。

## 离线使用

生产构建会生成带版本号的 Service Worker 预缓存，覆盖 `index.html`、所有 Vite 资源、懒加载路由和完整 `hanzi-data` 目录。部署到 HTTPS 静态站点（本机可用 `localhost`）并至少联网打开一次；Service Worker 安装完成后即可断网刷新或重新打开。

唯一不进预缓存的是拍照识字的引擎包（`public/ocr/` 下的 worker、wasm 内核、语言包，
合计约 5.5 MB）：多数访客不会打开这一页，没必要让所有人一进门就下载它。
`sw.js` 改成第一次真的去认字时才下载，下完写进 `literacy-app-ocr-pack` 缓存，
之后断网照样能认字。这个缓存不带版本号，换版本时不会被 `activate` 清掉。

`npm run test:offline` 会把这条链路整个跑一遍：联网时认一次示例照片、确认引擎包
落进了按需缓存而不是预缓存，然后关掉 HTTP 服务，断网再认一次，必须照样认得出。

Service Worker 不支持 `file://`，不能通过直接双击 `dist/index.html` 安装离线缓存。可在仓库根目录运行 `npm run build && npm run test:offline`，验证关闭 HTTP 服务后仍能启动详情页并读取笔顺数据。

## 拍照识字

`/ocr`。孩子在书上、路牌上、包装袋上遇到不认识的字，拍下来当场认，认出来的字
直接接上字库讲解（拼音、释义、组词），点一下就进单字页看笔顺、听读音。

- **取图三条路**：拍一张（`capture="environment"` 直接调后置摄像头）、相册选一张、
  试一张示例。都落到同一个 `<input type="file">`，比 `getUserMedia` 少一层权限弹窗，
  Android WebView 与桌面浏览器表现一致；没有摄像头也能完整走一遍流程。
- **识别**：`src/utils/ocr.js`。先把照片缩到长边 1280 px、转灰度、把实际用到的
  灰阶拉满 0–255（家里随手拍的书页通常偏黄且明暗不匀），再交给 Tesseract 的
  chi_sim LSTM 模型。
- **只讲字库里的字**：识别文本先过 `extractHanzi()` 去掉标点、拼音和噪声并去重，
  再按 `CHARACTER_MAP` 分成「讲得了」和「还没进字库」两堆，后者如实列出来，
  不硬编一段释义糊弄孩子。这两段是纯函数，`npm run test:ocr` 在 Node 里守住。
- **隐私**：识别全程在本机 wasm 里跑，照片不上传、不落盘。

`src/composables/useOcr.js` 把流水线包成 `idle → loading → reading → done/error`
的状态机，并把 Tesseract 的英文进度（`loading language traineddata` 之类）
翻成一句中文，界面上的文字和 `aria-live` 播报用的是同一句。

wasm 内核只带 SIMD + LSTM 这一个变体：SIMD 从 Chrome 91 / Firefox 89 / Safari 16.4
起就是标配，每多带一个变体就多 3.9 MB。更老的浏览器会在装引擎时失败，
界面会明说「浏览器太旧」，其余功能不受影响。

## 字表与复习曲线

字表 1820 字 / 99 单元,分两层存放,规模由 `check:data` 与 `gen:hanzi` 双重守护:

- `src/data/char-index.js` —— 每个字的拼音 / 声调 / 单元 / 部首 / 笔画 / 图标。
  首页地图、字表卡片、复习队列、家长报表都只用这一层,它随主包加载。
- `src/data/chars/uN.js` —— 每个单元的释义 / 组词 / 例句。
  由 `src/data/characters.js` 里的 `loadUnitDetails()` / `loadCharacter()` 用
  `import()` 按需拉取,Vite 的 `manualChunks` 把它们切成 `chars-uN` 独立块,
  翻到哪个单元才下载哪一包。`npm run check:bundle` 会在 dist 上核对
  「首屏没有同步加载课文包」,防止有人一行 import 把上千个字的课文塞回主包。
- `src/data/unit-index.js` —— 单元名录和每个单元详情包的 `import()` 加载器,
  同样由 seed 生成,新增单元不必再手工登记到 `characters.js`。

字表页一次只挂一个单元,底部按单元翻页,避免上百张卡片同时进 DOM。

### 字表怎么改

两层字表和共享基线都是生成物,不要手改,改 `scripts/data/char-seed.txt` 再重新生成:

```bash
npm run gen:corpus     # 只读缓存,不需要额外依赖
```

seed 每行一个字,字段是 `汉字|拼音|部首 id|图标|释义|组词|例句`
(老单元只写前四段,课文仍是手写稿)。声调、笔画、部首和组词例句的拼音一律派生,
不手写:笔画数 `hanzi-writer-data` 的笔顺条数,部首走 cnchar,拼音走 pinyin-pro,
派生结果落在 `scripts/data/derived-cache.json`,所以平时生成不依赖这两个工具包。
seed 里换了字或改了词句之后要重新派生:

```bash
npm i --no-save pinyin-pro cnchar cnchar-radical
npm run gen:corpus -- --refresh
```

多音字是这里最容易出错的地方:标注器按词典挑读音,挑的和字表登记的不一致时,
生成器以字表为准就地改回来,并把每一处改动打印出来让人复核。

## 形近字库与选择题干扰项

听音识字和单字页「练一练 / 说一说」的错误选项不是随机抽的,而是取形近字:
四个选项长得都差不多,孩子才必须真的听清读音、记住字形,而不是靠轮廓排除。

`src/data/similar-chars.js` 是生成物,由 `npm run gen:similar` 从离线笔顺数据
(`hanzi-writer-data` 的 medians 骨架)算出来,不联网、不查表:

1. 把每一笔的中线密集采样进 12 × 12 的占格图 —— 「墨在哪儿」越像,看上去越像;
2. 每一小段的方向按 8 个方位做长度加权直方图 —— 占格图分不出「人 / 八」,笔向能;
3. 笔画差超过 3 笔的直接排除,同部首加一点分;
4. 再压一份人工形近清单(己已巳、未末、土士、乌鸟…)兜底,算法漏了也不至于丢。

运行时的取值顺序在 `src/utils/distractors.js`:
形近字库 → 同部首且笔画接近 → 笔画接近 → 候选池兜底。
最像的那个固定出现,其余洗牌,重复出题不会四个选项一模一样。
`check:data` 守着「库里没有字表之外的字」和「≥95% 的字有形近字」。

## 字源语料

`src/data/etymology.js` 只放**手写**的那一批 —— 有小图的象形 / 指事字,和故事
各不相同的会意字。形声字的讲法是同构的(形旁管意思 + 声旁管读音),一个一个抄
没有意义,所以走生成:

```bash
npm run gen:etymology
```

种子 `scripts/data/etymology-seed.txt` 里每个形声字只写两样东西 —— 声旁是谁、
声旁本来念什么。形旁取自字表索引的部首,形旁的讲法查生成器里的 `SEMANTIC` 表,
字义取自单元详情包,读音取自字表拼音并和声旁比对,决定要不要写「A → B」。
产物是 `src/data/etymology-derived.js` 和 `src/data/etymology-index.js`,都不要手改。

种子只收「声旁本身也是个能给孩子看的字」的形声字:声旁要是个谁也不认识的偏旁
(㐬、𢦏、巠…),拆开讲反而添乱,这种字宁可不收;形旁的意思和字义对不上的
(带反犬旁却不是动物的「狡」「猜」)同样不收 —— 讲错了比不讲更糟。
`check:data` 会核对派生条目的形旁和字表部首一致、讲解里写的读音和字表一致。

## 学习计划

家长中心的「学习计划」写进 `settings.dailyNewLimit`(每天最多学几个新字,0 = 不限)
与 `settings.planUnits`(这一阶段只学哪几个单元,空 = 按课程顺序学全部)。
计划只影响「今天推荐学什么」:首页的「继续学」按钮、字表的随机字都先在计划单元里挑,
首页和字表会显示今天还剩几个新字。它不锁已学过的字,也不拦到期复习——
复习排期由 FSRS 记忆卡说了算。

复习不看「答对几次」,而是由 `src/utils/srs.js` 的 FSRS-lite 记忆卡决定:
描红和答题都会更新记忆卡的稳定性与难度,首页的「该复习 N 字」、
字表的「要复习」筛选、听音识字的出题偏好都取自同一个到期队列;
家长中心的记忆强度热力图按每个字此刻的保持率着色,点格子直接去复习。
老存档没有记忆卡时,会按已有掌握度反推一张初始卡,升级不清零进度。

## 单字学习闭环与徽章

单字详情页(`CharDetailView`)是一台五步状态机:
**玩一玩 → 认一认 → 练一练 → 写一写 → 说一说**。

第一步不是讲字,是先陪这个字玩一小会儿(`CharPlayStage`,玩法数据来自
`getCharPlay(char)`):孩子先对这个字有印象,后面的认写练才挂得住。
「认一认」这一步,有字源语料的字会**直接把演变动画摆在正中间自动播**,
不再藏在一个「看看它的来历」按钮后面——认字本来就该看着字怎么来的学;
没有语料的字退回看字形、听读音。「说一说」把原来单开一屏的「领奖励」并了进来,
答完题星星就在原地开出来。

每一步做完自动衔接下一步——衔接不是立刻跳走:先在面板上挂出「马上进入『练一练』…」
并同时写进 `aria-live` 播报,期间随时可以按「等一下」停下(WCAG §2.2.1)。
顶部步骤条也可以手动跳,但只能往回看或往前一步,而且**跳过去不等于做过**:
只有认、练、写、说四步都真的做完,才会调 `progress.completeCharFlow()` 给这一轮记账,
所以「五步全通」徽章刷不出来。「玩」是暖场,不记账也不拦路,随时可以「先不玩了」。
田字格、组词、例句和底部操作在所有步骤都留在原地,
孩子想临时写一笔、听个词不必先退出当前步骤。

描红时**同一笔连错 3 次会自动示范那一笔**:`HanziStrokeBox` 自己按笔序记错误次数,
够 3 次就调 HanziWriter 的 `animateStroke()` 慢放这一笔。`animateStroke()` 会顺手取消
当前测验,所以示范完再用 `quizStartStrokeNum` 从同一笔把测验接回来;
错误总数、已辅助笔数这些账记在组件里,重启测验不会被清零。

徽章体系 v1 的 10 枚徽章定义在 `src/data/badges.js`,规则统一是「某个指标攒够阈值」:
识字量 1 / 10 / 50、掌握 5 字、描红 10 遍、五步闭环 3 次、听音连对 5 题、
连续 3 天、读完 3 本绘本、看懂 3 个成语。store 里 `badgeStats` 一变就自动对表解锁,
老存档读档时静默补发(不发星星也不弹庆祝)。`BadgeShelf` 负责展示:
首页摆已点亮的加最接近的三枚,家长中心摆整面墙。徽章不做隐藏成就——
没拿到的也显示条件和「还差多少」的进度条,才能当成下一个小目标。

## 无障碍

设计令牌统一来自仓库根目录的 `shared/styles/design-tokens.css`（由 `src/styles/base.css`
第一行引入），`src/styles/theme.css` 只留识字 App 自己的 `--art-tint`。三套主题
（sunny / care / night）的正文与三级灰都按各自最亮的底色算过对比度，全部 ≥ 4.5:1。

两处只靠颜色和动画表达的环节补了读屏通道：

- **答题与庆祝**：听音识字每一关的关卡号、对错、正确答案、结算星数，以及庆祝浮层的
  标题/星数/「可以跳过」，都写进常驻的 `aria-live="polite"` 区域；视觉上的短提示
  标了 `aria-hidden`，避免读屏念两遍。
- **描红**：描红本身要在田字格里拖拽，键盘和开关设备做不到。进入描红后田字格可聚焦，
  按空格 / 回车 / → 或点「写下一笔」由程序补一笔，写满全部笔画同样算完成、照常升级
  掌握度；按 Esc 或点「跳过描红」随时退出。同一笔连错 3 次自动示范这件事也写在田字格的
  `aria-label` 里，示范开始与结束都经由 `hz__hint` 播报，示范期间「写下一笔」会禁用，
  免得孩子在示范中途把这一笔跳掉。

`node scripts/axe-states.mjs`（仓库根目录，也可 `npm run test:a11y`）会用三套主题
把每条路由和「描红练习中 / 答题反馈 / 庆祝浮层」这三个交互态各扫一遍，
critical 与 serious 都必须为 0；`npm run test:acceptance` 已经接上这一步。

## 功能模块与路由

| 模块 | 路由 | 视图 |
|------|------|------|
| 学习地图(首页) | `/` | `HomeView` |
| 字库学习(单元) | `/learn` | `LearnView` |
| 单字详情·五步闭环(玩→认→练→写→说) | `/learn/:char` | `CharDetailView` |
| 听音识字游戏 | `/game/listen` | `ListenGameView` |
| 拍照识字(本地 OCR) | `/ocr`(`/camera` 重定向) | `CameraOcrView` |
| 偏旁部首·字源 | `/radicals` | `RadicalsView` |
| 字源馆(525 字的演变动画) | `/etymology/:char?` | `EtymologyView` |
| 分级绘本 | `/books` `/books/:id` | `BooksView` / `BookReadView` |
| 成语启蒙 | `/idioms` `/idioms/:id` | `IdiomsView` / `IdiomDetailView` |
| 家长中心(报表/设置/进度导入导出) | `/parent` | `ParentView` |

采用 hash 路由,打包后可在任意子目录静态托管；离线缓存要求 HTTPS 或 `localhost`。

## 技术栈

- **Vue 3 + Vite 5 + Pinia + vue-router**(全路由懒加载)
- **HanziWriter**: 笔顺动画与手写描红判定;数据经 `scripts/gen-hanzi-data.mjs` 离线化
- **GSAP**: 学习环节转场与奖励动画
- **Tesseract.js**(`src/utils/ocr.js`): 拍照识字的本地 OCR,worker / wasm 内核 / chi_sim
  语言包全部同源托管,照片不出设备;引擎近 6 MB,只有真的开始认字才 `import()`
- **Web Speech API**(`src/utils/speech.js`): zh-CN 朗读,零音频资产
- **WebAudio 合成音效**(`src/utils/sfx.js`): 答题/奖励短音效,不打包音频文件
- **localStorage 版本化持久化**: 进度全本地,家长中心可导出/导入 JSON 实现多端同步

## 目录结构

```
src/
├── main.js / App.vue        # 应用壳
├── router/index.js          # hash 路由,懒加载
├── stores/                  # progress(进度/星星/每日统计) · settings(家长设置)
├── utils/                   # speech · sfx · audio · hanziWriter · hanziData · srs(FSRS-lite,已接入复习队列)
├── data/                    # characters / books / idioms / radicals / badges — 全部数据驱动
├── components/              # HanziStrokeBox · BadgeShelf · ProgressRing · AppHeader · BottomNav · BreakReminder
├── views/                   # 各路由页面
└── styles/                  # base.css(引入共享设计令牌+通用组件类) · theme.css(仅识字独有的 --art-tint)
```

## 自检与测试

```bash
npm run test:srs     # FSRS 调度纯函数单测
npm run test:speech  # 跟读评测判分纯函数单测
npm run test:ocr     # 拍照识字的取字与字库匹配规则单测
npm run check:data   # 内容自检,不需要浏览器
npm run smoke        # 无头 Chrome 跑完全部路由与关键交互(需先 build)
npm test             # test:srs + test:speech + test:ocr + check:data + build + check:bundle + smoke
```

`check:data` 守住分级绘本最重要的那条约束——**正文只能用字表里已有的汉字**。
绘本的价值就在于孩子能从头到尾自己读下来,一句超纲的话就会让他卡住,
所以这条必须自动化。它还会校验字表规模(≥100 字)与字段完整性(声调/图标/组词拼音)、
每个单元至少 5 个字、部首示例是否都在字表内、成语的四字拆解与情景题答案下标。

`gen:hanzi` 把课程字表和顺带收录的字(部首示例、成语、绘本正文)分开处理:
课程字缺笔顺数据会让构建直接失败,其余缺字只警告。

`smoke` 用无头 Chrome 依次打开 17 条路由,收集控制台报错与未捕获异常,
并检查:组件是否挂载、页面有没有漏出 `NaN`/`undefined`、
**详情页是否被重定向回列表**(内容改 id 之后最容易出现的回归)。
之后再跑一组交互:听音识字答题、绘本翻到读完、成语小剧场走到结尾、
家长验证与主题切换(含刷新后是否保持)、进度存档累加、笔顺 SVG 是否画出来,
以及三条无障碍硬断言——只用键盘写完「日」并记进「会写了」、Esc 能跳过描红、
答题与庆祝都有 aria-live 播报、共享设计令牌确实生效。

Round 4 又加了三项闭环断言:五步状态机自动从「玩一玩」走到「说一说」并记下闭环次数、
在田字格里横着乱划三次会触发这一笔的自动示范且示范后能接着写完、
学会第一个字就点亮「启蒙芽」且首页与家长中心都看得见。

Round 7 加的拍照识字断言走的是真 wasm:进 `/ocr` 时不许有任何引擎请求,
点「试一张示例」之后要认出示例图上「日月山水」里的至少三个字、
每张结果卡都配上字库讲解、播报里说清认出几个字、
worker 与语言包都确实下载过,最后还要能从结果卡点进单字页。

`smoke` 依赖仓库根目录的 `puppeteer-core` 与系统里的 Chrome,
CI 上跑不了时可以只跑 `check:data`。

## 内容即数据

所有教学内容都在 `src/data/*.js` 中以纯数据形式维护,代码不含硬编码课程。
新增一个字/一本绘本/一条成语 = 追加一条数据,欢迎贡献。
字条目 schema(节选): `char / pinyin / unit / words[] / sentence / etymology / distractors[]`,
其中 `distractors` 为形近字,供听音识字与测验自动出题。

## 许可与合规

- 应用代码:MIT。
- 依赖与数据的完整第三方声明见仓库根目录
  [`THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md)(随发行 zip 分发)。
- 特别注意:`hanzi-writer` 代码是 MIT,但 `public/hanzi-data/` 里的笔顺数据源自
  `hanzi-writer-data`,受 **Arphic Public License** 约束——再分发必须随附同目录的
  `ARPHICPL.TXT`,两者不可混淆。
