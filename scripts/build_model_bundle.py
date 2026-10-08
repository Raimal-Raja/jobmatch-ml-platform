"""Prepare a portable, attributed bundle of the pinned public models in CI."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen
from huggingface_hub import HfApi, snapshot_download

MODELS = {
    'sentence-transformers--all-MiniLM-L6-v2': ('sentence-transformers/all-MiniLM-L6-v2', '1110a243fdf4706b3f48f1d95db1a4f5529b4d41'),
    'cross-encoder--ms-marco-MiniLM-L6-v2': ('cross-encoder/ms-marco-MiniLM-L6-v2', '233902d25c440f23af6f7d6e94d2946bac0bee0a'),
}

def main():
    root = Path('reports/model-bundle')
    root.mkdir(parents=True, exist_ok=True)
    manifest = {'schema_version': 1, 'models': {}}
    for slug, (repo, revision) in MODELS.items():
        info = HfApi().model_info(repo, revision=revision)
        license_name = info.card_data.get('license') if info.card_data else None
        if license_name != 'apache-2.0':
            raise ValueError('Model card must declare apache-2.0 before bundling')
        directory = root / slug
        snapshot_download(repo, revision=revision, local_dir=directory,
                          allow_patterns=['*.json', '*.txt', 'model.safetensors', 'README.md', 'LICENSE*', '1_Pooling/*.json'])
        files = {}
        for path in directory.rglob('*'):
            if path.is_file() and '.cache' not in path.relative_to(directory).parts:
                files[path.relative_to(directory).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        if 'model.safetensors' not in files:
            raise ValueError('Bundle requires safetensors weights')
        manifest['models'][slug] = {'repo': repo, 'revision': revision, 'license': license_name, 'files': files}
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    (root / 'NOTICE.txt').write_text('Public model files retained from the repositories and exact revisions listed in manifest.json. Both model cards declare Apache-2.0. Original model cards and available license files are included. No resume or profile data is included.\n', encoding='utf-8')
    (root / 'LICENSE.txt').write_bytes(urlopen('https://www.apache.org/licenses/LICENSE-2.0.txt', timeout=30).read())

if __name__ == '__main__':
    main()
