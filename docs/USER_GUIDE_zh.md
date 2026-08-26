# OpenFEMLab 中文用户指南（快速上手）

OpenFEMLab 是一个开源、与求解器无关的结构动力学 Python 工具箱，将有限元模态分析、
FE/试验相关性分析（correlation）与基于灵敏度的模型修正（model updating）连接成一条
可复现的 CAE 工作流。它以商业软件 FEMtools 的核心工作流为参照目标（模型 → 分析 →
相关 → 修正 → 验证），但采用 MIT 许可证、纯 Python 实现，并为 CI 自动化设计了
机器可读的报告与退出码。

> 项目目前处于 alpha 阶段，API 与交换格式在首个稳定版之前可能变化。

## 1. OpenFEMLab 与 FEMtools 对照

| FEMtools 模块 | 功能 | OpenFEMLab 对应 |
|---|---|---|
| Framework | 脚本 + 桌面 CAE 自动化环境 | Python API + `openfemlab` 命令行（无图形界面） |
| Dynamics | 动响应仿真、结构修改 | `solver` 模块：模态提取、阻尼、复模态、FRF 合成 |
| Pretest & Correlation | 模态预试验、FE/试验相关（MAC、COMAC） | `correlation` 模块：MAC / COMAC / FRAC / FDAC、模态配对、缩聚与扩展 |
| Model Updating | 基于灵敏度的迭代修正（频率、振型、FRF） | `updating` 模块：Gauss-Newton / Levenberg-Marquardt、贝叶斯 MAP、参数诊断 |
| Optimization | 结构设计优化 | `optimization` 模块（scipy 后端） |
| MPE | 从 FRF 提取模态参数 | 暂未提供；可直接读取 UFF/UNV 数据集 55（振型）与 58（FRF）测试数据 |

与 FEMtools 相同的核心理念是**求解器无关**：相关性与修正只依赖中性的模态数据交换
格式（JSON/YAML 的模型、模态结果、试验数据文档），因此同一条工作流既可以驱动内置
求解器，也可以对接外部 CAE 求解器适配层。与 FEMtools 不同的是，OpenFEMLab 面向
脚本与 CI：每条命令都能输出 JSON/YAML 报告，验收门槛（`--require-*`）不满足时以
非零退出码结束，可直接作为流水线的质量闸门。

## 2. 安装

要求 Python 3.10 或更新版本。在仓库根目录执行：

```bash
python -m pip install -e .
```

如需开发工具、彩色 CLI 输出（rich）与基准脚本：

```bash
python -m pip install -e ".[dev,cli]"
```

可选的 `io` 附加依赖安装 `meshio`，`openfemlab.io.meshio_bridge` 借此读写
Gmsh、Abaqus、VTK 等 meshio 支持的网格格式：

```bash
python -m pip install -e ".[io]"
```

验证安装：

```bash
openfemlab --version   # 打印版本号
openfemlab info        # 平台与模块总览
```

## 3. 五分钟上手（Python API）

建立一根钢制悬臂梁并提取前五阶模态：

```python
from openfemlab import Material, ModalSolver, Section
from openfemlab.mesh.simple import beam_mesh

steel = Material(E=210e9, density=7850.0, nu=0.3)
section = Section(area=1.0e-4, inertia_z=8.333e-10)

model = beam_mesh(
    length=1.0,
    num_elements=20,
    material=steel,
    section=section,
    support="cantilever",
)
result = ModalSolver(model).solve(num_modes=5)

for mode, frequency in enumerate(result.frequencies, start=1):
    print(f"mode {mode}: {frequency:.3f} Hz")
```

完整的“模型 → 合成试验 → 相关 → 修正 → 验证”流程见
[`examples/02_model_updating_workflow.py`](../examples/02_model_updating_workflow.py)。

## 4. 命令行总览

`openfemlab` 提供四条分析命令，对应平台的四个层次，另有两条辅助命令：

