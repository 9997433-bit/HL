# Round 15 验收标准 · 一字一动画（玩·认·练·写·说）

> 版本：v1.0  
> 简报：`.agent_workspace/ROUND15-BRIEF.md`  
> 探针：`npm run check:round15` → `scripts/check-round15.mjs`

## G 总则

- **G1** 不复制洪恩 IP/美术；OpenMoji + 程序化动画。
- **G2** 1820 字 Play 覆盖率 100%；空洞=失败（H2/H5）。
- **G3** 五步默认顺序：玩 → 认 → 练 → 写 → 说；可手动跳步但不伪造 `done`。
- **G4** `prefers-reduced-motion` / 家长「减少动态」下仍可完成全流程。
- **G5** 每步可跳过；自动衔接保留「等一下」停表（沿用 CharDetailView 既有 WCAG 模式）。
- **G6** 往轮探针不因本轮回退（H8）。

## H1–H8（与探针一一对应）

详见 ROUND15-BRIEF 硬门槛表。回填时在 `acceptance-log-round15.md` 写实测命令与输出摘录。

## 走查（人工 / 代理）

| ID | 检查 |
|---|---|
| W1 | 点 u1「一」：先玩后认，有动效或可感知互动 |
| W2 | 点无富脚本冷门字：仍有模板互动，能点完成 |
| W3 | 有字源字：认步自动播演变，无需先找按钮 |
| W4 | 写步：先示范再描红；可跳过示范 |
| W5 | 开减少动态：五步仍可走完 |
| W6 | 街机厅游戏不回归 |

## 红线

- 禁止 `getCharPlay` 对缺字返回 `null` 却声称 H2 绿
- 禁止把 `templateFallback` 富脚本计数进 H3
- 禁止为过门禁把 PHASES 只改 label 不接 Play 舞台
