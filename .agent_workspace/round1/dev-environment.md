# 专业音频开发环境

## 支持基线

- 推荐 CPython 3.12；探针接受 3.11–3.13。
- Python 包使用 `requirements.txt` 和 `requirements-dev.txt` 精确锁定。
- 实时 I/O 通过 PortAudio（Python `sounddevice`）；文件 I/O 通过
  libsndfile（`soundfile`）；编解码和转封装通过 ffmpeg。
- 48 kHz / float32 是开发时的默认交换格式。打开设备前仍须读取其默认采样率、
  通道数和 host API，不可假定所有设备支持相同配置。

快速启动：

```bash
./scripts/setup-dev.sh
. .venv/bin/activate                 # Windows Git Bash: source .venv/Scripts/activate
python scripts/probe-system.py
```

脚本默认安装开发依赖，并把探针写入
`.agent_workspace/round1/system-probe.json`。`--runtime-only` 只安装运行时包；
`--no-venv` 使用当前环境；`--strict` 可用于要求完整硬件就绪的工作站 CI。

## Linux

Debian/Ubuntu 原生依赖：

```bash
sudo apt-get update
sudo apt-get install portaudio19-dev libasound2-dev libsndfile1-dev ffmpeg pkg-config
```

- PortAudio 可连接 ALSA、JACK 或 PulseAudio；PipeWire 主机通常通过其
  PulseAudio/JACK 兼容层工作。枚举到哪个 host API 必须以探针结果为准。
- 现代桌面通常由 logind/udev 授予当前会话设备权限。仅在发行版明确要求时才把
  用户加入 `audio` 组，组变更后需重新登录。
- 低延迟调度可能需要 `rtkit`，或在 `/etc/security/limits.d/` 配置有限的
  realtime priority 与 memlock。不要让开发程序以 root 运行。
- SSH、CI 和云主机没有 `/dev/snd` 很常见；离线 DSP 测试仍可运行，但实时录放
  必须标为未验证。
- WSL2 的声音由 WSLg/PulseAudio 桥接，延迟和设备语义与原生 ALSA 不同，不适合
  验收专业低延迟路径。

## macOS

```bash
brew install python@3.12 portaudio libsndfile ffmpeg pkg-config
```

- 使用同一架构的 Python 和 Homebrew。Apple Silicon 上不要混用 arm64 Python
  与 `/usr/local` 下的 x86_64 库；arm64 Homebrew 通常位于 `/opt/homebrew`。
- 首次录音时，macOS 会请求麦克风权限。权限属于真正启动 Python 的 Terminal、
  IDE 或已签名应用；可在“系统设置 → 隐私与安全性 → 麦克风”检查。
- CoreAudio 聚合设备可能发生时钟漂移；多设备测试应启用 drift correction，
  并记录实际设备 UID、buffer size 和 nominal sample rate。
- 发布签名应用时需要 `com.apple.security.device.audio-input` entitlement 和
  `NSMicrophoneUsageDescription`，开发脚本本身不能替代这些声明。

## Windows

推荐从 python.org 安装 64 位 CPython 3.12，并使用 PowerShell：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python .\scripts\probe-system.py --output .agent_workspace\round1\system-probe.json
```

ffmpeg 可用 `winget install Gyan.FFmpeg` 安装；新开终端后确认
`ffmpeg -version`。官方 `sounddevice` wheel 通常自带 PortAudio，源码构建才需要
单独的 PortAudio/MSVC 工具链。

- 首选 WASAPI 做现代 Windows 测试，同时保留 MME/DirectSound 的兼容性测试。
  shared mode 会经过系统混音和采样率转换；exclusive mode 必须单独处理设备占用
  和不支持的格式。
- 通用 PortAudio wheel 不保证包含 ASIO。ASIO SDK/驱动有单独许可和分发限制，
  应作为可选、用户提供的后端，不能把它当作基础环境能力。
- 在“设置 → 隐私和安全性 → 麦克风”同时允许麦克风访问和桌面应用访问。
- Windows 音频设备可在休眠、蓝牙 profile 切换或默认设备改变后失效。流错误后
  应重新枚举，而不是继续使用旧索引。
- `setup-dev.sh` 可在 Git Bash/MSYS2 中使用；原生 Windows 自动化优先采用上面的
  PowerShell 命令，避免 shell 路径转换影响 ffmpeg 和虚拟环境。

## Docker

```bash
docker compose build audio-dev
docker compose run --rm audio-dev
python scripts/probe-system.py
```

镜像包含 PortAudio、ALSA headers、libsndfile 和 ffmpeg，适合可重复的离线 DSP、
格式处理、lint 与测试。它默认不暴露声音设备。

Linux 主机可显式选择带 `/dev/snd` 的 profile：

```bash
AUDIO_GID="$(getent group audio | cut -d: -f3)" \
  docker compose --profile linux-audio run --rm audio-dev-linux
```

这只解决 ALSA device node。使用 PulseAudio/PipeWire 还需挂载当前用户的 Unix
socket、传递正确的 server 环境变量和 UID；socket 路径因发行版而异，不应硬编码
到共享 compose 文件。不要把 `--privileged` 当作音频配置方案。

Docker Desktop 的 Linux VM 不能直接透传 macOS CoreAudio 或 Windows WASAPI。
这些平台的实时 I/O 应在宿主进程执行，容器通过文件、网络流或测试 fixture 处理
音频。容器调度也不保证低延迟，因此容器结果不能作为 glitch/dropout 验收。

## 探针状态解释

- `ready`：Python/运行时库、PortAudio、平台原生音频库和 ffmpeg 都可用，且没有
  已知平台风险。
- `degraded`：离线开发仍可进行，但缺少开发工具、没有可见设备，或处于容器/WSL
  等不适合实时验收的环境。
- `not_ready`：缺少 Python 运行时包、PortAudio、Linux ALSA 或 ffmpeg 等阻塞项。

`missing_dependencies` 是可执行的安装清单；`platform_risks` 是不能仅靠 pip
消除的主机限制。请把探针 JSON 随环境问题一起附上，但设备名称可能暴露工作站
信息，对外分享前应检查。
