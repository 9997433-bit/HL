Model slug: claude-fable-5
# Round 10 验收标准 · 洪恩深度对标与发布终态

> 版本：Round 10 v1.1（2026-08-27，随探针修订同步）
> 依据：`.agent_workspace/ROUND10-BRIEF.md` + `round9-hongen-audit.md` §5 R10 归属备忘
> 配套：`.agent_workspace/acceptance-log-round10.md`（实测回填模板）、`scripts/check-round10.mjs`（H1–H8 机读探针，固定 8 个结果，`--json` 供编排器聚合）
> 判定原则：每条都能被脚本或 10 分钟内的手动步骤验证；**写进简报不跑脚本视为未交付**（主计划原则 4）。

## 0. 轮次门禁 G1–G6（顺序执行，全过才可出包）

| # | 门禁 | 验证方式 | PASS 标准 |
|---|---|---|---|
| G1 | 全量单测回归 | `npm test` | 全绿（识字 `test:srs`+`test:speech`+`test:ocr`+`check:data`+build+`check:bundle`+smoke；数学 `check:content`+build+smoke；feedback 单测；H4 交付后含投稿校验） |
| G2 | Round 10 硬门槛 | `npm run check:round10` | 退出码 0（**8/8**，见 §1；基线 `d89c455` + 探针 v1.1 为 **1/8 有意红灯**，见 §4.1） |
| G3 | Round 9 不退化 | `npm run check:round9` | 退出码 0（**8/8**，H8 同口径兜底）；抽查 `check:round8` 8/8、`check:round7` 8/8 |
| G4 | Round 3 全链回归 | `npm run test:round3` | 全绿（含离线 smoke + acceptance）；axe critical/serious = 0 |
| G5 | 出包 + Android | `npm run build:all` + `npm run sync:android` + `npm run check:android` | zip 产出 + `check:android` **26/26** |
| G6 | Lighthouse 双档终验 | `node scripts/lighthouse-ci.mjs`（mobile 档，R9 版本锁）+ desktop 档（H6 交付） | 双 App mobile **P ≥ 95**、A/BP ≥ 90；desktop 档三项分数落 log §2.1；原始 JSON 入 `evidence/r10/` |

---

## 1. 八项硬门槛（H1–H8，固定 8 个结果）

`npm run check:round10` 逐项断言，任一 FAIL 即退出码 1。**固定输出 8 个结果**，结果数 ≠ 8 时门禁自身 FAIL——防止探针被静默削减。`--json` 输出机读汇总（`passed`/`failed`/`results[].id/status/msg`）。模块不可读取、空文件占位、引用不落盘的资产、只在注释里写标记，一律 FAIL，不设 PENDING 放行。

