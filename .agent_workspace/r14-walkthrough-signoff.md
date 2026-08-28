Model slug: claude-fable-5

# Round 14 · W1–W6 手动走查分栏与签字台账（无真机收口版）

标记：`ROUND14_W_SIGNOFF`

> 路：Round 14-3 #17（fable，分支 `cursor/r14-walkthrough-signoff-9f67`）
> 基线：集成线 `cursor/openmoji-integration-9f67` @ `18d6e4c` · 2026-08-28 · Node v22.14.0
> 依据：`ROUND14-ACCEPTANCE.md` §3（W1–W6 定义）+ G7（体验走查 6/6 + owner 签字）；`ROUND14-2-CONCLUSION-BRIEF.md` §4-(3)（W3/W5 代理可达、W1/W2/W4/W6 供给依赖的分栏指令）；`ROUND14-3-BRIEF.md` 用户决策（**无真机收口**——代理可达项收尾、外部供给标诚实 BLOCKED、禁伪造）
> 用途：#18 集成收官回填 `acceptance-log-round14.md` §4 勾选时，逐项引用本台账；签字登记在本文件 §4。

**结论先行**：W1–W6 分两栏。**栏 A（代理可达）W3、W5 两项本 VM 实测全绿、可勾**——W3 绘本 404 页 scene（132 本 / 1121 页无回归，随机 10 页抽查 10/10），W5 L1 朗读 24/24 资产逐个 ffprobe 可解码 + 点读接线在位。**栏 B（供给依赖）W1、W2、W4、W6 四项保持未勾**，逐项记子信号现状、缺口类别（a 实体设备 / b 真人音频 / c Play 账号）、签字 owner 与解阻条件。无真机收口下 G7 的诚实上限即 **2/6 勾 + 4/6 BLOCKED 台账**，不得用签字把未勾项改勾。

---

## 0. 基线探针快照（本 VM 实跑，退出码为准）

`npm run check:round14` @ `18d6e4c` 首跑：**3/8**（H3 + H5 + H8 绿），与 ROUND14-3-BRIEF「无真机诚实上限 4/8」的差距仅剩 H4（humanVocal 9/13，#14 在途补 4 首）。与 W 走查直接相关的两行 verbatim（本 VM 两次实跑均稳定为绿）：

```
  ✓ H3 绘本密度 404 页 scene（≥400）+ 渲染 + ROUND14_H3
  ✓ H5 L1 朗读批次：24 资产 + 文档 + ROUND14_H5_SMOKE
```

环境备注：本 VM 为编排共用长驻机，复跑窗口内观察到并行 APK 重建活动（gradle daemon 在跑、`apps/*/android/app/build` 中途被清），H8 行随 APK 落盘状态在 绿↔红 间波动——即 14-2 简报 P1 已实证的「H6/H8 对构建产物环境敏感」，处方见其 §0.2，终验 VM 跑探针前须先重建 APK。该波动不影响本台账：H3/H5 是内容探针，不依赖 APK。

---

## 1. 栏 A：代理可达（W3 / W5）——本 VM 实测，可勾

### W3 绘本观感（≥400 scene 页 + 旧页不回归）—— [x] 可勾

判据（`ROUND14-ACCEPTANCE.md` §3 + 14-2 简报 §2-#9 的 W3 预演口径：随机 10 页抽查 ≥9 页多元素）。本 VM 一次性核验脚本实跑输出 verbatim：

```
W3.1 books=132 totalPages=1121 scenePages(>=2 obj els)=404
W3.2 旧页回归口径: books>=132 true / totalPages>=1121 true / scenePages>=400 true
W3.3 随机 10 页抽查（seed=14317）: 10/10（判据 ≥9）
W3.4 渲染接线: BookPageScene.vue 4492B; BookReadView 引用 scene=true; 引用 BookPageScene=true
```

- **404 scene 页**：探针同口径（页内 ≥2 个对象元素，import `books.js` 实数），132 本 / 1121 页总量与 R13 基线（132/1121/209）相比只增不减——旧 209 页零回归，scene 覆盖 209→404。
- **随机 10 页抽查 10/10**：线性同余伪随机（seed=14317，可复现），逐页核元素数 ≥2、`e` 为图形非汉字、`x/y` 在 0–100、`s` 在 0.4–3 档位、正文非空、`sceneAlt` 读屏句在位。抽中样本横跨手写核心本（b7/b11）与生成扩充本（bx13–bx49），无一页坏字段。
- **渲染接线**：`BookPageScene.vue` 组件实体 + `BookReadView.vue` 双引用，退化路径（无 scene 页走单 emoji）未动。

