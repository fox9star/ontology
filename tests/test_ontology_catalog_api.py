"""Creation through the local API yields a persisted, selectable ontology."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import app as studio


class CatalogAPITests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for change in (patch.object(studio, 'BASE_DIR', str(self.root)),
                       patch.object(studio, 'ONTOLOGIES', {}),
                       patch.dict(studio.app.config, {'TESTING': True, 'ONTOLOGY_LOCAL_DOCKER': '0',
                                                     'ONTOLOGY_AUDIT_LOG_PATH': str(self.root / 'audit.jsonl')})):
            change.start()
            self.addCleanup(change.stop)
        self.client = studio.app.test_client()
        self.payload = {'id': 'film-plan', 'name': '영화 기획', 'description': '영화 제작 기획과 자산을 정리합니다.'}

    def test_created_profile_is_selectable_and_survives_catalog_reload(self):
        response = self.client.post('/api/v1/ontologies', json=self.payload)
        self.assertEqual(response.status_code, 201, response.get_json())
        self.assertEqual(response.get_json()['key'], 'film-plan')
        studio.ONTOLOGIES.clear()
        profiles = self.client.get('/api/v1/ontologies').get_json()['ontologies']
        self.assertEqual(profiles['film-plan']['name'], '영화 기획')
        self.assertTrue(self.client.get('/api/validate?ont=film-plan').get_json()['conforms'])
        templates = self.client.get('/api/sparql-templates?ont=film-plan').get_json()['film-plan']
        self.assertEqual(len(templates), 1)
        response = self.client.post('/api/sparql', json={'ont': 'film-plan', 'query': templates[0]['query']})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['count'], 1)

    def test_duplicate_and_invalid_requests_preserve_existing_profile(self):
        self.assertEqual(self.client.post('/api/v1/ontologies', json=self.payload).status_code, 201)
        path = self.root / 'custom-ontologies/film-plan/example.ttl'
        before = path.read_bytes()
        self.assertEqual(self.client.post('/api/v1/ontologies', json=self.payload).status_code, 409)
        self.assertEqual(self.client.post('/api/v1/ontologies', json={**self.payload, 'id': '../outside'}).status_code, 400)
        self.assertEqual(self.client.post('/api/v1/ontologies', json=[]).status_code, 400)
        self.assertEqual(path.read_bytes(), before)

    def test_remote_and_cross_origin_creation_are_denied(self):
        remote = self.client.post('/api/v1/ontologies', json=self.payload,
                                  environ_overrides={'REMOTE_ADDR': '203.0.113.20'})
        origin = self.client.post('/api/v1/ontologies', json=self.payload, headers={'Origin': 'https://outside.example'})
        self.assertEqual(remote.status_code, 403)
        self.assertEqual(origin.status_code, 403)
        self.assertFalse((self.root / 'custom-ontologies').exists())


if __name__ == '__main__':
    unittest.main()
