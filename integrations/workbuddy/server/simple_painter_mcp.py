#!/usr/bin/env python3
"""Dependency-free MCP stdio adapter for the Simple Painter desktop bridge."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional


SERVER_NAME = "simple-painter-workbuddy"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2025-06-18"
SUPPORTED_PROTOCOL_VERSIONS = {"2024-11-05", "2025-03-26", PROTOCOL_VERSION}
DESCRIPTOR_FILE_NAME = "simple-painter-workbuddy-bridge.json"
TOOL_PREFIX = "simple_painter_"


def _object_schema(properties: Optional[Dict[str, Any]] = None, required: Optional[List[str]] = None) -> Dict[str, Any]:
    schema: Dict[str, Any] = {
        "type": "object",
        "properties": properties or {},
        "additionalProperties": False,
    }
    if required:
        schema["required"] = required
    return schema


def _fallback_tools() -> List[Dict[str, Any]]:
    number = {"type": "number"}
    string = {"type": "string"}
    boolean = {"type": "boolean"}
    item_id = {"type": "string", "description": "An exact item_id returned by a Simple Painter read tool."}
    read_annotation = {
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    }
    write_annotation = {
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False,
    }

    tools: List[Dict[str, Any]] = [
        {
            "name": "simple_painter_status",
            "description": "Check whether the Simple Painter desktop bridge is running and connected.",
            "inputSchema": _object_schema(),
            "annotations": read_annotation,
        },
        {
            "name": f"{TOOL_PREFIX}get_current_space_items",
            "description": "List item metadata from the current Simple Painter space.",
            "inputSchema": _object_schema({"limit": number, "brief": boolean}),
            "annotations": read_annotation,
        },
        {
            "name": f"{TOOL_PREFIX}get_visible_items",
            "description": "List items currently visible in the Simple Painter viewport.",
            "inputSchema": _object_schema({"limit": number, "brief": boolean}),
            "annotations": read_annotation,
        },
        {
            "name": f"{TOOL_PREFIX}get_selected_item",
            "description": "Read the currently selected Simple Painter item.",
            "inputSchema": _object_schema({"brief": boolean}),
            "annotations": read_annotation,
        },
        {
            "name": f"{TOOL_PREFIX}get_viewport_center",
            "description": "Read the current canvas viewport center and bounds.",
            "inputSchema": _object_schema(),
            "annotations": read_annotation,
        },
        {
            "name": f"{TOOL_PREFIX}search_canvas_items",
            "description": "Search canvas items by query, IDs, type, scope, region, or color.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": string,
                    "scope": {"type": "string", "enum": ["current", "subtree", "all"]},
                    "space_ids": {"type": "array", "items": string},
                    "item_ids": {"type": "array", "items": string},
                    "cursor": string,
                    "page_size": number,
                    "limit": number,
                    "types": {"type": "array", "items": string},
                    "region": string,
                    "color": string,
                    "near_item_id": item_id,
                    "match_mode": {"type": "string", "enum": ["hybrid", "semantic", "keyword"]},
                },
                "additionalProperties": False,
            },
            "annotations": read_annotation,
        },
        {
            "name": f"{TOOL_PREFIX}list_spaces",
            "description": "List all Simple Painter spaces and their exact space IDs.",
            "inputSchema": _object_schema(),
            "annotations": read_annotation,
        },
        {
            "name": f"{TOOL_PREFIX}navigate_to_space",
            "description": "Navigate to a space using an exact space ID or label.",
            "inputSchema": {
                "type": "object",
                "properties": {"target_space_id": string, "target_space_label": string},
                "anyOf": [{"required": ["target_space_id"]}, {"required": ["target_space_label"]}],
                "additionalProperties": False,
            },
            "annotations": write_annotation,
        },
        {
            "name": f"{TOOL_PREFIX}batch_add_text_items",
            "description": "Create one or more visible text cards on the current canvas.",
            "inputSchema": _object_schema(
                {
                    "absolute_position": boolean,
                    "items": {
                        "type": "array",
                        "items": _object_schema(
                            {"text": string, "x": number, "y": number, "width": number, "height": number},
                            ["text"],
                        ),
                    },
                },
                ["items"],
            ),
            "annotations": write_annotation,
        },
        {
            "name": f"{TOOL_PREFIX}move_item",
            "description": "Move one canvas item to an absolute x/y position.",
            "inputSchema": _object_schema({"item_id": item_id, "x": number, "y": number}, ["item_id", "x", "y"]),
            "annotations": write_annotation,
        },
        {
            "name": f"{TOOL_PREFIX}update_item_properties",
            "description": "Update position, size, text, colors, or other properties on one item. Put changed fields inside properties.",
            "inputSchema": _object_schema(
                {
                    "item_id": item_id,
                    "properties": {
                        "type": "object",
                        "properties": {
                            "x": number, "y": number, "width": number, "height": number, "rotation": number,
                            "name": string, "text": string, "font_size": number, "text_align": string,
                            "render_mode": string, "text_color": string, "background_color": string,
                            "line_color": string, "thickness": number, "border_width": number,
                            "border_color": string, "border_radius": number, "label": string,
                            "curvature": number, "connector_thickness": number,
                        },
                        "additionalProperties": False,
                    },
                },
                ["item_id", "properties"],
            ),
            "annotations": write_annotation,
        },
        {
            "name": f"{TOOL_PREFIX}batch_update_items",
            "description": "Update properties for multiple items in one call.",
            "inputSchema": _object_schema(
                {"items": {"type": "array", "items": {"type": "object", "additionalProperties": True}}},
                ["items"],
            ),
            "annotations": write_annotation,
        },
        {
            "name": f"{TOOL_PREFIX}link_items",
            "description": "Link a source item to a target item, optionally with a visible connector label.",
            "inputSchema": _object_schema(
                {"source_id": item_id, "target_id": item_id, "target_space_id": string, "label": string},
                ["source_id", "target_id"],
            ),
            "annotations": write_annotation,
        },
        {
            "name": f"{TOOL_PREFIX}batch_link_items",
            "description": "Link several item pairs and arrange the resulting network.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "bidirectional": boolean,
                    "items": {
                        "type": "array",
                        "items": _object_schema(
                            {"source_id": item_id, "target_id": item_id, "target_space_id": string, "bidirectional": boolean, "label": string},
                            ["source_id", "target_id"],
                        ),
                    },
                },
                "additionalProperties": False,
            },
            "annotations": write_annotation,
        },
        {
            "name": f"{TOOL_PREFIX}auto_layout",
            "description": "Automatically choose a suitable layout for a linked cluster or the current space. Requires in-app confirmation.",
            "inputSchema": _object_schema({"item_id": item_id}),
            "annotations": write_annotation,
        },
        {
            "name": f"{TOOL_PREFIX}auto_layout_links",
            "description": "Arrange an existing linked network around an anchor item. Requires in-app confirmation.",
            "inputSchema": _object_schema({"item_id": item_id}, ["item_id"]),
            "annotations": write_annotation,
        },
        {
            "name": f"{TOOL_PREFIX}auto_layout_tree",
            "description": "Arrange a tree from a root item. Requires in-app confirmation.",
            "inputSchema": _object_schema({"item_id": item_id, "depth": number, "max_nodes": number}, ["item_id"]),
            "annotations": write_annotation,
        },
        {
            "name": f"{TOOL_PREFIX}zoom_to_fit_items",
            "description": "Zoom the canvas viewport to fit exact item IDs.",
            "inputSchema": _object_schema({"item_ids": {"type": "array", "items": item_id}}, ["item_ids"]),
            "annotations": write_annotation,
        },
        {
            "name": f"{TOOL_PREFIX}get_linked_cluster",
            "description": "Read the connected item cluster around an anchor item.",
            "inputSchema": _object_schema({"item_id": item_id, "depth": number, "max_nodes": number}, ["item_id"]),
            "annotations": read_annotation,
        },
        {
            "name": f"{TOOL_PREFIX}create_space",
            "description": "Create a nested Simple Painter space portal. Requires in-app confirmation.",
            "inputSchema": _object_schema({"label": string, "x": number, "y": number}, ["label"]),
            "annotations": write_annotation,
        },
    ]
    return tools


class BridgeError(RuntimeError):
    pass


class SimplePainterBridge:
    def __init__(self) -> None:
        explicit = os.environ.get("SIMPLE_PAINTER_BRIDGE_FILE", "").strip()
        if explicit:
            self.descriptor_paths = [Path(explicit)]
        else:
            self.descriptor_paths = self._default_descriptor_paths()
        self.descriptor_path = self.descriptor_paths[0]

    @staticmethod
    def _default_descriptor_paths() -> List[Path]:
        # A sandboxed macOS app receives a container-specific temporary
        # directory, while WorkBuddy's MCP subprocess sees the user's normal
        # temporary directory. Check both locations so the two processes can
        # rendezvous without requiring a machine-specific configuration.
        candidates = [
            Path.home()
            / "Library"
            / "Containers"
            / "com.hn.threetimes2"
            / "Data"
            / "tmp"
            / DESCRIPTOR_FILE_NAME,
            Path(tempfile.gettempdir()) / DESCRIPTOR_FILE_NAME,
        ]
        unique: List[Path] = []
        for candidate in candidates:
            if candidate not in unique:
                unique.append(candidate)
        return unique

    @staticmethod
    def _descriptor(path: Path) -> Dict[str, Any]:
        try:
            descriptor = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise BridgeError(f"Cannot read the Simple Painter bridge descriptor at {path}: {error}") from error
        if not isinstance(descriptor, dict):
            raise BridgeError(f"The Simple Painter bridge descriptor at {path} is invalid.")
        return descriptor

    def request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        failures: List[str] = []
        for descriptor_path in self.descriptor_paths:
            try:
                descriptor = self._descriptor(descriptor_path)
            except FileNotFoundError:
                continue
            try:
                response = self._request_descriptor(descriptor, method, path, payload)
            except BridgeError as error:
                failures.append(f"{descriptor_path}: {error}")
                continue
            self.descriptor_path = descriptor_path
            return response
        if failures:
            raise BridgeError("; ".join(failures))
        checked = ", ".join(str(candidate) for candidate in self.descriptor_paths)
        raise BridgeError(
            "Simple Painter is not connected. Open a bridge-enabled Simple Painter "
            f"desktop build. Checked: {checked}"
        )

    def _request_descriptor(
        self,
        descriptor: Dict[str, Any],
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        host = str(descriptor.get("host") or "127.0.0.1")
        port = int(descriptor.get("port") or 0)
        token = str(descriptor.get("token") or "")
        if host not in {"127.0.0.1", "::1", "localhost"} or port <= 0 or not token:
            raise BridgeError("The Simple Painter bridge descriptor is incomplete or unsafe.")
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"http://{host}:{port}{path}",
            data=data,
            method=method,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(request, timeout=8) as response:
                decoded = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            raise BridgeError(f"Cannot reach the Simple Painter desktop bridge: {error}") from error
        if not isinstance(decoded, dict):
            raise BridgeError("Simple Painter returned an invalid bridge response.")
        return decoded

    def status(self) -> Dict[str, Any]:
        try:
            response = self.request("GET", "/health")
            return {
                "ok": bool(response.get("ok")),
                "connected": bool(response.get("ok")),
                "descriptor_path": str(self.descriptor_path),
                **response,
            }
        except BridgeError as error:
            return {
                "ok": False,
                "connected": False,
                "error": str(error),
                "descriptor_paths": [str(path) for path in self.descriptor_paths],
            }

    def tools(self) -> Optional[List[Dict[str, Any]]]:
        try:
            response = self.request("GET", "/v1/tools")
        except BridgeError:
            return None
        tools = response.get("tools")
        if not isinstance(tools, list):
            return None
        return [tool for tool in tools if isinstance(tool, dict)]

    def call(self, name: str, arguments: Dict[str, Any]) -> Any:
        response = self.request("POST", "/v1/tools/call", {"name": name, "arguments": arguments})
        if not response.get("ok"):
            raise BridgeError(str(response.get("error") or "Simple Painter tool call failed."))
        return response.get("result")


class McpServer:
    def __init__(self, input_stream: BinaryIO, output_stream: BinaryIO) -> None:
        self.input_stream = input_stream
        self.output_stream = output_stream
        self.bridge = SimplePainterBridge()

    def serve_forever(self) -> None:
        while True:
            message = self._read_message()
            if message is None:
                return
            try:
                response = self._handle(message)
            except Exception as error:  # Keep the MCP process alive for later calls.
                request_id = message.get("id") if isinstance(message, dict) else None
                response = self._error(request_id, -32603, str(error)) if request_id is not None else None
            if response is not None:
                self._write_message(response)

    def _read_message(self) -> Optional[Dict[str, Any]]:
        line = self.input_stream.readline()
        if not line:
            return None
        if line.lower().startswith(b"content-length:"):
            try:
                length = int(line.split(b":", 1)[1].strip())
            except ValueError as error:
                raise BridgeError("Invalid Content-Length header.") from error
            while True:
                header = self.input_stream.readline()
                if header in {b"\r\n", b"\n", b""}:
                    break
            raw = self.input_stream.read(length)
        else:
            raw = line.strip()
        if not raw:
            return self._read_message()
        decoded = json.loads(raw.decode("utf-8"))
        if not isinstance(decoded, dict):
            raise BridgeError("MCP messages must be JSON objects.")
        return decoded

    def _write_message(self, message: Dict[str, Any]) -> None:
        data = json.dumps(message, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
        self.output_stream.write(data)
        self.output_stream.flush()

    def _handle(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        method = message.get("method")
        request_id = message.get("id")
        params = message.get("params") if isinstance(message.get("params"), dict) else {}
        if method == "initialize":
            requested = str(params.get("protocolVersion") or PROTOCOL_VERSION)
            return self._result(
                request_id,
                {
                    "protocolVersion": requested if requested in SUPPORTED_PROTOCOL_VERSIONS else PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                    "instructions": "Open ThreeTimes and enable the MCP bridge in Settings before calling canvas tools.",
                },
            )
        if method in {"notifications/initialized", "notifications/cancelled"}:
            return None
        if method == "ping":
            return self._result(request_id, {})
        if method == "tools/list":
            dynamic_tools = self.bridge.tools()
            fallback = _fallback_tools()
            if dynamic_tools is not None:
                status_tool = fallback[0]
                tools = [status_tool, *[tool for tool in dynamic_tools if tool.get("name") != status_tool["name"]]]
            else:
                tools = fallback
            return self._result(request_id, {"tools": tools})
        if method == "tools/call":
            name = str(params.get("name") or "")
            arguments = params.get("arguments") if isinstance(params.get("arguments"), dict) else {}
            if name == "simple_painter_status":
                return self._tool_result(request_id, self.bridge.status())
            if not name.startswith(TOOL_PREFIX):
                return self._tool_result(request_id, {"ok": False, "error": f"Unknown tool: {name}"}, is_error=True)
            try:
                result = self.bridge.call(name, arguments)
            except BridgeError as error:
                return self._tool_result(request_id, {"ok": False, "error": str(error)}, is_error=True)
            is_error = isinstance(result, dict) and result.get("ok") is False
            return self._tool_result(request_id, result, is_error=is_error)
        if method in {"resources/list", "prompts/list"}:
            key = "resources" if method == "resources/list" else "prompts"
            return self._result(request_id, {key: []})
        if request_id is None:
            return None
        return self._error(request_id, -32601, f"Method not found: {method}")

    def _tool_result(self, request_id: Any, value: Any, is_error: bool = False) -> Dict[str, Any]:
        text = json.dumps(value, ensure_ascii=False, indent=2)
        result: Dict[str, Any] = {"content": [{"type": "text", "text": text}], "isError": is_error}
        if isinstance(value, dict):
            result["structuredContent"] = value
        return self._result(request_id, result)

    @staticmethod
    def _result(request_id: Any, result: Dict[str, Any]) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    @staticmethod
    def _error(request_id: Any, code: int, message: str) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def main() -> None:
    McpServer(sys.stdin.buffer, sys.stdout.buffer).serve_forever()


if __name__ == "__main__":
    main()
