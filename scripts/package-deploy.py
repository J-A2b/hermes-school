"""Package explicitly allowed source files, never runtime data or secrets."""
import hashlib
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOP_FILES = ('pyproject.toml', 'README.md', 'LICENSE', '.gitignore', '.gitattributes', 'requirements-windows.lock')
SOURCE_DIRS = ('src/hermes_school', 'tests', 'scripts', 'config', 'deploy', 'docs')
SECRET_SUFFIXES = ('.key', '.enc', '.sqlite', '.sqlite3', '.db', '.pyc')


def source_files(root):
    candidates = [root / name for name in TOP_FILES]
    for directory in SOURCE_DIRS:
        candidates.extend((root / directory).rglob('*'))
    result = []
    for path in candidates:
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if path.is_symlink() or any(p.is_symlink() for p in path.parents if p != root and root in p.parents):
            raise ValueError('Symbolic links are not allowed in a deployment archive')
        if '__pycache__' in relative.parts or any(p.endswith('.egg-info') for p in relative.parts):
            continue
        if path.name.startswith('.env') or path.name.startswith('credentials.') or path.name.endswith(SECRET_SUFFIXES):
            continue
        if '.sqlite-' in path.name or '.sqlite3-' in path.name:
            continue
        result.append(path)
    return sorted(set(result))


def package(root=ROOT):
    destination = root / 'dist'
    destination.mkdir(exist_ok=True)
    archive = destination / 'hermes-school-deploy.tar.gz'
    files = source_files(root)
    with tarfile.open(archive, 'w:gz', format=tarfile.PAX_FORMAT) as output:
        for path in files:
            info = output.gettarinfo(str(path), arcname=path.relative_to(root).as_posix())
            info.uid = info.gid = 0
            info.uname = info.gname = ''
            info.mode = 0o644
            with path.open('rb') as content:
                output.addfile(info, content)
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_name(archive.name + '.sha256').write_text(f'{digest}  {archive.name}\n', encoding='ascii')
    print(f'Archive: {archive}\nFiles: {len(files)}\nSHA-256: {digest}\nRuntime data, credentials and keys excluded.')
    return archive


if __name__ == '__main__':
    package()
