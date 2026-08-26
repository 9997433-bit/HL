# Round 1 测试基线

记录日期：2026-08-26

## 环境要求

| 组件 | 最低要求 | 本轮探针 |
| --- | --- | --- |
| Node.js | `>=20.11 <25`（建议使用 Node.js 22 LTS） | `v22.14.0` |
| npm | `>=10` | `10.9.7` |
| 操作系统 | Linux / macOS；Windows 使用 WSL 或 Git Bash | Linux `6.12.94+` x86_64 |
| 压缩工具 | Zip 3.0+；无 Zip 时可用 Python 3.8+ 后备 | Zip 3.0、Python 3.12.3 |

Node.js 与 npm 的版本约束也记录在根目录 `package.json#engines` 中。首次检出后运行：

```bash
bash scripts/setup.sh
```

脚本会校验运行时、校验两个 workspace，并使用根 `package-lock.json` 执行
`npm ci`；尚无锁文件时则执行 `npm install` 并生成锁文件。

## 基础测试范围

| 命令 | 覆盖范围 | 通过标准 |
| --- | --- | --- |
| `npm run test:literacy` | 识字 App 基础测试 | 项目自带测试（若有）通过；Vite 生产构建成功；存在 `dist/index.html` 与 JavaScript 资源；产物不再引用 `/src/` |
| `npm run test:math` | 数学 App 基础测试 | 项目自带测试（若有）通过；Vite 生产构建成功；存在 `dist/index.html` 与 JavaScript 资源；产物不再引用 `/src/` |
| `npm test` | 两个 App 顺序回归 | 上述两个脚本均以状态码 0 退出 |
| `npm run build:all` | 双 App 构建、归档完整性 | 两个生产构建成功；两个 ZIP 存在、非空且通过 ZIP 完整性检查 |

本基线是构建级冒烟测试，不代替浏览器端交互、视觉回归、无障碍、性能和真实儿童可用性测试。当前两个 App 尚未定义单元测试脚本，因此基础脚本会明确提示并执行生产构建冒烟测试；后续添加 `test` 脚本后会自动纳入。

## 打包约定

`scripts/build-all.sh` 每次重新构建两个 App，并把各自 `dist/` 下的完整静态部署产物打包到：

- `dist/hongen-literacy-app.zip`
- `dist/hongen-math-app.zip`

ZIP 根目录直接包含 `index.html` 和静态资源，可解压到任意静态 Web 服务器。`dist/` 是可再生构建产物，不纳入 Git。

## Round 1 验收基线

1. 环境探针满足 Node.js、npm 与压缩工具要求。
2. 根 workspace 能一次安装两个 App 的依赖。
3. 两个基础测试脚本均通过。
4. 双 App 构建脚本生成指定名称的有效 ZIP。
5. 后续轮次至少保持上述命令与产物路径稳定。
