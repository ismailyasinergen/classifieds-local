from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


V315_VERIFIED_POSTGRES_BACKUP_RESTORE_REHEARSAL = (
    "V315_VERIFIED_POSTGRES_BACKUP_RESTORE_REHEARSAL=1"
)

V315_OPERATOR_SEQUENCE = (
    "bash scripts/backup_postgres.sh --confirm",
    'CREATE DATABASE "test_restore_v315" TEMPLATE template0;',
    "--target-db test_restore_v315",
    "--confirm-target test_restore_v315",
    "python manage.py check",
    'DROP DATABASE "test_restore_v315";',
)

V315_SOURCE_SAFETY = (
    "classifieds_db is never a restore target",
    "source_database_modified=false",
    "development_migration_applied=false",
    "mutation_allowed=false",
    "accounts.0016_emailverificationstate_v306",
    "listings.0024_notification_provider_outcomes_v307",
    "listings.0025_notification_delivery_retention_v308",
)

V315_SEMANTIC_EQUIVALENCE = (
    "Table inventories are equal.",
    "Per-table row counts are equal.",
    "Django migration histories are equal.",
    "Sequence values are equal.",
    "Logical column definitions are equal.",
    "CHECK-constraint truth tables are equal.",
    "physical PostgreSQL attnum history",
    "PostgreSQL deparser formatting",
    "restore_semantically_equivalent=true",
)

V315_CLEANUP_AND_SCOPE = (
    "target_active_connections_before=0",
    "target_cleanup_performed=true",
    "target_exists_after=false",
    "backup_deleted=false",
    "Only the recorded test_ target may be dropped.",
    "The source database must still exist before cleanup.",
    "V315 adds no model or migration file.",
    "V315 adds no automatic startup operation.",
    "V315 does not authorize a development or production restore.",
    "V315 does not authorize migration application.",
    "The tracked checkpoint contains no backup artifact.",
    "The tracked checkpoint contains no database credentials.",
)


