> Model slug: claude-fable-5（Round 10 子代理 #1 · `cursor/r10-arch-contracts-9f67`）

# Round 10 · 洪恩深度对标与发布终态架构契约

> 基线：`cursor/openmoji-integration-9f67` @ `d89c455`（Round 9 闭合：`check:round9` **8/8**、
> 31/31 模块对标满盘；`check:round10` 基线 **1/8**——仅 H8 绿，本文撰写时实跑复核）。
> 性质：**只定数据契约与 API 边界，不含实现**。功能由子代理 #4–#10 按本契约落地，
> #3/#2 按第 9 节的门禁映射验收与审计。
> 关联：`ROUND10-BRIEF.md`、`scripts/check-round10.mjs`、`round9-architecture.md`、
> `round9-hongen-audit.md` §5「R10 归属备忘」（10 条全部在本文有落点，对账见 §11）。

基线八探针逐项水位（撰写时在 `d89c455` 实测 `node scripts/check-round10.mjs`）：

| 探针 | 基线状态 | 缺口 |
|---|---|---|
| H1 跟读 v3 | ✗ worker=false，smoke=false | ASR Worker 接线（含 `ROUND10_H1` 代码级标记）+ smoke |
| H2 OCR 真样张 | ✗ real=0/2，marker=false | ≥2 张 `real-*` 命名真实样张 + `ROUND10_H2` tier 化 |
| H3 推荐闭环 | ✗ wired=**true**，smoke=false | 闭环功能 + `ROUND10_H3_SMOKE` 行为断言（见下） |
| H4 投稿 CI | ✗ script=false，ajv=false | `import-book-submission.mjs` + ajv 挂链 |
| H5 儿歌旋律 | ✗ audio=0/3，marker=false | ≥3 首真实音频资产 + `ROUND10_H5` 双落点 |
| H6 双档 Perf | ✗ desktop=0/1，checklist=false | 桌面档 LH JSON 落 `evidence/r10/` 顶层 + 清单回填 |
| H7 发布就绪 | ✗ LICENSE=false，privacy=false，ver=false | 根 LICENSE + `/privacy` 路由 + 双 App 版本 1.0.0 |
| H8 R9 不退化 | ✓ check:round9 8/8 | 每分支合并前保持 |

三个基线已亮/半亮的格子，交付者别重做、别做歪：

- **H3 的 `wired` 半条件在基线恒真**：探针把 `daily.js + SkillGraphView.vue + skill-graph.js`
  三文件拼接后测 `/recommend|推荐/ && /daily|wrongBook|错题|日冒险/i`——`daily.js` 源码里
  天然有 `daily` 字样，第二个正则**空转命中**。所以 H3 的真门槛只有
  `ROUND10_H3_SMOKE`：#6 必须按 §3 交付**行为级闭环**并让 smoke 断言它，
  #3 在 v1.1 应堵掉这个恒真洞（§0.1 加严清单第 1 条）；
- **H7 的版本条件已对一半**：根 `package.json` 已是 `1.0.0`，缺口是
  `apps/literacy-app` 的 `0.1.0`（探针只查识字侧；数学同为 0.1.0，按 §7.3 一并统一）；
- **R9 审计 §5-2 的跟读隐私文案已在基线修复**：`FollowReadView.vue` 首屏文案现为
  「录音回放和离线评测不上传；浏览器逐字识别可能走厂商在线服务，需家长在下方
  显式打开」——R10 归属备忘 #4 **已销账**，#4 子代理不必再动这段，只须不改坏。

---

## 0. 总原则（对 Round 10 全部交付生效）

1. **探针即契约**。`scripts/check-round10.mjs` v1.0 已合入基线（`d89c455`），固定 8 项
   输出，升 v1.1 归 #3 且**只许加严**。六个易踩的匹配细节先点名（逐行读探针源码得出）：
   - **剥注释口径**：H1 对 `useSpeechEval.js`+`speechEval.js`、H2 对
     `test-ocr-accuracy.mjs`、H3 对三份源文件、H5 对 `songs.js`、H7 对识字
     `router/index.js`，以及两份 smoke，一律先 `stripComments` 再匹配——
     **所有标记词必须落在代码里**（标识符、字符串字面量或模板文本），
     写在注释里等于没写；
   - **H5 的 smoke 标记没有 `_SMOKE` 后缀豁免**：H1 探针是
     `/\bROUND10_H1(_SMOKE)?\b/`，而 H5 是 `/\bROUND10_H5\b/`——词边界后跟
     下划线不算边界，`const ROUND10_H5_SMOKE` **匹配不上**。smoke 里必须写成
     `const ROUND10_H5 = …`（H3 则相反，必须是完整的 `ROUND10_H3_SMOKE`）；
   - **H2 数图只数 `apps/literacy-app/scripts/fixtures/ocr/` 一层目录**下
     文件名命中 `/real|photo|capture/i` 的 `.png`（不递归，子目录白干）；
   - **H5 的 audio 判定**是 `await import` 后逐条测
     `String(s.audio || s.src || s.melodyUrl)` 命中 `/\.(mp3|ogg|wav|m4a)/i`——
     `songs.js` 及依赖链必须保持裸 Node 可载（§0.4），字段里写扩展名即可命中，
     但**文件必须真实存在**（v1.1 会查，见 §0.1）；
   - **H6 的桌面 JSON 只认 `.agent_workspace/evidence/r10/` 顶层**
     （`readdirSync` 不递归），文件名须含 `desktop` 且以 `.json` 结尾；
     清单判定 = 全文 >500 字符 **且前 2000 字符里零 `[待填]`**——
     `ANDROID-DEVICE-CHECKLIST.md` §1 设备表正好落在头 2000 字符内；
   - **H7 三与门**：根 `LICENSE` 存在 && 识字 router **代码**里出现
     `privacy|隐私` && `root.version === '1.0.0' && literacy.version === root.version`。
2. **v1.1 加严清单（#3 的活，功能方按加严后口径交付，不赌 v1.0 的宽松）**：
   ① H3 补 R10 专属信号（如要求 `\bROUND10_H3\b` 落在三文件之一的代码里），堵恒真洞；
   ② H5 对 `audio` 引用的文件逐一 `existsSync`（防指向不存在的 mp3）；
   ③ H2 对 `real-*.png` 补 PNG 魔数 + ≥10 KB 下限（真实照片不可能只有几 KB）；
   ④ H6 对 desktop JSON 补可解析断言（`categories.performance` 在场 +
   `configSettings.formFactor === 'desktop'`）；
   ⑤ H7 补数学 App 版本一致性与 `/privacy` 路由的 path 级断言；
   ⑥ H4 补 `--check` 自测真实可跑（spawn 退出码 0）。
   已定契约的命中面（路径、导出名、标记词、文件名）如需变更，必须回改本文档。
