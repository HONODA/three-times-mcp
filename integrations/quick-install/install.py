#!/usr/bin/env python3
"""Install the bundled ThreeTimes MCP without requiring a source checkout."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

MARKETPLACE = 'three-times-local'
VERSION = '0.2.0'


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def default_destination() -> Path:
    if sys.platform == 'darwin':
        return Path.home() / 'Library' / 'Application Support' / 'ThreeTimes' / 'MCP'
    if os.name == 'nt':
        return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'ThreeTimes' / 'MCP'
    return Path.home() / '.local' / 'share' / 'three-times' / 'mcp'


def prepare(source: Path, destination: Path, python: str) -> dict:
    """Only our named assets are updated; unrelated configuration is preserved."""
    destination = destination.resolve()
    server = destination / 'server' / 'simple_painter_mcp.py'
    server.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / 'server' / server.name, server)
    mcp = {'mcpServers': {'simple-painter': {
        'command': python, 'args': [str(server)],
        'env': {'PYTHONUNBUFFERED': '1'},
    }}}
    roots = {}
    for target in ('codex', 'workbuddy'):
        root = destination / (target + '-marketplace')
        plugin = root / 'plugins' / 'simple-painter'
        skill = plugin / 'skills' / 'canvas-collaboration' / 'SKILL.md'
        skill.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / 'skills' / 'canvas-collaboration' / 'SKILL.md', skill)
        write_json(plugin / '.mcp.json', mcp)
        metadata = {
            'name': 'simple-painter', 'version': VERSION,
            'description': 'Read and edit the running ThreeTimes canvas through a local MCP bridge.',
            'author': {'name': 'ThreeTimes'},
        }
        if target == 'codex':
            metadata.update({'skills': './skills/', 'mcpServers': './.mcp.json',
                             'interface': {'displayName': '三省',
                                           'shortDescription': '连接本机三省画布',
                                           'developerName': 'ThreeTimes',
                                           'category': 'Productivity'}})
            write_json(plugin / '.codex-plugin' / 'plugin.json', metadata)
            write_json(root / '.agents' / 'plugins' / 'marketplace.json', {
                'name': MARKETPLACE,
                'interface': {'displayName': '三省本地插件'},
                'plugins': [{'name': 'simple-painter',
                             'source': {'source': 'local', 'path': './plugins/simple-painter'},
                             'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_INSTALL'},
                             'category': 'Productivity'}],
            })
        else:
            write_json(plugin / '.codebuddy-plugin' / 'plugin.json', metadata)
            write_json(root / '.codebuddy-plugin' / 'marketplace.json', {
                'name': MARKETPLACE, 'owner': {'name': 'ThreeTimes'},
                'plugins': [{'name': 'simple-painter', 'source': './plugins/simple-painter',
                             'description': metadata['description'], 'version': VERSION}],
            })
        roots[target] = root
    write_json(destination / 'mcp.json', mcp)
    return roots


def find_cli(target: str) -> str | None:
    name = 'codex' if target == 'codex' else 'codebuddy'
    found = shutil.which(name)
    if found:
        return found
    if target == 'codex' and sys.platform == 'darwin':
        for app in ('ChatGPT', 'Codex'):
            candidate = Path('/Applications') / (app + '.app') / 'Contents' / 'Resources' / 'codex-cli' / 'CodexCLI.app' / 'Contents' / 'MacOS' / 'codex'
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
    return None


def install(target: str, marketplace: Path) -> bool:
    cli = find_cli(target)
    if cli is None:
        print('未找到 ' + target + ' 命令行程序。安装文件已准备好。')
        if target == 'workbuddy':
            print('请在 WorkBuddy → 插件 → 添加本地插件市场，选择：\n' + str(marketplace))
            print('然后安装并启用 simple-painter。')
        else:
            print('安装 Codex CLI 后重新运行本安装程序，或在 Codex 的 MCP 设置中使用：')
            print(str(marketplace.parents[0] / 'mcp.json'))
        return False
    # Argument lists preserve spaces and avoid shell interpolation.
    subprocess.run([cli, 'plugin', 'marketplace', 'add', str(marketplace)], check=True)
    command = 'add' if target == 'codex' else 'install'
    subprocess.run([cli, 'plugin', command, 'simple-painter@' + MARKETPLACE], check=True)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description='三省 MCP 快捷安装')
    parser.add_argument('--target', choices=('codex', 'workbuddy'), required=True)
    parser.add_argument('--destination', type=Path)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error('需要 Python 3.10 或更高版本，请从 python.org 安装后重试。')
    source = Path(__file__).resolve().parent
    roots = prepare(source, args.destination or default_destination(), str(Path(sys.executable).resolve()))
    root = roots[args.target]
    print('插件市场：' + str(root))
    if args.prepare_only:
        return 0
    try:
        if not install(args.target, root):
            return 2
    except (OSError, subprocess.CalledProcessError) as error:
        print('自动安装未完成：' + str(error), file=sys.stderr)
        print('安装文件已保留。排除错误后可重新运行，或手动添加上述插件市场。', file=sys.stderr)
        return 1
    print('安装完成。保持三省运行并开启 MCP 桥接，然后在 ' + args.target + ' 新会话中启用三省插件。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
