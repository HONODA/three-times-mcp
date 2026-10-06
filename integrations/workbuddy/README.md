# Simple Painter for WorkBuddy

This local plugin connects WorkBuddy to the full-stack Simple Painter example over a loopback-only MCP bridge. It reuses the app's existing AI tool policy, argument validation, and in-app confirmation flow.

## What the first release can do

- Inspect current, visible, or selected canvas items.
- Search the current space or other spaces.
- Add and update text cards.
- Move and connect existing items.
- Arrange linked networks and trees with in-app confirmation.
- List, create, and navigate spaces.

Deletion is intentionally not exposed in version `0.1.0`.

## Run Simple Painter with the bridge

Desktop builds enable the MCP bridge by default. Toggle it in Settings → AI → MCP bridge; the choice is saved locally and takes effect immediately. An explicit `ENABLE_WORKBUDDY_BRIDGE` build flag supplies the default only when no saved choice exists.

From the repository root:

```bash
cd example/fullstack_example
flutter run -d macos --dart-define=ENABLE_WORKBUDDY_BRIDGE=true
```

The app binds an ephemeral port on `127.0.0.1` and writes a random per-session bearer token to the user temporary directory. The descriptor is removed when the app closes. To use a fixed descriptor location during development, add:

```bash
--dart-define=WORKBUDDY_BRIDGE_DESCRIPTOR_PATH=/absolute/path/bridge.json
```

Then set the same path for the MCP process with `SIMPLE_PAINTER_BRIDGE_FILE`.

On macOS, the MCP adapter automatically checks both the normal temporary
directory and the sandbox container used by the `com.hn.threetimes2` desktop
app. No extra path configuration is required for the full-stack example.

## Install in WorkBuddy

The parent `integrations` directory is a local plugin marketplace:

1. Open WorkBuddy → Plugins → add a third-party/local marketplace.
2. Select the absolute path to this repository's `integrations` directory.
3. Install and enable `simple-painter`.
4. Reload plugins if WorkBuddy asks.

For a CLI-enabled CodeBuddy/WorkBuddy installation, the equivalent development flow is:

```bash
codebuddy plugin marketplace add /absolute/path/to/simple_painter/integrations
codebuddy plugin install simple-painter@simple-painter-local
```

Start with a prompt such as:

> 检查 Simple Painter 是否已连接，把当前画布上的项目整理成思维导图。先读取项目，所有 ID 都使用工具返回值。

The included Skill tells WorkBuddy to check the connection, read before writing, avoid invented IDs, and wait for in-app confirmations.

## Validate without WorkBuddy

Run the standalone protocol tests:

```bash
python3 -m unittest discover -s integrations/workbuddy/test -p '*_test.py'
```

Run the bridge HTTP test:

```bash
cd example/fullstack_example
flutter test test/workbuddy_bridge_server_test.dart
```

The MCP server has no third-party Python dependencies. It supports the MCP initialize, ping, tool discovery, and tool call flow over stdio.

## Security model

- The Flutter bridge binds only to IPv4 loopback.
- Each app session gets a new 256-bit random bearer token.
- The connection descriptor is permissioned to the current user on POSIX systems.
- Tool names are allowlisted in the Flutter app.
- Existing Simple Painter validation and confirmation policies remain in effect.
- The MCP adapter rejects non-loopback descriptors.