3. **预算红线**。识字入口 JS < 420 KB（literacy `check-bundle.mjs`）；数学首屏 gzip
   < 250 KB（math `check-bundle.mjs`，R9 已挂 test 链）；识字 zip < 10 MiB
   （基线 6,252,719 B，余量 ≈3.7 MiB）。本轮唯一的产物体积变量是 H5 音频资产——
   **总预算 ≤ 2.0 MiB**（§5.2），其余交付（ASR 引擎面、推荐 CTA、隐私页）全部在
   懒加载 chunk 域；`fixtures/`、`evidence/`、`.agent_workspace/` 不进构建产物。
   **模型红线**：任何 wasm ASR 运行时与模型文件不入库、不进 `public/`、
   不进 SW 预缓存（§1.4）。
4. **纯数据红线**。被 Node 门禁 `await import` 的文件——`songs.js`（R9 H1 + R10 H5）、
   `skill-graph.js`（R8 H3）、`daily.js`（本轮起被 R10 H3 探针读源码，且 #6 的
   check-content 新规则会 import 它）——与其依赖链禁止 Vue / 浏览器 API 顶层调用。
   `songs.js` 加 `audio` 字符串字段不引入任何 import，安全。
5. **不退化**。每个分支合并前 `npm test` 全绿 + `check:round9` **8/8**（= R10 H8，
   内含 `check:round8` 8/8、`check:round7` 8/8、`check:round6` 7/7 级联）。
   既有标记词命中面（`ROUND9_H1`/`ROUND9_H2`/`ROUND9_H3_SMOKE`/`ROUND9_H4`/
   `ROUND8_H4` 等）与格式活探针（`acceptance-log-round8.md` §2.1 斜杠三连、
   `GLOBAL-SUMMARY-REPORT` 零占位）一个不许碰坏。数值红线全数继承
   `round9-architecture.md` §0.5 与 R9 终态新水位：字库 **1820**、绘本 **132**、
   儿歌 **13**、字源 **808**、剧情 **99**、母题 **214**、`SKILL_NODES` **34**、
   OCR 基准 **10 张 8 tier**、LH mobile **双 App ≥95/90/90**、`evidence/r8`、
   `evidence/r9` 整目录只读。
6. **存储向后兼容**。识字主存档 `happy-literacy:v1` 顶层形状冻结（R8 收口的
   `songs` 字段 `{ [songId]: { sung, times } }` 不改语义，`markSongSung()` 仍是
   唯一写入口）；数学 `mathquest/*` **不新增持久化键**——H3 的「推荐→开练」是
   纯导航（§3.3），落页后由既有玩法记账路径（QuizShell / progress actions）写进度，
   图谱视图自身继续满足 R9 的 localStorage 字节级只读断言。ASR 模型缓存走
   CacheStorage 独立桶（§1.4），不碰 localStorage。
7. **并发纪律**。多个子代理共用一台 VM：不切 `/workspace` 共享树的分支，一律
   `git worktree`（`/tmp/wt-r10-<task>`）+ cherry-pick 合入；worktree 里跑门禁前
   先 `ln -s /workspace/node_modules`。**根 `package.json` 与 `package-lock.json`
   本轮只有 #7 动**（ajv 依赖 + `check:submission` 注册，§4.3）；#10 只动两个
   App 的 `package.json` version 字段，且必须**排在 #7 之后合并**并重刷 lockfile
   （npm workspaces 的 lockfile 记录子包版本，§7.3）。#9 本轮**不碰**根
   package.json（桌面档走既有 `test:lighthouse:ci` 的脚本内扩展，§6.2）。
8. **全程离线**。CI 零联网：ajv 走 lockfile `npm ci`；桌面档 LH 复用本地锁定的
   12.8.2；ASR smoke 用仓库内 mock 后端（§1.5），不下载模型；儿歌音频是仓库内
   静态资产。真机走查（H6）是唯一的「人 + 设备」环节，产出以文件回填为准。

---

## 1. 契约一 · 跟读 v3：离线 ASR Worker 接线（H1，所有者 #4）

### 1.1 探针拆解

H1 = `/Worker|sherpa|offline.*ASR|ROUND10_H1/i` 命中「`useSpeechEval.js` +
`speechEval.js` 剥注释拼接」 && `/\bROUND10_H1(_SMOKE)?\b/` 命中 literacy
`smoke.mjs` 剥注释文本。注意探针**只读这两个源文件**——Worker 本体、引擎
facade 放别的文件都可以，但 `useSpeechEval.js` 里必须有代码级的接线痕迹：
落 `const ROUND10_H1 = 'offline-asr-worker'` 常量（并真的用它，比如作为
data 属性值），别靠注释。

### 1.2 文件布局与导出面（新增，全部在识字 App 内）

```text
apps/literacy-app/src/
  utils/asrEngine.js        ← 引擎 facade（唯一被 useSpeechEval import 的新入口）
  workers/asr.worker.js     ← module worker（协议见 §1.3）
  utils/asrBackends/
    sherpa.js               ← sherpa-onnx wasm 装载器（从用户已下载的模型包启动）
    mock.js                 ← 确定性桩后端（纯 JS，入库，供 smoke/开发，§1.5）
```

`asrEngine.js` 导出面（冻结为本形状，后续轮次只许追加）：

```js
/** 引擎状态：absent 没装模型 | loading 启动中 | ready 可识别 | error 起不来 */
export const ASR_ENGINE_STATES = ['absent', 'loading', 'ready', 'error']

/**
 * ROUND10_H1 —— 离线 ASR 引擎句柄。backend: 'sherpa' | 'mock'。
 * 全程不联网：sherpa 后端只从 CacheStorage 里已有的模型包启动，
 * 缓存里没有就停在 absent，绝不静默去下载。
 */
export function createAsrEngine({ backend } = {})
// 返回：{ state /* ref */, init(), push(pcm, sampleRate), finalize(), dispose(),
//        onPartial(fn), onFinal(fn) }
```

### 1.3 Worker 消息协议（冻结）

主线程 → worker：

