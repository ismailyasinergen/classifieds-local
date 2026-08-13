from django.test import TestCase

from .listing_price_drop_period_filter_v280 import get_price_drop_period_label_v280


class TestPriceDropPeriodLabelV280(TestCase):
    def test_get_price_drop_period_label_v280(self):
        # Valid values
        self.assertEqual(get_price_drop_period_label_v280("24h"), "Last 24 hours")
        self.assertEqual(get_price_drop_period_label_v280("7d"), "Last 7 days")
        self.assertEqual(get_price_drop_period_label_v280("30d"), "Last 30 days")

        # Valid values with whitespace padding
        self.assertEqual(get_price_drop_period_label_v280(" 24h "), "Last 24 hours")
        self.assertEqual(get_price_drop_period_label_v280("7d "), "Last 7 days")

        # Invalid values
        self.assertEqual(get_price_drop_period_label_v280(""), "")
        self.assertEqual(get_price_drop_period_label_v280("invalid"), "")
        self.assertEqual(get_price_drop_period_label_v280("60d"), "")
        self.assertEqual(get_price_drop_period_label_v280(None), "")
