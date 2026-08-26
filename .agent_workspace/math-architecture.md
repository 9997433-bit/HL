# 数学应用架构设计书(Round 1)

> 项目代号:**MathQuest · 数学星球大冒险**
> 目标:超越洪恩数学的开源儿童数学 Web 应用(3-12 岁)
> 技术栈:Vue 3 + Vite + Pinia + GSAP + Canvas + Tone.js
> 状态:Round 1 架构定稿,骨架已落地于 `apps/math-app/`

---

## 1. 深度竞品分析

### 1.1 洪恩数学(主要对标)

**优势拆解:**

| 能力 | 细节 | 对我们的启示 |
|------|------|------|
| 一站式年龄覆盖 | 3-12 岁,启蒙→小学全学段 | 必须做 L1-L5 五级分层课程图谱,而非单一年龄段 |
| 内容体量 | 启蒙 200+ 课、1000+ 互动 | 用**参数化生成器**替代人工堆内容:一个生成器 = 无限题目 |
| 应用题母题 | 185 道母题覆盖小学应用题型 | 母题本质是**模板 + 参数域**,做模板引擎可低成本超越 |
| 计算专题 | 口算/竖式/速算专项训练 | 独立"计算闯关"玩法 + 错题自动归因(进位错/退位错) |
| 数独逻辑专项 | 数独 + 逻辑推理独立成线 | 4×4→9×9 渐进数独 + 唯一解保证,算法上完全可自研 |
| 剧情化演绎 | IP 角色 + 故事线包装知识点 | 设计"7 个星球 = 7 个模块"的世界观,低成本剧情框架 |
| 碎片化学习 | 单次 10-15 分钟日课 | "每日任务"系统:5 题日冒险 + 连续打卡 |

**弱点(我们的突破口):**
1. 订阅付费墙,内容不透明;
2. 原生 App,不可 Web 直达、不可定制;
3. 题库固定,刷完即止;
4. 家长报告较浅,无法导出数据;
5. 无开源生态,教师/家长无法扩展题型。

### 1.2 国际竞品

| 竞品 | 定位 | 核心机制 | 可借鉴点 | 短板 |
|------|------|----------|----------|------|
| **都都思维(Todo Math)** | 3-8 岁,哈佛教育团队,8 级 ×40 单元 | "每日冒险":每天 5 道互动题自动记录轨迹并推薄弱项;500+ 小游戏;多感官交互(拖拽/手写/旋转) | 日冒险节奏、手写数字输入、薄弱项回推 | 年费 ¥328+;仅到小学二年级 |
| **Khan Academy Kids** | 2-8 岁,完全免费,Common Core 对齐 | 自适应学习路径;逻辑思维专区(拼图/记忆配对/模式复制/迷宫);家长控制中心细粒度报告 | 自适应路径 + 免费模式即是我们"开源免费"策略的验证 | 无中文课标对齐;逻辑深度有限 |
| **Matific** | 4-15 岁,K-9 全覆盖 | 冒险岛屿地图,能力提升解锁新区域;宣称提分 34%;情景化"episode"小实验 | 地图式进度可视化、解锁驱动 | 订阅制;偏英语课标 |
| **斑马思维 / 火花思维** | 3-6 岁,AI 互动课/直播小班 | 动画情境 + 标准化课程 + 碎片化时间 | 动画情境的叙事节奏 | 依赖真人/录播,边际成本高,不可自学扩展 |

### 1.3 竞品能力矩阵与超越策略

```
              洪恩  都都  KhanKids  Matific  MathQuest(目标)
年龄跨度       ●●●   ●●    ●●        ●●●      ●●●  (3-12,L1-L5)
内容体量       ●●●   ●●●   ●●        ●●●      ●●●  (生成器→无限题)
应用题体系     ●●●   ●     ●         ●●       ●●●  (200+参数化母题模板)
数独/逻辑      ●●●   ●     ●●        ●        ●●●  (4/6/9宫+唯一解算法)
自适应难度     ●●    ●●●   ●●●       ●●●      ●●●  (掌握度模型)
免费/开源      ✗     ✗     免费闭源   ✗        ✓✓  (MIT 开源+离线)
Web直达        ✗     ✗     ✗         部分     ✓✓  (纯Web,零安装)
家长数据       ●●    ●●    ●●●       ●●●      ●●●  (可导出JSON报告)
```

