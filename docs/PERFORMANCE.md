# OpenFEMLab 性能与语言分层

OpenFEMLab 采用 **Python 平台 + 可选加速核** 策略，对标 FEMtools 的工作流层，而非 ANSYS 的全栈求解器。

## 语言分层（当前）

| 层 | 模块 | 语言 | 说明 |
|----|------|------|------|
| L5 交互 | `wizard`, `serve`, `report` | Python + HTML | CLI/Web 后处理 |
| L4 平台 | CLI, JSON/YAML, AC 验收 | Python | CI 可复现 |
| L3 算法 | `correlation`, `updating`, `mpe` | Python + Numba* | *可选 `[accel]` |
| L2 求解 | `ModalSolver` | Python + SciPy sparse | 50k DOF（AC-PERF-001） |
| L1 内核 | `core/assembly`, 单元 | Python | 中小规模；热点待下沉 |

## 可选依赖

```bash
pip install 'openfemlab[accel]'   # Numba MAC 加速核
pip install 'openfemlab[plot]'    # Matplotlib 绘图
pip install 'openfemlab[cli]'     # Rich 彩色输出
```

## MAC 加速核与后端选择

`openfemlab.accel.mac` 为「实数、无加权」这一种情况提供专用核，两个后端等价：

| 后端 | 实现 | 特点 |
|------|------|------|
| `numpy` | BLAS `dgemm` 求 `Φ_aᵀ Φ_b`，各做一遍列范数归约 | 速度取决于本地 NumPy 链接的 BLAS |
| `numba` | `_mac_real_unweighted`，沿 DOF 行单趟融合累加 | 不产生 `(ndof, m)` 临时数组，不依赖 BLAS 质量 |

**哪个更快取决于部署环境，而不是算法本身。** 对接优化过的多线程 BLAS 时，
标量核无法与 `dgemm` 竞争；对接参考实现 BLAS 时，融合单趟核反而胜出。因此
`resolve_backend()` 不在导入时写死选择，而是**首次使用时用小规模探针实测两者**
并缓存结果——装上 `[accel]` 因此不可能让 `mac()` 变慢。用
`OPENFEMLAB_ACCEL_MAC=numpy|numba` 可跳过实测、直接指定后端。

实测参考（4 核容器，NumPy 2.5 + OpenBLAS，best-of-N，单位 ms）：

| 规模 `ndof × m` | `numpy` 后端 | `numba` 后端 |
|---|---|---|
| 5 000 × 20 | 0.20 | 0.32 |
| 20 000 × 50 | 1.75 | 6.30 |

即在本环境下探针会选中 `numpy`；`numba` 核的价值在于 BLAS 孱弱的部署。
`njit` 关闭了 `fastmath`：允许重结合会让结果依赖主机 SIMD 宽度，
与本项目其余部分承诺的可复现性冲突。

`correlation.mac.mac()` 只在**实数、无加权、已是 `float64`、
且 `ndof·ma·mb ≥ 1e6`** 时才走加速路径；其余情况保持通用实现不变。

## 基准测试

```bash
openfemlab bench modal --sizes 100,1000,5000 --repeats 3
```

## 修正重分析

`ScalingModel` 在参数仅缩放刚度/质量块时：

1. **仿射快装配** — 固定 CSR 稀疏模式，只更新 `data` 数组  
2. **ModalSolver 复用** — 同一实例上更新 `K/M`，`cache_factorization=True`

## 验收门槛

| ID | 内容 |
|----|------|
| AC-PERF-001 | 50k DOF 稀疏求解，禁止全矩阵稠密化，≤120 s |
| AC-PERF-002 | 稀疏 vs 稠密参考，频率 1e-8，MAC ≥0.999 |
| AC-PERF-003 | 5000×20 MAC 与展开式 NumPy 参考误差 ≤1e-10、≤2 s，且不超过参考实现的 5 倍耗时 |

## 路线图

1. **现在：** Numba MAC、修正重分析、bench CLI  
2. **下一步：** Rust 装配核、LOBPCG、修正 modal cache  
3. **长期：** 外部 Nastran/Abaqus 求解器适配为主 L2，自研核只保原型规模