| type | payload | 语义 |
|---|---|---|
| `init` | `{ backend, modelSource }` | 启动引擎；sherpa 的 `modelSource` 是 CacheStorage 键，mock 忽略 |
| `push` | `{ pcm: Float32Array, sampleRate }` | 流式喂音频帧（transferable 转移所有权） |
| `finalize` | — | 收尾，触发 `final` |
| `dispose` | — | 释放 wasm 内存并终止 |

worker → 主线程：

| type | payload | 语义 |
|---|---|---|
| `ready` | `{ backend }` | init 成功 |
| `partial` | `{ text }` | 中间结果（可为空串） |
| `final` | `{ text }` | 最终转写，主线程拿去喂 `evaluate()` |
| `error` | `{ reason }` | 任何失败；主线程收到后按 §1.4 降级 |

### 1.4 能力链与隐私契约（三档不退化，新档只加不改）

- 能力链从三档升四档，**原三档 id、语义、默认值逐字不动**：

  ```
  recognition-local（新，最优先）：ASR 引擎 ready 且拿到麦克风 → 离线逐字评测
  recognition                    ：Web Speech，仍由 allowRecognition（默认 false）把关
  recording                      ：只有麦克风 → 响度分，封顶 85
  listen-only                    ：自评档
  ```

  `MODE_LABELS` 追加 `'recognition-local': '离线逐字评测'`（纯追加）；
  `useSpeechEval()` 返回面**只增不改**（追加 `asrState`、`asrSupported` 等）。
- **降级红线（评估文档 §3 的口径写进行为）**：本地引擎 init/运行失败 →
  **只降到 recording，绝不静默切到可联网的 Web Speech**；`allowRecognition`
  的语义保持「只管 Web Speech 那一档」，本地档不需要这个开关（它不联网），
  但仍需要麦克风授权这一层。
- **模型不入库**：sherpa-onnx 的 wasm 与模型文件不进 git、不进 `public/`、不进
  SW 预缓存清单。获取走**显式「下载离线识别包」UI**（跟读页家长区，写明体积与
  用途）→ 存 CacheStorage 桶 `asr-model-v1` → 可整体删除（同一 UI 提供删除）。
  默认状态 = 没下载 = `absent` = 行为与今天逐字节一致。
- `speechEval.js` 旧导出（`GRADES`…`evaluate`、`companionReplyForResult`、
  `phonemeMarks`、`similarityV2`）签名与行为冻结——本地档的转写走
  `evaluate({ mode: 'recognition', reference, heard })`，并显式传 `lookupPinyin`
  启用 v2 逐字四态标记（R9 §4.2 冻结的 hit/tone/near/miss 语义照用）；
  界面继续把 tone/near 称为「诊断线索」，不标红「错误」。

### 1.5 mock 后端与 smoke（诚实的可测性）

- `mock.js`：确定性桩——收到 `finalize` 后把 init 时注入的脚本文本原样返回
  （零随机、零网络、零 wasm），存在意义是让 CI 能走通「init → push → final →
  evaluate」全链。**界面在 mock 后端下必须显式标注「演示引擎」**，不冒充真识别。
  后端选择：`localStorage['hl-asr-backend'] = 'mock'`（仅 smoke/开发文档化使用，
  默认无此键 = sherpa 路径 = 缓存无模型即 absent）。
- 视图钩子：跟读面板落 `[data-asr-engine]`（值 = 引擎状态）与
  `[data-asr-mode]`（值 = 当前档位 id），供 smoke 与 v1.1 探针断言。
- literacy `smoke.mjs` 追加代码级常量 `const ROUND10_H1_SMOKE = '/follow-read'`
  + interact 段：种 `hl-asr-backend=mock` → 打开跟读页 → 断言
  `[data-asr-engine]` 走到 `ready`、档位显示「离线逐字评测」与「演示引擎」标注
  → 走一轮跟读拿到 `final` 驱动的逐字结果 → 清掉种子后重载，断言回到
  `absent` 且档位回落 recording/listen-only、`allowRecognition` 开关仍在且默认关。
  R6/R8/R9 既有 smoke 段一行不动。
- 体积：`asrEngine.js`/worker 只被 FollowRead 懒加载 chunk 引用，主包零增量；
  mock 后端 ≤ 2 KB。

---

## 2. 契约二 · OCR 真实拍摄样张 tier + WebView 实测（H2，所有者 #5）

### 2.1 探针拆解

H2 = `fixtures/ocr/` 一层目录下文件名命中 `/real|photo|capture/i` 的 `.png` **≥2**
&& `/\bROUND10_H2\b/` 命中 `test-ocr-accuracy.mjs` 剥注释文本。同时 R9 H2 探针
继续在跑：一层目录 PNG ≥8（逐张魔数 + ≥1 KB）、handwriting 双落点、
`ROUND8_H4|ROUND9_H2` 标记——**加图不许破坏旧探针**，新图自己也要过魔数校验。

### 2.2 样张契约（文件名锁定，来源如实）

| 文件名（锁定） | 要求 |
|---|---|
| `real-photo-01.png` | 真实相机拍摄：印刷字卡/绘本页实拍，自然光 |
| `real-photo-02.png` | 真实相机拍摄：不同光照或角度（暖光/侧光/轻微透视任选） |
| `real-photo-03.png` 起 | 可选追加，同前缀 |

- **必须是真实拍摄的照片**（自摄或 CC0/公有领域来源），裁剪、缩放、旋转、
  转 PNG 允许，**禁止**拿 `gen-ocr-benchmark.mjs` 的程序合成图改名冒充——
  这条是 R9 审计「边界如实声明”的兑现：R9 说了「认不出真人手写/实拍是已知
  边界」，R10 就要拿真图去量这条边界，量出来多低都如实定线；
- **合规**：画面零人脸、零儿童、零个人信息（地址/姓名/手机号）；来源与许可
  逐张记入 `.agent_workspace/r10-ocr-real-log.md`（新建，#5 独占）：
  文件名 · 来源（自摄设备型号 / CC0 出处链接）· 许可 · 处理链（裁剪/缩放参数）；
- 每张 `expect` 3–12 字、全部 ∈ `CHARACTER_MAP`、`keyword` ≥1 字
  （既有断言 `splitByLibrary().unknown === 0` 自动覆盖）。

### 2.3 精度脚本 tier 化（`test-ocr-accuracy.mjs`，纯追加）