**七条超越路径:**
1. **生成器 > 题库**:七大模块全部用参数化生成器,内容体量理论无限;
2. **母题模板引擎**:185 道母题 → 抽象成 ~40 类语义模板 × 参数域 × 场景皮肤,组合出 200+ 母题、无限题面;
3. **真算法数独**:挖洞法 + 唯一解校验,4×4/6×6/9×9 三档,超越固定题面;
4. **掌握度自适应**:每技能点 0-1 掌握度,错题自动归因回推,弱项优先出题;
5. **开源 + 离线 + 无墙**:MIT 协议、PWA 可离线、localStorage 本地进度、零付费;
6. **合成音效零资源**:Tone.js 程序化合成全部反馈音,无音频文件、包体极小;
7. **家长仪表盘可导出**:技能雷达图 + 学习时长 + 正确率曲线,JSON 一键导出。

---

## 2. 技术架构

### 2.1 技术选型

| 层 | 选型 | 理由 |
|----|------|------|
| 框架 | Vue 3.5 (Composition API) | 响应式适合教学状态机;与 literacy-app 同栈,共享工程规范 |
| 构建 | Vite 5 | 秒级 HMR;`base:'./'` 支持任意路径静态部署 |
| 状态 | Pinia 2 | progress / settings / session 三 store;localStorage 持久化 |
| 动画 | GSAP 3 | timeline 编排剧情动效;数字弹跳、星星飞行、卡片翻转 |
| 高频交互渲染 | 原生 Canvas 2D(自封装 Stage) | 点数、七巧板、迷宫、数独棋盘等高频重绘场景;避免引重型游戏引擎 |
| 音效 | Tone.js 15 | 程序化合成答对/答错/连击/星星音效,零音频资源 |
| 路由 | vue-router 4(hash 模式可选) | 七模块 + 首页 + 家长页 |

**渲染分工原则(关键决策):**
- **DOM + GSAP**:菜单、卡片、剧情对话、奖励动画——利于无障碍与快速迭代;
- **Canvas(自封装 `core/canvas/stage.js`)**:需要逐帧重绘/自由拖拽/几何变换的玩法(点数散点、七巧板旋转、数独手写、迷宫路径);
- 不引入 Pixi/Phaser:骨架期保持零重依赖,Round 2 若几何模块性能不足再评估 Pixi。

### 2.2 分层架构

```
┌─────────────────────────────────────────────────────┐
│  Views 层    Home / 7×ModuleView / ParentDashboard  │
├─────────────────────────────────────────────────────┤
│  Components  ModuleCard StarReward QuizShell        │
│              NumberPad DragBoard …                  │
├─────────────────────────────────────────────────────┤
│  Stores(Pinia)                                      │
│   progress: 掌握度/星星/徽章/打卡  settings: 音效/护眼│
│   session:  当前关卡运行时状态(不持久化)             │
├─────────────────────────────────────────────────────┤
│  Core 引擎层(纯 JS,无框架依赖,可单测)              │
│   engine/generator  题目生成器协议+四则/数感生成器    │
│   engine/adaptive   掌握度模型+难度调度              │
│   engine/sudoku     数独生成/求解/唯一解校验         │
│   engine/wordproblem 母题模板实例化                  │
│   canvas/stage      DPR自适应Canvas舞台+指针事件     │
│   audio/sound       Tone.js 合成音效引擎             │
├─────────────────────────────────────────────────────┤
│  Data 层(静态课程资产,JSON-like JS 模块)            │
│   curriculum  L1-L5×7模块 技能图谱                   │
│   word-problems  母题模板库                          │
└─────────────────────────────────────────────────────┘
```

### 2.3 核心数据契约

**题目协议(所有生成器统一输出):**
```js
{
  id: 'arith-add-carry-001',
  skill: 'add-2digit-carry',        // 关联技能点
  type: 'choice' | 'input' | 'drag' | 'canvas',
  prompt: { text, speech, visual },  // 题面(文字/语音文本/可视化描述)
  answer: 42,
  choices: [38, 42, 44, 52],         // choice 型才有,含认知性干扰项
  meta: { difficulty: 0.6, errorTags: ['carry'] }  // 错因标签用于归因
}
```

**技能点协议(curriculum):**
```js
{
  id: 'count-to-10', module: 'number-sense', level: 'L1',
  name: '10以内点数', deps: ['count-to-5'],   // 前置依赖构成 DAG
  generator: 'countObjects', params: { max: 10 }
}
```

**掌握度模型(adaptive):**
- 每技能 `mastery ∈ [0,1]`,答对 `m += α(1-m)`,答错 `m -= β·m`(α=0.25, β=0.35);
- 出题调度:70% 当前弱项(0.3<m<0.8)、20% 新技能(依赖已达 0.8)、10% 复习(m>0.8 按遗忘曲线抽样);
- 难度映射:题目 difficulty 取 `mastery ± 0.15` 邻域,保持"最近发展区"。

### 2.4 持久化与离线