| ID | 交付物 | PASS 标准 | 验证方式 | 责任分支 |
|---|---|---|---|---|
| H1 | 跟读 v3 | 语音相关源码（剥注释）含 **Worker 构造/引入信号**（`new Worker(`/`?worker`/字面 `ROUND10_H1`）+ **离线 ASR 信号**（`sherpa`/`offline-asr`/`离线 ASR`）+ smoke 标记 `ROUND10_H1_SMOKE` | 探针 §2.1 + 走查 W1 | r10-literacy-followread-v3 |
| H2 | OCR 真样张 | `real/photo/capture/实拍` 命名**有效 PNG ≥ 2**（魔数 + ≥4KB）+ 精度脚本内 real tier 信号 + `ROUND10_H2` | 探针 §2.2 + 走查 W2 | r10-literacy-ocr-real |
| H3 | 推荐闭环 | **R10 专属开练入口信号**（基线为 false，见 §2.3）+ **同文件跨域接线**（视图含 daily/错题信号 或 daily.js 含推荐信号）+ smoke 标记 `ROUND10_H3_SMOKE` | 探针 §2.3 + 走查 W3 | r10-math-reco-daily |
| H4 | 投稿 CI | `scripts/import-book-submission.mjs` **实体**（剥注释含 ajv + validate/compile + 退出断言）+ **挂进 test/check 链**（package.json scripts 或 `test-literacy.sh` 引用脚本名） | 探针 §2.4 + 走查 W5 | r10-book-import-ci |
| H5 | 儿歌旋律 | `SONGS` 合规条目（R9 口径：对象 + id 非空不重复 + title/name）中 **≥ 3 首**挂音频引用且 **public 下资产真实存在、≥ 10KB、去重后 ≥ 3 个文件** + `ROUND10_H5` | 探针 §2.5 + 走查 W4 | r10-literacy-songs-melody |
| H6 | 双档 Perf | `evidence/r10/` 含 desktop 命名 **可解析 JSON ≥ 1**（>200B + desktop/formFactor 信号）+ 真机清单**全量回填**（`[待填…]` 全文为 0，勾选/SKIP ≥ 8） | 探针 §2.6 + G6 | r10-perf-device-desktop |
| H7 | 发布就绪 | 根 `LICENSE` **实体**（>200 字符 + MIT + Copyright）+ 隐私**路由与视图文件**齐备 + **三包版本 1.0.0 统一**（根 + 识字 + 数学） | 探针 §2.7 + 走查 W6 | r10-global-release |
| H8 | R9 不退化 | `check:round9` 退出码 0 且输出 **8/8**（链式兜底 R8/R7…） | 探针 §2.8 | 全部分支合并前 |

## 2. 探针细则（机读接线契约，逐项与 `check-round10.mjs` v1.1 对齐）

探针分两类：**数据探针**经 `scripts/alias-loader.mjs` 直接 `import` 应用数据模块（顶部 `register('./alias-loader.mjs', …)` 不可删）；**接线探针**为纯静态分析（fs + 正则，**剥注释后**匹配，无 node_modules 可跑）。剥注释规则：HTML `<!-- -->`、块 `/* */`、整行 `//` 全剥——**信号必须写成代码**（常量、断言名或行内尾注），单独一行 `// ROUND10_XX` 会被剥掉导致 FAIL。责任分支按下列路径/命名接线即绿；如需改约定，必须在同一 PR 内同步探针与本节，否则视为未交付。

