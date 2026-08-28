Model slug: claude-fable-5
# Round 14 · 体验终审（无真机收口版）

标记：`ROUND14_FINAL_AUDIT`

> 审计人：Round 14-3 子代理 #13（fable，分支 `cursor/r14-final-audit-9f67`）
> 审计基线：集成线 `cursor/openmoji-integration-9f67` @ **`18d6e4c`**（R14-2 六路已合入 + 14-3 编排已启动、14-3 功能分支 #14–#18 在途未合入）
> 审计日期：2026-08-28 · Node v22.14.0 / npm 10.9.7 · 干净 VM 检出，构建链按 R14-2 审计 §0.2 处方自装，门禁实跑退出码为准
> 用户决策口径（ROUND14-3-BRIEF，2026-08-28）：**无真机收口**——不伪造 onDevice/SUBMITTED；代理可达项收尾；外部供给标诚实 BLOCKED
> **结论先行**：干净 VM 首跑 `check:round14` **2/8**、`check:round13` **6/8**——**第三次逐字复现 P1**（H6 对 APK 构建产物环境敏感，R14-1 §0.3 发现、R14-2 §0.1 复现、本轮再复现）。照 §0.2 五步处方（JDK 17 + SDK 34 自装 + `android:sim` 11 分 56 秒重建双 APK）后，**`check:round14` 3/8（H3+H5+H8，exit 1）· `check:round13` 7/8（仅 H7 红，exit 1）· `check:round12` 8/8（exit 0）**。**H3（scene 404 页）与 H5（L1 朗读 24 资产）系集成线上首次翻绿**——这是 R14-2 对 R14-2 审计 §4「3/8 稳」预判的逐格兑现。6◐ 全部收窄、零 flip、零退化：L-M10 仍五腿只欠 deviceB，L-M11 从 0/13 收到 **9/13 真人声源**（sg1/sg2/sg3/sg5 归 #14），L-M9/L-M15/M-M16 工具与台账腿全绿但供给腿零证据。**无真机终态目标声明：`check:round14` = 4/8（H3+H4+H5+H8）**——当前 3/8，唯一在途的代理可达 flip 是 H4（#14 补 4 首），H1/H2/H6/H7 按 §2 台账诚实 BLOCKED，凭用户签字接受收口 R14；**4/8 不是欠交，是无真机诚实上限**（较 R14-2 §3-S2 的 3/8 上修一格，因 H4 被 14-2 实证代理可达：真人棚录元音源 + 旋律适配，9 首已落库）。

---

## 0. 三探针实跑（本 VM，verbatim，退出码为准）

### 0.1 干净 VM 首跑（未重建 APK）——P1 第三次复现

`npm run check:round14`（**2/8**，verbatim）：

```
> hongen-edu-apps@1.0.0 check:round14
> node scripts/check-round14.mjs

  ✓ H3 绘本密度 404 页 scene（≥400）+ 渲染 + ROUND14_H3
  ✓ H5 L1 朗读批次：24 资产 + 文档 + ROUND14_H5_SMOKE

  ✗ H1 ASR 体验未放行：available=false，recorded=0/300，release=false，deviceRtf=false，harness=true，smoke=true —— r14-literacy-asr-finalize
  ✗ H2 OCR 体验未闭环：app=40/41，ocrSection=true，deviceB=false，queue=true，reflux=true，harness=true —— r14-literacy-ocr-device-b
  ✗ H4 范唱未全库：songs=13，humanVocal=9/13，doc=true —— r14-literacy-vocal-full
  ✗ H6 真机未签核：signoff=false，decision=false，record=true，noR13SimPath=true —— r14-android-device-matrix
  ✗ H7 商店内测未闭环：submit=false —— r14-store-internal-test
  ✗ H8 退化：round12=true，round13Pass=6/8

Round 14 体验门禁：2/8 项通过，6 项失败。
说明：R14 功能分支未全部合并时 FAIL 属预期红灯；体验 flip 目标 7/8 或 8/8。
```

