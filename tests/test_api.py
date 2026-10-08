"""
Unit tests for core API endpoints:
  - /api/graph-data
  - /api/v1/metrics
  - /api/v1/domains
  - /api/sparql
  - /api/explorer
"""

import unittest
from app import app


class TestCoreAPI(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_domains_list(self):
        res = self.client.get('/api/v1/domains')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('domains', data)
        self.assertIn('mv', data['domains'])
        self.assertIn('agent', data['domains'])
        self.assertIn('devops', data['domains'])

    def test_graph_data(self):
        res = self.client.get('/api/graph-data?ont=mv')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('nodes', data)
        self.assertIn('edges', data)
        self.assertGreater(data['count_nodes'], 0)
        self.assertGreater(data['count_edges'], 0)
        # Check node structure for Vis.js Network compatibility
        sample_node = data['nodes'][0]
        self.assertIn('id', sample_node)
        self.assertIn('label', sample_node)
        self.assertIn('group', sample_node)
        self.assertIn('color', sample_node)
        self.assertIn('shape', sample_node)

    def test_metrics(self):
        res = self.client.get('/api/v1/metrics')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('totals', data)
        self.assertIn('domains', data)
        self.assertGreater(data['totals']['triples'], 0)
        self.assertGreater(data['totals']['classes'], 0)

    def test_explorer(self):
        res = self.client.get('/api/explorer?ont=agent')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('classes', data)
        self.assertIn('properties', data)
        self.assertIn('instances', data)
        self.assertGreater(len(data['classes']), 0)
        self.assertGreater(len(data['instances']), 0)

    def test_sparql_query(self):
        query = """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?s ?label WHERE {
            ?s rdfs:label ?label .
        } LIMIT 5
        """
        res = self.client.post('/api/sparql', json={'ont': 'mv', 'query': query})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('vars', data)
        self.assertIn('rows', data)
        self.assertGreater(data['count'], 0)


if __name__ == '__main__':
    unittest.main()
