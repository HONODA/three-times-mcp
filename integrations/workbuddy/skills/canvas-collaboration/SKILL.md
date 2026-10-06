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

## Organized drafts

Organized drafts are independent Markdown documents, not canvas cards. Use `simple_painter_list_organized_drafts` and `simple_painter_get_organized_draft` to read them in the current space. To organize the whiteboard, read `simple_painter_get_organized_draft_sources`, compose Markdown that distinguishes facts from inference and preserves `citation_url` links, then call `simple_painter_create_organized_draft`. Do not call an additional AI service or substitute canvas cards for a draft.

Before `simple_painter_update_organized_draft` or `simple_painter_save_organized_draft`, read the exact text and `updated_at`, and supply them as `expected_text` and `expected_updated_at`. A conflict requires a fresh read; never retry blindly. Close the document editor before an external write. Creation and updates preserve recovery text and leave the saved baseline unchanged; only save explicitly when the user requests it. Drafts currently remain local to this account/device.

## Native mind maps

Use `simple_painter_create_mind_map` for a complete native tree, `simple_painter_add_mind_map_node` for a child, and `simple_painter_layout_mind_map` for arrangement. Read real IDs with canvas read tools; temporary node keys are only for initial creation. Edit existing text with `simple_painter_replace_text_in_item` or property updates. Use `simple_painter_attach_mind_map_card` / `simple_painter_batch_attach_mind_map_cards` to attach existing cards; `simple_painter_detach_mind_map_card` preserves the card and subtree. These tree operations use the app's confirmation workflow. Never substitute ordinary linked text cards for a requested native mind map.

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
