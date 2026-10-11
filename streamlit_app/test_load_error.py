"""User-visible load failures, independent of CSV validation and routing."""

import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class LoadErrorTests(unittest.TestCase):
    def assert_load_error(self, error):
        # Import main rather than re-executing app.py so the patched loader is
        # the same function used by the real error boundary.
        app = AppTest.from_string("from streamlit_app.app import main\nmain()")
        with (
            patch("streamlit_app.app.load_data", side_effect=error) as loader,
            patch("streamlit.download_button") as download,
        ):
            app.run()

        loader.assert_called_once_with()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(
            [message.value for message in app.error],
            [f"Could not load ticket listings: {error}"],
        )
        for element_type in (
            "date_input",
            "multiselect",
            "text_input",
            "tab",
            "metric",
            "dataframe",
            "plotly_chart",
            "download_button",
        ):
            with self.subTest(element_type=element_type):
                self.assertEqual(len(app.get(element_type)), 0)
        download.assert_not_called()

    def test_missing_ticket_file_shows_helpful_error_and_stops(self):
        self.assert_load_error(
            FileNotFoundError(
                "Could not find navratri_festival_analytics.csv. "
                "Place the CSV in the project root."
            )
        )

    def test_invalid_ticket_file_shows_helpful_error_and_stops(self):
        self.assert_load_error(
            ValueError("The festival CSV is missing required columns: Date")
        )


if __name__ == "__main__":
    unittest.main()