- Round 1:Pinia + localStorage(`mathquest/progress`, `mathquest/settings`);
- Round 2:PWA(vite-plugin-pwa)+ IndexedDB 迁移(答题日志量大时);
- 数据导出:家长页一键导出 JSON(学习报告/迁移设备)。

---

## 3. 七大模块设计

世界观:**数学星球大冒险**——小狐狸船长「麦麦」驾驶飞船探索 7 颗星球,每颗星球对应一个模块;星球内是关卡链,通关点亮星座。

### M1 数字星球 · 数与量启蒙(number-sense)
- 目标:L1-L2(3-6 岁)数感建立;
- 玩法:①点数收集(Canvas 散点拖入篮子)②数字描红(Canvas 轨迹判定)③比大小(天平动画)④序数与排队 ⑤10 以内分与合(数字弹珠);
- 生成器:`countObjects / compareQuantity / numberTrace / composeTen`;
- 交互:全语音引导(Web Speech API 兜底 TTS),不识字可玩。

### M2 计算星球 · 加减乘除(arithmetic)
- 目标:L2-L5,对标洪恩"计算专题";
- 玩法:①口算流星雨(限时连击)②竖式工坊(逐位填空,进/退位高亮)③乘法口诀消消乐 ④除法分披萨;
- 生成器按技能细分:`add-within-10/20/100 · carry/no-carry · sub-borrow · mul-table · div-remainder`;
- **错因归因**:干扰项按典型错误构造(忘进位=answer-10、忘退位=answer+10),命中即打 errorTag,回推弱项训练。

### M3 图形星球 · 几何空间(geometry)
- 玩法:①形状猎人(场景找图形)②七巧板拼图(Canvas 旋转/翻转/吸附)③对称画师(镜像补全)④立体展开(L4+:正方体展开图判断)⑤周长面积实验室;
- 技术:Canvas 矩阵变换 + 多边形吸附判定(SAT/顶点距离阈值)。

### M4 逻辑星球 · 逻辑推理(logic)
- 玩法:①图案序列(ABAB/AABB/递增模式续接)②分类大师(按颜色/形状/功能多维分类)③迷宫寻宝(条件迷宫:只走偶数格)④真假侦探(L4+ 简单命题推理);
- 生成器:模式文法 `pattern-grammar`(令牌序列 + 变换规则)可产无限模式题。

### M5 数独星球 · 数独专项(sudoku)
- 三档棋盘:4×4(L2)→ 6×6(L3)→ 9×9(L4-L5),低龄档用水果/动物图标代替数字;
- **算法核心(骨架已实现)**:回溯求解器 + 解计数器;生成 = 随机完整盘(带随机化回溯)→ 挖洞 → 每挖一格验证唯一解;难度 = 空格数 × 所需技巧层级;
- 辅助:候选数笔记、冲突高亮、提示(下一个"唯一候选"格)。

### M6 故事星球 · 应用题(word-problems)
- **母题模板引擎**(超越 185 母题的核心):
  - 语义类别 ~40 类:合并/剩余/比较差/倍数/等分/包含除/两步混合/年龄/行程相遇/工程/植树/鸡兔同笼…;
  - 每类 = `模板文本(占位符) × 参数约束(保证整数解/正数解) × 场景皮肤(农场/太空/超市…)`;
  - 40 类 × 5+ 皮肤 ≈ 200+ 母题面貌,参数随机 → 无限题;
- 教学法:**CPA 三段**——先实物动画演示(Concrete)、再线段图/示意图(Pictorial)、后算式(Abstract);线段图组件是 Round 2 重点;
- 分步引导:读题(语音)→ 圈关键量 → 选运算 → 列式 → 验算。

### M7 星图中心 · 进度系统(progress)
- 学习者侧:星座图(技能 DAG 可视化点亮)、星星/徽章、连续打卡、每日冒险(5 题,对标都都);
- 家长侧:技能雷达图(7 模块)、正确率/时长曲线、错因 Top5、JSON 导出;
- 复习:掌握度 >0.8 的技能按 1/3/7/14 天间隔进入"复习抽屉"(与识字应用记忆曲线逻辑对齐)。

---

## 4. 开源资源清单

