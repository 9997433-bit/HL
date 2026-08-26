# 设计令牌迁移方案 — Round 2（literacy theme.css + math cosmos 主题）

> 版本：Round 2 v1.0（2026-08-26）
> 依据：`.agent_workspace/ui-ux-design-spec.md` §11（令牌落地方式）、`sota-acceptance-criteria.md` C-4
> 唯一令牌源：`shared/styles/design-tokens.css`（已就绪，含 §11 兼容别名）
> 共享组件层：`shared/styles/components.css`（本轮新建，基础 `.btn`/`.card`）
> 验收绑定：`.agent_workspace/round2-acceptance-plan.md` 第 5 步（令牌与主题一致性）

---

## 0. 现状盘点（2026-08-26 实测）

| 项 | literacy-app | math-app |
|---|---|---|
| 令牌文件引入 | **未引入**。`main.js → styles/base.css → @import './theme.css'` | **未引入**。`main.js → styles/main.css`（自带全部变量） |
| `data-theme` 挂载 | ✅ 由 progress store `applyAppearance()` 写 `<html data-theme>`（sunny/care/night） | ❌ 无。护眼走 `.app-root.eye-care` 滤镜，与令牌主题机制无关 |
| Vite `@shared` 别名 | ❌ 无（仅 `@` → `./src`） | ❌ 无（仅 `@` → `./src`） |
| 与令牌重复的变量 | `theme.css` 186 行 ≈ 95% 与令牌逐值相同 | `main.css` §:root 38 行调色板与令牌 §11 别名对应 |
| 旧变量引用规模 | `--seed-*` 约 20 处（含 JS 数据文件 `characters.js`、`progress.js`） | 别名变量（`--space-* --ink* --cyan` 等）**约 135 处 / 12 文件**；骨架期变量（`--bg-deep --bg-card --text-main --text-dim --star-gold --radius-card --font-kid`）仅 `main.css` 内部 5 处 |
| 与令牌的数值分歧 | `--gap-xs: 6px`（令牌 8px，src 引用 **0 处**）、`--gap-sm: 10px`（令牌 12px，src 引用 **27 处**） | `--radius-l: 32px`（令牌别名映射到 `--radius-xl: 36px`）；`--font-kid` 首选 `'ZCOOL KuaiLe'`（无 @font-face 无外链，实际必然回退，等同令牌 `--font-round`） |

**结论**：令牌文件本身已按两个 App 的现值抄录，迁移的主要工作是「接线 + 删重 + 换名」，
预期视觉变化仅 3 处且全部符合 4pt 网格/圆角阶梯规范（见 §5 风险表）。

---

## 1. 迁移原则

1. **分相提交**：每个 Phase 一个独立 commit，出问题按 commit 回滚，不混入功能改动。
2. **先等值、后对齐**：Phase 0–2 保证像素级等值（分歧 3 处除外），规范对齐类改动（如按钮字号
   1.05rem → `--fs-lg`）留给各功能子代理在改到该组件时顺手完成，不在本迁移内批量做。
3. **组件只引语义层**：`.vue` 内只允许 `--bg-* --surface* --text* --brand* --accent* --info
   --success --danger --star --grid-line --stroke-* --focus-ring --overlay-scrim --shadow-*`
   与排印/间距/动效/尺寸令牌；原始色板（`--mango-* --cosmos-* --neon-*` 等）仅限装饰性场景
   （彩带、吉祥物、单元配色）且需注释说明。
4. **每相收口跑门禁**：`npm test`（两 App 的 check + build + smoke）必须全绿才允许进入下一相。

---

## 2. Phase 0 — 接线（零视觉变化，先行合入）

**改动文件**：`apps/*/vite.config.js`、`apps/literacy-app/src/styles/base.css`、
`apps/math-app/src/styles/main.css`、`apps/math-app/index.html`

1. 两个 `vite.config.js` 增加共享别名：

