import hashlib
import io
import json
import tarfile
import unittest
from restore_runtime import check_archive


def fixture(mutation=None):
    files = {}

    def blob(data):
        raw = json.dumps(data).encode() if isinstance(data, dict) else data
        digest = hashlib.sha256(raw).hexdigest()
        files['blobs/sha256/' + digest] = raw
        return dict(digest='sha256:' + digest, size=len(raw))

    config = blob({'architecture': 'amd64', 'os': 'linux'})
    layer = blob(b'synthetic layer bytes')
    manifest = blob({'schemaVersion': 2, 'config': config, 'layers': [layer]})
    root = blob({'schemaVersion': 2, 'manifests': [manifest]})
    accepted = root['digest'].split(':')[1]
    index = {'schemaVersion': 2, 'manifests': [root]}
    declaration = {'Config': 'blobs/sha256/' + config['digest'].split(':')[1], 'RepoTags': None,
                   'Layers': ['blobs/sha256/' + layer['digest'].split(':')[1]]}
    if mutation == 'index-tag':
        root['annotations'] = {'org.opencontainers.image.ref.name': 'existing-live:local'}
    if mutation == 'extra-root':
        index['manifests'].append(config)
    if mutation == 'repositories':
        files['repositories'] = b'{"existing-live":{"local":"unrelated"}}'
    if mutation == 'wrong-layer':
        declaration['Layers'] = [declaration['Config']]
    files['index.json'] = json.dumps(index).encode()
    files['manifest.json'] = json.dumps([declaration]).encode()
    files['oci-layout'] = b'{"imageLayoutVersion":"1.0.0"}'
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode='w') as tar:
        for name, raw in files.items():
            item = tarfile.TarInfo(name)
            item.size = len(raw)
            tar.addfile(item, io.BytesIO(raw))
    out.seek(0)
    return out, accepted


class ImageArchiveTests(unittest.TestCase):
    def test_closed_digest_graph_accepted(self):
        stream, accepted = fixture()
        check_archive(stream, 'image', accepted)

    def test_unbound_loader_metadata_refused(self):
        for mutation in ('index-tag', 'extra-root', 'repositories', 'wrong-layer'):
            with self.subTest(mutation=mutation):
                stream, accepted = fixture(mutation)
                with self.assertRaises(ValueError):
                    check_archive(stream, 'image', accepted)
