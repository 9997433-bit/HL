# Round 3 设计令牌迁移验收清单（check:tokens 门禁）

> 版本：Round 3 v1.0（2026-08-26）
> 依据：`design-tokens-migration.md`（分相方案与 §5 门禁）、`ui-ux-design-spec.md` §11（令牌落地方式）、
> `round2-acceptance-plan.md` §11（Round 3 章节，脚本规格与通过判据）
> 门禁实现：`scripts/check-tokens.mjs`（✅ 已落成，退出码即结论）
> 使用者：令牌迁移执行子代理（Phase 0–3）、Round 3 验收执行者

---

## 1. 验收标准（Acceptance Criteria）

| ID | 标准 | 检查方式 | 级别 |
|---|---|---|---|
| AC-1 | 两 App 入口 CSS 首个生效语句 `@import` design-tokens.css，第二条 `@import` components.css（顺序：令牌 → 共享组件 → App 本地） | check:tokens C 段 | P0 |
| AC-2 | 两 `vite.config.js` 含 `@shared → ../../shared` 别名，且 `@import` 路径可真实解析 | check:tokens C 段 | P0 |
| AC-3 | math `index.html` 静态挂 `<html data-theme="cosmos">`（避免首帧闪白）；literacy 由 progress store 动态写 `data-theme`（不检静态） | check:tokens C 段 + 人工确认 store 行为未变 | P0 |
| AC-4 | `apps/` 源码旧令牌名引用归零（旧名清单见 §3；含 `var(--x)` 与 `var(--x, fallback)` 两种形态） | check:tokens A 段 | P0 |
| AC-5 | `design-tokens.css` §11 兼容别名节整体删除（文件内无旧名定义） | check:tokens A 段 | P0 |
| AC-6 | `.vue` 硬编码十六进制色值：literacy = 0、math ≤ 10；豁免行必须带 `token-ok` 标记 + 理由 | check:tokens B 段 | P0 |
| AC-7 | 每相收口 `npm test` 全绿；Phase 3 后 `npm run build:all` 全绿 | 既有门禁 | P0 |
| AC-8 | 视觉回归仅允许 3 处预期差异：literacy `--gap-sm` 10→12px、（`--gap-xs` 6→8px 零引用）、math `--radius-l` 32→36px | 分相截屏对比（人工） | P0 |
| AC-9 | M-A8 对比度抽查：`--text-strong`/`--text` 对 `--surface*` ≥ 4.5:1（含 `--ice-100` 对 `--cosmos-1`） | 人工抽查 8 组 | P0 |
| AC-10 | `--cyan/--violet/--gold` 换名的语义判定（交互 → `--brand/--accent/--star`；装饰 → `--neon-*`）逐处人工核对 | sed 后人工过目 | P1 |

**Round 3 第 5 步通过判据：`npm run check:tokens` 退出码 0（AC-1–AC-6 全绿）+ AC-7/8/9 人工确认。**

---

## 2. check:tokens 脚本规格摘要

- **命令**：
  - `npm run check:tokens` — 全量档（C + A + B 三段），Round 3 验收与 Phase 3 合入门禁。
  - `npm run check:tokens:wiring` — 仅 C 段接线档（`--wiring-only`），Phase 0/1/2 合入门禁。
- **实现约束**：纯 Node（≥20）零依赖、不调用外部进程；扫描范围 `apps/*/src/**`
  （.vue/.css/.js/.mjs/.html）+ 两 `index.html`，跳过 node_modules/dist。
- **退出码**：0 = 所检各段全 PASS；1 = 任一项 FAIL（每段违例明细最多打印 20 行）。
- **白名单机制**（仅 B 段）：违例行内出现 `token-ok` 即豁免，写法示例：
  `fill="#5ee7ff" /* token-ok: 吉祥物 SVG 插画固有色，非 UI 语义色 */`。
  无理由的裸标记在人工走查中按违例回退。
- **A 段正则**（带闭合限定 `[),]`，不误伤令牌合法名 `--ink-900`、间距 `--space-…` 等新名）：

```text
var\(\s*--(?:seed-[a-z]+|space-[0-3]|ink(?:-soft|-dim)?|cyan|violet|pink|gold|green|red
|orange|radius-[sml]|shadow-card|bg-deep|bg-card|text-main|text-dim|star-gold
|radius-card|font-kid)\s*[),]
```

---

## 3. 旧令牌名 → 新名速查（迁移执行时对照）

| 旧名 | 新名 | 旧名 | 新名 |
|---|---|---|---|
| `--seed-mango` | `--mango-400` | `--cyan` | 交互 `--brand` / 装饰 `--neon-cyan` |
| `--seed-coral` | `--coral-400` | `--violet` | 交互 `--accent` / 装饰 `--neon-violet` |
| `--seed-mint` | `--mint-400` | `--gold` | 奖励 `--star` / 其余 `--neon-gold` |
| `--seed-sky` | `--sky-400` | `--green` / `--red` | `--success` / `--danger` |
| `--seed-grape` | `--grape-400` | `--pink` / `--orange` | `--neon-pink` / `--neon-orange` |
| `--seed-leaf` | `--leaf-400` | `--radius-s/m` | `--radius-sm/md`（同值） |
| `--ink` | `--text-strong` | `--radius-l` | `--radius-xl`（32→36px） |
| `--ink-soft` | `--text` | `--shadow-card` | `--shadow-lg`（同值） |
| `--ink-dim` | `--text-soft` | `--font-kid` | `--font-round` |
| `--space-0/1` | `--bg-page-solid` 或 `--cosmos-0/1` | `--text-main` / `--text-dim` | `--text-strong` / `--text-soft` |
| `--space-2/3` | `--surface-sunken` / `--surface-strong` | `--bg-deep --bg-card --star-gold --radius-card` | 无消费方，直接删定义 |