```js
resolve: {
  alias: {
    '@': fileURLToPath(new URL('./src', import.meta.url)),
    '@shared': fileURLToPath(new URL('../../shared', import.meta.url))
  }
}
```

   monorepo 根 `package.json` 含 `workspaces`，Vite 的 `server.fs.allow` 默认放行 workspace
   根，`../../shared` 无需额外配置即可在 dev 与 build 下解析。

2. 入口 CSS **最前** 引入令牌与共享组件层（顺序固定：令牌 → 共享组件 → App 本地）：

```css
/* apps/literacy-app/src/styles/base.css 第 1–3 行 */
@import '@shared/styles/design-tokens.css';
@import '@shared/styles/components.css';
@import './theme.css'; /* Phase 1 删除 */
```

```css
/* apps/math-app/src/styles/main.css 第 1–2 行 */
@import '@shared/styles/design-tokens.css';
@import '@shared/styles/components.css';
```

3. `apps/math-app/index.html`：`<html lang="zh-CN" data-theme="cosmos">`（静态写死，避免
   首帧闪白；literacy 已由 store 动态写，不动）。

4. 本相**不删任何旧变量**：literacy `theme.css` 与 math `main.css` 的同名变量在令牌之后
   声明，按 CSS 后声明覆盖，视觉与迁移前完全一致；令牌只是补齐了此前缺失的变量
   （`--fs-* --font-* --dur-instant/hero --ease-bounce/smooth/anticipate --z-* --tap-* --btn-h-*
   音频令牌等）供新代码立即使用。

**验证**：`npm test && npm run build:all` 全绿；两 App 各主题截屏与迁移前逐像素对比（允许 0 差异）。

---

## 3. Phase 1 — literacy：删除 theme.css 重复层

**改动文件**：`apps/literacy-app/src/styles/theme.css`（删除）、`base.css`

1. **删除 `theme.css` 整个文件**，并移除 `base.css` 对它的 `@import`。逐块对应关系：
   - `:root` 品牌种子/圆角/阴影/间距/时长/缓动 → 令牌 §1/§3/§4（`--seed-*` 由令牌 §11 别名
     以同值接管：`--seed-mango: var(--mango-400)` = `#ffb84d`，其余同理）。
   - sunny/care/night 三主题块 → 令牌 §8 逐值相同（含 care 的阴影覆盖；night 的
     `--brand: #ffb84d` = `var(--mango-400)`）。令牌额外补齐 `--info --focus-ring
     --overlay-scrim --shadow-glow --shadow-press`（care/night 版本），只增不改。
   - `data-font-scale` 四档 → 令牌 §9 逐值相同。
   - `data-motion` / `prefers-reduced-motion` 降级 → 令牌 §10 逐字相同。
2. **接受 2 处数值变化**（对齐 4pt 网格）：`--gap-xs` 6→8px（无引用，零影响）、
   `--gap-sm` 10→12px（27 处引用，行内间距整体 +2px）。
3. `base.css` 顺手等值替换（仍属"删重"不属"重设计"）：
   - `body { font-family: … }` 硬编码字体栈 → `var(--font-round)`（栈内容一致）；
   - `:focus-visible { outline-color: var(--brand) }` → `var(--focus-ring)`（sunny 下同值）；
   - `base.css` 里与 `shared/styles/components.css` 重复的 `.btn/.card` 基类**保留不动**
     （后声明覆盖，视觉不变），由「识字玩法深化」子代理在触碰对应组件时逐步删除本地副本，
     全部删完后 base.css 只剩 reset、`.tianzige`、路由过渡与工具类。
4. `--seed-*` 的消费方（`data/characters.js`、`stores/progress.js`、`MascotCompanion.vue`、
   `CelebrationLayer.vue`、`HomeView.vue` 等约 20 处）本相**不改名**，Phase 3 统一换成原始
   色板名（`--seed-mango` → `--mango-400` 等，纯文本替换、同值）。

**验证**：`npm --prefix apps/literacy-app run test`；三主题（sunny/care/night）截屏对比，
仅允许 `--gap-sm` 相关 +2px 位移差异。

---