| 资源 | 协议 | 用途 |
|------|------|------|
| [Vue 3](https://github.com/vuejs/core) / [Pinia](https://github.com/vuejs/pinia) / [vue-router](https://github.com/vuejs/router) | MIT | 框架与状态 |
| [Vite](https://github.com/vitejs/vite) | MIT | 构建 |
| [GSAP](https://github.com/greensock/GSAP)(核心免费) | Standard | DOM/剧情动效 |
| [Tone.js](https://github.com/Tonejs/Tone.js) | MIT | 合成音效/节奏游戏 |
| [OpenMoji](https://openmoji.org/) | CC BY-SA 4.0 | 物品/角色贴图(点数物件、场景皮肤) |
| [Kenney Assets](https://kenney.nl/assets) | CC0 | UI 图标、卡通元素备选 |
| [Twemoji](https://github.com/jdecked/twemoji) | CC BY 4.0 | emoji 级图形兜底 |
| [ZCOOL KuaiLe / 站酷快乐体](https://www.foundertype.com/) | 免费商用 | 儿童向中文字体(Round 2 引入 subset) |
| Web Speech API(浏览器内建) | — | 中文 TTS 语音引导,零成本 |
| [vite-plugin-pwa](https://github.com/vite-pwa/vite-plugin-pwa) | MIT | Round 2 离线化 |
| [lottie-web](https://github.com/airbnb/lottie-web) + [LottieFiles 免费库](https://lottiefiles.com/) | MIT/CC | 剧情过场动画备选(评估包体后决定) |
| 参考实现:[sudoku](https://github.com/robatron/sudoku.js)(思路参考,自研实现) | MIT | 数独生成算法对照 |
| 课标参考:人教版小学数学目录 / Common Core K-5 | 公开 | 课程图谱对齐 |

**素材策略**:Round 1 全部用 emoji + CSS/Canvas 绘制(零外部资源);Round 2 按模块替换 OpenMoji/Kenney 精美素材。

---

## 5. Round 1 骨架交付

`apps/math-app/` 已创建并可运行(`npm i && npm run dev`),包含:

- 工程配置:package.json(vue/pinia/router/gsap/tone)、vite.config.js(`@`别名、`base:'./'`)、index.html(移动端 viewport);
- `src/core/`:**四大引擎骨架**——sound(Tone.js 五种反馈音,已实现)、sudoku(生成+唯一解校验,已实现)、generator(数感/四则生成器,已实现基础档)、adaptive(掌握度模型,已实现)、canvas/stage(DPR 舞台封装,已实现);
- `src/data/`:curriculum 技能图谱(L1-L5 代表性技能点)、word-problems 母题模板样例(4 类);
- `src/stores/`:progress(掌握度/星星/打卡,localStorage 持久化)、settings(音效/护眼);
- `src/views + modules/`:首页星球地图 + 7 个模块占位视图(路由已通,标注 Round 2 实现点);
- 视觉:深空主题 CSS 变量体系、护眼模式钩子。

---

## 6. 下轮攻坚重点(Round 2 任务清单)

**P0(核心玩法闭环):**
1. M2 计算星球完整玩法:口算流星雨 + 竖式工坊 + 错因归因干扰项;
2. M5 数独完整 UI:三档棋盘 Canvas 渲染、图标模式、笔记/提示/冲突高亮;
3. M6 母题模板引擎:模板 DSL 实例化器 + 线段图(Pictorial)组件 + 分步引导状态机;
4. QuizShell 通用答题壳:题目协议 → 渲染 → 判定 → 反馈动画(GSAP)→ 掌握度上报 全链路。

**P1(体验纵深):**
5. M1 Canvas 点数拖拽 + 数字描红轨迹判定;
6. M3 七巧板(旋转/翻转/吸附)——技术风险最高,先做 spike;
7. 每日冒险 + 星座图进度可视化;
8. 全局语音引导(Web Speech TTS + 队列管理)。

**P2(打磨,可留 Round 3):**
9. 家长仪表盘雷达图与导出;PWA 离线;OpenMoji 素材替换;性能(Canvas 离屏缓存)与无障碍(键盘可玩)。

**已识别风险:**
- 七巧板吸附判定精度(Round 2 先做技术 spike);
- Tone.js AudioContext 需用户手势解锁(骨架已按"首次点击初始化"处理);
- 9×9 数独生成耗时(骨架实测:9×9 生成 3ms,唯一解校验通过;无需 Worker)。

**⚠️ Round 1 并行骨架待归并(Round 2 首要清理项):**
Round 1 两个子代理并行产出了两套实现,均已入库。当前**生效入口链**为本文档描述的结构
(`main.js → router → views/HomeView + modules/*`,引擎在 `src/core/`);
另一套(`src/views/{Arithmetic,Counting,Geometry,Logic,Sudoku}View.vue`、`src/utils/{sudoku,sudoku4,sound,random}.js`、
`src/data/{modules,wordProblems,achievements,shapes}.js`、`src/components/{TopBar,StarField,MascotBot,…}.vue`、`src/composables/*`)
未被路由引用,不影响构建。Round 2 应择优合并:UI 组件(StarField/MascotBot/AchievementToast)可并入 `components/`,
玩法逻辑统一收敛到 `core/` 引擎协议,删除重复的 sudoku/sound/wordProblems 实现,`src/assets/styles/` 与 `src/styles/` 二选一。
