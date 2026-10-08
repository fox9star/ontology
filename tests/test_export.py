"""
Unit tests for Export API (/api/v1/export) and export_all module.
"""

import os
import shutil
import tempfile
import unittest
import rdflib
from app import app
from export_all import export_all, export_domain, FORMAT_SPECS


class TestExportAPI(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_export_turtle(self):
        res = self.client.get('/api/v1/export?ont=mv&format=turtle')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'@prefix', res.data)
        g = rdflib.Graph().parse(data=res.data.decode('utf-8'), format='turtle')
        self.assertGreater(len(g), 0)

    def test_export_jsonld(self):
        res = self.client.get('/api/v1/export?ont=mv&format=jsonld')
        self.assertEqual(res.status_code, 200)
        g = rdflib.Graph().parse(data=res.data.decode('utf-8'), format='json-ld')
        self.assertGreater(len(g), 0)

    def test_export_rdfxml(self):
        res = self.client.get('/api/v1/export?ont=mv&format=xml')
        self.assertEqual(res.status_code, 200)
        g = rdflib.Graph().parse(data=res.data.decode('utf-8'), format='xml')
        self.assertGreater(len(g), 0)

    def test_export_ntriples(self):
        res = self.client.get('/api/v1/export?ont=mv&format=nt')
        self.assertEqual(res.status_code, 200)
        g = rdflib.Graph().parse(data=res.data.decode('utf-8'), format='nt')
        self.assertGreater(len(g), 0)

    def test_export_download_header(self):
        res = self.client.get('/api/v1/export?ont=mv&format=turtle&download=1')
        self.assertEqual(res.status_code, 200)
        self.assertIn('Content-Disposition', res.headers)
        self.assertIn('attachment', res.headers['Content-Disposition'])
        self.assertIn('mv_export.ttl', res.headers['Content-Disposition'])

    def test_export_invalid_format(self):
        res = self.client.get('/api/v1/export?ont=mv&format=invalid_fmt')
        self.assertEqual(res.status_code, 400)
        self.assertIn('지원하지 않는 포맷입니다', res.get_json()['error'])


class TestExportAllModule(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_export_domain(self):
        res = export_domain('devops', self.temp_dir, formats=['ttl', 'jsonld'])
        self.assertEqual(res['domain'], 'devops')
        self.assertGreater(res['triples'], 0)
        self.assertEqual(len(res['files']), 2)
        ttl_path = os.path.join(self.temp_dir, 'devops.ttl')
        self.assertTrue(os.path.exists(ttl_path))
        self.assertGreater(os.path.getsize(ttl_path), 0)

    def test_export_all_domains(self):
        results, elapsed = export_all(output_dir=self.temp_dir, formats=['ttl'])
        self.assertGreaterEqual(len(results), 7)
        self.assertGreater(elapsed, 0)
        for r in results:
            self.assertGreater(r['triples'], 0)
            self.assertEqual(len(r['files']), 1)
            file_info = r['files'][0]
            self.assertTrue(os.path.exists(file_info['path']))


if __name__ == '__main__':
    unittest.main()
