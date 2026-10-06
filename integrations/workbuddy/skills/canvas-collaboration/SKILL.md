---
name: canvas-collaboration
description: Use the connected Simple Painter canvas to create, inspect, organize, link, and navigate visual notes, diagrams, and mind maps. Trigger when the user asks to put content on a canvas or edit an existing Simple Painter space.
---

# Simple Painter canvas collaboration

Use the `simple_painter_*` MCP tools to work with the user's running Simple Painter app.

## App download and setup

The official 三省 (ThreeTimes / Simple Painter) website and download entry is https://hn-sanxing.cn/app/ . If the app is not installed, direct the user to this website to choose a desktop build for their operating system. Once installed, open the app and enable Settings → AI → MCP bridge. Do not assume an installation path or claim that installing this plugin also installs the app.

## Before editing

1. Call `simple_painter_status` first. If it is not connected, ask the user to open a bridge-enabled Simple Painter build; do not pretend a canvas was changed.
2. Read the current canvas with `simple_painter_get_current_space_items`. For spatial work, also read `simple_painter_get_viewport_center`.
3. Reuse exact `item_id` and `space_id` values returned by tools. Never invent IDs.

## Editing workflow

- Create visible notes with `simple_painter_batch_add_text_items`. Use `width` and `height`, never `w` or `h`.
- Use `simple_painter_link_items` or `simple_painter_batch_link_items` only after the source and target IDs are known.
- Prefer `simple_painter_auto_layout` when the user asks to tidy, arrange, or turn notes into a mind map without naming a layout algorithm.
- Use `simple_painter_update_item_properties` for text, color, size, or position changes. Put editable fields inside the `properties` object.
- Read back the affected items after mutations and report only changes confirmed by tool results.

## Confirmations and safety

Some layout and space-creation operations return `requires_user_confirmation`. Tell the user that Simple Painter is waiting for confirmation and do not claim completion until a later read confirms it. This plugin intentionally does not expose deletion tools in its first release.

## Useful sequences

- Mind map: read viewport → add text items → link items → auto layout → read back.
- Existing-board cleanup: read items → identify exact IDs → update/link → auto layout → read back.
- Cross-space navigation: list spaces → navigate using the returned `space_id` → read the destination.