| 命令 | 作用 |
|---|---|
| `modal` | 对模型规格文件做实模态分析 |
| `correlate` | FE 模态与实测模态的相关性报告（MAC、频率偏差、COMAC） |
| `correlate-frf` | 实测 FRF 与模型合成 FRF 的频域相关（FRAC、FDAC） |
| `update` | 由配置文件驱动的灵敏度模型修正 |
| `version` | 打印版本号 |
| `info` | 平台与模块总览 |

全局选项（写在子命令之前）：`-q/--quiet` 只打印结果，`--no-color` 关闭 rich 彩色
输出，`--traceback` 出错时抛出完整回溯（便于调试）。各分析命令都支持
`--format table|json|yaml` 选择输出形式，以及 `-o/--output PATH` 把完整报告写入
文件。

退出码约定（适用于 CI）：

| 退出码 | 含义 |
|---|---|
| 0 | 成功，所有门槛通过 |
| 1 | 输入或运行错误 |
| 3 | `correlate` / `correlate-frf` 的 `--require-*` 验收门槛未通过 |
| 4 | `update --strict` 时修正循环未收敛 |

## 5. 模型规格文件（model spec）

CLI 读取的模型由一个 JSON/YAML 文档描述，相当于项目文件：同一份文档既驱动
`openfemlab modal`，也是 `openfemlab update` 每次迭代重建模型的依据。

```yaml
name: cantilever
materials:
  steel: {E: 2.1e11, density: 7850.0, nu: 0.3}
sections:
  strip: {area: 1.0e-4, inertia_z: 8.333e-10}
mesh:
  type: beam            # bar | beam | chain | truss | custom
  length: 1.0
  num_elements: 20
  support: cantilever
  material: steel       # 引用上方 materials 表中的条目
  section: strip
point_masses:
  - {node: 20, mass: 0.5}
# 可选：供 correlate-frf 合成阻尼 FRF 使用
# damping: {ratio: 0.02}            # 统一模态阻尼比
# damping: {alpha: 1.0, beta: 1e-5} # 或 Rayleigh 比例阻尼
```

`mesh.type` 从 `openfemlab.mesh.simple` 选择网格生成器：`bar`（轴向杆）、`beam`
（平面 Euler-Bernoulli 梁）、`chain`（弹簧-质量链）、`truss`（由 `coordinates` 与
`connectivity` 数组给出的桁架），或 `custom`（显式列出 `nodes` 与 `elements`，
单元类型支持 `spring`、`truss`、`beam`）。`supports`、`point_masses`、
`rotary_inertias` 分别添加约束、集中质量与转动惯量。

模型修正通过**点分路径**寻址文档中的单个数值，例如 `materials.steel.E` 或
`mesh.elements.2.stiffness`——这是第 9 节参数声明中 `target` 字段的含义。

在模型规格之外，Python API 还提供空间梁单元 `BeamElement3D`（可从 `openfemlab`
顶层导入，或经 `ModelBuilder.add_beam3d` 添加）：类似 Nastran CBAR 的两节点空间
构件，每节点 6 个自由度（UX/UY/UZ/RX/RY/RZ），涵盖轴向拉压、St Venant 扭转与两个
主平面内互不耦合的弯曲；局部坐标系按 CBAR 约定由方向向量（`orientation`）确定，
截面需给出正的 `inertia_y`、`inertia_z` 与 `torsion_constant`。该单元由 42 项专门
测试覆盖。

### 平面壳单元 `ShellQuad4Element`

`ShellQuad4Element`（从 `openfemlab.core` 导入，或经 `MeshBuilder.add_shell_quad4`
添加）是让导入的壳网格**可以真正重新分析**的四节点平面小片单元，每节点同样是
6 个自由度。单元自身的坐标系由几何确定：`e_z` 取两条对角线的法向，`e_x` 取投影到
面内的平均 `xi` 方向，`e_y = e_z × e_x`；局部 24×24 矩阵再按节点块旋转到整体坐标，
方式与 `BeamElement3D` 旋转其 12×12 块完全一致。在该坐标系下单元分为三个互不耦合
的部分：

