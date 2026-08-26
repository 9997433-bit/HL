# 快乐识字 · literacy-app

开源儿童识字 Web 应用(3–8 岁),对标并力争超越「洪恩识字」:
单字学习 / 笔顺描红 / 听音识字 / 偏旁字源 / 分级绘本 / 成语启蒙 / 家长中心,
全部本地运行、离线可用、零跟踪、无订阅墙。

> 架构决策与竞品审计详见仓库根目录 `.agent_workspace/literacy-architecture.md`。

## 快速开始

```bash
npm install
npm run dev        # predev 会自动执行 gen:hanzi 裁剪离线笔顺数据
npm run build      # 产物在 dist/,base 为 './',可静态托管或直接打开
npm run preview
```

`npm run gen:hanzi` 从 `hanzi-writer-data`(devDependency)裁剪课程字表所需的
笔顺 JSON 到 `public/hanzi-data/`,运行时优先读本地、缺字才回退 jsDelivr CDN,
保证断网时核心字表仍能播放笔顺动画。

## 功能模块与路由

| 模块 | 路由 | 视图 |
|------|------|------|
| 学习地图(首页) | `/` | `HomeView` |
| 字库学习(单元) | `/learn` | `LearnView` |
| 单字详情·写一写(笔顺动画+描红判定) | `/learn/:char` | `CharDetailView` |
| 听音识字游戏 | `/game/listen` | `ListenGameView` |
| 偏旁部首·字源 | `/radicals` | `RadicalsView` |
| 分级绘本 | `/books` `/books/:id` | `BooksView` / `BookReadView` |
| 成语启蒙 | `/idioms` `/idioms/:id` | `IdiomsView` / `IdiomDetailView` |
| 家长中心(报表/设置/进度导入导出) | `/parent` | `ParentView` |

采用 hash 路由,打包后以 file:// 或任意子目录静态托管均可直接打开。

## 技术栈

- **Vue 3 + Vite 5 + Pinia + vue-router**(全路由懒加载)
- **HanziWriter**: 笔顺动画与手写描红判定;数据经 `scripts/gen-hanzi-data.mjs` 离线化
- **GSAP**: 学习环节转场与奖励动画
- **Web Speech API**(`src/utils/speech.js`): zh-CN 朗读,零音频资产
- **WebAudio 合成音效**(`src/utils/sfx.js`): 答题/奖励短音效,不打包音频文件
- **localStorage 版本化持久化**: 进度全本地,家长中心可导出/导入 JSON 实现多端同步

## 目录结构

```
src/
├── main.js / App.vue        # 应用壳
├── router/index.js          # hash 路由,懒加载
├── stores/                  # progress(进度/星星/每日统计) · settings(家长设置)
├── utils/                   # speech · sfx · audio · hanziWriter · hanziData · srs(FSRS-lite,R2 接入)
├── data/                    # characters / books / idioms / radicals — 全部数据驱动
├── components/              # HanziStrokeBox · ProgressRing · AppHeader · BottomNav · BreakReminder
├── views/                   # 各路由页面
└── styles/                  # base.css · theme.css(儿童向设计令牌/护眼模式)
```

## 自检与测试

```bash
npm run check:data   # 内容自检,不需要浏览器
npm run smoke        # 无头 Chrome 跑完全部路由与关键交互(需先 build)
npm test             # check:data + build + smoke
```

`check:data` 守住分级绘本最重要的那条约束——**正文只能用字表里已有的汉字**。
绘本的价值就在于孩子能从头到尾自己读下来,一句超纲的话就会让他卡住,
所以这条必须自动化。它还会校验字表字段完整性、部首示例是否都在字表内、
成语的四字拆解与情景题答案下标。

`smoke` 用无头 Chrome 依次打开 17 条路由,收集控制台报错与未捕获异常,
并检查:组件是否挂载、页面有没有漏出 `NaN`/`undefined`、
**详情页是否被重定向回列表**(内容改 id 之后最容易出现的回归)。
之后再跑 6 项交互:听音识字答题、绘本翻到读完、成语小剧场走到结尾、
家长验证与主题切换(含刷新后是否保持)、进度存档累加、笔顺 SVG 是否画出来。

`smoke` 依赖仓库根目录的 `puppeteer-core` 与系统里的 Chrome,
CI 上跑不了时可以只跑 `check:data`。

## 内容即数据

所有教学内容都在 `src/data/*.js` 中以纯数据形式维护,代码不含硬编码课程。
新增一个字/一本绘本/一条成语 = 追加一条数据,欢迎贡献。
字条目 schema(节选): `char / pinyin / unit / words[] / sentence / etymology / distractors[]`,
其中 `distractors` 为形近字,供听音识字与测验自动出题。

## 记忆曲线

Round 1 采用「掌握阈值 + 冷却复习队列」;`src/utils/srs.js` 已内置 FSRS-lite
纯函数(`createCard / schedule / dueCards / retention`)作为 Round 2 升级契约,
接线后支持按字粒度的间隔重复调度与家长端记忆强度热力图。

## License

MIT(数据集来源及其许可见架构文档 §6)。
