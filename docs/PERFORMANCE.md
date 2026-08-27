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
pip install 'openfemlab[accel]'   # Numba MAC 加速
pip install 'openfemlab[plot]'    # Matplotlib 绘图
pip install 'openfemlab[cli]'     # Rich 彩色输出
```

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
| AC-PERF-003 | 5000×20 MAC ≤2 s，与 NumPy 参考误差 ≤1e-10 |

## 路线图

1. **现在：** Numba MAC、修正重分析、bench CLI  
2. **下一步：** Rust 装配核、LOBPCG、修正 modal cache  
3. **长期：** 外部 Nastran/Abaqus 求解器适配为主 L2，自研核只保原型规模
