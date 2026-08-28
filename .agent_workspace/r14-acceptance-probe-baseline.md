# Round 14 v1.1 验收探针取证

> 模型 slug：`gpt-5.6-sol-xhigh-fast`
> 分支：`cursor/r14-acceptance-spec-9f67`
> 探针提交：`869e726`
> 日期：2026-08-28 UTC

## 0. 环境前置说明

干净 checkout 首跑没有 gitignored 双 APK，故 `check:round13` 的 H6 哈希落盘腿为红，连带 `check:round14` H8 为红（0/8）。这不是 v1.1 逻辑变化：安装锁文件依赖与 Android 34 SDK、执行 `build:all`/`sync:android` 并运行 `npm run android:sim` 刷新 R13 证据后，三轮基线恢复到规格值。正验包装器退出前恢复了 R13 tracked evidence；APK 仍为忽略产物，不纳入提交。

刷新结果：

```text
ANDROID EVIDENCE REFRESH: npm run android:sim [exit 0]
```

## 1. 基线三轮实跑（verbatim）

### `npm run check:round14`

```text
> hongen-edu-apps@1.0.0 check:round14
> node scripts/check-round14.mjs

  ✓ H8 往轮不退化：round12 8/8 + round13 7/8

  ✗ H1 ASR 体验未放行：available=false，recorded=0/300，release=false，deviceRtf=false，harness=false，smoke=false —— r14-literacy-asr-finalize
  ✗ H2 OCR 体验未闭环：app=0/0，ocrSection=false，deviceB=false，queue=false，reflux=false，harness=false —— r14-literacy-ocr-device-b
  ✗ H3 绘本未达标：scenePages=209/400，rendered=true，ROUND14_H3=false —— r14-literacy-books-batch2
  ✗ H4 范唱未全库：songs=13，humanVocal=0/13，doc=false —— r14-literacy-vocal-full
  ✗ H5 L1 朗读未闭环：assets=0/20，doc=false，smoke=false —— r14-literacy-tts-l1
  ✗ H6 真机未签核：signoff=false，decision=false，record=false，noR13SimPath=true —— r14-android-device-matrix
  ✗ H7 商店内测未闭环：submit=false —— r14-store-internal-test

Round 14 体验门禁：1/8 项通过，7 项失败。
说明：R14 功能分支未全部合并时 FAIL 属预期红灯；体验 flip 目标 7/8 或 8/8。
[exit 1]
```

### `npm run check:round13`

```text
> hongen-edu-apps@1.0.0 check:round13
> node scripts/check-round13.mjs

  ✓ H1 ASR 放行：files[] 落盘 37022120B + 放行/冻结集腿 + harness + ROUND13_H1_SMOKE
  ✓ H2 OCR Android 模拟 + 失败回流设计 + harness ROUND13_H2
  ✓ H3 绘本终局 209 页 scene（≥200）+ 渲染接线 + ROUND13_H3
  ✓ H4 范唱批次 3 首（≥3）+ 13/13 音频 + ROUND13_H4
  ✓ H5 lift 准实验口径 + ROUND13_H5_SMOKE
  ✓ H6 Android 模拟：双 APK 落盘 + 证据日志 + 签核文档 + ROUND13_H6 harness
  ✓ H8 Round 12 门禁 8/8 无退化

  ✗ H7 商店实提未闭环：submit=false —— r13-store-submit

Round 13 终局门禁：7/8 项通过，1 项失败。
说明：R13 功能分支未全部合并时 FAIL 属预期红灯；集成后必须 8/8。
[exit 1]
```

### `npm run check:round12`

```text
> hongen-edu-apps@1.0.0 check:round12
> node scripts/check-round12.mjs

  ✓ H1 ASR 落库：files[] 落盘校验 37022120B + R12 落库 Go/No-Go + harness + ROUND12_H1_SMOKE
  ✓ H2 OCR 系统化 10 张 + 授权 10 条 + tier 10 + harness + ROUND12_H2
  ✓ H3 绘本场景铺开 209 页（≥60）+ 渲染接线 + ROUND12_H3
  ✓ H4 儿歌 13/13（音频 13）+ 范唱试点 + ROUND12_H4
  ✓ H5 推荐度量 + 开练 34 节点覆盖 + ROUND12_H5_SMOKE
  ✓ H6 evidence/r12 mobile LH 2 份（P≥95）+ 真机通道定案文档
  ✓ H7 TTS 试点（true）或 商店提交演练 + R12 反馈运行（true）
  ✓ H8 Round 11 门禁 8/8 无退化

Round 12 全量落地门禁：8/8 项通过，0 项失败。
[exit 0]
```

### `node scripts/check-round14.mjs --json`

