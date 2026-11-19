# Local Harness · Mac 本地 AI 编程助手

这是一款面向 Apple 芯片 Mac 的独立开源桌面应用，基于 DeepSeek Harness 改造。它用本机运行的千问 Qwen3.8-27B 四比特模型读代码、回答问题和调用工具。应用关闭了上游的会话反馈、遥测、云模型和自动更新。它与 DeepSeek 官方在线版可以并存。

## 一条命令安装

在 Mac 上打开「终端」，复制整行并回车。

```bash
curl -fsSL https://raw.githubusercontent.com/CarverXx/harness-local-macos/v1.0.0/install.sh | /bin/bash -s -- --modelscope
```

适用于 **Apple 芯片、macOS 15 / 26 / 27**。建议 **32 GB 或以上统一内存**，首次安装请预留 **35 GB 可用空间**。模型权重约 **16 GB**，日后磁盘缓存可增长至 **24 GB**。上面的命令从 GitHub、DeepSeek 下载站和魔搭 ModelScope 获取文件，模型逐个按固定 Hugging Face 快照的 SHA-256 校验。去掉命令末尾的 `-s -- --modelscope` 即从 Hugging Face 下载。时间主要取决于下载速度。Intel Mac 不受支持。

终端显示 **Ready** 后，在 Finder 按 **⇧⌘H** 打开个人文件夹，进入「应用程序」并双击 **Local Harness**。推理服务会在登录时自动启动，仅监听本机 8000 端口。无需云账户、API Key、Homebrew、Xcode 或管理员权限。若网络中断，重新执行同一命令即可续装。若端口已被其他服务占用，先释放端口再运行。

代码、桌面补丁和安装脚本公开。安装器在本机校验原厂签名、下载摘要及模型文件，为每台 Mac 生成独立的本地凭据。已安装版本经过本地签名；有统一签名或公证要求的单位，请先按内部流程评估。长上下文和多任务的速度取决于芯片与工作负载。首次使用可用一个小项目试跑。

[安装脚本](install.sh) · [英文使用说明](README.md) · [隐私与安全边界](SECURITY.md) · [部署者职责](OPERATOR-NOTICE.md)

## 停用或卸载

退出 Local Harness。要停用登录时启动的服务，请运行：

```bash
launchctl bootout "gui/$(id -u)/local.harness.offline.inference"
```

在 Finder 按 **⇧⌘G**，分别前往 `~/Library/LaunchAgents` 移除 `local.harness.offline.inference.plist`，前往 `~/Applications` 移除 `Local Harness.app`。要释放模型和运行时空间，进入 `~/Library/Application Support/Local Harness`，移除 `Models`、`Runtime`、`Downloads` 和 `Inference`。保留其余子目录即可保留桌面会话和工作区。官方在线版使用独立的应用和配置目录。