同期 `check:round13` **6/8（exit 1）**——红的正是 H6（`sim=false`，磁盘无 APK 可对账）与 H7；`check:round12` **8/8（exit 0）**。与 R14-1 §0.3、R14-2 §0.1 的取证链逐字吻合：**任何干净 VM 不照方抓药就是 6/8 → round14-H8 连锁红**。终验 VM（#18）跑探针前必须先执行 §0.2。

### 0.2 P1 处方实操（本 VM 第三次独立验证，全程约 13 分钟）

1. `npm ci`（exit 0）；
2. `apt-get update && apt-get install openjdk-17-jdk-headless`（注意：不先 update 会 `Unable to locate package`）；
3. `dl.google.com` 下载 cmdline-tools（`commandlinetools-linux-11076708`）至 `/opt/android-sdk`，`sdkmanager` 装 `platform-tools` + `platforms;android-34` + `build-tools;34.0.0`；
4. `ANDROID_HOME=/opt/android-sdk JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 npm run android:sim`——本 VM 实测 **715,883 ms（11 分 56 秒）exit 0**：识字 APK **37,318,390 B**（较 R14-2 的 36,222,797 B 增大，因 14-2 合入 9 首范唱 + 24 个 L1 朗读资产随包）、数学 APK **4,261,565 B** 落盘，`report.json`（commit `18d6e4c`）SHA256 对账刷新，识字 164 路由 / 数学 20 路由 smoke 双双 0 问题；
5. 复跑三探针（§0.3）。刷新的 `evidence/r13/android-sim/` 六文件按既有惯例（`7b7cf73`/`7a2402e`/`b50e7a1`/`8d8c83a` 四次先例）随本终审提交，APK 本体照旧不入库。

### 0.3 处方后复跑（verbatim）

`npm run check:round14`（exit **1**，**3/8**）：

```
> hongen-edu-apps@1.0.0 check:round14
> node scripts/check-round14.mjs

  ✓ H3 绘本密度 404 页 scene（≥400）+ 渲染 + ROUND14_H3
  ✓ H5 L1 朗读批次：24 资产 + 文档 + ROUND14_H5_SMOKE
  ✓ H8 往轮不退化：round12 8/8 + round13 7/8

  ✗ H1 ASR 体验未放行：available=false，recorded=0/300，release=false，deviceRtf=false，harness=true，smoke=true —— r14-literacy-asr-finalize
  ✗ H2 OCR 体验未闭环：app=40/41，ocrSection=true，deviceB=false，queue=true，reflux=true，harness=true —— r14-literacy-ocr-device-b
  ✗ H4 范唱未全库：songs=13，humanVocal=9/13，doc=true —— r14-literacy-vocal-full
  ✗ H6 真机未签核：signoff=false，decision=false，record=true，noR13SimPath=true —— r14-android-device-matrix
  ✗ H7 商店内测未闭环：submit=false —— r14-store-internal-test

Round 14 体验门禁：3/8 项通过，5 项失败。
说明：R14 功能分支未全部合并时 FAIL 属预期红灯；体验 flip 目标 7/8 或 8/8。
```

`npm run check:round13`（exit **1**，**7/8**）：

```
> hongen-edu-apps@1.0.0 check:round13
> node scripts/check-round13.mjs

  ✓ H1 ASR 放行：files[] 落盘 37022120B + 放行/冻结集腿 + harness + ROUND13_H1_SMOKE
  ✓ H2 OCR Android 模拟 + 失败回流设计 + harness ROUND13_H2
  ✓ H3 绘本终局 404 页 scene（≥200）+ 渲染接线 + ROUND13_H3
  ✓ H4 范唱批次 12 首（≥3）+ 13/13 音频 + ROUND13_H4
  ✓ H5 lift 准实验口径 + ROUND13_H5_SMOKE
  ✓ H6 Android 模拟：双 APK 落盘 + 证据日志 + 签核文档 + ROUND13_H6 harness
  ✓ H8 Round 12 门禁 8/8 无退化

  ✗ H7 商店实提未闭环：submit=false —— r13-store-submit

Round 13 终局门禁：7/8 项通过，1 项失败。
说明：R13 功能分支未全部合并时 FAIL 属预期红灯；集成后必须 8/8。
```

