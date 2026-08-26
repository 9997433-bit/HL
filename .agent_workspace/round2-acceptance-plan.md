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
    "check:tokens": "node scripts/check-tokens.mjs",
    "check:tokens:wiring": "node scripts/check-tokens.mjs --wiring-only",
    "test:a11y": "node scripts/a11y-scan.mjs",
    "test:offline": "node scripts/offline-check.mjs",
    "accept:round2": "bash scripts/accept-round2.sh"
  }
}
```

  ✅ `check:tokens` / `check:tokens:wiring` 已于 Round 3 落成（`scripts/check-tokens.mjs`，
  规格与验收标准见 §11 与 `.agent_workspace/round3-tokens-checklist.md`）。

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
| 自动化 | ✅ `npm run check:tokens`（`scripts/check-tokens.mjs`，三段：C. 接线（两入口 CSS 令牌 → 组件层顺序引入 + `@shared` 别名 + math `data-theme="cosmos"`）→ A. 旧令牌名归零 + §11 别名删除 → B. `.vue` 硬编码色值 literacy=0 / math≤10；Phase 0 阶段可先跑 `npm run check:tokens:wiring` 只验 C 段，详见 §11）；🔧 四主题截屏：puppeteer-core 对关键 6 页 × sunny/care/night/cosmos 输出 `.agent_workspace/shots-round2/` |
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

---

## 11. Round 3 章节 — 令牌迁移收口验收与 check:tokens 门禁

> 增补：Round 3 v1.0（2026-08-26）
> 背景：Round 2 收口时 `design-tokens-migration.md` Phase 0–3 **均未执行**（两 App 未引入
> design-tokens.css），第 5 步自动化缺门禁脚本。本章将迁移收口列为 Round 3 第 5 步的
> P0 阻断项，并绑定已落成的 `scripts/check-tokens.mjs`。
> 配套细则与逐相勾选清单：`.agent_workspace/round3-tokens-checklist.md`

### 11.1 check:tokens 脚本规格（已落成 ✅）

| 项 | 规格 |
|---|---|
| 实现 | `scripts/check-tokens.mjs`（纯 Node ≥20，零依赖，不调用外部进程） |
| 入口 | `npm run check:tokens`（全量档）；`npm run check:tokens:wiring`（仅 C 段接线档，等价 `--wiring-only`） |
| C 段 接线 | ① `shared/styles/design-tokens.css`、`components.css` 存在且令牌源含语义层（`--bg-page`）与 cosmos 主题块；② 两入口 CSS（literacy `src/styles/base.css`、math `src/styles/main.css`）**首个生效语句**（跳过注释/`@charset`）`@import` design-tokens.css，第二条 `@import` components.css（顺序：令牌 → 共享组件 → App 本地）；③ `@import` 路径可解析（支持 `@shared/` 别名与相对路径）；④ 两 `vite.config.js` 含 `@shared` 别名；⑤ math `index.html` 静态挂 `data-theme="cosmos"`（literacy 由 store 动态写，不检静态） |
| A 段 旧名归零 | 扫描 `apps/*/src/**`（.vue/.css/.js/.mjs/.html）+ 两 `index.html`：`var(--旧名)` 与 `var(--旧名, fallback)` 全部归零（旧名清单 = 迁移文档 §5.a：`--seed-* --space-0..3 --ink/-soft/-dim --cyan --violet --pink --gold --green --red --orange --radius-s/m/l --shadow-card --bg-deep --bg-card --text-main --text-dim --star-gold --radius-card --font-kid`，正则带闭合限定不误伤 `--ink-900` 等令牌合法名）；且 design-tokens.css **§11 兼容别名节已删除**（文件内无旧名定义） |
| B 段 硬编码色值 | `.vue` 内十六进制色值（`#[0-9a-fA-F]{3,8}`）：literacy = 0、math ≤ 10；行内含 `token-ok` 注释标记的白名单行豁免（标记必须附理由，如 SVG 内嵌插画固有色） |
| 退出码 | 0 = 所检各段全 PASS；1 = 任一项 FAIL（打印 `[FAIL]` 明细，每段最多 20 行） |
| 不并入 `npm test` | 迁移收口前必红；由 Round 3 验收流程显式调用，收口后可考虑并入 |

### 11.2 分相门禁绑定（执行顺序 = 迁移文档 §7）

| 相 | 合入门禁（必须绿） | 备注 |
|---|---|---|
| Phase 0 接线 | `npm run check:tokens:wiring` + `npm test` | C 段 7 项接线检查全过；截屏与迁移前 0 差异 |
| Phase 1 literacy 删重 | `npm run check:tokens:wiring` + `npm --prefix apps/literacy-app run test` | 三主题截屏仅允许 `--gap-sm` +2px 位移 |
| Phase 2 math 语义化 | `npm run check:tokens:wiring` + `npm --prefix apps/math-app run test` | cosmos 截屏仅允许 panel 圆角 32→36px；M-A8 对比度抽查 |
| Phase 3 删别名 + 收口 | **`npm run check:tokens`（全量）** + `npm test && npm run build:all` | Round 3 第 5 步 P0 阻断项；A/B/C 三段全 PASS |

### 11.3 Round 3 通过判据与基线

- **通过判据（P0）**：`npm run check:tokens` 退出码 0；四主题截屏无坍塌/白字压白底；
  主题切换 ≤ 300ms 不闪白（沿用第 5 步人工走查）。
- **B 段口径**：math 预算 ≤ 10 的保留位仅限装饰性 SVG 插画固有色，逐条以 `token-ok` 标记
  说明；无标记的超预算即 FAIL。
- **现状基线（2026-08-26 实测，脚本输出）**：C 段 7 项接线全挂（Phase 0 未做）；旧令牌名
  literacy 45 处 / math 141 处（含 fallback 形态，较迁移文档正则多检出 15 处）；§11 别名节
  仍在；`.vue` 硬编码色值 literacy 14 处 / math 52 处（白名单 0）。全量档当前 FAIL 12 项，
  属预期红：迁移执行子代理按 §11.2 分相清零。
- **留档**：Round 3 执行结果写入 `.agent_workspace/acceptance-log-round3.md`（沿用 §9 模板），
  §5 小节粘贴 check:tokens 完整输出与白名单豁免清单。