- `BENCHMARK` 追加 `tier: 'real-photo'` 条目（`TIER_LABEL` 登记中文名
  「真实拍摄」——脚本有断言：没登记中文名当场红）；**既有 10 条的字节、阈值、
  keyword 一个不动**（R8/R9 两代冻结基准的延续）；
- **阈值方法论冻结**（三轮口径原文继承）：先实测、后定标，取实测值往下留一档
  写死在脚本里，禁 env 放水、之后只许上调。真实照片召回预期显著低于合成图——
  如实定低线（哪怕 0.2 起步），**禁止**为过基准调 `utils/ocr.js` 的
  `OEM.LSTM_ONLY` 与 `preprocess()` 链（基准适配引擎现状，不是反过来）；
- `OVERALL_RECALL = 0.9` 的统计范围**继续锁定 `tier === 'print'`**，real-photo
  单独设线；`REQUIRED_TIERS` 追加 `'real-photo'`（钉死，删图砍 tier 当场红）；
- 标记双落点（都是代码级）：`--json` 输出的 `marker` 升为 `'ROUND10_H2'` 并保留
  `supersedes: 'ROUND9_H2'` 链（`ROUND9_H2`/`ROUND8_H4` 字样继续在代码里在场，
  R9 H2 探针靠它们命中）；
- 实测数字回填 `.agent_workspace/acceptance-log-round9-h2.md` 时顺手校正 R9 审计
  §5-4 点名的旧账（表停在 9 张 51/51，现状 10 张 55/55）。

### 2.4 WebView 实测记录（真机执行面，文件所有权拆开）

- `.agent_workspace/r10-ocr-webview.md`（新建，**#5 独占**）：模板三列
  「预期 / 实测 / 判定」，覆盖：WebView 里 wasm 装载耗时、单图识别耗时、峰值
  内存、相机权限流（首拒/再授权/设置回跳）、real-photo 两张在真机拍摄条件下的
  召回。未执行的行判定写「未测」——**不留空、不写占位符**；
- #9 的 `ANDROID-DEVICE-CHECKLIST.md` 回填（§6.3）在 OCR 段**引用**该文件而非
  复制内容——两人不写同一文件。

---

## 3. 契约三 · 图谱推荐 × 每日冒险/错题本闭环（H3，所有者 #6）

### 3.1 探针拆解与真门槛

H3 = 三文件拼接命中双正则（**基线已恒真**，见文首）&& `/\bROUND10_H3_SMOKE\b/`
命中 math `smoke.mjs` 剥注释文本。所以本契约的验收实体是**行为**：推荐项一键
跳进可开练的页面，smoke 全程点给探针看。同时 R9 H3/R8 H3 继续在跑：
`SkillGraphView.vue` 路径锁死、`recommendPath()`/`nextSkills()` 导出在场、
localStorage 字节级只读断言——四条全不许退。建议 #6 顺手在 `SkillGraphView.vue`
代码里落 `const ROUND10_H3 = 'reco-practice-loop'` 常量，给 v1.1 加严当靶。

### 3.2 数据契约：`daily.js` 追加聚焦练习（旧导出面冻结）

既有导出 `DAILY_SIZE / DAILY_PERFECT_BONUS / dailyDateKey / dailySeed /
DAILY_TEMPLATE_IDS / buildDailyQuestion / buildDailyQuestions` 签名与行为
**逐字节不动**（`buildDailyQuestions(dateKey)` 的输出是家长可复现契约）。追加：

```js
/**
 * ROUND10_H3 —— 这个技能今天能不能在每日冒险里练。
 * 每日题模板只覆盖点数/加减/比大小/数序，图谱 34 个技能不是个个有对应模板；
 * 没有模板的技能界面上就不给「一键开练」按钮，不给一个跳过去货不对板的链接。
 */
export function dailySupports(skillId) // → boolean

/**
 * 聚焦练习：围绕一个技能出一组题，确定性与每日冒险同源。
 * 种子 `${dateKey}#focus:${skillId}#${slot}`——同一天同一技能永远同一套题，
 * 换技能换一套。skillId 不认识或不支持 → 返回 null（调用方回落标准每日题）。
 */