> **v1.1 探针修订记录**（相对 `d89c455` 首版 v1.0 堵掉的漏洞，全部经基线实测取证）：
> 1. **H3 跨文件拼接恒真**（R9 v1.0 同款事故复发）：v1.0 把 `daily.js` + `SkillGraphView.vue` + `skill-graph.js` **拼接后**匹配 `/recommend|推荐/ && /daily|wrongBook|错题|日冒险/`——`recommend` 由 R9 交付的 `recommendPath()` 提供、`daily` 由 `daily.js` 自身提供，基线实测 **`wired=true`**，闭环本体可以完全不交，加一行 smoke 标记即绿。现要求三重信号：R10 专属开练入口（`ROUND10_H3`/`一键开练`/`startRecommended`/`recommendToDaily`/`practiceFromReco`，基线全 false；注意裸 `开练` 基线已存在于「可开练」标签，不算数）+ **同一文件内**跨域接线（`SkillGraphView.vue` 自身出现 daily/wrongBook/错题/日冒险，或 `daily.js` 自身出现 recommend/推荐——基线两者均 false）+ smoke。
> 2. **H2 无有效性校验、tier 未接线**：v1.0 只数文件名——0 字节文件、改扩展名占位命名 `real-*.png` 即过（倒退回 R9 H2 v1.1 已堵过的洞）；且只查 `ROUND10_H2` 标记，不要求 real tier 真正接进 `test-ocr-accuracy.mjs`（光放图不跑不算）。现逐张校验 PNG 魔数 + **≥ 4KB**（真实拍摄样张的下限，占位图拦截），并要求脚本剥注释后含 `real|真实|实拍` tier 信号 + `ROUND10_H2`。
> 3. **H4 裸 `exists` + ajv 或关系**：v1.0 `exists()` 即算 script 交付——**空文件占位即过**（负向抽查已实测拦截，见 §4.1）；`/import-book-submission|ajv/` 对 package.json **任一**命中即算挂链——只往 devDependencies 加个 `ajv` 依赖、脚本不存在也能过一半。现要求脚本剥注释后同时含 `ajv` + `validate|compile` + `process.exit|assert`（校验逻辑与退出断言本体），且根/识字 package.json 的 **scripts 值**或 `scripts/test-literacy.sh` 引用 `import-book-submission`（真正进 test/check 链）。
> 4. **H5 音频引用不落盘校验**：v1.0 只看 `SONGS` 条目字段字符串**长得像**音频路径（`/\.(mp3|ogg|wav)/`）——`audio: '/x.mp3'` 而文件根本不存在也算 1 首；且不去重、不校验条目合规，3 条重复 id 引用同一个不存在的文件即过。现沿 R9 H1 合规口径过滤条目（对象 + id 非空不重复 + title/name），把引用解析到 `apps/literacy-app/public/` 下，**文件必须存在且 ≥ 10KB**，按去重后的资产文件数 ≥ 3 计。
> 5. **H6 空 JSON 即算 + 清单只扫前 2000 字符**：v1.0 desktop 证据只看文件名——空文件、写个 `{}` 也算 1 份；清单校验 `!/\[待填\]/.test(checklist.slice(0, 2000))`——基线 16 个精确 `[待填]` 中 **2 个在 2000 字符之后**（只填前两屏即可骗过），另有 2 个 `[待填，建议 …]` 变体**完全匹配不到**。现 desktop JSON 须可解析 + >200B + `desktop|formFactor` 信号；清单**全文**匹配 `\[待填[^\]]*\]`（含变体）须为 0（无法执行的项写 `[SKIP] 理由`，不许留待填），且 `[x]` 勾选 + `[SKIP]` 合计 ≥ 8（证明走查实际执行过，基线 0）。
> 6. **H7 空 LICENSE 即过、数学版本不查、隐私无视图**：v1.0 `exists('LICENSE')` 裸判——`touch LICENSE` 即过，简报明确要 **MIT**；版本只查根 + 识字（基线 root 已是 1.0.0、识字/数学都是 0.1.0——数学可以永远留在 0.1.0 也过「版本统一」）；隐私只查路由文件里出现字样，无视图文件也过。现 LICENSE 须 >200 字符 + `MIT` + `Copyright`；隐私须路由信号（剥注释）**加** `views/` 下存在 `*privacy*` 命名视图文件；版本须**根 + 识字 + 数学三包全为 `1.0.0`**。
> 7. **H1 单关键字 `Worker` 即过 + 探针盲区**：v1.0 `/Worker|sherpa|offline.*ASR|ROUND10_H1/i` 任一命中即算接线——写个 `workerReady` 变量名、或 `navigator.serviceWorker` 引用就绿，且只扫两个固定文件（Worker 接线若落在新文件 `src/workers/asr.worker.js` 反而探不到）。现扫描 `composables/`、`utils/`、`workers/` 下全部 `speech|asr|follow|sherpa|worker` 命名文件，要求 **Worker 构造/引入信号**（`new Worker(`/vite `?worker`/字面 `ROUND10_H1`）**与**离线 ASR 信号（`sherpa`/`offline-asr`/`离线 ASR`）同时命中；smoke 收紧为必须 `ROUND10_H1_SMOKE`（v1.0 的 `ROUND10_H1(_SMOKE)?` 允许 smoke 里不写 _SMOKE 后缀）。
> 8. **健壮性**：v1.0 的 H7 `JSON.parse(read(...) || '{}')` 在 package.json 存在但损坏时直接抛异常炸掉整个门禁（虽 fail-closed 但破坏「固定 8 结果」承诺）；现所有 package.json 读取走 try/catch 的 `pkgVersion()`/`pkgScripts()`。固定 8 结果自检与 `--json` v1.0 已具备，保持不动。

### 2.1 H1 跟读 v3 离线 ASR Worker（接线探针）