- **膜**——直接复用平面应力的 `Quad4Element`，因此库中只有一套双线性膜内核；
- **弯曲**——Reissner-Mindlin 板，`D_b = t³/12 · D`，剪切修正系数 `κ = 5/6`；横向
  剪切采用 Bathe 与 Dvorkin 的 **MITC4** 假设应变场（在四条边中点取协变剪应变后
  线性插值），既消除剪切自锁，又不像减缩积分那样留下秩亏；
- **钻转**——绕法向的转动在该列式中没有物理刚度，故以 `drilling_factor` 给出一个
  虚拟对角刚度，使局部矩阵非奇异。

使用前需要知道的三点约定：单元是**平的**，节点离面超过 `flatness_tolerance` 与单元
尺寸之积时会直接抛出 `ElementError`，而不是悄悄投影，翘曲的四边形必须加密；钻转
自由度恒为无质量，弯曲转动在未设 `rotary_inertia` 时同样无质量（模态求解器可精确
凝聚，但阻尼解或直接解必须约束它们）；膜与弯曲在单个小片内不耦合，曲率只能靠网格
的分片来表达。共面装配因此保持恰好 6 个刚体模态，折角处则会引入一点与网格相关的
人为刚度。

结构化网格生成器 `mesh.simple.shell_plate_mesh` 按与 `quad_plate_mesh` 相同的行主序
编号建立矩形板，`support` 可取 `cantilever`、`free` 或 `simply-supported`：

```python
from openfemlab.core import Material
from openfemlab.mesh.simple import shell_plate_mesh

model = shell_plate_mesh(
    1.0, 0.5, 8, 4,
    Material(E=2.1e11, nu=0.3, density=7850.0),
    thickness=2.0e-3,
    support="cantilever",
)
```

该单元由 72 项专门测试覆盖；包含 meshio 桥 44 项测试在内，当前完整套件共
**1308 项测试全部通过**。

## 6. meshio 工业网格桥（Python API）

安装 `[io]` 附加依赖后，可把 meshio 支持的 Gmsh、Abaqus、VTK 等网格读入统一的
`NeutralModel`，也可写回由文件扩展名或 `file_format` 指定的格式：

```python
from openfemlab.io import read_meshio, write_meshio

neutral = read_meshio("bracket.msh")
print(neutral.n_nodes, neutral.n_elements)
write_meshio(neutral, "bracket.vtu")
```

已有 `meshio.Mesh` 内存对象时，使用 `from_meshio(mesh)`；反向转换使用
`to_meshio(neutral)`。桥接层采用显式的一对一映射：

| meshio cell type | `ElementType` |
|---|---|
| `vertex` | `MASS1` |
| `line` | `ROD2` |
| `triangle` | `TRI3` |
| `quad` | `QUAD4` |
| `tetra` | `TET4` |
| `hexahedron` | `HEX8` |

meshio 的零基点索引会转换为中性模型的节点 ID。`node_ids`、`element_ids` 以及
`property_ids` / `gmsh:physical` / `medit:ref` 标签会尽可能保留；不支持的单元类型会
发出 `UserWarning`，数量记录在 `neutral.meta["skipped_cell_types"]`。由于 meshio 的
`line` 无法区分杆、梁和弹簧，`BEAM2` / `SPRING2` 不会被含糊地导出，而是抛出
`FormatError`。

当前 R2-T05 只完成了**几何与连接关系桥接**。一般网格文件不含 OpenFEMLab 所需的完整
材料和截面定义，因此导入结果的 `materials` / `properties` 为空，尚不能直接传给
`ModalSolver`；在自动 `NeutralModel → Model` 转换落地前，调用方需自行补充材料、截面、
约束并构造分析模型。UNV 2411/2412 几何读取也仍在后续范围内。`meshio` 采用懒加载，
未安装附加依赖时只有文件读写/导出入口会抛出带安装提示的 `MissingDependencyError`，
核心包与 `from_meshio` 的鸭子类型转换仍可使用。

## 7. 模态分析：`openfemlab modal`

```bash
openfemlab modal cantilever.yaml -n 8
openfemlab modal cantilever.yaml -n 6 --normalization mass -o modes.yaml
```

装配模型、提取最低若干阶实模态，并报告每阶的频率、周期、模态质量、参与因子、
有效质量及其累计占比；零频刚体模态以 `*` 标注。常用选项：

