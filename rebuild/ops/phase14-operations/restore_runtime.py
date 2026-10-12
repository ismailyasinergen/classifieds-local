import hashlib
import io
import json
import os
import re
import sys
import tarfile
from pathlib import Path


def extract_media(stream, root, inventory):
    expected = {row['name']: row for row in inventory}
    if len(expected) != len(inventory) or root.is_symlink() or any(root.iterdir()):
        raise ValueError('media_target_refused')
    seen, total = set(), 0
    with tarfile.open(fileobj=stream, mode='r|') as tar:
        for member in tar:
            name = member.name
            if (not re.fullmatch(r'(originals/[a-f0-9]{32}\.bin|derivatives/[a-f0-9]{32}\.jpg)', name)
                    or not member.isfile() or name not in expected or name in seen
                    or member.size != expected[name]['bytes'] or member.size < 0):
                raise ValueError('media_member_refused')
            total += member.size
            if total > 512 * 1024 * 1024:
                raise ValueError('media_capacity')
            dest = root / name
            dest.parent.mkdir(mode=0o700, exist_ok=True)
            if dest.parent.is_symlink():
                raise ValueError('media_link_refused')
            digest = hashlib.sha256()
            with tar.extractfile(member) as source, dest.open('xb') as output:
                while block := source.read(65536):
                    digest.update(block)
                    output.write(block)
            if digest.hexdigest() != expected[name]['sha256']:
                raise ValueError('media_digest_refused')
            seen.add(name)
    if seen != set(expected):
        raise ValueError('media_incomplete')


def check_archive(stream, kind, accepted='23e5fe716cd2f2e73c189f035eb3df345ca155c1cd31c78bfdbd0c06839a1839'):
    seen, digests, sizes, declarations, documents, headers = set(), {}, {}, None, {}, {}
    with tarfile.open(fileobj=stream, mode='r|') as tar:
        for member in tar:
            name = member.name
            if name in seen or name.startswith('/') or any(p in ('', '.', '..') for p in name.split('/')):
                raise ValueError('archive_path_refused')
            seen.add(name)
            if member.isdir() and kind == 'image':
                continue
            if not member.isfile() or member.size < 0:
                raise ValueError('archive_type_refused')
            if kind == 'source' and (not (name.startswith('rebuild/') or name == '.github/workflows/rebuild-ci.yml')
                    or '\\' in name or ':' in name
                    or (re.search(r'(^|/)\.env($|\.)', name, re.I) and name != 'rebuild/.env.example')):
                raise ValueError('source_member_refused')
            digest, data = hashlib.sha256(), bytearray()
            metadata = kind == 'image' and (name in ('manifest.json', 'index.json', 'oci-layout', 'repositories') or name.endswith('.json') or (name.startswith('blobs/sha256/') and member.size <= 32768))
            with tar.extractfile(member) as source:
                while block := source.read(65536):
                    digest.update(block)
                    if metadata:
                        if len(data) + len(block) > 32 * 1024 * 1024:
                            raise ValueError('image_metadata_capacity')
                        data.extend(block)
            digests[name] = digest.hexdigest()
            sizes[name] = member.size
            if metadata and name.startswith('blobs/sha256/'):
                try:
                    documents[digest.hexdigest()] = json.loads(data)
                except (ValueError, UnicodeError):
                    pass
            if kind == 'image' and name == 'manifest.json':
                declarations = json.loads(data)
            elif metadata and name in ('index.json', 'oci-layout', 'repositories'):
                headers[name] = json.loads(data)
    if kind == 'source':
        materialized = ''.join(digests[name] + '  ' + name + '\n' for name in sorted(digests)).encode()
        if len(digests) != 319 or hashlib.sha256(materialized).hexdigest() != 'f69c9d336c5baec787e2b0113d3ec77fd536c97e1ed0e3769ebb46bfda4bac58':
            raise ValueError('source_manifest_refused')
    else:
        if not declarations or len(declarations) != 1 or declarations[0].get('RepoTags'):
            raise ValueError('image_tags_refused')
        config_hash = digests.get(declarations[0]['Config'])
        index = headers.get('index.json', {})
        roots = index.get('manifests', [])
        if (index.get('schemaVersion') != 2 or len(roots) != 1 or roots[0].get('digest') != 'sha256:' + accepted
                or headers.get('oci-layout') != {'imageLayoutVersion': '1.0.0'} or headers.get('repositories')
                or declarations[0].get('LayerSources')):
            raise ValueError('image_import_metadata_refused')
        for annotations in (index.get('annotations', {}), roots[0].get('annotations', {})):
            for key, value in annotations.items():
                if key not in ('org.opencontainers.image.ref.name', 'io.containerd.image.name') or value not in (accepted, 'sha256:' + accepted, 'moby-dangling@sha256:' + accepted):
                    raise ValueError('image_import_tag_refused')
        allowed = {'manifest.json', 'index.json', 'oci-layout', 'blobs/sha256/' + accepted}
        if 'repositories' in headers:
            allowed.add('repositories')
        if config_hash != accepted:
            # Docker containerd stores the OCI manifest digest as the image ID.
            if digests.get('blobs/sha256/' + accepted) != accepted or accepted not in documents:
                raise ValueError('image_identity_refused')
            def verify_descriptor(descriptor):
                algorithm, digest = descriptor['digest'].split(':')
                member_name = 'blobs/sha256/' + digest
                if algorithm != 'sha256' or digests.get(member_name) != digest or sizes.get(member_name) != descriptor['size']:
                    raise ValueError('image_descriptor_refused')
                allowed.add(member_name)
                return digest

            verify_descriptor(roots[0])
            pending, visited, configs = [accepted], set(), []
            while pending:
                digest = pending.pop()
                if digest in visited or len(visited) >= 16:
                    raise ValueError('image_graph_refused')
                visited.add(digest)
                document = documents[digest]
                if 'manifests' in document:
                    pending.extend(verify_descriptor(item) for item in document['manifests'])
                else:
                    config = verify_descriptor(document['config'])
                    configs.append(config)
                    layer_names = []
                    for layer in document['layers']:
                        layer_names.append('blobs/sha256/' + verify_descriptor(layer))
                    if config == config_hash and declarations[0].get('Layers') != layer_names:
                        raise ValueError('image_layers_refused')
            if configs.count(config_hash) != 1:
                raise ValueError('image_config_refused')
        else:
            raise ValueError('image_oci_root_required')
        if set(digests) != allowed or not (seen - set(digests)).issubset({'blobs', 'blobs/sha256'}):
            raise ValueError('image_unbound_members_refused')


