from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from categories.category_seed_verification_v185 import (
    V185_CATEGORY_SEED_VERIFICATION_MARKER,
    build_category_seed_verification_report_v185,
)


V185_CATEGORY_VERIFY_COMMAND_MARKER = "V185_CATEGORY_VERIFY_COMMAND"


class Command(BaseCommand):
    help = "Verify the expanded marketplace category seed and Category admin setup."

    def add_arguments(self, parser):
        parser.add_argument(
            "--require-applied",
            action="store_true",
            help="Fail if the expanded 100-category taxonomy has not been applied.",
        )

    def handle(self, *args, **options):
        require_applied = bool(options.get("require_applied"))
        report = build_category_seed_verification_report_v185()

        self.stdout.write(V185_CATEGORY_VERIFY_COMMAND_MARKER)
        self.stdout.write(V185_CATEGORY_SEED_VERIFICATION_MARKER)
        self.stdout.write(f"Planned categories: {report.planned_count}")
        self.stdout.write(f"Existing planned categories: {report.existing_planned_count}")
        self.stdout.write(f"Missing planned categories: {report.missing_count}")
        self.stdout.write(f"Mismatched planned categories: {report.mismatched_count}")
        self.stdout.write(f"Extra non-plan categories: {report.extra_count}")
        self.stdout.write(f"Max planned category depth: {report.max_depth}")
        self.stdout.write(f"Admin registered: {report.admin_registered}")
        self.stdout.write(f"Admin fields OK: {report.admin_fields_ok}")
        self.stdout.write(f"Verified: {report.verified}")

        if report.missing_slugs:
            preview = ", ".join(report.missing_slugs[:20])
            self.stdout.write(f"Missing preview: {preview}")

        if report.mismatched_slugs:
            preview = ", ".join(report.mismatched_slugs[:20])
            self.stdout.write(f"Mismatch preview: {preview}")

        if require_applied and not report.verified:
            raise CommandError("Category seed verification failed.")

        if report.verified:
            self.stdout.write(self.style.SUCCESS("Category seed verification passed."))
        else:
            self.stdout.write("Category seed verification report complete.")
