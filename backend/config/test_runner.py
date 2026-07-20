from __future__ import annotations

from collections.abc import Iterable

from django.core.exceptions import ImproperlyConfigured
from django.db import connections
from django.db.backends.base.creation import TEST_DATABASE_PREFIX
from django.db.backends.postgresql.creation import (
    DatabaseCreation as PostgreSQLDatabaseCreation,
)
from django.test.runner import DiscoverRunner


class MigrationAwarePostgreSQLTestDatabaseCreation(
    PostgreSQLDatabaseCreation
):
    """
    Refresh preserved parallel clones from the migrated base test database.

    Django migrates the preserved base test database before cloning. Its
    default PostgreSQL keepdb behavior, however, reuses existing worker clones
    without migrating or replacing them. That can leave clone schemas behind
    the base schema after a new migration is added.
    """

    @staticmethod
    def _validated_clone_names(
        source_database_name: str,
        suffix: str,
        target_database_name: str,
    ) -> tuple[str, str]:
        normalized_suffix = str(suffix)

        if (
            not normalized_suffix.isdecimal()
            or int(normalized_suffix) < 1
        ):
            raise ImproperlyConfigured(
                "Parallel test database suffix must be a positive integer."
            )

        if not source_database_name.startswith(TEST_DATABASE_PREFIX):
            raise ImproperlyConfigured(
                "Refusing to refresh a parallel clone from a database "
                "without Django's test database prefix."
            )

        expected_target = (
            f"{source_database_name}_{normalized_suffix}"
        )

        if (
            target_database_name != expected_target
            or not target_database_name.startswith(TEST_DATABASE_PREFIX)
        ):
            raise ImproperlyConfigured(
                "Refusing to refresh an unexpected parallel test "
                "database name."
            )

        return source_database_name, target_database_name

    def _clone_test_db(
        self,
        suffix,
        verbosity,
        keepdb=False,
    ):
        if not keepdb:
            return super()._clone_test_db(
                suffix,
                verbosity,
                keepdb=False,
            )

        self.connection.close()
        self.connection.close_pool()

        source_database_name = str(
            self.connection.settings_dict["NAME"]
        )

        target_database_name = str(
            self.get_test_db_clone_settings(suffix)["NAME"]
        )

        (
            source_database_name,
            target_database_name,
        ) = self._validated_clone_names(
            source_database_name,
            str(suffix),
            target_database_name,
        )

        quoted_target = self._quote_name(
            target_database_name
        )

        test_db_params = {
            "dbname": quoted_target,
            "suffix": self._get_database_create_suffix(
                template=source_database_name
            ),
        }

        if verbosity >= 1:
            self.log(
                "Refreshing preserved parallel test database "
                f"{target_database_name!r} from migrated base "
                f"{source_database_name!r}..."
            )

        with self._nodb_cursor() as cursor:
            # Do not force-disconnect active sessions. An active worker clone
            # can indicate another test process, so refresh must fail safely
            # rather than terminating that process.
            cursor.execute(
                "DROP DATABASE IF EXISTS "
                f"{quoted_target}"
            )
            self._execute_create_test_db(
                cursor,
                test_db_params,
                keepdb=False,
            )


class MigrationAwareParallelDiscoverRunner(DiscoverRunner):
    """
    Install migration-aware PostgreSQL clone handling only for parallel keepdb.

    The replacement is temporary and is restored immediately after Django
    finishes test database setup. Serial runs, non-keepdb runs, non-PostgreSQL
    databases, and application runtime connections retain Django defaults.
    """

    def _database_aliases_for_setup(
        self,
        aliases,
    ) -> Iterable[str]:
        if aliases is None:
            return tuple(connections)

        return tuple(aliases)

    def setup_databases(self, **kwargs):
        if not (self.keepdb and self.parallel > 1):
            return super().setup_databases(**kwargs)

        original_creation_objects = {}

        for alias in self._database_aliases_for_setup(
            kwargs.get("aliases")
        ):
            connection = connections[alias]

            if connection.vendor != "postgresql":
                continue

            if isinstance(
                connection.creation,
                MigrationAwarePostgreSQLTestDatabaseCreation,
            ):
                continue

            original_creation_objects[alias] = (
                connection.creation
            )

            connection.creation = (
                MigrationAwarePostgreSQLTestDatabaseCreation(
                    connection
                )
            )

        try:
            return super().setup_databases(**kwargs)
        finally:
            for (
                alias,
                original_creation,
            ) in original_creation_objects.items():
                connections[alias].creation = (
                    original_creation
                )
