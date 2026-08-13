from django.test import TestCase, RequestFactory

from .listing_price_drop_period_filter_v280 import (
    get_price_drop_period_label_v280,
    get_price_drop_period_value_v280,
    PRICE_DROP_PERIOD_PARAM_V280,
)


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


class TestPriceDropPeriodValueV280(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_get_price_drop_period_value_valid(self):
        # valid value
        request = self.factory.get("/", {PRICE_DROP_PERIOD_PARAM_V280: "7d"})
        self.assertEqual(get_price_drop_period_value_v280(request), "7d")

        # valid value with spaces
        request = self.factory.get("/", {PRICE_DROP_PERIOD_PARAM_V280: " 24h "})
        self.assertEqual(get_price_drop_period_value_v280(request), "24h")

    def test_get_price_drop_period_value_invalid(self):
        # invalid value
        request = self.factory.get("/", {PRICE_DROP_PERIOD_PARAM_V280: "invalid"})
        self.assertEqual(get_price_drop_period_value_v280(request), "")

        # empty value
        request = self.factory.get("/", {PRICE_DROP_PERIOD_PARAM_V280: ""})
        self.assertEqual(get_price_drop_period_value_v280(request), "")

    def test_get_price_drop_period_value_missing(self):
        # parameter missing entirely
        request = self.factory.get("/")
        self.assertEqual(get_price_drop_period_value_v280(request), "")
