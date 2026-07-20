from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.db.backends.postgresql.creation import (
    DatabaseCreation as PostgreSQLDatabaseCreation,
)
from django.test import SimpleTestCase

from config.test_runner import (
    MigrationAwareParallelDiscoverRunner,
    MigrationAwarePostgreSQLTestDatabaseCreation,
)


class MigrationAwareCloneNameTests(SimpleTestCase):
    def test_accepts_exact_prefixed_positive_worker_clone(self):
        result = (
            MigrationAwarePostgreSQLTestDatabaseCreation
            ._validated_clone_names(
                "test_classifieds_db",
                "3",
                "test_classifieds_db_3",
            )
        )

        self.assertEqual(
            result,
            (
                "test_classifieds_db",
                "test_classifieds_db_3",
            ),
        )

    def test_rejects_non_test_source_database(self):
        with self.assertRaises(ImproperlyConfigured):
            (
                MigrationAwarePostgreSQLTestDatabaseCreation
                ._validated_clone_names(
                    "classifieds_db",
                    "1",
                    "classifieds_db_1",
                )
            )

    def test_rejects_unexpected_or_non_numeric_clone(self):
        invalid_values = (
            (
                "test_classifieds_db",
                "worker",
                "test_classifieds_db_worker",
            ),
            (
                "test_classifieds_db",
                "2",
                "test_classifieds_db_7",
            ),
            (
                "test_classifieds_db",
                "0",
                "test_classifieds_db_0",
            ),
        )

        for source, suffix, target in invalid_values:
            with self.subTest(
                source=source,
                suffix=suffix,
                target=target,
            ):
                with self.assertRaises(
                    ImproperlyConfigured
                ):
                    (
                        MigrationAwarePostgreSQLTestDatabaseCreation
                        ._validated_clone_names(
                            source,
                            suffix,
                            target,
                        )
                    )


class MigrationAwareCloneRefreshTests(SimpleTestCase):
    def _creation(self):
        cursor = mock.Mock()

        @contextmanager
        def nodb_cursor():
            yield cursor

        connection = SimpleNamespace(
            settings_dict={
                "NAME": "test_classifieds_db",
            },
            close=mock.Mock(),
            close_pool=mock.Mock(),
        )

        creation = (
            MigrationAwarePostgreSQLTestDatabaseCreation
            .__new__(
                MigrationAwarePostgreSQLTestDatabaseCreation
            )
        )

        creation.connection = connection
        creation.log = mock.Mock()
        creation._nodb_cursor = nodb_cursor
        creation._quote_name = (
            lambda value: f'"{value}"'
        )
        creation._get_database_create_suffix = (
            lambda *, template: (
                f'TEMPLATE "{template}"'
            )
        )
        creation._execute_create_test_db = mock.Mock()

        return creation, connection, cursor

    def test_parallel_keepdb_clone_is_refreshed(self):
        creation, connection, cursor = (
            self._creation()
        )

        creation._clone_test_db(
            suffix="2",
            verbosity=1,
            keepdb=True,
        )

        connection.close.assert_called_once_with()
        connection.close_pool.assert_called_once_with()

        cursor.execute.assert_called_once_with(
            'DROP DATABASE IF EXISTS '
            '"test_classifieds_db_2"'
        )

        creation._execute_create_test_db.assert_called_once_with(
            cursor,
            {
                "dbname": '"test_classifieds_db_2"',
                "suffix": (
                    'TEMPLATE "test_classifieds_db"'
                ),
            },
            keepdb=False,
        )

    def test_non_keepdb_clone_uses_django_default(self):
        creation, _, _ = self._creation()

        with mock.patch.object(
            PostgreSQLDatabaseCreation,
            "_clone_test_db",
            autospec=True,
        ) as default_clone:
            creation._clone_test_db(
                suffix="1",
                verbosity=0,
                keepdb=False,
            )

        default_clone.assert_called_once_with(
            creation,
            "1",
            0,
            keepdb=False,
        )


