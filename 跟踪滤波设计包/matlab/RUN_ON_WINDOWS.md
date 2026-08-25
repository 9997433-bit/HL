# Windows + MATLAB 本地仿真验证指南

本指南面向在 **Windows 上安装了 MATLAB** 的用户，一步一步在本机跑通本仓库的
MATLAB/Octave 移植验证，并运行新的**真实场景仿真研究**（scenario_study）。

- 适用环境：**MATLAB R2020b 或更高**（GNU Octave >= 8 亦可），**无需任何工具箱**。
- 输出编码说明：核心对比脚本输出为 ASCII/英文；统计验证器与场景套件
  （`validate_tracking`、`scenario_study` 等）的说明行含 **UTF-8 中文**。所有
  机器可读行（`KEY,...`、`[PASS]/[FAIL] <编号>`、`ALL CHECKS PASSED`）均为纯
  ASCII —— Windows GBK 控制台若把中文说明行显示成乱码，**不影响判定与数字**；
  完整结果同时写入 UTF-8 编码的 `results_*.txt`，用 VS Code 等 UTF-8 编辑器
  查看即可。
- 不需要编译器：MEX 内核是可选加速，缺编译器时自动回退纯 M 代码，**结果逐位一致**。

---

## 第 0 步：获取代码（分支 `cursor/matlab-port-verify-075a`）

方式 A —— git（推荐）：

```bat
git clone -b cursor/matlab-port-verify-075a https://github.com/9997433-bit/HL.git
cd HL
```

方式 B —— 浏览器下载 ZIP：

1. 打开 https://github.com/9997433-bit/HL
2. 左上角分支下拉框选择 `cursor/matlab-port-verify-075a`
3. 绿色 **Code** 按钮 → **Download ZIP**，解压到本地（建议解压到较短的路径，如 `C:\work\HL`）

## 第 1 步：进入 matlab 目录并初始化路径

打开 MATLAB，在命令行窗口执行（把路径换成你的实际位置）：

```matlab
cd C:\work\HL\跟踪滤波设计包\matlab
homodyne_setup_path
```

> 各验证入口脚本（`run_all_verify`、`validate_realistic_scenarios` 等）内部也会
> 自动调用 `homodyne_setup_path` 并补齐 `heterodyne/`、`qtec/` 路径，手动执行一次
> 主要是为了单独调用底层函数时也能找到它们。

## 第 2 步：快速冒烟（约 5 分钟）

```matlab
compare_with_python      % 零差核心金标对比：MATLAB vs Python，rtol=1e-10，数秒
validate_tracking        % 零差跟踪统计验证器 V1–V5（含逐位一致的 numpy RNG；V5 =
                         % v_peak 未知时按 APP_V_PEAK_MAX=30 m/s 保守评估守卫），数分钟
```

- `compare_with_python` 末尾应打印 `compare_with_python: PASS -- all N fields match ...`。
- `validate_tracking` 逐项打印检查结果，全部通过时正常返回（失败会直接报错）。

## 第 3 步：完整验证（约 10 分钟）

```matlab
rc = run_all_verify('full')    % rc == 0 表示全部通过
```

- 会依次重跑全部统计验证器（外差 H0–H6、QTec Q0–Q1、零差 5 个验证器、椭圆 3 个
  验证器），再做全部金标对比，最后打印 `RUN_ALL_VERIFY SUMMARY` 汇总表，
  全部通过时输出 `ALL VERIFICATIONS PASSED`。
- 只想快速对比金标（数秒）：`rc = run_all_verify()`。

## 第 4 步：真实场景仿真研究（scenario_study）

```matlab
cd scenario_study
rc = validate_realistic_scenarios     % 完整场景套件 (S1-S5/H1-H4/X1), 打印全部表格,
                                      % 生成 results_realistic_scenarios.txt + .mat
plot_scenario_results                 % 生成 4 张图 -> scenario_study/figs/*.png + *.fig
cd ..
```

生成的四张图：

| 图 | 文件名 | 内容 |
|---|---|---|
| 1 | `fig1_homodyne_operating_map` | 零差工作域热力图：自动选档后的未跟踪多普勒相位（频率 x 速度平面），白虚线 = 1 rad 守卫 |
| 2 | `fig2_homodyne_band_map` | 零差选档地图：守卫先行规则在 (f, v) 平面上选 SLOW/MEDIUM/FAST |
| 3 | `fig3_speckle_tradeoff` | QTec 散斑分集权衡：联合深衰落概率 vs 通道数 M（理论 p^M + 蒙特卡洛） |
| 4 | `fig4_heterodyne_bathtub` | 外差浴缸曲线：各档可跟踪速度上限 v_pll_limit(f)（谷底在 f = fn）+ IF 窗/混叠上限 |

`.fig` 文件可在 MATLAB 中 `openfig` 交互查看，`.png` 可直接分享。

