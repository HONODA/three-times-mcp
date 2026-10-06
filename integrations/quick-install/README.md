# 三省 MCP 快捷安装

三省官网与下载入口：https://hn-sanxing.cn/app/ 。尚未安装三省时，请先访问官网选择适合当前系统的桌面版本。

1. 运行支持 MCP 的三省桌面版，在「设置 → AI → MCP 桥接」保持开启。
2. 解压安装包。macOS 双击 `Install-codex.command` 或 `Install-workbuddy.command`；Windows 双击对应的 `.cmd`。Linux 使用 `python3 install.py --target codex` 或 `--target workbuddy`。
3. 安装后在 AI 工具的新会话中启用三省插件，先要求检查连接，再读取当前画布。

需要 Python 3.10 或更高版本；安装程序会检查环境，不会自动下载软件。Codex 桌面版的内置 CLI 可自动找到；WorkBuddy 若没有 CodeBuddy CLI，会显示本地插件市场路径，在 WorkBuddy 插件页面添加该路径并安装 `simple-painter` 即可。

适配程序复制到用户的长期应用数据目录，下载的 ZIP 和解压目录安装后可删除。不会覆盖完整的 Codex / WorkBuddy 设置；由各产品的官方 CLI 安装插件。重跑安装程序可更新同名插件。已有单独配置的三省 MCP，可在新插件确认可用后关闭旧连接，避免重复工具。

本程序只连接本机回环地址。会话凭证由三省生成，不包含在安装包或插件配置中。关闭三省或桥接后，AI 工具无法读写画布。工具列表可显示不代表已经连到三省，必须检查 `simple_painter_status`。

外部 AI 空间归属：`get_space_summaries` 提供本地空间层级、代表卡片摘录和整理稿标题；`search_canvas_items` 支持跨空间范围、指定空间和分页检索。AI 根据实际证据推荐位置，概览本身不会切换空间或移动内容。

新增能力：独立整理稿的列出、读取、来源引用、创建、修改与显式保存；原生思维导图创建、增补、布局及卡片依附/脱离。需要包含这些接口的新版三省客户端。整理稿写入需要先关闭其编辑器，并提供最近读取的正文和版本以避免覆盖。原生导图操作沿用应用确认流程。

开发者：修改 MCP 程序、技能或安装脚本后，执行 `python3 integrations/quick-install/build_bundle.py` 更新随应用发布的 ZIP。