## 4. Phase 2 — math：cosmos 主题语义化

**改动文件**：`apps/math-app/src/styles/main.css` + 12 个含旧名引用的 `.vue`

1. `main.css` 删除 `:root` 全部自有变量（38 行），改由令牌供给；文件内 5 处骨架期变量就地改写：
   - `--font-kid` → `--font-round`（`'ZCOOL KuaiLe'` 无字体文件，删除即可；若后续引入子集化
     字体，以 App 级 `--font-app: 'ZCOOL KuaiLe', var(--font-round)` 覆盖）；
   - `--text-main` → `--text-strong`、`--text-dim` → `--text-soft`；
   - `body` 背景径向渐变 → `var(--bg-page)`（令牌 cosmos 版逐字相同）；
   - `--bg-deep --bg-card --star-gold --radius-card` 已无消费方，直接删定义。
2. **12 个 `.vue` 文件约 135 处旧名批量换名**，映射表（机械 sed 安全，逐文件核对语义列）：

| 旧名 | 新名（语义优先） | 说明 |
|---|---|---|
| `--ink` | `--text-strong` | 正文强调 |
| `--ink-soft` | `--text` | 正文 |
| `--ink-dim` | `--text-soft` | 辅助文字 |
| `--space-0/1` | `--bg-page-solid` 或保留 `--cosmos-0/1` | 页面底=语义；装饰渐变=原始板 |
| `--space-2/3` | `--surface-sunken` / `--surface-strong` | 容器面 |
| `--cyan` | 可交互→`--brand`；装饰→`--neon-cyan` | 需人工判定 |
| `--violet` | 可交互→`--accent`；装饰→`--neon-violet` | 需人工判定 |
| `--green` | `--success` | 判分正确 |
| `--red` | `--danger` | 判分错误 |
| `--gold` | 奖励→`--star`；其余→`--neon-gold` | 星星语义优先 |
| `--pink` / `--orange` | `--neon-pink` / `--neon-orange` | 无语义位，保留原始板 |
| `--radius-s/m` | `--radius-sm/md` | 同值 |
| `--radius-l` | `--radius-xl` | **32→36px**，panel 圆角略增 |
| `--shadow-card` | `--shadow-lg` | 同值 |

   参考批量命令（换名后必须人工过一遍 `--cyan/--violet/--gold` 的语义列）：

```bash
cd apps/math-app/src
rg -l 'var\(--(ink|space-|cyan|violet|pink|gold|green|red|orange|radius-[sml]\)|shadow-card)' \
  | xargs sed -i -E \
    -e 's/var\(--ink-soft\)/var(--text)/g' \
    -e 's/var\(--ink-dim\)/var(--text-soft)/g' \
    -e 's/var\(--ink\)/var(--text-strong)/g' \
    -e 's/var\(--green\)/var(--success)/g' \
    -e 's/var\(--red\)/var(--danger)/g' \
    -e 's/var\(--radius-s\)/var(--radius-sm)/g' \
    -e 's/var\(--radius-m\)/var(--radius-md)/g' \
    -e 's/var\(--radius-l\)/var(--radius-xl)/g' \
    -e 's/var\(--shadow-card\)/var(--shadow-lg)/g'
```

3. `main.css` 本地 `.btn/.btn-primary/.btn-warm/.btn-ghost/.btn-sm/.btn-lg` 命名与共享层
   BEM 规范（`.btn--primary`）不一致：本相保留原类名与样式（避免一次性改模板），由
   「数学 QuizShell」子代理在收敛答题壳时切换到 `shared/styles/components.css` 的
   `.btn--*`/`.card--*`，`main.css` 中对应块随之删除。
4. `.app-root.eye-care` 滤镜与 `data-theme` 机制并存，本轮不动（math 的护眼档位设计留
   Round 3 议题：是否升级为真正的 care 主题变体）。

**验证**：`npm --prefix apps/math-app run test`（check:content + build + smoke 9 路由 +
10 交互）；cosmos 截屏对比，仅允许 panel 圆角 32→36px 差异；对比度抽查 M-A8
（`--text-strong`/`--text` 对 `--surface*` ≥ 4.5:1）。