export function buildFocusQuestions(skillId, dateKey = dailyDateKey(), size = DAILY_SIZE)
// → Array<question>（形状与 buildDailyQuestion 返回一致，含 skill/stars/xp）| null
```

- 技能 → 模板映射表 `SKILL_TO_DAILY`（模块内常量，可导出供 check-content 验）：
  key ∈ `SKILL_NODES` 的 id，value = 模板 id 数组；**零随机、零 Date 之外的
  非确定源**（`dailyDateKey()` 的隐式今天允许，与既有一致）；
- 不 import 任何 store；`daily.js` 保持裸 Node 可载（探针读它源码，
  check-content 会 import 它）。

### 3.3 路由与视图契约（推荐 ≠ 代点，导航不是写进度）

- **每日冒险**：`DailyView` 读 `route.query.focus`——合法且 `dailySupports` 为真
  → 用 `buildFocusQuestions` 替换题组，页头挂聚焦徽标（`[data-daily-focus]`，
  值 = skillId，文案「⚡ 今天专练：<技能名>」+ 一键退回标准每日题的链接）；
  非法/缺省 → 标准每日题，**行为与今天逐字节一致**。记账走 QuizShell 既有路径，
  聚焦模式不新增持久化键、不改 `daily` 存档语义（完成聚焦组**不**记为
  「今日冒险已完成」——它是加练，不顶替每日任务，防刷完美奖励）；
- **错题本**：`ProgressView` 读 `route.query.panel === 'wrongbook'` → 滚动到
  `WrongBook` 区并落 `[data-panel-open="wrongbook"]`；`WrongBook` 组件不改；
- **图谱侧**（`SkillGraphView.vue` 纯追加）：推荐条目行尾追加 CTA——
  `dailySupports(item.id)` 为真给「⚡ 一键开练」（`router-link` 到
  `/daily?focus=<id>`，`[data-reco-practice]`）；该技能在错题本有未清条目
  （视图侧从 `progress.wrongList` 按 `entry.skill` 聚合，**只读**，与 R9
  `wrongSkills` 同一口径）给「📕 错题重练 n」（到 `/progress?panel=wrongbook`，
  `[data-reco-wrongbook]`）。`data-reco-readonly` 只读声明与 R9 推荐区结构不动；
  `recommend()`/`recommendPath()` 签名冻结，本轮零改动。

### 3.4 校验与 smoke

- math `check-content.mjs` 追加规则段（既有规则只加不改）：
  ① `SKILL_TO_DAILY` 的 key 全 ∈ `SKILL_NODE_MAP`、value 全 ∈
  `DAILY_TEMPLATE_IDS`；② L1/L2 的核心运算技能（加减、比大小、点数）至少各有
  一个映射（推荐首屏最常见的落点不能全是「没按钮」）；③ 同参两次调用
  `buildFocusQuestions` 深比较相等（确定性）；④ 固定日期下
  `buildDailyQuestions` 输出与追加前快照相等（默认路径零漂移）；
  ⑤ `daily.js` 源文本无 `Math.random` 直调、无 store import。
- math `smoke.mjs`：`const ROUND10_H3_SMOKE = '/daily'`（完整词，见 §0.1）+
  interact 段：种一份含 learning 技能与 1 条错题的存档 → 开图谱 → 断言
  `[data-reco-practice]` 在场 → 点击 → 落在 `/daily?focus=…`、
  `[data-daily-focus]` 可见、第一题可作答 → 回图谱点 `[data-reco-wrongbook]` →
  `[data-panel-open="wrongbook"]` 在场 → 全程无控制台报错；末尾重复 R9 的
  localStorage 只读断言口径：**逛图谱与点击跳转本身不写任何进度键**
  （落页作答后写进度是玩法页的事，断言范围划在跳转前）。R9 smoke 段不动。

---

## 4. 契约四 · 绘本投稿自动化：import 脚本 + ajv CI（H4，所有者 #7）

### 4.1 探针拆解

H4 = `scripts/import-book-submission.mjs` 存在 && `/import-book-submission|ajv/i`
命中「根 `package.json` + literacy `package.json`」拼接。Brief 加码「进 test 链」
——只在 package.json 写个名字而不真挂链是 R9 §0.1 点过名的作弊形态，禁止。

### 4.2 Schema 单一来源

- 新建 `scripts/data/book-submission.schema.json` = `BOOK-COMMUNITY-SUBMISSION.md`
  §3.5 的 draft 2020-12 全文**原样落盘**（`$id` 保持
  `hongen-book/1` 语义，`schema` 常量、`contributor.license` 枚举
  `CC0-1.0|CC-BY-4.0`、逐级页数下限的 `allOf` 一条不改）；
- 文档 §3.5 加一行指向该文件为权威（「文档是给人读的副本，CI 用的是
  schema.json」），顺手校正审计 §5-4 点的「§五 61 项应为 71 项」。

### 4.3 CLI 契约：`scripts/import-book-submission.mjs`（新建，根 scripts/）

```text
node scripts/import-book-submission.mjs <submission.json> [--dry-run]   # 导入模式
node scripts/import-book-submission.mjs --check                          # CI 自测模式
```

- **导入模式**：ajv（draft 2020-12）按 schema 校验 → 逐字过
  `CHARACTER_MAP`（import literacy `characters.js`，越级用字直接拒，报错列出
  越界字与其所属级）→ 追加种子条目 `{ t, sub, cover, summary, pages }` 到
  `apps/literacy-app/scripts/data/book-seed-l{N}.mjs` 尾部（格式与现有条目一致）
  → 提示后续命令链（`gen:books → check:data`，**脚本不自动跑生成器**，
  合入判断留给人，与文档 §五 流程一致）。`--dry-run` 只校验零写入。
  书名撞车、多音字注音等深层校验**不重造**——那是 `gen-books` + `check:data`
  的地盘，脚本只负责把「手工翻写种子」这一步变成机器动作；
- **`--check` 自测模式**（挂 test 链的形态）：编译 schema + 跑仓库内固定夹具
  `scripts/fixtures/book-submissions/`（新建：`valid-l2.json` 必过、
  `invalid-charset.json`/`invalid-pages.json` 必拒，拒因断言到具体路径）——
  零写入、零网络、<1 s；
- **依赖与挂链**（根 `package.json` + lockfile，**#7 本轮独占**）：
  devDependencies 加 `"ajv"`（精确版本，无 `^`，以 `npm i -DE ajv` 实装版为准
  记入本文档回填与 evidence README）；scripts 注册
  `"check:submission": "node scripts/import-book-submission.mjs --check"` 并串进
  根 `test` 链（`test:feedback` 之后）。`ajv` 字样在根 package.json 出现即命中
  探针第二与门；
- 文档 §七 改写为落地记录：两项自列欠账（import 脚本、CI ajv 步）销账，
  「线上上传通道」仍如实列为不做。

### 4.4 红线

`books.js` / `gen-books.mjs` / 种子文件既有条目零改动（脚本只追加）；不建
`community.js`；投稿不自动合入；`contributor.original !== true` 一票否决；
R8 H1/H2 与绘本水位（132 本零越界）不动。

---

## 5. 契约五 · 儿歌真实旋律资产（H5，所有者 #8）

### 5.1 探针拆解

H5 = `SONGS` 里 `audio|src|melodyUrl` 字段值含 `.mp3|.ogg|.wav|.m4a` 的条目 **≥3**
&& `/\bROUND10_H5\b/` 命中「`songs.js` 剥注释 + literacy smoke 剥注释」拼接。
同时 R9 H1（≥10 首 + v2 标记）与 R8 H2（≥3 首 + 路由）继续在跑；literacy
`check:data` 的儿歌六探针（覆盖率/拼音对齐/notes 对齐/分区非空）对新增字段
零感知——**只加字段，不动歌词与 notes**。

### 5.2 资产政策（本仓库第一批媒体资产，规则先立后放）

- **来源与版权**：首选路径是**给库里 13 首原创旋律做音频化**——`notes` 数组
  已是原创五声旋律，渲染/录制它们零第三方权利问题；也可采用公有领域曲调重新
  演绎（须在溯源日志给出公版依据）。**禁止**在版权期内的旋律与录音。若渲染
  用到开源音色库/soundfont，许可必须允许再分发并进 `THIRD_PARTY_NOTICES.md`；
- **溯源日志** `.agent_workspace/r10-songs-melody-log.md`（新建，#8 独占）：
  逐首「songId · 来源（渲染链/录制）· 许可 · 时长 · 字节数 · bpm 一致性」；
- **文件契约**：`apps/literacy-app/public/songs/<songId>.<ext>`（文件名 = 歌 id，
  锁定）；格式 ogg 或 mp3（目标运行时是 Android WebView/Chromium，ogg 体积占优；
  探针两者都认）；单声道、≤400 KB/首、**总预算 ≤2.0 MiB**（识字 zip 10 MiB
  红线下留稳余量，§0.3）。资产进 SW 预缓存（离线第一原则：装了就全能用；
  预算若被突破，改走 `offlinePrecache({ exclude })` 运行时缓存并回改本节，
  两条路二选一，禁止「预缓存一半」）；
- **节拍对齐**：渲染音频必须按该歌 `bpm` 出——v2 歌词同步动画的时间轴是
  `bpm × notes` 排的，音频跟谱不齐等于亲手打碎 R9 H1 的交付。

### 5.3 数据与视图契约

- `songs.js`：≥3 首的 `audio` 从 `null` 改为 `'songs/<id>.ogg'`
  （**BASE_URL 相对路径、不带前导斜杠**，视图用
  `import.meta.env.BASE_URL + song.audio` 解析——数据文件不碰 `import.meta`，
  保持裸 Node 可载）；头注释的「audio 暂时都是 null」段落改写成如实描述；
  追加导出 `export const SONG_AUDIO_MARKER = 'ROUND10_H5'`（代码级标记落点，
  SongsView 真实消费它——如作为音频区 `data-song-audio` 的值），其余导出面
  与 R9 冻结口径一致一个不改；
- `SongsView.vue`（单文件，纯追加）：有 `audio` 的歌展示「🎧 听录音」控件——
  `<audio>` 元素用户点击触发（**不自动播放**，WebView autoplay 策略 + 儿童场景
  双重理由）；录音播放期间 v2 同步层降到**句级进度**（音频没有逐字回调，
  不假装字级精度——读模式的既有口径平移）；合成旋律 `playMelody()` 与逐字
  卡拉OK照旧可用，两种模式并列、互不替代；`audio` 缺席的歌界面零变化。
  `markSongSung()` 记账语义不变（唱完整首才记，无论哪种伴奏）；
- literacy `smoke.mjs`：`const ROUND10_H5 = 'songs-real-audio'`（**精确此形，
  无后缀**，§0.1 第 2 条）+ interact 段：开 `/songs` → 断言歌卡 ≥10（R9 地板）、
  `data-song-sync="v2"` 仍在场 → 展开一首带音频的歌 → 断言 `[data-song-audio]`
  在场、`<audio>` 的 `src` 经 page fetch 可取（HTTP 200，防指向不存在的文件）→
  无控制台报错。**不断言真实出声**（无头环境音频不可靠，断言资源与 DOM 协议）。

---

## 6. 契约六 · 双档 Perf：桌面 LH + 真机清单回填（H6，所有者 #9）

### 6.1 探针拆解

H6 = `.agent_workspace/evidence/r10/` **顶层**存在文件名含 `desktop` 的 `.json`
≥1 && `ANDROID-DEVICE-CHECKLIST.md` 全文 >500 字符且**前 2000 字符零 `[待填]`**。

### 6.2 桌面档：`scripts/lighthouse-ci.mjs` 脚本内扩展（不动根 package.json）

- 既有 mobile 流程（三重版本锁 12.8.2 + acceptance.sh 子流程 + P ≥ 0.95 断言）
  **一行不改**；追加桌面阶段：mobile 验收过线后，对双 App 的构建产物同一静态服
  直跑 `node_modules/.bin/lighthouse --preset=desktop --output=json`（Chrome
  解析沿 acceptance.sh 的既有路径/环境变量，不另起炉灶），产出写
  `lighthouse-<app>-desktop.json`；
- 证据目录切换：R10 起 `ACCEPTANCE_EVIDENCE_DIR` 缺省值升为
  `.agent_workspace/evidence/r10`（mobile 两份 JSON 与 desktop 两份都落这里的
  **顶层**——探针不递归，desktop JSON 放子目录白干）；`evidence/r9/` 从此只读；
- **桌面阈值方法论**：首跑实测 → 取实测往下留一档写死脚本常量（桌面分数
  通常高于 mobile，预期下限不低于 mobile 的 0.95/0.90/0.90；实测更高就定更高）
  → 之后只许上调、禁 env 放水。阈值与实测值回填进 evidence README 与
  `acceptance-log-round10`（#3/#10 的表）；
- 版本升级三件套纪律继承：动 LH 版本 = 改常量 + lockfile + 重定标同一 commit。

### 6.3 `evidence/r10/` 路径规范（锁定，全体引用这一份）

```text
.agent_workspace/evidence/r10/
  README.md                                  ← #9：索引 + SHA-256 + 工具版本 + 复现命令
  lighthouse-literacy-app.json               ← #9（mobile，acceptance.sh 原生命名）
  lighthouse-math-app.json                   ← #9（mobile）
  lighthouse-literacy-app-desktop.json       ← #9（探针命中面，必须顶层）
  lighthouse-math-app-desktop.json           ← #9（同上）
  checks/round9.txt round10.txt              ← #10：门禁逐行输出快照
  ocr/…                                      ← #5（--json 快照与 WebView 佐证，可选）
  device/…                                   ← #9（adb dumpsys、录屏帧等真机佐证）