| 选项 | 含义 |
|---|---|
| `-n/--modes N` | 提取的模态数（默认 6） |
| `--max-frequency HZ` | 丢弃高于此频率的模态 |
| `--normalization mass\|max\|none` | 振型归一化方式（默认 mass，即质量归一） |
| `--direction DOF` | 参与因子方向，如 `UX`（默认取有效质量最大的平动方向） |
| `--sparse` / `--dense` | 强制 Lanczos 稀疏路径或 LAPACK 稠密路径（默认自动选择） |
| `-o/--output PATH` | 写出完整模态结果（频率、振型、DOF 映射），可直接作为 `correlate` 的 FE 侧输入 |

## 8. FE/试验相关：`openfemlab correlate`

```bash
openfemlab correlate cantilever.yaml measured.yaml --mac-threshold 0.7
openfemlab correlate modes.yaml measured.yaml --partial-dofs --pairing optimal --matrix
```

第一个参数是 FE 侧：既可以是 `modal -o` 保存的模态结果文件，也可以直接给模型规格
文件（此时先求解，模态数由 `-n` 控制，默认 10）。第二个参数是实测模态数据
（JSON/YAML），其原生格式为：

```yaml
object_type: test_data
frequencies_hz: [10.2, 63.5, 177.1]
mode_shapes: [...]            # 布局为 dofs_by_mode（每行一个 DOF，每列一阶模态）
mode_shape_layout: dofs_by_mode
dof_map:
  node_ids: [4, 8, 12, 16, 20]
  dof_types: [UY, UY, UY, UY, UY]
damping: [0.01, 0.01, 0.01]   # 可选
```

两侧在 DOF 映射的交集上配对并报告 MAC、频率偏差与 COMAC。常用选项：

| 选项 | 含义 |
|---|---|
| `--pairing greedy\|optimal\|frequency` | 配对策略：贪心（默认）、匈牙利最优、纯频率 |
| `--mac-threshold MAC` | 拒绝 MAC 低于此值的配对（默认 0.0） |
| `--frequency-tolerance PCT` | 拒绝频率偏差超过此百分比的配对 |
| `--freq-penalty W` | 配对得分中频率距离的权重（建议 0.1） |
| `--partial-dofs` | 容忍模型中不存在对应自由度的测量通道（部分布点） |
| `--matrix` | 额外打印完整 MAC 矩阵 |
| `--require-mac MAC` | 任一配对 MAC 低于此值时以退出码 3 结束 |
| `--require-frequency PCT` | 任一频率误差超过此百分比时以退出码 3 结束 |

## 9. 模型修正：`openfemlab update`

```bash
openfemlab update updating.yaml -o cantilever.updated.yaml --report report.json --strict
```

由一个配置文件驱动 Levenberg-Marquardt 修正循环。配置文件指明模型规格、实测目标
与待修正的无量纲缩放参数：

```yaml
model: cantilever.yaml          # 路径，或内联的模型规格映射
parameters:
  - name: youngs_modulus
    target: materials.steel.E   # 点分路径，指向模型规格中的一个数值
    lower: 0.6                  # 缩放因子下界（默认 0.5）
    upper: 1.5                  # 缩放因子上界（默认 2.0）
    kind: stiffness             # stiffness | mass | damping | generic
  - name: cross_section
    target: sections.strip.area
    lower: 0.8
    upper: 1.3
    kind: mass
target:
  file: measured.yaml           # 实测模态数据；或直接给 frequencies_hz 列表
modes: 4                        # 每次评估提取的 FE 模态数
partial_dofs: true              # 振型相关时容忍部分布点
options:                        # 透传给 UpdatingOptions
  max_iterations: 25
  shape_weight: 1.0             # >0 且目标含实测振型时参与振型/MAC 残差
```

参数是**缩放因子**（初值 1.0），修正结果对原始文档中的名义值做乘法缩放，因此重复
运行同一配置总能得到同一模型。命令行可用 `-n` 与 `--max-iterations` 覆盖配置值；
`-o` 写出修正后的模型规格（可直接再交给 `openfemlab modal` / `correlate`），
`--report` 写出含迭代历史的运行报告，`--strict` 在未收敛时以退出码 4 结束。

