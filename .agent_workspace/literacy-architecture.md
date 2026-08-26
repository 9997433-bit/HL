# 识字应用架构文档 — 「快乐识字」(literacy-app)

> Round 1 架构规划与竞品审计 · fable 架构子代理产出
> 目标: 超越「洪恩识字」的开源 Web 识字应用
> 位置: `/workspace/apps/literacy-app/` · 分支: `cursor/hongen-edu-apps-9f67`
> 注: §3/§4/§7 已与本轮实现代理(opus-fast)并行落地的代码对齐;
> 实现与原设计的偏差均为更优解(WebAudio 合成音效替代 Howler、
> 构建期裁剪离线笔顺数据),已按实际吸收进本文档。

---

## 1. 产品定位

**一句话**: 面向 3–8 岁儿童的开源、离线可用、无订阅墙的 Web 识字乐园,覆盖
「认 → 读 → 写 → 用 → 复习」全闭环,以浏览器原生能力(Web Speech / Canvas /
IndexedDB)替代洪恩的原生 App 能力,以开源数据集替代其自制内容护城河。

**北极星指标**(供后续轮次验收):
- 单字学习闭环 ≤ 90 秒/字,含 认-读-写-测 四步;
- 首屏可交互 < 2s(本地静态部署),完全离线可玩;
- 家长可在 30 秒内看懂孩子本周学习报告。

---

## 2. 深度竞品分析: 洪恩识字

### 2.1 洪恩做得好的(必须对齐的基线)

| # | 洪恩优势 | 拆解分析 | 我们的对齐方案 |
|---|---------|---------|--------------|
| 1 | **1800 常用字**,科学选字排序 | 按学前→小学低年级高频字排序,分主题单元 | 采用《通用规范汉字表》一级字 + 小学语文生字表交集,首期 300 字 × 30 单元,数据结构预留 1800+ 扩容 |
| 2 | **130 本分级绘本** | 每单元配套绘本,已学字高亮,巩固语境记忆 | 绘本 JSON 化(页/句/字三级结构),已学字自动高亮 + 点字发音;首期 10 本自编短绘本,格式开放供社区投稿 |
| 3 | **认-读-写-玩 四步闭环** | 每个字有 4–8 个互动环节,游戏化包装 | 单字学习机采用 状态机(intro→trace→listen→quiz→reward),GSAP 驱动环节转场 |
| 4 | **800+ 字源互动** | 象形字演变动画(甲骨文→楷书),建立字形意联结 | makemeahanzi 自带 etymology(象形/会意/形声分解)字段,可程序化生成字源展示,数据量反超 800 |
| 5 | **记忆曲线复习** | 艾宾浩斯遗忘曲线个性化推送复习字 | R1 用「掌握阈值(答对3次)+ 3天冷却复习队列」;R2 接线 `utils/srs.js` 的 **FSRS-lite**(对标 ts-fsrs,比洪恩的静态艾宾浩斯间隔更先进),按字粒度调度 |
| 6 | **AI 学伴/语音评测** | 跟读打分、AI 对话 | Round 1 不做;Round 2 用 Web Speech `SpeechRecognition` 做跟读比对(Chrome 可用),降级为录音回放自评 |
| 7 | **拍照识字** | 拍实物→OCR→讲解 | Round 2/3 用 Tesseract.js(chi_sim)纯前端 OCR,无需服务器 |
| 8 | **成语国学** | 50+ 成语故事、古诗 | chinese-xinhua 成语库(3 万条)取儿童高频 60 条 + 古诗数据集,量与质均可反超 |
| 9 | **动画儿歌** | 自制动画 IP(洪恩小猴) | 无法复制自制 IP;用 GSAP/CSS 程序化动画 + Web Speech 朗读替代,美术走扁平贴纸风降低资产成本 |
| 10 | **防沉迷/家长控制** | 时长限制、家长验证 | 家长门(算术题验证)+ 每日时长/单元数限制 + 护眼提醒,纯本地实现 |

### 2.2 洪恩的弱点(我们的超越点)

