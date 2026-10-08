import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app


class DashboardAndTemplateTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()

    def test_every_template_runs_and_returns_rows(self):
        templates = self.client.get('/api/sparql-templates').get_json()
        self.assertEqual(set(templates), set(app.ONTOLOGIES))
        for key, items in templates.items():
            self.assertTrue(items, f'{key} has no templates')
            for item in items:
                with self.subTest(ontology=key, template=item['key']):
                    response = self.client.post('/api/sparql', json={'ont': key, 'project': '', 'query': item['query']})
                    self.assertEqual(response.status_code, 200, response.get_json())
                    self.assertGreaterEqual(response.get_json()['count'], 0)
                    self.assertIsInstance(response.get_json()['results'], list)

    def test_templates_filter_and_unknown_ontology(self):
        data = self.client.get('/api/sparql-templates', query_string={'ont': 'devops'}).get_json()
        self.assertEqual(list(data), ['devops'])
        self.assertEqual(self.client.get('/api/sparql-templates', query_string={'ont': 'nope'}).status_code, 400)

    def test_metrics_shape_and_history(self):
        validation = self.client.get('/api/v1/validate-all').get_json()
        self.assertTrue(validation['overall_conforms'])
        data = self.client.get('/api/v1/metrics').get_json()
        self.assertEqual({d['key'] for d in data['domains']}, set(app.ONTOLOGIES))
        for domain in data['domains']:
            with self.subTest(domain=domain['key']):
                self.assertGreater(domain['triples'], 0)
                self.assertGreater(domain['classes'], 0)
                self.assertGreater(domain['instances'], 0)
                self.assertEqual(domain['shacl'], 'PASS')
        self.assertEqual(data['totals']['triples'], sum(d['triples'] for d in data['domains']))
        self.assertGreaterEqual(len(data['history']), 1)
        self.assertTrue(data['history'][-1]['overall'])

    def test_dashboard_ui_is_wired(self):
        html = self.client.get('/').get_data(as_text=True)
        self.assertIn('dashboard-tab', html)
        self.assertIn('chart.umd.min.js', html)


if __name__ == '__main__':
    unittest.main()
