from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile

from django.conf import settings
from django.test import SimpleTestCase


class UnappliedMigrationDeploymentPreflightV302Tests(
    SimpleTestCase
):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.entrypoint_path = (
            Path(settings.BASE_DIR) / "entrypoint.sh"
        )

    def _write_executable(
        self,
        path: Path,
        content: str,
    ) -> None:
        path.write_text(
            content,
            encoding="utf-8",
        )
        path.chmod(0o755)

    def _run_entrypoint(
        self,
        *,
        auto_migrate: str | None,
        migrate_check_exit: int = 0,
    ) -> tuple[
        subprocess.CompletedProcess[str],
        list[str],
    ]:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake_bin = root / "bin"
            fake_bin.mkdir()
            command_log = root / "commands.log"

            self._write_executable(
                fake_bin / "nc",
                """#!/bin/sh
exit 0
""",
            )

            self._write_executable(
                fake_bin / "python",
                """#!/bin/sh
printf 'python:%s\\n' "$*" >> "$V302_COMMAND_LOG"

if [ "$*" = "manage.py migrate --check --noinput" ]; then
  exit "${V302_MIGRATE_CHECK_EXIT:-0}"
fi

exit 0
""",
            )

            self._write_executable(
                fake_bin / "v302-start-app",
                """#!/bin/sh
printf 'app:%s\\n' "$*" >> "$V302_COMMAND_LOG"
exit 0
""",
            )

            environment = os.environ.copy()
            environment.update(
                {
                    "PATH": (
                        f"{fake_bin}{os.pathsep}"
                        f"{environment.get('PATH', '')}"
                    ),
                    "DB_HOST": "db",
                    "DB_PORT": "5432",
                    "V302_COMMAND_LOG": str(command_log),
                    "V302_MIGRATE_CHECK_EXIT": str(
                        migrate_check_exit
                    ),
                }
            )

            if auto_migrate is None:
                environment.pop(
                    "DJANGO_AUTO_MIGRATE",
                    None,
                )
            else:
                environment[
                    "DJANGO_AUTO_MIGRATE"
                ] = auto_migrate

            result = subprocess.run(
                [
                    "/bin/sh",
                    str(self.entrypoint_path),
                    "v302-start-app",
                    "--served",
                ],
                cwd=settings.BASE_DIR,
                env=environment,
                text=True,
                capture_output=True,
                check=False,
            )

            if command_log.exists():
                commands = command_log.read_text(
                    encoding="utf-8",
                ).splitlines()
            else:
                commands = []

            return result, commands

    def test_entrypoint_default_is_read_only_and_fail_closed(
        self,
    ):
        result, commands = self._run_entrypoint(
            auto_migrate=None,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            commands[0],
            (
                "python:manage.py migrate "
                "--check --noinput"
            ),
        )
        self.assertNotIn(
            "python:manage.py migrate --noinput",
            commands,
        )
        self.assertEqual(
            commands[-1],
            "app:--served",
        )

    def test_local_compose_mode_applies_migrations(
        self,
    ):
        result, commands = self._run_entrypoint(
            auto_migrate="1",
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            commands,
            [
                "python:manage.py migrate --noinput",
                (
                    "python:manage.py "
                    "archive_expired_listings"
                ),
                (
                    "python:manage.py "
                    "expire_featured_listings"
                ),
                "python:manage.py expire_promotions",
                (
                    "python:manage.py collectstatic "
                    "--noinput"
                ),
                "app:--served",
            ],
        )
        self.assertIn(
            "Applying database migrations",
            result.stdout,
        )

    def test_production_mode_checks_without_applying(
        self,
    ):
        result, commands = self._run_entrypoint(
            auto_migrate="0",
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            commands[0],
            (
                "python:manage.py migrate "
                "--check --noinput"
            ),
        )
        self.assertNotIn(
            "python:manage.py migrate --noinput",
            commands,
        )
        self.assertIn(
            "Database migration preflight passed",
            result.stdout,
        )

    def test_pending_migration_blocks_all_startup_work(
        self,
    ):
        result, commands = self._run_entrypoint(
            auto_migrate="false",
            migrate_check_exit=7,
        )

        self.assertEqual(result.returncode, 1)
        self.assertEqual(
            commands,
            [
                (
                    "python:manage.py migrate "
                    "--check --noinput"
                )
            ],
        )
        self.assertIn(
            "unapplied database migrations detected",
            result.stderr,
        )
        self.assertNotIn(
            "Archiving expired listings",
            result.stdout,
        )
        self.assertNotIn(
            "Starting app",
            result.stdout,
        )

    def test_invalid_policy_fails_before_database_work(
        self,
    ):
        result, commands = self._run_entrypoint(
            auto_migrate="sometimes",
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(commands, [])
        self.assertIn(
            "DJANGO_AUTO_MIGRATE must be a boolean",
            result.stderr,
        )

    def test_migration_gate_precedes_dependent_work(
        self,
    ):
        source = self.entrypoint_path.read_text(
            encoding="utf-8",
        )

        migration_gate = source.index(
            "python manage.py migrate --check --noinput"
        )

        for command in (
            "python manage.py archive_expired_listings",
            "python manage.py expire_featured_listings",
            "python manage.py expire_promotions",
            "python manage.py collectstatic --noinput",
            'exec "$@"',
        ):
            with self.subTest(command=command):
                self.assertLess(
                    migration_gate,
                    source.index(command),
                )
