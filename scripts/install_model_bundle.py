"""Validate a portable model bundle before installing it in the local cache."""
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath

MODELS = {
    'sentence-transformers--all-MiniLM-L6-v2': ('sentence-transformers/all-MiniLM-L6-v2', '1110a243fdf4706b3f48f1d95db1a4f5529b4d41'),
    'cross-encoder--ms-marco-MiniLM-L6-v2': ('cross-encoder/ms-marco-MiniLM-L6-v2', '233902d25c440f23af6f7d6e94d2946bac0bee0a'),
}

def install(archive_path, cache=None):
    cache = Path(cache or Path(__file__).resolve().parent.parent / '.model_cache').resolve()
    with zipfile.ZipFile(archive_path) as archive:
        if len(archive.infolist()) > 200 or sum(item.file_size for item in archive.infolist()) > 250 * 1024 * 1024:
            raise ValueError('Model bundle exceeds limits')
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate bundle members')
        manifest = json.loads(archive.read('manifest.json'))
        if manifest.get('schema_version') != 1 or set(manifest.get('models', {})) != set(MODELS):
            raise ValueError('Unexpected model bundle manifest')
        validated = []
        for slug, (repo, revision) in MODELS.items():
            model = manifest['models'][slug]
            if (model.get('repo'), model.get('revision'), model.get('license')) != (repo, revision, 'apache-2.0'):
                raise ValueError('Unexpected model identity')
            files = model.get('files', {})
            if 'model.safetensors' not in files:
                raise ValueError('Missing model weights')
            for name, digest in files.items():
                relative = PurePosixPath(name)
                if relative.is_absolute() or any(part in ('..', '.', '') for part in relative.parts) or '\\' in name or ':' in name:
                    raise ValueError('Unsafe model path')
                if not (name.endswith(('.json', '.txt')) or name in ('model.safetensors', 'README.md') or relative.name.startswith('LICENSE')):
                    raise ValueError('Unexpected model file type')
                target = (cache / ('models--' + slug) / 'snapshots' / revision / name).resolve()
                if not target.is_relative_to(cache):
                    raise ValueError('Model path escapes cache')
                data = archive.read(slug + '/' + name)
                if not isinstance(digest, str) or not re.fullmatch('[a-f0-9]{64}', digest) or hashlib.sha256(data).hexdigest() != digest:
                    raise ValueError('Model bundle checksum mismatch')
                validated.append((target, data))
        # No cache writes occur until every member has passed validation.
        for target, data in validated:
            target.parent.mkdir(parents=True, exist_ok=True)
            temporary = target.with_name(target.name + '.bundle.tmp')
            temporary.write_bytes(data)
            temporary.replace(target)
        return len(validated)

if __name__ == '__main__':
    print(f'Installed {install(sys.argv[1])} verified model files')