---

## 5. Phase 3 — 删除兼容别名 + 立防回归门禁

**改动文件**：`shared/styles/design-tokens.css`、literacy 中 `--seed-*` 消费方

1. literacy `--seed-*` 约 20 处换名：`--seed-mango→--mango-400`、`--seed-coral→--coral-400`、
   `--seed-mint→--mint-400`、`--seed-sky→--sky-400`、`--seed-grape→--grape-400`、
   `--seed-leaf→--leaf-400`（同值纯换名，含 `.js` 数据文件内的字符串）。
2. 删除 `design-tokens.css` §11 兼容别名整节（literacy 旧名 + math 旧名）。
3. 防回归门禁（绑定验收计划第 5 步，建议由验收自动化子代理落成 `npm run check:tokens`）：

```bash
# a) 旧名归零：命中即失败
rg -n 'var\(--(seed-[a-z]+|space-[0-3]|ink(-soft|-dim)?|cyan|violet|pink|gold|green|red|orange|radius-[sml]|shadow-card|bg-deep|bg-card|text-main|text-dim|star-gold|radius-card|font-kid)\)' \
  apps/ && exit 1 || echo "PASS: 无旧令牌引用"

# b) 硬编码色值收敛：.vue 内十六进制色值只允许出现在白名单注释行
#    （现状基线：literacy 18 处 / math 67 处，Round 2 目标 literacy=0、math ≤ 10）
rg -n '#[0-9a-fA-F]{3,8}\b' apps/literacy-app/src apps/math-app/src --glob '*.vue'

# c) 双 App 均以令牌开头引入
head -1 apps/literacy-app/src/styles/base.css | rg -q 'design-tokens' || exit 1
head -1 apps/math-app/src/styles/main.css | rg -q 'design-tokens' || exit 1
```

**验证**：`npm test && npm run build:all` 全绿；门禁 a/c 必过，b 记录进验收日志。

---

## 6. 风险与回滚

| # | 风险 | 影响 | 缓解 |
|---|---|---|---|
| R1 | `--gap-sm` 10→12px（27 处） | 行内元素间距 +2px | 符合 4pt 网格；三主题截屏走查确认无换行/溢出 |
| R2 | `--radius-l` 32→36px | math panel 圆角略增 | 视觉无损；如需保留 32px 可在 main.css 加一行 App 级覆盖 |
| R3 | math 字体栈去掉 `'ZCOOL KuaiLe'` | 无（该字体从未真实加载） | 保留 App 级 `--font-app` 覆盖位 |
| R4 | `--cyan/--violet/--gold` 语义误判（交互色 vs 装饰色） | 主题间对比度漂移 | sed 后人工核对 + M-A8 对比度抽查 |
| R5 | 别名删早了（Phase 3 先于全部换名） | 页面变量落空、样式坍塌 | 门禁 a 在删除前先跑一次必须 PASS；每相独立 commit，`git revert` 即回滚 |
| R6 | 与其他 9 个并发子代理改同一批 `.vue` 冲突 | 合并冲突 | 换名相（Phase 2/3）安排在功能子代理收敛提交之后执行；纯文本同值替换重放成本低 |

## 7. 执行顺序与分工建议

| 相 | 前置 | 建议执行者 | 产出 commit |
|---|---|---|---|
| Phase 0 接线 | 无 | 本轮任一样式向子代理 | `tokens: 双App接入design-tokens+components` |
| Phase 1 literacy 删重 | Phase 0 | 识字玩法深化子代理 | `tokens(literacy): 删除theme.css重复层` |
| Phase 2 math 语义化 | Phase 0；QuizShell 收敛后 | 数学 QuizShell/归并子代理 | `tokens(math): cosmos语义化换名` |
| Phase 3 删别名+门禁 | Phase 1+2 全绿 | 验收自动化子代理 | `tokens: 删除兼容别名+check:tokens门禁` |
