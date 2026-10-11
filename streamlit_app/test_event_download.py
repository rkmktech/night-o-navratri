import io
import unittest
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from streamlit_app.app import DATA_FILE, EMPTY_MESSAGE, PRICE_COLUMN, REQUIRED_COLUMNS


FILTER_COLUMNS = [
    "Location_City",
    "Booking_Platform",
    "Availability_Status",
    "Food_Available",
]


class EventDownloadTests(unittest.TestCase):
    def expected_export(self, source):
        expected = source[REQUIRED_COLUMNS].copy()
        expected["Date"] = pd.to_datetime(expected["Date"]).dt.normalize()
        expected[PRICE_COLUMN] = expected[PRICE_COLUMN].astype(float)
        # Match loading order before applying the ticket table's price/date sort.
        expected = expected.sort_values("Date").reset_index(drop=True)
        return expected.sort_values([PRICE_COLUMN, "Date"]).reset_index(
            drop=True
        ).assign(Date=lambda frame: frame["Date"].dt.strftime("%Y-%m-%d"))

    def assert_matches_table(self, exported, app):
        pd.testing.assert_frame_equal(
            exported,
            app.dataframe[0].value.reset_index(drop=True).assign(
                Date=lambda frame: frame["Date"].dt.strftime("%Y-%m-%d")
            ),
            # A header-only CSV has no values from which to infer column types.
            check_dtype=not exported.empty,
        )

    def run_app(self):
        app = AppTest.from_file(str(DATA_FILE.parent / "streamlit_app" / "app.py"))
        app.run()
        self.assertEqual(len(app.exception), 0)
        return app

    def download(self, app):
        with patch("streamlit.download_button") as button:
            app.run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(button.call_count, 1)
        return button.call_args.kwargs

    def test_all_rows_prices_and_csv_format(self):
        app = self.run_app()
        download = self.download(app)
        exported = pd.read_csv(io.BytesIO(download["data"]))
        source = pd.read_csv(DATA_FILE)
        self.assertEqual(download["mime"], "text/csv")
        self.assertEqual(download["file_name"], "navratri_filtered_tickets.csv")
        self.assertIsInstance(download["data"], bytes)
        self.assertFalse(download["disabled"])
        self.assertEqual(exported.columns.tolist(), REQUIRED_COLUMNS)
        pd.testing.assert_frame_equal(exported, self.expected_export(source))
        self.assert_matches_table(exported, app)

    def test_each_sidebar_filter_limits_export(self):
        source = pd.read_csv(DATA_FILE)
        for index, column in enumerate(FILTER_COLUMNS):
            with self.subTest(column=column):
                app = self.run_app()
                value = source.iloc[0][column]
                expected = source.loc[source[column] == value]
                self.assertGreater(len(expected), 0)
                self.assertLess(len(expected), len(source))
                app.sidebar.multiselect[index].set_value([value])
                exported = pd.read_csv(io.BytesIO(self.download(app)["data"]))
                pd.testing.assert_frame_equal(exported, self.expected_export(expected))
                self.assert_matches_table(exported, app)

    def test_date_range_limits_export_inclusively(self):
        app = self.run_app()
        source = pd.read_csv(DATA_FILE)
        dates = sorted(source["Date"].unique())
        start, end = dates[1], dates[-2]
        expected = source.loc[source["Date"].between(start, end)]
        self.assertGreater(len(expected), 0)
        self.assertLess(len(expected), len(source))
        app.sidebar.date_input[0].set_value(
            (pd.Timestamp(start).date(), pd.Timestamp(end).date())
        )
        exported = pd.read_csv(io.BytesIO(self.download(app)["data"]))
        pd.testing.assert_frame_equal(exported, self.expected_export(expected))
        self.assert_matches_table(exported, app)

    def test_search_alone_limits_export_case_insensitively(self):
        app = self.run_app()
        source = pd.read_csv(DATA_FILE)
        query = source.iloc[0]["Event_Name"].lower()
        expected = source.loc[
            source.astype(str).agg(" ".join, axis=1).str.contains(
                query, case=False, regex=False
            )
        ]
        self.assertGreater(len(expected), 0)
        self.assertLess(len(expected), len(source))
        app.text_input[0].set_value(f"  {query}  ")
        exported = pd.read_csv(io.BytesIO(self.download(app)["data"]))
        pd.testing.assert_frame_equal(exported, self.expected_export(expected))
        self.assert_matches_table(exported, app)

    def test_combined_sidebar_and_search_filters(self):
        app = self.run_app()
        source = pd.read_csv(DATA_FILE)
        row = source.iloc[0]
        event_date = pd.Timestamp(row["Date"]).date()
        app.sidebar.date_input[0].set_value((event_date, event_date))
        for widget, column in zip(
            app.sidebar.multiselect, FILTER_COLUMNS
        ):
            widget.set_value([row[column]])
        # Booking links identify listings even when event names repeat.
        app.text_input[0].set_value(row["Booking_Link_Placeholder"].upper())
        download = self.download(app)
        exported = pd.read_csv(io.BytesIO(download["data"]))
        self.assertEqual(
            exported["Booking_Link_Placeholder"].tolist(),
            [row["Booking_Link_Placeholder"]],
        )
        self.assertEqual(exported["Date"].tolist(), [row["Date"]])
        pd.testing.assert_frame_equal(
            exported, self.expected_export(source.iloc[[0]])
        )
        self.assert_matches_table(exported, app)

    def test_unmatched_literal_search_disables_download(self):
        app = self.run_app()
        app.text_input[0].set_value("[no match")
        download = self.download(app)
        exported = pd.read_csv(io.BytesIO(download["data"]))
        self.assertTrue(download["disabled"])
        self.assertTrue(exported.empty)
        self.assertEqual(exported.columns.tolist(), REQUIRED_COLUMNS)
        self.assert_matches_table(exported, app)
        self.assertIn(
            "No events match your search. Try a different keyword.",
            [message.value for message in app.info],
        )

    def test_empty_sidebar_selection_does_not_export_all_events(self):
        for index, column in enumerate(FILTER_COLUMNS):
            with self.subTest(column=column):
                app = self.run_app()
                app.sidebar.multiselect[index].set_value([])
                with patch("streamlit.download_button") as button:
                    app.run()
                self.assertEqual(len(app.exception), 0)
                button.assert_not_called()
                self.assertEqual(len(app.dataframe), 0)
                self.assertIn(EMPTY_MESSAGE, [message.value for message in app.info])


if __name__ == "__main__":
    unittest.main()
