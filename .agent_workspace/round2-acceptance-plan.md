# Round 2 验收计划 — 7 步验收流程与自动化绑定

> 版本：Round 2 v1.0（2026-08-26）
> 依据：`sota-acceptance-criteria.md`（§0 轮次门槛：Round 2 须通过**全部功能 P0 + 性能 P0**）、
> `ROUND1-BRIEF.md`（遗留缺陷 1–8）、`design-tokens-migration.md`（令牌迁移分相）
> 留档：结果一律写入 `.agent_workspace/acceptance-log-round2.md`（模板见 §9）
> 环境基准：`npm run build:all` 产物 zip 解压 → 静态服务器（`npx serve`）；性能项
> Chrome DevTools 4× CPU 节流。

---

## 0. 门禁总则

- 7 步**顺序执行、逐步阻断**：任何一步 P0 判据失败即停止出包，修复后从该步重跑。
- 每步分「自动化绑定」（脚本命令，退出码即结论）与「人工走查」（10 分钟内可完成的补充项）。
- 自动化脚本现状标注：✅ 已存在可直接绑定；🔧 本轮由「验收自动化」子代理落成。
- 汇总入口（🔧 建议加入根 `package.json`）：

```json
{
  "scripts": {
    "check:tokens": "bash scripts/check-tokens.sh",
    "test:a11y": "node scripts/a11y-scan.mjs",
    "test:offline": "node scripts/offline-check.mjs",
    "accept:round2": "bash scripts/accept-round2.sh"
  }
}
```

  `accept-round2.sh` 按本计划第 1–7 步顺序串联，任一步非零退出即中止并打印失败步骤号。

---

## 第 1 步 环境与资源完整性

| 项 | 内容 |
|---|---|
| 目的 | 排除环境噪音；确认开源资产与许可合规（C-2） |
| 自动化 | ✅ `bash scripts/setup.sh` → ✅ `bash scripts/verify-resources.sh` |
| 通过判据 | verify-resources PASS（≥100 汉字、85 数学题、42 成语、许可声明齐全，对齐 test-baseline.md） |
| 人工走查 | 无 |
| 产出 | 日志 §1：Node/npm 版本、资源计数 |

## 第 2 步 数据与内容正确性

| 项 | 内容 |
|---|---|
| 目的 | 判分正确性与内容规模达标（L-F1 Round2 ≥ 100 字、M-F1 七类玩法；判分不靠 E2E 假阳性，对应遗留缺陷 8） |
| 自动化 | ✅ `npm --prefix apps/literacy-app run check:data`、✅ `run test:srs`（FSRS 单测，验证遗留缺陷 4 的接线正确性）、✅ `npm --prefix apps/math-app run check:content` |
| 通过判据 | 三脚本零退出；check:data 报告字库 ≥ 100 且每字含拼音/释义/例词/笔顺；check:content 覆盖 7 模块题型与答案自洽 |
| 人工走查 | 抽 5 字/5 题人工核对读音与答案 |
| 产出 | 日志 §2：字库计数、题型覆盖表、FSRS 用例数 |

## 第 3 步 构建、包体与打包门禁

| 项 | 内容 |
|---|---|
| 目的 | C-3 出包门禁 + L-P4 包体预算；盯住遗留缺陷 3（Tone.js 431KB） |
| 自动化 | ✅ `npm test`（两 App check + build + smoke 串联）→ ✅ `npm run build:all`（产 zip + 完整性校验）→ 🔧 包体断言：`gzip -c apps/*/dist/assets/*.js \| wc -c` 聚合首屏入口 chunk |
| 通过判据 | 全部零退出；两 zip 非空且解压含 index.html；**首屏 JS gzip < 250KB**（math 当前 gzip 138KB 主包为最大风险项，Tone.js 未瘦身则单列豁免并记 P1 债） |
| 人工走查 | 解压 zip 到任意子路径 `npx serve` 冷启（L-O4 相对 base） |
| 产出 | 日志 §3：zip 体积、各 chunk gzip 明细表、与 Round 1 基线（272KB/149KB）对比 |

## 第 4 步 冒烟与交互 E2E

| 项 | 内容 |
|---|---|
| 目的 | 路由全通 + 学习闭环可完成（L-F2–F10、M-F2–F10 抽样）；验证代码归并（遗留缺陷 1/2）未破坏路由 |
| 自动化 | ✅ `npm --prefix apps/literacy-app run smoke`（17 路由 + 6 交互）、✅ `npm --prefix apps/math-app run smoke`（9 路由 + 10 交互）；🔧 归并后死代码门禁：`rg` 断言 `apps/math-app/src/views/`、`core/engine/` 与 literacy 未引用视图已删除或已被路由引用 |
| 通过判据 | 冒烟零失败零控制台错误；断言无「存在但未被 import」的双套实现残留 |
| 人工走查 | 各 App 手动完成 1 条完整学习闭环（识字：认→写→测；数学：进关卡→答题→结算） |
| 产出 | 日志 §4：路由/交互通过矩阵、死代码清单归零证明 |

## 第 5 步 设计令牌与主题一致性

