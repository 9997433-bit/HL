# Round 2 中期性能报告

生成日期：2026-08-26（UTC）  
分支：`agent/audio-analysis-software`

## 结论

- Round 1 同构基线对比的 9 个指标全部落在 ±10% 稳定区间，没有性能回归项。
- 48 kHz / 128 frames 合成回调探针测得 p99 `0.844 ms`，低于 Rust 逃生舱
  `1.33 ms` 阈值；500 次回调未出现 deadline miss/underrun。
- **中期不建议立即迁移 Rust。** 该结论不能替代真实设备、实际效果链和 10 分钟
  soak；硬件测试若出现 p99 `> 1.33 ms` 或 underrun `> 0.1%`，应立即重新评估
  Rust/PyO3 实时内环。
- 云端仍为无音频设备的 degraded 环境。GUI 采用 Qt offscreen +
  `--null-audio --exit-after 5` 回退路径，冒烟测试通过。

## Round 1 基线增量

本次运行与 Round 1 使用相同 Python `3.12.3`、Linux 平台和 benchmark 配置
（FFT 2048×40、load repetitions 7、buffer 512），因此 delta 可直接比较。
`tools/perf-regression.py` 默认把不利变化超过 10% 标记为回归。

| 指标 | Round 1 | Round 2 中期 | Delta | 判定 |
|---|---:|---:|---:|---|
| 文件加载中位数 | 0.019336 ms | 0.019806 ms | +2.43% | stable |
| 文件加载聚合耗时 | 0.275555 ms | 0.264871 ms | -3.88% | stable |
| FFT elapsed | 0.084797 s | 0.083626 s | -1.38% | stable |
| FFT throughput | 471.715 transforms/s | 478.318 transforms/s | +1.40% | stable |
| FFT sample throughput | 966,073 samples/s | 979,595 samples/s | +1.40% | stable |
| Python peak allocation | 276,730 B | 276,780 B | +0.018% | stable |
| Process peak RSS | 20,021,248 B | 19,832,832 B | -0.94% | stable |
| 44.1 kHz startup estimate | 11.629059 ms | 11.629562 ms | +0.004% | stable |
| 48 kHz startup estimate | 10.686003 ms | 10.686539 ms | +0.005% | stable |

startup 项仍是“文件加载中位数 + 一个 512-frame 输出 buffer”的估算，不是设备
round-trip latency。

## 实时逃生舱探针

`tools/monitor-realtime.py --mode measure` 执行无第三方依赖的 32 轨 × 每轨 4 效果
合成热循环：

| 项目 | 结果 |
|---|---:|
| Callback budget（48 kHz / 128） | 2.667 ms |
| 样本数 | 500 callbacks |
| Mean | 0.815 ms |
| Median | 0.813 ms |
| p95 | 0.831 ms |
| p99 | 0.844 ms |
| p99 budget utilization | 31.63% |
| Deadline miss / underrun | 0 / 0（0.0%） |
| Rust migration recommendation | 否 |

脚本也支持确定性 simulation、导入 `durations_ms` 实测 JSON、注入 underrun，以及
`--fail-on-trigger` 门禁。判定使用严格大于：p99 `> 1.33 ms` 或 underrun
`> 0.1%`。

## CI 与可复现性

- `lint-and-test` 扩为 `ubuntu-latest`、`macos-latest`、`windows-latest` 矩阵，
  全局 `QT_QPA_PLATFORM=offscreen`，执行 Ruff 与两套 pytest。
- 独立 `gui-smoke` job 在 Ubuntu 启动 null-audio GUI 5 秒后自动退出。
- 独立 `performance-probes` job 生成当前 benchmark、Round 1 delta 和实时阈值报告，
  并上传 artifact。
- `.github/requirements.lock` 由 pip-tools/Python 3.12 生成，锁定 Qt、NumPy、
  SciPy、soundfile、pytest、pytest-qt、Ruff 及传递依赖。

本地验证：Ruff 通过；`371 passed in 1.77s`；5 秒 offscreen/null-audio GUI
冒烟退出码为 0。

## 未完成风险

1. 云端没有 CoreAudio/WASAPI/ALSA 实体设备，设备 I/O、驱动缓冲和 round-trip
   latency 均未测量。
2. 当前实时探针是合成 Python 热循环，不是完整应用 callback/实际插件链。
3. 500 次离线紧密循环不是 10 分钟 wall-clock soak，无法证明 underrun SLO。
4. 三平台 workflow 已落地为 skeleton；最终结论应以 GitHub-hosted runner 首次完整
   运行及真实工作站测试为准。