- **扫描池**：`apps/literacy-app/src/composables/`、`src/utils/`、`src/workers/`（如存在）下所有文件名含 `speech|asr|follow|sherpa|worker` 的文件，剥注释后拼接匹配。
- **Worker 信号**：`new Worker(`、vite 风格 `?worker` 引入、或字面 `ROUND10_H1`（若另起文件/命名，用它显式声明入口，同 R9 H3 约定）。
- **离线信号**：`sherpa`、`offline-asr`（容忍空格/下划线/连字符）、`离线 ASR` 或字面 `ROUND10_H1`。sherpa-onnx spike 模型必须本地资产、禁 CDN（§6 红线）。
- **smoke**：识字 `scripts/smoke.mjs` 剥注释后含字面 **`ROUND10_H1_SMOKE`**。
- **三档降级不退化**（在线识别 → 本地评分 → 仅跟读）与隐私提示由 R6/R7 存量探针经 H8 链兜底；Worker 不可用时必须无缝落回 v2 评分路径（走查 W1）。

### 2.2 H2 OCR 真实样张 tier（文件探针 + 接线探针）

- **样张**：`apps/literacy-app/scripts/fixtures/ocr/` 下文件名含 `real|photo|capture|实拍` 且 `.png` 的，逐张校验 PNG 魔数（`89 50 4E 47 …`）+ **≥ 4096 字节**，有效数 **≥ 2**。命名建议 `real-*.png`（如 `real-photo-book.png`）。「真实拍摄」的实质（非程序合成）探针无法静态证明，由走查 W2 复核 + WebView 实测记录回填 log §2.2。
- **脚本接线**：`test-ocr-accuracy.mjs` 剥注释后含 `real|真实|实拍`（tier 真正接进基准集）+ 字面 **`ROUND10_H2`**。真样张 tier 允许独立阈值（低于合成图基准），量化结果回填 log §2.2。
- **不退化**：R9 H2 的 8 张有效 PNG + handwriting tier + `ROUND9_H2` 由 H8 链兜底，扩样不得删旧图旧断言。

### 2.3 H3 推荐 × 日冒险/错题本闭环（接线探针）

- **入口信号**：`apps/math-app/src/data/` 下 `skill*.js`/`daily*.js` + `modules/skill-graph/` 全部文件，剥注释后匹配 `/\bROUND10_H3\b|一键开练|startRecommended|recommendToDaily|practiceFromReco/i`。推荐命名 `startRecommendedPractice()`：从推荐路径首项一键生成/跳转当日练习或对应错题集。裸 `开练` 不算（基线「可开练」标签恒真）。
- **跨域接线（同文件内）**：`SkillGraphView.vue` 剥注释后自身含 `/daily|wrongBook|错题|日冒险/i`（跳转目标真的渲染在图谱视图里），**或** `daily.js` 剥注释后自身含 `/recommend|推荐/`（日冒险消费推荐结果）。二者基线均 false，任一即为 R10 净增量。
- **smoke**：数学（或识字）`scripts/smoke.mjs` 剥注释后含字面 **`ROUND10_H3_SMOKE`**（建议数学侧：进图谱 → 点推荐项 → 断言落在日冒险/错题本路由）。
- **写回边界**：R9「推荐只读」红线在 R10 放宽为**仅经用户显式点击**产生练习记录——自动写回 FSRS/解锁状态仍然禁止（走查 W3 验证）。

### 2.4 H4 绘本投稿 import + ajv CI（接线探针）

- **脚本实体**：`scripts/import-book-submission.mjs` 存在且剥注释后**同时**含 `ajv`（校验器）、`validate|compile`（校验调用）、`process.exit|assert`（不合规非零退出）。功能对齐 R9 `BOOK-COMMUNITY-SUBMISSION.md` 的 schema：读投稿 JSON → ajv 按 schema 校验 → 字表约束复核 → 通过则落 `books` 数据、拒绝则非零退出并给出逐条错误。
- **挂链**：根或识字 `package.json` 的 **scripts 值**、或 `scripts/test-literacy.sh` 中出现 `import-book-submission`（建议 `check:book-submission` 脚本并挂进 `test:literacy` 链，G1 兜底）。
- ajv 依赖走 devDependencies 本地安装，禁运行时 CDN。