class VerifiedPostgresBackupRestoreRehearsalV315Tests(
    SimpleTestCase
):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.backend_root = Path(
            settings.BASE_DIR
        )

        cls.test_path = Path(
            __file__
        ).resolve()

        cls.backup_script_path = (
            cls.backend_root
            / "scripts"
            / "create_verified_postgres_backup_v313.sh"
        )

        cls.restore_script_path = (
            cls.backend_root
            / "scripts"
            / "restore_verified_postgres_backup_v314.sh"
        )

        cls.test_source = cls.test_path.read_text(
            encoding="utf-8",
        )

        cls.backup_source = (
            cls.backup_script_path.read_text(
                encoding="utf-8",
            )
        )

        cls.restore_source = (
            cls.restore_script_path.read_text(
                encoding="utf-8",
            )
        )

    def test_marker_and_candidate_test_are_packaged(
        self,
    ):
        self.assertTrue(
            self.test_path.is_file()
        )

        self.assertEqual(
            V315_VERIFIED_POSTGRES_BACKUP_RESTORE_REHEARSAL,
            (
                "V315_VERIFIED_POSTGRES_BACKUP_"
                "RESTORE_REHEARSAL=1"
            ),
        )

        self.assertIn(
            V315_VERIFIED_POSTGRES_BACKUP_RESTORE_REHEARSAL,
            self.test_source,
        )

    def test_existing_backup_and_restore_foundations_remain_canonical(
        self,
    ):
        self.assertTrue(
            self.backup_script_path.is_file()
        )

        self.assertTrue(
            self.restore_script_path.is_file()
        )

        self.assertIn(
            "V313_VERIFIED_POSTGRES_BACKUP_FOUNDATION=1",
            self.backup_source,
        )

        self.assertIn(
            "V314_VERIFIED_POSTGRES_RESTORE_FOUNDATION=1",
            self.restore_source,
        )

        self.assertTrue(
            self.backup_source.startswith(
                "#!/usr/bin/env bash"
            )
        )

        self.assertTrue(
            self.restore_source.startswith(
                "#!/usr/bin/env bash"
            )
        )

    def test_backup_foundation_requires_verified_explicit_creation(
        self,
    ):
        required_fragments = (
            "--confirm",
            "--source-db",
            "pg_dump",
            "backup_gzip_integrity=verified",
            "backup_dump_identity=postgresql_plain_sql",
            "backup_checksum=verified",
            "backup_publish=atomic",
            "backup_restore_performed=false",
            "migration_apply_performed=false",
        )

        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(
                    fragment,
                    self.backup_source,
                )

    def test_restore_foundation_is_disposable_typed_and_transactional(
        self,
    ):
        required_fragments = (
            "--backup",
            "--checksum",
            "--target-db",
            "--confirm-target",
            "--source-db",
            "--single-transaction",
            "restore_target_disposable=verified",
            "restore_target_identity=verified",
            "restore_target_initially_empty=verified",
            "restore_transaction=single",
            "restore_performed=true",
            "migration_apply_performed=false",
        )

        for fragment in required_fragments:
            with self.subTest(fragment=fragment):
                self.assertIn(
                    fragment,
                    self.restore_source,
                )

        forbidden_fragments = (
            "CREATE DATABASE",
            "DROP DATABASE",
            "manage.py migrate",
        )

        for fragment in forbidden_fragments:
            with self.subTest(fragment=fragment):
                self.assertNotIn(
                    fragment,
                    self.restore_source,
                )

    def test_operator_sequence_contract_is_explicit(
        self,
    ):
        self.assertEqual(
            V315_OPERATOR_SEQUENCE,
            (
                "bash scripts/backup_postgres.sh --confirm",
                (
                    'CREATE DATABASE "test_restore_v315" '
                    "TEMPLATE template0;"
                ),
                "--target-db test_restore_v315",
                "--confirm-target test_restore_v315",
                "python manage.py check",
                'DROP DATABASE "test_restore_v315";',
            ),
        )

    def test_source_database_and_pending_migrations_are_protected(
        self,
    ):
        self.assertEqual(
            V315_SOURCE_SAFETY,
            (
                "classifieds_db is never a restore target",
                "source_database_modified=false",
                "development_migration_applied=false",
                "mutation_allowed=false",
                (
                    "accounts."
                    "0016_emailverificationstate_v306"
                ),
                (
                    "listings."
                    "0024_notification_provider_outcomes_v307"
                ),
                (
                    "listings."
                    "0025_notification_delivery_retention_v308"
                ),
            ),
        )

    def test_semantic_restore_equivalence_contract_is_explicit(
        self,
    ):
        self.assertEqual(
            V315_SEMANTIC_EQUIVALENCE,
            (
                "Table inventories are equal.",
                "Per-table row counts are equal.",
                "Django migration histories are equal.",
                "Sequence values are equal.",
                "Logical column definitions are equal.",
                "CHECK-constraint truth tables are equal.",
                "physical PostgreSQL attnum history",
                "PostgreSQL deparser formatting",
                "restore_semantically_equivalent=true",
            ),
        )

    def test_cleanup_and_audit_only_scope_are_explicit(
        self,
    ):
        self.assertEqual(
            V315_CLEANUP_AND_SCOPE,
            (
                "target_active_connections_before=0",
                "target_cleanup_performed=true",
                "target_exists_after=false",
                "backup_deleted=false",
                "Only the recorded test_ target may be dropped.",
                (
                    "The source database must still exist "
                    "before cleanup."
                ),
                "V315 adds no model or migration file.",
                "V315 adds no automatic startup operation.",
                (
                    "V315 does not authorize a development "
                    "or production restore."
                ),
                (
                    "V315 does not authorize migration "
                    "application."
                ),
                (
                    "The tracked checkpoint contains "
                    "no backup artifact."
                ),
                (
                    "The tracked checkpoint contains "
                    "no database credentials."
                ),
            ),
        )
