"""Offline tests of the opt-in HTTP checker; never contact a deployment."""

import io
import unittest
from unittest.mock import Mock
from urllib.error import HTTPError, URLError

from scripts.check_live_deployment import (
    NoRedirects,
    check_deployment,
    published_origin,
    validate_response,
)


class LiveDeploymentTests(unittest.TestCase):
    def response(self, body, content_type):
        response = Mock(status=200, headers={"Content-Type": content_type})
        response.read.return_value = body
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        return response

    def test_checks_all_three_routes_without_credentials(self):
        opener = Mock()
        opener.open.side_effect = [
            self.response(b"<html><title>Streamlit</title></html>", "text/html"),
            self.response(b"ok", "text/plain"),
            self.response(b'{"status":"ok"}', "application/json"),
        ]
        output = io.StringIO()
        self.assertEqual(check_deployment("https://example.com/", opener=opener, output=output), 0)
        self.assertEqual(
            [call.args[0].full_url for call in opener.open.call_args_list],
            ["https://example.com/", "https://example.com/_stcore/health", "https://example.com/api/healthz"],
        )
        for call in opener.open.call_args_list:
            self.assertNotIn("Authorization", call.args[0].headers)
        self.assertEqual(output.getvalue().count("PASS"), 3)

    def test_redirect_failure_and_network_errors_do_not_skip_other_routes(self):
        opener = Mock()
        opener.open.side_effect = [
            HTTPError("https://example.com/", 307, "private", {}, None),
            URLError("secret-looking error text should not be printed"),
            TimeoutError(),
        ]
        output = io.StringIO()
        self.assertEqual(check_deployment("https://example.com", opener=opener, output=output), 1)
        self.assertEqual(opener.open.call_count, 3)
        self.assertEqual(output.getvalue().count("FAIL"), 3)
        self.assertNotIn("secret-looking", output.getvalue())
        self.assertIsNone(NoRedirects().redirect_request(None, None, 307, "", {}, "https://login.example"))

    def test_access_gate_or_wrong_service_cannot_pass(self):
        for path, content_type, body in (
            ("/", "text/html", b"<title>Log in</title>"),
            ("/_stcore/health", "text/html", b"<title>Streamlit</title>"),
            ("/api/healthz", "text/plain", b"ok"),
            ("/api/healthz", "application/json", b'{"status":"error"}'),
            ("/api/healthz", "application/json", b"not json"),
        ):
            with self.subTest(path=path, body=body), self.assertRaises(ValueError):
                validate_response(path, 200, content_type, body)
        with self.assertRaises(ValueError):
            validate_response("/", 503, "text/html", b"<title>Streamlit</title>")

    def test_refuses_credentials_query_or_non_origin_urls(self):
        for url in (
            "http://example.com", "https://user:password@example.com",
            "https://example.com/?token=secret", "https://example.com/#secret",
            "https://example.com/api", "https:///missing-host",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                published_origin(url)


if __name__ == "__main__":
    unittest.main()