def main():
    os.umask(0o077)
    mode = sys.argv[1]
    if mode == 'missing-key-check':
        if Path('/run/recovery-keys.json').exists():
            raise ValueError('key_already_present')
        import django
        try:
            django.setup()
        except FileNotFoundError as error:
            if error.filename == '/run/recovery-keys.json':
                return
            raise
        raise ValueError('missing_key_not_refused')
    elif mode in ('keys', 'catalog'):
        data = sys.stdin.buffer.read(32 * 1024 * 1024 + 1)
        if len(data) > 32 * 1024 * 1024:
            raise ValueError('metadata_capacity')
        parsed = json.loads(data)
        if mode == 'catalog':
            from deployment import validate_deployment
            from snapshot_catalog import require_phase10_catalog
            validate_deployment(parsed.get('deployment'))
            require_phase10_catalog(parsed)
        if mode == 'keys' and (not isinstance(parsed.get('secretKey'), str) or not parsed['secretKey'] or not isinstance(parsed.get('fallbacks'), list)):
            raise ValueError('keys_refused')
        with open('/run/recovery-' + mode + '.json', 'xb') as output:
            output.write(data)
    elif mode == 'media':
        catalog = json.loads(Path('/run/recovery-catalog.json').read_bytes())
        extract_media(sys.stdin.buffer, Path('/var/lib/classifieds/media'), catalog['media'])
    elif mode in ('source', 'image'):
        check_archive(sys.stdin.buffer, mode)
    else:
        raise ValueError('restore_mode_refused')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        safe = str(error) if isinstance(error, ValueError) and re.fullmatch('[a-z_]+', str(error)) else type(error).__name__
        sys.stderr.write('restore_runtime_failed:' + safe + '\n')
        sys.exit(1)
