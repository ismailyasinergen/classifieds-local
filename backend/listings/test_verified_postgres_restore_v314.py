from __future__ import annotations

import gzip
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

from django.conf import settings
from django.test import SimpleTestCase


V314_VERIFIED_POSTGRES_RESTORE_FOUNDATION = (
    "V314_VERIFIED_POSTGRES_RESTORE_FOUNDATION"
)


class VerifiedPostgresRestoreV314Tests(
    SimpleTestCase
):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.script_path = (
            Path(settings.BASE_DIR)
            / "scripts"
            / "restore_verified_postgres_backup_v314.sh"
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

    def _backup(
        self,
        root: Path,
    ) -> tuple[Path, Path]:
        backup = (
            root
            / "backups"
            / "postgres_20260722_030000.sql.gz"
        )

        with gzip.open(
            backup,
            "wb",
        ) as stream:
            stream.write(
                b"--\n"
                b"-- PostgreSQL database dump\n"
                b"--\n"
                b"CREATE TABLE restored_example (id integer);\n"
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
printf '%s\n' "$*" >> "$V314_DOCKER_LOG"

arguments="$*"

case "$arguments" in
  *"SELECT count(*) FROM pg_database WHERE datname = 'test_restore_v314';"*)
    if [ "$V314_DOCKER_MODE" = "missing_target" ]; then
      printf '0\n'
    else
      printf '1\n'
    fi
    exit 0
    ;;
  *"SELECT current_database();"*)
    if [ "$V314_DOCKER_MODE" = "wrong_identity" ]; then
      printf 'wrong_database\n'
    else
      printf 'test_restore_v314\n'
    fi
    exit 0
    ;;
  *"SELECT count(*) FROM pg_stat_activity WHERE datname = 'test_restore_v314';"*)
    if [ "$V314_DOCKER_MODE" = "active_connections" ]; then
      printf '2\n'
    else
      printf '0\n'
    fi
    exit 0
    ;;
  *"SELECT count(*) FROM information_schema.tables"*)
    if [ "$V314_DOCKER_MODE" = "nonempty_target" ]; then
      printf '3\n'
    else
      printf '0\n'
    fi
    exit 0
    ;;
  *"--single-transaction"*)
    cat >/dev/null

    if [ "$V314_DOCKER_MODE" = "restore_failure" ]; then
      printf 'simulated restore failure\n' >&2
      exit 23
    fi

    exit 0
    ;;
  *)
    printf 'unexpected docker invocation: %s\n' "$arguments" >&2
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
        environment["V314_DOCKER_LOG"] = str(
            docker_log
        )
        environment["V314_DOCKER_MODE"] = mode

        return environment, docker_log

    def _command(
        self,
        backup: Path,
        checksum: Path,
    ) -> list[str]:
        return [
            "bash",
            str(self.script_path),
            "--backup",
            str(backup),
            "--checksum",
            str(checksum),
            "--target-db",
            "test_restore_v314",
            "--confirm-target",
            "test_restore_v314",
            "--source-db",
            "classifieds_db",
            "--db-user",
            "postgres",
        ]

    def test_marker_and_canonical_script_are_packaged(
        self,
    ):
        self.assertEqual(
            V314_VERIFIED_POSTGRES_RESTORE_FOUNDATION,
            (
                "V314_VERIFIED_POSTGRES_"
                "RESTORE_FOUNDATION"
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

    def test_typed_confirmation_is_required_before_docker(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(
                directory
            )

            backup, checksum = self._backup(
                root
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
                    "--backup",
                    str(backup),
                    "--checksum",
                    str(checksum),
                    "--target-db",
                    "test_restore_v314",
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
                "explicit --confirm-target authorization is required",
                result.stderr,
            )

            self.assertFalse(
                docker_log.exists()
            )

    def test_unsafe_target_identifier_is_rejected_before_docker(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(
                directory
            )

            backup, checksum = self._backup(
                root
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
                    "--backup",
                    str(backup),
                    "--checksum",
                    str(checksum),
                    "--target-db",
                    "test-unsafe",
                    "--confirm-target",
                    "test-unsafe",
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
                "target_db is not a safe PostgreSQL identifier",
                result.stderr,
            )

            self.assertFalse(
                docker_log.exists()
            )

    def test_non_disposable_target_is_rejected_before_docker(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(
                directory
            )

            backup, checksum = self._backup(
                root
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
                    "--backup",
                    str(backup),
                    "--checksum",
                    str(checksum),
                    "--target-db",
                    "classifieds_restore",
                    "--confirm-target",
                    "classifieds_restore",
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
                "target database must begin with test_",
                result.stderr,
            )

            self.assertFalse(
                docker_log.exists()
            )

    def test_backup_outside_repository_is_rejected_before_docker(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(
                directory
            )

            outside = Path(
                directory
            ).parent / "postgres_20260722_030000.sql.gz"

            with gzip.open(
                outside,
                "wb",
            ) as stream:
                stream.write(
                    b"-- PostgreSQL database dump\n"
                )

            digest = hashlib.sha256(
                outside.read_bytes()
            ).hexdigest()

            outside_checksum = Path(
                f"{outside}.sha256"
            )

            outside_checksum.write_text(
                f"{digest}  {outside.name}\n",
                encoding="utf-8",
                newline="\n",
            )

            environment, docker_log = (
                self._environment(
                    directory
                )
            )

            try:
                result = subprocess.run(
                    self._command(
                        outside,
                        outside_checksum,
                    ),
                    cwd=root,
                    env=environment,
                    text=True,
                    capture_output=True,
                    check=False,
                )
            finally:
                outside.unlink(
                    missing_ok=True
                )
                outside_checksum.unlink(
                    missing_ok=True
                )

            self.assertNotEqual(
                result.returncode,
                0,
            )

            self.assertIn(
                "backup must be located inside the repository backups directory",
                result.stderr,
            )

            self.assertFalse(
                docker_log.exists()
            )

    def test_checksum_mismatch_is_rejected_before_docker(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(
                directory
            )

            backup, checksum = self._backup(
                root
            )

            checksum.write_text(
                f"{'0' * 64}  {backup.name}\n",
                encoding="utf-8",
                newline="\n",
            )

            environment, docker_log = (
                self._environment(
                    directory
                )
            )

            result = subprocess.run(
                self._command(
                    backup,
                    checksum,
                ),
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
                "backup SHA-256 checksum does not match",
                result.stderr,
            )

            self.assertFalse(
                docker_log.exists()
            )

    def test_missing_target_is_rejected(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(
                directory
            )

            backup, checksum = self._backup(
                root
            )

            environment, _docker_log = (
                self._environment(
                    directory,
                    mode="missing_target",
                )
            )

            result = subprocess.run(
                self._command(
                    backup,
                    checksum,
                ),
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
                "disposable target database does not exist",
                result.stderr,
            )

    def test_active_connections_are_rejected(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(
                directory
            )

            backup, checksum = self._backup(
                root
            )

            environment, _docker_log = (
                self._environment(
                    directory,
                    mode="active_connections",
                )
            )

            result = subprocess.run(
                self._command(
                    backup,
                    checksum,
                ),
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
                "disposable target has active connections",
                result.stderr,
            )

    def test_nonempty_target_is_rejected(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(
                directory
            )

            backup, checksum = self._backup(
                root
            )

            environment, _docker_log = (
                self._environment(
                    directory,
                    mode="nonempty_target",
                )
            )

            result = subprocess.run(
                self._command(
                    backup,
                    checksum,
                ),
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
                "disposable target is not empty",
                result.stderr,
            )

    def test_success_restores_only_named_disposable_target(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(
                directory
            )

            backup, checksum = self._backup(
                root
            )

            environment, docker_log = (
                self._environment(
                    directory
                )
            )

            result = subprocess.run(
                self._command(
                    backup,
                    checksum,
                ),
                cwd=root,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(
                result.returncode,
                0,
                result.stderr,
            )

            self.assertIn(
                "restore_target_disposable=verified",
                result.stdout,
            )

            self.assertIn(
                "restore_transaction=single",
                result.stdout,
            )

            self.assertIn(
                "source_database_modified=false",
                result.stdout,
            )

            log = docker_log.read_text(
                encoding="utf-8"
            )

            self.assertIn(
                "--single-transaction",
                log,
            )

            self.assertIn(
                "-d test_restore_v314",
                log,
            )

            self.assertNotIn(
                "-d classifieds_db --single-transaction",
                log,
            )

    def test_restore_failure_is_nonzero_and_transactional(
        self,
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = self._repository(
                directory
            )

            backup, checksum = self._backup(
                root
            )

            environment, docker_log = (
                self._environment(
                    directory,
                    mode="restore_failure",
                )
            )

            result = subprocess.run(
                self._command(
                    backup,
                    checksum,
                ),
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
                "--single-transaction",
                docker_log.read_text(
                    encoding="utf-8"
                ),
            )

            self.assertNotIn(
                "restore_performed=true",
                result.stdout,
            )

    def test_restore_script_has_no_database_lifecycle_or_migration_surface(
        self,
    ):
        required_fragments = (
            "V314_VERIFIED_POSTGRES_RESTORE_FOUNDATION=1",
            "--confirm-target",
            "target database must begin with test_",
            "backup_checksum=verified",
            "backup_gzip_integrity=verified",
            "backup_dump_identity=postgresql_plain_sql",
            "pg_stat_activity",
            "information_schema.tables",
            "--single-transaction",
            "source_database_modified=false",
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
            "manage.py migrate",
            "dropdb",
            "createdb",
            "pg_terminate_backend",
            "WITH (FORCE)",
            "ALTER DATABASE",
        )

        for fragment in forbidden_fragments:
            with self.subTest(
                forbidden_fragment=fragment
            ):
                self.assertNotIn(
                    fragment,
                    self.source,
                )
