"""
Unit tests for Natural Language Query & GraphRAG engine.
"""

import unittest
from app import app, load_graph
from nl_query import resolve_sparql, answer_natural_query


class TestNLQuery(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.client.testing = True

    def test_resolve_sparql_mv_tasks(self):
        query, template = resolve_sparql("완료된 작업 목록과 에이전트를 알려줘", "mv")
        self.assertIn("GenerationTask", query)
        self.assertIn("wasAssociatedWith", query)

    def test_resolve_sparql_agent_roles(self):
        query, template = resolve_sparql("등록된 에이전트 목록과 역할을 보여줘", "agent")
        self.assertIn("AutonomousAgent", query)

    def test_resolve_sparql_devops_builds(self):
        query, template = resolve_sparql("파이프라인 빌드 실행 상태를 알려줘", "devops")
        self.assertIn("PipelineRun", query)

    def test_answer_natural_query_execution(self):
        g = load_graph("mv")
        res = answer_natural_query(g, "완료된 작업 목록을 보여줘", "mv")
        self.assertEqual(res["domain"], "mv")
        self.assertGreater(res["count"], 0)
        self.assertIn("작업", res["answer"])
        self.assertGreater(len(res["rows"]), 0)

    def test_api_nl_query_endpoint(self):
        res = self.client.post('/api/v1/nl-query', json={
            "ont": "mv",
            "question": "에셋 파일 목록을 알려줘"
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("answer", data)
        self.assertIn("sparql", data)
        self.assertIn("rows", data)
        self.assertGreater(data["count"], 0)

    def test_api_nl_query_empty_question(self):
        res = self.client.post('/api/v1/nl-query', json={"ont": "mv", "question": ""})
        self.assertEqual(res.status_code, 400)


if __name__ == '__main__':
    unittest.main()
