"""Hash a prepared wheelhouse. Integrity checking is NOT a publisher signature."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def inventory(root: Path) -> dict[str, str]:
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'Symlink is not allowed in offline bundle: {path}')
        if path.is_file() and path.name != 'manifest.json':
            result[path.relative_to(root).as_posix()] = digest(path)
    return result


def create(root: Path) -> None:
    files = inventory(root)
    if 'requirements-build.txt' not in files or not any(n.endswith('.whl') for n in files):
        raise ValueError('Bundle must contain requirements-build.txt and wheels.')
    (root / 'manifest.json').write_text(json.dumps({'version': 1, 'files': files}, indent=2), encoding='utf-8')


def verify(root: Path, requirements: Path | None = None) -> None:
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('version') != 1 or manifest.get('files') != inventory(root):
        raise ValueError('Offline bundle is incomplete, modified, or contains unexpected files.')
    if requirements and digest(root / 'requirements-build.txt') != digest(requirements):
        raise ValueError('Bundle requirements differ from this source revision; prepare a new bundle.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['create', 'verify'])
    parser.add_argument('bundle', type=Path)
    parser.add_argument('--requirements', type=Path)
    args = parser.parse_args()
    if args.action == 'create':
        create(args.bundle)
    else:
        verify(args.bundle, args.requirements)
    print(f'Bundle {args.action}: OK')