### 2.5 H5 儿歌真实旋律资产（数据探针 + 文件探针）

- **曲目口径**：探针 `import` `apps/literacy-app/src/data/songs.js`，按 R9 合规口径过滤（对象 + `id` 非空不重复 + `title`/`name`）；取 `audio || src || melodyUrl` 字符串，须以 `.mp3/.ogg/.wav/.m4a` 结尾（可带 `?#` 后缀）。
- **资产落盘**：引用解析到 `apps/literacy-app/public/`（去掉前导 `/`），文件必须**存在且 ≥ 10240 字节**；按**去重后的资产文件**计数 ≥ 3（3 条目引用同一文件只算 1）。建议路径 `public/audio/songs/*.mp3`，开源来源与许可证写进 log §2.4 与 LICENSE 第三方声明。
- **标记**：`songs.js`（剥注释）或识字 smoke 含字面 **`ROUND10_H5`**。
- **不退化**：合成旋律路线（`playMelody()`）是无音频曲目的降级路径，不得删除；`verifySongCoverage()` 字表红线由 `check:data`/G1 兜底。音频资产懒加载，不进 SW 预缓存首屏（§6）。

### 2.6 H6 双档 Perf + 真机清单（文件探针）

- **desktop 证据**：`.agent_workspace/evidence/r10/` 递归统计文件名含 `desktop` 的 `.json`：可解析 + **>200 字节** + 内容含 `desktop|formFactor` 信号，≥ 1 份（建议 `lighthouse-literacy-desktop.json`/`lighthouse-math-desktop.json` 双份；mobile 档沿 R9 版本锁口径一并归档）。
- **真机清单**：`.agent_workspace/ANDROID-DEVICE-CHECKLIST.md` >500 字符、全文 `\[待填[^\]]*\]` **为 0**（基线 18 处含 2 处「[待填，建议 …]」变体；确实无法执行的项写 `[SKIP] 理由`），且 `[x]` + `[SKIP]` 合计 **≥ 8**。
- 双档阈值：mobile 沿 G6（P ≥ 95）；desktop 档首轮记录实测、不设硬阈值，分数落 log §2.1，异常回归单独立项。

### 2.7 H7 发布就绪（文件探针 + 接线探针）

- **LICENSE**：仓库根 `LICENSE` >200 字符 + 字面 `MIT` + `Copyright`（大小写不敏感）。第三方声明（OpenMoji CC BY-SA、Tesseract Apache-2.0、字体、旋律来源等）逐个核对（走查 W6）。
- **隐私页**：识字 `src/router/index.js` 剥注释后含 `privacy|隐私`，**且** `src/views/` 下存在文件名含 `privacy` 的视图（建议 `PrivacyView.vue`，`/privacy` 路由）。数学侧隐私入口走走查 W6，不硬锁。
- **版本统一**：根、`apps/literacy-app`、`apps/math-app` 三个 `package.json` 的 `version` 全为 **`1.0.0`**。
- Android `versionName` 与 zip 产物版本对齐走走查 W6 + `check:android` 兜底。

### 2.8 H8 Round 9 不退化（子进程探针）

- 探针以子进程跑 `scripts/check-round9.mjs`：退出码 0 **且**输出含 `8/8`。R9 八结果再链式兜底 R8/R7 及更早；R10 任何分支合并如碰坏其一，此处红灯。R6 及更早由 G3 在集成分支抽查兜底。

## 3. smoke 断言建议（新面必须进浏览器 smoke，随责任分支同 PR 交付）

标记写法同 R9：探针剥整行 `//` 注释——标记要写成常量/断言名或**行内尾注**（如 `await interact(...) // ROUND10_H1_SMOKE`），单独一行注释会被剥掉导致 FAIL。Round 10 增量：