---

## 4. 分相勾选清单（执行顺序固定，逐相独立 commit）

### Phase 0 — 接线（门禁：`npm run check:tokens:wiring` + `npm test`）

- [ ] 两 `vite.config.js` 增加 `'@shared': fileURLToPath(new URL('../../shared', import.meta.url))`
- [ ] literacy `base.css` 顶部：`@import '@shared/styles/design-tokens.css';` → `@import '@shared/styles/components.css';` → `@import './theme.css';`
- [ ] math `main.css` 顶部：同顺序引入令牌与组件层（本相不删自有变量，后声明覆盖保证零视觉变化）
- [ ] math `index.html`：`<html lang="zh-CN" data-theme="cosmos">`
- [ ] `npm run check:tokens:wiring` 退出码 0（C 段 12 项全过）
- [ ] `npm test && npm run build:all` 全绿；两 App 截屏与迁移前 0 差异
- [ ] commit：`tokens: 双App接入design-tokens+components`

### Phase 1 — literacy 删重（门禁：wiring 档 + literacy test）

- [ ] 删除 `theme.css` 整文件与 `base.css` 对它的 `@import`
- [ ] `base.css` 等值替换：body 字体栈 → `var(--font-round)`；focus 描边 → `var(--focus-ring)`
- [ ] 三主题（sunny/care/night）截屏对比：仅允许 `--gap-sm` +2px 位移
- [ ] commit：`tokens(literacy): 删除theme.css重复层`

### Phase 2 — math cosmos 语义化（门禁：wiring 档 + math test）

- [ ] `main.css` 删 `:root` 全部自有变量（38 行）；5 处骨架期变量就地改写（§3 速查表末行）
- [ ] 12 个 `.vue` 约 135+ 处批量换名（§3 速查表；sed 后**人工核对** `--cyan/--violet/--gold` 语义列 = AC-10）
- [ ] cosmos 截屏对比：仅允许 panel 圆角 32→36px；M-A8 对比度抽查（AC-9）
- [ ] commit：`tokens(math): cosmos语义化换名`

### Phase 3 — 删别名 + 收口（门禁：**全量档** + `npm test && npm run build:all`）

- [ ] literacy `--seed-*` 约 45 处换名为原始色板名（含 `.js` 数据文件内字符串）
- [ ] 删除 `design-tokens.css` §11 兼容别名整节（当前 450–487 行）
- [ ] `.vue` 硬编码色值清理：literacy 14 → 0；math 52 → ≤ 10（保留位逐条 `token-ok` + 理由）
- [ ] `npm run check:tokens` 退出码 0（A/B/C 三段全 PASS）
- [ ] check:tokens 完整输出 + 白名单豁免清单粘贴进 `acceptance-log-round3.md` §5
- [ ] commit：`tokens: 删除兼容别名+check:tokens门禁全绿`

---

## 5. 现状基线（2026-08-26 实测，`node scripts/check-tokens.mjs` 输出）

| 段 | 项 | 现值 | 目标 |
|---|---|---|---|
| C | 接线检查 | **7 项全挂**（未引入令牌、无 `@shared` 别名、math 无 data-theme） | 12 项全过 |
| A | literacy 旧令牌名 | **45 处 / 7 文件**（全部 `--seed-*`） | 0 |
| A | math 旧令牌名 | **141 处 / 13 文件**（含 15 处 `var(--x, fallback)` 形态，迁移文档正则漏检，已由本脚本覆盖） | 0 |
| A | §11 兼容别名节 | 仍在（design-tokens.css 450–487 行） | 删除 |
| B | literacy `.vue` 硬编码色值 | **14 处**（白名单 0） | 0 |
| B | math `.vue` 硬编码色值 | **52 处**（白名单 0；大头 `MascotBot.vue` SVG 插画色，属 `token-ok` 豁免候选） | ≤ 10 |

全量档当前 FAIL 12 项 —— **属预期红**（Phase 0–3 均未执行），按 §4 分相清零。

---

## 6. 常见修复指引（脚本 FAIL 时对照）

- `入口 CSS 首个生效语句引入 design-tokens.css` 挂 → 检查 `@import` 是否被普通规则或本地
  `@import` 抢先；注释与 `@charset` 可在其前，其余不行。
- `vite.config.js 含 @shared 别名` 挂 → 按 §4 Phase 0 第 1 项补 `resolve.alias`；monorepo 根
  含 `workspaces`，`server.fs.allow` 默认放行，无需额外配置。
- `旧令牌名引用` 挂 → 对照 §3 速查表换名；JS 数据文件（`characters.js`、`progress.js`）内的
  字符串形态同样计入。
- `§11 兼容别名已删除` 挂 → 必须先保证两 App 旧名归零（A 段前两项 PASS）再删节，防样式坍塌
  （迁移文档风险 R5）。
- `硬编码色值` 超预算 → 优先换语义令牌；确属插画固有色才加 `token-ok` 标记并写明理由。