`npm run check:round12`（exit **0**，**8/8**）：

```
> hongen-edu-apps@1.0.0 check:round12
> node scripts/check-round12.mjs

  ✓ H1 ASR 落库：files[] 落盘校验 37022120B + R12 落库 Go/No-Go + harness + ROUND12_H1_SMOKE
  ✓ H2 OCR 系统化 10 张 + 授权 10 条 + tier 10 + harness + ROUND12_H2
  ✓ H3 绘本场景铺开 404 页（≥60）+ 渲染接线 + ROUND12_H3
  ✓ H4 儿歌 13/13（音频 13）+ 范唱试点 + ROUND12_H4
  ✓ H5 推荐度量 + 开练 34 节点覆盖 + ROUND12_H5_SMOKE
  ✓ H6 evidence/r12 mobile LH 2 份（P≥95）+ 真机通道定案文档
  ✓ H7 TTS 试点（true）或 商店提交演练 + R12 反馈运行（true）
  ✓ H8 Round 11 门禁 8/8 无退化

Round 12 全量落地门禁：8/8 项通过，0 项失败。
```

链式旁证：`npm test` 本 VM 实跑 **exit 0 全绿**（feedback + 识字 + 数学三套）。

---

## 1. 6◐ 收窄表：R14-1 基线（`0d70870`）→ R14-2 起点（`c33caf4`）→ 本轮终审（`18d6e4c`）

一手数字（本 VM 探针同口径复测）：绘本 **132 本 / 1121 页 / scene 404 页 / 60 本带 scene**（209→404、33→60）；儿歌 **13 首 / humanStudio 9（sg4、sg6–sg13，vocal 全部 ≥10,240 B 实测落盘）**；ASR `manifest.available=false`、冻结集 100 槽、recorded **0**；OCR 回流队列 **5 条（4 closed + 1 engine-limit，零逾期）**；`public/audio/tts-l1/` **24 个 ogg（探针口径 ≥4,096 B 全过）+ manifest**；`evidence/r14/` 现有 `ocr/`、`asr/`、`android/` 三子目录，其中 asr/android 内为**诚实占位**（`device-rtf.json` status `not-measured`·`onDevice:false`；`ocr-device-b.skip.json` status `skipped`·exit 2），无一伪造。

| ◐ 模块 | 探针 | 子信号轨迹（R14-1 → R14-2 → 本轮） | 收窄判定 |
|---|---|---|---|
| L-M5 绘本 | H3 | scene 209 → 209 → **404**；带 scene 书 33 → 33 → **60**（第 2 级铺满 + 第 3 级九本）；`ROUND14_H3` 落 books.js + smoke；**探针格集成线首绿** | **探针格 flip，体验口径记「大幅收窄」不记 ✅**——BRIEF 明文全库 1121 归 R15；W3（随机 10 页 ≥9 页多元素）代理可达，归 #17 勾选 |
| L-M9 跟读 | H1 | harness/smoke 绿（14-1 遗产）；冻结集 58 → 100 → 100 槽；14-2 新增**放行收货台**（`r14-followread-release.md` 诚实 NO-GO 卡 12 处 + 文档/数据互锁：recorded<300 时锚点词禁现，探针 release 腿被设计性压红）+ RTF 证据契约（schema + example + `check:asr:device-rtf` 校验器，校验器严于探针）；available/recorded/deviceRtf **0→0→0 零证据** | **收窄工具与互锁腿，核心三腿全押供给**：recorded 供给 (b)、deviceRtf 供给 (a)、available 被 G1 收货台闸住——无真机 + 无实录时 H1 红是**设计正确**的红 |
| L-M10 OCR | H2 | app 0/41 → 40/41 → 40/41；queue/reflux/harness 绿保持；14-2 新增 **B 段真机全链路**（三 npm 入口 + `ocr-device-b.schema.json` 自洽性门禁 + 无设备 exit 2 SKIP 单列 + `ocr-device-b.skip.json` 台账带 adb 实跑出处）；deviceB false 保持 | **全线最接近 flip 不变（5/6 腿）**：工程侧已无剩余工作，唯一缺口 = 实体设备（供给 a）；设备到手当天可翻 |
| L-M11 儿歌 | H4 | humanVocal 0/13 → 0/13 → **9/13**（sg4、sg6–sg13，真人棚录元音源 + 旋律适配，73,861–108,899 B 逐首落盘 + SHA-256 清单）；`r14-songs-vocal-full.md` 落库且**诚实记 9/13**、sg1/sg3/sg5 旧 Piper 未虚标 | **收窄 9/13，且证伪了「范唱必须外部供给」**：14-2 用真人声源资产（非 Piper/TTS）走通了代理可达路径——剩 4 首（sg1/sg2/sg3/sg5）归 #14，H4 是本轮唯一在途的探针格 flip |
| L-M15 识字真机 | H6 | record 绿（`r14-android-device-record.md`）+ noR13SimPath 绿（v1.1 隔离闸）保持；14-2 新增 `android:device:qa` 无设备 exit 2 SKIP 路径（「No QA pass or device-signoff.json was produced.」实跑留痕）；signoff/decision **零证据不变**，`evidence/r14/android/` 仅 schema + skip 台账 | **工具腿闭合，签核三腿（signoff JSON / GO 定案 / ≥2 台真机）全押供给 (a)**：无真机时 NO-GO 延续是唯一诚实态 |
| M-M16 数学真机 | H6 | 与 L-M15 完全同源；数学 APK 本轮第三次重建 **4,261,565 B**、20 路由 smoke 0 问题、mobile LH 0.95 底子未动 | 同上，随 L-M15 共判 |

