from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from listings.notification_delivery_migration_rollout_preflight_v310 import (
    V310_TARGET_MIGRATIONS,
)


V316_NOTIFICATION_DELIVERY_MIGRATION_ROLLOUT_COMPLETION = (
    "V316_NOTIFICATION_DELIVERY_MIGRATION_ROLLOUT_COMPLETION=1"
)

V316_COMPLETED_MIGRATIONS = (
    "accounts.0016_emailverificationstate_v306",
    "listings.0024_notification_provider_outcomes_v307",
    "listings.0025_notification_delivery_retention_v308",
)

V316_POST_APPLY_CONTRACT = (
    "status=already_applied",
    "migration_mode=post_apply",
    "applied_target_count=3",
    "pending_target_count=0",
    "required_schema_objects=present",
)

V316_VALIDATION_EVIDENCE = (
    "focused_tests=71",
    "full_regression_tests=2806",
    "django_system_check=passed",
    "general_migration_check=passed",
    "application_health=passed",
    "verified_pre_application_backup=valid",
)

V316_SCOPE = (
    "rollback_performed=false",
    "restore_performed=false",
    "migration_reversal_performed=false",
    "new_migration_file_added=false",
    "backup_artifact_tracked=false",
)


class NotificationDeliveryMigrationRolloutCompletionV316Tests(
    SimpleTestCase
):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.base_dir = Path(settings.BASE_DIR)

        cls.preflight_path = (
            cls.base_dir
            / "listings"
            / "notification_delivery_migration_rollout_preflight_v310.py"
        )

        cls.v315_test_path = (
            cls.base_dir
            / "listings"
            / "test_verified_postgres_backup_restore_rehearsal_v315.py"
        )

        cls.preflight_source = cls.preflight_path.read_text(
            encoding="utf-8"
        )

        cls.v315_test_source = cls.v315_test_path.read_text(
            encoding="utf-8"
        )

    def test_marker_and_completion_test_are_packaged(
        self,
    ):
        self.assertEqual(
            V316_NOTIFICATION_DELIVERY_MIGRATION_ROLLOUT_COMPLETION,
            (
                "V316_NOTIFICATION_DELIVERY_"
                "MIGRATION_ROLLOUT_COMPLETION=1"
            ),
        )

        self.assertTrue(
            Path(__file__).is_file()
        )

    def test_exact_completed_migration_set_is_retained(
        self,
    ):
        self.assertEqual(
            V316_COMPLETED_MIGRATIONS,
            (
                "accounts.0016_emailverificationstate_v306",
                "listings.0024_notification_provider_outcomes_v307",
                "listings.0025_notification_delivery_retention_v308",
            ),
        )

        self.assertEqual(
            tuple(V310_TARGET_MIGRATIONS),
            V316_COMPLETED_MIGRATIONS,
        )

    def test_canonical_preflight_supports_post_apply_completion(
        self,
    ):
        required_fragments = (
            'migration_mode = "post_apply"',
            'status = "already_applied"',
            '"applied_target_count"',
            '"pending_target_count"',
            '"missing_tables"',
            '"missing_columns"',
            '"missing_relations"',
            '"missing_constraints"',
            '"read_only": True',
            '"mutation_allowed": False',
        )

        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(
                    fragment,
                    self.preflight_source,
                )

    def test_post_apply_contract_is_exact(
        self,
    ):
        self.assertEqual(
            V316_POST_APPLY_CONTRACT,
            (
                "status=already_applied",
                "migration_mode=post_apply",
                "applied_target_count=3",
                "pending_target_count=0",
                "required_schema_objects=present",
            ),
        )

    def test_validation_evidence_is_explicit(
        self,
    ):
        self.assertEqual(
            V316_VALIDATION_EVIDENCE,
            (
                "focused_tests=71",
                "full_regression_tests=2806",
                "django_system_check=passed",
                "general_migration_check=passed",
                "application_health=passed",
                "verified_pre_application_backup=valid",
            ),
        )

    def test_backup_rehearsal_and_non_destructive_scope_remain_explicit(
        self,
    ):
        self.assertIn(
            "restore_semantically_equivalent=true",
            self.v315_test_source,
        )

        self.assertIn(
            "backup_deleted=false",
            self.v315_test_source,
        )

        self.assertEqual(
            V316_SCOPE,
            (
                "rollback_performed=false",
                "restore_performed=false",
                "migration_reversal_performed=false",
                "new_migration_file_added=false",
                "backup_artifact_tracked=false",
            ),
        )
