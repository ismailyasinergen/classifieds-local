from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile

from django.conf import settings
from django.test import SimpleTestCase


V311_NOTIFICATION_DELIVERY_MIGRATION_ROLLOUT_REHEARSAL = (
    "V311_NOTIFICATION_DELIVERY_MIGRATION_ROLLOUT_REHEARSAL"
)


class NotificationDeliveryMigrationRolloutRehearsalV311Tests(
    SimpleTestCase
):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.script_path = (
            Path(settings.BASE_DIR)
            / "scripts"
            / "rehearse_notification_delivery_migrations_v311.sh"
        )

        cls.source = cls.script_path.read_text(
            encoding="utf-8"
        )

    def _fake_environment(
        self,
        directory: str,
    ) -> tuple[dict[str, str], Path]:
        root = Path(directory)
        fake_bin = root / "bin"
        fake_bin.mkdir()

        docker_log = root / "docker.log"

        docker_path = fake_bin / "docker"
        docker_path.write_text(
            """#!/bin/sh
printf '%s\n' "$*" >> "$V311_DOCKER_LOG"
exit 97
""",
            encoding="utf-8",
            newline="\n",
        )
        docker_path.chmod(0o755)

        environment = os.environ.copy()
        environment["PATH"] = (
            f"{fake_bin}{os.pathsep}"
            f"{environment.get('PATH', '')}"
        )
        environment["V311_DOCKER_LOG"] = str(
            docker_log
        )

        return environment, docker_log

    def test_marker_and_canonical_script_are_packaged(
        self,
    ):
        self.assertEqual(
            V311_NOTIFICATION_DELIVERY_MIGRATION_ROLLOUT_REHEARSAL,
            (
                "V311_NOTIFICATION_DELIVERY_"
                "MIGRATION_ROLLOUT_REHEARSAL"
            ),
        )

        self.assertTrue(
            self.script_path.is_file()
        )

        self.assertTrue(
            self.source.startswith(
                "#!/usr/bin/env bash"
            )
        )

    def test_explicit_confirmation_is_required_before_docker(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            environment, docker_log = (
                self._fake_environment(
                    directory
                )
            )

            result = subprocess.run(
                [
                    "bash",
                    str(self.script_path),
                ],
                cwd=directory,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(
            result.returncode,
            2,
        )

        self.assertIn(
            "explicit --confirm authorization is required",
            result.stderr,
        )

        self.assertFalse(
            docker_log.exists()
        )

    def test_unsafe_clone_name_is_rejected_before_docker(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            environment, docker_log = (
                self._fake_environment(
                    directory
                )
            )

            result = subprocess.run(
                [
                    "bash",
                    str(self.script_path),
                    "--confirm",
                    "--clone-name",
                    "unsafe-clone",
                ],
                cwd=directory,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(
            result.returncode,
            2,
        )

        self.assertIn(
            "clone name must match test_[a-z0-9_]+",
            result.stderr,
        )

        self.assertFalse(
            docker_log.exists()
        )

    def test_source_and_clone_names_must_differ(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            environment, docker_log = (
                self._fake_environment(
                    directory
                )
            )

            result = subprocess.run(
                [
                    "bash",
                    str(self.script_path),
                    "--confirm",
                    "--source-db",
                    "test_same_database",
                    "--clone-name",
                    "test_same_database",
                ],
                cwd=directory,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(
            result.returncode,
            2,
        )

        self.assertIn(
            "source and clone database names must differ",
            result.stderr,
        )

        self.assertFalse(
            docker_log.exists()
        )

    def test_rehearsal_encodes_exact_migration_contract(
        self,
    ):
        required_fragments = (
            "accounts.0016_emailverificationstate_v306",
            "listings.0024_notification_provider_outcomes_v307",
            "listings.0025_notification_delivery_retention_v308",
            'result.get("status") != "ready_to_apply"',
            'result.get("status") != "already_applied"',
            "pending_target_count",
            "applied_target_count",
            "target_table_count",
            "target_column_count",
            "target_index_count",
            "target_constraint_count",
        )

        for fragment in required_fragments:
            with self.subTest(
                fragment=fragment
            ):
                self.assertIn(
                    fragment,
                    self.source,
                )

    def test_rehearsal_is_fail_closed_without_force_disconnect(
        self,
    ):
        required_fragments = (
            "source_active_connections",
            "source database has active connections",
            "disposable clone has active connections",
            "No session was terminated.",
            "No forced database drop was attempted.",
            "trap cleanup_clone EXIT",
            "createdb",
            '--template "$SOURCE_DB"',
            "dropdb",
        )

        for fragment in required_fragments:
            with self.subTest(
                fragment=fragment
            ):
                self.assertIn(
                    fragment,
                    self.source,
                )

        forbidden_fragments = (
            "pg_terminate_backend",
            "WITH (FORCE)",
            "--force",
            "dropdb --force",
        )

        for fragment in forbidden_fragments:
            with self.subTest(
                forbidden_fragment=fragment
            ):
                self.assertNotIn(
                    fragment,
                    self.source,
                )

    def test_only_disposable_clone_receives_migration_apply(
        self,
    ):
        apply_fragment = (
            'docker compose exec -T \\\n'
            '  -e DB_NAME="$clone_name" \\\n'
            '  -e PYTHONDONTWRITEBYTECODE=1 \\\n'
            '  web \\\n'
            '  python manage.py migrate \\\n'
            '  --noinput'
        )

        self.assertEqual(
            self.source.count(
                apply_fragment
            ),
            1,
        )

        self.assertNotIn(
            '-e DB_NAME="$source_db" \\\n'
            '    -e PYTHONDONTWRITEBYTECODE=1 \\\n'
            '    web \\\n'
            '    python manage.py migrate \\\n'
            '    --noinput',
            self.source,
        )
