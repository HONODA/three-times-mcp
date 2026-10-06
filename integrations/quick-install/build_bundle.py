#!/usr/bin/env python3
"""Build the reproducible ZIP bundled in the Flutter app."""
from pathlib import Path
import argparse
import zipfile

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / 'dist/three-times-mcp.zip'


def build(output: Path) -> None:
    files = {
        'install.py': (ROOT / 'integrations/quick-install/install.py').read_bytes(),
        'server/simple_painter_mcp.py': (ROOT / 'integrations/workbuddy/server/simple_painter_mcp.py').read_bytes(),
        'skills/canvas-collaboration/SKILL.md': (ROOT / 'integrations/workbuddy/skills/canvas-collaboration/SKILL.md').read_bytes(),
        'README.md': (ROOT / 'integrations/quick-install/README.md').read_bytes(),
    }
    for target in ('codex', 'workbuddy'):
        # Terminal login shells provide the user's normal CLI PATH.
        files['Install-' + target + '.command'] = ('''#!/bin/bash
cd -- "$(dirname -- "$0")" || exit 1
python_bin=""
for candidate in python3 /opt/homebrew/bin/python3 /usr/local/bin/python3 /Library/Frameworks/Python.framework/Versions/Current/bin/python3; do
  if "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
    python_bin="$candidate"
    break
  fi
done
if [ -z "$python_bin" ]; then
  echo '需要 Python 3.10 或更高版本，请从 python.org 安装后重试。'
  read -r -p '按回车关闭…'
  exit 1
fi
"$python_bin" install.py --target ''' + target + '''
result=$?
read -r -p '按回车关闭…'
exit "$result"
''').encode()
        files['Install-' + target + '.cmd'] = ('''@echo off\r\ncd /d "%~dp0"\r\nwhere py >nul 2>nul\r\nif errorlevel 1 (\r\n  python install.py --target ''' + target + '''\r\n) else (\r\n  py -3 install.py --target ''' + target + '''\r\n)\r\nset result=%errorlevel%\r\npause\r\nexit /b %result%\r\n''').encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo('three-times-mcp/' + name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o100755 if name.endswith('.command') else 0o100644) << 16
            bundle.writestr(info, data)
    print(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    build(parser.parse_args().output)
