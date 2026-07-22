from __future__ import annotations

import gzip
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

from django.conf import settings
from django.test import SimpleTestCase


V313_VERIFIED_POSTGRES_BACKUP_FOUNDATION = (
    "V313_VERIFIED_POSTGRES_BACKUP_FOUNDATION"
)


class VerifiedPostgresBackupV313Tests(
    SimpleTestCase
):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.script_path = (
            Path(settings.BASE_DIR)
            / "scripts"
            / "create_verified_postgres_backup_v313.sh"
        )

        cls.source = cls.script_path.read_text(
            encoding="utf-8"
        )

    def _repository(
        self,
        directory: str,
    ) -> Path:
        root = Path(directory)

        (root / "backups").mkdir()

        (root / "docker-compose.yml").write_text(
            "services: {}\n",
            encoding="utf-8",
            newline="\n",
        )

        return root

    def _environment(
        self,
        directory: str,
        *,
        mode: str = "success",
    ) -> tuple[dict[str, str], Path]:
        root = Path(directory)
        fake_bin = root / "bin"
        fake_bin.mkdir()

        docker_log = root / "docker.log"

        docker_path = fake_bin / "docker"
        docker_path.write_text(
            """#!/bin/sh
printf '%s\n' "$*" >> "$V313_DOCKER_LOG"

case "$V313_DOCKER_MODE" in
  success)
    printf '%s\n' \
      '--' \
      '-- PostgreSQL database dump' \
      '--' \
      'SELECT 1;'
    exit 0
    ;;
  invalid)
    printf '%s\n' 'not a PostgreSQL dump'
    exit 0
    ;;
  failure)
    printf '%s\n' 'simulated pg_dump failure' >&2
    exit 19
    ;;
  *)
    exit 91
    ;;
esac
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
        environment["V313_DOCKER_LOG"] = str(
            docker_log
        )
        environment["V313_DOCKER_MODE"] = mode

        return environment, docker_log

    def _command(
        self,
    ) -> list[str]:
        return [
            "bash",
            str(self.script_path),
            "--confirm",
            "--source-db",
            "classifieds_db",
            "--db-user",
            "postgres",
            "--timestamp",
            "20260722_001500",
        ]

    def test_marker_and_canonical_script_are_packaged(
        self,
    ):
        self.assertEqual(
            V313_VERIFIED_POSTGRES_BACKUP_FOUNDATION,
            (
                "V313_VERIFIED_POSTGRES_"
                "BACKUP_FOUNDATION"
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
            root = self._repository(
                directory
            )

            environment, docker_log = (
                self._environment(
                    directory
                )
            )

            result = subprocess.run(
                [
                    "bash",
                    str(self.script_path),
                ],
                cwd=root,
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

    def test_unsafe_database_identifier_is_rejected_before_docker(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(
                directory
            )

            environment, docker_log = (
                self._environment(
                    directory
                )
            )

            result = subprocess.run(
                [
                    "bash",
                    str(self.script_path),
                    "--confirm",
                    "--source-db",
                    "unsafe-db",
                    "--timestamp",
                    "20260722_001500",
                ],
                cwd=root,
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

    def test_invalid_timestamp_is_rejected_before_docker(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(
                directory
            )

            environment, docker_log = (
                self._environment(
                    directory
                )
            )

            result = subprocess.run(
                [
                    "bash",
                    str(self.script_path),
                    "--confirm",
                    "--timestamp",
                    "not-a-timestamp",
                ],
                cwd=root,
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
                "timestamp must match YYYYMMDD_HHMMSS",
                result.stderr,
            )

            self.assertFalse(
                docker_log.exists()
            )

    def test_success_creates_verified_backup_and_checksum(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(
                directory
            )

            environment, docker_log = (
                self._environment(
                    directory
                )
            )

            result = subprocess.run(
                self._command(),
                cwd=root,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

            backup = (
                root
                / "backups"
                / "postgres_20260722_001500.sql.gz"
            )

            checksum = Path(
                f"{backup}.sha256"
            )

            self.assertEqual(
                result.returncode,
                0,
                result.stderr,
            )

            self.assertTrue(
                backup.is_file()
            )

            self.assertTrue(
                checksum.is_file()
            )

            self.assertGreater(
                backup.stat().st_size,
                0,
            )

            with gzip.open(
                backup,
                "rb",
            ) as stream:
                content = stream.read()

            self.assertIn(
                b"PostgreSQL database dump",
                content,
            )

            expected_digest = hashlib.sha256(
                backup.read_bytes()
            ).hexdigest()

            self.assertEqual(
                checksum.read_text(
                    encoding="utf-8"
                ),
                (
                    f"{expected_digest}  "
                    f"{backup.name}\n"
                ),
            )

            self.assertIn(
                "backup_publish=atomic",
                result.stdout,
            )

            self.assertIn(
                "backup_checksum=verified",
                result.stdout,
            )

            self.assertIn(
                "compose exec -T db pg_dump",
                docker_log.read_text(
                    encoding="utf-8"
                ),
            )

            self.assertEqual(
                list(
                    (root / "backups").glob(
                        "*.partial.*"
                    )
                ),
                [],
            )

    def test_pg_dump_failure_leaves_no_artifact(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(
                directory
            )

            environment, _docker_log = (
                self._environment(
                    directory,
                    mode="failure",
                )
            )

            result = subprocess.run(
                self._command(),
                cwd=root,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(
                result.returncode,
                0,
            )

            self.assertEqual(
                list(
                    (root / "backups").iterdir()
                ),
                [],
            )

    def test_invalid_dump_identity_leaves_no_artifact(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(
                directory
            )

            environment, _docker_log = (
                self._environment(
                    directory,
                    mode="invalid",
                )
            )

            result = subprocess.run(
                self._command(),
                cwd=root,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(
                result.returncode,
                0,
            )

            self.assertIn(
                "does not identify as a PostgreSQL plain-SQL dump",
                result.stderr,
            )

            self.assertEqual(
                list(
                    (root / "backups").iterdir()
                ),
                [],
            )

    def test_existing_artifact_is_never_overwritten(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(
                directory
            )

            environment, docker_log = (
                self._environment(
                    directory
                )
            )

            backup = (
                root
                / "backups"
                / "postgres_20260722_001500.sql.gz"
            )

            backup.write_bytes(
                b"existing-artifact"
            )

            result = subprocess.run(
                self._command(),
                cwd=root,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(
                result.returncode,
                2,
            )

            self.assertEqual(
                backup.read_bytes(),
                b"existing-artifact",
            )

            self.assertFalse(
                docker_log.exists()
            )

    def test_backup_script_contains_no_restore_or_migration_surface(
        self,
    ):
        required_fragments = (
            "V313_VERIFIED_POSTGRES_BACKUP_FOUNDATION=1",
            "--confirm",
            "pg_dump",
            "--format=plain",
            "gzip -t",
            "hashlib.sha256",
            "backup_publish=atomic",
            "backup_restore_performed=false",
            "migration_apply_performed=false",
        )

        for fragment in required_fragments:
            with self.subTest(
                required_fragment=fragment
            ):
                self.assertIn(
                    fragment,
                    self.source,
                )

        forbidden_fragments = (
            "pg_restore",
            "psql -U",
            "gunzip -c",
            "python manage.py migrate",
            "dropdb",
            "createdb",
            "pg_terminate_backend",
            "WITH (FORCE)",
        )

        for fragment in forbidden_fragments:
            with self.subTest(
                forbidden_fragment=fragment
            ):
                self.assertNotIn(
                    fragment,
                    self.source,
                )
