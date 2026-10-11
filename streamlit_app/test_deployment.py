"""Offline deployment contracts; no server, browser, or storage access required."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]


def artifact(slug):
    with (ROOT / "artifacts" / slug / ".replit-artifact" / "artifact.toml").open("rb") as source:
        return tomllib.load(source)


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.web = artifact("navratri")
        self.service = next(s for s in self.web["services"] if s["name"] == "web")

    def test_streamlit_is_a_production_root_web_service(self):
        self.assertEqual(self.web["kind"], "web", "Streamlit must be publishable, not API-only")
        self.assertEqual(self.web["previewPath"], "/")
        self.assertEqual(self.service["paths"], ["/"])
        self.assertEqual(self.service["localPort"], 8080)
        self.assertEqual(self.service["env"]["PORT"], "8080")
        self.assertEqual(self.service["env"]["BASE_PATH"], "/")
        self.assertEqual(self.service["production"]["run"]["env"]["PORT"], "8080")
        self.assertEqual(
            self.service["production"]["health"]["startup"]["path"],
            "/_stcore/health",
        )

    def test_api_stays_on_its_own_route_and_port(self):
        api = artifact("api-server")
        self.assertEqual(api["kind"], "api")
        self.assertEqual(api["previewPath"], "/api")
        for service in api["services"]:
            with self.subTest(service=service["name"]):
                self.assertEqual(service["paths"], ["/api"])
                self.assertNotEqual(service["localPort"], 8080)
                self.assertEqual(service["env"]["PORT"], str(service["localPort"]))
                self.assertEqual(
                    service["production"]["run"]["env"]["PORT"],
                    str(service["localPort"]),
                )

    def test_run_button_opens_the_managed_web_service(self):
        with (ROOT / ".replit").open("rb") as source:
            config = tomllib.load(source)
        self.assertEqual(
            config["workflows"]["runButton"], "artifacts/navratri: web",
            "Validation registration must not replace the app's Run button",
        )

    def test_production_build_command_is_runnable(self):
        result = subprocess.run(
            self.service["production"]["build"]["args"],
            cwd=ROOT, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def smoke_launch(self, command, *, outside_root=False, python_status=0, sync_status=0):
        """Run the real launch chain, replacing only Python and asset syncing.

        pnpm still uses real Node, so production package/script resolution is
        exercised. The fake processes record only launch arguments and selected
        non-secret environment values. No video downloads or sockets are opened.
        """
        node = shutil.which("node")
        self.assertIsNotNone(node, "Node must be installed for the production pnpm command")
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            capture = temporary / "calls.jsonl"
            fake = f"""#!{sys.executable}
import json, os, sys
from pathlib import Path
tool = Path(sys.argv[0]).name
if tool == "node" and sys.argv[1:] != ["scripts/sync-dance-guides.mjs"]:
    os.execv({node!r}, [{node!r}, *sys.argv[1:]])
with open(os.environ["LAUNCH_CAPTURE"], "a") as log:
    log.write(json.dumps({{
        "tool": tool, "args": sys.argv[1:], "cwd": os.getcwd(),
        "port": os.environ.get("PORT"),
        "streamlit_port": os.environ.get("STREAMLIT_SERVER_PORT"),
    }}) + "\\n")
sys.exit(int(os.environ["SYNC_STATUS" if tool == "node" else "PYTHON_STATUS"]))
"""
            for tool in ("python", "node"):
                executable = temporary / tool
                executable.write_text(fake)
                executable.chmod(0o755)
            env = {
                **os.environ,
                **self.service["env"],
                **self.service["production"]["run"].get("env", {}),
                "PATH": f"{temporary}{os.pathsep}{os.environ['PATH']}",
                # Hostile inherited ports must not override the launcher contract.
                "PORT": "9999",
                "STREAMLIT_SERVER_PORT": "9998",
                "LAUNCH_CAPTURE": str(capture),
                "PYTHON_STATUS": str(python_status),
                "SYNC_STATUS": str(sync_status),
            }
            result = subprocess.run(
                command, cwd=temporary if outside_root else ROOT,
                env=env, capture_output=True, text=True, timeout=30,
            )
            calls = [json.loads(line) for line in capture.read_text().splitlines()] if capture.exists() else []
            self.assertEqual(
                result.returncode, sync_status or python_status,
                result.stdout + result.stderr,
            )
            return calls

    def assert_streamlit_launch(self, calls):
        self.assertEqual([call["tool"] for call in calls], ["node", "python"])
        self.assertEqual(calls[0]["args"], ["scripts/sync-dance-guides.mjs"])
        launch = calls[1]
        self.assertEqual(launch["cwd"], str(ROOT))
        self.assertEqual(launch["port"], "8080")
        self.assertEqual(launch["streamlit_port"], "8080")
        self.assertEqual(launch["args"], [
            "-m", "streamlit", "run", "streamlit_app/app.py",
            "--server.port", "8080", "--server.address", "0.0.0.0",
        ])
        self.assertTrue((ROOT / launch["args"][3]).is_file(), "Streamlit entry point is missing")

    def test_production_command_actually_reaches_streamlit(self):
        # Read production args from TOML, not the dev workflow or a copied command.
        self.assert_streamlit_launch(
            self.smoke_launch(self.service["production"]["run"]["args"])
        )

    def test_launcher_works_outside_project_and_propagates_failure(self):
        for status in (0, 17):
            with self.subTest(exit_status=status):
                self.assert_streamlit_launch(self.smoke_launch(
                    ["bash", str(ROOT / "scripts/start-streamlit.sh")],
                    outside_root=True, python_status=status,
                ))

    def test_failed_asset_sync_stops_production_launch(self):
        calls = self.smoke_launch(
            self.service["production"]["run"]["args"], sync_status=19,
        )
        self.assertEqual([call["tool"] for call in calls], ["node"])


if __name__ == "__main__":
    unittest.main()
