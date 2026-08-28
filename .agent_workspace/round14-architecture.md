> Model slug: claude-fable-5（Round 14 子代理 #1 · `cursor/r14-arch-contracts-9f67`）
> 架构标记：`ROUND14_ARCH = 'r14-experience-endgame-v1'`

# Round 14 · 洪恩体验终局架构契约（E1–E5 对齐）

> 基线：`cursor/openmoji-integration-9f67` @ `0d70870`（R13 集成 · `check:round13` 7/8，仅 H7 BLOCKED 预期红）
> 性质：**只定数据契约、目录约定与探针接线，不含实现**。功能由 Round 14-1/14-2/14-3 各分支按本契约落地。
> 关联：`ROUND14-BRIEF.md`、`ROUND14-ACCEPTANCE.md`、`scripts/check-round14.mjs` v1.0、
> `round13-architecture.md`（R13 契约，本文 supersedes 其 R14 归属项）、
> `round13-hongen-audit.md` §5.1/§5.2（6 个 ◐ + X1–X3 横切债的 R14 尾巴全部在本文有落点）。

基线八探针实跑水位（撰写时在 `0d70870` 实跑 `node scripts/check-round14.mjs`，**1/8**）：

| 探针 | 基线状态 | 关键实测值 |
|---|---|---|
| H1 ASR 体验放行 | ✗ | available=false，recorded=0/300，release/deviceRtf/harness/smoke 全 false |
| H2 OCR 体验闭环 | ✗ | app=0/41（r14 矩阵未产出），deviceB/queue/reflux/harness 全 false |
| H3 绘本密度 | ✗ | scenePages=**209**/400，rendered=true，`ROUND14_H3`=false |
| H4 范唱全库 | ✗ | songs=13，humanVocal=**0**/13，doc=false |
| H5 L1 朗读批次 | ✗ | assets=0/20，doc=false，smoke=false |
| H6 真机签核 | ✗ | signoff/decision/record 全 false |
| H7 商店内测 | ✗ | submit=false（R13 BLOCKED 延续） |
| H8 往轮不退化 | ✓ | round12 **8/8** + round13 **7/8** |

---

## 1. E1–E5 体验维度 → R14 落点映射（本轮总纲）

R10–R13 审计沿用的「洪恩真实体验深度」五维杆：**E1 看到 / E2 听到 / E3 摸到 / E4 家长 / E5 真机**。
R14 的唯一目标是把 `round13-hongen-audit.md` 预判的 **6 个 ◐** 按维度推到**体验口径 ✅**——
「用起来和洪恩一样」，而不是再堆工程证据。

### 1.1 维度 × 模块 × 探针总表

| 维度 | 含义（孩子/家长当场感知） | R13 后残差 | R14 落点（探针） | flip 模块 |
|---|---|---|---|---|
| **E1 看到** | 打开即见的美术表现力密度 | scene 209/1121 页，高频外仍单 emoji | **H3** scene ≥400 页 + 渲染不退化 | L-M5 ◐→大幅收窄（1121 全库归 R15） |
| **E2 听到** | 真人/高质量人声，非合成「啦」音 | 范唱 3/13（Piper 为主）；字卡仍 SpeechSynthesis | **H4** 13/13 `humanStudio:true` 范唱；**H5** L1 单元 ≥20 条朗读资产 | L-M11 ◐→✅；X1 收窄 |
| **E3 摸到** | 交互当场给真反馈，非回放/降级 | 跟读仍录音回放（available:false）；拍照识字 App 召回 33/41 | **H1** `available:true` + 实时评分；**H2** App ≥40/41 + 回流队列 closed | L-M9 ◐→✅；L-M10 ◐→✅ |
| **E4 家长** | 家长可核验、可安装、可反馈 | 内测 BLOCKED；盲听/走查无签字 | **H7** 内测轨道实提回执；W1–W6 人工走查签字（G7） | 发布流程 ◐→✅ |
| **E5 真机** | 真机上的一切（RTF/相机/离线/温升） | 全部证据 `simulated:true`；NO-GO 未解除 | **H1** device RTF p95≤0.5；**H2** 真机 B 段；**H6** `device-signoff.json` GO | L-M15/M-M16 ◐→✅ |

### 1.2 维度判读规则

