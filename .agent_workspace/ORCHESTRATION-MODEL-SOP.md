# 编排模型配比 SOP（永久）

> 自 Round 15 起，**所有后续轮次**默认按此配比发射子代理。用户已确认。

## 固定 10 路

| # | 角色族 | Model slug |
|---|---|---|
| 1–3 | fable（规划/审计/验收） | `claude-fable-5-thinking-high` |
| 4–8 | opus-fast（实现） | `claude-opus-5-thinking-high-fast` |
| 9–10 | gpt-sol（测试/门禁） | `gpt-5.6-sol-high` |

## 分工模板

1. **fable** — 架构契约  
2. **fable** — 洪恩/体验对标审计  
3. **fable** — ACCEPTANCE + check-roundN  
4–8. **opus-fast** — 本轮 P0 功能实现（可再拆内容/管线/UI）  
9. **gpt-sol** — smoke / 单测  
10. **gpt-sol** — 回归探针 + evidence 回填  

## 运维

- 分支：`cursor/<task>-9f67`；worktree 开发  
- **缺了立马补**：某路超时无 push / ERROR，按同模型同职责重开  
- 合入集成分支前跑 `check:roundN` + 往轮门禁  