X1（H5，非 6◐ 但在探针内）：assets 0 → 0 → **24**、doc/smoke 绿，**探针格集成线首绿**；W5 听感抽查归 #17。

**flip 对账（对 R14-2 §4 预判）**：预判「3/8 稳（H8 处方就绪 + H3 高置信 + H5 高置信）」——本轮逐格兑现为实测 3/8；预判「H1 双供给依赖、H4 供给依赖、H6 供给依赖、H7 供给依赖」——H4 一项被 14-2 的真人声源路径部分证伪（详 §3），其余三项维持。**零欠交、零空转、零 flip 虚报。**

---

## 2. H1 / H2 / H6 / H7 诚实 BLOCKED 台账（owner + 解阻路径 + 签字接受）

三类外部供给（沿 R14-2 §3-S2 建模）：**(a) 实体 Android 设备**（≥2 台，一台低档）；**(b) 真人音频资产**（300 条儿童实录双标注）；**(c) Play Console 账号**（有权限、启用 MFA）。三类均不在任何子代理可达范围内，也不存在合规替代品（合成充实录、sim 充真机、无回执充 SUBMITTED 均为 BRIEF 明令红线）。

| 探针 | 缺口腿（探针子信号） | 供给类 | owner | 解阻路径（供给到位后的既定动线） | 签字接受口径（无真机收口时） |
|---|---|---|---|---|---|
| **H1** | `recorded=0/300`、`available=false`（被 G1 收货台闸住）、`deviceRtf=false`（诚实占位 `not-measured`） | **(b)+(a)** | 实录批次：产品/内容侧（监护人授权的儿童录音供给，属用户）；deviceRtf 与五类故障演练：Android QA（`device-rtf.json` 台账在案） | `r14-followread-release.md` §6 既定五步：实录 ≥300 → 双标注 → 过 `test-asr-eval-set.mjs` 收货台（G1）→ 真机按 `device-rtf.schema.json` 实测并过 `check:asr:device-rtf` → 文档锚点词翻 GO、flip `available:true` | 用户签字确认：**接受 H1 红灯收口 R14**，L-M9 记「收窄（跑道全就位）」；供给 (a)(b) 作为 R15 前置条件显式移交，任何一类先到即可推进对应腿，**禁止**为收口改动收货台互锁 |
| **H2** | `deviceB=false`（五腿已绿，`ocr-device-b.skip.json` exit 2 台账在案） | **(a)** | Android QA（skip 台账 owner 栏在案）；设备供给：用户 | 真机 + adb 授权 → 跑 B 段三入口（npm scripts 已接线）→ `evidence/r14/android/ocr-device-b.json` 落 `pass:true + onDevice:true + simulated:false`（schema 自洽性门禁自动把关）→ H2 当天翻绿 | 用户签字确认：**接受 H2 红灯收口 R14**，L-M10 记「收窄 5/6 腿、设备到手即翻」；SKIP 台账（exit 2 + 无设备实证）作为诚实证据留档，**禁止**用 r13 sim 数据或本 VM 结果填 `evidence/r14/android/` |
| **H6** | `signoff=false`（需 ≥2 台真机 JSON）、`decision=false`（现行定案 NO-GO，无 r14 版 GO 文档） | **(a)** | Android QA + 发布负责人；设备供给：用户 | ≥2 台真机（含低档机，#16 的回归清单为既定脚本）→ `android:device:qa` 产 `device-signoff.json`（`pass+onDevice+simulated:false+devices≥2`）→ 30 分钟离线走查（W6 前半）→ `r14-android-device-decision.md` 落 GO（>600 字 + `ROUND14_H6`，结论区无 NO-GO/BLOCKED） | 用户签字确认：**接受 H6 红灯 + NO-GO 定案延续收口 R14**，L-M15/M-M16 记「收窄（sim 全绿 + QA harness 闭合）」；sim 证据永留 `evidence/r13/android-sim/`，noR13SimPath 隔离闸持续把守 |
| **H7** | `submit=false`（`r14-store-submission-record.md` 未落库，属 #15 在途交付） | **(c)** | 发布负责人（用户）；BLOCKED 收口文档：#15（gpt-sol） | `r13-store-submission-record.md` §5 六条件（身份与权限 / Play App Signing / 政策表单 / 测试者名单 / Review 无阻断 / 双人签字）逐条清零 → Console 接收 release + QA opt-in 安装 → 状态 BLOCKED→READY→SUBMITTED/VERIFIED，追加不可变回执 | **沿 R13 已确立的签字接受先例**：#15 落 `r14-store-submission-record.md`（操作结论 BLOCKED + 六条件 unblock 清单 + `ROUND14_H7`），用户签字接受 H7 红灯收口——**禁止**无 Console 回执写 `状态：SUBMITTED`，禁止回写虚构值覆盖 BLOCKED 结论 |

