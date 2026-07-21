from __future__ import annotations

import gzip
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

from django.conf import settings
from django.test import SimpleTestCase


V312_NOTIFICATION_DELIVERY_ROLLOUT_AUTHORIZATION = (
    "V312_NOTIFICATION_DELIVERY_ROLLOUT_AUTHORIZATION"
)


class NotificationDeliveryRolloutAuthorizationV312Tests(
    SimpleTestCase
):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.script_path = (
            Path(settings.BASE_DIR)
            / "scripts"
            / "check_notification_delivery_rollout_authorization_v312.sh"
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
printf '%s\n' "$*" >> "$V312_DOCKER_LOG"
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
        environment["V312_DOCKER_LOG"] = str(
            docker_log
        )

        return environment, docker_log

    def _minimal_repository(
        self,
        directory: str,
    ) -> Path:
        root = Path(directory)

        (root / "backend").mkdir()
        (root / "backups").mkdir()

        (root / "docker-compose.yml").write_text(
            "services: {}\n",
            encoding="utf-8",
            newline="\n",
        )

        (root / "backend" / "manage.py").write_text(
            "# placeholder\n",
            encoding="utf-8",
            newline="\n",
        )

        return root

    def _write_backup(
        self,
        root: Path,
        *,
        name: str = (
            "postgres_20260721_220000.sql.gz"
        ),
    ) -> tuple[Path, Path]:
        backup = root / "backups" / name

        with gzip.open(
            backup,
            "wb",
        ) as stream:
            stream.write(
                b"--\n"
                b"-- PostgreSQL database dump\n"
                b"--\n"
                b"SELECT 1;\n"
            )

        digest = hashlib.sha256(
            backup.read_bytes()
        ).hexdigest()

        checksum = Path(
            f"{backup}.sha256"
        )

        checksum.write_text(
            f"{digest}  {backup.name}\n",
            encoding="utf-8",
            newline="\n",
        )

        return backup, checksum

    def test_marker_and_canonical_script_are_packaged(
        self,
    ):
        self.assertEqual(
            V312_NOTIFICATION_DELIVERY_ROLLOUT_AUTHORIZATION,
            (
                "V312_NOTIFICATION_DELIVERY_"
                "ROLLOUT_AUTHORIZATION"
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
            "explicit --confirm-check authorization is required",
            result.stderr,
        )

        self.assertFalse(
            docker_log.exists()
        )

    def test_unsafe_source_database_is_rejected_before_docker(
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
                    "--confirm-check",
                    "--backup",
                    "backups/postgres_20260721_220000.sql.gz",
                    "--expected-head",
                    "a" * 40,
                    "--source-db",
                    "unsafe-db",
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
            "source database name is not a safe PostgreSQL identifier",
            result.stderr,
        )

        self.assertFalse(
            docker_log.exists()
        )

    def test_invalid_expected_head_is_rejected_before_docker(
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
                    "--confirm-check",
                    "--backup",
                    "backups/postgres_20260721_220000.sql.gz",
                    "--expected-head",
                    "not-a-commit",
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
            "expected head must be a lowercase 40-character commit SHA",
            result.stderr,
        )

        self.assertFalse(
            docker_log.exists()
        )

    def test_backup_outside_repository_backup_directory_is_rejected(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = self._minimal_repository(
                directory
            )

            environment, docker_log = (
                self._fake_environment(
                    directory
                )
            )

            outside_backup = (
                root / "postgres_20260721_220000.sql.gz"
            )

            with gzip.open(
                outside_backup,
                "wb",
            ) as stream:
                stream.write(
                    b"-- PostgreSQL database dump\n"
                )

            digest = hashlib.sha256(
                outside_backup.read_bytes()
            ).hexdigest()

            outside_checksum = Path(
                f"{outside_backup}.sha256"
            )

            outside_checksum.write_text(
                f"{digest}\n",
                encoding="utf-8",
                newline="\n",
            )

            result = subprocess.run(
                [
                    "bash",
                    str(self.script_path),
                    "--confirm-check",
                    "--backup",
                    str(outside_backup),
                    "--checksum",
                    str(outside_checksum),
                    "--expected-head",
                    "a" * 40,
                ],
                cwd=root,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(
            result.returncode,
            1,
        )

        self.assertIn(
            "backup must be located inside the repository backups directory",
            result.stdout,
        )

        self.assertIn(
            "checksum must be located inside the repository backups directory",
            result.stdout,
        )

        self.assertFalse(
            docker_log.exists()
        )

    def test_missing_checksum_sidecar_is_rejected_before_docker(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = self._minimal_repository(
                directory
            )

            environment, docker_log = (
                self._fake_environment(
                    directory
                )
            )

            backup, checksum = (
                self._write_backup(
                    root
                )
            )

            checksum.unlink()

            result = subprocess.run(
                [
                    "bash",
                    str(self.script_path),
                    "--confirm-check",
                    "--backup",
                    str(backup),
                    "--expected-head",
                    "a" * 40,
                ],
                cwd=root,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

        self.assertEqual(
            result.returncode,
            1,
        )

        self.assertIn(
            "checksum sidecar does not exist",
            result.stdout,
        )

        self.assertFalse(
            docker_log.exists()
        )

    def test_read_only_authorization_contract_is_exact(
        self,
    ):
        required_fragments = (
            "V312_NOTIFICATION_DELIVERY_MIGRATION_ROLLOUT_AUTHORIZATION=1",
            "--confirm-check",
            "--backup",
            "--checksum",
            "--expected-head",
            "--max-age-hours",
            "PostgreSQL database dump",
            "hashlib.sha256",
            "ready_to_apply",
            "pending_target_count",
            "applied_target_count",
            "auth_users_without_email",
            "ready_for_explicit_human_approval",
            "mutation_allowed=false",
            "migration_apply_performed=false",
            "backup_restore_performed=false",
        )

        for fragment in required_fragments:
            with self.subTest(
                fragment=fragment
            ):
                self.assertIn(
                    fragment,
                    self.source,
                )

    def test_authorization_script_contains_no_mutation_surface(
        self,
    ):
        forbidden_fragments = (
            "python manage.py migrate --noinput",
            "python manage.py migrate\n",
            "pg_terminate_backend",
            "WITH (FORCE)",
            "dropdb",
            "createdb",
            "pg_restore",
            "psql -U",
            "gunzip -c",
            "pg_dump",
        )

        for fragment in forbidden_fragments:
            with self.subTest(
                forbidden_fragment=fragment
            ):
                self.assertNotIn(
                    fragment,
                    self.source,
                )
