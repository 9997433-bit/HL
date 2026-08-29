# Round 19 验收标准 · 精美度补齐 + 全库富 Play + 剖析视频级

> 版本：v1.0 · 简报：`ROUND19-BRIEF.md` · 探针：`npm run check:round19`（ROUND19-v1.0）

## G 总则

- **G1** 不复制洪恩 IP；OpenMoji + 程序化动效；reduced-motion / 可跳过延续 R16–R18。
- **G2** 富 Play 计数口径不变：`templateFallback≠true`、按 char 去重、narration 去重复核；
  `countRichPlays()` / `listRichPlays()` / `loadAllRichPlays()` **必须继续从
  `char-play.js` 导出**，允许同步值或 Promise（探针一律 `await`）。
- **G3** 分片管线不破：全库富 Play 仍按单元懒加载；禁止为凑 H2 把剧本重新打成
  整包静态 import（H2 要求 `loadAllRichPlays` 仍可调用）。
- **G4** `WORD_PROBLEMS` / `buildAnalysis` / `WORD_PROBLEM_EXPLAINS` 三个导出名
  不许改（H5 运行时口径挂在上面）；H4 播放器吃手写 explain 步文案，扩写时
  保持 steps 与 `buildAnalysis` 步数对齐（R18 红线）。
- **G5** `check:round18` 必须保持 8/8（H8）。干净环境先 `npm run android:sim`
  重建双 APK，否则 r18→r17→…→r13 连锁红。
- **G6** 真机外网密钥不作硬绿；无设备须诚实 BLOCKED + 复现命令（H7）。
- **G7** 所有 `ROUND19_H*` 标记必须写在**可执行代码**里（探针剥
  HTML/块/行注释后判标），注释骗标一律不算。

## H1 差距续表

`.agent_workspace/round19-hongen-gap-audit.md`：

- 内容 >600 字符；识字、数学两侧都要有；
- 有状态标记（✅/◐/❌ 或 达标/缺口）；
- **相对洪恩 + 相对 R18** 双基线：文中须出现 R18（上轮）与 R19（本轮）
  的归属表述，只抄 R18 旧表不标本轮归属不算。

## H2 全库富 Play ≥1820

- 运行时口径：Node import `char-play.js`，先 `await loadAllRichPlays()`（若存在），
  再 `await countRichPlays()` ≥ **1820**；
- `await listRichPlays()` 里 `templateFallback≠true` 条目的 narration
  去重 ≥ **1600**（消灭模板断崖后仍要求绝大多数不撞句）；
- `apps/literacy-app/src/data` 或 `apps/literacy-app/scripts` 下存在
  剥注释后仍含 `ROUND19_H2` 的可执行文件；
- **分片管线不破**：`loadAllRichPlays` 必须是可调用函数（禁止为凑数把懒加载
  入口删掉、改回整包同步塞满）。

## H3 精美度升级（CharPlayStage 或等价）

三个断言全过才绿：

1. **可执行标记**：`apps/literacy-app/src` 下存在剥注释后含 `ROUND19_H3`
   的文件（期望落在 `CharPlayStage` 或等价舞台组件/组合式）。
2. **≥3 类可感知升级词证**（在含标记的可执行代码里计，至少命中 3 类）：
   - 多拍节 / timeline：`timeline` / `多拍` / `拍节` / `beat`
   - 道具命中反馈：`命中` / `反馈` / `hitFeedback` / `propHit` / `道具`
   - 主题氛围层：`氛围` / `atmosphere` / `主题` / `themeLayer` / `ambience`
3. **reduced-motion 可跳过/降级**：同批可执行代码须含
   `reduced-motion` / `reduceMotion` / `prefers-reduced-motion` 词证，
   且出现跳过或降级语义（`skip` / `跳过` / `降级` / `fallback`）。

禁止只改 CSS 变量名、不改行为；禁止把升级词写进注释骗过探针。

## H4 剖析视频级播放器

- `apps/math-app/src` 下存在剥注释后含 `ROUND19_H4` 的可执行文件
  （期望 `WpAnalysisPanel` 或等价剖析壳）；
- **播放器词证**（含标记的可执行 blob 内须齐）：
  - 播放：`播放` / `play` / `playing`
  - 暂停：`暂停` / `pause` / `paused`
  - 进度：`进度` / `progress` / `currentTime` / `seek`
- **自动推进**：须有自动推进步骤语义（`自动` / `autoplay` / `autoAdvance` /
  `setInterval` / `requestAnimationFrame` / `gsap` / `timeline`）；
- **reduced-motion 降级为手动点步**：同批代码须含 reduced-motion 词证，
  且出现手动/点步语义（`手动` / `nextStep` / `点步` / `click` 推进）。

视频级 = 程序化讲解时间轴，不强制每题 MP4。

## H5 精品剖析 ≥150

- 运行时口径：`WORD_PROBLEM_EXPLAINS` 里「`steps` 为非空数组且每步都是
  函数」的条目按 id 去重 ≥ **150**（空壳 `steps: []` / 非函数步不计）；
- 静态口径：剥注释后含 `ROUND19_H5` 的文件（可与 R17/R18 同文件续写）
  内，按引号切分的去重中文讲解句（≥10 字符且 ≥8 个汉字）≥ **400**；
- 两口径同时满足 + 标记存在才绿。

## H6 走查证据包

`.agent_workspace/evidence/r19/walkthrough.md`：

- 文档 >400 字符；
- 引用的 `evidence/r19/*.png|jpg|webp|gif|mp4|webm` 中至少 **4 个**
  真实落盘于 `.agent_workspace/` 下且每个 ≥ **200 字节**（只列路径不算）；
- 四类场景词齐：全库富玩（富玩/富脚本/rich/全库）、精美舞台（精美/舞台/
  polish/CharPlayStage）、剖析播放器（播放器/讲解播放/timeline/剖析）、
  周报或学伴（周报/weekly/学伴/mascot）。

## H7 真机或模拟台账

必须是 **r19 自己的**台账，二选一：

- `evidence/r19/android-sim-report.md`（>200 字符，可引用重跑的
  report.json，须含 android:sim/APK/模拟 + sha256/report.json/exit 词证）；
- `evidence/r19/device-blocked.md`（>200 字符，含 `BLOCKED` + 复现 +
  `npm run android` / `android:sim` / gradle 命令）。

仅继承 r13/r17/r18 旧报告冒充本轮不算。

## H8 往轮不退化

`node scripts/check-round18.mjs --json` 须 **8/8**（ROUND18-v1.0）。

## 红线

- 禁止用注释骗过 `ROUND19_H*` 探针（探针剥注释后判标）。
- 禁止把模板 Play 算进 H2；禁止为 H2 生成撞句旁白
  （narration 去重 ≥1600 堵死）；禁止删掉 `loadAllRichPlays` 假绿。
- 禁止 H3 只贴空壳标记、无三类升级词证或无 reduced-motion 降级。
- 禁止 H4 只写「播放器」文案、无播/暂停/进度与自动推进词证。
- 禁止空壳 `steps: []` 凑 H5 条数（运行时逐条验步骤函数 +
  去重中文句 ≥400 双锁）。
- 禁止伪造走查截图路径（H6 要求真实落盘 ≥200B）；只认 `evidence/r19/`。
- 禁止用旧轮 android 报告顶替 r19 台账（H7 只认 `evidence/r19/`）。
- 回填时把探针原话粘贴到 `acceptance-log-round19.md`。