**代理实测边界**：结构、口径、接线、回归四腿均为客观可验项，本 VM 已收口；「观感」的主观终审（美感/年龄适配）留给 §4 签字 owner 在勾选确认时完成——若观感不过，按 14-2 先例记**收窄不记回退**，不推翻探针绿。

### W5 L1 朗读（字卡听感可接受）—— [x] 可勾

判据（`ROUND14-ACCEPTANCE.md` §3「W5 L1 朗读：字卡听感可接受」+ 14-2 简报 §2-#11 红线：资产可播放非空壳、逐个 ≥1KB 级抽查）。本 VM 实跑输出 verbatim：

```
W5.1 资产: 磁盘音频=24（判据 ≥20）; manifest.files=24; marker=ROUND14_H5
W5.2 manifest↔磁盘对账: manifest 缺盘=0 盘缺 manifest=0
W5.3 逐资产 ffprobe: 24/24 可解码 opus 且 >0.3s; size 最小=5851B; 时长 0.93–2.88s; 异常=无
W5.4 覆盖: unit=u1 cardCount=12 kinds={"character":12,"sentence":12}
W5.5 标记: smoke ROUND14_H5_SMOKE=true; 文档 ROUND14_H5=true
```

- **24/24 逐资产核验**：不止字节数抽查——每个文件过 `ffprobe`，Ogg/Opus 全部可解码、时长 0.93–2.88 秒（字卡「字 + 例句」双档合理区间）、最小 5,851 B（远超 4,096 B 探针地板与 1KB 红线）。
- **manifest 对账零缺**：`manifest.json`（Kokoro-82M-v1.1-zh，Apache-2.0，参数与 SHA 留痕）声明的 24 条与磁盘一一对上，u1 单元 12 张字卡 × (character + sentence) 全覆盖。
- **点读接线**：`src/utils/offlineTts.js` 按 `audio/tts-l1/` 路径供片，`CharDetailView.vue`（字卡点读）、`PoemDetailView.vue`、`App.vue` 三处引用——W5 的「L1 单元点读」用户路径可走通。
- 14-2 简报明文「BRIEF 允许真人**或**高质量离线 TTS，H5 是代理可达的一格」，故 W5 与 H3 同理属栏 A。

**代理实测边界**：可播放性、覆盖、接线客观收口；「听感可接受」的主观终审留给 §4 签字 owner——若听感不过，按 14-2 §2-#11 红线**记收窄不记 flip**。

---

## 2. 栏 B：供给依赖（W1 / W2 / W4 / W6）——保持未勾，诚实 BLOCKED

缺口类别沿 14-2 简报 §3-S2：**(a) 实体 Android 设备 · (b) 真人音频资产 · (c) Play 账号**。子信号为本 VM `check:round14` @ `18d6e4c` 实跑值。

| 项 | 定义（R14 §3） | 子信号现状（工程腿 vs 供给腿） | 缺口 | 签字 owner | 解阻条件（勾选前置） |
|---|---|---|---|---|---|
| W1 ASR 体验 | 跟读实时反馈，非回放 | 工程腿绿：harness=true、smoke=true、冻结集 100 槽在库；供给腿零：recorded **0/300**、available=false、release=false、deviceRtf=false | (b)+(a) | **儿童实录供给 owner（含监护人授权）** + **Android QA**（真机 RTF） | ≥300 条儿童实录落库（禁合成/成人代录，W1 盲测防）→ available flip → 真机 RTF p95≤0.5 → GO 放行文档 |
| W2 OCR 体验 | 真机拍照 + 回流路径可演示 | 五腿绿：app 40/41、ocrSection=true、queue=true（4 closed + 1 engine-limit 无逾期）、reflux=true、harness=true；仅 deviceB=false | (a) | **Android QA**（设备持有人） | 实体设备跑 `test-ocr-device.mjs` B 段 → `evidence/r14/android/ocr-device-b.json` 落 `pass:true + onDevice:true + simulated:false`（禁 sim 结果冒充，noR13SimPath 闸在位） |
| W4 范唱全库 | 13 首真人主唱 | humanVocal **9/13**（sg4、sg6–sg13，VocalSet CC-BY 4.0 真人声源「啊」音范唱，许可留痕）、doc=true；余 sg1/sg2/sg3/sg5 由 14-3 #14 在途补齐 | (b) | **音频内容 owner**（盲听终审） | #14 合入后探针腿 13/13；勾选前 owner 盲听抽查确认真人声源非换标（14-2 红线：humanStudio:true 仅限真人演播资产）；中文歌词演唱版属 R15「范唱 IP 化」交接面 |
| W6 真机/商店 | 真机 evidence + Console 回执（非 BLOCKED） | simulated 声明已核（R13 先例延续）、record=true、noR13SimPath=true；signoff=false、decision=false、submit=false（H7 BLOCKED，签字接受路径见 `r14-store-submission-record.md` §3） | (a)+(c) | **Android QA**（2 台真机签核） + **发布负责人**（Play Console 账号持有人） | 真机腿：`device-signoff.json`（≥2 devices + onDevice:true + simulated:false）+ GO 定案；商店腿：真实 Console 回执（日期/版本/处理状态），**签字接受 4/8 不使本项转勾** |

