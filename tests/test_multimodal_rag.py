"""
tests/test_multimodal_rag.py - Tests for Multimodal RAG (Vision + Audio + KG Fusion)
"""

import io
import unittest
from multimodal_rag import (
    extract_image_vector,
    extract_audio_info,
    process_multimodal_query
)
import app


class TestMultimodalRAG(unittest.TestCase):

    def setUp(self):
        self.app = app.app.test_client()

    def test_extract_image_vector_fallback(self):
        # 1x1 transparent PNG bytes
        dummy_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82'
        vec = extract_image_vector(dummy_png, dim=512)
        self.assertEqual(len(vec), 512)
        self.assertTrue(any(v != 0.0 for v in vec))

    def test_extract_audio_info_fallback(self):
        dummy_wav = b'RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00D\xac\x00\x00\x88X\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00'
        transcript, vec = extract_audio_info(dummy_wav)
        self.assertEqual(len(vec), 512)

    def test_process_multimodal_query(self):
        dummy_png = b'fake_image_bytes_for_testing'
        dummy_wav = b'fake_audio_bytes_for_testing'
        question = "영상 샷과 배경음악의 싱크로율이 적합한가요?"

        uris, prompt = process_multimodal_query(question, image_bytes=dummy_png, audio_bytes=dummy_wav, top_k=3)
        self.assertIsInstance(uris, list)
        self.assertGreater(len(uris), 0)
        self.assertIn("System Instructions", prompt)
        self.assertIn("Vision", prompt)
        self.assertIn("Audio", prompt)
        self.assertIn(question, prompt)

    def test_api_v1_nl_query_multimodal_upload(self):
        # Test multipart/form-data POST to /api/v1/nl-query
        data = {
            'question': '뮤직비디오 오프닝 샷의 색보정과 어울리는 음악 트랙은?',
            'image': (io.BytesIO(b'dummy_image_data'), 'test.png'),
            'audio': (io.BytesIO(b'dummy_audio_data'), 'test.wav')
        }
        res = self.app.post(
            '/api/v1/nl-query',
            data=data,
            content_type='multipart/form-data'
        )
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertIn("node_uris", json_data)
        self.assertIn("prompt", json_data)
        self.assertIn("뮤직비디오", json_data["question"])


if __name__ == "__main__":
    unittest.main()
