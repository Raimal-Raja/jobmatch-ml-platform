import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from scripts.install_model_bundle import MODELS, install


class ModelBundleTests(unittest.TestCase):
    def make_bundle(self, path, unsafe=False, corrupt=False):
        manifest = {'schema_version': 1, 'models': {}}
        with zipfile.ZipFile(path, 'w') as archive:
            for slug, (repo, revision) in MODELS.items():
                payload = b'fictional test weight bytes'
                files = {'model.safetensors': hashlib.sha256(payload).hexdigest()}
                archive.writestr(slug + '/model.safetensors', b'corrupt' if corrupt else payload)
                if unsafe:
                    files['../../escape.json'] = hashlib.sha256(b'{}').hexdigest()
                    archive.writestr(slug + '/../../escape.json', b'{}')
                manifest['models'][slug] = {'repo': repo, 'revision': revision, 'license': 'apache-2.0', 'files': files}
            archive.writestr('manifest.json', json.dumps(manifest))

    def test_valid_bundle_installs_and_corruption_writes_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / 'models.zip'
            self.make_bundle(archive)
            self.assertEqual(install(archive, root / 'cache'), 2)
            self.make_bundle(archive, corrupt=True)
            with self.assertRaisesRegex(ValueError, 'checksum'):
                install(archive, root / 'corrupt-cache')
            self.assertFalse((root / 'corrupt-cache').exists())

    def test_traversal_is_rejected_before_cache_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / 'models.zip'
            self.make_bundle(archive, unsafe=True)
            with self.assertRaisesRegex(ValueError, 'Unsafe'):
                install(archive, root / 'cache')
            self.assertFalse((root / 'cache').exists())
