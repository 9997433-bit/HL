# Round 18 验收标准 · 密度收口 + 拆包性能 + 剖析对齐

> 版本：v1.0 · 简报：`ROUND18-BRIEF.md` · 探针：`npm run check:round18`（ROUND18-v1.0）

## G 总则

- **G1** 不复制洪恩 IP；OpenMoji + 程序化动画；reduced-motion / 可跳过延续 R16/R17。
- **G2** 富 Play 计数口径不变：`templateFallback≠true`、按 char 去重、narration 去重复核；
  `countRichPlays()` / `listRichPlays()` **必须继续从 `char-play.js` 导出**，
  允许返回值为同步值或 Promise（探针一律 `await`）。
- **G3** 拆包后 `apps/literacy-app/src/data/char-play.js` 仍须可被 Node 直接
  `import`（H2 是运行时口径）；懒加载 loader 用动态 `import()`（Node 原生支持）
  或 `import.meta.glob`（若用后者，注意别放进 H2 依赖的模块里让 Node 炸掉）。
- **G4** `WORD_PROBLEMS` / `buildAnalysis` / `WORD_PROBLEM_EXPLAINS` 三个导出名
  不许改（H4/H5 运行时口径挂在上面）；改名 = 探针红，自己兜着。
- **G5** `check:round17` 必须保持 8/8（H8）。干净环境先 `npm run android:sim`
  重建双 APK，否则 r17→r16→r15→r13 连锁红。
- **G6** 真机外网密钥不作硬绿；无设备须诚实 BLOCKED + 复现命令（H7）。
- **G7** 所有 `ROUND18_H*` 标记必须写在**可执行代码**里（探针剥
  HTML/块/行注释后判标），注释骗标一律不算。

## H1 差距续表

`.agent_workspace/round18-hongen-gap-audit.md`：

- 内容 >600 字符；识字、数学两侧都要有；
- 有状态标记（✅/◐/❌ 或 达标/缺口）；
- **相对洪恩 + 相对 R17** 双基线：文中须出现 R17（上轮）与 R18（本轮）
  的归属表述，只抄 R17 旧表不标本轮归属不算。

## H2 富 Play ≥1200

- 运行时口径：Node import `char-play.js`，`await countRichPlays()` ≥ **1200**；
- `await listRichPlays()` 里 `templateFallback≠true` 条目的 narration
  去重 ≥ **960**（≥80% 不撞句）；
- `apps/literacy-app/src/data` 或 `apps/literacy-app/scripts` 下存在
  剥注释后仍含 `ROUND18_H2` 的可执行文件。

## H3 富脚本按单元拆包（机读契约，防假绿）

四个断言全过才绿：

1. **可执行标记**：`apps/literacy-app/src` 下存在剥注释后含 `ROUND18_H3`
   的文件，且这些文件里出现动态加载（`import(` 或 `import.meta.glob`）
   + 词证（rich/富脚本）+ 单元词证（unit/单元）。
2. **无整包静态 import**：剥注释后扫描全 `apps/literacy-app/src`，
   不允许任何静态 `import/export … from '…/char-play-rich(.js)'`
   （specifier 以 `char-play-rich` 结尾才算整包；`char-play-rich/index.js`
   之类分片索引路径不在此列）。动态 `import('…char-play-rich…')` 不禁止，
   但见断言 4 的体量下限——单片懒加载整包不算「按单元」。
3. **分片契约**：分片文件路径必须含 `play-rich`（目录如
   `src/data/play-rich/u56.js` 或文件名如 `char-play-rich-u56.js` 均可），
   排除整包 `char-play-rich.js` 本身后，分片数 ≥ **5**。
4. **分片体量**：上述分片合计 ≥ **100KB**——防「留整包 + 摆 5 个空壳分片」
   凑数（1200 条富脚本的真实体量远超此数）。

H2 的运行时计数同时兜底：分片里的内容必须真的能被注册表数出来。

## H4 剖析步数对齐 ≥90%

- 运行时口径：`reseed(20260828)` 后，对 `WORD_PROBLEMS` **全量**逐母题
  连抽 2 个实例，每个实例都满足
  `buildAnalysis(make()).steps.length === 母题.steps` 才算该母题对齐；
- 对齐母题数 / 总母题数 ≥ **90%**；
- **题库防缩水**：`WORD_PROBLEMS.length ≥ 200`（当前 214；把不一致的
  56 题删掉凑比例 = 直接红）；
- `apps/math-app/src` 下存在剥注释后含 `ROUND18_H4` 的可执行文件。

## H5 精品剖析 ≥80

- 运行时口径：`WORD_PROBLEM_EXPLAINS` 里「`steps` 为非空数组且每步都是
  函数」的条目按 id 去重 ≥ **80**（空壳 `steps: []` / 非函数步不计）；
- 静态口径：剥注释后含 `ROUND18_H5` 的文件（可与 `ROUND17_H4` 同文件续写）
  内，按引号切分的去重中文讲解句（≥10 字符且 ≥8 个汉字）≥ **200**；
- 两口径同时满足 + 标记存在才绿。

## H6 走查证据包

`.agent_workspace/evidence/r18/walkthrough.md`：

- 文档 >400 字符；
- 引用的 `evidence/r18/*.png|jpg|webp|gif|mp4|webm` 中至少 **4 个**
  真实落盘于 `.agent_workspace/` 下且每个 ≥ **200 字节**（只列路径不算）；
- 四类场景词齐：富玩（富玩/富脚本/rich）、拆包（拆包/懒加载/分片/chunk）、
  剖析对齐（剖析/对齐/analysis）、周报或学伴（周报/weekly/学伴/mascot）。

## H7 真机或模拟台账

必须是 **r18 自己的**台账，二选一：

- `evidence/r18/android-sim-report.md`（>200 字符，可引用重跑的
  report.json，须含 android:sim/APK/模拟 + sha256/report.json/exit 词证）；
- `evidence/r18/device-blocked.md`（>200 字符，含 `BLOCKED` + 复现 +
  `npm run android` / `android:sim` / gradle 命令）。

仅继承 r13/r17 旧报告冒充本轮不算。

## H8 往轮不退化

`node scripts/check-round17.mjs --json` 须 **8/8**（v1.1）。

## 红线

- 禁止用注释骗过 `ROUND18_H*` 探针（探针剥注释后判标）。
- 禁止把模板 Play 算进 H2；禁止为 H2 生成撞句旁白
  （narration 去重 ≥960 堵死）。
- 禁止「留整包 + 空壳分片」骗 H3（分片数 ≥5 且合计 ≥100KB +
  无整包静态 import 三道锁）。
- 禁止删除步数不一致的母题凑 H4 比例（题库 ≥200 兜底）。
- 禁止空壳 `steps: []` 凑 H5 条数（运行时逐条验步骤函数 +
  去重中文句 ≥200 双锁）。
- 禁止伪造走查截图路径（H6 要求真实落盘 ≥200B）。
- 禁止用旧轮 android 报告顶替 r18 台账（H7 只认 `evidence/r18/`）。
- 回填时把探针原话粘贴到 `acceptance-log-round18.md`。
