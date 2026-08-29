# 编排模型配比 SOP（永久）

> 自 Round 15 起固定十路并发；**自 2026-08-29 起**默认模型改为全路  
> `cursor-grok-4.6-high-fast`（简称 grok-4.6-fast）。用户已确认。  
> 变更原因：Claude / GPT / Gemini / cf5h 云端子代理额度不可用；实测  
> `cursor-grok-4.6-high-fast` 可稳定发射。额度恢复后若改回分色，须再实测并改本文。

## 固定 10 路

| # | 角色族 | Model slug |
|---|---|---|
| 1–10 | 全角色（规划/审计/验收/实现/测试/门禁） | `cursor-grok-4.6-high-fast` |

> 角色分工仍按下面「分工模板」拆开，只是**模型统一**；发射时 `model` 一律填  
> `cursor-grok-4.6-high-fast`（不要用 `inherit` 冒充，除非该 slug 再次探测失败）。

## 分工模板

1. **#1** — 架构契约  
2. **#2** — 洪恩/体验对标审计  
3. **#3** — ACCEPTANCE + check-roundN  
4–8. **#4–#8** — 本轮 P0 功能实现（可再拆内容/管线/UI）  
9. **#9** — smoke / 单测  
10. **#10** — 回归探针 + evidence 回填  

## 运维

- 分支：`cursor/<task>-9f67`；worktree 开发  
- **缺了立马补**：某路超时无 push / ERROR，按同模型同职责重开  
- 合入集成分支前跑 `check:roundN` + 往轮门禁  
- 发射前若怀疑额度变化：先对 `cursor-grok-4.6-high-fast` 做一行连通探测；失败再临时降级 `inherit`，并记入本轮 BRIEF  

## 修订记录

| 日期 | 变更 |
|---|---|
| Round 15 起 | fable×3 + opus-fast×5 + gpt-sol×2 |
| 2026-08-29 | 实测仅 inherit / composer / grok 可用；用户指定永久改为 **十路全 grok-4.6-fast**（`cursor-grok-4.6-high-fast`） |