> 说明：`scenario_study/validate_realistic_scenarios.m` 是完整版时域蒙特卡洛场景
> 套件（零差 S1–S5、外差 H1–H4、交叉对照 X1），与 Python 主脚本
> `scenario_study/validate_realistic_scenarios.py` 同种子、同判据；噪声流经
> numpy 精确 RNG 逐位一致，"KEY," 指标行可直接与 Python 输出对比。
> 无编译器时自动走纯 M 回退（结果不变，速度较慢）。
> 结果字段说明见该文件头部注释（OUTPUT 一节）。

## MEX 编译失败怎么办（HOMODYNE_NO_MEX=1）

两个可选 MEX 加速内核（numpy 精确 RNG、PLL 标量环）会在首次使用时自动尝试编译。
Windows MATLAB 上编译需要 **MinGW-w64** 编译器（MSVC 编不过：缺 `__uint128_t`）。

**不想折腾编译器？直接跳过 MEX：**

```matlab
setenv('HOMODYNE_NO_MEX', '1')     % 本次 MATLAB 会话内生效，然后正常运行各脚本
```

纯 M 回退与 MEX **结果逐位一致**，只是慢一些。想要 MEX 加速的话：
MATLAB 主页 → 附加功能 → 搜索安装 *MATLAB Support for MinGW-w64 C/C++ Compiler*，
然后 `mex -setup` 选择 MinGW。

## 常见错误与处理

| 现象 | 原因 | 处理 |
|---|---|---|
| `未定义函数或变量 'homodyne_setup_path'` | 当前目录不在 `跟踪滤波设计包\matlab` | `cd` 到该目录后再运行 |
| `未定义函数 'pll_carrier_regen'`（或其它底层函数） | 没有先运行 `homodyne_setup_path` | 先运行 `homodyne_setup_path`（或直接用 `run_all_verify` 等入口脚本） |
| MEX 报错：`未找到支持的编译器` 或 `__uint128_t` 相关错误 | Windows 缺 MinGW / 用了 MSVC | `setenv('HOMODYNE_NO_MEX','1')` 跳过（结果不变），或安装 MinGW-w64 附加功能 |
| `golden data missing -- regenerating (python3 export)...` 然后报错 | 金标 `.mat` 文件缺失且本机无 `python3` | 金标已随仓库提交，正常不会触发；若触发说明下载不完整，请重新完整下载/克隆分支 |
| `plot_scenario_results` 报 `results_realistic_scenarios.mat not found` | 还没生成结果文件 | 先在 `matlab\scenario_study\` 下运行 `validate_realistic_scenarios` |
| 打开 `.m`/`.md` 文件中文注释乱码 | 编辑器没用 UTF-8 编码 | MATLAB：预设 → 编辑器/调试器 → 将文本文件编码设为 UTF-8；或用 VS Code 打开 |
| `addpath`/`mex` 在中文路径下行为异常 | 个别旧版 MATLAB 对非 ASCII 路径支持不佳 | 把仓库移到纯 ASCII 短路径（如 `C:\work\HL`）再试 |
| 某统计验证器偶发 FAIL 后重跑又 PASS | 不应出现：所有种子固定、结果确定 | 请完整复制输出反馈（附 MATLAB 版本），便于排查 |

## 命令速查表（Windows / MATLAB）

```matlab
% ---- 一次性准备 ----
cd C:\work\HL\跟踪滤波设计包\matlab       % 换成你的路径
homodyne_setup_path                        % 初始化路径
% setenv('HOMODYNE_NO_MEX','1')            % 可选：无编译器时跳过 MEX

% ---- 快速冒烟（约 5 分钟）----
compare_with_python                        % 核心金标对比（数秒）
validate_tracking                          % 零差 V1–V5 统计验证

% ---- 完整验证（约 10 分钟）----
rc = run_all_verify('full')                % rc == 0 即全部通过
rc = run_all_verify()                      % 只做金标对比（数秒）

% ---- 真实场景仿真研究 ----
cd scenario_study
rc = validate_realistic_scenarios          % 完整场景套件 -> results_realistic_scenarios.txt/.mat
plot_scenario_results                      % 4 张图 -> scenario_study\figs\
cd ..

% ---- 单个验证器（按需）----
validate_off_mode                          % 零差 OFF 模式 O1–O6b
validate_zeta_sweep                        % 零差 zeta 扫描 Z0–Z3
validate_app_30ms_100khz                   % 应用场景 A1–A8
cd heterodyne; rc = validate_heterodyne(); cd ..    % 外差 H0–H6
cd qtec; rc = validate_diversity_p0_p1(); cd ..     % QTec P0+P1
cd homodyne; rc = validate_ellipse_small_disp(); cd ..   % 椭圆校正 E1–E5
```

如果你用的是 **Octave for Windows**，把上述命令放进
`octave --no-gui --eval "..."` 中运行即可，行为一致。

更多背景（移植约定、金标体系、验证器清单）见 `matlab/README.md`。
