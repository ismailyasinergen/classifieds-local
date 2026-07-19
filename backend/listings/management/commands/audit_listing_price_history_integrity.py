"""Run the read-only v295 listing price-history integrity audit."""

import json

from django.core.management.base import BaseCommand, CommandError

from listings.listing_price_history_integrity_audit_v295 import (
    DEFAULT_MAX_FINDINGS_V295,
    MAX_FINDINGS_V295,
    audit_listing_price_history_integrity_v295,
)


class Command(BaseCommand):
    help = (
        "Audit listing price-history chains and guardrail evidence without "
        "modifying data."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--max-findings",
            type=int,
            default=DEFAULT_MAX_FINDINGS_V295,
            help=(
                "Maximum findings to print (1-"
                f"{MAX_FINDINGS_V295}; default {DEFAULT_MAX_FINDINGS_V295})."
            ),
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help="Emit sanitized machine-readable JSON.",
        )
        parser.add_argument(
            "--fail-on-findings",
            action="store_true",
            help="Return a command error when any finding is detected.",
        )

    def handle(self, *args, **options):
        try:
            report = audit_listing_price_history_integrity_v295(
                max_findings=options["max_findings"],
            )
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        if options["json_output"]:
            self.stdout.write(
                json.dumps(
                    report.as_dict(),
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
        else:
            self.stdout.write(
                "Price-history integrity audit: "
                f"listings={report.listing_count} "
                f"transitions={report.transition_count} "
                f"findings={report.finding_count} "
                f"displayed={len(report.displayed_findings)}"
            )
            for finding in report.displayed_findings:
                transition = (
                    str(finding.transition_id)
                    if finding.transition_id is not None
                    else "none"
                )
                self.stdout.write(
                    f"finding code={finding.code} "
                    f"listing_id={finding.listing_id} "
                    f"transition_id={transition}"
                )
            if report.is_truncated:
                self.stdout.write(
                    self.style.WARNING(
                        "Finding output was truncated; increase --max-findings "
                        "within the supported limit."
                    )
                )
            if report.is_clean:
                self.stdout.write(self.style.SUCCESS("Integrity audit passed."))

        if options["fail_on_findings"] and not report.is_clean:
            raise CommandError(
                f"Price-history integrity audit found {report.finding_count} issue(s)."
            )
