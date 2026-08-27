# Round 5B 验收记录（待回填）

> 状态：**启动中** —— 基线 `3cf37eb`（Round 5 12/12 全绿），`check:round5b` **0/6 有意红灯**
> 判定标准：`.agent_workspace/ROUND5B-ACCEPTANCE.md`
> 回填规则：每格填实测输出/计数/勾选，禁止「应该可以」；未达标项进 §5。

记录日期：（合并后回填）
集成分支：`cursor/openmoji-integration-9f67`

## 0. 轮次门禁总览

| # | 门禁 | 命令 | 结果 | 备注 |
| --- | --- | --- | --- | --- |
| G1 | 全量单测 | `npm test` | 待回填 | |
| G2 | Round 5 不退化 | `npm run check:round5` | 待回填 | 要求保持 12/12 |
| G3 | Round 5B 硬门槛 | `npm run check:round5b` | 待回填 | 要求 6/6，粘贴输出到 §1 |
| G4 | Round 3 全链 | `npm run test:round3` | 待回填 | 含离线 smoke + Lighthouse |
| G5 | 出包 | `npm run build:all` | 待回填 | zip 体积见 §4 |

## 1. `check:round5b` 六项硬门槛

| ID | 检查 | 阈值 | 基线（3cf37eb） | 实测（合并后） | 责任分支 |
| --- | --- | --- | --- | --- | --- |
| P1 | 每日冒险 | 模板 ≥3 / 每日 3 件 / 首页 + 庆祝 | ✗ 任务库缺失 | 待回填 | r5b-daily-adventure |
| P2 | 吉祥物陪跑 | 识字 ≥5 且数学 ≥5 视图 | ✗ 识字 0/5、数学 6/5 | 待回填 | r5b-mascot-companion |
| P3 | 统一 useFeedback | 粒子/震动/音效 + 三面接线 | ✗ 统一 composable 缺失 | 待回填 | r5b-use-feedback |
| P4 | 地图叙事 | 剧情 ≥5 条 + 接线 + 过渡标记 | ✗ 识字 0、数学 0 条 | 待回填 | r5b-map-narrative |
| P5 | 街机大厅 | 街机标记 + 全渲染 + 一句话玩法 | ✗ 一句话玩法 0/4 | 待回填 | r5b-games-arcade |
| P6 | 答对节奏 | 双 App streak 谱面 + 各 ≥1 调用 | ✗ 双 App 无 streak 谱面 | 待回填 | r5b-sfx-rhythm |

`npm run check:round5b` 最终输出粘贴处：

```
（待回填）
```

## 2. 手动走查（ROUND5B-ACCEPTANCE §3）

- [ ] W1 每日冒险：第三件勾上有庆祝；手动勾/取消算数；隔天轮换
- [ ] W2 吉祥物：点触有语音/鼓励；不遮挡答题区；reduced-motion 安分
- [ ] W3 useFeedback：星星粒子 + 震动；答错抖动克制；reduced-motion 全降级
- [ ] W4 解锁过渡：动画可跳过；灰显 + 一句话剧情可读
- [ ] W5 街机大厅：护眼主题辉光收敛；一句话玩法孩子读得完
- [ ] W6 连对节奏：3+ 音高递进；断连回落；关音效全静音
- [ ] W7 红线抽查：触控 ≥ 56×56、键盘可达、庆祝可跳过

## 3. 回归指标

| 指标 | 要求 | 实测 |
| --- | --- | --- |
| Lighthouse 识字 Perf/A11y | ≥ 90 / ≥ 90 | 待回填 |
| Lighthouse 数学 Perf/A11y | ≥ 90 / ≥ 90 | 待回填 |
| axe critical / serious | 0 / 0 | 待回填 |
| 识字首屏 JS gzip | < 250KB | 待回填 |

## 4. 出包 zip

| 文件 | 大小（bytes） |
| --- | ---: |
| `dist/hongen-literacy-app.zip` | 待回填 |
| `dist/hongen-math-app.zip` | 待回填 |

## 5. 未达标项

| 项 | 差距 | 责任分支 | 计划 |
| --- | --- | --- | --- |
| （无则写「无」） | | | |

## 6. 结论

（子代理交付合并后回填：P0 达成率、是否可出包、下一轮建议）