1. **E5 是地基**（X3 横切债）：任何 E1–E4 的 flip 主张，凡涉及设备能力（ASR RTF、
   相机、离线稳定性），**必须以 `evidence/r14/` 真机 JSON 为准**；sim 证据只维持工程链，
   永不参与 flip 判定；
2. **E2 双腿**：H4 范唱（儿歌主唱）与 H5 朗读（字卡/单元）分开验收，不许互相充数；
3. **E3 的「实时」口径**：H1 flip 后 UI 必须与 `manifest.available` 一致——
   `[data-tier=offline-asr]` 实时评分路径，禁止「files 在库 = 孩子可用」文案；
4. **E4 签字权**：W1–W6 走查（`ROUND14-ACCEPTANCE.md` §3）由 owner 人工勾选，
   探针绿 ≠ 走查过；终审（Round 14-3 #13）按两口径分列。

---

## 2. evidence/r14 目录约定（本文核心交付其一）

### 2.1 目录树（唯一合法布局）

```text
.agent_workspace/evidence/r14/
├── README.md                        # 目录索引 + 采集环境声明（首个写入者创建）
├── asr/
│   └── device-rtf.json              # H1 真机 RTF（onDevice:true 强制）
├── ocr/
│   └── app-webview-matrix.json      # H2 App/WebView 召回矩阵（≥40/41）
└── android/
    ├── ocr-device-b.json            # H2 真机 B 段（adb 拍照端到端）
    ├── device-signoff.json          # H6 真机签核（devices[]≥2）
    └── *.log / *.png                # 佐证日志与截图（可选，命名见 §2.4）
```

### 2.2 铁律：r14 = 真机层，与 r13 sim 层分目录、分语义、分签核权

| 路径 | 语义 | `simulated` 字段 | 可否参与 flip / 解除 NO-GO |
|---|---|---|---|
| `evidence/r13/android-sim/` | VM 模拟（R13 H6 冻结面，只读） | **`true` 不可删** | **否** |
| `evidence/r14/asr/`、`evidence/r14/ocr/`、`evidence/r14/android/` | **真机/实测证据** | 缺省或 `false`；**禁止 `simulated:true` 写入** | **是**（探针即按此判） |

- 探针硬断言：H1 `!rtf.simulated`、H2 `b.simulated !== true`、H6 `j.simulated !== true`——
  把 sim 数据复制进 r14 目录 = 冒充真机，**终审一票否决**；
- r13 sim 证据继续由 `android-sim.mjs` 刷新，**不迁移、不删除**（H8 冻结面）。

### 2.3 JSON schema（探针逐字段消费，缺一腿即 FAIL）

```jsonc
// evidence/r14/asr/device-rtf.json（H1 · 所有者 #5→#8）
{
  "onDevice": true,            // 强制 true
  "rtfP95": 0.42,              // number；≤ 0.5
  "rtfP50": 0.31,              // 建议附
  "device": "型号/SoC/RAM",     // 溯源（探针不查但终审查）
  "clips": 300,                // 参与统计的实录条数
  "collectedAt": "2026-XX-XX", // ISO 日期
  "sha256": "APK 或模型包指纹"
  // 禁止出现 "simulated": true
}
```

```jsonc
// evidence/r14/ocr/app-webview-matrix.json（H2 App 腿 · 所有者 #3→#12）
{
  "passCount": 40,             // ≥40（探针也认 "recall" 字段名）
  "total": 41,                 // ≥41
  "tiers": { "print": "...", "handwrite": "...", "scene": "..." },
  "failures": [ { "id": "...", "reason": "...", "queuedAs": "queue.json id" } ],
  "collectedAt": "2026-XX-XX"
}
```

```jsonc
// evidence/r14/android/ocr-device-b.json（H2 真机 B 段 · 所有者 #12）
{
  "pass": true,                // 强制 true
  "onDevice": true,            // 强制 true
  "device": "...",
  "samples": 10,               // 日常场景 ≥10 张，≥9 张首屏认对（W2 口径）
  "firstScreenCorrect": 9,
  "collectedAt": "2026-XX-XX"
  // simulated 不得为 true
}
```