红线（继承 ROUND14-3-BRIEF「禁止」节）：禁写 `onDevice:true`/`simulated:false` 假证据、禁 H7 无回执标 SUBMITTED、禁 recorded=0 时 flip `available:true`。栏 B 四项在供给到位前**保持未勾即是合格交付**，不是欠交。

---

## 3. 与 G7 门禁的关系

`ROUND14-ACCEPTANCE.md` G7 要求「W1–W6 人工勾选 6/6 + owner 签字」。无真机收口决策下：

- **诚实上限 = 栏 A 2/6 勾**（W3/W5，代理实测 + owner 确认签字）**+ 栏 B 4/6 BLOCKED 台账**（owner/解阻/签字接受口径齐备）。
- G7 因此在 R14 **不判 PASS**，与 `check:round14` 目标 4/8 同构——这是口径内的诚实红，#18 集成收官照实回填 `acceptance-log-round14.md` §4（W3/W5 勾 + 引用本文件，W1/W2/W4/W6 留空 + 引用 §2 台账），不得为凑 6/6 虚勾。
- 若用户按 `r14-store-submission-record.md` §3 路径 A 签字接受 R14 以 4/8 收口，该签字覆盖的是**轮次终态**，不改写本台账任何一格的勾选状态。

## 4. 签字登记

签字是对「勾选状态与台账口径」的验收确认，本轮没有代替任何人签字；空白字段不视为接受证据（沿 `r14-store-submission-record.md` §3 登记口径）。

| 项 | 栏 | 勾选状态 | 签字 owner（角色） | 签字（姓名/身份 + UTC 日期 + 引用日志） |
|---|---|---|---|---|
| W1 | B 供给依赖 | ☐ 未勾（BLOCKED） | 儿童实录供给 owner + Android QA | _待填_ |
| W2 | B 供给依赖 | ☐ 未勾（BLOCKED） | Android QA | _待填_ |
| W3 | A 代理可达 | ☑ 可勾（本 VM 实测 §1） | 项目验收人（观感终审） | _待填_ |
| W4 | B 供给依赖 | ☐ 未勾（9/13 在途） | 音频内容 owner（盲听终审） | _待填_ |
| W5 | A 代理可达 | ☑ 可勾（本 VM 实测 §1） | 项目验收人（听感终审） | _待填_ |
| W6 | B 供给依赖 | ☐ 未勾（BLOCKED） | Android QA + 发布负责人 | _待填_ |

## 5. 复现口径

- 探针：`npm run check:round14`（H3/H5 行）。
- W3：import `apps/literacy-app/src/data/books.js`，统计页内 ≥2 对象元素的页数；线性同余伪随机 `seed=14317`（`seed = (seed*1103515245+12345) % 2^31`）从 scene 页序列抽 10 页，逐页核元素数 / `e` 非汉字 / `x,y∈[0,100]` / `s∈[0.4,3]` / 正文与 `sceneAlt`。
- W5：`ls apps/literacy-app/public/audio/tts-l1/*.ogg` 逐个 `ffprobe -show_entries format=duration:stream=codec_name`；与 `manifest.json` `files[]` 双向对账；`rg ROUND14_H5_SMOKE apps/literacy-app/scripts/smoke.mjs`。
- 接线：`rg tts-l1 apps/literacy-app/src` → `offlineTts.js`；`rg offlineTts apps/literacy-app/src` → CharDetailView / PoemDetailView / App。