**台账的完备性自证**：四格的「工程可达部分」在 14-1/14-2 已全部做完（H1 收货台与契约、H2 五腿与 B 段链路、H6 harness 与隔离闸、H7 的 R13 级提交手册），本轮终审逐一实查无一遗漏——**剩余红灯全部且仅仅卡在 (a)(b)(c) 三类供给**。签字接受不是降杆：探针保持红、evidence 保持诚实占位、解阻动线全部预置，供给到位后每格都是「当天可翻」而非「重新开工」。

---

## 3. 无真机终态目标声明：`check:round14` = 4/8

**声明**：Round 14 在「无真机收口」决策下的终态目标为 **4/8 = H3 + H4 + H5 + H8**（ROUND14-3-BRIEF 目标行）。本轮终审对该数字的置信度拆解：

- **已实测 3/8**（H3+H5+H8，§0.3 verbatim）：H3/H5 数据与标记全在库、与在途分支无耦合；H8 依赖终验 VM 照 §0.2 处方重建 APK（第三次验证，处方稳定）。
- **+1 格 = H4，唯一在途的代理可达 flip**：#14 补 sg1/sg2/sg3/sg5 四首真人声源范唱 + 更新 `r14-songs-vocal-full.md` 至 13/13 + 许可留痕。14-2 已用同一路径落 9 首（真人棚录元音源，非 Piper/TTS，逐首 SHA-256 在案），技术与素材路径均已验证——H4 flip 属高置信。
- **上限修正的依据**：R14-2 §3-S2 曾把三类供给全缺时的上限定为 3/8，其中把「真人音频资产 (b)」整类划为外部供给。14-2 的实践把 (b) 拆成两半：**儿歌范唱可用合规真人声源资产代理达成**（已落 9 首），**儿童跟读实录不可**（涉及儿童真人录音与监护人授权，代理零可达）。故无真机诚实上限从 3/8 上修至 **4/8**，且到此为止——5/8 起步需要供给 (a)。
- **4/8 不是欠交**：BRIEF 14-3 原目标「7/8 或 8/8」隐含三类供给到位；用户 2026-08-28 已明确决策无真机收口。**#18 集成收官与 `acceptance-log-round14.md` 回填应按 4/8 + 签字接受台账（§2）记收口状态，模板里的「[待填：7/8 或 8/8]」按本声明改口径**，不得为凑数伪造 evidence（探针的 simulated/onDevice/noR13SimPath 三重闸 + 收货台互锁会拦，但防绕行意识仍须人审）。
- **W1–W6 分栏**（#17 执行）：**W3/W5 代理可达**（H3/H5 已绿，随走查勾选）；**W1/W2/W6 供给依赖**（真机/实录，随 §2 台账 BLOCKED）；**W4 特殊**——#14 后 13/13 探针绿，但「盲听可接受真人主唱」的裁量属用户：范唱是「真人声源元音范唱」（示范音高/节拍/换气，非中文歌词演唱，界面已如实标注），盲听按此定义裁量，接受则 L-M11 记 flip，不接受则记「收窄至待 IP 化演唱（R15）」。
- **体验口径终态预判**：签字收口时 **25✅/6◐**（零 flip 虚报口径）；若用户 W4 盲听接受则 **26✅/5◐**。六 ◐ 全部带「大幅收窄」注记（§1 表），与 R14-2 §4「收窄要如实记收窄，防『原地』被误读为『空转』」的要求一致。
- **R15 移交面**：供给征集清单 (a)(b)(c)（§2 台账 owner 栏）作为 R15 前置条件显式移交；绘本 404→1121 全库分批；ASR 实录双标注成色复审；范唱 IP 化演唱；低档机常态回归（#16 清单为底稿）。