```jsonc
// evidence/r14/android/device-signoff.json（H6 · 所有者 #5→#16）
{
  "pass": true,                // 强制 true
  "onDevice": true,            // 强制 true
  "devices": [                 // 数组 ≥2 台（探针硬断言 length≥2）
    { "model": "...", "soc": "...", "androidVersion": "...", "tier": "low|mid" },
    { "model": "...", "soc": "...", "androidVersion": "...", "tier": "mid|high" }
  ],
  "apps": {
    "literacy": { "apkSha256": "...", "offlineMinutes": 30, "crash": 0 },
    "math":     { "apkSha256": "...", "offlineMinutes": 30, "crash": 0 }
  },
  "signedBy": "owner 签名",
  "signedAt": "2026-XX-XX"
  // 文件体积 ≥100 B（探针 evidenceFileOk 下限；实际应远超）
}
```

### 2.4 命名与写入纪律

1. **JSON 文件名 = 探针硬编码路径**，一个字符不许偏（见 §3 接线表第 3 列）；
2. 佐证文件命名 `r14-<域>-<内容>-<日期>.<ext>`（如 `r14-android-lowend-thermal-0905.log`）；
3. 每个子目录首个写入者补 `README.md`：设备清单、采集人、采集环境、与探针的对应关系；
4. **只许追加**：r8–r13 全部 evidence 目录为冻结面（H8），不删不改；
5. 写者分工：`asr/` 归 ASR 线（#4→#8），`ocr/` 归 OCR 线（#3→#12），
   `android/` 归真机线（#5→#16），交叉写入须在 PR 说明对账。

---

## 3. H1–H7 接线表（探针 ↔ 文件 ↔ 标记 ↔ 所有者，本文核心交付其二）

探针源：`scripts/check-round14.mjs` v1.0（升版只许**加严**，归 #6 验收线）。
所有代码/文档匹配先 `stripComments`——**标记词必须落在代码/正文里，注释里无效**。

| 探针 | AND 腿（全过才绿） | 精确文件路径 | 标记词 | 所有者（R14-1→14-3） | E 维度 |
|---|---|---|---|---|---|
| **H1** ASR 放行 | ① `available===true` ② `clips[].status==='recorded'` 且带 `audio\|audioPath\|wav` **≥300 条** ③ release 文档 >600 字 + GO 结论（结论段无 NO-GO/BLOCKED） ④ 真机 RTF `onDevice:true && rtfP95<=0.5 && !simulated` ⑤ harness 有标记 + assert ⑥ smoke 段 | `apps/literacy-app/public/asr/manifest.json`；`apps/literacy-app/scripts/data/asr-eval-set.json`；`.agent_workspace/r14-followread-release.md`；`.agent_workspace/evidence/r14/asr/device-rtf.json`；`apps/literacy-app/scripts/test-asr-eval-set.mjs`；literacy `smoke.mjs` | `ROUND14_H1` + `ROUND14_H1_SMOKE` | #4 录音启动 → #8 finalize | E3+E5 |
| **H2** OCR 闭环 | ① App 矩阵 `passCount>=40 && total>=41` ② 真机 B 段 `pass && onDevice && !simulated` ③ 回流队列 `items>=1` 且无 `dueRound<=14` 的 `new/triaged` ④ 回流文档 >600 字含 采集/标注/复现/闭环 ⑤ harness 标记 + assert + android/WebView/device/真机 字样 | `evidence/r14/ocr/app-webview-matrix.json`；`evidence/r14/android/ocr-device-b.json`；`apps/literacy-app/scripts/fixtures/ocr/regressions/queue.json`；`.agent_workspace/r14-ocr-experience-loop.md`；`apps/literacy-app/scripts/test-ocr-device.mjs` | `ROUND14_H2` | #3 预处理 → #12 device B | E3+E5 |
| **H3** 绘本密度 | ① `scene[]`（≥2 对象元素/页）计数 **≥400 页** ② `BookPageScene.vue` >300 字或 BookReadView 含 scene（渲染在线） ③ 标记落在 books 数据或 smoke | `apps/literacy-app/src/data/books.js`（+ `src/data/books/` 分文件亦扫描）；`src/components/BookPageScene.vue` | `ROUND14_H3` | Round 14-1 +200 页 → #9 batch2（→400+） | E1 |
| **H4** 范唱全库 | ① songs ≥13 首去重 ② 每首 `humanStudio===true` 且 `vocal\|vocalAudio` 指向 public 实文件 **≥10240 B**（.mp3/.ogg/.wav/.m4a，禁 URL/`..`），去重集 **≥13** ③ 批次文档 >500 字含 13/13/全库/humanStudio/真人 | `apps/literacy-app/src/data/songs.js`；`apps/literacy-app/public/audio/**`；`.agent_workspace/r14-songs-vocal-full.md` | `ROUND14_H4` | 14-1 范唱 4–7 → #10 7–13 → #14 收尾+许可 | E2 |
| **H5** L1 朗读 | ① 批次文档 >500 字含 L1/单元/字卡/朗读/TTS/真人 ② `public/audio/tts-l1/` 音频 **≥20 个**、每个 **≥4096 B** ③ literacy smoke 段 | `.agent_workspace/r14-tts-l1-batch.md`；`apps/literacy-app/public/audio/tts-l1/`；literacy `smoke.mjs` | `ROUND14_H5` + `ROUND14_H5_SMOKE` | #11 tts-l1 | E2 |
| **H6** 真机签核 | ① signoff `pass && onDevice && !simulated && devices.length>=2`（文件 ≥100 B） ② 定案文档 >600 字 + GO（结论段无 NO-GO/BLOCKED） ③ 记录文档 **>800 字** 含 真机/onDevice/不等价模拟 + 字面 `evidence/r14/android` | `evidence/r14/android/device-signoff.json`；`.agent_workspace/r14-android-device-decision.md`；`.agent_workspace/r14-android-device-record.md` | `ROUND14_H6` | #5 矩阵 harness → #16 低档机回归 | E5 |
| **H7** 商店内测 | ① 文档 >600 字含 内测/Play Console/TestFlight/track/轨道 + 日期 + SHA + 版本 ② 结论段**非** BLOCKED/NO-GO ③ 「## 6.」回执段 >200 字、含真实日期、无 `[待填]`（或 `状态：SUBMITTED/VERIFIED`） | `.agent_workspace/r14-store-submission-record.md` | `ROUND14_H7` | #15 内测实提 | E4 |
| **H8** 不退化 | `check:round12` **8/8** + `check:round13` **≥7 ✓** | `scripts/check-round12.mjs` / `check-round13.mjs`（探针内 spawn 实跑） | —（继承往轮标记） | 每分支合并前 | 链式兜底 |

