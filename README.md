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

## 空间归属建议（0.4.0）

外部 AI 可以用 `simple_painter_get_space_summaries` 阅读本地空间名称、父子层级、代表卡片摘录和整理稿标题。支持 `space_ids`、`offset`、`limit`、`sample_limit`；按 `next_offset` 翻页。当前空间使用未保存的实时卡片，其他空间使用本地快照。恢复副本不作为归属推荐目标；不存在或无法读取的空间明确标识，不能当成空空间。

`simple_painter_search_canvas_items` 已提供跨空间检索；0.4.0 的离线目录补齐 `scope: all/subtree/current`、`space_ids`、`item_ids` 和分页参数，与客户端一致。先查相关内容，再解释推荐位置；用户明确指定空间时按指定位置处理。确认目标后导航并重新读取，再执行已授权的写入。概览本身不会切换空间或移动卡片，未实现自动归档或偏好学习。本更新不修改三省内置 AI 提示词。

这些接口需要新版三省客户端，仅更新插件不会给旧客户端增加接口。

## 新增能力（0.3.0）

- **整理稿**：列出与读取当前空间稿件、读取白板来源及引用链接、创建 Markdown 稿件、修改正文、显式保存。AI 可以读来源后撰写整理稿，无需额外调用内置 AI。
- **原生思维导图**：创建完整层级、新增子主题、布局、普通卡片依附与批量依附、脱离父分支、读取及修改已有主题。导图操作沿用三省应用内确认流程。

需要运行包含新增接口的三省客户端；只更新插件不能让旧版客户端获得新接口。整理稿是独立文档，创建和修改保留恢复正文，不自动标记已保存；保存使用单独工具。修改/保存前读取稿件，传回精确的 `expected_text` 与 `expected_updated_at`。冲突必须重新读取。正在编辑的稿件会拒绝外部写入，请先关闭整理稿编辑器。整理稿目前仅在本机保存，MCP 未开放删除稿件或卡片工具。

## 状态与访问

Codex 原有安装和画布读取已验证；新增接口通过协议、文档存储和导图回归测试，尚未在当前运行的旧客户端中联调；WorkBuddy 安装文件已提供，尚未实测客户端；Harness 尚未联调。GitHub 分发不代表官方市场收录。

桥接仅连接本机回环地址，凭证不进入仓库。工具可读写画布，请遵守客户端确认要求。先调用 `simple_painter_status` 检查连接，再读取画布；关闭三省或桥接后不能操作画布。

## 验证

```sh
python3 -m unittest discover -s integrations/quick-install/test -p '*_test.py'
python3 -m unittest discover -s integrations/workbuddy/test -p '*_test.py'
```
