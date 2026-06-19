from django.test import SimpleTestCase
from django.urls import resolve, reverse

from accounts import appeal_list_views, appeal_views, evidence_stage_views, extra_evidence_views


class AppealUrlIntegrityTests(SimpleTestCase):
    def test_seller_appeal_routes_resolve_to_expected_views(self):
        list_match = resolve(reverse("accounts:my_moderation_appeals"))
        self.assertEqual(list_match.func, appeal_list_views.my_moderation_appeals)

        detail_match = resolve(reverse("accounts:moderation_appeal_detail", args=[123]))
        self.assertEqual(detail_match.func, appeal_views.moderation_appeal_detail)

        upload_match = resolve(reverse("accounts:moderation_appeal_add_extra_evidence", args=[123]))
        self.assertEqual(upload_match.func, extra_evidence_views.moderation_appeal_add_extra_evidence)

    def test_admin_appeal_evidence_stage_route_resolves_to_expected_view(self):
        stage_match = resolve(
            reverse("accounts:moderation_appeal_attachment_update_stage", args=[123])
        )
        self.assertEqual(
            stage_match.func,
            evidence_stage_views.moderation_appeal_attachment_update_stage,
        )

    def test_important_appeal_urls_have_expected_paths(self):
        self.assertEqual(reverse("accounts:my_moderation_appeals"), "/accounts/appeals/")
        self.assertEqual(reverse("accounts:moderation_appeal_detail", args=[123]), "/accounts/appeals/123/")
        self.assertEqual(
            reverse("accounts:moderation_appeal_add_extra_evidence", args=[123]),
            "/accounts/appeals/123/add-evidence/",
        )
        self.assertEqual(
            reverse("accounts:moderation_appeal_attachment_update_stage", args=[456]),
            "/accounts/trust-safety/appeals/attachments/456/stage/",
        )