```

JSON 原样入库不精简；文件名小写连字符；所有权按行注分区，两人不碰同一文件。

### 6.4 真机清单回填（`ANDROID-DEVICE-CHECKLIST.md`，#9 独占）

- §1 设备表**全部 `[待填]` 换成实测值**（低档 + 中高档两台真机；探针盯的就是
  这一段），APK SHA-256、WebView 版本、commit 逐项落实；
- 执行过的检查项打钩并在证据列给出 `evidence/r10/device/` 内的文件引用；
  **没执行的项保持不打钩并在证据列写「未测：<原因>」**——回填是记录事实，
  不是把方框全画满；全文任何位置不新造 `[待填]`（头 2000 字符是探针范围，
  但占位符零容忍是全文纪律）；
- OCR 专项段引用 #5 的 `r10-ocr-webview.md`（§2.4），不复制数字；
- 清单模板结构（章节、表头、App ID）不动——它是可复用的走查模板，回填不等于重写。

### 6.5 红线

`evidence/r8`、`evidence/r9` 只读；`acceptance.sh` 行为不动（SKIP 语义留给裸
环境，强制性由 `test:lighthouse:ci` 承担的分工不变）；mobile 阈值不降；
axe 四主题 critical/serious 0/0 维持；本轮 #9 不碰根 package.json / lockfile。

---

## 7. 契约七 · 发布就绪：LICENSE + 隐私页 + 版本统一（H7，所有者 #10）

### 7.1 探针拆解

H7 = 根 `LICENSE` 存在 && 识字 `router/index.js` 剥注释后命中 `/privacy|隐私/
&& 根 version === '1.0.0' && 识字 version === 根 version。三个都是发布硬件，
不是文档姿态——R9 RELEASE-CHECKLIST 已把 LICENSE 升格为「发布阻断」，本轮落地。