| 项 | 内容 |
|---|---|
| 目的 | C-4；绑定 `design-tokens-migration.md` Phase 0–3 收口；成语 hero 卡跟随主题（遗留缺陷 6） |
| 自动化 | 🔧 `npm run check:tokens`（三段：a. 旧令牌名归零 b. `.vue` 硬编码色值 literacy=0 / math≤10 c. 两入口 CSS 首行引入 design-tokens）；🔧 四主题截屏：puppeteer-core 对关键 6 页 × sunny/care/night/cosmos 输出 `.agent_workspace/shots-round2/` |
| 通过判据 | check:tokens 全 PASS；截屏无坍塌/白字压白底；主题切换 ≤ 300ms 不闪白；成语 hero 卡在 care/night 下正确换肤 |
| 人工走查 | 对照 ui-ux-design-spec §3.4 抽查 8 组前景/背景对比度（含 M-A8：`--ice-100` 对 `--cosmos-1`） |
| 产出 | 日志 §5：check:tokens 输出、截屏索引、对比度抽查表 |

## 第 6 步 性能与无障碍阈值

| 项 | 内容 |
|---|---|
| 目的 | L-P1–P4 / L-A1（Round 2 性能 P0 门槛）；Lighthouse/axe 自动化补齐（遗留缺陷 7 后半） |
| 自动化 | ✅ `bash scripts/benchmark.sh`（需 `LIGHTHOUSE_BIN` 或本地安装 lighthouse，产出 Perf/LCP/TBT/CLS）；🔧 `npm run test:a11y`：puppeteer-core + axe-core（根 devDependencies 已装）扫两 App 全路由；✅ `node scripts/stress-test.js`（回归 Round 1 基线：2 万卡片 <100ms、10 万题 0 无效） |
| 通过判据 | Lighthouse Performance ≥ 95、Accessibility ≥ 95；FCP<1.0s / LCP<1.5s / TTI<2.0s / CLS<0.05 / TBT<150ms（4× 节流）；axe **critical/serious = 0**；stress-test PASS |
| 人工走查 | Performance 面板录 60s 学习操作：≥55fps、无 >50ms long task（L-P5）；点击到发声 <100ms 抽测（L-P6） |
| 产出 | 日志 §6：Lighthouse 双 App 分数表、axe 违例清单、帧率记录 |

## 第 7 步 离线、隐私与验收留档

| 项 | 内容 |
|---|---|
| 目的 | L-O1–O3 / C-1（Service Worker 为 Round 2 P0 攻坚项，遗留缺陷 7 前半）；固化本轮结论 |
| 自动化 | 🔧 `npm run test:offline`：puppeteer-core 首访预缓存 → `page.setOfflineMode(true)` → 刷新断言可进入并完成 1 次答题；同场景开启请求拦截，断言**外部域名请求数 = 0**（C-1）；🔧 TTS 缺中文嗓音时的降级断言（遗留缺陷 5：静默失败改为可见提示） |
| 通过判据 | 断网冷启动学习闭环可完成；运行时零第三方请求；未缓存懒加载失败给角色化提示不白屏 |
| 人工走查 | DevTools Network 切 Offline 手动复核一遍；家长面板逐项开关后刷新验证持久化（L-F8/F9） |
| 产出 | `.agent_workspace/acceptance-log-round2.md` 定稿：7 步结论 + 未达标项 + 责任模块 + P1 债务表 |

---

## 8. 验收项 ↔ 步骤覆盖矩阵（Round 2 门槛项）

| 验收项 | 步骤 | | 验收项 | 步骤 |
|---|---|---|---|---|
| C-1 隐私零外联 | 7 | | L-P1–P4 性能阈值 | 6 |
| C-2 许可合规 | 1 | | L-P5–P7 帧率/延迟/内存 | 6（人工） |
| C-3 构建打包 | 3 | | L-A1 Lighthouse/axe | 6 |
| C-4 设计令牌 | 5 | | L-A3/M-A8 对比度 | 5 |
| L-F1/M-F1 内容规模 | 2 | | L-O1–O4 离线 | 3、7 |
| L-F2–F10/M-F2–F10 功能 | 4 | | 遗留缺陷 1–8 复核 | 3、4、5、6、7 |

## 9. acceptance-log-round2.md 模板

```markdown
# Round 2 验收日志（执行日期 / 执行者 / commit SHA）
## 总结论：PASS | FAIL（阻断步骤号）
## §1 环境与资源  ## §2 数据与内容  ## §3 构建与包体
## §4 冒烟与E2E   ## §5 令牌与主题  ## §6 性能与无障碍
## §7 离线与隐私
## 未达标项（ID / 现值 / 阈值 / 责任模块 / 计划轮次）
## P1 债务表（移交 Round 3）
```

## 10. 分工绑定（对应 PROGRESS.md Round 2 十子代理）

| 步骤 | 依赖的子代理产出 |
|---|---|
| 2 | 识字 FSRS+扩字（字库 ≥100 + test:srs）、FSRS 单测子代理 |
| 3、4 | 数学代码归并、识字/数学玩法子代理（归并不破路由） |
| 5 | 本文档 + `design-tokens-migration.md` 执行者（Phase 0–3） |
| 6 | 验收自动化子代理（benchmark 接 Lighthouse、a11y-scan） |
| 7 | Service Worker 离线子代理、验收自动化子代理（offline-check） |
