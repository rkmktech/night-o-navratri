"""Opt-in, unauthenticated smoke check of the published application."""

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


MAX_RESPONSE_BYTES = 1024 * 1024


class NoRedirects(HTTPRedirectHandler):
    """An access gate must fail, not silently turn into a successful login page."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def published_origin(value):
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
    ):
        raise ValueError("Supply a credential-free HTTPS published origin, without a path or query.")
    return value.rstrip("/")


def validate_response(path, status, content_type, body):
    if status != 200:
        raise ValueError(f"HTTP {status}; expected 200 (redirects/access gates are not healthy).")
    if path == "/":
        if "text/html" not in content_type.lower() or b"<title>Streamlit</title>" not in body:
            raise ValueError("Expected the Streamlit HTML shell, not a login or API response.")
    elif path == "/_stcore/health":
        if "text/plain" not in content_type.lower() or body.strip() != b"ok":
            raise ValueError("Expected Streamlit's plain-text 'ok' health response.")
    elif path == "/api/healthz":
        try:
            data = json.loads(body)
        except (ValueError, UnicodeDecodeError):
            raise ValueError("Expected the separately routed API JSON health response.") from None
        if "application/json" not in content_type.lower() or data != {"status": "ok"}:
            raise ValueError("Expected API JSON {'status': 'ok'}, not Streamlit HTML or text.")


def check_deployment(origin, timeout=30, *, opener=None, output=None):
    origin = published_origin(origin)
    opener = opener or build_opener(NoRedirects())
    output = output or sys.stdout
    failures = 0
    for path in ("/", "/_stcore/health", "/api/healthz"):
        try:
            request = Request(origin + path, headers={"User-Agent": "navratri-deployment-smoke/1"})
            with opener.open(request, timeout=timeout) as response:
                body = response.read(MAX_RESPONSE_BYTES + 1)
                if len(body) > MAX_RESPONSE_BYTES:
                    raise ValueError("Response exceeded the smoke check's size limit.")
                validate_response(path, response.status, response.headers.get("Content-Type", ""), body)
            print(f"PASS {path}", file=output)
        except HTTPError as error:
            # Never print bodies, redirect URLs, cookies, or credentials.
            error.close()
            print(f"FAIL {path}: HTTP {error.code}; expected 200. Check deployment visibility/routing.", file=output)
            failures += 1
        except (URLError, TimeoutError, OSError):
            print(f"FAIL {path}: connection failed or timed out.", file=output)
            failures += 1
        except ValueError as error:
            print(f"FAIL {path}: {error}", file=output)
            failures += 1
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Actual published HTTPS origin from deployment metadata.")
    parser.add_argument("--timeout", type=float, default=30, help="Per-request timeout in seconds (default: 30).")
    args = parser.parse_args()
    try:
        origin = published_origin(args.url)
    except ValueError as error:
        parser.error(str(error))
    if not 0 < args.timeout <= 120:
        parser.error("--timeout must be greater than 0 and at most 120 seconds.")
    return check_deployment(origin, args.timeout)


if __name__ == "__main__":
    sys.exit(main())
