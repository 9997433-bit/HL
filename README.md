# 洪恩式教育双 App

对标并力争超越「洪恩识字」「洪恩数学」的两个开源儿童教育 Web 应用：

- **快乐识字**（`apps/literacy-app`）：单字学习 / 笔顺描红 / 听音识字 / 偏旁字源 /
  分级绘本 / 成语启蒙 / FSRS 复习曲线 / 家长中心。
- **MathQuest 数学星球大冒险**（`apps/math-app`）：数感 / 四则运算 / 几何 / 逻辑 /
  数独（4×4/6×6/9×9）/ 应用题 / 成就与进度系统。

两者都是纯前端 Vite 应用：零账号、零遥测、零订阅墙，学习进度只保存在浏览器本机，
支持 JSON 导出/导入。生产构建自带 Service Worker，安装一次后可完全断网使用。

## 版本状态（Round 3 · SOTA 终验进行中）

| 轮次 | 状态 | 交付要点 |
|---|---|---|
| Round 1 | ✅ 完成 | 双 App MVP、构建与打包流水线、验收标准与设计规范 |
| Round 2 | ✅ 完成 | 识字 106 字 + FSRS 接线、数学 QuizShell + 包体瘦身（主包 gzip ~80KB）、双 App 离线 SW、axe critical = 0 |
| Round 3 | 🔄 进行中 | 字库扩至 200 字、数学家长面板、axe serious 清零、设计令牌迁移、Lighthouse ≥ 90 终验、合规文档对齐 |

终验门槛与实测数据见 `.agent_workspace/sota-acceptance-criteria.md` 与
`.agent_workspace/GLOBAL-SUMMARY-REPORT.md`。

## 仓库结构

```
apps/literacy-app/    识字 App（Vue 3 + HanziWriter）
apps/math-app/        数学 App（Vue 3 + 纯 JS 引擎层）
shared/               共享设计令牌 / 数据 / 素材（含各素材许可证文本）
scripts/              构建、打包、验收、离线冒烟、资源合规脚本
.agent_workspace/     架构、验收标准、轮次简报与总结报告
THIRD_PARTY_NOTICES.md  第三方组件与素材声明（随 zip 分发）
```

## 构建与离线使用

```bash
npm install
npm run build          # 构建并打包 dist/hongen-literacy-app.zip 与 dist/hongen-math-app.zip
npm run test:offline
```

生产构建会为每个 App 生成 `dist/sw.js`，并把 `index.html`、全部 Vite 哈希资源和公开资源写入版本化预缓存。识字 App 还会预缓存完整的 `hanzi-data` 笔顺数据。

把 `apps/literacy-app/dist` 和 `apps/math-app/dist` 分别部署到 HTTPS 静态站点（本机可用 `localhost`）。首次联网访问完成 Service Worker 安装后，刷新、重新打开页面及访问懒加载路由均可断网运行。Service Worker 不支持 `file://`，因此不要直接双击 `index.html` 来启用离线缓存。

## 测试与验收

```bash
npm test                    # 两 App 各自的内容自检 + 构建 + 无头 Chrome 冒烟
npm run test:acceptance     # 构建时长 / 首屏 gzip / Lighthouse / axe 自动化门禁
npm run test:offline        # 安装 SW 后关停 HTTP 服务，验证断网冷启动
bash scripts/verify-resources.sh   # 共享资源与第三方声明合规检查
```

`npm run test:offline` 会先在线安装两个 App 的 Service Worker，再彻底关闭测试 HTTP 服务，并从新页面打开识字详情与数独路由，同时校验识字笔顺 JSON 可离线读取。运行前需先完成构建。

## 许可与合规

- 第三方依赖、笔顺数据与素材的许可证义务集中记录在
  [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)，打包脚本会把它放进两个 zip。
- 识字 App 随包分发的笔顺数据源自 `hanzi-writer-data`，受 Arphic Public License 约束，
  `apps/literacy-app/public/hanzi-data/ARPHICPL.TXT` 随数据一起分发，请勿删除。
- 运行时零第三方域名请求（唯一例外：笔顺数据本地缺字时回退 jsDelivr，课程字表不触发）。