### 3.1 易踩细节（逐行读 v1.0 源码得出）

1. **H1 release 结论段扫描**：探针取 `操作结论|verdict|当前决策` 命中行（或文档前 400 字）查
   NO-GO/BLOCKED——GO 文档里引用历史 NO-GO 须放在结论段之外；
2. **H1 recorded 计数**：`asr-eval-set.json` 顶层 `clips[]`，只数 `status:'recorded'` **且**
   带音频引用字段的条目——占位/`simulated` 条目不计；R13 冻结集 56 条骨架须扩到 300 实录；
3. **H2 App 矩阵 fallback**：r14 矩阵缺失时探针回退读 r13 `android-sim/ocr-section.json`——
   但 r13 是 33/41，**必产出 r14 矩阵才可能 ≥40**；
4. **H2 队列语义**：`queue.json` 至少 1 条 item（空队列 = FAIL）；`dueRound<=14` 的
   `new/triaged` 一条即红——回流演练条目须推进到 `closed/fixed`；
5. **H4 humanStudio 判定**：探针对 song 对象 `JSON.stringify` 后匹配
   `humanStudio: true`——字段必须真在数据里，写在注释/文档里无效；10KB 下限按
   public 实文件 stat，软链接/缺文件不计；
6. **H6 record ≠ decision**：两份文档分开验，record 须 >800 字且**字面出现**
   `evidence/r14/android` 路径字符串；
7. **H7 回执段**：探针按 `## 6.` 正则截取——提交记录文档必须保留「## 6.x 回执」章节结构；
8. **H3 计数口径**：`scene` 或 `sceneElements` 数组、每页 ≥2 个 object 元素；
   209 页基线（R13 H3 冻结）只许追加。

### 3.2 标记词清单（全部字面、去注释后命中）

