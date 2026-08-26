# MathQuest · 数学星球大冒险

开源儿童数学 Web 应用(3-12 岁),对标并超越洪恩数学。

## 快速开始

```bash
npm install
npm run dev      # http://localhost:5174
npm run build
```

## 七大模块(7 颗星球)

| 星球 | 模块 | 路由 |
|------|------|------|
| 数字星球 | 数与量启蒙 | `/number-sense` |
| 计算星球 | 加减乘除 | `/arithmetic` |
| 图形星球 | 几何空间 | `/geometry` |
| 逻辑星球 | 逻辑推理 | `/logic` |
| 数独星球 | 数独专项 | `/sudoku` |
| 故事星球 | 应用题 | `/word-problems` |
| 星图中心 | 进度系统 | `/progress` |

## 架构

- `src/core/` — 纯 JS 引擎层(无框架依赖,可单测):题目生成器、掌握度自适应、数独生成/求解、Tone.js 音效、Canvas 舞台;
- `src/data/` — 课程技能图谱(L1-L5)与应用题母题模板;
- `src/stores/` — Pinia:progress(掌握度/星星/打卡,localStorage 持久化)、settings(音效/护眼);
- `src/modules/` — 七大模块视图。

完整设计见 `/.agent_workspace/math-architecture.md`。