| # | 洪恩弱点 | 超越手段 |
|---|---------|---------|
| 1 | **订阅付费墙**(内容分级收费) | 100% 开源免费,MIT 许可,所有 1800 字规划全量开放 |
| 2 | **仅原生 App**(iOS/Android),体积 >600MB | Web 一键打开,PWA 可安装,目标构建产物 < 10MB(不含音频),按需加载笔顺数据 |
| 3 | **封闭内容**,家长无法定制 | 字库/绘本/成语全部 JSON 数据驱动,家长模式可自定义学习计划与自选字表 |
| 4 | **数据上云,隐私顾虑** | 本地优先(localStorage → IndexedDB),零跟踪零上传,导出/导入 JSON 进度实现多端同步 |
| 5 | **记忆曲线黑盒** | FSRS 开源算法 + 家长可视化: 每个字的记忆强度热力图公开可查 |
| 6 | **写字练习反馈弱**(仅描红) | HanziWriter quiz 模式做笔画级实时判定(笔顺错误即时纠正),支持"提示笔画"渐进脚手架 |
| 7 | **无护眼/无障碍设计** | 护眼模式(参考 hanzi-study 绿叶按钮)、大字号、可关音效、色弱安全配色 |
| 8 | **强设备性能要求** | 纯 SVG/CSS/GSAP 动画,低端平板 60fps;不用 WebGL 重资产 |

### 2.3 开源同类参考项目审计