### 7.2 LICENSE 与许可结构

- 根 `LICENSE` = **MIT 全文**（Brief 指定），版权行
  `Copyright (c) 2026 hongen-edu-apps contributors`；RELEASE-CHECKLIST 中
  「若权利人另选许可证，替换文件 + 本行打钩」的 owner 复核项**保留**（落地 MIT
  是解除发布阻断，不剥夺权利人改选权）；
- 许可分层如实写进 RELEASE-CHECKLIST 对应节：代码 MIT；第三方资产义务以
  `THIRD_PARTY_NOTICES.md` 为准（OpenMoji CC BY-SA 4.0 署名义务重申，tesseract.js
  Apache-2.0，若 #8 引入音色资产由其条目补入）；原创内容资产（剧情/儿歌/绘本
  文本与旋律）随仓库 MIT 或单独 CC BY 4.0，清单记录决定；投稿内容按投稿人所选
  `CC0-1.0|CC-BY-4.0`（§4 schema 枚举）。LICENSE 落地后把清单里
  「阻断：仓库当前不存在」一行翻成落地记录，**历史文字不删改，追加状态**。

### 7.3 隐私页与版本统一

- 识字新增懒加载路由（放 `/parent` 前，模式沿现状）：

  ```js
  {
    path: '/privacy',
    name: 'privacy',
    component: () => import('@/views/PrivacyView.vue'),
    meta: { title: '隐私说明', emoji: '🔒' }
  }
  ```

  `PrivacyView.vue` 内容契约（写给家长看，每节一句人话结论 + 细节）：
  ① 数据去向总述（全程离线、无账号、无采集、无遥测）；② 麦克风（录音只存
  内存 Blob 页面关了就没；浏览器逐字识别可能走厂商在线服务、默认关、家长开——
  与 FollowReadView 已修文案同一口径；离线识别包是可选下载、可整体删除）；
  ③ 相机/OCR（拍的照片本地 wasm 识别，不上传）；④ 存储（localStorage 存档、
  家长中心可导出/导入/清除）；⑤ 第三方资源署名（OpenMoji 等，指向
  THIRD_PARTY_NOTICES）；⑥ 仓库与联系方式。`ParentView` 追加入口链接
  （纯追加一行 router-link）。数学 App 同样落 `/privacy`（同结构改写，
  探针虽只查识字侧，双 App 发布口径必须一致——这条按契约执行，不赌探针）；
- **版本统一**：`apps/literacy-app/package.json` 与 `apps/math-app/package.json`
  的 `version` → `1.0.0`（根已是 1.0.0 不动）；npm workspaces 的 lockfile 记录
  子包版本，改完跑 `npm install --package-lock-only` 重刷——所以 **#10 必须排在
  #7 的 lockfile 变更之后合并**（§8 合并顺序）；Android 侧 `check:android`
  26/26 复跑确认版本字段无联动断裂。

### 7.4 报告与日志收口（H7 探针之外的 #10 责任面，审计 §5-1 欠账在此清）

- **`acceptance-log-round9.md` 回填**（R9 审计点名的头号收口欠账）：§1 H1–H8
  集成实测格、§2 LH/OCR/体积表、§4 走查勾选、§5 集成 SHA——数据全部现成
  （审计 §0 + evidence/r9），照抄回填，零占位过夜；
- `GLOBAL-SUMMARY-REPORT.md` 追加 Round 10 终态章：含字面 `Round 10`、八项交付
  逐项证据、`check:round10` 8/8 输出全文、`evidence/r10` 索引。占位反向命中面
  并集继续生效（R7 H7 的状态正则、零 `⏳/待回填/TODO/TBD/[P/F]/⬜/❌`、
  `evidence/r8` 字样保留、首行 Model slug 不删）；历史数字不删改；
- `RELEASE-CHECKLIST.md` 更新：LICENSE 行翻状态（§7.2）、版本号方案落定
  （1.0.0 + tag 约定）、发布门禁链补 `check:round10`、G4/G5 在集成 HEAD 重跑
  落数（审计 §5-7）。

---

## 8. 文件所有权与冲突矩阵

| 热点文件 | 触碰者 | 隔离规则 |
|---|---|---|
| literacy `composables/useSpeechEval.js`、`utils/asrEngine.js`、`workers/asr.worker.js`、`utils/asrBackends/*`、`FollowReadPanel/FollowReadView`（追加区） | #4 独占 | `speechEval.js` 旧导出冻结只许追加；三档语义与 `allowRecognition` 默认不动 |
| literacy `scripts/smoke.mjs` | #4（`ROUND10_H1_SMOKE` 段）+ #8（`ROUND10_H5` 段） | 各自纯追加独立 interact 段，先到先得，R6/R8/R9 段不动 |
| literacy `scripts/fixtures/ocr/real-photo-*.png`、`scripts/test-ocr-accuracy.mjs`、`.agent_workspace/r10-ocr-real-log.md`、`r10-ocr-webview.md` | #5 独占 | 既有 10 条基准字节与阈值冻结，只追加 tier |
| math `data/daily.js`、`modules/daily/DailyView.vue`、`modules/skill-graph/SkillGraphView.vue`（CTA 区）、`modules/progress/ProgressView.vue`（query 段）、math `scripts/check-content.mjs`、`scripts/smoke.mjs` | #6 独占 | `daily.js`/`skill-graph.js` 旧导出冻结；check/smoke 纯追加段 |
| 根 `scripts/import-book-submission.mjs`、`scripts/data/book-submission.schema.json`、`scripts/fixtures/book-submissions/*`、**根 `package.json` + `package-lock.json`**、`BOOK-COMMUNITY-SUBMISSION.md`（§3.5/§五/§七 修订） | #7 独占 | 根 pkg/lockfile 本轮唯一写者；literacy 种子文件只追加 |
| literacy `data/songs.js`、`views/SongsView.vue`、`public/songs/*`、`THIRD_PARTY_NOTICES.md`（音色条目）、`.agent_workspace/r10-songs-melody-log.md` | #8 独占 | 歌词/notes/旧导出冻结；音频总量 ≤2.0 MiB |
| `scripts/lighthouse-ci.mjs`、`.agent_workspace/evidence/r10/`（README/LH JSON/device/）、`ANDROID-DEVICE-CHECKLIST.md` | #9 独占（evidence/r10 内 ocr/ 归 #5、checks/ 归 #10） | mobile 流程不改只追加桌面段；不碰根 pkg |
| 根 `LICENSE`、literacy+math `router/index.js`（privacy 路由）、`PrivacyView.vue` ×2、`ParentView`（入口一行）、两 App `package.json`（version）、`GLOBAL-SUMMARY-REPORT.md`、`RELEASE-CHECKLIST.md`、`acceptance-log-round9.md`（回填）、`evidence/r10/checks/` | #10 独占 | 排最后；version 改完重刷 lockfile |
| `.agent_workspace/round10-architecture.md`（本文） | #1 | 契约变更须回改本文 |
| `ROUND10-ACCEPTANCE.md`、`check-round10.mjs` v1.1 | #3 | 探针只许加严（§0.2 清单） |