```json
{
  "passed": 1,
  "failed": 7,
  "results": [
    {
      "id": "H1",
      "status": "fail",
      "msg": "H1 ASR 体验未放行：available=false，recorded=0/300，release=false，deviceRtf=false，harness=false，smoke=false —— r14-literacy-asr-finalize"
    },
    {
      "id": "H2",
      "status": "fail",
      "msg": "H2 OCR 体验未闭环：app=0/0，ocrSection=false，deviceB=false，queue=false，reflux=false，harness=false —— r14-literacy-ocr-device-b"
    },
    {
      "id": "H3",
      "status": "fail",
      "msg": "H3 绘本未达标：scenePages=209/400，rendered=true，ROUND14_H3=false —— r14-literacy-books-batch2"
    },
    {
      "id": "H4",
      "status": "fail",
      "msg": "H4 范唱未全库：songs=13，humanVocal=0/13，doc=false —— r14-literacy-vocal-full"
    },
    {
      "id": "H5",
      "status": "fail",
      "msg": "H5 L1 朗读未闭环：assets=0/20，doc=false，smoke=false —— r14-literacy-tts-l1"
    },
    {
      "id": "H6",
      "status": "fail",
      "msg": "H6 真机未签核：signoff=false，decision=false，record=false，noR13SimPath=true —— r14-android-device-matrix"
    },
    {
      "id": "H7",
      "status": "fail",
      "msg": "H7 商店内测未闭环：submit=false —— r14-store-internal-test"
    },
    {
      "id": "H8",
      "status": "pass",
      "msg": "H8 往轮不退化：round12 8/8 + round13 7/8"
    }
  ]
}
[exit 1]
```

断言：`passed=1`、`failed=7`、`results.length=8`、唯一 PASS 为 H8。

## 2. v1.1 正/负向实跑（verbatim）

方法：临时补齐 H1/H2/H6 的全部合规腿；四次执行都走真实 `check-round14.mjs --json`，每次固定八项。其他 H 保持基线。夹具在 `finally` 中逐字恢复。夹具替换 ASR eval-set 时会令嵌套 R13 H1 暂红，因此本节 H8 红是隔离夹具副作用，不影响第 1 节干净基线。

### 正向：H1/H2/H6 合规实体

```text
=== POSITIVE — H1/H2/H6 complete evidence ===
$ node scripts/check-round14.mjs --json
{
  "passed": 3,
  "failed": 5,
  "results": [
    {
      "id": "H1",
      "status": "pass",
      "msg": "H1 ASR 体验放行：available + recorded≥300 + 真机 RTF + ROUND14_H1"
    },
    {
      "id": "H2",
      "status": "pass",
      "msg": "H2 OCR 体验闭环：App 40/41 + 真机 B 段 + 队列 + ROUND14_H2"
    },
    {
      "id": "H3",
      "status": "fail",
      "msg": "H3 绘本未达标：scenePages=209/400，rendered=true，ROUND14_H3=false —— r14-literacy-books-batch2"
    },
    {
      "id": "H4",
      "status": "fail",
      "msg": "H4 范唱未全库：songs=13，humanVocal=0/13，doc=false —— r14-literacy-vocal-full"
    },
    {
      "id": "H5",
      "status": "fail",
      "msg": "H5 L1 朗读未闭环：assets=0/20，doc=false，smoke=false —— r14-literacy-tts-l1"
    },
    {
      "id": "H6",
      "status": "pass",
      "msg": "H6 真机签核：device-signoff + GO 定案 + 签核文档 + ROUND14_H6"
    },
    {
      "id": "H7",
      "status": "fail",
      "msg": "H7 商店内测未闭环：submit=false —— r14-store-internal-test"
    },
    {
      "id": "H8",
      "status": "fail",
      "msg": "H8 退化：round12=true，round13Pass=6/8"
    }
  ]
}
[exit 1]
```

### 负向 H1：删除 device 身份

```text
=== NEGATIVE H1 — device identity removed ===
$ node scripts/check-round14.mjs --json
{
  "passed": 2,
  "failed": 6,
  "results": [
    {
      "id": "H1",
      "status": "fail",
      "msg": "H1 ASR 体验未放行：available=true，recorded=300/300，release=true，deviceRtf=false，harness=true，smoke=true —— r14-literacy-asr-finalize"
    },
    {
      "id": "H2",
      "status": "pass",
      "msg": "H2 OCR 体验闭环：App 40/41 + 真机 B 段 + 队列 + ROUND14_H2"
    },
    {
      "id": "H3",
      "status": "fail",
      "msg": "H3 绘本未达标：scenePages=209/400，rendered=true，ROUND14_H3=false —— r14-literacy-books-batch2"
    },
    {
      "id": "H4",
      "status": "fail",
      "msg": "H4 范唱未全库：songs=13，humanVocal=0/13，doc=false —— r14-literacy-vocal-full"
    },
    {
      "id": "H5",
      "status": "fail",
      "msg": "H5 L1 朗读未闭环：assets=0/20，doc=false，smoke=false —— r14-literacy-tts-l1"
    },
    {
      "id": "H6",
      "status": "pass",
      "msg": "H6 真机签核：device-signoff + GO 定案 + 签核文档 + ROUND14_H6"
    },
    {
      "id": "H7",
      "status": "fail",
      "msg": "H7 商店内测未闭环：submit=false —— r14-store-internal-test"
    },
    {
      "id": "H8",
      "status": "fail",
      "msg": "H8 退化：round12=true，round13Pass=6/8"
    }
  ]
}
[exit 1]
```

