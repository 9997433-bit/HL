# MathQuest · 数学星球大冒险

开源儿童数学 Web 应用(3-12 岁),对标并超越洪恩数学。太空冒险主题,纯前端、
进度存在本机 localStorage,不需要账号也不上传任何数据。

**版本状态(Round 3 · SOTA 终验进行中)**:Round 2 实测基线为 QuizShell 统一答题壳、
34 个应用题母题、4×4/6×6/9×9 数独、14 类错因统计、Tone.js 移除后主包 gzip ~80KB、
离线 Service Worker。Round 3 攻坚项:家长面板(防沉迷/报表/导出)、axe serious 清零、
设计令牌迁移、题库 ≥300、Lighthouse ≥ 90 终验。
终验实测见 `.agent_workspace/GLOBAL-SUMMARY-REPORT.md`。

## 快速开始

```bash
npm install
npm run dev            # http://localhost:5174
npm run build          # 产物在 dist/,可直接静态托管
npm run preview        # 本地预览构建产物
```

## 离线使用

生产构建会生成带版本号的 Service Worker 预缓存，覆盖 `index.html`、全部 Vite 资源和所有懒加载玩法。部署到 HTTPS 静态站点（本机可用 `localhost`）并至少联网打开一次；Service Worker 安装完成后即可断网刷新或重新打开。

Service Worker 不支持 `file://`，不能通过直接双击 `dist/index.html` 安装离线缓存。可在仓库根目录运行 `npm run build && npm run test:offline`，验证关闭 HTTP 服务后仍能启动数独路由。

## 质量校验

```bash
npm run check:content  # 不开浏览器:题库与生成器跑几千次,查负数答案/重复选项/数独多解
npm run smoke          # 无头 Chrome:9 条路由 + 10 项交互,查控制台报错与渲染事故
npm test               # 上面两项 + 一次完整构建
```

`check:content` 校验的是内容正确性:每个应用题母题各生成 2000 道,确认答案是非负整数、
题干里没有 `NaN` 或没替换掉的占位符;数独 4×4 / 6×6 / 9×9 三档连出上百局,确认每局都是
唯一解且题面本身无冲突;选项生成器抽 5000 次,确认四个选项互不相同且必定包含正确答案;
穷举各玩法的技能点映射,确认产出的 id 全在技能图谱里、且每个应用题技能点都有母题能练到;
音效谱面的音名逐个解析,确认没有拼错导致某个音静默消失。

`smoke` 校验的是真实浏览器里的行为:每条路由都要能挂载、不许出现 `NaN` / `undefined`
泄漏到界面上,每个玩法连答 6 题,数独一路解到完成态,成就墙的改名/导出/清空要真的生效,
答完题刷新页面进度还得在。装货题用真实鼠标事件驱动(货物走的是 pointer 事件,
合成 `click` 测不出真实行为),另有一条用例专门确认键盘也能装货。

## 七大模块(7 颗星球)

| 星球 | 模块 | 路由 | 玩法 |
|------|------|------|------|
| 数字星球 | 数与量启蒙 | `/number-sense` | 拖拽装货点数(1-20)、数量识别、数序填空 |
| 计算星球 | 加减乘除 | `/arithmetic` | 10 以内 / 100 以内切换,选择与数字键盘两种作答方式 |
| 图形星球 | 几何空间 | `/geometry` | 平面/立体/混合三档,认名字、找同类、数边数、找生活中的形状 |
| 逻辑星球 | 逻辑推理 | `/logic` | 图形与数字找规律、旋转规律、分类推理 |
| 数独星球 | 数独专项 | `/sudoku` | 4×4/6×6/9×9 三档唯一解数独,冲突高亮、提示、数字/图案两种皮肤 |
| 故事星球 | 应用题 | `/word-problems` | 18 个生活场景母题(10 个一步 / 8 个两步),分级提示与算式讲解 |
| 星图中心 | 进度系统 | `/progress` | 成就墙、各星球掌握度、最近练习曲线、学习报告导出 |

## 架构

- `src/utils/` — 纯 JS 引擎层(无框架依赖,可在 Node 里直接单测):`sudoku`(4×4/6×6/9×9
  生成与唯一解校验)、`mastery`(掌握度模型)、`sound`(Web Audio 合成音效)、
  `random`(随机数与选项生成);
- `src/data/` — 课程技能图谱(L1-L5)、技能点映射、星球元数据、成就定义与应用题母题库;
- `src/stores/` — Pinia:`progress`(掌握度/星星/经验等级/连击/成就/打卡/错因统计,
  localStorage 持久化)、`settings`(音效/护眼/年龄档);
- `src/composables/` — `useFeedback`(GSAP 答对答错反馈、星星飞入、粒子迸发);
- `src/modules/` — 首页地图与七大模块视图,路由指向的视图全在这里;
- `src/components/` — 星空画布、顶栏、成就吐司等共享组件。

每件事只有一个入口,新增玩法时沿用即可:进度读写走 `stores/progress`,声音走
`utils/sound`,「这道题算哪个技能点」走 `data/skill-mapping`。技能 id 写错不会静默,
`recordAnswer` 会拒绝记录并在开发期打警告,`check:content` 也会拦下。

音效是用 Web Audio 的振荡器 + 增益包络现场合成的,不打包任何音频文件,也没有音频库依赖。

完整设计见 `/.agent_workspace/math-architecture.md`。

## 许可与合规

应用代码 MIT;打进产物的运行时依赖(Vue / Vue Router / Pinia / GSAP)的许可证义务
见仓库根目录 [`THIRD_PARTY_NOTICES.md`](../../THIRD_PARTY_NOTICES.md)(随发行 zip 分发)。
本 App 不含第三方素材与数据,运行时零外部域名请求。