class MigrationAwareRunnerTests(SimpleTestCase):
    def test_runner_replacement_is_parallel_keepdb_only_and_temporary(
        self,
    ):
        original_creation = object()

        connection = SimpleNamespace(
            vendor="postgresql",
            creation=original_creation,
        )

        observed = {}

        def fake_setup(runner, **kwargs):
            observed["during_setup"] = (
                fake_connections["default"].creation
            )
            return "old-config"

        fake_connections = {
            "default": connection,
        }

        runner = MigrationAwareParallelDiscoverRunner(
            parallel=4,
            keepdb=True,
            interactive=False,
        )

        with (
            mock.patch(
                "config.test_runner.connections",
                fake_connections,
            ),
            mock.patch.object(
                PostgreSQLDatabaseCreation,
                "__init__",
                return_value=None,
            ),
            mock.patch.object(
                MigrationAwareParallelDiscoverRunner.__mro__[1],
                "setup_databases",
                fake_setup,
            ),
        ):
            result = runner.setup_databases(
                aliases={"default": False}
            )

        self.assertEqual(result, "old-config")

        self.assertIsInstance(
            observed["during_setup"],
            MigrationAwarePostgreSQLTestDatabaseCreation,
        )

        self.assertIs(
            connection.creation,
            original_creation,
        )

    def test_runner_bypasses_serial_keepdb(self):
        runner = MigrationAwareParallelDiscoverRunner(
            parallel=1,
            keepdb=True,
            interactive=False,
        )

        base_runner = (
            MigrationAwareParallelDiscoverRunner
            .__mro__[1]
        )

        with mock.patch.object(
            base_runner,
            "setup_databases",
            return_value="serial-config",
        ) as default_setup:
            result = runner.setup_databases(
                aliases={"default": False}
            )

        self.assertEqual(
            result,
            "serial-config",
        )

        default_setup.assert_called_once_with(
            aliases={"default": False}
        )

    def test_runner_bypasses_parallel_without_keepdb(self):
        runner = MigrationAwareParallelDiscoverRunner(
            parallel=4,
            keepdb=False,
            interactive=False,
        )

        base_runner = (
            MigrationAwareParallelDiscoverRunner
            .__mro__[1]
        )

        with mock.patch.object(
            base_runner,
            "setup_databases",
            return_value="non-keepdb-config",
        ) as default_setup:
            result = runner.setup_databases(
                aliases={"default": False}
            )

        self.assertEqual(
            result,
            "non-keepdb-config",
        )

        default_setup.assert_called_once_with(
            aliases={"default": False}
        )

    def test_runner_leaves_non_postgresql_creation_unchanged(
        self,
    ):
        original_creation = object()

        connection = SimpleNamespace(
            vendor="sqlite",
            creation=original_creation,
        )

        fake_connections = {
            "default": connection,
        }

        observed = {}

        def fake_setup(runner, **kwargs):
            observed["during_setup"] = (
                fake_connections["default"].creation
            )
            return "sqlite-config"

        runner = MigrationAwareParallelDiscoverRunner(
            parallel=4,
            keepdb=True,
            interactive=False,
        )

        base_runner = (
            MigrationAwareParallelDiscoverRunner
            .__mro__[1]
        )

        with (
            mock.patch(
                "config.test_runner.connections",
                fake_connections,
            ),
            mock.patch.object(
                base_runner,
                "setup_databases",
                fake_setup,
            ),
        ):
            result = runner.setup_databases(
                aliases={"default": False}
            )

        self.assertEqual(
            result,
            "sqlite-config",
        )

        self.assertIs(
            observed["during_setup"],
            original_creation,
        )

        self.assertIs(
            connection.creation,
            original_creation,
        )

    def test_runner_restores_creation_after_setup_error(
        self,
    ):
        original_creation = object()

        connection = SimpleNamespace(
            vendor="postgresql",
            creation=original_creation,
        )

        fake_connections = {
            "default": connection,
        }

        observed = {}

        def failing_setup(runner, **kwargs):
            observed["during_setup"] = (
                fake_connections["default"].creation
            )
            raise RuntimeError("database setup failed")

        runner = MigrationAwareParallelDiscoverRunner(
            parallel=4,
            keepdb=True,
            interactive=False,
        )

        base_runner = (
            MigrationAwareParallelDiscoverRunner
            .__mro__[1]
        )

        with (
            mock.patch(
                "config.test_runner.connections",
                fake_connections,
            ),
            mock.patch.object(
                PostgreSQLDatabaseCreation,
                "__init__",
                return_value=None,
            ),
            mock.patch.object(
                base_runner,
                "setup_databases",
                failing_setup,
            ),
        ):
            with self.assertRaisesMessage(
                RuntimeError,
                "database setup failed",
            ):
                runner.setup_databases(
                    aliases={"default": False}
                )

        self.assertIsInstance(
            observed["during_setup"],
            MigrationAwarePostgreSQLTestDatabaseCreation,
        )

        self.assertIs(
            connection.creation,
            original_creation,
        )
