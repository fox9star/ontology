import json
from pathlib import Path
import shutil
import struct
import tempfile
import unittest
from unittest.mock import patch
import wave
import zlib

from rdflib import Graph, Literal, Namespace, XSD

import app
import import_media
import project_store


MV = Namespace('https://example.org/mv#')
PROV = Namespace('http://www.w3.org/ns/prov#')


def tiny_png():
    def chunk(name, data):
        body = name + data
        return struct.pack('>I', len(data)) + body + struct.pack('>I', zlib.crc32(body) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(b'\x00\x00\x00\xff'))
            + chunk(b'IEND', b''))


@unittest.skipUnless(shutil.which('ffprobe'), 'ffprobe is required to test real media imports')
class RegisteredMediaTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(prefix='ontology-media-test-')
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.source = self.root / 'source with spaces'
        self.source.mkdir()
        with wave.open(str(self.source / 'track.wav'), 'wb') as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(8000)
            audio.writeframes(b'\x00\x00' * 8000)
        for filename in ('one.png', 'two.png'):
            (self.source / filename).write_bytes(tiny_png())
        self.plan = {'id': 'fixture', 'name': 'Local fixture', 'source_directory': str(self.source),
                     'audio': 'track.wav', 'images': ['one.png', 'two.png'],
                     'provenance_note': 'Original generation model and prompt are unknown.'}
        self.projects_root = self.root / 'projects'
        self.result = import_media.import_project(self.plan, self.projects_root)
        self.project = self.projects_root / 'fixture'
        self.store_patch = patch.object(project_store, 'PROJECTS_DIR', self.projects_root)
        self.store_patch.start()
        self.addCleanup(self.store_patch.stop)
        self.client = app.app.test_client()

    def validate(self):
        return self.client.get('/api/validate', query_string={'ont': 'mv', 'project': 'fixture'})

    def test_import_measures_files_and_preserves_originals(self):
        manifest = project_store.load_manifest('fixture')
        self.assertEqual(len(manifest['assets']), 3)
        self.assertEqual(manifest['assets'][0]['duration_seconds'], '1.000000')
        for asset in manifest['assets']:
            source = Path(asset['source_file'])
            copied = self.project / 'assets' / asset['file_name']
            self.assertEqual(import_media.file_sha256(source), import_media.file_sha256(copied))
            if asset['kind'] == 'image':
                self.assertEqual((asset['width'], asset['height']), (1, 1))
        first, second = manifest['timeline']
        self.assertEqual(first['end_second'], second['start_second'])
        self.assertEqual(second['end_second'], manifest['duration_seconds'])
        graph = Graph().parse(self.project / 'data.ttl', format='turtle')
        self.assertEqual(str(graph.value(MV.audio01, PROV.wasDerivedFrom)), (self.source / 'track.wav').as_uri())
        self.assertNotIn('video01', {str(s).split('#')[-1] for s in graph.subjects()})

    def test_project_list_detail_and_media_range(self):
        catalog = self.client.get('/api/projects?ont=mv').get_json()
        self.assertEqual(catalog['default_project'], 'fixture')
        detail = self.client.get('/api/project-detail?project=fixture').get_json()
        self.assertEqual(len(detail['assets']), 3)
        audio_url = next(a['preview_url'] for a in detail['assets'] if a['kind'] == 'audio')
        response = self.client.get(audio_url, headers={'Range': 'bytes=0-15'})
        try:
            self.assertEqual(response.status_code, 206)
            self.assertEqual(len(response.data), 16)
            self.assertTrue(response.headers['Content-Type'].startswith('audio/'))
        finally:
            response.close()

    def test_project_graph_queries_are_isolated(self):
        query = 'PREFIX mv: <https://example.org/mv#> SELECT ?audio WHERE { ?audio a mv:AudioAsset }'
        response = self.client.post('/api/sparql', json={'ont': 'mv', 'project': 'fixture', 'query': query})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['count'], 1)
        graph = app.load_graph('mv', 'fixture')
        self.assertEqual(str(graph.value(MV.project01, app.rdflib.RDFS.label)), 'Local fixture')
        self.assertEqual(str(app.load_graph('mv').value(MV.project01, app.rdflib.RDFS.label)), '시티팝 60초 뮤직비디오 프로젝트')
        self.assertEqual(self.client.get('/api/projects?ont=agent').get_json()['projects'], [])

    def test_integrated_validation_accepts_registered_files(self):
        response = self.validate()
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['conforms'])
        self.assertTrue(data['shacl_conforms'])
        self.assertTrue(data['files_conform'])
        self.assertEqual(len(data['file_checks']), 3)
        self.assertTrue(all(row['sha256_matches'] for row in data['file_checks']))

    def test_changed_file_fails_checksum_check(self):
        with (self.project / 'assets' / 'image01.png').open('ab') as output:
            output.write(b'changed')
        data = self.validate().get_json()
        self.assertFalse(data['conforms'])
        self.assertTrue(data['shacl_conforms'])
        self.assertFalse(next(row for row in data['file_checks'] if row['id'] == 'image01')['sha256_matches'])

    def test_missing_file_fails(self):
        (self.project / 'assets' / 'image01.png').rename(self.project / 'assets' / 'image01-moved.png')
        data = self.validate().get_json()
        self.assertFalse(data['conforms'])
        self.assertFalse(next(row for row in data['file_checks'] if row['id'] == 'image01')['exists'])

    def test_rdf_and_manifest_metadata_disagreement_fails(self):
        path = self.project / 'data.ttl'
        graph = Graph().parse(path, format='turtle')
        graph.set((MV.image01, MV.width, Literal(5, datatype=XSD.integer)))
        graph.serialize(destination=str(path), format='turtle')
        data = self.validate().get_json()
        self.assertFalse(data['conforms'])
        self.assertTrue(data['shacl_conforms'])

    def test_omitted_manifest_asset_cannot_bypass_file_checks(self):
        path = self.project / 'manifest.json'
        manifest = json.loads(path.read_text(encoding='utf-8'))
        manifest['assets'] = [a for a in manifest['assets'] if a['id'] != 'image01']
        path.write_text(json.dumps(manifest), encoding='utf-8')
        response = self.validate()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.get_json()['conforms'])

    def test_project_and_media_access_errors(self):
        self.assertEqual(self.client.get('/api/explorer?ont=agent&project=fixture').status_code, 400)
        self.assertEqual(self.client.get('/api/project-detail?project=missing').status_code, 404)
        self.assertEqual(self.client.get('/api/project-detail?project=../escape').status_code, 400)
        self.assertEqual(self.client.get('/media/fixture/unregistered.png').status_code, 404)
        self.assertEqual(self.client.get('/media/fixture/../project.json').status_code, 400)
        self.assertEqual(self.client.post('/api/add-shot', json={'project': 'fixture'}).status_code, 400)

    def test_import_never_overwrites_an_existing_project(self):
        before = (self.project / 'data.ttl').read_bytes()
        with self.assertRaises(FileExistsError):
            import_media.import_project(self.plan, self.projects_root)
        self.assertEqual((self.project / 'data.ttl').read_bytes(), before)

    def test_invalid_import_is_not_registered(self):
        plan = {**self.plan, 'id': 'invalid-duration', 'target_duration_seconds': '2'}
        with self.assertRaises(ValueError):
            import_media.import_project(plan, self.projects_root)
        self.assertFalse((self.projects_root / 'invalid-duration').exists())
        (self.root / 'outside.png').write_bytes(tiny_png())
        plan = {**self.plan, 'id': 'escape', 'images': ['../outside.png']}
        with self.assertRaises(ValueError):
            import_media.import_project(plan, self.projects_root)
        self.assertFalse((self.projects_root / 'escape').exists())


if __name__ == '__main__':
    unittest.main()
