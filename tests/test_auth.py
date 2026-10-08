"""Exercise the local boundary without depending on unrelated app modules."""

import unittest
from unittest.mock import patch

from flask import Flask, jsonify

import auth


class TestLocalAccess(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            TESTING=True, ONTOLOGY_LOCAL_DOCKER="0", ONTOLOGY_AUDIT_LOG_PATH=""
        )
        self.app.before_request(auth.authorize_request)
        self.writes = []

        @self.app.route("/api/test", methods=["GET", "POST"])
        def operation():
            from flask import request
            if request.method == "POST":
                self.writes.append("written")
            ok, role, identity = auth.get_client_identity()
            return jsonify(authenticated=ok, role=role, identity=identity)

        self.client = self.app.test_client()
        auth._AUDIT_LOGS.clear()

    def test_native_local_owner_needs_no_key(self):
        result = self.client.post("/api/test")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json["role"], "admin")
        self.assertEqual(result.json["identity"], "local_owner")
        self.assertEqual(self.writes, ["written"])
        self.assertEqual(auth.get_audit_logs()[0]["method"], "POST")

    def test_remote_reads_and_writes_are_denied_even_with_old_credentials(self):
        for method in ("GET", "POST"):
            with self.subTest(method=method):
                result = self.client.open("/api/test", method=method,
                    environ_overrides={"REMOTE_ADDR": "192.168.1.25"},
                    headers={"X-API-Key": "admin-key-dev", "Authorization": "Bearer admin-key-dev"})
                self.assertEqual(result.status_code, 403)
                self.assertEqual(result.json["reason"], "remote_client")
        self.assertEqual(self.writes, [])

    def test_proxy_headers_do_not_make_remote_client_local(self):
        result = self.client.post("/api/test", environ_overrides={"REMOTE_ADDR": "203.0.113.9"},
            headers={"X-Forwarded-For": "127.0.0.1", "X-Forwarded-Host": "localhost"})
        self.assertEqual(result.status_code, 403)
        self.assertEqual(self.writes, [])

    def test_foreign_and_rebinding_hosts_rejected(self):
        for host in ("evil.example:5000", "localhost.evil.example:5000", "192.168.1.2:5000"):
            with self.subTest(host=host):
                result = self.client.post("/api/test", headers={"Host": host})
                self.assertEqual(result.status_code, 403)
                self.assertEqual(result.json["reason"], "untrusted_host")
        self.assertEqual(self.writes, [])

    def test_same_origin_browser_allowed(self):
        result = self.client.post("/api/test", base_url="http://127.0.0.1:5000",
            headers={"Origin": "http://127.0.0.1:5000", "Sec-Fetch-Site": "same-origin"})
        self.assertEqual(result.status_code, 200)

    def test_foreign_origins_and_ports_rejected(self):
        for origin in ("https://evil.example", "null", "http://127.0.0.1:8766", "http://localhost:5000"):
            with self.subTest(origin=origin):
                result = self.client.post("/api/test", base_url="http://127.0.0.1:5000", headers={"Origin": origin})
                self.assertEqual(result.status_code, 403)
                self.assertEqual(result.json["reason"], "foreign_origin")
        self.assertEqual(self.writes, [])

    def test_browser_cross_site_without_origin_rejected(self):
        result = self.client.get("/api/test", headers={"Sec-Fetch-Site": "cross-site"})
        self.assertEqual(result.status_code, 403)

    def test_ipv6_and_mapped_loopback_allowed(self):
        for address in ("::1", "::ffff:127.0.0.1"):
            with self.subTest(address=address):
                result = self.client.get("/api/test", base_url="http://[::1]:5000",
                    environ_overrides={"REMOTE_ADDR": address})
                self.assertEqual(result.status_code, 200)

    def test_docker_bridge_requires_explicit_mode_and_subnet(self):
        self.app.config["ONTOLOGY_DOCKER_CLIENT_CIDR"] = "172.30.71.0/24"
        blocked = self.client.get("/api/test", environ_overrides={"REMOTE_ADDR": "172.30.71.1"})
        self.assertEqual(blocked.status_code, 403)
        self.app.config["ONTOLOGY_LOCAL_DOCKER"] = "1"
        accepted = self.client.get("/api/test", environ_overrides={"REMOTE_ADDR": "172.30.71.1"})
        self.assertEqual(accepted.status_code, 200)
        outside = self.client.get("/api/test", environ_overrides={"REMOTE_ADDR": "172.30.72.1"})
        self.assertEqual(outside.status_code, 403)
        rebinding = self.client.get("/api/test", environ_overrides={"REMOTE_ADDR": "172.30.71.1"},
            headers={"Host": "evil.example"})
        self.assertEqual(rebinding.status_code, 403)

    def test_misconfigured_docker_fails_closed(self):
        self.app.config.update(ONTOLOGY_LOCAL_DOCKER="1", ONTOLOGY_DOCKER_CLIENT_CIDR="10.0.0.0/8")
        result = self.client.get("/api/test", environ_overrides={"REMOTE_ADDR": "10.0.0.2"})
        self.assertEqual(result.status_code, 403)
        self.assertEqual(result.json["reason"], "invalid_local_docker_configuration")

    def test_native_bind_rejects_public_interface(self):
        with patch.dict("os.environ", {"ONTOLOGY_LOCAL_DOCKER": "0"}):
            self.assertEqual(auth.validate_bind_host("127.0.0.1"), "127.0.0.1")
            self.assertEqual(auth.validate_bind_host("::1"), "::1")
            with self.assertRaises(ValueError):
                auth.validate_bind_host("0.0.0.0")

    def test_docker_bind_requires_bounded_explicit_bridge(self):
        with patch.dict("os.environ", {"ONTOLOGY_LOCAL_DOCKER": "1", "ONTOLOGY_DOCKER_CLIENT_CIDR": "172.30.71.0/24"}):
            self.assertEqual(auth.validate_bind_host("0.0.0.0"), "0.0.0.0")
        with patch.dict("os.environ", {"ONTOLOGY_LOCAL_DOCKER": "1", "ONTOLOGY_DOCKER_CLIENT_CIDR": ""}):
            with self.assertRaises(ValueError):
                auth.validate_bind_host("0.0.0.0")

    def test_audit_can_be_recorded_without_request_and_zero_limit_is_empty(self):
        with patch.dict("os.environ", {"ONTOLOGY_AUDIT_LOG_PATH": ""}):
            auth.log_audit_action("TEST", "local_owner", "admin", "POST")
            self.assertEqual(auth.get_audit_logs(1)[0]["action"], "TEST")
            self.assertIsNone(auth.get_audit_logs(1)[0]["ip"])
            self.assertEqual(auth.get_audit_logs(0), [])

    def test_studio_registers_boundary_for_real_reads_and_mutations(self):
        from app import app as studio
        client = studio.test_client()
        local = client.get("/api/health")
        self.assertEqual(local.status_code, 200)
        remote = client.get("/api/health", environ_overrides={"REMOTE_ADDR": "192.168.1.25"})
        self.assertEqual(remote.status_code, 403)
        foreign = client.post("/api/v1/codex/jobs", json={"prompt": "must not run"},
            headers={"Origin": "https://evil.example"})
        self.assertEqual(foreign.status_code, 403)
        self.assertEqual(foreign.json["code"], "LOCAL_ACCESS_REQUIRED")


if __name__ == "__main__":
    unittest.main()
