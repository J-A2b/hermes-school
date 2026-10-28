import importlib.util
import tarfile
from pathlib import Path


def test_package_excludes_runtime_credentials_and_generated_files(tmp_path):
    script = Path(__file__).resolve().parents[1] / 'scripts' / 'package-deploy.py'
    spec = importlib.util.spec_from_file_location('deployment_package', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    files = {
        'pyproject.toml': 'project',
        'src/hermes_school/cli.py': 'source',
        'src/hermes_school/credentials.enc': 'must not leave',
        'src/hermes_school/session.key': 'must not leave',
        'src/hermes_school/__pycache__/cli.pyc': 'generated',
        'data/reel/credentials.enc': 'must not leave',
        'data/reel/school.sqlite': 'must not leave',
        '.venv/file': 'environment',
        '.git/config': 'git',
    }
    for name, content in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    archive = module.package(tmp_path)
    with tarfile.open(archive) as bundle:
        assert set(bundle.getnames()) == {'pyproject.toml', 'src/hermes_school/cli.py'}
    assert archive.with_name(archive.name + '.sha256').exists()