### 负向 H2：空 ocrSection + 伪造 40/41 汇总

```text
=== NEGATIVE H2 — empty ocrSection with forged 40/41 aggregate ===
$ node scripts/check-round14.mjs --json
{
  "passed": 2,
  "failed": 6,
  "results": [
    {
      "id": "H1",
      "status": "pass",
      "msg": "H1 ASR 体验放行：available + recorded≥300 + 真机 RTF + ROUND14_H1"
    },
    {
      "id": "H2",
      "status": "fail",
      "msg": "H2 OCR 体验未闭环：app=0/0，ocrSection=false，deviceB=true，queue=true，reflux=true，harness=true —— r14-literacy-ocr-device-b"
    },
    {
      "id": "H3",
      "status": "fail",
      "msg": "H3 绘本未达标：scenePages=209/400，rendered=true，ROUND14_H3=false —— r14-literacy-books-batch2"
    },
    {
      "id": "H4",
      "status": "fail",
      "msg": "H4 范唱未全库：songs=13，humanVocal=0/13，doc=false —— r14-literacy-vocal-full"
    },
    {
      "id": "H5",
      "status": "fail",
      "msg": "H5 L1 朗读未闭环：assets=0/20，doc=false，smoke=false —— r14-literacy-tts-l1"
    },
    {
      "id": "H6",
      "status": "pass",
      "msg": "H6 真机签核：device-signoff + GO 定案 + 签核文档 + ROUND14_H6"
    },
    {
      "id": "H7",
      "status": "fail",
      "msg": "H7 商店内测未闭环：submit=false —— r14-store-internal-test"
    },
    {
      "id": "H8",
      "status": "fail",
      "msg": "H8 退化：round12=true，round13Pass=6/8"
    }
  ]
}
[exit 1]
```

### 负向 H6：注入 R13 android-sim 路径

```text
=== NEGATIVE H6 — r13 android-sim path injected ===
$ node scripts/check-round14.mjs --json
{
  "passed": 2,
  "failed": 6,
  "results": [
    {
      "id": "H1",
      "status": "pass",
      "msg": "H1 ASR 体验放行：available + recorded≥300 + 真机 RTF + ROUND14_H1"
    },
    {
      "id": "H2",
      "status": "pass",
      "msg": "H2 OCR 体验闭环：App 40/41 + 真机 B 段 + 队列 + ROUND14_H2"
    },
    {
      "id": "H3",
      "status": "fail",
      "msg": "H3 绘本未达标：scenePages=209/400，rendered=true，ROUND14_H3=false —— r14-literacy-books-batch2"
    },
    {
      "id": "H4",
      "status": "fail",
      "msg": "H4 范唱未全库：songs=13，humanVocal=0/13，doc=false —— r14-literacy-vocal-full"
    },
    {
      "id": "H5",
      "status": "fail",
      "msg": "H5 L1 朗读未闭环：assets=0/20，doc=false，smoke=false —— r14-literacy-tts-l1"
    },
    {
      "id": "H6",
      "status": "fail",
      "msg": "H6 真机未签核：signoff=true，decision=true，record=true，noR13SimPath=false —— r14-android-device-matrix"
    },
    {
      "id": "H7",
      "status": "fail",
      "msg": "H7 商店内测未闭环：submit=false —— r14-store-internal-test"
    },
    {
      "id": "H8",
      "status": "fail",
      "msg": "H8 退化：round12=true，round13Pass=6/8"
    }
  ]
}
[exit 1]
```

```text
PROBE ASSERTIONS: PASS (4 runs, each fixed at 8 results)
```

## 3. 结论

- H1：正向 PASS；仅删除 `device` 身份后 `deviceRtf=false`，FAIL。
- H2：正向 40/41 PASS；空 `ocrSection` 即使伪造顶层 40/41，`ocrSection=false`，FAIL。
- H6：正向 PASS；追加 R13 android-sim 路径后 `noR13SimPath=false`，FAIL。
- 基线：Round 14 **1/8（仅 H8）**；Round 13 **7/8**；Round 12 **8/8**。
- JSON：四组正/负向探针及基线均固定 `results.length=8`。