---

## 4. 审计方法备注

- 实跑：`/workspace` @ `18d6e4c` 干净检出（分支 `cursor/r14-final-audit-9f67`）→ `npm ci`（exit 0）→ 首跑三探针（§0.1：r14 2/8 · r13 6/8 exit 1 · r12 8/8 exit 0）→ §0.2 处方（JDK 17.0.20 + cmdline-tools 11076708 + SDK 34 自装约 1 分钟，`android:sim` 715,883 ms exit 0）→ 复跑三探针（§0.3：r14 3/8 exit 1 · r13 7/8 exit 1 · r12 8/8 exit 0）→ `npm test` exit 0。
- 一手计数：探针同口径 import `books.js`（132/1121/404/60）与 `songs.js`（13 首 / humanStudio 9 / vocal ≥10,240 B 逐首 `fs.statSync` 实测）；`fs` 实读 `manifest.json`（available:false / files 7）、`asr-eval-set.json`（clips 100 / recorded 0）、`regressions/queue.json`（4 closed + 1 engine-limit）、`device-rtf.json`（not-measured / onDevice:false）、`ocr-device-b.skip.json`（skipped / exit 2 / device null）、刷新后 `report.json`（commit 18d6e4c / APK 37,318,390 B + 4,261,565 B）；`ls` 实证 `tts-l1/` 24 ogg + manifest、`evidence/r14/` 三子目录内容。
- 引用而非重测：R14-1 审计（`0d70870` 基线列）、R14-2 审计（`c33caf4` 中间列 + §0.2 处方 + §3-S2 供给建模）、`r14-followread-release.md` 的 12 处阻塞清单、`r13-store-submission-record.md` §5 六条件。
- 边界：本终审只审集成线 HEAD，**不预支 #14–#18 在途分支内容**；§3 对 H4 的「+1 格」是预判并给出判据，不是替 #14 记账。刷新的 `evidence/r13/android-sim/` 六文件随本终审按先例提交，APK 本体不入库。