- **H1 跟读 v3**：识字 smoke 增断言：跟读页在 Worker 可用/不可用两态下均无 pageerror，降级链路可见，旁注 `ROUND10_H1_SMOKE`。
- **H3 推荐闭环**：数学 smoke 增交互断言：`/skill-map` 推荐项点击 → 落日冒险或错题本路由 → 返回不丢图谱状态，旁注 `ROUND10_H3_SMOKE`。
- **H2/H4**：`test-ocr-accuracy.mjs` 与 `import-book-submission.mjs` 独立跑（不进浏览器 smoke），挂 `npm test` 链由 G1 兜底。
- **H5 儿歌**：现有唱播断言不变；新增真实音频曲目进页可播（或降级到合成旋律）不报错，标记 `ROUND10_H5` 可落 songs.js 常量。

## 4. 基线与预验证

### 4.1 基线红灯记录（有意红灯）+ 绿灯路径预验证

基线 `cursor/openmoji-integration-9f67` @ `d89c455`（R9 闭合、R10 未合并），v1.1 探针实测：

```
  ✓ H8 Round 9 门禁 8/8 无退化

  ✗ H1 跟读 v3 未闭环：worker=false，offline=false，smoke=false —— r10-literacy-followread-v3
  ✗ H2 OCR 真样张未闭环：有效 real 图=0/2，脚本 tier=false，ROUND10_H2=false —— r10-literacy-ocr-real
  ✗ H3 推荐闭环未接线：entry=false，crossWired=false，smoke=false —— r10-math-reco-daily
  ✗ H4 投稿 CI 未闭环：script=false，chain=false —— r10-book-import-ci
  ✗ H5 儿歌旋律未闭环：有效音频=0/3，ROUND10_H5=false —— r10-literacy-songs-melody
  ✗ H6 双档 Perf 未闭环：desktop=0/1，checklist=false（待填 18 处，勾选/SKIP 0/8） —— r10-perf-device-desktop
  ✗ H7 发布未就绪：LICENSE=false，route=false，view=false，ver=false —— r10-global-release

Round 10 深度门禁：1/8 项通过，7 项失败。 → 退出码 1
```

1/8 属**有意红灯**：探针先行、交付点绿（继承 Round 4–9 原则）。`--json` 实测 `passed=1 failed=7 results=8`。

**绿灯路径预验证（8/8 全路径）**：在验收分支工作区以最小伪造交付物模拟集成——speechEval 加 `new Worker(...)` + sherpa 常量 + smoke 标记（H1）、复制 2 张 ≥4KB 真 PNG 命名 `real-*` + 脚本 tier/标记（H2）、视图加 `ROUND10_H3` 开练跳转常量 + 数学 smoke 标记（H3）、含 ajv/validate/exit 的 import 脚本 + `check:book-submission` 挂链（H4）、3 份 ≥10KB 音频落 `public/audio/songs/` + songs.js 挂接 + 标记（H5）、desktop LH JSON + 清单全量回填（H6）、MIT LICENSE + 隐私路由/视图 + 三包版本 1.0.0（H7）——实测 **8/8 → 退出码 0**，且 H8 子进程 `check:round9` 在伪造物叠加下仍 8/8（无 R9 预验证那种「删行碰红旧门禁」的连带）。随后**负向抽查**：把 import 脚本清空、把一张 real 图截为 0 字节，实测 H4 `script=false`、H2 `有效 real 图=1/2` 双双红灯——v1.0 的两个「占位即过」洞确认已堵。伪造物全部回滚不入库。

### 4.2 Lighthouse 双档 / 体积（集成后回填到 acceptance-log §2.1 / §2.3）

跑法：mobile 档 `node scripts/lighthouse-ci.mjs`（R9 版本锁 12.8.2 + 阈值断言）；desktop 档按 H6 交付跑法；原始 JSON 拷入 `.agent_workspace/evidence/r10/`。R9 终态双 App mobile 98/100/100——R10 新增内容（ASR Worker、真样张、音频资产）不得把任一 App mobile 档拖回 95 以下。

