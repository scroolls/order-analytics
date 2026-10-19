import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from analysis import load_and_validate, query_metrics, summary, wilson_interval  # noqa: E402
from generate_sample import generate_orders  # noqa: E402


class AnalysisTests(unittest.TestCase):
    def setUp(self) -> None:
        self.orders = generate_orders(250, seed=31)
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "orders.csv"
        self.orders.to_csv(self.path, index=False)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_sample_is_reproducible(self) -> None:
        pd.testing.assert_frame_equal(self.orders, generate_orders(250, seed=31))

    def test_duplicate_order_is_rejected(self) -> None:
        changed = self.orders.copy()
        changed.loc[1, "order_id"] = changed.loc[0, "order_id"]
        changed.to_csv(self.path, index=False)
        with self.assertRaisesRegex(ValueError, "повторяющиеся order_id"):
            load_and_validate(self.path)

    def test_invalid_delivery_date_is_rejected(self) -> None:
        changed = self.orders.copy()
        index = changed.index[changed["status"] != "cancelled"][0]
        changed.loc[index, "delivered_date"] = "2020-01-01"
        changed.to_csv(self.path, index=False)
        with self.assertRaisesRegex(ValueError, "Доставка раньше даты заказа"):
            load_and_validate(self.path)

    def test_sql_totals_match_order_data(self) -> None:
        data = load_and_validate(self.path)
        metrics = query_metrics(data, ROOT / "sql" / "metrics.sql")
        result = summary(data)
        self.assertEqual(int(metrics["monthly"]["orders"].sum()), result["orders"])
        self.assertEqual(int(metrics["monthly"]["returned_orders"].sum()), result["returned_orders"])
        self.assertAlmostEqual(float(metrics["monthly"]["net_revenue"].sum()), result["net_revenue"], places=2)

    def test_confidence_interval_contains_observed_rate(self) -> None:
        low, high = wilson_interval(12, 100)
        self.assertLess(low, 0.12)
        self.assertGreater(high, 0.12)
        self.assertGreaterEqual(low, 0)
        self.assertLessEqual(high, 1)


if __name__ == "__main__":
    unittest.main()
