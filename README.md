# 三省 MCP

三省官网与下载入口：**https://hn-sanxing.cn/app/**。本仓库提供本地 MCP 程序、Codex / WorkBuddy 插件安装工具和使用说明，不包含三省客户端源码。

## 给 AI 的安装指引

用户可以将本仓库链接交给具有本机操作能力的 AI，要求“帮我安装三省 MCP”。先确认系统、Python 3.10+ 和目标客户端。未安装三省时，引导用户访问官网下载安装桌面版；打开「设置 → AI → MCP 桥接」。本程序不会自动下载客户端。

构建安装包：

```sh
python3 integrations/quick-install/build_bundle.py
```

解压 `dist/three-times-mcp.zip`，macOS 双击对应 `.command`，Windows 双击 `.cmd`，或在解压目录运行：

```sh
python3 install.py --target codex
python3 install.py --target workbuddy
```

见 [安装说明](integrations/quick-install/README.md)。程序保存到长期应用数据目录，再生成当前电脑的插件配置，不依赖仓库位置；不要把某台电脑的绝对路径放入共享配置。

## DeepSeek Harness

通过官方 MCP 客户端配置本地 STDIO，替换以下路径为本机路径。此示例尚未经过 Harness 桌面端联调。

```yaml
- id: mcp-three-times
  name: '@deepseek-ai/dsh-mcp-client'
  config:
    serverName: three-times
    transport: stdio
    command: /absolute/path/to/python3
    args: ['/absolute/path/to/simple_painter_mcp.py']
```

脚本在 `integrations/workbuddy/server/simple_painter_mcp.py` 或快捷安装后的长期应用数据目录。

## 状态与访问

Codex 安装和读取已验证；WorkBuddy 安装文件已提供，尚未实测客户端；Harness 尚未联调。GitHub 分发不代表官方市场收录。

桥接仅连接本机回环地址，凭证不进入仓库。工具可读写画布，请遵守客户端确认要求。先调用 `simple_painter_status` 检查连接，再读取画布；关闭三省或桥接后不能操作画布。

## 验证

```sh
python3 -m unittest discover -s integrations/quick-install/test -p '*_test.py'
python3 -m unittest discover -s integrations/workbuddy/test -p '*_test.py'
```