| 指标 | 预算/基线 | 集成实测 | 判定 |
|---|---|---|---|
| mobile 识字 P / A / BP | ≥ 95 / ≥ 90 / ≥ 90（R9：98/100/100） | log §2.1 | `[P/F]` |
| mobile 数学 P / A / BP | ≥ 95 / ≥ 90 / ≥ 90（R9：98/100/100） | log §2.1 | `[P/F]` |
| desktop 识字 / 数学 P | 首轮记录，无硬阈值 | log §2.1 | 记录 |
| 识字首屏 JS gzip | < 420 KB（`check:bundle`） | log §2.3 | `[P/F]` |
| 数学首屏 JS gzip | < 250 KB（`check:bundle`） | log §2.3 | `[P/F]` |
| zip 体积 | R9 值见 `acceptance-log-round9.md` §2.3 | log §2.3（Δ 注明来源，音频资产单列） | 记录 |

## 5. 手动走查（探针盲区，合并前 10 分钟过一遍）

| # | 走查项 | 期望 |
|---|---|---|
| W1 | 跟读 v3 | Worker 可用：离线 ASR 出结果、延迟可接受；Worker 不可用/拒麦克风：无缝落回 v2 三档降级，无 pageerror；模型资产本地、断网可用 |
| W2 | OCR 真样张复核 | `real-*` 样张确为真实拍摄（非程序合成）；跑精度脚本看 real tier 量化数字过自设阈值；WebView 实测记录已回填 log §2.2 |
| W3 | 推荐闭环可信 | 图谱推荐项一键开练落到正确的日冒险/错题集；仅用户点击产生练习记录，无自动写回 FSRS/解锁；键盘可达 |
| W4 | 儿歌旋律观感 | 新音频曲目可进可播可退、音画同步；无音频曲目仍走合成旋律降级；资产来源与许可证已记录 |
| W5 | 投稿链演练 | 照 R9 文档写一本最小合规绘本 JSON 跑 import 脚本：通过能落库；故意放字表外字/缺字段，脚本非零退出且报错可读 |
| W6 | 发布走查 | LICENSE 与第三方声明和实际依赖一致（含新旋律资产）；隐私页内容与数据实践相符（本地存储、无上传）；数学侧隐私入口；Android versionName 对齐 1.0.0 |

## 6. 不回归红线（继承 Round 3–9，抽查即可）

- `check:round9` 8/8（H8 硬门槛）、`check:round8` 8/8、`check:round7` 8/8；更早轮次 G3 抽查
- 首屏 JS gzip 识字 < 420 KB、数学 < 250 KB（`check:bundle`）；ASR 模型、真样张、音频资产一律懒加载，不进 SW 预缓存首屏
- axe critical = 0 且 serious = 0（双 App 全路由 + 交互态 + 四主题，`npm run test:a11y`）
- 断网冷启动完成学习闭环（`npm run test:offline`）；`/privacy` 新路由离线可达
- 运行时零第三方域名请求：sherpa 模型本地资产、LH 本地跑、禁 CDN/远端 PSI
- FSRS、解锁规则、母题阈值不动；推荐闭环仅经用户显式点击写练习记录；家长面板、每日冒险、吉祥物陪跑不缺席
- Android 同步不缺席：`npm run sync:android` 后 `check:android` 26/26
- worktree 开发（`.agent_workspace/r10-*` 或 `/tmp/wt-r10-*`），禁止在共享 `/workspace` 切功能分支

## 7. 回填要求

每条 H1–H8 在 `acceptance-log-round10.md` 对应小节必须有**实测数据或命令输出**（计数、日志粘贴、走查勾选），§1 表格写明「要回填什么」。集成回填必须带：集成 SHA、`check:round10` 全文输出（8/8）、双档 Lighthouse 分数与 LH 版本号、OCR real tier 精度、音频资产清单（文件、大小、来源、许可证）、zip/bundle 体积表、走查勾选。禁止「应该可以」「理论上通过」。未达标项一律进 log §3 未达标表并写明责任分支与计划，不得静默遗漏。