报告包含每个参数的名义值、更新值、缩放因子与变化百分比，修正前后的相关性指标
（最大频率误差，若使用振型还有 mean/min MAC），以及逐次迭代的代价、阻尼与步长。

## 10. FRF 相关：`openfemlab correlate-frf`

```bash
openfemlab correlate-frf measured.unv cantilever.yaml --require-frac 0.9
openfemlab correlate-frf measured.unv cantilever.yaml --damping 0.02 --excitation 1:UZ
```

第一个参数是实测 FRF：UFF/UNV 数据集 58 文件（`.uff`/`.unv`），或等价的 JSON/YAML
FRF 文档：

```yaml
object_type: frf
response_type: receptance       # receptance | mobility | accelerance
frequencies_hz: [10.0, 11.0, 12.0]
excitation: {node: 1, direction: UZ}
channels:
  - {node: 3, direction: UZ, real: [...], imag: [...]}
```

第二个参数是比较侧：另一份 FRF 文件，或一个模型规格——后者会先求解，再在实测
频率线与通道集上合成同一列 FRF，逐通道报告 FRAC 与频率线上的 FDAC 矩阵。常用选项：

| 选项 | 含义 |
|---|---|
| `-n/--modes N` | 合成保留的模态数（默认 10） |
| `--damping ZETA` | 统一模态阻尼比（默认取模型规格的 `damping` 块，否则 0.02） |
| `--rayleigh ALPHA BETA` | 比例阻尼 C = αM + βK（与 `--damping` 互斥） |
| `--response-type` | 实测纵坐标的响应类型；合成侧使用同一类型 |
| `--excitation NODE:DOF` | 激励自由度，如 `1:UZ`（默认取测量的参考自由度） |
| `--no-fdac` | 跳过 FDAC 矩阵（其规模是频率线数的平方） |
| `--matrix` | 额外打印完整 FDAC 矩阵 |
| `--require-frac FRAC` | 任一通道 FRAC 低于此值时以退出码 3 结束 |
| `--require-fdac FDAC` | 任一 FDAC 对角元低于此值时以退出码 3 结束 |

## 11. 端到端工作流

示例脚本一次生成模型规格、实测模态数据与修正配置三个文件：

```bash
python examples/02_model_updating_workflow.py --output-dir run
```

随后即可走完整条 FEMtools 式闭环：

```bash
# 1) 求解并保存可移植的模态结果
openfemlab modal run/cantilever.yaml -n 6 \
  --normalization mass --output run/modes.yaml

# 2) 用部分布点的实测数据做相关，并设置 CI 验收门槛
openfemlab correlate run/cantilever.yaml run/measured.yaml \
  --partial-dofs --pairing optimal --matrix \
  --require-mac 0.95 --require-frequency 2.0 \
  --output run/correlation.json

# 3) 修正有界参数，写出修正后的模型与运行报告
openfemlab update run/updating.yaml \
  --output run/cantilever.updated.yaml \
  --report run/updating-report.json --strict

# 4) 在修正后的模型上复查验收门槛
openfemlab correlate run/cantilever.updated.yaml run/measured.yaml \
  --partial-dofs --require-mac 0.95 --require-frequency 1.0
```

在 CI 中，把第 2、4 步作为质量闸门：门槛未过时命令以退出码 3 结束，流水线即失败；
`--format json` 与 `-o` 产出的报告是 schema 版本化的，便于归档与比对。

## 12. 延伸阅读

- [`README.md`](../README.md) —— 功能总览、测试与基准
- [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) —— 模块边界与数据流
- [`docs/MODULE_SPEC.md`](MODULE_SPEC.md) —— 各模块的行为规格
- [`docs/SOTA_GAP_ANALYSIS.md`](SOTA_GAP_ANALYSIS.md) —— 与 FEMtools 及 2026 SOTA 的差距分析
- `examples/01_cantilever_modal.py`、`examples/02_model_updating_workflow.py` —— 可运行示例
