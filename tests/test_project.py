import re
import unittest
from pathlib import Path

import pyshacl
from rdflib import Graph, Literal, Namespace, XSD
from rdflib.compare import isomorphic

import app


ROOT = Path(app.BASE_DIR)
MV = Namespace('https://example.org/mv#')
AG = Namespace('https://example.org/agent#')


class OntologyTests(unittest.TestCase):
    def validate(self, key, data):
        cfg = app.ONTOLOGIES[key]
        return pyshacl.validate(
            data,
            shacl_graph=Graph().parse(ROOT / cfg['shapes'], format='turtle'),
            ont_graph=Graph().parse(ROOT / cfg['owl'], format='xml'),
            inference='rdfs',
        )

    def example(self, key):
        return Graph().parse(ROOT / app.ONTOLOGIES[key]['example'], format='turtle')

    def test_all_rdf_files_parse(self):
        for path in ROOT.iterdir():
            if path.suffix in ('.ttl', '.owl', '.rdf'):
                with self.subTest(file=path.name):
                    graph = Graph().parse(path, format='turtle' if path.suffix == '.ttl' else 'xml')
                    self.assertGreater(len(graph), 0)

    def test_schema_serializations_match(self):
        for key in ('agent', 'mv'):
            with self.subTest(ontology=key):
                cfg = app.ONTOLOGIES[key]
                source = Graph().parse(ROOT / cfg['schema'], format='turtle')
                exported = Graph().parse(ROOT / cfg['owl'], format='xml')
                self.assertTrue(isomorphic(source, exported))

    def test_examples_conform(self):
        for key in ('agent', 'mv'):
            with self.subTest(ontology=key):
                conforms, _, report = self.validate(key, self.example(key))
                self.assertTrue(conforms, report)

    def test_missing_media_uri_fails(self):
        data = self.example('mv')
        data.remove((MV.audio01, MV.fileUri, None))
        conforms, _, report = self.validate('mv', data)
        self.assertFalse(conforms)
        self.assertIn('MinCountConstraintComponent', report)

    def test_literal_file_uri_fails(self):
        data = self.example('mv')
        data.set((MV.audio01, MV.fileUri, Literal('https://example.org/audio.wav', datatype=XSD.anyURI)))
        conforms, _, report = self.validate('mv', data)
        self.assertFalse(conforms)
        self.assertIn('NodeKindConstraintComponent', report)

    def test_invalid_media_numbers_fail(self):
        cases = (
            (MV.brief01, MV.targetDurationSeconds, '0', XSD.decimal),
            (MV.audio01, MV.durationSeconds, '0', XSD.decimal),
            (MV.video01, MV.durationSeconds, '0', XSD.decimal),
            (MV.image01, MV.width, '0', XSD.integer),
            (MV.image01, MV.height, '0', XSD.integer),
            (MV.shot01, MV.orderIndex, '0', XSD.integer),
            (MV.shot01, MV.startSecond, '-0.1', XSD.decimal),
            (MV.shot01, MV.endSecond, '0', XSD.decimal),
        )
        for subject, predicate, value, datatype in cases:
            with self.subTest(subject=str(subject), predicate=str(predicate)):
                data = self.example('mv')
                self.assertIn((subject, predicate, None), data)
                data.set((subject, predicate, Literal(value, datatype=datatype)))
                self.assertFalse(self.validate('mv', data)[0])

    def test_unapproved_final_artifact_fails(self):
        data = self.example('agent')
        data.set((AG.decision01, AG.decision, Literal('rejected')))
        conforms, _, report = self.validate('agent', data)
        self.assertFalse(conforms)
        self.assertIn('SPARQLConstraintComponent', report)

    def test_review_target_mismatch_fails(self):
        data = self.example('agent')
        data.set((AG.decision01, AG.decisionAbout, AG.notesV1))
        self.assertFalse(self.validate('agent', data)[0])


class WebApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()

    def test_index_and_ontology_catalog(self):
        self.assertEqual(self.client.get('/').status_code, 200)
        response = self.client.get('/api/ontologies')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.get_json()), set(app.ONTOLOGIES.keys()))

    def test_ui_assets_are_served_locally(self):
        html = self.client.get('/').get_data(as_text=True)
        assets = re.findall(r'<(?:link|script)\b[^>]*(?:href|src)="([^"]+)"', html)
        self.assertGreaterEqual(len(assets), 3)
        for asset in assets:
            with self.subTest(asset=asset):
                self.assertTrue(asset.startswith('/static/'), asset)
                response = self.client.get(asset)
                try:
                    self.assertEqual(response.status_code, 200)
                    self.assertGreater(len(response.data), 100)
                finally:
                    response.close()

    def test_explorer_lists_only_unique_domain_instances(self):
        for key, cfg in app.ONTOLOGIES.items():
            with self.subTest(ontology=key):
                response = self.client.get('/api/explorer', query_string={'ont': key})
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertGreater(len(data['classes']), 0)
                self.assertGreater(len(data['properties']), 0)
                uris = [row['uri'] for row in data['instances']]
                self.assertTrue(uris)
                self.assertEqual(len(uris), len(set(uris)))
                self.assertTrue(all(uri.startswith(cfg['prefix']) for uri in uris))
                if key == 'academic':
                    self.assertEqual(len(uris), 2)

    def test_validation_api_runs_for_each_configured_domain(self):
        for key in ('agent', 'mv'):
            with self.subTest(ontology=key):
                response = self.client.get('/api/validate', query_string={'ont': key})
                self.assertEqual(response.status_code, 200)
                self.assertIs(response.get_json()['conforms'], True)
        response = self.client.get('/api/validate', query_string={'ont': 'academic'})
        self.assertEqual(response.status_code, 200)
        self.assertIs(response.get_json()['conforms'], True)
        self.assertIs(response.get_json()['supported'], True)

    def test_empty_project_keeps_the_example_selected(self):
        for key in app.ONTOLOGIES:
            with self.subTest(ontology=key):
                response = self.client.get('/api/explorer', query_string={'ont': key, 'project': ''})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json(), self.client.get('/api/explorer', query_string={'ont': key}).get_json())
                validation = self.client.get('/api/validate', query_string={'ont': key, 'project': ''})
                self.assertEqual(validation.status_code, 200)
                self.assertNotIn('error', validation.get_json())
                query = self.client.post('/api/sparql', json={'ont': key, 'project': '', 'query': 'SELECT ?s WHERE { ?s ?p ?o } LIMIT 1'})
                self.assertEqual(query.status_code, 200)

    def test_sparql_finds_subclass_generation_tasks(self):
        query = '''PREFIX mv: <https://example.org/mv#>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT DISTINCT ?task WHERE {
            ?task rdf:type/rdfs:subClassOf* mv:GenerationTask .
        }'''
        response = self.client.post('/api/sparql', json={'ont': 'mv', 'query': query})
        self.assertEqual(response.status_code, 200)
        actual = {row['task'] for row in response.get_json()['rows']}
        expected = {str(s) for s in app.load_graph('mv').subjects(MV.status, None)}
        self.assertTrue(expected)
        self.assertEqual(actual, expected)

    def test_instance_detail_and_query_errors(self):
        response = self.client.get('/api/instance-detail', query_string={'ont': 'mv', 'uri': str(MV.video01)})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['triples'])
        self.assertEqual(self.client.get('/api/instance-detail').status_code, 400)
        self.assertEqual(self.client.post('/api/sparql', json={'query': ''}).status_code, 400)
        self.assertEqual(self.client.post('/api/sparql', json={'query': 'not a query'}).status_code, 400)


if __name__ == '__main__':
    unittest.main()
