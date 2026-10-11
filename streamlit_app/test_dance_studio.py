import json
import unittest
from unittest.mock import patch

from streamlit_app.dance_studio import DIRECTORY, render_pose_studio, studio_html


class DanceStudioTests(unittest.TestCase):
    def test_configured_model_is_in_component(self):
        config = json.loads((DIRECTORY / "dance_config.json").read_text())
        html = studio_html()
        self.assertIn(config["pose_model_url"], html)
        self.assertNotIn("__MODEL_URL__", html)
        self.assertIn('audio: false', html)
        self.assertIn('start.addEventListener("click"', html)
        self.assertIn('track.stop()', html)
        self.assertIn('model.estimatePose(canvas)', html)
        self.assertIn('model.predict(posenetOutput)', html)
        self.assertIn('@tensorflow/tfjs@1.3.1/', html)

    def test_component_has_room_for_controls_and_scores(self):
        with patch("streamlit_app.dance_studio.st.iframe") as component:
            render_pose_studio()
        self.assertEqual(component.call_args.kwargs, {
            "height": 720, "alt": "Live dance pose feedback and camera controls"
        })
        self.assertIn("not a rating of dance quality", component.call_args.args[0])

    def test_invalid_model_url_fails_explicitly(self):
        with patch("streamlit_app.dance_studio.json.loads", return_value={
            "pose_model_url": "https://example.com/models/model/"
        }):
            with self.assertRaises(ValueError):
                studio_html()


if __name__ == "__main__":
    unittest.main()
