from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from categories.models import Category
from listings.models import Listing


V322_MARKER = "LISTING_DETAIL_ACCESSIBILITY_V322"


class _AccessibilityStructureParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.heading_levels = []
        self.ids = []
        self.main_count = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)

        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.heading_levels.append(int(tag[1]))

        if attributes.get("id"):
            self.ids.append(attributes["id"])

        if tag == "main":
            self.main_count += 1


class ListingDetailAccessibilityV322Tests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base_dir = Path(settings.BASE_DIR)
        cls.base_template_path = cls.base_dir / "templates" / "base.html"
        cls.detail_template_path = (
            cls.base_dir
            / "listings"
            / "templates"
            / "listings"
            / "listing_detail.html"
        )

    def setUp(self):
        self.seller = get_user_model().objects.create_user(
            username="v322-seller",
            password="StrongPass123!",
        )
        self.category = Category.objects.create(
            name="V322 Accessibility",
            slug="v322-accessibility",
        )
        self.listing = Listing.objects.create(
            title="V322 accessible listing detail",
            description="Accessibility regression fixture.",
            price=Decimal("322.00"),
            location="Berlin",
            category=self.category,
            owner=self.seller,
            status=Listing.Status.APPROVED,
        )
        self.detail_url = reverse(
            "listings:listing_detail",
            kwargs={"pk": self.listing.pk},
        )

    def test_skip_link_targets_focusable_primary_content(self):
        response = self.client.get(self.detail_url)

        self.assertContains(response, V322_MARKER)
        self.assertContains(
            response,
            'class="skip-to-primary-content-v322"',
            count=1,
        )
        self.assertContains(response, 'href="#primary-content"', count=1)
        self.assertContains(
            response,
            'class="content" id="primary-content" tabindex="-1"',
            count=1,
        )

    def test_primary_content_precedes_category_sidebar_in_dom(self):
        base_source = self.base_template_path.read_text(encoding="utf-8")

        self.assertLess(
            base_source.index('<section class="content"'),
            base_source.index('<aside class="sidebar"'),
        )
        self.assertIn("body.listing-detail-page-v321 .content", base_source)
        self.assertIn("body.listing-detail-page-v321 .sidebar", base_source)

    def test_rendered_heading_and_id_structure_is_valid(self):
        response = self.client.get(self.detail_url)
        parser = _AccessibilityStructureParser()
        parser.feed(response.content.decode("utf-8"))

        self.assertEqual(parser.main_count, 1)
        self.assertGreater(len(parser.heading_levels), 1)
        self.assertEqual(parser.heading_levels[0], 1)
        self.assertEqual(len(parser.ids), len(set(parser.ids)))

        for previous, current in zip(
            parser.heading_levels,
            parser.heading_levels[1:],
        ):
            self.assertLessEqual(current - previous, 1)

    def test_lightbox_has_modal_and_keyboard_focus_contract(self):
        source = self.detail_template_path.read_text(encoding="utf-8")

        for fragment in (
            'aria-modal="true"',
            "focusableControls",
            'event.key === "Tab"',
            'event.key === "Escape"',
            "event.shiftKey",
            "closeLightbox();",
            "restoreFocusNode.focus()",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, source)

    def test_focus_visibility_and_reduced_motion_are_packaged(self):
        source = self.detail_template_path.read_text(encoding="utf-8")

        for fragment in (
            "LISTING_DETAIL_ACCESSIBILITY_V322",
            ":focus-visible",
            "@media (prefers-reduced-motion: reduce)",
            "transition-duration: 0.01ms !important;",
            "animation-duration: 0.01ms !important;",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, source)

    def test_status_announcements_use_explicit_status_roles(self):
        response = self.client.get(self.detail_url)

        self.assertContains(
            response,
            'role="status"',
            count=2,
        )
        self.assertContains(response, 'aria-live="polite"', count=2)
        self.assertContains(response, 'aria-atomic="true"', count=2)

    def test_v322_adds_no_database_migration(self):
        matches = []

        for app_name in ("accounts", "listings"):
            matches.extend(
                (self.base_dir / app_name / "migrations").glob("*v322*.py")
            )

        self.assertEqual(matches, [])