**合并顺序**：#4 / #5 / #6 / #8 四条功能线互不依赖可乱序（唯一交叉点 literacy
smoke 按「各自追加段」先到先得）→ **#7**（动根 package.json/lockfile，单独一拍）
→ **#9**（在全量功能上量分，evidence/r10 落桌面档）→ **#10 收口**（版本 + 隐私 +
LICENSE + 报告，version 变更重刷 lockfile 必须压在 #7 之后）。#2 审计、#3 验收
强化随时可合，但探针加严若改变命中面必须回改本文档。

---

## 9. 契约 → 门禁映射

| 契约 | check:round10 探针 | 所有者 | 回归红线 |
|---|---|---|---|
| §1 跟读 v3 | H1：`/Worker\|sherpa\|offline.*ASR\|ROUND10_H1/i`（两源文件代码级）+ `ROUND10_H1(_SMOKE)` in smoke | #4 | 三档语义/默认值不动；本地失败只降 recording；模型零入库；`speechEval.js` 冻结面 |
| §2 OCR 真样张 | H2：`real-*` PNG ≥2（一层目录）+ `ROUND10_H2`（代码级） | #5 | 既有 10 条基准冻结；总召回仍只统计 print；运行时识别参数不动；来源如实溯源 |
| §3 推荐闭环 | H3：wired（基线恒真）+ `ROUND10_H3_SMOKE`（行为断言） | #6 | `buildDailyQuestions` 逐字节不动；推荐只读不写 store；聚焦练习不顶替每日任务 |
| §4 投稿 CI | H4：脚本存在 + `ajv` 入 package.json（真挂 test 链） | #7 | 种子/生成器既有条目零改动；根 pkg/lockfile 独占；`--check` 零写入 |
| §5 儿歌旋律 | H5：audio 字段 ≥3 首 + `\bROUND10_H5\b`（无后缀，代码级） | #8 | 歌词/notes/存档形状冻结；≤2.0 MiB；不自动播放；版权溯源留档 |
| §6 双档 Perf | H6：evidence/r10 顶层 desktop JSON ≥1 + 清单头 2000 字符零 `[待填]` | #9 | mobile 流程与阈值不动；r8/r9 证据只读；未测项如实写「未测」 |
| §7 发布 | H7：LICENSE + router 代码级 `privacy` + 双侧 version 1.0.0 | #10 | R7/R8/R9 H7 占位反向命中面并集；历史数字不删改；#7 之后合并 |
| 全体 | H8：`check:round9` 8/8（内含 R8/R7/R6 级联） | 每个分支 | 合并前 `npm test` 全绿 |

---

## 10. 明确不做（Out of scope）

- 跟读不把 sherpa wasm/模型提交入库、不做后台静默下载、不改 `allowRecognition`
  默认值、不把 mock 后端冒充真识别（界面必须标注）、不做声学音素评分
  （评估文档口径：tone/near 是诊断线索不是判决）；
- OCR 不采集儿童手写/人像样张、不为过基准调运行时识别参数、不把 fixtures 挪进
  `public/`、不删程序合成图（两类样张并存，各测各的边界）；
- 推荐闭环不代点开练（CTA 是导航不是自动开始答题）、不写任何 store、不动
  `curriculum.js` 与星球解锁经济、聚焦练习不计入「今日冒险完成」、不新增持久化键；
- 投稿不开线上上传通道、不自动合入过审内容、不在 import 脚本里重造
  `check:data` 已有的深层校验；
- 儿歌不引入在版权期内的旋律或录音、不自动播放、不做录音跟唱评分、不改
  13 首既有歌词与 notes、总音频不超 2.0 MiB；
- Perf 不降 mobile 阈值、不改 `acceptance.sh`、不动 `vite-offline-plugin` 行为
  （§5.2 的 exclude 分支若启用属参数使用非行为修改）、真机清单不伪造勾选；
- 发布不删改历史数字、不写任何「⏳ 待 Rn」形态、LICENSE 选型保留 owner 复核项；
  根 `package.json` 的 version 不动（已 1.0.0）；
- 全体：不改识字主存档 `happy-literacy:v1` 顶层结构与 FSRS 参数、不动数学
  `mathquest/settings` sanitize 白名单、不动四主题 axe 0/0 水位。

---

## 11. R9 审计「R10 归属备忘」对账（10 条 → 本文落点）

| # | 备忘项 | 本文落点 |
|---|---|---|
| 1 | acceptance-log-round9 回填 + 出包终验 | §7.4（#10） |
| 2 | Android 真机走查执行 | §6.4（#9） |
| 3 | 跟读 v3 阶段 A：sherpa Worker spike | §1（#4） |
| 4 | 跟读隐私文案修正 | **基线已修复，销账**（文首基线说明） |
| 5 | OCR 真实样张 + WebView 实测 | §2（#5） |
| 6 | 投稿 import 脚本 + CI ajv | §4（#7） |
| 7 | 儿歌旋律资产升级 | §5（#8） |
| 8 | 推荐 × 错题本/每日冒险闭环 | §3（#6） |
| 9 | LICENSE / 版本统一 / 隐私页 / tag 冻结 | §7（#10） |
| 10 | 字源复核余量 + 桌面档 LH 定标 | 桌面档归 §6.2（#9）；字源批量复核**本轮除名**——R9 已抽修 13 条且探针无缺口，余量属常态维护，不设 R10 门禁（如实记录，不装作有人做） |
