import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

from streamlit_app.app import PRICE_COLUMN, REQUIRED_COLUMNS, load_data


class LoadDataTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "tickets.csv"
        self.listing = {
            "Event_Name": "Test Garba",
            "Location_City": "Ahmedabad",
            "Booking_Platform": "Test Booking",
            PRICE_COLUMN: "12.50",
            "Availability_Status": "Available",
            "Date": "2026-10-11",
            "Event_Time": "19:00",
            "Food_Available": "Yes",
            "Booking_Link_Placeholder": "https://example.com/tickets",
        }

    def write_csv(self, rows, columns=None):
        with self.path.open("w", newline="", encoding="utf-8") as fixture:
            writer = csv.DictWriter(
                fixture,
                fieldnames=REQUIRED_COLUMNS if columns is None else columns,
            )
            writer.writeheader()
            writer.writerows(rows)

    def test_each_required_column_is_checked(self):
        for column in REQUIRED_COLUMNS:
            with self.subTest(column=column):
                columns = [name for name in REQUIRED_COLUMNS if name != column]
                self.write_csv(
                    [{name: self.listing[name] for name in columns}], columns
                )
                with self.assertRaisesRegex(
                    ValueError,
                    f"The festival CSV is missing required columns: {column}",
                ):
                    load_data(self.path)

    def test_missing_columns_are_reported_together(self):
        columns = [name for name in REQUIRED_COLUMNS if name not in ("Date", PRICE_COLUMN)]
        self.write_csv([{name: self.listing[name] for name in columns}], columns)
        with self.assertRaisesRegex(
            ValueError,
            f"missing required columns: {PRICE_COLUMN}, Date",
        ):
            load_data(self.path)

    def test_invalid_dates_produce_clear_errors(self):
        for date, message in (
            ("not-a-date", "not-a-date"),
            ("2026-02-30", "day is out of range for month"),
        ):
            with self.subTest(date=date):
                self.write_csv([self.listing, {**self.listing, "Date": date}])
                with self.assertRaises(ValueError) as error:
                    load_data(self.path)
                self.assertIn(message, str(error.exception))

    def test_missing_values_in_each_column_reject_the_dataset(self):
        for column in REQUIRED_COLUMNS:
            with self.subTest(column=column):
                self.write_csv([self.listing, {**self.listing, column: ""}])
                with self.assertRaisesRegex(
                    ValueError,
                    "The ticket dataset must contain complete event listings",
                ):
                    load_data(self.path)

    def test_header_only_dataset_is_rejected(self):
        self.write_csv([])
        with self.assertRaisesRegex(
            ValueError, "The ticket dataset must contain complete event listings"
        ):
            load_data(self.path)

    def test_negative_and_infinite_prices_are_rejected(self):
        for price in ("-0.01", "-100", "inf", "-inf"):
            with self.subTest(price=price):
                self.write_csv([self.listing, {**self.listing, PRICE_COLUMN: price}])
                with self.assertRaisesRegex(
                    ValueError, "Ticket prices must be finite, non-negative numbers"
                ):
                    load_data(self.path)

    def test_valid_prices_and_dates_are_loaded_normalized_and_sorted(self):
        rows = [
            {**self.listing, PRICE_COLUMN: "12.50", "Date": "2026-10-12 19:30:00"},
            {**self.listing, PRICE_COLUMN: "0", "Date": "2026-10-10 00:00:00"},
            {**self.listing, PRICE_COLUMN: "100", "Date": "2026-10-11 08:15:00"},
        ]
        self.write_csv(rows)
        expected = pd.DataFrame([rows[1], rows[2], rows[0]], columns=REQUIRED_COLUMNS)
        expected["Date"] = pd.to_datetime(expected["Date"]).dt.normalize()
        expected[PRICE_COLUMN] = expected[PRICE_COLUMN].astype(float)

        pd.testing.assert_frame_equal(load_data(self.path), expected)


if __name__ == "__main__":
    unittest.main()
