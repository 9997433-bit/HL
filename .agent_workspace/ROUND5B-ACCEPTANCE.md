# Round 5B 验收标准 · Play Layer

## 1. 轮次门禁

| # | 命令 | 要求 |
|---|---|---|
| G1 | `npm test` | 全绿 |
| G2 | `npm run check:round5` | Round 5 不退化（12/12） |
| G3 | `npm run check:round5b` | 六项 Play 硬门槛全绿 |
| G4 | `npm run test:round3` | 全绿 |
| G5 | `npm run build:all` | zip 产出 |

## 2. 六项硬门槛

| ID | 检查 | 阈值 |
|---|---|---|
| P1 | 每日冒险任务 | 识字首页 ≥3 项可勾选今日任务 |
| P2 | 吉祥物陪跑 | 核心路由常驻 ≥5（探针：MascotCompanion/MascotBot 引用） |
| P3 | useFeedback | `shared/` 或双 App composable 存在且各 App ≥1 处引用 |
| P4 | 地图叙事 | 解锁状态+剧情文案（识字 LearnView 或数学 HomeView） |
| P5 | 街机大厅 | GamesView 街机风 class/结构探针 |
| P6 | 答对节奏 | streak SFX 或音高递进接线（两 App 各 ≥1） |

## 3. 记录

合并后更新 `.agent_workspace/acceptance-log-round5b.md`。