| 项目 | 亮点(可借鉴) | 不足(我们要避免) |
|------|-------------|-----------------|
| [dhjz/hanzi-study](https://github.com/dhjz/hanzi-study) | 闯关制、听音识字、护眼模式、点标题10次进家长模式、1200+字、Docker 部署 | 无框架(原生JS)难维护;无记忆曲线;无绘本;美术粗糙 |
| [brianhliou/hanzi-flow](https://github.com/brianhliou/hanzi-flow) | IndexedDB 本地优先 + 自适应调度 + 离线,数据集选型专业(CC-CEDICT/Tatoeba) | 面向成人 HSK,无儿童游戏化 |
| [simonkoennecke/hanzi-trainer](https://github.com/simonkoennecke/hanzi-trainer) | hanzi-writer 手写判定 + 拼音音频索引方案 | 无课程体系 |

**结论**: 无任何开源项目同时具备「课程体系 + 游戏化 + 记忆曲线 + 绘本 + 家长模式」,
这正是本项目的差异化组合拳。

---

## 3. 技术架构设计

### 3.1 技术栈与选型理由

| 层 | 选型 | 理由 |
|----|------|------|
| 框架 | **Vue 3.5**(Composition API + `<script setup>`) | 响应式适合游戏状态机;SFC 便于按模块拆分;体积小 |
| 构建 | **Vite 5** | 秒级 HMR;`base:'./'` 支持 file:// 与任意静态托管;产物易打压缩包交付 |
| 状态 | **Pinia** | 三 store(progress/srs/settings)+ 插件式 localStorage 持久化 |
| 动画 | **GSAP 3** | timeline 编排学习环节转场、奖励粒子、字源演变;比 CSS 动画可控 |
| 笔顺 | **HanziWriter 3** | SVG 笔顺动画 + quiz 手写判定,一库两用;`scripts/gen-hanzi-data.mjs` 构建前从 hanzi-writer-data 裁剪课程字表到 `public/hanzi-data/`,运行时本地优先、CDN 兜底(`utils/hanziData.js`) |
| 路由 | **vue-router 4**(hash 模式) | 打包后 file:// 或子目录静态托管可直接打开,免服务端 rewrite;全部懒加载 |
| 语音 | **Web Speech API**(`utils/speech.js`) | zh-CN TTS 零成本零资产;R2 预留真人 mp3 音源降级位 |
| 音效 | **WebAudio 合成音效**(`utils/sfx.js`) | 程序化合成答对/答错/奖励短音,零音频资产、零请求,优于原 Howler 方案 |
| 存储 | localStorage 版本化 key(`literacy.progress.v1`)+ 家长中心导出/导入 JSON | R1 进度体量小;R2 绘本音频缓存再引 IndexedDB |
| 离线 | 笔顺数据本地化(已做)+ **vite-plugin-pwa**(R2) | Service Worker 预缓存壳与数据 |

### 3.2 分层架构

```
┌────────────────────────────────────────────────────┐
│  Views (路由页)  Home/CharLearn/Stroke/Listen/      │
│                  Books/Idiom/Progress/Parent        │
├────────────────────────────────────────────────────┤
│  Components (通用) HanziStroke·RewardStars·         │
│                    BigButton·GameShell·PinyinBadge  │
├────────────────────────────────────────────────────┤
│  Stores (Pinia)   progress(星星/解锁) ·             │
│                   srs(FSRS记忆卡) · settings(家长)  │
├────────────────────────────────────────────────────┤
│  Utils            speech(TTS) · srs(FSRS-lite) ·    │
│                   audio(音效) · storage(持久化)     │
├────────────────────────────────────────────────────┤
│  Data (静态JSON)  characters(字库) · books(绘本) ·  │
│                   idioms(成语) — 全部数据驱动       │
└────────────────────────────────────────────────────┘
```

**关键原则**:
1. **数据驱动**: 所有教学内容是 JSON,代码不含任何硬编码汉字课程;新增一课 = 加一段 JSON。
2. **游戏即状态机**: 每个学习环节是 `phase` 状态(intro→trace→listen→quiz→reward),GSAP timeline 与 phase 一一对应,便于插拔环节。
3. **本地优先**: 所有进度写 store → 自动持久化;无网络依赖(hanzi-writer-data 打包进产物或按需加载本地副本)。
4. **儿童 UI 规范**: 触控目标 ≥ 64px;全程语音引导(不依赖识字!);无文字菜单,图标+语音;横屏优先适配平板。

### 3.3 数据流(单字学习闭环)

```
data/characters.js ─▶ CharDetailView(环节状态机)
                     │ phase: intro   → speech.say(字/词/句) + 字源提示(GSAP)
                     │ phase: trace   → HanziStrokeBox(quiz模式,笔画判定)
                     │ phase: quiz    → 听音/组词测验
                     │ phase: reward  → 星星奖励 + progress.visitChar/addStars
                     ▼
        progress.recordAnswer(char, ok) → 掌握计数 + 每日统计
        (R2: 此处改调 srs.schedule(card, rating) 更新 FSRS 记忆卡)
                     ▼
        localStorage 持久化 → 首页复习队列 / ParentView 报表
```

---

## 4. 模块划分(7 大模块)

(路由为实际落地版,hash 模式)

| 模块 | 路由 | 视图 | 依赖 store/util | 数据 | 轮次 |
|------|------|------|----------------|------|------|
| ① 字库学习(单元列表+单字闭环) | `/learn` → `/learn/:char` | `LearnView` / `CharDetailView` | progress, speech | data/characters.js | **R1 核心** |
| ② 笔顺动画/写一写 | 并入 `/learn/:char` | `HanziStrokeBox` 组件(animate+quiz 双模式) | hanziWriter, hanziData | public/hanzi-data(离线裁剪) | **R1 核心** |
| ③ 听音识字游戏 | `/game/listen` | `ListenGameView` | speech, sfx, progress | characters.js(已学字池+形近干扰) | **R1 核心** |
| ④ 绘本阅读 | `/books` `/books/:id` | `BooksView` / `BookReadView` | progress(已学字高亮), speech | data/books.js | R1 基础 / R2 扩容 |
| ⑤ 成语国学 | `/idioms` `/idioms/:id` | `IdiomsView` / `IdiomDetailView` | speech, progress | data/idioms.js | R1 基础 / R2 扩容 |
| ⑤+ 偏旁字源(对标洪恩字源互动) | `/radicals` | `RadicalsView` | speech, progress | data/radicals.js | R1 基础 |
| ⑥ 进度追踪(儿童侧) | 首页星星/连续天数 + `ProgressRing` | `HomeView` | progress | — | R1 简版 |
| ⑦ 家长模式 | `/parent` | `ParentView`(家长门) | settings, progress | — | R1 基础 / R2 热力图报表 |

**模块间契约**:
- 「已学字池」= `progress.chars` 的键集,是 ③④ 出题/高亮的唯一输入,保证只考已学内容(儿童挫败感控制);
- 「复习队列」= `progress.reviewQueue`(R1: 掌握阈值+冷却;R2: 换 `srs.dueCards()`);
- 「家长设置」= `settings`(每日限时、音量、护眼、休息提醒 BreakReminder),各模块启动时读取;
- 单元解锁 = 前一单元完成 ≥60%(`progress.unlockedUnits`),首单元恒开放。

---

## 5. 数据模型(Schema;落地为 `src/data/*.js` 纯数据模块,便于 tree-shaking 与类型提示)

### 5.1 字条目(characters)
```json
{
  "id": "ren2",  "char": "人", "pinyin": "rén",
  "unit": 1, "order": 1, "strokes": 2,
  "words": [{ "w": "大人", "py": "dà rén" }, { "w": "人口", "py": "rén kǒu" }],
  "sentence": "三个人在一起。",
  "etymology": { "type": "象形", "hint": "像一个侧立行走的人", "glyphs": ["𠆢", "人"] },
  "emoji": "🧍", "distractors": ["入", "八"]
}
```
`distractors` 为形近字,供听音识字/测验出题;`etymology` 对标洪恩字源互动。

### 5.2 绘本(books)
```json
{
  "id": "book-01", "title": "小小的我", "level": 1, "requireUnit": 1,
  "pages": [{ "text": "我是一个小小的人。", "focusChars": ["我", "人", "小"], "scene": "sunrise" }]
}
```

### 5.3 记忆卡(srs, FSRS-lite)
```json
{ "charId": "ren2", "due": 1735171200000, "stability": 2.4,
  "difficulty": 5.1, "reps": 3, "lapses": 0, "lastRating": 3 }
```

### 5.4 进度(progress)
```json
{ "stars": 27, "learnedCharIds": ["ren2", "kou3"], "unitStars": { "1": 9 },
  "todayMinutes": 12, "streak": 3 }
```

---

## 6. 开源资源清单

### 6.1 核心依赖(npm)

已入 package.json:

| 包 | 用途 | License |
|----|------|---------|
| [hanzi-writer](https://github.com/chanind/hanzi-writer) | 笔顺动画 + 手写 quiz 判定 | MIT |
| [hanzi-writer-data](https://www.npmjs.com/package/hanzi-writer-data)(devDep) | 9000+ 字笔画数据(源自 makemeahanzi),构建期裁剪进产物 | 数据 ARPHIC PL / 代码 MIT |
| [gsap](https://github.com/greensock/GSAP) | 动画编排 | Standard(免费商用) |
| [pinia](https://github.com/vuejs/pinia) / vue / vue-router | 框架三件套 | MIT |

R2 候选(按需引入,当前用零依赖方案替代):

| 包 | 用途 | 现状 |
|----|------|------|
| [pinyin-pro](https://github.com/zh-lx/pinyin-pro) | 绘本自动注音/多音字 | R1 拼音随字库数据内联 |
| [howler](https://github.com/goldfire/howler.js) | 真人录音播放 | R1 用 WebAudio 合成音效 + Web Speech TTS |
| [ts-fsrs](https://github.com/open-spaced-repetition/ts-fsrs) | 完整 FSRS 调度 | R1 内置简化版 `utils/srs.js` |

### 6.2 数据集(构建期引入,不进运行时依赖)

| 资源 | 用途 | 备注 |
|------|------|------|
| [skishore/makemeahanzi](https://github.com/skishore/makemeahanzi) | `dictionary.txt` 含 decomposition/etymology/radical → 程序化生成字源互动 | 超越洪恩 800+ 字源的关键 |
| [pwxcoo/chinese-xinhua](https://github.com/pwxcoo/chinese-xinhua) | 汉字释义/成语 3.1 万条/歇后语 → 成语国学模块 | MIT |
| [jaywcjlove/table-of-general-standard-chinese-characters](https://github.com/jaywcjlove/table-of-general-standard-chinese-characters) | 《通用规范汉字表》8105 字分级 → 选字与排序依据 | MIT |
| [chinese-poetry/chinese-poetry](https://github.com/chinese-poetry/chinese-poetry) | 古诗数据 → 国学扩展(R3) | MIT |
| [davinfifield/mp3-chinese-pinyin-sound](https://github.com/davinfifield/mp3-chinese-pinyin-sound) | 拼音音节真人 MP3 → TTS 不可用时的降级音源(R2) | Public Domain |
| [parsimonhi/animCJK](https://github.com/parsimonhi/animCJK) | 备选笔顺 SVG 方案(对比 hanzi-writer) | ARPHIC PL |
| [naptha/tesseract.js](https://github.com/naptha/tesseract.js) | chi_sim OCR → 拍照识字(R2/R3) | Apache-2.0 |
| [open-spaced-repetition/ts-fsrs](https://github.com/open-spaced-repetition/ts-fsrs) | FSRS 调度参考实现;R1 先内置简化版 `utils/srs.js`,R2 可换正式库 | MIT |
| [OpenMoji](https://openmoji.org/) | 词卡配图 emoji 资产 | CC BY-SA 4.0 |

### 6.3 参考项目(仅借鉴设计,不引代码)

- [dhjz/hanzi-study](https://github.com/dhjz/hanzi-study) — 闯关流程、家长门交互(点标题10次)、护眼模式;
- [brianhliou/hanzi-flow](https://github.com/brianhliou/hanzi-flow) — IndexedDB 本地优先 + SRS 工程化;
- [simonkoennecke/hanzi-trainer](https://github.com/simonkoennecke/hanzi-trainer) — 手写判定与音频索引组织。

---

## 7. 目录结构(已落地骨架)

```
apps/literacy-app/
├── package.json            # vue3+pinia+router+gsap+hanzi-writer(+data devDep)
├── vite.config.js          # base './'、@ 别名、host:true
├── index.html              # zh-CN、儿童主题色、viewport 锁缩放
├── README.md               # 运行/构建/模块表/数据格式
├── scripts/
│   └── gen-hanzi-data.mjs  # predev/prebuild: 裁剪课程字表笔顺数据 → public/hanzi-data/
└── src/
    ├── main.js  App.vue    # 全局壳
    ├── router/index.js     # hash 路由,10 路由全懒加载,afterEach 写标题
    ├── stores/
    │   ├── progress.js     # 字/绘本/成语/游戏/每日统计/星星/连续天数/单元解锁,localStorage v1,导出导入 JSON
    │   └── settings.js     # 家长设置/护眼/音量(persist)
    ├── utils/
    │   ├── speech.js       # Web Speech TTS 封装
    │   ├── sfx.js          # WebAudio 合成音效(零资产)
    │   ├── audio.js        # 音频总开关/协调
    │   ├── hanziWriter.js  # HanziWriter 实例封装
    │   ├── hanziData.js    # 笔顺数据本地优先加载,CDN 兜底
    │   └── srs.js          # FSRS-lite 纯函数(createCard/schedule/dueCards/retention),R2 接入点
    ├── data/
    │   ├── characters.js   # 字库: 单元×字(拼音/组词/例句/字源提示/形近干扰项)
    │   ├── books.js  idioms.js  radicals.js
    ├── components/
    │   ├── HanziStrokeBox.vue  # 笔顺动画+描红判定
    │   ├── ProgressRing.vue  AppHeader.vue  BottomNav.vue  BreakReminder.vue
    ├── views/ (10 视图,详见 §4)
    └── styles/  base.css  theme.css   # 设计令牌: 暖色主题/大触控目标/护眼变量
```

---

## 8. 三轮路线图

| 轮次 | 交付 |
|------|------|
| **R1(本轮)** | 架构文档 + 骨架(package.json/vite/路由/stores/utils/数据模块/README)+ FSRS-lite 契约;opus-fast 子代理并行实现 ①②③ 核心玩法与各视图 |
| **R2(靶向攻坚)** | 见下节 |
| **R3(SOTA 打磨)** | 全量 300+ 字数据、绘本 10 本、音效资产、PWA 离线、性能预算达标、双应用打包 |

### Round 2 攻坚重点(按优先级)

1. **字库数据流水线**: 写脚本从 makemeahanzi + 通用规范汉字表 + chinese-xinhua 自动生成 `characters.json`(300 字,含字源/组词/形近干扰项)——内容量是超越洪恩观感的第一要素;
2. **单字学习状态机打磨**: 五环节 GSAP 转场、连击奖励、错误宽容(3 次提示后自动示范);
3. **听音识字游戏化**: 从"三选一"升级为"钓鱼/打地鼠"皮肤,同一逻辑换皮复用;
4. **绘本阅读器**: 逐句朗读高亮 + 点字查发音 + 读完自动归入复习池;
5. **家长仪表盘**: 记忆强度热力图(字 × FSRS stability)、周报、自定义字表;
6. **音频降级链**: Web Speech 不可用(iOS Safari 静音策略)→ pinyin mp3 拼读 → 静音字幕模式;
7. **测试**: gpt-sol 子代理补 Vitest 单测(srs.js 调度正确性、storage 迁移)+ Playwright 冒烟。

### 风险与对策

| 风险 | 对策 |
|------|------|
| Web Speech 在 iOS 需用户手势触发/音色差 | 首页"开始"大按钮即首次手势;R2 引入 mp3 音源 |
| hanzi-writer-data 全量 ~20MB | 按需 fetch 单字 JSON(`hanzi-writer-data/人.json` 动态导入),或构建期只打包课程内 300 字 |
| 儿童误触退出学习 | 全屏 API + 路由守卫确认(家长门) |
| 并行子代理改动冲突 | 本轮骨架文件保持 stub 粒度,实现代理以模块为界各自负责 |
