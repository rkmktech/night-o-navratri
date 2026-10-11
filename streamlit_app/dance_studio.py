"""Browser-only pose inference; no camera frames are sent to Streamlit."""

import json
from pathlib import Path
from urllib.parse import urlparse

import streamlit as st


DIRECTORY = Path(__file__).resolve().parent


def studio_html() -> str:
    config = json.loads((DIRECTORY / "dance_config.json").read_text())
    url = config["pose_model_url"]
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "teachablemachine.withgoogle.com"
        or not parsed.path.startswith("/models/")
        or not parsed.path.removeprefix("/models/").strip("/")
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Configure a complete HTTPS Teachable Machine model URL.")
    # JSON encoding prevents configuration from being interpreted as markup.
    model_url = json.dumps(url.rstrip("/") + "/").replace("<", "\\u003c")
    template = (DIRECTORY / "pose_studio.html").read_text()
    return template.replace("__MODEL_URL__", model_url)


def render_pose_studio() -> None:
    st.iframe(studio_html(), height=720, alt="Live dance pose feedback and camera controls")