| 标记 | 落点 | 备注 |
|---|---|---|
| `ROUND14_H1` | `test-asr-eval-set.mjs` + release 文档 | 双落点都要 |
| `ROUND14_H1_SMOKE` | literacy `smoke.mjs` | available flip 后断言实时评分 tier |
| `ROUND14_H2` | `test-ocr-device.mjs` + 回流文档 | 双落点 |
| `ROUND14_H3` | books 数据或 literacy smoke | 建议随台账对象 `Object.freeze({ target: 400, ... })` |
| `ROUND14_H4` | `r14-songs-vocal-full.md` | 数据侧建议同名 export 溯源 |
| `ROUND14_H5` / `ROUND14_H5_SMOKE` | `r14-tts-l1-batch.md` / literacy smoke | 文档腿 + smoke 腿 |
| `ROUND14_H6` | decision + record 两份文档 | 双落点 |
| `ROUND14_H7` | `r14-store-submission-record.md` | 单落点 |
| `ROUND14_ARCH` | 本文（架构契约在位信号） | 编排器/审计核对用 |

---

## 4. 冻结面与红线（R13 → R14）

每分支合并前：`npm test` 全绿 + `check:round13` **≥7/8** + `check:round12` **8/8**（= H8）。

| 冻结项 | R13 终态 | 破坏判定 |
|---|---|---|
| 绘本 scene | **209 页** + `text/p` 一字不改 | 删改已有 scene；计数回退 |
| ASR 冻结集 | 56 条骨架 + freeze 文档 | 删条目；`files[]` sha256 不一致 |
| 范唱批次 | R13 3 首 vocal 资产 | 删音频；sg1–sg13 旋律路径变 |
| android-sim | `simulated:true` report | 删字段；复制进 r14 目录冒充真机 |
| OCR real 矩阵 | ≥10 张 + tier + 99% | 删样张；阈值下调 |
| lift 准实验 | trend 导出 + quasi-v1 | 删 `recommendationEffect` 域 |
| 标记词 | `ROUND12_H*` / `ROUND13_H*` | 命中面减少 |
| evidence | r8–r13 全部目录 | 删改历史 JSON |

横切禁令：模型不进 precache；四档降级/隐私只许往下降；零遥测 SDK；儿童数据不上传；
生产发布仍须 QA + Release Manager 双签（H7 内测 ≠ 生产放行）。

## 5. 合并顺序建议与文件所有权

**顺序**（按冲突面从小到大）：#6 验收 spec（scripts 根）→ #5 真机矩阵 harness →
#3 OCR 预处理 → #4 ASR 录音（literacy scripts 串行）→ H3 绘本（独立数据文件）→
H4/H5 音频资产（public 串行）→ #15/#16 真机与商店文档 → #13 终审。

| 热点 | 所有者 | 隔离规则 |
|---|---|---|
| `asr-eval-set.json`、`manifest.json`、`r14-followread-release.md` | ASR 线 | available flip 须 GO 文档在先 |
| `test-ocr-device.mjs`、`queue.json`、`r14-ocr-experience-loop.md` | OCR 线 | R13 回流 schema 只许扩展 |
| `books.js` / `books/*`、`ROUND14_H3` 台账 | 绘本线 | 209 页冻结，只追加 |
| `songs.js`、`public/audio/vocal/*`、`public/audio/tts-l1/*` | 音频线 | 旋律 13 首 frozen；两目录分写者 |
| `evidence/r14/**` | 见 §2.4 | 分子目录写者；禁 sim 数据 |
| literacy `smoke.mjs` | 各线追加段 | R11–R13 段不动 |
| `check-round14.mjs` | #6 | 只许加严 |
| 本文 | #1 | 契约变更须回改本文 |

## 6. 明确不做（Out of scope）

- 绘本 1121 页全库（R14 只 ≥400，全库分批归 R15）；GSAP MV/IP 化演出；
- ASR 声调声学级验证、模型换版横比治理（record ≥300 + flip 即止）；
- OCR 儿童手写识别；iOS 真机矩阵（Android 双 App 优先）;
- 远端 A/B 平台、因果声称 UI；识字主存档结构与 FSRS 参数变更；
- 生产商店上架（内测轨道即 H7 满分；生产受双签约束）。

**一句话**：R13 交「工程链闭合、sim 诚实」；R14 交「孩子摸到实时评分、听到真人声、
看到 400 页 scene、家长装上内测包、一切设备主张有 `evidence/r14/` 真机 JSON 背书」——
在 H8 不退化红线之上完成 E1–E5 体验 flip，**sim 证据永不进 r14 目录**。
